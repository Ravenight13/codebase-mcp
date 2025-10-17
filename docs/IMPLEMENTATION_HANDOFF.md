# Background Indexing MVP - Implementation Handoff

**Date**: 2025-10-17
**Branch**: `015-background-indexing-mvp` ✅ **ACTIVE**
**Previous Branch**: `014-add-background-indexing`
**Status**: Phase 1 Complete (T001-T002) - Ready for T003

---

## Executive Summary

### What We're Building

Background indexing support for large repositories (10K+ files) that exceed MCP client timeout limits (30 seconds). Users can start indexing, receive immediate confirmation with a job ID, and poll for status while the work completes in the background.

### Why It's Needed

**Problem**: Large repositories (10K+ files) take 5-10 minutes to index, exceeding typical MCP request timeouts. Claude Code stops waiting, and users lose their work.

**Solution**: Background indexing with PostgreSQL job tracking
- Start job → get job_id immediately (<1s)
- Poll status with `get_indexing_status(job_id)`
- State persists in PostgreSQL (survives restarts)

### What Approach Was Chosen

**MVP-optimized approach** (6-7 hours, 13 tasks):
- PostgreSQL-native architecture (not in-memory)
- Reuse existing infrastructure (`session.py`, `indexer.py`)
- Simplified schema (10 columns vs. 18 in full plan)
- Binary state tracking (running/done, no granular progress)
- Deferred features: job listing, ETA calculation, cancellation, resumption

### Current Status

**Phase 1 Complete**: Database migration created, tested, and validated.

**✅ Completed Tasks (Phase 1)**:
- **T001**: Alembic migration created (`008_add_indexing_jobs.py`, 138 lines)
- **T002**: Migration applied and validated (see validation report)

**Deliverables**:
- Migration file with upgrade/downgrade functions
- Type stub for mypy compliance
- Comprehensive validation report (208 lines)
- Git commit: `e6573958`

**Validation Summary**:
- ✅ All 10 columns created with correct types/defaults
- ✅ CHECK constraint working (rejects invalid status)
- ✅ Partial index performance: 0.030ms (target <100ms)
- ✅ created_at index performance: 0.039ms (target <100ms)
- ✅ Downgrade tested successfully

**Next Steps**:
- **T003** (30m): Create `IndexingJob` Pydantic model
- **T003-test** (15m): Unit tests for model validation

---

## Key Decisions Made

### 1. MVP-First Approach
- **Scope**: User Story 1 only (start job + check status)
- **Timeline**: 6-7 hours vs. 10-12 hours for full plan (58% faster)
- **Code**: ~1,200-1,500 lines vs. ~2,500 lines (50% less)
- **Rationale**: Ship core functionality fast, iterate based on user feedback

### 2. PostgreSQL-Native Architecture
- **State storage**: PostgreSQL `indexing_jobs` table (not in-memory)
- **Benefits**: Survives restarts, ACID guarantees, no custom job manager
- **Trade-off**: No real-time progress updates (poll-based only)

### 3. Reuse Existing Infrastructure
- **Database**: Use `get_session()` and `resolve_project_id()` from `session.py`
- **Indexer**: No modifications to `indexer.py` (call as-is)
- **MCP**: Use `@mcp.tool()` decorator from FastMCP
- **Rationale**: Minimize new code, leverage battle-tested infrastructure

### 4. Simplified Database Schema
- **Essential columns**: 10 vs. 18 in full plan
- **Removed**: progress_percentage, progress_message, phase messages, ETA
- **Keep**: id, repo_path, project_id, status, error_message, timestamps, counters
- **Rationale**: MVP needs binary state (running/done), not real-time progress

### 5. Deferred Features (Phase 2)
- **US2**: Job listing, ETA calculation, phase messages
- **US3**: Cancellation
- **US4**: Resumption after failures
- **Rationale**: Nice-to-have features, not critical for core functionality

---

## Implementation Plan

### Primary Task Document
**File**: `docs/architecture/background-indexing-tasks-mvp.md`
**Tasks**: 13 tasks (T001-T013)
**Timeline**: 6-7 hours
**Critical Path**: T001 → T002 → T003 → T004 → T005 → T006 → T013 (5.5 hours)

