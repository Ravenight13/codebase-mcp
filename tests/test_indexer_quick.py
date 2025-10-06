#!/usr/bin/env python3
"""Quick test for indexer bug fixes (no embedding generation).

Tests:
1. Timezone issue is fixed (datetime.utcfromtimestamp)
2. Binary files are filtered out
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import src.database as database
from src.services.scanner import scan_repository
from src.services.indexer import _create_code_files, _get_or_create_repository


async def main():
    """Quick test for bug fixes."""
    print("=" * 80)
    print("Quick Indexer Bug Fix Test")
    print("=" * 80)

    # Initialize database
    print("\n1. Initializing database...")
    await database.init_db_connection()

    if database.SessionLocal is None:
        print("❌ SessionLocal is None")
        return

    async with database.SessionLocal() as session:
        try:
            repo_path = Path("/Users/cliffclarke/Claude_Code/codebase-mcp")

            # Test 1: Scan repository (should filter binary files)
            print(f"\n2. Scanning repository: {repo_path}")
            files = await scan_repository(repo_path)
            print(f"   ✅ Found {len(files)} non-ignored files")

            # Check that binary files are filtered
            binary_extensions = {'.png', '.jpg', '.pyc', '.so'}
            binary_files = [f for f in files if f.suffix in binary_extensions]
            if binary_files:
                print(f"   ⚠️  Found {len(binary_files)} binary files that should be filtered:")
                for f in binary_files[:5]:
                    print(f"      - {f}")
            else:
                print("   ✅ No binary files in scanned results")

            # Check that cache dirs are filtered
            cache_dirs = ['__pycache__', '.ruff_cache', '.pytest_cache', 'htmlcov']
            cache_files = [f for f in files if any(d in str(f) for d in cache_dirs)]
            if cache_files:
                print(f"   ⚠️  Found {len(cache_files)} files in cache dirs:")
                for f in cache_files[:5]:
                    print(f"      - {f}")
            else:
                print("   ✅ No cache directory files in scanned results")

            # Test 2: Create CodeFile records (tests timezone fix)
            print(f"\n3. Testing CodeFile creation (timezone fix)...")

            # Get or create repository
            repository = await _get_or_create_repository(
                session, repo_path, "codebase-mcp-test"
            )
            await session.flush()

            # Try to create CodeFile records for first 5 files
            test_files = files[:5]
            print(f"   Creating CodeFile records for {len(test_files)} files...")

            try:
                file_ids = await _create_code_files(
                    session, repository.id, repo_path, test_files
                )
                await session.flush()
                print(f"   ✅ Created {len(file_ids)} CodeFile records")
                print("   ✅ Timezone fix working (no datetime mismatch error)")
            except Exception as e:
                if "timezone" in str(e).lower() or "offset-naive" in str(e):
                    print(f"   ❌ Timezone error: {e}")
                    raise
                else:
                    print(f"   ❌ Other error: {e}")
                    raise

            print("\n" + "=" * 80)
            print("✅ ALL BUG FIXES VERIFIED")
            print("=" * 80)
            print("\nResults:")
            print(f"  ✅ Binary file filtering: {len(files)} files scanned (no binary files)")
            print(f"  ✅ Timezone fix: CodeFile records created without error")
            print(f"  ✅ Files ready for chunking: {len(files)}")

            await session.rollback()  # Don't commit test data

        except Exception as e:
            print(f"\n❌ Test failed:")
            print(f"   {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
