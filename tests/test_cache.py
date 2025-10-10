"""Tests for SQLite cache service with 30-minute TTL.

Validates:
- Async context manager initialization and cleanup
- Vendor extractor caching with TTL enforcement
- Work item caching with TTL enforcement
- Staleness detection for cache entries
- Batch cleanup of stale entries
- Cache statistics calculation
- Error handling and edge cases

Constitutional Compliance:
- Principle VII: Test-driven development (comprehensive test coverage)
- Principle VIII: Type safety (mypy --strict compliance)

Test Strategy:
- Unit tests for individual cache operations
- Integration tests for TTL enforcement and cleanup
- Edge case handling (connection errors, invalid keys, empty cache)
- Performance validation (cache operations complete within targets)
"""

from __future__ import annotations

import asyncio
import json
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.services.cache import (
    STALENESS_THRESHOLD_SECONDS,
    SQLiteCache,
    CacheStats,
)


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
async def temp_cache_path() -> Path:
    """Create temporary database path for isolated testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir) / "test_cache.db"
        yield cache_path


@pytest.fixture
async def cache(temp_cache_path: Path) -> SQLiteCache:
    """Create and initialize SQLite cache instance."""
    cache_instance = SQLiteCache(db_path=temp_cache_path)
    async with cache_instance:
        yield cache_instance


@pytest.fixture
def sample_vendor_data() -> dict:
    """Sample vendor extractor data for testing."""
    return {
        "id": str(uuid4()),
        "name": "vendor_abc",
        "status": "operational",
        "version": 1,
        "extractor_version": "2.3.1",
        "metadata_": {
            "format_support": {"excel": True, "csv": True, "pdf": False, "ocr": False},
            "test_results": {"passing": 45, "total": 50, "skipped": 5},
            "extractor_version": "2.3.1",
            "manifest_compliant": True,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "created_by": "test-client",
    }


@pytest.fixture
def sample_work_item_data() -> dict:
    """Sample work item data for testing."""
    return {
        "id": str(uuid4()),
        "version": 1,
        "title": "Test work item",
        "description": "Test description",
        "notes": "Test notes",
        "item_type": "task",
        "status": "active",
        "parent_id": None,
        "path": "/",
        "depth": 0,
        "branch_name": "003-test-branch",
        "commit_hash": "a" * 40,
        "pr_number": 123,
        "metadata_": {
            "estimated_hours": 2.5,
            "actual_hours": None,
            "blocked_reason": None,
        },
        "deleted_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "created_by": "test-client",
    }


# ==============================================================================
# Context Manager Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_cache_context_manager_initialization(temp_cache_path: Path) -> None:
    """Test async context manager initialization creates schema."""
    cache = SQLiteCache(db_path=temp_cache_path)

    assert not cache._initialized

    async with cache:
        assert cache._initialized
        assert cache._conn is not None
        assert temp_cache_path.exists()

    # Connection should be closed after context exit
    assert cache._conn is None


@pytest.mark.asyncio
async def test_cache_double_initialization_idempotent(temp_cache_path: Path) -> None:
    """Test schema initialization is idempotent (safe to call multiple times)."""
    cache = SQLiteCache(db_path=temp_cache_path)

    async with cache:
        # Initialize again (should be no-op)
        await cache._initialize_schema()
        assert cache._initialized


# ==============================================================================
# Vendor Cache Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_set_and_get_vendor(cache: SQLiteCache, sample_vendor_data: dict) -> None:
    """Test caching and retrieving vendor extractor data."""
    vendor_name = sample_vendor_data["name"]

    # Cache vendor
    await cache.set_vendor(vendor_name, sample_vendor_data)

    # Retrieve vendor
    cached_vendor = await cache.get_vendor(vendor_name)

    assert cached_vendor is not None
    assert cached_vendor["name"] == vendor_name
    assert cached_vendor["status"] == "operational"
    assert cached_vendor["metadata_"]["test_results"]["passing"] == 45


@pytest.mark.asyncio
async def test_get_vendor_not_found(cache: SQLiteCache) -> None:
    """Test retrieving non-existent vendor returns None."""
    result = await cache.get_vendor("nonexistent_vendor")
    assert result is None


@pytest.mark.asyncio
async def test_vendor_cache_overwrite(cache: SQLiteCache, sample_vendor_data: dict) -> None:
    """Test updating cached vendor data overwrites previous entry."""
    vendor_name = sample_vendor_data["name"]

    # Cache initial data
    await cache.set_vendor(vendor_name, sample_vendor_data)

    # Update vendor data
    updated_data = sample_vendor_data.copy()
    updated_data["status"] = "broken"
    updated_data["version"] = 2

    await cache.set_vendor(vendor_name, updated_data)

    # Retrieve updated data
    cached_vendor = await cache.get_vendor(vendor_name)

    assert cached_vendor is not None
    assert cached_vendor["status"] == "broken"
    assert cached_vendor["version"] == 2


# ==============================================================================
# Work Item Cache Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_set_and_get_work_item(
    cache: SQLiteCache, sample_work_item_data: dict
) -> None:
    """Test caching and retrieving work item data."""
    item_id = uuid4()
    sample_work_item_data["id"] = str(item_id)

    # Cache work item
    await cache.set_work_item(item_id, sample_work_item_data)

    # Retrieve work item
    cached_item = await cache.get_work_item(item_id)

    assert cached_item is not None
    assert cached_item["id"] == str(item_id)
    assert cached_item["title"] == "Test work item"
    assert cached_item["item_type"] == "task"


@pytest.mark.asyncio
async def test_get_work_item_not_found(cache: SQLiteCache) -> None:
    """Test retrieving non-existent work item returns None."""
    result = await cache.get_work_item(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_work_item_cache_overwrite(
    cache: SQLiteCache, sample_work_item_data: dict
) -> None:
    """Test updating cached work item data overwrites previous entry."""
    item_id = uuid4()
    sample_work_item_data["id"] = str(item_id)

    # Cache initial data
    await cache.set_work_item(item_id, sample_work_item_data)

    # Update work item data
    updated_data = sample_work_item_data.copy()
    updated_data["status"] = "completed"
    updated_data["version"] = 2

    await cache.set_work_item(item_id, updated_data)

    # Retrieve updated data
    cached_item = await cache.get_work_item(item_id)

    assert cached_item is not None
    assert cached_item["status"] == "completed"
    assert cached_item["version"] == 2


# ==============================================================================
# TTL and Staleness Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_vendor_staleness_detection(
    cache: SQLiteCache, sample_vendor_data: dict
) -> None:
    """Test vendor cache entry staleness detection after TTL expiration."""
    vendor_name = sample_vendor_data["name"]

    # Cache vendor
    await cache.set_vendor(vendor_name, sample_vendor_data)

    # Fresh entry should not be stale
    is_stale = await cache.is_stale(f"vendor:{vendor_name}")
    assert not is_stale

    # Manually expire entry by manipulating cached_at timestamp
    async with cache._conn.execute(
        "UPDATE cached_vendors SET cached_at = cached_at - ? WHERE name = ?",
        (STALENESS_THRESHOLD_SECONDS + 1, vendor_name),
    ):
        pass
    await cache._conn.commit()

    # Expired entry should be stale
    is_stale = await cache.is_stale(f"vendor:{vendor_name}")
    assert is_stale


@pytest.mark.asyncio
async def test_work_item_staleness_detection(
    cache: SQLiteCache, sample_work_item_data: dict
) -> None:
    """Test work item cache entry staleness detection after TTL expiration."""
    item_id = uuid4()
    sample_work_item_data["id"] = str(item_id)

    # Cache work item
    await cache.set_work_item(item_id, sample_work_item_data)

    # Fresh entry should not be stale
    is_stale = await cache.is_stale(f"work_item:{item_id}")
    assert not is_stale

    # Manually expire entry
    async with cache._conn.execute(
        "UPDATE cached_work_items SET cached_at = cached_at - ? WHERE id = ?",
        (STALENESS_THRESHOLD_SECONDS + 1, str(item_id)),
    ):
        pass
    await cache._conn.commit()

    # Expired entry should be stale
    is_stale = await cache.is_stale(f"work_item:{item_id}")
    assert is_stale


@pytest.mark.asyncio
async def test_get_stale_vendor_returns_none(
    cache: SQLiteCache, sample_vendor_data: dict
) -> None:
    """Test retrieving stale vendor cache entry returns None."""
    vendor_name = sample_vendor_data["name"]

    # Cache vendor
    await cache.set_vendor(vendor_name, sample_vendor_data)

    # Manually expire entry
    async with cache._conn.execute(
        "UPDATE cached_vendors SET cached_at = cached_at - ? WHERE name = ?",
        (STALENESS_THRESHOLD_SECONDS + 1, vendor_name),
    ):
        pass
    await cache._conn.commit()

    # Stale entry should return None
    cached_vendor = await cache.get_vendor(vendor_name)
    assert cached_vendor is None


@pytest.mark.asyncio
async def test_get_stale_work_item_returns_none(
    cache: SQLiteCache, sample_work_item_data: dict
) -> None:
    """Test retrieving stale work item cache entry returns None."""
    item_id = uuid4()
    sample_work_item_data["id"] = str(item_id)

    # Cache work item
    await cache.set_work_item(item_id, sample_work_item_data)

    # Manually expire entry
    async with cache._conn.execute(
        "UPDATE cached_work_items SET cached_at = cached_at - ? WHERE id = ?",
        (STALENESS_THRESHOLD_SECONDS + 1, str(item_id)),
    ):
        pass
    await cache._conn.commit()

    # Stale entry should return None
    cached_item = await cache.get_work_item(item_id)
    assert cached_item is None


# ==============================================================================
# Stale Entry Cleanup Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_clear_stale_removes_expired_entries(
    cache: SQLiteCache, sample_vendor_data: dict, sample_work_item_data: dict
) -> None:
    """Test clear_stale() removes only expired entries."""
    # Cache vendor and work item
    vendor_name = sample_vendor_data["name"]
    await cache.set_vendor(vendor_name, sample_vendor_data)

    item_id = uuid4()
    sample_work_item_data["id"] = str(item_id)
    await cache.set_work_item(item_id, sample_work_item_data)

    # Cache additional fresh vendor
    fresh_vendor_data = sample_vendor_data.copy()
    fresh_vendor_data["name"] = "fresh_vendor"
    await cache.set_vendor("fresh_vendor", fresh_vendor_data)

    # Expire first two entries
    async with cache._conn.execute(
        "UPDATE cached_vendors SET cached_at = cached_at - ? WHERE name = ?",
        (STALENESS_THRESHOLD_SECONDS + 1, vendor_name),
    ):
        pass
    async with cache._conn.execute(
        "UPDATE cached_work_items SET cached_at = cached_at - ? WHERE id = ?",
        (STALENESS_THRESHOLD_SECONDS + 1, str(item_id)),
    ):
        pass
    await cache._conn.commit()

    # Clear stale entries
    removed_count = await cache.clear_stale()

    # Should remove exactly 2 stale entries
    assert removed_count == 2

    # Fresh vendor should still exist
    fresh_vendor = await cache.get_vendor("fresh_vendor")
    assert fresh_vendor is not None
    assert fresh_vendor["name"] == "fresh_vendor"

    # Stale vendor should be removed
    stale_vendor = await cache.get_vendor(vendor_name)
    assert stale_vendor is None


@pytest.mark.asyncio
async def test_clear_stale_empty_cache(cache: SQLiteCache) -> None:
    """Test clear_stale() on empty cache returns 0."""
    removed_count = await cache.clear_stale()
    assert removed_count == 0


# ==============================================================================
# Cache Statistics Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_get_stats_empty_cache(cache: SQLiteCache) -> None:
    """Test get_stats() on empty cache returns zero counts."""
    stats = await cache.get_stats()

    assert stats.total_entries == 0
    assert stats.stale_entries == 0
    assert stats.vendors_cached == 0
    assert stats.work_items_cached == 0
    assert stats.oldest_entry_age_seconds == 0.0


@pytest.mark.asyncio
async def test_get_stats_with_entries(
    cache: SQLiteCache, sample_vendor_data: dict, sample_work_item_data: dict
) -> None:
    """Test get_stats() calculates correct counts and ages."""
    # Cache 2 vendors
    await cache.set_vendor("vendor1", sample_vendor_data)
    vendor2_data = sample_vendor_data.copy()
    vendor2_data["name"] = "vendor2"
    await cache.set_vendor("vendor2", vendor2_data)

    # Cache 1 work item
    item_id = uuid4()
    sample_work_item_data["id"] = str(item_id)
    await cache.set_work_item(item_id, sample_work_item_data)

    # Expire one vendor
    async with cache._conn.execute(
        "UPDATE cached_vendors SET cached_at = cached_at - ? WHERE name = ?",
        (STALENESS_THRESHOLD_SECONDS + 1, "vendor1"),
    ):
        pass
    await cache._conn.commit()

    stats = await cache.get_stats()

    assert stats.total_entries == 3
    assert stats.stale_entries == 1
    assert stats.vendors_cached == 2
    assert stats.work_items_cached == 1
    assert stats.oldest_entry_age_seconds > STALENESS_THRESHOLD_SECONDS


# ==============================================================================
# Clear All Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_clear_all_removes_all_entries(
    cache: SQLiteCache, sample_vendor_data: dict, sample_work_item_data: dict
) -> None:
    """Test clear_all() removes all cache entries."""
    # Cache vendor and work item
    await cache.set_vendor("vendor1", sample_vendor_data)

    item_id = uuid4()
    sample_work_item_data["id"] = str(item_id)
    await cache.set_work_item(item_id, sample_work_item_data)

    # Clear all
    removed_count = await cache.clear_all()
    assert removed_count == 2

    # Verify cache is empty
    stats = await cache.get_stats()
    assert stats.total_entries == 0


# ==============================================================================
# Error Handling Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_operations_without_context_manager_raise_error(
    temp_cache_path: Path,
) -> None:
    """Test cache operations without context manager raise RuntimeError."""
    cache = SQLiteCache(db_path=temp_cache_path)

    with pytest.raises(RuntimeError, match="Cache not connected"):
        await cache.get_vendor("test")

    with pytest.raises(RuntimeError, match="Cache not connected"):
        await cache.set_vendor("test", {})

    with pytest.raises(RuntimeError, match="Cache not connected"):
        await cache.clear_stale()


@pytest.mark.asyncio
async def test_invalid_cache_key_format_raises_error(cache: SQLiteCache) -> None:
    """Test is_stale() with invalid cache key format raises ValueError."""
    with pytest.raises(ValueError, match="Invalid cache_key format"):
        await cache.is_stale("invalid_key_without_colon")


@pytest.mark.asyncio
async def test_unknown_table_prefix_raises_error(cache: SQLiteCache) -> None:
    """Test is_stale() with unknown table prefix raises ValueError."""
    with pytest.raises(ValueError, match="Unknown table prefix"):
        await cache.is_stale("unknown_prefix:key")


@pytest.mark.asyncio
async def test_staleness_check_for_nonexistent_entry(cache: SQLiteCache) -> None:
    """Test is_stale() for non-existent entry returns True."""
    is_stale = await cache.is_stale("vendor:nonexistent")
    assert is_stale


# ==============================================================================
# JSON Serialization Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_vendor_json_serialization_with_uuid(
    cache: SQLiteCache, sample_vendor_data: dict
) -> None:
    """Test vendor cache handles UUID serialization correctly."""
    vendor_name = sample_vendor_data["name"]
    vendor_uuid = uuid4()
    sample_vendor_data["id"] = vendor_uuid  # Use UUID object

    await cache.set_vendor(vendor_name, sample_vendor_data)

    cached_vendor = await cache.get_vendor(vendor_name)
    assert cached_vendor is not None
    # UUID should be serialized as string
    assert isinstance(cached_vendor["id"], str)


@pytest.mark.asyncio
async def test_work_item_json_serialization_with_datetime(
    cache: SQLiteCache, sample_work_item_data: dict
) -> None:
    """Test work item cache handles datetime serialization correctly."""
    item_id = uuid4()
    sample_work_item_data["id"] = str(item_id)

    # Use datetime object instead of ISO string
    sample_work_item_data["created_at"] = datetime.now(timezone.utc)

    await cache.set_work_item(item_id, sample_work_item_data)

    cached_item = await cache.get_work_item(item_id)
    assert cached_item is not None
    # Datetime should be serialized as string
    assert isinstance(cached_item["created_at"], str)


# ==============================================================================
# Performance Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_cache_lookup_performance(
    cache: SQLiteCache, sample_vendor_data: dict
) -> None:
    """Test cache lookups complete within performance target (<1ms)."""
    vendor_name = sample_vendor_data["name"]
    await cache.set_vendor(vendor_name, sample_vendor_data)

    # Measure lookup time
    start_time = time.perf_counter()
    await cache.get_vendor(vendor_name)
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # Should be well under 1ms for indexed lookup
    assert elapsed_ms < 1.0


@pytest.mark.asyncio
async def test_batch_cleanup_performance(
    cache: SQLiteCache, sample_vendor_data: dict
) -> None:
    """Test batch cleanup completes within performance target (<100ms)."""
    # Cache 50 vendors
    for i in range(50):
        vendor_data = sample_vendor_data.copy()
        vendor_data["name"] = f"vendor_{i}"
        await cache.set_vendor(f"vendor_{i}", vendor_data)

    # Expire all entries
    async with cache._conn.execute(
        f"UPDATE cached_vendors SET cached_at = cached_at - {STALENESS_THRESHOLD_SECONDS + 1}"
    ):
        pass
    await cache._conn.commit()

    # Measure cleanup time
    start_time = time.perf_counter()
    await cache.clear_stale()
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # Should complete within 100ms
    assert elapsed_ms < 100.0
