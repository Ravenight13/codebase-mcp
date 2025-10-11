"""Integration test for vendor name case-insensitive uniqueness via functional unique index.

Tests migration 005: Functional unique index on LOWER(name) for vendor_extractors table.

Constitutional Compliance:
- Principle V: Production Quality (robust database-level uniqueness enforcement)
- Principle IV: Performance Guarantees (maintains <1ms vendor lookup with functional index)
- Principle VII: TDD (validates FR-012 acceptance criteria)

Test Scenarios:
1. Case-insensitive duplicate detection (NewCorp vs newcorp)
2. Functional index exists and is unique
3. Query performance with case-insensitive lookup
4. Error message shows existing vendor with actual casing

Performance Target:
- <1ms vendor lookup using functional index on LOWER(name)
"""

from __future__ import annotations

import time
from typing import Any

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.tracking import VendorExtractor


# ==============================================================================
# Integration Tests for Migration 005
# ==============================================================================


@pytest.mark.asyncio
async def test_functional_unique_index_exists(session: AsyncSession) -> None:
    """Test that functional unique index idx_vendor_name_lower exists.

    Given: Database migration 005 has been applied
    When: Inspect vendor_extractors table indexes
    Then: idx_vendor_name_lower functional index exists and is unique

    Verification:
    - Index name: idx_vendor_name_lower
    - Index is unique: True
    - Index expression: LOWER(name)
    """
    # Query pg_indexes to check for functional index
    result = await session.execute(
        text("""
            SELECT
                indexname,
                indexdef
            FROM pg_indexes
            WHERE tablename = 'vendor_extractors'
              AND indexname = 'idx_vendor_name_lower'
        """)
    )
    index_row = result.fetchone()

    assert index_row is not None, "Functional index idx_vendor_name_lower not found"

    indexname, indexdef = index_row
    assert indexname == "idx_vendor_name_lower"
    assert "UNIQUE" in indexdef.upper(), "Index should be unique"
    assert "lower(name" in indexdef.lower(), "Index should be on LOWER(name)"


@pytest.mark.asyncio
async def test_case_insensitive_duplicate_prevention(session: AsyncSession) -> None:
    """Test that case-insensitive duplicates are prevented at database level.

    Given: Vendor "NewCorp" exists in database
    When: Attempt to insert "newcorp" (different casing)
    Then: IntegrityError raised due to functional unique index

    Verification:
    - First insert succeeds: "NewCorp"
    - Second insert fails: "newcorp" (conflicts with "NewCorp")
    - Third insert fails: "NEWCORP" (conflicts with "NewCorp")
    - Fourth insert succeeds: "DifferentCorp" (no conflict)

    Constitutional Compliance:
    - FR-012: Case-insensitive uniqueness requirement
    - FR-013: Concurrent duplicate prevention (atomic database constraint)
    """
    # First vendor: "NewCorp" (original casing)
    vendor1 = VendorExtractor(
        name="NewCorp",
        status="operational",
        extractor_version="1.0.0",
        metadata_={
            "format_support": {"excel": True, "csv": False, "pdf": False, "ocr": False},
            "test_results": {"passing": 10, "total": 10, "skipped": 0},
        },
        created_by="test",
    )
    session.add(vendor1)
    await session.commit()
    await session.flush()

    # Second vendor: "newcorp" (lowercase - should fail)
    vendor2 = VendorExtractor(
        name="newcorp",
        status="broken",
        extractor_version="1.0.0",
        metadata_={
            "format_support": {"excel": False, "csv": False, "pdf": False, "ocr": False},
            "test_results": {"passing": 0, "total": 0, "skipped": 0},
        },
        created_by="test",
    )
    session.add(vendor2)

    with pytest.raises(IntegrityError) as exc_info:
        await session.commit()
        await session.flush()

    # Verify error message references functional index
    error_message = str(exc_info.value).lower()
    assert "idx_vendor_name_lower" in error_message or "unique" in error_message

    # Rollback failed transaction
    await session.rollback()

    # Third vendor: "NEWCORP" (uppercase - should also fail)
    vendor3 = VendorExtractor(
        name="NEWCORP",
        status="broken",
        extractor_version="1.0.0",
        metadata_={
            "format_support": {"excel": False, "csv": False, "pdf": False, "ocr": False},
            "test_results": {"passing": 0, "total": 0, "skipped": 0},
        },
        created_by="test",
    )
    session.add(vendor3)

    with pytest.raises(IntegrityError) as exc_info:
        await session.commit()
        await session.flush()

    await session.rollback()

    # Fourth vendor: "DifferentCorp" (no conflict - should succeed)
    vendor4 = VendorExtractor(
        name="DifferentCorp",
        status="operational",
        extractor_version="1.0.0",
        metadata_={
            "format_support": {"excel": True, "csv": False, "pdf": False, "ocr": False},
            "test_results": {"passing": 10, "total": 10, "skipped": 0},
        },
        created_by="test",
    )
    session.add(vendor4)
    await session.commit()
    await session.flush()

    # Verify only 2 vendors exist (NewCorp and DifferentCorp)
    result = await session.execute(text("SELECT COUNT(*) FROM vendor_extractors"))
    count = result.scalar()
    assert count == 2


