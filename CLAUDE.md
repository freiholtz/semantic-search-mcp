# CLAUDE.md

This file provides guidance to AI agents when working with code in this repository.

## Overview

This is Semantic Search MCP - a modern Python-based semantic code search server built with 2025 best practices. It provides intelligent code discovery through ChromaDB with explicit workspace configuration.

## Architecture (2025)

### Core Design Philosophy
- **Explicit Configuration**: Each project specifies target workspace via `WORKSPACE_PATH`
- **Per-Project Control**: No global MCP configuration, every project manages its own
- **Cross-Project Support**: Multiple MCP servers with different names/paths
- **Predictable Namespacing**: Collection names always based on explicit workspace path
- **Zero Auto-Detection**: No guessing, no fallbacks, only explicit configuration

### Technology Stack
- **UV**: Lightning-fast Python package management (10-100x faster than pip)
- **Official MCP SDK**: Stable server implementation (replaces buggy FastMCP 0.4.1)
- **ChromaDB 2025**: Rust-core performance improvements for 4x speed boost
- **Modern Python**: Type checking with `ty`, formatting with `black`, linting with `ruff`

## Tool Usage Instructions

**Use @semantic_search for CONCEPTUAL queries about ideas, themes, patterns, processes, or flows. For exact string matches, specific names, or single words, use Grep tool instead.**

**How to use @semantic_search effectively:**
- **Transform single words** → `"Liriel"` becomes `@semantic_search "character Liriel personality role and background"` 
- **Add descriptive context** → `"authentication"` becomes `@semantic_search "user authentication flow and security patterns"`
- **Focus on concepts** → `"calendar"` becomes `@semantic_search "calendar system logic and calculations"`
- **Describe what you seek** → `@semantic_search "emotional reflection patterns in diary entries"`

**When to use Grep instead:**
- `Grep pattern="Liriel"` (when you need exact name references)
- `Grep pattern="def authenticate"` (specific function definitions)
- `Grep pattern="class.*User"` (exact implementation details)

## Development Commands

**IMPORTANT**: Always use `uv run` for all Python command execution instead of `python3` or `python`. This ensures proper virtual environment and dependency management.

### Setup
```bash
# Initialize development environment
uv sync

# Health check all components
uv run scripts/health_check.py

# Run the MCP server directly (for testing)
WORKSPACE_PATH=/path/to/test/project uv run scripts/run_server.py
```

### Quality Assurance
```bash
# Run all checks (recommended)
./check.sh

# Individual checks
uv run ty check                     # Type checking
uv run ruff check src/ scripts/ manage.py      # Linting
uv run scripts/health_check.py     # Component verification
```

**IMPORTANT**: Always run `./check.sh` before committing any changes to ensure code quality standards are maintained.

### MCP Server Configuration

**Per-Project Setup (Required Approach):**
```bash
# From your target project directory
claude mcp add semantic-search \
  --env WORKSPACE_PATH=/full/path/to/target/project \
  -- uv run --directory /full/path/to/semantic-search-mcp scripts/run_server.py
```

**Multi-Project Setup:**
```bash
# Main project search
claude mcp add semantic-search \
  --env WORKSPACE_PATH=/path/to/main/project \
  -- uv run --directory /path/to/semantic-search-mcp scripts/run_server.py

# Additional project search  
claude mcp add semantic-search-lib \
  --env WORKSPACE_PATH=/path/to/library/project \
  -- uv run --directory /path/to/semantic-search-mcp scripts/run_server.py
```

## Tool Behavior

### semantic_search Tool
**Parameter:**
- `query`: Natural language search query (REQUIRED)

**Environment Variable (Required in MCP Config):**
- `WORKSPACE_PATH`: Absolute path to project directory to index and search

**Smart Behaviors:**
1. **Explicit Targeting**: Uses `WORKSPACE_PATH` environment variable exclusively
2. **Collection Creation**: If collection doesn't exist, auto-indexes the specified workspace
3. **Modification Detection**: Compares file timestamps, re-indexes changed files only
4. **Intelligent Filtering**: Skips venv, node_modules, static/admin, cache directories
5. **Error Recovery**: Clear error messages if workspace path invalid or missing
6. **Performance**: Leverages ChromaDB's 2025 Rust optimizations

**Collection Naming:**
- Format: `{folder_name}_{path_hash}` 
- Example: `transcribe_0785aac9`, `my_app_a1b2c3d4`
- Path hash ensures uniqueness across different projects with same folder names

