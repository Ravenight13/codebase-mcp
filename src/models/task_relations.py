"""Task relationship models.

Supporting entities for task management:
- TaskPlanningReference: Links tasks to planning documents
- TaskBranchLink: Associates tasks with git branches
- TaskCommitLink: Associates tasks with git commits
- TaskStatusHistory: Tracks task status transitions

Entity Responsibilities:
- Provide many-to-many relationships for task tracking
- Enable git workflow integration (branches, commits)
- Maintain audit trail of status changes
- Support traceability from code to planning documents

Constitutional Compliance:
- Principle V: Production quality (unique constraints, proper indexes)
- Principle VIII: Type safety (full Mapped[] annotations)
- Principle X: Git micro-commits (commit tracking for atomic changes)
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

if TYPE_CHECKING:
    from .task import Task


class TaskPlanningReference(Base):
    """Links tasks to planning documents (spec.md, plan.md, etc.).

    Table: task_planning_references

    Relationships:
        - task: Many-to-one with Task

    Purpose:
        - Trace tasks back to requirements and design decisions
        - Support impact analysis when specs change
        - Enable documentation generation from tasks

    Reference Types:
        - spec: Feature specification (spec.md)
        - plan: Implementation plan (plan.md)
        - design: Design artifacts (data-model.md, contracts/, etc.)
        - other: Custom planning documents
    """

    __tablename__ = "task_planning_references"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Foreign keys
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False
    )

    # Reference fields
    file_path: Mapped[str] = mapped_column(
        String, nullable=False
    )  # Relative path to planning doc
    reference_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # spec|plan|design|other

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    task: Mapped[Task] = relationship(back_populates="planning_references")


class TaskBranchLink(Base):
    """Associates tasks with git branches.

    Table: task_branch_links

    Relationships:
        - task: Many-to-one with Task

    Indexes:
        - (task_id, branch_name): Unique composite

    Purpose:
        - Track which branch a task is implemented on
        - Support branch-per-feature workflow
        - Enable task filtering by branch

    Constitutional Compliance:
        - Principle X: Git workflow (feature branches ###-name)
    """

    __tablename__ = "task_branch_links"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Foreign keys
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False
    )

    # Branch metadata
    branch_name: Mapped[str] = mapped_column(String, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    task: Mapped[Task] = relationship(back_populates="branch_links")

    # Table-level constraints
    __table_args__ = (
        Index("ix_branch_links_task_branch", "task_id", "branch_name", unique=True),
    )


class TaskCommitLink(Base):
    """Associates tasks with git commits.

    Table: task_commit_links

    Relationships:
        - task: Many-to-one with Task

    Indexes:
        - (task_id, commit_hash): Unique composite

    Purpose:
        - Track which commits implement a task
        - Support micro-commit workflow (one commit per task)
        - Enable task completion verification via git log

    Constitutional Compliance:
        - Principle X: Git micro-commits (atomic commits after each task)
    """

    __tablename__ = "task_commit_links"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Foreign keys
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False
    )

    # Commit metadata
    commit_hash: Mapped[str] = mapped_column(
        String(40), nullable=False
    )  # Git SHA-1 (40 hex chars)
    commit_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    task: Mapped[Task] = relationship(back_populates="commit_links")

    # Table-level constraints
    __table_args__ = (
        Index("ix_commit_links_task_commit", "task_id", "commit_hash", unique=True),
    )


class TaskStatusHistory(Base):
    """Tracks task status transitions over time.

    Table: task_status_history

    Relationships:
        - task: Many-to-one with Task

    Indexes:
        - changed_at: B-tree for temporal queries

    Purpose:
        - Audit trail of status changes
        - Calculate task metrics (time in status, cycle time)
        - Support workflow analysis and optimization

    Status Transitions:
        - Creation: from_status=None, to_status='need to be done'
        - Start work: from_status='need to be done', to_status='in-progress'
        - Complete: from_status='in-progress', to_status='complete'
        - Reopened: from_status='complete', to_status='in-progress' (allowed)
    """

    __tablename__ = "task_status_history"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Foreign keys
    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False
    )

    # Status transition
    from_status: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # None on creation
    to_status: Mapped[str] = mapped_column(String, nullable=False)

    # Timestamps
    changed_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )

    # Relationships
    task: Mapped[Task] = relationship(back_populates="status_history")
