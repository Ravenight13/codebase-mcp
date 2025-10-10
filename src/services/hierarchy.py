"""Hierarchical work item query service for efficient tree traversal.

Provides high-performance queries for work item hierarchies using:
- Materialized paths for ancestor retrieval (parse path column)
- Recursive CTEs for descendant traversal (up to 5 levels)
- Path update propagation for hierarchy modifications

Performance Targets:
- <10ms for 5-level hierarchies (FR-013)
- <1ms for single work item lookup by ID

Entity Responsibilities:
- Query work items with full hierarchical context (ancestors + descendants)
- Retrieve ancestors via materialized path parsing
- Retrieve descendants via PostgreSQL recursive CTE
- Update materialized paths atomically when parent changes
- Recursively propagate path updates to all descendants

Constitutional Compliance:
- Principle IV: Performance (<10ms hierarchical queries)
- Principle V: Production quality (error handling, atomic transactions)
- Principle VIII: Type safety (100% type annotations, mypy --strict)
"""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.task import WorkItem


class HierarchyServiceError(Exception):
    """Base exception for hierarchy service errors."""
    pass


class WorkItemNotFoundError(HierarchyServiceError):
    """Raised when work item lookup fails."""
    pass


class InvalidDepthError(HierarchyServiceError):
    """Raised when depth exceeds maximum (5 levels)."""
    pass


