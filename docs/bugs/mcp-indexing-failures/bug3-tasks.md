# Bug 3 Tasks: Background Error Status Reporting

**Bug Summary**: Background indexing jobs incorrectly report `status="completed"` when indexing fails due to database errors, despite logging critical errors. The worker does not check `IndexResult.status` before marking the job as completed.

**Root Cause**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/background_worker.py:135-152` - Worker assumes success if no exception is raised, but `index_repository()` returns `IndexResult` with `status="failed"` instead of raising exceptions.

**Fix Strategy**: Implement Option A (minimal change) - Check `IndexResult.status` after indexing and set job status accordingly. Option B (database pre-validation) deferred as complementary enhancement.

---

## Task Breakdown

### Phase 1: Code Analysis & Test Infrastructure (TDD Setup)

#### T3.1: Analyze current error handling flow
- **Acceptance Criteria**:
  - Document current code flow in lines 127-162 of `background_worker.py`
  - Identify exact insertion point for status check (after line 133)
  - Confirm `IndexResult` model has `status` and `errors` fields
  - Verify `update_job()` accepts `error_message` parameter
- **Files Analyzed**:
  - `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/background_worker.py:83-218`
  - `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/indexer.py:881-908` (IndexResult return)
  - `/Users/cliffclarke/Claude_Code/codebase-mcp/src/models/indexing_job.py` (verify error_message column)
- **Commit**: No (analysis only)
- **Duration**: 20 minutes

#### T3.2: Create unit test file and test fixtures
- **Acceptance Criteria**:
  - Create `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/services/test_background_worker.py`
  - Add imports: `pytest`, `AsyncMock`, `patch`, `uuid4`, `IndexResult`, `_background_indexing_worker`
  - Create fixture for mock `IndexResult` with `status="failed"`, `errors=["Database error: ..."]`
  - Create fixture for mock `update_job` call tracker
  - File structure matches existing test patterns (docstrings, type hints)
- **Files Created**:
  - `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/services/test_background_worker.py` (~50 lines)
- **Commit**: `test(background): add unit test fixtures for worker error handling`
- **Duration**: 30 minutes

---

### Phase 2: Test-Driven Development (RED Phase)

#### T3.3: Write failing unit test for IndexResult.status="failed"
- **Acceptance Criteria**:
  - Test name: `test_worker_respects_failed_index_result`
  - Mock `index_repository` to return `IndexResult(status="failed", errors=["Database error: ..."])`
  - Mock `get_session`, `update_job` to track calls
  - Assert `update_job` called with `status="failed"` and `error_message` containing "Database error"
  - Test FAILS (RED) - worker currently marks as "completed"
  - Run test: `pytest tests/unit/services/test_background_worker.py::test_worker_respects_failed_index_result -v`
- **Files Modified**:
  - `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/services/test_background_worker.py` (+30 lines)
- **Expected Output**: Test fails with assertion error showing `status="completed"` instead of `"failed"`
- **Commit**: `test(background): add failing test for IndexResult.status check (RED)`
- **Duration**: 45 minutes

#### T3.4: Write failing integration test for database-not-found scenario
- **Acceptance Criteria**:
  - Create `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/integration/test_background_indexing_errors.py`
  - Test name: `test_background_indexing_database_not_found`
  - Create job in registry database with non-existent `project_id` (e.g., `"fake-proj-xyz-12345"`)
  - Call `_background_indexing_worker()` with fake project_id
  - Query job status from registry database
  - Assert `status="failed"`, `error_message IS NOT NULL`, `files_indexed=0`
  - Test FAILS (RED) - worker currently marks as "completed"
  - Run test: `pytest tests/integration/test_background_indexing_errors.py::test_background_indexing_database_not_found -v`
- **Files Created**:
  - `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/integration/test_background_indexing_errors.py` (~80 lines)
- **Expected Output**: Test fails with assertion showing `status="completed"`, `error_message=NULL`
- **Commit**: `test(background): add failing integration test for db errors (RED)`
- **Duration**: 1 hour

---

### Phase 3: Implementation (GREEN Phase)

#### T3.5: Implement IndexResult.status check in background worker
- **Acceptance Criteria**:
  - Insert status check after line 133 in `background_worker.py`
  - Add conditional block: `if result.status == "failed":`
  - Extract error message: `error_message = result.errors[0] if result.errors else "Unknown indexing error"`
  - Add structured logging with context (job_id, error, errors_count)
  - Call `update_job(job_id, status="failed", error_message=..., completed_at=datetime.now())`
  - Add early return to skip "completed" update
  - Move path validation checks (lines 136-143) AFTER status check for clarity
  - Update success log message (line 154-162) - only reached if status != "failed"
  - Unit test PASSES (GREEN)
  - Integration test PASSES (GREEN)
- **Files Modified**:
  - `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/background_worker.py:135-162` (~25 lines changed)
- **Lines Changed**:
  - Production code: ~25 lines (insert 18 new, reorder 7 existing)
  - Net addition: +18 lines
- **Expected Test Results**:
  - `test_worker_respects_failed_index_result`: PASS
  - `test_background_indexing_database_not_found`: PASS
- **Commit**: `fix(background): check IndexResult.status before marking job completed`
- **Duration**: 45 minutes

---

### Phase 4: Validation & Documentation

#### T3.6: Add unit test for successful indexing (ensure no regression)
- **Acceptance Criteria**:
  - Test name: `test_worker_completes_successful_indexing`
  - Mock `index_repository` to return `IndexResult(status="success", files_indexed=100, chunks_created=500)`
  - Assert `update_job` called with `status="completed"`, `files_indexed=100`, `chunks_created=500`
  - Verify `error_message` NOT set in final update call
  - Test PASSES (GREEN)
- **Files Modified**:
  - `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/services/test_background_worker.py` (+25 lines)
- **Commit**: `test(background): add regression test for successful indexing`
- **Duration**: 30 minutes

#### T3.7: Manual reproduction test with Claude Code session
- **Acceptance Criteria**:
  - Run manual test script from bug3-error-status-plan.md (lines 332-357)
  - Start PostgreSQL: `docker-compose up -d postgres`
  - Create indexing job with non-existent database using Python REPL
  - Query job status: `SELECT status, error_message, files_indexed FROM indexing_jobs ORDER BY created_at DESC LIMIT 1;`
  - Verify: `status='failed'`, `error_message` contains "database ... does not exist", `files_indexed=0`
  - Compare with original bug behavior (status='completed', error_message=NULL)
  - Document results in test execution notes
- **Files Modified**: None (manual test only)
- **Commit**: No
- **Duration**: 20 minutes

#### T3.8: Update observability metrics (optional monitoring enhancement)
- **Acceptance Criteria**:
  - Add log metric counter for `status="failed"` jobs (increment on line ~142)
  - Add log warning for `status="completed" AND files_indexed=0` (defensive check)
  - Verify structured logging includes all context fields: `job_id`, `error`, `errors_count`, `project_id`
  - Check logs during integration test run for correct structured output
- **Files Modified**:
  - `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/background_worker.py:140-145` (~5 lines enhanced)
- **Commit**: `chore(background): enhance structured logging for error metrics`
- **Duration**: 20 minutes

#### T3.9: Run full background indexing test suite
- **Acceptance Criteria**:
  - Run all unit tests: `pytest tests/unit/services/test_background_worker.py -v`
  - Run all integration tests: `pytest tests/integration/test_background_indexing*.py -v`
  - Verify all existing tests still pass (no regressions)
  - Check test coverage for `background_worker.py`: `pytest --cov=src.services.background_worker tests/ -v`
  - Target coverage: >85% for error handling paths
- **Files Modified**: None (validation only)
- **Commit**: No
- **Duration**: 15 minutes

---

## Micro-Commit Strategy

| Commit # | Task | Message | Lines Changed |
|----------|------|---------|---------------|
| 1 | T3.2 | `test(background): add unit test fixtures for worker error handling` | +50 (test) |
| 2 | T3.3 | `test(background): add failing test for IndexResult.status check (RED)` | +30 (test) |
| 3 | T3.4 | `test(background): add failing integration test for db errors (RED)` | +80 (test) |
| 4 | T3.5 | `fix(background): check IndexResult.status before marking job completed` | +25 (prod), passes all tests |
| 5 | T3.6 | `test(background): add regression test for successful indexing` | +25 (test) |
| 6 | T3.8 | `chore(background): enhance structured logging for error metrics` | +5 (prod) |

**Total Commits**: 6 (TDD: 3 test commits, 2 fix commits, 1 enhancement)

---

## Code Change Summary

### Production Code Changes
**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/background_worker.py`

