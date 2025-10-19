# Testing Guide: status_message Field

## Quick Start

After the MCP server restarts, run these tests to verify `status_message` functionality.

## Method 1: Direct MCP Tool Testing

### Scenario A: No Changes

```python
# Via Claude Code or MCP client
job = await mcp__codebase_mcp__start_indexing_background(
    repo_path="/Users/cliffclarke/Claude_Code/workflow-mcp"
)

# Wait 3-5 seconds
status = await mcp__codebase_mcp__get_indexing_status(
    job_id=job["job_id"]
)

# Check status_message
print(status["status_message"])
# Expected: "Repository up to date - no file changes detected since last index (351 files already indexed)"
```

### Scenario B: Incremental Update

```bash
# Touch a file first
touch /Users/cliffclarke/Claude_Code/workflow-mcp/README.md
```

```python
# Re-index
job = await mcp__codebase_mcp__start_indexing_background(
    repo_path="/Users/cliffclarke/Claude_Code/workflow-mcp"
)

# Wait 3-5 seconds
status = await mcp__codebase_mcp__get_indexing_status(
    job_id=job["job_id"]
)

# Check status_message
print(status["status_message"])
# Expected: "Incremental update completed: 1 files updated"
```

### Scenario C: Full Index

```python
# Index codebase-mcp
job = await mcp__codebase_mcp__start_indexing_background(
    repo_path="/Users/cliffclarke/Claude_Code/codebase-mcp"
)

# Wait 10-15 seconds (larger repo)
status = await mcp__codebase_mcp__get_indexing_status(
    job_id=job["job_id"]
)

# Check status_message
print(status["status_message"])
# Expected: "Full repository index completed: 87 files, 450 chunks"
```

## Method 2: Automated Test Script

```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp
python test_status_message.py
```

### Expected Output

```
Testing status_message field in background indexing
================================================================================

================================================================================
Scenario A: Incremental indexing - no changes
================================================================================
Job started: <uuid>

Status: completed
Status Message: Repository up to date - no file changes detected since last index (351 files already indexed)
Files Indexed: 0
Chunks Created: 0

================================================================================
Scenario B: Incremental indexing - with changes
================================================================================
Touching /Users/cliffclarke/Claude_Code/workflow-mcp/README.md...
Job started: <uuid>

Status: completed
Status Message: Incremental update completed: 1 files updated
Files Indexed: 1
Chunks Created: <number>

================================================================================
Scenario C: Full repository index
================================================================================
Job started: <uuid>

Status: completed
Status Message: Full repository index completed: 87 files, 450 chunks
Files Indexed: 87
Chunks Created: 450

================================================================================
Summary
================================================================================

Scenario A (no changes):
  status_message: Repository up to date - no file changes detected since last index (351 files already indexed)

Scenario B (incremental):
  status_message: Incremental update completed: 1 files updated

Scenario C (full index):
  status_message: Full repository index completed: 87 files, 450 chunks

================================================================================
Validation
================================================================================
✅ Scenario A: status_message present and non-null
✅ Scenario B: status_message present and non-null
✅ Scenario C: status_message present and non-null

✅ All scenarios passed!
```

## Method 3: Database Verification

```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp
./verify_status_message_db.sh
```

### Expected Output

```
Recent indexing jobs with status messages:
==========================================
                  id                  | repo_path | status | status_message | files_indexed | chunks_created
--------------------------------------+-----------+--------+----------------+---------------+----------------
<uuid> | workflow-mcp | completed | Repository up to date... | 0 | 0
<uuid> | workflow-mcp | completed | Incremental update...    | 1 | <n>
<uuid> | codebase-mcp | completed | Full repository index... | 87 | 450

Jobs with non-null status messages:
====================================
<uuid> | completed | Repository up to date - no file changes detected since last index (351 files already indexed) | 0 | 0
<uuid> | completed | Incremental update completed: 1 files updated | 1 | <n>
<uuid> | completed | Full repository index completed: 87 files, 450 chunks | 87 | 450
```

## Validation Criteria

For each test scenario, verify:

1. ✅ `status_message` field is present in response
2. ✅ `status_message` is NOT null
3. ✅ Message format matches expected pattern
4. ✅ Message accurately describes the indexing outcome

## Status Message Formats

### No Changes (Incremental)

```
"Repository up to date - no file changes detected since last index (<count> files already indexed)"
```

### Incremental Update

```
"Incremental update completed: <count> files updated"
```

### Full Index

```
"Full repository index completed: <files_count> files, <chunks_count> chunks"
```

## Troubleshooting

### Issue: status_message is null

**Cause**: Server not restarted or old code still running

**Solution**: Restart MCP server, reconnect Claude Code

### Issue: status_message field missing

**Cause**: Migration not applied

**Solution**: Run migration
```bash
DATABASE_URL=postgresql+asyncpg://localhost/codebase_mcp alembic upgrade head
```

### Issue: Empty status_message

**Cause**: Worker code not setting the field

**Solution**: Check worker code at line 220 in `background_worker.py`

## Post-Testing

After successful testing:

1. Document results in `TEST_RESULTS.md`
2. Update BUG_REPORT.md with resolution
3. Commit changes with message: `feat(indexing): expose status_message in MCP tool response`
