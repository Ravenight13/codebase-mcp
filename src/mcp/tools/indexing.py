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
from pydantic import ValidationError

from src.database import get_session_factory
from src.database.session import get_session, resolve_project_id
from src.mcp.mcp_logging import get_logger
from src.mcp.server_fastmcp import mcp
from src.models.project_identifier import ProjectIdentifier
from src.services.indexer import IndexResult
from src.services.indexer import index_repository as index_repository_service

# ==============================================================================
# Constants
# ==============================================================================

logger = get_logger(__name__)

# ==============================================================================
# Tool Implementation
# ==============================================================================


@mcp.tool()
async def index_repository(
    repo_path: str,
    project_id: str | None = None,
    force_reindex: bool = False,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Index a code repository for semantic search.

    Orchestrates the complete repository indexing workflow: scanning,
    chunking, embedding generation, and storage in PostgreSQL with pgvector.

    Args:
        repo_path: Absolute path to repository directory (required)
        project_id: Optional project identifier for workspace isolation.
                   If None, resolves from workflow-mcp or uses default workspace.
        force_reindex: Force full re-index even if already indexed (default: False)
        ctx: FastMCP context for progress reporting (optional)

    Returns:
        Dictionary with indexing results matching MCP contract:
        {
            "repository_id": "uuid",
            "files_indexed": 1234,
            "chunks_created": 5678,
            "duration_seconds": 45.2,
            "project_id": "client-a" or None,
            "schema_name": "project_client_a" or "project_default",
            "status": "success",  # or "partial", "failed"
            "errors": []  # List of error messages if any
        }

    Raises:
        ValueError: If input validation fails (including invalid project_id format)
        RuntimeError: If indexing operation fails critically

    Performance:
        Target: <60 seconds for 10,000 files
        Uses batching for files (100/batch) and embeddings (50/batch)
    """
    # Context logging (to MCP client)
    if ctx:
        await ctx.info(f"Indexing repository: {repo_path}")

    # 1. Resolve project_id (with workflow-mcp fallback)
    resolved_id = await resolve_project_id(project_id)

    # 2. Validate project_id format if provided
    schema_name: str
    if resolved_id is not None:
        try:
            identifier = ProjectIdentifier(value=resolved_id)
            schema_name = identifier.to_schema_name()
            logger.debug(
                "Using project workspace",
                extra={
                    "context": {
                        "operation": "index_repository",
                        "project_id": resolved_id,
                        "schema_name": schema_name,
                    }
                },
            )
        except ValidationError as e:
            error_msg = f"Invalid project_id format: {e}"
            logger.error(
                "Project identifier validation failed",
                extra={
                    "context": {
                        "operation": "index_repository",
                        "project_id": resolved_id,
                        "error": str(e),
                    }
                },
            )
            raise ValueError(error_msg) from e
    else:
        schema_name = "project_default"
        logger.debug(
            "Using default workspace",
            extra={
                "context": {
                    "operation": "index_repository",
                    "schema_name": schema_name,
                }
            },
        )

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
                "project_id": resolved_id,
                "schema_name": schema_name,
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

    # Perform indexing
    try:
        # Use get_session with project_id for workspace isolation
        # This will auto-provision workspace if needed
        async with get_session(project_id=resolved_id) as db:
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
            # Note: get_session auto-commits on success, no manual commit needed

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
        "project_id": resolved_id,
        "schema_name": schema_name,
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
                "project_id": resolved_id,
                "schema_name": schema_name,
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
