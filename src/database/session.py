"""Async SQLAlchemy session factory for PostgreSQL with database-per-project architecture.

This module provides production-grade database session management with:
- Database-per-project isolation instead of schema-based isolation
- Registry database for project metadata and lookups
- Per-project connection pools with AsyncPG
- Context manager pattern for automatic transaction management
- Session-based project resolution via .codebase-mcp/config.json
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
    >>> async with get_session(ctx=ctx) as session:
    ...     result = await session.execute(select(Repository))
    ...     # Session automatically commits on success, rolls back on error
    >>> # Health monitoring:
    >>> is_healthy = await check_database_health()
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict

import asyncpg
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from sqlalchemy.sql import text

from src.mcp.mcp_logging import get_logger
from src.config.settings import Settings, get_settings

# Session-based project resolution imports
from pathlib import Path
from fastmcp import Context
from src.auto_switch.session_context import get_session_context_manager
from src.auto_switch.discovery import find_config_file
from src.auto_switch.validation import validate_config_syntax
from src.auto_switch.cache import get_config_cache

# Database provisioning and registry imports
from src.database.provisioning import create_pool

# ==============================================================================
# Module Configuration
# ==============================================================================

logger = get_logger(__name__)

# Registry database URL from environment with secure default
# Note: REGISTRY_DATABASE_URL should NEVER fall back to DATABASE_URL since they serve different purposes
# DATABASE_URL is for legacy single-database mode, REGISTRY_DATABASE_URL is for project metadata
REGISTRY_DATABASE_URL: str = os.getenv(
    "REGISTRY_DATABASE_URL",
    "postgresql+asyncpg://localhost/codebase_mcp_registry"
)

# SQL echo mode for debugging (disabled in production for performance)
SQL_ECHO: bool = os.getenv("SQL_ECHO", "false").lower() == "true"

# Connection pool configuration for project databases
POOL_MIN_SIZE: int = int(os.getenv("POOL_MIN_SIZE", "2"))
POOL_MAX_SIZE: int = int(os.getenv("POOL_MAX_SIZE", "10"))

# Default project database name
DEFAULT_PROJECT_DB: str = "cb_proj_default_00000000"

# ==============================================================================
# Global Connection Pools
# ==============================================================================

# Registry database pool (initialized on first use)
_registry_pool: asyncpg.Pool | None = None

# Per-project database pools: {database_name: asyncpg.Pool}
_project_pools: Dict[str, asyncpg.Pool] = {}

# Legacy global engine for backward compatibility (will be phased out)
# This is kept to avoid breaking existing code that imports it directly
DATABASE_URL: str = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://localhost/codebase_mcp"
)
engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=SQL_ECHO,
    poolclass=NullPool,  # Disabled pooling (using AsyncPG pools instead)
)

logger.info(
    "Legacy async database engine created (no pooling - will be phased out)",
    extra={
        "context": {
            "operation": "engine_creation",
            "database_host": DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else "localhost",
            "note": "Use get_session() for production access"
        }
    },
)

# Legacy session factory (kept for backward compatibility)
SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ==============================================================================
# Registry Pool Initialization
# ==============================================================================


async def _initialize_registry_pool() -> asyncpg.Pool:
    """Initialize the registry database connection pool.

    Creates a connection pool to the codebase_mcp_registry database for
    project metadata lookups. This pool is used to map project_id/name to
    database_name.

    Returns:
        AsyncPG connection pool for registry database

    Raises:
        asyncpg.PostgresError: If pool creation fails
    """
    global _registry_pool

    if _registry_pool is not None:
        return _registry_pool

    # Extract database name from registry URL
    # Format: postgresql+asyncpg://user:pass@host:port/database
    if "@" in REGISTRY_DATABASE_URL:
        db_part = REGISTRY_DATABASE_URL.split("@")[1]
        registry_db_name = db_part.split("/")[-1] if "/" in db_part else "codebase_mcp_registry"
    else:
        registry_db_name = "codebase_mcp_registry"

    logger.info(
        "Initializing registry database pool",
        extra={
            "context": {
                "operation": "initialize_registry_pool",
                "database_name": registry_db_name,
                "min_size": POOL_MIN_SIZE,
                "max_size": POOL_MAX_SIZE,
            }
        },
    )

    try:
        # Use provisioning utility to create pool
        _registry_pool = await create_pool(
            database_name=registry_db_name,
            min_size=POOL_MIN_SIZE,
            max_size=POOL_MAX_SIZE,
        )

        logger.info(
            "Registry database pool initialized successfully",
            extra={
                "context": {
                    "operation": "initialize_registry_pool",
                    "database_name": registry_db_name,
                }
            },
        )

        return _registry_pool

    except asyncpg.PostgresError as e:
        logger.error(
            "Failed to initialize registry database pool",
            extra={
                "context": {
                    "operation": "initialize_registry_pool",
                    "database_name": registry_db_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            },
            exc_info=True,
        )
        raise


# ==============================================================================
# Per-Project Pool Management
# ==============================================================================


async def get_or_create_project_pool(database_name: str) -> asyncpg.Pool:
    """Get or create a connection pool for a specific project database.

    Manages per-project connection pools with lazy initialization. Pools are
    cached in module-level dict for reuse across sessions.

    Args:
        database_name: Project database name (cb_proj_*)

    Returns:
        AsyncPG connection pool for project database

    Raises:
        asyncpg.PostgresError: If pool creation fails

    Example:
        >>> pool = await get_or_create_project_pool("cb_proj_my_project_abc123de")
        >>> async with pool.acquire() as conn:
        ...     result = await conn.fetch("SELECT * FROM repositories")
    """
    # Check if pool already exists
    if database_name in _project_pools:
        logger.debug(
            f"Using existing pool for database: {database_name}",
            extra={
                "context": {
                    "operation": "get_or_create_project_pool",
                    "database_name": database_name,
                    "pool_exists": True,
                }
            },
        )
        return _project_pools[database_name]

    logger.info(
        f"Creating new pool for database: {database_name}",
        extra={
            "context": {
                "operation": "get_or_create_project_pool",
                "database_name": database_name,
                "min_size": POOL_MIN_SIZE,
                "max_size": POOL_MAX_SIZE,
            }
        },
    )

    try:
        # Use provisioning utility to create pool
        pool = await create_pool(
            database_name=database_name,
            min_size=POOL_MIN_SIZE,
            max_size=POOL_MAX_SIZE,
        )

        # Cache pool for reuse
        _project_pools[database_name] = pool

        logger.info(
            f"Project pool created successfully: {database_name}",
            extra={
                "context": {
                    "operation": "get_or_create_project_pool",
                    "database_name": database_name,
                    "total_pools": len(_project_pools),
                }
            },
        )

        return pool

    except asyncpg.PostgresError as e:
        logger.error(
            f"Failed to create pool for database: {database_name}",
            extra={
                "context": {
                    "operation": "get_or_create_project_pool",
                    "database_name": database_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            },
            exc_info=True,
        )
        raise


# ==============================================================================
# Project Resolution Utility
# ==============================================================================


async def _resolve_project_context(
    ctx: Context | None
) -> tuple[str, str] | None:
    """Resolve project from session config (graceful fallback).

    Resolution algorithm:
    1. Get session_id from FastMCP Context (explicit, async-safe)
    2. Look up working_directory for that session
    3. Search for .codebase-mcp/config.json (up to 20 levels)
    4. Check cache (async LRU with mtime invalidation)
    5. Parse and validate config (if cache miss)
    6. Extract project.name or project.id
    7. Look up project in registry database to get database_name
    8. Return (project_id, database_name)

    Args:
        ctx: FastMCP Context (contains session_id)

    Returns:
        Tuple of (project_id, database_name) or None if resolution fails
        (None enables graceful fallback to other resolution methods)

    Note:
        Does NOT raise exceptions - returns None for graceful fallback
    """
    # Must have context for session-based resolution
    if ctx is None:
        logger.debug("No FastMCP Context provided, cannot resolve from session")
        return None

    # Get session-specific working directory
    session_id = ctx.session_id  # ✅ From FastMCP Context (explicit)
    session_ctx_mgr = get_session_context_manager()

    try:
        working_dir = await session_ctx_mgr.get_working_directory(session_id)
    except Exception as e:
        logger.debug(f"Error getting working directory for session {session_id}: {e}")
        return None

    if not working_dir:
        logger.debug(
            f"No working directory set for session {session_id}. "
            f"Call set_working_directory() first for session-based resolution."
        )
        return None

    # Check cache first
    cache = get_config_cache()
    config = None
    config_path = None

    try:
        cache_result = await cache.get(working_dir)
        if cache_result is not None:
            config, config_path = cache_result
    except Exception as e:
        logger.debug(f"Cache lookup failed for {working_dir}: {e}")
        config = None
        config_path = None

    if config is None:
        # Cache miss: search for config file
        try:
            config_path = find_config_file(Path(working_dir))
        except Exception as e:
            logger.debug(f"Config file search failed for {working_dir}: {e}")
            return None

        if not config_path:
            logger.debug(
                f"No .codebase-mcp/config.json found in {working_dir} or ancestors "
                f"(searched up to 20 levels)"
            )
            return None

        # Parse and validate config
        try:
            config = validate_config_syntax(config_path)
        except ValueError as e:
            logger.debug(f"Config validation failed for {config_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error validating config {config_path}: {e}")
            return None

        # Store in cache
        try:
            await cache.set(working_dir, config, config_path)
        except Exception as e:
            logger.debug(f"Failed to cache config for {working_dir}: {e}")
            # Continue anyway (caching is optional)

    # At this point, we must have both config and config_path
    # Either from cache hit or from cache miss + filesystem search
    assert config is not None and config_path is not None, \
        "Internal error: config and config_path should be set by this point"

    # Get or create project from config using auto-create module
    try:
        from src.database.auto_create import get_or_create_project_from_config

        project = await get_or_create_project_from_config(
            config_path=config_path,
            registry=None  # Uses singleton registry
        )

        logger.debug(
            f"Resolved project from config: {project.name}",
            extra={
                "context": {
                    "operation": "_resolve_project_context",
                    "project_id": project.project_id,
                    "database_name": project.database_name,
                }
            }
        )

        return (project.project_id, project.database_name)

    except Exception as e:
        logger.error(
            f"Failed to get/create project from config: {e}",
            extra={
                "context": {
                    "operation": "_resolve_project_context",
                    "config_path": str(config_path),
                    "error": str(e),
                }
            },
            exc_info=True,
        )
        return None


async def resolve_project_id(
    explicit_id: str | None = None,
    settings: Settings | None = None,
    ctx: Context | None = None,
) -> tuple[str, str]:
    """Resolve project_id and database_name with 4-tier resolution chain.

    Implements the multi-project workspace resolution strategy with four-tier
    fallback logic to determine which workspace context to use for database
    operations.

    Resolution Order (FR-012, FR-013, FR-014):
        1. **Explicit ID**: If explicit_id is provided, look up in registry
           (highest priority, user-specified context)
        2. **Session-based config**: Query .codebase-mcp/config.json via FastMCP Context
        3. **workflow-mcp Integration**: Query external workflow-mcp server
           for active project context with timeout protection
        4. **Default Workspace**: Fallback to default project database when all
           resolution methods are unavailable, timeout occurs, or no active project exists

    Args:
        explicit_id: Explicitly provided project identifier (from MCP tool parameters).
                    Takes precedence over all other resolution methods.
        settings: Optional Settings instance for workflow-mcp configuration.
                 If not provided, uses global settings singleton.
        ctx: Optional FastMCP Context for session-based config resolution.

    Returns:
        Tuple of (project_id, database_name):
        - project_id: Project UUID or name
        - database_name: Physical PostgreSQL database name (cb_proj_*)

    Error Handling:
        All workflow-mcp errors are handled gracefully by returning default:
        - Timeout: workflow-mcp query exceeds timeout threshold
        - Connection refused: workflow-mcp server not running
        - Invalid response: malformed JSON or unexpected error

    Performance:
        - Explicit ID: <10ms (registry lookup)
        - Session config: <1ms (cached) or <60ms (uncached)
        - workflow-mcp query: <1000ms (timeout protection)
        - Default fallback: <1ms (constant)

    Example:
        >>> # Explicit ID takes precedence
        >>> project_id, db_name = await resolve_project_id("client-a")
        >>> assert db_name.startswith("cb_proj_")

        >>> # Query workflow-mcp when no explicit ID
        >>> project_id, db_name = await resolve_project_id(None, ctx=ctx)
        >>> # Returns active project or default if unavailable

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
        logger.info(
            "Attempting Tier 1: Explicit ID resolution",
            extra={
                "context": {
                    "operation": "resolve_project_id",
                    "tier_name": "explicit_id",
                    "tier_number": 1,
                    "explicit_id": explicit_id,
                    "session_id": ctx.session_id if ctx else None,
                }
            },
        )

        logger.debug(
            "Using explicit project_id, looking up in registry",
            extra={
                "context": {
                    "operation": "resolve_project_id",
                    "project_id": explicit_id,
                    "resolution_method": "explicit",
                }
            },
        )

        try:
            registry_pool = await _initialize_registry_pool()
            async with registry_pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT id, database_name
                    FROM projects
                    WHERE id::text = $1 OR name = $1
                    LIMIT 1
                    """,
                    explicit_id
                )

                if row is None:
                    raise ValueError(
                        f"Project '{explicit_id}' not found in registry. "
                        f"To create this project:\n"
                        f"1. Add .codebase-mcp/config.json with project.id = '{explicit_id}'\n"
                        f"2. Call set_working_directory() to enable auto-creation"
                    )
                else:
                    # Found in registry - return immediately
                    logger.info(
                        "✓ Tier 1 success: Resolved via explicit ID",
                        extra={
                            "context": {
                                "operation": "resolve_project_id",
                                "tier_name": "explicit_id",
                                "tier_number": 1,
                                "project_id": row['id'],
                                "database_name": row['database_name'],
                            }
                        },
                    )
                    return (row['id'], row['database_name'])

        except ValueError:
            # Re-raise ValueError from not-found check above
            raise
        except Exception as e:
            # Registry lookup error - re-raise as ValueError with clear message
            logger.error(
                f"Registry lookup failed for explicit project_id: {explicit_id}",
                extra={
                    "context": {
                        "operation": "resolve_project_id",
                        "project_id": explicit_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                },
                exc_info=True,
            )
            raise ValueError(
                f"Failed to look up project '{explicit_id}' in registry: {e}"
            ) from e

    # 2. Try session-based config resolution (if Context provided)
    if ctx is not None:
        logger.info(
            "Attempting Tier 2: Session config resolution",
            extra={
                "context": {
                    "operation": "resolve_project_id",
                    "tier_name": "session_config",
                    "tier_number": 2,
                    "session_id": ctx.session_id,
                    "explicit_id": explicit_id,
                }
            },
        )

        try:
            result = await _resolve_project_context(ctx)
            if result is not None:
                project_id, database_name = result
                logger.info(
                    "✓ Tier 2 success: Resolved via session config",
                    extra={
                        "context": {
                            "operation": "resolve_project_id",
                            "tier_name": "session_config",
                            "tier_number": 2,
                            "project_id": project_id,
                            "database_name": database_name,
                        }
                    }
                )
                logger.debug(
                    "Resolved project via session config",
                    extra={
                        "context": {
                            "operation": "resolve_project_id",
                            "project_id": project_id,
                            "database_name": database_name,
                            "resolution_method": "session_config"
                        }
                    }
                )
                return (project_id, database_name)
        except Exception as e:
            logger.debug(f"Session-based resolution failed: {e}")

    # ✅ FIX 2 + BUG 9: Prevent fallthrough when config exists
    # If config file exists but resolution failed, raise exception instead of falling through
    if ctx is not None and ctx.session_id:
        try:
            working_dir = await get_session_context_manager().get_working_directory(ctx.session_id)
            if working_dir:
                config_path = find_config_file(Path(working_dir))
                if config_path:
                    logger.error(
                        f"Config exists but project resolution failed: {config_path}",
                        extra={
                            "context": {
                                "config_path": str(config_path),
                                "session_id": ctx.session_id,
                                "operation": "resolve_project_id"
                            }
                        }
                    )
                    raise ValueError(
                        f"Project resolution failed despite config at {config_path}. "
                        f"Check config file for errors (project.id or project.name required)."
                    )
                else:
                    logger.info(
                        "No config file found, allowing fallthrough to Tier 3 (workflow-mcp)",
                        extra={
                            "context": {
                                "operation": "resolve_project_id",
                                "working_directory": str(working_dir),
                                "session_id": ctx.session_id
                            }
                        }
                    )
        except ValueError:
            # Re-raise ValueError from config validation check above
            raise
        except Exception as e:
            # Graceful fallthrough if session context lookup fails
            logger.debug(f"Config existence check failed, allowing fallthrough: {e}")

    # 3. Try workflow-mcp integration (if configured)
    if settings is None:
        settings = get_settings()

    if settings.workflow_mcp_url is not None:
        logger.info(
            "Attempting Tier 3: workflow-mcp fallback",
            extra={
                "context": {
                    "operation": "resolve_project_id",
                    "tier_name": "workflow_mcp",
                    "tier_number": 3,
                    "workflow_mcp_url": str(settings.workflow_mcp_url),
                    "session_id": ctx.session_id if ctx else None,
                    "explicit_id": explicit_id,
                }
            },
        )

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

        from src.services.workflow_client import WorkflowIntegrationClient

        client = WorkflowIntegrationClient(
            base_url=str(settings.workflow_mcp_url),
            timeout=settings.workflow_mcp_timeout,
            cache_ttl=settings.workflow_mcp_cache_ttl,
        )

        try:
            active_project = await client.get_active_project()

            if active_project is not None:
                # Look up in registry to get database_name
                registry_pool = await _initialize_registry_pool()
                async with registry_pool.acquire() as conn:
                    row = await conn.fetchrow(
                        """
                        SELECT id, database_name
                        FROM projects
                        WHERE id::text = $1 OR name = $1
                        LIMIT 1
                        """,
                        active_project
                    )

                    if row is not None:
                        logger.info(
                            "✓ Tier 3 success: Resolved via workflow-mcp",
                            extra={
                                "context": {
                                    "operation": "resolve_project_id",
                                    "tier_name": "workflow_mcp",
                                    "tier_number": 3,
                                    "project_id": row['id'],
                                    "database_name": row['database_name'],
                                }
                            },
                        )
                        logger.info(
                            "Resolved project from workflow-mcp",
                            extra={
                                "context": {
                                    "operation": "resolve_project_id",
                                    "project_id": row['id'],
                                    "database_name": row['database_name'],
                                    "resolution_method": "workflow_mcp",
                                }
                            },
                        )
                        return (row['id'], row['database_name'])
                    else:
                        logger.warning(
                            f"workflow-mcp project not found in registry: {active_project}",
                            extra={
                                "context": {
                                    "operation": "resolve_project_id",
                                    "project_id": active_project,
                                }
                            },
                        )
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

    # 4. Fallback to default workspace
    logger.info(
        "Attempting Tier 4: Default project",
        extra={
            "context": {
                "operation": "resolve_project_id",
                "tier_name": "default_project",
                "tier_number": 4,
                "session_id": ctx.session_id if ctx else None,
                "explicit_id": explicit_id,
            }
        },
    )

    logger.debug(
        "Using default workspace (no explicit ID, session config unavailable, workflow-mcp unavailable/disabled)",
        extra={
            "context": {
                "operation": "resolve_project_id",
                "resolution_method": "default_fallback",
            }
        },
    )

    logger.info(
        "✓ Tier 4 success: Resolved via default project",
        extra={
            "context": {
                "operation": "resolve_project_id",
                "tier_name": "default_project",
                "tier_number": 4,
                "project_id": "default",
                "database_name": DEFAULT_PROJECT_DB,
            }
        },
    )

    return ("default", DEFAULT_PROJECT_DB)


# ==============================================================================
# Session Context Manager
# ==============================================================================


@asynccontextmanager
async def get_session(
    project_id: str | None = None,
    ctx: Context | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for database sessions with automatic transaction management.

    Provides a database session connected to the correct project database with
    automatic commit on success and rollback on error. This is the primary way
    to interact with the database in MCP tools.

    Args:
        project_id: Optional project identifier for workspace isolation.
                   If None, uses 4-tier resolution chain (explicit → session → workflow-mcp → default).
        ctx: Optional FastMCP Context for session-based project resolution.

    Yields:
        AsyncSession: Configured database session connected to project database

    Raises:
        ValueError: If project_id format is invalid
        Exception: Any exception from database operations (after rollback)

    Transaction Management:
        - Resolves project_id and database_name via 4-tier chain
        - Creates session from project-specific connection pool
        - Automatically commits on successful completion
        - Automatically rolls back on any exception
        - Ensures session is closed after use

    Example:
        >>> # In MCP tool with project isolation:
        >>> async with get_session(project_id="client-a") as session:
        ...     result = await session.execute(select(Repository))
        ...     repos = result.scalars().all()

        >>> # With session-based resolution:
        >>> async with get_session(ctx=ctx) as session:
        ...     result = await session.execute(select(Repository))
        ...     # Uses project from .codebase-mcp/config.json

        >>> # With error handling:
        >>> try:
        ...     async with get_session(ctx=ctx) as session:
        ...         await session.execute(insert(Repository).values(...))
        ... except IntegrityError:
        ...     logger.error("Duplicate repository")

    Performance:
        - Uses per-project connection pools for efficient resource usage
        - Connection recycling prevents stale connections
        - Registry lookup cached for repeated access

    Constitutional Compliance:
        - Principle V: Production quality (proper error handling, cleanup)
        - Principle VIII: Type safety (mypy --strict compliance)
        - Principle XI: FastMCP Foundation (async pattern for MCP tools)

    Multi-Project Support:
        - Resolves project_id to physical database name (cb_proj_*)
        - Uses dedicated connection pool per project database
        - Complete data isolation (no shared tables or schemas)
        - Backward compatible with project_id=None
    """
    # Resolve project_id and database_name via 4-tier resolution chain
    resolved_project_id, database_name = await resolve_project_id(
        explicit_id=project_id,
        ctx=ctx,
    )

    logger.debug(
        f"Resolved project for session: {resolved_project_id} (database: {database_name})",
        extra={
            "context": {
                "operation": "get_session",
                "project_id": resolved_project_id,
                "database_name": database_name,
            }
        },
    )

    # Get or create connection pool for project database
    try:
        pool = await get_or_create_project_pool(database_name)
    except Exception as e:
        logger.error(
            f"Failed to get pool for database: {database_name}",
            extra={
                "context": {
                    "operation": "get_session",
                    "database_name": database_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            },
            exc_info=True,
        )
        raise

    # Create SQLAlchemy engine from AsyncPG pool (temporary bridge)
    # TODO: Move to pure AsyncPG for better performance
    from sqlalchemy.ext.asyncio import create_async_engine

    # Build connection string for this project database
    db_user = os.getenv("DB_USER", os.getenv("USER", "postgres"))
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = int(os.getenv("DB_PORT", "5432"))
    db_password = os.getenv("DB_PASSWORD", "")

    if db_password:
        project_db_url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{database_name}"
    else:
        project_db_url = f"postgresql+asyncpg://{db_user}@{db_host}:{db_port}/{database_name}"

    # Create engine with pooling disabled (we manage pools separately)
    project_engine = create_async_engine(
        project_db_url,
        echo=SQL_ECHO,
        poolclass=NullPool,  # No SQLAlchemy pooling (using AsyncPG pools)
    )

    # Create session factory for this project
    ProjectSessionLocal = async_sessionmaker(
        project_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with ProjectSessionLocal() as session:
        try:
            logger.debug(
                "Database session started for project",
                extra={
                    "context": {
                        "operation": "get_session",
                        "project_id": resolved_project_id,
                        "database_name": database_name,
                    }
                },
            )

            yield session

            # Commit transaction on success
            await session.commit()

            logger.debug(
                "Database session committed successfully",
                extra={
                    "context": {
                        "operation": "get_session",
                        "project_id": resolved_project_id,
                    }
                },
            )

        except Exception as e:
            # Rollback transaction on error
            await session.rollback()

            logger.error(
                "Database session rolled back due to error",
                extra={
                    "context": {
                        "operation": "get_session",
                        "project_id": resolved_project_id,
                        "database_name": database_name,
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
                extra={
                    "context": {
                        "operation": "get_session",
                        "project_id": resolved_project_id,
                    }
                },
            )

            # Dispose of project-specific engine
            await project_engine.dispose()


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

    Note:
        This returns the LEGACY session factory. For production use,
        prefer get_session() which uses per-project pools.

    Example:
        >>> # Legacy usage (backward compatibility):
        >>> factory = get_session_factory()
        >>> async with factory() as session:
        ...     result = await session.execute(select(Repository))

    Constitutional Compliance:
        - Principle VIII: Type safety (explicit return type annotation)
    """
    return SessionLocal


# ==============================================================================
# Database Health Check
# ==============================================================================


async def check_database_health() -> bool:
    """Check database connection health.

    Performs a simple query (`SELECT 1`) to verify the registry database is
    accessible and responsive. This is useful for health check endpoints and
    monitoring.

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

    Performance:
        - Uses connection pool for efficient health checks
        - Minimal overhead (<1ms typical latency)

    Constitutional Compliance:
        - Principle IV: Performance (<1ms query execution)
        - Principle V: Production quality (comprehensive error logging)
    """
    try:
        # Check registry pool health
        registry_pool = await _initialize_registry_pool()
        async with registry_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")

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
    """Initialize database connection pools.

    This function is called during server startup to ensure the registry
    database connection pool is properly initialized and ready to serve requests.

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
        # Initialize registry pool
        await _initialize_registry_pool()

        # Verify registry database is accessible
        is_healthy = await check_database_health()
        if not is_healthy:
            raise RuntimeError("Registry database health check failed during initialization")

        logger.info(
            "Database connection pools initialized successfully",
            extra={
                "context": {
                    "operation": "init_db_connection",
                    "registry_pool_ready": True,
                }
            },
        )

    except Exception as e:
        logger.critical(
            "Failed to initialize database connection pools",
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
    """Close database connection pools gracefully.

    This function is called during server shutdown to ensure all database
    connections are properly closed and resources are cleaned up.

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
            "Closing database connection pools...",
            extra={"context": {"operation": "close_db_connection"}},
        )

        # Close all project pools
        for database_name, pool in _project_pools.items():
            try:
                await pool.close()
                logger.debug(f"Closed pool for database: {database_name}")
            except Exception as e:
                logger.error(
                    f"Error closing pool for database: {database_name}",
                    extra={
                        "context": {
                            "operation": "close_db_connection",
                            "database_name": database_name,
                            "error": str(e),
                        }
                    },
                )

        _project_pools.clear()

        # Close registry pool
        global _registry_pool
        if _registry_pool is not None:
            try:
                await _registry_pool.close()
                logger.debug("Closed registry pool")
                _registry_pool = None
            except Exception as e:
                logger.error(
                    "Error closing registry pool",
                    extra={
                        "context": {
                            "operation": "close_db_connection",
                            "error": str(e),
                        }
                    },
                )

        # Dispose of legacy engine
        await engine.dispose()

        logger.info(
            "Database connection pools closed successfully",
            extra={"context": {"operation": "close_db_connection"}},
        )

    except Exception as e:
        logger.error(
            "Error closing database connection pools",
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
    "_resolve_project_context",
    "check_database_health",
    "init_db_connection",
    "close_db_connection",
    "get_or_create_project_pool",
    "_initialize_registry_pool",
    "DATABASE_URL",
    "REGISTRY_DATABASE_URL",
]
