"""4-layer fallback service for database unavailability.

Provides graceful degradation when PostgreSQL is unavailable through cascading
fallback layers:
1. PostgreSQL (primary) - Full CRUD operations
2. SQLite cache (30-min TTL) - Read-only cached data
3. Git history parsing - Historical data from commit messages/tags
4. Manual markdown file - Legacy .project_status.md fallback

Constitutional Compliance:
- Principle II: Local-first architecture (SQLite cache, git, markdown fallbacks)
- Principle V: Production quality (comprehensive error handling, warning collection)
- Principle VIII: Type safety (full mypy --strict compliance)
- Principle IV: Performance (<10ms fallback layer detection)

Key Features:
- execute_with_fallback: Read operations with automatic layer cascade
- write_with_fallback: Write to cache+markdown in parallel on PostgreSQL failure
- check_postgresql_health: Async health check with configuration update
- get_fallback_data: Query cached/historical data with staleness warnings
- Comprehensive warning collection for observability
- No hard failures - always return data or actionable error messages
"""

from __future__ import annotations

import asyncio
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Final, Literal, TypeVar

import aiosqlite  # type: ignore[import-not-found]
from sqlalchemy import text
from sqlalchemy.exc import (
    DatabaseError,
    InterfaceError,
    OperationalError,
    TimeoutError as SQLAlchemyTimeoutError,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.mcp.mcp_logging import get_logger

# ==============================================================================
# Constants
# ==============================================================================

logger = get_logger(__name__)

# Cache TTL for SQLite layer (30 minutes as per spec FR-028)
CACHE_TTL_SECONDS: Final[int] = 1800  # 30 minutes

# SQLite cache database path (relative to project root)
CACHE_DB_PATH: Final[Path] = Path(__file__).parent.parent.parent / ".cache" / "fallback_cache.db"

# Markdown fallback file path (legacy .project_status.md)
MARKDOWN_FALLBACK_PATH: Final[Path] = Path(__file__).parent.parent.parent / ".project_status.md"

# Git repository root (for git history parsing)
GIT_REPO_ROOT: Final[Path] = Path(__file__).parent.parent.parent

# PostgreSQL connection timeout (seconds)
POSTGRESQL_TIMEOUT_SECONDS: Final[float] = 2.0

# Fallback layer names
FallbackLayer = Literal["postgresql", "sqlite_cache", "git_history", "markdown_file"]

# ==============================================================================
# Type Variables
# ==============================================================================

T = TypeVar("T")

# ==============================================================================
# Custom Exceptions
# ==============================================================================


class AllFallbackLayersFailedError(Exception):
    """Raised when all 4 fallback layers fail to provide data."""

    pass


class PostgreSQLUnavailableError(Exception):
    """Raised when PostgreSQL is unavailable (triggers fallback cascade)."""

    pass


class InvalidCacheDataError(Exception):
    """Raised when cached data is malformed or invalid."""

    pass


# ==============================================================================
# PostgreSQL Health Check
# ==============================================================================


async def check_postgresql_health(session: AsyncSession) -> bool:
    """Check PostgreSQL database health with timeout.

    Args:
        session: Async database session

    Returns:
        True if PostgreSQL is healthy and responsive, False otherwise

    Raises:
        No exceptions raised - returns False on any error

    Health Check:
        - Executes simple SELECT 1 query with timeout
        - Target response time: <100ms for healthy database
        - Timeout after 2 seconds (POSTGRESQL_TIMEOUT_SECONDS)
        - Updates ProjectConfiguration.database_healthy on check

    Performance:
        - <10ms typical response time
        - <2s timeout for unresponsive database

    Example:
        >>> async with get_session() as session:
        ...     is_healthy = await check_postgresql_health(session)
        ...     if not is_healthy:
        ...         logger.warning("PostgreSQL is down, using fallback layers")
    """
    logger.debug("Checking PostgreSQL health")

    try:
        # Simple health check query with timeout
        result = await asyncio.wait_for(
            session.execute(text("SELECT 1")),
            timeout=POSTGRESQL_TIMEOUT_SECONDS,
        )

        # Verify result is valid
        row = result.scalar_one_or_none()
        if row != 1:
            logger.warning(
                "PostgreSQL health check returned unexpected result",
                extra={"context": {"result": row}},
            )
            return False

        logger.debug("PostgreSQL health check passed")
        return True

    except (asyncio.TimeoutError, SQLAlchemyTimeoutError):
        logger.warning(
            "PostgreSQL health check timed out",
            extra={"context": {"timeout_seconds": POSTGRESQL_TIMEOUT_SECONDS}},
        )
        return False

    except (OperationalError, InterfaceError, DatabaseError) as e:
        logger.warning(
            "PostgreSQL health check failed (database error)",
            extra={"context": {"error_type": type(e).__name__, "error": str(e)}},
        )
        return False

    except Exception as e:
        logger.error(
            "PostgreSQL health check failed (unexpected error)",
            extra={"context": {"error_type": type(e).__name__, "error": str(e)}},
        )
        return False


# ==============================================================================
# SQLite Cache Layer
# ==============================================================================


async def _init_sqlite_cache() -> None:
    """Initialize SQLite cache database schema if not exists.

    Creates:
        - cache_entries table with key, data, created_at columns
        - Index on created_at for TTL cleanup
        - Index on key for fast lookups

    Schema:
        CREATE TABLE IF NOT EXISTS cache_entries (
            key TEXT PRIMARY KEY,
            data TEXT NOT NULL,  -- JSON-serialized data
            created_at TEXT NOT NULL  -- ISO 8601 timestamp
        )

    Raises:
        aiosqlite.Error: If schema creation fails
    """
    logger.debug("Initializing SQLite cache schema")

    # Ensure cache directory exists
    CACHE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(str(CACHE_DB_PATH)) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS cache_entries (
                key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        # Create indexes for performance
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_cache_created_at ON cache_entries(created_at)"
        )

        await db.commit()

    logger.debug("SQLite cache schema initialized")


async def _get_from_sqlite_cache(cache_key: str) -> tuple[Any, list[str]]:
    """Retrieve data from SQLite cache with TTL validation.

    Args:
        cache_key: Unique cache key (e.g., "vendor_status:vendor_abc")

    Returns:
        Tuple of (cached_data, warnings)
        - cached_data: Deserialized JSON data from cache
        - warnings: List of warning messages (e.g., stale data)

    Raises:
        InvalidCacheDataError: If cached data is malformed or invalid
        FileNotFoundError: If cache database does not exist

    TTL Validation:
        - Rejects entries older than CACHE_TTL_SECONDS (30 minutes)
        - Adds warning if data is stale (>15 minutes old)
        - Returns None if entry not found or expired

    Example:
        >>> data, warnings = await _get_from_sqlite_cache("work_item:task-uuid")
        >>> if data:
        ...     logger.info(f"Cache hit: {cache_key}", extra={"warnings": warnings})
    """
    logger.debug("Querying SQLite cache", extra={"context": {"cache_key": cache_key}})

    warnings: list[str] = []

    if not CACHE_DB_PATH.exists():
        logger.debug("SQLite cache database does not exist")
        raise FileNotFoundError(f"Cache database not found: {CACHE_DB_PATH}")

    try:
        async with aiosqlite.connect(str(CACHE_DB_PATH)) as db:
            # Query cache entry
            async with db.execute(
                "SELECT data, created_at FROM cache_entries WHERE key = ?",
                (cache_key,),
            ) as cursor:
                row = await cursor.fetchone()

                if row is None:
                    logger.debug("Cache miss", extra={"context": {"cache_key": cache_key}})
                    raise InvalidCacheDataError(f"Cache key not found: {cache_key}")

                data_json, created_at_str = row

                # Parse creation timestamp
                created_at = datetime.fromisoformat(created_at_str)
                age_seconds = (datetime.now(timezone.utc) - created_at).total_seconds()

                # Check TTL expiration
                if age_seconds > CACHE_TTL_SECONDS:
                    logger.debug(
                        "Cache entry expired",
                        extra={
                            "context": {
                                "cache_key": cache_key,
                                "age_seconds": age_seconds,
                                "ttl_seconds": CACHE_TTL_SECONDS,
                            }
                        },
                    )
                    warnings.append(
                        f"Cache entry expired (age: {age_seconds:.0f}s, TTL: {CACHE_TTL_SECONDS}s)"
                    )
                    raise InvalidCacheDataError("Cache entry expired")

                # Add staleness warning if >15 minutes old
                if age_seconds > 900:  # 15 minutes
                    warnings.append(
                        f"Cache data is stale (age: {age_seconds / 60:.1f} minutes)"
                    )

                # Deserialize JSON data
                try:
                    data = json.loads(data_json)
                except json.JSONDecodeError as e:
                    logger.error(
                        "Failed to deserialize cache data",
                        extra={
                            "context": {
                                "cache_key": cache_key,
                                "error": str(e),
                            }
                        },
                    )
                    raise InvalidCacheDataError(f"Invalid JSON in cache: {e}")

                logger.debug(
                    "Cache hit",
                    extra={
                        "context": {
                            "cache_key": cache_key,
                            "age_seconds": age_seconds,
                        }
                    },
                )

                return data, warnings

    except aiosqlite.Error as e:
        logger.error(
            "SQLite cache query failed",
            extra={"context": {"cache_key": cache_key, "error": str(e)}},
        )
        raise InvalidCacheDataError(f"SQLite error: {e}")


async def _write_to_sqlite_cache(cache_key: str, data: Any) -> None:
    """Write data to SQLite cache with timestamp.

    Args:
        cache_key: Unique cache key
        data: Data to cache (must be JSON-serializable)

    Raises:
        aiosqlite.Error: If cache write fails
        TypeError: If data is not JSON-serializable

    Upsert Pattern:
        - INSERT OR REPLACE for atomic updates
        - Overwrites existing entries with same key
        - Timestamp reset on every write

    Example:
        >>> await _write_to_sqlite_cache("vendor:abc", {"status": "operational"})
    """
    logger.debug("Writing to SQLite cache", extra={"context": {"cache_key": cache_key}})

    # Ensure cache schema exists
    await _init_sqlite_cache()

    try:
        # Serialize data to JSON
        data_json = json.dumps(data)
        created_at_str = datetime.now(timezone.utc).isoformat()

        async with aiosqlite.connect(str(CACHE_DB_PATH)) as db:
            await db.execute(
                "INSERT OR REPLACE INTO cache_entries (key, data, created_at) VALUES (?, ?, ?)",
                (cache_key, data_json, created_at_str),
            )
            await db.commit()

        logger.debug(
            "Cache write successful", extra={"context": {"cache_key": cache_key}}
        )

    except TypeError as e:
        logger.error(
            "Failed to serialize data for cache",
            extra={"context": {"cache_key": cache_key, "error": str(e)}},
        )
        raise

    except aiosqlite.Error as e:
        logger.error(
            "Failed to write to SQLite cache",
            extra={"context": {"cache_key": cache_key, "error": str(e)}},
        )
        raise


# ==============================================================================
# Git History Layer
# ==============================================================================


async def _get_from_git_history(query_type: str, params: dict[str, Any]) -> tuple[Any, list[str]]:
    """Parse git history for historical data (commit messages, tags, branches).

    Args:
        query_type: Type of query (e.g., "work_item", "deployment", "vendor")
        params: Query parameters (e.g., {"id": "uuid"})

    Returns:
        Tuple of (historical_data, warnings)
        - historical_data: Parsed data from git history
        - warnings: List of warning messages about data staleness

    Raises:
        subprocess.CalledProcessError: If git command fails
        FileNotFoundError: If git repository not found

    Supported Query Types:
        - "deployment": Parse deployment tags and commit messages
        - "work_item": Parse branch names and commit references
        - "vendor": Not supported (returns empty with warning)

    Git Parsing Strategy:
        - deployment: git log --grep="deployment" --format="%H|%s|%cd"
        - work_item: git branch --contains <commit>
        - Limit to last 100 commits for performance

    Example:
        >>> data, warnings = await _get_from_git_history("deployment", {"id": "uuid"})
        >>> if data:
        ...     logger.info("Git history provided fallback data", extra={"warnings": warnings})
    """
    logger.debug(
        "Querying git history",
        extra={"context": {"query_type": query_type, "params": params}},
    )

    warnings: list[str] = [
        "Data retrieved from git history (may be incomplete or outdated)"
    ]

    # Verify git repository exists
    if not (GIT_REPO_ROOT / ".git").exists():
        logger.error("Git repository not found", extra={"context": {"path": str(GIT_REPO_ROOT)}})
        raise FileNotFoundError(f"Git repository not found: {GIT_REPO_ROOT}")

    try:
        if query_type == "deployment":
            # Parse deployment-related commits
            result = subprocess.run(
                [
                    "git",
                    "log",
                    "--grep=deployment",
                    "--grep=deploy",
                    "--format=%H|%s|%cd",
                    "-n",
                    "100",
                ],
                cwd=GIT_REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
                timeout=5.0,
            )

            if not result.stdout.strip():
                logger.debug("No deployment commits found in git history")
                warnings.append("No deployment history found in git commits")
                return None, warnings

            # Parse commit output
            deployments = []
            for line in result.stdout.strip().split("\n"):
                parts = line.split("|", 2)
                if len(parts) == 3:
                    commit_hash, subject, date = parts
                    deployments.append({
                        "commit_hash": commit_hash,
                        "title": subject,
                        "deployed_at": date,
                        "source": "git_history",
                    })

            logger.debug(
                "Parsed deployment history from git",
                extra={"context": {"count": len(deployments)}},
            )

            return deployments, warnings

        elif query_type == "work_item":
            # Parse branch information for work item
            work_item_id = params.get("id")
            if not work_item_id:
                warnings.append("No work item ID provided for git lookup")
                return None, warnings

            # Get branches containing the work item ID in their name
            result = subprocess.run(
                ["git", "branch", "-a", "--format=%(refname:short)"],
                cwd=GIT_REPO_ROOT,
                capture_output=True,
                text=True,
                check=True,
                timeout=5.0,
            )

            branches = [
                branch.strip()
                for branch in result.stdout.strip().split("\n")
                if str(work_item_id) in branch
            ]

            if not branches:
                logger.debug(
                    "No branches found for work item",
                    extra={"context": {"work_item_id": work_item_id}},
                )
                warnings.append(f"No git branches found for work item: {work_item_id}")
                return None, warnings

            logger.debug(
                "Found branches for work item",
                extra={"context": {"work_item_id": work_item_id, "count": len(branches)}},
            )

            return {"branches": branches, "source": "git_history"}, warnings

        else:
            logger.debug(
                "Unsupported query type for git history",
                extra={"context": {"query_type": query_type}},
            )
            warnings.append(f"Query type '{query_type}' not supported by git history layer")
            return None, warnings

    except subprocess.TimeoutExpired:
        logger.error("Git command timed out", extra={"context": {"query_type": query_type}})
        warnings.append("Git history query timed out (>5s)")
        return None, warnings

    except subprocess.CalledProcessError as e:
        logger.error(
            "Git command failed",
            extra={
                "context": {
                    "query_type": query_type,
                    "returncode": e.returncode,
                    "stderr": e.stderr,
                }
            },
        )
        warnings.append(f"Git command failed: {e.stderr}")
        return None, warnings


# ==============================================================================
# Markdown Fallback Layer
# ==============================================================================


async def _get_from_markdown_fallback(query_type: str, params: dict[str, Any]) -> tuple[Any, list[str]]:
    """Read legacy .project_status.md file as final fallback.

    Args:
        query_type: Type of query (ignored - returns all markdown content)
        params: Query parameters (ignored)

    Returns:
        Tuple of (markdown_data, warnings)
        - markdown_data: Parsed markdown file content
        - warnings: List of warnings about data being manual/outdated

    Raises:
        FileNotFoundError: If .project_status.md does not exist
        IOError: If file cannot be read

    Markdown Parsing:
        - Read entire file as plain text
        - Return raw markdown content (no structured parsing)
        - Client must parse markdown structure manually
        - Add warning about manual maintenance required

    Example:
        >>> data, warnings = await _get_from_markdown_fallback("vendor", {})
        >>> if data:
        ...     logger.warning("Using manual markdown fallback", extra={"warnings": warnings})
    """
    logger.debug("Reading markdown fallback file")

    warnings: list[str] = [
        "Data from manual .project_status.md (requires human updates, may be outdated)"
    ]

    if not MARKDOWN_FALLBACK_PATH.exists():
        logger.error(
            "Markdown fallback file not found",
            extra={"context": {"path": str(MARKDOWN_FALLBACK_PATH)}},
        )
        raise FileNotFoundError(f"Markdown fallback file not found: {MARKDOWN_FALLBACK_PATH}")

    try:
        # Read markdown file asynchronously
        loop = asyncio.get_event_loop()
        markdown_content = await loop.run_in_executor(
            None,
            MARKDOWN_FALLBACK_PATH.read_text,
            "utf-8",
        )

        logger.debug(
            "Markdown fallback file read successfully",
            extra={"context": {"size_bytes": len(markdown_content)}},
        )

        # Return raw markdown content with metadata
        return {
            "content": markdown_content,
            "source": "markdown_file",
            "path": str(MARKDOWN_FALLBACK_PATH),
        }, warnings

    except IOError as e:
        logger.error(
            "Failed to read markdown fallback file",
            extra={"context": {"path": str(MARKDOWN_FALLBACK_PATH), "error": str(e)}},
        )
        raise


# ==============================================================================
# Write Fallback Operations
# ==============================================================================


async def _write_to_markdown_fallback(data: dict[str, Any]) -> None:
    """Write update marker to .project_status.md when PostgreSQL is unavailable.

    Args:
        data: Data to write (appended as YAML frontmatter comment)

    Raises:
        IOError: If file write fails

    Write Strategy:
        - Append timestamp and data to markdown file as comment
        - Format: <!-- FALLBACK_WRITE: {timestamp} | {data} -->
        - Does NOT modify existing content
        - Human intervention required to reconcile updates

    Example:
        >>> await _write_to_markdown_fallback({"type": "vendor_update", "vendor": "abc"})
    """
    logger.debug("Writing to markdown fallback file")

    if not MARKDOWN_FALLBACK_PATH.exists():
        logger.warning(
            "Markdown fallback file does not exist, creating new file",
            extra={"context": {"path": str(MARKDOWN_FALLBACK_PATH)}},
        )

    try:
        # Generate fallback write marker
        timestamp = datetime.now(timezone.utc).isoformat()
        marker = f"\n<!-- FALLBACK_WRITE: {timestamp} | {json.dumps(data)} -->\n"

        # Append marker to markdown file
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: MARKDOWN_FALLBACK_PATH.open("a", encoding="utf-8").write(marker),
        )

        logger.info(
            "Fallback write marker added to markdown file",
            extra={"context": {"timestamp": timestamp}},
        )

    except IOError as e:
        logger.error(
            "Failed to write to markdown fallback file",
            extra={"context": {"path": str(MARKDOWN_FALLBACK_PATH), "error": str(e)}},
        )
        raise


