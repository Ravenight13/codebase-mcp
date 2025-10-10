"""MCP tool handlers for vendor tracking and deployment recording.

Provides vendor operational status queries, status updates with optimistic locking,
and deployment event recording with vendor/work item relationships.

Constitutional Compliance:
- Principle III: Protocol Compliance (MCP-compliant responses)
- Principle IV: Performance (<1ms vendor queries, <200ms deployment recording)
- Principle V: Production Quality (comprehensive validation, error handling)
- Principle VIII: Type Safety (mypy --strict compliance)
- Principle X: Git micro-commits (deployment audit trail)
- Principle XI: FastMCP Foundation (FastMCP decorators, Context injection)
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from typing import Any
from uuid import UUID

from fastmcp import Context

from src.database import get_session_factory
from src.mcp.server_fastmcp import mcp
from src.services.deployment import (
    DeploymentNotFoundError,
    InvalidDeploymentDataError,
    create_deployment,
)
from src.services.locking import OptimisticLockError
from src.services.validation import ValidationError
from src.services.vendor import (
    VendorNotFoundError,
    get_vendor_by_name,
    update_vendor_status as update_vendor_service,
)

# ==============================================================================
# Import Pydantic Schemas from Contracts
# ==============================================================================

import sys
from pathlib import Path

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
        DeploymentMetadata,
        VendorMetadata,
        VendorStatus,
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

# Commit hash validation regex (40 lowercase hex characters)
COMMIT_HASH_PATTERN = re.compile(r"^[a-f0-9]{40}$")

# ==============================================================================
# Helper Functions
# ==============================================================================


def _vendor_to_dict(vendor: Any) -> dict[str, Any]:
    """Convert VendorExtractor model to MCP contract dictionary.

    Args:
        vendor: VendorExtractor SQLAlchemy model instance

    Returns:
        Dictionary matching MCP contract VendorExtractor definition
    """
    return {
        "id": str(vendor.id),
        "version": vendor.version,
        "name": vendor.name,
        "status": vendor.status,
        "extractor_version": vendor.extractor_version,
        "metadata": vendor.metadata_,
        "created_at": vendor.created_at.isoformat(),
        "updated_at": vendor.updated_at.isoformat(),
        "created_by": vendor.created_by,
    }


def _deployment_to_dict(deployment: Any, vendor_ids: list[UUID], work_item_ids: list[UUID]) -> dict[str, Any]:
    """Convert DeploymentEvent model to MCP contract dictionary.

    Args:
        deployment: DeploymentEvent SQLAlchemy model instance
        vendor_ids: List of vendor UUIDs affected by deployment
        work_item_ids: List of work item UUIDs included in deployment

    Returns:
        Dictionary matching MCP contract DeploymentEvent definition
    """
    return {
        "id": str(deployment.id),
        "deployed_at": deployment.deployed_at.isoformat(),
        "commit_hash": deployment.commit_hash,
        "metadata": deployment.metadata_,
        "vendor_ids": [str(vid) for vid in vendor_ids],
        "work_item_ids": [str(wid) for wid in work_item_ids],
        "created_at": deployment.created_at.isoformat(),
        "created_by": deployment.created_by,
    }


def _validate_commit_hash(commit_hash: str) -> None:
    """Validate git commit hash format.

    Args:
        commit_hash: Git commit hash to validate

    Raises:
        ValueError: If commit hash is not 40 lowercase hex characters
    """
    if not COMMIT_HASH_PATTERN.match(commit_hash):
        raise ValueError(
            f"Invalid commit hash format: {commit_hash}. "
            "Must be 40 lowercase hexadecimal characters."
        )


# ==============================================================================
# Tool Implementations
# ==============================================================================


@mcp.tool()
async def record_deployment(
    deployed_at: datetime,
    metadata: dict[str, Any],
    vendor_ids: list[str] | None = None,
    work_item_ids: list[str] | None = None,
    created_by: str = "claude-code",
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Record deployment event with relationships.

    Creates a deployment event with PR details, test results, constitutional
    compliance status, and relationships to affected vendors and work items.
    Creates many-to-many links in junction tables.

    Args:
        deployed_at: Deployment timestamp (UTC)
        metadata: Deployment metadata dict (PR details, commit hash, test results)
        vendor_ids: List of vendor UUID strings affected by deployment (optional)
        work_item_ids: List of work item UUID strings included in deployment (optional)
        created_by: AI client identifier (default: "claude-code")
        ctx: FastMCP context for logging (injected)

    Returns:
        Dictionary with deployment event data matching MCP contract

    Raises:
        ValueError: If input validation fails or invalid metadata

    Performance:
        Target: <200ms p95 latency

    Requirements:
        FR-005 to FR-007 (deployment tracking with relationships)
    """
    start_time = time.perf_counter()

    # Normalize empty lists
    vendor_ids = vendor_ids or []
    work_item_ids = work_item_ids or []

    # Dual logging pattern
    if ctx:
        await ctx.info(
            f"Recording deployment at {deployed_at.isoformat()} with "
            f"{len(vendor_ids)} vendors and {len(work_item_ids)} work items"
        )

    logger.info(
        "record_deployment called",
        extra={
            "deployed_at": deployed_at.isoformat(),
            "vendor_count": len(vendor_ids),
            "work_item_count": len(work_item_ids),
            "created_by": created_by,
        },
    )

    # Validate metadata and convert to Pydantic model
    try:
        deployment_metadata = DeploymentMetadata.model_validate(metadata)
    except Exception as e:
        error_msg = f"Invalid deployment metadata: {e}"
        if ctx:
            await ctx.error(error_msg)
        logger.error(
            "Deployment metadata validation failed",
            extra={"error": str(e), "metadata_keys": list(metadata.keys())},
        )
        raise ValueError(error_msg) from e

    # Validate commit hash format
    try:
        _validate_commit_hash(deployment_metadata.commit_hash)
    except ValueError as e:
        if ctx:
            await ctx.error(str(e))
        logger.error(
            "Commit hash validation failed",
            extra={"commit_hash": deployment_metadata.commit_hash},
        )
        raise

    # Convert string UUIDs to UUID objects
    try:
        vendor_uuids = [UUID(vid) for vid in vendor_ids]
        work_item_uuids = [UUID(wid) for wid in work_item_ids]
    except (ValueError, AttributeError) as e:
        error_msg = f"Invalid UUID format in vendor_ids or work_item_ids: {e}"
        if ctx:
            await ctx.error(error_msg)
        logger.error(
            "UUID conversion failed",
            extra={"error": str(e), "vendor_ids": vendor_ids, "work_item_ids": work_item_ids},
        )
        raise ValueError(error_msg) from e

    # Create deployment event
    try:
        async with get_session_factory()() as db:
            deployment = await create_deployment(
                deployed_at=deployed_at,
                metadata=deployment_metadata,
                vendor_ids=vendor_uuids,
                work_item_ids=work_item_uuids,
                created_by=created_by,
                session=db,
            )
            await db.commit()
    except ValidationError as e:
        error_msg = f"Deployment metadata validation failed: {e.field_errors}"
        if ctx:
            await ctx.error(error_msg)
        logger.error(
            "Deployment validation failed",
            extra={"field_errors": e.field_errors},
        )
        raise ValueError(error_msg) from e
    except InvalidDeploymentDataError as e:
        if ctx:
            await ctx.error(str(e))
        logger.error(
            "Invalid deployment data",
            extra={"error": str(e)},
        )
        raise ValueError(str(e)) from e
    except Exception as e:
        logger.error(
            "Failed to create deployment",
            extra={
                "deployed_at": deployed_at.isoformat(),
                "error": str(e),
            },
        )
        if ctx:
            await ctx.error(f"Failed to create deployment: {e}")
        raise

    # Convert to response format
    response = _deployment_to_dict(deployment, vendor_uuids, work_item_uuids)

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    logger.info(
        "record_deployment completed successfully",
        extra={
            "deployment_id": str(deployment.id),
            "pr_number": deployment_metadata.pr_number,
            "latency_ms": latency_ms,
        },
    )

    if ctx:
        await ctx.info(f"Deployment recorded: {deployment.id}")

    return response


