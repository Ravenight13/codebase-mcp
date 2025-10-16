"""Database provisioning utilities for project database management.

This module provides utilities for creating and managing isolated project databases
in the registry + database-per-project architecture.

Constitutional Compliance:
- Principle V: Production quality with comprehensive error handling
- Principle VIII: Type safety with mypy --strict compliance
- Principle XI: FastMCP Foundation with async operations

Usage:
    >>> from src.database.provisioning import create_project_database
    >>> await create_project_database("cb_proj_my_project_abc123de")
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

import asyncpg
from src.mcp.mcp_logging import get_logger

if TYPE_CHECKING:
    pass

# ==============================================================================
# Module Configuration
# ==============================================================================

logger = get_logger(__name__)

# Project root directory for resolving SQL file paths
_PROJECT_ROOT = Path(__file__).parent.parent.parent

# Database connection defaults from environment
_DB_HOST = os.getenv("DB_HOST", "localhost")
_DB_PORT = int(os.getenv("DB_PORT", "5432"))
_DB_USER = os.getenv("DB_USER", os.getenv("USER", "postgres"))
_DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# ==============================================================================
# Database Name Generation
# ==============================================================================


def sanitize_name(name: str) -> str:
    """Sanitize project name for database naming.

    Converts to lowercase, replaces spaces/hyphens with underscores,
    removes non-alphanumeric characters, and limits length.

    Args:
        name: Raw project name

    Returns:
        Sanitized name suitable for database identifiers

    Example:
        >>> sanitize_name("My Project - 2024")
        'my_project_2024'
    """
    # Lowercase and replace spaces/hyphens with underscores
    sanitized = name.lower().replace(" ", "_").replace("-", "_")

    # Remove non-alphanumeric/underscore characters
    sanitized = re.sub(r"[^a-z0-9_]", "", sanitized)

    # Limit length (30 chars + 9 for prefix + 8 for hash = 47 chars total < 63 limit)
    return sanitized[:30]


def generate_database_name(project_name: str, uuid_str: str) -> str:
    """Generate database name from project name and UUID.

    Format: cb_proj_{sanitized_name}_{uuid8}
    - cb_proj: Prefix for Codebase MCP projects
    - sanitized_name: Lowercase, underscores, max 30 chars
    - uuid8: First 8 characters of UUID (without hyphens)

    Args:
        project_name: Human-readable project name
        uuid_str: UUID string (with or without hyphens)

    Returns:
        Database name following naming convention

    Example:
        >>> generate_database_name("My Project", "abc123de-f456-7890-abcd-ef0123456789")
        'cb_proj_my_project_abc123de'
    """
    sanitized = sanitize_name(project_name)
    uuid_hash = uuid_str.replace("-", "")[:8].lower()
    return f"cb_proj_{sanitized}_{uuid_hash}"


# ==============================================================================
# Database Provisioning
# ==============================================================================


async def create_database(database_name: str, db_user: str | None = None) -> None:
    """Create a new PostgreSQL database.

    Connects to the default 'postgres' database and creates a new database.
    Uses quoted identifiers to prevent SQL injection.

    Args:
        database_name: Name of database to create (must follow naming convention)
        db_user: Database user (defaults to environment or current user)

    Raises:
        asyncpg.DuplicateDatabaseError: If database already exists
        asyncpg.PostgresError: If creation fails

    Example:
        >>> await create_database("cb_proj_my_project_abc123de")
    """
    if db_user is None:
        db_user = _DB_USER

    # Validate database name format
    if not re.match(r"^cb_proj_[a-z0-9_]+_[a-f0-9]{8}$", database_name):
        raise ValueError(
            f"Invalid database name format: {database_name}. "
            "Must match: cb_proj_{{name}}_{{hash}}"
        )

    # Build DSN for postgres database
    dsn_parts = [
        f"postgresql://{db_user}",
        f"@{_DB_HOST}:{_DB_PORT}/postgres",
    ]
    if _DB_PASSWORD:
        dsn_parts[0] = f"postgresql://{db_user}:{_DB_PASSWORD}"

    dsn = "".join(dsn_parts)

    logger.info(
        f"Creating database: {database_name}",
        extra={
            "context": {
                "operation": "create_database",
                "database_name": database_name,
                "host": _DB_HOST,
                "port": _DB_PORT,
            }
        },
    )

    try:
        conn = await asyncpg.connect(dsn)
        try:
            # Cannot use parameters for database name in CREATE DATABASE
            # Using quoted identifier to prevent SQL injection
            await conn.execute(f'CREATE DATABASE "{database_name}"')
            logger.info(
                f"✓ Database created successfully: {database_name}",
                extra={"context": {"operation": "create_database", "database_name": database_name}},
            )
        finally:
            await conn.close()
    except asyncpg.DuplicateDatabaseError:
        logger.warning(
            f"Database already exists: {database_name}",
            extra={"context": {"operation": "create_database", "database_name": database_name}},
        )
        raise
    except asyncpg.PostgresError as e:
        logger.error(
            f"Failed to create database: {database_name}",
            extra={
                "context": {
                    "operation": "create_database",
                    "database_name": database_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            },
        )
        raise


async def initialize_project_schema(database_name: str, db_user: str | None = None) -> None:
    """Initialize project database schema from SQL file.

    Executes scripts/init_project_schema.sql in the specified database.
    Creates tables: repositories, code_files, code_chunks with pgvector support.

    Args:
        database_name: Target database name
        db_user: Database user (defaults to environment or current user)

    Raises:
        FileNotFoundError: If init_project_schema.sql not found
        asyncpg.PostgresError: If schema initialization fails

    Example:
        >>> await initialize_project_schema("cb_proj_my_project_abc123de")
    """
    if db_user is None:
        db_user = _DB_USER

    # Resolve SQL file path
    sql_file = _PROJECT_ROOT / "scripts" / "init_project_schema.sql"
    if not sql_file.exists():
        raise FileNotFoundError(f"Schema file not found: {sql_file}")

    # Build DSN for project database
    dsn_parts = [
        f"postgresql://{db_user}",
        f"@{_DB_HOST}:{_DB_PORT}/{database_name}",
    ]
    if _DB_PASSWORD:
        dsn_parts[0] = f"postgresql://{db_user}:{_DB_PASSWORD}"

    dsn = "".join(dsn_parts)

    logger.info(
        f"Initializing schema for database: {database_name}",
        extra={
            "context": {
                "operation": "initialize_schema",
                "database_name": database_name,
                "sql_file": str(sql_file),
            }
        },
    )

    try:
        # Read SQL file
        with open(sql_file) as f:
            sql = f.read()

        # Connect and execute
        conn = await asyncpg.connect(dsn)
        try:
            await conn.execute(sql)
            logger.info(
                f"✓ Schema initialized successfully: {database_name}",
                extra={
                    "context": {
                        "operation": "initialize_schema",
                        "database_name": database_name,
                        "tables": ["repositories", "code_files", "code_chunks"],
                    }
                },
            )
        finally:
            await conn.close()
    except FileNotFoundError:
        logger.error(
            f"Schema file not found: {sql_file}",
            extra={"context": {"operation": "initialize_schema", "sql_file": str(sql_file)}},
        )
        raise
    except asyncpg.PostgresError as e:
        logger.error(
            f"Failed to initialize schema: {database_name}",
            extra={
                "context": {
                    "operation": "initialize_schema",
                    "database_name": database_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            },
        )
        raise


async def create_project_database(
    project_name: str, project_uuid: str, db_user: str | None = None
) -> str:
    """Create and initialize a complete project database.

    High-level function that:
    1. Generates database name from project name and UUID
    2. Creates the physical database
    3. Initializes schema (repositories, code_files, code_chunks)

    Args:
        project_name: Human-readable project name
        project_uuid: Project UUID (with or without hyphens)
        db_user: Database user (defaults to environment or current user)

    Returns:
        Database name (cb_proj_*)

    Raises:
        ValueError: If database name format invalid
        asyncpg.DuplicateDatabaseError: If database already exists
        asyncpg.PostgresError: If creation or initialization fails

    Example:
        >>> db_name = await create_project_database(
        ...     "My Project",
        ...     "abc123de-f456-7890-abcd-ef0123456789"
        ... )
        >>> print(db_name)
        'cb_proj_my_project_abc123de'
    """
    # Generate database name
    database_name = generate_database_name(project_name, project_uuid)

    logger.info(
        f"Creating project database: {database_name}",
        extra={
            "context": {
                "operation": "create_project_database",
                "project_name": project_name,
                "project_uuid": project_uuid,
                "database_name": database_name,
            }
        },
    )

    # Step 1: Create database
    await create_database(database_name, db_user)

    # Step 2: Initialize schema
    await initialize_project_schema(database_name, db_user)

    logger.info(
        f"✓ Project database ready: {database_name}",
        extra={
            "context": {
                "operation": "create_project_database",
                "database_name": database_name,
                "status": "ready",
            }
        },
    )

    return database_name


# ==============================================================================
# Connection Utilities
# ==============================================================================


async def create_connection(database_name: str, db_user: str | None = None) -> asyncpg.Connection:
    """Create a connection to a specific database.

    Args:
        database_name: Target database name
        db_user: Database user (defaults to environment or current user)

    Returns:
        AsyncPG connection

    Raises:
        asyncpg.PostgresError: If connection fails

    Example:
        >>> conn = await create_connection("cb_proj_my_project_abc123de")
        >>> try:
        ...     result = await conn.fetchval("SELECT COUNT(*) FROM repositories")
        ... finally:
        ...     await conn.close()
    """
    if db_user is None:
        db_user = _DB_USER

    # Build DSN
    dsn_parts = [
        f"postgresql://{db_user}",
        f"@{_DB_HOST}:{_DB_PORT}/{database_name}",
    ]
    if _DB_PASSWORD:
        dsn_parts[0] = f"postgresql://{db_user}:{_DB_PASSWORD}"

    dsn = "".join(dsn_parts)

    return await asyncpg.connect(dsn)


async def create_pool(
    database_name: str,
    min_size: int = 2,
    max_size: int = 10,
    db_user: str | None = None,
) -> asyncpg.Pool:
    """Create a connection pool for a specific database.

    Args:
        database_name: Target database name
        min_size: Minimum pool size (default: 2)
        max_size: Maximum pool size (default: 10)
        db_user: Database user (defaults to environment or current user)

    Returns:
        AsyncPG connection pool

    Raises:
        asyncpg.PostgresError: If pool creation fails

    Example:
        >>> pool = await create_pool("cb_proj_my_project_abc123de")
        >>> async with pool.acquire() as conn:
        ...     result = await conn.fetchval("SELECT COUNT(*) FROM repositories")
    """
    if db_user is None:
        db_user = _DB_USER

    # Build DSN
    dsn_parts = [
        f"postgresql://{db_user}",
        f"@{_DB_HOST}:{_DB_PORT}/{database_name}",
    ]
    if _DB_PASSWORD:
        dsn_parts[0] = f"postgresql://{db_user}:{_DB_PASSWORD}"

    dsn = "".join(dsn_parts)

    logger.info(
        f"Creating connection pool: {database_name}",
        extra={
            "context": {
                "operation": "create_pool",
                "database_name": database_name,
                "min_size": min_size,
                "max_size": max_size,
            }
        },
    )

    return await asyncpg.create_pool(
        dsn,
        min_size=min_size,
        max_size=max_size,
        command_timeout=60,
    )