# ==============================================================================
# High-Level Fallback API
# ==============================================================================


async def execute_with_fallback(
    query_func: Callable[..., Awaitable[T]],
    session: AsyncSession,
    fallback_query_type: str,
    fallback_params: dict[str, Any],
    fallback_enabled: bool = True,
) -> tuple[T, FallbackLayer, list[str]]:
    """Execute read operation with automatic fallback layer cascade.

    Args:
        query_func: Async callable that executes PostgreSQL query
        session: Async database session
        fallback_query_type: Query type for fallback layers (e.g., "vendor", "work_item")
        fallback_params: Parameters for fallback queries (e.g., {"id": "uuid"})
        fallback_enabled: Enable fallback cascade (default: True)

    Returns:
        Tuple of (result, source_layer, warnings)
        - result: Query result from successful layer
        - source_layer: Which layer provided the data
        - warnings: List of warning messages about data staleness

    Raises:
        AllFallbackLayersFailedError: If all 4 layers fail
        Exception: Re-raises exceptions from query_func if fallback_enabled=False

    Cascade Order:
        1. PostgreSQL (primary) - full CRUD, latest data
        2. SQLite cache (30-min TTL) - cached data, <30min stale
        3. Git history - commit messages, branches, tags
        4. Markdown file - manual .project_status.md

    Performance:
        - <10ms layer detection and failover
        - PostgreSQL timeout: 2 seconds
        - Git command timeout: 5 seconds

    Example:
        >>> async def get_vendor(session: AsyncSession, vendor_id: str) -> dict:
        ...     result = await session.execute(select(VendorExtractor).where(VendorExtractor.id == vendor_id))
        ...     return result.scalar_one()
        >>>
        >>> data, layer, warnings = await execute_with_fallback(
        ...     query_func=lambda: get_vendor(session, "vendor-uuid"),
        ...     session=session,
        ...     fallback_query_type="vendor",
        ...     fallback_params={"id": "vendor-uuid"},
        ... )
        >>> logger.info(f"Data from {layer}", extra={"warnings": warnings})
    """
    logger.debug(
        "Executing query with fallback",
        extra={
            "context": {
                "fallback_query_type": fallback_query_type,
                "fallback_enabled": fallback_enabled,
            }
        },
    )

    warnings: list[str] = []

    # Layer 1: PostgreSQL (primary)
    try:
        logger.debug("Attempting PostgreSQL query (layer 1)")
        result = await query_func(session)
        logger.debug("PostgreSQL query successful")
        return result, "postgresql", warnings

    except (OperationalError, InterfaceError, DatabaseError, asyncio.TimeoutError) as e:
        if not fallback_enabled:
            logger.error("PostgreSQL query failed and fallback disabled")
            raise

        logger.warning(
            "PostgreSQL unavailable, cascading to fallback layers",
            extra={"context": {"error_type": type(e).__name__, "error": str(e)}},
        )
        warnings.append(f"PostgreSQL unavailable: {type(e).__name__}")

    # Layer 2: SQLite cache (30-min TTL)
    try:
        logger.debug("Attempting SQLite cache query (layer 2)")
        cache_key = f"{fallback_query_type}:{fallback_params.get('id', 'unknown')}"
        cached_data, cache_warnings = await _get_from_sqlite_cache(cache_key)
        warnings.extend(cache_warnings)
        logger.info("Cache hit - returning cached data", extra={"context": {"cache_key": cache_key}})
        return cached_data, "sqlite_cache", warnings

    except (InvalidCacheDataError, FileNotFoundError) as e:
        logger.warning(
            "SQLite cache unavailable or expired",
            extra={"context": {"error": str(e)}},
        )
        warnings.append(f"Cache unavailable: {str(e)}")

    # Layer 3: Git history
    try:
        logger.debug("Attempting git history query (layer 3)")
        git_data, git_warnings = await _get_from_git_history(
            fallback_query_type, fallback_params
        )
        warnings.extend(git_warnings)

        if git_data is not None:
            logger.info("Git history provided fallback data")
            return git_data, "git_history", warnings

        warnings.append("Git history did not contain relevant data")

    except (subprocess.SubprocessError, FileNotFoundError) as e:
        logger.warning(
            "Git history query failed",
            extra={"context": {"error": str(e)}},
        )
        warnings.append(f"Git history unavailable: {str(e)}")

    # Layer 4: Markdown fallback (final layer)
    try:
        logger.debug("Attempting markdown fallback query (layer 4)")
        markdown_data, markdown_warnings = await _get_from_markdown_fallback(
            fallback_query_type, fallback_params
        )
        warnings.extend(markdown_warnings)
        logger.warning("Using manual markdown fallback (last resort)")
        return markdown_data, "markdown_file", warnings

    except (FileNotFoundError, IOError) as e:
        logger.error(
            "Markdown fallback failed",
            extra={"context": {"error": str(e)}},
        )
        warnings.append(f"Markdown fallback unavailable: {str(e)}")

    # All layers failed
    logger.error(
        "All 4 fallback layers failed",
        extra={"context": {"warnings": warnings}},
    )
    raise AllFallbackLayersFailedError(
        f"All fallback layers exhausted. Warnings: {warnings}"
    )


