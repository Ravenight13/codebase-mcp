# Data Model: Background Indexing

## Overview

This document defines the database schema and Pydantic models for the background indexing feature. The data model supports asynchronous repository indexing with progress tracking, checkpoint-based recovery, audit trail logging, and graceful cancellation.

**Design Principles**:
- **PostgreSQL-native state tracking**: All job state persisted in database, survives server restarts
- **JSONB for flexibility**: Checkpoint data and metadata stored in JSONB for schema evolution
- **ACID guarantees**: Checkpoint consistency via PostgreSQL transactions
- **Performance-optimized**: Indexes support <100ms status queries, <200ms list queries

**Constitutional Alignment**:
- Principle I (Simplicity): No external job queue, reuses existing database infrastructure
- Principle II (Local-First): No cloud dependencies, offline-capable storage
- Principle IV (Performance): Indexed queries, <1% overhead for progress tracking
- Principle V (Production Quality): Type safety, comprehensive error tracking, immutable audit log

## Database Schema

### Table: indexing_jobs

Primary table for tracking background indexing operations.

**Purpose**: Stores all metadata for asynchronous repository indexing jobs, including status, progress, checkpoints, and results.

**Columns**:
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique job identifier |
| repository_id | UUID | NULLABLE, FK repositories(id) ON DELETE SET NULL | Associated repository (NULL until created) |
| repo_path | TEXT | NOT NULL | Absolute path to repository |
| repo_name | TEXT | NOT NULL | Display name for repository |
| project_id | VARCHAR(255) | NOT NULL | Project workspace identifier |
| force_reindex | BOOLEAN | NOT NULL, DEFAULT FALSE | Whether to reindex existing repository |
| status | VARCHAR(20) | NOT NULL, CHECK IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'blocked') | Job lifecycle state |
| progress_percentage | INTEGER | NOT NULL, DEFAULT 0, CHECK (0 <= value <= 100) | Overall progress (0-100) |
| progress_message | TEXT | NULLABLE | Human-readable progress description |
| files_scanned | INTEGER | NOT NULL, DEFAULT 0 | Total files discovered during scanning |
| files_indexed | INTEGER | NOT NULL, DEFAULT 0 | Files processed so far |
| chunks_created | INTEGER | NOT NULL, DEFAULT 0 | Code chunks generated |
| error_message | TEXT | NULLABLE | Error description if failed |
| error_type | VARCHAR(255) | NULLABLE | Exception class name |
| error_traceback | TEXT | NULLABLE | Full Python traceback |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Job creation time |
| started_at | TIMESTAMPTZ | NULLABLE | When job started execution |
| completed_at | TIMESTAMPTZ | NULLABLE | When job finished (success or failure) |
| cancelled_at | TIMESTAMPTZ | NULLABLE | When user cancelled job |
| metadata | JSONB | NOT NULL, DEFAULT '{}'::jsonb | Checkpoints, estimates, custom data |

**Indexes**:
```sql
-- Fast queries for active jobs (status queries, concurrency control)
CREATE INDEX idx_indexing_jobs_status
ON indexing_jobs(status)
WHERE status IN ('pending', 'running');

-- Project isolation (list jobs for specific workspace)
CREATE INDEX idx_indexing_jobs_project_id
ON indexing_jobs(project_id);

-- FIFO queue ordering (oldest pending jobs first)
CREATE INDEX idx_indexing_jobs_created_at
ON indexing_jobs(created_at DESC);

-- Cleanup queries (7-day retention)
CREATE INDEX idx_indexing_jobs_completed_at
ON indexing_jobs(completed_at)
WHERE completed_at IS NOT NULL;
```

**Status Enum Values**:
- **pending**: Job created, waiting for execution slot (queued)
- **running**: Job actively processing files
- **completed**: Job finished successfully with results
- **failed**: Job terminated due to error
- **cancelled**: User requested cancellation, job stopped gracefully
- **blocked**: Job waiting for external resource (embedding service unavailable)

