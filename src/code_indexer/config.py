"""Configuration management with Pydantic v2."""

from pathlib import Path
from typing import Set, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class IndexingConfig(BaseModel):
    """Configuration for indexing behavior."""
    
    model_config = ConfigDict(
        frozen=True,
        validate_assignment=True,
        str_strip_whitespace=True
    )
    
    max_file_size: int = Field(
        default=1024 * 1024,  # 1MB
        gt=0,
        description="Maximum file size to index in bytes"
    )
    
    modification_check_interval: int = Field(
        default=300,  # 5 minutes
        ge=60,
        description="How often to check for file modifications in seconds"
    )
    
    allowed_extensions: Set[str] = Field(
        default_factory=lambda: {
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
        },
        description="File extensions to index"
    )
    
    ignore_patterns: Set[str] = Field(
        default_factory=lambda: {
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
        },
        description="Patterns to ignore during indexing"
    )
    
    @field_validator('allowed_extensions')
    @classmethod
    def validate_extensions(cls, v: Set[str]) -> Set[str]:
        """Ensure all extensions start with a dot."""
        validated = set()
        for ext in v:
            if not ext.startswith('.'):
                ext = f'.{ext}'
            validated.add(ext.lower())
        return validated


class ChromaDBConfig(BaseModel):
    """Configuration for ChromaDB connection."""
    
    model_config = ConfigDict(
        frozen=True,
        validate_assignment=True
    )
    
    database_path: Path = Field(
        default=Path("./chroma_db"),
        description="Path to ChromaDB storage directory"
    )
    
    anonymized_telemetry: bool = Field(
        default=False,
        description="Whether to enable ChromaDB telemetry"
    )
    
    similarity_metric: str = Field(
        default="cosine",
        description="Similarity metric for vector search"
    )
    
    @field_validator('database_path')
    @classmethod
    def ensure_path_exists(cls, v: Path) -> Path:
        """Ensure database directory exists."""
        v.mkdir(parents=True, exist_ok=True)
        return v


class SemanticSearchConfig(BaseSettings):
    """Main configuration for semantic search MCP server."""
    
    model_config = SettingsConfigDict(
        case_sensitive=False,
        validate_assignment=True
    )
    
    workspace_path: str = Field(
        description="Absolute path to workspace directory to index"
    )
    
    indexing: IndexingConfig = Field(
        default_factory=IndexingConfig,
        description="Indexing behavior configuration"
    )
    
    chromadb: ChromaDBConfig = Field(
        default_factory=ChromaDBConfig,
        description="ChromaDB connection configuration"
    )
    
    @field_validator('workspace_path')
    @classmethod
    def validate_workspace_path(cls, v: str) -> str:
        """Validate workspace path exists and is directory."""
        if not v:
            raise ValueError("Workspace path is required")
        
        path = Path(v)
        if not path.exists():
            raise ValueError(f"Workspace directory does not exist: {v}")
        
        if not path.is_dir():
            raise ValueError(f"Workspace path is not a directory: {v}")
        
        return str(path.absolute())


# Global configuration instance
config: Optional[SemanticSearchConfig] = None


def get_config() -> SemanticSearchConfig:
    """Get or create global configuration instance."""
    global config
    if config is None:
        import os
        workspace_path = os.environ.get('WORKSPACE_PATH')
        if not workspace_path:
            raise ValueError("WORKSPACE_PATH environment variable is required")
        
        config = SemanticSearchConfig(workspace_path=workspace_path)
    
    return config


# Default configuration instances for standalone use
def get_default_indexing_config() -> IndexingConfig:
    """Get default indexing configuration without requiring WORKSPACE_PATH."""
    return IndexingConfig()


def get_default_chromadb_config() -> ChromaDBConfig:
    """Get default ChromaDB configuration without requiring WORKSPACE_PATH."""
    return ChromaDBConfig()


def get_allowed_extensions() -> Set[str]:
    """Get allowed file extensions from config, or defaults if WORKSPACE_PATH not available."""
    try:
        return get_config().indexing.allowed_extensions
    except ValueError:
        # WORKSPACE_PATH not set, use defaults for management tool
        return get_default_indexing_config().allowed_extensions


def get_ignore_patterns() -> Set[str]:
    """Get ignore patterns from config, or defaults if WORKSPACE_PATH not available."""
    try:
        return get_config().indexing.ignore_patterns
    except ValueError:
        # WORKSPACE_PATH not set, use defaults for management tool
        return get_default_indexing_config().ignore_patterns


def get_max_file_size() -> int:
    """Get maximum file size from config, or defaults if WORKSPACE_PATH not available."""
    try:
        return get_config().indexing.max_file_size
    except ValueError:
        # WORKSPACE_PATH not set, use defaults for management tool
        return get_default_indexing_config().max_file_size


def get_modification_check_interval() -> int:
    """Get modification check interval from config."""
    return get_config().indexing.modification_check_interval


def get_chromadb_config() -> ChromaDBConfig:
    """Get ChromaDB configuration from config, or defaults if WORKSPACE_PATH not available.""" 
    try:
        return get_config().chromadb
    except ValueError:
        # WORKSPACE_PATH not set, use defaults for management tool
        return get_default_chromadb_config()