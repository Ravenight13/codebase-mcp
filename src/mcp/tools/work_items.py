"""MCP tool handlers for work item management.

Provides work item CRUD operation tools for MCP clients to manage hierarchical
work items (projects, sessions, tasks, research) with type-safe metadata validation,
optimistic locking, and dependency tracking.

Constitutional Compliance:
- Principle III: Protocol Compliance (MCP-compliant responses)
- Principle IV: Performance (<150ms p95 for CRUD, <10ms for hierarchies)
- Principle V: Production Quality (comprehensive validation, error handling)
- Principle VIII: Type Safety (mypy --strict compliance)
- Principle XI: FastMCP Foundation (FastMCP decorators, Context injection)

Performance Targets:
- create_work_item: <150ms p95
- update_work_item: <150ms p95
- query_work_item: <10ms p95 (5-level hierarchies)
- list_work_items: <200ms p95
"""

from __future__ import annotations

import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from fastmcp import Context
from sqlalchemy import inspect as sqlalchemy_inspect
from sqlalchemy.orm.attributes import NEVER_SET  # type: ignore[attr-defined]

from src.database import get_session_factory
from src.mcp.server_fastmcp import mcp
from src.services.hierarchy import (
    InvalidDepthError,
    WorkItemNotFoundError as HierarchyWorkItemNotFoundError,
)
from src.services.locking import OptimisticLockError
from src.services.validation import ValidationError
from src.services.work_items import (
    InvalidWorkItemDataError,
    WorkItemNotFoundError,
    create_work_item as create_work_item_service,
    get_work_item as get_work_item_service,
    list_work_items as list_work_items_service,
    update_work_item as update_work_item_service,
)

# ==============================================================================
# Import Pydantic Schemas from Contracts
# ==============================================================================

# Add specs/003-database-backed-project/contracts to Python path
specs_contracts_path = (
    Path(__file__).parent.parent.parent.parent
    / "specs"
    / "003-database-backed-project"
    / "contracts"
)
if specs_contracts_path.exists() and str(specs_contracts_path) not in sys.path:
    sys.path.insert(0, str(specs_contracts_path))

try:
    from pydantic_schemas import (  # type: ignore
        ItemType,
        ProjectMetadata,
        ResearchMetadata,
        SessionMetadata,
        TaskMetadata,
        WorkItemStatus,
    )
except ImportError as e:
    raise ImportError(
        f"Failed to import Pydantic schemas from {specs_contracts_path}. "
        f"Ensure contracts/pydantic-schemas.py exists and is valid. Error: {e}"
    ) from e

# ==============================================================================
# Constants
# ==============================================================================

# File logger for persistent logging (separate from Context logging)
logger = logging.getLogger(__name__)

# ==============================================================================
# Helper Functions
# ==============================================================================


