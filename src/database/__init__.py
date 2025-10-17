"""Database package providing async session management for PostgreSQL.

This package provides:
- Async SQLAlchemy session factory with connection pooling
- Context manager for automatic transaction management
- Database health check functionality
- Type-safe session access patterns
- Database-per-project architecture support
- Project registry and auto-provisioning

Database-Per-Project Architecture:
    This package supports isolated project databases with automatic provisioning:

    - **Session Management**: Multi-database session routing via resolve_project_id
    - **Project Registry**: In-memory tracking of created projects
    - **Auto-Provisioning**: Automatic database creation from config files
    - **Connection Pools**: Efficient pooling for project databases

Constitutional Compliance:
- Principle VIII: Type safety (complete type annotations)
- Principle XI: FastMCP Foundation (async patterns for MCP tools)

Usage:
    >>> from src.database import get_session, check_database_health
    >>> async with get_session() as session:
    ...     result = await session.execute(select(Repository))

    >>> # Auto-create project from config
    >>> from src.database import get_or_create_project_from_config
    >>> from pathlib import Path
    >>> config_path = Path(".codebase-mcp/config.json")
    >>> project = await get_or_create_project_from_config(config_path)
"""

from __future__ import annotations

from src.database.auto_create import (
    Project,
    ProjectRegistry,
    get_or_create_project_from_config,
    get_registry,
)
from src.database.provisioning import (
    create_pool,
    create_project_database,
    generate_database_name,
)
from src.database.session import (
    DATABASE_URL,
    SessionLocal,
    check_database_health,
    close_db_connection,
    engine,
    get_session,
    get_session_factory,
    init_db_connection,
    resolve_project_id,
)

__all__ = [
    # Session management
    "engine",
    "SessionLocal",
    "get_session",
    "get_session_factory",
    "check_database_health",
    "init_db_connection",
    "close_db_connection",
    "DATABASE_URL",
    "resolve_project_id",
    # Project provisioning
    "create_project_database",
    "create_pool",
    "generate_database_name",
    # Project registry
    "Project",
    "ProjectRegistry",
    "get_registry",
    "get_or_create_project_from_config",
]
