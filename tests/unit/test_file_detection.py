"""Test file modification and new file detection."""

import pytest
import tempfile
import time
import sys
import os
from pathlib import Path
import chromadb
from chromadb.config import Settings as ChromaSettings

# Add src to path for imports  
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from code_indexer.utils import generate_collection_name
from code_indexer.config import get_allowed_extensions, get_ignore_patterns, get_max_file_size


class TestFileDetection:
    """Test file modification and new file detection capabilities."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace with test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            
            # Create initial files
            (workspace / "main.py").write_text("def main():\n    print('hello world')")
            (workspace / "utils.py").write_text("def helper():\n    return 'utility function'")
            (workspace / "README.md").write_text("# Test Project\nThis is a test project.")
            
            yield workspace
    
    @pytest.fixture  
    def chroma_client(self):
        """Create a test ChromaDB client."""
        with tempfile.TemporaryDirectory() as temp_db:
            client = chromadb.PersistentClient(
                path=temp_db,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            yield client
    
    def index_workspace_initially(self, workspace: Path, client: chromadb.ClientAPI):
        """Index workspace for the first time (simulate initial indexing)."""
        collection_name = generate_collection_name(str(workspace))
        collection = client.get_or_create_collection(
            collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        allowed_extensions = get_allowed_extensions()
        ignore_patterns = get_ignore_patterns()
        max_file_size = get_max_file_size()
        
        # Index all initial files
        for file_path in workspace.rglob("*"):
            if (file_path.is_file() and 
                file_path.suffix.lower() in allowed_extensions and
                file_path.stat().st_size <= max_file_size):
                
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    chunks = [chunk.strip() for chunk in content.split('\n\n') if chunk.strip()]
                    
                    if chunks:
                        current_time = time.time()
                        ids = [f"{file_path.name}_{i}_{int(current_time)}" for i in range(len(chunks))]
                        metadatas = [
                            {
                                "file_path": str(file_path.relative_to(workspace)),
                                "collection_root": str(workspace),
                                "last_modified": current_time
                            } 
                            for _ in chunks
                        ]
                        
                        collection.add(
                            documents=chunks,
                            ids=ids,
                            metadatas=metadatas
                        )
                except Exception as e:
                    print(f"Failed to index {file_path}: {e}")
        
        return collection_name, collection
    
    def check_file_in_collection(self, collection, workspace: Path, filename: str) -> bool:
        """Check if a file exists in the collection."""
        rel_path = filename
        all_data = collection.get()
        
        if all_data['metadatas']:
            for metadata in all_data['metadatas']:
                if metadata and metadata.get('file_path') == rel_path:
                    return True
        return False
    
    def search_collection_for_content(self, collection, search_term: str) -> list:
        """Search collection for specific content."""
        try:
            results = collection.query(
                query_texts=[search_term],
                n_results=5
            )
            return results['documents'][0] if results['documents'] and results['documents'][0] else []
        except Exception:
            return []
    
    def test_initial_indexing_works(self, temp_workspace, chroma_client):
        """Test that initial indexing works correctly."""
        collection_name, collection = self.index_workspace_initially(temp_workspace, chroma_client)
        
        # Verify initial files are indexed
        assert self.check_file_in_collection(collection, temp_workspace, "main.py")
        assert self.check_file_in_collection(collection, temp_workspace, "utils.py") 
        assert self.check_file_in_collection(collection, temp_workspace, "README.md")
        
        # Verify content can be found
        results = self.search_collection_for_content(collection, "hello world")
        assert len(results) > 0
        assert any("hello world" in result for result in results)
    
    def test_new_file_detection_fails(self, temp_workspace, chroma_client):
        """Test that demonstrates the bug: new files are not detected."""
        # Initial indexing
        collection_name, collection = self.index_workspace_initially(temp_workspace, chroma_client)
        initial_count = collection.count()
        
        # Wait a moment to ensure different timestamp
        time.sleep(0.1)
        
        # Add a new file with unique content
        new_file = temp_workspace / "quantum_meditation.py"
        new_file.write_text("""def quantum_meditation_synchronizer():
    '''Quantum Meditation Synchronizer with bio-rhythm detection'''
    import time
    from philips_hue import HueController
    
    def sync_brainwaves_with_lighting():
        # Sync Philips Hue lights with detected brainwave patterns
        return "consciousness state synchronized"
    
    return sync_brainwaves_with_lighting()
