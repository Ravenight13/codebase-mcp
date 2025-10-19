"""Async config cache with LRU eviction and mtime validation.

This module provides a production-grade async-safe configuration cache with:
- LRU eviction policy for bounded memory usage
- mtime-based automatic cache invalidation
- asyncio.Lock for async-safe concurrent access
- Comprehensive logging for debugging and monitoring

Constitutional Compliance:
- Principle 8: Complete Pydantic/type safety (dataclasses + type annotations)
- Principle 4: Performance guarantee (<50ms cache lookup)
- Principle 5: Production quality error handling
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import asyncio
import logging
import time

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with mtime-based invalidation.

    Attributes:
        config: Parsed configuration dictionary
        config_path: Path to config file for mtime tracking
        mtime_ns: File modification time in nanoseconds (high precision)
        access_time: Last access timestamp for LRU eviction
    """
    config: Dict[str, Any]
    config_path: Path
    mtime_ns: int
    access_time: float


class ConfigCache:
    """Async-safe LRU cache with mtime-based automatic invalidation.

    Design:
        - Uses asyncio.Lock for async-safe concurrent access
        - LRU eviction based on access_time when max_size reached
        - Automatic cache invalidation when config file mtime changes
        - Invalidation on file deletion or access errors

    Performance:
        - Cache hit: O(1) lookup + O(1) stat() syscall
        - Cache miss: O(1) lookup
        - Eviction: O(n) scan to find oldest entry (acceptable for max_size=100)

    Thread Safety:
        - All public methods use async with self._lock
        - Safe for concurrent asyncio tasks
    """

    def __init__(self, max_size: int = 100) -> None:
        """Initialize cache with bounded size.

        Args:
            max_size: Maximum number of cache entries (LRU eviction after)
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size: int = max_size
        self._lock: asyncio.Lock = asyncio.Lock()

    async def get(self, working_directory: str) -> Optional[Tuple[Dict[str, Any], Path]]:
        """Get config and config_path from cache with mtime validation.

        Performs mtime-based validation to detect config file changes.
        Automatically invalidates cache if:
        - File modification time changed
        - File deleted or inaccessible

        Args:
            working_directory: Working directory path (cache key)

        Returns:
            Tuple of (config dict, config_path) or None if cache miss/invalidated.
            Returning both values eliminates redundant filesystem searches.
        """
        async with self._lock:
            entry: Optional[CacheEntry] = self._cache.get(working_directory)
            if entry is None:
                logger.debug(f"Cache miss: {working_directory}")
                return None

            # Check if file still exists and mtime matches
            try:
                current_mtime_ns: int = entry.config_path.stat().st_mtime_ns
                if current_mtime_ns != entry.mtime_ns:
                    # File modified, invalidate cache
                    logger.debug(
                        f"Cache invalidated (mtime changed): {working_directory} "
                        f"(cached: {entry.mtime_ns}, current: {current_mtime_ns})"
                    )
                    del self._cache[working_directory]
                    return None
            except (OSError, FileNotFoundError) as e:
                # File deleted or inaccessible, invalidate cache
                logger.debug(
                    f"Cache invalidated (file error): {working_directory}, error: {e}"
                )
                del self._cache[working_directory]
                return None

            # Cache hit! Update access time for LRU
            entry.access_time = time.time()
            logger.debug(f"Cache hit: {working_directory}")
            return (entry.config, entry.config_path)

    async def set(
        self,
        working_directory: str,
        config: Dict[str, Any],
        config_path: Path,
    ) -> None:
        """Store config in cache with current mtime.

        Implements LRU eviction policy:
        - If cache at capacity, evict entry with oldest access_time
        - Capture mtime at cache time for invalidation detection

        Args:
            working_directory: Working directory path (cache key)
            config: Parsed config dictionary
            config_path: Path to config file (for mtime tracking)
        """
        async with self._lock:
            # Evict oldest entry if at capacity (LRU)
            if len(self._cache) >= self._max_size:
                oldest_key: str = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k].access_time,
                )
                del self._cache[oldest_key]
                logger.debug(f"Cache evicted (LRU): {oldest_key}")

            # Capture mtime at cache time
            try:
                mtime_ns: int = config_path.stat().st_mtime_ns
            except (OSError, FileNotFoundError) as e:
                logger.warning(f"Cannot stat config file {config_path}: {e}")
                return  # Don't cache if we can't get mtime

            self._cache[working_directory] = CacheEntry(
                config=config,
                config_path=config_path,
                mtime_ns=mtime_ns,
                access_time=time.time(),
            )
            logger.debug(f"Cache set: {working_directory} (mtime: {mtime_ns})")

    async def clear(self) -> None:
        """Clear all cache entries.

        Use for testing or when global cache invalidation needed.
        """
        async with self._lock:
            count: int = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache cleared: {count} entries removed")

    async def get_size(self) -> int:
        """Get current cache size (for monitoring).

        Returns:
            Number of entries currently in cache
        """
        async with self._lock:
            return len(self._cache)


# Global singleton
_config_cache: Optional[ConfigCache] = None


def get_config_cache() -> ConfigCache:
    """Get global config cache instance.

    Thread-safe singleton pattern for module-level cache.

    Returns:
        Global ConfigCache instance (created on first access)
    """
    global _config_cache
    if _config_cache is None:
        _config_cache = ConfigCache(max_size=100)
    return _config_cache
