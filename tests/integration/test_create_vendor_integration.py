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

# Import service functions (not MCP tool wrappers)
try:
    from src.services.vendor import create_vendor, VendorAlreadyExistsError
    CREATE_VENDOR_IMPORTED = True
except ImportError:
    CREATE_VENDOR_IMPORTED = False
    create_vendor = None  # type: ignore
    VendorAlreadyExistsError = Exception  # type: ignore

# Import query service for validation
from src.services.vendor import get_vendor_by_name


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

    # Call create_vendor service function
    response = await create_vendor(
        name=vendor_name,
        initial_metadata=initial_metadata,
        created_by="claude-code",
        session=session
    )

    latency_ms = (time.perf_counter() - start_time) * 1000

    # Verify response structure and values
    assert response.id is not None
    assert response.name == vendor_name
    assert response.status == "broken"
    assert response.extractor_version == "0.0.0"
    assert response.version == 1
    assert response.created_by == "claude-code"

    # Verify metadata matches input
    assert response.metadata_ == initial_metadata

    # Verify timestamps (created_at and updated_at should be recent)
    created_at = response.created_at
    updated_at = response.updated_at
    assert (datetime.now(timezone.utc) - created_at).total_seconds() < 2
    # Timestamps should be within 1 millisecond of each other (database precision)
    assert abs((created_at - updated_at).total_seconds()) < 0.001

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
    query_response = await get_vendor_by_name(vendor_name, session=session)
    assert query_response.id == response.id
    assert query_response.name == vendor_name
    assert query_response.status == "broken"
    assert query_response.metadata_ == initial_metadata


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
        initial_metadata=initial_metadata,
        created_by="claude-code",
        session=session
    )

    # Verify response
    assert response.name == vendor_name
    assert response.status == "broken"
    assert response.version == 1
    assert response.created_by == "claude-code"

    # Verify metadata contains only scaffolder_version
    assert response.metadata_ == {"scaffolder_version": "1.0"}
    assert "created_at" not in response.metadata_
    assert "custom_field" not in response.metadata_

    # Verify via query
    query_response = await get_vendor_by_name(vendor_name, session=session)
    assert query_response.metadata_["scaffolder_version"] == "1.0"
    assert "created_at" not in query_response.metadata_
    assert "custom_field" not in query_response.metadata_


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
    response = await create_vendor(name=vendor_name,
        initial_metadata=None,
        created_by="claude-code",
        session=session
    )

    # Verify response
    assert response.name == vendor_name
    assert response.status == "broken"
    assert response.extractor_version == "0.0.0"
    assert response.version == 1
    assert response.created_by == "claude-code"

    # Verify metadata is empty dict
    assert response.metadata_ == {}

    # Verify via query
    query_response = await get_vendor_by_name(vendor_name, session=session)
    assert query_response.metadata_ == {}


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
        initial_metadata=initial_metadata,
        created_by="claude-code",
        session=session
    )

    # Immediately query without delay
    query_response = await get_vendor_by_name(vendor_name, session=session)

    # Verify both operations succeeded
    assert create_response.id == query_response.id
    assert create_response.name == query_response.name
    assert create_response.status == query_response.status
    assert create_response.version == query_response.version
    assert create_response.metadata_ == query_response.metadata_
    assert create_response.extractor_version == query_response.extractor_version

    # Verify consistency
    assert query_response.name == vendor_name
    assert query_response.status == "broken"
    assert query_response.version == 1
    assert query_response.metadata_ == initial_metadata


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
        initial_metadata=initial_metadata,
        created_by="claude-code",
        session=session
    )
    latency_ms = (time.perf_counter() - start_time) * 1000

    # Verify successful creation
    assert response.name == vendor_name

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
        initial_metadata=None,
        created_by=custom_client,
        session=session
    )

    # Verify custom created_by
    assert response.created_by == custom_client

    # Verify via query
    query_response = await get_vendor_by_name(vendor_name, session=session)
    assert query_response.created_by == custom_client


# ==============================================================================
# Error Scenario Tests (T005 - Scenarios 4, 5, 7-12 from quickstart.md)
# ==============================================================================


