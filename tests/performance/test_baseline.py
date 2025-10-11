"""Baseline performance tests for MCP server indexing and search.

Measures baseline performance metrics before the multi-project refactor to ensure
no performance regressions are introduced. Uses pytest-benchmark for reliable
performance measurements.

Usage:
    # Install pytest-benchmark first:
    pip install pytest-benchmark

    # Run baseline tests:
    pytest tests/performance/test_baseline.py --benchmark-only --benchmark-json=baseline-results.json

    # Parse results:
    python scripts/parse_baseline.py baseline-results.json

Constitutional Compliance:
- Principle IV: Performance (60s indexing, <500ms p95 search latency)
- Principle VIII: Type Safety (mypy --strict compliance)
- Principle V: Production Quality (comprehensive benchmarking)

Requirements:
- pytest-benchmark must be installed: pip install pytest-benchmark
- Test repository must be generated: python scripts/generate_test_repo.py --files 100
- Database must be initialized: python scripts/init_db.py
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture

# ==============================================================================
# Test Configuration
# ==============================================================================

TEST_REPO_PATH = Path("test_repos/baseline_repo")
SEARCH_QUERY = "function process data validation"

# Performance targets from constitutional principles
INDEXING_TARGET_SECONDS = 60.0
SEARCH_TARGET_MS = 500.0

# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture(scope="module")
def test_repo_path() -> Path:
    """Provide path to test repository.

    Returns:
        Path to baseline test repository

    Raises:
        pytest.skip: If test repository doesn't exist
    """
    if not TEST_REPO_PATH.exists():
        pytest.skip(
            f"Test repository not found at {TEST_REPO_PATH}. "
            f"Generate with: python scripts/generate_test_repo.py --files 100 --output {TEST_REPO_PATH}"
        )
    return TEST_REPO_PATH


@pytest.fixture(scope="module")
def event_loop() -> asyncio.AbstractEventLoop:
    """Create event loop for async tests.

    Returns:
        New event loop instance
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==============================================================================
# Baseline Performance Tests
# ==============================================================================


@pytest.mark.benchmark
@pytest.mark.performance
@pytest.mark.asyncio
async def test_indexing_baseline(
    test_repo_path: Path,
    benchmark: BenchmarkFixture,
) -> None:
    """Benchmark repository indexing performance.

    Measures the time to index a test repository with 100 Python files,
    establishing a baseline before the multi-project refactor.

    This test:
    1. Imports the MCP indexing tool
    2. Indexes the test repository
    3. Measures total execution time
    4. Asserts performance < 60 seconds target

    Args:
        test_repo_path: Path to test repository fixture
        benchmark: pytest-benchmark fixture for measurements
    """
    # Import here to avoid import-time side effects
    from src.mcp.tools.indexing import index_repository

    async def run_indexing() -> dict[str, Any]:
        """Run indexing operation.

        Returns:
            Indexing result dictionary
        """
        result = await index_repository(
            repo_path=str(test_repo_path.absolute()),
            force_reindex=True,  # Force full reindex for consistent baseline
            ctx=None,  # No context needed for benchmarking
        )
        return result

    # Run benchmark with async wrapper
    def sync_wrapper() -> dict[str, Any]:
        """Synchronous wrapper for async function.

        Returns:
            Indexing result from async operation
        """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(run_indexing())

    # Execute benchmark
    result = benchmark(sync_wrapper)

    # Validate result structure
    assert isinstance(result, dict)
    assert "repository_id" in result
    assert "files_indexed" in result
    assert "chunks_created" in result
    assert "duration_seconds" in result
    assert "status" in result

    # Validate performance
    duration = result["duration_seconds"]
    assert duration < INDEXING_TARGET_SECONDS, (
        f"Indexing took {duration:.2f}s, exceeding target of {INDEXING_TARGET_SECONDS}s"
    )

    # Log results for reference
    print(f"\n[INDEXING BASELINE]")
    print(f"  Files indexed: {result['files_indexed']}")
    print(f"  Chunks created: {result['chunks_created']}")
    print(f"  Duration: {duration:.2f}s")
    print(f"  Status: {result['status']}")


@pytest.mark.benchmark
@pytest.mark.performance
@pytest.mark.asyncio
async def test_search_baseline(
    test_repo_path: Path,
    benchmark: BenchmarkFixture,
) -> None:
    """Benchmark semantic search performance.

    Measures the latency of semantic code search, establishing a baseline
    before the multi-project refactor.

    This test:
    1. Ensures repository is indexed
    2. Performs semantic search
    3. Measures search latency
    4. Asserts performance < 500ms p95 target

    Args:
        test_repo_path: Path to test repository fixture
        benchmark: pytest-benchmark fixture for measurements

    Note:
        This test assumes the repository was already indexed by test_indexing_baseline.
        If running independently, ensure repository is indexed first.
    """
    # Import here to avoid import-time side effects
    from src.mcp.tools.indexing import index_repository
    from src.mcp.tools.search import search_code

    # Ensure repository is indexed (idempotent if already indexed)
    await index_repository(
        repo_path=str(test_repo_path.absolute()),
        force_reindex=False,  # Don't reindex if already indexed
        ctx=None,
    )

    async def run_search() -> dict[str, Any]:
        """Run search operation.

        Returns:
            Search result dictionary
        """
        result = await search_code(
            query=SEARCH_QUERY,
            repository_id=None,  # Search all repositories
            limit=10,
            ctx=None,  # No context needed for benchmarking
        )
        return result

    # Run benchmark with async wrapper
    def sync_wrapper() -> dict[str, Any]:
        """Synchronous wrapper for async function.

        Returns:
            Search result from async operation
        """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(run_search())

    # Execute benchmark
    result = benchmark(sync_wrapper)

    # Validate result structure
    assert isinstance(result, dict)
    assert "results" in result
    assert "total_count" in result
    assert "latency_ms" in result

    # Validate performance
    latency_ms = result["latency_ms"]
    assert latency_ms < SEARCH_TARGET_MS, (
        f"Search took {latency_ms}ms, exceeding target of {SEARCH_TARGET_MS}ms"
    )

    # Log results for reference
    print(f"\n[SEARCH BASELINE]")
    print(f"  Query: {SEARCH_QUERY}")
    print(f"  Results: {result['total_count']}")
    print(f"  Latency: {latency_ms}ms")


# ==============================================================================
# Test Markers and Configuration
# ==============================================================================

pytestmark = [
    pytest.mark.benchmark,
    pytest.mark.performance,
]
