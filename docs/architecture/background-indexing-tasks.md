# Tasks: Background Indexing with PostgreSQL-Native Status Tracking

**Feature Branch**: `015-background-indexing`
**Source Document**: `docs/architecture/background-indexing.md`
**Constitutional Principles**: I (Simplicity), II (Local-First), IV (Performance), V (Production Quality), VIII (Type Safety), XI (FastMCP Foundation)

---

## Executive Summary

This task list implements PostgreSQL-native background indexing for large repositories (10K+ files, 5-10 minute indexing time) that exceed typical MCP request timeouts. The architecture uses PostgreSQL as the single source of truth for job state, eliminating in-memory complexity while ensuring production-ready reliability with state persistence across server restarts.

**Key Architectural Decision**: Job state lives in the database, not in memory. This trades slight query overhead for massive gains in simplicity, reliability, and debuggability.

**Implementation Approach**: TDD throughout, with test tasks preceding implementation. Each phase is independently testable and delivers incremental value.

---

## Implementation Timeline

**Total Estimated Time**: 10-12 hours

| Phase | Description | Time | Dependencies |
|-------|-------------|------|--------------|
| Phase 1 | Database Schema & Migration | 1.5 hours | None (Critical Path Start) |
| Phase 2 | Core Models & Validation | 1.5 hours | Phase 1 |
| Phase 3 | Database Utilities | 1.5 hours | Phase 2 |
| Phase 4 | Background Worker | 2 hours | Phase 3 |
| Phase 5 | MCP Tools | 1.5 hours | Phase 4 |
| Phase 6 | Indexer Enhancement | 1 hour | Phase 4-5 (Parallel) |
| Phase 7 | Integration Testing | 2 hours | Phase 5 |
| Phase 8 | Documentation & Polish | 1 hour | Phase 7 |

**Critical Path**: Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 7 → Phase 8 (9 hours)
**Parallel Opportunities**: Phase 6 can run parallel with Phase 4-5 (saves 1 hour)

---

## Phase Breakdown

### Phase 1: Database Schema & Migration (Critical Path)
**Purpose**: Create `indexing_jobs` table for job state persistence
**Estimated Time**: 1.5 hours
**Dependencies**: None (blocks all other phases)

### Phase 2: Core Models & Validation
**Purpose**: Pydantic models with security validation (path traversal prevention)
**Estimated Time**: 1.5 hours
**Dependencies**: Phase 1 complete

### Phase 3: Database Utilities
**Purpose**: Transaction-safe job state update functions
**Estimated Time**: 1.5 hours
**Dependencies**: Phase 2 complete

### Phase 4: Background Worker
**Purpose**: Asyncio task that executes indexing and updates database
**Estimated Time**: 2 hours
**Dependencies**: Phase 3 complete

### Phase 5: MCP Tools
**Purpose**: FastMCP tools for start/status/cancel operations
**Estimated Time**: 1.5 hours
**Dependencies**: Phase 4 complete

### Phase 6: Indexer Enhancement (Parallel with Phase 4-5)
**Purpose**: Add progress callbacks to existing indexer service
**Estimated Time**: 1 hour
**Dependencies**: Phase 4 started (can run parallel)

### Phase 7: Integration Testing
**Purpose**: End-to-end workflow validation, cancellation, persistence
**Estimated Time**: 2 hours
**Dependencies**: Phase 5 complete

### Phase 8: Documentation & Polish
**Purpose**: User documentation, .env examples, CLAUDE.md updates
**Estimated Time**: 1 hour
**Dependencies**: Phase 7 complete

---

## Detailed Tasks

### Phase 1: Database Schema & Migration

**Checkpoint**: Migration created, applied, and validated ✅

---

#### T001: Create Alembic migration for indexing_jobs table [Implementation]
**Dependencies**: None (Critical Path Start)
**Estimated Time**: 1 hour
**Parallelization**: Cannot parallelize (critical path)

**Description**:
Create Alembic migration to add the `indexing_jobs` table to project databases with proper schema, indexes, and constraints matching the architecture specification.

**Deliverables**:
- [ ] Create migration file: `migrations/versions/008_add_indexing_jobs.py`
- [ ] Define table schema matching architecture doc lines 73-113
- [ ] Add all 4 performance indexes with WHERE clauses
- [ ] Add CHECK constraints for status enum and progress range
- [ ] Implement upgrade() function
- [ ] Implement downgrade() function
- [ ] Add table and column comments for documentation

**Acceptance Criteria**:
- [ ] Migration file passes `alembic check`
- [ ] upgrade() creates table with correct 18 columns
- [ ] downgrade() cleanly removes table and indexes
- [ ] All indexes created with partial WHERE conditions
- [ ] CHECK constraints enforce valid status values and 0-100 progress range
- [ ] Comments explain purpose of key columns (repo_path, status, metadata)

**Constitutional Principles**:
- Principle V: Production Quality (proper indexes for <10ms queries, constraints)
- Principle VIII: Type Safety (explicit PostgreSQL column types)
- Principle II: Local-First (standard PostgreSQL schema, no cloud dependencies)

**Technical Notes**:
- Use PostgreSQL-specific types: UUID (gen_random_uuid()), TIMESTAMPTZ, JSONB
- Use partial indexes for performance: `WHERE status IN ('pending', 'running')`
- Reference architecture doc lines 73-129 for exact schema
- Table will be created in ALL project databases (cb_proj_* pattern)

**SQL Schema Reference**:
```sql
CREATE TABLE indexing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID,
    repo_path TEXT NOT NULL,
    repo_name TEXT NOT NULL,
    project_id VARCHAR(255) NOT NULL,
    force_reindex BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
    progress_percentage INTEGER NOT NULL DEFAULT 0 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    progress_message TEXT,
    files_scanned INTEGER NOT NULL DEFAULT 0,
    files_indexed INTEGER NOT NULL DEFAULT 0,
    chunks_created INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    error_type VARCHAR(255),
    error_traceback TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    cancelled_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb,
    worker_task_id TEXT,
    connection_id TEXT
);
```

**Risks**:
- Migration must apply to both registry and project databases
- Need to handle existing projects (apply migration to all cb_proj_* databases)
- Downgrade must not leave orphaned indexes

---

#### T002: Apply migration to test project database [Migration]
**Dependencies**: T001
**Estimated Time**: 15 minutes
**Parallelization**: Cannot parallelize (depends on T001)

**Description**:
Apply the indexing_jobs migration to the test project database and validate schema correctness.

**Deliverables**:
- [ ] Run `alembic upgrade head` on test database
- [ ] Verify table exists with `\d indexing_jobs` in psql
- [ ] Verify all 4 indexes created correctly
- [ ] Verify CHECK constraints active
- [ ] Document migration validation steps

**Acceptance Criteria**:
- [ ] `SELECT * FROM indexing_jobs LIMIT 1;` succeeds (returns no rows)
- [ ] All indexes appear in `\di` output
- [ ] CHECK constraint violation fails: `INSERT INTO indexing_jobs (status) VALUES ('invalid');`
- [ ] Progress range constraint works: `INSERT INTO indexing_jobs (progress_percentage) VALUES (101);` fails
- [ ] Table comments visible: `\d+ indexing_jobs`

**Constitutional Principles**:
- Principle V: Production Quality (validation before proceeding)
- Principle VI: Specification-First (migration validates against spec)

**Technical Notes**:
- Use test database: `cb_proj_test_<hash>`
- Test both upgrade and downgrade paths
- Validate foreign key behavior (repository_id can be NULL initially)

**Risks**:
- Test database may not exist yet (may need setup script)
- Migration might fail on constraint naming conflicts

---

#### T003: Validate migration rollback (downgrade) [Testing]
**Dependencies**: T002
**Estimated Time**: 15 minutes
**Parallelization**: Cannot parallelize (depends on T002)

**Description**:
Test the downgrade path to ensure clean rollback without leaving artifacts.

**Deliverables**:
- [ ] Run `alembic downgrade -1` on test database
- [ ] Verify table removed: `\d indexing_jobs` fails
- [ ] Verify all indexes removed
- [ ] Re-upgrade to validate idempotency
- [ ] Document rollback validation

