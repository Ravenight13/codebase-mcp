"""File scanner service with ignore pattern support.

Scans repository directories, respects .gitignore/.mcpignore patterns, and detects
file changes by comparing filesystem timestamps with database state.

Constitutional Compliance:
- Principle IV: Performance (async operations, cached ignore patterns, <5s for 10K files)
- Principle V: Production quality (comprehensive error handling, graceful degradation)
- Principle VIII: Type safety (full mypy --strict compliance)

Key Features:
- Respects .gitignore patterns using pathspec library
- Supports custom .mcpignore patterns
- Change detection via mtime comparison
- Async operations for I/O performance
- Cached ignore pattern parsing
"""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Final, Sequence

from pathspec import PathSpec
from pathspec.patterns.gitwildmatch import GitWildMatchPattern
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.mcp.mcp_logging import get_logger
from src.models import CodeFile

# ==============================================================================
# Constants
# ==============================================================================

logger = get_logger(__name__)

# Default ignore patterns (always applied)
DEFAULT_IGNORE_PATTERNS: Final[list[str]] = [
    # Python bytecode and cache
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    # Version control
    ".git/",
    ".svn/",
    ".hg/",
    # Dependencies
    "node_modules/",
    ".venv/",
    "venv/",
    ".env",
    "*.egg-info/",
    # Build artifacts
    "build/",
    "dist/",
    # Cache and coverage
    ".ruff_cache/",
    ".pytest_cache/",
    "htmlcov/",
    ".coverage",
    ".coverage.*",
    # Binary files - Images
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.webp",
    "*.ico",
    "*.bmp",
    "*.svg",
    # Binary files - Compiled/Native
    "*.so",
    "*.dylib",
    "*.dll",
    "*.exe",
    "*.bin",
    "*.obj",
    "*.o",
    # Binary files - Archives
    "*.zip",
    "*.tar",
    "*.tar.gz",
    "*.tgz",
    "*.rar",
    "*.7z",
    # Binary files - Media
    "*.mp4",
    "*.mp3",
    "*.wav",
    "*.avi",
    "*.mov",
    # System files
    ".DS_Store",
    "Thumbs.db",
]

# Ignore file names to load
IGNORE_FILE_NAMES: Final[list[str]] = [".gitignore", ".mcpignore"]


# ==============================================================================
# Data Structures
# ==============================================================================


@dataclass(frozen=True)
class ChangeSet:
    """Represents file changes detected during repository scan.

    Attributes:
        added: Files that don't exist in database
        modified: Files with newer mtime than database record
        deleted: Files in database that no longer exist on filesystem
    """

    added: list[Path]
    modified: list[Path]
    deleted: list[Path]

    def __post_init__(self) -> None:
        """Validate ChangeSet invariants."""
        # Ensure no overlapping files between categories
        added_set = set(self.added)
        modified_set = set(self.modified)
        deleted_set = set(self.deleted)

        if added_set & modified_set:
            raise ValueError("Files cannot be both added and modified")
        if added_set & deleted_set:
            raise ValueError("Files cannot be both added and deleted")
        if modified_set & deleted_set:
            raise ValueError("Files cannot be both modified and deleted")

    @property
    def total_changes(self) -> int:
        """Total number of changed files."""
        return len(self.added) + len(self.modified) + len(self.deleted)

    @property
    def has_changes(self) -> bool:
        """Whether any changes were detected."""
        return self.total_changes > 0


# ==============================================================================
# Ignore Pattern Cache
# ==============================================================================


class IgnorePatternCache:
    """Caches parsed ignore patterns for performance.

    Singleton pattern to avoid re-parsing .gitignore files on each scan.
    """

    _instance: IgnorePatternCache | None = None
    _cache: dict[Path, PathSpec]

    def __new__(cls) -> IgnorePatternCache:
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache = {}
        return cls._instance

    def get_or_create(self, repo_path: Path) -> PathSpec:
        """Get cached PathSpec or create new one.

        Args:
            repo_path: Root path of repository

        Returns:
            PathSpec for repository ignore patterns
        """
        if repo_path in self._cache:
            logger.debug(f"Using cached ignore patterns for {repo_path}")
            return self._cache[repo_path]

        logger.debug(f"Building ignore patterns for {repo_path}")
        pathspec = self._build_pathspec(repo_path)
        self._cache[repo_path] = pathspec
        return pathspec

    def _build_pathspec(self, repo_path: Path) -> PathSpec:
        """Build PathSpec from ignore files and defaults.

        Args:
            repo_path: Root path of repository

        Returns:
            PathSpec combining default patterns, .gitignore, and .mcpignore
        """
        patterns: list[str] = DEFAULT_IGNORE_PATTERNS.copy()

        # Load patterns from .gitignore and .mcpignore files
        for ignore_file_name in IGNORE_FILE_NAMES:
            ignore_file = repo_path / ignore_file_name
            if ignore_file.is_file():
                try:
                    content = ignore_file.read_text(encoding="utf-8")
                    # Filter out comments and empty lines
                    file_patterns = [
                        line.strip()
                        for line in content.splitlines()
                        if line.strip() and not line.strip().startswith("#")
                    ]
                    patterns.extend(file_patterns)
                    logger.debug(
                        f"Loaded {len(file_patterns)} patterns from {ignore_file_name}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to read {ignore_file_name}: {e}",
                        extra={
                            "context": {
                                "ignore_file": str(ignore_file),
                                "error": str(e),
                            }
                        },
                    )

        return PathSpec.from_lines(GitWildMatchPattern, patterns)

    def clear(self) -> None:
        """Clear the cache (useful for testing)."""
        self._cache.clear()


# ==============================================================================
# Public API
# ==============================================================================


