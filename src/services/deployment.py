"""Deployment event tracking service.

Records deployment events with PR details, test results, constitutional compliance,
and many-to-many relationships with vendors and work items for complete audit trail.

Constitutional Compliance:
- Principle V: Production quality (complete deployment audit trail, error handling)
- Principle VIII: Type safety (100% type annotations, mypy --strict)
- Principle X: Git micro-commits (deployment tracking for traceability)

Key Features:
- Create deployment events with PR metadata and relationships
- Query recent deployments (chronological order)
- Lookup deployments by commit hash
- Pydantic validation for all JSONB metadata
- Many-to-many links via junction tables (vendors, work items)
- Comprehensive error handling and structured logging

Performance Targets:
- <200ms p95 latency for deployment creation
- <50ms for deployment queries by commit hash
- <100ms for recent deployments list (limit 10)
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.mcp.mcp_logging import get_logger
from src.models.tracking import (
    DeploymentEvent,
    VendorDeploymentLink,
    WorkItemDeploymentLink,
)
from src.services.validation import ValidationError, validate_deployment_metadata

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
    from pydantic_schemas import DeploymentMetadata  # type: ignore
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


class DeploymentNotFoundError(Exception):
    """Raised when deployment lookup fails.

    HTTP Mapping:
        404 Not Found - Deployment does not exist
    """

    def __init__(self, *, deployment_id: UUID | None = None, commit_hash: str | None = None) -> None:
        """Initialize DeploymentNotFoundError.

        Args:
            deployment_id: Deployment UUID that was not found (optional)
            commit_hash: Git commit hash that was not found (optional)
        """
        self.deployment_id = deployment_id
        self.commit_hash = commit_hash

        if deployment_id:
            message = f"Deployment not found: {deployment_id}"
        elif commit_hash:
            message = f"Deployment not found for commit: {commit_hash}"
        else:
            message = "Deployment not found"

        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for MCP error responses."""
        return {
            "error_type": "DeploymentNotFoundError",
            "deployment_id": str(self.deployment_id) if self.deployment_id else None,
            "commit_hash": self.commit_hash,
            "http_status": 404,
        }


