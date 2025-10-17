# Test Prompt: Index workflow-mcp Project with Background Indexing

**Purpose**: Test background indexing with a real medium-sized codebase (workflow-mcp)

**Branch**: `015-background-indexing-mvp` (on codebase-mcp)

---

## Copy This Prompt for workflow-mcp Chat

```
I want to test the background indexing feature from the codebase-mcp project by indexing the entire workflow-mcp codebase.

**Setup**:
- The codebase-mcp MCP server should be running with branch: 015-background-indexing-mvp
- I want to index the workflow-mcp project located at: /Users/cliffclarke/Claude_Code/workflow-mcp
- This will test background indexing with a real medium-sized Python project

**Steps**:

1. **Start Background Indexing**:
   - Use the codebase-mcp tool: start_indexing_background()
   - Repository path: /Users/cliffclarke/Claude_Code/workflow-mcp
   - Project ID: "workflow-mcp-test"
   - Save the returned job_id

2. **Monitor Progress**:
   - Poll status every 5 seconds using: get_indexing_status(job_id)
   - Show me each status update with:
     - Current status (pending/running/completed/failed)
     - Files indexed so far
     - Chunks created so far
     - Elapsed time
   - Continue until status is "completed" or "failed"

3. **Report Results**:
   When complete, show me:
   - Total files indexed
   - Total chunks created
   - Total duration (from started_at to completed_at)
   - Any errors encountered
   - Average indexing speed (files per second)

**Expected Results**:
- workflow-mcp has approximately 50-100 Python files
- Should complete in 1-3 minutes
- Should create 500-2000 chunks depending on code complexity
- No timeout errors (background indexing should handle the duration)

**What I'm Testing**:
✅ Background indexing works with real medium-sized project
✅ No MCP timeout errors (job runs in background)
✅ Status polling provides accurate progress updates
✅ State transitions correctly (pending → running → completed)
✅ Metrics are accurate for real codebase
✅ Cross-project indexing works (codebase-mcp indexing workflow-mcp)

Please execute this test and show me detailed progress updates every 5 seconds until completion.
```

---

## Alternative: Minimal Prompt

If you want a shorter version:

```
Use codebase-mcp's background indexing to index the workflow-mcp project:

1. Start: start_indexing_background(repo_path="/Users/cliffclarke/Claude_Code/workflow-mcp", project_id="workflow-mcp-test")
2. Poll every 5s: get_indexing_status(job_id) until status="completed"
3. Show: status updates, final metrics (files, chunks, duration)

Expected: 50-100 files, 1-3 minutes, no timeout errors.
```

---

## What to Look For

### Success Indicators ✅
- Job creates immediately (<1 second)
- Status transitions: `pending` → `running` → `completed`
- Files indexed: 50-100 (actual count from workflow-mcp)
- Chunks created: 500-2,000 (depends on code size)
- Duration: 1-3 minutes (no timeout!)
- No errors in error_message field

### Potential Issues ⚠️
- **Job stuck in "pending"**: Worker may not have started
- **Job fails quickly**: Path might be wrong, check repo_path
- **Very slow progress**: Normal for first-time indexing with embeddings
- **Timeout error**: Should NOT happen (that's what we're testing!)

---

## Expected Output Pattern

```
Starting background indexing...
✅ Job created: a7f3b2c1-4d5e-6f7a-8b9c-0d1e2f3a4b5c

Polling status every 5 seconds...

[0s] Status: pending
     Files: 0, Chunks: 0

[5s] Status: running
     Files: 12, Chunks: 156
     Progress: ~12 files/5s = 2.4 files/sec

[10s] Status: running
      Files: 28, Chunks: 374
      Progress: ~16 files/5s = 3.2 files/sec

[15s] Status: running
      Files: 45, Chunks: 628
      Progress: ~17 files/5s = 3.4 files/sec

[20s] Status: running
      Files: 63, Chunks: 891
      Progress: ~18 files/5s = 3.6 files/sec

[25s] Status: completed ✅
      Files: 78, Chunks: 1,142
      Duration: 25.3 seconds

Final Results:
✅ Successfully indexed workflow-mcp codebase
   - Files indexed: 78
   - Chunks created: 1,142
   - Duration: 25.3s
   - Average speed: 3.1 files/second
   - Status: completed
   - Errors: None
```

---

## Validation Checklist

After the test completes, verify:

- [ ] Job created in <1 second ✓
- [ ] No MCP client timeout (job ran in background) ✓
- [ ] Status transitioned correctly (pending → running → completed) ✓
- [ ] Files indexed matches workflow-mcp file count ✓
- [ ] Chunks created is reasonable (10-20 chunks per file) ✓
- [ ] Duration is reasonable (1-3 minutes for ~100 files) ✓
- [ ] No errors in error_message field ✓
- [ ] All timestamps populated (created_at, started_at, completed_at) ✓
- [ ] Can query the indexed data with semantic search ✓

---

## Follow-Up Test (Optional)

After indexing completes, test semantic search on the indexed workflow-mcp code:

```
Now that workflow-mcp is indexed, test semantic search:

Search for: "database session management"
Expected: Should find results from workflow-mcp code about database sessions

Search for: "MCP tool registration"
Expected: Should find workflow-mcp MCP tool implementation code

This validates that:
1. Background indexing completed successfully
2. The indexed data is searchable
3. Semantic search works across the indexed codebase
```

---

## Troubleshooting

### "Repository not found" error
**Fix**: Verify the path is correct:
```bash
ls -la /Users/cliffclarke/Claude_Code/workflow-mcp
# Should show workflow-mcp project files
```

### Job stays in "pending" forever
**Fix**: Check codebase-mcp server logs for worker errors

### "Table indexing_jobs does not exist"
**Fix**: Ensure codebase-mcp is on branch `015-background-indexing-mvp` and migration is applied:
```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp
git checkout 015-background-indexing-mvp
alembic upgrade head
```

### Very slow indexing (>5 minutes)
**Possible causes**:
- First-time embedding generation (normal)
- Large files taking time to process
- Database write contention

---

## Success Criteria

For this test to be considered successful:

1. ✅ **No Timeout**: Job completes without MCP client timeout (proves background processing works)
2. ✅ **Accurate Metrics**: Files indexed matches actual workflow-mcp file count
3. ✅ **Reasonable Speed**: 1-5 files/second (accounting for embedding generation)
4. ✅ **State Management**: Clean transitions through pending → running → completed
5. ✅ **No Errors**: error_message field is null
6. ✅ **Searchable**: Can search the indexed workflow-mcp code afterward

If all criteria met: **Background Indexing MVP validated with real-world project! 🎉**
