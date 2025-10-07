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

from src.database import SessionLocal
from src.mcp.mcp_logging import get_logger
from src.mcp.server_fastmcp import _db_init_task, mcp
from src.services import SearchFilter, SearchResult
from src.services.searcher import search_code as search_code_service

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
async def search_code(
    query: str,
    repository_id: str | None = None,
    file_type: str | None = None,
    directory: str | None = None,
    limit: int = 10,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Search codebase using semantic similarity.

    Performs semantic code search across indexed repositories using embeddings
    and pgvector similarity matching. Supports filtering by repository, file type,
    and directory.

    Performance target: <500ms p95 latency

    Args:
        query: Natural language search query (required)
        repository_id: Optional UUID string to filter by repository
        file_type: Optional file extension filter (e.g., "py", "js")
        directory: Optional directory path filter (supports wildcards)
        limit: Maximum number of results (1-50, default: 10)
        ctx: FastMCP context for client logging (injected automatically)

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
            "latency_ms": 250
        }

    Raises:
        ValueError: If input validation fails
        Exception: If search operation fails

    Performance:
        Target: <500ms p95 latency (includes embedding generation and search)
    """
    # Wait for background database initialization if needed
    await _ensure_db_ready()

    start_time = time.perf_counter()

    # Dual logging: Context logging for MCP client + file logging for server
    if ctx:
        await ctx.info(f"Searching for: {query[:100]}")

    logger.info(
        "search_code called",
        extra={
            "context": {
                "query": query[:100],  # Truncate for logging
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

    # Get database session
    if SessionLocal is None:
        raise RuntimeError(
            "Database not initialized. Call init_db_connection() during startup."
        )

    # Perform semantic search
    try:
        async with SessionLocal() as db:
            results: list[SearchResult] = await search_code_service(query, db, filters)
            await db.commit()
    except Exception as e:
        logger.error(
            "Search operation failed",
            extra={
                "context": {
                    "query": query[:100],
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
        "latency_ms": latency_ms,
    }

    logger.info(
        "search_code completed successfully",
        extra={
            "context": {
                "query": query[:100],
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
