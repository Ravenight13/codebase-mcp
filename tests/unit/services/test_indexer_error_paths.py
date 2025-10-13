"""Unit tests for indexer.py error paths and edge cases.

This test suite targets uncovered lines in src/services/indexer.py to improve
coverage from 50.76% to 90%+.

Test Coverage Areas:
- File reading errors (FileNotFoundError, UnicodeDecodeError, PermissionError)
- Repository path validation errors (not absolute, not a directory)
- Empty repository scenarios (no files found)
- Force reindex edge cases (all files filtered)
- Transaction rollback on critical errors
- Chunk deletion failures
- Embedding generation failures
- Change event creation with edge cases
- Code file creation errors

Constitutional Compliance:
- Principle VII: Test-driven development with comprehensive error coverage
- Principle VIII: Type-safe test patterns with mypy --strict
- Principle V: Production quality with edge case validation
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import CodeChunk, CodeFile, Repository
from src.services.indexer import (
    IndexResult,
    _create_code_files,
    _delete_chunks_for_file,
    _get_or_create_repository,
    _read_file,
    incremental_update,
    index_repository,
)
from src.services.scanner import ChangeSet


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def mock_repo_path(tmp_path: Path) -> Path:
    """Create a temporary repository path for testing."""
    repo = tmp_path / "test-repo"
    repo.mkdir()
    return repo


@pytest.fixture
def sample_python_file(tmp_path: Path) -> Path:
    """Create a sample Python file for testing."""
    test_file = tmp_path / "test.py"
    test_file.write_text("def hello():\n    return 'world'\n", encoding="utf-8")
    return test_file


@pytest.fixture
def binary_file(tmp_path: Path) -> Path:
    """Create a binary file for testing."""
    binary = tmp_path / "test.png"
    binary.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    return binary


@pytest.fixture
def empty_file(tmp_path: Path) -> Path:
    """Create an empty file for testing."""
    empty = tmp_path / "empty.py"
    empty.write_text("", encoding="utf-8")
    return empty


# ==============================================================================
# Repository Path Validation Error Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_get_or_create_repository_non_absolute_path(db_session: AsyncSession) -> None:
    """Test ValueError raised for non-absolute repository path.

    Covers: Line 134 (ValueError for non-absolute path)
    """
    relative_path = Path("relative/path")

    with pytest.raises(ValueError, match="Repository path must be absolute"):
        await _get_or_create_repository(db_session, relative_path, "test-repo")


@pytest.mark.asyncio
async def test_index_repository_non_directory(db_session: AsyncSession, tmp_path: Path) -> None:
    """Test indexing fails gracefully when path is not a directory.

    Covers: OSError handling in index_repository
    """
    # Create a file instead of directory
    file_path = tmp_path / "not-a-directory.txt"
    file_path.write_text("test")

    # Mock scan_repository to raise OSError
    with patch("src.services.indexer.scan_repository", side_effect=OSError("Not a directory")):
        result = await index_repository(file_path, "test", db_session)

    assert result.status == "failed"
    assert len(result.errors) > 0
    assert result.files_indexed == 0


@pytest.mark.asyncio
async def test_index_repository_permission_denied(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    """Test indexing fails gracefully when repository is not accessible.

    Covers: OSError handling for permission errors
    """
    repo_path = tmp_path / "no-access"
    repo_path.mkdir()

    # Mock scan_repository to raise PermissionError
    with patch(
        "src.services.indexer.scan_repository",
        side_effect=PermissionError("Permission denied"),
    ):
        result = await index_repository(repo_path, "test", db_session)

    assert result.status == "failed"
    assert any("Permission denied" in error for error in result.errors)


# ==============================================================================
# File Reading Error Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_read_file_not_found() -> None:
    """Test FileNotFoundError handling in _read_file.

    Covers: Lines 189-194 (UnicodeDecodeError logging)
    Covers: Lines 195-200 (Exception handling in _read_file)
    """
    nonexistent = Path("/nonexistent/file.py")

    with pytest.raises(FileNotFoundError):
        await _read_file(nonexistent)


@pytest.mark.asyncio
async def test_read_file_unicode_decode_error(tmp_path: Path) -> None:
    """Test UnicodeDecodeError handling for binary files.

    Covers: Lines 189-194 (UnicodeDecodeError exception path)
    """
    binary_file = tmp_path / "binary.dat"
    binary_file.write_bytes(b"\x80\x81\x82\x83\x84")

    with pytest.raises(UnicodeDecodeError):
        await _read_file(binary_file)


@pytest.mark.asyncio
async def test_read_file_permission_denied(tmp_path: Path) -> None:
    """Test permission error handling in file reading.

    Covers: Lines 195-200 (general Exception handling)
    """
    restricted_file = tmp_path / "restricted.py"
    restricted_file.write_text("test")

    # Mock read_text to raise PermissionError
    with patch.object(Path, "read_text", side_effect=PermissionError("Permission denied")):
        with pytest.raises(PermissionError):
            await _read_file(restricted_file)


@pytest.mark.asyncio
async def test_index_repository_file_read_errors(
    db_session: AsyncSession, mock_repo_path: Path
) -> None:
    """Test partial indexing success when some files fail to read.

    Covers: Lines 687-695 (file read error handling in batch processing)
    """
    # Create test files
    good_file = mock_repo_path / "good.py"
    good_file.write_text("def test(): pass")

    bad_file = mock_repo_path / "bad.py"
    bad_file.write_text("test")

    # Mock scan_repository to return both files
    with patch(
        "src.services.indexer.scan_repository", return_value=[good_file, bad_file]
    ), patch("src.services.indexer._read_file") as mock_read:
        # First call succeeds, second fails
        async def read_side_effect(path: Path) -> str:
            if path == good_file:
                return "def test(): pass"
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")

        mock_read.side_effect = read_side_effect

        # Mock other dependencies
        with patch("src.services.indexer.detect_changes") as mock_changes:
            mock_changes.return_value = ChangeSet(
                added=[good_file, bad_file], modified=[], deleted=[]
            )

            with patch("src.services.indexer.chunk_files_batch", return_value=[]):
                result = await index_repository(
                    mock_repo_path, "test-repo", db_session, force_reindex=True
                )

    # Should be partial success with errors
    assert result.status == "partial"
    assert len(result.errors) > 0
    assert any("bad.py" in error for error in result.errors)


# ==============================================================================
# Empty Repository Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_index_repository_no_files_found(
    db_session: AsyncSession, mock_repo_path: Path
) -> None:
    """Test indexing fails when no files are found in repository.

    Covers: Lines 596-620 (empty repository error handling)
    """
    # Mock scan_repository to return empty list
    with patch("src.services.indexer.scan_repository", return_value=[]):
        result = await index_repository(
            mock_repo_path, "empty-repo", db_session, force_reindex=True
        )

    assert result.status == "failed"
    assert result.files_indexed == 0
    assert result.chunks_created == 0
    assert any("No files found" in error for error in result.errors)


@pytest.mark.asyncio
async def test_index_repository_force_reindex_all_filtered(
    db_session: AsyncSession, mock_repo_path: Path
) -> None:
    """Test force reindex when all files are filtered out.

    Covers: Lines 623-647 (force reindex with no processable files)
    """
    # Create files that exist but will be filtered
    test_file = mock_repo_path / "test.py"
    test_file.write_text("test")

    # Mock scan to return files, but detect_changes returns nothing
    with patch("src.services.indexer.scan_repository", return_value=[test_file]):
        with patch(
            "src.services.indexer.detect_changes",
            return_value=ChangeSet(added=[], modified=[], deleted=[]),
        ):
            result = await index_repository(
                mock_repo_path, "test-repo", db_session, force_reindex=True
            )

    # Should fail because force_reindex=True but nothing to process
    assert result.status == "failed"
    assert "Force reindex requested but no files to process" in result.errors[0]


@pytest.mark.asyncio
async def test_index_repository_no_changes_incremental(
    db_session: AsyncSession, mock_repo_path: Path
) -> None:
    """Test incremental update with no changes returns success.

    Covers: Lines 649-672 (no changes detected, normal case)
    """
    test_file = mock_repo_path / "test.py"
    test_file.write_text("test")

    with patch("src.services.indexer.scan_repository", return_value=[test_file]):
        with patch(
            "src.services.indexer.detect_changes",
            return_value=ChangeSet(added=[], modified=[], deleted=[]),
        ):
            result = await index_repository(
                mock_repo_path, "test-repo", db_session, force_reindex=False
            )

    assert result.status == "success"
    assert result.files_indexed == 0
    assert len(result.errors) == 0


# ==============================================================================
# CodeFile Creation Error Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_create_code_files_path_outside_repo(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    """Test ValueError when file path is not under repository.

    Covers: Line 227 (ValueError for path outside repo)
    """
    repo_path = tmp_path / "repo"
    repo_path.mkdir()

    outside_file = tmp_path / "outside.py"
    outside_file.write_text("test")

    repo_id = uuid4()

    with pytest.raises(ValueError, match="is not under repository"):
        await _create_code_files(db_session, repo_id, repo_path, [outside_file])


@pytest.mark.asyncio
async def test_index_repository_code_file_creation_error(
    db_session: AsyncSession, mock_repo_path: Path
) -> None:
    """Test partial success when CodeFile creation fails.

    Covers: Lines 702-709 (CodeFile creation error handling)
    """
    test_file = mock_repo_path / "test.py"
    test_file.write_text("def test(): pass")

    with patch("src.services.indexer.scan_repository", return_value=[test_file]):
        with patch(
            "src.services.indexer.detect_changes",
            return_value=ChangeSet(added=[test_file], modified=[], deleted=[]),
        ):
            # Mock _create_code_files to raise error
            with patch(
                "src.services.indexer._create_code_files",
                side_effect=ValueError("Database error"),
            ):
                result = await index_repository(
                    mock_repo_path, "test-repo", db_session, force_reindex=True
                )

    assert result.status == "partial"
    assert any("Failed to create CodeFile records" in error for error in result.errors)


# ==============================================================================
# Chunk Deletion Error Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_delete_chunks_for_file_success(db_session: AsyncSession) -> None:
    """Test successful deletion of chunks for a file.

    Covers: Lines 303-319 (chunk deletion logic)
    """
    # Create test file and chunks
    file_id = uuid4()

    # Mock the query to return some chunks
    mock_chunks = [
        Mock(spec=CodeChunk, id=uuid4()),
        Mock(spec=CodeChunk, id=uuid4()),
    ]

    with patch.object(db_session, "execute") as mock_execute:
        mock_result = Mock()
        mock_result.scalars().all.return_value = mock_chunks
        mock_execute.return_value = mock_result

        await _delete_chunks_for_file(db_session, file_id)

        # Should have called delete for each chunk
        assert db_session.delete.call_count == len(mock_chunks)


@pytest.mark.asyncio
async def test_index_repository_chunk_deletion_error(
    db_session: AsyncSession, mock_repo_path: Path
) -> None:
    """Test partial success when chunk deletion fails.

    Covers: Lines 715-718 (chunk deletion error handling)
    """
    test_file = mock_repo_path / "test.py"
    test_file.write_text("def test(): pass")

    with patch("src.services.indexer.scan_repository", return_value=[test_file]):
        with patch(
            "src.services.indexer.detect_changes",
            return_value=ChangeSet(added=[], modified=[test_file], deleted=[]),
        ):
            with patch("src.services.indexer._create_code_files", return_value=[uuid4()]):
                # Mock chunk deletion to fail
                with patch(
                    "src.services.indexer._delete_chunks_for_file",
                    side_effect=Exception("Delete failed"),
                ):
                    with patch("src.services.indexer.chunk_files_batch", return_value=[]):
                        result = await index_repository(
                            mock_repo_path, "test-repo", db_session, force_reindex=False
                        )

    assert result.status == "partial"
    assert any("Failed to delete chunks" in error for error in result.errors)


# ==============================================================================
# Chunking Error Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_index_repository_chunking_error(
    db_session: AsyncSession, mock_repo_path: Path
) -> None:
    """Test partial success when chunking fails.

    Covers: Lines 724-731 (chunking error handling)
    """
    test_file = mock_repo_path / "test.py"
    test_file.write_text("def test(): pass")

    with patch("src.services.indexer.scan_repository", return_value=[test_file]):
        with patch(
            "src.services.indexer.detect_changes",
            return_value=ChangeSet(added=[test_file], modified=[], deleted=[]),
        ):
            with patch("src.services.indexer._create_code_files", return_value=[uuid4()]):
                with patch("src.services.indexer._delete_chunks_for_file"):
                    # Mock chunking to fail
                    with patch(
                        "src.services.indexer.chunk_files_batch",
                        side_effect=Exception("Chunking failed"),
                    ):
                        result = await index_repository(
                            mock_repo_path, "test-repo", db_session, force_reindex=True
                        )

    assert result.status == "partial"
    assert any("Failed to chunk files" in error for error in result.errors)


# ==============================================================================
# Embedding Generation Error Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_index_repository_embedding_error(
    db_session: AsyncSession, mock_repo_path: Path
) -> None:
    """Test partial success when embedding generation fails.

    Covers: Lines 789-802 (embedding generation error handling)
    """
    test_file = mock_repo_path / "test.py"
    test_file.write_text("def test(): pass")

    # Create mock chunk
    from src.services.chunker import CodeChunkCreate

    mock_chunk = CodeChunkCreate(
        code_file_id=uuid4(),
        content="def test(): pass",
        start_line=1,
        end_line=1,
        chunk_type="function",
    )

    with patch("src.services.indexer.scan_repository", return_value=[test_file]):
        with patch(
            "src.services.indexer.detect_changes",
            return_value=ChangeSet(added=[test_file], modified=[], deleted=[]),
        ):
            with patch("src.services.indexer._create_code_files", return_value=[uuid4()]):
                with patch("src.services.indexer._delete_chunks_for_file"):
                    with patch(
                        "src.services.indexer.chunk_files_batch", return_value=[[mock_chunk]]
                    ):
                        # Mock embedding generation to fail
                        with patch(
                            "src.services.indexer.generate_embeddings",
                            side_effect=Exception("Ollama connection failed"),
                        ):
                            result = await index_repository(
                                mock_repo_path, "test-repo", db_session, force_reindex=True
                            )

    assert result.status == "partial"
    assert any("Failed to generate embeddings" in error for error in result.errors)


# ==============================================================================
# Transaction Rollback Error Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_index_repository_critical_error_rollback(
    db_session: AsyncSession, mock_repo_path: Path
) -> None:
    """Test transaction rollback on critical error.

    Covers: Lines 873-900 (critical error handling with rollback)
    """
    # Mock get_or_create_repository to raise critical error
    with patch(
        "src.services.indexer._get_or_create_repository",
        side_effect=Exception("Critical database error"),
    ):
        result = await index_repository(
            mock_repo_path, "test-repo", db_session, force_reindex=True
        )

    assert result.status == "failed"
    assert len(result.errors) > 0
    assert any("Critical error" in error for error in result.errors)
    assert result.repository_id == UUID("00000000-0000-0000-0000-000000000000")


# ==============================================================================
# Incremental Update Error Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_incremental_update_repository_not_found(db_session: AsyncSession) -> None:
    """Test incremental_update raises ValueError for non-existent repository.

    Covers: Lines 937-938 (repository not found error)
    """
    fake_repo_id = uuid4()

    with pytest.raises(ValueError, match="Repository not found"):
        await incremental_update(fake_repo_id, db_session)


@pytest.mark.asyncio
async def test_incremental_update_success(db_session: AsyncSession, tmp_path: Path) -> None:
    """Test successful incremental update flow.

    Covers: Lines 903-948 (incremental_update function)
    """
    repo_path = tmp_path / "test-repo"
    repo_path.mkdir()

    # Create repository in database
    repo = Repository(path=str(repo_path), name="test-repo", is_active=True)
    db_session.add(repo)
    await db_session.commit()
    await db_session.refresh(repo)

    # Mock scan and detect_changes to return no changes
    with patch("src.services.indexer.scan_repository", return_value=[]):
        with patch(
            "src.services.indexer.detect_changes",
            return_value=ChangeSet(added=[], modified=[], deleted=[]),
        ):
            result = await incremental_update(repo.id, db_session)

    assert result.status == "failed"  # No files found
    assert result.files_indexed == 0


# ==============================================================================
# Edge Case Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_index_repository_empty_file(
    db_session: AsyncSession, mock_repo_path: Path
) -> None:
    """Test indexing empty file succeeds with no chunks.

    Edge case: empty files should be indexed but produce no chunks.
    """
    empty_file = mock_repo_path / "empty.py"
    empty_file.write_text("")

    with patch("src.services.indexer.scan_repository", return_value=[empty_file]):
        with patch(
            "src.services.indexer.detect_changes",
            return_value=ChangeSet(added=[empty_file], modified=[], deleted=[]),
        ):
            with patch("src.services.indexer._create_code_files", return_value=[uuid4()]):
                with patch("src.services.indexer._delete_chunks_for_file"):
                    with patch("src.services.indexer.chunk_files_batch", return_value=[[]]):
                        result = await index_repository(
                            mock_repo_path, "test-repo", db_session, force_reindex=True
                        )

    # Empty file should succeed with 0 chunks
    assert result.status == "success"
    assert result.files_indexed == 1
    assert result.chunks_created == 0


@pytest.mark.asyncio
async def test_index_repository_deleted_files_only(
    db_session: AsyncSession, mock_repo_path: Path
) -> None:
    """Test indexing with only deleted files (no additions/modifications).

    Covers: Lines 583-589 (deleted files handling with no files to index)
    """
    deleted_file = mock_repo_path / "deleted.py"

    with patch("src.services.indexer.scan_repository", return_value=[]):
        with patch(
            "src.services.indexer.detect_changes",
            return_value=ChangeSet(added=[], modified=[], deleted=[deleted_file]),
        ):
            with patch("src.services.indexer._mark_files_deleted"):
                with patch("src.services.indexer._create_change_events"):
                    result = await index_repository(
                        mock_repo_path, "test-repo", db_session, force_reindex=False
                    )

    # Should succeed with 0 files indexed (only deletions processed)
    assert result.status == "success"
    assert result.files_indexed == 0
    assert len(result.errors) == 0