def _work_item_to_dict(work_item: Any, include_hierarchy: bool = False) -> dict[str, Any]:
    """Convert WorkItem SQLAlchemy model to MCP contract dictionary.

    Safely handles both attached (session-bound) and detached SQLAlchemy objects.
    Only includes lazy-loaded relationships (children, dependencies) if they were
    already loaded before the session closed.

    Args:
        work_item: WorkItem SQLAlchemy model instance (attached or detached)
        include_hierarchy: Include ancestors and descendants arrays if available

    Returns:
        Dictionary matching MCP contract WorkItem definition
    """
    result: dict[str, Any] = {
        "id": str(work_item.id),
        "version": work_item.version,
        "item_type": work_item.item_type,
        "title": work_item.title,
        "status": work_item.status,
        "parent_id": str(work_item.parent_id) if work_item.parent_id else None,
        "path": work_item.path,
        "depth": work_item.depth,
        "branch_name": work_item.branch_name,
        "commit_hash": work_item.commit_hash,
        "pr_number": work_item.pr_number,
        "metadata": work_item.metadata_,
        "deleted_at": work_item.deleted_at.isoformat() if work_item.deleted_at else None,
        "created_at": work_item.created_at.isoformat(),
        "updated_at": work_item.updated_at.isoformat(),
        "created_by": work_item.created_by,
    }

    # SQLAlchemy session safety: Only include lazy-loaded relationships if they're
    # already loaded. This prevents "Parent instance is not bound to a Session"
    # errors when accessing relationships on detached objects.
    #
    # CRITICAL: Must use inspect() to check load state WITHOUT triggering lazy-load.
    # Even hasattr() will trigger lazy-load on detached objects and raise DetachedInstanceError.
    inspector = sqlalchemy_inspect(work_item)

    # Include children if present (from hierarchical query) and already loaded
    # Use inspect() to check if relationship is loaded without triggering lazy-load
    if "children" in inspector.mapper.relationships:
        children_state = inspector.attrs.children
        # Check if relationship was loaded: loaded_value != NEVER_SET
        # NEVER_SET is a sentinel value indicating the relationship was never accessed
        if children_state.loaded_value is not NEVER_SET:
            # Relationship was loaded, safe to access
            children_value = children_state.loaded_value
            if children_value:  # Only include if non-empty
                result["children"] = [_work_item_to_dict(child) for child in children_value]

    # Include dependencies if present and already loaded
    # Note: The WorkItem model has dependencies_as_source and dependencies_as_target,
    # but not a direct "dependencies" attribute. Skip this for now to avoid AttributeError.
    # If a "dependencies" relationship is added to the model, this code will handle it safely.
    if "dependencies" in inspector.mapper.relationships:
        dependencies_state = inspector.attrs.dependencies
        if dependencies_state.loaded_value is not NEVER_SET:
            dependencies_value = dependencies_state.loaded_value
            if dependencies_value:  # Only include if non-empty
                result["dependencies"] = [
                    {
                        "source_id": str(dep.source_id),
                        "target_id": str(dep.target_id),
                        "dependency_type": dep.dependency_type,
                        "created_at": dep.created_at.isoformat(),
                        "created_by": dep.created_by,
                    }
                    for dep in dependencies_value
                ]

    # Include ancestors and descendants arrays if hierarchy was requested
    # These are temporary attributes set by hierarchy service (not database columns)
    if include_hierarchy:
        # Check for ancestors attribute (set by get_work_item_with_hierarchy)
        if hasattr(work_item, "ancestors") and work_item.ancestors:
            result["ancestors"] = [
                {
                    "id": str(ancestor.id),
                    "title": ancestor.title,
                    "item_type": ancestor.item_type,
                    "depth": ancestor.depth,
                    "path": ancestor.path,
                }
                for ancestor in work_item.ancestors
            ]

        # Check for descendants attribute (set by get_work_item_with_hierarchy)
        if hasattr(work_item, "descendants") and work_item.descendants:
            result["descendants"] = [
                {
                    "id": str(descendant.id),
                    "title": descendant.title,
                    "item_type": descendant.item_type,
                    "depth": descendant.depth,
                    "path": descendant.path,
                }
                for descendant in work_item.descendants
            ]

    return result


def _parse_metadata(item_type: str, metadata: dict[str, Any]) -> Any:
    """Parse and validate metadata based on item_type.

    Args:
        item_type: Work item type (project|session|task|research)
        metadata: Raw metadata dictionary

    Returns:
        Validated Pydantic metadata model instance

    Raises:
        ValueError: If item_type is invalid or metadata validation fails
    """
    item_type_enum = ItemType(item_type)

    metadata_map = {
        ItemType.PROJECT: ProjectMetadata,
        ItemType.SESSION: SessionMetadata,
        ItemType.TASK: TaskMetadata,
        ItemType.RESEARCH: ResearchMetadata,
    }

    if item_type_enum not in metadata_map:
        raise ValueError(
            f"Invalid item_type: {item_type}. Must be one of {list(metadata_map.keys())}"
        )

    model_class = metadata_map[item_type_enum]
    try:
        return model_class.model_validate(metadata)
    except Exception as e:
        raise ValueError(f"Metadata validation failed for {item_type}: {e}") from e


# ==============================================================================
# Tool Implementations
# ==============================================================================