**Status Transitions**:
```
pending → running → completed
          ↓
          failed
          ↓
          cancelled
          ↓
          blocked → running (auto-resume when unblocked)
```

**Business Invariants**:
1. Jobs in 'completed' status MUST have `completed_at` timestamp set
2. Jobs in 'failed' status MUST have `error_message` populated
3. Jobs in 'cancelled' status MUST have `cancelled_at` timestamp set
4. `progress_percentage` MUST be monotonically increasing (never decreases)
5. Only one 'running' job per `repository_id` at any time (enforced via application logic)
6. `files_indexed` <= `files_scanned` (cannot process more files than discovered)
7. `started_at` >= `created_at` (cannot start before creation)
8. `completed_at` >= `started_at` (cannot complete before starting)
9. Final status ('completed', 'failed', 'cancelled') is immutable (no transitions back to 'running')

**Metadata JSONB Schema**:
```json
{
  "checkpoint": {
    "checkpoint_type": "file_list_snapshot",
    "checkpointed_at": "2025-10-17T10:30:15Z",
    "files_processed": [
      "/path/to/repo/file1.py",
      "/path/to/repo/file2.py"
    ],
    "files_remaining": 1234,
    "last_file_path": "/path/to/repo/file500.py",
    "embedding_batch_offset": 2500
  },
  "estimate": {
    "estimated_duration_seconds": 108.0,
    "estimation_method": "historical_average",
    "file_count": 15000,
    "estimated_at": "2025-10-17T10:25:00Z"
  },
  "timing": {
    "scanning_duration_seconds": 2.5,
    "chunking_duration_seconds": 45.0,
    "embedding_duration_seconds": 55.0,
    "writing_duration_seconds": 5.5
  },
  "performance": {
    "files_per_second": 150.0,
    "chunks_per_second": 500.0
  }
}
```

**Foreign Key Constraints**:
```sql
ALTER TABLE indexing_jobs
ADD CONSTRAINT fk_indexing_jobs_repository
FOREIGN KEY (repository_id) REFERENCES repositories(id)
ON DELETE SET NULL;  -- Keep job history even if repository deleted
```

**Table Creation DDL**:
```sql
CREATE TABLE indexing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID,
    repo_path TEXT NOT NULL,
    repo_name TEXT NOT NULL,
    project_id VARCHAR(255) NOT NULL,
    force_reindex BOOLEAN NOT NULL DEFAULT FALSE,

    -- Status tracking
    status VARCHAR(20) NOT NULL
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'blocked')),
    progress_percentage INTEGER NOT NULL DEFAULT 0
        CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    progress_message TEXT,

    -- Counters
    files_scanned INTEGER NOT NULL DEFAULT 0,
    files_indexed INTEGER NOT NULL DEFAULT 0,
    chunks_created INTEGER NOT NULL DEFAULT 0,

    -- Error tracking
    error_message TEXT,
    error_type VARCHAR(255),
    error_traceback TEXT,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,

    -- Checkpoints and metadata
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Foreign key
    CONSTRAINT fk_indexing_jobs_repository
        FOREIGN KEY (repository_id) REFERENCES repositories(id)
        ON DELETE SET NULL
);

-- Performance indexes
CREATE INDEX idx_indexing_jobs_status
    ON indexing_jobs(status)
    WHERE status IN ('pending', 'running');

CREATE INDEX idx_indexing_jobs_project_id
    ON indexing_jobs(project_id);

CREATE INDEX idx_indexing_jobs_created_at
    ON indexing_jobs(created_at DESC);

CREATE INDEX idx_indexing_jobs_completed_at
    ON indexing_jobs(completed_at)
    WHERE completed_at IS NOT NULL;

-- GIN index for JSONB metadata queries (optional, for future analytics)
CREATE INDEX idx_indexing_jobs_metadata
    ON indexing_jobs USING GIN (metadata);
```

---

### Table: job_events

Audit log table for tracking all significant state transitions and progress updates in background jobs.

**Purpose**: Provides complete history trail for debugging, monitoring, compliance, and post-mortem analysis.

