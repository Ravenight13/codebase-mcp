# Bug 3: Background Indexing Reports "Completed" on Error

## Symptoms
- Job fails with database error: `database "cb_proj_codebase_mcp_455c8532" does not exist`
- Job status incorrectly set to: **"completed"** (should be **"failed"**)
- Job metrics show zero work done: `files_indexed: 0`, `chunks_created: 0`
- Error message is **null** (should contain database error details)
- Logs show contradictory messages:
  - `ERROR: "Critical error during indexing: database \"cb_proj_codebase_mcp_455c8532\" does not exist"`
  - `INFO: "Job 2ebcda95-8210-43cd-8309-cf9b34d1d05d completed successfully"`

## Root Cause Analysis

### The Critical Flow Gap

The bug occurs due to a **mismatch in error handling semantics** between two components:

1. **`index_repository()` service** (`/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/indexer.py:493-908`)
   - **Catches all exceptions** and returns `IndexResult` with `status="failed"` (line 881-908)
   - **NEVER raises exceptions** - always returns a result object
   - Database errors are caught, logged, and packaged into a failed result

2. **`_background_indexing_worker()` worker** (`/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/background_worker.py:83-218`)
   - **Assumes exceptions will be raised** on failure (try/except pattern)
   - Only checks for specific exception types: `FileNotFoundError`, `NotADirectoryError`, generic `Exception`
   - **Does NOT check `IndexResult.status`** after successful return from `index_repository()`

### What Actually Happens

```python
# Worker calls indexer (line 127-133)
result = await index_repository(...)  # Returns IndexResult, NEVER raises

# Worker assumes success if no exception raised (line 136-152)
if not repo_path_obj.exists():
    raise FileNotFoundError(...)  # These checks run AFTER indexer returns

# Worker sets status to "completed" (line 146-152)
await update_job(
    job_id=job_id,
    status="completed",  # ❌ BUG: Ignores result.status = "failed"
    files_indexed=result.files_indexed,  # 0
    chunks_created=result.chunks_created,  # 0
    completed_at=datetime.now(),
)
```

### Why Database Errors Slip Through

When the project database doesn't exist:
1. `get_session(project_id)` creates an AsyncSession for the non-existent database
2. `index_repository()` calls `_get_or_create_repository()` (line 547)
3. First database operation fails with: `asyncpg.InvalidCatalogNameError: database "cb_proj_..." does not exist`
4. Exception caught by `index_repository()`'s catch-all handler (line 881-908)
5. **Returns** `IndexResult(status="failed", errors=["Critical error..."])` - **DOES NOT RAISE**
6. Worker receives this result, **ignores `status="failed"`**, and marks job as "completed"

## Code Locations

### Primary Bug Location
**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/background_worker.py`
**Lines**: 127-152

```python
# Line 127-133: Call indexer (returns IndexResult, never raises)
async with get_session(project_id=project_id, ctx=ctx) as session:
    result = await index_repository(
        repo_path=Path(repo_path),
        name=Path(repo_path).name,
        db=session,
        project_id=project_id,
    )

# Line 136-144: Path validation (happens AFTER indexer already processed)
repo_path_obj = Path(repo_path)
if not repo_path_obj.exists():
    raise FileNotFoundError(...)
if not repo_path_obj.is_dir():
    raise NotADirectoryError(...)

# Line 146-152: ❌ BUG - Unconditionally marks as "completed"
await update_job(
    job_id=job_id,
    status="completed",  # Should check result.status first!
    files_indexed=result.files_indexed,
    chunks_created=result.chunks_created,
    completed_at=datetime.now(),
)
```

### Supporting Evidence
**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/indexer.py`
**Lines**: 881-908

```python
except Exception as e:
    # Critical error - rollback transaction
    await db.rollback()

    error_msg = f"Critical error during indexing: {e}"
    errors.append(error_msg)
    logger.error(...)

    # Returns IndexResult with status="failed" - DOES NOT RAISE
    return IndexResult(
        repository_id=UUID("00000000-0000-0000-0000-000000000000"),
        files_indexed=0,
        chunks_created=0,
        duration_seconds=duration,
        status="failed",  # This status is ignored by worker!
        errors=errors,
    )
```

## Proposed Fix

### Option A: Check IndexResult Status (RECOMMENDED - Minimal Change)

**Rationale**: Respects existing architecture where `index_repository()` never raises exceptions.

**Change Location**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/background_worker.py:135-162`

```python
# 2. Run existing indexer (NO MODIFICATIONS to indexer.py!)
async with get_session(project_id=project_id, ctx=ctx) as session:
    result = await index_repository(
        repo_path=Path(repo_path),
        name=Path(repo_path).name,
        db=session,
        project_id=project_id,
    )

