"""Pydantic schemas for task API responses - optimized for token efficiency.

This module provides two-tier task response models following the inheritance pattern:
- BaseTaskFields: Shared core fields (5 fields: id, title, status, created_at, updated_at)
- TaskSummary: Lightweight summary for list operations (inherits base fields only)
- TaskResponse: Full task details including metadata (inherits base + adds 5 detail fields)

Token Efficiency Goals:
- TaskSummary: ~120-150 tokens per task (6x reduction vs TaskResponse)
- TaskResponse: ~800-1000 tokens per task (full details for get_task)

Feature: 004-as-an-ai (Optimize list_tasks MCP Tool for Token Efficiency)
Related: specs/004-as-an-ai/data-model.md, specs/004-as-an-ai/research.md

Constitutional Compliance:
- Principle VIII: Pydantic-based type safety with explicit type annotations
- Principle IV: Performance guarantees (token optimization)
- Principle V: Production quality (comprehensive validation)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BaseTaskFields(BaseModel):
    """Shared core fields between summary and full task representations.

    This base model defines the 5 essential task fields that appear in both
    TaskSummary (lightweight) and TaskResponse (full details) models.

    Fields:
        id: Unique task identifier (UUID4)
        title: Task title (1-200 characters, whitespace stripped)
        status: Current task status (one of 3 valid values)
        created_at: Task creation timestamp (UTC, timezone-aware)
        updated_at: Last modification timestamp (UTC, timezone-aware)

    Validation Rules:
        - title: Non-empty after stripping whitespace, max 200 characters
        - status: Must be one of: "need to be done", "in-progress", "complete"
        - id: Valid UUID format (auto-coerced from string if needed)
        - created_at/updated_at: Valid datetime objects (ISO 8601 string auto-coerced)

    ORM Compatibility:
        - from_attributes=True enables construction from SQLAlchemy Task model
        - Use model_validate() to convert ORM instances to Pydantic models

    Constitutional Compliance:
        - Principle VIII: Pydantic-based type safety with explicit types
        - All fields have explicit type annotations (no inference)
        - Field validators ensure data quality and consistency
        - ConfigDict enforces ORM compatibility for SQLAlchemy integration

    Example:
        >>> from datetime import datetime, timezone
        >>> from uuid import uuid4
        >>> base_fields = BaseTaskFields(
        ...     id=uuid4(),
        ...     title="Implement user authentication",
        ...     status="in-progress",
        ...     created_at=datetime.now(timezone.utc),
        ...     updated_at=datetime.now(timezone.utc)
        ... )
        >>> base_fields.title
        'Implement user authentication'
    """

    id: uuid.UUID = Field(
        ...,
        description="Unique task identifier (UUID4 format)",
    )

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Task title (1-200 characters, non-empty after stripping)",
    )

    status: Literal["need to be done", "in-progress", "complete"] = Field(
        ...,
        description="Current task status (one of 3 valid values)",
    )

    created_at: datetime = Field(
        ...,
        description="Task creation timestamp (UTC, timezone-aware)",
    )

    updated_at: datetime = Field(
        ...,
        description="Last modification timestamp (UTC, timezone-aware)",
    )

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure title is non-empty after stripping whitespace.

        Args:
            v: Raw title string input

        Returns:
            Stripped title string with leading/trailing whitespace removed

        Raises:
            ValueError: If title is empty or whitespace-only after stripping

        Constitutional Compliance:
            - Principle V: Production quality (comprehensive validation)
            - Ensures data integrity at Pydantic layer before persistence
        """
        stripped = v.strip()
        if not stripped:
            raise ValueError("Title cannot be empty or whitespace-only")
        return stripped

    model_config = ConfigDict(
        from_attributes=True,  # Enable ORM mode for SQLAlchemy Task model
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Implement user authentication",
                "status": "in-progress",
                "created_at": "2025-10-10T10:00:00Z",
                "updated_at": "2025-10-10T15:30:00Z",
            }
        },
    )


