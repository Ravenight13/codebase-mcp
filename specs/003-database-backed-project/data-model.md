# Data Model: Project Status and Work Item Tracking System

**Feature**: 003-database-backed-project | **Date**: 2025-10-10
**Prerequisites**: [spec.md](./spec.md), [research.md](./research.md), [plan.md](./plan.md)

## Overview

This data model supports a database-backed project status and work item tracking system for MCP clients. It extends the existing task tracking infrastructure with 9 entities supporting vendor management, deployment history, hierarchical work items, and configuration management. Performance targets: <1ms vendor queries, <10ms work item hierarchies, <100ms full status generation.

## Entity Definitions

### 1. VendorExtractor (NEW)

**Purpose**: Track operational status, test results, and capabilities for 45+ commission data vendor extractors.

**Table**: `vendor_extractors`

**Schema**:
```python
class VendorExtractor(Base):
    __tablename__ = "vendor_extractors"
    __mapper_args__ = {"version_id_col": "version"}

    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Optimistic Locking
    version: Mapped[int] = mapped_column(default=1, nullable=False)

    # Core Fields
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # "operational" | "broken"
    extractor_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # JSONB Metadata (Pydantic-validated)
    metadata_: Mapped[VendorMetadata] = mapped_column(
        "metadata",
        PydanticJSON(VendorMetadata),
        nullable=False
    )

    # Audit Trail
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)  # AI client identifier

    # Relationships
    deployment_links: Mapped[list["VendorDeploymentLink"]] = relationship(back_populates="vendor", cascade="all, delete-orphan")
```

**Indexes**:
```sql
CREATE UNIQUE INDEX idx_vendor_name ON vendor_extractors(name);  -- <1ms lookup
CREATE INDEX idx_vendor_status ON vendor_extractors(status);     -- Filter operational vendors
```

**Constraints**:
- `name`: UNIQUE, NOT NULL
- `status`: CHECK (status IN ('operational', 'broken'))
- `version`: NOT NULL, auto-incremented on UPDATE

**Performance Target**: <1ms for single vendor query by name (FR-002)

---

### 2. DeploymentEvent (NEW)

**Purpose**: Record deployment occurrences with PR details, test results, constitutional compliance, and relationships to affected vendors and work items.

**Table**: `deployment_events`

**Schema**:
```python
class DeploymentEvent(Base):
    __tablename__ = "deployment_events"

    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Core Fields
    deployed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    commit_hash: Mapped[str] = mapped_column(String(40), nullable=False)  # Git SHA-1

    # JSONB Metadata (Pydantic-validated)
    metadata_: Mapped[DeploymentMetadata] = mapped_column(
        "metadata",
        PydanticJSON(DeploymentMetadata),
        nullable=False
    )

    # Audit Trail
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    vendor_links: Mapped[list["VendorDeploymentLink"]] = relationship(back_populates="deployment", cascade="all, delete-orphan")
    work_item_links: Mapped[list["WorkItemDeploymentLink"]] = relationship(back_populates="deployment", cascade="all, delete-orphan")
```

**Indexes**:
```sql
CREATE INDEX idx_deployment_deployed_at ON deployment_events(deployed_at DESC);  -- Chronological queries
CREATE INDEX idx_deployment_commit_hash ON deployment_events(commit_hash);        -- Lookup by commit
```

**Constraints**:
- `deployed_at`: NOT NULL
- `commit_hash`: NOT NULL, CHECK (commit_hash ~ '^[a-f0-9]{40}$')  -- 40-char lowercase hex
- `metadata_.pr_number`: MUST be positive integer (Pydantic validation)
- `metadata_.constitutional_compliance`: MUST be boolean (Pydantic validation)

**Performance Considerations**: Index on `deployed_at` DESC for recent deployments query (FR-006)

---

### 3. WorkItem (EXTENDED)

**Purpose**: Polymorphic entity representing projects, work sessions, tasks, or research phases with hierarchical parent-child relationships, dependencies, git integration, and type-specific metadata.

**Table**: `work_items`

