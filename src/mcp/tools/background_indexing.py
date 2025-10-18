"""Background indexing MCP tools for non-blocking repository indexing.

This module provides MCP tools for starting background indexing jobs and
querying their status. Jobs are stored in PostgreSQL and processed by an
async worker that runs in the background.

Constitutional Compliance:
- Principle I: Simplicity (reuses existing indexer, minimal new code)
- Principle IV: Performance (non-blocking, <1s response time)
- Principle V: Production Quality (validation, error handling, logging)
- Principle VIII: Type Safety (full type hints, mypy --strict)
- Principle XI: FastMCP Foundation (@mcp.tool() decorator)

MCP Tool Responsibilities:
- start_indexing_background(): Create job record, spawn worker
- get_indexing_status(): Query job status from database

Worker Responsibilities (in background_worker.py):
- Update job status through state machine
- Call existing index_repository service
- Capture errors and update job status
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from uuid import UUID

from fastmcp import Context

from src.database.session import get_session, resolve_project_id, engine
from sqlalchemy.ext.asyncio import AsyncSession
from src.mcp.mcp_logging import get_logger
from src.mcp.server_fastmcp import mcp
from src.models.indexing_job import IndexingJob, IndexingJobCreate
from src.services.background_worker import _background_indexing_worker

logger = get_logger(__name__)


@mcp.tool()
async def start_indexing_background(
    repo_path: str,
    project_id: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Start repository indexing in the background (non-blocking).

    Returns immediately with job_id. Use get_indexing_status(job_id) to poll progress.

    Args:
        repo_path: Absolute path to repository (validated for path traversal)
        project_id: Optional project identifier (resolved via 4-tier chain)
        ctx: FastMCP Context for session-based project resolution

    Returns:
        {
            "job_id": "uuid",
            "status": "pending",
            "message": "Indexing job started",
            "project_id": "resolved_project_id",
            "database_name": "cb_proj_xxx"
        }

    Raises:
        ValueError: If repo_path validation fails (path traversal, not absolute)

    Constitutional Compliance:
        - Principle IV: Performance (non-blocking, <1s response)
        - Principle V: Production Quality (path validation, error handling)
        - Principle XI: FastMCP Foundation (@mcp.tool() decorator)

    Example:
        >>> result = await start_indexing_background(
        ...     repo_path="/Users/alice/projects/myapp",
        ...     ctx=ctx
        ... )
        >>> job_id = result["job_id"]
        >>> # Poll status:
        >>> status = await get_indexing_status(job_id=job_id)
    """
    # Resolve project_id via 4-tier chain
    resolved_id, database_name = await resolve_project_id(
        explicit_id=project_id,
        ctx=ctx,
    )

    # Bug 2 Fix: Capture config path while ctx is valid (before background task)
    # FastMCP Context objects are request-scoped and become stale in background workers.
    # We capture the config file path here (while ctx is valid) and pass it to the worker.
    config_path: Path | None = None
    if ctx:
        try:
            from src.auto_switch.discovery import find_config_file
            from src.auto_switch.session_context import get_session_context_manager

            working_dir = await get_session_context_manager().get_working_directory(ctx.session_id)
            if working_dir:
                config_path = find_config_file(Path(working_dir))
        except Exception:
            pass  # Fallback to config_path=None

    # Validate input (includes path traversal check)
    # This will raise ValueError if validation fails
    job_input = IndexingJobCreate(
        repo_path=repo_path,
        project_id=resolved_id,
    )

    # Create job record in main database (status=pending)
    # Note: indexing_jobs table lives in main codebase_mcp database, not project databases
    async with AsyncSession(engine) as session:
        job = IndexingJob(
            repo_path=job_input.repo_path,
            project_id=resolved_id,
            status="pending",
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        job_id = job.id

    # Start background worker (non-blocking)
    asyncio.create_task(
        _background_indexing_worker(
            job_id=job_id,
            repo_path=job_input.repo_path,
            project_id=resolved_id,
            config_path=config_path,  # Pass config path, not ctx (Bug 2 fix)
        )
    )

    logger.info(
        f"Indexing job created: {job_id}",
        extra={
            "context": {
                "job_id": str(job_id),
                "project_id": resolved_id,
                "repo_path": job_input.repo_path,
            }
        },
    )

    if ctx:
        await ctx.info(f"Indexing started in background. Job ID: {job_id}")

    return {
        "job_id": str(job_id),
        "status": "pending",
        "message": "Indexing job started",
        "project_id": resolved_id,
        "database_name": database_name,
    }


@mcp.tool()
async def get_indexing_status(
    job_id: str,
    project_id: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Get status of a background indexing job.

    Queries PostgreSQL for current job state. Read-only operation for polling.

    Args:
        job_id: UUID of the indexing job
        project_id: Optional project identifier (resolved via 4-tier chain)
        ctx: FastMCP Context for session-based project resolution

    Returns:
        {
            "job_id": "uuid",
            "status": "running",  # pending/running/completed/failed
            "repo_path": "/path/to/repo",
            "files_indexed": 5000,
            "chunks_created": 45000,
            "error_message": null,
            "created_at": "2025-10-17T10:30:00Z",
            "started_at": "2025-10-17T10:30:01Z",
            "completed_at": null
        }

    Raises:
        ValueError: If job_id is invalid or not found

    Constitutional Compliance:
        - Principle IV: Performance (fast query, <50ms typical)
        - Principle V: Production Quality (UUID validation, error handling)
        - Principle XI: FastMCP Foundation (@mcp.tool() decorator)

    Example:
        >>> status = await get_indexing_status(job_id="550e8400-...")
        >>> if status["status"] == "completed":
        ...     print(f"Indexed {status['files_indexed']} files!")
    """
    # Resolve project_id
    resolved_id, _ = await resolve_project_id(
        explicit_id=project_id,
        ctx=ctx,
    )

    # Validate UUID format
    try:
        job_uuid = UUID(job_id)
    except ValueError as e:
        logger.warning(
            f"Invalid job_id format: {job_id}",
            extra={
                "context": {
                    "operation": "get_indexing_status",
                    "job_id": job_id,
                    "error": str(e),
                }
            },
        )
        raise ValueError(f"Invalid job_id format: {job_id}") from e

    # Query job from main database
    # Note: indexing_jobs table lives in main codebase_mcp database, not project databases
    async with AsyncSession(engine) as session:
        job = await session.get(IndexingJob, job_uuid)

        if job is None:
            logger.warning(
                f"Job not found: {job_id}",
                extra={
                    "context": {
                        "operation": "get_indexing_status",
                        "job_id": job_id,
                        "project_id": resolved_id,
                    }
                },
            )
            raise ValueError(f"Job not found: {job_id}")

        # Convert to dict
        return {
            "job_id": str(job.id),
            "status": job.status,
            "repo_path": job.repo_path,
            "project_id": job.project_id,
            "files_indexed": job.files_indexed,
            "chunks_created": job.chunks_created,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }


__all__ = [
    "start_indexing_background",
    "get_indexing_status",
]