**Columns**:
| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY, DEFAULT gen_random_uuid() | Unique event identifier |
| job_id | UUID | NOT NULL, FK indexing_jobs(id) ON DELETE CASCADE | Associated background job |
| event_type | VARCHAR(50) | NOT NULL, CHECK IN ('created', 'started', 'progress', 'completed', 'failed', 'cancelled', 'blocked', 'unblocked') | Type of event |
| event_data | JSONB | NOT NULL, DEFAULT '{}'::jsonb | Event-specific context data |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | When event occurred |

**Indexes**:
```sql
-- Fast lookup of all events for a job (debugging, audit queries)
CREATE INDEX idx_job_events_job_id
ON job_events(job_id, created_at DESC);

-- Event type filtering (monitoring queries: "show all failures")
CREATE INDEX idx_job_events_event_type
ON job_events(event_type);

-- Time-based cleanup (7-day retention enforcement)
CREATE INDEX idx_job_events_created_at
ON job_events(created_at DESC);

-- GIN index for JSONB event_data queries
CREATE INDEX idx_job_events_event_data
ON job_events USING GIN (event_data);
```

**Event Type Definitions**:

1. **created**: Job record created (initial state)
   ```json
   {
     "repo_path": "/path/to/repo",
     "repo_name": "my-repo",
     "project_id": "my-project",
     "force_reindex": false,
     "estimated_duration_seconds": 108.0
   }
   ```

2. **started**: Job execution began
   ```json
   {
     "concurrency_slot": 1,
     "active_jobs_count": 2
   }
   ```

3. **progress**: Progress update milestone
   ```json
   {
     "progress_percentage": 45,
     "progress_message": "Chunking files: 5000/10000",
     "files_scanned": 10000,
     "files_indexed": 5000,
     "chunks_created": 25000
   }
   ```

4. **completed**: Job finished successfully
   ```json
   {
     "files_indexed": 10000,
     "chunks_created": 50000,
     "duration_seconds": 95.5,
     "scanning_duration_seconds": 2.5,
     "chunking_duration_seconds": 45.0,
     "embedding_duration_seconds": 43.0,
     "writing_duration_seconds": 5.0
   }
   ```

5. **failed**: Job terminated with error
   ```json
   {
     "error_message": "Embedding service unavailable",
     "error_type": "ConnectionError",
     "files_indexed": 3000,
     "chunks_created": 15000,
     "duration_seconds": 35.0
   }
   ```

6. **cancelled**: User requested cancellation
   ```json
   {
     "cancelled_by": "user",
     "cancellation_reason": "Wrong repository selected",
     "files_indexed": 2000,
     "chunks_created": 10000,
     "partial_work_retained": true
   }
   ```

7. **blocked**: Job waiting for external resource
   ```json
   {
     "block_reason": "Embedding service unavailable",
     "retry_count": 3,
     "next_retry_at": "2025-10-17T10:35:00Z"
   }
   ```

8. **unblocked**: External resource available, job resumed
   ```json
   {
     "unblock_reason": "Embedding service restored",
     "blocked_duration_seconds": 45.0
   }
   ```

**Business Invariants**:
1. Events are immutable once created (no UPDATE operations)
2. Event timestamps MUST be monotonically increasing within a job
3. First event for any job MUST be 'created' type
4. 'completed', 'failed', or 'cancelled' events mark end of job lifecycle (no events after)
5. Progress update events MUST include `files_indexed` count in event_data
6. 'blocked' events MUST be followed by 'unblocked' or 'cancelled' events
7. Event count per job should not exceed 1000 (reasonable upper bound for 7-day retention)

**Foreign Key Constraints**:
```sql
ALTER TABLE job_events
ADD CONSTRAINT fk_job_events_job
FOREIGN KEY (job_id) REFERENCES indexing_jobs(id)
ON DELETE CASCADE;  -- Delete events when job deleted (7-day cleanup)
```

