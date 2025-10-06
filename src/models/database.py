"""Database configuration and session management.

This module provides the core database infrastructure for the MCP server:
- AsyncEngine with asyncpg driver for PostgreSQL
- Base declarative class for all SQLAlchemy models
- Async session factory for database operations
- Connection pooling configuration (20 connections, 10 overflow)

Constitutional Compliance:
- Principle IV: Performance (connection pooling, async operations)
- Principle V: Production quality (proper error handling, type safety)
- Principle VIII: Type safety (mypy --strict compliance)
"""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models.

    All models inherit from this class to enable declarative mapping
    and consistent table structure across the database.
    """
    pass


def create_engine(database_url: str, echo: bool = False) -> AsyncEngine:
    """Create async database engine with connection pooling.

    Args:
        database_url: PostgreSQL connection string (asyncpg driver)
            Format: postgresql+asyncpg://user:pass@host:port/dbname
        echo: Enable SQL query logging for debugging (default: False)

    Returns:
        Configured AsyncEngine with connection pooling

    Connection Pool Configuration:
        - pool_size: 20 connections (main pool)
        - max_overflow: 10 connections (additional on demand)
        - pool_pre_ping: True (validate connections before use)
        - pool_recycle: 3600s (recycle connections after 1 hour)

    Example:
        >>> engine = create_engine("postgresql+asyncpg://user:pass@localhost/mcp")
        >>> async with engine.begin() as conn:
        ...     await conn.execute(text("SELECT 1"))
    """
    return create_async_engine(
        database_url,
        echo=echo,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
    )


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create async session factory for database operations.

    Args:
        engine: Configured AsyncEngine instance

    Returns:
        Session factory that creates AsyncSession instances

    Configuration:
        - expire_on_commit: False (retain objects after commit)
        - class_: AsyncSession (use async session class)

    Example:
        >>> engine = create_engine("postgresql+asyncpg://user:pass@localhost/mcp")
        >>> SessionFactory = create_session_factory(engine)
        >>> async with SessionFactory() as session:
        ...     result = await session.execute(select(Repository))
    """
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection helper for FastAPI routes.

    Args:
        session_factory: Configured async session factory

    Yields:
        AsyncSession instance for database operations

    Usage in FastAPI:
        >>> @app.get("/repositories")
        >>> async def list_repos(session: AsyncSession = Depends(get_session)):
        ...     result = await session.execute(select(Repository))
        ...     return result.scalars().all()

    Notes:
        - Automatically commits on success
        - Automatically rolls back on exception
        - Closes session after request completes
    """
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database(engine: AsyncEngine) -> None:
    """Initialize database schema (create all tables).

    Args:
        engine: Configured AsyncEngine instance

    Creates:
        - All tables defined in SQLAlchemy models
        - Indexes and constraints
        - pgvector extension (if not exists)

    Warning:
        This function should only be used in development or testing.
        Production deployments should use Alembic migrations.

    Example:
        >>> engine = create_engine("postgresql+asyncpg://user:pass@localhost/mcp")
        >>> await init_database(engine)
    """
    async with engine.begin() as conn:
        # Enable pgvector extension
        from sqlalchemy import text
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)


async def drop_database(engine: AsyncEngine) -> None:
    """Drop all database tables (DANGEROUS - use only in testing).

    Args:
        engine: Configured AsyncEngine instance

    Drops:
        - All tables defined in SQLAlchemy models
        - Associated indexes and constraints

    Warning:
        This function permanently deletes all data. Only use in testing
        or development environments. Never use in production.

    Example:
        >>> engine = create_engine("postgresql+asyncpg://user:pass@localhost/test_db")
        >>> await drop_database(engine)
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
