"""Alembic environment configuration for async SQLAlchemy.

This module configures Alembic to work with async SQLAlchemy and asyncpg driver
for PostgreSQL database migrations.

Constitutional Compliance:
- Principle V: Production quality (proper async handling, error logging)
- Principle VIII: Type safety (mypy --strict compliance)

Migration Strategy:
- Async operations for all database interactions
- Automatic model detection via Base.metadata
- Support for offline SQL generation
- Connection pooling disabled for migrations
"""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import Base and all models for auto-detection
from src.models import Base
from src.models.code_chunk import CodeChunk
from src.models.code_file import CodeFile
from src.models.repository import Repository
from src.models.task import Task
from src.models.task_relations import (
    TaskBranchLink,
    TaskCommitLink,
    TaskPlanningReference,
    TaskStatusHistory,
)
from src.models.tracking import ChangeEvent, EmbeddingMetadata, SearchQuery

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

# Override sqlalchemy.url with environment variable if set
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    Output:
        SQL statements written to stdout (for review or execution elsewhere)
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with an active connection.

    Args:
        connection: Active SQLAlchemy connection for migration execution

    Configuration:
        - compare_type: Detect column type changes
        - compare_server_default: Detect default value changes
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine.

    Creates an async Engine and associates a connection with the context.
    Supports asyncpg driver for PostgreSQL.

    Configuration:
        - poolclass: NullPool (no connection pooling for migrations)
        - Future: True (SQLAlchemy 2.0 style)
    """
    # Get configuration and create async engine
    configuration = config.get_section(config.config_ini_section, {})
    sqlalchemy_url = config.get_main_option("sqlalchemy.url")
    if sqlalchemy_url is None:
        raise ValueError("sqlalchemy.url is not configured in alembic.ini")
    configuration["sqlalchemy.url"] = sqlalchemy_url

    # Create async engine with no connection pooling
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    async with connectable.connect() as connection:
        # Run migrations synchronously within async context
        await connection.run_sync(do_run_migrations)

    # Dispose of engine
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (async).

    Entry point for online migrations. Delegates to async implementation.
    """
    asyncio.run(run_async_migrations())


# Determine mode and run migrations
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