**Table Creation DDL**:
```sql
CREATE TABLE job_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL,
    event_type VARCHAR(50) NOT NULL
        CHECK (event_type IN (
            'created', 'started', 'progress', 'completed',
            'failed', 'cancelled', 'blocked', 'unblocked'
        )),
    event_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Foreign key
    CONSTRAINT fk_job_events_job
        FOREIGN KEY (job_id) REFERENCES indexing_jobs(id)
        ON DELETE CASCADE
);

-- Performance indexes
CREATE INDEX idx_job_events_job_id
    ON job_events(job_id, created_at DESC);

CREATE INDEX idx_job_events_event_type
    ON job_events(event_type);

CREATE INDEX idx_job_events_created_at
    ON job_events(created_at DESC);

CREATE INDEX idx_job_events_event_data
    ON job_events USING GIN (event_data);
```

---

## Pydantic Models

### IndexingJobStatus Enum

```python
from enum import Enum

class IndexingJobStatus(str, Enum):
    """Job lifecycle states."""

    PENDING = "pending"      # Queued, waiting for execution slot
    RUNNING = "running"      # Actively processing
    COMPLETED = "completed"  # Finished successfully
    FAILED = "failed"        # Terminated with error
    CANCELLED = "cancelled"  # User-requested cancellation
    BLOCKED = "blocked"      # Waiting for external resource
```

### IndexingJobCreate

```python
from pydantic import BaseModel, Field, field_validator
from pathlib import Path

class IndexingJobCreate(BaseModel):
    """Schema for creating a new background indexing job.

    Validation:
        - repo_path: Must be absolute path
        - repo_name: Non-empty display name
        - project_id: Valid project workspace identifier
    """

    repo_path: str = Field(
        ...,
        description="Absolute path to repository"
    )
    repo_name: str = Field(
        ...,
        description="Repository display name",
        min_length=1,
        max_length=255
    )
    project_id: str = Field(
        ...,
        description="Project workspace identifier",
        min_length=1,
        max_length=255
    )
    force_reindex: bool = Field(
        default=False,
        description="Whether to reindex existing repository"
    )

    @field_validator("repo_path")
    @classmethod
    def validate_absolute_path(cls, v: str) -> str:
        """Ensure path is absolute (security: prevent path traversal)."""
        path = Path(v)
        if not path.is_absolute():
            raise ValueError(f"repo_path must be absolute: {v}")
        return str(path.resolve())

    model_config = {"from_attributes": True}
```

### IndexingJobProgress

```python
from datetime import datetime
from uuid import UUID

class IndexingJobProgress(BaseModel):
    """Schema for job progress/status responses.

    Returned by:
        - get_indexing_status(job_id)
        - list_indexing_jobs(filters)
    """

    # Identity
    id: UUID
    repository_id: UUID | None
    repo_path: str
    repo_name: str
    project_id: str

    # Status
    status: IndexingJobStatus
    progress_percentage: int = Field(ge=0, le=100)
    progress_message: str | None

    # Counters
    files_scanned: int = Field(ge=0)
    files_indexed: int = Field(ge=0)
    chunks_created: int = Field(ge=0)

    # Error tracking
    error_message: str | None = None
    error_type: str | None = None

    # Timestamps
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None

    # Computed fields
    duration_seconds: float | None = Field(
        None,
        description="Job execution duration (completed_at - started_at)"
    )
    estimated_completion_at: datetime | None = Field(
        None,
        description="Estimated completion time based on progress"
    )

    model_config = {"from_attributes": True}
```

### IndexingJobResult

```python
class IndexingJobResult(BaseModel):
    """Schema for completed job results.

    Returned by:
        - get_indexing_status(job_id) for completed jobs
        - Stored in job_events with event_type='completed'
    """

    job_id: UUID
    status: IndexingJobStatus  # Must be 'completed'

    # Summary statistics
    files_indexed: int
    chunks_created: int
    duration_seconds: float

    # Phase timings
    scanning_duration_seconds: float
    chunking_duration_seconds: float
    embedding_duration_seconds: float
    writing_duration_seconds: float

    # Performance metrics
    files_per_second: float
    chunks_per_second: float

    model_config = {"from_attributes": True}
```

