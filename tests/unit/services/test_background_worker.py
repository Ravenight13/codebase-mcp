"""Unit tests for background indexing worker.

Tests worker's error handling and status reporting without requiring database.
Uses mocks to isolate worker logic from dependencies.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

from src.services.indexer import IndexResult


@pytest.mark.asyncio
async def test_worker_respects_failed_index_result():
    """Worker must check IndexResult.status and set job to failed.

    This test verifies the fix for Bug 3:
    - Worker receives IndexResult with status="failed"
    - Worker must update job status to "failed" (not "completed")
    - Worker must set error_message field with error details
    """
    from src.services.background_worker import _background_indexing_worker

    job_id = uuid4()

    # Mock index_repository to return failed result (no exception raised)
    failed_result = IndexResult(
        repository_id=UUID("00000000-0000-0000-0000-000000000000"),
        files_indexed=0,
        chunks_created=0,
        duration_seconds=1.0,
        status="failed",
        errors=["Database error: database does not exist"],
    )

    with patch("src.services.background_worker.index_repository", new=AsyncMock(return_value=failed_result)):
        with patch("src.services.background_worker.update_job", new=AsyncMock()) as mock_update:
            with patch("src.services.background_worker.get_session"):
                await _background_indexing_worker(
                    job_id=job_id,
                    repo_path="/tmp/test-repo",
                    project_id="test-project",
                )

    # Verify worker called update_job with status="failed"
    calls = [call.kwargs for call in mock_update.call_args_list]
    final_update = calls[-1]

    assert final_update["status"] == "failed", \
        "Worker must set job status to 'failed' when IndexResult.status is 'failed'"
    assert "error_message" in final_update, \
        "Worker must set error_message field"
    assert "Database error" in final_update["error_message"], \
        "Error message must contain details from IndexResult.errors"


@pytest.mark.asyncio
async def test_worker_completes_successful_indexing():
    """Regression test: Successful indexing still marks job as completed.

    Ensures the fix for Bug 3 doesn't break the success path.
    Worker receives IndexResult with status="success" and must:
    - Update job status to "completed"
    - Set files_indexed and chunks_created metrics
    - NOT set error_message field
    """
    from src.services.background_worker import _background_indexing_worker

    job_id = uuid4()

    # Mock successful indexing result
    success_result = IndexResult(
        repository_id=uuid4(),
        files_indexed=100,
        chunks_created=500,
        duration_seconds=45.0,
        status="success",
        errors=[],
    )

    with patch("src.services.background_worker.index_repository", new=AsyncMock(return_value=success_result)):
        with patch("src.services.background_worker.update_job", new=AsyncMock()) as mock_update:
            with patch("src.services.background_worker.get_session"):
                # Mock path validation
                with patch("src.services.background_worker.Path") as mock_path:
                    mock_path.return_value.exists.return_value = True
                    mock_path.return_value.is_dir.return_value = True

                    await _background_indexing_worker(
                        job_id=job_id,
                        repo_path="/tmp/test-repo",
                        project_id="test-project",
                    )

    # Verify success path unchanged
    calls = [call.kwargs for call in mock_update.call_args_list]
    final_update = calls[-1]

    assert final_update["status"] == "completed", \
        "Successful indexing must still mark job as completed"
    assert final_update["files_indexed"] == 100, \
        "Worker must preserve files_indexed metric"
    assert final_update["chunks_created"] == 500, \
        "Worker must preserve chunks_created metric"
    assert "error_message" not in final_update, \
        "Successful indexing must NOT set error_message"
