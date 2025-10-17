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
from typing import Any
from uuid import UUID

from fastmcp import Context

from src.database.session import get_session, engine
from sqlalchemy.ext.asyncio import AsyncSession
from src.mcp.mcp_logging import get_logger
from src.models.indexing_job import IndexingJob
from src.services.indexer import index_repository

logger = get_logger(__name__)


async def update_job(
    job_id: UUID,
    **updates: Any,
) -> None:
    """Update job fields atomically in main database.

    Args:
        job_id: UUID of indexing_jobs row
        **updates: Field names and values to update
            (e.g., status="in_progress", files_indexed=100)

    Example:
        >>> await update_job(
        ...     job_id=job_id,
        ...     status="completed",
        ...     files_indexed=1000,
        ...     completed_at=datetime.now()
        ... )
    """
    async with AsyncSession(engine) as session:
        job = await session.get(IndexingJob, job_id)
        if job is None:
            logger.warning(f"Job {job_id} not found for update")
            return

        # Apply updates
        for key, value in updates.items():
            if hasattr(job, key):
                setattr(job, key, value)
            else:
                logger.warning(f"Invalid field for job update: {key}")

        await session.commit()


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
        await update_job(
            job_id=job_id,
            status="running",
            started_at=datetime.now(),
        )

        # 2. Run existing indexer (NO MODIFICATIONS to indexer.py!)
        async with get_session(project_id=project_id, ctx=ctx) as session:
            result = await index_repository(
                repo_path=Path(repo_path),
                name=Path(repo_path).name,
                db=session,
                project_id=project_id,
            )

        # 3. Check if indexing succeeded (files_indexed > 0 or path exists check)
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            # Path doesn't exist - mark as failed
            raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

        if not repo_path_obj.is_dir():
            # Path is not a directory - mark as failed
            raise NotADirectoryError(f"Repository path is not a directory: {repo_path}")

        # 4. Update to completed with results
        await update_job(
            job_id=job_id,
            status="completed",
            files_indexed=result.files_indexed,
            chunks_created=result.chunks_created,
            completed_at=datetime.now(),
        )

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

    except FileNotFoundError as e:
        # Repository not found
        logger.error(
            f"Repository not found for job {job_id}",
            extra={"context": {"job_id": str(job_id), "repo_path": repo_path}},
        )
        await update_job(
            job_id=job_id,
            status="failed",
            error_message=f"Repository not found: {repo_path}",
            completed_at=datetime.now(),
        )

    except NotADirectoryError as e:
        # Path exists but is not a directory
        logger.error(
            f"Path is not a directory for job {job_id}",
            extra={"context": {"job_id": str(job_id), "repo_path": repo_path}},
        )
        await update_job(
            job_id=job_id,
            status="failed",
            error_message=f"Path is not a directory: {repo_path}",
            completed_at=datetime.now(),
        )

    except Exception as e:
        # Catch-all for unexpected errors
        logger.error(
            f"Unexpected error in job {job_id}",
            extra={
                "context": {
                    "job_id": str(job_id),
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            },
            exc_info=True,
        )

        # Nested try/catch for status update failures
        try:
            await update_job(
                job_id=job_id,
                status="failed",
                error_message=str(e),
                completed_at=datetime.now(),
            )
        except Exception as update_error:
            logger.error(
                f"Failed to update job {job_id} status to failed",
                extra={"context": {"error": str(update_error)}},
            )


__all__ = [
    "_background_indexing_worker",
    "update_job",
]
