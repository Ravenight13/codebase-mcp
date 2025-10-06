"""MCP tool handler for semantic code search.

Provides the search_code tool for MCP clients to perform semantic code search
using pgvector similarity matching.

Constitutional Compliance:
- Principle III: Protocol Compliance (MCP-compliant responses)
- Principle IV: Performance (<500ms p95 latency target)
- Principle V: Production Quality (comprehensive validation, error handling)
- Principle VIII: Type Safety (mypy --strict compliance)
"""

from __future__ import annotations

import time
from typing import Any
from uuid import UUID

from pydantic import Field, ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.mcp.mcp_logging import get_logger
from src.mcp.server import ValidationError as MCPValidationError
from src.services import SearchFilter, SearchResult, search_code

# ==============================================================================
# Constants
# ==============================================================================

logger = get_logger(__name__)

# ==============================================================================
# Tool Implementation
# ==============================================================================


async def search_code_tool(
    db: AsyncSession,
    query: str,
    repository_id: str | None = None,
    file_type: str | None = None,
    directory: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Semantic code search across indexed repositories.

    MCP tool handler that performs semantic search using embeddings and pgvector
    similarity matching.

    Args:
        query: Natural language search query (required)
        db: Async database session (injected by dependency)
        repository_id: Optional UUID string to filter by repository
        file_type: Optional file extension filter (e.g., "py", "js")
        directory: Optional directory path filter (supports wildcards)
        limit: Maximum number of results (1-50, default: 10)

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
        MCPValidationError: If input validation fails
        Exception: If search operation fails

    Performance:
        Target: <500ms p95 latency (includes embedding generation and search)
    """
    start_time = time.perf_counter()

    logger.info(
        "search_code tool called",
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
            raise MCPValidationError(
                "Search query cannot be empty",
                details={"parameter": "query", "value": query},
            )

        # Validate limit
        if limit < 1 or limit > 50:
            raise MCPValidationError(
                f"Limit must be between 1 and 50, got {limit}",
                details={"parameter": "limit", "value": limit, "min": 1, "max": 50},
            )

        # Validate repository_id format (UUID)
        repo_uuid: UUID | None = None
        if repository_id is not None:
            try:
                repo_uuid = UUID(repository_id)
            except (ValueError, AttributeError) as e:
                raise MCPValidationError(
                    f"Invalid repository_id format: {repository_id}",
                    details={
                        "parameter": "repository_id",
                        "value": repository_id,
                        "expected_format": "UUID",
                        "error": str(e),
                    },
                ) from e

        # Validate file_type (no leading dot)
        if file_type is not None and file_type.startswith("."):
            raise MCPValidationError(
                "file_type should not include leading dot (use 'py' not '.py')",
                details={
                    "parameter": "file_type",
                    "value": file_type,
                    "expected_format": "extension without dot",
                },
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
            raise MCPValidationError(
                f"Invalid search filters: {e}",
                details={"validation_errors": e.errors()},
            ) from e

    except MCPValidationError:
        # Re-raise MCP validation errors
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
        raise MCPValidationError(
            f"Input validation failed: {e}",
            details={"error": str(e)},
        ) from e

    # Perform semantic search
    try:
        results: list[SearchResult] = await search_code(query, db, filters)
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
        raise  # Let FastAPI handle the error response

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

    return response


# ==============================================================================
# Module Exports
# ==============================================================================

__all__ = ["search_code_tool"]
