"""Pytest fixtures for integration tests.

Provides shared test fixtures for integration testing:
- test_engine: Async database engine for test database (function scope)
- session: Async database session with automatic rollback (function scope)
- clean_database: Fixture to reset database between tests

Integration tests require a running PostgreSQL database with
the test schema created by migrations.

Fixture Architecture:
- All async fixtures use function scope to avoid event loop conflicts
- Each test gets fresh engine + session with isolated transaction
- Session automatically rolls back after test for isolation
- Database schema created once per test (teardown drops tables)

Constitutional Compliance:
- Principle VII: TDD (comprehensive test infrastructure)
- Principle VIII: Type safety (type-annotated fixtures)
"""

from __future__ import annotations

import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.models.database import Base


@pytest.fixture(scope="session")
def database_url() -> str:
    """Get test database URL from environment or use default.

    Returns:
        PostgreSQL connection string for test database

    Note:
        Session scope is safe for non-async fixtures that return config values
    """
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/codebase_mcp_test",
    )


@pytest_asyncio.fixture(scope="function")
async def test_engine(database_url: str) -> AsyncGenerator[AsyncEngine, None]:
    """Create async database engine for tests.

    **IMPORTANT**: Function-scoped to avoid event loop conflicts.
    Each test gets its own engine with fresh event loop.

    Args:
        database_url: PostgreSQL connection string

    Yields:
        Configured AsyncEngine instance

    Cleanup:
        Disposes engine connection pool and drops all tables

    Fixture Pattern:
        - Function scope prevents "different loop" errors
        - Each test creates schema, runs test, drops schema
        - Ensures complete test isolation
    """
    test_engine = create_async_engine(
        database_url,
        echo=False,  # Disable SQL logging in tests
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )

    # Create all tables
    async with test_engine.begin() as conn:
        # Import ALL models to register them with Base.metadata
        from src.models.task import WorkItem, Task  # noqa: F401
        from src.models.task_relations import (  # noqa: F401
            TaskBranchLink,
            TaskCommitLink,
            TaskPlanningReference,
            TaskStatusHistory,
        )
        from src.models.tracking import (  # noqa: F401
            ArchivedWorkItem,
            DeploymentEvent,
            FutureEnhancement,
            ProjectConfiguration,
            VendorDeploymentLink,
            VendorExtractor,
            WorkItemDependency,
            WorkItemDeploymentLink,
        )
        from src.models.indexing_job import IndexingJob  # noqa: F401

        # Install pgvector extension
        await conn.execute(sqlalchemy.text("CREATE EXTENSION IF NOT EXISTS vector"))

        await conn.run_sync(Base.metadata.create_all)

    yield test_engine

    # Cleanup: Drop all tables and dispose engine
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest.fixture(scope="function")
def test_session_factory(test_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Provide test-specific session factory for creating multiple sessions.

    **Use Case**: Tests that need to simulate multiple concurrent clients,
    each with their own database session.

    Args:
        test_engine: Test database engine (function-scoped)

    Returns:
        async_sessionmaker that creates sessions bound to test engine

    Usage in Tests (Concurrent Client Pattern):
        >>> async def test_concurrent_updates(
        ...     test_session_factory: async_sessionmaker[AsyncSession]
        ... ) -> None:
        ...     # Client A session
        ...     async with test_session_factory() as db1:
        ...         await update_work_item(session=db1, ...)
        ...         await db1.commit()
        ...
        ...     # Client B session
        ...     async with test_session_factory() as db2:
        ...         await update_work_item(session=db2, ...)
        ...         await db2.commit()

    Note:
        - All sessions created by this factory use the test engine
        - No event loop conflicts (engine is function-scoped)
        - Each session should be used in a context manager
        - Test isolation via test_engine fixture (drops tables after test)
    """
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Keep objects usable after commit
    )


@pytest_asyncio.fixture(scope="function")
async def session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for tests with automatic rollback.

    **Transaction Isolation Pattern**:
    - Creates new session WITHOUT explicit transaction block
    - Tests and fixtures can commit as needed
    - Automatically rolls back ALL changes after test
    - Provides complete test isolation

    Args:
        test_engine: Test database engine (function-scoped)

    Yields:
        AsyncSession instance for database operations

    Cleanup:
        Rolls back any pending transaction and closes session

    Usage in Tests:
        >>> async def test_something(session: AsyncSession) -> None:
        ...     # Add test data
        ...     session.add(WorkItem(...))
        ...     await session.commit()  # Commits to database
        ...
        ...     # Test assertions
        ...     assert ...
        ...
        ...     # Automatic rollback after test completes

    Usage in Fixtures:
        >>> @pytest.fixture
        ... async def test_data(session: AsyncSession) -> WorkItem:
        ...     item = WorkItem(...)
        ...     session.add(item)
        ...     await session.commit()  # Required to flush to DB
        ...     await session.refresh(item)  # Get DB-generated fields
        ...     return item

    Note:
        This pattern allows fixtures and tests to commit freely, but
        ensures all changes are rolled back at test end via table truncation
        in the test_engine fixture (drops/recreates schema).
    """
    # Create session factory
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Keep objects usable after commit
    )

    # Create session WITHOUT transaction block to allow commits
    async with async_session_factory() as test_session:
        try:
            yield test_session
        finally:
            # Rollback any pending transaction
            if test_session.in_transaction():
                await test_session.rollback()
            # Close session
            await test_session.close()


@pytest_asyncio.fixture
async def clean_database(test_engine: AsyncEngine) -> None:
    """Reset database to clean state between tests.

    Drops and recreates all tables. Use this fixture when you need
    a completely clean database state (e.g., testing migrations).

    Args:
        test_engine: Test database engine

    Usage:
        @pytest.mark.usefixtures("clean_database")
        async def test_something(session: AsyncSession) -> None:
            # Test runs with completely clean database
            ...

    Note:
        Most tests don't need this - the session fixture's automatic
        rollback provides sufficient isolation. Only use when you need
        to reset auto-increment sequences or test database creation.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture(autouse=True, scope="function")
async def cleanup_connection_pools() -> AsyncGenerator[None, None]:
    """Clean up module-level connection pools after each test.

    **CRITICAL FIX**: Prevents "Event loop is closed" errors by properly
    closing and resetting module-level connection pools that persist
    across test function boundaries.

    Problem:
        - session.py maintains module-level globals: _registry_pool and _project_pools
        - These pools are bound to the event loop that created them
        - pytest-asyncio creates a NEW event loop for each function-scoped test
        - Old pools become invalid when their event loop closes
        - Next test fails when trying to use pools from closed event loop

    Solution:
        - Run after EVERY test (autouse=True)
        - Close all active connection pools
        - Reset module-level globals to None/empty dict
        - Next test creates fresh pools with new event loop

    Fixture Pattern:
        - autouse=True: Runs automatically for all tests
        - function scope: Runs after each test function
        - Yield-based cleanup: Ensures pools are closed even if test fails

    Args:
        None (autouse fixture)

    Yields:
        None (cleanup happens after yield)

    Note:
        This fixture is REQUIRED for any test that uses:
        - src.database.session._initialize_registry_pool()
        - src.database.session.get_or_create_project_pool()
        - Any MCP tool that creates database connections
    """
    # Run test first (yield allows test to execute)
    yield

    # Cleanup after test completes
    import src.database.session as session_module

    # Close registry pool if it exists
    if session_module._registry_pool is not None:
        await session_module._registry_pool.close()
        session_module._registry_pool = None

    # Close all project pools
    for pool in session_module._project_pools.values():
        await pool.close()

    # Reset project pools dict
    session_module._project_pools.clear()
