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

import re
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from fastmcp import Context

from src.database.session import get_session, engine
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.mcp.mcp_logging import get_logger
from src.models.indexing_job import IndexingJob
from src.models.code_file import CodeFile
from src.models.repository import Repository
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


async def get_available_databases(prefix: str = "cb_proj_") -> list[str]:
    """Query PostgreSQL for available databases matching prefix.

    Args:
        prefix: Database name prefix to search for (default: cb_proj_)

    Returns:
        List of database names matching the prefix, sorted alphabetically

    Example:
        >>> databases = await get_available_databases()
        >>> print(databases)
        ['cb_proj_client_a_abc123de', 'cb_proj_default_00000000']
    """
    from src.database.session import _initialize_registry_pool

    try:
        registry_pool = await _initialize_registry_pool()
        async with registry_pool.acquire() as conn:
            databases = await conn.fetch(
                "SELECT datname FROM pg_database WHERE datname LIKE $1 ORDER BY datname",
                f"{prefix}%"
            )
            return [db['datname'] for db in databases]
    except Exception as e:
        logger.debug(f"Could not query available databases: {e}")
        return []


async def generate_database_suggestion(error_message: str, project_id: str | None) -> str:
    """Generate helpful error message with database suggestions.

    Parses database connection errors to extract the missing database name
    and provides actionable suggestions including available alternatives.

    Args:
        error_message: Original database error message
        project_id: Project ID that was attempted (if any)

    Returns:
        Enhanced error message with actionable suggestions

    Example:
        >>> error = 'database "cb_proj_test" does not exist'
        >>> suggestion = await generate_database_suggestion(error, "test-project")
        >>> print(suggestion)
        ❌ Database 'cb_proj_test' does not exist.

        📋 Available databases:
          • cb_proj_default_00000000

        🔧 Recommended actions:
        1. Update .codebase-mcp/config.json with a valid database name
        ...
    """
    # Extract database name from error (e.g., "database \"cb_proj_xxx\" does not exist")
    db_match = re.search(r'database "([^"]+)" does not exist', error_message)
    if not db_match:
        return error_message  # Can't enhance, return original

    missing_db = db_match.group(1)

    # Get available databases
    available_dbs = await get_available_databases()

    # Build enhanced error message
    msg = f"❌ Database '{missing_db}' does not exist.\n\n"

    if available_dbs:
        msg += "📋 Available databases:\n"
        for db in available_dbs:
            msg += f"  • {db}\n"
        msg += "\n"
    else:
        msg += "⚠️  No codebase-mcp databases found. This may be the first project.\n\n"

    msg += "🔧 Recommended actions:\n"
    msg += "1. Update .codebase-mcp/config.json with a valid database name\n"
    if available_dbs:
        msg += f"   Example: Use database '{available_dbs[0]}' if it matches your project\n"
    msg += "2. Or, remove the 'id' field from config to auto-create a new database\n"
    msg += "3. Or, create the database manually: createdb " + missing_db + "\n"

    return msg


