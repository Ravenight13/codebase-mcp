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

from src.connection_pool.exceptions import (
    ConnectionValidationError,
    PoolClosedError,
    PoolTimeoutError,
)
from src.database import get_session_factory
from src.database.session import get_session, resolve_project_id
from src.mcp.errors import MCPError
from src.mcp.mcp_logging import get_logger
from src.mcp.server_fastmcp import get_pool_manager, mcp
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

    Multi-Project Isolation:
        Uses schema-based isolation within a shared database connection pool.
        Each project has a dedicated PostgreSQL schema (e.g., "project_myapp").

    Args:
        repo_path: Absolute path to repository directory (required)
        project_id: Optional project identifier for workspace isolation.
                   If None, uses 4-tier resolution chain:
                   1. Session-based config (via set_working_directory + .codebase-mcp/config.json)
                   2. workflow-mcp integration (active project query)
                   3. CODEBASE_MCP_PROJECT_ID environment variable
                   4. Default project workspace (project_default schema)
        force_reindex: Force full re-index even if already indexed (default: False)
        ctx: FastMCP context for session-based config resolution and progress reporting (optional)

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

    Config-Based Auto-Switching:
        When ctx is provided, the tool automatically discovers project configuration:
        1. Retrieves working directory from session context (ctx.session_id)
        2. Searches for .codebase-mcp/config.json (up to 20 parent directories)
        3. Caches config with mtime-based invalidation (<1ms cached lookups)
        4. Uses project.name or project.id from config
        5. Falls back to workflow-mcp or default workspace if config not found

    Example:
        >>> # Set working directory once per session
        >>> await set_working_directory("/Users/alice/my-project", ctx=ctx)

        >>> # All subsequent calls auto-resolve project from config
        >>> result = await index_repository(
        ...     repo_path="/Users/alice/my-project",
        ...     ctx=ctx  # Uses .codebase-mcp/config.json automatically
        ... )
    """
    # Context logging (to MCP client)
    if ctx:
        await ctx.info(f"Indexing repository: {repo_path}")

    # 1. Resolve project_id (with 4-tier resolution chain)
    resolved_id = await resolve_project_id(explicit_id=project_id, ctx=ctx)

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
    pool_info: dict[str, Any]  # Declare once for all exception handlers
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

    except PoolTimeoutError as e:
        # Connection pool timeout - provide actionable error with pool statistics
        try:
            pool_manager = get_pool_manager()
            stats = pool_manager.get_statistics()
            pool_info = {
                "total_connections": stats.total_connections,
                "idle_connections": stats.idle_connections,
                "active_connections": stats.active_connections,
                "waiting_requests": stats.waiting_requests,
                "peak_active": stats.peak_active_connections,
            }
        except Exception:
            pool_info = {"error": "Unable to retrieve pool statistics"}

        logger.error(
            "Connection pool timeout during indexing",
            extra={
                "context": {
                    "repo_path": repo_path,
                    "name": name,
                    "error": str(e),
                    "pool_statistics": pool_info,
                }
            },
        )
        if ctx:
            await ctx.error(
                f"Database connection pool exhausted. "
                f"Try: Increase POOL_MAX_SIZE or wait for connections to become available."
            )
        raise MCPError(
            message=f"Connection pool timeout during indexing: {str(e)}",
            code="DATABASE_ERROR",
            details={
                "error_type": "PoolTimeoutError",
                "pool_statistics": pool_info,
                "suggestion": "Try: Increase POOL_MAX_SIZE environment variable or reduce concurrent operations",
            },
        ) from e

    except ConnectionValidationError as e:
        # Connection validation failed - database connection issue
        try:
            pool_manager = get_pool_manager()
            stats = pool_manager.get_statistics()
            pool_info = {
                "total_connections": stats.total_connections,
                "idle_connections": stats.idle_connections,
                "active_connections": stats.active_connections,
                "last_error": stats.last_error,
            }
        except Exception:
            pool_info = {"error": "Unable to retrieve pool statistics"}

        logger.error(
            "Connection validation failed during indexing",
            extra={
                "context": {
                    "repo_path": repo_path,
                    "name": name,
                    "error": str(e),
                    "pool_statistics": pool_info,
                }
            },
        )
        if ctx:
            await ctx.error(
                f"Database connection validation failed. "
                f"Try: Check database connectivity and restart server."
            )
        raise MCPError(
            message=f"Database connection validation failed during indexing: {str(e)}",
            code="DATABASE_ERROR",
            details={
                "error_type": "ConnectionValidationError",
                "pool_statistics": pool_info,
                "suggestion": "Try: Check PostgreSQL is running and network connectivity is available",
            },
        ) from e

    except PoolClosedError as e:
        # Pool is closed - server shutdown or lifecycle issue
        try:
            pool_manager = get_pool_manager()
            stats = pool_manager.get_statistics()
            pool_info = {
                "total_connections": stats.total_connections,
                "idle_connections": stats.idle_connections,
            }
        except Exception:
            pool_info = {"error": "Pool closed or unavailable"}

        logger.error(
            "Connection pool closed during indexing",
            extra={
                "context": {
                    "repo_path": repo_path,
                    "name": name,
                    "error": str(e),
                    "pool_statistics": pool_info,
                }
            },
        )
        if ctx:
            await ctx.error(
                f"Database connection pool is closed. "
                f"Try: Restart the server or check server lifecycle."
            )
        raise MCPError(
            message=f"Connection pool closed during indexing: {str(e)}",
            code="DATABASE_ERROR",
            details={
                "error_type": "PoolClosedError",
                "pool_statistics": pool_info,
                "suggestion": "Try: Restart the MCP server to reinitialize the connection pool",
            },
        ) from e

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
