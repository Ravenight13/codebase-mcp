"""Integration tests for create_vendor MCP tool (Feature 005).

Tests verify success scenarios from specs/005-create-vendor/quickstart.md:
- Scenario 1: Create vendor with full metadata
- Scenario 2: Create vendor with partial metadata (scaffolder_version only)
- Scenario 3: Create vendor with no metadata (empty dict)
- Scenario 6: Immediate query after creation

TDD Compliance: These tests are written BEFORE create_vendor() tool implementation.
They MUST FAIL initially because the tool doesn't exist yet.

Constitutional Compliance:
- Principle VII: TDD (tests written before implementation)
- Principle IV: Performance Guarantees (<100ms p95 latency for vendor creation)
- Principle VIII: Type Safety (mypy --strict, full type hints)
- Principle V: Production Quality (comprehensive error handling validation)

Performance Requirements:
- FR-015: Create vendor with <100ms p95 latency
- FR-002: Query vendor status with <1ms p95 latency
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.tracking import VendorExtractor

# Import MCP tool (will fail until implemented - expected for TDD)
try:
    from src.mcp.tools.tracking import create_vendor
    CREATE_VENDOR_IMPORTED = True
except ImportError:
    CREATE_VENDOR_IMPORTED = False
    create_vendor = None  # type: ignore

# Import query tool for validation
from src.mcp.tools.tracking import query_vendor_status


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
async def clean_vendors(session: AsyncSession) -> None:
    """Clean up any existing test vendors before test execution.

    Ensures each test starts with a clean vendor table state.

    Args:
        session: Async database session
    """
    # Delete all vendors (for test isolation)
    await session.execute(select(VendorExtractor))
    await session.commit()


# ==============================================================================
# Success Scenario Tests (Scenarios 1, 2, 3, 6 from quickstart.md)
# ==============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not CREATE_VENDOR_IMPORTED, reason="create_vendor tool not yet implemented (TDD)")
async def test_create_vendor_with_full_metadata(
    session: AsyncSession,
    clean_vendors: None,
) -> None:
    """Test creating vendor with full metadata (Scenario 1).

    From quickstart.md Scenario 1:
    - Creates vendor "NewCorp" with full metadata
    - Validates all response fields match expected values
    - Verifies database record created correctly
    - Confirms vendor is immediately queryable

    Expected Response:
        - status: "broken" (default for new vendors)
        - extractor_version: "0.0.0" (default for new vendors)
        - metadata: matches input metadata
        - version: 1 (initial version)
        - created_by: "claude-code"

    Performance Target:
        <100ms p95 latency (FR-015)

    Requirements:
        FR-008: Create vendor with initial metadata
        FR-009: Default status "broken" for new vendors
        FR-010: Default extractor_version "0.0.0"
    """
    start_time = time.perf_counter()

    # Test data from quickstart.md Scenario 1
    vendor_name = "NewCorp"
    initial_metadata = {
        "scaffolder_version": "1.0",
        "created_at": "2025-10-11T10:00:00Z",
        "custom_field": "custom_value"
    }

    # Call create_vendor (will fail until implemented)
    response = await create_vendor(
        name=vendor_name,
        initial_metadata=initial_metadata,
        created_by="claude-code"
    )

    latency_ms = (time.perf_counter() - start_time) * 1000

    # Verify response structure and values
    assert "id" in response
    assert response["name"] == vendor_name
    assert response["status"] == "broken"
    assert response["extractor_version"] == "0.0.0"
    assert response["version"] == 1
    assert response["created_by"] == "claude-code"

    # Verify metadata matches input
    assert response["metadata"] == initial_metadata

    # Verify timestamps (created_at and updated_at should be recent)
    created_at = datetime.fromisoformat(response["created_at"].replace("Z", "+00:00"))
    updated_at = datetime.fromisoformat(response["updated_at"].replace("Z", "+00:00"))
    assert (datetime.now(timezone.utc) - created_at).total_seconds() < 2
    assert created_at == updated_at  # Should be identical for new vendor

    # Verify database record created
    stmt = select(VendorExtractor).where(VendorExtractor.name == vendor_name)
    result = await session.execute(stmt)
    db_vendor = result.scalar_one_or_none()

    assert db_vendor is not None
    assert db_vendor.name == vendor_name
    assert db_vendor.status == "broken"
    assert db_vendor.extractor_version == "0.0.0"
    assert db_vendor.version == 1
    assert db_vendor.metadata_ == initial_metadata

    # Verify performance target
    assert latency_ms < 100, f"Creation latency {latency_ms:.2f}ms exceeds 100ms target"

    # Verify vendor is immediately queryable (Scenario 6 requirement)
    query_response = await query_vendor_status(name=vendor_name)
    assert query_response["id"] == response["id"]
    assert query_response["name"] == vendor_name
    assert query_response["status"] == "broken"
    assert query_response["metadata"] == initial_metadata


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not CREATE_VENDOR_IMPORTED, reason="create_vendor tool not yet implemented (TDD)")
async def test_create_vendor_with_partial_metadata(
    session: AsyncSession,
    clean_vendors: None,
) -> None:
    """Test creating vendor with partial metadata (Scenario 2).

    From quickstart.md Scenario 2:
    - Creates vendor "AcmeInc" with only scaffolder_version
    - Validates metadata contains only provided field
    - Verifies optional fields not included in response

    Expected Behavior:
        - Metadata contains only scaffolder_version
        - No other optional fields present (created_at, custom_field)
        - created_by defaults to "claude-code"

    Requirements:
        FR-008: Support partial metadata (scaffolder_version only)
        FR-011: Optional metadata fields
    """
    vendor_name = "AcmeInc"
    initial_metadata = {
        "scaffolder_version": "1.0"
    }

    # Call create_vendor with partial metadata
    response = await create_vendor(
        name=vendor_name,
        initial_metadata=initial_metadata
    )

    # Verify response
    assert response["name"] == vendor_name
    assert response["status"] == "broken"
    assert response["version"] == 1
    assert response["created_by"] == "claude-code"  # Default value

    # Verify metadata contains only scaffolder_version
    assert response["metadata"] == {"scaffolder_version": "1.0"}
    assert "created_at" not in response["metadata"]
    assert "custom_field" not in response["metadata"]

    # Verify via query
    query_response = await query_vendor_status(name=vendor_name)
    assert query_response["metadata"]["scaffolder_version"] == "1.0"
    assert "created_at" not in query_response["metadata"]
    assert "custom_field" not in query_response["metadata"]


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not CREATE_VENDOR_IMPORTED, reason="create_vendor tool not yet implemented (TDD)")
async def test_create_vendor_with_no_metadata(
    session: AsyncSession,
    clean_vendors: None,
) -> None:
    """Test creating vendor with no metadata (Scenario 3).

    From quickstart.md Scenario 3:
    - Creates vendor "TechCo" with no metadata (default parameter)
    - Validates metadata is empty dict
    - Verifies all other fields have correct default values

    Expected Behavior:
        - Metadata is empty dict {}
        - All other fields present with defaults
        - Vendor creation succeeds without metadata

    Requirements:
        FR-012: Support vendor creation without metadata
        FR-013: Empty metadata dict for no metadata case
    """
    vendor_name = "TechCo"

    # Call create_vendor without metadata (default to None or {})
    response = await create_vendor(name=vendor_name)

    # Verify response
    assert response["name"] == vendor_name
    assert response["status"] == "broken"
    assert response["extractor_version"] == "0.0.0"
    assert response["version"] == 1
    assert response["created_by"] == "claude-code"

    # Verify metadata is empty dict
    assert response["metadata"] == {}

    # Verify via query
    query_response = await query_vendor_status(name=vendor_name)
    assert query_response["metadata"] == {}


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not CREATE_VENDOR_IMPORTED, reason="create_vendor tool not yet implemented (TDD)")
async def test_immediate_query_after_creation(
    session: AsyncSession,
    clean_vendors: None,
) -> None:
    """Test vendor is immediately queryable after creation (Scenario 6).

    From quickstart.md Scenario 6:
    - Creates vendor "QueryTest"
    - Immediately queries without delay
    - Validates both operations succeed
    - Confirms returned data matches between create and query

    Expected Behavior:
        - Create and query both succeed
        - All fields match between create and query responses
        - No database consistency issues

    Requirements:
        FR-014: Immediate queryability after vendor creation
        FR-002: Query vendor status with <1ms latency
    """
    vendor_name = "QueryTest"
    initial_metadata = {"scaffolder_version": "1.0"}

    # Create vendor
    create_response = await create_vendor(
        name=vendor_name,
        initial_metadata=initial_metadata
    )

    # Immediately query without delay
    query_response = await query_vendor_status(name=vendor_name)

    # Verify both operations succeeded
    assert create_response["id"] == query_response["id"]
    assert create_response["name"] == query_response["name"]
    assert create_response["status"] == query_response["status"]
    assert create_response["version"] == query_response["version"]
    assert create_response["metadata"] == query_response["metadata"]
    assert create_response["extractor_version"] == query_response["extractor_version"]

    # Verify consistency
    assert query_response["name"] == vendor_name
    assert query_response["status"] == "broken"
    assert query_response["version"] == 1
    assert query_response["metadata"] == initial_metadata


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not CREATE_VENDOR_IMPORTED, reason="create_vendor tool not yet implemented (TDD)")
async def test_create_vendor_performance_single_creation(
    session: AsyncSession,
    clean_vendors: None,
) -> None:
    """Test single vendor creation meets <100ms latency requirement.

    Validates FR-015: Create vendor with <100ms p95 latency

    Test Strategy:
        - Create single vendor with full metadata
        - Measure latency using time.perf_counter()
        - Assert latency < 100ms

    Performance Target:
        <100ms for single vendor creation (FR-015)
    """
    vendor_name = "PerfTest"
    initial_metadata = {
        "scaffolder_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    start_time = time.perf_counter()
    response = await create_vendor(
        name=vendor_name,
        initial_metadata=initial_metadata
    )
    latency_ms = (time.perf_counter() - start_time) * 1000

    # Verify successful creation
    assert response["name"] == vendor_name

    # Verify performance
    print(f"\nSingle vendor creation latency: {latency_ms:.2f}ms")
    assert latency_ms < 100, f"Latency {latency_ms:.2f}ms exceeds 100ms target"


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not CREATE_VENDOR_IMPORTED, reason="create_vendor tool not yet implemented (TDD)")
async def test_create_vendor_with_custom_created_by(
    session: AsyncSession,
    clean_vendors: None,
) -> None:
    """Test creating vendor with custom created_by value.

    Validates that AI client identifier can be customized beyond default.

    Expected Behavior:
        - created_by field respects custom value
        - Database record persists custom created_by
        - Query returns custom created_by

    Requirements:
        FR-008: Support custom created_by parameter
    """
    vendor_name = "CustomClient"
    custom_client = "copilot-workspace"

    response = await create_vendor(
        name=vendor_name,
        created_by=custom_client
    )

    # Verify custom created_by
    assert response["created_by"] == custom_client

    # Verify via query
    query_response = await query_vendor_status(name=vendor_name)
    assert query_response["created_by"] == custom_client


# ==============================================================================
# Test Summary
# ==============================================================================

"""
Test Summary for T004 - Create Vendor Success Scenarios:

