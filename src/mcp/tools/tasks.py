"""MCP tool handlers for task management.

Provides task CRUD operation tools for MCP clients to manage development tasks
with git integration and status tracking.

Constitutional Compliance:
- Principle III: Protocol Compliance (MCP-compliant responses)
- Principle IV: Performance (<200ms p95 latency targets)
- Principle V: Production Quality (comprehensive validation, error handling)
- Principle VIII: Type Safety (mypy --strict compliance)
- Principle X: Git micro-commits (branch/commit tracking)
"""

from __future__ import annotations

import time
from typing import Any, Literal
from uuid import UUID

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.mcp.mcp_logging import get_logger
from src.mcp.server import NotFoundError, ValidationError as MCPValidationError
from src.models import Task, TaskCreate, TaskResponse, TaskUpdate
from src.services import (
    InvalidCommitHashError,
    InvalidStatusError,
    TaskNotFoundError,
    create_task,
    get_task,
    list_tasks,
    update_task,
)

# ==============================================================================
# Constants
# ==============================================================================

logger = get_logger(__name__)

# Valid task statuses from MCP contract
VALID_STATUSES: set[str] = {"need to be done", "in-progress", "complete"}

# ==============================================================================
# Helper Functions
# ==============================================================================


def _task_to_dict(task_response: TaskResponse) -> dict[str, Any]:
    """Convert TaskResponse to MCP contract dictionary.

    Args:
        task_response: TaskResponse Pydantic model

    Returns:
        Dictionary matching MCP contract Task definition
    """
    return {
        "id": str(task_response.id),
        "title": task_response.title,
        "description": task_response.description,
        "notes": task_response.notes,
        "status": task_response.status,
        "created_at": task_response.created_at.isoformat(),
        "updated_at": task_response.updated_at.isoformat(),
        "planning_references": task_response.planning_references,
        "branches": task_response.branches,
        "commits": task_response.commits,
    }


# ==============================================================================
# Tool Implementations
# ==============================================================================


async def get_task_tool(
    db: AsyncSession,
    task_id: str,
) -> dict[str, Any]:
    """Retrieve a development task by ID.

    Args:
        task_id: UUID string of the task to retrieve (required)
        db: Async database session (injected by dependency)

    Returns:
        Dictionary with task data matching MCP contract Task definition

    Raises:
        MCPValidationError: If task_id format is invalid
        NotFoundError: If task does not exist

    Performance:
        Target: <100ms p95 latency
    """
    start_time = time.perf_counter()

    logger.info(
        "get_task tool called",
        extra={"context": {"task_id": task_id}},
    )

    # Validate task_id format (UUID)
    try:
        task_uuid = UUID(task_id)
    except (ValueError, AttributeError) as e:
        raise MCPValidationError(
            f"Invalid task_id format: {task_id}",
            details={
                "parameter": "task_id",
                "value": task_id,
                "expected_format": "UUID",
                "error": str(e),
            },
        ) from e

    # Retrieve task
    try:
        task_response = await get_task(db, task_uuid)
    except TaskNotFoundError as e:
        raise NotFoundError(
            f"Task not found: {task_id}",
            details={"task_id": task_id},
        ) from e
    except Exception as e:
        logger.error(
            "Failed to retrieve task",
            extra={"context": {"task_id": task_id, "error": str(e)}},
        )
        raise

    # Check if task exists
    if task_response is None:
        raise NotFoundError(
            f"Task not found: {task_id}",
            details={"task_id": task_id},
        )

    # Convert to response format
    response = _task_to_dict(task_response)

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    logger.info(
        "get_task completed successfully",
        extra={
            "context": {
                "task_id": task_id,
                "latency_ms": latency_ms,
            }
        },
    )

    return response


