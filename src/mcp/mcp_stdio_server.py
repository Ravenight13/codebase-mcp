#!/usr/bin/env python3
"""MCP Server with stdio transport using official MCP SDK.

This is the CORRECT implementation using the official MCP Python SDK.
The previous stdio_server.py was a custom JSON-RPC implementation that
doesn't speak the actual MCP protocol.

Key Differences from stdio_server.py:
1. Uses official mcp.server.stdio for protocol compliance
2. Properly registers MCP tools with schemas
3. Handles MCP-specific methods (tools/list, tools/call)
4. Correct async session management

Constitutional Compliance:
- Principle III: Protocol Compliance - Uses official MCP SDK
- Principle V: Production Quality - Proper error handling
- Principle VIII: Type Safety - Full type hints
"""

from __future__ import annotations

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.database import get_db, init_db_connection
from src.mcp.mcp_logging import get_logger
from src.mcp.tools import (
    create_task_tool,
    get_task_tool,
    index_repository_tool,
    list_tasks_tool,
    search_code_tool,
    update_task_tool,
)

logger = get_logger(__name__)

# Create MCP server instance
app = Server("codebase-mcp")


# ==============================================================================
# Tool Registration
# ==============================================================================


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MCP tools.
    
    This is called by Claude Desktop to discover what tools are available.
    Each tool needs a name, description, and input schema.
    """
    return [
        Tool(
            name="search_code",
            description="Search codebase using semantic similarity",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search query"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="index_repository",
            description="Index a git repository for semantic search",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Absolute path to git repository"
                    }
                },
                "required": ["repo_path"]
            }
        ),
        Tool(
            name="list_tasks",
            description="List all tasks with optional filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed"],
                        "description": "Filter by task status"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of tasks to return",
                        "default": 50
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="get_task",
            description="Get details of a specific task by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "UUID of the task"
                    }
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="create_task",
            description="Create a new task",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Task title"
                    },
                    "description": {
                        "type": "string",
                        "description": "Detailed task description"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed"],
                        "description": "Initial task status",
                        "default": "pending"
                    }
                },
                "required": ["title"]
            }
        ),
        Tool(
            name="update_task",
            description="Update an existing task",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "UUID of the task to update"
                    },
                    "title": {
                        "type": "string",
                        "description": "New task title"
                    },
                    "description": {
                        "type": "string",
                        "description": "New task description"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pending", "in_progress", "completed"],
                        "description": "New task status"
                    }
                },
                "required": ["task_id"]
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute a tool by name with given arguments.
    
    This is called by Claude Desktop when it wants to use a tool.
    We route to the appropriate handler and return results.
    """
    logger.info(
        f"Tool call: {name}",
        extra={"context": {"tool": name, "arguments": arguments}}
    )
    
    # Map tool names to handlers
    tool_handlers = {
        "search_code": search_code_tool,
        "index_repository": index_repository_tool,
        "list_tasks": list_tasks_tool,
        "get_task": get_task_tool,
        "create_task": create_task_tool,
        "update_task": update_task_tool,
    }
    
    handler = tool_handlers.get(name)
    if not handler:
        error_msg = f"Unknown tool: {name}"
        logger.error(error_msg, extra={"context": {"tool": name}})
        return [TextContent(type="text", text=error_msg)]
    
    # Get database session using proper context manager
    try:
        async for db in get_db():
            try:
                # Call tool handler with database session
                result = await handler(db=db, **arguments)
                
                # Format result as MCP text content
                import json
                result_text = json.dumps(result, indent=2)
                
                logger.info(
                    f"Tool call successful: {name}",
                    extra={"context": {"tool": name}}
                )
                
                return [TextContent(type="text", text=result_text)]
                
            except Exception as e:
                logger.error(
                    f"Tool execution error: {name}",
                    exc_info=True,
                    extra={
                        "context": {
                            "tool": name,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        }
                    }
                )
                error_text = f"Error executing {name}: {str(e)}"
                return [TextContent(type="text", text=error_text)]
                
    except Exception as e:
        logger.error(
            "Database session error",
            exc_info=True,
            extra={"context": {"error": str(e)}}
        )
        error_text = f"Database error: {str(e)}"
        return [TextContent(type="text", text=error_text)]


# ==============================================================================
# Server Lifecycle
# ==============================================================================


async def main() -> None:
    """Run the MCP server with stdio transport."""
    logger.info("Starting MCP stdio server")
    
    # Initialize database connection pool
    try:
        await init_db_connection()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(
            "Failed to initialize database",
            exc_info=True,
            extra={"context": {"error": str(e)}}
        )
        raise
    
    # Run MCP server with stdio transport
    # This handles all the protocol complexity automatically
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(
            "Fatal error in MCP server",
            exc_info=True,
            extra={"context": {"error": str(e)}}
        )
        raise
