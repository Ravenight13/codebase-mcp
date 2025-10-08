#!/usr/bin/env python3
"""MCP Server v3 - Fixed initialization sequence and error handling."""

from __future__ import annotations

import asyncio
import json
import sys
import traceback
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

import src.database as database
from src.database import init_db_connection
from src.mcp.mcp_logging import get_logger

# Import tool handlers
from src.mcp.tools import (
    create_task_tool,
    get_task_tool,
    index_repository_tool,
    list_tasks_tool,
    search_code_tool,
    update_task_tool,
)

logger = get_logger(__name__)

# Create MCP server
app = Server("codebase-mcp")

# Tool definitions at module level
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
                "repository_id": {
                    "type": "string",
                    "description": "Filter by repository UUID (optional)"
                },
                "file_type": {
                    "type": "string",
                    "description": "Filter by file extension without dot (e.g., 'py', 'js')"
                },
                "directory": {
                    "type": "string",
                    "description": "Filter by directory path (supports wildcards)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (1-50)",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50
                }
            },
            "required": ["query"]
        }
    ),
    Tool(
        name="index_repository",
        description="Index a code repository for semantic search",
        inputSchema={
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Absolute path to repository directory"
                },
                "force_reindex": {
                    "type": "boolean",
                    "description": "Force full re-index even if already indexed",
                    "default": False
                }
            },
            "required": ["repo_path"]
        }
    ),
    Tool(
        name="list_tasks",
        description="List development tasks with optional filters",
        inputSchema={
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter by task status",
                    "enum": ["need to be done", "in-progress", "complete"]
                },
                "branch": {
                    "type": "string",
                    "description": "Filter by git branch name"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results (1-100)",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100
                }
            }
        }
    ),
    Tool(
        name="get_task",
        description="Get task by ID",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {"type": "string"}
            },
            "required": ["task_id"]
        }
    ),
    Tool(
        name="create_task",
        description="Create a new development task",
        inputSchema={
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Task title (1-200 characters)",
                    "minLength": 1,
                    "maxLength": 200
                },
                "description": {
                    "type": "string",
                    "description": "Detailed task description"
                },
                "notes": {
                    "type": "string",
                    "description": "Additional notes or context"
                },
                "planning_references": {
                    "type": "array",
                    "description": "Relative file paths to planning documents",
                    "items": {"type": "string"},
                    "default": []
                }
            },
            "required": ["title"]
        }
    ),
    Tool(
        name="update_task",
        description="Update an existing development task",
        inputSchema={
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "UUID of the task to update"
                },
                "title": {
                    "type": "string",
                    "description": "New task title (1-200 characters)",
                    "minLength": 1,
                    "maxLength": 200
                },
                "description": {
                    "type": "string",
                    "description": "New task description"
                },
                "notes": {
                    "type": "string",
                    "description": "New notes or additional context"
                },
                "status": {
                    "type": "string",
                    "description": "New task status",
                    "enum": ["need to be done", "in-progress", "complete"]
                },
                "branch": {
                    "type": "string",
                    "description": "Git branch name to associate with task"
                },
                "commit": {
                    "type": "string",
                    "description": "Git commit hash (40-character SHA-1)",
                    "pattern": "^[0-9a-f]{40}$"
                }
            },
            "required": ["task_id"]
        }
    ),
]

HANDLERS = {
    "search_code": search_code_tool,
    "index_repository": index_repository_tool,
    "list_tasks": list_tasks_tool,
    "get_task": get_task_tool,
    "create_task": create_task_tool,
    "update_task": update_task_tool,
}


@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Return available tools."""
    logger.info(f"Listing {len(TOOLS)} tools")
    return TOOLS


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute a tool."""
    logger.info(f"Tool call: {name}", extra={"context": {"tool": name}})
    
    handler = HANDLERS.get(name)
    if not handler:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    try:
        if database.SessionLocal is None:
            raise RuntimeError("Database not initialized")
        
        async with database.SessionLocal() as session:
            try:
                result = await handler(db=session, **arguments)
                await session.commit()
                
                # Serialize result
                result_text = json.dumps(result, indent=2, default=str)
                logger.info(f"Tool success: {name}")
                return [TextContent(type="text", text=result_text)]
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Tool error: {name}", exc_info=True)
                error_msg = f"Error: {type(e).__name__}: {str(e)}"
                return [TextContent(type="text", text=error_msg)]
                
    except Exception as e:
        logger.error(f"Fatal tool error: {name}", exc_info=True)
        return [TextContent(type="text", text=f"Fatal error: {str(e)}")]


async def main() -> None:
    """Run MCP server."""
    logger.info("Starting MCP server v3")
    
    # Init database
    try:
        await init_db_connection()
        logger.info("Database OK")
    except Exception as e:
        logger.error("Database init failed", exc_info=True)
        print(f"FATAL: Database initialization failed: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Run server
    logger.info("Starting stdio transport")
    async with stdio_server() as (read_stream, write_stream):
        logger.info("Server ready")
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopped")
    except Exception as e:
        logger.error("Fatal error", exc_info=True)
        print(f"FATAL: {e}", file=sys.stderr)
        sys.exit(1)
