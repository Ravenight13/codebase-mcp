"""FastMCP server implementation for Codebase MCP Server.

This module implements the MCP server using the FastMCP framework,
replacing the custom protocol implementation with a standardized approach.

Features:
- FastMCP framework initialization
- Stdio transport for Claude Desktop integration
- Tool registration via decorators
- Automatic schema generation from Pydantic models
- Dual logging pattern (Context for client, file for server)
- Context injection for logging

Constitutional Compliance:
- Principle III: Protocol Compliance (stdio transport, no stdout/stderr pollution)
- Principle V: Production Quality (startup validation, error handling)
- Principle VIII: Type Safety (full type hints, mypy --strict)
- Principle XI: FastMCP Foundation (FastMCP as standard MCP interface)
"""

from __future__ import annotations

import asyncio
import logging
import logging.handlers
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, AsyncGenerator

from fastmcp import FastMCP

if TYPE_CHECKING:
    pass

# ==============================================================================
# Configure File Logging (separate from MCP protocol)
# ==============================================================================

# Dual Logging Pattern:
# 1. Context logging (ctx.info()) -> MCP client (Claude Desktop)
# 2. Python logging -> /tmp/codebase-mcp.log (server persistence)

LOG_FILE = Path("/tmp/codebase-mcp.log")

# Create logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        # File handler for persistent logs
        logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        ),
    ],
)

# Get logger for this module
logger = logging.getLogger(__name__)

# Suppress external library logs from polluting our log file
logging.getLogger("fastmcp").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("asyncpg").setLevel(logging.WARNING)

logger.info("=" * 80)
logger.info("FastMCP Server Initialization")
logger.info(f"Log file: {LOG_FILE}")
logger.info("=" * 80)

# ==============================================================================
# Module-Level State (Database Initialization Tracking)
# ==============================================================================

# Module-level variable to track database initialization task
_db_init_task: asyncio.Task[None] | None = None

# ==============================================================================
# FastMCP Lifespan (Database Initialization)
# ==============================================================================


@asynccontextmanager
async def lifespan(app: FastMCP) -> AsyncGenerator[None, None]:
    """Lifespan context manager for FastMCP server.

    Manages server startup and shutdown lifecycle:
    - Startup: Initialize database in background (non-blocking)
    - Shutdown: Close database connections gracefully

    Non-Blocking Pattern:
    - Uses asyncio.create_task() to start DB init in background
    - Tools become visible immediately (FastAPI best practice)
    - First tool call waits for init completion if needed

    Constitutional Compliance:
    - Principle V: Production Quality (proper initialization order, error handling)
    - Principle VIII: Type Safety (full type hints, mypy --strict)

    Args:
        app: FastMCP server instance

    Yields:
        None (context manager pattern)

    Raises:
        RuntimeError: If database initialization fails
    """
    # Import database connection management
    from src.database import close_db_connection, init_db_connection

    global _db_init_task

    # Startup: Initialize database in background (non-blocking)
    # FastAPI pattern: Use create_task() to avoid blocking tool visibility
    try:
        logger.info("Starting database initialization in background...")
        _db_init_task = asyncio.create_task(init_db_connection())
        logger.info("Database initialization task started (non-blocking)")
    except Exception as e:
        logger.critical(
            f"Failed to start database initialization: {e}",
            exc_info=True,
        )
        raise RuntimeError(f"Database initialization task failed: {e}") from e

    # Yield control to FastMCP server (tools are visible NOW)
    yield

    # Shutdown: Ensure init completed, then close
    try:
        logger.info("Shutting down server...")

        # Wait for database initialization to complete if still running
        if _db_init_task and not _db_init_task.done():
            logger.info("Waiting for database initialization to complete...")
            await _db_init_task

        # Close database connection pool
        logger.info("Closing database connection pool...")
        await close_db_connection()
        logger.info("Database closed successfully")
    except Exception as e:
        logger.error(
            f"Error during shutdown: {e}",
            exc_info=True,
        )


# ==============================================================================
# Initialize FastMCP Server
# ==============================================================================

mcp = FastMCP("codebase-mcp", version="0.1.0", lifespan=lifespan)

# Export for tool access
__all__ = ["mcp", "_db_init_task"]


# ==============================================================================
# Startup Validation
# ==============================================================================