### JobEventCreate

```python
class JobEventCreate(BaseModel):
    """Schema for creating audit log events.

    Used internally by background worker to record state transitions.
    """

    job_id: UUID
    event_type: str = Field(
        ...,
        description="Event type (created, started, progress, completed, etc.)"
    )
    event_data: dict = Field(
        default_factory=dict,
        description="Event-specific context data (JSONB)"
    )

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Ensure event_type is valid."""
        valid_types = {
            "created", "started", "progress", "completed",
            "failed", "cancelled", "blocked", "unblocked"
        }
        if v not in valid_types:
            raise ValueError(f"Invalid event_type: {v}. Must be one of {valid_types}")
        return v

    model_config = {"from_attributes": True}
```

### JobEventResponse

```python
class JobEventResponse(BaseModel):
    """Schema for job event API responses.

    Returned by:
        - get_job_events(job_id) for audit trail queries
    """

    id: UUID
    job_id: UUID
    event_type: str
    event_data: dict
    created_at: datetime

    model_config = {"from_attributes": True}
```

### ProgressCallback Type

```python
from typing import Callable, Awaitable

ProgressCallback = Callable[[str, int, dict[str, int]], Awaitable[None]]
"""
Type alias for progress callback function.

Args:
    message: Human-readable progress message
    percentage: Progress 0-100
    counters: Dict with keys: files_scanned, files_indexed, chunks_created

Usage:
    async def my_callback(message: str, percentage: int, counters: dict[str, int]) -> None:
        await update_job_progress(job_id, message, percentage, **counters)
"""
```

---

## SQLAlchemy ORM Models

### IndexingJob Model

```python
from sqlalchemy import Boolean, Integer, String, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import uuid

class IndexingJob(Base):
    """SQLAlchemy model for background indexing jobs.

    Table: indexing_jobs

    Relationships:
        - repository: Many-to-one with Repository (optional)
        - events: One-to-many with JobEvent (cascade delete)

    Constraints:
        - status: CHECK constraint for enum values
        - progress_percentage: CHECK constraint for 0-100 range
        - Foreign key to repositories table (nullable)

    State Management:
        - status: Job lifecycle state (pending → running → completed/failed/cancelled)
        - progress_percentage: 0-100 integer (monotonically increasing)
        - metadata: JSONB for checkpoints and estimates
    """

    __tablename__ = "indexing_jobs"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Repository references
    repository_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    repo_path: Mapped[str] = mapped_column(Text, nullable=False)
    repo_name: Mapped[str] = mapped_column(Text, nullable=False)
    project_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    force_reindex: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )
    progress_percentage: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    progress_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Counters
    files_scanned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_indexed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chunks_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error_traceback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Metadata (checkpoints, estimates)
    metadata: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )

    # Relationships
    repository: Mapped["Repository"] = relationship(back_populates="indexing_jobs")
    events: Mapped[list["JobEvent"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan"
    )

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'blocked')",
            name="ck_indexing_jobs_status"
        ),
        CheckConstraint(
            "progress_percentage >= 0 AND progress_percentage <= 100",
            name="ck_indexing_jobs_progress_percentage"
        ),
    )
```

### JobEvent Model

```python
class JobEvent(Base):
    """SQLAlchemy model for job audit events.

    Table: job_events

    Relationships:
        - job: Many-to-one with IndexingJob

    Constraints:
        - event_type: CHECK constraint for enum values
        - Foreign key to indexing_jobs table (cascade delete)

    Immutability:
        - Events are never updated after creation
        - Only INSERT and SELECT operations (no UPDATE)
    """

    __tablename__ = "job_events"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Job reference
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("indexing_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Event data
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    event_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )

    # Relationships
    job: Mapped["IndexingJob"] = relationship(back_populates="events")

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('created', 'started', 'progress', 'completed', 'failed', 'cancelled', 'blocked', 'unblocked')",
            name="ck_job_events_event_type"
        ),
    )
```