### Task Breakdown

#### Phase 1: Database (1h)
- **T001**: Create simplified Alembic migration (45m)
- **T002**: Apply migration and validate (15m)

#### Phase 2: Models (1h)
- **T003**: Create IndexingJob SQLAlchemy + Pydantic models (45m)
- **T003-test**: Unit tests for models (15m) [CAN RUN PARALLEL WITH T004]

#### Phase 3: Core Implementation (2.5h)
- **T004**: Implement simplified background worker (45m)
- **T005**: Implement `start_indexing_background()` MCP tool (30m)
- **T006**: Implement `get_indexing_status()` MCP tool (30m)
- **T007**: Add `update_job()` utility function (15m)
- **T008**: Integration test for complete workflow (30m)

#### Phase 4: Production Hardening (1h)
- **T009**: Add error handling and logging (20m) [CAN RUN PARALLEL]
- **T010**: Test state persistence across restart (20m)
- **T011**: Add configuration to .env (10m) [CAN RUN PARALLEL]
- **T012**: Update documentation (10m) [CAN RUN PARALLEL]

#### Phase 5: Validation (30m)
- **T013**: End-to-end test with large repository (30m)

### Parallel Opportunities
- T003-test can run parallel with T004 (after T003)
- T009-T012 can run in parallel (documentation and config)

---

## Key Files to Reference

### Architecture & Planning
- `docs/architecture/background-indexing-tasks-mvp.md` - **PRIMARY TASK LIST** (read this first!)
- `docs/architecture/background-indexing.md` - Detailed architecture specification
- `specs/014-add-background-indexing/spec.md` - User stories and requirements
- `.specify/memory/constitution.md` - Constitutional principles (simplicity, production quality)

### Existing Code to Reuse
- `src/database/session.py` - **Key infrastructure**
  - `get_session(ctx=ctx)` - Database session with project resolution
  - `resolve_project_id(ctx=ctx)` - 4-tier project resolution chain
  - No modifications needed, just call these functions
- `src/services/indexer.py` - **Existing indexer**
  - `index_repository(repo_path, name, db, project_id)` - No modifications needed!
  - Call as-is from background worker
- `src/mcp/server_fastmcp.py` - **MCP server**
  - `@mcp.tool()` decorator for registering new tools
  - `from src.mcp.server_fastmcp import mcp`
- `migrations/versions/` - **Alembic migration examples**
  - Look at recent migrations for schema patterns
  - Follow naming convention: `###_add_indexing_jobs.py`

### Git Context
- **Current branch**: `015-background-indexing-mvp` ✅ **ACTIVE**
- **Main branch**: `master`
- **Last commit**: `e6573958` - "feat(indexing): add indexing_jobs table migration"

---

## First Steps (Immediate Actions)

### ✅ 1. Create Feature Branch (COMPLETE)
Branch `015-background-indexing-mvp` created and active.

### ✅ 2. Database Migration (T001-T002 COMPLETE)
**Migration file**: `migrations/versions/008_add_indexing_jobs.py` ✅ Created
**Type stub**: `migrations/versions/008_add_indexing_jobs.pyi` ✅ Created
**Validation report**: `docs/migrations/008-indexing-jobs-validation.md` ✅ Created
**Status**: Migration applied, all tests passing

**Validation Results**:
- ✅ All 10 columns created with correct types/defaults
- ✅ CHECK constraint rejects invalid status values
- ✅ Partial index optimizes active job queries (0.030ms)
- ✅ created_at index optimizes history queries (0.039ms)
- ✅ Downgrade tested and working

### 3. Next: Create Pydantic Model (T003)
**Create file**: `src/models/indexing_job.py`

**Reference**: `docs/architecture/background-indexing-tasks-mvp.md` lines 196-276

**Requirements**:
- SQLAlchemy model (`IndexingJob`) mapping to `indexing_jobs` table
- Pydantic models (`IndexingJobCreate`, `IndexingJobResponse`)
- Path validation (absolute paths only, no traversal)
- Status type safety (TypedDict or Enum)

### 4. Follow TDD Approach
- Implement test task first (if exists)
- Then implementation task
- Commit after each task with conventional commit message

