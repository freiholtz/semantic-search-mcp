# 🔮 Semantic Search MCP

Add semantic code search to any AI agent (Claude Code, Cursor, etc.). Search your codebase with natural language instead of exact keywords.

**Why this exists:** Cursor IDE has excellent semantic code search that makes AI agents much more effective. Claude Code uses only traditional search (find/grep), missing contextual connections. This tool brings Cursor-like semantic search capabilities to Claude Code and other AI agents.

**🔒 Completely local** - No API keys, no data leaves your computer  
**⚡ No server required** - Pre-indexed collections, updates on-demand

## TLDR

1. Clone this repo  
2. Add a working directory path and get the MCP configuration
3. Add the MCP to your coding agent
4. Now you have semantic search. 🎉

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
```

**2. Add a project for searching:**
```bash
# Start the management tool
uv run manage.py

# Add your project (automatically analyzes first):
> add /path/to/your/project

# It will show you what files will be indexed and ask for confirmation.
# This is useful to verify the file count matches your expectations.

# Get the configuration for your AI agent:  
> json 1
```

**3. Add to your AI agent:**

**For Claude Code:**
```bash
# Use the command from the management tool:
claude mcp add semantic-search --env WORKSPACE_PATH="/path/to/your/project" -- uv run --directory /path/to/semantic-search-mcp scripts/run_server.py
```

**For other MCP clients:**
```json
{
  "mcpServers": {
    "semantic-search": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/semantic-search-mcp", "scripts/run_server.py"],
      "env": {
        "WORKSPACE_PATH": "/path/to/your/project"
      }
    }
  }
}
```

## Usage

Once installed, your AI agent will **automatically use** semantic search when you ask code questions:

```bash
# Just talk naturally to your agent:
"How does user authentication work in this codebase?"
"Show me the database connection logic"  
"Find error handling patterns in the code"
```

The agent learns from the MCP tool description to use semantic search for conceptual queries and Grep for exact matches. **No special commands needed** - just ask naturally!

**Manual override:** If you want to force the agent to use semantic search, you can mention it: *"Use semantic search to find..."*

## Multiple Projects

To search multiple codebases, add each with a different name:

```bash
claude mcp add semantic-search-main --env WORKSPACE_PATH="/path/to/main/project" -- uv run --directory /path/to/semantic-search-mcp scripts/run_server.py
claude mcp add semantic-search-lib --env WORKSPACE_PATH="/path/to/library" -- uv run --directory /path/to/semantic-search-mcp scripts/run_server.py
```

Creates: `@semantic_search_main` and `@semantic_search_lib`

## Management

**Workspace commands:**
- `add <path>` - Analyze and index project (shows preview, asks confirmation)
- `investigate <path>` - Analyze project without indexing (for planning)
- `json <nr>` - Get configuration for existing collection

**Collection commands:**  
- `info <nr>` - View collection details
- `delete <nr>` - Remove collection

## Technical Info

- **Requirements**: Python ≥3.12, UV package manager
- **Safe indexing**: 1MB file limit, text files only (no binaries)
- **Smart filtering**: Ignores node_modules, .venv, build artifacts
- **File types**: Programming languages, docs (.md, .txt, .csv), configs
- **Performance**: ChromaDB with cosine similarity, sentence-transformers

Built with UV, ChromaDB, Pydantic v2, and the official MCP SDK.

## Development

**Code quality checks:**
```bash
./check.sh  # Run all checks (type, format, lint, test)
```

Run this before submitting changes to ensure code quality standards.

## License

Free to use and modify for any purpose. If you find this useful, please credit David Freiholtz for the original implementation.