""")
        
        # Simulate the modification check that should happen during search
        # This is the key test: after adding a new file, can we find it?
        from code_indexer.server import _find_modified_files, _find_deleted_files
        
        # Check if the new file would be detected by current functions
        workspace_dir = temp_workspace
        all_data = collection.get()
        
        modified_files = _find_modified_files(all_data.get('metadatas', []))
        deleted_files = _find_deleted_files(all_data.get('metadatas', []), workspace_dir)
        
        print(f"Modified files detected: {modified_files}")
        print(f"Deleted files detected: {deleted_files}") 
        print(f"New file exists: {new_file.exists()}")
        
        # THE BUG: Current functions don't detect NEW files at all!
        # This test documents the bug - new_file should be detected but won't be
        # because there's no _find_new_files function
        
        # Let's manually check if the new file would be detected
        # (This simulates what a _find_new_files function should do)
        indexed_files = set()
        for metadata in all_data.get('metadatas', []):
            if metadata and metadata.get('file_path'):
                indexed_files.add(metadata['file_path'])
        
        # Find all indexable files in workspace
        from code_indexer.utils import is_file_indexable
        allowed_extensions = get_allowed_extensions()
        ignore_patterns = get_ignore_patterns() 
        max_file_size = get_max_file_size()
        
        all_workspace_files = set()
        for file_path in workspace_dir.rglob("*"):
            if file_path.is_file():
                rel_path = str(file_path.relative_to(workspace_dir))
                indexable, _ = is_file_indexable(file_path, allowed_extensions, ignore_patterns, max_file_size)
                if indexable:
                    all_workspace_files.add(rel_path)
        
        # New files = files in workspace but not in collection
        new_files = all_workspace_files - indexed_files
        print(f"New files found: {new_files}")
        
        # THE BUG TEST: The new file should be in new_files
        new_file_rel = str(new_file.relative_to(workspace_dir))
        assert new_file_rel in new_files, f"New file {new_file_rel} should be detected in new_files: {new_files}"
        
        # The new file should NOT be indexed yet (this demonstrates the bug)
        # Because the system doesn't detect new files, this will be False:
        new_file_indexed = self.check_file_in_collection(collection, temp_workspace, "quantum_meditation.py")
        
        # BUG DEMONSTRATION: The new file should not be indexed yet
        assert not new_file_indexed, "BUG DEMONSTRATED: New file should not be indexed yet because system doesn't detect new files"
        
        # BUG DEMONSTRATION: Collection count should be the same (no new chunks added)
        final_count = collection.count()
        assert final_count == initial_count, f"BUG DEMONSTRATED: Collection count should be same because new file wasn't indexed. Initial: {initial_count}, Final: {final_count}"
        
        # SUCCESS: We can detect new files manually (this is what the fix needs to do)
        print(f"✅ New file detection logic works - found: {new_files}")
        print(f"❌ But system doesn't use this logic automatically")
        print(f"❌ File indexed: {new_file_indexed}")
        print(f"❌ Collection count unchanged: {initial_count} -> {final_count}")
    
    def test_file_modification_detection(self, temp_workspace, chroma_client):
        """Test that modified files are detected and reindexed."""
        # Initial indexing
        collection_name, collection = self.index_workspace_initially(temp_workspace, chroma_client)
        
        # Wait to ensure different timestamp
        time.sleep(0.1)
        
        # Modify an existing file
        main_file = temp_workspace / "main.py"
        main_file.write_text("""def main():
    print('hello world')
    print('this file has been modified with quantum meditation features')
    
def new_quantum_function():
    return "bio-rhythm synchronization active"
""")
        
        # Check modification detection
        from code_indexer.server import _find_modified_files
        
        all_data = collection.get()
        modified_files = _find_modified_files(all_data.get('metadatas', []))
        
        # Should detect the modified file
        assert main_file in modified_files, f"Modified file should be detected. Found modified: {modified_files}"
        
        # For now, just verify the detection works - 
        # the actual reindexing would happen in the MCP server flow
    
    @pytest.mark.asyncio
    async def test_new_file_detection_fix_works(self, temp_workspace, chroma_client):
        """Test that the fix allows new files to be detected and indexed."""
        # Initial indexing
        collection_name, collection = self.index_workspace_initially(temp_workspace, chroma_client)
        initial_count = collection.count()
        
        # Wait a moment to ensure different timestamp
        time.sleep(0.1)
        
        # Add a new file with unique content
        new_file = temp_workspace / "bio_rhythm_tracker.py"
        new_file.write_text("""def bio_rhythm_tracker():
    '''Advanced bio-rhythm tracking with circadian analysis'''
    import datetime
    
    def analyze_circadian_patterns():
        return "bio_rhythm_analysis_complete"
    
    return analyze_circadian_patterns()
""")
        
        # Use the NEW detection function
        from code_indexer.server import _find_new_files
        
        all_data = collection.get()
        new_files = _find_new_files(all_data.get('metadatas', []), temp_workspace)
        
        # Should detect the new file
        assert new_file in new_files, f"New file should be detected. Found: {new_files}"
        
        # Simulate the indexing that would happen in _process_file_updates
        if new_files:
            from code_indexer.server import reindex_single_file
            for file_path in new_files:
                await reindex_single_file(collection, file_path, temp_workspace, collection_name)
        
        # Verify the new file is now indexed
        new_file_indexed = self.check_file_in_collection(collection, temp_workspace, "bio_rhythm_tracker.py")
        assert new_file_indexed, "New file should be indexed after processing"
        
        # Collection count should be higher
        final_count = collection.count()
        assert final_count > initial_count, f"Collection should have more chunks after indexing new file. Initial: {initial_count}, Final: {final_count}"