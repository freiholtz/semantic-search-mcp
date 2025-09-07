#!/usr/bin/env python3
"""CLI management tool for Semantic Search MCP collections."""

import os
import sys
from pathlib import Path
import chromadb
from chromadb.config import Settings as ChromaSettings
from datetime import datetime

# Import shared utilities
sys.path.insert(0, str(Path(__file__).parent / "src"))
from code_indexer.utils import (
    should_ignore_path,
    generate_collection_name,
    is_file_indexable
)
from code_indexer.config import (
    get_allowed_extensions,
    get_ignore_patterns,
    get_max_file_size
)


def get_client():
    """Get ChromaDB client."""
    try:
        return chromadb.PersistentClient(
            path="./chroma_db",
            settings=ChromaSettings(anonymized_telemetry=False)
        )
    except Exception as e:
        print(f"❌ Failed to connect to ChromaDB: {e}")
        sys.exit(1)


def get_folder_size(path):
    """Get folder size in MB."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.exists(filepath):
                total_size += os.path.getsize(filepath)
    return total_size / (1024 * 1024)  # Convert to MB


def list_collections():
    """List all indexed collections with details."""
    client = get_client()
    collections = client.list_collections()
    
    if not collections:
        print("📭 No indexed projects found.")
        return []
    
    print(f"\n📚 Found {len(collections)} indexed projects:\n")
    
    collection_info = []
    for i, col in enumerate(collections, 1):
        try:
            count = col.count()
            # Get some metadata to estimate dates
            sample_data = col.get(limit=1)
            if sample_data['metadatas'] and sample_data['metadatas'][0]:
                last_modified = sample_data['metadatas'][0].get('last_modified')
                if last_modified:
                    last_date = datetime.fromtimestamp(last_modified).strftime('%Y-%m-%d %H:%M')
                else:
                    last_date = "Unknown"
            else:
                last_date = "Unknown"
            
            # Estimate size (rough calculation)
            size_mb = count * 0.002  # Rough estimate: ~2KB per chunk
            
            print(f"{i}. {col.name} {size_mb:.1f} MB ({count} chunks) - Last: {last_date}")
            collection_info.append({
                'index': i,
                'name': col.name,
                'collection': col,
                'count': count,
                'size_mb': size_mb,
                'last_date': last_date
            })
        except Exception as e:
            print(f"{i}. {col.name} - Error reading collection: {e}")
            collection_info.append({
                'index': i,
                'name': col.name,
                'collection': col,
                'count': 0,
                'size_mb': 0,
                'last_date': "Error"
            })
    
    return collection_info


def show_info(collection_info, index):
    """Show detailed info for a collection."""
    if index < 1 or index > len(collection_info):
        print("❌ Invalid collection number")
        return
    
    info = collection_info[index - 1]
    col = info['collection']
    
    print("\n📋 Collection Details:")
    print(f"Name: {info['name']}")
    print(f"Size: {info['size_mb']:.1f} MB")
    print(f"Chunks: {info['count']}")
    
    try:
        # Get all metadata to find first and last modified dates
        all_data = col.get()
        timestamps = []
        
        if all_data['metadatas']:
            for metadata in all_data['metadatas']:
                if metadata and 'last_modified' in metadata:
                    timestamps.append(metadata['last_modified'])
        
        if timestamps:
            first_modified = datetime.fromtimestamp(min(timestamps)).strftime('%Y-%m-%d %H:%M')
            last_modified = datetime.fromtimestamp(max(timestamps)).strftime('%Y-%m-%d %H:%M')
            
            print(f"First Indexed: {first_modified}")
            print(f"Last Modified: {last_modified}")
            
            # Show how long we've been indexing this project
            days_diff = (max(timestamps) - min(timestamps)) / (24 * 3600)
            if days_diff < 1:
                print("Indexing Duration: Less than 1 day")
            else:
                print(f"Indexing Duration: {days_diff:.1f} days")
        else:
            print("Modified Dates: Unknown")
            
    except Exception as e:
        print(f"Could not retrieve timestamp data: {e}")




def investigate_workspace(workspace_path):
    """Analyze workspace without indexing to show estimation."""
    print(f"\n🔍 Analyzing workspace: {workspace_path}")
    
    try:
        workspace_dir = Path(workspace_path)
        if not workspace_dir.exists():
            print(f"❌ Directory not found: {workspace_path}")
            return
        
        if not workspace_dir.is_dir():
            print(f"❌ Path is not a directory: {workspace_path}")
            return
        
        allowed_extensions = get_allowed_extensions()
        ignore_patterns = get_ignore_patterns()
        
        # Scan files
        valid_files = []
        total_size = 0
        by_extension = {}
        skipped_large = 0
        
        print("📊 Scanning files...")
        
        for file_path in workspace_dir.rglob("*"):
            indexable, reason = is_file_indexable(file_path, allowed_extensions, ignore_patterns, get_max_file_size())
            if not indexable:
                if "file too large" in reason:
                    skipped_large += 1
                continue
                
            try:
                file_size = file_path.stat().st_size
                
                ext = file_path.suffix.lower()
                if ext not in by_extension:
                    by_extension[ext] = {'count': 0, 'size': 0}
                
                by_extension[ext]['count'] += 1
                by_extension[ext]['size'] += file_size
                
                valid_files.append((file_path, file_size))
                total_size += file_size
                
            except Exception as e:
                print(f"⚠️  Error scanning {file_path}: {e}")
        
        # Calculate estimates
        collection_name = generate_collection_name(workspace_path)
        estimated_chunks = sum(max(1, size // 200) for _, size in valid_files)  # Rough estimate: ~200 chars per chunk
        estimated_time = len(valid_files) * 0.1  # Rough estimate: ~0.1 sec per file
        
        print("\n📋 Workspace Analysis Results:")
        print(f"📁 Workspace: {workspace_path}")
        print(f"🏷️  Collection: {collection_name}")
        print(f"📊 Files to index: {len(valid_files):,} files")
        print(f"📈 Total size: {total_size/1024/1024:.1f} MB")
        print(f"🧩 Estimated chunks: ~{estimated_chunks:,} chunks")
        print(f"⏱️  Estimated time: {estimated_time/60:.1f} minutes")
        
        if skipped_large > 0:
            print(f"⚠️  Skipped {skipped_large} files >1MB")
        
        # Show breakdown by file type
        if by_extension:
            print("\n📂 File breakdown:")
            for ext, data in sorted(by_extension.items(), key=lambda x: x[1]['size'], reverse=True)[:8]:
                size_mb = data['size'] / 1024 / 1024
                print(f"  • {ext}: {data['count']} files ({size_mb:.1f} MB)")
        
        return len(valid_files), total_size, estimated_chunks, collection_name
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return None


def output_mcp_config_for_workspace(workspace_path):
    """Output MCP server configuration JSON for workspace path."""
    try:
        workspace_dir = Path(workspace_path)
        if not workspace_dir.exists():
            print(f"❌ Directory not found: {workspace_path}")
            return
        
        if not workspace_dir.is_dir():
            print(f"❌ Path is not a directory: {workspace_path}")
            return
        
        _generate_mcp_config(workspace_path)
        
    except Exception as e:
        print(f"❌ Failed to generate config: {e}")


def output_mcp_config_for_collection(collection_info, index):
    """Output MCP server configuration JSON for existing collection."""
    if index < 1 or index > len(collection_info):
        print("❌ Invalid collection number")
        return
    
    info = collection_info[index - 1]
    col = info['collection']
    
    try:
        # Get workspace path from collection metadata
        sample_data = col.get(limit=1)
        if not sample_data['metadatas'] or not sample_data['metadatas'][0]:
            print("❌ No metadata found in collection")
            return
        
        workspace_path = sample_data['metadatas'][0].get('collection_root')
        if not workspace_path:
            print("❌ No workspace path found in collection metadata")
            return
        
        print(f"\n📄 MCP Configuration for existing collection: {info['name']}")
        _generate_mcp_config(workspace_path)
        
    except Exception as e:
        print(f"❌ Failed to generate config from collection: {e}")


def _generate_mcp_config(workspace_path):
    """Generate and display MCP configuration."""
    import json
    
    # Generate collection name for reference
    collection_name = generate_collection_name(workspace_path)
    script_dir = Path(__file__).parent.absolute()
    
    config = {
        "mcpServers": {
            "semantic-search": {
                "command": "uv",
                "args": [
                    "run",
                    "--directory",
                    str(script_dir),
                    "scripts/run_server.py"
                ],
                "env": {
                    "WORKSPACE_PATH": workspace_path
                }
            }
        }
    }
    
    print(f"📁 Workspace: {workspace_path}")
    print(f"🏷️  Collection: {collection_name}")
    print("\n📋 Copy this JSON to your .claude.json:")
    print(json.dumps(config, indent=2))
    
    print("\n💡 Or use this command:")
    print(f"claude mcp add semantic-search --env WORKSPACE_PATH=\"{workspace_path}\" -- uv run --directory {script_dir} scripts/run_server.py")


def add_workspace(workspace_path):
    """Add and index a workspace with progress tracking."""
    print(f"\n🚀 Adding workspace: {workspace_path}")
    
    # First, run investigation
    result = investigate_workspace(workspace_path)
    if not result:
        return
    
    file_count, total_size, estimated_chunks, collection_name = result
    
    # Ask for confirmation
    size_mb = total_size / 1024 / 1024
    print("\n⚠️  INDEXING CONFIRMATION")
    print(f"This will index {file_count:,} files ({size_mb:.1f} MB)")
    print(f"Estimated {estimated_chunks:,} chunks in collection '{collection_name}'")
    
    confirm = input("\nContinue with indexing? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ Indexing cancelled")
        return
    
    # Start indexing with progress
    print("\n📁 Starting indexing...")
    
    try:
        client = get_client()
        collection = client.get_or_create_collection(
            collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        workspace_dir = Path(workspace_path)
        allowed_extensions = get_allowed_extensions()
        ignore_patterns = get_ignore_patterns()
        MAX_FILE_SIZE = 1024 * 1024
        
        files_processed = 0
        chunks_added = 0
        
        # Get valid files list for progress tracking
        valid_files = []
        for file_path in workspace_dir.rglob("*"):
            if (file_path.is_file() and 
                file_path.suffix.lower() in allowed_extensions and
                not should_ignore_path(file_path, ignore_patterns)):
                
                try:
                    if file_path.stat().st_size <= MAX_FILE_SIZE:
                        valid_files.append(file_path)
                except Exception:
                    continue
        
        print(f"📊 Processing {len(valid_files)} files...")
        
        for i, file_path in enumerate(valid_files):
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                # Simple chunking - split on double newlines
                chunks = [chunk.strip() for chunk in content.split('\n\n') if chunk.strip()]
                
                if chunks:
                    import time
                    current_time = time.time()
                    
                    ids = [f"{file_path.name}_{j}_{int(current_time)}" for j in range(len(chunks))]
                    metadatas = [
                        {
                            "file_path": str(file_path.relative_to(workspace_dir)),
                            "collection_root": str(workspace_dir),
                            "last_modified": current_time
                        } 
                        for _ in chunks
                    ]
                    
                    collection.add(
                        documents=chunks,
                        ids=ids,
                        metadatas=metadatas
                    )
                    
                    chunks_added += len(chunks)
                    files_processed += 1
                
                # Progress update every 50 files
                if (i + 1) % 50 == 0 or i == len(valid_files) - 1:
                    progress = ((i + 1) / len(valid_files)) * 100
                    print(f"Progress: {progress:5.1f}% | Files: {files_processed:,}/{len(valid_files):,} | Chunks: {chunks_added:,}")
                    
            except Exception as e:
                print(f"⚠️  Failed to index {file_path}: {e}")
                continue
        
        print("\n✅ Indexing complete!")
        print(f"📊 Indexed {files_processed:,} files with {chunks_added:,} chunks")
        print(f"🏷️  Collection: {collection_name}")
        print("🔍 Ready for @semantic_search!")
        
    except Exception as e:
        print(f"❌ Indexing failed: {e}")


def delete_collection(collection_info, index):
    """Delete a collection after confirmation."""
    if index < 1 or index > len(collection_info):
        print("❌ Invalid collection number")
        return
    
    info = collection_info[index - 1]
    name = info['name']
    
    print("\n⚠️  DELETE CONFIRMATION")
    print(f"Collection: {name}")
    print(f"Size: {info['size_mb']:.1f} MB ({info['count']} chunks)")
    print("⚠️  This action CANNOT be undone!")
    print("💡 The collection will be re-indexed next time the MCP tool is used in that project.")
    
    confirm = input(f"\nType 'DELETE' to confirm deletion of '{name}': ").strip()
    
    if confirm == 'DELETE':
        try:
            client = get_client()
            client.delete_collection(name)
            print(f"✅ Successfully deleted collection '{name}'")
        except Exception as e:
            print(f"❌ Failed to delete collection: {e}")
    else:
        print("❌ Deletion cancelled")


def main():
    """Main CLI interface."""
    print("SEMANTIC SEARCH MCP")
    print("------------------")
    
    while True:
        # Check if chroma_db exists (relative to this script)
        script_dir = Path(__file__).parent
        chroma_path = script_dir / "chroma_db"
        
        if chroma_path.exists():
            print("\nIndexed projects:")
            collection_info = list_collections()
            
            if not collection_info:
                print("📭 No collections found.")
            
            print("\nOptions: delete <nr>, info <nr>, json <nr>, investigate <path>, add <path>, json <path>, exit")
        else:
            print("\n📭 No indexed data found.")
            print("\nOptions: investigate <path>, add <path>, json <path>, exit")
            collection_info = []
        
        try:
            command = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Goodbye!")
            break
        
        if command.lower() == 'exit':
            print("👋 Goodbye!")
            break
        elif command.lower().startswith('delete '):
            try:
                index = int(command.split()[1])
                delete_collection(collection_info, index)
            except (ValueError, IndexError):
                print("❌ Usage: delete <number>")
        elif command.lower().startswith('info '):
            try:
                index = int(command.split()[1])
                show_info(collection_info, index)
            except (ValueError, IndexError):
                print("❌ Usage: info <number>")
        elif command.lower().startswith('investigate '):
            try:
                path = ' '.join(command.split()[1:])  # Handle paths with spaces
                if path:
                    investigate_workspace(path)
                else:
                    print("❌ Usage: investigate <workspace_path>")
            except Exception as e:
                print(f"❌ Error: {e}")
        elif command.lower().startswith('add '):
            try:
                path = ' '.join(command.split()[1:])  # Handle paths with spaces
                if path:
                    add_workspace(path)
                else:
                    print("❌ Usage: add <workspace_path>")
            except Exception as e:
                print(f"❌ Error: {e}")
        elif command.lower().startswith('json '):
            try:
                arg = command.split()[1] if len(command.split()) > 1 else ""
                if not arg:
                    print("❌ Usage: json <number> or json <workspace_path>")
                elif arg.isdigit():
                    # json <number> - use existing collection
                    index = int(arg)
                    if collection_info:
                        output_mcp_config_for_collection(collection_info, index)
                    else:
                        print("❌ No collections available")
                else:
                    # json <path> - analyze workspace path  
                    path = ' '.join(command.split()[1:])  # Handle paths with spaces
                    output_mcp_config_for_workspace(path)
            except Exception as e:
                print(f"❌ Error: {e}")
        else:
            print("❌ Commands: delete <nr>, info <nr>, json <nr>/<path>, investigate <path>, add <path>, exit")


if __name__ == "__main__":
    main()