---

## Entity Relationships

### Relationship Diagram

```
Repository (existing)
    ↓ (1:N, optional, ON DELETE SET NULL)
IndexingJob
    ↓ (1:N, cascade delete)
JobEvent
```

**Relationship Details**:

1. **Repository → IndexingJob** (One-to-Many, Optional)
   - One repository can have many indexing jobs over time
   - `repository_id` is nullable (repository may not exist yet at job creation)
   - Foreign key constraint: ON DELETE SET NULL (preserve job history even if repository deleted)
   - Use case: Track all indexing attempts for a repository

2. **IndexingJob → JobEvent** (One-to-Many, Mandatory)
   - One job has many events (audit trail)
   - Cascade delete: when job is deleted, all events are deleted
   - Events provide complete history of job lifecycle
   - Use case: Debugging, monitoring, compliance auditing

---

## Checkpoint Strategy

### Checkpoint Data Structure (JSONB)

Checkpoints are stored in `indexing_jobs.metadata` JSONB column under the `checkpoint` key.

**File List Snapshot** (Phase 1 implementation):
```json
{
  "checkpoint": {
    "checkpoint_type": "file_list_snapshot",
    "checkpointed_at": "2025-10-17T10:30:15Z",
    "files_processed": [
      "/path/to/repo/file1.py",
      "/path/to/repo/file2.py",
      "/path/to/repo/file500.py"
    ],
    "files_remaining": 9500,
    "last_file_path": "/path/to/repo/file500.py",
    "embedding_batch_offset": 2500
  }
}
```

**Progress Marker** (Future optimization):
```json
{
  "checkpoint": {
    "checkpoint_type": "progress_marker",
    "checkpointed_at": "2025-10-17T10:30:15Z",
    "last_file_index": 500,
    "last_file_path": "/path/to/repo/file500.py",
    "total_files": 10000,
    "embedding_batch_offset": 2500
  }
}
```

### Checkpoint Frequency

- **Every 500 files**: Batch-based checkpoint during chunking phase
- **Every 30 seconds**: Time-based checkpoint for slow file processing
- **Before cancellation**: Graceful shutdown checkpoint

**Trade-offs**:
- 500 files = <1% duplicate work on recovery (acceptable)
- 30 seconds = ensures checkpoint even for large files
- Total overhead: <1% performance impact

### Recovery Algorithm

```python
async def resume_interrupted_job(job_id: UUID, project_id: str) -> None:
    """Resume indexing job from last checkpoint.

    Strategy:
    1. Query indexing_jobs for job with status='running'
    2. Load checkpoint data from metadata->checkpoint
    3. Re-scan repository to get current file list
    4. Diff checkpoint vs current files to find unprocessed files
    5. Resume indexing from unprocessed files
    6. Update progress counters to account for already-processed files
    """
    async with get_session(project_id) as db:
        result = await db.execute(
            select(IndexingJob).where(IndexingJob.id == job_id)
        )
        job = result.scalar_one()

    # Extract checkpoint
    checkpoint = job.metadata.get("checkpoint", {})
    files_processed = set(checkpoint.get("files_processed", []))

    # Re-scan repository
    all_files = await scan_repository(Path(job.repo_path))

    # Compute unprocessed files
    files_remaining = [f for f in all_files if str(f) not in files_processed]

    # Resume indexing with adjusted progress
    await index_repository(
        repo_path=Path(job.repo_path),
        name=job.repo_name,
        project_id=job.project_id,
        force_reindex=job.force_reindex,
        files_to_process=files_remaining,
        initial_progress={
            "files_indexed": job.files_indexed,
            "chunks_created": job.chunks_created,
        },
        progress_callback=create_progress_callback(job_id, project_id)
    )
```

---

## Migration DDL

### Alembic Migration Script

**Revision**: `add_background_indexing_tables`
**Parent Revision**: `<latest_migration>`

