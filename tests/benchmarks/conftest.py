"""Pytest fixtures for performance benchmark tests.

Provides shared test fixtures for benchmarking codebase-mcp performance:
- test_engine: Async database engine for benchmark database (function scope)
- session: Async database session with automatic rollback (function scope)
- benchmark_repository: Generated 10,000-file test repository

Benchmark tests validate constitutional performance targets:
- FR-001: Index 10,000 files in <60s (p95)
- SC-001: Search latency <500ms (p95)

Constitutional Compliance:
- Principle VII: TDD (performance regression tests)
- Principle VIII: Type safety (type-annotated fixtures)
- Principle IV: Performance guarantees (<60s indexing, <500ms search)

Fixture Architecture:
- All async fixtures use function scope to avoid event loop conflicts
- Each benchmark gets fresh engine + session with isolated transaction
- Session automatically rolls back after benchmark for isolation
- Database schema created once per benchmark (teardown drops tables)
"""

from __future__ import annotations

import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from src.models.database import Base


@pytest.fixture(scope="session")
def database_url() -> str:
    """Get benchmark database URL from environment or use default.

    Returns:
        PostgreSQL connection string for benchmark database

    Note:
        Session scope is safe for non-async fixtures that return config values.
        Uses separate test database to avoid conflicts with development data.
    """
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/codebase_mcp_test",
    )


@pytest_asyncio.fixture(scope="function")
async def test_engine(database_url: str) -> AsyncGenerator[AsyncEngine, None]:
    """Create async database engine for benchmarks.

    **IMPORTANT**: Function-scoped to avoid event loop conflicts.
    Each benchmark gets its own engine with fresh event loop.

    Args:
        database_url: PostgreSQL connection string

    Yields:
        Configured AsyncEngine instance

    Cleanup:
        Disposes engine connection pool and drops all tables

    Fixture Pattern:
        - Function scope prevents "different loop" errors
        - Each benchmark creates schema, runs benchmark, drops schema
        - Ensures complete benchmark isolation
    """
    engine = create_async_engine(
        database_url,
        echo=False,  # Disable SQL logging in benchmarks (reduces noise)
        pool_size=10,  # Larger pool for benchmark concurrency
        max_overflow=20,
        pool_pre_ping=True,
    )

    # Create schema before benchmark
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup: drop all tables and dispose engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for benchmarks with automatic rollback.

    **Transaction Isolation Pattern**:
    - Creates new session WITHOUT explicit transaction block
    - Benchmarks can commit as needed for realistic workflows
    - Automatically rolls back ALL changes after benchmark
    - Provides complete benchmark isolation

    Args:
        test_engine: Benchmark database engine (function-scoped)

    Yields:
        AsyncSession instance for database operations

    Cleanup:
        Rolls back any pending transaction and closes session

    Usage in Benchmarks:
        >>> async def test_indexing_performance(
        ...     benchmark: BenchmarkFixture,
        ...     session: AsyncSession
        ... ) -> None:
        ...     # Run indexing benchmark
        ...     result = await index_repository(repo_path, session)
        ...     # Session automatically rolls back after benchmark

    Note:
        Function scope ensures each benchmark gets fresh session with
        isolated transaction. No cross-contamination between benchmarks.
    """
    # Create session from engine
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        yield session

        # Cleanup: rollback any uncommitted changes
        await session.rollback()
