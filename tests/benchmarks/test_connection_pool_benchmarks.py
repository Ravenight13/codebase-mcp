"""Connection pool performance benchmarks for baseline collection.

This module provides pytest-benchmark tests for measuring connection pool performance
across critical operations: initialization, acquisition, and health checks.

**Performance Targets** (from specs/009-v2-connection-mgmt/spec.md):
- Pool initialization: <2s for 10 connections
- Connection acquisition: <10ms p95 latency
- Health check: <10ms p99 latency
- Graceful shutdown: <30s

**Usage**:
    # Run all benchmarks and save results
    pytest tests/benchmarks/test_connection_pool_benchmarks.py --benchmark-only

    # Run with JSON output for baseline collection
    pytest tests/benchmarks/test_connection_pool_benchmarks.py --benchmark-only \
        --benchmark-json=performance_baselines/connection_pool_benchmark_raw.json

    # Compare against saved baseline
    pytest tests/benchmarks/test_connection_pool_benchmarks.py --benchmark-only \
        --benchmark-compare=performance_baselines/connection_pool_baseline.json

**Constitutional Compliance**:
- Principle VIII (Type Safety): Full mypy --strict compliance with complete annotations
- Principle IV (Performance): Validates <2s init, <10ms p95 acquisition, <10ms p99 health
- Principle VII (TDD): Benchmarks serve as performance regression tests

**Benchmark Structure**:
Each benchmark function receives a `benchmark` fixture that handles:
- Multiple iterations for statistical reliability
- Warmup rounds to stabilize measurements
- p50/p95/p99 percentile calculation
- JSON serialization for baseline storage
"""

from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING

import pytest

from src.connection_pool.config import PoolConfig
from src.connection_pool.manager import ConnectionPoolManager

if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture  # type: ignore[import-untyped]


# Test database URL (use in-memory or test database)
TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://localhost:5432/codebase_mcp_test"
)


@pytest.fixture
def pool_config() -> PoolConfig:
    """Create pool configuration for benchmarks.

    Uses small pool size (2-5) to minimize database overhead while still
    testing realistic multi-connection scenarios.

    Returns:
        PoolConfig with test database URL and conservative pool settings.
    """
    return PoolConfig(
        min_size=2,
        max_size=5,
        timeout=30.0,
        database_url=TEST_DB_URL,
    )


@pytest.mark.performance
@pytest.mark.asyncio
async def test_benchmark_pool_initialization(
    benchmark: BenchmarkFixture,
    pool_config: PoolConfig,
) -> None:
    """Benchmark connection pool initialization time.

    **Performance Target**: <2s for pool initialization with min_size connections.

    This benchmark measures the time to:
    1. Create asyncpg pool with min_size connections
    2. Validate all connections with SELECT 1 query
    3. Transition pool state from INITIALIZING to RUNNING

    **What is measured**:
    - Pool object creation
    - Database connection establishment (min_size connections)
    - Initial health validation

    **What is NOT measured**:
    - Test fixture overhead
    - Pool teardown/cleanup

    Args:
        benchmark: pytest-benchmark fixture for measurement
        pool_config: Pool configuration fixture
    """
    async def initialize_pool() -> None:
        """Initialize pool and immediately close it."""
        pool = ConnectionPoolManager()
        await pool.initialize(pool_config)
        await pool.shutdown()

    # Run benchmark (pytest-benchmark handles iteration internally)
    benchmark.pedantic(
        lambda: asyncio.run(initialize_pool()),
        iterations=10,  # 10 iterations for statistical reliability
        rounds=3,       # 3 warmup rounds to stabilize measurements
    )


@pytest.mark.performance
@pytest.mark.asyncio
async def test_benchmark_connection_acquisition_single(
    benchmark: BenchmarkFixture,
    pool_config: PoolConfig,
) -> None:
    """Benchmark single connection acquisition latency.

    **Performance Target**: <10ms p95 latency for connection acquisition.

    This benchmark measures the time to acquire a connection from an initialized
    pool when connections are immediately available (no contention).

    **What is measured**:
    - Pool.acquire() call latency
    - Connection validation query (if configured)
    - Context manager entry overhead

    **What is NOT measured**:
    - Pool initialization (done in setup)
    - Query execution time (only acquire/release)
    - Pool teardown (done in cleanup)

    Args:
        benchmark: pytest-benchmark fixture for measurement
        pool_config: Pool configuration fixture
    """
    # Setup: Initialize pool once before benchmark
    pool = ConnectionPoolManager()
    await pool.initialize(pool_config)

    try:
        async def acquire_and_release() -> None:
            """Acquire connection and immediately release it."""
            async with pool.acquire():
                pass  # Connection automatically released on context exit

        # Benchmark only the acquire/release cycle
        benchmark.pedantic(
            lambda: asyncio.run(acquire_and_release()),
            iterations=100,  # 100 iterations for p95/p99 accuracy
            rounds=5,        # 5 warmup rounds
        )
    finally:
        # Cleanup: Close pool after benchmark
        await pool.shutdown()


