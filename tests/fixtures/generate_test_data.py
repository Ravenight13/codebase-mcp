#!/usr/bin/env python3
"""Test data generation utility for database migration testing.

This script generates realistic test data for the Codebase MCP Server database,
specifically designed to test database migrations and schema changes.

Constitutional Compliance:
- Principle V: Production quality (comprehensive error handling, validation)
- Principle VIII: Type safety (mypy --strict compliance, complete type annotations)
- Principle IV: Performance (bulk inserts for large datasets)

Features:
- Generates N repositories with M code_chunks per repository
- Realistic file paths and Python code snippets
- Progress indication for large datasets
- Bulk INSERT operations for performance
- Proper error handling and cleanup

Database Schema (migration 001):
- repositories: id (UUID), path (TEXT UNIQUE), name (TEXT),
               last_indexed_at (TIMESTAMP), is_active (BOOLEAN), created_at (TIMESTAMP)
- code_files: id (UUID), repository_id (UUID FK), path (TEXT), relative_path (TEXT),
             content_hash (TEXT), size_bytes (INT), language (TEXT), modified_at (TIMESTAMP),
             indexed_at (TIMESTAMP), is_deleted (BOOLEAN), deleted_at (TIMESTAMP), created_at (TIMESTAMP)
- code_chunks: id (UUID), code_file_id (UUID FK), content (TEXT),
              start_line (INT), end_line (INT), chunk_type (TEXT), embedding (VECTOR), created_at (TIMESTAMP)

Usage:
    # Basic usage:
    python tests/fixtures/generate_test_data.py --database codebase_mcp_test

    # Custom dataset sizes:
    python tests/fixtures/generate_test_data.py \
        --database codebase_mcp_test \
        --repositories 100 \
        --chunks-per-repo 100

    # Using DATABASE_URL environment variable:
    export DATABASE_URL=postgresql://localhost/codebase_mcp_test
    python tests/fixtures/generate_test_data.py

Exit Codes:
    0 - Success (data generated successfully)
    1 - Error (connection failed, validation failed, etc.)
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
import os
import sys
from typing import NoReturn
import uuid

import asyncpg  # type: ignore[import-untyped]

# ==============================================================================
# Type Definitions
# ==============================================================================


@dataclass(frozen=True)
class Repository:
    """Repository record for insertion.

    Attributes:
        id: UUID primary key
        path: Absolute path to repository (must be unique)
        name: Repository display name
        last_indexed_at: Timestamp of indexing
        is_active: Whether repository is active
        created_at: Creation timestamp
    """

    id: uuid.UUID
    path: str
    name: str
    last_indexed_at: datetime
    is_active: bool
    created_at: datetime


@dataclass(frozen=True)
class CodeFile:
    """Code file record for insertion.

    Attributes:
        id: UUID primary key
        repository_id: Foreign key to repositories table
        path: Absolute path to file
        relative_path: Relative path within repository
        content_hash: SHA256 hash of file content
        size_bytes: File size in bytes
        language: Programming language (e.g., 'python')
        modified_at: File modification timestamp
        indexed_at: File indexing timestamp
        is_deleted: Whether file is deleted
        deleted_at: Deletion timestamp (nullable)
        created_at: Creation timestamp
    """

    id: uuid.UUID
    repository_id: uuid.UUID
    path: str
    relative_path: str
    content_hash: str
    size_bytes: int
    language: str
    modified_at: datetime
    indexed_at: datetime
    is_deleted: bool
    deleted_at: datetime | None
    created_at: datetime


@dataclass(frozen=True)
class CodeChunk:
    """Code chunk record for insertion.

    Attributes:
        id: UUID primary key
        code_file_id: Foreign key to code_files table
        content: Python code content
        start_line: Starting line number (1-indexed)
        end_line: Ending line number (1-indexed)
        chunk_type: Type of chunk ('function', 'class', 'block')
        created_at: Creation timestamp
    """

    id: uuid.UUID
    code_file_id: uuid.UUID
    content: str
    start_line: int
    end_line: int
    chunk_type: str
    created_at: datetime


@dataclass(frozen=True)
class GenerationStats:
    """Statistics for data generation run.

    Attributes:
        repositories_created: Number of repositories inserted
        code_files_created: Number of code files inserted
        code_chunks_created: Number of code chunks inserted
        duration_seconds: Total generation time in seconds
    """

    repositories_created: int
    code_files_created: int
    code_chunks_created: int
    duration_seconds: float


# ==============================================================================
# Test Data Templates
# ==============================================================================

# Realistic Python file paths
FILE_PATHS: list[str] = [
    "main.py",
    "app.py",
    "server.py",
    "models.py",
    "schemas.py",
    "database.py",
    "utils.py",
    "helpers.py",
    "config.py",
    "settings.py",
    "tests/test_main.py",
    "tests/test_models.py",
    "tests/test_api.py",
    "src/__init__.py",
    "src/core/engine.py",
    "src/api/routes.py",
    "src/api/handlers.py",
    "src/services/processor.py",
    "src/services/validator.py",
    "lib/parser.py",
]

# Realistic Python code snippets
CODE_SNIPPETS: list[str] = [
    '''def process_data(input: str) -> dict[str, Any]:
    """Process input data and return structured result."""
    result = {"status": "success", "data": input}
    return result''',

    '''class DataProcessor:
    """Handles data processing operations."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.initialized = False''',

    '''async def fetch_records(
    session: AsyncSession,
    filters: dict[str, Any]
) -> list[Record]:
    """Fetch records from database with filters."""
    query = select(Record).filter_by(**filters)
    result = await session.execute(query)
    return result.scalars().all()''',

    '''def validate_input(data: dict[str, Any]) -> bool:
    """Validate input data against schema."""
    required_fields = ["id", "name", "created_at"]
    return all(field in data for field in required_fields)''',

    '''class APIHandler:
    """REST API request handler."""

    def __init__(self, database: Database) -> None:
        self.db = database
        self.logger = logging.getLogger(__name__)''',

    '''async def save_record(
    session: AsyncSession,
    record: Record
) -> uuid.UUID:
    """Save record to database and return ID."""
    session.add(record)
    await session.commit()
    return record.id''',

    '''def parse_config(file_path: str) -> dict[str, Any]:
    """Parse configuration file and return settings."""
    with open(file_path, "r") as f:
        config = json.load(f)
    return config''',

    '''class ServiceManager:
    """Manages service lifecycle and dependencies."""

    def __init__(self) -> None:
        self.services: dict[str, Service] = {}
        self.running = False''',
]


