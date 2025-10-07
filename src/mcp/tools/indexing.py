"""MCP tool handler for repository indexing.

Provides the index_repository tool for MCP clients to index code repositories
for semantic search.

Constitutional Compliance:
- Principle III: Protocol Compliance (MCP-compliant responses)
- Principle IV: Performance (60s target for 10K files)
- Principle V: Production Quality (comprehensive validation, error handling)
- Principle VIII: Type Safety (mypy --strict compliance)
- Principle XI: FastMCP Foundation (FastMCP decorator-based tool)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastmcp import Context

from src.database import SessionLocal
from src.mcp.mcp_logging import get_logger
from src.mcp.server_fastmcp import mcp, _db_init_task
from src.services.indexer import IndexResult
from src.services.indexer import index_repository as index_repository_service

# ==============================================================================
# Constants
# ==============================================================================

logger = get_logger(__name__)

# ==============================================================================
# Helper Functions
# ==============================================================================


async def _ensure_db_ready() -> None:
    """Wait for background database initialization to complete.

    FastAPI non-blocking pattern: Database initializes in background,
    first tool call waits if needed.

    Performance: Usually completes in <1 second, often already done by first call.
    """
    if _db_init_task and not _db_init_task.done():
        logger.info("Waiting for database initialization to complete...")
        await _db_init_task
        logger.info("Database initialization complete")


# ==============================================================================
# Tool Implementation
# ==============================================================================


@mcp.tool()
async def index_repository(
    repo_path: str,
    force_reindex: bool = False,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Index a code repository for semantic search.

    Orchestrates the complete repository indexing workflow: scanning,
    chunking, embedding generation, and storage in PostgreSQL with pgvector.

    Args:
        repo_path: Absolute path to repository directory (required)
        force_reindex: Force full re-index even if already indexed (default: False)
        ctx: FastMCP context for progress reporting (optional)

    Returns:
        Dictionary with indexing results matching MCP contract:
        {
            "repository_id": "uuid",
            "files_indexed": 1234,
            "chunks_created": 5678,
            "duration_seconds": 45.2,
            "status": "success",  # or "partial", "failed"
            "errors": []  # List of error messages if any
        }

    Raises:
        ValueError: If input validation fails
        RuntimeError: If indexing operation fails critically

    Performance:
        Target: <60 seconds for 10,000 files
        Uses batching for files (100/batch) and embeddings (50/batch)
    """
    # Wait for background database initialization if needed
    await _ensure_db_ready()

    # Context logging (to MCP client)
    if ctx:
        await ctx.info(f"Indexing repository: {repo_path}")

    # Derive name from directory name
    path_obj = Path(repo_path)
    name = path_obj.name or "repository"

    # File logging (to /tmp/codebase-mcp.log)
    logger.info(
        "index_repository tool called",
        extra={
            "context": {
                "repo_path": repo_path,
                "name": name,
                "force_reindex": force_reindex,
            }
        },
    )

    # Validate input parameters
    # Validate path
    if not repo_path or not repo_path.strip():
        raise ValueError("Repository path cannot be empty")

    path_obj = Path(repo_path)

    # Check if path is absolute
    if not path_obj.is_absolute():
        raise ValueError(f"Repository path must be absolute: {repo_path}")

    # Check if path exists
    if not path_obj.exists():
        raise ValueError(f"Repository path does not exist: {repo_path}")

    # Check if path is a directory
    if not path_obj.is_dir():
        raise ValueError(f"Repository path must be a directory: {repo_path}")

    # Get database session
    if SessionLocal is None:
        raise RuntimeError(
            "Database not initialized. Call init_db_connection() during startup."
        )

    # Perform indexing
    try:
        async with SessionLocal() as db:
            # Progress callback for real-time updates via Context
            async def progress_callback(message: str) -> None:
                if ctx:
                    await ctx.info(message)

            result: IndexResult = await index_repository_service(
                repo_path=path_obj,
                name=name,
                db=db,
                force_reindex=force_reindex,
            )
            await db.commit()

            # Send completion notification
            if ctx:
                await ctx.info(
                    f"Indexed {result.files_indexed} files, "
                    f"created {result.chunks_created} chunks in "
                    f"{result.duration_seconds:.1f}s"
                )

    except Exception as e:
        logger.error(
            "Indexing operation failed critically",
            extra={
                "context": {
                    "repo_path": repo_path,
                    "name": name,
                    "force_reindex": force_reindex,
                    "error": str(e),
                }
            },
        )
        if ctx:
            await ctx.error(f"Indexing failed: {str(e)[:100]}")
        raise RuntimeError(f"Failed to index repository: {e}") from e

    # Format response according to MCP contract
    response: dict[str, Any] = {
        "repository_id": str(result.repository_id),
        "files_indexed": result.files_indexed,
        "chunks_created": result.chunks_created,
        "duration_seconds": result.duration_seconds,
        "status": result.status,
    }

    # Include errors if any
    if result.errors:
        response["errors"] = result.errors

    logger.info(
        "index_repository completed",
        extra={
            "context": {
                "repository_id": str(result.repository_id),
                "files_indexed": result.files_indexed,
                "chunks_created": result.chunks_created,
                "duration_seconds": result.duration_seconds,
                "status": result.status,
                "error_count": len(result.errors),
            }
        },
    )

    # Performance warning if exceeds target (60s for 10K files)
    # Extrapolate target based on actual file count
    target_seconds = (result.files_indexed / 10000) * 60
    if result.duration_seconds > target_seconds and result.files_indexed > 100:
        logger.warning(
            "index_repository duration exceeded target",
            extra={
                "context": {
                    "duration_seconds": result.duration_seconds,
                    "target_seconds": target_seconds,
                    "files_indexed": result.files_indexed,
                }
            },
        )

    return response


# ==============================================================================
# Module Exports
# ==============================================================================

__all__ = ["index_repository"]


# Legacy export for backwards compatibility during migration
# This will be removed after all references are updated
index_repository_tool = index_repository
