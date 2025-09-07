"""Shared utilities for semantic search operations."""

import hashlib
import time
from pathlib import Path
from typing import Set, Tuple, Dict, Any, Optional


# Constants
MAX_FILE_SIZE = 1024 * 1024  # 1MB
MODIFICATION_CHECK_INTERVAL = 300  # 5 minutes in seconds


def get_allowed_extensions() -> Set[str]:
    """Get the allowlist of safe file extensions to index."""
    return {
        # Programming languages
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp', 
        '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.cs', '.fs',
        '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd',
        # Web technologies  
        '.html', '.htm', '.css', '.scss', '.sass', '.less',
        # Data formats
        '.json', '.yaml', '.yml', '.toml', '.xml', '.csv', '.tsv',
        # Documentation
        '.md', '.rst', '.txt', '.adoc',
        # Configuration
        '.ini', '.conf', '.cfg', '.env.example', '.gitignore', '.editorconfig'
    }


def get_ignore_patterns() -> Set[str]:
    """Get comprehensive ignore patterns for directories and files."""
    return {
        # Virtual environments
        'venv', '.venv', 'env', '.env', 'virtualenv',
        # Package managers
        'node_modules', '__pycache__', '.pytest_cache',
        # Version control
        '.git', '.svn', '.hg',
        # Build artifacts  
        'build', 'dist', 'target', '.next', '.nuxt',
        # IDE/editor files
        '.vscode', '.idea', '*.swp', '*.swo',
        # Cache directories
        'cache', '.cache', '.npm', '.yarn',
        # Static files (Django)
        'staticfiles', 'static/admin', 'collectstatic',
        # Logs
        '*.log', 'logs',
        # Temporary files
        'tmp', 'temp', '.tmp'
    }


def should_ignore_path(file_path: Path, ignore_patterns: Set[str]) -> bool:
    """Check if file path should be ignored based on patterns."""
    if not isinstance(file_path, Path):
        file_path = Path(file_path)
    
    path_parts = file_path.parts
    path_str = str(file_path).lower()
    
    for pattern in ignore_patterns:
        if pattern.startswith('*'):
            # Wildcard pattern
            if path_str.endswith(pattern[1:]):
                return True
        else:
            # Check if pattern matches any directory component exactly
            if pattern in path_parts or file_path.name == pattern:
                return True
            # Also check for exact directory matches like 'static/admin'
            if '/' in pattern and pattern in path_str:
                return True
                
    return False


def generate_collection_name(workspace_path: str) -> str:
    """Generate unique collection name from workspace path."""
    workspace_dir = Path(workspace_path)
    folder_name = workspace_dir.name.lower().replace('-', '_').replace(' ', '_')
    clean_name = ''.join(c for c in folder_name if c.isalnum() or c == '_')
    
    # Generate short hash of full workspace path  
    path_hash = hashlib.sha256(str(workspace_dir.absolute()).encode()).hexdigest()[:8]
    return f"{clean_name}_{path_hash}"


def is_file_indexable(file_path: Path, allowed_extensions: Set[str], ignore_patterns: Set[str]) -> Tuple[bool, str]:
    """Check if file should be indexed and return reason if not.
    
    Returns:
        (is_indexable, reason_if_not)
    """
    if not file_path.is_file():
        return False, "not a file"
    
    if file_path.suffix.lower() not in allowed_extensions:
        return False, f"extension {file_path.suffix} not in allowlist"
    
    if should_ignore_path(file_path, ignore_patterns):
        return False, "path matches ignore pattern"
    
    try:
        file_size = file_path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            return False, f"file too large ({file_size/1024/1024:.1f}MB > 1MB)"
    except Exception as e:
        return False, f"stat error: {e}"
    
    return True, ""


def create_chunk_metadata(file_path: Path, workspace_dir: Path, chunk_index: int) -> Dict[str, Any]:
    """Create metadata for a chunk."""
    current_time = time.time()
    return {
        "file_path": str(file_path.relative_to(workspace_dir)),
        "collection_root": str(workspace_dir),
        "last_modified": current_time,
        "chunk_index": chunk_index
    }


def generate_chunk_id(file_path: Path, chunk_index: int, timestamp: Optional[float] = None) -> str:
    """Generate unique chunk ID."""
    if timestamp is None:
        timestamp = time.time()
    return f"{file_path.name}_{chunk_index}_{int(timestamp)}"