**Schema**:
```python
class WorkItem(Base):
    __tablename__ = "work_items"
    __mapper_args__ = {"version_id_col": "version"}

    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Optimistic Locking
    version: Mapped[int] = mapped_column(default=1, nullable=False)

    # Core Fields
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "project" | "session" | "task" | "research"
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")  # "active" | "completed" | "blocked"

    # Hierarchy Fields (Self-Referential)
    parent_id: Mapped[UUID | None] = mapped_column(ForeignKey("work_items.id"), nullable=True, index=True)
    path: Mapped[str] = mapped_column(String(500), nullable=False, index=True)  # Materialized path: "/parent1/parent2/current"
    depth: Mapped[int] = mapped_column(default=0, nullable=False)  # 0-5 levels

    # Git Integration
    branch_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    commit_hash: Mapped[str | None] = mapped_column(String(40), nullable=True)
    pr_number: Mapped[int | None] = mapped_column(nullable=True)

    # JSONB Metadata (Pydantic-validated, type-specific)
    metadata_: Mapped[dict] = mapped_column(
        "metadata",
        PydanticJSON(WorkItemMetadata),  # Union type: ProjectMetadata | SessionMetadata | TaskMetadata | ResearchMetadata
        nullable=False
    )

    # Soft Delete
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Audit Trail
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    parent: Mapped["WorkItem | None"] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[list["WorkItem"]] = relationship(back_populates="parent")
    dependencies_as_source: Mapped[list["WorkItemDependency"]] = relationship(foreign_keys="WorkItemDependency.source_id", back_populates="source")
    dependencies_as_target: Mapped[list["WorkItemDependency"]] = relationship(foreign_keys="WorkItemDependency.target_id", back_populates="target")
    deployment_links: Mapped[list["WorkItemDeploymentLink"]] = relationship(back_populates="work_item", cascade="all, delete-orphan")
```

**Indexes**:
```sql
CREATE INDEX idx_work_item_parent_id ON work_items(parent_id);           -- Recursive CTE queries
CREATE INDEX idx_work_item_path ON work_items(path);                     -- Ancestor queries
CREATE INDEX idx_work_item_type ON work_items(item_type);                -- Filter by type
CREATE INDEX idx_work_item_status ON work_items(status);                 -- Filter active items
CREATE INDEX idx_work_item_created_at ON work_items(created_at);         -- Archiving threshold queries
CREATE INDEX idx_work_item_deleted_at ON work_items(deleted_at) WHERE deleted_at IS NULL;  -- Partial index for active items
```

**Constraints**:
- `item_type`: CHECK (item_type IN ('project', 'session', 'task', 'research'))
- `depth`: CHECK (depth >= 0 AND depth <= 5)  -- Max 5 levels (FR-008)
- `status`: CHECK (status IN ('active', 'completed', 'blocked'))
- `parent_id`: FOREIGN KEY to work_items.id, nullable
- Circular dependency prevention: Application-level validation in service layer

**State Transitions**:
- `active` → `completed`: Marked by AI client on completion
- `active` → `blocked`: Marked when dependency prevents progress
- `deleted_at = NULL` → `deleted_at = NOW()`: Soft delete (FR-012)
- Archiving: Items with `created_at < NOW() - INTERVAL '1 year'` → `archived_work_items` table

**Performance Target**: <10ms for hierarchical queries up to 5 levels (FR-013)

---

### 4. ProjectConfiguration (NEW - Singleton)

**Purpose**: Maintain global project configuration including active context, token budgets, current session, git state, and health status.

**Table**: `project_configuration`

**Schema**:
```python
class ProjectConfiguration(Base):
    __tablename__ = "project_configuration"

    # Singleton Pattern (single row enforced)
    id: Mapped[int] = mapped_column(primary_key=True, default=1)  # Always 1

    # Core Fields
    active_context_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "feature" | "maintenance" | "research"
    current_session_id: Mapped[UUID | None] = mapped_column(ForeignKey("work_items.id"), nullable=True)
    git_branch: Mapped[str | None] = mapped_column(String(100), nullable=True)
    git_head_commit: Mapped[str | None] = mapped_column(String(40), nullable=True)

    # Token Budget
    default_token_budget: Mapped[int] = mapped_column(default=200000, nullable=False)

    # Health Status
    database_healthy: Mapped[bool] = mapped_column(default=True, nullable=False)
    last_health_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Audit Trail
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    current_session: Mapped["WorkItem | None"] = relationship(foreign_keys=[current_session_id])
```

**Indexes**:
```sql
-- No indexes needed (singleton table, always 1 row)
```

**Constraints**:
- `id`: CHECK (id = 1)  -- Enforce singleton pattern
- `active_context_type`: CHECK (active_context_type IN ('feature', 'maintenance', 'research'))
- Singleton enforcement: Application-level `INSERT ... ON CONFLICT (id) DO UPDATE` pattern

**Access Pattern**: Always query/update `WHERE id = 1` (FR-015, FR-016)

---

### 5. FutureEnhancement (NEW)

**Purpose**: Track planned future enhancements with priorities, dependencies, target timelines, and constitutional compliance requirements.

**Table**: `future_enhancements`

**Schema**:
```python
class FutureEnhancement(Base):
    __tablename__ = "future_enhancements"

    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Core Fields
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(nullable=False, index=True)  # 1 (high) to 5 (low)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="planned")  # "planned" | "approved" | "implementing" | "completed"
    target_quarter: Mapped[str | None] = mapped_column(String(10), nullable=True)  # "2025-Q1"

    # Constitutional Compliance
    requires_constitutional_principles: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list
    )

    # Audit Trail
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
```