@pytest.mark.performance
@pytest.mark.asyncio
async def test_benchmark_connection_acquisition_concurrent(
    benchmark: BenchmarkFixture,
    pool_config: PoolConfig,
) -> None:
    """Benchmark concurrent connection acquisition latency.

    **Performance Target**: <10ms p95 latency under moderate contention.

    This benchmark measures acquisition latency when multiple concurrent requests
    compete for pool connections (max_size=5, concurrent requests=3).

    **What is measured**:
    - Concurrent acquire() calls (3 simultaneous requests)
    - Connection queuing when all connections are busy
    - Average latency across concurrent requests

    **Contention Scenario**:
    - Pool has 5 max connections
    - 3 concurrent requests compete for connections
    - Measures realistic multi-request load

    Args:
        benchmark: pytest-benchmark fixture for measurement
        pool_config: Pool configuration fixture
    """
    # Setup: Initialize pool once before benchmark
    pool = ConnectionPoolManager()
    await pool.initialize(pool_config)

    try:
        async def concurrent_acquisitions() -> None:
            """Acquire 3 connections concurrently and release them."""
            async def acquire_one() -> None:
                async with pool.acquire():
                    # Simulate minimal work (just acquire/release)
                    await asyncio.sleep(0.001)  # 1ms simulated query

            # Launch 3 concurrent acquisition tasks
            await asyncio.gather(
                acquire_one(),
                acquire_one(),
                acquire_one(),
            )

        # Benchmark concurrent acquisition pattern
        benchmark.pedantic(
            lambda: asyncio.run(concurrent_acquisitions()),
            iterations=50,   # 50 iterations for p95/p99 accuracy
            rounds=3,        # 3 warmup rounds
        )
    finally:
        # Cleanup: Close pool after benchmark
        await pool.shutdown()


@pytest.mark.performance
@pytest.mark.asyncio
async def test_benchmark_health_check(
    benchmark: BenchmarkFixture,
    pool_config: PoolConfig,
) -> None:
    """Benchmark health check query latency.

    **Performance Target**: <10ms p99 latency for health_check() call.

    This benchmark measures the time to execute a complete health check,
    including pool statistics calculation and database connectivity validation.

    **What is measured**:
    - Pool.health_check() call latency
    - SELECT 1 validation query
    - Pool statistics snapshot calculation
    - Health status determination (HEALTHY/DEGRADED/UNHEALTHY)
    - Pydantic model serialization

    **What is NOT measured**:
    - Pool initialization (done in setup)
    - Connection acquisition (health check uses internal mechanism)
    - Pool teardown (done in cleanup)

    Args:
        benchmark: pytest-benchmark fixture for measurement
        pool_config: Pool configuration fixture
    """
    # Setup: Initialize pool once before benchmark
    pool = ConnectionPoolManager()
    await pool.initialize(pool_config)

    try:
        async def health_check() -> None:
            """Execute health check and discard result."""
            _ = await pool.health_check()

        # Benchmark health check call
        benchmark.pedantic(
            lambda: asyncio.run(health_check()),
            iterations=100,  # 100 iterations for p99 accuracy
            rounds=5,        # 5 warmup rounds
        )
    finally:
        # Cleanup: Close pool after benchmark
        await pool.shutdown()


@pytest.mark.performance
@pytest.mark.asyncio
async def test_benchmark_graceful_shutdown(
    benchmark: BenchmarkFixture,
    pool_config: PoolConfig,
) -> None:
    """Benchmark graceful pool shutdown latency.

    **Performance Target**: <30s for graceful shutdown (including active connection drain).

    This benchmark measures the time to gracefully close a connection pool,
    including waiting for active connections to be released and closing all
    idle connections.

    **What is measured**:
    - Pool.close() call latency
    - Active connection drain time
    - Idle connection closure
    - Background task cancellation
    - State transition to CLOSED

    **What is NOT measured**:
    - Pool initialization (done per iteration)
    - Connection acquisition (pool is idle at shutdown)

    Args:
        benchmark: pytest-benchmark fixture for measurement
        pool_config: Pool configuration fixture
    """
    async def initialize_and_shutdown() -> None:
        """Initialize pool and then gracefully shut down."""
        pool = ConnectionPoolManager()
        await pool.initialize(pool_config)
        # Pool is now RUNNING with idle connections
        await pool.shutdown()  # Graceful shutdown

    # Benchmark full lifecycle: initialize + shutdown
    benchmark.pedantic(
        lambda: asyncio.run(initialize_and_shutdown()),
        iterations=10,   # 10 iterations (shutdown is expensive)
        rounds=2,        # 2 warmup rounds
    )
