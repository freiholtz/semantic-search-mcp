"""Test management command functions."""

import pytest
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from manage import investigate_workspace, generate_collection_name


def test_investigate_workspace_nonexistent():
    """Test investigating non-existent workspace."""
    # Capture print output by redirecting to list
    output = []
    
    with patch('builtins.print', side_effect=lambda *args: output.append(' '.join(map(str, args)))):
        result = investigate_workspace('/nonexistent/path')
    
    assert result is None
    assert any('Directory not found' in line for line in output)


def test_investigate_workspace_file_not_directory():
    """Test investigating a file instead of directory."""
    with tempfile.NamedTemporaryFile() as temp_file:
        output = []
        
        with patch('builtins.print', side_effect=lambda *args: output.append(' '.join(map(str, args)))):
            result = investigate_workspace(temp_file.name)
        
        assert result is None
        assert any('not a directory' in line for line in output)


def test_investigate_workspace_empty_directory():
    """Test investigating empty workspace."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set WORKSPACE_PATH for config
        with patch.dict('os.environ', {'WORKSPACE_PATH': temp_dir}):
            output = []
            
            with patch('builtins.print', side_effect=lambda *args: output.append(' '.join(map(str, args)))):
                result = investigate_workspace(temp_dir)
            
            # Should complete successfully even with 0 files
            assert result is not None
            files, size, chunks, collection = result
            assert files == 0
            assert size == 0
            assert chunks == 0
            assert isinstance(collection, str)


def test_investigate_workspace_with_files():
    """Test investigating workspace with actual files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test files
        (temp_path / 'main.py').write_text('def main(): pass\n\nif __name__ == "__main__":\n    main()')
        (temp_path / 'README.md').write_text('# Test Project\n\nDescription here.')
        (temp_path / 'package.json').write_text('{"name": "test"}')
        
        # Create ignored directory with file (should be skipped)
        node_modules = temp_path / 'node_modules'
        node_modules.mkdir()
        (node_modules / 'lib.js').write_text('library code')
        
        # Set WORKSPACE_PATH for config
        with patch.dict('os.environ', {'WORKSPACE_PATH': temp_dir}):
            output = []
            
            with patch('builtins.print', side_effect=lambda *args: output.append(' '.join(map(str, args)))):
                result = investigate_workspace(temp_dir)
            
            assert result is not None
            files, size, chunks, collection = result
            
            # Should find 3 files (.py, .md, .json) but ignore node_modules
            assert files == 3
            assert size > 0
            assert chunks > 0
            assert isinstance(collection, str)
            
            # Verify output mentions the correct files
            output_text = ' '.join(output)
            assert 'main.py' in output_text or '.py:' in output_text
            assert 'README.md' in output_text or '.md:' in output_text


def test_generate_collection_name_consistency():
    """Test that collection name generation is consistent."""
    path = '/Users/test/my-awesome-project'
    
    name1 = generate_collection_name(path)
    name2 = generate_collection_name(path)
    
    # Should be consistent 
    assert name1 == name2
    
    # Should be valid identifier
    assert name1.replace('_', '').replace('0', '').replace('1', '').replace('2', '').replace('3', '').replace('4', '').replace('5', '').replace('6', '').replace('7', '').replace('8', '').replace('9', '').isalpha()
    
    # Should contain project name and hash
    assert 'my_awesome_project' in name1
    assert '_' in name1  # Should have hash separator