**Indexes**:
```sql
CREATE INDEX idx_enhancement_priority ON future_enhancements(priority);           -- Filter by priority (FR-018)
CREATE INDEX idx_enhancement_status ON future_enhancements(status);               -- Filter by status (FR-018)
CREATE INDEX idx_enhancement_target_quarter ON future_enhancements(target_quarter);  -- Filter by timeline (FR-018)
```

**Constraints**:
- `priority`: CHECK (priority >= 1 AND priority <= 5)
- `status`: CHECK (status IN ('planned', 'approved', 'implementing', 'completed'))
- `target_quarter`: CHECK (target_quarter ~ '^\d{4}-Q[1-4]$' OR target_quarter IS NULL)  -- YYYY-Q# format

**Dependencies**: Managed through `WorkItemDependency` junction table if enhancement is linked to work items

---

### 6. WorkItemDependency (NEW - Junction)

**Purpose**: Relationship between work items indicating blocked-by or depends-on constraints.

**Table**: `work_item_dependencies`

**Schema**:
```python
class WorkItemDependency(Base):
    __tablename__ = "work_item_dependencies"

    # Composite Primary Key
    source_id: Mapped[UUID] = mapped_column(ForeignKey("work_items.id", ondelete="CASCADE"), primary_key=True)
    target_id: Mapped[UUID] = mapped_column(ForeignKey("work_items.id", ondelete="CASCADE"), primary_key=True)

    # Dependency Type
    dependency_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "blocks" | "depends_on"

    # Audit Trail
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationships
    source: Mapped["WorkItem"] = relationship(foreign_keys=[source_id], back_populates="dependencies_as_source")
    target: Mapped["WorkItem"] = relationship(foreign_keys=[target_id], back_populates="dependencies_as_target")
```

**Indexes**:
```sql
CREATE INDEX idx_dependency_source_id ON work_item_dependencies(source_id);  -- Query dependencies for a work item
CREATE INDEX idx_dependency_target_id ON work_item_dependencies(target_id);  -- Reverse lookup (what blocks this item)
```

**Constraints**:
- `dependency_type`: CHECK (dependency_type IN ('blocks', 'depends_on'))
- `source_id != target_id`: CHECK constraint to prevent self-dependencies
- Circular dependency detection: Application-level validation (graph traversal)

**Semantics**:
- `(A, B, "blocks")`: Work item A blocks work item B
- `(A, B, "depends_on")`: Work item A depends on work item B

---

### 7. VendorDeploymentLink (NEW - Junction)

**Purpose**: Many-to-many relationship connecting deployments to affected vendors.

**Table**: `vendor_deployment_links`

**Schema**:
```python
class VendorDeploymentLink(Base):
    __tablename__ = "vendor_deployment_links"

    # Composite Primary Key
    deployment_id: Mapped[UUID] = mapped_column(ForeignKey("deployment_events.id", ondelete="CASCADE"), primary_key=True)
    vendor_id: Mapped[UUID] = mapped_column(ForeignKey("vendor_extractors.id", ondelete="CASCADE"), primary_key=True)

    # Audit Trail
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    deployment: Mapped["DeploymentEvent"] = relationship(back_populates="vendor_links")
    vendor: Mapped["VendorExtractor"] = relationship(back_populates="deployment_links")
```

**Indexes**:
```sql
CREATE INDEX idx_vendor_deployment_deployment_id ON vendor_deployment_links(deployment_id);  -- Query vendors for deployment
CREATE INDEX idx_vendor_deployment_vendor_id ON vendor_deployment_links(vendor_id);          -- Query deployments for vendor
```

**Constraints**:
- Composite primary key ensures uniqueness of (deployment_id, vendor_id) pairs
- Foreign key cascades: DELETE deployment → delete links, DELETE vendor → delete links (FR-004)

---

### 8. WorkItemDeploymentLink (NEW - Junction)

**Purpose**: Many-to-many relationship connecting deployments to related work items.

**Table**: `work_item_deployment_links`

**Schema**:
```python
class WorkItemDeploymentLink(Base):
    __tablename__ = "work_item_deployment_links"

    # Composite Primary Key
    deployment_id: Mapped[UUID] = mapped_column(ForeignKey("deployment_events.id", ondelete="CASCADE"), primary_key=True)
    work_item_id: Mapped[UUID] = mapped_column(ForeignKey("work_items.id", ondelete="CASCADE"), primary_key=True)

    # Audit Trail
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # Relationships
    deployment: Mapped["DeploymentEvent"] = relationship(back_populates="work_item_links")
    work_item: Mapped["WorkItem"] = relationship(back_populates="deployment_links")
```

**Indexes**:
```sql
CREATE INDEX idx_work_item_deployment_deployment_id ON work_item_deployment_links(deployment_id);  -- Query work items for deployment
CREATE INDEX idx_work_item_deployment_work_item_id ON work_item_deployment_links(work_item_id);    -- Query deployments for work item
```

**Constraints**:
- Composite primary key ensures uniqueness of (deployment_id, work_item_id) pairs
- Foreign key cascades: DELETE deployment → delete links, DELETE work item (soft delete) → keep links (FR-007)

