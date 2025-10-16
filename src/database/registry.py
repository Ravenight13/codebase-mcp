"""Project registry service for database-per-project architecture.

This module provides the Project model and ProjectRegistry service for managing
the central registry database that tracks all project databases in the
registry + database-per-project architecture.

Constitutional Compliance:
- Principle V: Production quality with comprehensive error handling
- Principle VIII: Type safety with mypy --strict compliance
- Principle XI: FastMCP Foundation with async operations

Architecture:
- Registry Database: codebase_mcp_registry (central registry)
- Project Databases: cb_proj_{name}_{hash} (isolated per project)

Usage:
    >>> from src.database.registry import ProjectRegistry, Project
    >>> from src.database.provisioning import create_pool
    >>>
    >>> # Initialize registry service
    >>> registry_pool = await create_pool("codebase_mcp_registry")
    >>> registry = ProjectRegistry(registry_pool)
    >>>
    >>> # Create project (provisions database automatically)
    >>> project = await registry.create_project(
    ...     name="My Project",
    ...     description="Example project"
    ... )
    >>> print(project.database_name)
    'cb_proj_my_project_abc123de'
    >>>
    >>> # Query projects
    >>> all_projects = await registry.list_projects()
    >>> project = await registry.get_project(project.id)
    >>> project = await registry.get_project_by_name("My Project")
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any

import asyncpg
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.database.provisioning import create_project_database, generate_database_name
from src.mcp.mcp_logging import get_logger

# ==============================================================================
# Module Configuration
# ==============================================================================

logger = get_logger(__name__)

# ==============================================================================
# Pydantic Models
# ==============================================================================


class Project(BaseModel):
    """Pydantic model for project registry records.

    Represents a project in the central registry database with validation
    for all fields according to database schema constraints.

    Fields:
        id: Unique UUID identifier for the project
        name: Human-readable project name (unique, alphanumeric + spaces/hyphens/underscores)
        description: Optional project description
        database_name: Physical database name following cb_proj_* convention
        created_at: Timestamp when project was created
        updated_at: Timestamp when project was last updated
        metadata: Flexible JSONB storage for additional project information

    Example:
        >>> project = Project(
        ...     id="550e8400-e29b-41d4-a716-446655440000",
        ...     name="My Project",
        ...     description="Example project",
        ...     database_name="cb_proj_my_project_abc123de",
        ...     created_at=datetime.now(),
        ...     updated_at=datetime.now(),
        ...     metadata={"owner": "alice@example.com"}
        ... )
    """

    model_config = ConfigDict(
        frozen=False,  # Allow updates to mutable fields
        extra="forbid",  # Reject unexpected fields
        str_strip_whitespace=True,  # Clean string inputs
    )

    id: str = Field(
        ...,
        description="Unique UUID identifier",
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    )
    name: str = Field(
        ...,
        description="Human-readable project name (unique)",
        min_length=1,
        max_length=255,
    )
    description: str | None = Field(
        default=None,
        description="Optional project description",
    )
    database_name: str = Field(
        ...,
        description="Physical database name (cb_proj_*)",
        min_length=1,
        max_length=255,
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when project was created",
    )
    updated_at: datetime = Field(
        ...,
        description="Timestamp when project was last updated",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Flexible JSONB storage for project metadata",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate project name format (alphanumeric + spaces/hyphens/underscores).

        Args:
            v: Project name to validate

        Returns:
            Validated project name

        Raises:
            ValueError: If name contains invalid characters
        """
        if not re.match(r"^[a-zA-Z0-9_ -]+$", v):
            raise ValueError(
                f"Invalid project name: {v}. "
                "Name must contain only alphanumeric characters, spaces, hyphens, and underscores."
            )
        return v

    @field_validator("database_name")
    @classmethod
    def validate_database_name(cls, v: str) -> str:
        """Validate database name format (cb_proj_*).

        Args:
            v: Database name to validate

        Returns:
            Validated database name

        Raises:
            ValueError: If database name does not match cb_proj_* pattern
        """
        if not re.match(r"^cb_proj_[a-z0-9_]+_[a-f0-9]{8}$", v):
            raise ValueError(
                f"Invalid database name: {v}. "
                "Must match pattern: cb_proj_{{name}}_{{hash}}"
            )
        return v


# ==============================================================================
# Project Registry Service
# ==============================================================================


