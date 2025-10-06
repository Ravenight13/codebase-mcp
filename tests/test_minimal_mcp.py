#!/usr/bin/env python3
"""Minimal MCP server to test tool registration."""

import asyncio
import json
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Create server
app = Server("test-mcp")

# Register a simple test tool
@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Return list of available tools."""
    print("DEBUG: handle_list_tools() was called!", file=sys.stderr)
    tools = [
        Tool(
            name="test_tool",
            description="A simple test tool",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "A test message"
                    }
                },
                "required": ["message"]
            }
        )
    ]
    print(f"DEBUG: Returning {len(tools)} tools", file=sys.stderr)
    return tools

@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool execution."""
    print(f"DEBUG: handle_call_tool({name}) was called!", file=sys.stderr)
    return [TextContent(
        type="text",
        text=f"Tool '{name}' executed with args: {json.dumps(arguments)}"
    )]

async def main():
    """Run the server."""
    print("Starting minimal test MCP server", file=sys.stderr)
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
