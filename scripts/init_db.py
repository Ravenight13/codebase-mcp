#!/usr/bin/env python3
"""Database initialization script for Codebase MCP Server.

This script initializes the PostgreSQL database by:
1. Validating database connection and pgvector extension availability
2. Running Alembic migrations to create schema
3. Verifying table and index creation
4. Providing detailed error messages for troubleshooting

Constitutional Compliance:
- Principle V: Production quality (comprehensive error handling, validation)
- Principle VIII: Type safety (mypy --strict compliance)

Usage:
    python scripts/init_db.py --database-url postgresql+asyncpg://localhost/codebase_mcp
    python scripts/init_db.py  # Uses DATABASE_URL environment variable

Exit Codes:
    0 - Success (database initialized)
    1 - Error (connection failed, migration failed, etc.)
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any, NoReturn

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


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
    sys.exit(1)


def success_message(message: str) -> None:
    """Print success message to stdout.

    Args:
        message: Success message to display
    """
    print(f"✅ {message}")


async def check_database_connection(engine: AsyncEngine) -> None:
    """Verify database connection is working.

    Args:
        engine: Async SQLAlchemy engine

    Raises:
        Exception: If connection fails

    Checks:
        - Database connectivity
        - Basic query execution
    """
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()
        success_message("Database connection successful")
    except Exception as e:
        error_exit(
            "Failed to connect to database",
            f"Check that PostgreSQL is running and connection string is correct.\n{e}",
        )


async def check_pgvector_extension(engine: AsyncEngine) -> None:
    """Verify pgvector extension is available.

    Args:
        engine: Async SQLAlchemy engine

    Raises:
        Exception: If pgvector extension is not available

    Checks:
        - pgvector extension installation
        - Extension creation permission
    """
    try:
        async with engine.connect() as conn:
            # Try to create extension (idempotent)
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.commit()

            # Verify extension exists
            result = await conn.execute(
                text(
                    "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                )
            )
            exists = result.scalar()

            if not exists:
                error_exit(
                    "pgvector extension not available",
                    "Install pgvector: https://github.com/pgvector/pgvector#installation",
                )

        success_message("pgvector extension available")
    except Exception as e:
        error_exit(
            "Failed to enable pgvector extension",
            f"Ensure you have permission to create extensions.\n{e}",
        )


def run_alembic_migrations(database_url: str) -> None:
    """Run Alembic migrations to create database schema.

    Args:
        database_url: PostgreSQL connection string

    Raises:
        Exception: If migration fails

    Operations:
        - Loads alembic.ini configuration
        - Sets database URL
        - Runs 'alembic upgrade head'
    """
    try:
        # Get path to alembic.ini (should be in project root)
        project_root = Path(__file__).parent.parent
        alembic_ini_path = project_root / "alembic.ini"

        if not alembic_ini_path.exists():
            error_exit(
                "alembic.ini not found",
                f"Expected location: {alembic_ini_path}",
            )

        # Create Alembic config
        alembic_cfg = Config(str(alembic_ini_path))
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)

        # Run migrations
        success_message("Running Alembic migrations...")
        command.upgrade(alembic_cfg, "head")
        success_message("Alembic migrations completed")

    except Exception as e:
        error_exit(
            "Failed to run Alembic migrations",
            f"Check migration files for errors.\n{e}",
        )


async def verify_schema(engine: AsyncEngine) -> None:
    """Verify database schema was created correctly.

    Args:
        engine: Async SQLAlchemy engine

    Raises:
        Exception: If schema verification fails

    Verifies:
        - All 11 tables exist
        - HNSW index on code_chunks.embedding exists
        - Key indexes exist
    """
    expected_tables = [
        "repositories",
        "code_files",
        "code_chunks",
        "tasks",
        "task_planning_references",
        "task_branch_links",
        "task_commit_links",
        "task_status_history",
        "change_events",
        "embedding_metadata",
        "search_queries",
    ]

    try:
        async with engine.connect() as conn:
            # Check tables
            result = await conn.execute(
                text(
                    """
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """
                )
            )
            tables = [row[0] for row in result.fetchall()]

            missing_tables = set(expected_tables) - set(tables)
            if missing_tables:
                error_exit(
                    "Missing database tables",
                    f"Tables not found: {', '.join(sorted(missing_tables))}",
                )

            success_message(f"All {len(expected_tables)} tables created")

            # Check HNSW index exists
            result = await conn.execute(
                text(
                    """
                    SELECT indexname
                    FROM pg_indexes
                    WHERE tablename = 'code_chunks'
                      AND indexname = 'ix_chunks_embedding_cosine'
                """
                )
            )
            hnsw_index = result.fetchone()

            if not hnsw_index:
                error_exit(
                    "HNSW index not created",
                    "Index 'ix_chunks_embedding_cosine' missing on code_chunks table",
                )

            success_message("HNSW index created on code_chunks.embedding")

            # Count total indexes
            result = await conn.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                """
                )
            )
            index_count = result.scalar()

            success_message(f"Total indexes created: {index_count}")

    except Exception as e:
        error_exit(
            "Failed to verify database schema",
            str(e),
        )