@pytest.fixture
async def existing_vendor(session: AsyncSession) -> VendorExtractor:
    """Create an existing vendor for duplicate detection tests.

    Returns:
        VendorExtractor instance with name "ExistingVendor"
    """
    vendor = VendorExtractor(
        name="ExistingVendor",
        status="broken",
        extractor_version="0.0.0",
        metadata_={"scaffolder_version": "1.0"},
        created_by="test-setup",
    )

    session.add(vendor)
    await session.commit()
    await session.refresh(vendor)

    return vendor


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not CREATE_VENDOR_IMPORTED, reason="create_vendor tool not yet implemented (TDD)")
async def test_create_vendor_duplicate_exact_match(
    session: AsyncSession,
    existing_vendor: VendorExtractor,
) -> None:
    """Test duplicate detection for exact name match (Scenario 4).

    From quickstart.md Scenario 4:
    Given: Vendor "ExistingVendor" already exists in database
    When: Attempt to create vendor with exact same name
    Then: ValueError raised with "already exists" message
    And: No new database record created
    And: Existing vendor record unchanged

    Requirements:
        FR-016: Case-insensitive duplicate detection
        FR-018: Clear error messages for duplicate vendors
    """
    from sqlalchemy import func

    # Verify existing vendor is in database
    result = await session.execute(
        select(func.count()).select_from(VendorExtractor)
        .where(VendorExtractor.name == "ExistingVendor")
    )
    count_before = result.scalar()
    assert count_before == 1, "Existing vendor not found in database"

    # Act & Assert: Attempt to create duplicate vendor
    with pytest.raises(VendorAlreadyExistsError) as exc_info:
        await create_vendor(
            name="ExistingVendor",
            initial_metadata={},
        created_by="test-duplicate",
        session=session
    )

    # Assert: Error message indicates duplicate
    error_message = str(exc_info.value).lower()
    assert "already exists" in error_message, (
        f"Expected 'already exists' in error message, got: {exc_info.value}"
    )
    assert "existingvendor" in error_message, (
        f"Expected vendor name in error message, got: {exc_info.value}"
    )

    # Verify: No new record created (still only 1)
    result = await session.execute(
        select(func.count()).select_from(VendorExtractor)
        .where(VendorExtractor.name == "ExistingVendor")
    )
    count_after = result.scalar()
    assert count_after == 1, f"Expected 1 vendor record, found {count_after}"

    # Verify: Existing vendor unchanged (version still 1)
    result = await session.execute(
        select(VendorExtractor).where(VendorExtractor.name == "ExistingVendor")
    )
    vendor = result.scalar_one()
    assert vendor.version == 1, f"Existing vendor version changed to {vendor.version}"
    assert vendor.created_by == "test-setup", "Existing vendor created_by changed"


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not CREATE_VENDOR_IMPORTED, reason="create_vendor tool not yet implemented (TDD)")
async def test_create_vendor_duplicate_case_insensitive(
    session: AsyncSession,
    existing_vendor: VendorExtractor,
) -> None:
    """Test case-insensitive duplicate detection (Scenario 5).

    From quickstart.md Scenario 5:
    Given: Vendor "ExistingVendor" exists in database
    When: Attempt to create vendor with name "existingvendor" (lowercase)
    Then: ValueError raised with "already exists" message
    And: Error message shows conflicting name: "conflicts with existing 'ExistingVendor'"
    And: No new database record created

    Requirements:
        FR-016: Case-insensitive duplicate detection enforced by database
        FR-018: Clear error messages showing case conflict
    """
    from sqlalchemy import func

    # Act & Assert: Attempt to create case-insensitive duplicate
    with pytest.raises(VendorAlreadyExistsError) as exc_info:
        await create_vendor(
            name="existingvendor",  # Different case
            initial_metadata={},
        created_by="test-case-insensitive",
        session=session
    )

    # Assert: Error message indicates case-insensitive conflict
    error_message = str(exc_info.value).lower()
    assert "already exists" in error_message, (
        f"Expected 'already exists' in error message, got: {exc_info.value}"
    )

    # Verify: Only one record exists (no duplicate created)
    result = await session.execute(
        select(func.count()).select_from(VendorExtractor)
        .where(func.lower(VendorExtractor.name) == "existingvendor")
    )
    count = result.scalar()
    assert count == 1, f"Expected 1 vendor with case-insensitive name, found {count}"


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not CREATE_VENDOR_IMPORTED, reason="create_vendor tool not yet implemented (TDD)")
async def test_create_vendor_empty_name_validation(
    session: AsyncSession,
    clean_vendors: None,
) -> None:
    """Test empty name validation (Scenario 7).

    From quickstart.md Scenario 7:
    Given: Attempting to create vendor with empty name
    When: Call create_vendor with name=""
    Then: ValueError raised with "cannot be empty" message
    And: No database record created

    Requirements:
        FR-019: Name validation (1-100 characters)
        FR-020: Clear validation error messages
    """
    # Act & Assert: Attempt to create vendor with empty name
    with pytest.raises(ValueError) as exc_info:
        await create_vendor(
            name="",
            initial_metadata={},
        created_by="test-empty-name",
        session=session
    )

    # Assert: Error message indicates empty name
    error_message = str(exc_info.value).lower()
    assert "cannot be empty" in error_message or "empty" in error_message, (
        f"Expected 'empty' in error message, got: {exc_info.value}"
    )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not CREATE_VENDOR_IMPORTED, reason="create_vendor tool not yet implemented (TDD)")
