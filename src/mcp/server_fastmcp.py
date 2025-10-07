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
from pathlib import Path
from typing import TYPE_CHECKING

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
# Initialize FastMCP Server
# ==============================================================================

mcp = FastMCP("codebase-mcp")


# ==============================================================================
# Tool Registration
# ==============================================================================

# Tool handlers will be imported from dedicated modules in subsequent tasks:
# - search_code -> src/mcp/tools/search.py
# - index_repository -> src/mcp/tools/indexing.py
# - create_task, get_task, list_tasks, update_task -> src/mcp/tools/tasks.py


# ==============================================================================
# Main Entry Point
# ==============================================================================

def main() -> None:
    """Main entry point for FastMCP server.

    Runs the server with stdio transport for Claude Desktop compatibility.

    Logging behavior:
    - File logging: All server events -> /tmp/codebase-mcp.log
    - Context logging: Tool execution events -> MCP client (via ctx.info())
    """
    try:
        logger.info("Starting FastMCP server with stdio transport")

        # Start server with stdio transport (default)
        # This is compatible with Claude Desktop out-of-the-box
        mcp.run()

    except Exception as e:
        logger.critical(f"Server startup failed: {e}", exc_info=True)
        # Log to stderr before exiting (stderr is safe during startup failures)
        sys.stderr.write(f"FATAL: Server startup failed: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
