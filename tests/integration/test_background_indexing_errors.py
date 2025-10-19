"""Integration tests for background indexing error scenarios.

End-to-end tests that verify error status reporting with real database operations.
These tests validate the fix for Bug 3 using actual PostgreSQL.
"""

import asyncio
import pytest
from pathlib import Path
from uuid import UUID, uuid4
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.background_worker import _background_indexing_worker
from src.services.indexer import IndexResult
from src.database.session import engine
from src.models.indexing_job import IndexingJob


@pytest.mark.integration
@pytest.mark.asyncio
async def test_background_indexing_database_not_found():
    """Job status='failed' when indexing returns failed status.

    This is the end-to-end test for Bug 3:
    1. Create job in registry database
    2. Mock index_repository to return IndexResult(status="failed")
    3. Worker must update job status to "failed" (not "completed")
    4. Worker must populate error_message field

    Before fix: status="completed", error_message=NULL, files_indexed=0
    After fix: status="failed", error_message="Database error...", files_indexed=0
    """
    job_id = uuid4()
    fake_project_id = f"test-project-{uuid4().hex[:8]}"
    test_repo_path = "/tmp/test-repo-integration-errors"

    # Create test repository directory
    Path(test_repo_path).mkdir(parents=True, exist_ok=True)
    (Path(test_repo_path) / "test.py").write_text("# test file")

    try:
        # Create job in registry database
        async with AsyncSession(engine) as session:
            job = IndexingJob(
                id=job_id,
                repo_path=test_repo_path,
                project_id=fake_project_id,
                status="pending",
            )
            session.add(job)
            await session.commit()

        # Mock index_repository to return failed result (simulating database error)
        failed_result = IndexResult(
            repository_id=UUID("00000000-0000-0000-0000-000000000000"),
            files_indexed=0,
            chunks_created=0,
            duration_seconds=1.0,
            status="failed",
            errors=["Critical error during indexing: database does not exist"],
        )

        with patch("src.services.background_worker.index_repository", new=AsyncMock(return_value=failed_result)):
            # Run worker - will receive failed result from mocked indexer
            await _background_indexing_worker(
                job_id=job_id,
                repo_path=test_repo_path,
                project_id=fake_project_id,
            )

        # Wait for async worker to complete
        await asyncio.sleep(0.5)

        # Verify job status is "failed" (not "completed")
        async with AsyncSession(engine) as session:
            updated_job = await session.get(IndexingJob, job_id)

            assert updated_job is not None, "Job must exist in registry"
            assert updated_job.status == "failed", \
                f"Expected status='failed' when IndexResult.status='failed', got '{updated_job.status}'"
            assert updated_job.error_message is not None, \
                "error_message must be populated when indexing fails"
            assert len(updated_job.error_message) > 0, \
                f"Error message should not be empty, got: {updated_job.error_message}"
            assert updated_job.files_indexed == 0, \
                "files_indexed must be 0 when indexing fails"
            assert updated_job.chunks_created == 0, \
                "chunks_created must be 0 when indexing fails"

    finally:
        # Cleanup: remove test job and directory
        try:
            async with AsyncSession(engine) as session:
                job = await session.get(IndexingJob, job_id)
                if job:
                    await session.delete(job)
                    await session.commit()
        except Exception:
            pass

        try:
            import shutil
            shutil.rmtree(test_repo_path, ignore_errors=True)
        except Exception:
            pass
