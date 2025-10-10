"""Task CRUD service with git integration and status history.

Provides complete task management including creation, updates, queries, and
git metadata tracking (branches, commits). Records all status transitions
for audit trail and workflow analysis.

Constitutional Compliance:
- Principle V: Production quality (audit trails, validation, transaction safety)
- Principle VIII: Type safety (full mypy --strict compliance)
- Principle X: Git micro-commits (branch/commit tracking for traceability)

Key Features:
- Create tasks with planning references
- Update tasks with status transition tracking
- Query tasks by status, branch, with pagination
- Link tasks to git branches (TaskBranchLink)
- Link tasks to git commits (TaskCommitLink, SHA-1 validation)
- Automatic status history recording
- Relationship preloading to avoid N+1 queries
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Final
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.mcp.mcp_logging import get_logger
from src.models import (
    Task,
    TaskBranchLink,
    TaskCommitLink,
    TaskCreate,
    TaskPlanningReference,
    TaskResponse,
    TaskStatusHistory,
    TaskSummary,
    TaskUpdate,
)

# ==============================================================================
# Constants
# ==============================================================================

logger = get_logger(__name__)

# Valid task status values
VALID_STATUSES: Final[set[str]] = {"need to be done", "in-progress", "complete"}

# Git SHA-1 validation (40 hex characters)
SHA1_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{40}$")

# Default query limit
DEFAULT_TASK_LIMIT: Final[int] = 20
MAX_TASK_LIMIT: Final[int] = 100


# ==============================================================================
# Custom Exceptions
# ==============================================================================


class TaskNotFoundError(Exception):
    """Raised when task does not exist."""

    pass


class InvalidStatusError(Exception):
    """Raised when task status is invalid."""

    pass


class InvalidCommitHashError(Exception):
    """Raised when commit hash format is invalid."""

    pass


# ==============================================================================
# Helper Functions
# ==============================================================================


def _validate_commit_hash(commit_hash: str) -> None:
    """Validate git commit hash format (SHA-1).

    Args:
        commit_hash: Git commit hash to validate

    Raises:
        InvalidCommitHashError: If hash is not valid SHA-1 format
    """
    if not SHA1_PATTERN.match(commit_hash):
        raise InvalidCommitHashError(
            f"Invalid commit hash format: {commit_hash}. "
            "Expected 40-character hexadecimal SHA-1."
        )


def _task_to_response(task: Task) -> TaskResponse:
    """Convert Task model to TaskResponse schema.

    Args:
        task: Task model with loaded relationships

    Returns:
        TaskResponse with aggregated data
    """
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        notes=task.notes,
        status=task.status,
        created_at=task.created_at,
        updated_at=task.updated_at,
        planning_references=[ref.file_path for ref in task.planning_references],
        branches=[link.branch_name for link in task.branch_links],
        commits=[link.commit_hash for link in task.commit_links],
    )


# ==============================================================================
# Task CRUD Operations
# ==============================================================================


async def create_task(db: AsyncSession, task_data: TaskCreate) -> TaskResponse:
    """Create a new task with planning references.

    Args:
        db: Async database session
        task_data: Task creation data

    Returns:
        Created task with ID and timestamps

    Raises:
        ValueError: If task_data validation fails
        IntegrityError: If database constraints are violated

    Example:
        >>> async with get_session() as db:
        ...     task = await create_task(
        ...         db,
        ...         TaskCreate(
        ...             title="Implement authentication",
        ...             description="Add JWT-based auth",
        ...             planning_references=["specs/001-auth/spec.md"]
        ...         )
        ...     )
        ...     await db.commit()
    """
    logger.info(
        "Creating new task",
        extra={
            "context": {
                "title": task_data.title,
                "planning_references_count": len(task_data.planning_references),
            }
        },
    )

    try:
        # Create task
        task = Task(
            title=task_data.title,
            description=task_data.description,
            notes=task_data.notes,
            status="need to be done",  # Initial status
        )

        db.add(task)
        await db.flush()  # Get task ID without committing

        # Create planning references
        for file_path in task_data.planning_references:
            # Infer reference type from file path
            if "spec.md" in file_path:
                ref_type = "spec"
            elif "plan.md" in file_path:
                ref_type = "plan"
            elif any(
                keyword in file_path
                for keyword in ["data-model", "contract", "quickstart"]
            ):
                ref_type = "design"
            else:
                ref_type = "other"

            ref = TaskPlanningReference(
                task_id=task.id,
                file_path=file_path,
                reference_type=ref_type,
            )
            db.add(ref)

        # Record initial status in history (from None to 'need to be done')
        history = TaskStatusHistory(
            task_id=task.id,
            from_status=None,
            to_status="need to be done",
            changed_at=datetime.utcnow(),
        )
        db.add(history)

        await db.flush()

        # Reload with relationships
        await db.refresh(
            task,
            [
                "planning_references",
                "branch_links",
                "commit_links",
                "status_history",
            ],
        )

        logger.info(
            "Task created successfully",
            extra={"context": {"task_id": str(task.id), "title": task.title}},
        )

        return _task_to_response(task)

    except IntegrityError as e:
        logger.error(
            "Failed to create task (integrity error)",
            extra={"context": {"title": task_data.title, "error": str(e)}},
        )
        raise
    except Exception as e:
        logger.error(
            "Failed to create task",
            extra={"context": {"title": task_data.title, "error": str(e)}},
        )
        raise


async def get_task(db: AsyncSession, task_id: UUID) -> TaskResponse | None:
    """Get task by ID with all relationships loaded.

    Args:
        db: Async database session
        task_id: Task UUID

    Returns:
        Task with relationships, or None if not found

    Example:
        >>> async with get_session() as db:
        ...     task = await get_task(db, task_uuid)
        ...     if task:
        ...         print(f"Task: {task.title}, Status: {task.status}")
    """
    logger.debug(
        "Fetching task by ID", extra={"context": {"task_id": str(task_id)}}
    )

    stmt = (
        select(Task)
        .where(Task.id == task_id)
        .options(
            selectinload(Task.planning_references),
            selectinload(Task.branch_links),
            selectinload(Task.commit_links),
            selectinload(Task.status_history),
        )
    )

    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if task is None:
        logger.warning(
            "Task not found", extra={"context": {"task_id": str(task_id)}}
        )
        return None

    logger.debug(
        "Task retrieved successfully",
        extra={"context": {"task_id": str(task_id), "title": task.title}},
    )

    return _task_to_response(task)


async def list_tasks(
    db: AsyncSession,
    status: str | None = None,
    branch: str | None = None,
    limit: int = DEFAULT_TASK_LIMIT,
    full_details: bool = False,
) -> list[TaskSummary | TaskResponse]:
    """List tasks with optional filters and conditional serialization.

    Args:
        db: Async database session
        status: Filter by status (optional)
        branch: Filter by branch name (optional)
        limit: Maximum results (default 20, max 100)
        full_details: If True, return full TaskResponse; if False, return lightweight
            TaskSummary for token efficiency (default: False)

    Returns:
        List of tasks ordered by created_at descending:
        - TaskSummary objects (~120-150 tokens each) if full_details=False
        - TaskResponse objects (~800-1000 tokens each) if full_details=True

    Raises:
        ValueError: If status is invalid or limit exceeds maximum

    Token Efficiency:
        - full_details=False: 15 tasks ≈ 1800-2250 tokens (6x reduction)
        - full_details=True: 15 tasks ≈ 12000-15000 tokens (backward compatible)

    Example:
        >>> async with get_session() as db:
        ...     # Get task summaries (token-efficient default)
        ...     summaries = await list_tasks(db, status="in-progress", limit=10)
        ...
        ...     # Get full task details
        ...     full_tasks = await list_tasks(
        ...         db, branch="001-auth", limit=5, full_details=True
        ...     )
    """
    # Validate inputs
    if status is not None and status not in VALID_STATUSES:
        raise ValueError(
            f"Invalid status: {status}. Must be one of {VALID_STATUSES}"
        )

    if limit < 1 or limit > MAX_TASK_LIMIT:
        raise ValueError(f"Limit must be between 1 and {MAX_TASK_LIMIT}")

    logger.info(
        "Listing tasks",
        extra={
            "context": {
                "status": status,
                "branch": branch,
                "limit": limit,
            }
        },
    )

    # Build query
    stmt = (
        select(Task)
        .options(
            selectinload(Task.planning_references),
            selectinload(Task.branch_links),
            selectinload(Task.commit_links),
            selectinload(Task.status_history),
        )
        .order_by(Task.created_at.desc())
    )

    # Apply filters
    if status is not None:
        stmt = stmt.where(Task.status == status)

    if branch is not None:
        # Join with TaskBranchLink to filter by branch
        stmt = stmt.join(TaskBranchLink).where(TaskBranchLink.branch_name == branch)

    stmt = stmt.limit(limit)

    # Execute query
    result = await db.execute(stmt)
    tasks = result.scalars().unique().all()

    logger.info(
        "Tasks retrieved successfully",
        extra={
            "context": {
                "count": len(tasks),
                "full_details": full_details,
            }
        },
    )

    # Conditional serialization: TaskSummary for efficiency, TaskResponse for full details
    if full_details:
        return [_task_to_response(task) for task in tasks]
    else:
        return [TaskSummary.model_validate(task) for task in tasks]


async def update_task(
    db: AsyncSession,
    task_id: UUID,
    update_data: TaskUpdate,
    branch: str | None = None,
    commit: str | None = None,
) -> TaskResponse | None:
    """Update task and record status history.

    Args:
        db: Async database session
        task_id: Task UUID to update
        update_data: Fields to update (partial updates supported)
        branch: Git branch to link (optional)
        commit: Git commit hash to link (optional, SHA-1 format)

    Returns:
        Updated task, or None if not found

    Raises:
        TaskNotFoundError: If task does not exist
        InvalidStatusError: If status is invalid
        InvalidCommitHashError: If commit hash format is invalid
        IntegrityError: If database constraints are violated

    Status History:
        - Records transition when status changes
        - Stores from_status -> to_status with timestamp

    Git Integration:
        - Creates TaskBranchLink if branch provided
        - Creates TaskCommitLink if commit provided
        - Validates commit hash format (SHA-1)
        - Handles duplicate links (unique constraint)

    Example:
        >>> async with get_session() as db:
        ...     task = await update_task(
        ...         db,
        ...         task_uuid,
        ...         TaskUpdate(status="in-progress"),
        ...         branch="001-auth",
        ...         commit="a1b2c3d4..."
        ...     )
        ...     await db.commit()
    """
    logger.info(
        "Updating task",
        extra={
            "context": {
                "task_id": str(task_id),
                "branch": branch,
                "commit": commit[:8] if commit else None,
            }
        },
    )

    # Validate commit hash if provided
    if commit is not None:
        _validate_commit_hash(commit)

    # Fetch task with relationships
    stmt = (
        select(Task)
        .where(Task.id == task_id)
        .options(
            selectinload(Task.planning_references),
            selectinload(Task.branch_links),
            selectinload(Task.commit_links),
            selectinload(Task.status_history),
        )
    )

    result = await db.execute(stmt)
    task = result.scalar_one_or_none()

    if task is None:
        logger.warning(
            "Task not found for update", extra={"context": {"task_id": str(task_id)}}
        )
        return None

    try:
        # Track old status for history
        old_status = task.status

        # Update fields (only if provided)
        if update_data.title is not None:
            task.title = update_data.title
        if update_data.description is not None:
            task.description = update_data.description
        if update_data.notes is not None:
            task.notes = update_data.notes
        if update_data.status is not None:
            if update_data.status not in VALID_STATUSES:
                raise InvalidStatusError(
                    f"Invalid status: {update_data.status}. "
                    f"Must be one of {VALID_STATUSES}"
                )
            task.status = update_data.status

        # Record status transition
        if update_data.status is not None and update_data.status != old_status:
            history = TaskStatusHistory(
                task_id=task.id,
                from_status=old_status,
                to_status=update_data.status,
                changed_at=datetime.utcnow(),
            )
            db.add(history)

            logger.info(
                "Task status changed",
                extra={
                    "context": {
                        "task_id": str(task_id),
                        "from_status": old_status,
                        "to_status": update_data.status,
                    }
                },
            )

        # Link to branch if provided
        if branch is not None:
            # Check if already linked (avoid duplicate unique constraint violation)
            existing_branch = await db.execute(
                select(TaskBranchLink).where(
                    TaskBranchLink.task_id == task_id,
                    TaskBranchLink.branch_name == branch,
                )
            )
            if existing_branch.scalar_one_or_none() is None:
                branch_link = TaskBranchLink(
                    task_id=task.id,
                    branch_name=branch,
                )
                db.add(branch_link)

                logger.info(
                    "Task linked to branch",
                    extra={
                        "context": {
                            "task_id": str(task_id),
                            "branch": branch,
                        }
                    },
                )

        # Link to commit if provided
        if commit is not None:
            # Check if already linked
            existing_commit = await db.execute(
                select(TaskCommitLink).where(
                    TaskCommitLink.task_id == task_id,
                    TaskCommitLink.commit_hash == commit,
                )
            )
            if existing_commit.scalar_one_or_none() is None:
                commit_link = TaskCommitLink(
                    task_id=task.id,
                    commit_hash=commit,
                    commit_message=None,  # Can be populated separately
                )
                db.add(commit_link)

                logger.info(
                    "Task linked to commit",
                    extra={
                        "context": {
                            "task_id": str(task_id),
                            "commit": commit[:8],
                        }
                    },
                )

        await db.flush()

        # Reload relationships
        await db.refresh(
            task,
            [
                "planning_references",
                "branch_links",
                "commit_links",
                "status_history",
            ],
        )

        logger.info(
            "Task updated successfully",
            extra={"context": {"task_id": str(task_id), "title": task.title}},
        )

        return _task_to_response(task)

    except IntegrityError as e:
        logger.error(
            "Failed to update task (integrity error)",
            extra={"context": {"task_id": str(task_id), "error": str(e)}},
        )
        raise
    except Exception as e:
        logger.error(
            "Failed to update task",
            extra={"context": {"task_id": str(task_id), "error": str(e)}},
        )
        raise


# ==============================================================================
# Module Exports
# ==============================================================================

__all__ = [
    "TaskNotFoundError",
    "InvalidStatusError",
    "InvalidCommitHashError",
    "create_task",
    "get_task",
    "list_tasks",
    "update_task",
]
