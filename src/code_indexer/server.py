"""Semantic Search MCP Server - Production Ready."""

import logging
import asyncio
import os
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from chromadb.errors import NotFoundError
import chromadb
from chromadb.config import Settings as ChromaSettings

from .utils import (
    get_allowed_extensions, 
    get_ignore_patterns,
    generate_collection_name,
    is_file_indexable,
    create_chunk_metadata,
    generate_chunk_id,
    MODIFICATION_CHECK_INTERVAL
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the MCP server
server = Server("semantic-search-mcp")


@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools."""
    logger.info("📋 Listing tools...")
    
    workspace_path = os.environ.get('WORKSPACE_PATH', 'Not configured')
    
    return [
        Tool(
            name="semantic_search",
            description=f"Semantic search across this project ({workspace_path}). Use for CONCEPTUAL queries about ideas, themes, patterns, processes, or flows. Transform single words into descriptive phrases: 'Liriel' → 'character Liriel personality and role', 'authentication' → 'user authentication flow and security'. For exact matches of specific names/functions, use Grep tool instead.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Conceptual query using descriptive phrases. Transform single words: 'authentication' → 'user authentication flow and patterns', 'calendar' → 'calendar system logic and implementation'. For exact string matches, use Grep instead."
                    }
                },
                "required": ["query"]
            }
        )
    ]


def get_workspace_info() -> Tuple[str, str]:
    """Get workspace directory and collection name from WORKSPACE_PATH environment variable."""
    
    # Get workspace path from environment variable
    workspace_path = os.environ.get('WORKSPACE_PATH')
    
    if not workspace_path:
        raise ValueError("WORKSPACE_PATH environment variable is required but not set")
    
    # Convert to Path and validate
    workspace_dir = Path(workspace_path)
    if not workspace_dir.exists():
        raise ValueError(f"Workspace directory does not exist: {workspace_path}")
    
    if not workspace_dir.is_dir():
        raise ValueError(f"Workspace path is not a directory: {workspace_path}")
    
    # Generate collection name using shared utility
    collection_name = generate_collection_name(workspace_path)
    
    logger.info(f"Using explicit workspace: {workspace_path} -> collection: {collection_name}")
    return str(workspace_dir.absolute()), collection_name



@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls.""" 
    logger.info(f"🔧 Tool called: {name} with args: {arguments}")
    
    if name == "semantic_search":
        query = arguments.get("query", "")
        response = await handle_semantic_search(query)
        return [TextContent(type="text", text=response)]
    
    else:
        error_msg = f"❌ Unknown tool: {name}"
        logger.error(error_msg)
        raise ValueError(error_msg)



async def handle_semantic_search(query: str) -> str:
    """Smart semantic search with auto-indexing and modification detection."""
    logger.info(f"🧠 Semantic search: '{query}'")
    
    try:
        # Get workspace from environment
        workspace_path, collection_name = get_workspace_info()
        logger.info(f"📁 Using workspace: {workspace_path} → collection: {collection_name}")
        
        dir_path = Path(workspace_path)
        if not dir_path.exists():
            return f"❌ Directory not found: {workspace_path}"
        
        client = get_chroma_client()
        
        # Check if collection exists
        try:
            collection = client.get_collection(collection_name)
            logger.info(f"📚 Found existing collection '{collection_name}' with {collection.count()} chunks")
            
            # Check for modified files and re-index if needed
            await check_and_update_collection(collection, collection_name)
            
        except NotFoundError:
            logger.info(f"📁 Collection '{collection_name}' not found, auto-indexing directory...")
            
            # Auto-index the directory
            index_result = await handle_index_directory(workspace_path, collection_name)
            if "❌" in index_result:
                # Show available collections in error
                collections = client.list_collections()
                if collections:
                    available = [f"• {col.name} ({col.count()} chunks)" for col in collections]
                    return f"{index_result}\n\n📚 Available collections:\n" + "\n".join(available)
                else:
                    return f"{index_result}\n\n📭 No collections available."
            
            # Get the newly created collection
            collection = client.get_collection(collection_name)
            logger.info(f"✅ Auto-indexed and created collection '{collection_name}'")
        
        # Perform the search
        results = collection.query(
            query_texts=[query],
            n_results=5
        )
        
        if (results['documents'] and results['documents'][0] and 
            results['metadatas'] and results['metadatas'][0] and
            results['distances'] and results['distances'][0]):
            
            response_parts = [f"🎯 Found {len(results['documents'][0])} results for '{query}':\n"]
            
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )):
                similarity = round((1 - distance) * 100, 1)
                file_path = metadata.get('file_path', 'unknown') if metadata else 'unknown'
                
                response_parts.append(f"\n📄 Result {i+1} ({similarity}% match) - {file_path}:")
                response_parts.append(f"```\n{doc}\n```")
                
            return "\n".join(response_parts)
        else:
            # No results found - show helpful message with available collections
            collections = client.list_collections()
            available = [f"• {col.name} ({col.count()} chunks)" for col in collections]
            
            return f"❌ No matches found for '{query}' in collection '{collection_name}'\n\n📚 Available collections:\n" + "\n".join(available)
            
    except Exception as e:
        logger.error(f"Semantic search error: {e}")
        return f"❌ Search failed: {str(e)}"


