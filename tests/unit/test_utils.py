"""Test utility functions."""

import pytest
import tempfile
import sys
from pathlib import Path

# Add src to path for imports  
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from code_indexer.utils import (
    should_ignore_path,
    generate_collection_name,
    is_file_indexable,
    generate_chunk_id
)


def test_should_ignore_path():
    """Test path ignoring logic."""
    ignore_patterns = {'.venv', 'node_modules', '__pycache__', '*.log'}
    
    # Should ignore
    assert should_ignore_path(Path('/project/.venv/lib/file.py'), ignore_patterns)
    assert should_ignore_path(Path('/project/node_modules/package.js'), ignore_patterns)
    assert should_ignore_path(Path('/project/__pycache__/file.pyc'), ignore_patterns)
    assert should_ignore_path(Path('/project/app.log'), ignore_patterns)
    
    # Should not ignore
    assert not should_ignore_path(Path('/project/src/main.py'), ignore_patterns)
    assert not should_ignore_path(Path('/project/README.md'), ignore_patterns)


def test_generate_collection_name():
    """Test collection name generation."""
    # Test basic name generation
    name1 = generate_collection_name('/path/to/my-project')
    name2 = generate_collection_name('/different/path/my-project')
    
    assert isinstance(name1, str)
    assert isinstance(name2, str)
    
    # Should have project name and hash
    assert 'my_project' in name1
    assert 'my_project' in name2
    
    # Different paths should have different hashes
    assert name1 != name2
    
    # Should be safe identifiers
    assert name1.replace('_', '').isalnum()
    assert name2.replace('_', '').isalnum()


def test_is_file_indexable():
    """Test file indexing eligibility."""
    allowed_extensions = {'.py', '.md', '.js'}
    ignore_patterns = {'.venv', 'node_modules'}
    max_file_size = 1024 * 1024  # 1MB
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test files
        py_file = temp_path / 'test.py'
        py_file.write_text('print("hello")')
        
        large_file = temp_path / 'large.py'
        large_file.write_text('x' * (2 * 1024 * 1024))  # 2MB
        
        ignored_file = temp_path / '.venv' / 'lib.py'
        ignored_file.parent.mkdir()
        ignored_file.write_text('lib code')
        
        binary_file = temp_path / 'image.png'
        binary_file.write_text('fake image')
        
        # Test indexable file
        indexable, reason = is_file_indexable(py_file, allowed_extensions, ignore_patterns, max_file_size)
        assert indexable
        assert reason == ""
        
        # Test large file
        indexable, reason = is_file_indexable(large_file, allowed_extensions, ignore_patterns, max_file_size)
        assert not indexable
        assert "file too large" in reason
        
        # Test ignored path
        indexable, reason = is_file_indexable(ignored_file, allowed_extensions, ignore_patterns, max_file_size)
        assert not indexable
        assert "path matches ignore pattern" in reason
        
        # Test wrong extension
        indexable, reason = is_file_indexable(binary_file, allowed_extensions, ignore_patterns, max_file_size)
        assert not indexable
        assert "not in allowlist" in reason


def test_generate_chunk_id():
    """Test chunk ID generation."""
    file_path = Path('/project/src/main.py')
    
    # Test with timestamp
    chunk_id = generate_chunk_id(file_path, 0, 1234567890)
    assert 'main.py' in chunk_id
    assert '0' in chunk_id
    assert '1234567890' in chunk_id
    
    # Test without timestamp (uses current time)
    chunk_id2 = generate_chunk_id(file_path, 1)
    assert 'main.py' in chunk_id2
    assert '1' in chunk_id2
    
    # Different chunk indices should give different IDs
    assert chunk_id != chunk_id2