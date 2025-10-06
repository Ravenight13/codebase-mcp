#!/usr/bin/env python3
"""Cleanup script for 90-day deleted file retention policy.

This script removes files that have been soft-deleted for more than 90 days,
including their associated chunks and embeddings (cascaded automatically).

Constitutional Compliance:
- Principle V: Production quality (dry-run mode, detailed logging, safety)
- Principle VIII: Type safety (mypy --strict compliance)

Usage:
    # Manual execution with default database URL from environment
    python scripts/cleanup_deleted_files.py

    # Explicit database URL
    python scripts/cleanup_deleted_files.py --database-url postgresql+asyncpg://...

    # Dry run (no actual deletion)
    python scripts/cleanup_deleted_files.py --dry-run

    # Custom retention period (default 90 days)
    python scripts/cleanup_deleted_files.py --retention-days 30

    # Quiet mode (errors only)
    python scripts/cleanup_deleted_files.py --quiet

Cron Schedule:
    # Run daily at 2:00 AM
    0 2 * * * /usr/bin/python3 /path/to/scripts/cleanup_deleted_files.py

Exit Codes:
    0 - Success (files cleaned up or dry-run completed)
    1 - Error (database connection, validation, or cleanup failure)
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import get_settings
from src.models.code_chunk import CodeChunk
from src.models.code_file import CodeFile

# ==============================================================================
# Type Definitions
# ==============================================================================


class CleanupSummary:
    """Summary of cleanup operation results."""

    def __init__(
        self,
        *,
        files_deleted: int,
        chunks_deleted: int,
        cutoff_date: datetime,
        dry_run: bool,
        retention_days: int,
    ) -> None:
        """Initialize cleanup summary.

        Args:
            files_deleted: Number of files deleted
            chunks_deleted: Number of chunks deleted (cascaded)
            cutoff_date: Date cutoff for deletion
            dry_run: Whether this was a dry run
            retention_days: Retention period in days
        """
        self.files_deleted = files_deleted
        self.chunks_deleted = chunks_deleted
        self.cutoff_date = cutoff_date
        self.dry_run = dry_run
        self.retention_days = retention_days

    def to_dict(self) -> dict[str, Any]:
        """Convert summary to dictionary.

        Returns:
            Dictionary representation of summary
        """
        return {
            "files_deleted": self.files_deleted,
            "chunks_deleted": self.chunks_deleted,
            "cutoff_date": self.cutoff_date.isoformat(),
            "dry_run": self.dry_run,
            "retention_days": self.retention_days,
        }

    def __str__(self) -> str:
        """Format summary as human-readable string.

        Returns:
            Formatted summary string
        """
        mode = "DRY RUN" if self.dry_run else "EXECUTED"
        return (
            f"\n{'=' * 80}\n"
            f"Cleanup Summary ({mode})\n"
            f"{'=' * 80}\n"
            f"Retention Period: {self.retention_days} days\n"
            f"Cutoff Date: {self.cutoff_date.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"Files Deleted: {self.files_deleted}\n"
            f"Chunks Deleted (cascaded): {self.chunks_deleted}\n"
            f"{'=' * 80}\n"
        )


# ==============================================================================
# Core Cleanup Logic
# ==============================================================================


async def cleanup_deleted_files(
    database_url: str,
    retention_days: int = 90,
    dry_run: bool = False,
    verbose: bool = True,
) -> CleanupSummary:
    """Clean up files deleted more than retention_days ago.

    Args:
        database_url: PostgreSQL connection URL (asyncpg driver)
        retention_days: Number of days to retain deleted files (default: 90)
        dry_run: If True, report what would be deleted without deleting (default: False)
        verbose: If True, print progress messages (default: True)

    Returns:
        CleanupSummary with deletion statistics

    Raises:
        DatabaseError: If database connection or query fails
        ValueError: If retention_days is invalid

    Implementation:
        1. Calculate cutoff date (NOW - retention_days)
        2. Find all files with is_deleted=True and deleted_at < cutoff
        3. Count associated chunks (will be cascade deleted)
        4. Delete files (cascade deletes chunks and embeddings via FK)
        5. Return summary with counts

    Example:
        >>> summary = await cleanup_deleted_files(
        ...     database_url="postgresql+asyncpg://user:pass@localhost/mcp",
        ...     retention_days=90,
        ...     dry_run=False
        ... )
        >>> print(f"Deleted {summary.files_deleted} files")
    """
    # Validate inputs
    if retention_days <= 0:
        raise ValueError(f"retention_days must be positive, got {retention_days}")

    if verbose:
        print(f"\n{'=' * 80}")
        print("Deleted Files Cleanup Script")
        print(f"{'=' * 80}")
        print(f"Mode: {'DRY RUN' if dry_run else 'EXECUTE'}")
        print(f"Retention Period: {retention_days} days")
        print(f"Database: {database_url.split('@')[-1]}")  # Hide credentials
        print(f"{'=' * 80}\n")

    # Calculate cutoff date
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

    if verbose:
        print(
            f"Finding files deleted before: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )

    # Create database engine and session
    engine = create_async_engine(database_url, echo=False)
    SessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with SessionFactory() as session:
            # Step 1: Find files to delete
            stmt = select(CodeFile).where(
                CodeFile.is_deleted == True,  # noqa: E712 - SQLAlchemy requires == for boolean
                CodeFile.deleted_at < cutoff_date,
            )
            result = await session.execute(stmt)
            files_to_delete = result.scalars().all()

            files_count = len(files_to_delete)

            if files_count == 0:
                if verbose:
                    print("\nNo files found for cleanup.")
                return CleanupSummary(
                    files_deleted=0,
                    chunks_deleted=0,
                    cutoff_date=cutoff_date,
                    dry_run=dry_run,
                    retention_days=retention_days,
                )

            if verbose:
                print(f"\nFound {files_count} file(s) eligible for deletion:")
                for file in files_to_delete[:10]:  # Show first 10
                    print(
                        f"  - {file.relative_path} "
                        f"(deleted: {file.deleted_at.strftime('%Y-%m-%d') if file.deleted_at else 'unknown'})"
                    )
                if files_count > 10:
                    print(f"  ... and {files_count - 10} more")

            # Step 2: Count associated chunks (will be cascade deleted)
            file_ids = [file.id for file in files_to_delete]
            chunk_count_stmt = select(func.count(CodeChunk.id)).where(
                CodeChunk.code_file_id.in_(file_ids)
            )
            chunk_count_result = await session.execute(chunk_count_stmt)
            chunks_count = chunk_count_result.scalar() or 0

            if verbose:
                print(f"\nAssociated chunks to delete (cascade): {chunks_count}")

            # Step 3: Delete files (or report in dry-run)
            if not dry_run:
                if verbose:
                    print("\nDeleting files and chunks...")

                # Delete files (chunks cascade automatically via FK)
                delete_stmt = delete(CodeFile).where(
                    CodeFile.is_deleted == True,  # noqa: E712
                    CodeFile.deleted_at < cutoff_date,
                )
                await session.execute(delete_stmt)
                await session.commit()

                if verbose:
                    print("Deletion complete.")
            else:
                if verbose:
                    print(
                        "\nDRY RUN: No files were deleted. Use --no-dry-run to execute."
                    )

            # Return summary
            return CleanupSummary(
                files_deleted=files_count,
                chunks_deleted=chunks_count,
                cutoff_date=cutoff_date,
                dry_run=dry_run,
                retention_days=retention_days,
            )

    finally:
        # Close database connection
        await engine.dispose()


# ==============================================================================
# CLI Interface
# ==============================================================================


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Clean up files deleted more than N days ago",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run with default settings (90 days)
  python cleanup_deleted_files.py --dry-run

  # Execute cleanup with default settings
  python cleanup_deleted_files.py

  # Custom retention period (30 days)
  python cleanup_deleted_files.py --retention-days 30

  # Quiet mode (errors only)
  python cleanup_deleted_files.py --quiet

Cron Schedule:
  # Daily at 2:00 AM
  0 2 * * * /usr/bin/python3 /path/to/cleanup_deleted_files.py
        """,
    )

    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="PostgreSQL connection URL (default: from DATABASE_URL env var)",
    )

    parser.add_argument(
        "--retention-days",
        type=int,
        default=90,
        help="Number of days to retain deleted files (default: 90)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Report what would be deleted without actually deleting",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Suppress progress messages (errors only)",
    )

    return parser.parse_args()


async def main() -> int:
    """Main entry point for cleanup script.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    args = parse_arguments()

    # Get database URL from args or environment
    try:
        if args.database_url:
            database_url = args.database_url
        else:
            settings = get_settings()
            database_url = str(settings.database_url)
    except Exception as e:
        print(f"ERROR: Failed to get database URL: {e}", file=sys.stderr)
        print(
            "HINT: Set DATABASE_URL environment variable or use --database-url",
            file=sys.stderr,
        )
        return 1

    # Validate retention days
    if args.retention_days <= 0:
        print(
            f"ERROR: --retention-days must be positive, got {args.retention_days}",
            file=sys.stderr,
        )
        return 1

    # Execute cleanup
    try:
        summary = await cleanup_deleted_files(
            database_url=database_url,
            retention_days=args.retention_days,
            dry_run=args.dry_run,
            verbose=not args.quiet,
        )

        # Print summary
        if not args.quiet:
            print(summary)

        # Print machine-readable output for automation
        if args.quiet or args.dry_run:
            import json

            print(json.dumps(summary.to_dict(), indent=2))

        return 0

    except Exception as e:
        print(f"ERROR: Cleanup failed: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        return 1


# ==============================================================================
# Entry Point
# ==============================================================================

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