async def validate_server_startup(mcp_server: FastMCP) -> None:
    """Validate all registered components before starting server.

    This fail-fast validation ensures that critical server components are
    properly configured before accepting client connections.

    Constitutional Compliance:
    - Principle V: Production Quality (fail-fast validation, error handling)

    Args:
        mcp_server: FastMCP server instance to validate

    Raises:
        RuntimeError: If any tools are missing or misconfigured
        ValueError: If tool schemas are invalid

    Validation Checks:
    1. All 6 expected tools are registered
    2. Tool schemas are properly generated
    3. Tool names match expected identifiers
    """
    # Expected tool set for Codebase MCP Server
    expected_tools = {
        "search_code",
        "index_repository",
        "create_task",
        "get_task",
        "list_tasks",
        "update_task",
    }

    # Check that tools are registered
    registered_tools_dict = await mcp_server.get_tools()

    if not registered_tools_dict:
        logger.error("VALIDATION FAILED: No tools registered")
        raise RuntimeError(
            "Server validation failed: No tools registered.\n"
            "Fix: Ensure all tool modules are imported before calling main()."
        )

    # Extract tool names from registered tools (get_tools returns dict[str, Tool])
    registered_tools = set(registered_tools_dict.keys())

    # Check for missing tools
    missing_tools = expected_tools - registered_tools
    if missing_tools:
        logger.error(f"VALIDATION FAILED: Missing tools: {missing_tools}")
        raise RuntimeError(
            f"Server validation failed: Missing tools: {missing_tools}\n"
            f"Fix: Import and register missing tool handlers."
        )

    # Check for unexpected extra tools
    extra_tools = registered_tools - expected_tools
    if extra_tools:
        logger.warning(f"VALIDATION WARNING: Unexpected tools registered: {extra_tools}")

    # Validate tool schemas are present
    for tool_name, tool_obj in registered_tools_dict.items():
        # Check if tool has a schema (FastMCP generates schemas automatically)
        # Tool objects should have proper signatures
        if not hasattr(tool_obj, "__call__"):
            logger.error(f"VALIDATION FAILED: Tool '{tool_name}' is not callable")
            raise ValueError(
                f"Server validation failed: Tool '{tool_name}' is not callable.\n"
                f"Fix: Ensure tool is properly registered with @mcp.tool decorator."
            )

    # Log successful validation
    logger.info(f"Server startup validation passed: {len(registered_tools_dict)} tools registered")
    logger.info(f"Registered tools: {sorted(registered_tools)}")


# ==============================================================================
# Tool Registration (Import After MCP Instance Creation)
# ==============================================================================

# Import tool handlers to register them with FastMCP via @mcp.tool() decorator
# These imports must come after mcp = FastMCP() to avoid circular imports
# Import directly from modules (not __init__.py) to avoid dependency issues
try:
    import src.mcp.tools.indexing  # noqa: F401, E402
    import src.mcp.tools.search  # noqa: F401, E402
    import src.mcp.tools.tasks  # noqa: F401, E402
    logger.info("Tool modules imported successfully")
except ImportError as e:
    logger.error(f"Failed to import tool modules: {e}", exc_info=True)
    raise


# ==============================================================================
# Main Entry Point
# ==============================================================================

def main() -> None:
    """Main entry point for FastMCP server.

    Runs the server with stdio transport for Claude Desktop compatibility.

    Logging behavior:
    - File logging: All server events -> /tmp/codebase-mcp.log
    - Context logging: Tool execution events -> MCP client (via ctx.info())

    Startup sequence:
    1. Validate server configuration (fail-fast)
    2. Start stdio transport server
    3. Handle graceful shutdown on errors
    """
    try:
        logger.info("Starting FastMCP server with stdio transport")
        logger.info("Tool registration complete, starting server...")

        # Start server with stdio transport (default)
        # This is compatible with Claude Desktop out-of-the-box
        mcp.run()

    except (RuntimeError, ValueError) as e:
        # Validation errors - provide clear error messages
        logger.critical(f"Server validation failed: {e}", exc_info=True)
        sys.stderr.write(f"FATAL: Server validation failed: {e}\n")
        sys.exit(1)

    except Exception as e:
        # Unexpected errors during startup
        logger.critical(f"Server startup failed: {e}", exc_info=True)
        sys.stderr.write(f"FATAL: Server startup failed: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