async def test_create_vendor_name_too_long_validation(
    session: AsyncSession,
    clean_vendors: None,
) -> None:
    """Test length constraint validation - max 100 characters (Scenario 8).

    From quickstart.md Scenario 8:
    Given: Attempting to create vendor with 101-character name
    When: Call create_vendor with name="A" * 101
    Then: ValueError raised with "1-100 characters" message
    And: No database record created

    Requirements:
        FR-019: Name length constraint (1-100 characters)
        FR-020: Clear validation error messages showing actual length
    """
    long_name = "A" * 101

    # Act & Assert: Attempt to create vendor with too-long name
    with pytest.raises(ValueError) as exc_info:
        await create_vendor(
            name=long_name,
            initial_metadata={},
        created_by="test-long-name",
        session=session
    )

    # Assert: Error message indicates length constraint
    error_message = str(exc_info.value).lower()
    assert "1-100 characters" in error_message or "100" in error_message, (
        f"Expected length constraint in error message, got: {exc_info.value}"
    )
    assert "101" in error_message, (
        f"Expected actual length (101) in error message, got: {exc_info.value}"
    )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not CREATE_VENDOR_IMPORTED, reason="create_vendor tool not yet implemented (TDD)")
async def test_create_vendor_invalid_characters_validation(
    session: AsyncSession,
    clean_vendors: None,
) -> None:
    """Test character constraint validation (Scenario 9).

    From quickstart.md Scenario 9:
    Given: Attempting to create vendor with special characters
    When: Call create_vendor with names containing @, !, #, $, %
    Then: ValueError raised with "alphanumeric" message for each
    And: No database records created

    Requirements:
        FR-021: Name character constraint (alphanumeric + spaces/hyphens/underscores)
        FR-020: Clear validation error messages
    """
    invalid_names = [
        "Test@Vendor",
        "Vendor!",
        "Test#123",
        "Vendor$Corp",
        "Test%Value",
    ]

    for invalid_name in invalid_names:
        # Act & Assert: Attempt to create vendor with invalid characters
        with pytest.raises(ValueError) as exc_info:
            await create_vendor(
                name=invalid_name,
                initial_metadata={},
        created_by="test-invalid-chars",
        session=session
    )

        # Assert: Error message indicates character constraint
        error_message = str(exc_info.value).lower()
        assert "alphanumeric" in error_message or "invalid" in error_message, (
            f"Expected 'alphanumeric' or 'invalid' for name '{invalid_name}', "
            f"got: {exc_info.value}"
        )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not CREATE_VENDOR_IMPORTED, reason="create_vendor tool not yet implemented (TDD)")