**Acceptance Criteria**:
- [ ] After downgrade, `SELECT * FROM indexing_jobs` fails with "relation does not exist"
- [ ] After downgrade, no `idx_indexing_jobs_*` indexes exist
- [ ] Re-running upgrade succeeds without errors
- [ ] Downgrade → upgrade → downgrade cycle works cleanly

**Constitutional Principles**:
- Principle V: Production Quality (safe rollback capability)
- Principle VII: Test-Driven Development (validate failure paths)

**Technical Notes**:
- Test idempotency: upgrade twice, downgrade twice
- Check for orphaned constraints or indexes
- Validate with `\d` and `\di` psql commands

**Risks**:
- Downgrade might fail if indexes not dropped in correct order
- Partial downgrade could leave database in inconsistent state

---

### Phase 2: Core Models & Validation

**Checkpoint**: Pydantic models created with security validation ✅

---

#### T004-test: Write unit tests for IndexingJobCreate validation [Testing]
**Dependencies**: T001 (schema defined)
**Estimated Time**: 30 minutes
**Parallelization**: [P] Can run parallel with other test tasks

**Description**:
Write TDD tests for the IndexingJobCreate Pydantic model focusing on path traversal prevention and validation rules.

**Deliverables**:
- [ ] Create test file: `tests/unit/test_indexing_job_models.py`
- [ ] Test valid absolute path acceptance
- [ ] Test relative path rejection
- [ ] Test path traversal rejection (../ sequences)
- [ ] Test symlink path handling
- [ ] Test field validation (repo_name, project_id required)
- [ ] Test default values (force_reindex=False)

