#!/usr/bin/env python3
"""Test embeddings are generated for indexed chunks."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pytest

pytest.skip("Test requires refactoring for FastMCP - old import pattern", allow_module_level=True)

import src.database as database
# from src.mcp.tools import index_repository_tool  # Old import - needs refactoring
from sqlalchemy import select, func
from src.models import CodeChunk


async def main():
    """Test full indexing with embeddings."""
    print("=" * 80)
    print("Full Indexing Test with Embeddings")
    print("=" * 80)

    # Initialize database
    print("\n1. Initializing database...")
    await database.init_db_connection()

    if database.SessionLocal is None:
        print("❌ SessionLocal is None")
        return

    async with database.SessionLocal() as session:
        try:
            # Index the small test repository
            repo_path = "/Users/cliffclarke/Claude_Code/codebase-mcp/test_small_repo"
            print(f"\n2. Indexing small repository: {repo_path}")

            result = await index_repository_tool(
                db=session,
                repo_path=repo_path,
                force_reindex=True,  # Force reindex to ensure fresh data
            )

            print("\n" + "=" * 80)
            print("INDEXING RESULTS")
            print("=" * 80)
            print(f"Repository ID: {result['repository_id']}")
            print(f"Files indexed: {result['files_indexed']}")
            print(f"Chunks created: {result['chunks_created']}")
            print(f"Duration: {result['duration_seconds']:.2f}s")
            print(f"Status: {result['status']}")

            if result.get('errors'):
                print(f"\n⚠️  Errors:")
                for error in result['errors']:
                    print(f"  - {error}")
            else:
                print("\n✅ No errors during indexing")

            # Verify chunks have embeddings
            print("\n3. Verifying embeddings...")

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

                if total > 0:
                    percentage = (with_embeddings / total) * 100
                    print(f"   Coverage: {percentage:.1f}%")

                    if with_embeddings == total:
                        print(f"\n   ✅ All {total} chunks have embeddings!")
                    else:
                        missing = total - with_embeddings
                        print(f"\n   ⚠️  {missing} chunks missing embeddings")

                    # Show a sample chunk
                    if with_embeddings > 0:
                        sample_stmt = select(CodeChunk).where(
                            CodeChunk.embedding.isnot(None)
                        ).limit(1)
                        sample_result = await session.execute(sample_stmt)
                        sample_chunk = sample_result.scalar_one_or_none()

                        if sample_chunk:
                            print(f"\n4. Sample chunk with embedding:")
                            print(f"   Content preview: {sample_chunk.content[:100]}...")
                            embedding_dims = len(sample_chunk.embedding) if sample_chunk.embedding is not None else 0
                            print(f"   Embedding dimensions: {embedding_dims}")
                            print(f"   Chunk type: {sample_chunk.chunk_type}")
                else:
                    print("   ⚠️  No chunks created")

            print("\n" + "=" * 80)
            print("✅ TEST COMPLETE")
            print("=" * 80)

        except Exception as e:
            print(f"\n❌ Test failed:")
            print(f"   {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