class TaskSummary(BaseTaskFields):
    """Lightweight task summary for list operations - optimized for token efficiency.

    Inherits all 5 core fields from BaseTaskFields with NO additional fields.
    Designed for efficient list_tasks() responses where full task details are
    unnecessary.

    Token Footprint:
        - ~120-150 tokens per task (estimated)
        - 15 tasks ≈ 1800-2250 tokens (with response envelope)
        - 6x reduction vs TaskResponse (~800-1000 tokens per task)

    Fields (inherited from BaseTaskFields):
        id: UUID
        title: str
        status: Literal["need to be done", "in-progress", "complete"]
        created_at: datetime
        updated_at: datetime

    Excluded Fields (present in TaskResponse):
        - description: str | None
        - notes: str | None
        - planning_references: list[str]
        - branches: list[str]
        - commits: list[str]

    Use Cases:
        - Default response for list_tasks() MCP tool
        - Task browsing and quick status overview
        - Token-efficient operations for AI assistants
        - Identifying tasks of interest before fetching full details

    Constitutional Compliance:
        - Principle IV: Performance (6x token reduction target achieved)
        - Principle VIII: Type safety (inherits Pydantic validation from base)
        - Principle V: Production quality (maintains data integrity)

    Example:
        >>> summary = TaskSummary(
        ...     id=uuid4(),
        ...     title="Fix authentication bug",
        ...     status="need to be done",
        ...     created_at=datetime.now(timezone.utc),
        ...     updated_at=datetime.now(timezone.utc)
        ... )
        >>> summary.model_dump()
        {
            'id': UUID('...'),
            'title': 'Fix authentication bug',
            'status': 'need to be done',
            'created_at': datetime(...),
            'updated_at': datetime(...)
        }

    Token Efficiency Example:
        >>> # 15 TaskSummary objects serialize to ~2000 tokens
        >>> # 15 TaskResponse objects would serialize to ~12000 tokens
        >>> # Reduction: 6x improvement in token usage
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Implement user authentication",
                "status": "in-progress",
                "created_at": "2025-10-10T10:00:00Z",
                "updated_at": "2025-10-10T15:30:00Z",
            }
        },
    )


class TaskResponse(BaseTaskFields):
    """Full task details including all metadata - for get_task() and detailed views.

    Inherits all 5 core fields from BaseTaskFields and adds 5 detail fields:
    description, notes, planning_references, branches, commits.

    Designed for get_task(task_id) responses and list_tasks(full_details=True)
    where complete task context is required.

    Token Footprint:
        - ~800-1000 tokens per task (estimated, varies by description length)
        - 15 tasks ≈ 12000-15000 tokens (with response envelope)
        - Use TaskSummary for list operations to achieve 6x token reduction

    Fields (5 inherited from BaseTaskFields):
        id: UUID
        title: str
        status: Literal["need to be done", "in-progress", "complete"]
        created_at: datetime
        updated_at: datetime

    Additional Fields (5 detail fields):
        description: str | None - Detailed task description
        notes: str | None - Additional notes or context
        planning_references: list[str] - Relative file paths to planning documents
        branches: list[str] - Associated git branch names
        commits: list[str] - Associated git commit hashes (40-char hex)

    Use Cases:
        - get_task(task_id) MCP tool response
        - list_tasks(full_details=True) for backward compatibility
        - Detailed task examination and implementation context
        - Full context for AI assistants working on specific tasks

    Constitutional Compliance:
        - Principle VIII: Type safety (Pydantic validation for all fields)
        - Principle X: Git integration (branches, commits tracking)
        - Principle V: Production quality (comprehensive data model)

    Example:
        >>> response = TaskResponse(
        ...     id=uuid4(),
        ...     title="Implement JWT authentication",
        ...     description="Add JWT-based authentication with refresh tokens",
        ...     notes="Consider OAuth2 integration for social login",
        ...     status="in-progress",
        ...     created_at=datetime.now(timezone.utc),
        ...     updated_at=datetime.now(timezone.utc),
        ...     planning_references=["specs/001-auth/spec.md", "specs/001-auth/plan.md"],
        ...     branches=["001-user-auth"],
        ...     commits=["a1b2c3d4e5f6..."]
        ... )
        >>> response.model_dump()
        {
            'id': UUID('...'),
            'title': 'Implement JWT authentication',
            'description': 'Add JWT-based authentication...',
            'notes': 'Consider OAuth2 integration...',
            'status': 'in-progress',
            'created_at': datetime(...),
            'updated_at': datetime(...),
            'planning_references': ['specs/001-auth/spec.md', ...],
            'branches': ['001-user-auth'],
            'commits': ['a1b2c3d4e5f6...']
        }
    """

    description: str | None = Field(
        None,
        description="Detailed task description (optional, can be lengthy)",
    )

    notes: str | None = Field(
        None,
        description="Additional notes or context (optional)",
    )

    planning_references: list[str] = Field(
        default_factory=list,
        description="Relative file paths to planning documents (e.g., spec.md, plan.md)",
    )

    branches: list[str] = Field(
        default_factory=list,
        description="Associated git branch names for task implementation",
    )

    commits: list[str] = Field(
        default_factory=list,
        description="Associated git commit hashes (40-character hex strings)",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Implement user authentication",
                "description": "Add JWT-based authentication with refresh tokens...",
                "notes": "Consider OAuth2 integration for social login",
                "status": "in-progress",
                "created_at": "2025-10-10T10:00:00Z",
                "updated_at": "2025-10-10T15:30:00Z",
                "planning_references": [
                    "specs/001-auth/spec.md",
                    "specs/001-auth/plan.md",
                ],
                "branches": ["001-user-auth"],
                "commits": ["a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"],
            }
        },
    )