# 3. Check if indexing succeeded by inspecting result.status
if result.status == "failed":
    # Indexer reported failure - extract error message
    error_message = result.errors[0] if result.errors else "Unknown indexing error"

    logger.error(
        f"Indexing failed for job {job_id}",
        extra={
            "context": {
                "job_id": str(job_id),
                "error": error_message,
                "errors_count": len(result.errors),
            }
        },
    )

    await update_job(
        job_id=job_id,
        status="failed",
        error_message=error_message,
        completed_at=datetime.now(),
    )
    return  # Exit early - do not proceed to "completed" update

# 4. Path validation (defensive checks - should never fail after successful indexing)
repo_path_obj = Path(repo_path)
if not repo_path_obj.exists():
    raise FileNotFoundError(f"Repository path does not exist: {repo_path}")
if not repo_path_obj.is_dir():
    raise NotADirectoryError(f"Repository path is not a directory: {repo_path}")

# 5. Update to completed with results (only reached if result.status != "failed")
await update_job(
    job_id=job_id,
    status="completed",
    files_indexed=result.files_indexed,
    chunks_created=result.chunks_created,
    completed_at=datetime.now(),
)

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
```

### Option B: Validate Database Before Indexing (Defense in Depth)

**Rationale**: Fail fast if database doesn't exist, preventing wasted indexing work.

**Change Location**: Add validation BEFORE calling `index_repository()` in `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/background_worker.py:118-127`

```python
try:
    # 1. Update status to running
    await update_job(
        job_id=job_id,
        status="running",
        started_at=datetime.now(),
    )

    # 1.5. Validate database exists before expensive indexing operation
    try:
        async with get_session(project_id=project_id, ctx=ctx) as session:
            # Lightweight query to verify database connectivity
            await session.execute(text("SELECT 1"))
    except Exception as db_check_error:
        # Database doesn't exist or is unreachable
        error_msg = f"Database validation failed: {db_check_error}"
        logger.error(
            f"Pre-indexing database check failed for job {job_id}",
            extra={
                "context": {
                    "job_id": str(job_id),
                    "project_id": project_id,
                    "error": str(db_check_error),
                }
            },
        )

        await update_job(
            job_id=job_id,
            status="failed",
            error_message=error_msg,
            completed_at=datetime.now(),
        )
        return  # Exit early

    # 2. Run existing indexer (database validated)
    async with get_session(project_id=project_id, ctx=ctx) as session:
        result = await index_repository(...)

    # 3. Check result.status (Option A still needed!)
    if result.status == "failed":
        ...