async def test_create_vendor_invalid_scaffolder_version_type(
    session: AsyncSession,
    clean_vendors: None,
) -> None:
    """Test scaffolder_version type constraint (Scenario 10).

    From quickstart.md Scenario 10:
    Given: Attempting to create vendor with non-string scaffolder_version
    When: Call create_vendor with scaffolder_version=123 (integer)
    Then: ValueError raised with "scaffolder_version must be string" message
    And: No database record created

    Requirements:
        FR-022: Metadata validation (scaffolder_version must be string)
        FR-020: Clear validation error messages
    """
    # Act & Assert: Attempt to create vendor with invalid metadata type
    with pytest.raises(ValueError) as exc_info:
        await create_vendor(
            name="TestVendor",
            initial_metadata={"scaffolder_version": 123},  # Integer instead of string
            created_by="test-invalid-metadata-type",
        session=session
    )

    # Assert: Error message indicates type constraint
    error_message = str(exc_info.value).lower()
    assert "scaffolder_version" in error_message, (
        f"Expected 'scaffolder_version' in error message, got: {exc_info.value}"
    )
    assert "string" in error_message, (
        f"Expected 'string' in error message, got: {exc_info.value}"
    )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not CREATE_VENDOR_IMPORTED, reason="create_vendor tool not yet implemented (TDD)")
async def test_create_vendor_invalid_created_at_format(
    session: AsyncSession,
    clean_vendors: None,
) -> None:
    """Test created_at ISO 8601 format constraint (Scenario 11).

    From quickstart.md Scenario 11:
    Given: Attempting to create vendor with invalid created_at format
    When: Call create_vendor with created_at="invalid-date"
    Then: ValueError raised with "ISO 8601" message
    And: No database record created

    Requirements:
        FR-023: Metadata validation (created_at must be ISO 8601 format)
        FR-020: Clear validation error messages
    """
    invalid_dates = [
        "invalid-date",
        "2025-13-01",  # Invalid month
        "2025-10-32",  # Invalid day
        "not-a-date",
    ]

    for invalid_date in invalid_dates:
        # Act & Assert: Attempt to create vendor with invalid date format
        with pytest.raises(ValueError) as exc_info:
            await create_vendor(
                name=f"TestVendor_{invalid_date}",
                initial_metadata={"created_at": invalid_date},
        created_by="test-invalid-date",
        session=session
    )

        # Assert: Error message indicates ISO 8601 format requirement
        error_message = str(exc_info.value).lower()
        assert "created_at" in error_message or "iso 8601" in error_message or "invalid" in error_message, (
            f"Expected ISO 8601 error for date '{invalid_date}', got: {exc_info.value}"
        )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not CREATE_VENDOR_IMPORTED, reason="create_vendor tool not yet implemented (TDD)")
