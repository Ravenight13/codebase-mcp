"""MCP tool handlers for Codebase MCP Server.

This module exports all MCP tool handlers for semantic code search,
repository indexing, and task management.

Constitutional Compliance:
- Principle III: Protocol Compliance (MCP-compliant tool handlers)
- Principle V: Production Quality (comprehensive validation, error handling)
- Principle VIII: Type Safety (mypy --strict compliance)
"""

from .indexing import index_repository_tool
from .search import search_code_tool
from .tasks import (
    create_task_tool,
    get_task_tool,
    list_tasks_tool,
    update_task_tool,
)

__all__ = [
    # Search
    "search_code_tool",
    # Indexing
    "index_repository_tool",
    # Tasks
    "get_task_tool",
    "list_tasks_tool",
    "create_task_tool",
    "update_task_tool",
]
