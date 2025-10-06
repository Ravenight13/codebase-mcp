# Data Model: Production-Grade MCP Server

**Feature**: Production-Grade MCP Server for Semantic Code Search
**Date**: 2025-10-06
**Phase**: Phase 1 - Design & Contracts

## Entity Relationship Overview

```
Repository 1──────* CodeFile 1──────* CodeChunk 1─────1 Embedding
                       │
                       │
                       1
                       │
                       *
                   ChangeEvent

Task 1─────* TaskPlanningReference
     1─────* TaskBranchLink
     1─────* TaskCommitLink
     1─────* TaskStatusHistory
```

## Core Entities

### 1. Repository

Represents a code repository being indexed.

**SQLAlchemy Model**:
```python
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    path: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    code_files: Mapped[list["CodeFile"]] = relationship(back_populates="repository", cascade="all, delete-orphan")
```

**Pydantic Schema**:
```python
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

class RepositoryCreate(BaseModel):
    path: str = Field(..., description="Absolute path to repository")
    name: str = Field(..., description="Repository display name")

class RepositoryResponse(BaseModel):
    id: UUID
    path: str
    name: str
    last_indexed_at: datetime | None
    is_active: bool
    created_at: datetime
    file_count: int = Field(..., description="Number of indexed files")

    model_config = {"from_attributes": True}
```

---

### 2. CodeFile

Represents a source code file in the repository.

**SQLAlchemy Model**:
```python
class CodeFile(Base):
    __tablename__ = "code_files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False)
    path: Mapped[str] = mapped_column(String, nullable=False, index=True)
    relative_path: Mapped[str] = mapped_column(String, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA-256
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    language: Mapped[str | None] = mapped_column(String, nullable=True)
    modified_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    indexed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    repository: Mapped["Repository"] = relationship(back_populates="code_files")
    chunks: Mapped[list["CodeChunk"]] = relationship(back_populates="code_file", cascade="all, delete-orphan")
    change_events: Mapped[list["ChangeEvent"]] = relationship(back_populates="code_file", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_code_files_repo_path", "repository_id", "relative_path", unique=True),
    )
```

**Pydantic Schema**:
```python
class CodeFileResponse(BaseModel):
    id: UUID
    repository_id: UUID
    relative_path: str
    content_hash: str
    size_bytes: int
    language: str | None
    modified_at: datetime
    indexed_at: datetime
    is_deleted: bool
    chunk_count: int = Field(..., description="Number of code chunks")

    model_config = {"from_attributes": True}
```

---

### 3. CodeChunk

Represents a semantic chunk of code (function, class, or logical block).

**SQLAlchemy Model**:
```python
from pgvector.sqlalchemy import Vector

class CodeChunk(Base):
    __tablename__ = "code_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code_file_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("code_files.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_type: Mapped[str] = mapped_column(String, nullable=False)  # function, class, block
    embedding: Mapped[Vector] = mapped_column(Vector(768), nullable=True)  # nomic-embed-text
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    code_file: Mapped["CodeFile"] = relationship(back_populates="chunks")

    __table_args__ = (
        Index("ix_chunks_embedding_cosine", "embedding", postgresql_using="hnsw", postgresql_with={"m": 16, "ef_construction": 64}, postgresql_ops={"embedding": "vector_cosine_ops"}),
    )
```

**Pydantic Schema**:
```python
class CodeChunkCreate(BaseModel):
    code_file_id: UUID
    content: str
    start_line: int = Field(..., ge=1)
    end_line: int = Field(..., ge=1)
    chunk_type: str = Field(..., pattern="^(function|class|block)$")

class CodeChunkResponse(BaseModel):
    id: UUID
    code_file_id: UUID
    content: str
    start_line: int
    end_line: int
    chunk_type: str
    has_embedding: bool = Field(..., description="Whether embedding is generated")
    similarity_score: float | None = Field(None, description="Similarity score when from search")

    model_config = {"from_attributes": True}
```

---

### 4. Embedding

Metadata about embedding generation (stored with CodeChunk, tracked separately for analytics).

**SQLAlchemy Model**:
```python
class EmbeddingMetadata(Base):
    __tablename__ = "embedding_metadata"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_name: Mapped[str] = mapped_column(String, nullable=False, default="nomic-embed-text")
    model_version: Mapped[str | None] = mapped_column(String, nullable=True)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False, default=768)
    generation_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
```

---

### 5. Task

Represents a development task with status tracking.

**SQLAlchemy Model**:
```python
class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="need to be done", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    planning_references: Mapped[list["TaskPlanningReference"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    branch_links: Mapped[list["TaskBranchLink"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    commit_links: Mapped[list["TaskCommitLink"]] = relationship(back_populates="task", cascade="all, delete-orphan")
    status_history: Mapped[list["TaskStatusHistory"]] = relationship(back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("status IN ('need to be done', 'in-progress', 'complete')", name="valid_status"),
    )
```

**Pydantic Schema**:
```python
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    notes: str | None = None
    planning_references: list[str] = Field(default_factory=list, description="Relative file paths to planning docs")

class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    notes: str | None = None
    status: str | None = Field(None, pattern="^(need to be done|in-progress|complete)$")

class TaskResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    notes: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    planning_references: list[str]
    branches: list[str]
    commits: list[str]

    model_config = {"from_attributes": True}
```

---

### 6. TaskPlanningReference

