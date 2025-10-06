"""Semantic code search service with pgvector cosine similarity.

Provides semantic code search using Ollama embeddings and pgvector for similarity
matching. Includes context extraction (lines before/after) for richer results.

Constitutional Compliance:
- Principle IV: Performance (<500ms p95 latency, HNSW index usage)
- Principle V: Production quality (comprehensive filtering, error handling)
- Principle VIII: Type safety (full mypy --strict compliance)

Key Features:
- Query embedding generation via Ollama
- Pgvector cosine similarity search with HNSW index
- Multi-dimensional filtering (repository, file type, directory)
- Context extraction (10 lines before/after chunks)
- Configurable result limits (1-50)
- Performance monitoring and logging
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Final
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.mcp.logging import get_logger
from src.models import CodeChunk, CodeFile
from src.services.embedder import generate_embedding

# ==============================================================================
# Constants
# ==============================================================================

logger = get_logger(__name__)

# Context extraction settings
CONTEXT_LINES_BEFORE: Final[int] = 10
CONTEXT_LINES_AFTER: Final[int] = 10

# Search result limits
DEFAULT_RESULT_LIMIT: Final[int] = 10
MAX_RESULT_LIMIT: Final[int] = 50


# ==============================================================================
# Pydantic Models
# ==============================================================================


class SearchFilter(BaseModel):
    """Filters for semantic code search.

    Attributes:
        repository_id: Filter by specific repository (optional)
        file_type: Filter by file extension (e.g., "py", "ts", "rs")
        directory: Filter by directory path (supports wildcards)
        limit: Maximum number of results (1-50, default 10)

    Validation:
        - file_type: No leading dot (use "py" not ".py")
        - limit: Range [1, 50]
    """

    repository_id: UUID | None = Field(
        None, description="Repository UUID to filter by"
    )
    file_type: str | None = Field(
        None,
        min_length=1,
        max_length=20,
        description="File extension (no leading dot)",
    )
    directory: str | None = Field(
        None, min_length=1, description="Directory path filter (supports % wildcard)"
    )
    limit: int = Field(
        default=DEFAULT_RESULT_LIMIT,
        ge=1,
        le=MAX_RESULT_LIMIT,
        description="Maximum results to return",
    )

    @field_validator("file_type")
    @classmethod
    def validate_file_type(cls, v: str | None) -> str | None:
        """Ensure file type doesn't include leading dot."""
        if v is not None and v.startswith("."):
            raise ValueError("file_type should not include leading dot (use 'py' not '.py')")
        return v

    model_config = {"frozen": True}


class SearchResult(BaseModel):
    """Single search result with similarity score and context.

    Attributes:
        chunk_id: UUID of the matching code chunk
        file_path: Relative path to the file containing the chunk
        content: Chunk content (code snippet)
        start_line: Starting line number (1-indexed)
        end_line: Ending line number (1-indexed)
        similarity_score: Cosine similarity (0.0-1.0, higher = more similar)
        context_before: Lines before chunk (up to 10)
        context_after: Lines after chunk (up to 10)

    Note:
        similarity_score is computed as 1 - cosine_distance, where cosine_distance
        is from pgvector's <=> operator. Higher scores indicate greater similarity.
    """

    chunk_id: UUID
    file_path: str
    content: str
    start_line: int = Field(..., ge=1, description="Starting line (1-indexed)")
    end_line: int = Field(..., ge=1, description="Ending line (1-indexed)")
    similarity_score: float = Field(
        ..., ge=0.0, le=1.0, description="Similarity score (0-1)"
    )
    context_before: str = Field(default="", description="Lines before chunk")
    context_after: str = Field(default="", description="Lines after chunk")

    model_config = {"frozen": True}


# ==============================================================================
# Context Extraction
# ==============================================================================


async def _extract_context(
    file_path: str,
    start_line: int,
    end_line: int,
    lines_before: int = CONTEXT_LINES_BEFORE,
    lines_after: int = CONTEXT_LINES_AFTER,
) -> tuple[str, str]:
    """Extract context lines before and after a code chunk.

    Args:
        file_path: Absolute path to the source file
        start_line: Starting line of chunk (1-indexed)
        end_line: Ending line of chunk (1-indexed)
        lines_before: Number of lines to extract before chunk
        lines_after: Number of lines to extract after chunk

    Returns:
        Tuple of (context_before, context_after) as strings

    Note:
        - Returns empty strings if file cannot be read
        - Handles edge cases (start of file, end of file)
        - Line numbers are 1-indexed
    """
    try:
        path = Path(file_path)
        if not path.exists():
            logger.warning(
                "File not found for context extraction",
                extra={"context": {"file_path": file_path}},
            )
            return ("", "")

        # Read entire file (async I/O)
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(None, path.read_text, "utf-8")
        lines = content.splitlines()

        # Extract context before (line numbers are 1-indexed)
        context_start = max(0, start_line - lines_before - 1)
        context_end = max(0, start_line - 1)
        context_before_lines = lines[context_start:context_end]
        context_before = "\n".join(context_before_lines) if context_before_lines else ""

        # Extract context after
        after_start = min(len(lines), end_line)
        after_end = min(len(lines), end_line + lines_after)
        context_after_lines = lines[after_start:after_end]
        context_after = "\n".join(context_after_lines) if context_after_lines else ""

        return (context_before, context_after)

    except Exception as e:
        logger.error(
            "Failed to extract context",
            extra={
                "context": {
                    "file_path": file_path,
                    "start_line": start_line,
                    "end_line": end_line,
                    "error": str(e),
                }
            },
        )
        return ("", "")


# ==============================================================================
# Search Service
# ==============================================================================