class ProjectRegistry:
    """Service class for managing project registry operations.

    Provides high-level operations for creating, querying, and managing
    projects in the central registry database. Automatically provisions
    isolated project databases when creating new projects.

    Args:
        registry_pool: AsyncPG connection pool for registry database

    Example:
        >>> from src.database.provisioning import create_pool
        >>> registry_pool = await create_pool("codebase_mcp_registry")
        >>> registry = ProjectRegistry(registry_pool)
        >>>
        >>> # Create project
        >>> project = await registry.create_project("My Project")
        >>>
        >>> # Query projects
        >>> projects = await registry.list_projects()
        >>> project = await registry.get_project(project.id)
    """

    def __init__(self, registry_pool: asyncpg.Pool) -> None:
        """Initialize ProjectRegistry with connection pool.

        Args:
            registry_pool: AsyncPG connection pool for registry database
        """
        self._pool = registry_pool
        logger.debug(
            "ProjectRegistry initialized",
            extra={"context": {"operation": "init", "pool_size": registry_pool.get_size()}},
        )

    async def create_project(
        self,
        name: str,
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Project:
        """Create a new project with isolated database provisioning.

        Creates a project record in the registry AND provisions a new isolated
        PostgreSQL database for the project. This is a transactional operation:
        - On success: Project record created and database provisioned
        - On failure: Registry record rolled back (database may exist if provisioning failed)

        Args:
            name: Human-readable project name (unique, 1-255 chars)
            description: Optional project description (default: empty string)
            metadata: Optional JSONB metadata (default: empty dict)

        Returns:
            Project instance with all fields populated

        Raises:
            ValueError: If name format is invalid or already exists
            asyncpg.DuplicateDatabaseError: If database provisioning fails (duplicate)
            asyncpg.PostgresError: If database operation fails

        Example:
            >>> project = await registry.create_project(
            ...     name="My Project",
            ...     description="Example project",
            ...     metadata={"owner": "alice@example.com"}
            ... )
            >>> print(project.id)
            '550e8400-e29b-41d4-a716-446655440000'
            >>> print(project.database_name)
            'cb_proj_my_project_abc123de'
        """
        # Validate name format
        if not re.match(r"^[a-zA-Z0-9_ -]+$", name):
            raise ValueError(
                f"Invalid project name: {name}. "
                "Name must contain only alphanumeric characters, spaces, hyphens, and underscores."
            )

        # Generate project UUID
        project_id = str(uuid.uuid4())

        # Generate database name
        database_name = generate_database_name(name, project_id)

        logger.info(
            f"Creating project: {name}",
            extra={
                "context": {
                    "operation": "create_project",
                    "name": name,
                    "project_id": project_id,
                    "database_name": database_name,
                }
            },
        )

        # Provision project database FIRST (fail fast if provisioning fails)
        try:
            await create_project_database(name, project_id)
            logger.info(
                f"✓ Project database provisioned: {database_name}",
                extra={
                    "context": {
                        "operation": "create_project",
                        "database_name": database_name,
                    }
                },
            )
        except asyncpg.DuplicateDatabaseError as e:
            logger.error(
                f"Database already exists: {database_name}",
                extra={
                    "context": {
                        "operation": "create_project",
                        "database_name": database_name,
                        "error": str(e),
                    }
                },
            )
            raise ValueError(f"Database already exists: {database_name}") from e
        except Exception as e:
            logger.error(
                f"Failed to provision database: {database_name}",
                extra={
                    "context": {
                        "operation": "create_project",
                        "database_name": database_name,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                },
            )
            raise

        # Insert project record into registry
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO projects (id, name, description, database_name, metadata)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING id, name, description, database_name, created_at, updated_at, metadata
                    """,
                    project_id,
                    name,
                    description,
                    database_name,
                    metadata or {},
                )

                if row is None:
                    raise RuntimeError(f"Failed to insert project record: {name}")

                project = Project(
                    id=str(row["id"]),
                    name=row["name"],
                    description=row["description"],
                    database_name=row["database_name"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    metadata=dict(row["metadata"]) if row["metadata"] else {},
                )

                logger.info(
                    f"✓ Project created successfully: {name}",
                    extra={
                        "context": {
                            "operation": "create_project",
                            "project_id": project.id,
                            "database_name": project.database_name,
                        }
                    },
                )

                return project

        except asyncpg.UniqueViolationError as e:
            logger.error(
                f"Project name already exists: {name}",
                extra={
                    "context": {
                        "operation": "create_project",
                        "name": name,
                        "error": str(e),
                    }
                },
            )
            raise ValueError(f"Project name already exists: {name}") from e
        except Exception as e:
            logger.error(
                f"Failed to create project record: {name}",
                extra={
                    "context": {
                        "operation": "create_project",
                        "name": name,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                },
            )
            raise

    async def get_project(self, project_id: str) -> Project | None:
        """Get project by UUID.

        Args:
            project_id: Project UUID to lookup

        Returns:
            Project instance or None if not found

        Example:
            >>> project = await registry.get_project("550e8400-e29b-41d4-a716-446655440000")
            >>> if project:
            ...     print(project.name)
        """
        logger.debug(
            f"Getting project by ID: {project_id}",
            extra={"context": {"operation": "get_project", "project_id": project_id}},
        )

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, name, description, database_name, created_at, updated_at, metadata
                FROM projects
                WHERE id = $1
                """,
                project_id,
            )

            if row is None:
                logger.debug(
                    f"Project not found: {project_id}",
                    extra={"context": {"operation": "get_project", "project_id": project_id}},
                )
                return None

            return Project(
                id=str(row["id"]),
                name=row["name"],
                description=row["description"],
                database_name=row["database_name"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                metadata=dict(row["metadata"]) if row["metadata"] else {},
            )

    async def get_project_by_name(self, name: str) -> Project | None:
        """Get project by name.

        Args:
            name: Project name to lookup

        Returns:
            Project instance or None if not found

        Example:
            >>> project = await registry.get_project_by_name("My Project")
            >>> if project:
            ...     print(project.id)
        """
        logger.debug(
            f"Getting project by name: {name}",
            extra={"context": {"operation": "get_project_by_name", "name": name}},
        )

        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, name, description, database_name, created_at, updated_at, metadata
                FROM projects
                WHERE name = $1
                """,
                name,
            )

            if row is None:
                logger.debug(
                    f"Project not found: {name}",
                    extra={"context": {"operation": "get_project_by_name", "name": name}},
                )
                return None

            return Project(
                id=str(row["id"]),
                name=row["name"],
                description=row["description"],
                database_name=row["database_name"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                metadata=dict(row["metadata"]) if row["metadata"] else {},
            )

    async def list_projects(self) -> list[Project]:
        """List all projects ordered by creation date (newest first).

        Returns:
            List of Project instances

        Example:
            >>> projects = await registry.list_projects()
            >>> for project in projects:
            ...     print(f"{project.name}: {project.database_name}")
        """
        logger.debug(
            "Listing all projects",
            extra={"context": {"operation": "list_projects"}},
        )

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, name, description, database_name, created_at, updated_at, metadata
                FROM projects
                ORDER BY created_at DESC
                """
            )

            projects = [
                Project(
                    id=str(row["id"]),
                    name=row["name"],
                    description=row["description"],
                    database_name=row["database_name"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    metadata=dict(row["metadata"]) if row["metadata"] else {},
                )
                for row in rows
            ]

            logger.debug(
                f"Found {len(projects)} projects",
                extra={"context": {"operation": "list_projects", "count": len(projects)}},
            )

            return projects

    async def delete_project(self, project_id: str, confirmed: bool = False) -> None:
        """Soft delete a project (requires confirmation).

        NOTE: This only deletes the registry record. The physical database
        is NOT automatically dropped to prevent accidental data loss.
        Use DROP DATABASE manually if you want to remove the database.

        Args:
            project_id: Project UUID to delete
            confirmed: Explicit confirmation required (must be True)

        Raises:
            ValueError: If confirmation not provided or project not found

        Example:
            >>> await registry.delete_project(
            ...     project_id="550e8400-e29b-41d4-a716-446655440000",
            ...     confirmed=True
            ... )
        """
        if not confirmed:
            raise ValueError(
                "Project deletion requires explicit confirmation. "
                "Set confirmed=True to proceed."
            )

        logger.warning(
            f"Deleting project: {project_id}",
            extra={
                "context": {
                    "operation": "delete_project",
                    "project_id": project_id,
                    "confirmed": confirmed,
                }
            },
        )

        async with self._pool.acquire() as conn:
            # Check if project exists
            project = await self.get_project(project_id)
            if project is None:
                raise ValueError(f"Project not found: {project_id}")

            # Delete from registry
            result = await conn.execute(
                """
                DELETE FROM projects
                WHERE id = $1
                """,
                project_id,
            )

            if result == "DELETE 0":
                raise ValueError(f"Project not found: {project_id}")

            logger.warning(
                f"✓ Project deleted from registry: {project.name}",
                extra={
                    "context": {
                        "operation": "delete_project",
                        "project_id": project_id,
                        "database_name": project.database_name,
                        "warning": f"Physical database {project.database_name} still exists. Drop manually if needed.",
                    }
                },
            )


# ==============================================================================
# Public API
# ==============================================================================

__all__ = [
    "Project",
    "ProjectRegistry",
]
