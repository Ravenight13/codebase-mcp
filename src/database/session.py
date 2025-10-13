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
from src.config.settings import Settings, get_settings
from src.services.workflow_client import WorkflowIntegrationClient

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
# Project Resolution Utility
# ==============================================================================


async def resolve_project_id(
    explicit_id: str | None,
    settings: Settings | None = None,
) -> str | None:
    """Resolve project_id with workflow-mcp fallback logic.

    Implements the multi-project workspace resolution strategy with three-tier
    fallback logic to determine which workspace context to use for database
    operations.

    Resolution Order (FR-012, FR-013, FR-014):
        1. **Explicit ID**: If explicit_id is provided, return immediately
           (highest priority, user-specified context)
        2. **workflow-mcp Integration**: Query external workflow-mcp server
           for active project context with timeout protection
        3. **Default Workspace**: Fallback to None when workflow-mcp is
           unavailable, timeout occurs, or no active project exists

    Args:
        explicit_id: Explicitly provided project identifier (from MCP tool parameters).
                    Takes precedence over all other resolution methods.
        settings: Optional Settings instance for workflow-mcp configuration.
                 If not provided, uses global settings singleton.

    Returns:
        Resolved project_id string or None for default workspace:
        - str: Project UUID from explicit_id or workflow-mcp
        - None: Default workspace (backward compatibility)

    Error Handling:
        All workflow-mcp errors are handled gracefully by returning None:
        - Timeout: workflow-mcp query exceeds timeout threshold
        - Connection refused: workflow-mcp server not running
        - Invalid response: malformed JSON or unexpected error

    Performance:
        - Explicit ID: <1μs (immediate return)
        - workflow-mcp query: <1000ms (timeout protection)
        - Default fallback: <1μs (no I/O)

    Example:
        >>> # Explicit ID takes precedence
        >>> project = await resolve_project_id("client-a")
        >>> assert project == "client-a"

        >>> # Query workflow-mcp when no explicit ID
        >>> project = await resolve_project_id(None)
        >>> # Returns active project UUID or None if unavailable

        >>> # Fallback to None when workflow-mcp timeout
        >>> project = await resolve_project_id(None)
        >>> if project is None:
        ...     print("Using default workspace")

    Constitutional Compliance:
        - Principle II: Local-first (graceful degradation when workflow-mcp unavailable)
        - Principle V: Production quality (comprehensive error handling)
        - Principle VIII: Type safety (mypy --strict compliance)

    Functional Requirements:
        - FR-012: Detect workflow-mcp active project with caching
        - FR-013: Handle workflow-mcp unavailability gracefully
        - FR-014: TTL-based cache invalidation (60s default)
    """
    # 1. Explicit ID takes precedence (highest priority)
    if explicit_id is not None:
        logger.debug(
            "Using explicit project_id",
            extra={
                "context": {
                    "operation": "resolve_project_id",
                    "project_id": explicit_id,
                    "resolution_method": "explicit",
                }
            },
        )
        return explicit_id

    # 2. Try workflow-mcp integration (if configured)
    if settings is None:
        settings = get_settings()

    if settings.workflow_mcp_url is not None:
        logger.debug(
            "Querying workflow-mcp for active project",
            extra={
                "context": {
                    "operation": "resolve_project_id",
                    "workflow_mcp_url": str(settings.workflow_mcp_url),
                    "timeout": settings.workflow_mcp_timeout,
                }
            },
        )

        client = WorkflowIntegrationClient(
            base_url=str(settings.workflow_mcp_url),
            timeout=settings.workflow_mcp_timeout,
            cache_ttl=settings.workflow_mcp_cache_ttl,
        )

        try:
            active_project = await client.get_active_project()

            if active_project is not None:
                logger.info(
                    "Resolved project from workflow-mcp",
                    extra={
                        "context": {
                            "operation": "resolve_project_id",
                            "project_id": active_project,
                            "resolution_method": "workflow_mcp",
                        }
                    },
                )
                return active_project
            else:
                logger.debug(
                    "workflow-mcp returned no active project, using default workspace",
                    extra={
                        "context": {
                            "operation": "resolve_project_id",
                            "resolution_method": "default_fallback",
                        }
                    },
                )

        except Exception as e:
            logger.warning(
                "Failed to query workflow-mcp, using default workspace",
                extra={
                    "context": {
                        "operation": "resolve_project_id",
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "resolution_method": "default_fallback",
                    }
                },
            )

        finally:
            # Always close client connection to prevent resource leaks
            await client.close()

    # 3. Fallback to default workspace
    logger.debug(
        "Using default workspace (no explicit ID, workflow-mcp unavailable/disabled)",
        extra={
            "context": {
                "operation": "resolve_project_id",
                "resolution_method": "default_fallback",
            }
        },
    )
    return None


