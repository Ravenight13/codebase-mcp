"""Background indexing worker for non-blocking repository indexing.

Simple state machine: pending → running → completed/failed
No progress callbacks - binary state only.

Constitutional Compliance:
- Principle I: Simplicity (reuses existing indexer, no callbacks)
- Principle V: Production Quality (error handling, logging)
- Principle VIII: Type Safety (full type hints)

Worker Responsibilities:
- Update job status through state machine
- Call existing index_repository service (NO modifications)
- Capture errors and update job status
- Use structured logging with context
- Handle all exception types gracefully

State Machine:
1. pending → running: Job starts processing
2. running → completed: Indexing succeeds
3. running → failed: Indexing encounters error

Error Handling:
- Catch ALL exceptions (never crash)
- Log errors with structured context
- Always update job status to failed
- Nested try/catch for status update failures
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastmcp import Context

from src.database.session import get_session
from src.mcp.mcp_logging import get_logger
from src.models.indexing_job import IndexingJob
from src.services.indexer import index_repository

logger = get_logger(__name__)


async def _background_indexing_worker(
    job_id: UUID,
    repo_path: str,
    project_id: str,
    ctx: Context | None = None,
) -> None:
    """Background worker that executes indexing and updates PostgreSQL.

    Simple state machine: pending → running → completed/failed
    No progress callbacks - binary state only.

    Args:
        job_id: UUID of indexing_jobs row
        repo_path: Absolute path to repository
        project_id: Resolved project identifier
        ctx: Optional FastMCP Context for session resolution

    State Transitions:
        1. Update status: pending → running (with started_at timestamp)
        2. Execute: Call index_repository service
        3. Update status: running → completed/failed (with completed_at timestamp)

    Error Handling:
        - All exceptions caught and logged
        - Job status always updated to failed on error
        - Nested try/catch prevents status update failures

    Performance:
        Worker execution time depends on repository size (60s target for 10K files)
    """
    logger.info(
        f"Background worker started for job {job_id}",
        extra={"context": {"job_id": str(job_id), "project_id": project_id}},
    )

    try:
        # 1. Update status to running
        async with get_session(project_id=project_id, ctx=ctx) as session:
            job = await session.get(IndexingJob, job_id)
            if job is None:
                logger.error(f"Job {job_id} not found")
                return

            job.status = "running"
            job.started_at = datetime.now()
            await session.commit()

        # 2. Run existing indexer (NO MODIFICATIONS to indexer.py!)
        async with get_session(project_id=project_id, ctx=ctx) as session:
            result = await index_repository(
                repo_path=Path(repo_path),
                name=Path(repo_path).name,
                db=session,
                project_id=project_id,
            )

        # 3. Update to completed with results
        async with get_session(project_id=project_id, ctx=ctx) as session:
            job = await session.get(IndexingJob, job_id)
            if job is None:
                logger.error(f"Job {job_id} not found for completion update")
                return

            job.status = "completed"
            job.completed_at = datetime.now()
            job.files_indexed = result.files_indexed
            job.chunks_created = result.chunks_created
            await session.commit()

        logger.info(
            f"Job {job_id} completed successfully",
            extra={
                "context": {
                    "job_id": str(job_id),
                    "files_indexed": result.files_indexed,
                    "chunks_created": result.chunks_created,
                }
            },
        )

    except Exception as e:
        # 4. Update to failed with error message
        logger.error(
            f"Job {job_id} failed with error",
            extra={
                "context": {
                    "job_id": str(job_id),
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            },
            exc_info=True,
        )

        try:
            async with get_session(project_id=project_id, ctx=ctx) as session:
                job = await session.get(IndexingJob, job_id)
                if job is not None:
                    job.status = "failed"
                    job.error_message = str(e)
                    job.completed_at = datetime.now()
                    await session.commit()
        except Exception as update_error:
            logger.error(
                f"Failed to update job {job_id} status to failed",
                extra={"context": {"error": str(update_error)}},
            )


__all__ = [
    "_background_indexing_worker",
]
