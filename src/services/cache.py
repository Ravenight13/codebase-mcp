"""SQLite cache service for offline fallback with 30-minute TTL.

Provides async SQLite-based caching for vendor extractors and work items when PostgreSQL
is unavailable. Supports 30-minute TTL, schema mirroring, and async context managers.

Constitutional Compliance:
- Principle II: Local-first (file-based persistence, no external dependencies)
- Principle III: Protocol compliance (async operations matching AsyncPG patterns)
- Principle IV: Performance (<1ms cache lookups via indexed keys)
- Principle V: Production quality (comprehensive error handling, TTL enforcement)
- Principle VIII: Type safety (full mypy --strict compliance)

Key Features:
- Async context manager support for automatic connection management
- 30-minute TTL on all cached entries with automatic staleness detection
- Schema mirroring (VendorExtractor, WorkItem) matching PostgreSQL tables
- JSON serialization for complex Pydantic models
- Batch operations for stale entry cleanup
- File-based persistence at cache/project_status.db

Performance Targets:
- <1ms for single cache lookups (indexed primary keys)
- <100ms for bulk stale entry cleanup
- Automatic initialization on first use

Usage Example:
    >>> cache = SQLiteCache()
    >>> async with cache:
    ...     # Cache a vendor extractor
    ...     vendor_data = {
    ...         "id": str(uuid4()),
    ...         "name": "vendor_abc",
    ...         "status": "operational",
    ...         "version": 1,
    ...         "extractor_version": "2.3.1",
    ...         "metadata_": {...},
    ...         "created_at": datetime.now(timezone.utc).isoformat(),
    ...         "updated_at": datetime.now(timezone.utc).isoformat(),
    ...         "created_by": "mcp-client"
    ...     }
    ...     await cache.set_vendor("vendor_abc", vendor_data)
    ...
    ...     # Retrieve cached vendor
    ...     cached = await cache.get_vendor("vendor_abc")
    ...     if cached:
    ...         print(f"Found cached vendor: {cached['name']}")
    ...
    ...     # Check if cache entry is stale
    ...     if await cache.is_stale("vendor:vendor_abc"):
    ...         print("Cache entry expired (>30 minutes old)")
    ...
    ...     # Remove all stale entries
    ...     removed_count = await cache.clear_stale()
    ...     print(f"Removed {removed_count} stale entries")
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Final, Literal
from uuid import UUID

import aiosqlite
from pydantic import BaseModel, Field

from src.mcp.mcp_logging import get_logger

# ==============================================================================
# Constants
# ==============================================================================

logger = get_logger(__name__)

# Cache configuration
DEFAULT_CACHE_PATH: Final[Path] = Path("cache/project_status.db")
TTL_MINUTES: Final[int] = 30
STALENESS_THRESHOLD_SECONDS: Final[float] = TTL_MINUTES * 60  # 1800 seconds

# Schema version for cache migrations
CACHE_SCHEMA_VERSION: Final[int] = 1


# ==============================================================================
# Pydantic Models
# ==============================================================================


class CacheStats(BaseModel):
    """Statistics for cache operations.

    Attributes:
        total_entries: Total number of cached entries across all tables
        stale_entries: Number of entries exceeding TTL threshold
        vendors_cached: Count of cached vendor extractors
        work_items_cached: Count of cached work items
        oldest_entry_age_seconds: Age of oldest cache entry in seconds
    """

    total_entries: int = Field(ge=0)
    stale_entries: int = Field(ge=0)
    vendors_cached: int = Field(ge=0)
    work_items_cached: int = Field(ge=0)
    oldest_entry_age_seconds: float = Field(ge=0.0)

    model_config = {"frozen": True}


# ==============================================================================
# SQLite Cache Service
# ==============================================================================


class SQLiteCache:
    """Async SQLite cache for offline fallback with 30-minute TTL.

    Provides persistent caching for vendor extractors and work items when PostgreSQL
    is unavailable. All cached entries expire after 30 minutes and can be automatically
    cleaned up via clear_stale().

    Attributes:
        db_path: Path to SQLite database file (default: cache/project_status.db)
        _conn: Async SQLite connection (None until initialized)
        _initialized: Flag indicating schema creation status

    Schema:
        - cached_vendors: Vendor extractor cache with name as primary key
        - cached_work_items: Work item cache with UUID as primary key
        - cache_metadata: Schema version and statistics tracking

    Performance:
        - Indexed lookups via primary keys (name for vendors, id for work items)
        - Batch cleanup for stale entries
        - Row factory for dict-based result access
    """

    def __init__(self, db_path: Path = DEFAULT_CACHE_PATH) -> None:
        """Initialize SQLite cache with specified database path.

        Args:
            db_path: Path to SQLite database file (default: cache/project_status.db)
        """
        self.db_path: Path = db_path
        self._conn: aiosqlite.Connection | None = None
        self._initialized: bool = False

        logger.debug(f"SQLiteCache initialized with path: {self.db_path}")

    async def __aenter__(self) -> SQLiteCache:
        """Async context manager entry: open connection and initialize schema.

        Returns:
            Self for use in async with statement

        Raises:
            RuntimeError: If database connection fails
        """
        await self._connect()
        await self._initialize_schema()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit: close connection and cleanup.

        Args:
            exc_type: Exception type if error occurred
            exc_val: Exception value if error occurred
            exc_tb: Exception traceback if error occurred
        """
        await self._close()

    async def _connect(self) -> None:
        """Open async SQLite connection with row factory configuration.

        Creates parent directory if it doesn't exist.

        Raises:
            RuntimeError: If connection fails or db_path is invalid
        """
        try:
            # Ensure parent directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Open connection with row factory for dict-based access
            self._conn = await aiosqlite.connect(str(self.db_path))
            self._conn.row_factory = aiosqlite.Row

            logger.info(f"SQLite connection opened: {self.db_path}")

        except Exception as e:
            logger.error(f"Failed to connect to SQLite at {self.db_path}: {e}")
            raise RuntimeError(f"SQLite connection failed: {e}") from e

    async def _close(self) -> None:
        """Close async SQLite connection if open."""
        if self._conn:
            await self._conn.close()
            self._conn = None
            logger.debug("SQLite connection closed")

    async def _initialize_schema(self) -> None:
        """Create cache schema if not exists.

        Creates three tables:
        1. cached_vendors: Vendor extractor cache with name PK
        2. cached_work_items: Work item cache with UUID PK
        3. cache_metadata: Schema version and statistics

        All tables include cached_at timestamp for TTL enforcement.

        Raises:
            RuntimeError: If schema creation fails
        """
        if self._initialized:
            return

        if not self._conn:
            raise RuntimeError("Cannot initialize schema: connection not established")

        try:
            # Create cached_vendors table
            await self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cached_vendors (
                    name TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    cached_at REAL NOT NULL
                )
                """
            )

            # Create cached_work_items table
            await self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cached_work_items (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    cached_at REAL NOT NULL
                )
                """
            )

            # Create cache_metadata table for version tracking
            await self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )

            # Insert schema version if not exists
            await self._conn.execute(
                """
                INSERT OR IGNORE INTO cache_metadata (key, value, updated_at)
                VALUES ('schema_version', ?, ?)
                """,
                (str(CACHE_SCHEMA_VERSION), time.time()),
            )

            # Create indexes for TTL queries
            await self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_vendors_cached_at
                ON cached_vendors (cached_at)
                """
            )
            await self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_work_items_cached_at
                ON cached_work_items (cached_at)
                """
            )

            await self._conn.commit()

            self._initialized = True
            logger.info(f"SQLite cache schema initialized (version {CACHE_SCHEMA_VERSION})")

        except Exception as e:
            logger.error(f"Failed to initialize cache schema: {e}")
            raise RuntimeError(f"Schema initialization failed: {e}") from e

    # ==========================================================================
    # Vendor Extractor Cache Operations
    # ==========================================================================

    async def get_vendor(self, name: str) -> dict[str, Any] | None:
        """Retrieve cached vendor extractor by name.

        Args:
            name: Vendor name (primary key)

        Returns:
            Vendor data dict if found and not stale, None otherwise

        Performance:
            <1ms via indexed primary key lookup
        """
        if not self._conn:
            raise RuntimeError("Cache not connected. Use async context manager.")

        try:
            cursor = await self._conn.execute(
                """
                SELECT data, cached_at FROM cached_vendors WHERE name = ?
                """,
                (name,),
            )
            row = await cursor.fetchone()

            if not row:
                logger.debug(f"Cache miss: vendor '{name}' not found")
                return None

            # Check TTL
            cached_at: float = row["cached_at"]
            age_seconds = time.time() - cached_at

            if age_seconds > STALENESS_THRESHOLD_SECONDS:
                logger.debug(
                    f"Cache stale: vendor '{name}' (age: {age_seconds:.1f}s > {STALENESS_THRESHOLD_SECONDS}s)"
                )
                return None

            # Deserialize JSON data
            data: dict[str, Any] = json.loads(row["data"])
            logger.debug(f"Cache hit: vendor '{name}' (age: {age_seconds:.1f}s)")
            return data

        except Exception as e:
            logger.error(f"Failed to get cached vendor '{name}': {e}")
            return None

    async def set_vendor(self, name: str, data: dict[str, Any]) -> None:
        """Cache vendor extractor data with current timestamp.

        Args:
            name: Vendor name (primary key)
            data: Vendor data dict (JSON-serializable)

        Raises:
            RuntimeError: If cache write fails
        """
        if not self._conn:
            raise RuntimeError("Cache not connected. Use async context manager.")

        try:
            # Serialize data to JSON
            json_data = json.dumps(data, default=str)  # default=str for UUID/datetime
            cached_at = time.time()

            # INSERT OR REPLACE for upsert behavior
            await self._conn.execute(
                """
                INSERT OR REPLACE INTO cached_vendors (name, data, cached_at)
                VALUES (?, ?, ?)
                """,
                (name, json_data, cached_at),
            )
            await self._conn.commit()

            logger.debug(f"Cached vendor: '{name}' (size: {len(json_data)} bytes)")

        except Exception as e:
            logger.error(f"Failed to cache vendor '{name}': {e}")
            raise RuntimeError(f"Cache write failed for vendor '{name}': {e}") from e

    # ==========================================================================
    # Work Item Cache Operations
    # ==========================================================================

    async def get_work_item(self, item_id: UUID) -> dict[str, Any] | None:
        """Retrieve cached work item by UUID.

        Args:
            item_id: Work item UUID (primary key)

        Returns:
            Work item data dict if found and not stale, None otherwise

        Performance:
            <1ms via indexed primary key lookup
        """
        if not self._conn:
            raise RuntimeError("Cache not connected. Use async context manager.")

        try:
            cursor = await self._conn.execute(
                """
                SELECT data, cached_at FROM cached_work_items WHERE id = ?
                """,
                (str(item_id),),
            )
            row = await cursor.fetchone()

            if not row:
                logger.debug(f"Cache miss: work item '{item_id}' not found")
                return None

            # Check TTL
            cached_at: float = row["cached_at"]
            age_seconds = time.time() - cached_at

            if age_seconds > STALENESS_THRESHOLD_SECONDS:
                logger.debug(
                    f"Cache stale: work item '{item_id}' (age: {age_seconds:.1f}s > {STALENESS_THRESHOLD_SECONDS}s)"
                )
                return None

            # Deserialize JSON data
            data: dict[str, Any] = json.loads(row["data"])
            logger.debug(f"Cache hit: work item '{item_id}' (age: {age_seconds:.1f}s)")
            return data

        except Exception as e:
            logger.error(f"Failed to get cached work item '{item_id}': {e}")
            return None

    async def set_work_item(self, item_id: UUID, data: dict[str, Any]) -> None:
        """Cache work item data with current timestamp.

        Args:
            item_id: Work item UUID (primary key)
            data: Work item data dict (JSON-serializable)

        Raises:
            RuntimeError: If cache write fails
        """
        if not self._conn:
            raise RuntimeError("Cache not connected. Use async context manager.")

        try:
            # Serialize data to JSON
            json_data = json.dumps(data, default=str)  # default=str for UUID/datetime
            cached_at = time.time()

            # INSERT OR REPLACE for upsert behavior
            await self._conn.execute(
                """
                INSERT OR REPLACE INTO cached_work_items (id, data, cached_at)
                VALUES (?, ?, ?)
                """,
                (str(item_id), json_data, cached_at),
            )
            await self._conn.commit()

            logger.debug(f"Cached work item: '{item_id}' (size: {len(json_data)} bytes)")

        except Exception as e:
            logger.error(f"Failed to cache work item '{item_id}': {e}")
            raise RuntimeError(f"Cache write failed for work item '{item_id}': {e}") from e

    # ==========================================================================
    # TTL and Cleanup Operations
    # ==========================================================================

    async def is_stale(self, cache_key: str) -> bool:
        """Check if cache entry exceeds 30-minute TTL threshold.

        Args:
            cache_key: Cache key in format "table:primary_key"
                      (e.g., "vendor:vendor_abc" or "work_item:uuid")

        Returns:
            True if entry is stale or not found, False if fresh

        Raises:
            ValueError: If cache_key format is invalid
        """
        if not self._conn:
            raise RuntimeError("Cache not connected. Use async context manager.")

        # Parse cache key
        parts = cache_key.split(":", 1)
        if len(parts) != 2:
            raise ValueError(
                f"Invalid cache_key format: '{cache_key}'. Expected 'table:key' format."
            )

        table_prefix, primary_key = parts

        # Determine table and column based on prefix
        if table_prefix == "vendor":
            table = "cached_vendors"
            column = "name"
        elif table_prefix == "work_item":
            table = "cached_work_items"
            column = "id"
        else:
            raise ValueError(
                f"Unknown table prefix: '{table_prefix}'. Expected 'vendor' or 'work_item'."
            )

        try:
            # Query cached_at timestamp
            cursor = await self._conn.execute(
                f"SELECT cached_at FROM {table} WHERE {column} = ?",
                (primary_key,),
            )
            row = await cursor.fetchone()

            if not row:
                # Entry not found = considered stale
                return True

            # Check staleness threshold
            cached_at: float = row["cached_at"]
            age_seconds = time.time() - cached_at
            is_stale = age_seconds > STALENESS_THRESHOLD_SECONDS

            logger.debug(
                f"Staleness check: {cache_key} - age={age_seconds:.1f}s, stale={is_stale}"
            )
            return is_stale

        except Exception as e:
            logger.error(f"Failed to check staleness for '{cache_key}': {e}")
            # On database error, consider entry stale to trigger refresh
            return True

    async def clear_stale(self) -> int:
        """Remove all cache entries exceeding 30-minute TTL.

        Deletes stale entries from both cached_vendors and cached_work_items tables.

        Returns:
            Total number of entries removed

        Raises:
            RuntimeError: If cleanup operation fails
        """
        if not self._conn:
            raise RuntimeError("Cache not connected. Use async context manager.")

        try:
            current_time = time.time()
            cutoff_time = current_time - STALENESS_THRESHOLD_SECONDS

            # Delete stale vendors
            cursor_vendors = await self._conn.execute(
                "DELETE FROM cached_vendors WHERE cached_at < ?",
                (cutoff_time,),
            )

            # Delete stale work items
            cursor_work_items = await self._conn.execute(
                "DELETE FROM cached_work_items WHERE cached_at < ?",
                (cutoff_time,),
            )

            await self._conn.commit()

            # Calculate total removed
            vendors_removed: int = cursor_vendors.rowcount or 0
            work_items_removed: int = cursor_work_items.rowcount or 0
            total_removed: int = vendors_removed + work_items_removed

            logger.info(
                f"Cleared {total_removed} stale entries "
                f"(vendors: {vendors_removed}, work_items: {work_items_removed})"
            )

            return total_removed

        except Exception as e:
            logger.error(f"Failed to clear stale cache entries: {e}")
            raise RuntimeError(f"Stale entry cleanup failed: {e}") from e

    async def get_stats(self) -> CacheStats:
        """Calculate cache statistics including staleness metrics.

        Returns:
            CacheStats with entry counts and age information

        Performance:
            <10ms for full cache scan with COUNT queries
        """
        if not self._conn:
            raise RuntimeError("Cache not connected. Use async context manager.")

        try:
            current_time = time.time()
            cutoff_time = current_time - STALENESS_THRESHOLD_SECONDS

            # Count vendors
            cursor = await self._conn.execute("SELECT COUNT(*) as count FROM cached_vendors")
            row = await cursor.fetchone()
            vendors_cached: int = row["count"] if row else 0

            # Count work items
            cursor = await self._conn.execute("SELECT COUNT(*) as count FROM cached_work_items")
            row = await cursor.fetchone()
            work_items_cached: int = row["count"] if row else 0

            # Count stale entries
            cursor = await self._conn.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM cached_vendors WHERE cached_at < ?) +
                    (SELECT COUNT(*) FROM cached_work_items WHERE cached_at < ?)
                    as stale_count
                """,
                (cutoff_time, cutoff_time),
            )
            row = await cursor.fetchone()
            stale_entries: int = row["stale_count"] if row else 0

            # Find oldest entry age
            cursor = await self._conn.execute(
                """
                SELECT MIN(cached_at) as oldest FROM (
                    SELECT cached_at FROM cached_vendors
                    UNION ALL
                    SELECT cached_at FROM cached_work_items
                )
                """
            )
            row = await cursor.fetchone()
            oldest_cached_at: float | None = row["oldest"] if row else None

            oldest_entry_age_seconds = (
                current_time - oldest_cached_at if oldest_cached_at else 0.0
            )

            total_entries = vendors_cached + work_items_cached

            stats = CacheStats(
                total_entries=total_entries,
                stale_entries=stale_entries,
                vendors_cached=vendors_cached,
                work_items_cached=work_items_cached,
                oldest_entry_age_seconds=oldest_entry_age_seconds,
            )

            logger.debug(f"Cache stats: {stats.model_dump()}")
            return stats

        except Exception as e:
            logger.error(f"Failed to calculate cache stats: {e}")
            # Return empty stats on error
            return CacheStats(
                total_entries=0,
                stale_entries=0,
                vendors_cached=0,
                work_items_cached=0,
                oldest_entry_age_seconds=0.0,
            )

    async def clear_all(self) -> int:
        """Clear all cache entries (vendors and work items).

        Returns:
            Total number of entries removed

        Raises:
            RuntimeError: If clear operation fails
        """
        if not self._conn:
            raise RuntimeError("Cache not connected. Use async context manager.")

        try:
            # Delete all vendors
            cursor_vendors = await self._conn.execute("DELETE FROM cached_vendors")

            # Delete all work items
            cursor_work_items = await self._conn.execute("DELETE FROM cached_work_items")

            await self._conn.commit()

            # Calculate total removed
            vendors_removed: int = cursor_vendors.rowcount or 0
            work_items_removed: int = cursor_work_items.rowcount or 0
            total_removed: int = vendors_removed + work_items_removed

            logger.info(
                f"Cleared all cache entries: {total_removed} "
                f"(vendors: {vendors_removed}, work_items: {work_items_removed})"
            )

            return total_removed

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            raise RuntimeError(f"Cache clear failed: {e}") from e
