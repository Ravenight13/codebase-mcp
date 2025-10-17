# Background Indexing MVP Implementation Tasks

## Executive Summary

**Scope**: User Story 1 only - Background indexing with basic status tracking
**Tasks**: 13 tasks (50% reduction from full plan)
**Timeline**: 6-7 hours (58% faster than full 10-12 hour plan)
**Code**: ~1,200-1,500 lines (50% less than full plan)
**Approach**: MVP-first, reuse existing infrastructure, defer enhancements

### MVP Features

✅ Non-blocking indexing for large repositories (10K+ files)
✅ Immediate job_id response (<1s)
✅ Status tracking (pending/running/completed/failed)
✅ State persistence across server restarts
✅ Production-quality error handling

### Deferred to Phase 2 (Based on User Feedback)

⏸️ Job listing with filters (list_background_jobs)
⏸️ ETA calculation and granular progress
⏸️ Job cancellation
⏸️ Resumption after failures
⏸️ Phase-specific progress messages

## Implementation Timeline

| Phase | Tasks | Time | Description |
|-------|-------|------|-------------|
| Phase 1 | T001-T002 | 1h | Database schema |
| Phase 2 | T003-T003test | 1h | Models and validation |
| Phase 3 | T004-T008 | 2.5h | Core implementation |
| Phase 4 | T009-T012 | 1h | Production hardening |
| Phase 5 | T013 | 0.5h | Validation |
| **Total** | **13 tasks** | **6-7h** | **MVP complete** |

## Critical Path

**T001 → T002 → T003 → T004 → T005 → T006 → T013** (5.5 hours)

### Parallel Opportunities

- T003-test can run parallel with T004 (after T003)
- T009-T012 can run in parallel (documentation and config)

## Success Metrics

✅ Index 10K+ file repository without timeout
✅ Job creation responds in <1 second
✅ State persists across server restart
✅ Complete workflow test passes
✅ Documentation updated

## Constitutional Compliance

- **Principle I (Simplicity)**: 50% less code, reuses existing infrastructure
- **Principle II (Local-First)**: No external dependencies, PostgreSQL only
- **Principle V (Production Quality)**: Error handling, state persistence, testing
- **Principle VIII (Type Safety)**: Pydantic validation, mypy compliance

---

## Key Simplifications Applied

### 1. Defer US2 Entirely
- **Removed**: list_background_jobs(), ETA calculation, phase-specific messages
- **Keep**: Just start + status tools
- **Rationale**: Users need to start jobs and check status. Listing and ETAs are nice-to-have.

### 2. Reuse Database Session Infrastructure
- **Use**: Existing `get_session(ctx=ctx)` from session.py
- **Use**: SQLAlchemy ORM, not raw SQL
- **No**: Custom transaction management
- **Rationale**: session.py already handles project resolution, connection pooling, transactions

### 3. No Progress Callbacks
- **Don't modify**: indexer.py at all
- **Worker updates**: pending → running → completed/failed
- **No**: Granular progress during execution
- **Rationale**: MVP doesn't need real-time progress. Binary state (running/done) is sufficient.

### 4. Single Database Update Pattern
All job updates use one function:
```python
async def update_job(job_id: UUID, ctx: Context, **kwargs):
    """Update job fields atomically."""
    async with get_session(ctx=ctx) as session:
        job = await session.get(IndexingJob, job_id)
        for key, value in kwargs.items():
            setattr(job, key, value)
        await session.commit()
```

### 5. Simplified Worker
```python
async def _background_indexing_worker(job_id: UUID, repo_path: str, ctx: Context):
    try:
        await update_job(job_id, ctx=ctx, status="running", started_at=datetime.now())
        result = await index_repository_service(...)  # Existing service, no changes
        await update_job(job_id, ctx=ctx, status="completed", files_indexed=result.files_indexed)
    except Exception as e:
        await update_job(job_id, ctx=ctx, status="failed", error_message=str(e))
```

### 6. Simplified Schema
**Essential columns only** (10 vs. 18):
- id, repo_path, project_id, status, error_message
- started_at, completed_at, created_at
- files_indexed, chunks_created

**Removed** (deferred to Phase 2):
- progress_percentage, progress_message, files_scanned
- error_type, error_traceback, cancelled_at
- metadata, worker_task_id, connection_id
- force_reindex flag

---

## Phase 1: Database Schema (1 hour)

### T001: Create simplified Alembic migration [Implementation]
**Phase**: 1 - Database Schema
**Estimated Time**: 45 minutes
**Dependencies**: None (critical path start)
**User Story**: Infrastructure (enables US1)

**Description**:
Create Alembic migration for simplified indexing_jobs table with only essential columns.

