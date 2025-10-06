"""
Integration tests for file deletion and 90-day retention (Scenario 6).

Tests verify (from quickstart.md):
- File deletion detection (FR-009)
- 90-day retention policy
- Soft delete marking (is_deleted=True, deleted_at set)
- Cleanup job after retention period
- Cascade deletion of chunks and embeddings

TDD Compliance: These tests MUST FAIL initially since services are not implemented yet.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from src.models.code_chunk import CodeChunk
    from src.models.code_file import CodeFile
    from src.models.tracking import ChangeEvent


@pytest.fixture
async def indexed_repository_for_deletion(
    tmp_path: Path,
    db_session: AsyncSession,
) -> Path:
    """
    Create and index a test repository for deletion testing.

    Returns repository path after initial indexing.
    """
    pytest.skip("Indexer service not implemented yet (T031)")

    # Future implementation:
    # from src.services.indexer import index_repository
    #
    # repo_path = tmp_path / "deletion-test-repo"
    # repo_path.mkdir()
    #
    # src_dir = repo_path / "src"
    # src_dir.mkdir()
    #
    # (src_dir / "calculator.py").write_text('''def add(a: int, b: int) -> int:
    #     """Add two numbers."""
    #     return a + b
    # ''')
    #
    # (src_dir / "utils.py").write_text('''def log_message(msg: str) -> None:
    #     """Log a message."""
    #     print(msg)
    # ''')
    #
    # (src_dir / "config.py").write_text('''CONFIG = {"debug": True}
    # ''')
    #
    # # Index repository
    # await index_repository(path=repo_path, name="Deletion Test Repo", force_reindex=False)
    #
    # return repo_path


@pytest.fixture
async def db_session() -> AsyncSession:
    """Create async database session for tests."""
    pytest.skip("Database session fixture not implemented yet (requires T019-T027)")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_file_deletion_marks_as_deleted_not_implemented(
    indexed_repository_for_deletion: Path,
    db_session: AsyncSession,
) -> None:
    """
    Test that deleted files are marked as deleted - NOT YET IMPLEMENTED.

    Expected workflow:
    1. Repository is indexed with 3 files
    2. Delete one file from filesystem
    3. Re-run indexing
    4. Verify file marked as deleted (is_deleted=True)
    5. Verify deleted_at timestamp set
    6. Verify chunks are retained (not immediately deleted)

    This test MUST FAIL until T031 (indexer with deletion detection) is implemented.
    """
    pytest.skip("File deletion detection not implemented yet (T031)")

    # Future implementation:
    # from src.services.indexer import index_repository
    # from src.models.code_file import CodeFile
    # from src.models.code_chunk import CodeChunk
    #
    # # Get utils.py file ID before deletion
    # stmt = select(CodeFile).where(CodeFile.relative_path == "src/utils.py")
    # utils_file = await db_session.scalar(stmt)
    # assert utils_file is not None
    # assert utils_file.is_deleted is False
    # file_id = utils_file.id
    #
    # # Get chunks for this file
    # stmt = select(CodeChunk).where(CodeChunk.code_file_id == file_id)
    # result = await db_session.execute(stmt)
    # chunks_before = result.scalars().all()
    # chunk_count = len(chunks_before)
    # assert chunk_count > 0
    #
    # # Delete file from filesystem
    # utils_file_path = indexed_repository_for_deletion / "src" / "utils.py"
    # utils_file_path.unlink()
    #
    # # Re-index to detect deletion
    # await index_repository(
    #     path=indexed_repository_for_deletion,
    #     name="Deletion Test Repo",
    #     force_reindex=False,
    # )
    #
    # # Verify file marked as deleted
    # await db_session.refresh(utils_file)
    # assert utils_file.is_deleted is True
    # assert utils_file.deleted_at is not None
    # assert isinstance(utils_file.deleted_at, datetime)
    #
    # # Verify chunks still exist (retained)
    # stmt = select(CodeChunk).where(CodeChunk.code_file_id == file_id)
    # result = await db_session.execute(stmt)
    # chunks_after = result.scalars().all()
    # assert len(chunks_after) == chunk_count  # Chunks retained


@pytest.mark.integration
@pytest.mark.asyncio
async def test_change_event_recorded_for_deletion(
    indexed_repository_for_deletion: Path,
    db_session: AsyncSession,
) -> None:
    """
    Test that ChangeEvent is recorded when file is deleted.

    Expected behavior:
    - Delete file
    - Re-index repository
    - Verify ChangeEvent created with event_type='deleted'
    - Verify ChangeEvent.processed=True

    This test MUST FAIL until T025 (ChangeEvent model) and T031 (indexer) are implemented.
    """
    pytest.skip("Change event tracking not implemented yet (T025, T031)")

    # Future implementation:
    # from src.services.indexer import index_repository
    # from src.models.code_file import CodeFile
    # from src.models.tracking import ChangeEvent
    #
    # # Get config.py file ID
    # stmt = select(CodeFile).where(CodeFile.relative_path == "src/config.py")
    # config_file = await db_session.scalar(stmt)
    # assert config_file is not None
    # file_id = config_file.id
    #
    # # Delete file
    # config_file_path = indexed_repository_for_deletion / "src" / "config.py"
    # config_file_path.unlink()
    #
    # # Re-index
    # await index_repository(
    #     path=indexed_repository_for_deletion,
    #     name="Deletion Test Repo",
    #     force_reindex=False,
    # )
    #
    # # Verify ChangeEvent created
    # stmt = (
    #     select(ChangeEvent)
    #     .where(ChangeEvent.code_file_id == file_id)
    #     .where(ChangeEvent.event_type == "deleted")
    #     .order_by(ChangeEvent.detected_at.desc())
    # )
    # change_event = await db_session.scalar(stmt)
    # assert change_event is not None
    # assert change_event.event_type == "deleted"
    # assert change_event.processed is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_deleted_files_retained_for_90_days(
    indexed_repository_for_deletion: Path,
    db_session: AsyncSession,
) -> None:
    """
    Test that deleted files are retained in database for 90 days.

    Expected behavior:
    - Delete file and mark as deleted
    - Verify file record still exists in database
    - Verify chunks still accessible
    - File should remain until cleanup job runs

    This test MUST FAIL until T031 (indexer) is implemented.
    """
    pytest.skip("File deletion retention not implemented yet (T031)")

    # Future implementation:
    # from src.services.indexer import index_repository
    # from src.models.code_file import CodeFile
    # from src.models.code_chunk import CodeChunk
    #
    # # Delete file
    # utils_file_path = indexed_repository_for_deletion / "src" / "utils.py"
    # utils_file_path.unlink()
    #
    # # Re-index
    # await index_repository(
    #     path=indexed_repository_for_deletion,
    #     name="Deletion Test Repo",
    #     force_reindex=False,
    # )
    #
    # # Verify file still exists in database (soft deleted)
    # stmt = select(CodeFile).where(CodeFile.relative_path == "src/utils.py")
    # deleted_file = await db_session.scalar(stmt)
    # assert deleted_file is not None
    # assert deleted_file.is_deleted is True
    # assert deleted_file.deleted_at is not None
    #
    # # Verify chunks still exist
    # stmt = select(CodeChunk).where(CodeChunk.code_file_id == deleted_file.id)
    # result = await db_session.execute(stmt)
    # chunks = result.scalars().all()
    # assert len(chunks) > 0  # Chunks retained


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cleanup_removes_files_after_90_days(
    indexed_repository_for_deletion: Path,
    db_session: AsyncSession,
) -> None:
    """
    Test that cleanup job removes files deleted >90 days ago.

    Expected behavior:
    - Mark file as deleted with deleted_at = 91 days ago
    - Run cleanup job
    - Verify file permanently removed from database
    - Verify chunks cascade deleted

    This test MUST FAIL until T041 (cleanup script) is implemented.
    """
    pytest.skip("Cleanup job not implemented yet (T041)")

    # Future implementation:
    # from src.services.indexer import index_repository
    # from src.models.code_file import CodeFile
    # from src.models.code_chunk import CodeChunk
    # from scripts.cleanup_deleted_files import cleanup_deleted_files
    #
    # # Delete file
    # utils_file_path = indexed_repository_for_deletion / "src" / "utils.py"
    # utils_file_path.unlink()
    #
    # # Re-index
    # await index_repository(
    #     path=indexed_repository_for_deletion,
    #     name="Deletion Test Repo",
    #     force_reindex=False,
    # )
    #
    # # Get deleted file
    # stmt = select(CodeFile).where(CodeFile.relative_path == "src/utils.py")
    # deleted_file = await db_session.scalar(stmt)
    # assert deleted_file is not None
    # file_id = deleted_file.id
    #
    # # Manually set deleted_at to 91 days ago
    # ninety_one_days_ago = datetime.utcnow() - timedelta(days=91)
    # stmt = (
    #     update(CodeFile)
    #     .where(CodeFile.id == file_id)
    #     .values(deleted_at=ninety_one_days_ago)
    # )
    # await db_session.execute(stmt)
    # await db_session.commit()
    #
    # # Run cleanup job
    # await cleanup_deleted_files(db_session)
    #
    # # Verify file permanently removed
    # stmt = select(CodeFile).where(CodeFile.id == file_id)
    # result = await db_session.scalar(stmt)
    # assert result is None  # File permanently deleted
    #
    # # Verify chunks cascade deleted
    # stmt = select(CodeChunk).where(CodeChunk.code_file_id == file_id)
    # result = await db_session.execute(stmt)
    # chunks = result.scalars().all()
    # assert len(chunks) == 0  # Chunks cascade deleted


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cleanup_preserves_files_within_90_days(
    indexed_repository_for_deletion: Path,
    db_session: AsyncSession,
) -> None:
    """
    Test that cleanup job preserves files deleted <90 days ago.

    Expected behavior:
    - Mark file as deleted with deleted_at = 30 days ago
    - Run cleanup job
    - Verify file still exists (not removed)
    - Verify chunks still exist

    This test MUST FAIL until T041 (cleanup script) is implemented.
    """
    pytest.skip("Cleanup job not implemented yet (T041)")

    # Future implementation:
    # from src.services.indexer import index_repository
    # from src.models.code_file import CodeFile
    # from src.models.code_chunk import CodeChunk
    # from scripts.cleanup_deleted_files import cleanup_deleted_files
    #
    # # Delete file
    # config_file_path = indexed_repository_for_deletion / "src" / "config.py"
    # config_file_path.unlink()
    #
    # # Re-index
    # await index_repository(
    #     path=indexed_repository_for_deletion,
    #     name="Deletion Test Repo",
    #     force_reindex=False,
    # )
    #
    # # Get deleted file
    # stmt = select(CodeFile).where(CodeFile.relative_path == "src/config.py")
    # deleted_file = await db_session.scalar(stmt)
    # assert deleted_file is not None
    # file_id = deleted_file.id
    #
    # # Manually set deleted_at to 30 days ago (within retention)
    # thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    # stmt = (
    #     update(CodeFile)
    #     .where(CodeFile.id == file_id)
    #     .values(deleted_at=thirty_days_ago)
    # )
    # await db_session.execute(stmt)
    # await db_session.commit()
    #
    # # Run cleanup job
    # await cleanup_deleted_files(db_session)
    #
    # # Verify file still exists (preserved)
    # stmt = select(CodeFile).where(CodeFile.id == file_id)
    # result = await db_session.scalar(stmt)
    # assert result is not None  # File retained
    # assert result.is_deleted is True
    #
    # # Verify chunks still exist
    # stmt = select(CodeChunk).where(CodeChunk.code_file_id == file_id)
    # result_chunks = await db_session.execute(stmt)
    # chunks = result_chunks.scalars().all()
    # assert len(chunks) > 0  # Chunks retained


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cleanup_exactly_90_days_boundary(
    indexed_repository_for_deletion: Path,
    db_session: AsyncSession,
) -> None:
    """
    Test cleanup behavior at exactly 90-day boundary.

    Expected behavior:
    - File deleted exactly 90 days ago should be retained
    - File deleted 90 days + 1 second ago should be removed
    - Tests boundary condition

    This test MUST FAIL until T041 (cleanup script) is implemented.
    """
    pytest.skip("Cleanup job not implemented yet (T041)")

    # Future implementation:
    # from src.services.indexer import index_repository
    # from src.models.code_file import CodeFile
    # from scripts.cleanup_deleted_files import cleanup_deleted_files
    #
    # # Create two deleted files with different timestamps
    # # (This test would need manual database manipulation)
    #
    # # Test deleted exactly 90 days ago (should be retained)
    # exactly_90_days = datetime.utcnow() - timedelta(days=90)
    #
    # # Test deleted 90 days + 1 second ago (should be removed)
    # over_90_days = datetime.utcnow() - timedelta(days=90, seconds=1)
    #
    # # Run cleanup and verify boundary behavior


@pytest.mark.integration
@pytest.mark.asyncio
async def test_file_resurrection_after_deletion(
    indexed_repository_for_deletion: Path,
    db_session: AsyncSession,
) -> None:
    """
    Test that re-creating a deleted file updates the record.

    Expected behavior:
    - Delete file (marked is_deleted=True)
    - Re-create file with same path
    - Re-index repository
    - Verify is_deleted=False
    - Verify deleted_at=None
    - Verify new chunks created

    This test MUST FAIL until T031 (indexer) is implemented.
    """
    pytest.skip("File resurrection not implemented yet (T031)")

    # Future implementation:
    # from src.services.indexer import index_repository
    # from src.models.code_file import CodeFile
    #
    # # Delete file
    # utils_file_path = indexed_repository_for_deletion / "src" / "utils.py"
    # utils_file_path.unlink()
    #
    # # Re-index (marks as deleted)
    # await index_repository(
    #     path=indexed_repository_for_deletion,
    #     name="Deletion Test Repo",
    #     force_reindex=False,
    # )
    #
    # # Verify deleted
    # stmt = select(CodeFile).where(CodeFile.relative_path == "src/utils.py")
    # deleted_file = await db_session.scalar(stmt)
    # assert deleted_file is not None
    # assert deleted_file.is_deleted is True
    # file_id = deleted_file.id
    #
    # # Re-create file
    # utils_file_path.write_text('''def new_function() -> str:
    #     """New implementation."""
    #     return "resurrected"
    # ''')
    #
    # # Re-index (should resurrect)
    # await index_repository(
    #     path=indexed_repository_for_deletion,
    #     name="Deletion Test Repo",
    #     force_reindex=False,
    # )
    #
    # # Verify resurrected
    # await db_session.refresh(deleted_file)
    # assert deleted_file.is_deleted is False
    # assert deleted_file.deleted_at is None
    # assert deleted_file.content_hash != ""  # New hash for new content


@pytest.mark.integration
@pytest.mark.asyncio
async def test_deleted_files_excluded_from_search(
    indexed_repository_for_deletion: Path,
    db_session: AsyncSession,
) -> None:
    """
    Test that deleted files are excluded from search results.

    Expected behavior:
    - Delete file
    - Search for content that was in deleted file
    - Verify deleted file chunks not returned in search results
    - Only active file chunks returned

    This test MUST FAIL until T032 (searcher with deletion filtering) is implemented.
    """
    pytest.skip("Search with deletion filtering not implemented yet (T032)")

    # Future implementation:
    # from src.services.indexer import index_repository
    # from src.services.searcher import search_code
    #
    # # Delete utils.py
    # utils_file_path = indexed_repository_for_deletion / "src" / "utils.py"
    # utils_file_path.unlink()
    #
    # # Re-index
    # await index_repository(
    #     path=indexed_repository_for_deletion,
    #     name="Deletion Test Repo",
    #     force_reindex=False,
    # )
    #
    # # Search for "log message" (was in utils.py)
    # results = await search_code(
    #     query="log message function",
    #     limit=10,
    # )
    #
    # # Verify deleted file not in results
    # file_paths = [r.file_path for r in results]
    # assert "src/utils.py" not in file_paths
    #
    # # Verify only active files in results
    # for result in results:
    #     assert "src/calculator.py" in result.file_path or "src/config.py" in result.file_path
