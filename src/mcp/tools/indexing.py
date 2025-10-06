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

from src.mcp.mcp_logging import get_logger
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
    db: AsyncSession,
    repo_path: str,
    force_reindex: bool = False,
) -> dict[str, Any]:
    """Index a code repository for semantic search.

    MCP tool handler that orchestrates the complete repository indexing workflow:
    scanning, chunking, embedding generation, and storage.

    Args:
        db: Async database session (injected by dependency)
        repo_path: Absolute path to repository directory (required)
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
    # Derive name from directory name
    path_obj = Path(repo_path)
    name = path_obj.name or "repository"
    
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
    try:
        # Validate path
        if not repo_path or not repo_path.strip():
            raise MCPValidationError(
                "Repository path cannot be empty",
                details={"parameter": "repo_path", "value": repo_path},
            )

        path_obj = Path(repo_path)

        # Check if path is absolute
        if not path_obj.is_absolute():
            raise MCPValidationError(
                f"Repository path must be absolute: {repo_path}",
                details={
                    "parameter": "repo_path",
                    "value": repo_path,
                    "expected": "absolute path",
                },
            )

        # Check if path exists
        if not path_obj.exists():
            raise MCPValidationError(
                f"Repository path does not exist: {repo_path}",
                details={
                    "parameter": "repo_path",
                    "value": repo_path,
                    "error": "path not found",
                },
            )

        # Check if path is a directory
        if not path_obj.is_dir():
            raise MCPValidationError(
                f"Repository path must be a directory: {repo_path}",
                details={
                    "parameter": "repo_path",
                    "value": repo_path,
                    "error": "not a directory",
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
                    "repo_path": repo_path,
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
            repo_path=path_obj,
            name=name,
            db=db,
            force_reindex=force_reindex,
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
        raise OperationError(
            f"Failed to index repository: {e}",
            details={
                "repo_path": repo_path,
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
