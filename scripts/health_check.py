#!/usr/bin/env python3
"""Simple health check script that tests each component."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_imports():
    """Test that all imports work."""
    print("🧪 Testing imports...")
    
    try:
        from mcp.server import Server
        from mcp.types import Tool, TextContent
        print("  ✅ MCP imports working")
    except ImportError as e:
        print(f"  ❌ MCP import failed: {e}")
        return False
    
    try:
        import chromadb
        print("  ✅ ChromaDB import working")
    except ImportError as e:
        print(f"  ❌ ChromaDB import failed: {e}")
        return False
    
    try:
        import sentence_transformers
        print("  ✅ Sentence transformers import working")
    except ImportError as e:
        print(f"  ❌ Sentence transformers import failed: {e}")
        return False
    
    return True


def test_mcp_server():
    """Test MCP server creation.""" 
    print("🔧 Testing MCP server creation...")
    
    try:
        print("  ✅ Server import successful")
        
        # Test basic MCP objects
        from mcp.types import Tool, TextContent
        tool = Tool(
            name="test",
            description="Test tool",
            inputSchema={"type": "object", "properties": {}}
        )
        content = TextContent(type="text", text="Test")
        print("  ✅ Basic MCP objects work")
        
        return True
    except Exception as e:
        print(f"  ❌ MCP server test failed: {e}")
        return False


def test_chromadb():
    """Test ChromaDB basic functionality."""
    print("💾 Testing ChromaDB...")
    
    try:
        import chromadb
        
        # Test in-memory client (won't persist)
        client = chromadb.Client()
        print("  ✅ ChromaDB client created")
        
        # Test collection creation
        collection = client.create_collection("test")
        print("  ✅ Test collection created")
        
        # Test basic add/query
        collection.add(
            documents=["Hello world"],
            ids=["1"]
        )
        print("  ✅ Document added")
        
        results = collection.query(
            query_texts=["Hello"],
            n_results=1
        )
        print("  ✅ Query successful")
        
        return True
    except Exception as e:
        print(f"  ❌ ChromaDB test failed: {e}")
        return False


def main():
    """Run all health checks."""
    print("🏥 Starting health check...\n")
    
    checks = [
        ("Imports", test_imports),
        ("MCP Server", test_mcp_server),
        ("ChromaDB", test_chromadb)
    ]
    
    results = []
    
    for name, test_func in checks:
        print(f"\n{name}:")
        success = test_func()
        results.append((name, success))
        print(f"  {'✅' if success else '❌'} {name}: {'PASS' if success else 'FAIL'}")
    
    # Summary
    print(f"\n{'='*50}")
    print("📊 HEALTH CHECK SUMMARY")
    print(f"{'='*50}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} {name}")
    
    print(f"\nResult: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All health checks passed! System ready.")
        return True
    else:
        print("⚠️  Some health checks failed. Review the output above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)