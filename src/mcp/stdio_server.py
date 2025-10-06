#!/usr/bin/env python3
"""
===============================================================================
⚠️  DEPRECATED - DO NOT USE THIS FILE ⚠️
===============================================================================

This file is kept for reference only. It was an attempt to build a custom
JSON-RPC server, but it does NOT speak the MCP protocol correctly.

✅ USE INSTEAD: src/mcp/mcp_stdio_server.py

WHY THIS FAILS:
1. Protocol Mismatch - Claude Desktop expects MCP protocol (initialize, 
   tools/list, tools/call), but this only handles raw method names
2. No Tool Discovery - Claude can't see what tools are available
3. Broken DB Sessions - Misuses async generators, sessions leak
4. Missing Features - No parameter validation, error handling, etc.

READ THESE DOCS:
- EXECUTIVE_SUMMARY.md - Quick overview of the fix
- MCP_STDIO_FIX.md - Detailed troubleshooting guide  
- WRONG_VS_RIGHT.md - Side-by-side comparison of mistakes

===============================================================================

ORIGINAL DOCSTRING (for reference):

MCP Server with stdio transport (JSON-RPC over stdin/stdout).

This module provides stdio transport for the MCP server, allowing CLI and
command-line clients to interact via JSON-RPC 2.0 over stdin/stdout.

Constitutional Compliance:
- Principle III: Protocol Compliance - JSON-RPC via stdio, file logging only
- Principle V: Production Quality - Error handling, validation
- Principle VIII: Type Safety - Full mypy --strict compliance

Architecture:
- Reads JSON-RPC 2.0 requests from stdin line-by-line
- Routes to appropriate tool handlers (reuses existing MCP tools)
- Writes JSON-RPC 2.0 responses to stdout
- All logs go to file only (no stdout/stderr pollution)

Performance:
- Uses async/await for concurrent operations
- Database session pooling for efficient resource usage
- Proper cleanup on shutdown
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

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

# ==============================================================================
# Constants
# ==============================================================================

logger = get_logger(__name__)

# JSON-RPC 2.0 error codes (official specification)
PARSE_ERROR: int = -32700
INVALID_REQUEST: int = -32600
METHOD_NOT_FOUND: int = -32601
INVALID_PARAMS: int = -32602
INTERNAL_ERROR: int = -32603

# Tool registry mapping method names to handlers
# All handlers must accept **params and db: AsyncSession
TOOL_REGISTRY: dict[str, Any] = {
    "search_code": search_code_tool,
    "index_repository": index_repository_tool,
    "get_task": get_task_tool,
    "list_tasks": list_tasks_tool,
    "create_task": create_task_tool,
    "update_task": update_task_tool,
}


# ==============================================================================
# Request Handling
# ==============================================================================


async def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    """Handle a single JSON-RPC request.

    Validates JSON-RPC format, routes to tool handler, and returns response.

    Args:
        request: JSON-RPC request object with jsonrpc, method, params, id fields

    Returns:
        JSON-RPC response object with jsonrpc, id, result or error fields

    JSON-RPC 2.0 Request Format:
        {
            "jsonrpc": "2.0",
            "method": "search_code",
            "params": {"query": "async def", "limit": 10},
            "id": 1
        }

    JSON-RPC 2.0 Response Format (Success):
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {...}
        }

    JSON-RPC 2.0 Response Format (Error):
        {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32601,
                "message": "Method not found"
            }
        }
    """
    request_id = request.get("id")

    # Validate JSON-RPC version
    if request.get("jsonrpc") != "2.0":
        logger.warning(
            "Invalid JSON-RPC version",
            extra={"context": {"request": request, "request_id": request_id}},
        )
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": INVALID_REQUEST,
                "message": "JSON-RPC version must be 2.0",
            },
        }

    # Get method name
    method = request.get("method")
    if not method:
        logger.warning(
            "Missing method in request",
            extra={"context": {"request": request, "request_id": request_id}},
        )
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": INVALID_REQUEST, "message": "Missing method field"},
        }

    # Get tool handler
    tool_handler = TOOL_REGISTRY.get(method)
    if not tool_handler:
        logger.warning(
            f"Method not found: {method}",
            extra={"context": {"method": method, "request_id": request_id}},
        )
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": METHOD_NOT_FOUND,
                "message": f"Method '{method}' not found",
            },
        }

    # Get parameters
    params = request.get("params", {})

    # Log tool call
    logger.info(
        f"Calling tool: {method}",
        extra={
            "context": {
                "method": method,
                "params": params,
                "request_id": request_id,
            }
        },
    )

    # Call tool handler with database session
    # We need to manually manage the database session since we're not in FastAPI
    try:
        # Get database session from dependency generator
        db_generator = get_db()
        db_session = await db_generator.__anext__()

        try:
            # Call tool handler with params and db session
            result = await tool_handler(db=db_session, **params)

            # Log success
            logger.info(
                f"Tool call successful: {method}",
                extra={
                    "context": {
                        "method": method,
                        "request_id": request_id,
                    }
                },
            )

            # Close the generator properly
            try:
                await db_generator.__anext__()
            except StopAsyncIteration:
                pass

            # Return success response
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result,
            }

        except Exception as e:
            # Close the generator on error
            try:
                await db_generator.__anext__()
            except StopAsyncIteration:
                pass
            # Let outer exception handler catch this
            raise

    except TypeError as e:
        # Invalid parameters (missing required params or wrong types)
        logger.error(
            f"Invalid parameters for {method}",
            exc_info=True,
            extra={
                "context": {
                    "method": method,
                    "params": params,
                    "error": str(e),
                    "request_id": request_id,
                }
            },
        )
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": INVALID_PARAMS,
                "message": f"Invalid parameters: {str(e)}",
            },
        }

    except Exception as e:
        # Internal error (tool handler raised exception)
        logger.error(
            f"Internal error in {method}",
            exc_info=True,
            extra={
                "context": {
                    "method": method,
                    "params": params,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "request_id": request_id,
                }
            },
        )
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": INTERNAL_ERROR,
                "message": "Internal server error",
            },
        }


# ==============================================================================
# Server Main Loop
# ==============================================================================


async def run_stdio_server() -> None:
    """Run MCP server with stdio transport.

    Reads JSON-RPC requests from stdin, processes them, and writes
    responses to stdout. All logging goes to files only.

    Lifecycle:
        1. Initialize database connection pool
        2. Read JSON-RPC requests from stdin (line-by-line)
        3. Parse and validate each request
        4. Route to appropriate tool handler
        5. Write JSON-RPC response to stdout
        6. Repeat until EOF or shutdown signal

    Error Handling:
        - Parse errors: Returns JSON-RPC parse error response
        - Validation errors: Returns JSON-RPC invalid request/params error
        - Tool errors: Returns JSON-RPC internal error response
        - System errors: Logs and exits gracefully

    Performance:
        - Async operations for I/O efficiency
        - Database connection pooling
        - Minimal latency (no buffering on stdout)
    """
    logger.info("Starting MCP server with stdio transport")

    # Initialize database connection pool
    try:
        await init_db_connection()
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error(
            "Failed to initialize database connection",
            exc_info=True,
            extra={"context": {"error": str(e)}},
        )
        # Write error to stdout (JSON-RPC error response)
        error_response = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": INTERNAL_ERROR,
                "message": "Failed to initialize database connection",
            },
        }
        print(json.dumps(error_response), flush=True)
        return

    try:
        # Read from stdin line by line
        while True:
            # Read line from stdin (blocking call, run in executor for async)
            loop = asyncio.get_event_loop()
            line = await loop.run_in_executor(None, sys.stdin.readline)

            # EOF - exit gracefully
            if not line:
                logger.info("EOF received, shutting down")
                break

            # Skip empty lines
            line = line.strip()
            if not line:
                continue

            # Parse JSON-RPC request
            try:
                request = json.loads(line)
            except json.JSONDecodeError as e:
                logger.error(
                    "JSON parse error",
                    exc_info=True,
                    extra={"context": {"line": line, "error": str(e)}},
                )
                response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": PARSE_ERROR,
                        "message": f"Parse error: {str(e)}",
                    },
                }
                # Write error response to stdout
                print(json.dumps(response), flush=True)
                continue

            # Handle request
            response = await handle_request(request)

            # Write response to stdout (JSON-RPC protocol)
            # flush=True ensures immediate write (no buffering)
            print(json.dumps(response), flush=True)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down")
    except Exception as e:
        logger.error(
            "Unexpected error in stdio server",
            exc_info=True,
            extra={"context": {"error": str(e), "error_type": type(e).__name__}},
        )
        raise
    finally:
        logger.info("MCP stdio server stopped")


# ==============================================================================
# Entry Point
# ==============================================================================


def main() -> None:
    """Entry point for stdio server.

    Can be invoked via:
        - python -m src.mcp.stdio_server
        - ./src/mcp/stdio_server.py (if executable)

    Usage:
        # Interactive mode (type JSON-RPC requests):
        python -m src.mcp.stdio_server

        # Pipe input from file:
        cat requests.jsonl | python -m src.mcp.stdio_server

        # Echo single request:
        echo '{"jsonrpc":"2.0","id":1,"method":"get_task","params":{"task_id":"..."}}' | python -m src.mcp.stdio_server

    Note:
        - Expects JSON-RPC requests on stdin (one per line)
        - Writes JSON-RPC responses to stdout (one per line)
        - All logs go to /tmp/codebase-mcp.log
    """
    try:
        # Run async server
        asyncio.run(run_stdio_server())
    except KeyboardInterrupt:
        # Graceful shutdown on Ctrl+C
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        # Log unexpected errors
        logger.error(
            "Fatal error in stdio server",
            exc_info=True,
            extra={"context": {"error": str(e), "error_type": type(e).__name__}},
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