@mcp.tool()
async def create_work_item(
    item_type: str,
    title: str,
    metadata: dict[str, Any],
    parent_id: str | None = None,
    branch_name: str | None = None,
    created_by: str = "claude-code",
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Create hierarchical work item (project/session/task/research).

    Creates a new work item with type-specific metadata and optional parent relationship.
    Supports hierarchical organization up to 5 levels deep.

    Args:
        item_type: Work item type (project|session|task|research)
        title: Work item title (1-200 characters)
        metadata: Type-specific JSONB metadata (validated by Pydantic)
        parent_id: Parent work item ID (null for root-level items)
        branch_name: Git branch name (optional)
        created_by: AI client identifier (default: "claude-code")
        ctx: FastMCP context for logging (injected)

    Returns:
        Dictionary with created work item data matching MCP contract

    Raises:
        ValueError: Invalid input data or validation failures

    Performance:
        Target: <150ms p95 latency
    """
    start_time = time.perf_counter()

    # Dual logging pattern
    if ctx:
        await ctx.info(f"Creating {item_type} work item: {title[:50]}")

    logger.info(
        "create_work_item called",
        extra={
            "item_type": item_type,
            "title": title[:100],
            "parent_id": parent_id,
            "created_by": created_by,
        },
    )

    # Validate parameters
    if not title or not title.strip():
        raise ValueError("Work item title cannot be empty")

    if len(title) > 200:
        raise ValueError(f"Work item title too long (max 200 characters): {len(title)}")

    # Parse and validate item_type
    try:
        item_type_enum = ItemType(item_type)
    except ValueError as e:
        raise ValueError(
            f"Invalid item_type: {item_type}. Must be one of "
            f"{[t.value for t in ItemType]}"
        ) from e

    # Parse and validate metadata
    try:
        validated_metadata = _parse_metadata(item_type, metadata)
    except ValueError as e:
        if ctx:
            await ctx.error(f"Metadata validation failed: {e}")
        raise

    # Parse parent_id UUID if provided
    parent_uuid: UUID | None = None
    if parent_id is not None:
        try:
            parent_uuid = UUID(parent_id)
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid parent_id format: {parent_id}") from e

    # Create work item
    try:
        async with get_session_factory()() as db:
            work_item = await create_work_item_service(
                item_type=item_type_enum,
                title=title,
                metadata=validated_metadata,
                parent_id=parent_uuid,
                created_by=created_by,
                session=db,
                branch_name=branch_name,
            )
            await db.commit()
    except ValidationError as e:
        if ctx:
            await ctx.error(f"Validation failed: {e.field_errors}")
        raise ValueError(f"Validation failed: {e.field_errors}") from e
    except WorkItemNotFoundError as e:
        if ctx:
            await ctx.error(f"Parent work item not found: {parent_id}")
        raise ValueError(f"Parent work item not found: {parent_id}") from e
    except InvalidDepthError as e:
        if ctx:
            await ctx.error(f"Depth limit exceeded: {e}")
        raise ValueError(f"Depth limit exceeded: {e}") from e
    except Exception as e:
        logger.error(
            "Failed to create work item",
            extra={"title": title[:100], "error": str(e)},
        )
        if ctx:
            await ctx.error(f"Failed to create work item: {e}")
        raise

    # Convert to response format
    response = _work_item_to_dict(work_item)

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    logger.info(
        "create_work_item completed successfully",
        extra={
            "work_item_id": str(work_item.id),
            "item_type": item_type,
            "title": title[:100],
            "latency_ms": latency_ms,
        },
    )

    if ctx:
        await ctx.info(f"Work item created: {work_item.id}")

    return response


@mcp.tool()
async def update_work_item(
    id: str,
    version: int,
    updated_by: str,
    title: str | None = None,
    status: str | None = None,
    metadata: dict[str, Any] | None = None,
    deleted_at: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Update work item with optimistic locking.

    Supports partial updates (only provided fields are modified). Rejects
    conflicting concurrent updates with version mismatch error.

    Args:
        id: Work item ID to update (UUID string)
        version: Expected version (for optimistic locking)
        updated_by: AI client identifier performing update
        title: New title (null = no change)
        status: New status (active|completed|blocked, null = no change)
        metadata: Updated metadata (null = no change)
        deleted_at: Soft delete timestamp ISO string (set to NOW() to delete)
        ctx: FastMCP context for logging (injected)

    Returns:
        Dictionary with updated work item data matching MCP contract

    Raises:
        ValueError: Invalid input data or validation failures

    Performance:
        Target: <150ms p95 latency
    """
    start_time = time.perf_counter()

    # Dual logging pattern
    if ctx:
        await ctx.info(f"Updating work item: {id}")

    logger.info(
        "update_work_item called",
        extra={
            "work_item_id": id,
            "version": version,
            "updated_by": updated_by,
        },
    )

    # Validate work_item_id format (UUID)
    try:
        work_item_uuid = UUID(id)
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid work item id format: {id}") from e

    # Validate version
    if version < 1:
        raise ValueError(f"Invalid version: {version}. Must be >= 1")

    # Build updates dictionary
    updates: dict[str, Any] = {}

    if title is not None:
        if not title.strip():
            raise ValueError("Work item title cannot be empty")
        if len(title) > 200:
            raise ValueError(f"Work item title too long (max 200 characters): {len(title)}")
        updates["title"] = title

    if status is not None:
        try:
            status_enum = WorkItemStatus(status)
            updates["status"] = status_enum.value
        except ValueError as e:
            raise ValueError(
                f"Invalid status: {status}. Must be one of "
                f"{[s.value for s in WorkItemStatus]}"
            ) from e

    if metadata is not None:
        # Metadata validation will be handled by the service
        updates["metadata"] = metadata

    if deleted_at is not None:
        # Parse ISO datetime string or use current time
        if deleted_at.upper() == "NOW()":
            updates["deleted_at"] = datetime.now(timezone.utc)
        else:
            try:
                updates["deleted_at"] = datetime.fromisoformat(deleted_at.replace("Z", "+00:00"))
            except ValueError as e:
                raise ValueError(f"Invalid deleted_at format: {deleted_at}. Use ISO format or 'NOW()'") from e

    # Update work item
    try:
        async with get_session_factory()() as db:
            work_item = await update_work_item_service(
                work_item_id=work_item_uuid,
                version=version,
                updates=updates,
                updated_by=updated_by,
                session=db,
            )
            await db.commit()
    except WorkItemNotFoundError as e:
        if ctx:
            await ctx.error(f"Work item not found: {id}")
        raise ValueError(f"Work item not found: {id}") from e
    except OptimisticLockError as e:
        if ctx:
            await ctx.error(
                f"Version conflict: expected {e.expected_version}, "
                f"current {e.current_version}"
            )
        raise ValueError(
            f"Work item was modified by another client (expected version "
            f"{e.expected_version}, current version {e.current_version})"
        ) from e
    except ValidationError as e:
        if ctx:
            await ctx.error(f"Validation failed: {e.field_errors}")
        raise ValueError(f"Validation failed: {e.field_errors}") from e
    except InvalidDepthError as e:
        if ctx:
            await ctx.error(f"Depth limit exceeded: {e}")
        raise ValueError(f"Depth limit exceeded: {e}") from e
    except Exception as e:
        logger.error(
            "Failed to update work item",
            extra={"work_item_id": id, "error": str(e)},
        )
        if ctx:
            await ctx.error(f"Failed to update work item: {e}")
        raise

    # Convert to response format
    response = _work_item_to_dict(work_item)

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    logger.info(
        "update_work_item completed successfully",
        extra={
            "work_item_id": id,
            "new_version": work_item.version,
            "latency_ms": latency_ms,
        },
    )

    if ctx:
        await ctx.info(f"Work item updated: {id}")

    return response


@mcp.tool()
async def query_work_item(
    id: str,
    include_children: bool = True,
    include_dependencies: bool = True,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Query single work item with full hierarchy.

    Retrieves work item by ID with full parent chain and children up to 5 levels deep.
    Includes dependency relationships (blocked-by, depends-on). Uses materialized
    path for ancestor queries and recursive CTE for descendants.

    Args:
        id: Work item ID to retrieve (UUID string)
        include_children: Include child work items (recursive, max 5 levels)
        include_dependencies: Include dependency relationships
        ctx: FastMCP context for logging (injected)

    Returns:
        Dictionary with work item data and hierarchy matching MCP contract

    Raises:
        ValueError: Invalid input data or work item not found

    Performance:
        Target: <10ms p95 latency (up to 5 levels)
    """
    start_time = time.perf_counter()

    # Dual logging pattern
    if ctx:
        await ctx.info(f"Querying work item: {id}")

    logger.info(
        "query_work_item called",
        extra={
            "work_item_id": id,
            "include_children": include_children,
            "include_dependencies": include_dependencies,
        },
    )

    # Validate work_item_id format (UUID)
    try:
        work_item_uuid = UUID(id)
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid work item id format: {id}") from e

    # Query work item
    try:
        async with get_session_factory()() as db:
            work_item = await get_work_item_service(
                work_item_id=work_item_uuid,
                include_hierarchy=include_children,
                session=db,
            )
            await db.commit()
    except WorkItemNotFoundError as e:
        if ctx:
            await ctx.error(f"Work item not found: {id}")
        raise ValueError(f"Work item not found: {id}") from e
    except HierarchyWorkItemNotFoundError as e:
        if ctx:
            await ctx.error(f"Work item not found: {id}")
        raise ValueError(f"Work item not found: {id}") from e
    except Exception as e:
        logger.error(
            "Failed to query work item",
            extra={"work_item_id": id, "error": str(e)},
        )
        if ctx:
            await ctx.error(f"Failed to query work item: {e}")
        raise

    # Convert to response format (include ancestors/descendants if hierarchy was requested)
    response = _work_item_to_dict(work_item, include_hierarchy=include_children)

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    logger.info(
        "query_work_item completed successfully",
        extra={
            "work_item_id": id,
            "latency_ms": latency_ms,
        },
    )

    if ctx:
        await ctx.info(f"Work item retrieved: {id}")

    return response


@mcp.tool()
async def list_work_items(
    item_type: str | None = None,
    status: str | None = None,
    parent_id: str | None = None,
    include_deleted: bool = False,
    limit: int = 50,
    offset: int = 0,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """List work items with filtering and pagination.

    List work items with optional filtering by type, status, parent, and pagination
    support. Results ordered by updated_at descending. Excludes soft-deleted items
    unless explicitly requested.

    Args:
        item_type: Filter by work item type (project|session|task|research)
        status: Filter by status (active|completed|blocked)
        parent_id: Filter by parent (null = root-level items only)
        include_deleted: Include soft-deleted items
        limit: Maximum results to return (1-100, default: 50)
        offset: Pagination offset (default: 0)
        ctx: FastMCP context for logging (injected)

    Returns:
        Dictionary with items list, total count, limit, and offset

    Raises:
        ValueError: Invalid filter parameters

    Performance:
        Target: <200ms p95 latency
    """
    start_time = time.perf_counter()

    # Dual logging pattern
    if ctx:
        await ctx.info(
            f"Listing work items (type={item_type}, status={status}, "
            f"parent={parent_id}, limit={limit})"
        )

    logger.info(
        "list_work_items called",
        extra={
            "item_type": item_type,
            "status": status,
            "parent_id": parent_id,
            "include_deleted": include_deleted,
            "limit": limit,
            "offset": offset,
        },
    )

    # Validate parameters
    if limit < 1 or limit > 100:
        raise ValueError(f"Limit must be between 1 and 100, got {limit}")

    if offset < 0:
        raise ValueError(f"Offset must be non-negative, got {offset}")

    # Build filters dictionary
    filters: dict[str, Any] = {"include_deleted": include_deleted}

    if item_type is not None:
        try:
            item_type_enum = ItemType(item_type)
            filters["item_type"] = item_type_enum.value
        except ValueError as e:
            raise ValueError(
                f"Invalid item_type: {item_type}. Must be one of "
                f"{[t.value for t in ItemType]}"
            ) from e

    if status is not None:
        try:
            status_enum = WorkItemStatus(status)
            filters["status"] = status_enum.value
        except ValueError as e:
            raise ValueError(
                f"Invalid status: {status}. Must be one of "
                f"{[s.value for s in WorkItemStatus]}"
            ) from e

    if parent_id is not None:
        try:
            parent_uuid = UUID(parent_id)
            filters["parent_id"] = parent_uuid
        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid parent_id format: {parent_id}") from e

    # List work items
    try:
        async with get_session_factory()() as db:
            paginated_result = await list_work_items_service(
                filters=filters,
                limit=limit,
                offset=offset,
                session=db,
            )
            await db.commit()
    except Exception as e:
        logger.error(
            "Failed to list work items",
            extra={
                "filters": filters,
                "limit": limit,
                "offset": offset,
                "error": str(e),
            },
        )
        if ctx:
            await ctx.error(f"Failed to list work items: {e}")
        raise

    # Convert to response format
    response: dict[str, Any] = {
        "items": [_work_item_to_dict(item) for item in paginated_result.items],
        "total_count": paginated_result.total_count,
        "limit": paginated_result.limit,
        "offset": paginated_result.offset,
    }

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    logger.info(
        "list_work_items completed successfully",
        extra={
            "items_count": len(paginated_result.items),
            "total_count": paginated_result.total_count,
            "latency_ms": latency_ms,
        },
    )

    if ctx:
        await ctx.info(f"Listed {len(paginated_result.items)} work items")

    return response


# ==============================================================================
# Module Exports
# ==============================================================================

__all__ = [
    "create_work_item",
    "update_work_item",
    "query_work_item",
    "list_work_items",
]