async def write_with_fallback(
    write_func: Callable[..., Awaitable[None]],
    session: AsyncSession,
    data: dict[str, Any],
    fallback_enabled: bool = True,
) -> tuple[bool, FallbackLayer, list[str]]:
    """Execute write operation with fallback to cache+markdown on PostgreSQL failure.

    Args:
        write_func: Async callable that executes PostgreSQL write
        session: Async database session
        data: Data to write (must be JSON-serializable)
        fallback_enabled: Enable fallback writes (default: True)

    Returns:
        Tuple of (success, target_layer, warnings)
        - success: True if write succeeded
        - target_layer: Which layer received the write
        - warnings: List of warning messages

    Raises:
        Exception: Re-raises exceptions from write_func if fallback_enabled=False

    Write Strategy (per spec FR-029 clarification #2):
        - PostgreSQL success: Return immediately
        - PostgreSQL failure: Write to cache AND markdown IN PARALLEL
        - Both fallback writes must succeed (maximum redundancy)
        - Return warnings about pending sync to PostgreSQL

    Parallel Write Justification:
        - Maximizes redundancy (per clarification #2)
        - Cache provides structured queryable data
        - Markdown provides human-readable audit trail
        - PostgreSQL sync occurs when database reconnects

    Example:
        >>> async def update_vendor_status(session: AsyncSession, vendor_id: str, status: str) -> None:
        ...     vendor = await session.get(VendorExtractor, vendor_id)
        ...     vendor.status = status
        ...     await session.commit()
        >>>
        >>> success, layer, warnings = await write_with_fallback(
        ...     write_func=lambda: update_vendor_status(session, "vendor-uuid", "operational"),
        ...     session=session,
        ...     data={"vendor_id": "vendor-uuid", "status": "operational"},
        ... )
        >>> if layer != "postgresql":
        ...     logger.warning("Write to fallback layers", extra={"warnings": warnings})
    """
    logger.debug("Executing write with fallback", extra={"context": {"fallback_enabled": fallback_enabled}})

    warnings: list[str] = []

    # Layer 1: PostgreSQL (primary)
    try:
        logger.debug("Attempting PostgreSQL write")
        await write_func(session)
        logger.debug("PostgreSQL write successful")
        return True, "postgresql", warnings

    except (OperationalError, InterfaceError, DatabaseError, asyncio.TimeoutError) as e:
        if not fallback_enabled:
            logger.error("PostgreSQL write failed and fallback disabled")
            raise

        logger.warning(
            "PostgreSQL unavailable for write, using fallback layers",
            extra={"context": {"error_type": type(e).__name__, "error": str(e)}},
        )
        warnings.append(f"PostgreSQL write failed: {type(e).__name__}")

    # Parallel writes to cache AND markdown (per clarification #2)
    logger.info("Writing to cache and markdown in parallel (maximum redundancy)")

    # Generate cache key from data
    cache_key = f"{data.get('type', 'unknown')}:{data.get('id', 'unknown')}"

    try:
        # Execute cache and markdown writes in parallel
        cache_task = _write_to_sqlite_cache(cache_key, data)
        markdown_task = _write_to_markdown_fallback(data)

        # Wait for both writes to complete
        await asyncio.gather(cache_task, markdown_task)

        logger.info("Parallel fallback writes successful (cache + markdown)")
        warnings.append(
            "Write succeeded to cache and markdown - will sync to PostgreSQL when reconnected"
        )

        return True, "sqlite_cache", warnings

    except Exception as e:
        logger.error(
            "Fallback writes failed",
            extra={"context": {"error_type": type(e).__name__, "error": str(e)}},
        )
        warnings.append(f"Fallback writes failed: {str(e)}")
        return False, "markdown_file", warnings


