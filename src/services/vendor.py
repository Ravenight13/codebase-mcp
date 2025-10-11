"""Vendor extractor status tracking service.

Provides high-performance queries and updates for 45+ commission vendor extractors
with <1ms lookup times and optimistic locking support.

Constitutional Compliance:
- Principle IV: Performance (<1ms vendor queries via unique index on name)
- Principle V: Production quality (error handling, optimistic locking, audit trail)
- Principle VIII: Type safety (100% type annotations, mypy --strict)

Key Features:
- Vendor lookup by name with <1ms performance (unique index)
- Filter vendors by operational status (operational|broken)
- Update vendor status with optimistic locking (version checking)
- Pydantic validation for all JSONB metadata
- Comprehensive error handling and structured logging

Performance Targets:
- <1ms for single vendor query by name (FR-002)
- <5ms for vendor status updates with validation
- <10ms for filtered vendor list queries
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.mcp.mcp_logging import get_logger
from src.models.tracking import VendorExtractor
from src.services.locking import OptimisticLockError, update_with_version_check
from src.services.validation import ValidationError, validate_create_vendor_metadata, validate_vendor_name

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
    from pydantic_schemas import VendorMetadata, VendorStatus  # type: ignore
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


class VendorNotFoundError(Exception):
    """Raised when vendor lookup fails.

    HTTP Mapping:
        404 Not Found - Vendor does not exist
    """

    def __init__(self, *, vendor_name: str | None = None, vendor_id: UUID | None = None) -> None:
        """Initialize VendorNotFoundError.

        Args:
            vendor_name: Vendor name that was not found (optional)
            vendor_id: Vendor UUID that was not found (optional)
        """
        self.vendor_name = vendor_name
        self.vendor_id = vendor_id

        if vendor_name:
            message = f"Vendor not found: {vendor_name}"
        elif vendor_id:
            message = f"Vendor not found: {vendor_id}"
        else:
            message = "Vendor not found"

        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for MCP error responses."""
        return {
            "error_type": "VendorNotFoundError",
            "vendor_name": self.vendor_name,
            "vendor_id": str(self.vendor_id) if self.vendor_id else None,
            "http_status": 404,
        }


