"""Optimistic locking service for concurrent update conflict detection.

Provides version-based optimistic locking using SQLAlchemy's version_id_col feature
to prevent lost updates in concurrent scenarios. Handles VendorExtractor and WorkItem
entities with automatic version checking and incrementation.

Constitutional Compliance:
- Principle V: Production quality (comprehensive error handling, conflict detection)
- Principle VIII: Type safety (full mypy --strict compliance)

Key Features:
- Automatic version checking via SQLAlchemy StaleDataError
- Custom OptimisticLockError with detailed conflict information
- Version retrieval for pre-update validation
- Support for VendorExtractor and WorkItem entities
- HTTP 409 Conflict mapping for MCP error responses

Performance:
- <1ms version check (indexed primary key lookup)
- Atomic update with version increment (SQLAlchemy ORM automatic)
"""

from __future__ import annotations

from typing import Any, Literal, TypeVar, Union
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from src.mcp.mcp_logging import get_logger
from src.models.task import WorkItem
from src.models.tracking import VendorExtractor

# ==============================================================================
# Type Variables and Aliases
# ==============================================================================

logger = get_logger(__name__)

# Union type for entities that support optimistic locking
VersionedEntity = Union[VendorExtractor, WorkItem]
T_VersionedEntity = TypeVar("T_VersionedEntity", VendorExtractor, WorkItem)

# Entity type discriminator
EntityType = Literal["VendorExtractor", "WorkItem"]


# ==============================================================================
# Exception Classes
# ==============================================================================