---

### 9. ArchivedWorkItem (NEW - Archive Table)

**Purpose**: Archive table for work items older than 1 year, maintaining identical schema for data preservation while keeping active table performant.

**Table**: `archived_work_items`

**Schema**:
```python
class ArchivedWorkItem(Base):
    __tablename__ = "archived_work_items"

    # Identical schema to WorkItem (no version column - read-only archive)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    parent_id: Mapped[UUID | None] = mapped_column(nullable=True, index=True)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    depth: Mapped[int] = mapped_column(nullable=False)
    branch_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    commit_hash: Mapped[str | None] = mapped_column(String(40), nullable=True)
    pr_number: Mapped[int | None] = mapped_column(nullable=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSON, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)

    # Archive-Specific Fields
    archived_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
```

**Indexes** (read-optimized):
```sql
CREATE INDEX idx_archived_work_item_created_at ON archived_work_items(created_at);  -- Year-based queries
CREATE INDEX idx_archived_work_item_type ON archived_work_items(item_type);         -- Filter by type
CREATE INDEX idx_archived_work_item_archived_at ON archived_work_items(archived_at); -- Audit archiving process
```

**Constraints**:
- Same CHECK constraints as `work_items` table
- `archived_at`: NOT NULL (record when archiving occurred)
- No foreign key to `work_items` parent_id (archive is standalone)

**Access Pattern**: Separate MCP tool `query_archived_work_items` for historical data (FR-039)

**Archiving Strategy**:
```python
# Background task (daily): Move items older than 1 year
async def archive_old_work_items(threshold_days: int = 365):
    cutoff_date = datetime.utcnow() - timedelta(days=threshold_days)
    old_items = await session.execute(
        select(WorkItem).where(
            WorkItem.created_at < cutoff_date,
            WorkItem.deleted_at.is_(None)
        )
    )
    for item in old_items.scalars():
        await session.execute(
            insert(ArchivedWorkItem).values(
                **{k: v for k, v in item.__dict__.items() if not k.startswith('_')},
                archived_at=datetime.utcnow()
            )
        )
        await session.delete(item)
    await session.commit()
```

---

## Relationships Summary

### Entity Relationship Diagram (ERD)

```
VendorExtractor (1) ----< (M) VendorDeploymentLink (M) >---- (1) DeploymentEvent
                                                                       |
                                                                       | (1)
                                                                       |
                                                                       v
                                                                      (M)
                                                             WorkItemDeploymentLink
                                                                       |
                                                                       | (M)
                                                                       v
                                                                      (1)
                                                                   WorkItem
                                                                     /  |  \
                                                    (self-referential)  |  (dependencies)
                                                                       /|\
                                                                      / | \
                                                    WorkItem (parent) | WorkItemDependency
                                                                       |
                                                                       v
                                                              WorkItem (children)

ProjectConfiguration (1) ---- (1) WorkItem (current_session)

ArchivedWorkItem (standalone, no foreign keys)

FutureEnhancement (standalone, optional WorkItemDependency links)
```

### Relationship Details

1. **WorkItem Self-Referential Hierarchy**:
   - `WorkItem.parent_id → WorkItem.id` (nullable)
   - Max depth: 5 levels (FR-008)
   - Materialized path: `/parent1/parent2/current` for ancestor queries

2. **WorkItem Dependencies**:
   - `WorkItemDependency` junction table
   - `source_id` blocks/depends-on `target_id`
   - Circular dependency validation in application layer

3. **Deployment ↔ Vendor Many-to-Many**:
   - `VendorDeploymentLink` junction table
   - Tracks which vendors affected by each deployment (FR-004)
   - Cascade delete: deployment deleted → links deleted

4. **Deployment ↔ WorkItem Many-to-Many**:
   - `WorkItemDeploymentLink` junction table
   - Tracks which work items included in each deployment (FR-007)
   - Soft delete work items: links preserved for audit trail

5. **ProjectConfiguration ↔ WorkItem**:
   - Singleton configuration references current session
   - Foreign key `current_session_id → work_items.id`
   - Nullable (no active session possible)

---

## Validation Rules (Pydantic Schemas)

### VendorMetadata

```python
from pydantic import BaseModel, Field
from typing import Literal

class VendorMetadata(BaseModel):
    """JSONB metadata for VendorExtractor"""
    format_support: dict[Literal["excel", "csv", "pdf", "ocr"], bool] = Field(
        description="Supported file formats with capability flags"
    )
    test_results: dict[Literal["passing", "total", "skipped"], int] = Field(
        description="Test execution summary (counts)"
    )
    extractor_version: str = Field(
        min_length=1,
        max_length=50,
        description="Semantic version string (e.g., '2.3.1')"
    )
    manifest_compliant: bool = Field(
        description="Whether vendor follows manifest standards"
    )

    @validator('test_results')
    def validate_test_counts(cls, v):
        if v['passing'] > v['total']:
            raise ValueError("passing tests cannot exceed total tests")
        if v['passing'] + v['skipped'] > v['total']:
            raise ValueError("passing + skipped cannot exceed total tests")
        return v
```

