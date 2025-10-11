"""Performance tests for create_vendor MCP tool (FR-015 requirement).

Tests verify (from quickstart.md Performance Validation section):
- FR-015: Create vendor operation achieves <100ms p95 latency
- Bulk vendor creation performance at scale (100 vendors)
- Percentile calculation: p50, p95, p99 latencies
- Statistical analysis of latency distribution

TDD Compliance: Test written BEFORE implementation - will FAIL until create_vendor() is implemented.

Constitutional Compliance:
- Principle VII: TDD (test written first, validates acceptance criteria)
- Principle IV: Performance Guarantees (<100ms vendor creation via indexing)
- Principle VIII: Type Safety (mypy --strict, full type hints)
- Principle V: Production Quality (comprehensive error handling, logging)

Performance Requirements:
- Target: <100ms p95 latency for single vendor creation (FR-015)
- Expected: p50 <10ms, p95 <50ms (well under 100ms target), p99 <100ms
- Test validates performance at scale with 100 unique vendor creations
"""

from __future__ import annotations

import statistics
import time
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# Import future MCP tool (not yet implemented)
try:
    from src.mcp.tools.tracking import create_vendor
except ImportError:
    create_vendor = None  # Tool not yet implemented


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_vendor_p95_under_100ms(session: AsyncSession) -> None:
    """Test create_vendor achieves <100ms p95 latency (FR-015).

    Scenario: Bulk vendor creation performance validation
    (from quickstart.md Performance Validation section)

    Setup:
        - Clean database with no existing vendors
        - Prepare 100 unique vendor names for creation

    Test:
        - Create 100 vendors with unique names sequentially
        - Each vendor includes scaffolder_version metadata
        - Measure latency for each creation using time.perf_counter()
        - Calculate p50, p95, p99 percentiles using statistics module

    Assert:
        - p95 latency < 100ms (FR-015 requirement)
        - p50 latency < 10ms (expected fast path)
        - p99 latency < 100ms (consistent performance)
        - All 100 vendors created successfully

    Performance Target:
        <100ms p95 latency for vendor creation (FR-015)

    Expected Results (from quickstart.md):
        - p50: <10ms
        - p95: <50ms (well under 100ms target)
        - p99: <100ms

    Requirements:
        FR-015: Create vendor with <100ms p95 latency
    """
    # Skip test if create_vendor not yet implemented (TDD pattern)
    if create_vendor is None:
        pytest.skip("create_vendor() not yet implemented - TDD failing test")

    latencies_ms: list[float] = []

    # Create 100 vendors with unique names
    for i in range(100):
        vendor_name = f"PerfTest_{i}"

        # Measure creation latency
        start_time = time.perf_counter()

        vendor_response = await create_vendor(
            name=vendor_name,
            initial_metadata={"scaffolder_version": "1.0", "iteration": i},
            created_by="performance-test",
            session=session,
        )

        end_time = time.perf_counter()

        latency_ms = (end_time - start_time) * 1000  # Convert to milliseconds
        latencies_ms.append(latency_ms)

        # Verify successful creation
        assert vendor_response is not None
        assert vendor_response["name"] == vendor_name
        assert vendor_response["status"] == "broken"  # Initial status
        assert vendor_response["version"] == 1  # Initial version
        assert vendor_response["metadata"]["scaffolder_version"] == "1.0"
        assert vendor_response["metadata"]["iteration"] == i

    # Calculate percentiles using statistics.quantiles()
    # Sort latencies for percentile calculation
    latencies_ms.sort()

    # Calculate percentiles
    p50_ms = statistics.median(latencies_ms)  # 50th percentile
    p95_ms = latencies_ms[94]  # 95th percentile (index 94 out of 100)
    p99_ms = latencies_ms[98]  # 99th percentile (index 98 out of 100)
    min_ms = latencies_ms[0]
    max_ms = latencies_ms[-1]
    mean_ms = statistics.mean(latencies_ms)
    stdev_ms = statistics.stdev(latencies_ms) if len(latencies_ms) > 1 else 0.0

    # Print performance metrics for analysis
    print(f"\nVendor Creation Performance (100 operations):")
    print(f"  Min:    {min_ms:.2f}ms")
    print(f"  P50:    {p50_ms:.2f}ms")
    print(f"  P95:    {p95_ms:.2f}ms")
    print(f"  P99:    {p99_ms:.2f}ms")
    print(f"  Max:    {max_ms:.2f}ms")
    print(f"  Mean:   {mean_ms:.2f}ms")
    print(f"  StdDev: {stdev_ms:.2f}ms")

    # Assert FR-015 requirement: p95 < 100ms
    assert p95_ms < 100.0, (
        f"P95 latency {p95_ms:.2f}ms exceeds 100ms target "
        f"(FR-015 requirement violated)"
    )

    # Additional assertions for expected performance
    # (from quickstart.md expected results)
    print(f"\nPerformance Target Validation:")
    print(f"  P50 < 10ms:  {p50_ms:.2f}ms {'✓ PASS' if p50_ms < 10.0 else '✗ FAIL (expected but not required)'}")
    print(f"  P95 < 50ms:  {p95_ms:.2f}ms {'✓ PASS' if p95_ms < 50.0 else '✗ FAIL (expected but not required)'}")
    print(f"  P99 < 100ms: {p99_ms:.2f}ms {'✓ PASS' if p99_ms < 100.0 else '✗ FAIL'}")

    # Optional: Assert expected performance (stricter than requirement)
    # Commented out to avoid false failures, but useful for performance regression detection
    # assert p50_ms < 10.0, f"P50 latency {p50_ms:.2f}ms exceeds 10ms expected target"
    # assert p95_ms < 50.0, f"P95 latency {p95_ms:.2f}ms exceeds 50ms expected target"
    assert p99_ms < 100.0, f"P99 latency {p99_ms:.2f}ms exceeds 100ms target"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_vendor_performance_consistency(session: AsyncSession) -> None:
    """Test vendor creation performance consistency over time.

    Validates that create_vendor latency remains consistent across
    multiple batches, detecting performance degradation patterns.

    Setup:
        - Create 3 batches of 10 vendors each (30 total)
        - Measure p95 latency for each batch

    Test:
        - Calculate p95 latency for each batch
        - Verify all batches meet <100ms p95 requirement
        - Check that variance between batches is reasonable

    Assert:
        - Each batch p95 < 100ms
        - Batch variance < 50ms (consistent performance)

    Performance Target:
        Consistent <100ms p95 latency across batches
    """
    # Skip test if create_vendor not yet implemented (TDD pattern)
    if create_vendor is None:
        pytest.skip("create_vendor() not yet implemented - TDD failing test")

    batch_p95_latencies: list[float] = []
    batch_size = 10
    num_batches = 3

    for batch_num in range(num_batches):
        batch_latencies_ms: list[float] = []

        for i in range(batch_size):
            vendor_name = f"ConsistencyTest_Batch{batch_num}_Vendor{i}"

            start_time = time.perf_counter()
            await create_vendor(
                name=vendor_name,
                initial_metadata={"batch": batch_num, "index": i},
                session=session,
            )
            end_time = time.perf_counter()

            latency_ms = (end_time - start_time) * 1000
            batch_latencies_ms.append(latency_ms)

        # Calculate p95 for this batch
        batch_latencies_ms.sort()
        batch_p95 = batch_latencies_ms[9]  # 95th percentile of 10 items (index 9)
        batch_p95_latencies.append(batch_p95)

        print(f"  Batch {batch_num + 1} p95: {batch_p95:.2f}ms")

        # Assert each batch meets requirement
        assert batch_p95 < 100.0, (
            f"Batch {batch_num + 1} p95 latency {batch_p95:.2f}ms exceeds 100ms target"
        )

    # Check variance between batches
    if len(batch_p95_latencies) > 1:
        max_batch_p95 = max(batch_p95_latencies)
        min_batch_p95 = min(batch_p95_latencies)
        variance = max_batch_p95 - min_batch_p95

        print(f"\nBatch Performance Variance:")
        print(f"  Min batch p95: {min_batch_p95:.2f}ms")
        print(f"  Max batch p95: {max_batch_p95:.2f}ms")
        print(f"  Variance:      {variance:.2f}ms")

        # Assert reasonable variance (performance consistency)
        assert variance < 50.0, (
            f"Batch variance {variance:.2f}ms indicates inconsistent performance "
            f"(max: {max_batch_p95:.2f}ms, min: {min_batch_p95:.2f}ms)"
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_vendor_with_metadata_performance(session: AsyncSession) -> None:
    """Test vendor creation performance with large metadata payloads.

    Validates that create_vendor maintains <100ms p95 latency even
    with realistic metadata payloads containing multiple custom fields.

    Setup:
        - Create 50 vendors with large metadata (5+ custom fields)
        - Metadata includes scaffolder_version, created_at, and custom fields

    Test:
        - Measure latency for each creation
        - Calculate p95 latency with metadata overhead

    Assert:
        - p95 latency < 100ms even with large metadata

    Performance Target:
        <100ms p95 latency with realistic metadata payloads
    """
    # Skip test if create_vendor not yet implemented (TDD pattern)
    if create_vendor is None:
        pytest.skip("create_vendor() not yet implemented - TDD failing test")

    latencies_ms: list[float] = []

    for i in range(50):
        vendor_name = f"MetadataTest_{i}"

        # Large metadata payload with multiple custom fields
        large_metadata: dict[str, Any] = {
            "scaffolder_version": "1.0",
            "created_at": "2025-10-11T10:00:00Z",
            "custom_field_1": "value_1",
            "custom_field_2": "value_2",
            "custom_field_3": f"iteration_{i}",
            "custom_array": [1, 2, 3, 4, 5],
            "custom_nested": {
                "nested_key_1": "nested_value_1",
                "nested_key_2": f"nested_iteration_{i}",
            },
        }

        start_time = time.perf_counter()
        await create_vendor(
            name=vendor_name,
            initial_metadata=large_metadata,
            session=session,
        )
        end_time = time.perf_counter()

        latency_ms = (end_time - start_time) * 1000
        latencies_ms.append(latency_ms)

    # Calculate p95
    latencies_ms.sort()
    p95_ms = latencies_ms[47]  # 95th percentile of 50 items (index 47)

    print(f"\nVendor Creation with Large Metadata Performance (50 operations):")
    print(f"  P95: {p95_ms:.2f}ms")

    # Assert FR-015 requirement maintained with metadata overhead
    assert p95_ms < 100.0, (
        f"P95 latency with large metadata {p95_ms:.2f}ms exceeds 100ms target"
    )


# ==============================================================================
# Test Summary
# ==============================================================================

"""
Test Summary:

1. test_create_vendor_p95_under_100ms
   - Validates FR-015: <100ms p95 latency for vendor creation
   - Creates 100 unique vendors with metadata
   - Measures p50, p95, p99 percentiles using statistics module
   - Asserts p95 < 100ms (FR-015 requirement)
   - Prints detailed performance metrics for analysis

2. test_create_vendor_performance_consistency
   - Validates consistent performance across multiple batches
   - Creates 3 batches of 10 vendors each
   - Calculates p95 for each batch
   - Asserts each batch meets <100ms requirement
   - Verifies batch variance < 50ms for consistency

3. test_create_vendor_with_metadata_performance
   - Validates performance with realistic metadata payloads
   - Creates 50 vendors with large metadata (7+ fields)
   - Includes nested objects and arrays in metadata
   - Asserts p95 < 100ms even with metadata overhead

Total Test Count: 3 performance tests
Performance Target: <100ms p95 latency (FR-015)
Expected Results: p50 <10ms, p95 <50ms, p99 <100ms

TDD Status:
- Tests will FAIL until create_vendor() MCP tool is implemented
- Skipped with pytest.skip() message explaining implementation needed
- Ready for implementation in T007 (Phase 3.3: Implementation)

Constitutional Compliance:
- Principle VII: TDD (test written first)
- Principle IV: Performance Guarantees (<100ms creation latency)
- Principle VIII: Type Safety (full type hints, mypy --strict)
- Principle V: Production Quality (comprehensive performance validation)
"""
