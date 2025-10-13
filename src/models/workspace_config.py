"""Workspace configuration model for multi-project isolation.

Immutable Pydantic model representing project workspace metadata and PostgreSQL
schema configuration. Each workspace provides isolated storage for a project's
repositories, code files, and embeddings.

Model Responsibilities:
- Store immutable workspace configuration (project_id, schema_name)
- Track workspace creation timestamps
- Provide extensible metadata storage for future features
- Enforce immutability to prevent accidental configuration changes

Constitutional Compliance:
- Principle VIII: Pydantic-based type safety (mypy --strict)
- Principle V: Production quality (immutable config, clear validation)
- Principle I: Simplicity over features (minimal fields, future extensibility via metadata)

Functional Requirements:
- FR-009: System MUST provision isolated PostgreSQL schemas per project
- FR-010: System MUST auto-provision workspace on first project use
- FR-011: System MUST track workspace creation timestamps

Storage Mapping:
This model maps to the PostgreSQL table:
    CREATE TABLE project_registry.workspace_config (
        project_id VARCHAR(50) PRIMARY KEY,
        schema_name VARCHAR(60) NOT NULL UNIQUE,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        metadata JSONB DEFAULT '{}'::jsonb
    );
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.models.project_identifier import ProjectIdentifier


class WorkspaceConfig(BaseModel):
    """Project workspace metadata and configuration (immutable after creation).

    Represents an isolated workspace for a single project with its own PostgreSQL
    schema. Once created, configuration cannot be modified (frozen=True) to ensure
    consistency across all workspace operations.

    Example Usage:
        >>> config = WorkspaceConfig(
        ...     project_id="client-a",
        ...     schema_name="project_client_a"
        ... )
        >>> config.project_id
        'client-a'
        >>> config.schema_name
        'project_client_a'
        >>> config.created_at  # Auto-generated timestamp
        datetime.datetime(2025, 10, 12, 10, 30, 0)

        >>> # Immutability enforcement
        >>> config.project_id = "client-b"  # Raises ValidationError
        ValidationError: "WorkspaceConfig" is frozen and does not support item assignment

    Attributes:
        project_id: Validated project identifier (must match ProjectIdentifier format)
        schema_name: PostgreSQL schema name (e.g., "project_client_a")
        created_at: UTC timestamp when workspace was provisioned
        metadata: Optional key-value metadata for future extensibility

    Immutability:
        This model uses ConfigDict(frozen=True) to prevent modification after
        creation. This ensures workspace configuration remains consistent across
        all operations and prevents accidental state corruption.
    """

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "examples": [
                {
                    "project_id": "client-a",
                    "schema_name": "project_client_a",
                    "created_at": "2025-10-12T10:30:00Z",
                    "metadata": {},
                },
                {
                    "project_id": "frontend-app",
                    "schema_name": "project_frontend_app",
                    "created_at": "2025-10-12T11:45:00Z",
                    "metadata": {"description": "Main frontend application"},
                },
            ]
        },
    )

    project_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Validated project identifier (must match ProjectIdentifier format)",
        examples=["client-a", "frontend-app", "my-project-123"],
    )

    schema_name: str = Field(
        ...,
        min_length=1,
        max_length=60,
        pattern=r"^project_[a-z0-9]+(_[a-z0-9]+)*$",
        description="PostgreSQL schema name (e.g., project_client_a)",
        examples=["project_client_a", "project_frontend_app", "project_my_project_123"],
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when workspace was provisioned",
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata (reserved for future features like descriptions, tags, owner info)",
        examples=[
            {},
            {"description": "Main frontend application"},
            {"owner": "engineering-team", "tags": ["production", "critical"]},
        ],
    )

    @classmethod
    def from_identifier(
        cls, identifier: ProjectIdentifier, metadata: dict[str, Any] | None = None
    ) -> WorkspaceConfig:
        """Create WorkspaceConfig from validated ProjectIdentifier.

        Convenience factory method that automatically generates the PostgreSQL
        schema name from a validated ProjectIdentifier.

        Args:
            identifier: Validated ProjectIdentifier instance
            metadata: Optional metadata dictionary (default: empty dict)

        Returns:
            New WorkspaceConfig instance with auto-generated schema name

        Example:
            >>> identifier = ProjectIdentifier(value="client-a")
            >>> config = WorkspaceConfig.from_identifier(identifier)
            >>> config.project_id
            'client-a'
            >>> config.schema_name
            'project_client_a'
        """
        return cls(
            project_id=identifier.value,
            schema_name=identifier.to_schema_name(),
            metadata=metadata or {},
        )