# ==============================================================================
# Data Generation Functions
# ==============================================================================


def generate_repositories(count: int) -> list[Repository]:
    """Generate repository test data.

    Args:
        count: Number of repositories to generate

    Returns:
        List of Repository records with unique paths

    Example:
        >>> repos = generate_repositories(100)
        >>> len(repos)
        100
        >>> repos[0].path
        '/tmp/test_repo_001'
    """
    repositories: list[Repository] = []
    now = datetime.now(UTC)

    for i in range(count):
        repo = Repository(
            id=uuid.uuid4(),
            path=f"/tmp/test_repo_{i:04d}",
            name=f"test_repo_{i:04d}",
            last_indexed_at=now,
            is_active=True,
            created_at=now,
        )
        repositories.append(repo)

    return repositories


def generate_code_files(
    repositories: list[Repository],
    files_per_repo: int,
) -> list[CodeFile]:
    """Generate code file test data for repositories.

    Args:
        repositories: List of Repository records to generate files for
        files_per_repo: Number of files to generate per repository

    Returns:
        List of CodeFile records distributed across repositories

    Example:
        >>> repos = generate_repositories(10)
        >>> files = generate_code_files(repos, 10)
        >>> len(files)
        100
        >>> files[0].repository_id in [r.id for r in repos]
        True
    """
    files: list[CodeFile] = []
    now = datetime.now(UTC)

    for repo in repositories:
        for i in range(files_per_repo):
            # Cycle through file paths
            file_path_template = FILE_PATHS[i % len(FILE_PATHS)]
            relative_path = file_path_template
            absolute_path = f"{repo.path}/{relative_path}"

            # Generate fake content hash (SHA256)
            content_hash = uuid.uuid4().hex[:64]

            # Fake file size (100-5000 bytes)
            size_bytes = 100 + (i * 47) % 4900

            code_file = CodeFile(
                id=uuid.uuid4(),
                repository_id=repo.id,
                path=absolute_path,
                relative_path=relative_path,
                content_hash=content_hash,
                size_bytes=size_bytes,
                language="python",
                modified_at=now,
                indexed_at=now,
                is_deleted=False,
                deleted_at=None,
                created_at=now,
            )
            files.append(code_file)

    return files


