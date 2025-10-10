"""Integration tests for vendor query performance (Scenario 1 from quickstart.md).

Tests verify (from quickstart.md and spec.md):
- FR-002: Query vendor status in <1ms p95 latency
- Unique index on vendor_extractors.name enables <1ms lookups
- VendorResponse includes test_results, format_support, version
- Performance target: Single vendor query by name in <1ms (p95)

TDD Compliance: Tests validate acceptance criteria with comprehensive performance measurement.

Constitutional Compliance:
- Principle VII: TDD (integration test validates acceptance criteria)
- Principle IV: Performance Guarantees (<1ms vendor queries via unique index)
- Principle VIII: Type Safety (mypy --strict, full type hints)
"""

from __future__ import annotations

import statistics
import time
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.tracking import VendorExtractor
from src.services.vendor import get_vendor_by_name

# Import Pydantic schemas from contracts
import sys
from pathlib import Path

specs_contracts_path = (
    Path(__file__).parent.parent.parent
    / "specs"
    / "003-database-backed-project"
    / "contracts"
)
if specs_contracts_path.exists() and str(specs_contracts_path) not in sys.path:
    sys.path.insert(0, str(specs_contracts_path))

from pydantic_schemas import VendorMetadata, VendorStatus  # type: ignore


@pytest.fixture
async def seeded_vendors(session: AsyncSession) -> list[VendorExtractor]:
    """Seed database with 45 vendors with realistic metadata.

    Creates 45 vendor extractors with varied operational status,
    test results, and format support to simulate production data.

    Args:
        session: Async database session

    Returns:
        List of 45 created VendorExtractor instances

    Notes:
        - Vendor names: vendor_001 through vendor_045
        - Mix of operational (80%) and broken (20%) vendors
        - Varied test pass rates: 85-95% passing
        - Varied format support across vendors
    """
    vendors: list[VendorExtractor] = []

    for i in range(1, 46):  # Create 45 vendors
        vendor_name = f"vendor_{i:03d}"

        # 80% operational, 20% broken
        is_operational = i % 5 != 0
        status = "operational" if is_operational else "broken"

        # Test results: 85-95% pass rate
        total_tests = 50
        passing_tests = total_tests - (i % 8)  # 42-50 passing
        skipped_tests = min(i % 4, total_tests - passing_tests)  # 0-3 skipped

        # Format support: varied capabilities
        format_support = {
            "excel": i % 2 == 0,  # 50% support Excel
            "csv": i % 3 != 0,    # 67% support CSV
            "pdf": i % 4 == 0,    # 25% support PDF
            "ocr": i % 5 == 0,    # 20% support OCR
        }

        # Create metadata
        metadata = VendorMetadata(
            format_support=format_support,
            test_results={
                "passing": passing_tests,
                "total": total_tests,
                "skipped": skipped_tests,
            },
            extractor_version=f"2.{i % 5}.{i % 10}",
            manifest_compliant=i % 7 != 0,  # ~86% compliant
        )

        vendor = VendorExtractor(
            id=uuid4(),
            version=1,
            name=vendor_name,
            status=status,
            extractor_version=metadata.extractor_version,
            metadata_=metadata.model_dump(),
            created_by="test-fixture",
        )

        session.add(vendor)
        vendors.append(vendor)

    await session.commit()

    # Refresh to get database-generated fields
    for vendor in vendors:
        await session.refresh(vendor)

    return vendors


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_vendor_by_name_p95_under_1ms(
    session: AsyncSession, seeded_vendors: list[VendorExtractor]
) -> None:
    """Test vendor query by name achieves <1ms p95 latency (FR-002).

    Scenario: Query vendor status in <1ms (quickstart scenario 1)

    Setup:
        - 45 vendors seeded with metadata (via seeded_vendors fixture)
        - Unique index on vendor_extractors.name for fast lookups

    Test:
        - Query first vendor by name 100 times
        - Measure latency for each query using time.perf_counter()
        - Calculate p50, p95, p99 percentiles

    Assert:
        - p95 latency < 1ms (1000 microseconds)
        - All queries return correct vendor data
        - VendorResponse includes test_results, format_support, version

    Performance Target:
        <1ms p95 latency for single vendor query by name (FR-002)

    Requirements:
        FR-002: Query vendor status with <1ms latency
    """
    # Select first vendor for repeated queries
    target_vendor = seeded_vendors[0]
    vendor_name = target_vendor.name

    # Run 100 queries and measure latency
    latencies_us: list[float] = []  # Microseconds

    for _ in range(100):
        start_time = time.perf_counter()
        vendor = await get_vendor_by_name(vendor_name, session)
        end_time = time.perf_counter()

        latency_us = (end_time - start_time) * 1_000_000  # Convert to microseconds
        latencies_us.append(latency_us)

        # Verify correct vendor returned
        assert vendor.id == target_vendor.id
        assert vendor.name == vendor_name
        assert vendor.status == target_vendor.status

    # Calculate percentiles
    latencies_us.sort()
    p50_us = statistics.median(latencies_us)
    p95_us = latencies_us[94]  # 95th percentile (index 94 out of 100)
    p99_us = latencies_us[98]  # 99th percentile (index 98 out of 100)
    min_us = latencies_us[0]
    max_us = latencies_us[-1]

    # Convert to milliseconds for assertion and reporting
    p95_ms = p95_us / 1000

    # Print performance metrics for analysis
    print(f"\nVendor Query Performance (100 queries):")
    print(f"  Min: {min_us:.1f}µs ({min_us/1000:.3f}ms)")
    print(f"  P50: {p50_us:.1f}µs ({p50_us/1000:.3f}ms)")
    print(f"  P95: {p95_us:.1f}µs ({p95_us/1000:.3f}ms)")
    print(f"  P99: {p99_us:.1f}µs ({p99_us/1000:.3f}ms)")
    print(f"  Max: {max_us:.1f}µs ({max_us/1000:.3f}ms)")

    # Assert p95 < 1ms (1000 microseconds)
    assert p95_ms < 1.0, (
        f"P95 latency {p95_ms:.3f}ms exceeds 1ms target "
        f"(measured: {p95_us:.1f}µs)"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vendor_response_schema_compliance(
    session: AsyncSession, seeded_vendors: list[VendorExtractor]
) -> None:
    """Test that VendorResponse includes all required fields.

    Verifies vendor response schema compliance with MCP contract:
    - id: UUID
    - version: int (optimistic locking)
    - name: str (unique vendor name)
    - status: VendorStatus (operational|broken)
    - extractor_version: str (semantic version)
    - metadata: VendorMetadata with:
        - test_results: dict[str, int] (passing, total, skipped)
        - format_support: dict[str, bool] (excel, csv, pdf, ocr)
        - extractor_version: str (matches top-level field)
        - manifest_compliant: bool
    - created_at: datetime
    - updated_at: datetime
    - created_by: str (AI client identifier)

    Requirements:
        FR-003: Vendor metadata storage with Pydantic validation
    """
    # Query vendor by name
    target_vendor = seeded_vendors[0]
    vendor = await get_vendor_by_name(target_vendor.name, session)

    # Verify core fields
    assert vendor.id is not None
    assert isinstance(vendor.version, int)
    assert vendor.version >= 1
    assert vendor.name == target_vendor.name
    assert vendor.status in ["operational", "broken"]
    assert vendor.extractor_version is not None
    assert len(vendor.extractor_version) > 0

    # Verify metadata structure (JSONB)
    assert vendor.metadata_ is not None
    assert isinstance(vendor.metadata_, dict)

    # Verify metadata contains required fields
    metadata = vendor.metadata_
    assert "test_results" in metadata
    assert "format_support" in metadata
    assert "extractor_version" in metadata
    assert "manifest_compliant" in metadata

    # Verify test_results structure
    test_results = metadata["test_results"]
    assert "passing" in test_results
    assert "total" in test_results
    assert "skipped" in test_results
    assert test_results["passing"] >= 0
    assert test_results["total"] >= 0
    assert test_results["skipped"] >= 0
    assert test_results["passing"] <= test_results["total"]

    # Verify format_support structure
    format_support = metadata["format_support"]
    assert "excel" in format_support
    assert "csv" in format_support
    assert "pdf" in format_support
    assert "ocr" in format_support
    assert isinstance(format_support["excel"], bool)
    assert isinstance(format_support["csv"], bool)
    assert isinstance(format_support["pdf"], bool)
    assert isinstance(format_support["ocr"], bool)

    # Verify extractor_version in metadata matches top-level
    assert metadata["extractor_version"] == vendor.extractor_version

    # Verify manifest_compliant is boolean
    assert isinstance(metadata["manifest_compliant"], bool)

    # Verify audit trail fields
    assert vendor.created_at is not None
    assert vendor.updated_at is not None
    assert vendor.created_by is not None
    assert len(vendor.created_by) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_multiple_vendors_performance(
    session: AsyncSession, seeded_vendors: list[VendorExtractor]
) -> None:
    """Test querying multiple different vendors maintains <1ms p95 latency.

    Scenario: Query different vendors in sequence to verify index performance
    across the entire vendor dataset.

    Setup:
        - 45 vendors seeded with metadata

    Test:
        - Query 10 different vendors, 10 times each (100 total queries)
        - Measure latency for each query
        - Calculate p95 latency across all queries

    Assert:
        - p95 latency < 1ms across all vendor queries
        - Unique index performs consistently across dataset

    Performance Target:
        <1ms p95 latency for any vendor query by name
    """
    latencies_us: list[float] = []

    # Query 10 different vendors, 10 times each
    vendors_to_query = seeded_vendors[:10]

    for vendor in vendors_to_query:
        for _ in range(10):
            start_time = time.perf_counter()
            result = await get_vendor_by_name(vendor.name, session)
            end_time = time.perf_counter()

            latency_us = (end_time - start_time) * 1_000_000
            latencies_us.append(latency_us)

            # Verify correct vendor returned
            assert result.id == vendor.id

    # Calculate p95 across all queries
    latencies_us.sort()
    p95_us = latencies_us[94]  # 95th percentile
    p95_ms = p95_us / 1000

    print(f"\nMulti-Vendor Query Performance (100 queries, 10 vendors):")
    print(f"  P95: {p95_us:.1f}µs ({p95_ms:.3f}ms)")

    # Assert p95 < 1ms
    assert p95_ms < 1.0, (
        f"P95 latency {p95_ms:.3f}ms exceeds 1ms target "
        f"across multiple vendor queries"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vendor_metadata_validation_with_pydantic(
    session: AsyncSession, seeded_vendors: list[VendorExtractor]
) -> None:
    """Test that vendor metadata can be validated with Pydantic VendorMetadata schema.

    Verifies that JSONB metadata stored in database conforms to
    VendorMetadata Pydantic schema for type-safe access.

    Requirements:
        FR-003: Vendor metadata storage with Pydantic validation
        Principle VIII: Type Safety (Pydantic-based validation)
    """
    # Query vendor
    vendor = await get_vendor_by_name(seeded_vendors[0].name, session)

    # Validate metadata with Pydantic schema
    try:
        validated_metadata = VendorMetadata.model_validate(vendor.metadata_)
    except Exception as e:
        pytest.fail(f"Vendor metadata failed Pydantic validation: {e}")

    # Verify Pydantic model fields are accessible
    assert validated_metadata.format_support is not None
    assert validated_metadata.test_results is not None
    assert validated_metadata.extractor_version is not None
    assert validated_metadata.manifest_compliant is not None

    # Verify type safety
    assert isinstance(validated_metadata.format_support, dict)
    assert isinstance(validated_metadata.test_results, dict)
    assert isinstance(validated_metadata.extractor_version, str)
    assert isinstance(validated_metadata.manifest_compliant, bool)

    # Verify field constraints
    assert len(validated_metadata.extractor_version) > 0
    assert len(validated_metadata.extractor_version) <= 50
    assert validated_metadata.test_results["passing"] >= 0
    assert validated_metadata.test_results["total"] >= 0
    assert validated_metadata.test_results["passing"] <= validated_metadata.test_results["total"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vendor_status_filtering_operational(
    session: AsyncSession, seeded_vendors: list[VendorExtractor]
) -> None:
    """Test filtering vendors by operational status.

    Verifies that vendor queries can be filtered by status for
    operational health monitoring use cases.

    Expected:
        - ~80% of vendors are operational (36 out of 45)
        - ~20% of vendors are broken (9 out of 45)
    """
    from sqlalchemy import select

    # Count operational vendors
    stmt = select(VendorExtractor).where(VendorExtractor.status == "operational")
    result = await session.execute(stmt)
    operational_vendors = list(result.scalars().all())

    # Count broken vendors
    stmt = select(VendorExtractor).where(VendorExtractor.status == "broken")
    result = await session.execute(stmt)
    broken_vendors = list(result.scalars().all())

    # Verify distribution (80% operational, 20% broken)
    assert len(operational_vendors) == 36, f"Expected 36 operational vendors, got {len(operational_vendors)}"
    assert len(broken_vendors) == 9, f"Expected 9 broken vendors, got {len(broken_vendors)}"
    assert len(operational_vendors) + len(broken_vendors) == 45

    # Verify all operational vendors have correct status
    for vendor in operational_vendors:
        assert vendor.status == "operational"

    # Verify all broken vendors have correct status
    for vendor in broken_vendors:
        assert vendor.status == "broken"


# ==============================================================================
# Test Summary
# ==============================================================================

"""
Test Summary:

1. test_query_vendor_by_name_p95_under_1ms
   - Validates FR-002: <1ms p95 latency for vendor queries
   - Queries single vendor 100 times
   - Measures p50, p95, p99 percentiles
   - Asserts p95 < 1ms

2. test_vendor_response_schema_compliance
   - Validates FR-003: Vendor metadata structure
   - Verifies all required fields present
   - Validates test_results, format_support, version
   - Ensures VendorResponse schema compliance

3. test_query_multiple_vendors_performance
   - Validates consistent <1ms performance across dataset
   - Queries 10 different vendors, 10 times each
   - Verifies unique index performs uniformly

4. test_vendor_metadata_validation_with_pydantic
   - Validates Pydantic VendorMetadata schema compliance
   - Ensures type-safe metadata access
   - Verifies field constraints and validation

5. test_vendor_status_filtering_operational
   - Validates vendor status filtering capability
   - Verifies operational/broken distribution
   - Ensures indexed status queries work correctly

Total Test Count: 5 integration tests
Performance Target: <1ms p95 latency (FR-002)
Constitutional Compliance: Principle VII (TDD), Principle IV (Performance), Principle VIII (Type Safety)
"""