async def initialize_database(database_url: str) -> None:
    """Main database initialization workflow.

    Args:
        database_url: PostgreSQL connection string

    Workflow:
        1. Create async engine
        2. Check database connection
        3. Verify pgvector extension
        4. Run Alembic migrations
        5. Verify schema creation
        6. Dispose engine
    """
    print("\n🚀 Initializing Codebase MCP Database\n")
    print(f"Database URL: {database_url.split('@')[-1]}\n")

    # Create async engine (no pooling for initialization)
    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
    )

    try:
        # Step 1: Check connection
        await check_database_connection(engine)

        # Step 2: Verify pgvector
        await check_pgvector_extension(engine)

        # Step 3: Run migrations (synchronous Alembic)
        run_alembic_migrations(database_url)

        # Step 4: Verify schema
        await verify_schema(engine)

        print("\n" + "=" * 60)
        print("✅ Database initialization complete!")
        print("=" * 60)
        print("\nYou can now:")
        print("  - Start the MCP server: uvicorn src.main:app")
        print("  - Run tests: pytest")
        print("  - Check migrations: alembic history")
        print()

    finally:
        # Clean up engine
        await engine.dispose()


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments with database_url

    Arguments:
        --database-url: PostgreSQL connection string (optional)
    """
    parser = argparse.ArgumentParser(
        description="Initialize Codebase MCP Server database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use environment variable DATABASE_URL
  python scripts/init_db.py

  # Specify database URL directly
  python scripts/init_db.py --database-url postgresql+asyncpg://user:pass@localhost/codebase_mcp

  # Local development (default PostgreSQL)
  python scripts/init_db.py --database-url postgresql+asyncpg://localhost/codebase_mcp
        """,
    )

    parser.add_argument(
        "--database-url",
        type=str,
        help="PostgreSQL connection string (default: DATABASE_URL env var)",
    )

    return parser.parse_args()


def main() -> None:
    """Entry point for database initialization script.

    Validates arguments, checks environment, and runs initialization.

    Exit Codes:
        0 - Success
        1 - Error (validation, connection, migration, etc.)
    """
    args = parse_arguments()

    # Get database URL from argument or environment
    database_url = args.database_url or os.getenv("DATABASE_URL")

    if not database_url:
        error_exit(
            "No database URL provided",
            "Set DATABASE_URL environment variable or use --database-url argument",
        )

    # Validate URL format
    if not database_url.startswith("postgresql"):
        error_exit(
            "Invalid database URL",
            "URL must start with 'postgresql://' or 'postgresql+asyncpg://'",
        )

    # Ensure asyncpg driver is specified
    if "+asyncpg" not in database_url:
        # Convert postgresql:// to postgresql+asyncpg://
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        print(f"⚠️  Note: Using asyncpg driver (converted URL)")

    # Run initialization
    try:
        asyncio.run(initialize_database(database_url))
    except KeyboardInterrupt:
        print("\n\n⚠️  Initialization cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        error_exit("Unexpected error during initialization", str(e))


if __name__ == "__main__":
    main()