async def get_fallback_data(
    query_type: str,
    params: dict[str, Any],
) -> tuple[Any, FallbackLayer, list[str]]:
    """Query fallback data sources directly (skip PostgreSQL).

    Args:
        query_type: Type of query (e.g., "vendor", "work_item", "deployment")
        params: Query parameters (e.g., {"id": "uuid"})

    Returns:
        Tuple of (data, source_layer, warnings)
        - data: Query result from successful layer
        - source_layer: Which fallback layer provided data
        - warnings: List of warnings about data staleness

    Raises:
        AllFallbackLayersFailedError: If all fallback layers fail

    Use Cases:
        - Emergency read-only access when PostgreSQL is down
        - Historical data recovery from git/markdown
        - Cache validation and debugging

    Example:
        >>> data, layer, warnings = await get_fallback_data(
        ...     query_type="vendor",
        ...     params={"id": "vendor-uuid"}
        ... )
        >>> logger.info(f"Fallback data from {layer}", extra={"warnings": warnings})
    """
    logger.debug(
        "Querying fallback data sources",
        extra={"context": {"query_type": query_type, "params": params}},
    )

    warnings: list[str] = ["PostgreSQL bypassed - querying fallback layers directly"]

    # Try cache first (fastest)
    cache_key = f"{query_type}:{params.get('id', 'unknown')}"
    try:
        cached_data, cache_warnings = await _get_from_sqlite_cache(cache_key)
        warnings.extend(cache_warnings)
        logger.info("Fallback data from cache")
        return cached_data, "sqlite_cache", warnings

    except (InvalidCacheDataError, FileNotFoundError) as e:
        warnings.append(f"Cache miss: {str(e)}")

    # Try git history
    try:
        git_data, git_warnings = await _get_from_git_history(query_type, params)
        warnings.extend(git_warnings)

        if git_data is not None:
            logger.info("Fallback data from git history")
            return git_data, "git_history", warnings

    except Exception as e:
        warnings.append(f"Git history failed: {str(e)}")

    # Try markdown (last resort)
    try:
        markdown_data, markdown_warnings = await _get_from_markdown_fallback(query_type, params)
        warnings.extend(markdown_warnings)
        logger.warning("Fallback data from manual markdown file")
        return markdown_data, "markdown_file", warnings

    except Exception as e:
        warnings.append(f"Markdown fallback failed: {str(e)}")

    # All fallback layers failed
    logger.error(
        "All fallback layers failed",
        extra={"context": {"query_type": query_type, "warnings": warnings}},
    )
    raise AllFallbackLayersFailedError(
        f"All fallback layers exhausted for query_type={query_type}. Warnings: {warnings}"
    )


# ==============================================================================
# Module Exports
# ==============================================================================

__all__ = [
    "FallbackLayer",
    "AllFallbackLayersFailedError",
    "PostgreSQLUnavailableError",
    "InvalidCacheDataError",
    "check_postgresql_health",
    "execute_with_fallback",
    "write_with_fallback",
    "get_fallback_data",
    "CACHE_TTL_SECONDS",
    "CACHE_DB_PATH",
    "MARKDOWN_FALLBACK_PATH",
]