def generate_code_chunks(
    code_files: list[CodeFile],
    chunks_per_file: int,
) -> list[CodeChunk]:
    """Generate code chunk test data for code files.

    Args:
        code_files: List of CodeFile records to generate chunks for
        chunks_per_file: Number of chunks to generate per file

    Returns:
        List of CodeChunk records distributed across code files

    Example:
        >>> repos = generate_repositories(10)
        >>> files = generate_code_files(repos, 10)
        >>> chunks = generate_code_chunks(files, 10)
        >>> len(chunks)
        1000
        >>> chunks[0].code_file_id in [f.id for f in files]
        True
    """
    chunks: list[CodeChunk] = []
    now = datetime.now(UTC)

    # Chunk types to cycle through
    chunk_types = ["function", "class", "block"]

    for code_file in code_files:
        for i in range(chunks_per_file):
            # Cycle through code snippets and chunk types
            code_snippet = CODE_SNIPPETS[i % len(CODE_SNIPPETS)]
            chunk_type = chunk_types[i % len(chunk_types)]

            # Calculate line numbers (realistic ranges)
            start_line = (i * 10) + 1
            end_line = start_line + len(code_snippet.split("\n"))

            chunk = CodeChunk(
                id=uuid.uuid4(),
                code_file_id=code_file.id,
                content=code_snippet,
                start_line=start_line,
                end_line=end_line,
                chunk_type=chunk_type,
                created_at=now,
            )
            chunks.append(chunk)

    return chunks


# ==============================================================================
# Database Operations
# ==============================================================================


async def insert_repositories(
    conn: asyncpg.Connection,
    repositories: list[Repository],
) -> int:
    """Insert repositories using bulk INSERT.

    Args:
        conn: Database connection
        repositories: List of Repository records to insert

    Returns:
        Number of repositories inserted

    Raises:
        asyncpg.PostgresError: If database operation fails
    """
    # Prepare bulk insert data (let DB handle timestamps via server defaults)
    records = [
        (
            str(repo.id),
            repo.path,
            repo.name,
            repo.is_active,
        )
        for repo in repositories
    ]

    # Bulk INSERT for performance (use CURRENT_TIMESTAMP for timestamps)
    insert_query = """
        INSERT INTO repositories (
            id, path, name, last_indexed_at, is_active, created_at
        )
        VALUES ($1, $2, $3, CURRENT_TIMESTAMP, $4, CURRENT_TIMESTAMP)
    """

    await conn.executemany(insert_query, records)
    return len(records)


async def insert_code_files(
    conn: asyncpg.Connection,
    code_files: list[CodeFile],
    batch_size: int = 1000,
) -> int:
    """Insert code files using batched bulk INSERT.

    Args:
        conn: Database connection
        code_files: List of CodeFile records to insert
        batch_size: Number of records per batch (default: 1000)

    Returns:
        Number of code files inserted

    Raises:
        asyncpg.PostgresError: If database operation fails

    Note:
        Uses batching to avoid memory issues with large datasets
    """
    total_inserted = 0

    # Process in batches for large datasets
    for i in range(0, len(code_files), batch_size):
        batch = code_files[i : i + batch_size]

        # Prepare batch insert data
        records = [
            (
                str(file.id),
                str(file.repository_id),
                file.path,
                file.relative_path,
                file.content_hash,
                file.size_bytes,
                file.language,
                file.is_deleted,
            )
            for file in batch
        ]

        # Bulk INSERT for performance (use CURRENT_TIMESTAMP for all timestamps)
        insert_query = """
            INSERT INTO code_files (
                id, repository_id, path, relative_path, content_hash,
                size_bytes, language, modified_at, indexed_at, is_deleted, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, $8, CURRENT_TIMESTAMP)
        """

        await conn.executemany(insert_query, records)
        total_inserted += len(records)

        # Progress indication
        print(f"  Inserted {total_inserted:,} / {len(code_files):,} code files...")

    return total_inserted