@mcp.tool()
async def query_vendor_status(
    name: str,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Query vendor operational status.

    Queries vendor extractor operational status, test results, format support
    flags, and version information. Optimized for <1ms response time using
    unique index on vendor name.

    Args:
        name: Unique vendor name
        ctx: FastMCP context for logging (injected)

    Returns:
        Dictionary with vendor status data matching MCP contract

    Raises:
        ValueError: If vendor not found

    Performance:
        Target: <1ms p95 latency (single vendor query)

    Requirements:
        FR-001 to FR-003 (vendor tracking with <1ms query)
    """
    start_time = time.perf_counter()

    # Dual logging pattern
    if ctx:
        await ctx.info(f"Querying vendor status: {name}")

    logger.info(
        "query_vendor_status called",
        extra={"vendor_name": name},
    )

    # Validate vendor name
    if not name or not name.strip():
        error_msg = "Vendor name cannot be empty"
        if ctx:
            await ctx.error(error_msg)
        raise ValueError(error_msg)

    # Query vendor by name
    try:
        async with get_session_factory()() as db:
            vendor = await get_vendor_by_name(name, db)
            await db.commit()
    except VendorNotFoundError as e:
        error_msg = f"Vendor not found: {name}"
        if ctx:
            await ctx.error(error_msg)
        logger.warning(
            "Vendor not found",
            extra={"vendor_name": name},
        )
        raise ValueError(error_msg) from e
    except Exception as e:
        logger.error(
            "Failed to query vendor",
            extra={"vendor_name": name, "error": str(e)},
        )
        if ctx:
            await ctx.error(f"Failed to query vendor: {e}")
        raise

    # Convert to response format
    response = _vendor_to_dict(vendor)

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    logger.info(
        "query_vendor_status completed successfully",
        extra={
            "vendor_name": name,
            "vendor_status": vendor.status,
            "latency_ms": latency_ms,
        },
    )

    if ctx:
        await ctx.info(f"Vendor status retrieved: {name} ({vendor.status})")

    return response


@mcp.tool()
async def update_vendor_status(
    name: str,
    version: int,
    status: str | None = None,
    metadata: dict[str, Any] | None = None,
    updated_by: str = "claude-code",
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Update vendor status with optimistic locking.

    Updates vendor extractor status, test results, version, and metadata
    with optimistic locking version check. Rejects conflicting concurrent
    updates.

    Args:
        name: Unique vendor name
        version: Expected version for optimistic locking
        status: New operational status ("operational" or "broken", optional)
        metadata: Updated metadata dict (optional, merged with existing)
        updated_by: AI client identifier (default: "claude-code")
        ctx: FastMCP context for logging (injected)

    Returns:
        Dictionary with updated vendor status data matching MCP contract

    Raises:
        ValueError: If vendor not found, invalid status, or validation fails
        RuntimeError: If optimistic locking conflict occurs (version mismatch)

    Performance:
        Target: <100ms p95 latency

    Requirements:
        FR-003 (metadata storage), FR-037 (optimistic locking)
    """
    start_time = time.perf_counter()

    # Dual logging pattern
    if ctx:
        await ctx.info(f"Updating vendor status: {name} (version {version})")

    logger.info(
        "update_vendor_status called",
        extra={
            "vendor_name": name,
            "version": version,
            "has_status": status is not None,
            "has_metadata": metadata is not None,
            "updated_by": updated_by,
        },
    )

    # Validate version
    if version < 1:
        error_msg = f"Invalid version: {version}. Must be >= 1."
        if ctx:
            await ctx.error(error_msg)
        raise ValueError(error_msg)

    # Validate status if provided
    valid_statuses = {"operational", "broken"}
    if status is not None and status not in valid_statuses:
        error_msg = f"Invalid status: {status}. Valid values: {valid_statuses}"
        if ctx:
            await ctx.error(error_msg)
        raise ValueError(error_msg)

    # Build updates dictionary
    updates: dict[str, Any] = {}
    if status is not None:
        updates["status"] = status
    if metadata is not None:
        # Validate metadata with Pydantic (will be merged with existing in service)
        try:
            # Pass metadata fields individually for service layer validation
            if "test_results" in metadata:
                updates["test_results"] = metadata["test_results"]
            if "format_support" in metadata:
                updates["format_support"] = metadata["format_support"]
            if "extractor_version" in metadata:
                updates["extractor_version"] = metadata["extractor_version"]
            if "manifest_compliant" in metadata:
                updates["manifest_compliant"] = metadata["manifest_compliant"]
        except Exception as e:
            error_msg = f"Invalid metadata structure: {e}"
            if ctx:
                await ctx.error(error_msg)
            logger.error(
                "Metadata validation failed",
                extra={"error": str(e), "metadata_keys": list(metadata.keys())},
            )
            raise ValueError(error_msg) from e

    if not updates:
        error_msg = "No updates provided (status or metadata required)"
        if ctx:
            await ctx.error(error_msg)
        raise ValueError(error_msg)

    # Update vendor with optimistic locking
    try:
        async with get_session_factory()() as db:
            updated_vendor = await update_vendor_service(
                name=name,
                version=version,
                updates=updates,
                session=db,
            )
            await db.commit()
    except VendorNotFoundError as e:
        error_msg = f"Vendor not found: {name}"
        if ctx:
            await ctx.error(error_msg)
        logger.warning(
            "Vendor not found",
            extra={"vendor_name": name},
        )
        raise ValueError(error_msg) from e
    except OptimisticLockError as e:
        error_msg = (
            f"Version conflict: expected version {version}, "
            f"current version is {e.current_version}. "
            "Another client has modified this vendor."
        )
        if ctx:
            await ctx.error(error_msg)
        logger.warning(
            "Optimistic lock error",
            extra={
                "vendor_name": name,
                "expected_version": version,
                "current_version": e.current_version,
            },
        )
        raise RuntimeError(error_msg) from e
    except ValidationError as e:
        error_msg = f"Vendor metadata validation failed: {e.field_errors}"
        if ctx:
            await ctx.error(error_msg)
        logger.error(
            "Vendor validation failed",
            extra={"field_errors": e.field_errors},
        )
        raise ValueError(error_msg) from e
    except Exception as e:
        logger.error(
            "Failed to update vendor",
            extra={
                "vendor_name": name,
                "version": version,
                "error": str(e),
            },
        )
        if ctx:
            await ctx.error(f"Failed to update vendor: {e}")
        raise

    # Convert to response format
    response = _vendor_to_dict(updated_vendor)

    latency_ms = int((time.perf_counter() - start_time) * 1000)

    logger.info(
        "update_vendor_status completed successfully",
        extra={
            "vendor_name": name,
            "old_version": version,
            "new_version": updated_vendor.version,
            "latency_ms": latency_ms,
        },
    )

    if ctx:
        await ctx.info(f"Vendor status updated: {name} (version {updated_vendor.version})")

    return response


# ==============================================================================
# Module Exports
# ==============================================================================

__all__ = [
    "record_deployment",
    "query_vendor_status",
    "update_vendor_status",
]
