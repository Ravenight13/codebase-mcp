"""Search performance benchmarks for codebase-mcp.

This module provides pytest-benchmark tests for measuring semantic code search
performance with concurrent client simulation.

**Performance Targets** (from specs/011-performance-validation-multi/spec.md):
- Search query latency: <500ms p95 with 10 concurrent clients (FR-002)
- Constitutional target: <500ms p95 (Principle IV)
- Baseline comparison: Within 10% of pre-split baseline (FR-005)

**Usage**:
    # Run search benchmarks only
    pytest tests/benchmarks/test_search_perf.py --benchmark-only

    # Save results for baseline collection
    pytest tests/benchmarks/test_search_perf.py --benchmark-only \
        --benchmark-json=performance_baselines/search_benchmark_raw.json

    # Compare against saved baseline
    pytest tests/benchmarks/test_search_perf.py --benchmark-only \
        --benchmark-compare=docs/performance/baseline-pre-split.json

**Constitutional Compliance**:
- Principle VIII (Type Safety): Full mypy --strict compliance
- Principle IV (Performance): Validates <500ms p95 search latency
- Principle VII (TDD): Benchmark serves as performance regression test

**Benchmark Structure**:
Each benchmark function receives a `benchmark` fixture that:
- Executes multiple iterations for statistical reliability
- Performs warmup rounds to stabilize measurements
- Calculates p50/p95/p99 percentiles automatically
- Serializes results to JSON for baseline storage
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING

import pytest

from src.models.performance import PerformanceBenchmarkResult
from src.services.searcher import SearchFilter, search_code

if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture  # type: ignore[import-untyped]
    from sqlalchemy.ext.asyncio import AsyncSession


# Test database URL (use test database)
TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://localhost:5432/codebase_mcp_test"
)


@pytest.fixture
async def indexed_repository(
    db_session: AsyncSession,
    large_test_repository: Path,
) -> Path:
    """Ensure test repository is indexed before benchmarking.

    This fixture indexes a test repository once per test session to provide
    consistent search performance measurement baseline.

    Args:
        db_session: Async database session fixture
        large_test_repository: Path to test repository fixture (10k files)

    Returns:
        Path to indexed repository

    Note:
        This fixture assumes large_test_repository fixture is available from
        tests/fixtures/test_repository.py. If indexing is not complete,
        benchmark tests will be skipped.
    """
    # Skip until indexing is implemented
    pytest.skip("Repository indexing not implemented yet (requires T013 completion)")


@pytest.fixture
def concurrent_search_queries() -> list[str]:
    """Generate diverse search queries for concurrent client simulation.

    Returns list of 100 diverse queries covering common code search patterns:
    - Function searches
    - Class searches
    - Data structure searches
    - Algorithm searches
    - Error handling searches

    Returns:
        List of 100 search query strings
    """
    base_queries = [
        # Function searches
        "calculate average of numbers",
        "find maximum value in list",
        "filter positive numbers",
        "process data and return sum",
        "transform data with multiplier",
        # Class searches
        "data processor class",
        "initialize processor with name",
        "add value to data list",
        # Algorithm searches
        "sorting algorithm implementation",
        "binary search function",
        # Error handling
        "exception handling and logging",
        "error recovery mechanism",
        # Data structures
        "linked list implementation",
        "hash table structure",
        # Common patterns
        "authentication logic",
        "database connection handling",
        "configuration management",
        "file parsing utility",
        "validation function",
        "serialization method",
    ]
    # Replicate to get 100 total queries (5 * 20 = 100)
    return base_queries * 5


@pytest.mark.performance
@pytest.mark.asyncio
async def test_benchmark_search_single_client(
    benchmark: BenchmarkFixture,
    indexed_repository: Path,
    db_session: AsyncSession,
) -> None:
    """Benchmark search latency with single client (baseline).

    **Performance Target**: <500ms p95 latency for single client.

    This benchmark measures search latency without concurrency to establish
    a baseline for comparison with concurrent client tests.

    **What is measured**:
    - Query embedding generation (Ollama API call)
    - Pgvector cosine similarity search (HNSW index)
    - Result ranking and limiting
    - Context extraction (lines before/after)

    **What is NOT measured**:
    - Repository indexing (done in fixture setup)
    - Database connection establishment (done in fixture)
    - Test fixture overhead

    Args:
        benchmark: pytest-benchmark fixture for measurement
        indexed_repository: Pre-indexed test repository fixture
        db_session: Async database session fixture
    """
    query = "calculate average of numbers"
    search_filter = SearchFilter(limit=10)

    async def single_search() -> None:
        """Execute single search query."""
        _ = await search_code(
            query=query,
            db=db_session,
            filters=search_filter,
        )

    # Benchmark single search query
    benchmark.pedantic(
        lambda: asyncio.run(single_search()),
        iterations=100,  # 100 iterations for p95/p99 accuracy
        rounds=5,        # 5 warmup rounds
    )


@pytest.mark.performance
@pytest.mark.asyncio
async def test_benchmark_search_10_concurrent_clients(
    benchmark: BenchmarkFixture,
    indexed_repository: Path,
    db_session: AsyncSession,
    concurrent_search_queries: list[str],
) -> None:
    """Benchmark search latency with 10 concurrent clients.

    **Performance Target**: <500ms p95 latency with 10 concurrent clients (FR-002).

    This benchmark simulates the constitutional requirement of handling 10
    concurrent search clients while maintaining sub-500ms p95 latency.

    **What is measured**:
    - 10 concurrent search queries executing simultaneously
    - Database connection pool contention
    - Pgvector index performance under concurrent load
    - Average latency across all concurrent queries

    **Concurrency Scenario**:
    - 10 clients issue queries simultaneously
    - Each query uses independent database connection
    - Measures realistic multi-user load

    **Constitutional Compliance**:
    - FR-002: <500ms p95 latency with 10 concurrent clients
    - Principle IV: Performance guarantees under concurrent load

    Args:
        benchmark: pytest-benchmark fixture for measurement
        indexed_repository: Pre-indexed test repository fixture
        db_session: Async database session fixture
        concurrent_search_queries: List of diverse search queries
    """
    search_filter = SearchFilter(limit=10)

    async def concurrent_searches() -> None:
        """Execute 10 concurrent search queries."""
        async def search_task(query: str) -> None:
            """Execute single search query."""
            _ = await search_code(
                query=query,
                db=db_session,
                filters=search_filter,
            )

        # Select 10 diverse queries from the pool
        queries = concurrent_search_queries[:10]

        # Execute 10 concurrent searches
        await asyncio.gather(*[search_task(q) for q in queries])

    # Benchmark concurrent search pattern
    benchmark.pedantic(
        lambda: asyncio.run(concurrent_searches()),
        iterations=20,   # 20 iterations for p95 accuracy with concurrency
        rounds=3,        # 3 warmup rounds
    )


@pytest.mark.performance
@pytest.mark.asyncio
async def test_benchmark_search_latency_percentiles(
    benchmark: BenchmarkFixture,
    indexed_repository: Path,
    db_session: AsyncSession,
    concurrent_search_queries: list[str],
) -> None:
    """Benchmark search with detailed percentile measurement.

    **Performance Target**: <500ms p95 latency, comprehensive percentile tracking.

    This benchmark executes 100 search queries sequentially to collect
    comprehensive latency distribution data for percentile calculation.

    **Measured Percentiles**:
    - p50 (median): Typical user experience
    - p95: Constitutional requirement (<500ms)
    - p99: Worst-case performance (excluding outliers)
    - min/max: Full latency range

    **Constitutional Compliance**:
    - FR-002: <500ms p95 latency validation
    - FR-022: Mandatory p50/p95/p99 reporting

    Args:
        benchmark: pytest-benchmark fixture for measurement
        indexed_repository: Pre-indexed test repository fixture
        db_session: Async database session fixture
        concurrent_search_queries: List of diverse search queries
    """
    search_filter = SearchFilter(limit=10)

    async def measure_search_latencies() -> list[float]:
        """Execute 100 searches and collect individual latencies.

        Returns:
            List of latencies in milliseconds
        """
        latencies: list[float] = []

        for query in concurrent_search_queries:
            start_time = perf_counter()
            _ = await search_code(
                query=query,
                db=db_session,
                filters=search_filter,
            )
            latency_ms = (perf_counter() - start_time) * 1000
            latencies.append(latency_ms)

        return latencies

    # Run benchmark (collect latencies for analysis)
    result = benchmark.pedantic(
        lambda: asyncio.run(measure_search_latencies()),
        iterations=5,    # 5 iterations (each processes 100 queries)
        rounds=1,        # 1 warmup round
    )

    # Validate constitutional target after benchmark completes
    # Note: pytest-benchmark calculates percentiles automatically
    # Access via result.stats.percentiles after benchmark completes


@pytest.mark.performance
@pytest.mark.asyncio
async def test_search_performance_validation(
    indexed_repository: Path,
    db_session: AsyncSession,
    concurrent_search_queries: list[str],
) -> None:
    """Validate search performance meets constitutional targets.

    **Performance Target**: <500ms p95 latency with 10 concurrent clients (FR-002).

    This test (NOT a benchmark) validates that search performance meets
    constitutional requirements by:
    1. Running 100 search queries with 10 concurrent clients (10 rounds)
    2. Collecting latency measurements for each query
    3. Calculating p50/p95/p99 percentiles
    4. Asserting p95 < 500ms constitutional target
    5. Creating PerformanceBenchmarkResult for regression tracking

    **Constitutional Compliance**:
    - FR-002: <500ms p95 latency with 10 concurrent clients
    - FR-022: Report p50/p95/p99 latencies
    - Principle IV: Performance guarantees validation

    Args:
        indexed_repository: Pre-indexed test repository fixture
        db_session: Async database session fixture
        concurrent_search_queries: List of diverse search queries
    """
    search_filter = SearchFilter(limit=10)
    latencies: list[float] = []

    # Execute 10 rounds of 10 concurrent queries (100 total queries)
    for round_num in range(10):
        queries = concurrent_search_queries[round_num * 10:(round_num + 1) * 10]

        async def search_with_latency(query: str) -> float:
            """Execute search and return latency in milliseconds."""
            start_time = perf_counter()
            _ = await search_code(
                query=query,
                db=db_session,
                filters=search_filter,
            )
            return (perf_counter() - start_time) * 1000

        # Execute 10 concurrent searches
        round_latencies = await asyncio.gather(
            *[search_with_latency(q) for q in queries]
        )
        latencies.extend(round_latencies)

    # Calculate percentiles
    latencies_sorted = sorted(latencies)
    p50_index = len(latencies_sorted) // 2
    p95_index = int(len(latencies_sorted) * 0.95)
    p99_index = int(len(latencies_sorted) * 0.99)

    p50_ms = Decimal(str(round(latencies_sorted[p50_index], 2)))
    p95_ms = Decimal(str(round(latencies_sorted[p95_index], 2)))
    p99_ms = Decimal(str(round(latencies_sorted[p99_index], 2)))
    mean_ms = Decimal(str(round(sum(latencies) / len(latencies), 2)))
    min_ms = Decimal(str(round(min(latencies), 2)))
    max_ms = Decimal(str(round(max(latencies), 2)))

    # Create performance benchmark result
    result = PerformanceBenchmarkResult(
        benchmark_id=str(uuid.uuid4()),
        server_id="codebase-mcp",
        operation_type="search",
        timestamp=datetime.now(timezone.utc),
        latency_p50_ms=p50_ms,
        latency_p95_ms=p95_ms,
        latency_p99_ms=p99_ms,
        latency_mean_ms=mean_ms,
        latency_min_ms=min_ms,
        latency_max_ms=max_ms,
        sample_size=len(latencies),
        test_parameters={
            "concurrent_clients": 10,
            "total_queries": 100,
            "rounds": 10,
            "queries_per_round": 10,
            "result_limit": 10,
        },
        pass_status="pass" if p95_ms < Decimal("500.0") else "fail",
        target_threshold_ms=Decimal("500.0"),
    )

    # Constitutional validation: Assert p95 < 500ms
    assert result.pass_status == "pass", (
        f"Search p95 latency {p95_ms}ms exceeds 500ms constitutional target "
        f"(FR-002 violation)"
    )

    # Log performance metrics for debugging
    print(f"\nSearch Performance Metrics:")
    print(f"  Sample size: {result.sample_size} queries")
    print(f"  P50 latency: {p50_ms}ms")
    print(f"  P95 latency: {p95_ms}ms (target: <500ms)")
    print(f"  P99 latency: {p99_ms}ms")
    print(f"  Mean latency: {mean_ms}ms")
    print(f"  Range: {min_ms}ms - {max_ms}ms")
    print(f"  Concurrent clients: 10")
    print(f"  Pass status: {result.pass_status}")


@pytest.mark.performance
@pytest.mark.asyncio
async def test_search_filter_performance(
    indexed_repository: Path,
    db_session: AsyncSession,
) -> None:
    """Benchmark search performance with various filter combinations.

    **Performance Target**: <500ms p95 latency with filters applied.

    This test validates that search filters (repository, file type, directory)
    do not significantly degrade search performance.

    **Filter Scenarios**:
    - No filters (baseline)
    - File type filter (e.g., "py")
    - Directory filter (e.g., "src/%")
    - Combined filters (file type + directory)

    Args:
        indexed_repository: Pre-indexed test repository fixture
        db_session: Async database session fixture
    """
    query = "calculate average"

    async def search_with_filters(filters: SearchFilter) -> float:
        """Execute search with filters and return latency."""
        start_time = perf_counter()
        _ = await search_code(
            query=query,
            db=db_session,
            filters=filters,
        )
        return (perf_counter() - start_time) * 1000

    # Test various filter combinations
    filter_scenarios = [
        ("no_filters", SearchFilter(limit=10)),
        ("file_type_py", SearchFilter(limit=10, file_type="py")),
        ("directory_src", SearchFilter(limit=10, directory="src/%")),
        ("combined_filters", SearchFilter(limit=10, file_type="py", directory="src/%")),
    ]

    results: dict[str, list[float]] = {}

    for scenario_name, filters in filter_scenarios:
        latencies: list[float] = []
        for _ in range(20):  # 20 iterations per scenario
            latency_ms = await search_with_filters(filters)
            latencies.append(latency_ms)

        results[scenario_name] = latencies

        # Calculate p95 for scenario
        latencies_sorted = sorted(latencies)
        p95_ms = latencies_sorted[int(len(latencies_sorted) * 0.95)]

        # Validate p95 < 500ms for all scenarios
        assert p95_ms < 500.0, (
            f"Search with {scenario_name} has p95 latency {p95_ms:.0f}ms "
            f"exceeding 500ms target"
        )

    # Log comparative results
    print(f"\nFilter Performance Comparison:")
    for scenario_name, latencies in results.items():
        p95_ms = sorted(latencies)[int(len(latencies) * 0.95)]
        print(f"  {scenario_name}: p95={p95_ms:.0f}ms")
