"""Task model and schemas for development task management.

Represents development tasks with status tracking, planning references,
git integration, and status history.

EXTENDED for Feature 003: Polymorphic work items with hierarchical relationships.
The Task model is now an alias for WorkItem to maintain backward compatibility.

Entity Responsibilities:
- Track task metadata (title, description, notes)
- Support polymorphic work item types (project, session, task, research)
- Enforce hierarchical parent-child relationships (max depth 5)
- Enable type-specific metadata via Pydantic JSONB validation
- Manage work item dependencies (blocks/depends-on)
- Track git integration (branches, commits, PRs)
- Support soft delete and archiving (1+ year threshold)
- Optimistic locking for concurrent update protection
- Automatic timestamp updates on modification

Constitutional Compliance:
- Principle V: Production quality (check constraints, status validation)
- Principle VIII: Type safety (full Mapped[] annotations, Pydantic validation)
- Principle X: Git micro-commits (commit links for traceability)
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .types import PydanticJSON

if TYPE_CHECKING:
    from .task_relations import (
        TaskBranchLink,
        TaskCommitLink,
        TaskPlanningReference,
        TaskStatusHistory,
    )
    from .tracking import WorkItemDependency, WorkItemDeploymentLink

# Import Pydantic schemas for JSONB validation
try:
    # Add specs/003-database-backed-project/contracts to Python path
    specs_contracts_path = (
        Path(__file__).parent.parent.parent
        / "specs"
        / "003-database-backed-project"
        / "contracts"
    )
    if specs_contracts_path.exists() and str(specs_contracts_path) not in sys.path:
        sys.path.insert(0, str(specs_contracts_path))

    from pydantic_schemas import (  # type: ignore
        ProjectMetadata,
        ResearchMetadata,
        SessionMetadata,
        TaskMetadata,
        WorkItemMetadata,
    )
except ImportError:
    # Fallback for testing or if contracts not yet available
    from pydantic import BaseModel as FallbackBaseModel

    class ProjectMetadata(FallbackBaseModel):  # type: ignore
        """Fallback ProjectMetadata schema for development."""

        description: str
        target_quarter: str | None = None
        constitutional_principles: list[str] = Field(default_factory=list)

    class SessionMetadata(FallbackBaseModel):  # type: ignore
        """Fallback SessionMetadata schema for development."""

        token_budget: int = Field(ge=1000, le=1000000)
        prompts_count: int = Field(ge=0)
        yaml_frontmatter: dict[str, Any] = Field(default_factory=dict)

    class TaskMetadata(FallbackBaseModel):  # type: ignore
        """Fallback TaskMetadata schema for development."""

        estimated_hours: float | None = None
        actual_hours: float | None = None
        blocked_reason: str | None = None

    class ResearchMetadata(FallbackBaseModel):  # type: ignore
        """Fallback ResearchMetadata schema for development."""

        research_questions: list[str] = Field(default_factory=list)
        findings_summary: str | None = None
        references: list[str] = Field(default_factory=list)

    # Fallback union type
    WorkItemMetadata = (
        ProjectMetadata | SessionMetadata | TaskMetadata | ResearchMetadata
    )


class WorkItem(Base):
    """SQLAlchemy model for polymorphic work items (projects, sessions, tasks, research).

    Table: work_items (formerly tasks table, extended with new columns)

    BACKWARD COMPATIBILITY: Legacy Task functionality preserved via:
    - Existing columns: title, description, notes, status, created_at, updated_at
    - Existing relationships: planning_references, branch_links, commit_links, status_history
    - New item_type column defaults to "task" for legacy records

    NEW POLYMORPHIC FUNCTIONALITY (Feature 003):
    - item_type: Discriminator for polymorphic behavior (project, session, task, research)
    - Hierarchical relationships: parent_id, path (materialized), depth (0-5 levels)
    - Type-specific metadata: JSONB validated by Pydantic (ProjectMetadata | SessionMetadata | TaskMetadata | ResearchMetadata)
    - Git integration: branch_name, commit_hash, pr_number
    - Soft delete: deleted_at timestamp (preserve audit trail)
    - Optimistic locking: version column (prevent concurrent update conflicts)
    - Dependencies: Many-to-many via WorkItemDependency junction table
    - Deployment links: Many-to-many via WorkItemDeploymentLink junction table

    Relationships:
        - parent: Self-referential to WorkItem (nullable, one-to-many hierarchy)
        - children: List of child WorkItem (back_populates="parent")
        - dependencies_as_source: List[WorkItemDependency] (outgoing dependencies)
        - dependencies_as_target: List[WorkItemDependency] (incoming dependencies)
        - deployment_links: List[WorkItemDeploymentLink] (many-to-many with DeploymentEvent)
        - planning_references: One-to-many with TaskPlanningReference (LEGACY)
        - branch_links: One-to-many with TaskBranchLink (LEGACY)
        - commit_links: One-to-many with TaskCommitLink (LEGACY)
        - status_history: One-to-many with TaskStatusHistory (LEGACY)

    Indexes:
        - item_type: B-tree for filtering by work item type
        - parent_id: B-tree for hierarchical queries (recursive CTE)
        - path: B-tree for ancestor queries (materialized path)
        - status: B-tree for filtering active/completed/blocked items
        - deleted_at: Partial index (WHERE deleted_at IS NULL) for active items
        - created_at: B-tree for archiving threshold queries (1+ year)

    Constraints:
        - item_type: CHECK (item_type IN ('project', 'session', 'task', 'research'))
        - depth: CHECK (depth >= 0 AND depth <= 5)
        - status: CHECK (status IN ('active', 'completed', 'blocked', 'need to be done', 'in-progress', 'complete'))
        - parent_id: Foreign key to work_items.id, nullable, CASCADE delete

    Status Values:
        NEW (Feature 003):
        - active: Work item in progress (default for new polymorphic items)
        - completed: Work item finished
        - blocked: Work item blocked by dependency

        LEGACY (backward compatibility):
        - need to be done: Legacy task status (maps to "active")
        - in-progress: Legacy task status (maps to "active")
        - complete: Legacy task status (maps to "completed")

    Timestamps:
        - created_at: Set on creation (UTC)
        - updated_at: Auto-updated on any modification (UTC)
        - deleted_at: Soft delete timestamp (NULL = active, NOT NULL = deleted)

    Performance Targets:
        - <10ms for hierarchical queries up to 5 levels (FR-013)
        - <1ms for single work item lookup by ID
        - Archiving: Items with created_at < NOW() - INTERVAL '1 year' moved to archived_work_items

    Example Usage:
        >>> # Create a project work item
        >>> project = WorkItem(
        ...     item_type="project",
        ...     title="Implement semantic code search",
        ...     status="active",
        ...     path="/",
        ...     depth=0,
        ...     metadata_=ProjectMetadata(
        ...         description="Add semantic search to MCP server",
        ...         target_quarter="2025-Q1",
        ...         constitutional_principles=["Simplicity Over Features"]
        ...     ),
        ...     created_by="claude-code-v1"
        ... )
        >>>
        >>> # Create a child task under the project
        >>> task = WorkItem(
        ...     item_type="task",
        ...     title="Write indexing service",
        ...     status="active",
        ...     parent_id=project.id,
        ...     path=f"/{project.id}",
        ...     depth=1,
        ...     metadata_=TaskMetadata(
        ...         estimated_hours=4.0,
        ...         actual_hours=None,
        ...         blocked_reason=None
        ...     ),
        ...     created_by="claude-code-v1"
        ... )

    Constitutional Compliance:
        - Principle IV: Performance (<10ms hierarchical queries, archiving strategy)
        - Principle V: Production quality (CHECK constraints, optimistic locking, soft delete)
        - Principle VIII: Type safety (full Mapped[] annotations, Pydantic JSONB validation)
        - Principle X: Git micro-commits (git integration fields for traceability)
    """

    # NOTE: Temporarily keeping table name as "tasks" for backward compatibility
    # Will be renamed to "work_items" in Alembic migration (003_extend_work_items.py)
    __tablename__ = "tasks"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Optimistic locking (NEW - Feature 003)
    # NOTE: Do NOT set default when using version_id_col - SQLAlchemy manages version automatically
    # SQLAlchemy will initialize to None, then set to 1 on first INSERT
    version: Mapped[int] = mapped_column("version", Integer, nullable=False)

    # Core fields (EXISTING - preserved for backward compatibility)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Polymorphic discriminator (NEW - Feature 003)
    item_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="task", index=True
    )  # "project" | "session" | "task" | "research"

    # Status tracking (EXTENDED - supports both legacy and new statuses)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", index=True
    )  # "active" | "completed" | "blocked" | "need to be done" | "in-progress" | "complete"

    # Hierarchical fields (NEW - Feature 003)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    path: Mapped[str] = mapped_column(
        String(500), nullable=False, default="/", index=True
    )  # Materialized path: "/parent1/parent2/current"
    depth: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )  # 0-5 levels

    # Git integration (NEW - Feature 003)
    branch_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    commit_hash: Mapped[str | None] = mapped_column(String(40), nullable=True)
    pr_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Type-specific metadata (NEW - Feature 003)
    # NOTE: Using dict for now to avoid circular import issues
    # Will be properly typed with PydanticJSON(WorkItemMetadata) after schema validation
    from sqlalchemy.dialects.postgresql import JSONB

    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )

    # Soft delete (NEW - Feature 003)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Timestamps (EXISTING - preserved for backward compatibility)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Audit trail (NEW - Feature 003)
    created_by: Mapped[str] = mapped_column(
        String(100), nullable=False, default="system"
    )  # AI client identifier

    # Hierarchical relationships (NEW - Feature 003)
    parent: Mapped[WorkItem | None] = relationship(
        "WorkItem",
        remote_side=[id],
        back_populates="children",
        foreign_keys=[parent_id],
    )
    children: Mapped[list[WorkItem]] = relationship(
        "WorkItem",
        back_populates="parent",
        foreign_keys=[parent_id],
    )

    # Dependency relationships (NEW - Feature 003)
    dependencies_as_source: Mapped[list[WorkItemDependency]] = relationship(
        "WorkItemDependency",
        foreign_keys="WorkItemDependency.source_id",
        back_populates="source",
    )
    dependencies_as_target: Mapped[list[WorkItemDependency]] = relationship(
        "WorkItemDependency",
        foreign_keys="WorkItemDependency.target_id",
        back_populates="target",
    )

    # Deployment relationships (NEW - Feature 003)
    deployment_links: Mapped[list[WorkItemDeploymentLink]] = relationship(
        "WorkItemDeploymentLink",
        back_populates="work_item",
        cascade="all, delete-orphan",
    )

    # Legacy relationships (EXISTING - preserved for backward compatibility)
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

    # Mapper configuration for optimistic locking
    # MUST be defined after all columns, before __table_args__
    __mapper_args__ = {"version_id_col": version}

    # Table-level constraints
    __table_args__ = (
        CheckConstraint(
            "item_type IN ('project', 'session', 'task', 'research')",
            name="ck_work_item_type",
        ),
        CheckConstraint(
            "depth >= 0 AND depth <= 5",
            name="ck_work_item_depth",
        ),
        CheckConstraint(
            "status IN ('active', 'completed', 'blocked', 'need to be done', 'in-progress', 'complete')",
            name="ck_work_item_status",
        ),
    )


# Backward compatibility alias: Task = WorkItem
# This ensures existing code and relationships in task_relations.py continue to work
Task = WorkItem

# Register Task as an alias in the SQLAlchemy registry for relationship resolution
# This allows task_relations.py to reference 'Task' in back_populates
# WorkItem._sa_registry.register_alias(Task, "Task")


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

    LEGACY MODEL: This model is preserved for backward compatibility.
    For new code, use the optimized models from task_schemas:
    - TaskSummary: Lightweight summary for list operations (6x token reduction)
    - TaskResponse (in task_schemas): Full details with inheritance from BaseTaskFields

    Includes:
        - All core task fields
        - planning_references: List of file paths
        - branches: List of associated branch names
        - commits: List of associated commit hashes

    Usage:
        Used in GET /tasks and GET /tasks/{id} endpoints
        Includes aggregated data from relationships

    Migration Note:
        This legacy TaskResponse will be deprecated in favor of task_schemas.TaskResponse
        which inherits from BaseTaskFields for better type reuse and token efficiency.
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