async def insert_code_chunks(
    conn: asyncpg.Connection,
    code_chunks: list[CodeChunk],
    batch_size: int = 1000,
) -> int:
    """Insert code chunks using batched bulk INSERT.

    Args:
        conn: Database connection
        code_chunks: List of CodeChunk records to insert
        batch_size: Number of records per batch (default: 1000)

    Returns:
        Number of code chunks inserted

    Raises:
        asyncpg.PostgresError: If database operation fails

    Note:
        Uses batching to avoid memory issues with large datasets
    """
    total_inserted = 0

    # Process in batches for large datasets
    for i in range(0, len(code_chunks), batch_size):
        batch = code_chunks[i : i + batch_size]

        # Prepare batch insert data (let DB handle timestamps via server defaults)
        records = [
            (
                str(chunk.id),
                str(chunk.code_file_id),
                chunk.content,
                chunk.start_line,
                chunk.end_line,
                chunk.chunk_type,
            )
            for chunk in batch
        ]

        # Bulk INSERT for performance (use CURRENT_TIMESTAMP for timestamps)
        insert_query = """
            INSERT INTO code_chunks (
                id, code_file_id, content, start_line, end_line,
                chunk_type, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, CURRENT_TIMESTAMP)
        """

        await conn.executemany(insert_query, records)
        total_inserted += len(records)

        # Progress indication
        print(f"  Inserted {total_inserted:,} / {len(code_chunks):,} code chunks...")

    return total_inserted


async def verify_data(
    conn: asyncpg.Connection,
) -> tuple[int, int, int]:
    """Verify data was inserted correctly.

    Args:
        conn: Database connection

    Returns:
        Tuple of (repository_count, code_file_count, code_chunk_count)

    Raises:
        asyncpg.PostgresError: If database query fails
    """
    # Count repositories
    repo_count = await conn.fetchval("SELECT COUNT(*) FROM repositories")

    # Count code files
    file_count = await conn.fetchval("SELECT COUNT(*) FROM code_files")

    # Count code chunks
    chunk_count = await conn.fetchval("SELECT COUNT(*) FROM code_chunks")

    return (repo_count or 0, file_count or 0, chunk_count or 0)


# ==============================================================================
# Main Generation Workflow
# ==============================================================================


async def generate_test_data(
    database_url: str,
    num_repositories: int,
    files_per_repo: int,
    chunks_per_file: int,
) -> GenerationStats:
    """Generate test data and insert into database.

    Args:
        database_url: PostgreSQL connection string
        num_repositories: Number of repositories to create
        files_per_repo: Number of code files per repository
        chunks_per_file: Number of code chunks per file

    Returns:
        GenerationStats with creation counts and duration

    Raises:
        asyncpg.PostgresError: If database operations fail
        ValueError: If invalid parameters provided

    Example:
        >>> stats = await generate_test_data(
        ...     "postgresql://localhost/test_db",
        ...     10,
        ...     10,
        ...     10
        ... )
        >>> stats.repositories_created
        10
        >>> stats.code_files_created
        100
        >>> stats.code_chunks_created
        1000
    """
    start_time = datetime.now(UTC)

    print("\nGenerating test data...")
    print(f"Connected to database: {database_url.split('/')[-1]}")

    # Generate test data
    print(f"\nGenerating {num_repositories} repositories...")
    repositories = generate_repositories(num_repositories)

    total_files = num_repositories * files_per_repo
    print(f"Generating {total_files:,} code files ({files_per_repo} per repository)...")
    code_files = generate_code_files(repositories, files_per_repo)

    total_chunks = total_files * chunks_per_file
    print(f"Generating {total_chunks:,} code chunks ({chunks_per_file} per file)...")
    code_chunks = generate_code_chunks(code_files, chunks_per_file)

    # Connect to database and insert data
    conn = await asyncpg.connect(database_url)
    try:
        # Insert repositories
        print(f"\nInserting {num_repositories} repositories...")
        repos_inserted = await insert_repositories(conn, repositories)

        # Insert code files (with progress indication)
        print(f"Inserting {total_files:,} code files...")
        files_inserted = await insert_code_files(conn, code_files)

        # Insert code chunks (with progress indication)
        print(f"Inserting {total_chunks:,} code chunks...")
        chunks_inserted = await insert_code_chunks(conn, code_chunks)

        # Verify data
        print("\nVerifying data...")
        repo_count, file_count, chunk_count = await verify_data(conn)

        # Calculate duration
        duration = (datetime.now(UTC) - start_time).total_seconds()

        # Print summary
        print("\n" + "=" * 60)
        print("Complete!")
        print("=" * 60)
        print(f"Repositories: {repo_count:,}")
        print(f"Code files:   {file_count:,}")
        print(f"Code chunks:  {chunk_count:,}")
        print(f"Duration:     {duration:.2f} seconds")
        print("=" * 60)

        return GenerationStats(
            repositories_created=repo_count,
            code_files_created=file_count,
            code_chunks_created=chunk_count,
            duration_seconds=duration,
        )

    finally:
        await conn.close()