**Acceptance Criteria**:
- [ ] All tests fail initially (models don't exist yet)
- [ ] Test valid path: `/Users/alice/projects/myapp` → accepted
- [ ] Test relative path: `./relative/path` → ValueError
- [ ] Test traversal: `/var/data/../../etc/passwd` → ValueError
- [ ] Test traversal: `/tmp/../../../etc/passwd` → ValueError
- [ ] Test empty repo_path: ValueError with clear message
- [ ] Test empty project_id: ValueError with clear message

**Constitutional Principles**:
- Principle VII: Test-Driven Development (tests before implementation)
- Principle V: Production Quality (comprehensive security validation)
- Principle VIII: Type Safety (Pydantic validation testing)

**Technical Notes**:
- Use pytest with pytest-asyncio
- Test both valid and invalid cases
- Validate error messages are actionable
- Reference architecture doc lines 174-192 for validation logic

**Test Template**:
```python
def test_valid_absolute_path():
    """Test absolute paths are accepted."""
    job_input = IndexingJobCreate(
        repo_path="/tmp/test-repo",
        repo_name="test-repo",
        project_id="test-project",
    )
    assert job_input.repo_path == "/tmp/test-repo"

def test_relative_path_rejection():
    """Test relative paths are rejected."""
    with pytest.raises(ValueError, match="must be absolute"):
        IndexingJobCreate(
            repo_path="./relative/path",
            repo_name="test",
            project_id="test",
        )

def test_path_traversal_rejection():
    """Test path traversal attacks are rejected."""
    with pytest.raises(ValueError, match="Path traversal detected"):
        IndexingJobCreate(
            repo_path="/var/data/../../etc/passwd",
            repo_name="test",
            project_id="test",
        )
```

**Risks**:
- Path resolution behavior varies by OS (test on Linux, macOS, Windows)
- Symlinks might bypass validation if not handled

---

#### T004: Create IndexingJob Pydantic models [Implementation]
**Dependencies**: T004-test (tests written)
**Estimated Time**: 45 minutes
**Parallelization**: [P] Can run parallel with T005

**Description**:
Implement Pydantic models for indexing job data: IndexingJobStatus enum, IndexingJobCreate (input), and IndexingJobProgress (output).

**Deliverables**:
- [ ] Create file: `src/models/indexing_job.py`
- [ ] Define IndexingJobStatus enum (5 states)
- [ ] Implement IndexingJobCreate with path validation
- [ ] Implement IndexingJobProgress (immutable output)
- [ ] Add comprehensive docstrings
- [ ] Export models in `src/models/__init__.py`

**Acceptance Criteria**:
- [ ] All tests from T004-test pass
- [ ] mypy --strict passes with no errors
- [ ] IndexingJobStatus has 5 values: pending, running, completed, failed, cancelled
- [ ] IndexingJobCreate validates absolute paths only
- [ ] IndexingJobCreate detects path traversal (../ sequences)
- [ ] IndexingJobProgress is frozen (immutable)
- [ ] All fields have type hints and Field constraints

**Constitutional Principles**:
- Principle VIII: Type Safety (Pydantic models, mypy --strict)
- Principle V: Production Quality (security validation, clear errors)
- Principle VII: TDD (tests pass after implementation)

**Technical Notes**:
- Reference architecture doc lines 136-193
- Use pydantic.Field for constraints (min_length, ge, le)
- Use pydantic.validator for custom path validation
- IndexingJobProgress.Config: frozen=True for immutability
- Path validation: os.path.isabs() + Path.resolve() comparison

**Model Structure**:
```python
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, validator
from uuid import UUID

class IndexingJobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class IndexingJobCreate(BaseModel):
    repo_path: str = Field(min_length=1)
    repo_name: str = Field(min_length=1)
    project_id: str = Field(min_length=1)
    force_reindex: bool = False

    @validator('repo_path')
    def validate_repo_path(cls, v: str) -> str:
        # Absolute path check
        # Path traversal detection
        # Return validated path
        pass

class IndexingJobProgress(BaseModel):
    job_id: UUID
    status: IndexingJobStatus
    progress_percentage: int = Field(ge=0, le=100)
    progress_message: str
    files_scanned: int = Field(ge=0)
    files_indexed: int = Field(ge=0)
    chunks_created: int = Field(ge=0)
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    class Config:
        frozen = True
```

**Risks**:
- Path validation logic might have edge cases (symlinks, Windows paths)
- Enum string values must match database CHECK constraint exactly

---

#### T005-test: Write unit tests for path validation logic [Testing]
**Dependencies**: T001
**Estimated Time**: 30 minutes
**Parallelization**: [P] Can run parallel with T004-test

**Description**:
Write comprehensive tests for path traversal prevention logic covering edge cases.

**Deliverables**:
- [ ] Add tests to `tests/unit/test_indexing_job_models.py`
- [ ] Test multiple traversal patterns: `../`, `/../`, `/../../`
- [ ] Test encoded traversal: `%2e%2e%2f`
- [ ] Test symlink resolution
- [ ] Test path normalization edge cases
- [ ] Test Windows path handling (if applicable)

**Acceptance Criteria**:
- [ ] All traversal patterns rejected
- [ ] Encoded traversal patterns rejected
- [ ] Symlinks validated against resolved target
- [ ] Clear error messages for each rejection
- [ ] Tests cover both Unix and Windows path formats

**Constitutional Principles**:
- Principle VII: TDD (comprehensive test coverage)
- Principle V: Production Quality (security edge cases)

**Technical Notes**:
- Test on multiple platforms if possible
- Use pathlib.Path for cross-platform compatibility
- Validate error messages are actionable

**Edge Case Tests**:
```python
@pytest.mark.parametrize("malicious_path", [
    "/var/data/../../etc/passwd",
    "/tmp/../../../etc/passwd",
    "/home/user/../../../etc/shadow",
    "./../../sensitive",
    "relative/../../../etc/hosts",
])
def test_path_traversal_patterns(malicious_path):
    """Test various path traversal patterns are rejected."""
    with pytest.raises(ValueError, match="Path traversal detected"):
        IndexingJobCreate(
            repo_path=malicious_path,
            repo_name="test",
            project_id="test",
        )
```

**Risks**:
- Validation might not cover all attack vectors
- Cross-platform path handling differences

---

### Phase 3: Database Utilities

**Checkpoint**: Transaction-safe database update functions implemented ✅

---

#### T006-test: Write unit tests for database update utilities [Testing]
**Dependencies**: T002 (schema exists)
**Estimated Time**: 45 minutes
**Parallelization**: Cannot parallelize (requires database)

**Description**:
Write tests for the three database utility functions: _update_job_status, _update_job_progress, _check_cancellation.

**Deliverables**:
- [ ] Create test file: `tests/unit/test_indexing_db_utils.py`
- [ ] Test _update_job_status with all fields
- [ ] Test _update_job_progress with counters
- [ ] Test _check_cancellation for cancelled jobs
- [ ] Test transaction commit behavior
- [ ] Test error handling and rollback

**Acceptance Criteria**:
- [ ] Tests initially fail (functions don't exist)
- [ ] Test status update writes to database
- [ ] Test progress update increments counters
- [ ] Test cancellation detection returns True/False correctly
- [ ] Test transaction isolation (concurrent updates)
- [ ] Test error handling on invalid job_id

**Constitutional Principles**:
- Principle VII: TDD (tests before implementation)
- Principle V: Production Quality (transaction safety)
- Principle IV: Performance (efficient queries)

**Technical Notes**:
- Use pytest fixtures for test database setup
- Test with real PostgreSQL connection (not mocks)
- Validate transaction commits are visible to other connections
- Reference architecture doc lines 500-664

**Test Structure**:
```python
@pytest.mark.asyncio
async def test_update_job_status(test_db, test_job_id):
    """Test updating job status persists to database."""
    await _update_job_status(
        job_id=test_job_id,
        project_id="test",
        status=IndexingJobStatus.RUNNING,
        progress_percentage=10,
        progress_message="Starting...",
    )

    # Verify update visible in database
    async with get_session(project_id="test") as db:
        result = await db.execute(
            text("SELECT status FROM indexing_jobs WHERE id = :job_id"),
            {"job_id": test_job_id}
        )
        row = result.fetchone()
        assert row[0] == "running"
```

**Risks**:
- Race conditions if not using proper transactions
- Connection pool exhaustion during tests

---

#### T006: Implement _update_job_status utility [Implementation]
**Dependencies**: T006-test, T004 (models exist)
**Estimated Time**: 45 minutes
**Parallelization**: Cannot parallelize (depends on T006-test)

**Description**:
Implement the _update_job_status function that transactionally updates job state in PostgreSQL.

**Deliverables**:
- [ ] Create file: `src/mcp/tools/background_indexing.py`
- [ ] Implement _update_job_status function
- [ ] Dynamic SQL generation for optional fields
- [ ] Transaction commit after update
- [ ] Comprehensive error handling
- [ ] Logging for all updates

**Acceptance Criteria**:
- [ ] All tests from T006-test pass
- [ ] Function updates all provided fields atomically
- [ ] Transaction commits successfully
- [ ] Optional fields (started_at, error_message) handled correctly
- [ ] Errors logged with context
- [ ] mypy --strict passes

**Constitutional Principles**:
- Principle V: Production Quality (transaction safety, error handling)
- Principle VIII: Type Safety (full type hints)
- Principle IV: Performance (single UPDATE query)

**Technical Notes**:
- Use dynamic SQL: build UPDATE SET clause from non-None parameters
- Reference architecture doc lines 503-608
- Use get_session(project_id=...) for connection
- Commit transaction explicitly: await db.commit()

**Function Signature**:
```python
async def _update_job_status(
    job_id: UUID,
    project_id: str,
    status: IndexingJobStatus,
    progress_percentage: int,
    progress_message: str,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    cancelled_at: datetime | None = None,
    error_message: str | None = None,
    error_type: str | None = None,
    error_traceback: str | None = None,
    files_scanned: int | None = None,
    files_indexed: int | None = None,
    chunks_created: int | None = None,
    repository_id: UUID | None = None,
) -> None:
    """Update job status in PostgreSQL (transactional)."""
    async with get_session(project_id=project_id) as db:
        # Build dynamic UPDATE query
        # Execute and commit
        pass
```

**Risks**:
- SQL injection if not using parameterized queries (use text() with bindings)
- Transaction might deadlock under high concurrency

---

#### T007: Implement _update_job_progress and _check_cancellation [Implementation]
**Dependencies**: T006 (uses _update_job_status)
**Estimated Time**: 30 minutes
**Parallelization**: Cannot parallelize (depends on T006)

**Description**:
Implement the lightweight progress update and cancellation check utilities.

**Deliverables**:
- [ ] Add _update_job_progress to background_indexing.py
- [ ] Add _check_cancellation to background_indexing.py
- [ ] Progress function delegates to _update_job_status
- [ ] Cancellation function queries status column only
- [ ] Add logging for cancellation detection

**Acceptance Criteria**:
- [ ] _update_job_progress updates percentage and message
- [ ] _update_job_progress accepts optional counters (files_scanned, etc.)
- [ ] _check_cancellation returns True if status='cancelled'
- [ ] _check_cancellation returns False for all other statuses
- [ ] _check_cancellation handles missing job_id gracefully
- [ ] All functions pass mypy --strict

**Constitutional Principles**:
- Principle IV: Performance (lightweight queries)
- Principle VIII: Type Safety (complete type hints)
- Principle V: Production Quality (error handling)

**Technical Notes**:
- Reference architecture doc lines 610-664
- _update_job_progress is a convenience wrapper
- _check_cancellation does simple SELECT query
- No transaction needed for read-only cancellation check

**Function Signatures**:
```python
async def _update_job_progress(
    job_id: UUID,
    project_id: str,
    percentage: int,
    message: str,
    **kwargs,  # files_scanned, files_indexed, chunks_created
) -> None:
    """Update job progress (lightweight version)."""
    await _update_job_status(
        job_id=job_id,
        project_id=project_id,
        status=IndexingJobStatus.RUNNING,
        progress_percentage=percentage,
        progress_message=message,
        **kwargs
    )

async def _check_cancellation(job_id: UUID, project_id: str) -> bool:
    """Check if job has been cancelled via database query."""
    async with get_session(project_id=project_id) as db:
        result = await db.execute(
            text("SELECT status FROM indexing_jobs WHERE id = :job_id"),
            {"job_id": job_id}
        )
        row = result.fetchone()
        if row is None:
            return False
        return row[0] == IndexingJobStatus.CANCELLED.value
```

**Risks**:
- Frequent cancellation checks might impact performance (acceptable tradeoff)
- Missing job_id during cancellation check needs graceful handling

---

### Phase 4: Background Worker

**Checkpoint**: Asyncio background worker executes indexing and updates database ✅

---

#### T008-test: Write integration test for background worker [Testing]
**Dependencies**: T007 (utilities exist)
**Estimated Time**: 1 hour
**Parallelization**: Cannot parallelize (requires database)

**Description**:
Write integration test for the complete background worker lifecycle: start → run → complete/fail.

**Deliverables**:
- [ ] Create test file: `tests/integration/test_background_worker.py`
- [ ] Test successful indexing workflow
- [ ] Test worker failure handling
- [ ] Test cancellation during execution
- [ ] Test progress updates written to database
- [ ] Test cleanup on completion

**Acceptance Criteria**:
- [ ] Test initially fails (worker doesn't exist)
- [ ] Test creates job, starts worker, waits for completion
- [ ] Test verifies status transitions: pending → running → completed
- [ ] Test verifies progress updates increment
- [ ] Test verifies final counters (files_indexed, chunks_created)
- [ ] Test verifies error_message populated on failure
- [ ] Test verifies cleanup (no hanging connections)

**Constitutional Principles**:
- Principle VII: TDD (integration test before worker)
- Principle V: Production Quality (lifecycle testing)
- Principle IV: Performance (validate 60s target)

**Technical Notes**:
- Use small test repository (4-5 files) for fast execution
- Test with asyncio.wait_for() for timeout safety
- Verify worker task doesn't leak resources
- Reference architecture doc lines 330-496

**Test Structure**:
```python
@pytest.mark.asyncio
async def test_background_worker_success(test_repo_path, test_db):
    """Test successful background indexing workflow."""
    # Create job record
    async with get_session(project_id="test") as db:
        result = await db.execute(
            text("INSERT INTO indexing_jobs (...) VALUES (...) RETURNING id")
        )
        job_id = result.fetchone()[0]
        await db.commit()

    # Start worker
    worker_task = asyncio.create_task(
        _background_indexing_worker(
            job_id=job_id,
            repo_path=str(test_repo_path),
            repo_name="test-repo",
            project_id="test",
            force_reindex=False,
        )
    )

    # Wait for completion (with timeout)
    await asyncio.wait_for(worker_task, timeout=30)

    # Verify final status
    async with get_session(project_id="test") as db:
        result = await db.execute(
            text("SELECT status, files_indexed FROM indexing_jobs WHERE id = :job_id"),
            {"job_id": job_id}
        )
        row = result.fetchone()
        assert row[0] == "completed"
        assert row[1] > 0
```

**Risks**:
- Test might timeout if repository too large
- Worker might not clean up properly on failure

---

#### T008: Implement _background_indexing_worker function [Implementation]
**Dependencies**: T008-test, T007 (utilities exist)
**Estimated Time**: 1 hour
**Parallelization**: Cannot parallelize (critical path)

**Description**:
Implement the background worker function that executes the indexing workflow and updates PostgreSQL with progress.

**Deliverables**:
- [ ] Add _background_indexing_worker to background_indexing.py
- [ ] Implement status transition: pending → running
- [ ] Define progress callback that updates database
- [ ] Call index_repository with progress callback
- [ ] Handle successful completion
- [ ] Handle asyncio.CancelledError (user cancellation)
- [ ] Handle generic exceptions (failures)
- [ ] Ensure cleanup in finally block

**Acceptance Criteria**:
- [ ] All tests from T008-test pass
- [ ] Worker transitions status: pending → running → completed/failed/cancelled
- [ ] Progress callback invoked at milestones
- [ ] Progress callback detects cancellation requests
- [ ] Errors captured with full traceback
- [ ] Worker completes even if index_repository fails
- [ ] No resource leaks (connections closed)

**Constitutional Principles**:
- Principle V: Production Quality (error handling, cleanup)
- Principle VIII: Type Safety (mypy --strict)
- Principle IV: Performance (non-blocking execution)

**Technical Notes**:
- Reference architecture doc lines 330-496
- Use try/except/finally for cleanup
- Progress callback: async def progress_callback(message: str, percentage: int, **kwargs)
- Catch asyncio.CancelledError separately from Exception
- Log all state transitions

**Worker Structure**:
```python
async def _background_indexing_worker(
    job_id: UUID,
    repo_path: str,
    repo_name: str,
    project_id: str,
    force_reindex: bool,
) -> None:
    """Background worker that executes indexing and updates PostgreSQL."""
    try:
        # Update to running
        await _update_job_status(
            job_id=job_id,
            project_id=project_id,
            status=IndexingJobStatus.RUNNING,
            progress_percentage=0,
            progress_message="Starting indexing...",
            started_at=datetime.now(timezone.utc),
        )

        # Define progress callback
        async def progress_callback(message: str, percentage: int, **kwargs) -> None:
            # Check cancellation
            if await _check_cancellation(job_id, project_id):
                raise asyncio.CancelledError("Job cancelled by user")
            # Update progress
            await _update_job_progress(job_id, project_id, percentage, message, **kwargs)

        # Run indexing
        async with get_session(project_id=project_id) as db:
            result = await index_repository(
                repo_path=Path(repo_path),
                name=repo_name,
                db=db,
                project_id=project_id,
                force_reindex=force_reindex,
                progress_callback=progress_callback,
            )

        # Update to completed
        await _update_job_status(
            job_id=job_id,
            project_id=project_id,
            status=IndexingJobStatus.COMPLETED,
            progress_percentage=100,
            progress_message=f"Completed: {result.files_indexed} files",
            completed_at=datetime.now(timezone.utc),
            files_indexed=result.files_indexed,
            chunks_created=result.chunks_created,
            repository_id=result.repository_id,
        )

    except asyncio.CancelledError:
        # User cancellation
        await _update_job_status(
            job_id=job_id,
            project_id=project_id,
            status=IndexingJobStatus.CANCELLED,
            progress_percentage=0,
            progress_message="Job cancelled by user",
            cancelled_at=datetime.now(timezone.utc),
        )

    except Exception as e:
        # Failure
        import traceback
        await _update_job_status(
            job_id=job_id,
            project_id=project_id,
            status=IndexingJobStatus.FAILED,
            progress_percentage=0,
            progress_message=f"Error: {str(e)}",
            completed_at=datetime.now(timezone.utc),
            error_message=str(e),
            error_type=type(e).__name__,
            error_traceback=traceback.format_exc(),
        )

    finally:
        # Cleanup
        logger.debug(f"Background worker cleanup for job {job_id}")
```

**Risks**:
- Worker might hang if index_repository blocks
- Cancellation detection might not be frequent enough (acceptable: checked per progress update)

---

### Phase 5: MCP Tools

**Checkpoint**: FastMCP tools for start/status/cancel operations implemented ✅

---

#### T009-test: Write contract tests for MCP tools [Testing]
**Dependencies**: T002 (schema exists)
**Estimated Time**: 45 minutes
**Parallelization**: [P] Can run parallel with other tests

**Description**:
Write MCP contract tests for the three background indexing tools: start_indexing_background, get_indexing_status, cancel_indexing_background.

**Deliverables**:
- [ ] Create test file: `tests/contract/test_background_indexing_tools.py`
- [ ] Test start_indexing_background returns job_id
- [ ] Test get_indexing_status returns progress
- [ ] Test cancel_indexing_background sets cancelled status
- [ ] Validate MCP response schemas
- [ ] Test error cases (invalid job_id, missing repo_path)

**Acceptance Criteria**:
- [ ] Tests initially fail (tools don't exist)
- [ ] Test validates start returns dict with job_id key
- [ ] Test validates status returns progress_percentage (0-100)
- [ ] Test validates cancel returns success confirmation
- [ ] Test validates error responses for invalid inputs
- [ ] Test validates MCP schema compliance (Pydantic models)

**Constitutional Principles**:
- Principle VII: TDD (contract tests before tools)
- Principle III: Protocol Compliance (MCP response validation)
- Principle VIII: Type Safety (Pydantic response models)

**Technical Notes**:
- Use @pytest.mark.contract for test categorization
- Validate response schemas match architecture doc
- Test both success and error paths
- Reference architecture doc lines 197-838

**Test Structure**:
```python
@pytest.mark.contract
@pytest.mark.asyncio
async def test_start_indexing_background_returns_job_id(test_repo_path):
    """Test start_indexing_background returns job_id immediately."""
    result = await start_indexing_background(
        repo_path=str(test_repo_path),
        project_id="test",
    )

    assert "job_id" in result
    assert "status" in result
    assert result["status"] == "pending"
    assert "project_id" in result
    assert "database_name" in result

@pytest.mark.contract
@pytest.mark.asyncio
async def test_get_indexing_status_returns_progress():
    """Test get_indexing_status returns progress information."""
    # Create test job
    job_id = "test-job-id"

    result = await get_indexing_status(job_id=job_id, project_id="test")

    assert "job_id" in result
    assert "status" in result
    assert "progress_percentage" in result
    assert 0 <= result["progress_percentage"] <= 100
```

**Risks**:
- Contract tests might be flaky if database state not cleaned up
- MCP schema changes might break tests

---

#### T009: Implement start_indexing_background MCP tool [Implementation]
**Dependencies**: T009-test, T008 (worker exists)
**Estimated Time**: 45 minutes
**Parallelization**: Cannot parallelize (depends on T009-test)

**Description**:
Implement the start_indexing_background FastMCP tool that creates a job record and launches the background worker.

**Deliverables**:
- [ ] Add @mcp.tool() decorator to start_indexing_background
- [ ] Resolve project_id via 4-tier chain
- [ ] Validate input with IndexingJobCreate
- [ ] Insert job record with status=pending
- [ ] Launch worker via asyncio.create_task()
- [ ] Return job_id and metadata immediately
- [ ] Add comprehensive docstring

**Acceptance Criteria**:
- [ ] Tool registered in FastMCP server
- [ ] Path validation rejects relative paths
- [ ] Path validation rejects traversal attempts
- [ ] Job record created in database with status=pending
- [ ] Worker task started asynchronously
- [ ] Function returns immediately (non-blocking)
- [ ] Response includes job_id, status, project_id, database_name

**Constitutional Principles**:
- Principle XI: FastMCP Foundation (@mcp.tool() decorator)
- Principle V: Production Quality (input validation, error handling)
- Principle VIII: Type Safety (Pydantic models)
- Principle IV: Performance (non-blocking)

**Technical Notes**:
- Reference architecture doc lines 197-326
- Use IndexingJobCreate for validation (catches path traversal)
- Use resolve_project_id for 4-tier resolution
- asyncio.create_task() returns immediately, task runs in background
- Log job creation with context

**Function Structure**:
```python
@mcp.tool()
async def start_indexing_background(
    repo_path: str,
    project_id: str | None = None,
    force_reindex: bool = False,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Start repository indexing in the background (non-blocking).

    Returns immediately with job_id. Use get_indexing_status(job_id) to poll progress.

    Args:
        repo_path: Absolute path to repository (validated)
        project_id: Optional project identifier (resolved via 4-tier chain)
        force_reindex: If True, re-index even if already indexed
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
    """
    # Resolve project_id
    resolved_id, database_name = await resolve_project_id(
        explicit_id=project_id,
        ctx=ctx,
    )

    # Validate input (includes path traversal check)
    job_input = IndexingJobCreate(
        repo_path=repo_path,
        repo_name=Path(repo_path).name,
        project_id=resolved_id,
        force_reindex=force_reindex,
    )

    # Create job record
    async with get_session(project_id=resolved_id, ctx=ctx) as db:
        result = await db.execute(
            text("""
                INSERT INTO indexing_jobs
                    (repo_path, repo_name, project_id, force_reindex, status, progress_message)
                VALUES
                    (:repo_path, :repo_name, :project_id, :force_reindex, 'pending', 'Job queued')
                RETURNING id
            """),
            {
                "repo_path": job_input.repo_path,
                "repo_name": job_input.repo_name,
                "project_id": job_input.project_id,
                "force_reindex": job_input.force_reindex,
            }
        )
        row = result.fetchone()
        job_id = row[0]
        await db.commit()

    # Start background worker
    asyncio.create_task(
        _background_indexing_worker(
            job_id=job_id,
            repo_path=job_input.repo_path,
            repo_name=job_input.repo_name,
            project_id=resolved_id,
            force_reindex=job_input.force_reindex,
        )
    )

    logger.info(f"Indexing job created: {job_id}")

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

**Risks**:
- Worker task might fail silently if not properly monitored
- Path validation might have edge cases

---

#### T010: Implement get_indexing_status and cancel_indexing_background tools [Implementation]
**Dependencies**: T009
**Estimated Time**: 45 minutes
**Parallelization**: Cannot parallelize (depends on T009)

**Description**:
Implement the status query and cancellation request MCP tools.

**Deliverables**:
- [ ] Add @mcp.tool() to get_indexing_status
- [ ] Query indexing_jobs table by job_id
- [ ] Return comprehensive progress information
- [ ] Add @mcp.tool() to cancel_indexing_background
- [ ] Update job status to cancelled
- [ ] Handle invalid job_id errors
- [ ] Add docstrings for both tools

**Acceptance Criteria**:
- [ ] get_indexing_status returns all progress fields
- [ ] get_indexing_status handles missing job_id gracefully
- [ ] cancel_indexing_background updates status to cancelled
- [ ] cancel_indexing_background rejects already-completed jobs
- [ ] Both tools resolve project_id correctly
- [ ] Both tools pass mypy --strict

**Constitutional Principles**:
- Principle XI: FastMCP Foundation (@mcp.tool() decorators)
- Principle VIII: Type Safety (complete type hints)
- Principle IV: Performance (simple SELECT queries)

**Technical Notes**:
- Reference architecture doc lines 667-838
- get_indexing_status is read-only (no transaction)
- cancel_indexing_background does UPDATE WHERE status IN ('pending', 'running')
- Worker detects cancellation on next progress update

**Function Signatures**:
```python
@mcp.tool()
async def get_indexing_status(
    job_id: str,
    project_id: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Get status of a background indexing job.

    Returns:
        {
            "job_id": "uuid",
            "status": "running",
            "progress_percentage": 45,
            "progress_message": "Generating embeddings...",
            "files_scanned": 10585,
            "files_indexed": 5000,
            "chunks_created": 45000,
            ...
        }
    """
    resolved_id, _ = await resolve_project_id(explicit_id=project_id, ctx=ctx)

    async with get_session(project_id=resolved_id, ctx=ctx) as db:
        result = await db.execute(
            text("SELECT * FROM indexing_jobs WHERE id = :job_id"),
            {"job_id": job_id}
        )
        row = result.fetchone()

        if row is None:
            raise ValueError(f"Job not found: {job_id}")

        # Convert to dict and return
        return {...}

@mcp.tool()
async def cancel_indexing_background(
    job_id: str,
    project_id: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Cancel a running indexing job.

    Returns:
        {
            "job_id": "uuid",
            "status": "cancelled",
            "message": "Cancellation requested (worker will abort)"
        }
    """
    resolved_id, _ = await resolve_project_id(explicit_id=project_id, ctx=ctx)

    async with get_session(project_id=resolved_id, ctx=ctx) as db:
        result = await db.execute(
            text("""
                UPDATE indexing_jobs
                SET status = 'cancelled', cancelled_at = NOW()
                WHERE id = :job_id AND status IN ('pending', 'running')
                RETURNING id
            """),
            {"job_id": job_id}
        )
        row = result.fetchone()

        if row is None:
            raise ValueError(f"Job not found or already completed: {job_id}")

        await db.commit()

    return {
        "job_id": job_id,
        "status": "cancelled",
        "message": "Cancellation requested (worker will abort on next progress update)",
    }
```

**Risks**:
- Cancellation might not be immediate (acceptable: detected on next progress update)
- Status query might be stale if cached

---

### Phase 6: Indexer Enhancement (Parallel with Phase 4-5)

**Checkpoint**: Existing indexer service supports progress callbacks ✅

---

#### T011-test: Write tests for progress callback integration [Testing]
**Dependencies**: T002 (schema exists)
**Estimated Time**: 30 minutes
**Parallelization**: [P] Can run parallel with Phase 4 tests

**Description**:
Write tests for progress callback integration in the index_repository service.

**Deliverables**:
- [ ] Add tests to `tests/unit/test_indexer.py`
- [ ] Test callback invoked at scanning milestone
- [ ] Test callback invoked during chunking
- [ ] Test callback invoked during embedding
- [ ] Test callback receives correct percentages
- [ ] Test callback receives counters (files_scanned, etc.)

**Acceptance Criteria**:
- [ ] Tests initially fail (callback parameter doesn't exist)
- [ ] Test callback invoked at 10% (scanning complete)
- [ ] Test callback invoked during 10-50% (chunking)
- [ ] Test callback invoked during 50-90% (embedding)
- [ ] Test callback invoked at 95% (writing)
- [ ] Test callback receives files_scanned count
- [ ] Test indexer works without callback (optional parameter)

**Constitutional Principles**:
- Principle VII: TDD (tests before implementation)
- Principle IV: Performance (validate callback overhead minimal)

**Technical Notes**:
- Use mock callback to capture invocations
- Validate percentage progression: 10% → 50% → 90% → 100%
- Ensure callback is optional (backward compatibility)
- Reference architecture doc lines 842-910

**Test Structure**:
```python
@pytest.mark.asyncio
async def test_progress_callback_invoked(test_repo_path, test_db):
    """Test progress callback invoked at key milestones."""
    invocations = []

    async def mock_callback(message: str, percentage: int, **kwargs):
        invocations.append({
            "message": message,
            "percentage": percentage,
            "kwargs": kwargs,
        })

    result = await index_repository(
        repo_path=test_repo_path,
        name="test-repo",
        db=test_db,
        project_id="test",
        progress_callback=mock_callback,
    )

    # Verify callback invocations
    assert len(invocations) >= 3  # At least 3 milestones
    assert invocations[0]["percentage"] == 10  # Scanning
    assert "files_scanned" in invocations[0]["kwargs"]
```

**Risks**:
- Callback overhead might impact performance (measure with benchmarks)
- Callback exceptions might crash indexing (needs error handling)

---

#### T011: Add progress_callback parameter to index_repository [Implementation]
**Dependencies**: T011-test
**Estimated Time**: 1 hour
**Parallelization**: [P] Can run parallel with Phase 4-5 work

**Description**:
Enhance the existing index_repository function to accept an optional progress_callback parameter and invoke it at key milestones.

**Deliverables**:
- [ ] Add progress_callback parameter to index_repository signature
- [ ] Invoke callback after scanning (10%, files_scanned)
- [ ] Invoke callback during chunking (10-50%, files_indexed)
- [ ] Invoke callback during embedding (50-90%, chunks_created)
- [ ] Invoke callback before database writes (95%)
- [ ] Handle callback exceptions gracefully
- [ ] Maintain backward compatibility (callback optional)

**Acceptance Criteria**:
- [ ] All tests from T011-test pass
- [ ] Callback invoked at 4+ milestones
- [ ] Progress percentages match specification (10, 50, 90, 95)
- [ ] Counters passed to callback are accurate
- [ ] Callback exceptions logged but don't crash indexing
- [ ] Indexing works without callback (None default)

**Constitutional Principles**:
- Principle IV: Performance (callback overhead <5%)
- Principle V: Production Quality (error handling for callback failures)
- Principle VIII: Type Safety (proper callback signature typing)

**Technical Notes**:
- Reference architecture doc lines 842-910
- Callback signature: `Callable[[str, int], Awaitable[None]]`
- Calculate percentages based on batch progress
- Use try/except around callback invocations
- Log callback exceptions but continue indexing

**Code Changes**:
```python
# In src/services/indexer.py

from typing import Callable, Awaitable

async def index_repository(
    repo_path: Path,
    name: str,
    db: AsyncSession,
    project_id: str,
    force_reindex: bool = False,
    progress_callback: Callable[[str, int], Awaitable[None]] | None = None,  # NEW
) -> IndexResult:
    """Index repository with progress callbacks.

    Args:
        ...
        progress_callback: Optional async function(message: str, percentage: int, **kwargs)
            Called at key milestones with progress updates
    """

    # After scanning
    if progress_callback:
        try:
            await progress_callback(
                "Scanning repository...",
                10,
                files_scanned=len(all_files)
            )
        except Exception as e:
            logger.error(f"Progress callback failed: {e}")

    # During chunking
    for i, batch in enumerate(batches):
        percentage = 10 + int(40 * (i / total_batches))
        if progress_callback:
            try:
                await progress_callback(
                    f"Chunking files: {i * batch_size}/{total_files}",
                    percentage,
                    files_indexed=i * batch_size
                )
            except Exception as e:
                logger.error(f"Progress callback failed: {e}")

    # During embedding (50-90%)
    # Before database writes (95%)
    # Continue existing logic...
```

**Risks**:
- Callback overhead might slow down indexing (measure with benchmarks)
- Callback exceptions might lose progress tracking

---

### Phase 7: Integration Testing

**Checkpoint**: End-to-end workflows validated ✅

---

#### T012: Write integration test for complete workflow [Testing]
**Dependencies**: T010 (all tools exist)
**Estimated Time**: 1 hour
**Parallelization**: Cannot parallelize (requires full system)

**Description**:
Write comprehensive integration test for the complete background indexing workflow: start → poll → complete.

**Deliverables**:
- [ ] Create test file: `tests/integration/test_background_indexing_workflow.py`
- [ ] Test small repository (4 files, fast completion)
- [ ] Test polling loop with timeout
- [ ] Verify final status and counters
- [ ] Test force_reindex flag behavior
- [ ] Test error handling (invalid repo path)

**Acceptance Criteria**:
- [ ] Test creates job via start_indexing_background
- [ ] Test polls get_indexing_status every 2 seconds
- [ ] Test verifies status transitions: pending → running → completed
- [ ] Test verifies files_indexed > 0 and chunks_created > 0
- [ ] Test completes within 30 seconds (small repo)
- [ ] Test validates progress_percentage reaches 100
- [ ] Test verifies repository_id populated in final status

**Constitutional Principles**:
- Principle VII: TDD (comprehensive integration testing)
- Principle IV: Performance (validate 60s target for 10K files)
- Principle V: Production Quality (end-to-end validation)

**Technical Notes**:
- Use pytest fixtures for test repository (4-5 Python files)
- Poll with asyncio.sleep(2) between status checks
- Use asyncio.wait_for() for timeout safety (30s max)
- Clean up job records after test

**Test Structure**:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_background_indexing_complete_workflow(test_repo_path):
    """Test complete background indexing workflow."""
    # Start job
    result = await start_indexing_background(
        repo_path=str(test_repo_path),
        project_id="test",
    )
    job_id = result["job_id"]

    # Poll until completion
    max_attempts = 15  # 30 seconds max (2s polling interval)
    for attempt in range(max_attempts):
        status = await get_indexing_status(job_id=job_id, project_id="test")

        if status["status"] in ["completed", "failed"]:
            break

        await asyncio.sleep(2)
    else:
        pytest.fail("Job did not complete within 30 seconds")

    # Verify completion
    assert status["status"] == "completed"
    assert status["progress_percentage"] == 100
    assert status["files_indexed"] > 0
    assert status["chunks_created"] > 0
    assert status["completed_at"] is not None
```

**Risks**:
- Test might be flaky if system under load
- Timeout might be too short for slower systems

---

#### T013: Write integration test for cancellation [Testing]
**Dependencies**: T010
**Estimated Time**: 30 minutes
**Parallelization**: [P] Can run parallel with T012

**Description**:
Write integration test for job cancellation during execution.

**Deliverables**:
- [ ] Add test to `tests/integration/test_background_indexing_workflow.py`
- [ ] Start job with large repository (slow indexing)
- [ ] Cancel job mid-execution
- [ ] Verify status transitions to cancelled
- [ ] Verify worker aborts cleanly

**Acceptance Criteria**:
- [ ] Test starts indexing job
- [ ] Test waits 1 second for job to start
- [ ] Test calls cancel_indexing_background
- [ ] Test verifies status becomes 'cancelled' within 10 seconds
- [ ] Test verifies cancelled_at timestamp set
- [ ] Test verifies no hanging connections or tasks

**Constitutional Principles**:
- Principle VII: TDD (edge case testing)
- Principle V: Production Quality (clean cancellation)

**Technical Notes**:
- Use larger test repository to ensure job runs long enough
- Verify worker detects cancellation within 5 seconds (progress update interval)
- Clean up test database after cancellation

**Test Structure**:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_background_indexing_cancellation():
    """Test job cancellation during execution."""
    # Start job
    result = await start_indexing_background(
        repo_path=str(large_test_repo),
        project_id="test",
    )
    job_id = result["job_id"]

    # Wait for job to start
    await asyncio.sleep(1)

    # Cancel job
    cancel_result = await cancel_indexing_background(
        job_id=job_id,
        project_id="test",
    )
    assert cancel_result["status"] == "cancelled"

    # Wait for worker to detect cancellation
    await asyncio.sleep(6)

    # Verify cancellation
    status = await get_indexing_status(job_id=job_id, project_id="test")
    assert status["status"] == "cancelled"
    assert status["cancelled_at"] is not None
```

**Risks**:
- Cancellation might not propagate quickly enough
- Worker might not clean up resources properly

---

#### T014: Write integration test for concurrent jobs [Testing]
**Dependencies**: T010
**Estimated Time**: 30 minutes
**Parallelization**: [P] Can run parallel with T012

**Description**:
Write integration test for multiple concurrent indexing jobs in different projects.

**Deliverables**:
- [ ] Add test to `tests/integration/test_background_indexing_workflow.py`
- [ ] Start 3 jobs in parallel (different projects)
- [ ] Verify all jobs complete successfully
- [ ] Verify no interference between jobs
- [ ] Validate connection pool doesn't exhaust

**Acceptance Criteria**:
- [ ] Test starts 3 indexing jobs concurrently
- [ ] All 3 jobs reach status='running'
- [ ] All 3 jobs complete successfully
- [ ] No connection pool exhaustion errors
- [ ] Each job's progress tracked independently

**Constitutional Principles**:
- Principle IV: Performance (concurrent execution)
- Principle V: Production Quality (resource management)

**Technical Notes**:
- Use different project_ids for isolation
- Monitor connection pool usage
- Verify no deadlocks or contention

**Test Structure**:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_background_jobs():
    """Test multiple concurrent indexing jobs."""
    jobs = []
    for i in range(3):
        result = await start_indexing_background(
            repo_path=str(test_repo),
            project_id=f"test-project-{i}",
        )
        jobs.append(result["job_id"])

    # Wait for all jobs to complete
    await asyncio.sleep(10)

    # Verify all completed
    for job_id in jobs:
        status = await get_indexing_status(job_id=job_id)
        assert status["status"] in ["completed", "running"]
```

**Risks**:
- Connection pool might exhaust under concurrent load
- Jobs might interfere with each other

---

#### T015: Write test for state persistence across restarts [Testing]
**Dependencies**: T010
**Estimated Time**: 30 minutes
**Parallelization**: [P] Can run parallel with other tests

**Description**:
Write test that validates job state persists across server restarts (simulated connection pool closure).

**Deliverables**:
- [ ] Add test to `tests/integration/test_background_indexing_workflow.py`
- [ ] Create job record
- [ ] Simulate restart (close connection pools)
- [ ] Verify job still queryable after restart
- [ ] Verify job status preserved

**Acceptance Criteria**:
- [ ] Test creates job in database
- [ ] Test closes all connection pools
- [ ] Test reinitializes connection pools
- [ ] Test queries job status successfully
- [ ] Job status matches pre-restart state

**Constitutional Principles**:
- Principle V: Production Quality (state persistence)
- Principle II: Local-First (PostgreSQL reliability)

**Technical Notes**:
- Don't start actual worker (just test persistence)
- Close pools via provisioning.close_all_pools()
- Reinitialize via get_session()

**Test Structure**:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_job_state_persistence():
    """Test job state persists across server restarts."""
    # Create job
    async with get_session(project_id="test") as db:
        result = await db.execute(
            text("INSERT INTO indexing_jobs (...) VALUES (...) RETURNING id")
        )
        job_id = result.fetchone()[0]
        await db.commit()

    # Simulate restart (close pools)
    await close_all_pools()

    # Reinitialize and query
    status = await get_indexing_status(job_id=str(job_id), project_id="test")
    assert status["job_id"] == str(job_id)
    assert status["status"] == "pending"
```

**Risks**:
- Test might not accurately simulate restart
- Connection pool state might not fully reset

---

### Phase 8: Documentation & Polish

**Checkpoint**: User documentation complete, feature ready for production ✅

---

#### T016: Update .env.example with background indexing config [Documentation]
**Dependencies**: All previous phases
**Estimated Time**: 15 minutes
**Parallelization**: [P] Can run parallel with other docs

**Description**:
Add configuration examples for background indexing to .env.example.

**Deliverables**:
- [ ] Add section "Background Indexing" to .env.example
- [ ] Document MAX_CONCURRENT_INDEXING_JOBS
- [ ] Document INDEXING_JOB_TIMEOUT_SECONDS
- [ ] Document JOB_STATUS_RETENTION_DAYS
- [ ] Document MAX_REPO_SIZE_GB
- [ ] Document PROGRESS_UPDATE_INTERVAL_SECONDS
- [ ] Add comments explaining each option

**Acceptance Criteria**:
- [ ] All configuration options documented
- [ ] Defaults match architecture spec
- [ ] Comments explain purpose and impact
- [ ] Examples show reasonable production values

**Constitutional Principles**:
- Principle V: Production Quality (clear configuration)
- Principle VI: Specification-First (documentation matches spec)

**Technical Notes**:
- Reference architecture doc lines 1020-1036
- Include both development and production examples
- Explain performance implications of settings

**Configuration Template**:
```bash
# Background Indexing Configuration
# Maximum number of concurrent background indexing jobs
MAX_CONCURRENT_INDEXING_JOBS=2

# Timeout per indexing job (seconds)
INDEXING_JOB_TIMEOUT_SECONDS=3600

# Cleanup completed jobs older than N days
JOB_STATUS_RETENTION_DAYS=7

# Maximum repository size (GB) - reject larger repos
MAX_REPO_SIZE_GB=10

# Progress update frequency (seconds) - don't set too low
PROGRESS_UPDATE_INTERVAL_SECONDS=2

# Cancellation check interval (seconds)
CANCELLATION_CHECK_INTERVAL_SECONDS=5
```

**Risks**:
- None (documentation only)

---

#### T017: Update CLAUDE.md with background indexing usage [Documentation]
**Dependencies**: T016
**Estimated Time**: 30 minutes
**Parallelization**: [P] Can run parallel with T018

**Description**:
Add usage patterns and examples for background indexing to CLAUDE.md project instructions.

**Deliverables**:
- [ ] Add "Background Indexing" section to CLAUDE.md
- [ ] Document when to use background vs. foreground indexing
- [ ] Provide usage examples (start, poll, cancel patterns)
- [ ] Document troubleshooting tips
- [ ] Link to architecture doc

**Acceptance Criteria**:
- [ ] Section explains background indexing purpose
- [ ] 3 usage patterns documented (start-and-poll, fire-and-forget, cancellation)
- [ ] Examples use correct MCP tool syntax
- [ ] Troubleshooting covers common issues (timeout, cancellation, failure)
- [ ] Links to architecture doc for details

**Constitutional Principles**:
- Principle VI: Specification-First (documentation from spec)
- Principle XI: FastMCP Foundation (tool usage examples)

**Technical Notes**:
- Reference architecture doc lines 912-965 for usage patterns
- Include code examples in Python
- Explain when background indexing is required (10K+ files)

**Documentation Template**:
```markdown
## Background Indexing

Large repositories (10,000+ files) require 5-10 minutes to index, which exceeds typical MCP request timeouts. Use background indexing for these repositories.

### When to Use Background Indexing

- **Foreground (default)**: Repositories with <5,000 files (completes in <60 seconds)
- **Background**: Repositories with 10,000+ files (requires 5-10 minutes)

### Usage Pattern 1: Start and Poll

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
    if status["status"] in ["completed", "failed", "cancelled"]:
        break
    print(f"Progress: {status['progress_percentage']}% - {status['progress_message']}")
    await asyncio.sleep(2)

if status["status"] == "completed":
    print(f"✅ Indexed {status['files_indexed']} files!")
```

### Troubleshooting

**Job stuck in 'running' status**:
- Check server logs: `/tmp/codebase-mcp.log`
- Verify Ollama is running: `curl http://localhost:11434/api/tags`
- Cancel and restart: `await cancel_indexing_background(job_id=...)`

**Job fails immediately**:
- Verify repository path exists and is accessible
- Check path is absolute (not relative)
- Ensure sufficient disk space

For detailed architecture, see: `docs/architecture/background-indexing.md`
```

**Risks**:
- None (documentation only)

---

#### T018: Create integration examples in docs/ [Documentation]
**Dependencies**: T015 (tests exist as examples)
**Estimated Time**: 15 minutes
**Parallelization**: [P] Can run parallel with T017

**Description**:
Create standalone example scripts demonstrating background indexing integration.

**Deliverables**:
- [ ] Create file: `docs/examples/background_indexing_example.py`
- [ ] Example 1: Basic start-and-poll workflow
- [ ] Example 2: Cancellation workflow
- [ ] Example 3: Fire-and-forget workflow
- [ ] Add README.md explaining examples

**Acceptance Criteria**:
- [ ] Examples are runnable scripts
- [ ] Each example has clear comments
- [ ] README explains how to run examples
- [ ] Examples cover main use cases

**Constitutional Principles**:
- Principle VI: Specification-First (examples from spec)
- Principle XI: FastMCP Foundation (correct tool usage)

**Technical Notes**:
- Copy patterns from integration tests
- Simplify for readability
- Include error handling

**Risks**:
- None (documentation only)

---

#### T019: Validate quickstart.md scenarios [Testing]
**Dependencies**: T017 (documentation exists)
**Estimated Time**: 30 minutes
**Parallelization**: Cannot parallelize (final validation)

**Description**:
Manually validate all quickstart scenarios documented in CLAUDE.md work correctly.

**Deliverables**:
- [ ] Run start-and-poll example
- [ ] Run cancellation example
- [ ] Run fire-and-forget example
- [ ] Verify all examples complete without errors
- [ ] Document any issues found

**Acceptance Criteria**:
- [ ] All 3 usage patterns execute successfully
- [ ] Progress updates visible in logs
- [ ] Cancellation works within 5 seconds
- [ ] No errors in `/tmp/codebase-mcp.log`
- [ ] Database state clean after completion

**Constitutional Principles**:
- Principle VII: TDD (validation before release)
- Principle V: Production Quality (end-to-end verification)

**Technical Notes**:
- Use real MCP server (not mocks)
- Test with realistic repository (1,000-5,000 files)
- Verify against architecture specification

**Risks**:
- Quickstart might reveal issues not caught by unit/integration tests

---

## Critical Path

Tasks that cannot be delayed (blocking other work):

1. **T001** → T002 → T003: Database schema (blocks all other work)
2. **T004-test** → T004: Models (blocks utilities)
3. **T006-test** → T006 → T007: Database utilities (blocks worker)
4. **T008-test** → T008: Background worker (blocks tools)
5. **T009-test** → T009 → T010: MCP tools (blocks integration tests)
6. **T012-T015**: Integration testing (blocks release)
7. **T019**: Quickstart validation (final gate)

**Total Critical Path Time**: ~9 hours

---

## Parallel Work Opportunities

These tasks can run simultaneously (marked with [P]):

### Phase 2 Parallelization
- T004-test (model tests) [P]
- T005-test (path validation tests) [P]

### Phase 4-6 Parallelization
- T011-test (progress callback tests) [P] - while T008 is in progress
- T011 (indexer enhancement) [P] - parallel with T009-T010

### Phase 7 Parallelization
- T012 (workflow test)
- T013 (cancellation test) [P]
- T014 (concurrent jobs test) [P]
- T015 (persistence test) [P]

### Phase 8 Parallelization
- T016 (env docs) [P]
- T017 (CLAUDE.md) [P]
- T018 (examples) [P]

**Savings from Parallelization**: ~2 hours

---

## Risk Register

### High Priority Risks

1. **Path Traversal Validation Edge Cases**
   - Risk: Validation might not catch all attack vectors
   - Mitigation: Comprehensive test coverage (T005-test), security review
   - Owner: T004, T005

2. **Worker Resource Leaks**
   - Risk: Background workers might not clean up connections
   - Mitigation: finally blocks in worker, connection pool monitoring
   - Owner: T008

3. **Race Conditions in Job State**
   - Risk: Concurrent updates might cause inconsistency
   - Mitigation: PostgreSQL transaction isolation, row-level locking
   - Owner: T006, T007

4. **Migration Rollback Safety**
   - Risk: Downgrade might leave database in bad state
   - Mitigation: Test downgrade path thoroughly (T003)
   - Owner: T001, T003

### Medium Priority Risks

5. **Progress Callback Performance**
   - Risk: Callback overhead might slow indexing >5%
   - Mitigation: Benchmark before/after (T011), optimize if needed
   - Owner: T011

6. **Cancellation Latency**
   - Risk: Worker might not detect cancellation quickly enough
   - Mitigation: Check cancellation on every progress update (~2s interval)
   - Owner: T008, T013

7. **Test Flakiness**
   - Risk: Integration tests might be timing-dependent
   - Mitigation: Generous timeouts, proper test isolation
   - Owner: T012-T015

### Low Priority Risks

8. **Documentation Drift**
   - Risk: Docs might not match implementation
   - Mitigation: Generate docs from code, validate quickstart (T019)
   - Owner: T016-T018

---

## Success Metrics

**Feature Complete When:**

1. ✅ All 57 acceptance criteria pass
2. ✅ All tests pass (unit, integration, contract)
3. ✅ mypy --strict passes with no errors
4. ✅ Migration applies cleanly (upgrade and downgrade)
5. ✅ All 3 MCP tools registered and functional
6. ✅ Background indexing completes within 60s for 10K files
7. ✅ Job state persists across server restarts
8. ✅ Cancellation works within 5 seconds
9. ✅ No connection pool leaks or resource leaks
10. ✅ Documentation complete (CLAUDE.md, examples, .env)
11. ✅ Quickstart validation passes (T019)
12. ✅ No CRITICAL constitutional violations

**Performance Targets:**
- Indexing 10K files: <60 seconds (maintained from baseline)
- Job creation: <100ms (non-blocking)
- Status query: <50ms (simple SELECT)
- Cancellation: <5s propagation time
- Progress updates: <10ms per update

**Quality Targets:**
- Test coverage: >80% (existing project standard)
- Type safety: 100% mypy --strict compliance
- Security: 0 path traversal vulnerabilities
- Reliability: State persists across restarts

---

## Implementation Notes

### Git Micro-Commit Strategy

After completing each task (or logical subtask), make an atomic commit:

```bash
# After T001 (migration)
git add migrations/versions/008_add_indexing_jobs.py
git commit -m "feat(indexing): add indexing_jobs table migration

- Add indexing_jobs table with 18 columns
- Add 4 performance indexes with WHERE clauses
- Add CHECK constraints for status and progress range
- Implement upgrade and downgrade functions

Constitutional Compliance: Principle V (Production Quality), Principle VIII (Type Safety)
References: docs/architecture/background-indexing.md lines 73-129"

# After T004 (models)
git add src/models/indexing_job.py src/models/__init__.py
git commit -m "feat(models): add IndexingJob Pydantic models

- Add IndexingJobStatus enum (5 states)
- Add IndexingJobCreate with path traversal validation
- Add IndexingJobProgress (immutable output model)
- Validator prevents relative paths and ../ sequences

Constitutional Compliance: Principle VIII (Type Safety), Principle V (Production Quality)
References: docs/architecture/background-indexing.md lines 136-193"

# Continue pattern for each task...
```

### Testing Strategy

**Test Execution Order:**
1. Unit tests first (T004-test, T005-test, T006-test, T011-test)
2. Integration tests second (T008-test, T012-T015)
3. Contract tests third (T009-test)
4. Manual validation last (T019)

**Test Isolation:**
- Each test creates its own test project database
- Clean up job records after each test
- Use pytest fixtures for database setup/teardown

### Constitutional Compliance Checkpoints

**After Phase 1** (Database Schema):
- ✅ Principle V: Indexes for performance
- ✅ Principle VIII: Explicit column types

**After Phase 2** (Models):
- ✅ Principle VIII: Pydantic models, mypy --strict
- ✅ Principle V: Path traversal prevention

**After Phase 4** (Worker):
- ✅ Principle V: Comprehensive error handling
- ✅ Principle IV: Non-blocking execution

**After Phase 5** (Tools):
- ✅ Principle XI: FastMCP decorators
- ✅ Principle III: MCP protocol compliance

**After Phase 7** (Testing):
- ✅ Principle VII: TDD approach throughout
- ✅ Principle IV: Performance validation

---

## Post-Implementation Tasks (Future Enhancements)

**Not required for initial release, but documented for future work:**

1. **Job History Cleanup** (Optional)
   - Implement background task to clean up old completed jobs
   - Reference: architecture doc lines 1390-1419

2. **LISTEN/NOTIFY** (Optional)
   - Add real-time notifications via PostgreSQL LISTEN/NOTIFY
   - For advanced clients that want push-based updates
   - Reference: architecture doc lines 1351-1386

3. **Resource Limits Enforcement** (Nice-to-have)
   - Enforce MAX_CONCURRENT_INDEXING_JOBS
   - Add repository size validation
   - Job timeout via asyncio.wait_for()

4. **Orphaned Job Detection** (Nice-to-have)
   - Detect jobs stuck in 'running' after server crash
   - Mark as 'failed' with timeout error

---

## Completion Summary

**When all tasks complete:**

- ✅ PostgreSQL-native background indexing fully functional
- ✅ Job state persists across server restarts
- ✅ Path traversal attacks prevented
- ✅ All constitutional principles maintained
- ✅ Comprehensive test coverage (unit, integration, contract)
- ✅ Documentation complete and validated
- ✅ Production-ready reliability and security

**Ready for merge to main branch when:**
- All 19 tasks marked [X]
- All acceptance criteria validated
- Quickstart scenarios pass (T019)
- No CRITICAL constitutional violations
- Code review approved
- CI/CD pipeline green

---

**End of Tasks Document**

Total Tasks: 19 (T001-T019)
Total Estimated Time: 10-12 hours
Critical Path: 9 hours
Parallelization Savings: 2 hours

**Next Step**: Create feature branch and start with T001 (migration)

```bash
git checkout -b 015-background-indexing
git push -u origin 015-background-indexing
```
