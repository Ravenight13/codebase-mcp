"""MCP tool handler for repository indexing.

Provides the index_repository tool for MCP clients to index code repositories
for semantic search.

Constitutional Compliance:
- Principle III: Protocol Compliance (MCP-compliant responses)
- Principle IV: Performance (60s target for 10K files)
- Principle V: Production Quality (comprehensive validation, error handling)
- Principle VIII: Type Safety (mypy --strict compliance)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.mcp.logging import get_logger
from src.mcp.server import OperationError, ValidationError as MCPValidationError
from src.services.indexer import IndexResult, index_repository

# ==============================================================================
# Constants
# ==============================================================================

logger = get_logger(__name__)

# ==============================================================================
# Tool Implementation
# ==============================================================================


async def index_repository_tool(
    path: str,
    name: str,
    db: AsyncSession,
    force_reindex: bool = False,
) -> dict[str, Any]:
    """Index a code repository for semantic search.

    MCP tool handler that orchestrates the complete repository indexing workflow:
    scanning, chunking, embedding generation, and storage.

    Args:
        path: Absolute path to repository directory (required)
        name: Display name for repository (required)
        db: Async database session (injected by dependency)
        force_reindex: Force full re-index even if already indexed (default: False)

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
        MCPValidationError: If input validation fails
        OperationError: If indexing operation fails critically

    Performance:
        Target: <60 seconds for 10,000 files
        Uses batching for files (100/batch) and embeddings (50/batch)
    """
    logger.info(
        "index_repository tool called",
        extra={
            "context": {
                "path": path,
                "name": name,
                "force_reindex": force_reindex,
            }
        },
    )

    # Validate input parameters
    try:
        # Validate path
        if not path or not path.strip():
            raise MCPValidationError(
                "Repository path cannot be empty",
                details={"parameter": "path", "value": path},
            )

        repo_path = Path(path)

        # Check if path is absolute
        if not repo_path.is_absolute():
            raise MCPValidationError(
                f"Repository path must be absolute: {path}",
                details={
                    "parameter": "path",
                    "value": path,
                    "expected": "absolute path",
                },
            )

        # Check if path exists
        if not repo_path.exists():
            raise MCPValidationError(
                f"Repository path does not exist: {path}",
                details={
                    "parameter": "path",
                    "value": path,
                    "error": "path not found",
                },
            )

        # Check if path is a directory
        if not repo_path.is_dir():
            raise MCPValidationError(
                f"Repository path must be a directory: {path}",
                details={
                    "parameter": "path",
                    "value": path,
                    "error": "not a directory",
                },
            )

        # Validate name
        if not name or not name.strip():
            raise MCPValidationError(
                "Repository name cannot be empty",
                details={"parameter": "name", "value": name},
            )

        # Name length validation (reasonable limit)
        if len(name) > 200:
            raise MCPValidationError(
                f"Repository name too long (max 200 characters): {len(name)}",
                details={
                    "parameter": "name",
                    "length": len(name),
                    "max_length": 200,
                },
            )

    except MCPValidationError:
        # Re-raise MCP validation errors
        raise
    except Exception as e:
        # Wrap unexpected validation errors
        logger.error(
            "Unexpected error during input validation",
            extra={
                "context": {
                    "path": path,
                    "name": name,
                    "error": str(e),
                }
            },
        )
        raise MCPValidationError(
            f"Input validation failed: {e}",
            details={"error": str(e)},
        ) from e

    # Perform indexing
    try:
        result: IndexResult = await index_repository(
            repo_path=repo_path,
            name=name,
            db=db,
            force_reindex=force_reindex,
        )
    except Exception as e:
        logger.error(
            "Indexing operation failed critically",
            extra={
                "context": {
                    "path": path,
                    "name": name,
                    "force_reindex": force_reindex,
                    "error": str(e),
                }
            },
        )
        raise OperationError(
            f"Failed to index repository: {e}",
            details={
                "path": path,
                "name": name,
                "error": str(e),
            },
        ) from e

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

__all__ = ["index_repository_tool"]