# ==============================================================================
# CLI Interface
# ==============================================================================


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Generate test data for database migration testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with explicit database name:
  python tests/fixtures/generate_test_data.py --database codebase_mcp_test

  # Custom dataset sizes:
  python tests/fixtures/generate_test_data.py \\
      --database codebase_mcp_test \\
      --repositories 10 \\
      --files-per-repo 10 \\
      --chunks-per-file 10

  # Using DATABASE_URL environment variable:
  export DATABASE_URL=postgresql://localhost/codebase_mcp_test
  python tests/fixtures/generate_test_data.py
        """,
    )

    parser.add_argument(
        "--database",
        type=str,
        help="Database name (required if DATABASE_URL not set)",
    )

    parser.add_argument(
        "--repositories",
        type=int,
        default=10,
        help="Number of repositories to generate (default: 10)",
    )

    parser.add_argument(
        "--files-per-repo",
        type=int,
        default=10,
        help="Number of code files per repository (default: 10)",
    )

    parser.add_argument(
        "--chunks-per-file",
        type=int,
        default=10,
        help="Number of code chunks per file (default: 10)",
    )

    return parser.parse_args()


def construct_database_url(args: argparse.Namespace) -> str:
    """Construct database URL from arguments or environment.

    Args:
        args: Parsed command-line arguments

    Returns:
        PostgreSQL connection URL

    Raises:
        SystemExit: If no database configuration found
    """
    # Try DATABASE_URL environment variable first
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        # Remove asyncpg driver if present (asyncpg.connect doesn't use it)
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        return database_url

    # Require --database argument if DATABASE_URL not set
    if not args.database:
        error_exit(
            "No database configuration found",
            "Either set DATABASE_URL environment variable or use --database argument",
        )

    # Construct URL from database name
    return f"postgresql://localhost/{args.database}"


def validate_args(args: argparse.Namespace) -> None:
    """Validate command-line arguments.

    Args:
        args: Parsed command-line arguments

    Raises:
        SystemExit: If validation fails
    """
    if args.repositories < 1:
        error_exit(
            "Invalid --repositories value",
            f"Must be >= 1, got: {args.repositories}",
        )

    if args.files_per_repo < 1:
        error_exit(
            "Invalid --files-per-repo value",
            f"Must be >= 1, got: {args.files_per_repo}",
        )

    if args.chunks_per_file < 1:
        error_exit(
            "Invalid --chunks-per-file value",
            f"Must be >= 1, got: {args.chunks_per_file}",
        )

    # Warn about very large datasets
    total_files = args.repositories * args.files_per_repo
    total_chunks = total_files * args.chunks_per_file
    if total_chunks > 100_000:
        print(
            f"\nWarning: Generating {total_chunks:,} code chunks ({total_files:,} files). "
            "This may take several minutes...",
            file=sys.stderr,
        )


def error_exit(message: str, details: str | None = None) -> NoReturn:
    """Print error message and exit with code 1.

    Args:
        message: Primary error message
        details: Optional detailed error information

    Exit Code:
        1 (error)
    """
    print(f"\n❌ ERROR: {message}", file=sys.stderr)
    if details:
        print(f"\nDetails: {details}", file=sys.stderr)
    print("\nUse --help for usage information.\n", file=sys.stderr)
    sys.exit(1)


async def main() -> int:
    """Main entry point for test data generation.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Parse and validate arguments
        args = parse_args()
        validate_args(args)

        # Construct database URL
        database_url = construct_database_url(args)

        # Generate test data
        stats = await generate_test_data(
            database_url=database_url,
            num_repositories=args.repositories,
            files_per_repo=args.files_per_repo,
            chunks_per_file=args.chunks_per_file,
        )

        return 0

    except asyncpg.PostgresError as e:
        error_exit(
            "Database operation failed",
            f"{type(e).__name__}: {e}",
        )

    except KeyboardInterrupt:
        print("\n\n❌ Interrupted by user", file=sys.stderr)
        return 1

    except Exception as e:
        error_exit(
            "Unexpected error",
            f"{type(e).__name__}: {e}",
        )


# ==============================================================================
# Script Entry Point
# ==============================================================================


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