async def _background_indexing_worker(
    job_id: UUID,
    repo_path: str,
    project_id: str,
    config_path: Path | None = None,
    force_reindex: bool = False,
) -> None:
    """Background worker that executes indexing and updates PostgreSQL.

    Simple state machine: pending → running → completed/failed
    No progress callbacks - binary state only.

    Args:
        job_id: UUID of indexing_jobs row
        repo_path: Absolute path to repository
        project_id: Resolved project identifier
        config_path: Optional path to .codebase-mcp/config.json for auto-creation
                     If provided, worker will attempt to auto-create project database.
                     If None, worker uses existing database or default database.
        force_reindex: If True, re-index all files regardless of changes (default: False)

    Bug Fix:
        Resolves Bug 2 - Background indexing auto-creation failure.
        Previously passed FastMCP Context which becomes stale in background task.
        Now captures config path in foreground (while ctx valid) and passes path.

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
        extra={
            "context": {
                "job_id": str(job_id),
                "project_id": project_id,
                "force_reindex": force_reindex,
            }
        },
    )

    try:
        # 1. Update status to running
        await update_job(
            job_id=job_id,
            status="running",
            started_at=datetime.now(),
        )

        # 1.5. Auto-create project database if config provided (Bug 2 fix)
        if config_path:
            try:
                from src.database.auto_create import get_or_create_project_from_config
                await get_or_create_project_from_config(config_path)
                logger.debug(f"Auto-created/verified database from {config_path}")
            except Exception as e:
                logger.warning(f"Auto-creation failed: {e}, attempting indexing anyway")
                # Continue - database might exist, or get_session will fail below

        # 2. Run existing indexer (NO MODIFICATIONS to indexer.py!)
        async with get_session(project_id=project_id, ctx=None) as session:
            result = await index_repository(
                repo_path=Path(repo_path),
                name=Path(repo_path).name,
                db=session,
                project_id=project_id,
                force_reindex=force_reindex,
            )

        # 3. Check if indexing succeeded by inspecting result.status
        if result.status == "failed":
            # Indexer reported failure - extract error message
            error_message = result.errors[0] if result.errors else "Unknown indexing error"

            logger.error(
                f"Indexing failed for job {job_id}",
                extra={
                    "context": {
                        "job_id": str(job_id),
                        "error": error_message,
                        "errors_count": len(result.errors),
                    }
                },
            )

            await update_job(
                job_id=job_id,
                status="failed",
                error_message=error_message,
                completed_at=datetime.now(),
            )
            return  # Exit early - do not proceed to "completed" update

        # 4. Path validation (defensive checks - should never fail after successful indexing)
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            # Path doesn't exist - mark as failed
            raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

        if not repo_path_obj.is_dir():
            # Path is not a directory - mark as failed
            raise NotADirectoryError(f"Repository path is not a directory: {repo_path}")

        # 5. Determine indexing scenario and set appropriate status message
        status_message = ""

        # Query database to determine if this was incremental or full index
        async with AsyncSession(engine) as session:
            # Count total non-deleted files in database for this repository
            count_result = await session.execute(
                select(func.count(CodeFile.id)).where(
                    CodeFile.repository_id == result.repository_id,
                    CodeFile.is_deleted == False  # noqa: E712
                )
            )
            total_files_in_db = count_result.scalar() or 0

            # Determine scenario based on force_reindex flag, files_indexed count, and total files
            if force_reindex:
                # Force reindex mode - all files re-indexed regardless of changes
                status_message = f"Force reindex completed: {result.files_indexed} files, {result.chunks_created} chunks"
            elif result.files_indexed == 0:
                # No changes detected (incremental with no modifications)
                status_message = f"Repository up to date - no file changes detected since last index ({total_files_in_db} files already indexed)"
            elif total_files_in_db == result.files_indexed:
                # Full index of new repository (all files in DB equal files just indexed)
                status_message = f"Full repository index completed: {result.files_indexed} files, {result.chunks_created} chunks"
            else:
                # Incremental update - some files changed
                status_message = f"Incremental update completed: {result.files_indexed} files updated"

        # 6. Update to completed with results and status message
        await update_job(
            job_id=job_id,
            status="completed",
            files_indexed=result.files_indexed,
            chunks_created=result.chunks_created,
            status_message=status_message,
            completed_at=datetime.now(),
        )

        logger.info(
            f"Job {job_id} completed successfully",
            extra={
                "context": {
                    "job_id": str(job_id),
                    "files_indexed": result.files_indexed,
                    "chunks_created": result.chunks_created,
                    "status_message": status_message,
                    "force_reindex": force_reindex,
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
        error_str = str(e)

        # Check if this is a database existence error and enhance the message
        if "database" in error_str.lower() and "does not exist" in error_str.lower():
            error_message = await generate_database_suggestion(error_str, project_id)
        else:
            error_message = error_str

        logger.error(
            f"Unexpected error in job {job_id}",
            extra={
                "context": {
                    "job_id": str(job_id),
                    "repo_path": repo_path,
                    "project_id": project_id,
                    "error": error_message,
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
                error_message=error_message,  # Use enhanced message
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
    "get_available_databases",
    "generate_database_suggestion",
]
