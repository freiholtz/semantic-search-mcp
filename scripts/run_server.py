#!/usr/bin/env python3
"""Run the MCP server for AI agent connection."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import and run the server
if __name__ == "__main__":
    from code_indexer.server import main
    import asyncio
    
    print("🚀 Starting MCP server for AI agents...")
    print("💡 Server ready for AI agent connection")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1)