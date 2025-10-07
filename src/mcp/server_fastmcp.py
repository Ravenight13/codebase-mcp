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
# FastMCP Lifespan (Database Initialization)
# ==============================================================================


@asynccontextmanager
async def lifespan(app: FastMCP) -> AsyncGenerator[None, None]:
    """Lifespan context manager for FastMCP server.

    Manages server startup and shutdown lifecycle:
    - Startup: Initialize database (blocking to ensure ready before serving)
    - Shutdown: Close database connections gracefully

    Blocking Pattern:
    - Wait for DB to be ready before accepting connections from Claude Desktop
    - Ensures tools can access DB immediately when called
    - Prevents race conditions with early tool invocations

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

    # Startup: Initialize database (blocking to ensure ready before serving)
    # Wait for DB to be ready before accepting connections from Claude Desktop
    try:
        logger.info("Initializing database connection pool...")
        sys.stderr.write("INFO: Initializing database...\n")
        await init_db_connection()  # BLOCKING - wait for completion
        logger.info("✓ Database initialized successfully")
        sys.stderr.write("INFO: Database initialized successfully\n")
    except Exception as e:
        logger.critical(
            f"Failed to initialize database: {e}",
            exc_info=True,
        )
        sys.stderr.write(f"FATAL: Database initialization failed: {e}\n")
        sys.stderr.write("FIX: Check PostgreSQL is running and DATABASE_URL is correct\n")
        raise RuntimeError(f"Database initialization failed: {e}") from e

    # Yield control to FastMCP server (tools are visible NOW)
    yield

    # Shutdown: Close database connection pool gracefully
    try:
        logger.info("Shutting down server...")
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
__all__ = ["mcp"]

# ==============================================================================
# Tool Registration (Module-Level Import for Decorator Execution)
# ==============================================================================

# Import tool modules at module level to execute @mcp.tool() decorators
# This must happen AFTER mcp instance is created but BEFORE main() runs
# Decorators register tools synchronously at import time

try:
    logger.info("Importing tool modules...")
    import src.mcp.tools.indexing  # noqa: F401, E402
    import src.mcp.tools.search  # noqa: F401, E402
    import src.mcp.tools.tasks  # noqa: F401, E402
    logger.info("✓ Tool modules imported successfully")

    # CRITICAL FIX: Re-setup handlers after tools are imported
    # FastMCP calls _setup_handlers() in __init__, but our tools are imported after
    # the instance is created. We need to re-register the handlers so that
    # FastMCP's _mcp_list_tools() is used instead of the default empty handler.
    mcp._setup_handlers()
    logger.info("✓ MCP protocol handlers re-registered with tools")

except ImportError as e:
    logger.critical(f"FATAL: Failed to import tool modules: {e}", exc_info=True)
    sys.stderr.write(f"FATAL: Failed to import tool modules: {e}\n")
    sys.stderr.write("FIX: Check that all dependencies are installed (uv sync)\n")
    sys.stderr.write("LOG: See /tmp/codebase-mcp.log for details\n")
    # Exit immediately - no point continuing without tools
    sys.exit(1)

# ==============================================================================
# Main Entry Point
# ==============================================================================

def main() -> None:
    """Main entry point for FastMCP server.

    Runs the server with stdio transport for Claude Desktop compatibility.

    Startup sequence:
    1. Log startup information
    2. Start FastMCP server with stdio transport
    3. Handle graceful shutdown on errors

    Note: Tool imports happen at MODULE LEVEL before main() runs.
    Tools are registered via @mcp.tool() decorators during import.

    Validation: FastMCP handles validation internally during mcp.run().
    Pre-flight async validation is skipped because it would require a separate
    event loop that can't access the tools registered in the module context.

    Logging behavior:
    - File logging: All server events -> /tmp/codebase-mcp.log
    - Stderr logging: Startup status -> Claude Desktop debugging
    - Context logging: Tool execution events -> MCP client (via ctx.info())
    """
    try:
        logger.info("=" * 80)
        logger.info("FastMCP Server Startup")
        logger.info("=" * 80)
        logger.info("Tool modules imported successfully (6 tools registered)")
        logger.info("Starting FastMCP server with stdio transport...")

        sys.stderr.write("INFO: Starting FastMCP server...\n")
        sys.stderr.write("INFO: 6 tools registered (search, indexing, tasks)\n")
        sys.stderr.write("INFO: Server ready for connections\n")

        # Start server - FastMCP handles validation internally
        mcp.run()

    except Exception as e:
        # Unexpected errors during startup
        logger.critical(f"Server startup failed: {e}", exc_info=True)
        sys.stderr.write(f"FATAL: Server startup failed: {e}\n")
        sys.stderr.write(f"LOG: See /tmp/codebase-mcp.log for details\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