**File Extensions Indexed:**
`.py, .js, .ts, .jsx, .tsx, .java, .cpp, .h, .go, .rs, .md, .yml, .yaml, .toml, .json`

**Automatically Ignored:**
- Virtual environments: `venv/`, `.venv/`, `env/`
- Package managers: `node_modules/`, `__pycache__/`
- Build artifacts: `build/`, `dist/`, `target/`, `.next/`
- Static files: `staticfiles/`, `static/admin/`, `collectstatic/`
- Cache directories: `cache/`, `.cache/`, `.npm/`, `.yarn/`
- Version control: `.git/`, `.svn/`, `.hg/`
- IDE files: `.vscode/`, `.idea/`, `*.swp`

## Technical Implementation

### Explicit Workspace Configuration
- **Required Environment**: `WORKSPACE_PATH` must be set in MCP server configuration
- **Validation**: Server validates workspace path exists and is directory
- **Collection Generation**: Unique collection names from workspace path + hash
- **Error Handling**: Clear error messages for missing/invalid workspace configuration

### ChromaDB Integration
- **Persistent Storage**: Data stored in `./chroma_db/` relative to MCP server directory
- **Embedding Model**: `all-MiniLM-L6-v2` for optimal code semantics
- **Metadata Tracking**: File paths, modification times, language detection
- **Chunking Strategy**: Split on double newlines for semantic coherence

### Performance Optimizations
- **Lazy Loading**: Components initialized only when needed
- **Incremental Updates**: Only re-index modified files
- **Memory Efficiency**: No background processes consuming resources
- **Fast Startup**: UV's instant virtual environment management

## Configuration Examples

### Example 1: Web Application Project
```bash
cd ~/projects/my-web-app
claude mcp add semantic-search \
  --env WORKSPACE_PATH=/Users/username/projects/my-web-app \
  -- uv run --directory /Users/username/tools/semantic-search-mcp scripts/run_server.py

# Usage
@semantic_search "React components for user authentication"
@semantic_search "API endpoints and database queries"
```

### Example 2: Research Multiple Codebases
```bash
cd ~/research/project
claude mcp add semantic-search-frontend \
  --env WORKSPACE_PATH=/Users/username/company/frontend \
  -- uv run --directory /Users/username/tools/semantic-search-mcp scripts/run_server.py

claude mcp add semantic-search-backend \
  --env WORKSPACE_PATH=/Users/username/company/backend \
  -- uv run --directory /Users/username/tools/semantic-search-mcp scripts/run_server.py

# Usage
@semantic_search_frontend "user interface components"
@semantic_search_backend "business logic and data models"
```

## Critical Development Workflow

**⚠️ MCP Server Restart Required:**
You ONLY need to restart the MCP client when making changes that affect MCP tool definitions:
- Tool names, parameters, descriptions (`@server.list_tools()`)
- Tool input schemas or required parameters 
- Tool interface or instructions

**Internal logic changes DO NOT require restart:**
- Backend functionality, algorithms, exception handling
- File processing, indexing, search logic
- Configuration, imports, helper functions

**Workflow:**
1. **MCP Tool Interface Changes**: Restart MCP client session
2. **Internal Logic Changes**: Test immediately with MCP tools
3. When in doubt, internal changes rarely need restart

## Configuration Management

### Adding MCP Server
```bash
# Standard per-project setup
claude mcp add semantic-search \
  --env WORKSPACE_PATH=/absolute/path/to/target/project \
  -- uv run --directory /absolute/path/to/semantic-search-mcp scripts/run_server.py
```

### Removing MCP Server
```bash
# Remove from current project
claude mcp remove semantic-search

# List all configured servers
claude mcp list

# Get server details
claude mcp get semantic-search
```

### Data Management  
```bash
# Manage indexed collections
uv run manage.py

# Features: list, info <nr>, delete <nr>, exit
# Shows collection sizes, chunk counts, indexing duration
```

## Verification

All core functionality has been tested and proven:
- ✅ Explicit workspace configuration functional
- ✅ Per-project MCP server setup working
- ✅ ChromaDB indexing and search operational
- ✅ File modification detection working  
- ✅ Smart ignore patterns validated
- ✅ Collection management tools functional
- ✅ Error recovery with helpful messages
- ✅ Cross-project search capability verified

The system provides reliable semantic code search with predictable workspace targeting and robust error handling - ready for production use!