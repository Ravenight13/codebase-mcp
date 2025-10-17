"""Auto-create project from config file with registry integration.

This module provides automatic project provisioning from .codebase-mcp/config.json files.
It integrates with the database-per-project architecture by creating isolated project
databases on-demand when config files reference non-existent projects.

Constitutional Compliance:
- Principle V: Production quality with comprehensive error handling
- Principle VIII: Type safety with mypy --strict compliance
- Principle XI: FastMCP Foundation with async operations

Algorithm:
1. Parse config to get project.name and optional project.id
2. If project.id exists, lookup and return existing project database
3. If not found by ID, lookup by name in registry
4. If not found at all, create new project database automatically
5. Update config file with project.id if it was missing

Usage:
    >>> from src.database.auto_create import get_or_create_project_from_config
    >>> from pathlib import Path
    >>> config_path = Path("/path/to/.codebase-mcp/config.json")
    >>> project = await get_or_create_project_from_config(config_path)
    >>> print(project.database_name)
    'cb_proj_my_project_abc123de'
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field
from src.auto_switch.validation import validate_config_syntax
from src.database.provisioning import (
    create_project_database,
    generate_database_name,
)
from src.mcp.mcp_logging import get_logger

if TYPE_CHECKING:
    pass

# ==============================================================================
# Module Configuration
# ==============================================================================

logger = get_logger(__name__)

# ==============================================================================
# Project Model
# ==============================================================================


class Project(BaseModel):
    """Project metadata for database-per-project architecture.

    Represents a project workspace with its own isolated PostgreSQL database.
    Each project has:
    - Unique UUID identifier (project_id)
    - Human-readable name
    - Dedicated database (cb_proj_*)
    - Creation and update timestamps

    This model is compatible with workflow-mcp's Project model but simplified
    for codebase-mcp's local-first, config-based approach.
    """

    project_id: str = Field(..., description="Project UUID (without hyphens)")
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    database_name: str = Field(
        ..., description="Physical database name (cb_proj_*)"
    )
    description: str = Field(default="", description="Project description")

    class Config:
        """Pydantic model configuration."""

        frozen = False  # Allow mutation for updates


# ==============================================================================
# Project Registry (In-Memory)
# ==============================================================================


class ProjectRegistry:
    """In-memory project registry for tracking created projects.

    This is a simplified registry that tracks projects by name and ID without
    a persistent registry database. For codebase-mcp, we rely on:
    1. Config files (.codebase-mcp/config.json) as source of truth
    2. Physical database existence (cb_proj_* databases)
    3. In-memory tracking during server runtime

    Future Enhancement: Persistent registry database for cross-session tracking
    (similar to workflow-mcp's registry architecture).
    """

    def __init__(self) -> None:
        """Initialize empty in-memory registry."""
        self._projects_by_id: dict[str, Project] = {}
        self._projects_by_name: dict[str, Project] = {}

    def get_by_id(self, project_id: str) -> Project | None:
        """Get project by UUID.

        Args:
            project_id: Project UUID (with or without hyphens)

        Returns:
            Project if found, None otherwise
        """
        # Normalize UUID (remove hyphens for consistent lookup)
        normalized_id = project_id.replace("-", "").lower()
        return self._projects_by_id.get(normalized_id)

    def get_by_name(self, name: str) -> Project | None:
        """Get project by name (case-sensitive).

        Args:
            name: Project name

        Returns:
            Project if found, None otherwise
        """
        return self._projects_by_name.get(name)

    def add(self, project: Project) -> None:
        """Add project to registry.

        Args:
            project: Project to add
        """
        normalized_id = project.project_id.replace("-", "").lower()
        self._projects_by_id[normalized_id] = project
        self._projects_by_name[project.name] = project

        logger.info(
            f"Added project to registry: {project.name}",
            extra={
                "context": {
                    "operation": "registry_add",
                    "project_id": project.project_id,
                    "project_name": project.name,
                    "database_name": project.database_name,
                }
            },
        )


# Singleton registry instance
_registry_instance: ProjectRegistry | None = None


def get_registry() -> ProjectRegistry:
    """Get singleton registry instance.

    Returns:
        ProjectRegistry singleton
    """
    global _registry_instance  # noqa: PLW0603
    if _registry_instance is None:
        _registry_instance = ProjectRegistry()
    return _registry_instance


# ==============================================================================
# Config File Operations
# ==============================================================================


def read_config(config_path: Path) -> dict[str, any]:
    """Read and parse config file.

    Args:
        config_path: Path to .codebase-mcp/config.json

    Returns:
        Parsed config dictionary

    Raises:
        ValueError: If config is invalid
    """
    # Use validation module for consistent error handling
    return validate_config_syntax(config_path)


def write_config(config_path: Path, config: dict[str, any]) -> None:
    """Write config file atomically.

    Uses atomic write pattern (write to temp, then rename) to prevent
    corruption if interrupted.

    Args:
        config_path: Path to .codebase-mcp/config.json
        config: Config dictionary to write

    Raises:
        ValueError: If write fails
    """
    try:
        # Write to temporary file first
        temp_path = config_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
            f.write("\n")  # Add trailing newline

        # Atomic rename
        temp_path.replace(config_path)

        logger.debug(
            f"Updated config file: {config_path}",
            extra={"context": {"operation": "write_config", "path": str(config_path)}},
        )
    except (OSError, IOError) as e:
        raise ValueError(f"Failed to write config file {config_path}: {e}") from e


# ==============================================================================
# Project Auto-Creation
# ==============================================================================


async def get_or_create_project_from_config(
    config_path: Path,
    registry: ProjectRegistry | None = None,
) -> Project:
    """Get or create project from config file.

    Algorithm:
    1. Parse config to get project.name and optional project.id
    2. If project.id exists, lookup and return existing project
    3. If not found by ID, lookup by name
    4. If not found at all, create new project automatically
    5. Update config file with project.id if it was missing

    Args:
        config_path: Path to .codebase-mcp/config.json
        registry: Optional ProjectRegistry instance (uses singleton if None)

    Returns:
        Project (existing or newly created)

    Raises:
        ValueError: If config is invalid or project creation fails

    Example:
        >>> config_path = Path("/path/to/.codebase-mcp/config.json")
        >>> project = await get_or_create_project_from_config(config_path)
        >>> print(project.database_name)
        'cb_proj_my_project_abc123de'
    """
    if registry is None:
        registry = get_registry()

    # Step 1: Parse config
    logger.debug(
        f"Reading config: {config_path}",
        extra={"context": {"operation": "get_or_create_project", "path": str(config_path)}},
    )

    try:
        config = read_config(config_path)
    except ValueError as e:
        logger.error(
            f"Invalid config file: {config_path}",
            extra={
                "context": {
                    "operation": "get_or_create_project",
                    "path": str(config_path),
                    "error": str(e),
                }
            },
        )
        raise

    project_name = config["project"]["name"]
    project_id = config["project"].get("id")  # Optional

    logger.info(
        f"Processing config for project: {project_name}",
        extra={
            "context": {
                "operation": "get_or_create_project",
                "project_name": project_name,
                "has_project_id": project_id is not None,
            }
        },
    )

    # Step 2: Lookup by ID if provided
    if project_id:
        existing = registry.get_by_id(project_id)
        if existing:
            logger.debug(
                f"Found existing project by ID: {project_name}",
                extra={
                    "context": {
                        "operation": "get_or_create_project",
                        "project_id": project_id,
                        "database_name": existing.database_name,
                    }
                },
            )
            return existing

    # Step 3: Lookup by name
    existing = registry.get_by_name(project_name)
    if existing:
        # Update config with project.id if missing
        if not project_id:
            logger.info(
                f"Updating config with project ID: {existing.project_id}",
                extra={
                    "context": {
                        "operation": "get_or_create_project",
                        "project_name": project_name,
                        "project_id": existing.project_id,
                    }
                },
            )
            config["project"]["id"] = existing.project_id
            write_config(config_path, config)

        return existing

    # Step 4: Create new project
    if not project_id:
        project_id = str(uuid.uuid4())
        logger.info(
            f"Generated new project ID: {project_id}",
            extra={
                "context": {
                    "operation": "get_or_create_project",
                    "project_name": project_name,
                    "project_id": project_id,
                }
            },
        )

    # Generate database name
    database_name = generate_database_name(project_name, project_id)

    logger.info(
        f"Creating new project database: {database_name}",
        extra={
            "context": {
                "operation": "get_or_create_project",
                "project_name": project_name,
                "project_id": project_id,
                "database_name": database_name,
            }
        },
    )

    # Create database and initialize schema
    try:
        await create_project_database(project_name, project_id)
    except Exception as e:
        logger.error(
            f"Failed to create project database: {database_name}",
            extra={
                "context": {
                    "operation": "get_or_create_project",
                    "database_name": database_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            },
        )
        raise ValueError(f"Failed to create project database: {e}") from e

    # Create Project instance
    project = Project(
        project_id=project_id,
        name=project_name,
        database_name=database_name,
        description=config.get("description", ""),
    )

    # Add to registry
    registry.add(project)

    # Sync to persistent PostgreSQL registry
    # This ensures the project survives server restarts and is discoverable by Tier 1 resolution
    try:
        from src.database.session import _initialize_registry_pool

        registry_pool = await _initialize_registry_pool()
        async with registry_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO projects (id, name, description, database_name, created_at, updated_at, metadata)
                VALUES ($1, $2, $3, $4, NOW(), NOW(), $5::jsonb)
                ON CONFLICT (id) DO UPDATE SET updated_at = NOW()
                """,
                project_id,
                project_name,
                project.description or "",  # Handle None
                database_name,
                json.dumps({}),  # metadata as JSON string
            )
        logger.info(
            f"Synced project to persistent registry: {project_name}",
            extra={
                "context": {
                    "operation": "get_or_create_project",
                    "project_id": project_id,
                    "database_name": database_name,
                    "sync": "postgresql",
                }
            },
        )
    except Exception as e:
        # Don't fail project creation if registry sync fails
        # The in-memory registry is sufficient for current session
        logger.warning(
            f"Failed to sync project to persistent registry (continuing): {e}",
            extra={
                "context": {
                    "operation": "get_or_create_project",
                    "project_id": project_id,
                    "error": str(e),
                }
            },
        )

    # Step 5: Update config with project.id
    if config["project"].get("id") != project_id:
        logger.info(
            f"Updating config with project ID: {project_id}",
            extra={
                "context": {
                    "operation": "get_or_create_project",
                    "path": str(config_path),
                    "project_id": project_id,
                }
            },
        )
        config["project"]["id"] = project_id
        write_config(config_path, config)

    logger.info(
        f"✓ Project ready: {project_name}",
        extra={
            "context": {
                "operation": "get_or_create_project",
                "project_name": project_name,
                "project_id": project_id,
                "database_name": database_name,
                "created": True,
            }
        },
    )

    return project


# ==============================================================================
# Type Exports
# ==============================================================================

__all__ = [
    "Project",
    "ProjectRegistry",
    "get_registry",
    "get_or_create_project_from_config",
    "read_config",
    "write_config",
]