class InvalidDeploymentDataError(Exception):
    """Raised when deployment data is invalid.

    HTTP Mapping:
        400 Bad Request - Invalid input data
    """

    def __init__(self, message: str) -> None:
        """Initialize InvalidDeploymentDataError."""
        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for MCP error responses."""
        return {
            "error_type": "InvalidDeploymentDataError",
            "message": str(self),
            "http_status": 400,
        }


# ==============================================================================
# Service Functions
# ==============================================================================


async def create_deployment(
    deployed_at: datetime,
    metadata: DeploymentMetadata,
    vendor_ids: list[UUID],
    work_item_ids: list[UUID],
    created_by: str,
    session: AsyncSession,
) -> DeploymentEvent:
    """Create deployment event with PR details and relationships.

    Creates deployment event and associated many-to-many links to vendors
    and work items in a single atomic transaction.

    Args:
        deployed_at: Deployment timestamp (UTC)
        metadata: Deployment metadata (PR details, test results, compliance)
        vendor_ids: List of vendor UUIDs affected by deployment
        work_item_ids: List of work item UUIDs included in deployment
        created_by: AI client identifier creating deployment
        session: Active async database session

    Returns:
        Created DeploymentEvent instance with relationships

    Raises:
        ValidationError: Invalid metadata (Pydantic validation failed)
        InvalidDeploymentDataError: Invalid vendor/work item IDs

    Performance:
        <200ms p95 latency (includes junction table inserts)

    Example:
        >>> from datetime import datetime, timezone
        >>> from pydantic_schemas import DeploymentMetadata
        >>>
        >>> metadata = DeploymentMetadata(
        ...     pr_number=123,
        ...     pr_title="feat(indexer): add tree-sitter AST parsing",
        ...     commit_hash="84b04732a1f5e9c8d3b2a0e6f7c8d9e0a1b2c3d4",
        ...     test_summary={"unit": 150, "integration": 30},
        ...     constitutional_compliance=True
        ... )
        >>>
        >>> async with session_factory() as session:
        ...     deployment = await create_deployment(
        ...         deployed_at=datetime.now(timezone.utc),
        ...         metadata=metadata,
        ...         vendor_ids=[UUID("...")],
        ...         work_item_ids=[UUID("...")],
        ...         created_by="claude-code-v1",
        ...         session=session
        ...     )
        ...     await session.commit()
        ...     print(f"Deployment created: {deployment.id}")
    """
    logger.info(
        "Creating deployment event",
        extra={
            "context": {
                "deployed_at": deployed_at.isoformat(),
                "pr_number": metadata.pr_number,
                "commit_hash": metadata.commit_hash[:8],
                "vendor_count": len(vendor_ids),
                "work_item_count": len(work_item_ids),
                "created_by": created_by,
            }
        },
    )

    # Validate metadata (Pydantic validation)
    try:
        validated_metadata = validate_deployment_metadata(metadata.model_dump())
    except ValidationError as e:
        logger.warning(
            "Deployment metadata validation failed",
            extra={
                "context": {
                    "field_errors": e.field_errors,
                    "pr_number": metadata.pr_number,
                }
            },
        )
        raise

    # Validate no duplicate vendor IDs
    if len(vendor_ids) != len(set(vendor_ids)):
        raise InvalidDeploymentDataError("Duplicate vendor IDs not allowed")

    # Validate no duplicate work item IDs
    if len(work_item_ids) != len(set(work_item_ids)):
        raise InvalidDeploymentDataError("Duplicate work item IDs not allowed")

    # Create deployment event
    deployment = DeploymentEvent(
        deployed_at=deployed_at,
        commit_hash=metadata.commit_hash,
        metadata_=validated_metadata,
        created_by=created_by,
    )
    session.add(deployment)

    # Flush to get deployment.id for junction table inserts
    await session.flush()

    # Create vendor links (many-to-many)
    for vendor_id in vendor_ids:
        vendor_link = VendorDeploymentLink(
            deployment_id=deployment.id,
            vendor_id=vendor_id,
        )
        session.add(vendor_link)

    # Create work item links (many-to-many)
    for work_item_id in work_item_ids:
        work_item_link = WorkItemDeploymentLink(
            deployment_id=deployment.id,
            work_item_id=work_item_id,
        )
        session.add(work_item_link)

    # Flush to persist junction table records
    await session.flush()

    logger.info(
        "Deployment event created successfully",
        extra={
            "context": {
                "deployment_id": str(deployment.id),
                "pr_number": metadata.pr_number,
                "commit_hash": metadata.commit_hash[:8],
                "vendor_links_created": len(vendor_ids),
                "work_item_links_created": len(work_item_ids),
            }
        },
    )

    return deployment


async def get_recent_deployments(
    limit: int = 10,
    session: AsyncSession | None = None,
) -> list[DeploymentEvent]:
    """Retrieve recent deployments in chronological order (most recent first).

    Args:
        limit: Maximum number of deployments to return (default: 10)
        session: Active async database session

    Returns:
        List of DeploymentEvent instances ordered by deployed_at DESC

    Performance:
        <100ms for limit=10 (indexed deployed_at column)

    Example:
        >>> async with session_factory() as session:
        ...     recent = await get_recent_deployments(limit=5, session=session)
        ...     for deployment in recent:
        ...         print(f"PR #{deployment.metadata_.pr_number}: {deployment.metadata_.pr_title}")
    """
    if session is None:
        raise ValueError("session parameter is required")

    logger.debug(
        f"Querying recent deployments (limit={limit})",
        extra={
            "context": {
                "limit": limit,
            }
        },
    )

    result = await session.execute(
        select(DeploymentEvent)
        .order_by(DeploymentEvent.deployed_at.desc())
        .limit(limit)
    )
    deployments = list(result.scalars().all())

    logger.debug(
        f"Found {len(deployments)} recent deployments",
        extra={
            "context": {
                "deployment_count": len(deployments),
                "limit": limit,
            }
        },
    )

    return deployments


async def get_deployment_by_commit(
    commit_hash: str,
    session: AsyncSession,
) -> DeploymentEvent:
    """Retrieve deployment by git commit hash.

    Args:
        commit_hash: Git SHA-1 commit hash (40 lowercase hex characters)
        session: Active async database session

    Returns:
        DeploymentEvent instance

    Raises:
        DeploymentNotFoundError: No deployment found for commit hash

    Performance:
        <50ms (indexed commit_hash column)

    Example:
        >>> async with session_factory() as session:
        ...     deployment = await get_deployment_by_commit(
        ...         commit_hash="84b04732a1f5e9c8d3b2a0e6f7c8d9e0a1b2c3d4",
        ...         session=session
        ...     )
        ...     print(f"PR #{deployment.metadata_.pr_number}")
    """
    logger.debug(
        f"Querying deployment by commit: {commit_hash[:8]}",
        extra={
            "context": {
                "commit_hash": commit_hash[:8],
            }
        },
    )

    result = await session.execute(
        select(DeploymentEvent).where(DeploymentEvent.commit_hash == commit_hash)
    )
    deployment = result.scalar_one_or_none()

    if deployment is None:
        logger.warning(
            f"Deployment not found for commit: {commit_hash[:8]}",
            extra={
                "context": {
                    "commit_hash": commit_hash[:8],
                }
            },
        )
        raise DeploymentNotFoundError(commit_hash=commit_hash)

    logger.debug(
        f"Deployment found for commit: {commit_hash[:8]}",
        extra={
            "context": {
                "deployment_id": str(deployment.id),
                "commit_hash": commit_hash[:8],
                "pr_number": deployment.metadata_.pr_number,
            }
        },
    )

    return deployment


async def get_deployment_by_id(
    deployment_id: UUID,
    session: AsyncSession,
) -> DeploymentEvent:
    """Retrieve deployment by UUID.

    Args:
        deployment_id: Deployment UUID
        session: Active async database session

    Returns:
        DeploymentEvent instance

    Raises:
        DeploymentNotFoundError: Deployment with given UUID does not exist

    Performance:
        <10ms (primary key lookup)

    Example:
        >>> async with session_factory() as session:
        ...     deployment = await get_deployment_by_id(UUID("..."), session)
        ...     print(f"Deployed at: {deployment.deployed_at}")
    """
    logger.debug(
        f"Querying deployment by ID: {deployment_id}",
        extra={
            "context": {
                "deployment_id": str(deployment_id),
            }
        },
    )

    result = await session.execute(
        select(DeploymentEvent).where(DeploymentEvent.id == deployment_id)
    )
    deployment = result.scalar_one_or_none()

    if deployment is None:
        logger.warning(
            f"Deployment not found: {deployment_id}",
            extra={
                "context": {
                    "deployment_id": str(deployment_id),
                }
            },
        )
        raise DeploymentNotFoundError(deployment_id=deployment_id)

    logger.debug(
        f"Deployment found: {deployment_id}",
        extra={
            "context": {
                "deployment_id": str(deployment_id),
                "pr_number": deployment.metadata_.pr_number,
            }
        },
    )

    return deployment


# ==============================================================================
# Public API
# ==============================================================================

__all__ = [
    "DeploymentNotFoundError",
    "InvalidDeploymentDataError",
    "create_deployment",
    "get_recent_deployments",
    "get_deployment_by_commit",
    "get_deployment_by_id",
]