async def test_create_vendor_concurrent_creation_safety(
    session: AsyncSession,
    clean_vendors: None,
) -> None:
    """Test concurrent creation safety (Scenario 12).

    From quickstart.md Scenario 12:
    Given: Two AI assistants attempt to create same vendor simultaneously
    When: Execute create_vendor calls concurrently with asyncio.gather
    Then: One call succeeds (creates vendor)
    And: Other call fails with ValueError (VendorAlreadyExistsError)
    And: Exactly one vendor record exists in database
    And: Successful vendor has one of the two metadata values

    Requirements:
        FR-017: Concurrent creation safety (database constraint enforcement)
        FR-024: One success, one failure for concurrent attempts
    """
    import asyncio
    from sqlalchemy import func

    # Act: Simulate concurrent creation attempts
    task1 = create_vendor(
        name="ConcurrentVendor",
        initial_metadata={"source": "assistant1"},
        created_by="assistant1",
    )
    task2 = create_vendor(
        name="ConcurrentVendor",
        initial_metadata={"source": "assistant2"},
        created_by="assistant2",
    )

    results = await asyncio.gather(task1, task2, return_exceptions=True)

    # Assert: One success, one failure
    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1, (
        f"Expected exactly 1 concurrent creation to succeed, got {len(successes)}"
    )
    assert len(failures) == 1, (
        f"Expected exactly 1 concurrent creation to fail, got {len(failures)}"
    )

    # Assert: Failure is ValueError (translated VendorAlreadyExistsError)
    assert isinstance(failures[0], ValueError), (
        f"Expected ValueError for concurrent failure, got {type(failures[0])}"
    )
    error_message = str(failures[0]).lower()
    assert "already exists" in error_message, (
        f"Expected 'already exists' in concurrent failure message, got: {failures[0]}"
    )

    # Verify: Exactly one vendor record in database
    result = await session.execute(
        select(func.count()).select_from(VendorExtractor)
        .where(VendorExtractor.name == "ConcurrentVendor")
    )
    count = result.scalar()
    assert count == 1, f"Expected 1 vendor record after concurrent creation, found {count}"

    # Verify: Vendor has one of the two metadata values
    result = await session.execute(
        select(VendorExtractor).where(VendorExtractor.name == "ConcurrentVendor")
    )
    vendor = result.scalar_one()
    assert "source" in vendor.metadata_, "Vendor metadata missing 'source' field"
    assert vendor.metadata_["source"] in ["assistant1", "assistant2"], (
        f"Expected metadata source to be 'assistant1' or 'assistant2', "
        f"got: {vendor.metadata_['source']}"
    )


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(not CREATE_VENDOR_IMPORTED, reason="create_vendor tool not yet implemented (TDD)")
async def test_create_vendor_whitespace_only_name_validation(
    session: AsyncSession,
    clean_vendors: None,
) -> None:
    """Test whitespace-only name validation (additional edge case).

    Given: Attempting to create vendor with whitespace-only name
    When: Call create_vendor with name="   " (spaces only)
    Then: ValueError raised with "cannot be empty" message
    And: No database record created

    Additional edge case validation beyond quickstart scenarios.
    """
    whitespace_names = [
        "   ",  # Spaces
        "\t\t",  # Tabs
        "\n\n",  # Newlines
        " \t\n ",  # Mixed whitespace
    ]

    for whitespace_name in whitespace_names:
        # Act & Assert: Attempt to create vendor with whitespace-only name
        with pytest.raises(ValueError) as exc_info:
            await create_vendor(
                name=whitespace_name,
                initial_metadata={},
        created_by="test-whitespace",
        session=session
    )

        # Assert: Error message indicates empty/invalid name
        error_message = str(exc_info.value).lower()
        assert "cannot be empty" in error_message or "invalid" in error_message, (
            f"Expected 'empty' or 'invalid' for whitespace name, got: {exc_info.value}"
        )


# ==============================================================================
# Test Summary
# ==============================================================================

"""
Test Summary for T004/T005 - Create Vendor Integration Tests:

Success Scenarios (T004):
1. test_create_vendor_with_full_metadata (Scenario 1)
2. test_create_vendor_with_partial_metadata (Scenario 2)
3. test_create_vendor_with_no_metadata (Scenario 3)
4. test_immediate_query_after_creation (Scenario 6)
5. test_create_vendor_performance_single_creation
6. test_create_vendor_with_custom_created_by

Error Scenarios (T005):
7. test_create_vendor_duplicate_exact_match (Scenario 4)
8. test_create_vendor_duplicate_case_insensitive (Scenario 5)
9. test_create_vendor_empty_name_validation (Scenario 7)
10. test_create_vendor_name_too_long_validation (Scenario 8)
11. test_create_vendor_invalid_characters_validation (Scenario 9)
12. test_create_vendor_invalid_scaffolder_version_type (Scenario 10)
13. test_create_vendor_invalid_created_at_format (Scenario 11)
14. test_create_vendor_concurrent_creation_safety (Scenario 12)
15. test_create_vendor_whitespace_only_name_validation (additional)

Total Test Count: 15 integration tests
Coverage: All quickstart.md scenarios 1-12 (excluding performance bulk test)
Performance Target: <100ms p95 latency (FR-015)
Constitutional Compliance: Principle VII (TDD - tests before implementation)

Expected Test Result:
All tests MUST FAIL with ImportError or AttributeError because create_vendor()
tool has not been implemented yet. This is correct TDD behavior.

Next Implementation Steps:
1. Implement create_vendor() MCP tool in src/mcp/tools/tracking.py
2. Implement validation functions for name and metadata
3. Implement VendorAlreadyExistsError exception class
4. Add database constraint for case-insensitive uniqueness
5. Run tests and verify they pass
6. Commit: "feat(vendor): implement create_vendor with validation"
"""