### WorkItemMetadata (Type-Specific Union)

```python
from typing import Union

class ProjectMetadata(BaseModel):
    """Metadata for item_type='project'"""
    description: str = Field(max_length=1000)
    target_quarter: str | None = Field(None, pattern=r'^\d{4}-Q[1-4]$')
    constitutional_principles: list[str] = Field(default_factory=list)

class SessionMetadata(BaseModel):
    """Metadata for item_type='session'"""
    token_budget: int = Field(ge=1000, le=1000000)
    prompts_count: int = Field(ge=0)
    yaml_frontmatter: dict = Field(description="Raw YAML frontmatter from session prompt")

    @validator('yaml_frontmatter')
    def validate_schema_version(cls, v):
        if 'schema_version' not in v:
            raise ValueError("YAML frontmatter must include schema_version")
        return v

class TaskMetadata(BaseModel):
    """Metadata for item_type='task'"""
    estimated_hours: float | None = Field(None, ge=0, le=1000)
    actual_hours: float | None = Field(None, ge=0, le=1000)
    blocked_reason: str | None = Field(None, max_length=500)

class ResearchMetadata(BaseModel):
    """Metadata for item_type='research'"""
    research_questions: list[str] = Field(default_factory=list)
    findings_summary: str | None = Field(None, max_length=2000)
    references: list[str] = Field(default_factory=list)

# Union type for polymorphic metadata
WorkItemMetadata = Union[ProjectMetadata, SessionMetadata, TaskMetadata, ResearchMetadata]

# Custom TypeDecorator for SQLAlchemy
class WorkItemMetadataJSON(TypeDecorator):
    impl = JSON
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        # Validate based on item_type (requires context from WorkItem instance)
        # Implemented in WorkItem.__init__ or service layer
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        # Deserialize to appropriate type based on item_type
        # Return dict (type discrimination in application layer)
        return value
```

### DeploymentMetadata

```python
class DeploymentMetadata(BaseModel):
    """JSONB metadata for DeploymentEvent"""
    pr_number: int = Field(ge=1, description="GitHub pull request number")
    pr_title: str = Field(min_length=1, max_length=200)
    commit_hash: str = Field(
        pattern=r'^[a-f0-9]{40}$',
        description="Git SHA-1 commit hash (40 lowercase hex characters)"
    )
    test_summary: dict[str, int] = Field(
        description="Test results by category (e.g., {'unit': 150, 'integration': 30})"
    )
    constitutional_compliance: bool = Field(
        description="Whether deployment passes constitutional validation"
    )

    @validator('test_summary')
    def validate_test_counts_non_negative(cls, v):
        if any(count < 0 for count in v.values()):
            raise ValueError("test counts must be non-negative")
        return v
```

---

## State Transitions

### WorkItem Status Flow

```
┌─────────┐
│  active │ ────┬───> completed (work finished)
└─────────┘     │
       │        └───> blocked (dependency prevents progress)
       │
       └────────────> deleted (soft delete: deleted_at = NOW())
```

**Transitions**:
1. `active → completed`: AI client marks task done
2. `active → blocked`: Dependency check fails (WorkItemDependency validation)
3. `active → deleted`: Soft delete (preserve audit trail)
4. `completed → active`: Reopened (rare, manual intervention)

**Archiving Trigger**:
- `created_at < NOW() - INTERVAL '1 year'` AND `deleted_at IS NULL`
- Background task moves row to `archived_work_items` table
- Frees space in active table for <10ms query performance

### VendorExtractor Status Flow

```
┌──────────────┐
│ operational  │ <───────> broken (test failures)
└──────────────┘
```

**Transitions**:
1. `operational → broken`: Test execution detects failures (metadata_.test_results.passing < threshold)
2. `broken → operational`: Test suite passes (manual or automated re-validation)

**Validation**:
- Status change MUST update `metadata_.test_results` and `updated_at`
- Optimistic locking prevents concurrent status changes (version check)

---

## Performance Considerations

### Index Strategy

**<1ms Target (Vendor Queries - FR-002)**:
```sql
-- Single vendor lookup by name
CREATE UNIQUE INDEX idx_vendor_name ON vendor_extractors(name);

-- Query plan: Index Scan on idx_vendor_name (cost=0.15..8.17 rows=1)
-- Expected latency: <1ms for 45 vendors
```

**<10ms Target (Work Item Hierarchies - FR-013)**:
```sql
-- Materialized path for ancestor queries (single query, no recursion)
CREATE INDEX idx_work_item_path ON work_items(path);

-- Recursive CTE for descendants (5 levels max)
CREATE INDEX idx_work_item_parent_id ON work_items(parent_id);

-- Query plan: Recursive CTE with Index Scan on idx_work_item_parent_id
-- Expected latency: <10ms for 5-level depth with 100 children per level
```

