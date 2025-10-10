"""Work item CRUD operations service.

Provides comprehensive CRUD operations for polymorphic work items with
hierarchical relationships, optimistic locking, soft delete, and pagination.

Constitutional Compliance:
- Principle IV: Performance (<150ms CRUD operations, <10ms hierarchical queries)
- Principle V: Production quality (error handling, optimistic locking, soft delete)
- Principle VIII: Type safety (100% type annotations, mypy --strict)

Key Features:
- Create work items with type-specific metadata and parent relationships
- Update work items with optimistic locking (version checking)
- Query work items with optional full hierarchy (ancestors + descendants)
- List work items with filters and pagination
- Soft delete with audit trail preservation
- Pydantic validation for all JSONB metadata
- Integration with hierarchy service for path management
- Comprehensive error handling and structured logging

Performance Targets:
- <150ms for CRUD operations
- <10ms for hierarchical queries (5 levels)
- <1ms for single work item lookup by ID
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.mcp.mcp_logging import get_logger
from src.models.task import WorkItem
from src.services.hierarchy import (
    InvalidDepthError,
    WorkItemNotFoundError as HierarchyWorkItemNotFoundError,
    get_work_item_with_hierarchy,
    update_materialized_path,
)
from src.services.locking import OptimisticLockError, update_with_version_check
from src.services.validation import ValidationError, validate_work_item_metadata

# ==============================================================================
# Import Pydantic Schemas from Contracts
# ==============================================================================

# Add specs/003-database-backed-project/contracts to Python path
specs_contracts_path = (
    Path(__file__).parent.parent.parent
    / "specs"
    / "003-database-backed-project"
    / "contracts"
)
if specs_contracts_path.exists() and str(specs_contracts_path) not in sys.path:
    sys.path.insert(0, str(specs_contracts_path))

try:
    from pydantic_schemas import (  # type: ignore
        ItemType,
        WorkItemMetadata,
        WorkItemStatus,
    )
except ImportError as e:
    raise ImportError(
        f"Failed to import Pydantic schemas from {specs_contracts_path}. "
        f"Ensure contracts/pydantic-schemas.py exists and is valid. Error: {e}"
    ) from e

# ==============================================================================
# Constants and Logger
# ==============================================================================

logger = get_logger(__name__)

# ==============================================================================
# Exception Classes
# ==============================================================================


class WorkItemNotFoundError(Exception):
    """Raised when work item lookup fails.

    HTTP Mapping:
        404 Not Found - Work item does not exist
    """

    def __init__(self, work_item_id: UUID) -> None:
        """Initialize WorkItemNotFoundError."""
        self.work_item_id = work_item_id
        message = f"Work item not found: {work_item_id}"
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for MCP error responses."""
        return {
            "error_type": "WorkItemNotFoundError",
            "work_item_id": str(self.work_item_id),
            "http_status": 404,
        }