```python
"""Add background indexing tables.

Revision ID: add_background_indexing_tables
Revises: <latest_migration>
Create Date: 2025-10-17 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_background_indexing_tables'
down_revision = '<latest_migration>'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create indexing_jobs and job_events tables."""

    # Create indexing_jobs table
    op.create_table(
        'indexing_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('repository_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('repo_path', sa.Text(), nullable=False),
        sa.Column('repo_name', sa.Text(), nullable=False),
        sa.Column('project_id', sa.String(length=255), nullable=False),
        sa.Column('force_reindex', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('progress_percentage', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('progress_message', sa.Text(), nullable=True),
        sa.Column('files_scanned', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('files_indexed', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('chunks_created', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_type', sa.String(length=255), nullable=True),
        sa.Column('error_traceback', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'blocked')",
            name='ck_indexing_jobs_status'
        ),
        sa.CheckConstraint(
            'progress_percentage >= 0 AND progress_percentage <= 100',
            name='ck_indexing_jobs_progress_percentage'
        ),
        sa.ForeignKeyConstraint(
            ['repository_id'],
            ['repositories.id'],
            name='fk_indexing_jobs_repository',
            ondelete='SET NULL'
        ),
    )

    # Create indexes for indexing_jobs
    op.create_index(
        'idx_indexing_jobs_status',
        'indexing_jobs',
        ['status'],
        postgresql_where=sa.text("status IN ('pending', 'running')")
    )
    op.create_index('idx_indexing_jobs_project_id', 'indexing_jobs', ['project_id'])
    op.create_index('idx_indexing_jobs_created_at', 'indexing_jobs', [sa.text('created_at DESC')])
    op.create_index(
        'idx_indexing_jobs_completed_at',
        'indexing_jobs',
        ['completed_at'],
        postgresql_where=sa.text('completed_at IS NOT NULL')
    )
    op.create_index(
        'idx_indexing_jobs_metadata',
        'indexing_jobs',
        ['metadata'],
        postgresql_using='gin'
    )

    # Create job_events table
    op.create_table(
        'job_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('event_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint(
            "event_type IN ('created', 'started', 'progress', 'completed', 'failed', 'cancelled', 'blocked', 'unblocked')",
            name='ck_job_events_event_type'
        ),
        sa.ForeignKeyConstraint(
            ['job_id'],
            ['indexing_jobs.id'],
            name='fk_job_events_job',
            ondelete='CASCADE'
        ),
    )

    # Create indexes for job_events
    op.create_index('idx_job_events_job_id', 'job_events', ['job_id', sa.text('created_at DESC')])
    op.create_index('idx_job_events_event_type', 'job_events', ['event_type'])
    op.create_index('idx_job_events_created_at', 'job_events', [sa.text('created_at DESC')])
    op.create_index(
        'idx_job_events_event_data',
        'job_events',
        ['event_data'],
        postgresql_using='gin'
    )


def downgrade() -> None:
    """Drop indexing_jobs and job_events tables."""

    # Drop job_events table (must drop first due to FK constraint)
    op.drop_index('idx_job_events_event_data', table_name='job_events')
    op.drop_index('idx_job_events_created_at', table_name='job_events')
    op.drop_index('idx_job_events_event_type', table_name='job_events')
    op.drop_index('idx_job_events_job_id', table_name='job_events')
    op.drop_table('job_events')

    # Drop indexing_jobs table
    op.drop_index('idx_indexing_jobs_metadata', table_name='indexing_jobs')
    op.drop_index('idx_indexing_jobs_completed_at', table_name='indexing_jobs')
    op.drop_index('idx_indexing_jobs_created_at', table_name='indexing_jobs')
    op.drop_index('idx_indexing_jobs_project_id', table_name='indexing_jobs')
    op.drop_index('idx_indexing_jobs_status', table_name='indexing_jobs')
    op.drop_table('indexing_jobs')
```

---

## Performance Characteristics

### Query Performance Targets

