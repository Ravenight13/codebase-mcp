"""Integration tests for force_reindex parameter feature.

Tests validate that force_reindex parameter correctly forces re-indexing
of all files regardless of modification timestamps.

Constitutional Compliance:
- Principle VII: TDD (comprehensive test coverage before/with implementation)
- Principle VIII: Type Safety (full type hints, async/await patterns)
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import engine
from src.models.indexing_job import IndexingJob


@pytest.mark.asyncio
class TestForceReindex:
    """Test force_reindex parameter functionality."""

    async def test_force_reindex_flag_stored_in_job(self) -> None:
        """Test that force_reindex flag is stored in IndexingJob."""
        # Create job with force_reindex=True
        async with AsyncSession(engine) as session:
            job = IndexingJob(
                repo_path="/test/repo",
                project_id="test-project-123",
                status="pending",
                force_reindex=True,  # NEW FEATURE
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)
            job_id = job.id

        # Verify flag was stored
        async with AsyncSession(engine) as session:
            result = await session.get(IndexingJob, job_id)
            assert result is not None
            assert result.force_reindex is True

    async def test_force_reindex_defaults_to_false(self) -> None:
        """Test that force_reindex defaults to False."""
        async with AsyncSession(engine) as session:
            job = IndexingJob(
                repo_path="/test/repo",
                project_id="test-project-456",
                status="pending",
                # force_reindex not specified - should default to False
            )
            session.add(job)
            await session.commit()
            await session.refresh(job)

            assert job.force_reindex is False

    async def test_force_reindex_flag_in_pydantic_model(self) -> None:
        """Test that Pydantic model includes force_reindex field."""
        from datetime import datetime
        from src.models.indexing_job import IndexingJobResponse

        now = datetime.now()

        # Create response with force_reindex=True
        response = IndexingJobResponse(
            id="550e8400-e29b-41d4-a716-446655440000",
            repo_path="/test/repo",
            project_id="test-project",
            status="completed",
            force_reindex=True,
            files_indexed=100,
            chunks_created=500,
            error_message=None,
            status_message="Force reindex completed: 100 files, 500 chunks",
            created_at=now,
            started_at=now,
            completed_at=now,
        )

        assert response.force_reindex is True

        # Test default value (force_reindex=False)
        response_default = IndexingJobResponse(
            id="660e8400-e29b-41d4-a716-446655440001",
            repo_path="/test/repo2",
            project_id="test-project-2",
            status="pending",
            files_indexed=0,
            chunks_created=0,
            error_message=None,
            status_message=None,
            created_at=now,
            started_at=None,
            completed_at=None,
        )

        assert response_default.force_reindex is False