**Deliverables**:
- [ ] Migration file: `migrations/versions/008_add_indexing_jobs.py`
- [ ] Table with 10 essential columns
- [ ] 2 performance indexes
- [ ] Status CHECK constraint
- [ ] Upgrade and downgrade functions

**Schema**:
```sql
CREATE TABLE indexing_jobs (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Input
    repo_path TEXT NOT NULL,
    project_id VARCHAR(255) NOT NULL,

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    error_message TEXT,

    -- Counters
    files_indexed INTEGER DEFAULT 0,
    chunks_created INTEGER DEFAULT 0,

    -- Timestamps
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Performance indexes
CREATE INDEX idx_active_jobs ON indexing_jobs(project_id, status)
    WHERE status IN ('pending', 'running');
CREATE INDEX idx_created_at ON indexing_jobs(created_at DESC);
```

**Acceptance Criteria**:
- [ ] Migration passes `alembic check`
- [ ] Table created with correct schema (10 columns)
- [ ] Indexes optimize active job queries (<10ms)
- [ ] Downgrade cleanly removes table

**Constitutional Principles**:
- Principle I: Simplicity (10 columns vs. 18)
- Principle V: Production Quality (indexes, constraints)

**Time Estimate**: 45 minutes

---

### T002: Apply migration and validate [Migration]
**Phase**: 1 - Database Schema
**Estimated Time**: 15 minutes
**Dependencies**: T001

**Description**:
Apply the migration to test database and verify schema correctness.

**Deliverables**:
- [ ] Run migration on test database
- [ ] Verify table structure with `\d indexing_jobs`
- [ ] Verify indexes with `\di`
- [ ] Test INSERT with valid data
- [ ] Test CHECK constraint rejects invalid status

**Acceptance Criteria**:
- [ ] `alembic upgrade head` succeeds
- [ ] Table has exactly 10 columns
- [ ] Both indexes created
- [ ] `INSERT ... VALUES ('invalid_status')` fails
- [ ] `SELECT * FROM indexing_jobs` returns empty set

**Constitutional Principles**:
- Principle V: Production Quality (validation before proceeding)

**Time Estimate**: 15 minutes

---

## Phase 2: Models (1 hour)

### T003: Create IndexingJob SQLAlchemy model + Pydantic models [Implementation]
**Phase**: 2 - Models
**Estimated Time**: 45 minutes
**Dependencies**: T002 (schema exists)

**Description**:
Create SQLAlchemy ORM model and Pydantic validation models for indexing jobs.

**Deliverables**:
- [ ] File: `src/models/indexing_job.py`
- [ ] IndexingJob SQLAlchemy model (maps to table)
- [ ] IndexingJobCreate Pydantic model (validation)
- [ ] IndexingJobResponse Pydantic model (API response)
- [ ] Path validation with security checks
- [ ] Export in `src/models/__init__.py`

**Models**:
```python
# SQLAlchemy ORM Model
from sqlalchemy import Column, String, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from src.models.database import Base
import uuid

class IndexingJob(Base):
    """Background indexing job record."""
    __tablename__ = "indexing_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_path = Column(Text, nullable=False)
    project_id = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    files_indexed = Column(Integer, default=0)
    chunks_created = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now)

# Pydantic Validation Models
from pydantic import BaseModel, Field, validator
from datetime import datetime
from uuid import UUID
import os
from pathlib import Path

class IndexingJobCreate(BaseModel):
    """Input validation for creating indexing job."""
    repo_path: str = Field(min_length=1)
    project_id: str = Field(min_length=1)

    @validator('repo_path')
    def validate_repo_path(cls, v: str) -> str:
        """Validate repo_path is absolute and no path traversal."""
        # Must be absolute
        if not os.path.isabs(v):
            raise ValueError(f"repo_path must be absolute, got: {v}")

        # Resolve to detect traversal
        resolved = Path(v).resolve()
        original = Path(v)

        # Basic traversal check: resolved should start with original's parent
        if not str(resolved).startswith(str(original.parent.resolve())):
            raise ValueError(f"Path traversal detected in repo_path: {v}")

        return v

class IndexingJobResponse(BaseModel):
    """API response model."""
    job_id: UUID
    status: str
    repo_path: str
    project_id: str
    error_message: str | None
    files_indexed: int
    chunks_created: int
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime

    class Config:
        orm_mode = True  # Allow SQLAlchemy models
```

**Acceptance Criteria**:
- [ ] SQLAlchemy model maps to database table
- [ ] Create model validates absolute paths
- [ ] Create model rejects relative paths
- [ ] Create model rejects path traversal (../)
- [ ] Response model serializes from SQLAlchemy
- [ ] mypy --strict passes