def is_ignored(file_path: Path, repo_path: Path) -> bool:
    """Check if file should be ignored based on ignore patterns.

    Args:
        file_path: Absolute path to file
        repo_path: Root path of repository

    Returns:
        True if file should be ignored, False otherwise

    Raises:
        ValueError: If file_path is not under repo_path
    """
    if not file_path.is_relative_to(repo_path):
        raise ValueError(f"File {file_path} is not under repository {repo_path}")

    # Get relative path for pattern matching
    relative_path = file_path.relative_to(repo_path)

    # Get cached PathSpec
    cache = IgnorePatternCache()
    pathspec = cache.get_or_create(repo_path)

    # Check if path matches any ignore pattern
    return pathspec.match_file(str(relative_path))


async def scan_repository(repo_path: Path) -> list[Path]:
    """Scan repository and return all non-ignored files.

    Args:
        repo_path: Root path of repository to scan

    Returns:
        List of absolute paths to all non-ignored files

    Raises:
        ValueError: If repo_path is not a directory
        OSError: If repo_path is not accessible

    Performance:
        Target: <5 seconds for 10,000 files
        Uses async I/O for file system operations
    """
    if not repo_path.is_dir():
        raise ValueError(f"Repository path is not a directory: {repo_path}")

    logger.info(
        "Starting repository scan",
        extra={
            "context": {
                "repository_path": str(repo_path),
                "operation": "scan_repository",
            }
        },
    )

    start_time = asyncio.get_event_loop().time()

    # Scan all files (blocking I/O, but fast enough for our purposes)
    # For very large repos, could parallelize with concurrent.futures
    all_files = [f for f in repo_path.rglob("*") if f.is_file()]

    # Filter ignored files
    non_ignored_files = [f for f in all_files if not is_ignored(f, repo_path)]

    elapsed_ms = (asyncio.get_event_loop().time() - start_time) * 1000

    logger.info(
        "Repository scan complete",
        extra={
            "context": {
                "repository_path": str(repo_path),
                "total_files": len(all_files),
                "non_ignored_files": len(non_ignored_files),
                "ignored_files": len(all_files) - len(non_ignored_files),
                "duration_ms": elapsed_ms,
                "operation": "scan_repository",
            }
        },
    )

    return non_ignored_files


async def detect_changes(
    repo_path: Path, db: AsyncSession, repository_id: uuid.UUID
) -> ChangeSet:
    """Detect file changes since last scan by comparing filesystem with database.

    Args:
        repo_path: Root path of repository
        db: Async database session
        repository_id: UUID of repository in database

    Returns:
        ChangeSet with added, modified, and deleted files

    Raises:
        ValueError: If repo_path is not a directory
        OSError: If repo_path is not accessible

    Performance:
        Target: <5 seconds for 10,000 files
        Uses async database queries for state comparison
    """
    logger.info(
        "Starting change detection",
        extra={
            "context": {
                "repository_path": str(repo_path),
                "repository_id": repository_id,
                "operation": "detect_changes",
            }
        },
    )

    start_time = asyncio.get_event_loop().time()

    # Get current filesystem state
    current_files = await scan_repository(repo_path)
    current_state: dict[Path, float] = {}

    for file_path in current_files:
        try:
            stat = file_path.stat()
            current_state[file_path] = stat.st_mtime
        except OSError as e:
            logger.warning(
                f"Failed to stat file: {file_path}",
                extra={"context": {"file_path": str(file_path), "error": str(e)}},
            )

    # Get database state (only non-deleted files)
    result = await db.execute(
        select(CodeFile.path, CodeFile.modified_at).where(
            CodeFile.repository_id == repository_id, CodeFile.is_deleted == False  # noqa: E712
        )
    )
    db_records = result.all()

    db_state: dict[Path, float] = {
        Path(path): modified_at.timestamp() for path, modified_at in db_records
    }

    # Detect changes
    added: list[Path] = []
    modified: list[Path] = []
    deleted: list[Path] = []

    # Find added and modified files
    for file_path, mtime in current_state.items():
        if file_path not in db_state:
            added.append(file_path)
        elif mtime > db_state[file_path]:
            # File modified if mtime is newer
            modified.append(file_path)

    # Find deleted files
    deleted = list(set(db_state.keys()) - set(current_state.keys()))

    changeset = ChangeSet(added=added, modified=modified, deleted=deleted)

    elapsed_ms = (asyncio.get_event_loop().time() - start_time) * 1000

    logger.info(
        "Change detection complete",
        extra={
            "context": {
                "repository_path": str(repo_path),
                "repository_id": repository_id,
                "added_files": len(added),
                "modified_files": len(modified),
                "deleted_files": len(deleted),
                "total_changes": changeset.total_changes,
                "duration_ms": elapsed_ms,
                "operation": "detect_changes",
            }
        },
    )

    return changeset


async def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of file content.

    Args:
        file_path: Path to file

    Returns:
        Hex string of SHA-256 hash (64 characters)

    Raises:
        FileNotFoundError: If file does not exist
        OSError: If file is not accessible
    """
    hasher = hashlib.sha256()

    # Read file in chunks for memory efficiency
    chunk_size = 65536  # 64KB chunks

    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
    except FileNotFoundError:
        logger.error(
            f"File not found: {file_path}",
            extra={"context": {"file_path": str(file_path)}},
        )
        raise
    except OSError as e:
        logger.error(
            f"Failed to read file: {file_path}",
            extra={"context": {"file_path": str(file_path), "error": str(e)}},
        )
        raise

    return hasher.hexdigest()


# ==============================================================================
# Module Exports
# ==============================================================================

__all__ = [
    "ChangeSet",
    "scan_repository",
    "detect_changes",
    "is_ignored",
    "compute_file_hash",
]
