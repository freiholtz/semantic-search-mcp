"""Test configuration management functions."""

import pytest
import os
from pathlib import Path
import tempfile
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from code_indexer.config import get_allowed_extensions, get_ignore_patterns, get_max_file_size


def test_get_allowed_extensions():
    """Test that allowed extensions are returned correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with pytest.MonkeyPatch().context() as m:
            m.setenv('WORKSPACE_PATH', temp_dir)
            extensions = get_allowed_extensions()
    
    assert isinstance(extensions, set)
    assert '.py' in extensions
    assert '.js' in extensions  
    assert '.md' in extensions
    assert '.txt' in extensions
    assert '.csv' in extensions
    
    # Should not have binary extensions
    assert '.exe' not in extensions
    assert '.zip' not in extensions
    assert '.jpg' not in extensions


def test_get_ignore_patterns():
    """Test that ignore patterns are returned correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with pytest.MonkeyPatch().context() as m:
            m.setenv('WORKSPACE_PATH', temp_dir)
            patterns = get_ignore_patterns()
    
    assert isinstance(patterns, set)
    assert '.venv' in patterns
    assert 'node_modules' in patterns
    assert '.git' in patterns
    assert '__pycache__' in patterns


def test_get_max_file_size():
    """Test that max file size is reasonable."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with pytest.MonkeyPatch().context() as m:
            m.setenv('WORKSPACE_PATH', temp_dir)
            max_size = get_max_file_size()
    
    assert isinstance(max_size, int)
    assert max_size == 1024 * 1024  # 1MB
    assert max_size > 0


def test_config_with_workspace_path():
    """Test configuration with valid workspace path."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set environment variable
        os.environ['WORKSPACE_PATH'] = temp_dir
        
        # Test that config functions work
        extensions = get_allowed_extensions()
        patterns = get_ignore_patterns()
        max_size = get_max_file_size()
        
        assert isinstance(extensions, set)
        assert isinstance(patterns, set)
        assert isinstance(max_size, int)
        
        # Clean up
        if 'WORKSPACE_PATH' in os.environ:
            del os.environ['WORKSPACE_PATH']