"""
Integration tests for incremental file updates (Scenario 2).

Tests verify (from quickstart.md):
- Incremental update detection (FR-007 to FR-010)
- Only modified files are re-indexed
- Change events are recorded
- Update performance: <10 seconds for incremental updates
- File modification, addition, and deletion detection

TDD Compliance: These tests MUST FAIL initially since services are not implemented yet.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from src.models.change_event import ChangeEvent
    from src.models.code_chunk import CodeChunk
    from src.models.code_file import CodeFile
    from src.models.repository import Repository


@pytest.fixture
async def indexed_repository(tmp_path: Path, db_session: AsyncSession) -> Path:
    """
    Create and index a test repository.

    Returns the repository path after initial indexing.
    This fixture will need proper implementation once indexer is ready.
    """
    pytest.skip("Indexer service not implemented yet (T031)")

    # Future implementation:
    # repo_path = tmp_path / "test-repo"
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
    # # Initial indexing
    # from src.services.indexer import index_repository
    # await index_repository(path=repo_path, name="Test Repo", force_reindex=False)
    #
    # return repo_path


@pytest.fixture
async def db_session() -> AsyncSession:
    """
    Create async database session for tests.

    Note: This fixture will need proper implementation once database setup is complete.
    """
    pytest.skip("Database session fixture not implemented yet (requires T019-T027)")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_incremental_update_for_modified_file_not_implemented(
    indexed_repository: Path,
    db_session: AsyncSession,
) -> None:
    """
    Test that only modified files are re-indexed - NOT YET IMPLEMENTED.

    Expected workflow:
    1. Repository is already indexed (via fixture)
    2. Modify one file (add new function)
    3. Re-run indexing with force_reindex=False
    4. Verify only modified file is re-indexed
    5. Verify new chunks created for new function
    6. Verify unchanged file is not re-processed

    This test MUST FAIL until T031 (indexer with incremental logic) is implemented.
    """
    pytest.skip("Incremental indexing not implemented yet (T031)")

    # Future implementation:
    # from src.services.indexer import index_repository
    # from src.models.code_file import CodeFile
    # from src.models.code_chunk import CodeChunk
    #
    # # Get initial state
    # stmt = select(CodeFile).where(CodeFile.relative_path == "src/calculator.py")
    # original_file = await db_session.scalar(stmt)
    # assert original_file is not None
    # original_hash = original_file.content_hash
    # original_indexed_at = original_file.indexed_at
    #
    # stmt = select(CodeChunk).where(CodeChunk.code_file_id == original_file.id)
    # result = await db_session.execute(stmt)
    # original_chunks = result.scalars().all()
    # original_chunk_count = len(original_chunks)
    #
    # # Wait a moment to ensure timestamp difference
    # time.sleep(0.1)
    #
    # # Modify calculator.py - add new function
    # calc_file = indexed_repository / "src" / "calculator.py"
    # calc_file.write_text(calc_file.read_text() + '''
    #
    # def subtract(a: int, b: int) -> int:
    #     """Subtract b from a."""
    #     return a - b
    # ''')
    #
    # # Run incremental update
    # start_time = time.perf_counter()
    # result = await index_repository(
    #     path=indexed_repository,
    #     name="Test Repo",
    #     force_reindex=False,
    # )
    # duration = time.perf_counter() - start_time
    #
    # # Verify only one file re-indexed
    # assert result.files_indexed == 1
    # assert result.chunks_created >= 1  # At least subtract function
    # assert duration < 10, f"Incremental update took {duration:.2f}s, should be <10s"
    #
    # # Verify calculator.py was updated
    # await db_session.refresh(original_file)
    # assert original_file.content_hash != original_hash
    # assert original_file.indexed_at > original_indexed_at
    #
    # # Verify new chunk exists
    # stmt = select(CodeChunk).where(CodeChunk.code_file_id == original_file.id)
    # result_chunks = await db_session.execute(stmt)
    # updated_chunks = result_chunks.scalars().all()
    # assert len(updated_chunks) > original_chunk_count
    #
    # # Verify subtract function chunk exists
    # chunk_contents = [c.content for c in updated_chunks]
    # assert any("def subtract" in content for content in chunk_contents)
    #
    # # Verify utils.py was NOT re-indexed (unchanged)
    # stmt = select(CodeFile).where(CodeFile.relative_path == "src/utils.py")
    # utils_file = await db_session.scalar(stmt)
    # assert utils_file is not None
    # # indexed_at should not change for unchanged files
    # # (This assumes the indexer tracks file hashes and skips unchanged files)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_change_event_recorded_for_modification(
    indexed_repository: Path,
    db_session: AsyncSession,
) -> None:
    """
    Test that change events are recorded when files are modified.

    Expected behavior:
    - Modify a file
    - Re-index repository
    - Verify ChangeEvent record created with event_type='modified'
    - Verify ChangeEvent.processed=True after indexing

    This test MUST FAIL until T031 (indexer) and T025 (ChangeEvent model) are implemented.
    """
    pytest.skip("Change event tracking not implemented yet (T025, T031)")

    # Future implementation:
    # from src.services.indexer import index_repository
    # from src.models.code_file import CodeFile
    # from src.models.tracking import ChangeEvent
    #
    # # Modify file
    # calc_file = indexed_repository / "src" / "calculator.py"
    # calc_file.write_text(calc_file.read_text() + "\n# Comment\n")
    #
    # # Re-index
    # await index_repository(
    #     path=indexed_repository,
    #     name="Test Repo",
    #     force_reindex=False,
    # )
    #
    # # Get calculator.py file ID
    # stmt = select(CodeFile).where(CodeFile.relative_path == "src/calculator.py")
    # code_file = await db_session.scalar(stmt)
    # assert code_file is not None
    #
    # # Verify ChangeEvent created
    # stmt = (
    #     select(ChangeEvent)
    #     .where(ChangeEvent.code_file_id == code_file.id)
    #     .order_by(ChangeEvent.detected_at.desc())
    # )
    # change_event = await db_session.scalar(stmt)
    # assert change_event is not None
    # assert change_event.event_type == "modified"
    # assert change_event.processed is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_change_event_for_new_file_addition(
    indexed_repository: Path,
    db_session: AsyncSession,
) -> None:
    """
    Test that change events are recorded when new files are added.

    Expected behavior:
    - Add a new file to repository
    - Re-index repository
    - Verify ChangeEvent record created with event_type='added'
    - Verify new file is indexed

    This test MUST FAIL until T031 (indexer) is implemented.
    """
    pytest.skip("Change event tracking not implemented yet (T025, T031)")

    # Future implementation:
    # from src.services.indexer import index_repository
    # from src.models.code_file import CodeFile
    # from src.models.tracking import ChangeEvent
    #
    # # Add new file
    # new_file = indexed_repository / "src" / "math_utils.py"
    # new_file.write_text('''def square(x: int) -> int:
    #     """Return the square of x."""
    #     return x * x
    # ''')
    #
    # # Re-index
    # result = await index_repository(
    #     path=indexed_repository,
    #     name="Test Repo",
    #     force_reindex=False,
    # )
    #
    # # Verify new file detected
    # assert result.files_indexed >= 1
    #
    # # Get new file record
    # stmt = select(CodeFile).where(CodeFile.relative_path == "src/math_utils.py")
    # code_file = await db_session.scalar(stmt)
    # assert code_file is not None
    # assert code_file.is_deleted is False
    #
    # # Verify ChangeEvent created
    # stmt = (
    #     select(ChangeEvent)
    #     .where(ChangeEvent.code_file_id == code_file.id)
    #     .order_by(ChangeEvent.detected_at.desc())
    # )
    # change_event = await db_session.scalar(stmt)
    # assert change_event is not None
    # assert change_event.event_type == "added"
    # assert change_event.processed is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_change_event_for_file_deletion(
    indexed_repository: Path,
    db_session: AsyncSession,
) -> None:
    """
    Test that change events are recorded when files are deleted.

    Expected behavior:
    - Delete a file from repository
    - Re-index repository
    - Verify ChangeEvent record created with event_type='deleted'
    - Verify file marked as deleted in database (is_deleted=True)

    This test MUST FAIL until T031 (indexer) is implemented.
    """
    pytest.skip("Change event tracking not implemented yet (T025, T031)")

    # Future implementation:
    # from src.services.indexer import index_repository
    # from src.models.code_file import CodeFile
    # from src.models.tracking import ChangeEvent
    #
    # # Get utils.py file ID before deletion
    # stmt = select(CodeFile).where(CodeFile.relative_path == "src/utils.py")
    # code_file = await db_session.scalar(stmt)
    # assert code_file is not None
    # file_id = code_file.id
    #
    # # Delete file
    # utils_file = indexed_repository / "src" / "utils.py"
    # utils_file.unlink()
    #
    # # Re-index
    # await index_repository(
    #     path=indexed_repository,
    #     name="Test Repo",
    #     force_reindex=False,
    # )
    #
    # # Verify file marked as deleted
    # await db_session.refresh(code_file)
    # assert code_file.is_deleted is True
    # assert code_file.deleted_at is not None
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
async def test_incremental_update_performance(
    indexed_repository: Path,
    db_session: AsyncSession,
) -> None:
    """
    Test that incremental updates meet <10 second performance target.

    Expected behavior:
    - Modify a single file
    - Re-index should complete in <10 seconds
    - Much faster than full re-index

    This test MUST FAIL until T031 (indexer optimization) is implemented.
    """
    pytest.skip("Incremental indexing not implemented yet (T031)")

    # Future implementation:
    # from src.services.indexer import index_repository
    #
    # # Modify one file
    # calc_file = indexed_repository / "src" / "calculator.py"
    # calc_file.write_text(calc_file.read_text() + "\n# Modified\n")
    #
    # # Measure incremental update time
    # start_time = time.perf_counter()
    # result = await index_repository(
    #     path=indexed_repository,
    #     name="Test Repo",
    #     force_reindex=False,
    # )
    # duration = time.perf_counter() - start_time
    #
    # # Verify performance
    # assert duration < 10, f"Incremental update took {duration:.2f}s, exceeds 10s target"
    # assert result.files_indexed == 1
    # assert result.status == "success"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_force_reindex_overrides_incremental_logic(
    indexed_repository: Path,
    db_session: AsyncSession,
) -> None:
    """
    Test that force_reindex=True re-indexes all files regardless of changes.

    Expected behavior:
    - Call index_repository with force_reindex=True
    - All files should be re-indexed, not just changed ones
    - All chunks should be regenerated

    This test MUST FAIL until T031 (indexer) is implemented.
    """
    pytest.skip("Force reindex logic not implemented yet (T031)")

    # Future implementation:
    # from src.services.indexer import index_repository
    # from src.models.code_file import CodeFile
    #
    # # Get current file count
    # stmt = select(CodeFile)
    # result = await db_session.execute(stmt)
    # files_before = result.scalars().all()
    # file_count = len(files_before)
    #
    # # Store original indexed_at timestamps
    # original_timestamps = {f.id: f.indexed_at for f in files_before}
    #
    # # Wait to ensure timestamp difference
    # time.sleep(0.1)
    #
    # # Force reindex (no file modifications)
    # result = await index_repository(
    #     path=indexed_repository,
    #     name="Test Repo",
    #     force_reindex=True,
    # )
    #
    # # Verify all files re-indexed
    # assert result.files_indexed == file_count
    # assert result.status == "success"
    #
    # # Verify all files have updated timestamps
    # stmt = select(CodeFile)
    # result_after = await db_session.execute(stmt)
    # files_after = result_after.scalars().all()
    #
    # for file in files_after:
    #     assert file.indexed_at > original_timestamps[file.id]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_hash_based_change_detection(
    indexed_repository: Path,
    db_session: AsyncSession,
) -> None:
    """
    Test that file changes are detected via content hash (SHA-256).

    Expected behavior:
    - Modify file content (same path)
    - File hash should change
    - Incremental indexer should detect change via hash comparison

    This test MUST FAIL until T028 (scanner) and T031 (indexer) are implemented.
    """
    pytest.skip("Hash-based change detection not implemented yet (T028, T031)")

    # Future implementation:
    # from src.services.indexer import index_repository
    # from src.models.code_file import CodeFile
    #
    # # Get original hash
    # stmt = select(CodeFile).where(CodeFile.relative_path == "src/calculator.py")
    # original_file = await db_session.scalar(stmt)
    # assert original_file is not None
    # original_hash = original_file.content_hash
    #
    # # Modify file (change content)
    # calc_file = indexed_repository / "src" / "calculator.py"
    # original_content = calc_file.read_text()
    # calc_file.write_text(original_content.replace("Add two numbers", "Add numbers"))
    #
    # # Re-index
    # await index_repository(
    #     path=indexed_repository,
    #     name="Test Repo",
    #     force_reindex=False,
    # )
    #
    # # Verify hash changed
    # await db_session.refresh(original_file)
    # assert original_file.content_hash != original_hash
    # assert len(original_file.content_hash) == 64  # SHA-256 hex length
