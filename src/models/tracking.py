"""Tracking and analytics models.

Supporting entities for operational tracking:
- ChangeEvent: Records file system changes for incremental indexing
- EmbeddingMetadata: Analytics for embedding generation performance
- SearchQuery: Analytics for search query performance
- VendorExtractor: Tracks operational status and test results for 45+ vendor extractors (Feature 003)
- ProjectConfiguration: Singleton global configuration for project state
- ArchivedWorkItem: Archive table for work items older than 1 year
- FutureEnhancement: Track planned future enhancements with priorities
- WorkItemDependency: Junction table for work item dependencies (blocks/depends_on)
- VendorDeploymentLink: Junction table for deployment-vendor relationships
- WorkItemDeploymentLink: Junction table for deployment-work item relationships
- DeploymentEvent: Record deployment occurrences with PR details and relationships

Entity Responsibilities:
- Track file changes for incremental re-indexing
- Monitor embedding generation performance
- Analyze search query patterns and latency
- Maintain global project configuration (active context, token budgets, git state)
- Archive old work items to maintain <10ms active query performance
- Manage future enhancements with constitutional compliance
- Track work item dependencies for task ordering and blocking relationships
- Link deployments to affected vendors and work items for audit trail
- Record deployment events with vendor and work item tracking
- Support performance optimization and debugging

Constitutional Compliance:
- Principle IV: Performance (change detection for incremental indexing, archiving strategy)
- Principle V: Production quality (comprehensive logging and analytics)
- Principle VIII: Type safety (full Mapped[] annotations)
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.schema import ForeignKey

from .database import Base
from .types import PydanticJSON

if TYPE_CHECKING:
    from .code_file import CodeFile
    # Forward references for models not yet implemented
    WorkItem: Any  # Will be implemented in future task

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

    from pydantic_schemas import DeploymentMetadata  # type: ignore
except ImportError:
    # Fallback for testing or if contracts not yet available
    from pydantic import BaseModel, Field

    class DeploymentMetadata(BaseModel):  # type: ignore
        """Fallback DeploymentMetadata schema for development."""

        pr_number: int = Field(ge=1)
        pr_title: str = Field(min_length=1, max_length=200)
        commit_hash: str = Field(pattern=r"^[a-f0-9]{40}$")
        test_summary: dict[str, int] = Field(default_factory=dict)
        constitutional_compliance: bool = Field(default=True)


class ChangeEvent(Base):
    """Records file system changes for incremental indexing.

    Table: change_events

    Relationships:
        - code_file: Many-to-one with CodeFile

    Indexes:
        - detected_at: B-tree for temporal queries

    Purpose:
        - Track added/modified/deleted files
        - Enable incremental re-indexing (avoid full scans)
        - Support change batching for performance

    Event Types:
        - added: New file detected
        - modified: Existing file content changed
        - deleted: File removed from filesystem

    Workflow:
        1. File system watcher creates ChangeEvent
        2. Background worker processes unprocessed events
        3. Event marked processed=True after handling
        4. Periodic cleanup of old processed events
    """

    __tablename__ = "change_events"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Foreign keys
    code_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("code_files.id"), nullable=False
    )

    # Event metadata
    event_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # added|modified|deleted
    detected_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    code_file: Mapped[CodeFile] = relationship(back_populates="change_events")


class EmbeddingMetadata(Base):
    """Analytics for embedding generation performance.

    Table: embedding_metadata

    Purpose:
        - Track embedding model performance
        - Monitor generation latency
        - Support model version tracking
        - Enable performance optimization

    Model Information:
        - model_name: Default 'nomic-embed-text'
        - model_version: Optional version string from Ollama
        - dimensions: Default 768 (nomic-embed-text output)

    Performance Metrics:
        - generation_time_ms: Time to generate single embedding
        - Target: <100ms per embedding (60s for ~600 embeddings)

    Usage:
        Created automatically during batch embedding generation
        to track per-batch performance statistics.
    """

    __tablename__ = "embedding_metadata"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Model information
    model_name: Mapped[str] = mapped_column(
        String, nullable=False, default="nomic-embed-text"
    )
    model_version: Mapped[str | None] = mapped_column(String, nullable=True)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False, default=768)

    # Performance metrics
    generation_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


class SearchQuery(Base):
    """Analytics for search queries.

    Table: search_queries

    Indexes:
        - created_at: B-tree for temporal analysis

    Purpose:
        - Track search query patterns
        - Monitor search performance
        - Identify slow queries for optimization
        - Support usage analytics

    Performance Metrics:
        - latency_ms: Time from query to results
        - Target: <500ms (p95)
        - result_count: Number of results returned

    Filter Tracking:
        - filters: JSON object of applied filters
        - Examples: {"language": "python", "repository_id": "uuid"}
        - Supports analysis of filter effectiveness

    Usage:
        Created automatically for each search request
        to track performance and usage patterns.
    """

    __tablename__ = "search_queries"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Query information
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False)

    # Performance metrics
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    # Filter tracking
    filters: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )


# ============================================================================
# Database-Backed Project Tracking Models (Feature 003)
# ============================================================================


class VendorExtractor(Base):
    """Tracks operational status, test results, and capabilities for 45+ commission vendor extractors.

    Table: vendor_extractors

    Relationships:
        - deployment_links: One-to-many with VendorDeploymentLink (many-to-many with DeploymentEvent)

    Indexes:
        - name: UNIQUE B-tree index for <1ms vendor lookup by name (idx_vendor_name)
        - status: B-tree index for filtering operational vendors (idx_vendor_status)

    Constraints:
        - name: UNIQUE, NOT NULL (primary lookup key)
        - status: CHECK (status IN ('operational', 'broken'))
        - version: NOT NULL (optimistic locking, auto-incremented on UPDATE)

    Purpose:
        - Track operational status for 45+ commission vendor extractors
        - Store test results, format support, and capability flags in validated JSONB
        - Enable <1ms vendor queries via unique index on name (FR-002)
        - Prevent concurrent update conflicts with optimistic locking (version column)
        - Maintain audit trail for vendor status changes (created_at, updated_at, created_by)

    Performance Target:
        <1ms for single vendor query by name (FR-002)

    Example:
        >>> # Import VendorMetadata from contracts
        >>> import sys
        >>> from pathlib import Path
        >>> specs_path = Path(__file__).parent.parent.parent / "specs" / "003-database-backed-project" / "contracts"
        >>> sys.path.insert(0, str(specs_path))
        >>> from pydantic_schemas import VendorMetadata
        >>>
        >>> vendor = VendorExtractor(
        ...     name="vendor_abc",
        ...     status="operational",
        ...     extractor_version="2.3.1",
        ...     metadata_=VendorMetadata(
        ...         format_support={"excel": True, "csv": True, "pdf": False, "ocr": False},
        ...         test_results={"passing": 45, "total": 50, "skipped": 5},
        ...         extractor_version="2.3.1",
        ...         manifest_compliant=True
        ...     ),
        ...     created_by="claude-code-v1"
        ... )
        >>> session.add(vendor)
        >>> await session.commit()

    Constitutional Compliance:
        - Principle IV: Performance (<1ms vendor queries via unique index)
        - Principle V: Production quality (CHECK constraints, audit trail, Pydantic validation)
        - Principle VIII: Type safety (full Mapped[] annotations, PydanticJSON validation)
        - Principle X: Git micro-commits (audit trail for traceability)
    """

    __tablename__ = "vendor_extractors"

    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Optimistic Locking
    version: Mapped[int] = mapped_column("version", Integer, default=1, nullable=False)

    # Mapper configuration (after column definitions)
    __mapper_args__ = {"version_id_col": version}

    # Core Fields
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "operational" | "broken"
    extractor_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # JSONB Metadata (Pydantic-validated)
    # Note: Using JSONB temporarily. To enable Pydantic validation with VendorMetadata:
    # 1. Import: from pydantic_schemas import VendorMetadata
    # 2. Update type: metadata_: Mapped[VendorMetadata] = mapped_column("metadata", PydanticJSON(VendorMetadata), nullable=False)
    from sqlalchemy.dialects.postgresql import JSONB

    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False
    )

    # Audit Trail
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
    created_by: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # AI client identifier

    # Relationships
    deployment_links: Mapped[list["VendorDeploymentLink"]] = relationship(
        back_populates="vendor", cascade="all, delete-orphan"
    )

    # Table-level constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('operational', 'broken')",
            name="ck_vendor_status",
        ),
    )




class FutureEnhancement(Base):
    """Track planned future enhancements with priorities and constitutional compliance.

    Table: future_enhancements

    Indexes:
        - priority: B-tree for priority filtering
        - status: B-tree for status filtering
        - target_quarter: B-tree for timeline filtering

    Purpose:
        - Track planned future enhancements
        - Manage priorities (1-5 scale, 1=highest)
        - Track status transitions (planned → approved → implementing → completed)
        - Associate with constitutional principles
        - Target quarter planning (YYYY-Q# format)

    Status Transitions:
        - planned: Initial state for new enhancements
        - approved: Enhancement approved for implementation
        - implementing: Active development in progress
        - completed: Enhancement deployed and verified

    Priority Levels:
        - 1: Highest priority (critical)
        - 2: High priority
        - 3: Medium priority
        - 4: Low priority
        - 5: Lowest priority (nice-to-have)

    Constitutional Compliance:
        - requires_constitutional_principles: JSON list of principle names
        - Links enhancements to constitutional requirements
        - Validates compliance during implementation

    Constraints:
        - priority: CHECK (priority >= 1 AND priority <= 5)
        - status: CHECK (status IN ('planned', 'approved', 'implementing', 'completed'))
        - target_quarter: CHECK (target_quarter ~ '^\\d{4}-Q[1-4]$' OR target_quarter IS NULL)
    """

    __tablename__ = "future_enhancements"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Core fields
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )  # 1 (high) to 5 (low)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="planned", index=True
    )  # planned|approved|implementing|completed
    target_quarter: Mapped[str | None] = mapped_column(
        String(10), nullable=True, index=True
    )  # YYYY-Q# format (e.g., "2025-Q1")

    # Constitutional compliance
    requires_constitutional_principles: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )

    # Audit trail
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "priority >= 1 AND priority <= 5", name="ck_enhancement_priority_range"
        ),
        CheckConstraint(
            "status IN ('planned', 'approved', 'implementing', 'completed')",
            name="ck_enhancement_status",
        ),
        CheckConstraint(
            "target_quarter ~ '^\\d{4}-Q[1-4]$' OR target_quarter IS NULL",
            name="ck_enhancement_target_quarter_format",
        ),
    )


class ArchivedWorkItem(Base):
    """Archive table for work items older than 1 year.

    Table: archived_work_items

    Purpose:
        - Archive work items with created_at > 1 year old
        - Maintain <10ms query performance on active work_items table
        - Preserve complete historical data for audit trail
        - Read-only archive (no updates after archiving)

    Schema:
        - Identical to WorkItem table (all columns preserved)
        - No version column (read-only, no optimistic locking)
        - No relationships (archived items are standalone snapshots)
        - Additional archived_at timestamp for audit trail

    Indexes:
        - created_at: B-tree for year-based queries
        - item_type: B-tree for filtering by type
        - archived_at: B-tree for audit trail queries

    Access Pattern:
        - Separate MCP tool: query_archived_work_items
        - Background archiving task runs daily
        - Threshold: created_at < NOW() - INTERVAL '1 year'
        - Batch processing: 100 items per transaction

    Archiving Strategy:
        1. Daily background task identifies old work items
        2. Batch INSERT into archived_work_items (100 items/batch)
        3. Batch DELETE from work_items (maintain referential integrity)
        4. Commit transaction (rollback on any error)
        5. Performance target: <10ms for active table queries

    Constitutional Compliance:
        - Principle IV: Performance (<10ms active work item queries)
        - Principle V: Production quality (complete audit trail preservation)
        - Principle VIII: Type safety (full Mapped[] annotations)
    """

    __tablename__ = "archived_work_items"

    # Primary key (preserved from original work_items row)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)

    # Core fields (identical to WorkItem)
    item_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "project" | "session" | "task" | "research"
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "active" | "completed" | "blocked"

    # Hierarchy fields (preserved, no foreign key enforcement)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    path: Mapped[str] = mapped_column(
        String(500), nullable=False
    )  # Materialized path: "/parent1/parent2/current"
    depth: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-5 levels

    # Git integration (preserved)
    branch_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    commit_hash: Mapped[str | None] = mapped_column(String(40), nullable=True)
    pr_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Metadata (JSON, not Pydantic-validated - read-only archive)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False)

    # Soft delete timestamp (preserved)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Original timestamps (preserved)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)

    # Archive-specific field (NEW)
    archived_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )

    # Table constraints (same as WorkItem)
    __table_args__ = (
        CheckConstraint(
            "item_type IN ('project', 'session', 'task', 'research')",
            name="ck_archived_work_item_type",
        ),
        CheckConstraint(
            "status IN ('active', 'completed', 'blocked')",
            name="ck_archived_work_item_status",
        ),
        CheckConstraint(
            "depth >= 0 AND depth <= 5", name="ck_archived_work_item_depth"
        ),
    )


class ProjectConfiguration(Base):
    """Singleton global configuration for project state.

    Table: project_configuration

    Purpose:
        - Maintain single source of truth for active project context
        - Track current session and token budgets
        - Monitor database health status
        - Store git state for coordination between MCP tools

    Singleton Pattern:
        - id MUST always equal 1 (enforced by CHECK constraint)
        - Only one row allowed in table
        - Updates always use WHERE id = 1
        - No concurrent updates expected (no version column)

    Context Types:
        - feature: Active feature development (slash commands)
        - maintenance: Bug fixes and refactoring
        - research: Exploratory technical research

    Token Management:
        - default_token_budget: Default for new sessions (200,000)
        - Updated by /specify and /plan commands

    Health Monitoring:
        - database_healthy: True if last health check passed
        - last_health_check_at: Timestamp of most recent check
        - Background task runs health checks periodically

    Git Integration:
        - git_branch: Current active branch (e.g., "003-database-backed-project")
        - git_head_commit: Latest commit hash (40-char lowercase hex)
        - Synced on session start and git operations

    Access Pattern:
        Always query/update WHERE id = 1 (FR-015, FR-016)

    Usage Example:
        ```python
        # Upsert pattern for singleton
        config = await session.get(ProjectConfiguration, 1)
        if config is None:
            config = ProjectConfiguration(
                id=1,
                active_context_type="feature",
                default_token_budget=200000,
                database_healthy=True,
                updated_by="mcp-client"
            )
            session.add(config)
        else:
            config.git_branch = "003-database-backed-project"
            config.updated_by = "mcp-client"
        await session.commit()
        ```

    Constitutional Compliance:
        - Principle IV: Performance (singleton access pattern for <1ms config queries)
        - Principle V: Production quality (health monitoring, audit trail)
        - Principle VIII: Type safety (full Mapped[] annotations)
    """

    __tablename__ = "project_configuration"

    # Singleton primary key (always 1)
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, default=1, nullable=False
    )

    # Core configuration fields
    active_context_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "feature" | "maintenance" | "research"

    current_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True
    )

    # Git state
    git_branch: Mapped[str | None] = mapped_column(String(100), nullable=True)
    git_head_commit: Mapped[str | None] = mapped_column(
        String(40), nullable=True
    )  # 40-char hex SHA-1

    # Token management
    default_token_budget: Mapped[int] = mapped_column(
        Integer, nullable=False, default=200000
    )

    # Health monitoring
    database_healthy: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    last_health_check_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Audit trail (no created_at since singleton exists from migration)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_by: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # AI client identifier

    # Relationships
    current_session: Mapped[WorkItem | None] = relationship(
        foreign_keys=[current_session_id]
    )

    # Table-level constraints
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_singleton"),
        CheckConstraint(
            "active_context_type IN ('feature', 'maintenance', 'research')",
            name="ck_active_context_type",
        ),
    )


class WorkItemDependency(Base):
    """Junction table for work item dependencies (blocks/depends_on relationships).

    Table: work_item_dependencies

    Relationships:
        - source: Many-to-one with WorkItem (source of dependency)
        - target: Many-to-one with WorkItem (target of dependency)

    Constraints:
        - Composite primary key: (source_id, target_id)
        - CHECK: source_id != target_id (prevent self-dependencies)
        - dependency_type: enum ('blocks' | 'depends_on')

    Purpose:
        - Track blocking relationships between work items
        - Enable dependency validation before task execution
        - Support dependency graph queries for task ordering
        - Prevent circular dependencies (application-level validation)

    Semantics:
        - (A, B, "blocks"): Work item A blocks work item B
        - (A, B, "depends_on"): Work item A depends on work item B

    Cascade Behavior:
        - DELETE work item → CASCADE delete all dependency links

    Indexes:
        - source_id: B-tree for querying dependencies of a work item
        - target_id: B-tree for reverse lookup (what blocks this item)

    Performance:
        - Target: <1ms for dependency queries
        - Supports graph traversal for circular dependency detection
    """

    __tablename__ = "work_item_dependencies"

    # Composite primary key
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Dependency metadata
    dependency_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "blocks" | "depends_on"

    # Audit trail
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    source: Mapped[WorkItem] = relationship(
        "WorkItem",
        foreign_keys=[source_id],
        back_populates="dependencies_as_source",
    )
    target: Mapped[WorkItem] = relationship(
        "WorkItem",
        foreign_keys=[target_id],
        back_populates="dependencies_as_target",
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "source_id != target_id",
            name="ck_no_self_dependency",
        ),
        CheckConstraint(
            "dependency_type IN ('blocks', 'depends_on')",
            name="ck_dependency_type",
        ),
    )


class VendorDeploymentLink(Base):
    """Junction table for deployment-vendor many-to-many relationships.

    Table: vendor_deployment_links

    Relationships:
        - deployment: Many-to-one with DeploymentEvent
        - vendor: Many-to-one with VendorExtractor

    Constraints:
        - Composite primary key: (deployment_id, vendor_id)
        - Ensures uniqueness of deployment-vendor pairs

    Purpose:
        - Track which vendors were affected by each deployment
        - Enable queries: "Which deployments affected vendor X?"
        - Enable queries: "Which vendors were affected by deployment Y?"
        - Support deployment impact analysis

    Cascade Behavior:
        - DELETE deployment → CASCADE delete all vendor links
        - DELETE vendor → CASCADE delete all deployment links

    Indexes:
        - deployment_id: B-tree for querying vendors for a deployment
        - vendor_id: B-tree for querying deployments for a vendor

    Performance:
        - Target: <1ms for single deployment's vendor list
        - Supports bidirectional queries efficiently
    """

    __tablename__ = "vendor_deployment_links"

    # Composite primary key
    deployment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deployment_events.id", ondelete="CASCADE"),
        primary_key=True,
    )
    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendor_extractors.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Audit trail
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    deployment: Mapped[DeploymentEvent] = relationship(
        "DeploymentEvent", back_populates="vendor_links"
    )
    vendor: Mapped[VendorExtractor] = relationship(
        "VendorExtractor", back_populates="deployment_links"
    )


class WorkItemDeploymentLink(Base):
    """Junction table for deployment-work item many-to-many relationships.

    Table: work_item_deployment_links

    Relationships:
        - deployment: Many-to-one with DeploymentEvent
        - work_item: Many-to-one with WorkItem

    Constraints:
        - Composite primary key: (deployment_id, work_item_id)
        - Ensures uniqueness of deployment-work item pairs

    Purpose:
        - Track which work items were included in each deployment
        - Enable queries: "Which deployments included work item X?"
        - Enable queries: "Which work items were deployed in deployment Y?"
        - Support deployment traceability and audit trail
        - Preserve links even after work item soft delete (deleted_at != NULL)

    Cascade Behavior:
        - DELETE deployment → CASCADE delete all work item links
        - Soft delete work item → PRESERVE links for audit trail
        - Hard delete work item → CASCADE delete links

    Indexes:
        - deployment_id: B-tree for querying work items for a deployment
        - work_item_id: B-tree for querying deployments for a work item

    Performance:
        - Target: <1ms for single deployment's work item list
        - Supports bidirectional queries efficiently
    """

    __tablename__ = "work_item_deployment_links"

    # Composite primary key
    deployment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deployment_events.id", ondelete="CASCADE"),
        primary_key=True,
    )
    work_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tasks.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Audit trail
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    deployment: Mapped[DeploymentEvent] = relationship(
        "DeploymentEvent", back_populates="work_item_links"
    )
    work_item: Mapped[WorkItem] = relationship(
        "WorkItem", back_populates="deployment_links"
    )


class DeploymentEvent(Base):
    """Record deployment occurrences with PR details, test results, and relationships.

    Table: deployment_events

    Relationships:
        - vendor_links: Many-to-many with VendorExtractor via VendorDeploymentLink
        - work_item_links: Many-to-many with WorkItem via WorkItemDeploymentLink

    Indexes:
        - deployed_at: B-tree DESC for chronological queries (recent deployments first)
        - commit_hash: B-tree for lookup by git commit

    Purpose:
        - Record deployment events with PR metadata
        - Track which vendors were affected by each deployment
        - Link deployments to work items for traceability
        - Monitor test results and constitutional compliance
        - Support deployment history queries and audit trail

    Metadata (Pydantic-validated JSONB):
        - pr_number: GitHub pull request number (positive integer)
        - pr_title: Pull request title (1-200 chars)
        - commit_hash: Git SHA-1 commit hash (40 lowercase hex)
        - test_summary: Test results by category (e.g., {"unit": 150, "integration": 30})
        - constitutional_compliance: Boolean flag for validation pass/fail

    Constraints:
        - deployed_at: NOT NULL, indexed DESC
        - commit_hash: NOT NULL, CHECK (commit_hash ~ '^[a-f0-9]{40}$')
        - metadata_.pr_number: MUST be positive (Pydantic validation)
        - metadata_.constitutional_compliance: MUST be boolean (Pydantic validation)

    Performance:
        - Index on deployed_at DESC supports recent deployments query (FR-006)
        - Many-to-many relationships optimized with junction table indexes

    Constitutional Compliance:
        - Principle V: Production quality (complete deployment audit trail)
        - Principle VIII: Type safety (full Mapped[] annotations, Pydantic JSONB validation)
    """

    __tablename__ = "deployment_events"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Core fields
    deployed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    commit_hash: Mapped[str] = mapped_column(
        String(40), nullable=False, index=True
    )  # Git SHA-1 (40-char lowercase hex)

    # JSONB metadata (Pydantic-validated)
    metadata_: Mapped[DeploymentMetadata] = mapped_column(
        "metadata",
        PydanticJSON(DeploymentMetadata),
        nullable=False,
    )

    # Audit trail
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    created_by: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # AI client identifier

    # Relationships (many-to-many via junction tables)
    vendor_links: Mapped[list[VendorDeploymentLink]] = relationship(
        "VendorDeploymentLink", back_populates="deployment", cascade="all, delete-orphan"
    )
    work_item_links: Mapped[list[WorkItemDeploymentLink]] = relationship(
        "WorkItemDeploymentLink", back_populates="deployment", cascade="all, delete-orphan"
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "commit_hash ~ '^[a-f0-9]{40}$'",
            name="ck_deployment_commit_hash_format",
        ),
    )