**Constitutional Principles**:
- Principle VIII: Type Safety (Pydantic, SQLAlchemy)
- Principle V: Production Quality (security validation)

**Time Estimate**: 45 minutes

---

### T003-test: Unit tests for models [Testing]
**Phase**: 2 - Models
**Estimated Time**: 15 minutes
**Dependencies**: T003
**Parallel**: Can run parallel with T004

**Description**:
Unit tests for path validation and model serialization.

**Deliverables**:
- [ ] File: `tests/unit/test_indexing_job_models.py`
- [ ] Test absolute path accepted
- [ ] Test relative path rejected
- [ ] Test path traversal rejected
- [ ] Test model serialization

**Test Cases**:
```python
def test_valid_absolute_path():
    """Test absolute paths are accepted."""
    job = IndexingJobCreate(
        repo_path="/tmp/test-repo",
        project_id="test-project",
    )
    assert job.repo_path == "/tmp/test-repo"

def test_relative_path_rejected():
    """Test relative paths are rejected."""
    with pytest.raises(ValueError, match="must be absolute"):
        IndexingJobCreate(
            repo_path="./relative/path",
            project_id="test",
        )

@pytest.mark.parametrize("malicious_path", [
    "/var/data/../../etc/passwd",
    "/tmp/../../../etc/shadow",
])
def test_path_traversal_rejected(malicious_path):
    """Test path traversal patterns are rejected."""
    with pytest.raises(ValueError, match="Path traversal detected"):
        IndexingJobCreate(
            repo_path=malicious_path,
            project_id="test",
        )
```

**Acceptance Criteria**:
- [ ] All path validation tests pass
- [ ] Model serialization tests pass
- [ ] Coverage >90% for models module

**Time Estimate**: 15 minutes

---

## Phase 3: Core Implementation (2.5 hours)

### T004: Implement simplified background worker [Implementation]
**Phase**: 3 - Core Implementation
**Estimated Time**: 45 minutes
**Dependencies**: T003 (models exist)

**Description**:
Create the background worker that runs indexing and updates database state.

**Deliverables**:
- [ ] File: `src/services/background_worker.py`
- [ ] Worker function using asyncio.Task
- [ ] Simple state machine: pending → running → completed/failed
- [ ] Uses existing index_repository_service (no modifications)
- [ ] Error handling with full exception capture

**Implementation**:
```python
# src/services/background_worker.py
from uuid import UUID
from pathlib import Path
from datetime import datetime
from fastmcp import Context
from src.database.session import get_session
from src.services.indexer import index_repository as index_repository_service
from src.models.indexing_job import IndexingJob
from src.mcp.mcp_logging import get_logger

logger = get_logger(__name__)

async def _background_indexing_worker(
    job_id: UUID,
    repo_path: str,
    project_id: str,
    ctx: Context | None = None,
) -> None:
    """Background worker that executes indexing and updates PostgreSQL.

    Simple state machine: pending → running → completed/failed
    No progress callbacks - binary state only.

    Args:
        job_id: UUID of indexing_jobs row
        repo_path: Absolute path to repository
        project_id: Resolved project identifier
        ctx: Optional FastMCP Context for session resolution
    """
    logger.info(
        f"Background worker started for job {job_id}",
        extra={"context": {"job_id": str(job_id), "project_id": project_id}},
    )

    try:
        # Update to running
        async with get_session(project_id=project_id, ctx=ctx) as session:
            job = await session.get(IndexingJob, job_id)
            if job is None:
                logger.error(f"Job {job_id} not found")
                return

            job.status = "running"
            job.started_at = datetime.now()
            await session.commit()

        # Run existing indexer (NO MODIFICATIONS to indexer.py)
        async with get_session(project_id=project_id, ctx=ctx) as session:
            result = await index_repository_service(
                repo_path=Path(repo_path),
                name=Path(repo_path).name,
                db=session,
                project_id=project_id,
                force_reindex=False,  # MVP doesn't support force_reindex
            )

        # Update to completed
        async with get_session(project_id=project_id, ctx=ctx) as session:
            job = await session.get(IndexingJob, job_id)
            if job is None:
                logger.error(f"Job {job_id} not found for completion update")
                return

            job.status = "completed"
            job.completed_at = datetime.now()
            job.files_indexed = result.files_indexed
            job.chunks_created = result.chunks_created
            await session.commit()

        logger.info(
            f"Job {job_id} completed successfully",
            extra={
                "context": {
                    "job_id": str(job_id),
                    "files_indexed": result.files_indexed,
                    "chunks_created": result.chunks_created,
                }
            },
        )

    except Exception as e:
        # Update to failed
        logger.error(
            f"Job {job_id} failed with error",
            extra={
                "context": {
                    "job_id": str(job_id),
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            },
            exc_info=True,
        )

        try:
            async with get_session(project_id=project_id, ctx=ctx) as session:
                job = await session.get(IndexingJob, job_id)
                if job is not None:
                    job.status = "failed"
                    job.error_message = str(e)
                    job.completed_at = datetime.now()
                    await session.commit()
        except Exception as update_error:
            logger.error(
                f"Failed to update job {job_id} status to failed",
                extra={"context": {"error": str(update_error)}},
            )
```

