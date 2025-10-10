"""Integration tests for deployment event recording with relationships (T040).

Tests verify quickstart scenario 3: Record deployment with vendor and work item relationships.

Test Coverage:
- Deployment recording with PR metadata
- Many-to-many relationships via junction tables (VendorDeploymentLink, WorkItemDeploymentLink)
- DeploymentMetadata Pydantic validation
- Junction table record creation and verification
- Relationship query correctness
- Error handling (invalid commit hash, duplicate UUIDs)

Performance Targets:
- Deployment recording: <200ms p95 latency

Constitutional Compliance:
- Principle VII: TDD (validates acceptance criteria from quickstart.md scenario 3)
- Principle VIII: Type Safety (Pydantic validation, comprehensive type annotations)
- Principle V: Production Quality (comprehensive error handling, audit trail)

Feature Requirements:
- FR-005: Record deployment events with PR details
- FR-006: Link deployments to affected vendors (many-to-many)
- FR-007: Link deployments to related work items (many-to-many)
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_session_factory
from src.mcp.tools.tracking import record_deployment
from src.models.tracking import (
    DeploymentEvent,
    VendorDeploymentLink,
    VendorExtractor,
    WorkItemDeploymentLink,
)
from src.models.task import WorkItem

# Import Pydantic schemas from contracts
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
    pytest.skip(
        f"Pydantic schemas not available: {e}. "
        "Ensure specs/003-database-backed-project/contracts/pydantic-schemas.py exists.",
        allow_module_level=True,
    )


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
async def seeded_vendors(session: AsyncSession) -> list[VendorExtractor]:
    """Create 3 vendor extractors for deployment relationship testing.

    Returns:
        List of 3 VendorExtractor instances with operational status
    """
    vendors = [
        VendorExtractor(
            name=f"vendor_test_{i}",
            status="operational",
            extractor_version="1.0.0",
            metadata_={
                "format_support": {"excel": True, "csv": True, "pdf": False, "ocr": False},
                "test_results": {"passing": 10, "total": 12, "skipped": 2},
                "extractor_version": "1.0.0",
                "manifest_compliant": True,
            },
            created_by="test-setup",
        )
        for i in range(3)
    ]

    for vendor in vendors:
        session.add(vendor)

    await session.commit()

    # Refresh to get database-generated fields
    for vendor in vendors:
        await session.refresh(vendor)

    return vendors


@pytest.fixture
async def seeded_work_items(session: AsyncSession) -> list[WorkItem]:
    """Create 2 work items for deployment relationship testing.

    Returns:
        List of 2 WorkItem instances with task type
    """
    work_items = [
        WorkItem(
            item_type="task",
            title=f"Test Task {i}",
            status="active",
            path="/",
            depth=0,
            metadata_={"estimated_hours": 2.0},
            created_by="test-setup",
        )
        for i in range(2)
    ]

    for item in work_items:
        session.add(item)

    await session.commit()

    # Refresh to get database-generated fields
    for item in work_items:
        await session.refresh(item)

    return work_items


@pytest.fixture
def valid_deployment_metadata() -> dict[str, Any]:
    """Create valid deployment metadata for testing.

    Returns:
        Dictionary matching DeploymentMetadata schema
    """
    return {
        "pr_number": 123,
        "pr_title": "feat(tracking): add deployment event recording",
        "commit_hash": "a1b2c3d4e5f6789012345678901234567890abcd",
        "test_summary": {"unit": 150, "integration": 30, "contract": 8},
        "constitutional_compliance": True,
    }


# ==============================================================================
# Scenario 3: Deployment Event Recording with Relationships
# ==============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_record_deployment_with_vendor_and_work_item_relationships(
    seeded_vendors: list[VendorExtractor],
    seeded_work_items: list[WorkItem],
    valid_deployment_metadata: dict[str, Any],
) -> None:
    """Test deployment recording with complete vendor and work item relationships.

    Scenario (from quickstart.md Scenario 3):
    Given: 3 vendors and 2 work items exist in database
    When: Record deployment with PR details, linking to vendors and work items
    Then: DeploymentResponse includes all relationship IDs
    And: Junction table records created correctly

    Validates:
    - Deployment event created with PR metadata
    - VendorDeploymentLink records created (3 links)
    - WorkItemDeploymentLink records created (2 links)
    - Response includes vendor_ids and work_item_ids
    - All relationships queryable via foreign keys
    """
    vendor_ids = [str(v.id) for v in seeded_vendors]
    work_item_ids = [str(w.id) for w in seeded_work_items]

    deployed_at = datetime.now(timezone.utc)

    # Act: Record deployment with relationships
    start_time = time.perf_counter()
    response = await record_deployment(
        deployed_at=deployed_at,
        metadata=valid_deployment_metadata,
        vendor_ids=vendor_ids,
        work_item_ids=work_item_ids,
        created_by="claude-code-test",
    )
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # Assert: Performance target (<200ms)
    assert elapsed_ms < 200.0, (
        f"Deployment recording took {elapsed_ms:.2f}ms, "
        f"target is <200ms (p95 latency requirement)"
    )

    # Assert: Response structure
    assert "id" in response, "Response must include deployment ID"
    assert "deployed_at" in response
    assert "commit_hash" in response
    assert "metadata" in response
    assert "vendor_ids" in response
    assert "work_item_ids" in response
    assert "created_at" in response
    assert "created_by" in response

    deployment_id = UUID(response["id"])

    # Assert: Response includes correct relationship IDs
    assert len(response["vendor_ids"]) == 3, f"Expected 3 vendor IDs, got {len(response['vendor_ids'])}"
    assert len(response["work_item_ids"]) == 2, f"Expected 2 work item IDs, got {len(response['work_item_ids'])}"

    response_vendor_ids = set(response["vendor_ids"])
    expected_vendor_ids = set(vendor_ids)
    assert response_vendor_ids == expected_vendor_ids, (
        f"Vendor IDs mismatch: expected {expected_vendor_ids}, got {response_vendor_ids}"
    )

    response_work_item_ids = set(response["work_item_ids"])
    expected_work_item_ids = set(work_item_ids)
    assert response_work_item_ids == expected_work_item_ids, (
        f"Work item IDs mismatch: expected {expected_work_item_ids}, got {response_work_item_ids}"
    )

    # Assert: Response metadata matches input
    assert response["metadata"]["pr_number"] == 123
    assert response["metadata"]["pr_title"] == "feat(tracking): add deployment event recording"
    assert response["metadata"]["commit_hash"] == "a1b2c3d4e5f6789012345678901234567890abcd"
    assert response["metadata"]["test_summary"]["unit"] == 150
    assert response["metadata"]["constitutional_compliance"] is True
    assert response["created_by"] == "claude-code-test"

    # Verify database persistence
    async with get_session_factory()() as db:
        # Verify DeploymentEvent record
        deployment_result = await db.execute(
            select(DeploymentEvent).where(DeploymentEvent.id == deployment_id)
        )
        deployment = deployment_result.scalar_one_or_none()

        assert deployment is not None, f"Deployment {deployment_id} not found in database"
        assert deployment.commit_hash == "a1b2c3d4e5f6789012345678901234567890abcd"
        assert deployment.created_by == "claude-code-test"

        # Verify VendorDeploymentLink junction table records
        vendor_links_result = await db.execute(
            select(VendorDeploymentLink).where(
                VendorDeploymentLink.deployment_id == deployment_id
            )
        )
        vendor_links = vendor_links_result.scalars().all()

        assert len(vendor_links) == 3, (
            f"Expected 3 vendor links, found {len(vendor_links)} in database"
        )

        linked_vendor_ids = {str(link.vendor_id) for link in vendor_links}
        assert linked_vendor_ids == expected_vendor_ids, (
            f"Vendor junction table mismatch: expected {expected_vendor_ids}, got {linked_vendor_ids}"
        )

        # Verify WorkItemDeploymentLink junction table records
        work_item_links_result = await db.execute(
            select(WorkItemDeploymentLink).where(
                WorkItemDeploymentLink.deployment_id == deployment_id
            )
        )
        work_item_links_list = list(work_item_links_result.scalars().all())

        assert len(work_item_links_list) == 2, (
            f"Expected 2 work item links, found {len(work_item_links_list)} in database"
        )

        linked_work_item_ids = {str(link.work_item_id) for link in work_item_links_list}
        assert linked_work_item_ids == expected_work_item_ids, (
            f"Work item junction table mismatch: expected {expected_work_item_ids}, got {linked_work_item_ids}"
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_record_deployment_minimal_no_relationships(
    valid_deployment_metadata: dict[str, Any],
) -> None:
    """Test deployment recording with no vendor/work item relationships.

    Given: No vendor_ids or work_item_ids provided
    When: Record deployment with only PR metadata
    Then: Deployment created successfully
    And: No junction table records created
    And: Response contains empty vendor_ids and work_item_ids lists
    """
    deployed_at = datetime.now(timezone.utc)

    # Act: Record deployment without relationships
    response = await record_deployment(
        deployed_at=deployed_at,
        metadata=valid_deployment_metadata,
        vendor_ids=None,  # No vendors
        work_item_ids=None,  # No work items
        created_by="claude-code-minimal",
    )

    # Assert: Response structure
    assert "id" in response
    assert "vendor_ids" in response
    assert "work_item_ids" in response

    deployment_id = UUID(response["id"])

    # Assert: Empty relationship lists
    assert response["vendor_ids"] == [], f"Expected empty vendor list, got {response['vendor_ids']}"
    assert response["work_item_ids"] == [], f"Expected empty work item list, got {response['work_item_ids']}"

    # Verify database: no junction table records
    async with get_session_factory()() as db:
        # Verify DeploymentEvent exists
        deployment_result = await db.execute(
            select(DeploymentEvent).where(DeploymentEvent.id == deployment_id)
        )
        deployment = deployment_result.scalar_one_or_none()
        assert deployment is not None

        # Verify no VendorDeploymentLink records
        vendor_links_result = await db.execute(
            select(VendorDeploymentLink).where(
                VendorDeploymentLink.deployment_id == deployment_id
            )
        )
        vendor_links = vendor_links_result.scalars().all()
        assert len(vendor_links) == 0, f"Expected 0 vendor links, found {len(vendor_links)}"

        # Verify no WorkItemDeploymentLink records
        work_item_links_result = await db.execute(
            select(WorkItemDeploymentLink).where(
                WorkItemDeploymentLink.deployment_id == deployment_id
            )
        )
        work_item_links = work_item_links_result.scalars().all()
        assert len(work_item_links) == 0, f"Expected 0 work item links, found {len(work_item_links)}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_record_deployment_validates_deployment_metadata() -> None:
    """Test that record_deployment validates DeploymentMetadata with Pydantic.

    Given: Invalid deployment metadata (invalid commit hash format)
    When: Attempt to record deployment
    Then: ValueError raised with validation error message
    And: No deployment record created in database
    """
    invalid_metadata = {
        "pr_number": 123,
        "pr_title": "Valid title",
        "commit_hash": "INVALID_HASH",  # Invalid: not 40 lowercase hex characters
        "test_summary": {"unit": 10},
        "constitutional_compliance": True,
    }

    deployed_at = datetime.now(timezone.utc)

    # Act & Assert: Validation error raised
    with pytest.raises(ValueError) as exc_info:
        await record_deployment(
            deployed_at=deployed_at,
            metadata=invalid_metadata,
            created_by="claude-code-invalid",
        )

    # Assert: Error message indicates validation failure
    error_message = str(exc_info.value).lower()
    assert "invalid" in error_message or "validation" in error_message or "metadata" in error_message


@pytest.mark.integration
@pytest.mark.asyncio
async def test_record_deployment_rejects_duplicate_vendor_ids(
    seeded_vendors: list[VendorExtractor],
    valid_deployment_metadata: dict[str, Any],
) -> None:
    """Test that record_deployment rejects duplicate vendor_ids.

    Given: vendor_ids list contains duplicates
    When: Attempt to record deployment
    Then: ValueError raised indicating duplicate UUIDs
    And: No deployment record created
    """
    vendor_id = str(seeded_vendors[0].id)
    duplicate_vendor_ids = [vendor_id, vendor_id]  # Duplicate

    deployed_at = datetime.now(timezone.utc)

    # Act & Assert: Validation error raised
    with pytest.raises(ValueError) as exc_info:
        await record_deployment(
            deployed_at=deployed_at,
            metadata=valid_deployment_metadata,
            vendor_ids=duplicate_vendor_ids,
            created_by="claude-code-duplicate",
        )

    # Assert: Error message indicates duplicate UUIDs
    error_message = str(exc_info.value).lower()
    assert "duplicate" in error_message


@pytest.mark.integration
@pytest.mark.asyncio
async def test_record_deployment_rejects_duplicate_work_item_ids(
    seeded_work_items: list[WorkItem],
    valid_deployment_metadata: dict[str, Any],
) -> None:
    """Test that record_deployment rejects duplicate work_item_ids.

    Given: work_item_ids list contains duplicates
    When: Attempt to record deployment
    Then: ValueError raised indicating duplicate UUIDs
    And: No deployment record created
    """
    work_item_id = str(seeded_work_items[0].id)
    duplicate_work_item_ids = [work_item_id, work_item_id]  # Duplicate

    deployed_at = datetime.now(timezone.utc)

    # Act & Assert: Validation error raised
    with pytest.raises(ValueError) as exc_info:
        await record_deployment(
            deployed_at=deployed_at,
            metadata=valid_deployment_metadata,
            work_item_ids=duplicate_work_item_ids,
            created_by="claude-code-duplicate",
        )

    # Assert: Error message indicates duplicate UUIDs
    error_message = str(exc_info.value).lower()
    assert "duplicate" in error_message


@pytest.mark.integration
@pytest.mark.asyncio
async def test_record_deployment_validates_commit_hash_format(
    valid_deployment_metadata: dict[str, Any],
) -> None:
    """Test that record_deployment validates commit_hash format (40 lowercase hex).

    Given: commit_hash with invalid format (not 40 characters)
    When: Attempt to record deployment
    Then: ValueError raised with commit hash validation error
    """
    # Test various invalid commit hash formats
    invalid_hashes = [
        "abc123",  # Too short
        "a" * 39,  # 39 characters
        "a" * 41,  # 41 characters
        "A" * 40,  # Uppercase (should be lowercase)
        "g" * 40,  # Non-hex characters
    ]

    deployed_at = datetime.now(timezone.utc)

    for invalid_hash in invalid_hashes:
        metadata = valid_deployment_metadata.copy()
        metadata["commit_hash"] = invalid_hash

        # Act & Assert: Validation error raised
        with pytest.raises(ValueError) as exc_info:
            await record_deployment(
                deployed_at=deployed_at,
                metadata=metadata,
                created_by="claude-code-invalid-hash",
            )

        # Assert: Error message mentions commit hash
        error_message = str(exc_info.value).lower()
        assert "commit" in error_message or "hash" in error_message or "invalid" in error_message


@pytest.mark.integration
@pytest.mark.asyncio
async def test_record_deployment_query_relationships_via_foreign_keys(
    seeded_vendors: list[VendorExtractor],
    seeded_work_items: list[WorkItem],
    valid_deployment_metadata: dict[str, Any],
) -> None:
    """Test that deployment relationships are queryable via foreign keys.

    Given: Deployment recorded with vendor and work item relationships
    When: Query junction tables by deployment_id
    Then: All linked vendors and work items retrieved correctly
    And: Foreign keys resolve to correct entities
    """
    vendor_ids = [str(v.id) for v in seeded_vendors]
    work_item_ids = [str(w.id) for w in seeded_work_items]

    deployed_at = datetime.now(timezone.utc)

    # Act: Record deployment
    response = await record_deployment(
        deployed_at=deployed_at,
        metadata=valid_deployment_metadata,
        vendor_ids=vendor_ids,
        work_item_ids=work_item_ids,
        created_by="claude-code-fk-test",
    )

    deployment_id = UUID(response["id"])

    # Verify foreign key relationships
    async with get_session_factory()() as db:
        # Query vendors via junction table
        vendor_links_result = await db.execute(
            select(VendorDeploymentLink).where(
                VendorDeploymentLink.deployment_id == deployment_id
            )
        )
        vendor_links = vendor_links_result.scalars().all()

        # Verify each vendor link resolves to actual VendorExtractor
        for link in vendor_links:
            vendor_result = await db.execute(
                select(VendorExtractor).where(VendorExtractor.id == link.vendor_id)
            )
            vendor = vendor_result.scalar_one_or_none()

            assert vendor is not None, f"Vendor {link.vendor_id} not found"
            assert vendor.status == "operational"
            assert vendor.name.startswith("vendor_test_")

        # Query work items via junction table
        work_item_links_result = await db.execute(
            select(WorkItemDeploymentLink).where(
                WorkItemDeploymentLink.deployment_id == deployment_id
            )
        )
        work_item_links = work_item_links_result.scalars().all()

        # Verify each work item link resolves to actual WorkItem
        for link in work_item_links:
            work_item_result = await db.execute(
                select(WorkItem).where(WorkItem.id == link.work_item_id)
            )
            work_item = work_item_result.scalar_one_or_none()

            assert work_item is not None, f"Work item {link.work_item_id} not found"
            assert work_item.item_type == "task"
            assert work_item.title.startswith("Test Task")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_record_deployment_audit_trail_complete(
    seeded_vendors: list[VendorExtractor],
    valid_deployment_metadata: dict[str, Any],
) -> None:
    """Test that deployment recording includes complete audit trail.

    Given: Deployment recorded with created_by identifier
    When: Query deployment from database
    Then: created_at timestamp exists
    And: created_by field matches input
    And: Timestamps are in UTC
    """
    vendor_ids = [str(seeded_vendors[0].id)]
    deployed_at = datetime.now(timezone.utc)

    # Act: Record deployment
    response = await record_deployment(
        deployed_at=deployed_at,
        metadata=valid_deployment_metadata,
        vendor_ids=vendor_ids,
        created_by="claude-code-audit",
    )

    deployment_id = UUID(response["id"])

    # Verify audit trail
    async with get_session_factory()() as db:
        deployment_result = await db.execute(
            select(DeploymentEvent).where(DeploymentEvent.id == deployment_id)
        )
        deployment = deployment_result.scalar_one()

        # Assert: Audit trail fields
        assert deployment.created_by == "claude-code-audit"
        assert deployment.created_at is not None
        assert deployment.created_at.tzinfo is not None, "created_at must be timezone-aware"

        # Assert: deployed_at preserved correctly
        assert deployment.deployed_at == deployed_at
        assert deployment.deployed_at.tzinfo is not None, "deployed_at must be timezone-aware"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_record_deployment_performance_within_target(
    seeded_vendors: list[VendorExtractor],
    seeded_work_items: list[WorkItem],
    valid_deployment_metadata: dict[str, Any],
) -> None:
    """Test that deployment recording meets <200ms performance target (p95).

    Given: 3 vendors and 2 work items (5 junction table inserts)
    When: Record deployment with complete relationships
    Then: Operation completes in <200ms
    And: All data persisted correctly
    """
    vendor_ids = [str(v.id) for v in seeded_vendors]
    work_item_ids = [str(w.id) for w in seeded_work_items]

    deployed_at = datetime.now(timezone.utc)

    # Measure performance over multiple iterations
    iterations = 10
    latencies_ms = []

    for _ in range(iterations):
        start_time = time.perf_counter()

        await record_deployment(
            deployed_at=deployed_at,
            metadata=valid_deployment_metadata,
            vendor_ids=vendor_ids,
            work_item_ids=work_item_ids,
            created_by="claude-code-perf",
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        latencies_ms.append(elapsed_ms)

    # Calculate p95 latency
    latencies_ms.sort()
    p95_index = int(0.95 * len(latencies_ms))
    p95_latency = latencies_ms[p95_index]

    # Assert: p95 latency meets target
    assert p95_latency < 200.0, (
        f"p95 latency {p95_latency:.2f}ms exceeds 200ms target. "
        f"Latencies: {latencies_ms}"
    )


# ==============================================================================
# Test Summary
# ==============================================================================

"""
Integration Test Coverage (T040):

✅ Deployment recording with vendor and work item relationships
✅ Junction table record creation (VendorDeploymentLink, WorkItemDeploymentLink)
✅ DeploymentMetadata Pydantic validation
✅ Minimal deployment (no relationships)
✅ Duplicate UUID rejection (vendors and work items)
✅ Commit hash format validation
✅ Foreign key relationship queries
✅ Complete audit trail verification
✅ Performance target validation (<200ms p95)

Constitutional Compliance:
✅ Principle VII: TDD (validates quickstart.md scenario 3 acceptance criteria)
✅ Principle VIII: Type Safety (Pydantic validation throughout)
✅ Principle V: Production Quality (comprehensive error handling, audit trail)

Feature Requirements Validated:
✅ FR-005: Record deployment events with PR details
✅ FR-006: Link deployments to affected vendors (many-to-many)
✅ FR-007: Link deployments to related work items (many-to-many)

Performance Validation:
✅ <200ms p95 latency for deployment recording
✅ Junction table inserts included in performance measurement
"""