# ==============================================================================
# Session Context Manager
# ==============================================================================


@asynccontextmanager
async def get_session(project_id: str | None = None) -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for database sessions with automatic transaction management.

    Provides a database session with automatic commit on success and rollback on error.
    This is the primary way to interact with the database in MCP tools.

    Args:
        project_id: Optional project identifier for workspace isolation.
                   If None, uses default workspace (backward compatibility).

    Yields:
        AsyncSession: Configured database session with search_path set to project schema

    Raises:
        ValueError: If project_id format is invalid (from ProjectIdentifier validation)
        Exception: Any exception from database operations (after rollback)

    Transaction Management:
        - Sets search_path to project schema before yielding session
        - Automatically commits on successful completion
        - Automatically rolls back on any exception
        - Ensures session is closed after use

    Example:
        >>> # In MCP tool with project isolation:
        >>> async with get_session(project_id="client-a") as session:
        ...     result = await session.execute(select(Repository))
        ...     repos = result.scalars().all()

        >>> # Backward compatible (no project_id):
        >>> async with get_session() as session:
        ...     result = await session.execute(select(Repository))
        ...     # Uses default workspace (project_default schema)

        >>> # With error handling:
        >>> try:
        ...     async with get_session(project_id="frontend") as session:
        ...         await session.execute(insert(Repository).values(...))
        ... except IntegrityError:
        ...     logger.error("Duplicate repository")

    Performance:
        - Uses connection pooling for efficient resource usage
        - Pre-ping ensures valid connections before use
        - Connection recycling prevents stale connections
        - Schema existence check cached for performance

    Constitutional Compliance:
        - Principle V: Production quality (proper error handling, cleanup)
        - Principle VIII: Type safety (mypy --strict compliance)
        - Principle XI: FastMCP Foundation (async pattern for MCP tools)

    Multi-Project Support (FR-001, FR-002, FR-003, FR-009):
        - Resolves project_id to PostgreSQL schema name
        - Auto-provisions workspace if needed (FR-010)
        - Sets search_path to isolated schema (FR-017 data isolation)
        - Backward compatible with project_id=None (FR-018)
    """
    async with SessionLocal() as session:
        try:
            # Resolve schema name based on project_id
            if project_id is None:
                # Backward compatibility: use default workspace
                schema_name = "project_default"
                logger.debug(
                    "Using default workspace (backward compatibility)",
                    extra={"context": {"operation": "get_session", "schema_name": schema_name}},
                )
            else:
                # Project workspace: ensure exists and get schema name
                from src.services.workspace_manager import ProjectWorkspaceManager

                manager = ProjectWorkspaceManager(engine)
                schema_name = await manager.ensure_workspace_exists(project_id)

                logger.debug(
                    "Using project workspace",
                    extra={
                        "context": {
                            "operation": "get_session",
                            "project_id": project_id,
                            "schema_name": schema_name,
                        }
                    },
                )

            # Set search_path to project schema (include public for pgvector extension)
            await session.execute(text(f"SET search_path TO {schema_name}, public"))

            logger.debug(
                "Database session started with search_path set",
                extra={
                    "context": {
                        "operation": "get_session",
                        "schema_name": schema_name,
                        "project_id": project_id,
                    }
                },
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
    "resolve_project_id",
    "check_database_health",
    "init_db_connection",
    "close_db_connection",
    "DATABASE_URL",
]