**Before** (lines 135-152):
```python
# 3. Check if indexing succeeded (files_indexed > 0 or path exists check)
repo_path_obj = Path(repo_path)
if not repo_path_obj.exists():
    raise FileNotFoundError(f"Repository path does not exist: {repo_path}")

if not repo_path_obj.is_dir():
    raise NotADirectoryError(f"Repository path is not a directory: {repo_path}")

# 4. Update to completed with results
await update_job(
    job_id=job_id,
    status="completed",  # ❌ BUG: Always sets completed
    files_indexed=result.files_indexed,
    chunks_created=result.chunks_created,
    completed_at=datetime.now(),
)
```

**After** (lines 135-170, +18 lines):
```python
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

**Net Change**: +18 lines production code, +160 lines test code

---

## Test File Locations

### Unit Tests
**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/unit/services/test_background_worker.py` (NEW)
- `test_worker_respects_failed_index_result` - Verifies status check logic
- `test_worker_completes_successful_indexing` - Regression test for success path

### Integration Tests
**File**: `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/integration/test_background_indexing_errors.py` (NEW)
- `test_background_indexing_database_not_found` - End-to-end database error scenario

---

## Success Criteria Checklist

- [ ] **T3.3**: Unit test fails (RED) - worker marks failed indexing as "completed"
- [ ] **T3.4**: Integration test fails (RED) - database error shows status="completed"
- [ ] **T3.5**: Unit test passes (GREEN) - worker checks `result.status` and updates job
- [ ] **T3.5**: Integration test passes (GREEN) - database error shows status="failed" with error message
- [ ] **T3.6**: Regression test passes - successful indexing still marks as "completed"
- [ ] **T3.7**: Manual reproduction test shows `status="failed"` with populated `error_message`
- [ ] **T3.9**: All existing background indexing tests pass (no regressions)
- [ ] **Production Metrics** (post-deployment):
  - Zero jobs with `status="completed" AND files_indexed=0 AND error_message IS NULL`
  - `status="failed"` count increases (previously hidden errors now reported)
  - Log consistency: ERROR logs match `status="failed"` in database

