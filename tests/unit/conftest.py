"""Pytest fixtures for unit tests.

Provides shared test fixtures:
- session: Async database session with automatic cleanup
- engine: Async database engine for test database
- clean_database: Fixture to reset database between tests

Constitutional Compliance:
- Principle VII: TDD (comprehensive test infrastructure)
- Principle VIII: Type safety (type-annotated fixtures)
"""

from __future__ import annotations

import os
from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.models.database import Base


@pytest.fixture(scope="session")
def database_url() -> str:
    """Get test database URL from environment or use default.

    Returns:
        PostgreSQL connection string for test database
    """
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/codebase_mcp_test",
    )


@pytest.fixture(scope="session")
async def engine(database_url: str) -> AsyncGenerator[AsyncEngine, None]:
    """Create async database engine for tests.

    Args:
        database_url: PostgreSQL connection string

    Yields:
        Configured AsyncEngine instance

    Cleanup:
        Disposes engine connection pool
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
        await conn.run_sync(Base.metadata.create_all)

    yield test_engine

    # Cleanup: Drop all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for tests.

    Creates a new session for each test with automatic transaction rollback.

    Args:
        engine: Test database engine

    Yields:
        AsyncSession instance for database operations

    Cleanup:
        Rolls back transaction and closes session
    """
    # Create session factory
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as test_session:
        # Start transaction
        async with test_session.begin():
            yield test_session

            # Rollback transaction after test
            await test_session.rollback()


@pytest.fixture
async def clean_database(engine: AsyncEngine) -> None:
    """Reset database to clean state between tests.

    Drops and recreates all tables.

    Args:
        engine: Test database engine

    Usage:
        @pytest.mark.usefixtures("clean_database")
        async def test_something(session: AsyncSession) -> None:
            # Test runs with clean database
            ...
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