Links tasks to planning documents (spec.md, plan.md, etc.).

**SQLAlchemy Model**:
```python
class TaskPlanningReference(Base):
    __tablename__ = "task_planning_references"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    reference_type: Mapped[str] = mapped_column(String, nullable=False)  # spec, plan, design, other
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    task: Mapped["Task"] = relationship(back_populates="planning_references")
```

---

### 7. TaskBranchLink

Associates tasks with git branches.

**SQLAlchemy Model**:
```python
class TaskBranchLink(Base):
    __tablename__ = "task_branch_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    branch_name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    task: Mapped["Task"] = relationship(back_populates="branch_links")

    __table_args__ = (
        Index("ix_branch_links_task_branch", "task_id", "branch_name", unique=True),
    )
```

---

### 8. TaskCommitLink

Associates tasks with git commits.

**SQLAlchemy Model**:
```python
class TaskCommitLink(Base):
    __tablename__ = "task_commit_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    commit_hash: Mapped[str] = mapped_column(String(40), nullable=False)
    commit_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    task: Mapped["Task"] = relationship(back_populates="commit_links")

    __table_args__ = (
        Index("ix_commit_links_task_commit", "task_id", "commit_hash", unique=True),
    )
```

---

### 9. TaskStatusHistory

Tracks task status transitions over time.

**SQLAlchemy Model**:
```python
class TaskStatusHistory(Base):
    __tablename__ = "task_status_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String, nullable=True)
    to_status: Mapped[str] = mapped_column(String, nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    task: Mapped["Task"] = relationship(back_populates="status_history")
```

---

### 10. ChangeEvent

Records file system changes for incremental indexing.

**SQLAlchemy Model**:
```python
class ChangeEvent(Base):
    __tablename__ = "change_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code_file_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("code_files.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)  # added, modified, deleted
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    code_file: Mapped["CodeFile"] = relationship(back_populates="change_events")
```

---

### 11. SearchQuery

Analytics for search queries (optional, for optimization).

**SQLAlchemy Model**:
```python
class SearchQuery(Base):
    __tablename__ = "search_queries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    filters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
```

---

## Validation Rules

### CodeFile
- `content_hash`: SHA-256 hex string (64 chars)
- `size_bytes`: Non-negative integer
- `modified_at`: Must not be in future
- `deleted_at`: Set only when `is_deleted=True`, trigger 90-day cleanup

### CodeChunk
- `start_line <= end_line`
- `chunk_type` in `['function', 'class', 'block']`
- `embedding`: 768-dimensional vector or NULL

### Task
- `status` in `['need to be done', 'in-progress', 'complete']`
- Status transition: Create history entry on change
- `updated_at`: Auto-update on modification

### TaskPlanningReference
- `file_path`: Relative path, must exist in file system
- `reference_type` in `['spec', 'plan', 'design', 'other']`

---

## State Transitions

### Task Status Flow
```
[Created] → need to be done
            ↓
        in-progress
            ↓
        complete
```

**Rules**:
- Can move from any status to any other status
- Each transition creates `TaskStatusHistory` entry
- `updated_at` timestamp updates on transition

### File Deletion Flow
```
[Indexed] → is_deleted=True, deleted_at=NOW
            ↓
        [Wait 90 days]
            ↓
        [Permanent cleanup]
```

**Rules**:
- Mark `is_deleted=True` when file removed from filesystem
- Set `deleted_at` to current timestamp
- Scheduled job removes records where `deleted_at < NOW - 90 days`
- Cascades to chunks and embeddings

---

## Indexes

### Performance-Critical Indexes
1. **code_chunks.embedding** (HNSW, cosine distance) - Fast similarity search
2. **code_files.repository_id, relative_path** (BTREE, unique) - File lookup
3. **tasks.status** (BTREE) - Task filtering
4. **change_events.detected_at** (BTREE) - Incremental processing
5. **search_queries.created_at** (BTREE) - Analytics queries

### Unique Constraints
1. `repositories.path` - One entry per repository path
2. `code_files(repository_id, relative_path)` - One entry per file
3. `task_branch_links(task_id, branch_name)` - One branch per task
4. `task_commit_links(task_id, commit_hash)` - One commit per task

---

## Database Initialization

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Set vector distance function (cosine for normalized embeddings)
-- (Handled by SQLAlchemy index definition)

-- Scheduled cleanup job (90-day retention)
CREATE OR REPLACE FUNCTION cleanup_deleted_files()
RETURNS void AS $$
BEGIN
    DELETE FROM code_files
    WHERE is_deleted = TRUE
      AND deleted_at < NOW() - INTERVAL '90 days';
END;
$$ LANGUAGE plpgsql;

-- Run cleanup daily
SELECT cron.schedule('cleanup-deleted-files', '0 2 * * *', 'SELECT cleanup_deleted_files()');
```

---

## Migration Strategy

1. **Alembic Setup**: Auto-generate migrations from SQLAlchemy models
2. **Initial Migration**: Create all tables, indexes, extensions
3. **Version Control**: Migration files in `migrations/versions/`
4. **Rollback Support**: Down migrations for all changes
5. **Data Preservation**: Never drop columns without migration path

**Example Migration**:
```python
# migrations/versions/001_initial_schema.py
def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # ... table creation via SQLAlchemy auto-generate

def downgrade():
    # ... table drops in reverse order
    op.execute("DROP EXTENSION IF EXISTS vector")
```
