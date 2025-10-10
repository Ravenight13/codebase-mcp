"""Example usage of SQLite cache service for offline fallback.

Demonstrates:
- Async context manager initialization
- Vendor extractor caching and retrieval
- Work item caching and retrieval
- TTL staleness detection
- Batch cleanup of expired entries
- Cache statistics monitoring

Run with: python examples/cache_usage.py
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.services.cache import SQLiteCache


async def main() -> None:
    """Demonstrate SQLite cache operations."""
    print("=" * 60)
    print("SQLite Cache Usage Example")
    print("=" * 60)

    # Create cache with custom path
    cache_path = Path("cache/example_cache.db")
    cache = SQLiteCache(db_path=cache_path)

    async with cache:
        print(f"\n✓ Cache initialized at: {cache_path}")

        # Example 1: Cache a vendor extractor
        print("\n1. Caching vendor extractor...")
        vendor_data = {
            "id": str(uuid4()),
            "name": "vendor_xyz",
            "status": "operational",
            "version": 1,
            "extractor_version": "2.5.0",
            "metadata_": {
                "format_support": {"excel": True, "csv": True, "pdf": True, "ocr": False},
                "test_results": {"passing": 48, "total": 50, "skipped": 2},
                "extractor_version": "2.5.0",
                "manifest_compliant": True,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "created_by": "example-client",
        }
        await cache.set_vendor("vendor_xyz", vendor_data)
        print(f"   ✓ Cached vendor: {vendor_data['name']}")

        # Example 2: Retrieve cached vendor
        print("\n2. Retrieving cached vendor...")
        cached_vendor = await cache.get_vendor("vendor_xyz")
        if cached_vendor:
            print(f"   ✓ Found vendor: {cached_vendor['name']}")
            print(f"   - Status: {cached_vendor['status']}")
            print(f"   - Version: {cached_vendor['extractor_version']}")
            print(f"   - Tests: {cached_vendor['metadata_']['test_results']['passing']}/{cached_vendor['metadata_']['test_results']['total']} passing")

        # Example 3: Cache a work item
        print("\n3. Caching work item...")
        work_item_id = uuid4()
        work_item_data = {
            "id": str(work_item_id),
            "version": 1,
            "title": "Implement feature X",
            "description": "Add new feature with tests",
            "notes": "Priority: High",
            "item_type": "task",
            "status": "active",
            "parent_id": None,
            "path": "/",
            "depth": 0,
            "branch_name": "feature-x",
            "commit_hash": "a" * 40,
            "pr_number": 456,
            "metadata_": {
                "estimated_hours": 4.0,
                "actual_hours": None,
                "blocked_reason": None,
            },
            "deleted_at": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "created_by": "example-client",
        }
        await cache.set_work_item(work_item_id, work_item_data)
        print(f"   ✓ Cached work item: {work_item_data['title']}")

        # Example 4: Retrieve cached work item
        print("\n4. Retrieving cached work item...")
        cached_item = await cache.get_work_item(work_item_id)
        if cached_item:
            print(f"   ✓ Found work item: {cached_item['title']}")
            print(f"   - Type: {cached_item['item_type']}")
            print(f"   - Status: {cached_item['status']}")
            print(f"   - Branch: {cached_item['branch_name']}")

        # Example 5: Check staleness
        print("\n5. Checking entry staleness...")
        is_stale_vendor = await cache.is_stale(f"vendor:vendor_xyz")
        is_stale_item = await cache.is_stale(f"work_item:{work_item_id}")
        print(f"   - Vendor stale: {is_stale_vendor} (fresh entries)")
        print(f"   - Work item stale: {is_stale_item} (fresh entries)")

        # Example 6: Get cache statistics
        print("\n6. Cache statistics...")
        stats = await cache.get_stats()
        print(f"   - Total entries: {stats.total_entries}")
        print(f"   - Vendors cached: {stats.vendors_cached}")
        print(f"   - Work items cached: {stats.work_items_cached}")
        print(f"   - Stale entries: {stats.stale_entries}")
        print(f"   - Oldest entry age: {stats.oldest_entry_age_seconds:.2f}s")

        # Example 7: Clear stale entries (none expected)
        print("\n7. Clearing stale entries...")
        removed_count = await cache.clear_stale()
        print(f"   ✓ Removed {removed_count} stale entries")

        # Example 8: Update existing vendor
        print("\n8. Updating cached vendor...")
        vendor_data["status"] = "broken"
        vendor_data["version"] = 2
        await cache.set_vendor("vendor_xyz", vendor_data)
        updated_vendor = await cache.get_vendor("vendor_xyz")
        if updated_vendor:
            print(f"   ✓ Updated vendor status: {updated_vendor['status']}")
            print(f"   ✓ Updated version: {updated_vendor['version']}")

        # Example 9: Cache not found
        print("\n9. Handling cache miss...")
        missing_vendor = await cache.get_vendor("nonexistent_vendor")
        if missing_vendor is None:
            print("   ✓ Correctly returned None for missing vendor")

        # Example 10: Clear all cache
        print("\n10. Clearing all cache entries...")
        final_stats = await cache.get_stats()
        print(f"   - Entries before clear: {final_stats.total_entries}")
        cleared_count = await cache.clear_all()
        print(f"   ✓ Cleared {cleared_count} entries")

        after_clear_stats = await cache.get_stats()
        print(f"   - Entries after clear: {after_clear_stats.total_entries}")

    print("\n" + "=" * 60)
    print("Cache example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
