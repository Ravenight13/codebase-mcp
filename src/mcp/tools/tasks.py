"""MCP tool handlers for task management.

Provides task CRUD operation tools for MCP clients to manage development tasks
with git integration and status tracking.

Constitutional Compliance:
- Principle III: Protocol Compliance (MCP-compliant responses)
- Principle IV: Performance (<200ms p95 latency targets)
- Principle V: Production Quality (comprehensive validation, error handling)
- Principle VIII: Type Safety (mypy --strict compliance)
- Principle X: Git micro-commits (branch/commit tracking)
- Principle XI: FastMCP Foundation (FastMCP decorators, Context injection)
"""

from __future__ import annotations

import logging
import time
from typing import Any, Literal
from uuid import UUID

from fastmcp import Context
from pydantic import ValidationError as PydanticValidationError

from src.database import get_session_factory
from src.mcp.server_fastmcp import mcp
from src.models import Task, TaskCreate, TaskResponse, TaskUpdate
from src.services import (
    InvalidCommitHashError,
    InvalidStatusError,
    TaskNotFoundError,
    create_task as create_task_service,
    get_task as get_task_service,
    list_tasks as list_tasks_service,
    update_task as update_task_service,
)

# ==============================================================================
# Constants
# ==============================================================================

# File logger for persistent logging (separate from Context logging)
logger = logging.getLogger(__name__)

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


