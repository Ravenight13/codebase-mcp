"""Database package providing async session management for PostgreSQL.

This package provides:
- Async SQLAlchemy session factory with connection pooling
- Context manager for automatic transaction management
- Database health check functionality
- Type-safe session access patterns

Constitutional Compliance:
- Principle VIII: Type safety (complete type annotations)
- Principle XI: FastMCP Foundation (async patterns for MCP tools)

Usage:
    >>> from src.database import get_session, check_database_health
    >>> async with get_session() as session:
    ...     result = await session.execute(select(Repository))
"""

from __future__ import annotations

from src.database.session import (
    DATABASE_URL,
    SessionLocal,
    check_database_health,
    close_db_connection,
    engine,
    get_session,
    get_session_factory,
    init_db_connection,
)

__all__ = [
    "engine",
    "SessionLocal",
    "get_session",
    "get_session_factory",
    "check_database_health",
    "init_db_connection",
    "close_db_connection",
    "DATABASE_URL",
]