class InvalidWorkItemDataError(Exception):
    """Raised when work item data is invalid.

    HTTP Mapping:
        400 Bad Request - Invalid input data
    """

    def __init__(self, message: str) -> None:
        """Initialize InvalidWorkItemDataError."""
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for MCP error responses."""
        return {
            "error_type": "InvalidWorkItemDataError",
            "message": str(self),
            "http_status": 400,
        }


# ==============================================================================
# Pydantic Models for Pagination
# ==============================================================================


class PaginatedWorkItems:
    """Paginated work items result container.

    Attributes:
        items: List of WorkItem instances in current page
        total_count: Total number of items matching filter
        limit: Maximum items per page
        offset: Number of items skipped
        has_more: Whether more items exist beyond current page
    """

    def __init__(
        self,
        items: list[WorkItem],
        total_count: int,
        limit: int,
        offset: int,
    ) -> None:
        """Initialize PaginatedWorkItems."""
        self.items = items
        self.total_count = total_count
        self.limit = limit
        self.offset = offset
        self.has_more = (offset + len(items)) < total_count


# ==============================================================================
# Service Functions
# ==============================================================================


async def create_work_item(
    item_type: ItemType,
    title: str,
    metadata: WorkItemMetadata,
    parent_id: UUID | None,
    created_by: str,
    session: AsyncSession,
    description: str | None = None,
    notes: str | None = None,
    branch_name: str | None = None,
) -> WorkItem:
    """Create new work item with type-specific metadata and optional parent.

    Automatically calculates path and depth based on parent relationship.
    Validates metadata with Pydantic before creating database record.

    Args:
        item_type: Work item type (project|session|task|research)
        title: Work item title (1-200 characters)
        metadata: Type-specific metadata (must match item_type)
        parent_id: Parent work item UUID (None for root items)
        created_by: AI client identifier creating work item
        session: Active async database session
        description: Optional detailed description
        notes: Optional additional notes
        branch_name: Optional git branch name

    Returns:
        Created WorkItem instance with calculated path and depth

    Raises:
        ValidationError: Invalid metadata (Pydantic validation failed)
        WorkItemNotFoundError: Parent work item does not exist
        InvalidDepthError: Parent depth would exceed maximum (5 levels)

    Performance:
        <150ms for creation with validation

    Example:
        >>> from pydantic_schemas import ProjectMetadata, ItemType
        >>>
        >>> metadata = ProjectMetadata(
        ...     description="Add semantic search to MCP server",
        ...     target_quarter="2025-Q1",
        ...     constitutional_principles=["Simplicity Over Features"]
        ... )
        >>>
        >>> async with session_factory() as session:
        ...     project = await create_work_item(
        ...         item_type=ItemType.PROJECT,
        ...         title="Implement semantic code search",
        ...         metadata=metadata,
        ...         parent_id=None,  # Root item
        ...         created_by="claude-code-v1",
        ...         session=session
        ...     )
        ...     await session.commit()
        ...     print(f"Project created: {project.id}")
    """
    logger.info(
        f"Creating {item_type.value} work item: {title}",
        extra={
            "context": {
                "item_type": item_type.value,
                "title": title,
                "parent_id": str(parent_id) if parent_id else None,
                "created_by": created_by,
            }
        },
    )

    # Validate metadata matches item_type
    try:
        metadata_dict = metadata.model_dump() if hasattr(metadata, 'model_dump') else metadata
        validated_metadata = validate_work_item_metadata(item_type, metadata_dict)
    except ValidationError as e:
        logger.warning(
            f"Work item metadata validation failed for {item_type.value}",
            extra={
                "context": {
                    "item_type": item_type.value,
                    "field_errors": e.field_errors,
                }
            },
        )
        raise

    # Calculate path and depth based on parent
    if parent_id is None:
        # Root item: depth 0, path will be set after ID generation
        path = "/"
        depth = 0
    else:
        # Child item: inherit from parent
        result = await session.execute(
            select(WorkItem).where(WorkItem.id == parent_id)
        )
        parent = result.scalar_one_or_none()
        if parent is None:
            raise WorkItemNotFoundError(parent_id)

        # Validate depth constraint
        if parent.depth >= 5:
            raise InvalidDepthError(
                f"Cannot create child: parent depth {parent.depth} is at maximum (5)"
            )

        # Path will be calculated after ID generation: "{parent.path}/{new_id}"
        path = parent.path
        depth = parent.depth + 1

    # Create work item
    work_item = WorkItem(
        item_type=item_type.value,
        title=title,
        description=description,
        notes=notes,
        status=WorkItemStatus.ACTIVE.value,
        parent_id=parent_id,
        path=path,  # Temporary, will be updated after flush
        depth=depth,
        branch_name=branch_name,
        metadata_=validated_metadata.model_dump() if hasattr(validated_metadata, 'model_dump') else validated_metadata,
        created_by=created_by,
    )
    session.add(work_item)

    # Flush to get work_item.id for path calculation
    await session.flush()

    # Update path to include new work item ID
    if parent_id is None:
        work_item.path = f"/{work_item.id}"
    else:
        work_item.path = f"{path}/{work_item.id}"

    # Flush updated path
    await session.flush()

    logger.info(
        f"Work item created: {title}",
        extra={
            "context": {
                "work_item_id": str(work_item.id),
                "item_type": item_type.value,
                "title": title,
                "path": work_item.path,
                "depth": depth,
            }
        },
    )

    return work_item


async def update_work_item(
    work_item_id: UUID,
    version: int,
    updates: dict[str, Any],
    updated_by: str,
    session: AsyncSession,
) -> WorkItem:
    """Update work item with optimistic locking.

    Supports partial updates (only provided fields are updated).
    If parent_id is updated, automatically recalculates path and depth
    for the work item and all descendants.

    Args:
        work_item_id: Work item UUID to update
        version: Current version for optimistic locking
        updates: Dictionary of field updates
        updated_by: AI client identifier performing update
        session: Active async database session

    Returns:
        Updated WorkItem with incremented version

    Raises:
        WorkItemNotFoundError: Work item with given UUID does not exist
        OptimisticLockError: Version mismatch (concurrent update detected)
        ValidationError: Invalid metadata updates (Pydantic validation failed)
        InvalidDepthError: Parent change would exceed maximum depth (5 levels)

    Supported Update Fields:
        - title: str (1-200 characters)
        - description: str | None
        - notes: str | None
        - status: WorkItemStatus (active|completed|blocked)
        - parent_id: UUID | None (triggers path recalculation)
        - branch_name: str | None
        - commit_hash: str | None (40 hex chars)
        - pr_number: int | None
        - metadata: WorkItemMetadata (type-specific, validated)
        - deleted_at: datetime | None (soft delete)

    Performance:
        <150ms for updates without parent change
        <500ms for updates with parent change (path propagation)

    Example:
        >>> async with session_factory() as session:
        ...     # Update work item status
        ...     updated = await update_work_item(
        ...         work_item_id=UUID("..."),
        ...         version=3,
        ...         updates={
        ...             "status": WorkItemStatus.COMPLETED.value,
        ...             "commit_hash": "84b04732a1f5e9c8d3b2a0e6f7c8d9e0a1b2c3d4"
        ...         },
        ...         updated_by="claude-code-v1",
        ...         session=session
        ...     )
        ...     assert updated.version == 4
        ...     await session.commit()
    """
    logger.info(
        f"Updating work item: {work_item_id}",
        extra={
            "context": {
                "work_item_id": str(work_item_id),
                "version": version,
                "update_fields": list(updates.keys()),
                "updated_by": updated_by,
            }
        },
    )

    # Fetch work item
    result = await session.execute(
        select(WorkItem).where(WorkItem.id == work_item_id)
    )
    work_item = result.scalar_one_or_none()
    if work_item is None:
        raise WorkItemNotFoundError(work_item_id)

    # Validate metadata updates if present
    if "metadata" in updates:
        try:
            item_type = ItemType(work_item.item_type)
            validated_metadata = validate_work_item_metadata(
                item_type,
                updates["metadata"]
            )
            updates["metadata_"] = validated_metadata.model_dump()
            del updates["metadata"]  # Remove original key
        except ValidationError as e:
            logger.warning(
                f"Work item metadata validation failed for {work_item_id}",
                extra={
                    "context": {
                        "work_item_id": str(work_item_id),
                        "field_errors": e.field_errors,
                    }
                },
            )
            raise

    # Check if parent_id is being updated (requires path recalculation)
    parent_id_updated = "parent_id" in updates

    # Apply updates with optimistic locking
    try:
        updated_work_item = await update_with_version_check(
            entity=work_item,
            updates=updates,
            expected_version=version,
            session=session,
        )

        # If parent_id changed, recalculate paths
        if parent_id_updated:
            logger.info(
                f"Parent changed for work item {work_item_id}, recalculating paths",
                extra={
                    "context": {
                        "work_item_id": str(work_item_id),
                        "old_parent_id": str(work_item.parent_id) if work_item.parent_id else None,
                        "new_parent_id": str(updates["parent_id"]) if updates["parent_id"] else None,
                    }
                },
            )
            await update_materialized_path(updated_work_item, session)

        logger.info(
            f"Work item updated: {work_item_id}",
            extra={
                "context": {
                    "work_item_id": str(work_item_id),
                    "old_version": version,
                    "new_version": updated_work_item.version,
                    "updated_fields": list(updates.keys()),
                }
            },
        )

        return updated_work_item

    except OptimisticLockError as e:
        logger.error(
            f"Optimistic lock error updating work item {work_item_id}",
            extra={
                "context": {
                    "work_item_id": str(work_item_id),
                    "expected_version": version,
                    "current_version": e.current_version,
                }
            },
        )
        raise


async def get_work_item(
    work_item_id: UUID,
    include_hierarchy: bool = False,
    session: AsyncSession | None = None,
) -> WorkItem:
    """Retrieve work item with optional full hierarchy.

    Args:
        work_item_id: Work item UUID to retrieve
        include_hierarchy: Include ancestors and descendants (default: False)
        session: Active async database session

    Returns:
        WorkItem instance (with ancestors/descendants if include_hierarchy=True)

    Raises:
        WorkItemNotFoundError: Work item with given UUID does not exist

    Performance:
        <1ms for single work item lookup (without hierarchy)
        <10ms for hierarchical query (5 levels)

    Example:
        >>> async with session_factory() as session:
        ...     # Get work item without hierarchy
        ...     work_item = await get_work_item(UUID("..."), session=session)
        ...     print(f"Title: {work_item.title}")
        ...
        ...     # Get work item with full hierarchy
        ...     work_item_with_hierarchy = await get_work_item(
        ...         UUID("..."),
        ...         include_hierarchy=True,
        ...         session=session
        ...     )
        ...     print(f"Ancestors: {len(work_item_with_hierarchy.ancestors)}")
        ...     print(f"Descendants: {len(work_item_with_hierarchy.descendants)}")
    """
    if session is None:
        raise ValueError("session parameter is required")

    logger.debug(
        f"Querying work item: {work_item_id}",
        extra={
            "context": {
                "work_item_id": str(work_item_id),
                "include_hierarchy": include_hierarchy,
            }
        },
    )

    work_item: WorkItem
    if include_hierarchy:
        # Use hierarchy service for full hierarchical query
        try:
            work_item = await get_work_item_with_hierarchy(
                work_item_id,
                session,
                max_depth=5,
            )
        except HierarchyWorkItemNotFoundError as e:
            raise WorkItemNotFoundError(work_item_id) from e
    else:
        # Simple single-record query
        result = await session.execute(
            select(WorkItem).where(WorkItem.id == work_item_id)
        )
        work_item_or_none = result.scalar_one_or_none()
        if work_item_or_none is None:
            raise WorkItemNotFoundError(work_item_id)
        work_item = work_item_or_none

    logger.debug(
        f"Work item found: {work_item.title}",
        extra={
            "context": {
                "work_item_id": str(work_item_id),
                "title": work_item.title,
                "item_type": work_item.item_type,
            }
        },
    )

    return work_item


async def list_work_items(
    filters: dict[str, Any],
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession | None = None,
) -> PaginatedWorkItems:
    """List work items with filters and pagination.

    Args:
        filters: Filter criteria (item_type, status, parent_id, include_deleted)
        limit: Maximum number of results (1-1000, default: 50)
        offset: Number of results to skip (default: 0)
        session: Active async database session

    Returns:
        PaginatedWorkItems with items and pagination metadata

    Supported Filters:
        - item_type: ItemType (project|session|task|research)
        - status: WorkItemStatus (active|completed|blocked)
        - parent_id: UUID | None (filter by parent, None for root items)
        - include_deleted: bool (include soft-deleted items, default: False)

    Performance:
        <50ms for filtered queries with pagination

    Example:
        >>> async with session_factory() as session:
        ...     # Get active tasks
        ...     result = await list_work_items(
        ...         filters={
        ...             "item_type": ItemType.TASK.value,
        ...             "status": WorkItemStatus.ACTIVE.value,
        ...         },
        ...         limit=20,
        ...         offset=0,
        ...         session=session
        ...     )
        ...     print(f"Found {result.total_count} active tasks")
        ...     print(f"Page has {len(result.items)} items")
        ...     print(f"Has more: {result.has_more}")
    """
    if session is None:
        raise ValueError("session parameter is required")

    logger.debug(
        "Listing work items with filters",
        extra={
            "context": {
                "filters": filters,
                "limit": limit,
                "offset": offset,
            }
        },
    )

    # Build base query
    query = select(WorkItem)

    # Apply filters
    if "item_type" in filters:
        query = query.where(WorkItem.item_type == filters["item_type"])

    if "status" in filters:
        query = query.where(WorkItem.status == filters["status"])

    if "parent_id" in filters:
        query = query.where(WorkItem.parent_id == filters["parent_id"])

    # Soft delete filter (default: exclude deleted)
    include_deleted = filters.get("include_deleted", False)
    if not include_deleted:
        query = query.where(WorkItem.deleted_at.is_(None))

    # Get total count
    from sqlalchemy import func
    count_query = select(func.count()).select_from(query.subquery())
    total_count_result = await session.execute(count_query)
    total_count = total_count_result.scalar_one()

    # Apply pagination and ordering
    query = query.order_by(WorkItem.created_at.desc())
    query = query.limit(limit).offset(offset)

    # Execute query
    result = await session.execute(query)
    items = list(result.scalars().all())

    logger.debug(
        f"Found {len(items)} work items (total: {total_count})",
        extra={
            "context": {
                "item_count": len(items),
                "total_count": total_count,
                "limit": limit,
                "offset": offset,
            }
        },
    )

    return PaginatedWorkItems(
        items=items,
        total_count=total_count,
        limit=limit,
        offset=offset,
    )


async def soft_delete_work_item(
    work_item_id: UUID,
    version: int,
    session: AsyncSession,
) -> None:
    """Soft delete work item by setting deleted_at timestamp.

    Args:
        work_item_id: Work item UUID to delete
        version: Current version for optimistic locking
        session: Active async database session

    Raises:
        WorkItemNotFoundError: Work item with given UUID does not exist
        OptimisticLockError: Version mismatch (concurrent update detected)

    Performance:
        <50ms for soft delete

    Example:
        >>> async with session_factory() as session:
        ...     await soft_delete_work_item(
        ...         work_item_id=UUID("..."),
        ...         version=5,
        ...         session=session
        ...     )
        ...     await session.commit()
    """
    logger.info(
        f"Soft deleting work item: {work_item_id}",
        extra={
            "context": {
                "work_item_id": str(work_item_id),
                "version": version,
            }
        },
    )

    # Update work item with deleted_at timestamp
    await update_work_item(
        work_item_id=work_item_id,
        version=version,
        updates={"deleted_at": datetime.now(timezone.utc)},
        updated_by="system",
        session=session,
    )

    logger.info(
        f"Work item soft deleted: {work_item_id}",
        extra={
            "context": {
                "work_item_id": str(work_item_id),
            }
        },
    )


# ==============================================================================
# Public API
# ==============================================================================

__all__ = [
    "WorkItemNotFoundError",
    "InvalidWorkItemDataError",
    "PaginatedWorkItems",
    "create_work_item",
    "update_work_item",
    "get_work_item",
    "list_work_items",
    "soft_delete_work_item",
]
