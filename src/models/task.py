"""Task model and schemas for development task management.

Represents development tasks with status tracking, planning references,
git integration, and status history.

Entity Responsibilities:
- Track task metadata (title, description, notes)
- Enforce valid status transitions (need to be done -> in-progress -> complete)
- One-to-many relationships with planning references, branches, commits, status history
- Automatic timestamp updates on modification

Constitutional Compliance:
- Principle V: Production quality (check constraints, status validation)
- Principle VIII: Type safety (full Mapped[] annotations, Pydantic validation)
- Principle X: Git micro-commits (commit links for traceability)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import CheckConstraint, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

if TYPE_CHECKING:
    from .task_relations import (
        TaskBranchLink,
        TaskCommitLink,
        TaskPlanningReference,
        TaskStatusHistory,
    )


class Task(Base):
    """SQLAlchemy model for development tasks.

    Table: tasks

    Relationships:
        - planning_references: One-to-many with TaskPlanningReference
        - branch_links: One-to-many with TaskBranchLink
        - commit_links: One-to-many with TaskCommitLink
        - status_history: One-to-many with TaskStatusHistory

    Indexes:
        - status: B-tree for filtering by status

    Constraints:
        - status: Check constraint for valid values

    Status Values:
        - need to be done: Initial state
        - in-progress: Task being worked on
        - complete: Task finished

    Timestamps:
        - created_at: Set on creation
        - updated_at: Auto-updated on any modification
    """

    __tablename__ = "tasks"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Core fields
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="need to be done", index=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    planning_references: Mapped[list[TaskPlanningReference]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    branch_links: Mapped[list[TaskBranchLink]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    commit_links: Mapped[list[TaskCommitLink]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    status_history: Mapped[list[TaskStatusHistory]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )

    # Table-level constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('need to be done', 'in-progress', 'complete')",
            name="valid_status",
        ),
    )


# Pydantic Schemas


class TaskCreate(BaseModel):
    """Schema for creating a new task.

    Validation:
        - title: Required, 1-200 characters
        - planning_references: List of relative file paths to planning docs
    """

    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: str | None = Field(None, description="Detailed task description")
    notes: str | None = Field(None, description="Additional notes or context")
    planning_references: list[str] = Field(
        default_factory=list, description="Relative file paths to planning docs"
    )

    model_config = {"from_attributes": True}


class TaskUpdate(BaseModel):
    """Schema for updating an existing task.

    Validation:
        - status: Must be valid status value if provided
        - All fields optional (partial updates supported)
    """

    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    notes: str | None = None
    status: str | None = Field(
        None, pattern="^(need to be done|in-progress|complete)$"
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate status is one of the allowed values."""
        if v is not None:
            allowed = {"need to be done", "in-progress", "complete"}
            if v not in allowed:
                raise ValueError(f"Status must be one of {allowed}")
        return v

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    """Schema for task API responses.

    Includes:
        - All core task fields
        - planning_references: List of file paths
        - branches: List of associated branch names
        - commits: List of associated commit hashes

    Usage:
        Used in GET /tasks and GET /tasks/{id} endpoints
        Includes aggregated data from relationships
    """

    id: uuid.UUID
    title: str
    description: str | None
    notes: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    planning_references: list[str] = Field(
        default_factory=list, description="Planning document file paths"
    )
    branches: list[str] = Field(
        default_factory=list, description="Associated git branches"
    )
    commits: list[str] = Field(
        default_factory=list, description="Associated git commit hashes"
    )

    model_config = {"from_attributes": True}