**Acceptance Criteria**:
- [ ] Worker updates status: pending → running → completed/failed
- [ ] Uses existing index_repository_service (no modifications)
- [ ] Error messages captured in error_message field
- [ ] Worker completes even if indexing fails
- [ ] All database updates committed

**Constitutional Principles**:
- Principle I: Simplicity (reuses existing indexer, no callbacks)
- Principle V: Production Quality (error handling)

**Time Estimate**: 45 minutes

---

### T005: Implement start_indexing_background() MCP tool [Implementation]
**Phase**: 3 - Core Implementation
**Estimated Time**: 30 minutes
**Dependencies**: T004 (worker exists)

**Description**:
Create FastMCP tool that creates job record and spawns worker task.

**Deliverables**:
- [ ] File: `src/mcp/tools/background_indexing.py`
- [ ] @mcp.tool() decorator
- [ ] Creates job record with validated input
- [ ] Spawns worker via asyncio.create_task()
- [ ] Returns job_id immediately (<1s)

**Implementation**:
```python
# src/mcp/tools/background_indexing.py
from fastmcp import Context
from uuid import UUID
import asyncio
from pathlib import Path
from typing import Any

from src.models.indexing_job import IndexingJobCreate, IndexingJob
from src.database.session import get_session, resolve_project_id
from src.services.background_worker import _background_indexing_worker
from src.mcp.mcp_logging import get_logger
from src.mcp.server_fastmcp import mcp

logger = get_logger(__name__)

@mcp.tool()
async def start_indexing_background(
    repo_path: str,
    project_id: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Start repository indexing in the background (non-blocking).

    Returns immediately with job_id. Use get_indexing_status(job_id) to poll progress.

    Args:
        repo_path: Absolute path to repository (validated)
        project_id: Optional project identifier (resolved via 4-tier chain)
        ctx: FastMCP Context for session-based project resolution

    Returns:
        {
            "job_id": "uuid",
            "status": "pending",
            "message": "Indexing job started",
            "project_id": "resolved_project_id",
            "database_name": "cb_proj_xxx"
        }

    Raises:
        ValueError: If repo_path validation fails (path traversal, not absolute)

    Example:
        >>> result = await start_indexing_background(
        ...     repo_path="/Users/alice/projects/myapp",
        ...     ctx=ctx
        ... )
        >>> job_id = result["job_id"]
        >>> # Poll status:
        >>> status = await get_indexing_status(job_id=job_id)
    """
    # Resolve project_id via 4-tier chain
    resolved_id, database_name = await resolve_project_id(
        explicit_id=project_id,
        ctx=ctx,
    )

    # Validate input (includes path traversal check)
    job_input = IndexingJobCreate(
        repo_path=repo_path,
        project_id=resolved_id,
    )

    # Create job record in database (status=pending)
    async with get_session(project_id=resolved_id, ctx=ctx) as session:
        job = IndexingJob(
            repo_path=job_input.repo_path,
            project_id=resolved_id,
            status="pending",
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        job_id = job.id

    # Start background worker (non-blocking)
    asyncio.create_task(
        _background_indexing_worker(
            job_id=job_id,
            repo_path=job_input.repo_path,
            project_id=resolved_id,
            ctx=ctx,
        )
    )

    logger.info(
        f"Indexing job created: {job_id}",
        extra={
            "context": {
                "job_id": str(job_id),
                "project_id": resolved_id,
                "repo_path": job_input.repo_path,
            }
        },
    )

    if ctx:
        await ctx.info(f"Indexing started in background. Job ID: {job_id}")

    return {
        "job_id": str(job_id),
        "status": "pending",
        "message": "Indexing job started",
        "project_id": resolved_id,
        "database_name": database_name,
    }
```

**Acceptance Criteria**:
- [ ] Tool registered in FastMCP server
- [ ] Path validation rejects invalid inputs
- [ ] Job record created with status=pending
- [ ] Worker task spawned asynchronously
- [ ] Returns immediately (<1s)
- [ ] Response includes job_id, status, project_id

**Constitutional Principles**:
- Principle XI: FastMCP Foundation (@mcp.tool())
- Principle IV: Performance (non-blocking)

**Time Estimate**: 30 minutes

---