class VendorAlreadyExistsError(Exception):
    """Raised when attempting to create a vendor that already exists.

    HTTP Mapping:
        409 Conflict - Vendor name conflicts with existing vendor
    """

    def __init__(self, vendor_name: str, existing_name: str | None = None) -> None:
        """Initialize VendorAlreadyExistsError.

        Args:
            vendor_name: Vendor name that was attempted to be created
            existing_name: Existing vendor name that conflicts (for case-insensitive matches)
        """
        self.vendor_name = vendor_name
        self.existing_name = existing_name or vendor_name

        if existing_name and existing_name != vendor_name:
            message = f"Vendor already exists: {vendor_name} (conflicts with existing '{existing_name}')"
        else:
            message = f"Vendor already exists: {vendor_name}"

        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for MCP error responses."""
        return {
            "error_type": "VendorAlreadyExistsError",
            "vendor_name": self.vendor_name,
            "existing_name": self.existing_name,
            "http_status": 409,
        }


# ==============================================================================
# Service Functions
# ==============================================================================


async def get_vendor_by_name(
    name: str,
    session: AsyncSession,
) -> VendorExtractor:
    """Retrieve vendor by unique name.

    Uses unique index on vendor_extractors.name for <1ms performance.

    Args:
        name: Vendor name (unique identifier)
        session: Active async database session

    Returns:
        VendorExtractor instance with full metadata

    Raises:
        VendorNotFoundError: Vendor with given name does not exist

    Performance:
        <1ms for single vendor query (FR-002)

    Example:
        >>> async with session_factory() as session:
        ...     vendor = await get_vendor_by_name("vendor_abc", session)
        ...     print(f"Status: {vendor.status}")
        ...     print(f"Version: {vendor.extractor_version}")
    """
    logger.debug(
        f"Querying vendor by name: {name}",
        extra={
            "context": {
                "vendor_name": name,
            }
        },
    )

    result = await session.execute(
        select(VendorExtractor).where(VendorExtractor.name == name)
    )
    vendor = result.scalar_one_or_none()

    if vendor is None:
        logger.warning(
            f"Vendor not found: {name}",
            extra={
                "context": {
                    "vendor_name": name,
                }
            },
        )
        raise VendorNotFoundError(vendor_name=name)

    logger.debug(
        f"Vendor found: {name}",
        extra={
            "context": {
                "vendor_id": str(vendor.id),
                "vendor_name": name,
                "status": vendor.status,
                "version": vendor.version,
            }
        },
    )

    return vendor


async def get_vendor_by_id(
    vendor_id: UUID,
    session: AsyncSession,
) -> VendorExtractor:
    """Retrieve vendor by UUID.

    Args:
        vendor_id: Vendor UUID
        session: Active async database session

    Returns:
        VendorExtractor instance with full metadata

    Raises:
        VendorNotFoundError: Vendor with given UUID does not exist

    Performance:
        <1ms for primary key lookup

    Example:
        >>> async with session_factory() as session:
        ...     vendor = await get_vendor_by_id(UUID("..."), session)
        ...     print(f"Name: {vendor.name}")
    """
    logger.debug(
        f"Querying vendor by ID: {vendor_id}",
        extra={
            "context": {
                "vendor_id": str(vendor_id),
            }
        },
    )

    result = await session.execute(
        select(VendorExtractor).where(VendorExtractor.id == vendor_id)
    )
    vendor = result.scalar_one_or_none()

    if vendor is None:
        logger.warning(
            f"Vendor not found: {vendor_id}",
            extra={
                "context": {
                    "vendor_id": str(vendor_id),
                }
            },
        )
        raise VendorNotFoundError(vendor_id=vendor_id)

    logger.debug(
        f"Vendor found: {vendor.name}",
        extra={
            "context": {
                "vendor_id": str(vendor_id),
                "vendor_name": vendor.name,
                "status": vendor.status,
            }
        },
    )

    return vendor


async def get_all_vendors(
    status_filter: VendorStatus | None = None,
    session: AsyncSession | None = None,
) -> list[VendorExtractor]:
    """Retrieve all vendors with optional status filter.

    Args:
        status_filter: Filter by operational status (operational|broken), None for all
        session: Active async database session

    Returns:
        List of VendorExtractor instances

    Performance:
        <10ms for filtered queries (indexed status column)

    Example:
        >>> async with session_factory() as session:
        ...     # Get all operational vendors
        ...     operational = await get_all_vendors(VendorStatus.OPERATIONAL, session)
        ...     print(f"Operational vendors: {len(operational)}")
        ...
        ...     # Get all vendors (no filter)
        ...     all_vendors = await get_all_vendors(session=session)
        ...     print(f"Total vendors: {len(all_vendors)}")
    """
    if session is None:
        raise ValueError("session parameter is required")

    logger.debug(
        "Querying all vendors",
        extra={
            "context": {
                "status_filter": status_filter.value if status_filter else None,
            }
        },
    )

    # Build query with optional status filter
    query = select(VendorExtractor)
    if status_filter is not None:
        query = query.where(VendorExtractor.status == status_filter.value)

    query = query.order_by(VendorExtractor.name)

    result = await session.execute(query)
    vendors = list(result.scalars().all())

    logger.debug(
        f"Found {len(vendors)} vendors",
        extra={
            "context": {
                "status_filter": status_filter.value if status_filter else None,
                "vendor_count": len(vendors),
            }
        },
    )

    return vendors


async def update_vendor_status(
    name: str,
    version: int,
    updates: dict[str, Any],
    session: AsyncSession,
) -> VendorExtractor:
    """Update vendor status and metadata with optimistic locking.

    Validates metadata updates via Pydantic before applying to database.
    Uses optimistic locking to prevent concurrent update conflicts.

    Args:
        name: Vendor name (unique identifier)
        version: Current version for optimistic locking
        updates: Dictionary of field updates (status, metadata fields)
        session: Active async database session

    Returns:
        Updated VendorExtractor with incremented version

    Raises:
        VendorNotFoundError: Vendor with given name does not exist
        OptimisticLockError: Version mismatch (concurrent update detected)
        ValidationError: Invalid metadata updates (Pydantic validation failed)

    Supported Update Fields:
        - status: VendorStatus (operational|broken)
        - test_results: dict[str, int] (passing, total, skipped)
        - format_support: dict[str, bool] (excel, csv, pdf, ocr)
        - extractor_version: str (semantic version)
        - manifest_compliant: bool

    Performance:
        <5ms for updates with validation

    Example:
        >>> async with session_factory() as session:
        ...     # Update vendor status to broken
        ...     updated = await update_vendor_status(
        ...         name="vendor_abc",
        ...         version=5,
        ...         updates={
        ...             "status": "broken",
        ...             "test_results": {"passing": 40, "total": 50, "skipped": 5}
        ...         },
        ...         session=session
        ...     )
        ...     assert updated.version == 6
        ...     await session.commit()
    """
    logger.info(
        f"Updating vendor status: {name}",
        extra={
            "context": {
                "vendor_name": name,
                "version": version,
                "update_fields": list(updates.keys()),
            }
        },
    )

    # Fetch vendor by name
    vendor = await get_vendor_by_name(name, session)

    # Validate metadata updates if present
    if any(key in updates for key in ["test_results", "format_support", "extractor_version", "manifest_compliant"]):
        # Merge updates with existing metadata
        current_metadata = vendor.metadata_ if isinstance(vendor.metadata_, dict) else {}
        updated_metadata = {**current_metadata}

        # Map update keys to metadata fields
        metadata_field_map = {
            "test_results": "test_results",
            "format_support": "format_support",
            "extractor_version": "extractor_version",
            "manifest_compliant": "manifest_compliant",
        }

        for update_key, metadata_key in metadata_field_map.items():
            if update_key in updates:
                updated_metadata[metadata_key] = updates[update_key]

        # Validate merged metadata with Pydantic
        try:
            validated_metadata = validate_vendor_metadata(updated_metadata)
            # Convert Pydantic model to dict for database storage
            updates["metadata_"] = validated_metadata.model_dump()
            # Remove individual metadata fields from updates (they're now in metadata_)
            for key in metadata_field_map.keys():
                updates.pop(key, None)
        except ValidationError as e:
            logger.warning(
                f"Vendor metadata validation failed for {name}",
                extra={
                    "context": {
                        "vendor_name": name,
                        "field_errors": e.field_errors,
                    }
                },
            )
            raise

    # Apply updates with optimistic locking
    try:
        updated_vendor = await update_with_version_check(
            entity=vendor,
            updates=updates,
            expected_version=version,
            session=session,
        )

        logger.info(
            f"Vendor status updated: {name}",
            extra={
                "context": {
                    "vendor_id": str(updated_vendor.id),
                    "vendor_name": name,
                    "old_version": version,
                    "new_version": updated_vendor.version,
                    "updated_fields": list(updates.keys()),
                }
            },
        )

        return updated_vendor

    except OptimisticLockError as e:
        logger.error(
            f"Optimistic lock error updating vendor {name}",
            extra={
                "context": {
                    "vendor_name": name,
                    "expected_version": version,
                    "current_version": e.current_version,
                }
            },
        )
        raise


async def create_vendor(
    name: str,
    initial_metadata: dict[str, Any] | None,
    created_by: str,
    session: AsyncSession,
) -> VendorExtractor:
    """Create new vendor extractor record.

    Creates a vendor with initial "broken" status, version 1, and
    extractor_version "0.0.0". Enforces case-insensitive uniqueness
    via database functional unique index on LOWER(name).

    Args:
        name: Vendor name (pre-validated by tool layer)
        initial_metadata: Optional metadata dict (pre-validated by tool layer)
        created_by: AI client identifier
        session: Active async database session

    Returns:
        Created VendorExtractor instance with initial values

    Raises:
        VendorAlreadyExistsError: Vendor with name already exists (case-insensitive)
            Includes existing vendor name with actual casing for clarity
        IntegrityError: Database constraint violation (re-raised if not uniqueness)

    Performance:
        <5ms for single INSERT with functional unique index check

    Example:
        >>> async with session_factory() as session:
        ...     vendor = await create_vendor(
        ...         name="NewCorp",
        ...         initial_metadata={"scaffolder_version": "1.0"},
        ...         created_by="claude-code",
        ...         session=session
        ...     )
        ...     assert vendor.status == "broken"
        ...     assert vendor.version == 1
        ...     await session.commit()
    """
    # Validate inputs before database operations
    # validate_vendor_name and validate_create_vendor_metadata raise ValueError on failure
    validate_vendor_name(name)

    if initial_metadata:
        initial_metadata = validate_create_vendor_metadata(initial_metadata)

    logger.info(
        f"Creating vendor: {name}",
        extra={
            "context": {
                "vendor_name": name,
                "has_metadata": initial_metadata is not None,
                "created_by": created_by,
            }
        },
    )

    vendor = VendorExtractor(
        name=name,
        status="broken",
        extractor_version="0.0.0",
        metadata_=initial_metadata or {},
        created_by=created_by,
    )

    session.add(vendor)

    try:
        await session.flush()  # Trigger unique index check
    except IntegrityError as e:
        # Check if this is a unique constraint violation on vendor name (case-insensitive)
        error_str = str(e).lower()
        if "idx_vendor_name_lower" in error_str or "unique constraint" in error_str:
            # Rollback the session to allow subsequent queries
            await session.rollback()

            # Query existing vendor to get actual casing
            result = await session.execute(
                select(VendorExtractor).where(
                    func.lower(VendorExtractor.name) == func.lower(name)
                )
            )
            existing_vendor = result.scalar_one_or_none()
            existing_name = existing_vendor.name if existing_vendor else name

            logger.warning(
                f"Vendor already exists: {name} (conflicts with '{existing_name}')",
                extra={
                    "context": {
                        "vendor_name": name,
                        "existing_name": existing_name,
                    }
                },
            )

            raise VendorAlreadyExistsError(
                vendor_name=name, existing_name=existing_name
            ) from e
        raise

    logger.info(
        f"Vendor created successfully: {name}",
        extra={
            "context": {
                "vendor_id": str(vendor.id),
                "vendor_name": name,
                "status": vendor.status,
                "version": vendor.version,
            }
        },
    )

    return vendor


# ==============================================================================
# Public API
# ==============================================================================

__all__ = [
    "VendorNotFoundError",
    "VendorAlreadyExistsError",
    "get_vendor_by_name",
    "get_vendor_by_id",
    "get_all_vendors",
    "update_vendor_status",
    "create_vendor",
]
