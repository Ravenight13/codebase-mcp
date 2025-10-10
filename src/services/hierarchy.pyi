"""Type stub for hierarchical work item query service.

This stub defines the complete type interface for hierarchy.py.
All functions have complete type annotations for mypy --strict compliance.
"""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.task import WorkItem


class HierarchyServiceError(Exception):
    """Base exception for hierarchy service errors."""
    ...


class WorkItemNotFoundError(HierarchyServiceError):
    """Raised when work item lookup fails."""
    ...


class InvalidDepthError(HierarchyServiceError):
    """Raised when depth exceeds maximum (5 levels)."""
    ...


class CircularReferenceError(HierarchyServiceError):
    """Raised when path update would create circular reference."""
    ...


async def get_work_item_with_hierarchy(
    work_item_id: uuid.UUID,
    session: AsyncSession,
    max_depth: int = 5,
) -> WorkItem:
    """Query work item with full hierarchical context (ancestors + descendants).

    Performance: <10ms for 5-level hierarchies (FR-013)

    Args:
        work_item_id: UUID of work item to retrieve
        session: Active async database session
        max_depth: Maximum descendant depth to retrieve (1-5, default 5)

    Returns:
        WorkItem instance with ancestors[] and descendants[] populated

    Raises:
        WorkItemNotFoundError: If work item does not exist
        InvalidDepthError: If max_depth < 1 or > 5
    """
    ...


async def get_ancestors(
    work_item_id: uuid.UUID,
    session: AsyncSession,
) -> list[WorkItem]:
    """Retrieve all ancestors ordered from root to parent.

    Uses materialized path column for efficient single-query retrieval.

    Performance: <1ms for single work item lookup

    Args:
        work_item_id: UUID of work item to retrieve ancestors for
        session: Active async database session

    Returns:
        List of WorkItem instances ordered from root to immediate parent

    Raises:
        WorkItemNotFoundError: If work item does not exist
    """
    ...


async def get_descendants(
    work_item_id: uuid.UUID,
    session: AsyncSession,
    max_depth: int = 5,
) -> list[WorkItem]:
    """Retrieve all descendants ordered by depth and path.

    Uses PostgreSQL recursive CTE for efficient tree traversal with depth limit.

    Performance: <10ms for 5-level hierarchies

    Args:
        work_item_id: UUID of work item to retrieve descendants for
        session: Active async database session
        max_depth: Maximum recursion depth (1-5, default 5)

    Returns:
        List of WorkItem instances ordered by depth, then path

    Raises:
        WorkItemNotFoundError: If work item does not exist
        InvalidDepthError: If max_depth < 1 or > 5
    """
    ...


async def update_materialized_path(
    work_item: WorkItem,
    session: AsyncSession,
) -> None:
    """Update materialized path and depth when parent changes.

    Recursively updates paths for all descendants in atomic transaction.
    Prevents circular references by validating new parent is not a descendant.

    Performance: O(n) where n = total descendants

    Args:
        work_item: WorkItem instance with potentially changed parent_id
        session: Active async database session

    Raises:
        WorkItemNotFoundError: If parent_id references non-existent item
        CircularReferenceError: If new parent is a descendant of work_item
        HierarchyServiceError: If database update fails

    Notes:
        - Must be called within active transaction
        - Caller responsible for session.commit()
        - Validates max depth constraint (5 levels)
    """
    ...
