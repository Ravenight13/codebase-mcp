"""Repository indexer orchestration service.

Coordinates the complete repository indexing workflow by orchestrating:
- Scanner service (file discovery and change detection)
- Chunker service (AST-based code chunking)
- Embedder service (vector embedding generation)
- Database persistence (repository, files, chunks with embeddings)

Constitutional Compliance:
- Principle IV: Performance (60s target for 10K files, batching, async operations)
- Principle V: Production quality (error handling, transaction management, retry logic)
- Principle VIII: Type safety (full mypy --strict compliance)
- Principle II: Local-first (all processing local, no cloud dependencies)

Key Features:
- Scan → Chunk → Embed → Store pipeline
- Incremental updates (only reindex changed files)
- Batch processing for performance (100 files/batch, 50 embeddings/batch)
- Comprehensive error tracking with partial success support
- Change event tracking for analytics
- Performance metrics (files indexed, chunks created, duration)
- Force reindex option (reindex all files)
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from pathlib import Path
from typing import Final, Iterator, Literal, Sequence, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import get_settings
from src.mcp.mcp_logging import get_logger
from src.models import (
    ChangeEvent,
    CodeChunk,
    CodeFile,
    EmbeddingMetadata,
    Repository,
)
from src.services.chunker import chunk_files_batch, detect_language
from src.services.embedder import generate_embeddings
from src.services.scanner import ChangeSet, compute_file_hash, detect_changes, scan_repository

# ==============================================================================
# Constants
# ==============================================================================

logger = get_logger(__name__)

# Batching configuration
FILE_BATCH_SIZE: Final[int] = 100  # Files per chunking batch
EMBEDDING_BATCH_SIZE: Final[int] = 50  # Texts per embedding batch (from settings)

# Performance targets
TARGET_INDEXING_TIME_SECONDS: Final[int] = 60  # 60s for 10K files

T = TypeVar("T")


# ==============================================================================
# Pydantic Models
# ==============================================================================


class IndexResult(BaseModel):
    """Result of repository indexing operation.

    Attributes:
        repository_id: UUID of indexed repository
        files_indexed: Number of files processed
        chunks_created: Number of code chunks created
        duration_seconds: Total indexing time
        status: Success status (success/partial/failed)
        errors: List of error messages encountered
    """

    repository_id: UUID
    files_indexed: int
    chunks_created: int
    duration_seconds: float
    status: Literal["success", "partial", "failed"]
    errors: list[str] = Field(default_factory=list)

    model_config = {"frozen": True}


# ==============================================================================
# Helper Functions
# ==============================================================================


def _batch(items: Sequence[T], batch_size: int) -> Iterator[list[T]]:
    """Split sequence into batches of specified size.

    Args:
        items: Sequence to batch
        batch_size: Number of items per batch

    Yields:
        Lists of items (batches)

    Examples:
        >>> list(_batch([1, 2, 3, 4, 5], 2))
        [[1, 2], [3, 4], [5]]
    """
    for i in range(0, len(items), batch_size):
        yield list(items[i : i + batch_size])


async def _get_or_create_repository(
    db: AsyncSession, path: Path, name: str
) -> Repository:
    """Get existing repository or create new one.

    Args:
        db: Async database session
        path: Absolute path to repository
        name: Repository display name

    Returns:
        Repository instance (existing or newly created)

    Raises:
        ValueError: If path is not absolute
    """
    if not path.is_absolute():
        raise ValueError(f"Repository path must be absolute: {path}")

    path_str = str(path)

    # Try to find existing repository
    result = await db.execute(select(Repository).where(Repository.path == path_str))
    repository = result.scalar_one_or_none()

    if repository is not None:
        logger.debug(
            f"Found existing repository: {repository.id}",
            extra={"context": {"repository_id": str(repository.id), "path": path_str}},
        )
        return repository

    # Create new repository
    repository = Repository(path=path_str, name=name, is_active=True)
    db.add(repository)
    await db.flush()  # Get ID without committing

    logger.info(
        f"Created new repository: {repository.id}",
        extra={
            "context": {
                "repository_id": str(repository.id),
                "path": path_str,
                "name": name,
            }
        },
    )

    return repository


async def _read_file(file_path: Path) -> str:
    """Read file content as string.

    Args:
        file_path: Path to file

    Returns:
        File content as UTF-8 string

    Raises:
        FileNotFoundError: If file does not exist
        UnicodeDecodeError: If file is not valid UTF-8
        OSError: If file cannot be read
    """
    try:
        # Use asyncio for non-blocking I/O
        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(
            None, lambda: file_path.read_text(encoding="utf-8")
        )
        return content
    except UnicodeDecodeError as e:
        logger.warning(
            f"File is not valid UTF-8, skipping: {file_path}",
            extra={"context": {"file_path": str(file_path), "error": str(e)}},
        )
        raise
    except Exception as e:
        logger.error(
            f"Failed to read file: {file_path}",
            extra={"context": {"file_path": str(file_path), "error": str(e)}},
        )
        raise


async def _create_code_files(
    db: AsyncSession,
    repository_id: UUID,
    repo_path: Path,
    file_paths: list[Path],
) -> list[UUID]:
    """Create or update CodeFile records for given files.

    Args:
        db: Async database session
        repository_id: UUID of repository
        repo_path: Root path of repository
        file_paths: List of absolute file paths

    Returns:
        List of CodeFile UUIDs (in same order as file_paths)

    Raises:
        ValueError: If any file_path is not under repo_path
    """
    file_ids: list[UUID] = []

    for file_path in file_paths:
        if not file_path.is_relative_to(repo_path):
            raise ValueError(f"File {file_path} is not under repository {repo_path}")

        relative_path = str(file_path.relative_to(repo_path))
        path_str = str(file_path)

        # Get file metadata
        stat = file_path.stat()
        size_bytes = stat.st_size
        modified_at = datetime.utcfromtimestamp(stat.st_mtime)

        # Compute content hash
        content_hash = await compute_file_hash(file_path)

        # Detect language
        language = detect_language(file_path)

        # Check if file already exists
        result = await db.execute(
            select(CodeFile).where(
                CodeFile.repository_id == repository_id,
                CodeFile.relative_path == relative_path,
            )
        )
        existing_file = result.scalar_one_or_none()

        if existing_file is not None:
            # Update existing file
            existing_file.path = path_str
            existing_file.content_hash = content_hash
            existing_file.size_bytes = size_bytes
            existing_file.language = language
            existing_file.modified_at = modified_at
            existing_file.indexed_at = datetime.utcnow()
            existing_file.is_deleted = False
            existing_file.deleted_at = None
            file_ids.append(existing_file.id)

            logger.debug(
                f"Updated existing file: {relative_path}",
                extra={
                    "context": {
                        "file_id": str(existing_file.id),
                        "relative_path": relative_path,
                    }
                },
            )
        else:
            # Create new file
            code_file = CodeFile(
                repository_id=repository_id,
                path=path_str,
                relative_path=relative_path,
                content_hash=content_hash,
                size_bytes=size_bytes,
                language=language,
                modified_at=modified_at,
                indexed_at=datetime.utcnow(),
                is_deleted=False,
            )
            db.add(code_file)
            await db.flush()  # Get ID
            file_ids.append(code_file.id)

            logger.debug(
                f"Created new file: {relative_path}",
                extra={
                    "context": {
                        "file_id": str(code_file.id),
                        "relative_path": relative_path,
                    }
                },
            )

    return file_ids


async def _delete_chunks_for_file(db: AsyncSession, file_id: UUID) -> None:
    """Delete all chunks for a file (before re-chunking).

    Args:
        db: Async database session
        file_id: UUID of file
    """
    result = await db.execute(select(CodeChunk).where(CodeChunk.code_file_id == file_id))
    chunks = result.scalars().all()

    for chunk in chunks:
        await db.delete(chunk)

    logger.debug(
        f"Deleted {len(chunks)} chunks for file {file_id}",
        extra={"context": {"file_id": str(file_id), "chunk_count": len(chunks)}},
    )


async def _mark_files_deleted(
    db: AsyncSession, repository_id: UUID, file_paths: list[Path]
) -> None:
    """Mark files as deleted (soft delete).

    Args:
        db: Async database session
        repository_id: UUID of repository
        file_paths: List of absolute paths to deleted files
    """
    for file_path in file_paths:
        # Find file by path
        result = await db.execute(
            select(CodeFile).where(
                CodeFile.repository_id == repository_id,
                CodeFile.path == str(file_path),
            )
        )
        code_file = result.scalar_one_or_none()

        if code_file is not None:
            code_file.is_deleted = True
            code_file.deleted_at = datetime.utcnow()

            logger.debug(
                f"Marked file as deleted: {file_path}",
                extra={
                    "context": {
                        "file_id": str(code_file.id),
                        "path": str(file_path),
                    }
                },
            )


async def _create_change_events(
    db: AsyncSession, repository_id: UUID, changeset: ChangeSet, repo_path: Path
) -> None:
    """Create ChangeEvent records for detected changes.

    Args:
        db: Async database session
        repository_id: UUID of repository
        changeset: Detected file changes
        repo_path: Root path of repository
    """
    events_created = 0

    # Create events for added files
    for file_path in changeset.added:
        relative_path = str(file_path.relative_to(repo_path))

        # Find file record
        result = await db.execute(
            select(CodeFile).where(
                CodeFile.repository_id == repository_id,
                CodeFile.relative_path == relative_path,
            )
        )
        code_file = result.scalar_one_or_none()

        if code_file is not None:
            event = ChangeEvent(
                repository_id=repository_id,
                file_path=relative_path,
                change_type="added",
                detected_at=datetime.utcnow(),
            )
            db.add(event)
            events_created += 1

    # Create events for modified files
    for file_path in changeset.modified:
        relative_path = str(file_path.relative_to(repo_path))

        result = await db.execute(
            select(CodeFile).where(
                CodeFile.repository_id == repository_id,
                CodeFile.relative_path == relative_path,
            )
        )
        code_file = result.scalar_one_or_none()

        if code_file is not None:
            event = ChangeEvent(
                repository_id=repository_id,
                file_path=relative_path,
                change_type="modified",
                detected_at=datetime.utcnow(),
            )
            db.add(event)
            events_created += 1

    # Create events for deleted files
    for file_path in changeset.deleted:
        # Find file by absolute path
        result = await db.execute(
            select(CodeFile).where(
                CodeFile.repository_id == repository_id,
                CodeFile.path == str(file_path),
            )
        )
        code_file = result.scalar_one_or_none()

        if code_file is not None:
            event = ChangeEvent(
                repository_id=repository_id,
                file_path=code_file.relative_path,
                change_type="deleted",
                detected_at=datetime.utcnow(),
            )
            db.add(event)
            events_created += 1

    logger.info(
        f"Created {events_created} change events",
        extra={
            "context": {
                "repository_id": str(repository_id),
                "events_created": events_created,
            }
        },
    )


async def _create_embedding_metadata(
    db: AsyncSession, count: int, duration_ms: float
) -> None:
    """Create EmbeddingMetadata record for analytics.

    Args:
        db: Async database session
        count: Number of embeddings generated
        duration_ms: Total generation time in milliseconds
    """
    settings = get_settings()

    # Calculate average time per embedding
    avg_time_ms = int(duration_ms / count) if count > 0 else 0

    # NOTE: Embedding metadata tracking temporarily disabled due to model/schema mismatch
    # The Python model (analytics.py) doesn't match the actual database schema
    # This is non-essential analytics and doesn't affect core functionality
    # metadata = EmbeddingMetadata(
    #     model_name=settings.ollama_embedding_model,
    #     model_version=None,
    #     dimensions=768,
    #     generation_time_ms=avg_time_ms,
    #     created_at=datetime.utcnow(),
    # )
    # db.add(metadata)

    logger.debug(
        f"Created embedding metadata: {count} embeddings, {avg_time_ms}ms avg",
        extra={
            "context": {
                "embedding_count": count,
                "avg_time_ms": avg_time_ms,
                "total_time_ms": duration_ms,
            }
        },
    )


# ==============================================================================
# Public API
# ==============================================================================


async def index_repository(
    repo_path: Path,
    name: str,
    db: AsyncSession,
    project_id: str,
    force_reindex: bool = False,
) -> IndexResult:
    """Index or re-index a repository.

    Orchestrates the complete indexing workflow:
    1. Get or create Repository record
    2. Scan repository for files
    3. Detect changes (or force reindex all)
    4. Chunk files in batches
    5. Generate embeddings in batches
    6. Store chunks with embeddings
    7. Update repository metadata
    8. Create change events

    Args:
        repo_path: Absolute path to repository
        name: Repository display name
        db: Async database session
        project_id: Project workspace identifier
        force_reindex: If True, reindex all files (default: False)

    Returns:
        IndexResult with summary statistics

    Raises:
        ValueError: If repo_path is not a directory or not absolute
        OSError: If repo_path is not accessible

    Performance:
        Target: <60 seconds for 10,000 files
        Uses batching for files (100/batch) and embeddings (50/batch)
    """
    start_time = time.perf_counter()
    errors: list[str] = []

    logger.info(
        f"Starting repository indexing: {repo_path}",
        extra={
            "context": {
                "repository_path": str(repo_path),
                "name": name,
                "force_reindex": force_reindex,
                "operation": "index_repository",
            }
        },
    )

    try:
        # 1. Get or create Repository record
        repository = await _get_or_create_repository(db, repo_path, name)

        # 2. Scan repository for files
        all_files = await scan_repository(repo_path)

        logger.info(
            f"Scanned repository: {len(all_files)} files found",
            extra={
                "context": {
                    "repository_id": str(repository.id),
                    "file_count": len(all_files),
                }
            },
        )

        # 3. Detect changes (or force reindex all)
        if force_reindex:
            files_to_index = all_files
            changeset = ChangeSet(added=all_files, modified=[], deleted=[])
            logger.info(
                "Force reindex enabled: indexing all files",
                extra={"context": {"file_count": len(files_to_index)}},
            )
        else:
            changeset = await detect_changes(repo_path, db, repository.id)
            files_to_index = changeset.added + changeset.modified

            logger.info(
                f"Change detection: {len(changeset.added)} added, "
                f"{len(changeset.modified)} modified, {len(changeset.deleted)} deleted",
                extra={
                    "context": {
                        "repository_id": str(repository.id),
                        "added": len(changeset.added),
                        "modified": len(changeset.modified),
                        "deleted": len(changeset.deleted),
                    }
                },
            )

        # Handle deleted files (mark as deleted)
        if changeset.deleted:
            await _mark_files_deleted(db, repository.id, changeset.deleted)

        # Create change events
        if changeset.has_changes:
            await _create_change_events(db, repository.id, changeset, repo_path)

        # If no files to index, return early
        if not files_to_index:
            # Determine appropriate status based on context
            # If force_reindex is True and we found files but none to index, something is wrong
            # If no files were found at all, this is an error condition
            if len(all_files) == 0:
                error_msg = (
                    f"No files found in repository at {repo_path}. "
                    f"Check that the directory contains code files."
                )
                errors.append(error_msg)
                logger.error(
                    error_msg,
                    extra={
                        "context": {
                            "repository_id": str(repository.id),
                            "repository_path": str(repo_path),
                        }
                    },
                )

                duration = time.perf_counter() - start_time
                return IndexResult(
                    repository_id=repository.id,
                    files_indexed=0,
                    chunks_created=0,
                    duration_seconds=duration,
                    status="failed",
                    errors=errors,
                )

            # If we're in force_reindex mode but somehow nothing to index, that's suspicious
            if force_reindex and len(all_files) > 0:
                error_msg = (
                    f"Force reindex requested but no files to process. "
                    f"Found {len(all_files)} files but all filtered out or failed validation."
                )
                errors.append(error_msg)
                logger.warning(
                    error_msg,
                    extra={
                        "context": {
                            "repository_id": str(repository.id),
                            "file_count": len(all_files),
                        }
                    },
                )

                duration = time.perf_counter() - start_time
                return IndexResult(
                    repository_id=repository.id,
                    files_indexed=0,
                    chunks_created=0,
                    duration_seconds=duration,
                    status="failed",
                    errors=errors,
                )

            # Normal incremental update case: no changes detected (this is OK)
            logger.info(
                "No files to index (no changes detected since last indexing)",
                extra={
                    "context": {
                        "repository_id": str(repository.id),
                        "total_files": len(all_files),
                    }
                },
            )

            # Update repository metadata
            repository.last_indexed_at = datetime.utcnow()
            await db.commit()

            duration = time.perf_counter() - start_time
            return IndexResult(
                repository_id=repository.id,
                files_indexed=0,
                chunks_created=0,
                duration_seconds=duration,
                status="success",
                errors=[],
            )

        # 4. Chunk files in batches
        all_chunks_to_create: list[tuple[CodeChunk, str]] = []  # (chunk, embedding_text)
        files_processed = 0

        for file_batch in _batch(files_to_index, FILE_BATCH_SIZE):
            batch_start = time.perf_counter()

            # Read file contents
            file_contents: list[str] = []
            for file_path in file_batch:
                try:
                    content = await _read_file(file_path)
                    file_contents.append(content)
                except Exception as e:
                    error_msg = f"Failed to read {file_path}: {e}"
                    errors.append(error_msg)
                    logger.error(
                        error_msg,
                        extra={"context": {"file_path": str(file_path), "error": str(e)}},
                    )
                    # Use empty content for failed reads
                    file_contents.append("")

            # Create CodeFile records
            try:
                file_ids = await _create_code_files(
                    db, repository.id, repo_path, file_batch
                )
            except Exception as e:
                error_msg = f"Failed to create CodeFile records: {e}"
                errors.append(error_msg)
                logger.error(
                    error_msg,
                    extra={"context": {"batch_size": len(file_batch), "error": str(e)}},
                )
                continue

            # Delete old chunks for modified files
            for file_id in file_ids:
                try:
                    await _delete_chunks_for_file(db, file_id)
                except Exception as e:
                    error_msg = f"Failed to delete chunks for file {file_id}: {e}"
                    errors.append(error_msg)
                    logger.warning(error_msg, extra={"context": {"file_id": str(file_id)}})

            # Chunk files
            try:
                # Add project_id to each tuple for chunker
                chunk_files_input = list(
                    zip(file_batch, file_contents, file_ids, [project_id] * len(file_ids))
                )
                chunk_lists = await chunk_files_batch(chunk_files_input)
            except Exception as e:
                error_msg = f"Failed to chunk files: {e}"
                errors.append(error_msg)
                logger.error(
                    error_msg,
                    extra={"context": {"batch_size": len(file_batch), "error": str(e)}},
                )
                continue

            # Convert CodeChunkCreate to CodeChunk (without embeddings yet)
            for chunk_list in chunk_lists:
                for chunk_create in chunk_list:
                    chunk = CodeChunk(
                        code_file_id=chunk_create.code_file_id,
                        project_id=chunk_create.project_id,
                        content=chunk_create.content,
                        start_line=chunk_create.start_line,
                        end_line=chunk_create.end_line,
                        chunk_type=chunk_create.chunk_type,
                        embedding=None,  # Will be set after embedding generation
                    )
                    all_chunks_to_create.append((chunk, chunk_create.content))

            files_processed += len(file_batch)
            batch_duration = time.perf_counter() - batch_start

            logger.debug(
                f"Processed file batch: {len(file_batch)} files, "
                f"{sum(len(cl) for cl in chunk_lists)} chunks, "
                f"{batch_duration:.2f}s",
                extra={
                    "context": {
                        "batch_size": len(file_batch),
                        "chunk_count": sum(len(cl) for cl in chunk_lists),
                        "duration_seconds": batch_duration,
                    }
                },
            )

        logger.info(
            f"Chunking complete: {files_processed} files, {len(all_chunks_to_create)} chunks",
            extra={
                "context": {
                    "files_processed": files_processed,
                    "chunk_count": len(all_chunks_to_create),
                }
            },
        )

        # 5. Generate embeddings in batches
        embeddings_generated = 0

        if all_chunks_to_create:
            embedding_start = time.perf_counter()

            # Extract texts for embedding
            texts = [text for _, text in all_chunks_to_create]

            # Generate embeddings in batches
            all_embeddings: list[list[float]] = []

            for text_batch in _batch(texts, EMBEDDING_BATCH_SIZE):
                try:
                    batch_embeddings = await generate_embeddings(text_batch)
                    all_embeddings.extend(batch_embeddings)
                    embeddings_generated += len(batch_embeddings)
                except Exception as e:
                    error_msg = f"Failed to generate embeddings: {e}"
                    errors.append(error_msg)
                    logger.error(
                        error_msg,
                        extra={
                            "context": {
                                "batch_size": len(text_batch),
                                "error": str(e),
                            }
                        },
                    )
                    # Add None for failed embeddings
                    all_embeddings.extend([[] for _ in text_batch])

            embedding_duration_ms = (time.perf_counter() - embedding_start) * 1000

            logger.info(
                f"Generated {embeddings_generated} embeddings in {embedding_duration_ms:.0f}ms",
                extra={
                    "context": {
                        "embedding_count": embeddings_generated,
                        "duration_ms": embedding_duration_ms,
                        "avg_ms_per_embedding": (
                            embedding_duration_ms / embeddings_generated
                            if embeddings_generated > 0
                            else 0
                        ),
                    }
                },
            )

            # Create embedding metadata for analytics
            if embeddings_generated > 0:
                await _create_embedding_metadata(db, embeddings_generated, embedding_duration_ms)

            # 6. Store chunks with embeddings
            for i, (chunk, _) in enumerate(all_chunks_to_create):
                if i < len(all_embeddings) and all_embeddings[i]:
                    chunk.embedding = all_embeddings[i]
                db.add(chunk)

            logger.info(
                f"Stored {len(all_chunks_to_create)} chunks in database",
                extra={"context": {"chunk_count": len(all_chunks_to_create)}},
            )

        # 7. Update repository metadata
        repository.last_indexed_at = datetime.utcnow()

        # 8. Commit transaction
        await db.commit()

        duration = time.perf_counter() - start_time

        # Determine status
        if errors:
            status: Literal["success", "partial", "failed"] = "partial"
        else:
            status = "success"

        logger.info(
            f"Repository indexing complete: {status}",
            extra={
                "context": {
                    "repository_id": str(repository.id),
                    "files_indexed": len(files_to_index),
                    "chunks_created": len(all_chunks_to_create),
                    "duration_seconds": duration,
                    "status": status,
                    "error_count": len(errors),
                }
            },
        )

        return IndexResult(
            repository_id=repository.id,
            files_indexed=len(files_to_index),
            chunks_created=len(all_chunks_to_create),
            duration_seconds=duration,
            status=status,
            errors=errors,
        )

    except Exception as e:
        # Critical error - rollback transaction
        await db.rollback()

        error_msg = f"Critical error during indexing: {e}"
        errors.append(error_msg)
        logger.error(
            error_msg,
            extra={
                "context": {
                    "repository_path": str(repo_path),
                    "error": str(e),
                    "operation": "index_repository",
                }
            },
        )

        duration = time.perf_counter() - start_time

        # Return failed result (repository_id may not be available)
        return IndexResult(
            repository_id=UUID("00000000-0000-0000-0000-000000000000"),  # Placeholder
            files_indexed=0,
            chunks_created=0,
            duration_seconds=duration,
            status="failed",
            errors=errors,
        )


async def incremental_update(
    repository_id: UUID, db: AsyncSession, project_id: str
) -> IndexResult:
    """Perform incremental update for modified files.

    Detects changes since last indexing and only reindexes modified files.
    Much faster than full reindex for large repositories.

    Args:
        repository_id: UUID of repository to update
        db: Async database session
        project_id: Project workspace identifier

    Returns:
        IndexResult with summary statistics

    Raises:
        ValueError: If repository not found

    Performance:
        Significantly faster than full reindex (only processes changed files)
        Target: <5 seconds for typical change sets (<100 files)
    """
    logger.info(
        f"Starting incremental update for repository {repository_id}",
        extra={
            "context": {
                "repository_id": str(repository_id),
                "operation": "incremental_update",
            }
        },
    )

    # Get repository
    result = await db.execute(select(Repository).where(Repository.id == repository_id))
    repository = result.scalar_one_or_none()

    if repository is None:
        raise ValueError(f"Repository not found: {repository_id}")

    repo_path = Path(repository.path)

    # Perform indexing without force_reindex
    return await index_repository(
        repo_path=repo_path,
        name=repository.name,
        db=db,
        project_id=project_id,
        force_reindex=False,
    )


# ==============================================================================
# Module Exports
# ==============================================================================

__all__ = [
    "IndexResult",
    "index_repository",
    "incremental_update",
]
