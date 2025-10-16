"""MCP tool handler for semantic code search.

Provides the search_code tool for MCP clients to perform semantic code search
using pgvector similarity matching.

Constitutional Compliance:
- Principle III: Protocol Compliance (MCP-compliant responses)
- Principle IV: Performance (<500ms p95 latency target)
- Principle V: Production Quality (comprehensive validation, error handling)
- Principle VIII: Type Safety (mypy --strict compliance)
- Principle XI: FastMCP Foundation (FastMCP decorator-based tool)
"""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from fastmcp import Context
from pydantic import Field, ValidationError as PydanticValidationError

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
from src.services import SearchFilter, SearchResult
from src.services.searcher import search_code as search_code_service

# ==============================================================================
# Constants
# ==============================================================================

logger = get_logger(__name__)

# ==============================================================================
# Tool Implementation
# ==============================================================================


@mcp.tool()
async def search_code(
    query: str,
    project_id: str | None = None,
    repository_id: str | None = None,
    file_type: str | None = None,
    directory: str | None = None,
    limit: int = 10,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Search codebase using semantic similarity.

    Performs semantic code search across indexed repositories using embeddings
    and pgvector similarity matching. Supports filtering by repository, file type,
    and directory with multi-project workspace isolation.

    Multi-Project Isolation:
        Uses schema-based isolation within a shared database connection pool.
        Each project has a dedicated PostgreSQL schema (e.g., "project_myapp").

    Performance target: <500ms p95 latency

    Project Resolution Priority (4-tier chain):
        1. Explicit project_id parameter (if provided)
        2. Session-based config (via set_working_directory + .codebase-mcp/config.json)
        3. workflow-mcp integration (active project query)
        4. Default project workspace (project_default schema)

    Args:
        query: Natural language search query (required)
        project_id: Optional project identifier for workspace isolation
        repository_id: Optional UUID string to filter by repository
        file_type: Optional file extension filter (e.g., "py", "js")
        directory: Optional directory path filter (supports wildcards)
        limit: Maximum number of results (1-50, default: 10)
        ctx: FastMCP context for session-based config resolution and progress reporting (optional)

    Returns:
        Dictionary with search results matching MCP contract:
        {
            "results": [
                {
                    "chunk_id": "uuid",
                    "file_path": "relative/path/to/file.py",
                    "content": "code snippet",
                    "start_line": 10,
                    "end_line": 20,
                    "similarity_score": 0.95,
                    "context_before": "lines before chunk",
                    "context_after": "lines after chunk"
                }
            ],
            "total_count": 42,
            "project_id": "client-a" or None,
            "schema_name": "project_client_a" or "project_default",
            "latency_ms": 250
        }

    Raises:
        ValueError: If input validation fails
        Exception: If search operation fails

    Performance:
        Target: <500ms p95 latency (includes embedding generation and search)

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
        >>> result = await search_code(
        ...     query="authentication logic",
        ...     ctx=ctx  # Uses .codebase-mcp/config.json automatically
        ... )
    """
    start_time = time.perf_counter()

    # Resolve project_id with workflow-mcp fallback (4-tier chain)
    resolved_project_id = await resolve_project_id(explicit_id=project_id, ctx=ctx)

    # Dual logging: Context logging for MCP client + file logging for server
    if ctx:
        await ctx.info(f"Searching for: {query[:100]}")

    logger.info(
        "search_code called",
        extra={
            "context": {
                "query": query[:100],  # Truncate for logging
                "project_id": resolved_project_id,
                "repository_id": repository_id,
                "file_type": file_type,
                "directory": directory,
                "limit": limit,
            }
        },
    )

    # Validate input parameters
    try:
        # Validate query
        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        # Validate limit
        if limit < 1 or limit > 50:
            raise ValueError(f"Limit must be between 1 and 50, got {limit}")

        # Validate project_id format if provided
        schema_name: str
        if resolved_project_id is not None:
            try:
                identifier = ProjectIdentifier(value=resolved_project_id)
                schema_name = identifier.to_schema_name()
            except PydanticValidationError as e:
                raise ValueError(f"Invalid project_id: {e}") from e
        else:
            schema_name = "project_default"

        # Validate repository_id format (UUID)
        repo_uuid: UUID | None = None
        if repository_id is not None:
            try:
                repo_uuid = UUID(repository_id)
            except (ValueError, AttributeError) as e:
                raise ValueError(
                    f"Invalid repository_id format: {repository_id}"
                ) from e

        # Validate file_type (no leading dot)
        if file_type is not None and file_type.startswith("."):
            raise ValueError(
                "file_type should not include leading dot (use 'py' not '.py')"
            )

        # Create search filters
        try:
            filters = SearchFilter(
                repository_id=repo_uuid,
                file_type=file_type,
                directory=directory,
                limit=limit,
            )
        except PydanticValidationError as e:
            raise ValueError(f"Invalid search filters: {e}") from e

    except ValueError:
        # Re-raise validation errors (FastMCP handles them automatically)
        raise
    except Exception as e:
        # Wrap unexpected validation errors
        logger.error(
            "Unexpected error during input validation",
            extra={
                "context": {
                    "query": query,
                    "error": str(e),
                }
            },
        )
        raise ValueError(f"Input validation failed: {e}") from e

    # Perform semantic search with project isolation
    pool_info: dict[str, Any]  # Declare once for all exception handlers
    try:
        async with get_session(project_id=resolved_project_id) as db:
            results: list[SearchResult] = await search_code_service(query, db, filters)

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
            "Connection pool timeout during search",
            extra={
                "context": {
                    "query": query[:100],
                    "project_id": resolved_project_id,
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
            message=f"Connection pool timeout during search: {str(e)}",
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
            "Connection validation failed during search",
            extra={
                "context": {
                    "query": query[:100],
                    "project_id": resolved_project_id,
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
            message=f"Database connection validation failed during search: {str(e)}",
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
            "Connection pool closed during search",
            extra={
                "context": {
                    "query": query[:100],
                    "project_id": resolved_project_id,
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
            message=f"Connection pool closed during search: {str(e)}",
            code="DATABASE_ERROR",
            details={
                "error_type": "PoolClosedError",
                "pool_statistics": pool_info,
                "suggestion": "Try: Restart the MCP server to reinitialize the connection pool",
            },
        ) from e

    except Exception as e:
        logger.error(
            "Search operation failed",
            extra={
                "context": {
                    "query": query[:100],
                    "project_id": resolved_project_id,
                    "repository_id": repository_id,
                    "error": str(e),
                }
            },
        )
        if ctx:
            await ctx.error(f"Search failed: {str(e)[:100]}")
        raise  # Let FastMCP handle the error response

    # Calculate latency
    latency_ms = int((time.perf_counter() - start_time) * 1000)

    # Format response according to MCP contract
    response: dict[str, Any] = {
        "results": [
            {
                "chunk_id": str(result.chunk_id),
                "file_path": result.file_path,
                "content": result.content,
                "start_line": result.start_line,
                "end_line": result.end_line,
                "similarity_score": result.similarity_score,
                "context_before": result.context_before,
                "context_after": result.context_after,
            }
            for result in results
        ],
        "total_count": len(results),
        "project_id": resolved_project_id,
        "schema_name": schema_name,
        "latency_ms": latency_ms,
    }

    logger.info(
        "search_code completed successfully",
        extra={
            "context": {
                "query": query[:100],
                "project_id": resolved_project_id,
                "schema_name": schema_name,
                "results_count": len(results),
                "latency_ms": latency_ms,
            }
        },
    )

    # Performance warning if exceeds target
    if latency_ms > 500:
        logger.warning(
            "search_code latency exceeded p95 target",
            extra={
                "context": {
                    "latency_ms": latency_ms,
                    "target_ms": 500,
                    "query": query[:100],
                }
            },
        )

    if ctx:
        await ctx.info(
            f"Found {len(results)} results in {latency_ms}ms"
        )

    return response


# ==============================================================================
# Module Exports
# ==============================================================================

__all__ = ["search_code"]