@mcp.tool()
async def get_task(
    task_id: str,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Retrieve a development task by ID.

    Fetches task data including all associated planning references,
    git branches, and commits.

    Args:
        task_id: UUID string of the task to retrieve (required)
        ctx: FastMCP context for logging (injected)

    Returns:
        Dictionary with task data matching MCP contract Task definition

    Raises:
        ValueError: If task_id format is invalid or task not found

    Performance:
        Target: <100ms p95 latency
    """
    start_time = time.perf_counter()

    # Dual logging pattern
    if ctx:
        await ctx.info(f"Fetching task: {task_id}")

    logger.info("get_task called", extra={"task_id": task_id})

    # Validate task_id format (UUID)
    try:
        task_uuid = UUID(task_id)
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid task_id format: {task_id}") from e

    # Get database session
    try:
        async with get_session_factory()() as db:
            task_response = await get_task_service(db, task_uuid)
            await db.commit()
    except TaskNotFoundError as e:
        if ctx:
            await ctx.error(f"Task not found: {task_id}")
        raise ValueError(f"Task not found: {task_id}") from e
    except Exception as e:
        logger.error(
            "Failed to retrieve task",
            extra={"task_id": task_id, "error": str(e)},
        )
        if ctx:
            await ctx.error(f"Failed to retrieve task: {e}")
        raise

    # Check if task exists
    if task_response is None:
        if ctx:
            await ctx.error(f"Task not found: {task_id}")
        raise ValueError(f"Task not found: {task_id}")

    # Convert to response format
    response = _task_to_dict(task_response)

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    logger.info(
        "get_task completed successfully",
        extra={"task_id": task_id, "latency_ms": latency_ms},
    )

    if ctx:
        await ctx.info(f"Task retrieved: {task_id}")

    return response


@mcp.tool()
async def list_tasks(
    status: str | None = None,
    branch: str | None = None,
    limit: int = 50,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """List development tasks with optional filters.

    Supports filtering by status (need to be done, in-progress, complete)
    and git branch name. Results are ordered by updated_at descending.

    Args:
        status: Filter by task status (optional)
        branch: Filter by git branch name (optional)
        limit: Maximum number of results (1-100, default: 50)
        ctx: FastMCP context for logging (injected)

    Returns:
        Dictionary with tasks array and total count:
        {
            "tasks": [...],
            "total_count": 42
        }

    Raises:
        ValueError: If filters are invalid

    Performance:
        Target: <200ms p95 latency
    """
    start_time = time.perf_counter()

    # Dual logging pattern
    if ctx:
        await ctx.info(f"Listing tasks (status={status}, branch={branch})")

    logger.info(
        "list_tasks called",
        extra={"status": status, "branch": branch, "limit": limit},
    )

    # Validate parameters
    if status is not None and status not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status: {status}. Valid values: {list(VALID_STATUSES)}"
        )

    if limit < 1 or limit > 100:
        raise ValueError(f"Limit must be between 1 and 100, got {limit}")

    # Cast status to literal type if present
    status_literal: Literal["need to be done", "in-progress", "complete"] | None = None
    if status is not None:
        status_literal = status  # type: ignore[assignment]

    # List tasks
    try:
        async with get_session_factory()() as db:
            tasks = await list_tasks_service(
                db=db,
                status=status_literal,
                branch=branch,
                limit=limit,
            )
            await db.commit()
    except Exception as e:
        logger.error(
            "Failed to list tasks",
            extra={
                "status": status,
                "branch": branch,
                "limit": limit,
                "error": str(e),
            },
        )
        if ctx:
            await ctx.error(f"Failed to list tasks: {e}")
        raise

    # Convert tasks to response format
    response: dict[str, Any] = {
        "tasks": [_task_to_dict(task) for task in tasks],
        "total_count": len(tasks),
    }

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    logger.info(
        "list_tasks completed successfully",
        extra={"tasks_count": len(tasks), "latency_ms": latency_ms},
    )

    if ctx:
        await ctx.info(f"Listed {len(tasks)} tasks")

    return response


@mcp.tool()
async def create_task(
    title: str,
    description: str | None = None,
    notes: str | None = None,
    planning_references: list[str] | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Create a new development task.

    Creates a task with 'need to be done' status and optional planning
    references. Supports git integration for tracking implementation
    progress across branches and commits.

    Args:
        title: Task title (1-200 characters, required)
        description: Task description (optional)
        notes: Additional notes (optional)
        planning_references: Relative paths to planning documents (optional)
        ctx: FastMCP context for logging (injected)

    Returns:
        Dictionary with created task data matching MCP contract Task definition

    Raises:
        ValueError: If input validation fails

    Performance:
        Target: <150ms p95 latency
    """
    start_time = time.perf_counter()

    # Dual logging pattern
    if ctx:
        await ctx.info(f"Creating task: {title[:50]}")

    logger.info(
        "create_task called",
        extra={
            "title": title[:100],
            "has_description": description is not None,
            "has_notes": notes is not None,
            "planning_refs": len(planning_references) if planning_references else 0,
        },
    )

    # Validate parameters
    if not title or not title.strip():
        raise ValueError("Task title cannot be empty")

    if len(title) > 200:
        raise ValueError(f"Task title too long (max 200 characters): {len(title)}")

    # Construct TaskCreate model
    try:
        task_data = TaskCreate(
            title=title,
            description=description,
            notes=notes,
            planning_references=planning_references or [],
        )
    except PydanticValidationError as e:
        raise ValueError(f"Invalid task data: {e}") from e

    # Create task
    try:
        async with get_session_factory()() as db:
            task_response = await create_task_service(db=db, task_data=task_data)
            await db.commit()
    except Exception as e:
        logger.error(
            "Failed to create task",
            extra={"title": title[:100], "error": str(e)},
        )
        if ctx:
            await ctx.error(f"Failed to create task: {e}")
        raise

    # Convert to response format
    response = _task_to_dict(task_response)

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    logger.info(
        "create_task completed successfully",
        extra={
            "task_id": str(task_response.id),
            "title": title[:100],
            "latency_ms": latency_ms,
        },
    )

    if ctx:
        await ctx.info(f"Task created: {task_response.id}")

    return response


@mcp.tool()
async def update_task(
    task_id: str,
    status: str | None = None,
    branch: str | None = None,
    commit: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Update an existing development task.

    Supports partial updates (only provided fields are updated).
    Can associate tasks with git branches and commits for traceability.

    Args:
        task_id: UUID string of the task to update (required)
        status: New status (optional, must be valid status)
        branch: Git branch name to associate (optional)
        commit: Git commit hash to associate (optional, must be 40-char hex)
        ctx: FastMCP context for logging (injected)

    Returns:
        Dictionary with updated task data matching MCP contract Task definition

    Raises:
        ValueError: If input validation fails or task not found

    Performance:
        Target: <150ms p95 latency
    """
    start_time = time.perf_counter()

    # Dual logging pattern
    if ctx:
        await ctx.info(f"Updating task: {task_id}")

    logger.info(
        "update_task called",
        extra={
            "task_id": task_id,
            "status": status,
            "branch": branch,
            "commit": commit,
        },
    )

    # Validate task_id format (UUID)
    try:
        task_uuid = UUID(task_id)
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid task_id format: {task_id}") from e

    # Validate status if provided
    if status is not None and status not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status: {status}. Valid values: {list(VALID_STATUSES)}"
        )

    # Cast status to literal type if present
    status_literal: Literal["need to be done", "in-progress", "complete"] | None = None
    if status is not None:
        status_literal = status  # type: ignore[assignment]

    # Construct TaskUpdate model (simplified for contract - only status is updatable via MCP)
    try:
        task_update = TaskUpdate(
            title=None,
            description=None,
            notes=None,
            status=status_literal,
        )
    except PydanticValidationError as e:
        raise ValueError(f"Invalid task update data: {e}") from e

    # Update task
    try:
        async with get_session_factory()() as db:
            task_response = await update_task_service(
                db=db,
                task_id=task_uuid,
                update_data=task_update,
                branch=branch,
                commit=commit,
            )
            await db.commit()
    except TaskNotFoundError as e:
        if ctx:
            await ctx.error(f"Task not found: {task_id}")
        raise ValueError(f"Task not found: {task_id}") from e
    except InvalidStatusError as e:
        raise ValueError(f"Invalid status: {e}") from e
    except InvalidCommitHashError as e:
        raise ValueError(f"Invalid commit hash: {e}") from e
    except Exception as e:
        logger.error(
            "Failed to update task",
            extra={"task_id": task_id, "error": str(e)},
        )
        if ctx:
            await ctx.error(f"Failed to update task: {e}")
        raise

    # Check if task exists (type safety)
    if task_response is None:
        if ctx:
            await ctx.error(f"Task not found: {task_id}")
        raise ValueError(f"Task not found: {task_id}")

    # Convert to response format
    response = _task_to_dict(task_response)

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    logger.info(
        "update_task completed successfully",
        extra={"task_id": task_id, "latency_ms": latency_ms},
    )

    if ctx:
        await ctx.info(f"Task updated: {task_id}")

    return response


# ==============================================================================
# Module Exports
# ==============================================================================

__all__ = [
    "create_task",
    "get_task",
    "list_tasks",
    "update_task",
]