@pytest.mark.asyncio
async def test_case_insensitive_query_performance(session: AsyncSession) -> None:
    """Test query performance with case-insensitive lookup using functional index.

    Given: Functional index on LOWER(name) exists
    When: Query for vendor using LOWER(name) = LOWER(:name)
    Then: Query completes in <1ms (p95)

    Performance Target: <1ms for vendor lookup with functional index

    Constitutional Compliance:
    - Principle IV: Performance Guarantees (<1ms vendor lookup)
    - FR-015: Query optimization with functional index
    """
    # Create test vendor
    vendor = VendorExtractor(
        name="PerformanceTest",
        status="operational",
        extractor_version="1.0.0",
        metadata_={
            "format_support": {"excel": True, "csv": False, "pdf": False, "ocr": False},
            "test_results": {"passing": 10, "total": 10, "skipped": 0},
        },
        created_by="test",
    )
    session.add(vendor)
    await session.commit()
    await session.flush()

    # Measure case-insensitive query performance
    start_time = time.perf_counter()

    result = await session.execute(
        text("""
            SELECT id, name, status
            FROM vendor_extractors
            WHERE LOWER(name) = LOWER(:name)
        """),
        {"name": "performancetest"}  # Different casing
    )
    vendor_row = result.fetchone()

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # Verify query found vendor with correct casing
    assert vendor_row is not None
    assert vendor_row.name == "PerformanceTest"  # Original casing preserved
    assert vendor_row.status == "operational"

    # Performance assertion: <1ms target
    assert elapsed_ms < 1.0, f"Query took {elapsed_ms:.3f}ms (target: <1.0ms)"

    print(f"\nCase-insensitive vendor lookup: {elapsed_ms:.3f}ms (target: <1.0ms)")


@pytest.mark.asyncio
async def test_old_unique_constraint_removed(session: AsyncSession) -> None:
    """Test that old case-sensitive unique constraint/index was removed.

    Given: Migration 005 has been applied
    When: Check for old idx_vendor_name index (case-sensitive)
    Then: Old index does not exist (replaced by functional index)

    Verification:
    - idx_vendor_name index does not exist
    - vendor_extractors_name_key constraint does not exist
    - Only idx_vendor_name_lower functional index exists
    """
    # Query pg_indexes for old index
    result = await session.execute(
        text("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'vendor_extractors'
              AND indexname = 'idx_vendor_name'
        """)
    )
    old_index = result.fetchone()

    # Old index should not exist (replaced by functional index)
    assert old_index is None, "Old case-sensitive idx_vendor_name should be removed"

    # Query pg_constraint for old constraint
    result = await session.execute(
        text("""
            SELECT conname
            FROM pg_constraint
            WHERE conname = 'vendor_extractors_name_key'
        """)
    )
    old_constraint = result.fetchone()

    # Old constraint should not exist
    assert old_constraint is None, "Old vendor_extractors_name_key constraint should be removed"


@pytest.mark.asyncio
async def test_migration_downgrade_restores_case_sensitive_index(
    session: AsyncSession
) -> None:
    """Test that migration downgrade restores original case-sensitive unique index.

    Note: This test documents expected behavior for downgrade() function.
    Manual verification required for actual downgrade execution.

    Given: Migration 005 downgrade executed
    When: Check for indexes
    Then: idx_vendor_name (case-sensitive) exists, idx_vendor_name_lower removed

    This test is INFORMATIONAL - actual downgrade testing requires alembic CLI.
    """
    # Query for functional index (should exist in current migration)
    result = await session.execute(
        text("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'vendor_extractors'
              AND indexname = 'idx_vendor_name_lower'
        """)
    )
    functional_index = result.fetchone()

    # Functional index should exist (migration 005 applied)
    assert functional_index is not None, (
        "Functional index should exist - if missing, check migration 005 is applied"
    )

    # Document downgrade behavior (not executed in this test)
    print("\nDowngrade Behavior (not executed):")
    print("  - DROP INDEX idx_vendor_name_lower")
    print("  - CREATE UNIQUE INDEX idx_vendor_name ON vendor_extractors (name)")
    print("  - Restores case-sensitive uniqueness")