### T006: Implement get_indexing_status() MCP tool [Implementation]
**Phase**: 3 - Core Implementation
**Estimated Time**: 30 minutes
**Dependencies**: T005

**Description**:
Create FastMCP tool that queries job status from database.

**Deliverables**:
- [ ] Add to `src/mcp/tools/background_indexing.py`
- [ ] @mcp.tool() decorator
- [ ] Queries indexing_jobs by ID
- [ ] Returns current status and counters

**Implementation**:
```python
# Add to src/mcp/tools/background_indexing.py

@mcp.tool()
async def get_indexing_status(
    job_id: str,
    project_id: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Get status of a background indexing job.

    Queries PostgreSQL for current job state. Read-only operation for polling.

    Args:
        job_id: UUID of the indexing job
        project_id: Optional project identifier (resolved via 4-tier chain)
        ctx: FastMCP Context for session-based project resolution

    Returns:
        {
            "job_id": "uuid",
            "status": "running",  # pending/running/completed/failed
            "repo_path": "/path/to/repo",
            "files_indexed": 5000,
            "chunks_created": 45000,
            "error_message": null,
            "created_at": "2025-10-17T10:30:00Z",
            "started_at": "2025-10-17T10:30:01Z",
            "completed_at": null
        }

    Raises:
        ValueError: If job_id is invalid or not found

    Example:
        >>> status = await get_indexing_status(job_id="550e8400-...")
        >>> if status["status"] == "completed":
        ...     print(f"Indexed {status['files_indexed']} files!")
    """
    # Resolve project_id
    resolved_id, _ = await resolve_project_id(
        explicit_id=project_id,
        ctx=ctx,
    )

    # Query job from database
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        raise ValueError(f"Invalid job_id format: {job_id}")

    async with get_session(project_id=resolved_id, ctx=ctx) as session:
        job = await session.get(IndexingJob, job_uuid)

        if job is None:
            raise ValueError(f"Job not found: {job_id}")

        # Convert to dict
        return {
            "job_id": str(job.id),
            "status": job.status,
            "repo_path": job.repo_path,
            "project_id": job.project_id,
            "files_indexed": job.files_indexed,
            "chunks_created": job.chunks_created,
            "error_message": job.error_message,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }
```

**Acceptance Criteria**:
- [ ] Returns all status fields
- [ ] Handles missing job_id gracefully
- [ ] Validates job_id is valid UUID
- [ ] Read-only operation (no side effects)
- [ ] Query completes in <50ms

**Constitutional Principles**:
- Principle IV: Performance (simple SELECT query)
- Principle XI: FastMCP Foundation

**Time Estimate**: 30 minutes

---

### T007: Add update_job() utility function [Implementation]
**Phase**: 3 - Core Implementation
**Estimated Time**: 15 minutes
**Dependencies**: T006

**Description**:
Create utility function for atomic job updates (used by worker).

**Deliverables**:
- [ ] Add to `src/services/background_worker.py`
- [ ] Single function for all job updates
- [ ] Uses get_session() and SQLAlchemy ORM

**Implementation**:
```python
# Add to src/services/background_worker.py

async def update_job(
    job_id: UUID,
    project_id: str,
    ctx: Context | None = None,
    **updates,
) -> None:
    """Update job fields atomically.

    Args:
        job_id: UUID of indexing_jobs row
        project_id: Project identifier
        ctx: Optional FastMCP Context
        **updates: Field names and values to update
            (e.g., status="running", files_indexed=100)

    Example:
        >>> await update_job(
        ...     job_id=job_id,
        ...     project_id="test",
        ...     status="completed",
        ...     files_indexed=1000,
        ...     completed_at=datetime.now()
        ... )
    """
    async with get_session(project_id=project_id, ctx=ctx) as session:
        job = await session.get(IndexingJob, job_id)
        if job is None:
            logger.warning(f"Job {job_id} not found for update")
            return

        # Apply updates
        for key, value in updates.items():
            if hasattr(job, key):
                setattr(job, key, value)
            else:
                logger.warning(f"Invalid field for job update: {key}")

        await session.commit()
```

**Acceptance Criteria**:
- [ ] Updates any valid job field
- [ ] Commits atomically
- [ ] Handles missing job gracefully
- [ ] Warns on invalid field names

**Time Estimate**: 15 minutes

---

### T008: Integration test for complete workflow [Testing]
**Phase**: 3 - Core Implementation
**Estimated Time**: 30 minutes
**Dependencies**: T007

**Description**:
End-to-end test of start → poll → complete workflow.

**Deliverables**:
- [ ] File: `tests/integration/test_background_indexing.py`
- [ ] Test with small repository (4 files)
- [ ] Poll until completion
- [ ] Verify final status and counters