**<100ms Target (Full Status Generation - FR-023)**:
```sql
-- Parallel queries with indexed filters
CREATE INDEX idx_vendor_status ON vendor_extractors(status);  -- Operational vendors
CREATE INDEX idx_work_item_deleted_at ON work_items(deleted_at) WHERE deleted_at IS NULL;  -- Active items
CREATE INDEX idx_deployment_deployed_at ON deployment_events(deployed_at DESC);  -- Recent deployments

-- Query plan: 3 parallel Index Scans + template rendering
-- Expected latency: <100ms for 45 vendors + 1,200 work items + 50 deployments
```

### Query Optimization Patterns

**1. Ancestor Query (Materialized Path)**:
```python
async def get_ancestors(work_item_id: UUID) -> list[WorkItem]:
    """Single query using materialized path (no recursion)"""
    item = await session.get(WorkItem, work_item_id)
    ancestor_ids = [UUID(id_str) for id_str in item.path.split('/')[1:-1]]
    return await session.execute(
        select(WorkItem)
        .where(WorkItem.id.in_(ancestor_ids))
        .order_by(WorkItem.depth)
    )
```

**2. Descendant Query (Recursive CTE)**:
```python
async def get_descendants(root_id: UUID, max_depth: int = 5) -> list[WorkItem]:
    """Recursive CTE limited to 5 levels"""
    cte = select(
        WorkItem.id,
        WorkItem.parent_id,
        literal(0).label('level')
    ).where(WorkItem.id == root_id).cte(name='descendants', recursive=True)

    cte = cte.union_all(
        select(
            WorkItem.id,
            WorkItem.parent_id,
            cte.c.level + 1
        ).join(WorkItem, WorkItem.parent_id == cte.c.id)
        .where(cte.c.level < max_depth)
    )

    return await session.execute(
        select(WorkItem).join(cte, WorkItem.id == cte.c.id)
        .order_by(cte.c.level, WorkItem.path)
    )
```

**3. Active Work Items (Partial Index)**:
```python
async def get_active_work_items() -> list[WorkItem]:
    """Uses partial index on deleted_at IS NULL"""
    return await session.execute(
        select(WorkItem)
        .where(WorkItem.deleted_at.is_(None))
        .order_by(WorkItem.updated_at.desc())
    )
```

### Archiving Performance

**Background Task Strategy**:
- Daily execution via FastMCP background task decorator
- Batch processing: 100 items per transaction (avoid long locks)
- Index on `created_at` for threshold query
- Archive table has separate indexes optimized for read-only access

**Archiving Query**:
```python
# Batched archiving (100 items per commit)
async def archive_batch(threshold_days: int = 365, batch_size: int = 100):
    cutoff_date = datetime.utcnow() - timedelta(days=threshold_days)
    offset = 0

    while True:
        batch = await session.execute(
            select(WorkItem)
            .where(WorkItem.created_at < cutoff_date, WorkItem.deleted_at.is_(None))
            .limit(batch_size)
            .offset(offset)
        )
        items = batch.scalars().all()
        if not items:
            break

        # Bulk insert to archive, bulk delete from active
        await session.execute(
            insert(ArchivedWorkItem),
            [item.__dict__ for item in items]
        )
        await session.execute(
            delete(WorkItem).where(WorkItem.id.in_([item.id for item in items]))
        )
        await session.commit()

        offset += batch_size
```

---

## Migration Strategy

### Schema Migration (Alembic)

**Migration File**: `003_project_tracking.py`

