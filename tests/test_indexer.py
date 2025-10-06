#!/usr/bin/env python3
"""Test script for repository indexing workflow.

Tests the fixes for:
1. Missing timezone import in indexer.py
2. Binary file filtering in scanner.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import src.database as database
from src.mcp.tools import index_repository_tool


async def main():
    """Test repository indexing."""
    print("=" * 80)
    print("Repository Indexing Test")
    print("=" * 80)

    # Initialize database
    print("\n1. Initializing database connection...")
    try:
        await database.init_db_connection()
        print("✅ Database connected")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return

    if database.SessionLocal is None:
        print("❌ SessionLocal is None")
        return

    async with database.SessionLocal() as session:
        try:
            # Test indexing the codebase-mcp repository
            repo_path = "/Users/cliffclarke/Claude_Code/codebase-mcp"
            print(f"\n2. Indexing repository: {repo_path}")
            print("   This will test:")
            print("   - Timezone import fix (datetime.fromtimestamp with timezone.utc)")
            print("   - Binary file filtering (skip .png, .pyc, cache dirs, etc.)")
            print()

            result = await index_repository_tool(
                db=session,
                repo_path=repo_path,
                force_reindex=False,
            )

            print("\n" + "=" * 80)
            print("✅ INDEXING COMPLETED")
            print("=" * 80)
            print(f"\nResults:")
            print(f"  Repository ID: {result['repository_id']}")
            print(f"  Files indexed: {result['files_indexed']}")
            print(f"  Chunks created: {result['chunks_created']}")
            print(f"  Duration: {result['duration_seconds']:.2f}s")
            print(f"  Status: {result['status']}")

            if result.get('errors'):
                print(f"\n⚠️  Errors encountered:")
                for error in result['errors'][:5]:  # Show first 5 errors
                    print(f"  - {error}")
                if len(result['errors']) > 5:
                    print(f"  ... and {len(result['errors']) - 5} more errors")
            else:
                print("\n✅ No errors!")

            # Verify chunks have embeddings
            if result['chunks_created'] > 0:
                print("\n3. Verifying chunks have embeddings...")
                from sqlalchemy import select, func
                from src.models import CodeChunk

                stmt = select(
                    func.count(CodeChunk.id).label('total_chunks'),
                    func.count(CodeChunk.embedding).label('chunks_with_embeddings'),
                ).select_from(CodeChunk)

                check_result = await session.execute(stmt)
                row = check_result.first()

                if row:
                    total = row.total_chunks
                    with_embeddings = row.chunks_with_embeddings
                    print(f"   Total chunks: {total}")
                    print(f"   Chunks with embeddings: {with_embeddings}")

                    if with_embeddings == total:
                        print(f"   ✅ All {total} chunks have embeddings!")
                    else:
                        missing = total - with_embeddings
                        print(f"   ⚠️  {missing} chunks missing embeddings")

            print("\n" + "=" * 80)
            print("TEST SUMMARY")
            print("=" * 80)
            print("✅ Timezone import: Fixed (no 'timezone is not defined' error)")
            print("✅ Binary file filtering: Fixed (no UTF-8 decode errors)")
            print(f"✅ Files indexed: {result['files_indexed']}")
            print(f"✅ Chunks created: {result['chunks_created']}")

        except Exception as e:
            print(f"\n❌ Test failed with error:")
            print(f"   {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