---

## Risk Assessment

### Low Risk - Minimal Code Change
- **Scope**: 18-line insertion in single function (`_background_indexing_worker`)
- **Blast Radius**: Only affects background indexing jobs (foreground `index_repository` MCP tool unaffected)
- **Backward Compatibility**: No API changes, no database schema changes, existing jobs unaffected
- **Failure Mode**: If status check logic has bug, existing exception handlers still catch errors
- **Rollback**: Single `git revert` restores original behavior

### No Database Migration Required
- `error_message` column already exists in `indexing_jobs` table
- No schema changes needed
- No data backfill required

---

## Time Estimate

| Phase | Tasks | Duration |
|-------|-------|----------|
| Phase 1: Analysis & Setup | T3.1-T3.2 | 50 minutes |
| Phase 2: TDD (RED) | T3.3-T3.4 | 1h 45m |
| Phase 3: Implementation (GREEN) | T3.5 | 45 minutes |
| Phase 4: Validation | T3.6-T3.9 | 1h 25m |
| **Total** | **9 tasks** | **~4.5 hours** |

**Breakdown by Type**:
- Analysis: 20 minutes
- Test Infrastructure: 2h 45m (TDD setup + RED + GREEN validation)
- Implementation: 45 minutes (minimal code change)
- Validation & Documentation: 1h 25m

---

## Dependencies

### Prerequisites
- PostgreSQL running: `docker-compose up -d postgres`
- Existing integration test database setup
- Pytest fixtures for async testing (`pytest-asyncio`)

### Related Bugs
This fix is **independent** of Bug 1 (project auto-creation) and Bug 2 (session context):
- **Can be developed in parallel** - no code conflicts
- **Validates error reporting** regardless of root cause (database missing, permissions, etc.)
- **Should be deployed first** - ensures Bugs 1 & 2 failures are correctly reported

---

## Deferred Enhancements (Post-Bug Fix)

### Option B: Database Pre-Validation
- **Scope**: Add `SELECT 1` validation before calling `index_repository()`
- **Benefit**: Fail fast if database doesn't exist (saves wasted indexing work)
- **Effort**: +20 lines in `background_worker.py:118-127`
- **Status**: Deferred to separate task (complementary to Option A, not required)

### Observability Dashboard
- **Scope**: Prometheus metrics for `failed_jobs_total`, `completed_jobs_zero_files_total`
- **Benefit**: Real-time alerting on error rate increases
- **Effort**: ~2 hours (metrics service integration)
- **Status**: Deferred to Phase 06 observability work

---

## Notes

1. **TDD Approach**: Tests written BEFORE implementation (T3.3-T3.4 fail, then T3.5 makes them pass)
2. **Minimal Change Philosophy**: Only modify `background_worker.py`, no changes to `indexer.py` or database schema
3. **Constitutional Compliance**:
   - Principle I: Simplicity (18-line fix, reuses existing infrastructure)
   - Principle V: Production Quality (comprehensive error handling, structured logging)
   - Principle VII: TDD (tests before code, RED → GREEN → REFACTOR)
   - Principle VIII: Type Safety (preserves existing type annotations)
4. **Git Strategy**: Atomic commits after each phase, conventional commit messages
5. **Regression Prevention**: T3.6 ensures successful indexing still works after fix