```python
"""Add project tracking tables

Revision ID: 003
Revises: 002
Create Date: 2025-10-10

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # 1. Create vendor_extractors
    op.create_table(
        'vendor_extractors',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('version', sa.Integer, nullable=False, default=1),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('extractor_version', sa.String(50), nullable=False),
        sa.Column('metadata', postgresql.JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(100), nullable=False),
        sa.CheckConstraint("status IN ('operational', 'broken')", name='ck_vendor_status')
    )
    op.create_index('idx_vendor_name', 'vendor_extractors', ['name'], unique=True)
    op.create_index('idx_vendor_status', 'vendor_extractors', ['status'])

    # 2. Create deployment_events
    op.create_table(
        'deployment_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('deployed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('commit_hash', sa.String(40), nullable=False),
        sa.Column('metadata', postgresql.JSONB, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(100), nullable=False),
        sa.CheckConstraint("commit_hash ~ '^[a-f0-9]{40}$'", name='ck_commit_hash_format')
    )
    op.create_index('idx_deployment_deployed_at', 'deployment_events', ['deployed_at'])
    op.create_index('idx_deployment_commit_hash', 'deployment_events', ['commit_hash'])

    # 3. Extend work_items (existing table)
    op.add_column('work_items', sa.Column('version', sa.Integer, nullable=False, default=1))
    op.add_column('work_items', sa.Column('item_type', sa.String(20), nullable=False, default='task'))
    op.add_column('work_items', sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('work_items', sa.Column('path', sa.String(500), nullable=False, default='/'))
    op.add_column('work_items', sa.Column('depth', sa.Integer, nullable=False, default=0))
    op.add_column('work_items', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))

    op.create_foreign_key('fk_work_item_parent', 'work_items', 'work_items', ['parent_id'], ['id'])
    op.create_index('idx_work_item_parent_id', 'work_items', ['parent_id'])
    op.create_index('idx_work_item_path', 'work_items', ['path'])
    op.create_index('idx_work_item_type', 'work_items', ['item_type'])
    op.create_index('idx_work_item_deleted_at', 'work_items', ['deleted_at'], postgresql_where='deleted_at IS NULL')
    op.create_check_constraint('ck_work_item_type', 'work_items', "item_type IN ('project', 'session', 'task', 'research')")
    op.create_check_constraint('ck_work_item_depth', 'work_items', 'depth >= 0 AND depth <= 5')

    # 4. Create project_configuration (singleton)
    op.create_table(
        'project_configuration',
        sa.Column('id', sa.Integer, primary_key=True, default=1),
        sa.Column('active_context_type', sa.String(50), nullable=False),
        sa.Column('current_session_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('git_branch', sa.String(100), nullable=True),
        sa.Column('git_head_commit', sa.String(40), nullable=True),
        sa.Column('default_token_budget', sa.Integer, nullable=False, default=200000),
        sa.Column('database_healthy', sa.Boolean, nullable=False, default=True),
        sa.Column('last_health_check_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_by', sa.String(100), nullable=False),
        sa.CheckConstraint('id = 1', name='ck_singleton')
    )
    op.create_foreign_key('fk_current_session', 'project_configuration', 'work_items', ['current_session_id'], ['id'])

    # 5. Create future_enhancements
    op.create_table(
        'future_enhancements',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('priority', sa.Integer, nullable=False),
        sa.Column('status', sa.String(20), nullable=False, default='planned'),
        sa.Column('target_quarter', sa.String(10), nullable=True),
        sa.Column('requires_constitutional_principles', postgresql.JSONB, nullable=False, default=[]),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(100), nullable=False),
        sa.CheckConstraint('priority >= 1 AND priority <= 5', name='ck_priority_range'),
        sa.CheckConstraint("status IN ('planned', 'approved', 'implementing', 'completed')", name='ck_enhancement_status')
    )
    op.create_index('idx_enhancement_priority', 'future_enhancements', ['priority'])
    op.create_index('idx_enhancement_status', 'future_enhancements', ['status'])

    # 6. Create junction tables
    op.create_table(
        'work_item_dependencies',
        sa.Column('source_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('dependency_type', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(100), nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['work_items.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_id'], ['work_items.id'], ondelete='CASCADE'),
        sa.CheckConstraint("dependency_type IN ('blocks', 'depends_on')", name='ck_dependency_type'),
        sa.CheckConstraint('source_id != target_id', name='ck_no_self_dependency')
    )
    op.create_index('idx_dependency_source_id', 'work_item_dependencies', ['source_id'])
    op.create_index('idx_dependency_target_id', 'work_item_dependencies', ['target_id'])

    op.create_table(
        'vendor_deployment_links',
        sa.Column('deployment_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['deployment_id'], ['deployment_events.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['vendor_id'], ['vendor_extractors.id'], ondelete='CASCADE')
    )
    op.create_index('idx_vendor_deployment_deployment_id', 'vendor_deployment_links', ['deployment_id'])
    op.create_index('idx_vendor_deployment_vendor_id', 'vendor_deployment_links', ['vendor_id'])

    op.create_table(
        'work_item_deployment_links',
        sa.Column('deployment_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('work_item_id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['deployment_id'], ['deployment_events.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['work_item_id'], ['work_items.id'], ondelete='CASCADE')
    )
    op.create_index('idx_work_item_deployment_deployment_id', 'work_item_deployment_links', ['deployment_id'])
    op.create_index('idx_work_item_deployment_work_item_id', 'work_item_deployment_links', ['work_item_id'])

    # 7. Create archived_work_items
    op.create_table(
        'archived_work_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('item_type', sa.String(20), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('path', sa.String(500), nullable=False),
        sa.Column('depth', sa.Integer, nullable=False),
        sa.Column('branch_name', sa.String(100), nullable=True),
        sa.Column('commit_hash', sa.String(40), nullable=True),
        sa.Column('pr_number', sa.Integer, nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(100), nullable=False),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=False)
    )
    op.create_index('idx_archived_work_item_created_at', 'archived_work_items', ['created_at'])
    op.create_index('idx_archived_work_item_type', 'archived_work_items', ['item_type'])
    op.create_index('idx_archived_work_item_archived_at', 'archived_work_items', ['archived_at'])

def downgrade():
    # Drop in reverse order of creation
    op.drop_table('archived_work_items')
    op.drop_table('work_item_deployment_links')
    op.drop_table('vendor_deployment_links')
    op.drop_table('work_item_dependencies')
    op.drop_table('future_enhancements')
    op.drop_table('project_configuration')
    # Revert work_items extensions
    op.drop_constraint('fk_work_item_parent', 'work_items')
    op.drop_index('idx_work_item_parent_id', 'work_items')
    op.drop_index('idx_work_item_path', 'work_items')
    op.drop_index('idx_work_item_type', 'work_items')
    op.drop_index('idx_work_item_deleted_at', 'work_items')
    op.drop_column('work_items', 'version')
    op.drop_column('work_items', 'item_type')
    op.drop_column('work_items', 'parent_id')
    op.drop_column('work_items', 'path')
    op.drop_column('work_items', 'depth')
    op.drop_column('work_items', 'deleted_at')
    op.drop_table('deployment_events')
    op.drop_table('vendor_extractors')
```