async def list_tasks_tool(
    db: AsyncSession,
    status: str | None = None,
    branch: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """List development tasks with optional filters.

    Args:
        db: Async database session (injected by dependency)
        status: Filter by task status (optional)
        branch: Filter by git branch name (optional)
        limit: Maximum number of results (1-100, default: 20)

    Returns:
        Dictionary with tasks array and total count:
        {
            "tasks": [...],
            "total_count": 42
        }

    Raises:
        MCPValidationError: If filters are invalid

    Performance:
        Target: <200ms p95 latency
    """
    start_time = time.perf_counter()

    logger.info(
        "list_tasks tool called",
        extra={
            "context": {
                "status": status,
                "branch": branch,
                "limit": limit,
            }
        },
    )

    # Validate parameters
    if status is not None and status not in VALID_STATUSES:
        raise MCPValidationError(
            f"Invalid status: {status}",
            details={
                "parameter": "status",
                "value": status,
                "valid_values": list(VALID_STATUSES),
            },
        )

    if limit < 1 or limit > 100:
        raise MCPValidationError(
            f"Limit must be between 1 and 100, got {limit}",
            details={"parameter": "limit", "value": limit, "min": 1, "max": 100},
        )

    # Cast status to literal type if present
    status_literal: Literal["need to be done", "in-progress", "complete"] | None = None
    if status is not None:
        status_literal = status  # type: ignore[assignment]

    # List tasks
    try:
        tasks = await list_tasks(
            db=db,
            status=status_literal,
            branch=branch,
            limit=limit,
        )
    except Exception as e:
        logger.error(
            "Failed to list tasks",
            extra={
                "context": {
                    "status": status,
                    "branch": branch,
                    "limit": limit,
                    "error": str(e),
                }
            },
        )
        raise

    # Convert tasks to response format
    response: dict[str, Any] = {
        "tasks": [_task_to_dict(task) for task in tasks],
        "total_count": len(tasks),
    }

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    logger.info(
        "list_tasks completed successfully",
        extra={
            "context": {
                "tasks_count": len(tasks),
                "latency_ms": latency_ms,
            }
        },
    )

    return response


async def create_task_tool(
    db: AsyncSession,
    title: str,
    description: str | None = None,
    notes: str | None = None,
    planning_references: list[str] | None = None,
) -> dict[str, Any]:
    """Create a new development task.

    Args:
        title: Task title (1-200 characters, required)
        db: Async database session (injected by dependency)
        description: Task description (optional)
        notes: Additional notes (optional)
        planning_references: Relative paths to planning documents (optional)

    Returns:
        Dictionary with created task data matching MCP contract Task definition

    Raises:
        MCPValidationError: If input validation fails

    Performance:
        Target: <150ms p95 latency
    """
    start_time = time.perf_counter()

    logger.info(
        "create_task tool called",
        extra={
            "context": {
                "title": title[:100],  # Truncate for logging
                "has_description": description is not None,
                "has_notes": notes is not None,
                "planning_references_count": len(planning_references) if planning_references else 0,
            }
        },
    )

    # Validate parameters
    if not title or not title.strip():
        raise MCPValidationError(
            "Task title cannot be empty",
            details={"parameter": "title", "value": title},
        )

    if len(title) > 200:
        raise MCPValidationError(
            f"Task title too long (max 200 characters): {len(title)}",
            details={
                "parameter": "title",
                "length": len(title),
                "max_length": 200,
            },
        )

    # Construct TaskCreate model
    try:
        task_data = TaskCreate(
            title=title,
            description=description,
            notes=notes,
            planning_references=planning_references or [],
        )
    except PydanticValidationError as e:
        raise MCPValidationError(
            f"Invalid task data: {e}",
            details={"validation_errors": e.errors()},
        ) from e

    # Create task
    try:
        task_response = await create_task(db=db, task_data=task_data)
    except Exception as e:
        logger.error(
            "Failed to create task",
            extra={
                "context": {
                    "title": title[:100],
                    "error": str(e),
                }
            },
        )
        raise

    # Convert to response format
    response = _task_to_dict(task_response)

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    logger.info(
        "create_task completed successfully",
        extra={
            "context": {
                "task_id": str(task_response.id),
                "title": title[:100],
                "latency_ms": latency_ms,
            }
        },
    )

    return response


async def update_task_tool(
    db: AsyncSession,
    task_id: str,
    title: str | None = None,
    description: str | None = None,
    notes: str | None = None,
    status: str | None = None,
    branch: str | None = None,
    commit: str | None = None,
) -> dict[str, Any]:
    """Update an existing development task.

    Args:
        task_id: UUID string of the task to update (required)
        db: Async database session (injected by dependency)
        title: New title (optional)
        description: New description (optional)
        notes: New notes (optional)
        status: New status (optional, must be valid status)
        branch: Git branch name to associate (optional)
        commit: Git commit hash to associate (optional, must be 40-char hex)

    Returns:
        Dictionary with updated task data matching MCP contract Task definition

    Raises:
        MCPValidationError: If input validation fails
        NotFoundError: If task does not exist

    Performance:
        Target: <150ms p95 latency
    """
    start_time = time.perf_counter()

    logger.info(
        "update_task tool called",
        extra={
            "context": {
                "task_id": task_id,
                "has_title": title is not None,
                "has_description": description is not None,
                "has_notes": notes is not None,
                "status": status,
                "branch": branch,
                "commit": commit,
            }
        },
    )

    # Validate task_id format (UUID)
    try:
        task_uuid = UUID(task_id)
    except (ValueError, AttributeError) as e:
        raise MCPValidationError(
            f"Invalid task_id format: {task_id}",
            details={
                "parameter": "task_id",
                "value": task_id,
                "expected_format": "UUID",
                "error": str(e),
            },
        ) from e

    # Validate status if provided
    if status is not None and status not in VALID_STATUSES:
        raise MCPValidationError(
            f"Invalid status: {status}",
            details={
                "parameter": "status",
                "value": status,
                "valid_values": list(VALID_STATUSES),
            },
        )

    # Cast status to literal type if present
    status_literal: Literal["need to be done", "in-progress", "complete"] | None = None
    if status is not None:
        status_literal = status  # type: ignore[assignment]

    # Validate title length if provided
    if title is not None and len(title) > 200:
        raise MCPValidationError(
            f"Task title too long (max 200 characters): {len(title)}",
            details={
                "parameter": "title",
                "length": len(title),
                "max_length": 200,
            },
        )

    # Construct TaskUpdate model
    try:
        task_update = TaskUpdate(
            title=title,
            description=description,
            notes=notes,
            status=status_literal,
        )
    except PydanticValidationError as e:
        raise MCPValidationError(
            f"Invalid task update data: {e}",
            details={"validation_errors": e.errors()},
        ) from e

    # Update task
    try:
        task_response = await update_task(
            db=db,
            task_id=task_uuid,
            update_data=task_update,
            branch=branch,
            commit=commit,
        )
    except TaskNotFoundError as e:
        raise NotFoundError(
            f"Task not found: {task_id}",
            details={"task_id": task_id},
        ) from e
    except InvalidStatusError as e:
        raise MCPValidationError(
            f"Invalid status: {e}",
            details={"parameter": "status", "error": str(e)},
        ) from e
    except InvalidCommitHashError as e:
        raise MCPValidationError(
            f"Invalid commit hash: {e}",
            details={"parameter": "commit", "error": str(e)},
        ) from e
    except Exception as e:
        logger.error(
            "Failed to update task",
            extra={
                "context": {
                    "task_id": task_id,
                    "error": str(e),
                }
            },
        )
        raise

    # Convert to response format
    response = _task_to_dict(task_response)

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    logger.info(
        "update_task completed successfully",
        extra={
            "context": {
                "task_id": task_id,
                "latency_ms": latency_ms,
            }
        },
    )

    return response


# ==============================================================================
# Module Exports
# ==============================================================================

__all__ = [
    "get_task_tool",
    "list_tasks_tool",
    "create_task_tool",
    "update_task_tool",
]