**Example commit messages**:
```bash
git commit -m "feat(indexing): add indexing_jobs table migration"
git commit -m "test(indexing): add model validation tests"
git commit -m "feat(indexing): implement background worker"
```

---

## Critical Context

### Problem Statement (Detailed)

**Symptoms**:
- Large repositories (10K+ files) take 5-10 minutes to index
- MCP client timeout is ~30 seconds (validated with Claude Code)
- Claude Code stops waiting, user loses progress
- Current `index_repository()` tool is synchronous (blocking)

**User Experience Impact**:
- Users with enterprise codebases cannot use semantic search
- Frustration from lost work and unclear status
- No visibility into long-running operations

### Solution Architecture

**Background indexing with PostgreSQL job tracking**:

1. **Start Job** (`start_indexing_background()`):
   - Validate repo_path (absolute, no traversal)
   - Create job record (status=pending)
   - Spawn asyncio.Task for worker
   - Return job_id immediately (<1s)

2. **Poll Status** (`get_indexing_status(job_id)`):
   - Query indexing_jobs table
   - Return status, counters, error message
   - User polls every 2-5 seconds

3. **Background Worker**:
   - Update job to status=running
   - Call existing `index_repository()` (no changes!)
   - Update job to status=completed or failed
   - All state in PostgreSQL (survives restarts)

**State Machine**:
```
pending → running → completed
                 → failed
```

### MVP Scope (User Story 1)

**What's Included**:
- ✅ `start_indexing_background()` - Start job, return job_id
- ✅ `get_indexing_status(job_id)` - Poll for status
- ✅ Job table with status tracking (pending/running/completed/failed)
- ✅ State persists across restarts
- ✅ Error handling and logging

**What's Deferred (Phase 2)**:
- ❌ `list_background_jobs()` - No job listing
- ❌ ETA calculation - No time estimates
- ❌ Cancellation - Jobs run to completion
- ❌ Granular progress - Just running/done (no percentage)
- ❌ Resumption - No checkpoint recovery

---

## Key Design Patterns

### Pattern 1: Reuse Existing Session Management

```python
from src.database.session import get_session, resolve_project_id

# In MCP tools and worker
async with get_session(project_id=project_id, ctx=ctx) as session:
    job = await session.get(IndexingJob, job_id)
    job.status = "completed"
    await session.commit()
```

**Why**: `session.py` already handles:
- Project resolution (4-tier chain)
- Connection pooling
- Transaction management
- Error handling

### Pattern 2: Simple Background Worker

```python
async def _background_indexing_worker(job_id: UUID, repo_path: str, project_id: str, ctx: Context):
    """Simple state machine: pending → running → completed/failed."""
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

**Why**:
- No progress callbacks (deferred to Phase 2)
- Binary state (running or done)
- Reuses existing indexer unchanged

### Pattern 3: FastMCP Tool Structure

```python
from src.mcp.server_fastmcp import mcp
from fastmcp import Context