### Data Migration (Legacy .project_status.md)

**Migration Script**: `src/services/project_status.py:migrate_legacy_markdown()`

**Steps**:
1. Parse .project_status.md sections (vendors, deployments, enhancements, sessions)
2. Validate Pydantic schemas for all JSONB metadata
3. Insert into PostgreSQL tables with transaction boundaries
4. Execute 5 reconciliation checks (FR-025):
   - Vendor count match
   - Deployment history completeness
   - Enhancements count match
   - Session prompts count match
   - Vendor metadata completeness
5. Rollback on any validation failure (FR-026)

**Reconciliation Query**:
```python
async def validate_migration():
    """Execute 5 reconciliation checks"""
    # 1. Vendor count
    md_vendor_count = count_vendors_in_markdown()
    db_vendor_count = await session.scalar(select(func.count()).select_from(VendorExtractor))
    assert md_vendor_count == db_vendor_count, "Vendor count mismatch"

    # 2. Deployment history
    md_deployments = parse_deployments_from_markdown()
    db_deployments = await session.execute(select(DeploymentEvent))
    assert len(md_deployments) == len(db_deployments.scalars().all()), "Deployment count mismatch"

    # 3. Enhancements count
    md_enhancements = parse_enhancements_from_markdown()
    db_enhancements = await session.scalar(select(func.count()).select_from(FutureEnhancement))
    assert len(md_enhancements) == db_enhancements, "Enhancement count mismatch"

    # 4. Session prompts count
    md_sessions = parse_session_prompts_from_git()
    db_sessions = await session.scalar(
        select(func.count()).select_from(WorkItem).where(WorkItem.item_type == 'session')
    )
    assert len(md_sessions) == db_sessions, "Session count mismatch"

    # 5. Vendor metadata completeness
    vendors = await session.execute(select(VendorExtractor))
    for vendor in vendors.scalars():
        assert vendor.metadata_.format_support, "Missing format_support"
        assert vendor.metadata_.test_results, "Missing test_results"
        assert vendor.metadata_.extractor_version, "Missing extractor_version"
```

---

## Summary

**9 Entities Defined**:
1. VendorExtractor - Vendor operational status tracking
2. DeploymentEvent - Deployment history with PR/commit details
3. WorkItem - Polymorphic hierarchical work items (extends Task)
4. ProjectConfiguration - Singleton global configuration
5. FutureEnhancement - Planned feature tracking
6. WorkItemDependency - Junction for work item dependencies
7. VendorDeploymentLink - Junction for deployment-vendor relationships
8. WorkItemDeploymentLink - Junction for deployment-work item relationships
9. ArchivedWorkItem - Archive table for old work items (1+ year)

**Key Design Decisions**:
- **Optimistic Locking**: Version column with SQLAlchemy `version_id_col` (prevents concurrent update conflicts)
- **Materialized Paths**: `/parent1/parent2/current` for <10ms ancestor queries
- **Pydantic JSONB**: Custom TypeDecorator validates metadata at ORM boundaries
- **Automatic Archiving**: Background task moves items >1 year to separate table
- **Performance Indexes**: 11 indexes strategically placed for <1ms, <10ms, <100ms targets

**Compliance**:
- **FR-002**: <1ms vendor queries via `idx_vendor_name` unique index
- **FR-013**: <10ms work item hierarchies via recursive CTE + materialized path
- **FR-023**: <100ms full status via parallel indexed queries
- **FR-037**: Optimistic locking prevents concurrent update conflicts
- **FR-039**: Automatic archiving maintains <10ms query performance

**Next Steps**:
- Generate `contracts/mcp-tools.yaml` with 8 MCP tool specifications
- Create `contracts/pydantic-schemas.py` with validation schemas
- Write contract tests in `tests/contract/`
- Implement `quickstart.md` with integration test scenarios