class CircularReferenceError(HierarchyServiceError):
    """Raised when path update would create circular reference."""
    pass


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

    Example:
        >>> async with session_factory() as session:
        ...     work_item = await get_work_item_with_hierarchy(
        ...         uuid.UUID("..."),
        ...         session,
        ...         max_depth=3
        ...     )
        ...     print(f"Ancestors: {len(work_item.ancestors)}")
        ...     print(f"Descendants: {len(work_item.descendants)}")
    """
    # Validate max_depth
    if max_depth < 1 or max_depth > 5:
        raise InvalidDepthError(f"max_depth must be 1-5, got {max_depth}")

    # Fetch work item
    result = await session.execute(
        select(WorkItem).where(WorkItem.id == work_item_id)
    )
    work_item = result.scalar_one_or_none()
    if work_item is None:
        raise WorkItemNotFoundError(f"Work item {work_item_id} not found")

    # Get ancestors via materialized path
    ancestors = await get_ancestors(work_item_id, session)

    # Get descendants via recursive CTE
    descendants = await get_descendants(work_item_id, session, max_depth)

    # Populate relationships
    # NOTE: These are temporary attributes for API response
    # Not stored in database, but used for hierarchical queries
    work_item.ancestors = ancestors  # type: ignore
    work_item.descendants = descendants  # type: ignore

    return work_item


async def get_ancestors(
    work_item_id: uuid.UUID,
    session: AsyncSession,
) -> list[WorkItem]:
    """Retrieve all ancestors ordered from root to parent.

    Uses materialized path column for efficient single-query retrieval.
    Example path: "/parent1/parent2/current" → fetch [parent1, parent2]

    Performance: <1ms for single work item lookup

    Args:
        work_item_id: UUID of work item to retrieve ancestors for
        session: Active async database session

    Returns:
        List of WorkItem instances ordered from root to immediate parent

    Raises:
        WorkItemNotFoundError: If work item does not exist

    Example:
        >>> async with session_factory() as session:
        ...     ancestors = await get_ancestors(uuid.UUID("..."), session)
        ...     for ancestor in ancestors:
        ...         print(f"{ancestor.title} (depth {ancestor.depth})")
    """
    # Fetch work item to get path
    result = await session.execute(
        select(WorkItem).where(WorkItem.id == work_item_id)
    )
    work_item = result.scalar_one_or_none()
    if work_item is None:
        raise WorkItemNotFoundError(f"Work item {work_item_id} not found")

    # Parse path to extract ancestor IDs
    # Path format: "/parent1/parent2/current"
    # Split and filter empty strings from leading/trailing slashes
    path_parts = [p for p in work_item.path.split("/") if p]

    # If path is "/" (root item), no ancestors
    if not path_parts or len(path_parts) == 1:
        return []

    # Extract ancestor IDs (all except last, which is current item)
    ancestor_id_strs = path_parts[:-1]

    # Convert to UUIDs
    try:
        ancestor_ids = [uuid.UUID(id_str) for id_str in ancestor_id_strs]
    except ValueError as e:
        raise HierarchyServiceError(
            f"Invalid UUID in path {work_item.path}: {e}"
        ) from e

    # Fetch all ancestors in one query
    result = await session.execute(
        select(WorkItem)
        .where(WorkItem.id.in_(ancestor_ids))
        .order_by(WorkItem.depth)
    )
    ancestors = list(result.scalars().all())

    return ancestors


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

    Example:
        >>> async with session_factory() as session:
        ...     descendants = await get_descendants(
        ...         uuid.UUID("..."),
        ...         session,
        ...         max_depth=3
        ...     )
        ...     for descendant in descendants:
        ...         print(f"{'  ' * descendant.depth}{descendant.title}")
    """
    # Validate max_depth
    if max_depth < 1 or max_depth > 5:
        raise InvalidDepthError(f"max_depth must be 1-5, got {max_depth}")

    # Verify work item exists
    result = await session.execute(
        select(WorkItem).where(WorkItem.id == work_item_id)
    )
    work_item = result.scalar_one_or_none()
    if work_item is None:
        raise WorkItemNotFoundError(f"Work item {work_item_id} not found")

    # Recursive CTE for descendants
    # Based on research.md lines 228-242
    cte_query = text("""
        WITH RECURSIVE descendants AS (
            -- Anchor: Select the root work item
            SELECT
                id,
                parent_id,
                title,
                description,
                notes,
                item_type,
                status,
                path,
                depth,
                branch_name,
                commit_hash,
                pr_number,
                metadata,
                deleted_at,
                created_at,
                updated_at,
                created_by,
                version,
                0 as level
            FROM tasks
            WHERE id = :root_id

            UNION ALL

            -- Recursive: Select children of previous level
            SELECT
                w.id,
                w.parent_id,
                w.title,
                w.description,
                w.notes,
                w.item_type,
                w.status,
                w.path,
                w.depth,
                w.branch_name,
                w.commit_hash,
                w.pr_number,
                w.metadata,
                w.deleted_at,
                w.created_at,
                w.updated_at,
                w.created_by,
                w.version,
                d.level + 1
            FROM tasks w
            INNER JOIN descendants d ON w.parent_id = d.id
            WHERE d.level < :max_depth
        )
        SELECT * FROM descendants
        WHERE id != :root_id  -- Exclude root item from descendants
        ORDER BY level, path;
    """)

    # Execute CTE
    result = await session.execute(
        cte_query,
        {"root_id": work_item_id, "max_depth": max_depth}
    )

    # Convert rows to WorkItem instances
    # NOTE: text() queries return Row objects, not ORM instances
    # We need to manually construct WorkItem instances
    descendants: list[WorkItem] = []
    for row in result:
        descendant = WorkItem(
            id=row.id,
            parent_id=row.parent_id,
            title=row.title,
            description=row.description,
            notes=row.notes,
            item_type=row.item_type,
            status=row.status,
            path=row.path,
            depth=row.depth,
            branch_name=row.branch_name,
            commit_hash=row.commit_hash,
            pr_number=row.pr_number,
            metadata_=row.metadata,
            deleted_at=row.deleted_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
            created_by=row.created_by,
            version=row.version,
        )
        descendants.append(descendant)

    return descendants


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

    Example:
        >>> async with session_factory() as session:
        ...     work_item = await session.get(WorkItem, uuid.UUID("..."))
        ...     work_item.parent_id = new_parent_id
        ...     await update_materialized_path(work_item, session)
        ...     await session.commit()

    Notes:
        - Must be called within active transaction
        - Caller responsible for session.commit()
        - Validates max depth constraint (5 levels)
    """
    # Calculate new path and depth based on parent
    if work_item.parent_id is None:
        # Root item: path = "/{id}", depth = 0
        new_path = f"/{work_item.id}"
        new_depth = 0
    else:
        # Child item: inherit parent's path and increment depth
        result = await session.execute(
            select(WorkItem).where(WorkItem.id == work_item.parent_id)
        )
        parent = result.scalar_one_or_none()
        if parent is None:
            raise WorkItemNotFoundError(
                f"Parent work item {work_item.parent_id} not found"
            )

        # Prevent circular reference: new parent cannot be a descendant
        # Check if parent's path contains current item's ID
        if str(work_item.id) in parent.path:
            raise CircularReferenceError(
                f"Cannot set parent {work_item.parent_id}: "
                f"would create circular reference (parent is descendant)"
            )

        new_path = f"{parent.path}/{work_item.id}"
        new_depth = parent.depth + 1

        # Validate depth constraint
        if new_depth > 5:
            raise InvalidDepthError(
                f"Cannot update path: depth {new_depth} exceeds maximum (5)"
            )

    # Store old path for descendant updates
    old_path = work_item.path

    # Update current item's path and depth
    work_item.path = new_path
    work_item.depth = new_depth

    # Update all descendants' paths recursively
    # Replace old_path prefix with new_path in all descendant paths
    # Example: If old_path="/a/b", new_path="/c/d", and descendant="/a/b/e"
    #          Then new descendant path="/c/d/e"

    # Only update if path actually changed (avoid unnecessary updates)
    if old_path != new_path:
        # Get all descendants that need path updates
        descendants = await get_descendants(work_item.id, session, max_depth=5)

        for descendant in descendants:
            # Replace old path prefix with new path prefix
            if descendant.path.startswith(old_path):
                descendant.path = descendant.path.replace(
                    old_path,
                    new_path,
                    1  # Replace only first occurrence (prefix)
                )
                # Recalculate depth from new path
                path_parts = [p for p in descendant.path.split("/") if p]
                descendant.depth = len(path_parts) - 1

                # Validate depth constraint for descendants
                if descendant.depth > 5:
                    raise InvalidDepthError(
                        f"Cannot update path for descendant {descendant.id}: "
                        f"depth {descendant.depth} exceeds maximum (5)"
                    )

    # NOTE: Caller must commit session to persist changes
    # This allows batching multiple path updates in single transaction