async def search_code(
    query: str,
    db: AsyncSession,
    filters: SearchFilter | None = None,
) -> list[SearchResult]:
    """Perform semantic code search using pgvector similarity.

    Args:
        query: Natural language search query
        db: Async database session
        filters: Optional search filters (repository, file type, directory, limit)

    Returns:
        List of search results ordered by similarity (highest first)

    Raises:
        ValueError: If query is empty or filters are invalid
        OllamaError: If embedding generation fails

    Performance:
        - Target: <500ms p95 latency
        - HNSW index for fast similarity search
        - Async context extraction (parallel I/O)

    Example:
        >>> async with get_session() as db:
        ...     results = await search_code(
        ...         "authentication middleware",
        ...         db,
        ...         SearchFilter(file_type="py", limit=5)
        ...     )
        ...     for result in results:
        ...         print(f"{result.file_path}:{result.start_line} ({result.similarity_score:.2f})")
    """
    # Validate input
    if not query or not query.strip():
        raise ValueError("Search query cannot be empty")

    # Default filters
    if filters is None:
        filters = SearchFilter()

    start_time = asyncio.get_event_loop().time()

    logger.info(
        "Starting semantic code search",
        extra={
            "context": {
                "query": query,
                "repository_id": str(filters.repository_id) if filters.repository_id else None,
                "file_type": filters.file_type,
                "directory": filters.directory,
                "limit": filters.limit,
            }
        },
    )

    # Step 1: Generate query embedding
    try:
        query_embedding = await generate_embedding(query)
    except Exception as e:
        logger.error(
            "Failed to generate query embedding",
            extra={"context": {"query": query, "error": str(e)}},
        )
        raise

    embedding_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000

    # Step 2: Build similarity search query
    # Use pgvector's <=> operator for cosine distance
    # Join with code_files to get file metadata and apply filters
    stmt = (
        select(
            CodeChunk.id.label("chunk_id"),
            CodeChunk.content,
            CodeChunk.start_line,
            CodeChunk.end_line,
            CodeFile.path.label("file_path"),
            CodeFile.relative_path,
            # Cosine distance (0 = identical, 2 = opposite)
            # Convert to similarity score: 1 - distance/2 gives [0, 1] range
            (1 - CodeChunk.embedding.cosine_distance(query_embedding)).label("similarity"),
        )
        .join(CodeFile, CodeChunk.code_file_id == CodeFile.id)
        .where(CodeChunk.embedding.isnot(None))  # Only chunks with embeddings
        .where(CodeFile.is_deleted == False)  # Exclude soft-deleted files
    )

    # Apply filters
    if filters.repository_id is not None:
        stmt = stmt.where(CodeFile.repository_id == filters.repository_id)

    if filters.file_type is not None:
        # Filter by file extension (e.g., "py" matches "*.py")
        extension_pattern = f"%.{filters.file_type}"
        stmt = stmt.where(CodeFile.relative_path.like(extension_pattern))

    if filters.directory is not None:
        # Filter by directory path (support % wildcard)
        # User can pass "src/%" to match all files in src/
        directory_pattern = f"{filters.directory}%"
        stmt = stmt.where(CodeFile.relative_path.like(directory_pattern))

    # Order by similarity (ascending distance = descending similarity)
    stmt = stmt.order_by(CodeChunk.embedding.cosine_distance(query_embedding))

    # Limit results
    stmt = stmt.limit(filters.limit)

    # Execute query
    search_start = asyncio.get_event_loop().time()
    result = await db.execute(stmt)
    rows = result.fetchall()
    search_time_ms = (asyncio.get_event_loop().time() - search_start) * 1000

    logger.info(
        "Similarity search completed",
        extra={
            "context": {
                "results_count": len(rows),
                "embedding_time_ms": embedding_time_ms,
                "search_time_ms": search_time_ms,
            }
        },
    )

    # Step 3: Extract context for each result (parallel)
    context_start = asyncio.get_event_loop().time()

    async def build_result(row: tuple[UUID, str, int, int, str, str, float]) -> SearchResult:
        """Build search result with context extraction."""
        chunk_id, content, start_line, end_line, file_path, relative_path, similarity = row

        # Extract context (async I/O)
        context_before, context_after = await _extract_context(
            file_path, start_line, end_line
        )

        return SearchResult(
            chunk_id=chunk_id,
            file_path=relative_path,  # Use relative path for security
            content=content,
            start_line=start_line,
            end_line=end_line,
            similarity_score=float(similarity),
            context_before=context_before,
            context_after=context_after,
        )

    # Extract context for all results in parallel
    # Convert Row objects to tuples for type safety
    row_tuples = [
        (
            row.chunk_id,
            row.content,
            row.start_line,
            row.end_line,
            row.file_path,
            row.relative_path,
            row.similarity,
        )
        for row in rows
    ]
    results = await asyncio.gather(*[build_result(row) for row in row_tuples])

    context_time_ms = (asyncio.get_event_loop().time() - context_start) * 1000
    total_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000

    logger.info(
        "Semantic code search completed",
        extra={
            "context": {
                "query": query,
                "results_count": len(results),
                "embedding_time_ms": embedding_time_ms,
                "search_time_ms": search_time_ms,
                "context_time_ms": context_time_ms,
                "total_time_ms": total_time_ms,
            }
        },
    )

    # Performance warning if exceeds target
    if total_time_ms > 500:
        logger.warning(
            "Search latency exceeded p95 target",
            extra={
                "context": {
                    "total_time_ms": total_time_ms,
                    "target_ms": 500,
                }
            },
        )

    return results


# ==============================================================================
# Module Exports
# ==============================================================================

__all__ = [
    "SearchFilter",
    "SearchResult",
    "search_code",
]