**Test Code**:
```python
# tests/integration/test_background_indexing.py
import pytest
import asyncio
from pathlib import Path

@pytest.mark.integration
@pytest.mark.asyncio
async def test_background_indexing_complete_workflow(tmp_path):
    """Test complete background indexing workflow."""
    # Create test repository
    test_repo = tmp_path / "test-repo"
    test_repo.mkdir()
    (test_repo / "file1.py").write_text("def foo(): pass")
    (test_repo / "file2.py").write_text("def bar(): pass")
    (test_repo / "file3.py").write_text("def baz(): pass")
    (test_repo / "file4.py").write_text("def qux(): pass")

    # Start job
    from src.mcp.tools.background_indexing import start_indexing_background, get_indexing_status

    result = await start_indexing_background(
        repo_path=str(test_repo),
        project_id="test",
    )
    job_id = result["job_id"]
    assert result["status"] == "pending"

    # Poll until completion
    max_attempts = 15  # 30 seconds max
    for attempt in range(max_attempts):
        status = await get_indexing_status(job_id=job_id, project_id="test")

        if status["status"] in ["completed", "failed"]:
            break

        await asyncio.sleep(2)
    else:
        pytest.fail("Job did not complete within 30 seconds")

    # Verify completion
    assert status["status"] == "completed"
    assert status["files_indexed"] == 4
    assert status["chunks_created"] > 0
    assert status["completed_at"] is not None
    assert status["error_message"] is None
```

**Acceptance Criteria**:
- [ ] Test creates job successfully
- [ ] Test polls status every 2 seconds
- [ ] Test completes within 30 seconds
- [ ] Test verifies status transitions
- [ ] Test verifies final counters

**Time Estimate**: 30 minutes

---

## Phase 4: Production Hardening (1 hour)

### T009: Add error handling and logging [Implementation]
**Phase**: 4 - Production Hardening
**Estimated Time**: 20 minutes
**Dependencies**: T008

**Description**:
Enhance worker with comprehensive error handling and structured logging.

**Deliverables**:
- [ ] Worker catches all exception types
- [ ] Structured logging with context
- [ ] Error messages written to database
- [ ] No silent failures

**Updates**:
```python
# Update _background_indexing_worker with better error handling

try:
    # ... existing worker code ...
except asyncpg.PostgresError as e:
    # Database-specific errors
    logger.error(
        f"Database error in job {job_id}",
        extra={
            "context": {
                "job_id": str(job_id),
                "error": str(e),
                "error_type": "DatabaseError",
            }
        },
        exc_info=True,
    )
    await update_job(
        job_id=job_id,
        project_id=project_id,
        ctx=ctx,
        status="failed",
        error_message=f"Database error: {str(e)}",
        completed_at=datetime.now(),
    )
except FileNotFoundError as e:
    # Repository not found
    logger.error(
        f"Repository not found for job {job_id}",
        extra={"context": {"job_id": str(job_id), "repo_path": repo_path}},
    )
    await update_job(
        job_id=job_id,
        project_id=project_id,
        ctx=ctx,
        status="failed",
        error_message=f"Repository not found: {repo_path}",
        completed_at=datetime.now(),
    )
except Exception as e:
    # Catch-all for unexpected errors
    logger.error(
        f"Unexpected error in job {job_id}",
        extra={
            "context": {
                "job_id": str(job_id),
                "error": str(e),
                "error_type": type(e).__name__,
            }
        },
        exc_info=True,
    )
    await update_job(
        job_id=job_id,
        project_id=project_id,
        ctx=ctx,
        status="failed",
        error_message=str(e),
        completed_at=datetime.now(),
    )
```

**Acceptance Criteria**:
- [ ] All exception types caught
- [ ] Error messages written to database
- [ ] Logs include structured context
- [ ] No silent failures
- [ ] Worker always completes (no hangs)

**Time Estimate**: 20 minutes

---

### T010: Test state persistence across restart [Testing]
**Phase**: 4 - Production Hardening
**Estimated Time**: 20 minutes
**Dependencies**: T009

**Description**:
Verify job state persists after simulated server restart.

**Deliverables**:
- [ ] Test creates job
- [ ] Test simulates restart (close pools)
- [ ] Test queries job after restart
- [ ] Verify status preserved

