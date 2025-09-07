# Semantic Search MCP

Add semantic code search to any AI agent (Claude Code, Cursor, etc.). Search your codebase with natural language instead of exact keywords.

## Prerequisites

**Install UV** (Python package manager):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Setup

**1. Clone and install:**
```bash
git clone <this-repo>
cd semantic-search-mcp
uv sync
./check.sh  # Verify everything works
```

**2. Add a project for searching:**
```bash
# Start the management tool
uv run manage.py

# In the tool, analyze your project first:
> investigate /path/to/your/project

# If the analysis looks good, add it:
> add /path/to/your/project

# Get the configuration for your AI agent:  
> json 1
```

**3. Add to your AI agent:**

Copy the JSON configuration from step 2 into your Claude Code (or other AI agent):

```bash
# The management tool gives you this command:
claude mcp add semantic-search --env WORKSPACE_PATH="/path/to/your/project" -- uv run --directory /path/to/semantic-search-mcp scripts/run_server.py
```

## Usage

Now search your code with natural language:

```bash
@semantic_search "user authentication logic"
@semantic_search "database connection setup"
@semantic_search "error handling patterns"
```

**Tips:**
- Use **descriptive phrases** not single words
- For exact matches (like "MyClass"), use Grep tool instead
- Each project gets its own search collection

## Multiple Projects

To search multiple codebases, add each with a different name:

```bash
claude mcp add semantic-search-main --env WORKSPACE_PATH="/path/to/main/project" -- uv run --directory /path/to/semantic-search-mcp scripts/run_server.py
claude mcp add semantic-search-lib --env WORKSPACE_PATH="/path/to/library" -- uv run --directory /path/to/semantic-search-mcp scripts/run_server.py
```

Creates: `@semantic_search_main` and `@semantic_search_lib`

## Management

**Workspace commands:**
- `investigate <path>` - Analyze project size before indexing
- `add <path>` - Index a project with progress tracking
- `json <nr>` - Get configuration for existing collection

**Collection commands:**  
- `info <nr>` - View collection details
- `delete <nr>` - Remove collection

**For large projects:** Always use `investigate` first to see estimated size and time.

## Technical Info

- **Requirements**: Python ≥3.12, UV package manager
- **Safe indexing**: 1MB file limit, text files only (no binaries)
- **Smart filtering**: Ignores node_modules, .venv, build artifacts
- **File types**: Programming languages, docs (.md, .txt, .csv), configs
- **Performance**: ChromaDB with cosine similarity, sentence-transformers

Built with UV, ChromaDB, Pydantic v2, and the official MCP SDK.

Ready for production! 🚀