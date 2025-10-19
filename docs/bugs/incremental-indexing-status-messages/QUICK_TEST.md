# Quick Test Reference Card

## After Server Restart

### Test 1: No Changes (5 sec)
```python
job = await mcp__codebase_mcp__start_indexing_background(
    repo_path="/Users/cliffclarke/Claude_Code/workflow-mcp"
)
# Wait 3 sec
status = await mcp__codebase_mcp__get_indexing_status(job_id=job["job_id"])
print(status["status_message"])
# Expected: "Repository up to date - no file changes detected..."
```

### Test 2: Incremental (10 sec)
```bash
touch /Users/cliffclarke/Claude_Code/workflow-mcp/README.md
```
```python
job = await mcp__codebase_mcp__start_indexing_background(
    repo_path="/Users/cliffclarke/Claude_Code/workflow-mcp"
)
# Wait 3 sec
status = await mcp__codebase_mcp__get_indexing_status(job_id=job["job_id"])
print(status["status_message"])
# Expected: "Incremental update completed: 1 files updated"
```

### Test 3: Full Index (15 sec)
```python
job = await mcp__codebase_mcp__start_indexing_background(
    repo_path="/Users/cliffclarke/Claude_Code/codebase-mcp"
)
# Wait 10 sec
status = await mcp__codebase_mcp__get_indexing_status(job_id=job["job_id"])
print(status["status_message"])
# Expected: "Full repository index completed: 87 files, 450 chunks"
```

## Or Run Automated Test
```bash
python test_status_message.py
```

## Check Database Directly
```bash
./verify_status_message_db.sh
```

## Success Criteria
- ✅ All 3 tests return `status_message` field
- ✅ All messages are non-null
- ✅ Messages match expected patterns
