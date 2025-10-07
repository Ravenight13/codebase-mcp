"""Database connection management and pooling for Codebase MCP Server.

This module provides centralized database connection management with:
- AsyncPG connection pool for PostgreSQL
- Session dependency injection for FastAPI
- Proper session cleanup and transaction handling
- Connection health checks with pre-ping
- Connection recycling for long-running server

Constitutional Compliance:
- Principle IV: Performance (connection pooling, async operations, 1-hour recycling)
- Principle V: Production quality (proper error handling, graceful shutdown)
- Principle VIII: Type safety (mypy --strict compliance)

Usage:
    >>> from src.database import init_db_connection, get_db
    >>> await init_db_connection()
    >>> # In FastAPI routes:
    >>> @app.get("/repositories")
    >>> async def list_repos(db: AsyncSession = Depends(get_db)):
    ...     result = await db.execute(select(Repository))
    ...     return result.scalars().all()
"""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from src.config.settings import get_settings
from src.mcp.mcp_logging import get_logger
from src.models.database import create_engine, create_session_factory

# ==============================================================================
# Module-Level State
# ==============================================================================

logger = get_logger(__name__)

# Global session factory (initialized by init_db_connection)
SessionLocal: async_sessionmaker[AsyncSession] | None = None

# Global engine (initialized by init_db_connection)
_engine: AsyncEngine | None = None


# ==============================================================================
# Database Connection Management
# ==============================================================================


async def init_db_connection() -> None:
    """Initialize database connection pool.

    Creates the global AsyncEngine and session factory using settings from
    environment variables. This function should be called once during
    application startup.

    Configuration:
        - Pool size: from settings.db_pool_size (default 20)
        - Max overflow: from settings.db_max_overflow (default 10)
        - Pre-ping: enabled for connection health checks
        - Connection recycling: 3600s (1 hour)

    Raises:
        ValidationError: If database URL is invalid
        DatabaseError: If connection cannot be established

    Example:
        >>> # In FastAPI lifespan:
        >>> @asynccontextmanager
        >>> async def lifespan(app: FastAPI):
        ...     await init_db_connection()
        ...     yield
        ...     await close_db_connection()

    Note:
        This function is idempotent - calling it multiple times has no effect
        after the first successful initialization.
    """
    global SessionLocal, _engine

    # Check if already initialized
    if SessionLocal is not None and _engine is not None:
        logger.warning(
            "Database connection already initialized",
            extra={"context": {"operation": "init_db_connection"}},
        )
        return

    # Load settings
    settings = get_settings()

    logger.info(
        "Initializing database connection pool",
        extra={
            "context": {
                "operation": "init_db_connection",
                "pool_size": settings.db_pool_size,
                "max_overflow": settings.db_max_overflow,
                "database_host": str(settings.database_url).split("@")[-1],  # Hide credentials
            }
        },
    )

    # Create engine with connection pooling
    _engine = create_engine(
        database_url=str(settings.database_url),
        echo=False,  # Disable SQL logging (use structured logger)
    )

    # Note: create_engine already uses settings via default parameters in models/database.py
    # However, we override with settings values for explicit configuration
    from sqlalchemy.ext.asyncio import create_async_engine

    _engine = create_async_engine(
        str(settings.database_url),
        echo=False,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,  # Validate connections before use
        pool_recycle=3600,  # Recycle connections after 1 hour
    )

    # Create session factory
    SessionLocal = create_session_factory(_engine)

    logger.info(
        "Database connection pool initialized successfully",
        extra={
            "context": {
                "operation": "init_db_connection",
                "pool_size": settings.db_pool_size,
                "max_overflow": settings.db_max_overflow,
            }
        },
    )


async def close_db_connection() -> None:
    """Close database connection pool.

    Gracefully closes all database connections and disposes of the engine.
    This function should be called once during application shutdown.

    Example:
        >>> # In FastAPI lifespan:
        >>> @asynccontextmanager
        >>> async def lifespan(app: FastAPI):
        ...     await init_db_connection()
        ...     yield
        ...     await close_db_connection()

    Note:
        After calling this function, you must call init_db_connection again
        before using the database.
    """
    global SessionLocal, _engine

    if _engine is None:
        logger.warning(
            "Database connection not initialized, nothing to close",
            extra={"context": {"operation": "close_db_connection"}},
        )
        return

    logger.info(
        "Closing database connection pool",
        extra={"context": {"operation": "close_db_connection"}},
    )

    # Dispose of the engine (closes all connections)
    await _engine.dispose()

    # Clear global state
    SessionLocal = None
    _engine = None

    logger.info(
        "Database connection pool closed successfully",
        extra={"context": {"operation": "close_db_connection"}},
    )


