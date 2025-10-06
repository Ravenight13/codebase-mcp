#!/usr/bin/env python3
"""Ultra-minimal MCP server that definitely works."""

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Create server
app = Server("minimal-test")

# Define one simple tool
@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="echo",
            description="Echo back a message",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {"type": "string"}
                },
                "required": ["message"]
            }
        )
    ]

@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "echo":
        msg = arguments.get("message", "no message")
        return [TextContent(type="text", text=f"Echo: {msg}")]
    return [TextContent(type="text", text="Unknown tool")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