# Global ChromaDB client for persistence  
_chroma_client = None

# Modification check cache to avoid excessive filesystem checks
_last_modification_check = {}

def get_chroma_client() -> chromadb.ClientAPI:
    """Get or create global persistent ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(
            path="./chroma_db",
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        logger.info("📚 Created persistent ChromaDB client")
    return _chroma_client



async def handle_index_directory(directory_path: str, collection_name: str) -> str:
    """Index a directory of code files."""
    logger.info(f"📁 Indexing directory: {directory_path}")
    
    try:
        
        dir_path = Path(directory_path)
        if not dir_path.exists():
            return f"❌ Directory not found: {directory_path}"
        
        client = get_chroma_client()
        collection = client.get_or_create_collection(
            collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Get shared configuration
        allowed_extensions = get_allowed_extensions()
        ignore_patterns = get_ignore_patterns()
        
        files_processed = 0
        chunks_added = 0
        
        for file_path in dir_path.rglob("*"):
            indexable, reason = is_file_indexable(file_path, allowed_extensions, ignore_patterns)
            if not indexable:
                if "file too large" in reason:
                    logger.warning(f"Skipping file: {file_path} - {reason}")
                continue
                
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                # Simple chunking - split on double newlines
                chunks = [chunk.strip() for chunk in content.split('\n\n') if chunk.strip()]
                
                if chunks:
                    current_time = time.time()
                    
                    ids = [generate_chunk_id(file_path, i, current_time) for i in range(len(chunks))]
                    metadatas = [
                        create_chunk_metadata(file_path, dir_path, i) for i in range(len(chunks))
                    ]
                    
                    collection.add(
                        documents=chunks,
                        ids=ids,
                        metadatas=metadatas
                    )
                    
                    chunks_added += len(chunks)
                    files_processed += 1
                    
            except Exception as e:
                logger.warning(f"Failed to index {file_path}: {e}")
                continue
        
        return f"✅ Indexed {files_processed} files, {chunks_added} chunks in collection '{collection_name}'"
        
    except Exception as e:
        logger.error(f"Indexing error: {e}")
        return f"❌ Indexing failed: {str(e)}"




async def check_and_update_collection(collection, collection_name: str) -> None:
    """Check for modified files and update collection if needed."""
    if not _should_check_modifications(collection_name):
        return
        
    try:
        logger.info(f"🔍 Checking for file modifications in collection '{collection_name}'")
        _last_modification_check[collection_name] = time.time()
        
        # Get collection metadata
        all_metadata = collection.get()['metadatas']
        if not all_metadata:
            logger.debug(f"No metadata found in collection '{collection_name}'")
            return
        
        workspace_dir = _get_workspace_from_metadata(all_metadata)
        if not workspace_dir:
            logger.warning("Could not determine workspace directory from metadata")
            return
        
        # Find modified and deleted files
        files_to_reindex = _find_modified_files(all_metadata)
        deleted_files = _find_deleted_files(all_metadata, workspace_dir)
        
        # Process updates
        await _process_file_updates(collection, files_to_reindex, deleted_files, workspace_dir, collection_name)
        
    except Exception as e:
        logger.warning(f"File check error: {e}")


def _should_check_modifications(collection_name: str) -> bool:
    """Check if modification check is needed based on rate limiting."""
    current_time = time.time()
    last_check_time = _last_modification_check.get(collection_name, 0)
    
    if current_time - last_check_time < MODIFICATION_CHECK_INTERVAL:
        logger.debug(f"Skipping modification check for '{collection_name}' (checked {(current_time - last_check_time)/60:.1f} minutes ago)")
        return False
    return True


def _get_workspace_from_metadata(metadata_list: List[Dict[str, Any]]) -> Optional[Path]:
    """Extract workspace directory from collection metadata."""
    if not metadata_list:
        return None
    
    workspace_path = metadata_list[0].get('collection_root')
    return Path(workspace_path) if workspace_path else None


def _find_modified_files(metadata_list: List[Dict[str, Any]]) -> List[Path]:
    """Find files that have been modified since indexing."""
    files_to_reindex = []
    
    # Build file path set
    file_paths = set()
    for metadata in metadata_list:
        file_path = metadata.get('file_path')
        collection_root = metadata.get('collection_root')
        if file_path and collection_root:
            full_path = Path(collection_root) / file_path
            file_paths.add((str(full_path), metadata.get('last_modified', 0)))
    
    # Check modifications
    for file_path_str, last_indexed_time in file_paths:
        file_path = Path(file_path_str)
        if file_path.exists():
            current_mtime = file_path.stat().st_mtime
            if current_mtime > last_indexed_time:
                logger.info(f"📝 File modified: {file_path_str} (indexed: {datetime.fromtimestamp(last_indexed_time).strftime('%H:%M')}, current: {datetime.fromtimestamp(current_mtime).strftime('%H:%M')})")
                files_to_reindex.append(file_path)
    
    return files_to_reindex


def _find_deleted_files(metadata_list: List[Dict[str, Any]], workspace_dir: Path) -> List[str]:
    """Find files that have been deleted since indexing."""
    indexed_files = {metadata.get('file_path') for metadata in metadata_list if metadata.get('file_path')}
    deleted_files = []
    
    for indexed_file_path in indexed_files:
        if indexed_file_path:
            full_path = workspace_dir / indexed_file_path
            if not full_path.exists():
                deleted_files.append(indexed_file_path)
    
    return deleted_files


async def _process_file_updates(collection, files_to_reindex: List[Path], deleted_files: List[str], 
                               workspace_dir: Path, collection_name: str) -> None:
    """Process file modifications and deletions."""
    # Re-index modified files
    if files_to_reindex:
        logger.info(f"📝 Re-indexing {len(files_to_reindex)} modified files")
        for file_path in files_to_reindex:
            await reindex_single_file(collection, file_path, workspace_dir, collection_name)
    
    # Remove chunks for deleted files
    if deleted_files:
        logger.info(f"🗑️  Removing chunks for {len(deleted_files)} deleted files")
        for deleted_file in deleted_files:
            logger.info(f"🗑️  Cleaning up deleted file: {deleted_file}")
            collection.delete(where={"file_path": deleted_file})


async def reindex_single_file(collection, file_path: Path, workspace_dir: Path, collection_name: str) -> None:
    """Re-index a single modified file."""
    try:
        # Remove old chunks for this file using full relative path
        rel_path = str(file_path.relative_to(workspace_dir))
        logger.info(f"🔄 Re-indexing modified file: {rel_path}")
        collection.delete(where={"file_path": rel_path})
        
        # Read and re-index the file
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        chunks = [chunk.strip() for chunk in content.split('\n\n') if chunk.strip()]
        
        if chunks:
            current_time = time.time()
            
            ids = [f"{file_path.name}_{i}_{int(current_time)}" for i in range(len(chunks))]
            metadatas = [
                {
                    'file_path': rel_path,
                    'collection_root': str(workspace_dir),
                    'last_modified': current_time
                }
                for _ in chunks
            ]
            
            collection.add(
                documents=chunks,
                ids=ids,
                metadatas=metadatas
            )
            
            logger.info(f"✅ Re-indexed {len(chunks)} chunks from {rel_path}")
            
    except Exception as e:
        logger.warning(f"Failed to re-index {file_path}: {e}")





async def main():
    """Run the MCP server."""
    logger.info("🚀 Starting semantic search MCP server...")
    logger.info("💡 Run this with: uv run scripts/run_server.py")
    
    try:
        async with stdio_server() as streams:
            await server.run(
                streams[0], 
                streams[1], 
                server.create_initialization_options()
            )
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        raise


if __name__ == "__main__":
    logger.info("🎯 Starting semantic search MCP server...")
    asyncio.run(main())