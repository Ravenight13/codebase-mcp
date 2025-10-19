"""Unit tests for background indexing worker.

Tests worker's error handling and status reporting without requiring database.
Uses mocks to isolate worker logic from dependencies.
"""

import pytest
import re
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
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


@pytest.mark.asyncio
async def test_generate_database_suggestion_with_available_databases():
    """Test database suggestion with available alternatives."""
    from src.services.background_worker import generate_database_suggestion

    error_msg = 'database "cb_proj_missing_db" does not exist'
    available_dbs = ["cb_proj_default_00000000", "cb_proj_test_abc123"]

    with patch("src.services.background_worker.get_available_databases", new=AsyncMock(return_value=available_dbs)):
        result = await generate_database_suggestion(error_msg, "missing-project")

    # Verify the enhanced error message contains all expected elements
    assert "cb_proj_missing_db" in result, "Must mention the missing database name"
    assert "Available databases:" in result, "Must list available databases"
    assert "cb_proj_default_00000000" in result, "Must include first available database"
    assert "cb_proj_test_abc123" in result, "Must include second available database"
    assert "Update .codebase-mcp/config.json" in result, "Must suggest config update"
    assert "remove the 'id' field" in result, "Must suggest auto-creation"
    assert "createdb" in result, "Must suggest manual database creation"


@pytest.mark.asyncio
async def test_generate_database_suggestion_no_databases():
    """Test database suggestion when no databases exist."""
    from src.services.background_worker import generate_database_suggestion

    error_msg = 'database "cb_proj_first_db" does not exist'

    with patch("src.services.background_worker.get_available_databases", new=AsyncMock(return_value=[])):
        result = await generate_database_suggestion(error_msg, "first-project")

    # Verify the message for first-time setup
    assert "cb_proj_first_db" in result, "Must mention the missing database name"
    assert "No codebase-mcp databases found" in result, "Must indicate this is the first project"
    assert "first project" in result, "Must suggest this is the first project"
    assert "remove the 'id' field" in result, "Must suggest auto-creation"


@pytest.mark.asyncio
async def test_generate_database_suggestion_non_matching_error():
    """Test database suggestion with non-matching error format."""
    from src.services.background_worker import generate_database_suggestion

    error_msg = "Some other database error"

    with patch("src.services.background_worker.get_available_databases", new=AsyncMock(return_value=[])):
        result = await generate_database_suggestion(error_msg, None)

    # Should return original error unchanged
    assert result == error_msg, "Non-matching error should be returned unchanged"


@pytest.mark.asyncio
async def test_worker_enhances_database_error():
    """Test that worker enhances database existence errors."""
    from src.services.background_worker import _background_indexing_worker

    job_id = uuid4()

    # Simulate database connection error
    db_error = Exception('connection failed: database "cb_proj_test" does not exist')

    with patch("src.services.background_worker.get_session", side_effect=db_error):
        with patch("src.services.background_worker.update_job", new=AsyncMock()) as mock_update:
            with patch("src.services.background_worker.get_available_databases",
                      new=AsyncMock(return_value=["cb_proj_default_00000000"])):
                with patch("src.services.background_worker.Path") as mock_path:
                    mock_path.return_value.exists.return_value = True
                    mock_path.return_value.is_dir.return_value = True

                    await _background_indexing_worker(
                        job_id=job_id,
                        repo_path="/tmp/test-repo",
                        project_id="test-project",
                    )

    # Verify enhanced error message was used
    calls = [call.kwargs for call in mock_update.call_args_list]
    final_update = calls[-1]

    assert final_update["status"] == "failed", "Job must be marked as failed"
    error_msg = final_update.get("error_message", "")
    assert "Available databases:" in error_msg, "Error message must include available databases"
    assert "cb_proj_default_00000000" in error_msg, "Error message must list available database"
    assert "config.json" in error_msg, "Error message must mention config file"
