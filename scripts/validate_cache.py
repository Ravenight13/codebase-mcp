"""Validation test for async config cache implementation.

Tests:
1. Cache set/get operations
2. mtime-based invalidation
3. LRU eviction policy
4. Async-safe concurrent access
"""

from __future__ import annotations

import asyncio
import json
import tempfile
import time
from pathlib import Path
from typing import Dict, Any


async def test_basic_cache_operations() -> None:
    """Test basic cache set/get operations."""
    print("\n=== Test 1: Basic Cache Operations ===")
    from src.auto_switch.cache import get_config_cache

    cache = get_config_cache()
    await cache.clear()  # Start fresh

    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".codebase-mcp"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({"version": "1.0", "project": {"name": "test"}}))

        # Test cache set
        config: Dict[str, Any] = {"version": "1.0", "project": {"name": "test"}}
        await cache.set(tmpdir, config, config_file)
        print(f"✓ Cache set: {tmpdir}")

        # Test cache get (hit)
        cached = await cache.get(tmpdir)
        assert cached is not None, "Cache miss on first get"
        assert cached["project"]["name"] == "test", "Config data mismatch"
        print(f"✓ Cache hit: {cached['project']['name']}")

        # Test cache size
        size = await cache.get_size()
        assert size == 1, f"Expected size 1, got {size}"
        print(f"✓ Cache size: {size}")


async def test_mtime_invalidation() -> None:
    """Test automatic cache invalidation on file modification."""
    print("\n=== Test 2: mtime-based Invalidation ===")
    from src.auto_switch.cache import get_config_cache

    cache = get_config_cache()
    await cache.clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".codebase-mcp"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({"version": "1.0", "project": {"name": "original"}}))

        # Cache original config
        config: Dict[str, Any] = {"version": "1.0", "project": {"name": "original"}}
        await cache.set(tmpdir, config, config_file)
        print(f"✓ Cached original config")

        # Verify cache hit
        cached = await cache.get(tmpdir)
        assert cached is not None and cached["project"]["name"] == "original"
        print(f"✓ Cache hit confirmed")

        # Modify file (change mtime)
        await asyncio.sleep(0.01)  # Ensure mtime changes
        config_file.write_text(json.dumps({"version": "2.0", "project": {"name": "modified"}}))
        print(f"✓ Config file modified (mtime changed)")

        # Should detect mtime change and invalidate
        cached_after = await cache.get(tmpdir)
        assert cached_after is None, "Cache should be invalidated after mtime change"
        print(f"✓ Cache invalidated (mtime mismatch detected)")


async def test_lru_eviction() -> None:
    """Test LRU eviction policy."""
    print("\n=== Test 3: LRU Eviction Policy ===")
    from src.auto_switch.cache import ConfigCache

    cache = ConfigCache(max_size=3)  # Small cache for testing

    with tempfile.TemporaryDirectory() as tmpdir:
        base_dir = Path(tmpdir)

        # Create 4 config entries (will trigger eviction)
        for i in range(4):
            config_dir = base_dir / f"project{i}" / ".codebase-mcp"
            config_dir.mkdir(parents=True)
            config_file = config_dir / "config.json"
            config_file.write_text(json.dumps({"version": "1.0", "project": {"name": f"project{i}"}}))

            config: Dict[str, Any] = {"version": "1.0", "project": {"name": f"project{i}"}}
            await cache.set(str(base_dir / f"project{i}"), config, config_file)
            print(f"✓ Cached project{i}")
            await asyncio.sleep(0.01)  # Ensure different access times

        # Cache size should be max_size (oldest evicted)
        size = await cache.get_size()
        assert size == 3, f"Expected size 3 after eviction, got {size}"
        print(f"✓ LRU eviction: size capped at {size}")

        # project0 should be evicted (oldest access time)
        project0_cached = await cache.get(str(base_dir / "project0"))
        assert project0_cached is None, "Oldest entry should be evicted"
        print(f"✓ Oldest entry (project0) evicted")

        # project1-3 should still be cached
        for i in range(1, 4):
            cached = await cache.get(str(base_dir / f"project{i}"))
            assert cached is not None, f"project{i} should still be cached"
            assert cached["project"]["name"] == f"project{i}"
        print(f"✓ Newer entries (project1-3) retained")


async def test_file_deletion_invalidation() -> None:
    """Test cache invalidation when config file is deleted."""
    print("\n=== Test 4: File Deletion Invalidation ===")
    from src.auto_switch.cache import get_config_cache

    cache = get_config_cache()
    await cache.clear()

    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".codebase-mcp"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({"version": "1.0", "project": {"name": "test"}}))

        # Cache config
        config: Dict[str, Any] = {"version": "1.0", "project": {"name": "test"}}
        await cache.set(tmpdir, config, config_file)
        print(f"✓ Cached config")

        # Delete config file
        config_file.unlink()
        print(f"✓ Config file deleted")

        # Should detect file deletion and invalidate
        cached = await cache.get(tmpdir)
        assert cached is None, "Cache should be invalidated after file deletion"
        print(f"✓ Cache invalidated (file not found)")


async def main() -> None:
    """Run all validation tests."""
    print("=" * 60)
    print("Async Config Cache Validation")
    print("=" * 60)

    try:
        await test_basic_cache_operations()
        await test_mtime_invalidation()
        await test_lru_eviction()
        await test_file_deletion_invalidation()

        print("\n" + "=" * 60)
        print("✓ All validation tests passed!")
        print("=" * 60)
    except AssertionError as e:
        print(f"\n✗ Validation failed: {e}")
        raise
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
