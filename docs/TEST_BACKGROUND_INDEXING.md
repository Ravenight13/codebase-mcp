# Test Prompt: Background Indexing MVP

**Purpose**: Test the background indexing feature in the codebase-mcp project.

**Branch**: `015-background-indexing-mvp`

---

## Copy This Prompt for Testing

```
I want to test the new background indexing feature that was just implemented.

**Context**:
- Branch: 015-background-indexing-mvp
- Feature: Background indexing for large repositories (10K+ files)
- Implementation: Complete MVP with 13 tasks finished

**What to Test**:

1. **Small Repository Test** (validates basic workflow):
   - Create a temporary test repository with 10 Python files
   - Start background indexing with `start_indexing_background()`
   - Poll status with `get_indexing_status()` until complete
   - Verify: files_indexed=10, chunks_created>0, status=completed

2. **Large Repository Test** (validates performance):
   - Index the codebase-mcp project itself (100+ files)
   - Start background indexing
   - Poll status every 5 seconds, show progress
   - Verify: completes within 5 minutes, no timeout errors

3. **Error Handling Test** (validates security):
   - Try indexing a non-existent path: `/tmp/does-not-exist-12345`
   - Verify: job fails gracefully with clear error message
   - Try relative path: `./relative/path`
   - Verify: rejected with "must be absolute" error

4. **Status Polling Test** (validates state machine):
   - Start a job and immediately query status (should be "pending" or "running")
   - Continue polling every 2 seconds
   - Log each status transition
   - Verify: pending → running → completed

**Available MCP Tools**:
- `start_indexing_background(repo_path, project_id=None, ctx=None)` → returns job_id
- `get_indexing_status(job_id, project_id=None, ctx=None)` → returns status dict

**Expected Behavior**:
- Job creation: <1 second response time
- Status queries: <100ms response time
- Small repo (10 files): completes in <30 seconds
- Large repo (100+ files): completes in 2-5 minutes
- Failed jobs: error_message field populated

**Success Criteria**:
✅ Small repository test passes
✅ Large repository test passes
✅ Error handling works correctly
✅ Status transitions correctly
✅ No timeout errors
✅ All metrics accurate (files_indexed, chunks_created)

Please run these tests and show me the results for each scenario.
```

---

## Alternative: Quick Validation Test

If you want a shorter test, use this prompt:

```
I want to quickly validate the background indexing feature on branch 015-background-indexing-mvp.

Create a test directory with 5 Python files, start a background indexing job, poll the status until complete, and verify the results.

Show me:
1. The job_id when created
2. Status updates during polling (every 2 seconds)
3. Final results (files_indexed, chunks_created, duration)
4. Any errors encountered

Use the MCP tools:
- start_indexing_background(repo_path)
- get_indexing_status(job_id)
```

---

## Manual Testing Steps (for CLI)

If you prefer to test manually:

```bash
# 1. Ensure you're on the right branch
git checkout 015-background-indexing-mvp

# 2. Run unit tests
pytest tests/unit/test_indexing_job_models.py -v

# 3. Run integration tests (fast)
pytest tests/integration/test_background_indexing.py -v -m "not slow"

# 4. Run E2E test with large repo (slow - 5-10 minutes)
pytest tests/integration/test_background_indexing.py::test_large_repository_indexing -v -s

# 5. Check all tests pass
pytest tests/unit/test_indexing_job_models.py tests/integration/test_background_indexing.py -v
```

---

## Expected Test Output

### Small Repository Test
```
✅ Job created: 550e8400-e29b-41d4-a716-446655440000
⏳ Polling status...
   Attempt 1: Status=pending, Files=0, Chunks=0
   Attempt 2: Status=running, Files=3, Chunks=15
   Attempt 3: Status=completed, Files=10, Chunks=45
✅ Test passed: Indexed 10 files, created 45 chunks in 4.2s
```

### Error Handling Test
```
✅ Job created: 660e8400-e29b-41d4-a716-446655440001
⏳ Polling status...
   Attempt 1: Status=running, Files=0, Chunks=0
   Attempt 2: Status=failed, Files=0, Chunks=0
✅ Test passed: Job failed as expected
   Error: Repository not found: /tmp/does-not-exist-12345
```

### Path Validation Test
```
❌ ValueError: repo_path must be absolute, got: ./relative/path
✅ Test passed: Path validation prevents security issues
```

---

## Troubleshooting

**Issue**: Job stays in "pending" forever
- **Cause**: Worker didn't start
- **Fix**: Check logs for worker errors, verify asyncio.create_task() called

**Issue**: Job fails immediately with "Repository not found"
- **Cause**: Path doesn't exist or isn't accessible
- **Fix**: Verify path is absolute and directory exists

**Issue**: Tests fail with "Table indexing_jobs does not exist"
- **Cause**: Migration not applied
- **Fix**: Run `alembic upgrade head`

**Issue**: Import errors for background_indexing module
- **Cause**: Not on the right branch
- **Fix**: `git checkout 015-background-indexing-mvp`

---

## Documentation References

- **Architecture**: `docs/architecture/background-indexing.md`
- **MVP Tasks**: `docs/architecture/background-indexing-tasks-mvp.md`
- **Implementation Handoff**: `docs/IMPLEMENTATION_HANDOFF.md`
- **Usage Guide**: `CLAUDE.md` (Background Indexing section)
- **Migration Validation**: `docs/migrations/008-indexing-jobs-validation.md`

---

## Post-Test Checklist

After testing, verify:
- [ ] Small repository test passed
- [ ] Large repository test passed (or ran successfully for 2+ minutes)
- [ ] Error handling works (non-existent paths fail gracefully)
- [ ] Path validation works (relative paths rejected)
- [ ] No timeout errors
- [ ] Job IDs are valid UUIDs
- [ ] Status transitions correctly (pending → running → completed)
- [ ] Metrics are accurate (files_indexed, chunks_created)
- [ ] Timestamps populated (created_at, started_at, completed_at)
- [ ] Error messages clear and actionable

If all checkboxes pass: **Background Indexing MVP is production-ready! 🎉**
