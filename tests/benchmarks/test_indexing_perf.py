"""Indexing performance benchmarks for codebase-mcp.

This module provides pytest-benchmark tests for measuring indexing performance
of the codebase-mcp server against constitutional performance targets.

**Performance Targets** (from specs/011-performance-validation-multi/spec.md):
- FR-001: Index 10,000 files in <60s (p95) across 5 consecutive runs

**Constitutional Compliance**:
- Principle VIII: Type Safety (full mypy --strict compliance)
- Principle IV: Performance Guarantees (<60s p95 for 10,000 files)
- Principle VII: TDD (benchmarks serve as performance regression tests)

**Usage**:
    # Run indexing benchmarks only
    pytest tests/benchmarks/test_indexing_perf.py --benchmark-only

    # Save results to JSON baseline
    pytest tests/benchmarks/test_indexing_perf.py --benchmark-only \
        --benchmark-json=performance_baselines/indexing_benchmark.json

    # Compare against baseline
    pytest tests/benchmarks/test_indexing_perf.py --benchmark-only \
        --benchmark-compare=performance_baselines/indexing_baseline.json

**Benchmark Structure**:
- Uses pytest-benchmark fixture with pedantic mode for accurate measurements
- 5 iterations with 1 warmup round (per FR-001 requirements)
- Validates against constitutional target: <60s (60,000ms) p95 latency
- Returns PerformanceBenchmarkResult model for validation
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.performance import PerformanceBenchmarkResult
from src.services.indexer import index_repository
from tests.fixtures.test_repository import generate_benchmark_repository

if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture  # type: ignore[import-untyped]


# ==============================================================================
# Constants
# ==============================================================================

# Constitutional target from FR-001
CONSTITUTIONAL_TARGET_MS: Decimal = Decimal("60000.0")  # 60 seconds = 60,000ms

# Test parameters from FR-001
BENCHMARK_ITERATIONS: int = 5
WARMUP_ROUNDS: int = 1
TARGET_FILE_COUNT: int = 10_000


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest_asyncio.fixture(scope="function")
async def benchmark_repository(tmp_path: Path) -> Path:
    """Generate 10,000-file benchmark repository for performance testing.

    Uses test_repository fixtures to create realistic codebase with:
    - 10,000 files (60% Python, 40% JavaScript)
    - File sizes: 100 bytes to 50KB
    - Directory depth: up to 5 levels
    - Code complexity: functions, classes, imports

    Args:
        tmp_path: pytest tmp_path fixture (function-scoped)

    Returns:
        Path to generated repository root

    Note:
        Function-scoped to ensure each test gets fresh repository.
        Generation may take ~10 seconds for 10,000 files.
    """
    repo_path = generate_benchmark_repository(base_path=tmp_path)
    return repo_path


# ==============================================================================
# Helper Functions
# ==============================================================================


async def _run_indexing(repo_path: Path, session: AsyncSession) -> float:
    """Run indexing operation and return duration in seconds.

    This is the core operation being benchmarked. It performs:
    1. Repository scanning (file discovery)
    2. Change detection (or force reindex)
    3. File chunking with AST parsing
    4. Embedding generation via Ollama
    5. Database persistence

    Args:
        repo_path: Path to repository to index
        session: Database session for persistence

    Returns:
        Duration in seconds (from IndexResult.duration_seconds)

    Raises:
        RuntimeError: If indexing fails
    """
    result = await index_repository(
        repo_path=repo_path,
        name="benchmark_repo",
        db=session,
        force_reindex=True,  # Force full reindex for consistent benchmarking
    )

    if result.status == "failed":
        raise RuntimeError(f"Indexing failed: {result.errors}")

    return result.duration_seconds


def _create_benchmark_result(
    benchmark_stats: dict[str, float],
    test_parameters: dict[str, str | int | float],
) -> PerformanceBenchmarkResult:
    """Create PerformanceBenchmarkResult from pytest-benchmark statistics.

    Converts pytest-benchmark stats dict to Pydantic model for validation
    against constitutional targets.

    Args:
        benchmark_stats: Statistics from pytest-benchmark (stats dict)
        test_parameters: Test configuration (file_count, iterations, etc.)

    Returns:
        PerformanceBenchmarkResult with all latency percentiles

    Note:
        - All latencies converted from seconds to milliseconds
        - Uses Decimal for precision (Constitutional Principle VIII)
    """
    # Extract percentiles from benchmark stats (in seconds)
    # pytest-benchmark stores as fractions, multiply by 1000 for milliseconds
    stats = benchmark_stats

    # Get percentiles (default to 0 if not available)
    p50_s = stats.get("median", 0.0)
    p95_s = stats.get("q95", 0.0)
    p99_s = stats.get("q99", 0.0)
    mean_s = stats.get("mean", 0.0)
    min_s = stats.get("min", 0.0)
    max_s = stats.get("max", 0.0)

    # Convert to milliseconds with Decimal precision
    latency_p50_ms = Decimal(str(p50_s * 1000))
    latency_p95_ms = Decimal(str(p95_s * 1000))
    latency_p99_ms = Decimal(str(p99_s * 1000))
    latency_mean_ms = Decimal(str(mean_s * 1000))
    latency_min_ms = Decimal(str(min_s * 1000))
    latency_max_ms = Decimal(str(max_s * 1000))

    # Determine pass status
    if latency_p95_ms < CONSTITUTIONAL_TARGET_MS:
        pass_status = "pass"
    elif latency_p95_ms < CONSTITUTIONAL_TARGET_MS * Decimal("1.1"):
        pass_status = "warning"
    else:
        pass_status = "fail"

    # Extract iterations as int for sample_size
    iterations = test_parameters.get("iterations", BENCHMARK_ITERATIONS)
    if not isinstance(iterations, int):
        iterations = int(iterations)

    return PerformanceBenchmarkResult(
        benchmark_id=str(uuid4()),
        server_id="codebase-mcp",
        operation_type="index",
        timestamp=datetime.utcnow(),
        latency_p50_ms=latency_p50_ms,
        latency_p95_ms=latency_p95_ms,
        latency_p99_ms=latency_p99_ms,
        latency_mean_ms=latency_mean_ms,
        latency_min_ms=latency_min_ms,
        latency_max_ms=latency_max_ms,
        sample_size=iterations,
        test_parameters=test_parameters,
        pass_status=pass_status,  # type: ignore[arg-type]
        target_threshold_ms=CONSTITUTIONAL_TARGET_MS,
    )


# ==============================================================================
# Benchmark Tests
# ==============================================================================


@pytest.mark.benchmark(group="indexing")
@pytest.mark.asyncio
async def test_indexing_10k_files_performance(
    benchmark: BenchmarkFixture,
    benchmark_repository: Path,
    session: AsyncSession,
) -> None:
    """Benchmark indexing performance for 10,000-file repository.

    Validates FR-001: System MUST validate that codebase-mcp indexing completes
    in under 60 seconds (p95) for a 10,000-file repository across 5 consecutive
    benchmark runs.

    **What is measured**:
    - File scanning and change detection
    - AST-based code chunking
    - Embedding generation via Ollama
    - Database persistence (chunks + embeddings)

    **What is NOT measured**:
    - Test fixture setup (repository generation)
    - Database schema creation
    - Session/engine initialization

    **Performance Target**:
    - p95 latency < 60,000ms (60 seconds)
    - 5 iterations with 1 warmup round
    - Constitutional compliance required

    Args:
        benchmark: pytest-benchmark fixture
        benchmark_repository: Generated 10,000-file repository
        session: Database session for indexing

    Raises:
        AssertionError: If p95 latency exceeds constitutional target
    """

    def run_sync() -> float:
        """Synchronous wrapper for async indexing operation.

        pytest-benchmark requires synchronous callable, so we use
        asyncio.run to execute the async indexing function.

        Returns:
            Duration in seconds
        """
        return asyncio.run(_run_indexing(benchmark_repository, session))

    # Run benchmark with pedantic mode for accurate measurements
    result = benchmark.pedantic(
        run_sync,
        iterations=BENCHMARK_ITERATIONS,
        warmup_rounds=WARMUP_ROUNDS,
        rounds=1,  # 1 round per iteration (each round is expensive)
    )

    # Extract statistics from benchmark result
    stats = result.stats.as_dict()

    # Create PerformanceBenchmarkResult for validation
    test_params: dict[str, str | int | float] = {
        "file_count": TARGET_FILE_COUNT,
        "iterations": BENCHMARK_ITERATIONS,
        "warmup_rounds": WARMUP_ROUNDS,
        "force_reindex": 1,  # Use int for bool (1 = True)
    }

    perf_result = _create_benchmark_result(stats, test_params)

    # Validate against constitutional target
    assert perf_result.latency_p95_ms < CONSTITUTIONAL_TARGET_MS, (
        f"Indexing p95 {perf_result.latency_p95_ms}ms exceeds "
        f"constitutional target {CONSTITUTIONAL_TARGET_MS}ms (60 seconds)"
    )

    # Log result details for analysis
    print(f"\n{'=' * 60}")
    print(f"Indexing Performance Benchmark Results")
    print(f"{'=' * 60}")
    print(f"File Count:    {TARGET_FILE_COUNT:,}")
    print(f"Iterations:    {BENCHMARK_ITERATIONS}")
    print(f"Warmup Rounds: {WARMUP_ROUNDS}")
    print(f"")
    print(f"Latency Statistics (milliseconds):")
    print(f"  p50 (median): {perf_result.latency_p50_ms:>10.2f} ms")
    print(f"  p95:          {perf_result.latency_p95_ms:>10.2f} ms")
    print(f"  p99:          {perf_result.latency_p99_ms:>10.2f} ms")
    print(f"  mean:         {perf_result.latency_mean_ms:>10.2f} ms")
    print(f"  min:          {perf_result.latency_min_ms:>10.2f} ms")
    print(f"  max:          {perf_result.latency_max_ms:>10.2f} ms")
    print(f"")
    print(f"Constitutional Target: {CONSTITUTIONAL_TARGET_MS} ms (60 seconds)")
    print(f"Status:                {perf_result.pass_status.upper()}")
    print(f"{'=' * 60}\n")


@pytest.mark.benchmark(group="indexing")
@pytest.mark.asyncio
async def test_indexing_variance_validation(
    benchmark: BenchmarkFixture,
    benchmark_repository: Path,
    session: AsyncSession,
) -> None:
    """Validate indexing performance variance is within acceptable limits.

    Validates SC-001: Codebase-mcp indexes 10,000 files in under 60 seconds (p95)
    with less than 5% variance across 5 runs (variance calculated as coefficient
    of variation: standard deviation / mean × 100%).

    **Variance Calculation**:
    - Coefficient of Variation (CV) = (std_dev / mean) × 100%
    - Target: CV < 5% for consistent performance

    Args:
        benchmark: pytest-benchmark fixture
        benchmark_repository: Generated 10,000-file repository
        session: Database session for indexing

    Raises:
        AssertionError: If variance exceeds 5% threshold
    """

    def run_sync() -> float:
        """Synchronous wrapper for async indexing operation."""
        return asyncio.run(_run_indexing(benchmark_repository, session))

    # Run benchmark
    result = benchmark.pedantic(
        run_sync,
        iterations=BENCHMARK_ITERATIONS,
        warmup_rounds=WARMUP_ROUNDS,
        rounds=1,
    )

    # Extract statistics
    stats = result.stats.as_dict()
    mean_s = stats.get("mean", 0.0)
    stddev_s = stats.get("stddev", 0.0)

    # Calculate coefficient of variation (CV)
    if mean_s > 0:
        cv_percent = (stddev_s / mean_s) * 100.0
    else:
        cv_percent = 0.0

    # Validate variance within 5% threshold
    assert cv_percent < 5.0, (
        f"Indexing variance {cv_percent:.2f}% exceeds 5% threshold. "
        f"Mean: {mean_s:.2f}s, StdDev: {stddev_s:.2f}s"
    )

    print(f"\nVariance Validation:")
    print(f"  Mean:                {mean_s:.2f} s")
    print(f"  Standard Deviation:  {stddev_s:.2f} s")
    print(f"  Coefficient of Var:  {cv_percent:.2f}% (target: <5%)")
    print(f"  Status:              {'PASS' if cv_percent < 5.0 else 'FAIL'}\n")