| Query Type | Target Latency | Index Used |
|------------|----------------|------------|
| Get job status by ID | <50ms | Primary key (id) |
| List active jobs (status IN ('pending', 'running')) | <100ms | idx_indexing_jobs_status |
| List jobs by project | <200ms | idx_indexing_jobs_project_id |
| Get job events for audit | <150ms | idx_job_events_job_id |
| Cleanup old completed jobs | <500ms | idx_indexing_jobs_completed_at |
| Count active jobs for concurrency | <50ms | idx_indexing_jobs_status |

### Progress Update Overhead

- **Update frequency**: Every 2 seconds (30 updates/minute per job)
- **Transaction size**: Single UPDATE statement (<1KB)
- **Overhead per 10K files**: ~200ms (0.3% of 60s target)
- **Impact on indexing speed**: <1% (acceptable)

### Storage Requirements

**Per Job**:
- Base record: ~500 bytes (excluding JSONB)
- Checkpoint data: ~5-10 KB (500 file paths × 10-20 bytes each)
- Metadata: ~1-2 KB (estimates, timing)
- Total: ~7-13 KB per job

**Per Event**:
- Base record: ~200 bytes (excluding JSONB)
- Event data: ~500 bytes (progress counters, error messages)
- Total: ~700 bytes per event

**7-Day Retention**:
- 100 jobs × 13 KB = 1.3 MB (jobs)
- 100 jobs × 50 events × 700 bytes = 3.5 MB (events)
- Total: ~5 MB (negligible compared to code chunks and embeddings)

---

## Validation Rules

### Application-Level Validation

1. **Job Creation**:
   - `repo_path` must be absolute path (security: prevent path traversal)
   - `project_id` must be non-empty (isolation requirement)
   - `progress_percentage` must be 0-100 (enforced by CHECK constraint)

2. **Status Transitions**:
   - `pending` → `running` → `completed`|`failed`|`cancelled`
   - `running` → `blocked` → `running` (transient blocking)
   - Final states (`completed`, `failed`, `cancelled`) are immutable

3. **Progress Updates**:
   - `files_indexed` <= `files_scanned` (cannot process more than discovered)
   - `progress_percentage` must be monotonically increasing
   - `progress_message` should be non-empty during updates

4. **Completion Invariants**:
   - `status='completed'` requires `completed_at` timestamp
   - `status='failed'` requires `error_message`
   - `status='cancelled'` requires `cancelled_at` timestamp

5. **Concurrency Control**:
   - Maximum 3 jobs with `status='running'` at any time (application-enforced)
   - Only one `running` job per `repository_id` (application-enforced)

### Database-Level Constraints

1. **CHECK Constraints**:
   - `status` IN enum values
   - `progress_percentage` 0-100 range
   - `event_type` IN enum values

2. **Foreign Key Constraints**:
   - `repository_id` references `repositories(id)` (ON DELETE SET NULL)
   - `job_id` references `indexing_jobs(id)` (ON DELETE CASCADE)

3. **NOT NULL Constraints**:
   - Core fields: `repo_path`, `repo_name`, `project_id`, `status`
   - Counters: `files_scanned`, `files_indexed`, `chunks_created`
   - Timestamps: `created_at`

---

## Summary

This data model provides:

- **Comprehensive state tracking**: All job lifecycle states, progress, errors, and results
- **Checkpoint-based recovery**: JSONB checkpoints for automatic resumption after interruptions
- **Audit trail**: Immutable event log for debugging, monitoring, and compliance
- **Performance optimization**: Indexes for <100ms status queries, <200ms list queries
- **Production quality**: Type safety, validation, proper constraints, and foreign keys
- **Constitutional compliance**: Simplicity (PostgreSQL-native), Local-First (no external dependencies), Performance (indexed queries)

All 3 entities (IndexingJob, JobCheckpoint via JSONB, JobEvent) are fully specified with:
- Complete table definitions with columns, types, constraints
- Indexes supporting constitutional performance targets
- Pydantic models with validation
- Business invariants documented
- Migration DDL included
- Checkpoint strategy and recovery algorithm detailed