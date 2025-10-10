"""Example usage of the async session factory for database operations.

This file demonstrates how to use the database session factory in MCP tools
and other async contexts.

Constitutional Compliance:
- Principle XI: FastMCP Foundation (async session for MCP tools)
- Principle VIII: Type safety (complete type annotations)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from src.database import check_database_health, get_session
from src.models.repository import Repository

if TYPE_CHECKING:
    from uuid import UUID


# ==============================================================================
# Basic Session Usage
# ==============================================================================


async def example_basic_query() -> list[Repository]:
    """Basic query example using the session context manager.

    Returns:
        List of all repositories in the database

    Example:
        >>> repos = await example_basic_query()
        >>> for repo in repos:
        ...     print(f"Repository: {repo.path}")
    """
    async with get_session() as session:
        # Execute query
        result = await session.execute(select(Repository))
        repos = result.scalars().all()

        # Session automatically commits on exit
        return list(repos)


# ==============================================================================
# Create Operation Example
# ==============================================================================


async def example_create_repository(path: str) -> Repository:
    """Create a new repository with automatic transaction management.

    Args:
        path: Absolute path to the repository

    Returns:
        Created repository object

    Example:
        >>> repo = await example_create_repository("/path/to/repo")
        >>> print(f"Created repo with ID: {repo.id}")
    """
    async with get_session() as session:
        # Create new repository
        repo = Repository(path=path)

        # Add to session
        session.add(repo)

        # Flush to get ID before commit
        await session.flush()

        # Session automatically commits on exit
        return repo


# ==============================================================================
# Update Operation Example
# ==============================================================================


async def example_update_repository(repo_id: UUID, new_path: str) -> Repository | None:
    """Update a repository with error handling.

    Args:
        repo_id: UUID of the repository to update
        new_path: New path for the repository

    Returns:
        Updated repository or None if not found

    Example:
        >>> from uuid import uuid4
        >>> repo_id = uuid4()
        >>> updated_repo = await example_update_repository(repo_id, "/new/path")
    """
    async with get_session() as session:
        # Query for repository
        result = await session.execute(select(Repository).where(Repository.id == repo_id))
        repo = result.scalar_one_or_none()

        if repo is None:
            return None

        # Update repository
        repo.path = new_path

        # Session automatically commits on exit
        return repo


# ==============================================================================
# Error Handling Example
# ==============================================================================


async def example_with_error_handling(path: str) -> Repository | None:
    """Example with explicit error handling.

    Args:
        path: Repository path

    Returns:
        Created repository or None on error

    Example:
        >>> repo = await example_with_error_handling("/path/to/repo")
        >>> if repo:
        ...     print("Repository created successfully")
        ... else:
        ...     print("Failed to create repository")
    """
    try:
        async with get_session() as session:
            repo = Repository(path=path)
            session.add(repo)
            await session.flush()
            return repo

    except Exception as e:
        # Session automatically rolls back on exception
        print(f"Error creating repository: {e}")
        return None


# ==============================================================================
# Health Check Example
# ==============================================================================


async def example_health_check() -> dict[str, str]:
    """Check database health status.

    Returns:
        Health status dictionary

    Example:
        >>> status = await example_health_check()
        >>> print(f"Database status: {status['database']}")
    """
    is_healthy = await check_database_health()

    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "database": "ok" if is_healthy else "error",
    }


# ==============================================================================
# MCP Tool Integration Example
# ==============================================================================


async def example_mcp_tool_handler(repo_path: str) -> dict[str, str]:
    """Example MCP tool handler using the session factory.

    This demonstrates how to use the session factory in MCP tool implementations.

    Args:
        repo_path: Path to the repository

    Returns:
        Dictionary with result information

    Example (as MCP tool):
        >>> @mcp.tool()
        >>> async def create_repository(repo_path: str) -> dict[str, str]:
        ...     return await example_mcp_tool_handler(repo_path)
    """
    try:
        # Use session context manager
        async with get_session() as session:
            # Create repository
            repo = Repository(path=repo_path)
            session.add(repo)
            await session.flush()

            # Return success response
            return {
                "status": "success",
                "repo_id": str(repo.id),
                "path": repo.path,
            }

    except Exception as e:
        # Return error response
        return {
            "status": "error",
            "error": str(e),
        }


# ==============================================================================
# Batch Operation Example
# ==============================================================================


async def example_batch_create(paths: list[str]) -> int:
    """Create multiple repositories in a single transaction.

    Args:
        paths: List of repository paths

    Returns:
        Number of repositories created

    Example:
        >>> paths = ["/repo1", "/repo2", "/repo3"]
        >>> count = await example_batch_create(paths)
        >>> print(f"Created {count} repositories")
    """
    async with get_session() as session:
        # Create multiple repositories
        repos = [Repository(path=path) for path in paths]

        # Add all to session
        session.add_all(repos)

        # Session automatically commits all changes
        return len(repos)


# ==============================================================================
# Query with Filtering Example
# ==============================================================================


async def example_query_with_filter(path_prefix: str) -> list[Repository]:
    """Query repositories with filtering.

    Args:
        path_prefix: Path prefix to filter by

    Returns:
        List of matching repositories

    Example:
        >>> repos = await example_query_with_filter("/home/user/")
        >>> for repo in repos:
        ...     print(f"Repo: {repo.path}")
    """
    async with get_session() as session:
        # Execute filtered query
        result = await session.execute(
            select(Repository).where(Repository.path.startswith(path_prefix))
        )
        repos = result.scalars().all()

        return list(repos)
