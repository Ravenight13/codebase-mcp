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
except ImportError as e:
    logger.critical(f"FATAL: Failed to import tool modules: {e}", exc_info=True)
    sys.stderr.write(f"FATAL: Failed to import tool modules: {e}\n")
    sys.stderr.write("FIX: Check that all dependencies are installed (uv sync)\n")
    sys.stderr.write("LOG: See /tmp/codebase-mcp.log for details\n")
    # Exit immediately - no point continuing without tools
    sys.exit(1)

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
        # Check if tool has proper callable function (FastMCP FunctionTool pattern)
        # FastMCP returns FunctionTool objects with 'fn' attribute containing the callable
        if not (hasattr(tool_obj, "fn") and callable(tool_obj.fn)):
            logger.error(f"VALIDATION FAILED: Tool '{tool_name}' does not have callable function")
            raise ValueError(
                f"Server validation failed: Tool '{tool_name}' does not have callable function.\n"
                f"Fix: Ensure tool is properly registered with @mcp.tool() decorator."
            )

    # Log successful validation
    logger.info(f"Server startup validation passed: {len(registered_tools_dict)} tools registered")
    logger.info(f"Registered tools: {sorted(registered_tools)}")


# ==============================================================================
# Main Entry Point
# ==============================================================================

def main() -> None:
    """Main entry point for FastMCP server.

    Runs the server with stdio transport for Claude Desktop compatibility.

    Startup sequence:
    1. Validate tool registration (fail-fast)
    2. Log diagnostic information
    3. Start stdio transport server
    4. Handle graceful shutdown on errors

    Note: Tool imports happen at MODULE LEVEL before main() runs,
    so decorators have already registered all tools.

    Logging behavior:
    - File logging: All server events -> /tmp/codebase-mcp.log
    - Stderr logging: Critical errors -> Claude Desktop debugging
    - Context logging: Tool execution events -> MCP client (via ctx.info())
    """
    try:
        logger.info("=" * 80)
        logger.info("FastMCP Server Startup")
        logger.info("=" * 80)

        # Step 1: Validate tool registration
        logger.info("Validating tool registration...")
        sys.stderr.write("INFO: Validating tool registration...\n")

        asyncio.run(validate_server_startup(mcp))
        logger.info("✓ Server validation passed")
        sys.stderr.write("INFO: Server validation passed\n")

        # Step 2: Log diagnostic information
        logger.info("=" * 80)
        logger.info("Pre-flight Diagnostics:")

        tools = asyncio.run(mcp.get_tools())
        logger.info(f"  Tools registered: {len(tools)}")
        sys.stderr.write(f"INFO: {len(tools)} tools registered\n")

        for name in sorted(tools.keys()):
            logger.info(f"    - {name}")

        logger.info("=" * 80)

        # Step 3: Start server
        logger.info("Starting FastMCP server with stdio transport")
        sys.stderr.write("INFO: Starting FastMCP server...\n")

        mcp.run()

    except (RuntimeError, ValueError) as e:
        # Validation errors - provide clear error messages
        logger.critical(f"Server validation failed: {e}", exc_info=True)
        sys.stderr.write(f"FATAL: Server validation failed: {e}\n")
        sys.stderr.write(f"LOG: See /tmp/codebase-mcp.log for details\n")
        sys.exit(1)

    except Exception as e:
        # Unexpected errors during startup
        logger.critical(f"Server startup failed: {e}", exc_info=True)
        sys.stderr.write(f"FATAL: Server startup failed: {e}\n")
        sys.stderr.write(f"LOG: See /tmp/codebase-mcp.log for details\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