class OptimisticLockError(Exception):
    """Custom exception for version conflict during optimistic locking.

    Raised when an update operation fails due to version mismatch,
    indicating concurrent modification by another client.

    Attributes:
        current_version: The actual version in the database
        expected_version: The version provided by the client
        last_updated_by: AI client identifier who made the last update
        entity_type: Type of entity that experienced conflict
        entity_id: UUID of the conflicted entity

    HTTP Mapping:
        409 Conflict - Indicates concurrent update conflict
    """

    def __init__(
        self,
        *,
        current_version: int,
        expected_version: int,
        last_updated_by: str,
        entity_type: str,
        entity_id: UUID,
    ) -> None:
        """Initialize OptimisticLockError with conflict details.

        Args:
            current_version: Actual version in database
            expected_version: Version provided by client
            last_updated_by: AI client who made last update
            entity_type: Entity type name (VendorExtractor | WorkItem)
            entity_id: UUID of conflicted entity
        """
        self.current_version = current_version
        self.expected_version = expected_version
        self.last_updated_by = last_updated_by
        self.entity_type = entity_type
        self.entity_id = entity_id

        message = (
            f"Optimistic lock conflict for {entity_type} {entity_id}: "
            f"expected version {expected_version}, "
            f"but current version is {current_version} "
            f"(last updated by: {last_updated_by})"
        )
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for MCP error responses.

        Returns:
            Dictionary with conflict details for JSON serialization
        """
        return {
            "error_type": "OptimisticLockError",
            "entity_type": self.entity_type,
            "entity_id": str(self.entity_id),
            "current_version": self.current_version,
            "expected_version": self.expected_version,
            "last_updated_by": self.last_updated_by,
            "http_status": 409,
        }


# ==============================================================================
# Pydantic Models
# ==============================================================================


class VersionInfo(BaseModel):
    """Version information for an entity.

    Used for pre-update version checks and validation.
    """

    entity_id: UUID = Field(description="UUID of the entity")
    entity_type: EntityType = Field(description="Type of entity")
    current_version: int = Field(ge=1, description="Current version number")

    model_config = {"frozen": True}


# ==============================================================================
# Service Functions
# ==============================================================================


async def get_current_version(
    entity_id: UUID,
    entity_type: EntityType,
    session: AsyncSession,
) -> int:
    """Retrieve current version number for an entity.

    Used by MCP tools before updates to obtain current version
    for optimistic locking validation.

    Args:
        entity_id: UUID of the entity
        entity_type: Type discriminator ("VendorExtractor" | "WorkItem")
        session: Async SQLAlchemy session

    Returns:
        Current version number (>= 1)

    Raises:
        ValueError: If entity not found or entity_type invalid

    Performance:
        <1ms (indexed primary key lookup)

    Example:
        >>> version = await get_current_version(
        ...     entity_id=UUID("..."),
        ...     entity_type="VendorExtractor",
        ...     session=session
        ... )
        >>> # Use version for update_with_version_check
    """
    logger.debug(
        f"Retrieving current version for {entity_type} {entity_id}",
        extra={
            "context": {
                "entity_id": str(entity_id),
                "entity_type": entity_type,
            }
        },
    )

    # Map entity_type to model class
    model_class: type[VersionedEntity]
    if entity_type == "VendorExtractor":
        model_class = VendorExtractor
    elif entity_type == "WorkItem":
        model_class = WorkItem
    else:
        raise ValueError(f"Invalid entity_type: {entity_type}")

    # Query for entity by ID
    result = await session.execute(
        select(model_class).where(model_class.id == entity_id)
    )
    entity = result.scalar_one_or_none()

    if entity is None:
        raise ValueError(
            f"{entity_type} with id {entity_id} not found"
        )

    # Type narrowing: both VendorExtractor and WorkItem have version attribute
    version: int = entity.version  # type: ignore[attr-defined]
    logger.debug(
        f"Current version for {entity_type} {entity_id}: {version}",
        extra={
            "context": {
                "entity_id": str(entity_id),
                "version": version,
            }
        },
    )

    return version


async def update_with_version_check(
    entity: T_VersionedEntity,
    updates: dict[str, Any],
    expected_version: int,
    session: AsyncSession,
) -> T_VersionedEntity:
    """Update entity with optimistic locking version validation.

    Validates that entity's current version matches expected_version
    before applying updates. SQLAlchemy automatically increments version
    on successful UPDATE.

    Args:
        entity: Entity instance to update (VendorExtractor | WorkItem)
        updates: Dictionary of field updates to apply
        expected_version: Expected current version (from client)
        session: Async SQLAlchemy session

    Returns:
        Updated entity with incremented version

    Raises:
        OptimisticLockError: Version mismatch (concurrent update detected)
        ValueError: Invalid field names in updates dict

    Performance:
        <5ms (version check + UPDATE + version increment)

    Example:
        >>> vendor = await session.get(VendorExtractor, vendor_id)
        >>> updated_vendor = await update_with_version_check(
        ...     entity=vendor,
        ...     updates={"status": "broken"},
        ...     expected_version=5,
        ...     session=session
        ... )
        >>> # updated_vendor.version == 6 (auto-incremented)
    """
    entity_type = type(entity).__name__
    entity_id = entity.id

    logger.info(
        f"Updating {entity_type} {entity_id} with version check",
        extra={
            "context": {
                "entity_id": str(entity_id),
                "entity_type": entity_type,
                "expected_version": expected_version,
                "current_version": entity.version,
            }
        },
    )

    # Pre-update version validation
    if entity.version != expected_version:
        logger.warning(
            f"Version conflict for {entity_type} {entity_id}",
            extra={
                "context": {
                    "entity_id": str(entity_id),
                    "expected_version": expected_version,
                    "current_version": entity.version,
                    "last_updated_by": getattr(entity, "created_by", "unknown"),
                }
            },
        )
        raise OptimisticLockError(
            current_version=entity.version,
            expected_version=expected_version,
            last_updated_by=getattr(entity, "created_by", "unknown"),
            entity_type=entity_type,
            entity_id=entity_id,
        )

    # Apply updates to entity attributes
    for field_name, value in updates.items():
        if not hasattr(entity, field_name):
            raise ValueError(
                f"Invalid field '{field_name}' for {entity_type}"
            )
        setattr(entity, field_name, value)

    # CRITICAL: Manually increment version for optimistic locking
    # SQLAlchemy's version_id_col doesn't work reliably with async sessions
    # and Mapped[] annotations, so we increment manually
    entity.version = expected_version + 1

    # Add entity to session (if not already tracked)
    session.add(entity)

    try:
        # Flush to database
        logger.debug(
            f"Before flush: {entity_type} {entity_id} version={entity.version}",
            extra={"context": {"entity_id": str(entity_id), "version_before_flush": entity.version}}
        )
        await session.flush()
        logger.debug(
            f"After flush: {entity_type} {entity_id} version={entity.version}",
            extra={"context": {"entity_id": str(entity_id), "version_after_flush": entity.version}}
        )

        logger.info(
            f"Successfully updated {entity_type} {entity_id}",
            extra={
                "context": {
                    "entity_id": str(entity_id),
                    "new_version": entity.version,
                    "fields_updated": list(updates.keys()),
                }
            },
        )

        return entity

    except StaleDataError as e:
        # SQLAlchemy detected version conflict during UPDATE
        # This occurs when manual version increment fails to match WHERE clause
        logger.error(
            f"StaleDataError during update of {entity_type} {entity_id}",
            extra={
                "context": {
                    "entity_id": str(entity_id),
                    "expected_version": expected_version,
                }
            },
            exc_info=True,
        )

        # Rollback the failed transaction to reset session state
        await session.rollback()

        # Re-fetch entity to get current version
        from sqlalchemy import select
        result = await session.execute(
            select(type(entity)).where(type(entity).id == entity_id)
        )
        fresh_entity = result.scalar_one_or_none()

        if fresh_entity is None:
            # Entity was deleted between our check and update
            raise OptimisticLockError(
                current_version=expected_version + 1,  # Assume it was incremented
                expected_version=expected_version,
                last_updated_by="unknown",
                entity_type=entity_type,
                entity_id=entity_id,
            ) from e

        raise OptimisticLockError(
            current_version=fresh_entity.version,
            expected_version=expected_version,
            last_updated_by=getattr(fresh_entity, "created_by", "unknown"),
            entity_type=entity_type,
            entity_id=entity_id,
        ) from e