@mcp.tool()
async def start_indexing_background(
    repo_path: str,
    project_id: str | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Start repository indexing in background."""
    # Resolve project
    resolved_id, db_name = await resolve_project_id(explicit_id=project_id, ctx=ctx)

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

**Why**:
- FastMCP integration (`@mcp.tool()`)
- Path validation (security)
- Immediate response (<1s)
- Non-blocking worker spawn

---

## Database Schema (Reference)

### Simplified Schema (10 columns)

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

### Removed Columns (Deferred to Phase 2)
- `progress_percentage` - No real-time progress
- `progress_message` - No phase messages
- `files_scanned` - No scanning counter
- `error_type`, `error_traceback` - Simple error_message only
- `cancelled_at` - No cancellation in MVP
- `metadata` - No extensibility yet
- `worker_task_id`, `connection_id` - No resource tracking
- `force_reindex` - No force flag

**Rationale**: MVP focuses on start + status, not monitoring or control.

---

## Success Criteria

Before considering implementation complete:

- [ ] All 13 tasks completed (T001-T013)
- [ ] Index 10K+ file repository without timeout
- [ ] Job creation responds in <1 second
- [ ] State persists across server restart
- [ ] Integration tests pass
- [ ] Documentation updated (CLAUDE.md)

**Acceptance Tests**:

1. **Basic workflow**:
   - Start indexing on 4-file test repo
   - Poll status until completed
   - Verify files_indexed=4, chunks_created>0

2. **Large repository**:
   - Index codebase-mcp itself (1,000+ files)
   - Job creation <1s
   - Completes within 5 minutes
   - No timeout errors

3. **State persistence**:
   - Start job
   - Stop server mid-execution
   - Restart server
   - Query job status (should persist)

4. **Error handling**:
   - Index non-existent path
   - Status shows "failed" with clear error message

---

## Constitutional Compliance Checklist

### Principle I: Simplicity Over Features
- [ ] Reuses existing code (session.py, indexer.py)
- [ ] No custom job manager (PostgreSQL-native)
- [ ] Minimal new complexity (13 tasks, 1,200 lines)

### Principle II: Local-First Architecture
- [ ] PostgreSQL only (no Redis, RabbitMQ)
- [ ] No external dependencies
- [ ] Offline-capable storage

### Principle III: Protocol Compliance
- [ ] MCP-compliant tool responses
- [ ] Structured JSON responses
- [ ] No stdout/stderr pollution

### Principle IV: Performance Guarantees
- [ ] Job creation <1s (non-blocking)
- [ ] Status queries <100ms (indexed queries)
- [ ] No degradation during concurrent jobs

### Principle V: Production Quality
- [ ] Comprehensive error handling
- [ ] State persistence across restarts
- [ ] Structured logging with context
- [ ] Path traversal prevention
- [ ] No resource leaks

### Principle VIII: Type Safety
- [ ] Pydantic models for validation
- [ ] SQLAlchemy models for database
- [ ] mypy --strict compliance

### Principle XI: FastMCP Foundation
- [ ] Uses `@mcp.tool()` decorator
- [ ] Async/await throughout
- [ ] Context passed to sessions

---

## Quick Reference - Task Breakdown

### Phase 1: Database (1h) ✅ **COMPLETE**
- **T001**: Migration (45m) - Create `migrations/versions/008_add_indexing_jobs.py` ✅
- **T002**: Validate (15m) - Apply migration, test schema ✅

### Phase 2: Models (1h)
- **T003**: SQLAlchemy + Pydantic (45m) - Create `src/models/indexing_job.py`
- **T003-test**: Model tests (15m) - Create `tests/unit/test_indexing_job_models.py`

### Phase 3: Core (2.5h)
- **T004**: Worker (45m) - Create `src/services/background_worker.py`
- **T005**: start_indexing_background (30m) - Create `src/mcp/tools/background_indexing.py`
- **T006**: get_indexing_status (30m) - Add to `background_indexing.py`
- **T007**: update_job utility (15m) - Add to `background_worker.py`
- **T008**: Integration test (30m) - Create `tests/integration/test_background_indexing.py`

### Phase 4: Hardening (1h)
- **T009**: Error handling (20m) - Enhance worker error handling
- **T010**: State persistence test (20m) - Test server restart scenario
- **T011**: Configuration (10m) - Update `.env.example`
- **T012**: Documentation (10m) - Update `CLAUDE.md`

### Phase 5: Validation (30m)
- **T013**: E2E test with large repo (30m) - Test with codebase-mcp itself

---

## Known Issues from Previous Session

### Issue Resolved: Missing `projects` Table
- **Problem**: Registry database missing `projects` table
- **Fix**: Created table with proper schema
- **Status**: ✅ Resolved
- **Note**: This is already fixed in the environment

### Current Environment State
- **Registry database**: `codebase_mcp` (has `projects` table)
- **Project databases**: `cb_proj_*` pattern
- **Test repository**: `/tmp/test-repo` (4 files, 5 chunks) already indexed
- **Semantic search**: ✅ Working

**Validation**:
```bash
# Check registry database
psql codebase_mcp -c "\d projects"

# Check test repo indexed
psql cb_proj_default_00000000 -c "SELECT COUNT(*) FROM repositories;"
```

---

## Contact Information

### Previous Session Context
- **Session date**: 2025-10-17
- **Focus**: Architecture design, task planning, optimization
- **Key decisions**: MVP-first approach, reuse existing infrastructure
- **Parallel reviews**: code-reviewer + architect-reviewer validated approach
- **Comparison**: Human-AI collaborative planning vs spec-driven (/speckit.tasks)
- **Result**: MVP-optimized plan chosen (50% less code than full-featured)

### Key Contributors
- **Architecture**: Designed PostgreSQL-native approach with simplified schema
- **Planning**: Created MVP task breakdown with time estimates
- **Optimization**: Reduced from 18 columns to 10, 12 hours to 6 hours

---

## How to Use This Document

### Quick Start (10 minutes)
1. **Read sections 1-6** for context (Executive Summary → Critical Context)
2. **Review section 7** for code patterns (Key Design Patterns)
3. **Start T001** using section 11 as checklist (Quick Reference)
4. **Reference sections 8-10** during implementation (as needed)

### During Implementation
- **Stuck on a task?** → Check "Key Design Patterns" section
- **Need schema details?** → Check "Database Schema (Reference)" section
- **Confused about scope?** → Check "Critical Context - MVP Scope" section
- **Want to verify completion?** → Check "Success Criteria" section

### Before Committing
- **Run tests**: `pytest tests/integration/test_background_indexing.py -v`
- **Check constitutional compliance**: Review "Constitutional Compliance Checklist"
- **Update documentation**: Ensure CLAUDE.md has usage examples

---

## Next Session Prompt

**Suggested prompt for next AI session**:

```
I'm implementing background indexing for the codebase-mcp project. Please read:
1. docs/IMPLEMENTATION_HANDOFF.md (handoff context)
2. docs/architecture/background-indexing-tasks-mvp.md (task list)

I want to start with T001 (database migration). Let's create the Alembic migration
for the indexing_jobs table following the MVP specification.

Key requirements:
- 10 columns only (simplified schema)
- 2 indexes for performance
- Status CHECK constraint
- Follow existing migration patterns in migrations/versions/
```

---

## Appendix A: File Creation Checklist

**Files to Create** (6 new files):
- [ ] `migrations/versions/008_add_indexing_jobs.py` (T001)
- [ ] `src/models/indexing_job.py` (T003)
- [ ] `src/services/background_worker.py` (T004)
- [ ] `src/mcp/tools/background_indexing.py` (T005)
- [ ] `tests/unit/test_indexing_job_models.py` (T003-test)
- [ ] `tests/integration/test_background_indexing.py` (T008)

**Files to Modify** (2 existing files):
- [ ] `src/models/__init__.py` - Export IndexingJob model
- [ ] `.env.example` - Add background indexing config

**Total Lines**: ~1,200-1,500 (50% less than full plan)

---

## Appendix B: Environment Variables

Add to `.env.example` (T011):

```bash
# Background Indexing Configuration
# Maximum number of concurrent background indexing jobs
MAX_CONCURRENT_INDEXING_JOBS=2

# Timeout per indexing job (seconds) - 1 hour default
INDEXING_JOB_TIMEOUT_SECONDS=3600
```

**Note**: MVP doesn't enforce these limits yet, but documents them for Phase 2.

---

## Appendix C: Documentation Updates

Add to `CLAUDE.md` (T012):

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

---

## Appendix D: Testing Checklist

### Unit Tests (T003-test)
- [ ] Valid absolute path accepted
- [ ] Relative path rejected
- [ ] Path traversal rejected (`../../etc/passwd`)
- [ ] Model serialization works

### Integration Tests (T008)
- [ ] Job creation works
- [ ] Status polling works
- [ ] Job completes successfully
- [ ] Counters accurate (files_indexed, chunks_created)

### State Persistence (T010)
- [ ] Job survives server restart
- [ ] Status queryable after restart
- [ ] All fields preserved

### End-to-End (T013)
- [ ] Index large repo (1,000+ files)
- [ ] No timeout errors
- [ ] Completes within 5 minutes
- [ ] Status tracking accurate

---

**End of Handoff Document**

This document provides complete context to start implementation immediately without requiring the previous conversation history. Good luck! 🚀