**Test Code**:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_job_state_persistence():
    """Test job state persists across server restarts."""
    from src.database.session import get_session, close_db_connection, init_db_connection
    from src.models.indexing_job import IndexingJob
    from datetime import datetime

    # Create job
    async with get_session(project_id="test") as session:
        job = IndexingJob(
            repo_path="/tmp/test-repo",
            project_id="test",
            status="pending",
            created_at=datetime.now(),
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        job_id = job.id

    # Simulate restart (close pools)
    await close_db_connection()
    await init_db_connection()

    # Query job after restart
    from src.mcp.tools.background_indexing import get_indexing_status
    status = await get_indexing_status(job_id=str(job_id), project_id="test")

    # Verify state preserved
    assert status["job_id"] == str(job_id)
    assert status["status"] == "pending"
    assert status["repo_path"] == "/tmp/test-repo"
```

**Acceptance Criteria**:
- [ ] Job survives pool closure
- [ ] Status queryable after restart
- [ ] All fields preserved

**Time Estimate**: 20 minutes

---

### T011: Add configuration to .env [Configuration]
**Phase**: 4 - Production Hardening
**Estimated Time**: 10 minutes
**Dependencies**: None (parallel)

**Description**:
Add background indexing configuration to .env.example.

**Deliverables**:
- [ ] Add section to .env.example
- [ ] Document MAX_CONCURRENT_INDEXING_JOBS
- [ ] Document INDEXING_JOB_TIMEOUT_SECONDS

**Configuration**:
```bash
# Background Indexing Configuration
# Maximum number of concurrent background indexing jobs
MAX_CONCURRENT_INDEXING_JOBS=2

# Timeout per indexing job (seconds) - 1 hour default
INDEXING_JOB_TIMEOUT_SECONDS=3600
```

**Acceptance Criteria**:
- [ ] Configuration documented
- [ ] Defaults match architecture
- [ ] Comments explain purpose

**Time Estimate**: 10 minutes

---

### T012: Update documentation [Documentation]
**Phase**: 4 - Production Hardening
**Estimated Time**: 10 minutes
**Dependencies**: None (parallel)

**Description**:
Add background indexing usage to CLAUDE.md.

**Deliverables**:
- [ ] Add "Background Indexing" section
- [ ] Document start-and-poll pattern
- [ ] Document when to use background vs. foreground

**Documentation**:
```markdown
## Background Indexing

Large repositories (10,000+ files) require 5-10 minutes to index. Use background indexing for these repositories.

### Usage Pattern: Start and Poll

```python
# Start indexing
result = await start_indexing_background(
    repo_path="/path/to/large/repo",
    ctx=ctx
)
job_id = result["job_id"]

# Poll for completion
while True:
    status = await get_indexing_status(job_id=job_id, ctx=ctx)
    if status["status"] in ["completed", "failed"]:
        break
    await asyncio.sleep(2)

if status["status"] == "completed":
    print(f"✅ Indexed {status['files_indexed']} files!")
```

### When to Use

- **Foreground**: Repositories <5,000 files (completes in <60s)
- **Background**: Repositories 10,000+ files (requires 5-10 minutes)
```

**Acceptance Criteria**:
- [ ] Usage pattern documented
- [ ] Examples are correct
- [ ] Decision criteria clear

**Time Estimate**: 10 minutes

---

## Phase 5: Validation (30 minutes)

### T013: End-to-end test with large repository [Testing]
**Phase**: 5 - Validation
**Estimated Time**: 30 minutes
**Dependencies**: All previous phases

**Description**:
Test with realistic large repository (codebase-mcp itself).

**Deliverables**:
- [ ] Test with 10K+ file repository
- [ ] Verify no timeout
- [ ] Verify state tracking works
- [ ] Confirm production readiness

**Test Code**:
```python
@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
async def test_large_repository_indexing():
    """Test background indexing with large repository (codebase-mcp itself)."""
    import os

    # Use codebase-mcp repository (should have 1,000+ files)
    repo_path = os.path.abspath(os.path.join(__file__, "../../../../"))

    # Start job
    result = await start_indexing_background(
        repo_path=repo_path,
        project_id="test-large",
    )
    job_id = result["job_id"]

    # Poll until completion (allow up to 5 minutes)
    max_attempts = 150  # 5 minutes at 2s intervals
    for attempt in range(max_attempts):
        status = await get_indexing_status(job_id=job_id, project_id="test-large")

        # Log progress
        if attempt % 15 == 0:  # Every 30 seconds
            print(f"Status: {status['status']}, Files: {status['files_indexed']}")

        if status["status"] in ["completed", "failed"]:
            break

        await asyncio.sleep(2)
    else:
        pytest.fail("Job did not complete within 5 minutes")

    # Verify completion
    assert status["status"] == "completed", f"Job failed: {status.get('error_message')}"
    assert status["files_indexed"] > 100, "Should index at least 100 files"
    assert status["chunks_created"] > 1000, "Should create at least 1000 chunks"

    print(f"✅ Indexed {status['files_indexed']} files, "
          f"created {status['chunks_created']} chunks")
```

**Acceptance Criteria**:
- [ ] Test with 1,000+ file repository
- [ ] Completes successfully
- [ ] No timeout errors
- [ ] State tracking accurate
- [ ] Production-ready confirmed

**Time Estimate**: 30 minutes

---

## Summary

### What We Built

✅ **2 MCP Tools**:
- `start_indexing_background()` - Starts job, returns job_id
- `get_indexing_status()` - Queries job state

✅ **Background Worker**:
- Simple state machine (pending → running → completed/failed)
- Reuses existing `index_repository` service
- No modifications to indexer.py

✅ **Database Schema**:
- 10 essential columns (vs. 18 in full plan)
- 2 indexes for query performance
- State persists across restarts

✅ **Production Quality**:
- Path traversal prevention
- Error handling and logging
- State persistence
- Integration tests

### What We Deferred

⏸️ **US2: Job Management** (Phase 2)
- list_background_jobs() with filters
- Job cancellation
- ETA calculation

⏸️ **Advanced Features** (Phase 2)
- Granular progress tracking
- Progress callbacks in indexer
- Phase-specific messages
- force_reindex flag
- Resumption after failures

### Code Impact

**Files Created** (6 files):
1. `migrations/versions/008_add_indexing_jobs.py` (migration)
2. `src/models/indexing_job.py` (models)
3. `src/services/background_worker.py` (worker)
4. `src/mcp/tools/background_indexing.py` (MCP tools)
5. `tests/unit/test_indexing_job_models.py` (unit tests)
6. `tests/integration/test_background_indexing.py` (integration tests)

**Files Modified** (2 files):
1. `src/models/__init__.py` (exports)
2. `.env.example` (configuration)

**Total Lines**: ~1,200-1,500 (50% less than full plan)

### Timeline

**Total Time**: 6-7 hours (vs. 10-12 hours for full plan)

**Critical Path**: T001 → T002 → T003 → T004 → T005 → T006 → T013 (5.5 hours)

**Parallel Opportunities**: T003-test, T009-T012 can run parallel

### Next Steps

1. **Create feature branch**:
   ```bash
   git checkout -b 015-background-indexing-mvp
   ```

2. **Start with T001**: Create simplified migration

3. **Execute tasks sequentially**: Follow dependencies

4. **Test continuously**: Run tests after each task

5. **Deploy MVP**: Gather user feedback before Phase 2

---

## Key Code Patterns

### Pattern 1: Reuse Session Management
```python
# Throughout implementation
from src.database.session import get_session

async with get_session(project_id=project_id, ctx=ctx) as session:
    job = await session.get(IndexingJob, job_id)
    job.status = "completed"
    await session.commit()
```

### Pattern 2: Simple Worker (No Progress Callbacks)
```python
async def _background_indexing_worker(job_id, repo_path, project_id, ctx):
    try:
        # Update to running
        async with get_session(project_id=project_id, ctx=ctx) as session:
            job = await session.get(IndexingJob, job_id)
            job.status = "running"
            job.started_at = datetime.now()
            await session.commit()

        # Run existing indexer (NO MODIFICATIONS!)
        async with get_session(project_id=project_id, ctx=ctx) as session:
            result = await index_repository(
                repo_path=Path(repo_path),
                name=Path(repo_path).name,
                db=session,
                project_id=project_id,
            )

        # Update to completed
        async with get_session(project_id=project_id, ctx=ctx) as session:
            job = await session.get(IndexingJob, job_id)
            job.status = "completed"
            job.completed_at = datetime.now()
            job.files_indexed = result.files_indexed
            job.chunks_created = result.chunks_created
            await session.commit()

    except Exception as e:
        # Update to failed
        async with get_session(project_id=project_id, ctx=ctx) as session:
            job = await session.get(IndexingJob, job_id)
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = datetime.now()
            await session.commit()
```

### Pattern 3: MCP Tool Structure
```python
@mcp.tool()
async def start_indexing_background(
    repo_path: str,
    project_id: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Start repository indexing in background."""
    # Resolve project
    resolved_id, db_name = await resolve_project_id(project_id, ctx=ctx)

    # Validate path
    job_create = IndexingJobCreate(
        repo_path=repo_path,
        project_id=resolved_id,
    )

    # Create job record
    async with get_session(project_id=resolved_id, ctx=ctx) as session:
        job = IndexingJob(
            repo_path=job_create.repo_path,
            project_id=resolved_id,
            status="pending",
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        job_id = job.id

    # Start worker
    asyncio.create_task(_background_indexing_worker(job_id, repo_path, resolved_id, ctx))

    return {
        "job_id": str(job_id),
        "status": "pending",
        "message": "Indexing job started",
    }
```

---

**End of MVP Task Breakdown**

Ready to implement? Start with T001 (migration) and follow the critical path.

Questions? Refer to architecture doc: `docs/architecture/background-indexing.md`