async def check_db_health() -> bool:
    """Check database connection health.

    Performs a simple query to verify the database is accessible and responsive.

    Returns:
        True if database is healthy, False otherwise

    Example:
        >>> # In health check endpoint:
        >>> @app.get("/health")
        >>> async def health_check():
        ...     db_healthy = await check_db_health()
        ...     return {"status": "healthy" if db_healthy else "unhealthy"}

    Note:
        This function requires the database to be initialized via init_db_connection.
    """
    if _engine is None:
        logger.warning(
            "Database health check failed: connection not initialized",
            extra={"context": {"operation": "check_db_health"}},
        )
        return False

    try:
        # Execute simple query to verify connection
        async with _engine.connect() as conn:
            from sqlalchemy import text

            await conn.execute(text("SELECT 1"))

        logger.debug(
            "Database health check passed",
            extra={"context": {"operation": "check_db_health"}},
        )
        return True

    except Exception as e:
        logger.error(
            "Database health check failed",
            extra={
                "context": {
                    "operation": "check_db_health",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            },
            exc_info=True,
        )
        return False


# ==============================================================================
# Session Factory Access
# ==============================================================================


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get the initialized session factory.

    Provides access to the global SessionLocal factory for creating database
    sessions outside of FastAPI dependency injection context (e.g., in MCP tools).

    Returns:
        async_sessionmaker[AsyncSession]: Initialized session factory

    Raises:
        RuntimeError: If database is not initialized

    Example:
        >>> # In MCP tool:
        >>> factory = get_session_factory()
        >>> async with factory() as db:
        ...     result = await db.execute(select(Repository))
        ...     await db.commit()

    Note:
        This function does NOT create a session - it returns the factory.
        Call the returned factory to create a session: `factory()`
    """
    if SessionLocal is None:
        error_msg = (
            "Database not initialized. Call init_db_connection() during startup."
        )
        logger.error(
            "Session factory requested before initialization",
            extra={"context": {"operation": "get_session_factory", "error": error_msg}},
        )
        raise RuntimeError(error_msg)

    return SessionLocal


# ==============================================================================
# FastAPI Dependency
# ==============================================================================


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions.

    Provides a database session for each request with automatic transaction
    management and cleanup.

    Yields:
        AsyncSession instance for database operations

    Raises:
        RuntimeError: If database is not initialized

    Transaction Management:
        - Automatically commits on successful request completion
        - Automatically rolls back on exceptions
        - Ensures session is closed after request

    Example:
        >>> # In FastAPI route:
        >>> @app.get("/repositories")
        >>> async def list_repos(db: AsyncSession = Depends(get_db)):
        ...     result = await db.execute(select(Repository))
        ...     return result.scalars().all()

    Performance:
        - Uses connection pooling for efficient resource usage
        - Pre-ping ensures valid connections before use
        - Connection recycling prevents stale connections

    Note:
        This dependency should be used for ALL database operations in
        FastAPI routes to ensure proper transaction management.
    """
    if SessionLocal is None:
        error_msg = (
            "Database not initialized. Call init_db_connection() during startup."
        )
        logger.error(
            "Database session requested before initialization",
            extra={"context": {"operation": "get_db", "error": error_msg}},
        )
        raise RuntimeError(error_msg)

    # Create new session from factory
    async with SessionLocal() as session:
        try:
            # Yield session to request handler
            yield session

            # Commit transaction on success
            await session.commit()

            logger.debug(
                "Database session committed successfully",
                extra={"context": {"operation": "get_db"}},
            )

        except Exception as e:
            # Rollback transaction on error
            await session.rollback()

            logger.error(
                "Database session rolled back due to error",
                extra={
                    "context": {
                        "operation": "get_db",
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                },
                exc_info=True,
            )
            raise

        finally:
            # Ensure session is closed
            await session.close()

            logger.debug(
                "Database session closed",
                extra={"context": {"operation": "get_db"}},
            )


# ==============================================================================
# Public API
# ==============================================================================

__all__ = [
    "init_db_connection",
    "close_db_connection",
    "check_db_health",
    "get_session_factory",
    "get_db",
    "SessionLocal",
]
