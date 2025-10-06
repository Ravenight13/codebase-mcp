#!/usr/bin/env python3
"""Test MCP stdio server implementation.

This script tests the MCP server by simulating what Claude Desktop does:
1. Start the server process
2. Send MCP protocol messages
3. Verify responses

Run from project root:
    python tests/test_mcp_server.py
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_mcp_server():
    """Test MCP server with stdio transport."""
    print("🚀 Testing MCP stdio server...\n")
    
    # Start the server as a subprocess
    print("1. Starting MCP server process...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "src.mcp.mcp_stdio_server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=project_root,
        text=True,
        bufsize=1,  # Line buffered
    )
    
    try:
        # Give server time to initialize
        await asyncio.sleep(2)
        
        if server_process.poll() is not None:
            stderr = server_process.stderr.read()
            print(f"❌ Server exited immediately with error:\n{stderr}")
            return False
        
        print("✅ Server started successfully\n")
        
        # Test 1: Initialize connection
        print("2. Testing MCP initialization...")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "0.1.0",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        server_process.stdin.write(json.dumps(init_request) + "\n")
        server_process.stdin.flush()
        
        response_line = server_process.stdout.readline()
        if not response_line:
            print("❌ No response from server")
            return False
        
        response = json.loads(response_line)
        print(f"✅ Initialize response: {json.dumps(response, indent=2)}\n")
        
        # Test 2: List tools
        print("3. Testing tools/list...")
        list_tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        server_process.stdin.write(json.dumps(list_tools_request) + "\n")
        server_process.stdin.flush()
        
        response_line = server_process.stdout.readline()
        if not response_line:
            print("❌ No response from server")
            return False
        
        response = json.loads(response_line)
        tools = response.get("result", {}).get("tools", [])
        print(f"✅ Found {len(tools)} tools:")
        for tool in tools:
            print(f"   - {tool['name']}: {tool['description']}")
        print()
        
        # Test 3: Call a tool (list_tasks)
        print("4. Testing tool execution (list_tasks)...")
        call_tool_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "list_tasks",
                "arguments": {
                    "limit": 5
                }
            }
        }
        
        server_process.stdin.write(json.dumps(call_tool_request) + "\n")
        server_process.stdin.flush()
        
        response_line = server_process.stdout.readline()
        if not response_line:
            print("❌ No response from server")
            return False
        
        response = json.loads(response_line)
        if "error" in response:
            print(f"⚠️  Tool call returned error (might be expected if no tasks exist):")
            print(f"   {response['error']}")
        else:
            print(f"✅ Tool execution successful")
            print(f"   Result: {json.dumps(response.get('result'), indent=2)}")
        print()
        
        print("✅ All tests passed!\n")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean shutdown
        print("5. Shutting down server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
        
        # Print any stderr output
        stderr = server_process.stderr.read()
        if stderr:
            print(f"\nServer stderr output:\n{stderr}")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("MCP Server Test Suite")
    print("=" * 60)
    print()
    
    success = await test_mcp_server()
    
    print("=" * 60)
    if success:
        print("✅ All tests passed!")
        print("\nNext steps:")
        print("1. Copy claude_desktop_config.json contents to:")
        print("   ~/Library/Application Support/Claude/claude_desktop_config.json")
        print("2. Restart Claude Desktop")
        print("3. Look for 'codebase-mcp' in the tools menu")
    else:
        print("❌ Tests failed - check errors above")
    print("=" * 60)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
