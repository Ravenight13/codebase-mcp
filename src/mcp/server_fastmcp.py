"""FastMCP server implementation for Codebase MCP Server.

This module implements the MCP server using the FastMCP framework,
replacing the custom protocol implementation with a standardized approach.

Features:
- FastMCP framework initialization
- Stdio transport for Claude Desktop integration
- Tool registration via decorators
- Automatic schema generation from Pydantic models
- Context injection for logging

Constitutional Compliance:
- Principle III: Protocol Compliance (stdio transport, no stdout/stderr pollution)
- Principle V: Production Quality (startup validation, error handling)
- Principle VIII: Type Safety (full type hints, mypy --strict)
- Principle XI: FastMCP Foundation (FastMCP as standard MCP interface)
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from fastmcp import FastMCP

if TYPE_CHECKING:
    pass

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
    """
    try:
        # Start server with stdio transport (default)
        # This is compatible with Claude Desktop out-of-the-box
        mcp.run()
    except Exception as e:
        # Log to stderr before exiting (stderr is safe during startup failures)
        sys.stderr.write(f"FATAL: Server startup failed: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
