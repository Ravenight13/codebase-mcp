"""MCP tool handlers for Codebase MCP Server.

This module exports all MCP tool handlers for semantic code search,
repository indexing, and task management.

Constitutional Compliance:
- Principle III: Protocol Compliance (MCP-compliant tool handlers)
- Principle V: Production Quality (comprehensive validation, error handling)
- Principle VIII: Type Safety (mypy --strict compliance)
- Principle XI: FastMCP Foundation (FastMCP decorator-based tools)

Note:
    Tools are registered via @mcp.tool() decorators in their respective modules.
    They are imported in server_fastmcp.py after the mcp instance is created.
"""

# Legacy imports (will be removed after full FastMCP migration)
# from .indexing import index_repository_tool
# from .search import search_code
# from .tasks import (create_task, get_task, list_tasks, update_task)

__all__: list[str] = []
