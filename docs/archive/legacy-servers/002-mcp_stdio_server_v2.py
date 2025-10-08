#!/usr/bin/env python3
"""MCP Server with stdio transport using official MCP SDK.

CORRECTED VERSION with:
- Better error handling
- Fixed database session management  
- Debug logging
- Simplified tool registration
"""

from __future__ import annotations

import asyncio
import json
import sys
import traceback
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from src.database import init_db_connection, SessionLocal
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
# Tool Registry
# ==============================================================================

TOOLS = [
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
                    "description": "Maximum number of results",
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
                    "description": "Maximum number of tasks",
                    "default": 50
                }
            }
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
                    "description": "Task description"
                },
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "completed"],
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
                    "description": "UUID of the task"
                },
                "title": {"type": "string"},
                "description": {"type": "string"},
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "completed"]
                }
            },
            "required": ["task_id"]
        }
    ),
]

TOOL_HANDLERS = {
    "search_code": search_code_tool,
    "index_repository": index_repository_tool,
    "list_tasks": list_tasks_tool,
    "get_task": get_task_tool,
    "create_task": create_task_tool,
    "update_task": update_task_tool,
}


# ==============================================================================
# MCP Protocol Handlers
# ==============================================================================


@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List all available tools."""
    logger.info(f"Listing {len(TOOLS)} tools")
    return TOOLS


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute a tool by name."""
    logger.info(f"Tool call: {name}", extra={"context": {"tool": name, "args": arguments}})
    
    # Get handler
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        error_msg = f"Unknown tool: {name}"
        logger.error(error_msg)
        return [TextContent(type="text", text=error_msg)]
    
    # Execute with database session
    try:
        # Create session directly from SessionLocal
        if SessionLocal is None:
            raise RuntimeError("Database not initialized")
        
        async with SessionLocal() as session:
            try:
                # Call handler
                result = await handler(db=session, **arguments)
                
                # Commit
                await session.commit()
                
                # Format result
                result_text = json.dumps(result, indent=2, default=str)
                
                logger.info(f"Tool success: {name}")
                return [TextContent(type="text", text=result_text)]
                
            except Exception as e:
                # Rollback on error
                await session.rollback()
                raise
                
    except Exception as e:
        error_msg = f"Error in {name}: {str(e)}"
        logger.error(
            f"Tool error: {name}",
            exc_info=True,
            extra={"context": {"error": str(e), "traceback": traceback.format_exc()}}
        )
        return [TextContent(type="text", text=error_msg)]


# ==============================================================================
# Server Lifecycle
# ==============================================================================


async def main() -> None:
    """Run the MCP server."""
    logger.info("Starting MCP stdio server")
    
    # Initialize database
    try:
        await init_db_connection()
        logger.info("Database initialized")
    except Exception as e:
        logger.error("Database init failed", exc_info=True)
        raise
    
    # Run server
    try:
        async with stdio_server() as (read_stream, write_stream):
            logger.info("Server running")
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options()
            )
    except Exception as e:
        logger.error("Server error", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception as e:
        logger.error("Fatal error", exc_info=True)
        sys.exit(1)