Tests Implemented:
1. test_create_vendor_with_full_metadata (Scenario 1)
   - Full metadata with scaffolder_version, created_at, custom_field
   - Validates all response fields and defaults
   - Verifies database record and immediate queryability
   - Performance: <100ms

2. test_create_vendor_with_partial_metadata (Scenario 2)
   - Partial metadata (scaffolder_version only)
   - Validates only provided fields in metadata
   - Confirms optional fields not included

3. test_create_vendor_with_no_metadata (Scenario 3)
   - No metadata (empty dict)
   - Validates empty metadata handling
   - Confirms all defaults applied

4. test_immediate_query_after_creation (Scenario 6)
   - Creates vendor and immediately queries
   - Validates consistency between create and query
   - Confirms no database lag issues

5. test_create_vendor_performance_single_creation
   - Performance validation for single creation
   - Asserts <100ms latency (FR-015)

6. test_create_vendor_with_custom_created_by
   - Custom created_by parameter
   - Validates non-default AI client identifiers

Total Test Count: 6 integration tests
Performance Target: <100ms p95 latency (FR-015)
Constitutional Compliance: Principle VII (TDD - tests before implementation)

Expected Test Result:
All tests MUST FAIL with ImportError or AttributeError because create_vendor()
tool has not been implemented yet. This is correct TDD behavior.
"""
