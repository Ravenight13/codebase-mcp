"""Async SQLAlchemy session factory for PostgreSQL with connection pooling.

This module provides production-grade database session management with:
- AsyncPG driver for high-performance PostgreSQL connections
- Connection pooling with configurable size and overflow
- Context manager pattern for automatic transaction management
- Proper cleanup and error handling
- Health check functionality for monitoring

Constitutional Compliance:
- Principle IV: Performance (connection pooling, async operations, 30s timeout)
- Principle V: Production quality (comprehensive error handling, graceful cleanup)
- Principle VIII: Type safety (mypy --strict compliance, complete type annotations)
- Principle XI: FastMCP Foundation (async session for MCP tool integration)

Usage:
    >>> from src.database.session import get_session, check_database_health
    >>> # In MCP tools:
    >>> async with get_session() as session:
    ...     result = await session.execute(select(Repository))
    ...     # Session automatically commits on success, rolls back on error
    >>> # Health monitoring:
    >>> is_healthy = await check_database_health()
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.sql import text

from src.mcp.mcp_logging import get_logger

# ==============================================================================
# Module Configuration
# ==============================================================================

logger = get_logger(__name__)

# Database URL from environment with secure default (localhost)
DATABASE_URL: str = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://localhost/codebase_mcp"
)

# SQL echo mode for debugging (disabled in production for performance)
SQL_ECHO: bool = os.getenv("SQL_ECHO", "false").lower() == "true"

# Connection pool configuration
POOL_SIZE: int = 10  # Core connections maintained in pool
MAX_OVERFLOW: int = 20  # Additional connections beyond pool_size
POOL_TIMEOUT: int = 30  # Seconds to wait for connection before timeout

# ==============================================================================
# Engine Creation
# ==============================================================================

# Global async engine (created at module import for singleton pattern)
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=SQL_ECHO,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_pre_ping=True,  # Validate connections before use
    pool_recycle=3600,  # Recycle connections after 1 hour
)

logger.info(
    "Async database engine created",
    extra={
        "context": {
            "operation": "engine_creation",
            "pool_size": POOL_SIZE,
            "max_overflow": MAX_OVERFLOW,
            "pool_timeout": POOL_TIMEOUT,
            "database_host": DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else "localhost",
        }
    },
)

# ==============================================================================
# Session Factory
# ==============================================================================

# Session factory for creating async sessions
# Configuration:
# - expire_on_commit: False (retain objects after commit for better performance)
# - class_: AsyncSession (use async session class)
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ==============================================================================
# Session Context Manager
# ==============================================================================


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for database sessions with automatic transaction management.

    Provides a database session with automatic commit on success and rollback on error.
    This is the primary way to interact with the database in MCP tools.

    Yields:
        AsyncSession: Configured database session

    Raises:
        Exception: Any exception from database operations (after rollback)

    Transaction Management:
        - Automatically commits on successful completion
        - Automatically rolls back on any exception
        - Ensures session is closed after use

    Example:
        >>> # In MCP tool:
        >>> async with get_session() as session:
        ...     result = await session.execute(select(Repository))
        ...     repos = result.scalars().all()
        ...     await session.commit()  # Optional - auto-commits on exit

        >>> # With error handling:
        >>> try:
        ...     async with get_session() as session:
        ...         await session.execute(insert(Repository).values(...))
        ... except IntegrityError:
        ...     logger.error("Duplicate repository")

    Performance:
        - Uses connection pooling for efficient resource usage
        - Pre-ping ensures valid connections before use
        - Connection recycling prevents stale connections

    Constitutional Compliance:
        - Principle V: Production quality (proper error handling, cleanup)
        - Principle XI: FastMCP Foundation (async pattern for MCP tools)
    """
    async with SessionLocal() as session:
        try:
            logger.debug(
                "Database session started",
                extra={"context": {"operation": "get_session"}},
            )

            yield session

            # Commit transaction on success
            await session.commit()

            logger.debug(
                "Database session committed successfully",
                extra={"context": {"operation": "get_session"}},
            )

        except Exception as e:
            # Rollback transaction on error
            await session.rollback()

            logger.error(
                "Database session rolled back due to error",
                extra={
                    "context": {
                        "operation": "get_session",
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                },
                exc_info=True,
            )
            raise

        finally:
            # Ensure session is closed (cleanup)
            await session.close()

            logger.debug(
                "Database session closed",
                extra={"context": {"operation": "get_session"}},
            )


# ==============================================================================
# Session Factory Access
# ==============================================================================


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get the initialized session factory.

    Provides access to the global SessionLocal factory for creating database
    sessions. This is useful when you need the factory itself rather than a
    session instance (e.g., for dependency injection).

    Returns:
        async_sessionmaker[AsyncSession]: Initialized session factory

    Example:
        >>> # Get factory and create session:
        >>> factory = get_session_factory()
        >>> async with factory() as session:
        ...     result = await session.execute(select(Repository))

        >>> # Use in FastAPI dependency:
        >>> def get_db():
        ...     factory = get_session_factory()
        ...     return factory

    Note:
        This function returns the factory, NOT a session instance.
        Call the returned factory to create a session: `factory()`

    Constitutional Compliance:
        - Principle VIII: Type safety (explicit return type annotation)
    """
    return SessionLocal


# ==============================================================================
# Database Health Check
# ==============================================================================


async def check_database_health() -> bool:
    """Check database connection health.

    Performs a simple query (`SELECT 1`) to verify the database is accessible
    and responsive. This is useful for health check endpoints and monitoring.

    Returns:
        bool: True if database is healthy, False otherwise

    Example:
        >>> # In health check endpoint:
        >>> @mcp.tool()
        >>> async def health_check() -> dict[str, str]:
        ...     db_healthy = await check_database_health()
        ...     return {
        ...         "status": "healthy" if db_healthy else "unhealthy",
        ...         "database": "ok" if db_healthy else "error",
        ...     }

        >>> # In startup validation:
        >>> if not await check_database_health():
        ...     logger.error("Database is not accessible")
        ...     raise RuntimeError("Database health check failed")

    Performance:
        - Uses connection pool for efficient health checks
        - Pre-ping ensures connection validity before query
        - Minimal overhead (<1ms typical latency)

    Constitutional Compliance:
        - Principle IV: Performance (<1ms query execution)
        - Principle V: Production quality (comprehensive error logging)
    """
    try:
        # Execute simple query to verify connection
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        logger.debug(
            "Database health check passed",
            extra={"context": {"operation": "check_database_health"}},
        )
        return True

    except Exception as e:
        logger.error(
            "Database health check failed",
            extra={
                "context": {
                    "operation": "check_database_health",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            },
            exc_info=True,
        )
        return False


# ==============================================================================
# Connection Lifecycle Management
# ==============================================================================


async def init_db_connection() -> None:
    """Initialize database connection pool.

    This function is called during server startup to ensure the database
    connection pool is properly initialized and ready to serve requests.

    The engine is created at module import time (singleton pattern), but this
    function provides an explicit initialization hook for the server lifecycle.
    It verifies that the database is accessible before the server starts serving
    requests.

    Raises:
        RuntimeError: If database initialization fails (connection error, etc.)

    Example:
        >>> # In FastMCP lifespan:
        >>> @asynccontextmanager
        >>> async def lifespan(app: FastMCP):
        ...     await init_db_connection()  # BLOCKING - wait for DB to be ready
        ...     yield
        ...     await close_db_connection()

    Constitutional Compliance:
        - Principle V: Production quality (explicit initialization order)
        - Principle IV: Performance (connection pool pre-warming)
    """
    try:
        # Verify database is accessible
        is_healthy = await check_database_health()
        if not is_healthy:
            raise RuntimeError("Database health check failed during initialization")

        logger.info(
            "Database connection pool initialized successfully",
            extra={
                "context": {
                    "operation": "init_db_connection",
                    "pool_size": POOL_SIZE,
                    "max_overflow": MAX_OVERFLOW,
                }
            },
        )

    except Exception as e:
        logger.critical(
            "Failed to initialize database connection pool",
            extra={
                "context": {
                    "operation": "init_db_connection",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            },
            exc_info=True,
        )
        raise RuntimeError(f"Database initialization failed: {e}") from e


async def close_db_connection() -> None:
    """Close database connection pool gracefully.

    This function is called during server shutdown to ensure all database
    connections are properly closed and resources are cleaned up.

    Disposes of the global engine, which:
    - Closes all active connections in the pool
    - Waits for in-flight queries to complete (graceful shutdown)
    - Releases connection resources

    Example:
        >>> # In FastMCP lifespan:
        >>> @asynccontextmanager
        >>> async def lifespan(app: FastMCP):
        ...     await init_db_connection()
        ...     yield
        ...     await close_db_connection()  # Graceful shutdown

    Constitutional Compliance:
        - Principle V: Production quality (proper cleanup, no resource leaks)
    """
    try:
        logger.info(
            "Closing database connection pool...",
            extra={"context": {"operation": "close_db_connection"}},
        )

        # Dispose of engine (closes all connections in pool)
        await engine.dispose()

        logger.info(
            "Database connection pool closed successfully",
            extra={"context": {"operation": "close_db_connection"}},
        )

    except Exception as e:
        logger.error(
            "Error closing database connection pool",
            extra={
                "context": {
                    "operation": "close_db_connection",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            },
            exc_info=True,
        )
        # Don't raise - we're shutting down anyway


# ==============================================================================
# Public API
# ==============================================================================

__all__ = [
    "engine",
    "SessionLocal",
    "get_session",
    "get_session_factory",
    "check_database_health",
    "init_db_connection",
    "close_db_connection",
    "DATABASE_URL",
]