```

**Note**: Option B is complementary to Option A, not a replacement. Both should be implemented for defense in depth.

## Testing Plan

### Unit Test: Test IndexResult Status Handling

**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/services/test_background_worker.py` (create if doesn't exist)

```python
import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from src.services.background_worker import _background_indexing_worker
from src.services.indexer import IndexResult

@pytest.mark.asyncio
async def test_worker_respects_failed_index_result():
    """Worker must check IndexResult.status and set job to failed."""
    job_id = uuid4()

    # Mock index_repository to return failed result (no exception)
    failed_result = IndexResult(
        repository_id=uuid4(),
        files_indexed=0,
        chunks_created=0,
        duration_seconds=1.0,
        status="failed",
        errors=["Database error: database does not exist"],
    )

    with patch("src.services.background_worker.index_repository", new=AsyncMock(return_value=failed_result)):
        with patch("src.services.background_worker.update_job", new=AsyncMock()) as mock_update:
            with patch("src.services.background_worker.get_session"):
                await _background_indexing_worker(
                    job_id=job_id,
                    repo_path="/fake/path",
                    project_id="test-project",
                )

    # Verify worker called update_job with status="failed"
    calls = [call.kwargs for call in mock_update.call_args_list]
    final_update = calls[-1]

    assert final_update["status"] == "failed", "Worker must set job status to 'failed' when IndexResult.status is 'failed'"
    assert "error_message" in final_update, "Worker must set error_message field"
    assert "Database error" in final_update["error_message"]
```

### Integration Test: Database Not Found Scenario

**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/integration/test_background_indexing_errors.py` (create if doesn't exist)

```python
import pytest
from uuid import uuid4
from src.services.background_worker import _background_indexing_worker
from src.database.session import get_session, engine
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.indexing_job import IndexingJob

@pytest.mark.asyncio
async def test_background_indexing_database_not_found():
    """End-to-end test: job status = 'failed' when database doesn't exist."""
    job_id = uuid4()
    fake_project_id = "nonexistent-project-db-12345"

    # Create job in main database
    async with AsyncSession(engine) as session:
        job = IndexingJob(
            id=job_id,
            repo_path="/tmp/test-repo",
            project_id=fake_project_id,
            status="pending",
        )
        session.add(job)
        await session.commit()

    # Run worker (will fail due to missing database)
    await _background_indexing_worker(
        job_id=job_id,
        repo_path="/tmp/test-repo",
        project_id=fake_project_id,
    )

    # Verify job status is "failed" (not "completed")
    async with AsyncSession(engine) as session:
        updated_job = await session.get(IndexingJob, job_id)

        assert updated_job.status == "failed", f"Expected 'failed', got '{updated_job.status}'"
        assert updated_job.error_message is not None, "error_message must be set"
        assert "database" in updated_job.error_message.lower(), "Error message should mention database issue"
        assert updated_job.files_indexed == 0
        assert updated_job.chunks_created == 0
```

### Manual Test: Reproduce Original Bug

```bash
# 1. Start PostgreSQL
docker-compose up -d postgres

# 2. Create indexing job with non-existent database
python -c "
import asyncio
from uuid import uuid4
from src.services.background_worker import _background_indexing_worker

async def test():
    job_id = uuid4()
    await _background_indexing_worker(
        job_id=job_id,
        repo_path='/Users/cliffclarke/Claude_Code/codebase-mcp',
        project_id='fake-project-xyz',
    )

asyncio.run(test())
"

# 3. Query job status (BEFORE FIX: status="completed", AFTER FIX: status="failed")
psql -h localhost -U postgres -d codebase_mcp -c \
  "SELECT status, error_message, files_indexed, chunks_created FROM indexing_jobs ORDER BY created_at DESC LIMIT 1;"
```

**Expected Results**:
- **Before Fix**: `status = 'completed'`, `error_message = NULL`, `files_indexed = 0`
- **After Fix**: `status = 'failed'`, `error_message = 'Critical error during indexing: database "cb_proj_..." does not exist'`

## Risk Assessment

### Low Risk (Option A - Recommended)
- **Scope**: 30-line change in single function (`_background_indexing_worker`)
- **Blast Radius**: Only affects background indexing jobs (foreground `index_repository` MCP tool unaffected)
- **Backward Compatibility**: No API changes, existing jobs unaffected
- **Failure Mode**: If status check logic fails, existing exception handlers still catch errors
- **Rollback**: Single git revert restores original behavior

### Medium Risk (Option B - Defense in Depth)
- **Scope**: Additional 20-line database validation block
- **Performance Impact**: Adds ~10ms pre-flight query (`SELECT 1`) before indexing
- **Network Dependency**: Requires extra database round-trip (acceptable for background job)
- **Failure Mode**: False negatives if database exists but is slow to respond (timeout needed)
- **Rollback**: Can be disabled via feature flag if causes issues

### Mitigation Strategies

1. **Incremental Rollout**:
   - Deploy Option A first (minimal change)
   - Monitor error rates for 24-48 hours
   - Add Option B if additional safety needed

2. **Observability**:
   - Add metrics for `status="failed"` job count (should increase after fix)
   - Alert on `status="completed" AND files_indexed=0` (should drop to zero)
   - Track `error_message IS NULL` count (should drop to zero)

3. **Testing Coverage**:
   - Add unit tests (fast, covers logic)
   - Add integration tests (slow, covers end-to-end flow)
   - Run manual reproduction test before/after deployment

4. **Rollback Plan**:
   - Keep original code in git history
   - Feature flag for status check (if needed): `ENABLE_INDEXRESULT_STATUS_CHECK=true`
   - Database rollback NOT required (schema unchanged)

## Success Criteria

- [ ] Unit test passes: Worker correctly handles `IndexResult.status="failed"`
- [ ] Integration test passes: Database-not-found scenario sets job status to "failed"
- [ ] Manual test passes: Reproduction scenario shows `status="failed"` and `error_message` populated
- [ ] Zero jobs with `status="completed" AND files_indexed=0 AND error_message IS NULL` after deployment
- [ ] Log messages are consistent: `ERROR` in logs matches `status="failed"` in database

## Related Issues

This bug is one of three indexing failures being tracked:
- **Bug 1**: Project auto-creation failures (database provisioning)
- **Bug 2**: Session context issues (working directory not set)
- **Bug 3**: **This bug** - Error status misreporting

Fixing Bug 3 ensures that when Bug 1 or Bug 2 occur, the job status accurately reflects the failure state.
