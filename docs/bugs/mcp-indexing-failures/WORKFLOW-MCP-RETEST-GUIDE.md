# workflow-mcp Re-Test Guide

**Date**: 2025-10-18
**Purpose**: Verify Bug 2 fix after codebase-mcp server restart
**Branch**: `fix/project-resolution-auto-create`

---

## Prerequisites

Before running tests in workflow-mcp:

### 1. Restart codebase-mcp Server

```bash
# Stop current server (if running)
# Restart codebase-mcp server to pick up latest code

# Verify server is running on correct branch
# Expected: fix/project-resolution-auto-create
```

### 2. Verify Server Status

```bash
# Check recent commits in codebase-mcp
git log --oneline -5

# Expected output should include:
# 972e08bf - fix(background): trigger auto-creation from captured config path (Bug 2)
# 00ca2314 - feat(background): capture config path for background worker (Bug 2)
# 68ed9fad - test(background): add failing tests for auto-creation from config (Bug 2)
```

### 3. Confirm Server is Accessible

Test that workflow-mcp can communicate with codebase-mcp MCP tools.

---

## Test 1: Bug 2 - Background Auto-Creation (CRITICAL)

### What We're Testing

**Bug 2 Fix**: Background indexing should auto-create the database from `.codebase-mcp/config.json` when indexing starts.

**Before Fix**: Database error "database cb_proj_workflow_mcp_dev_04f99cfe does not exist"
**After Fix**: Database auto-created, indexing succeeds

---

### Test Steps for workflow-mcp AI Chat

Copy and paste this EXACT prompt into workflow-mcp's AI Chat:

```
I need to test background indexing with the codebase-mcp server to verify the Bug 2 fix.

1. First, set the working directory to this repository:
   /Users/cliffclarke/Claude_Code/workflow-mcp

2. Then start background indexing for this repository:
   - repo_path: /Users/cliffclarke/Claude_Code/workflow-mcp
   - Use the config at .codebase-mcp/config.json which specifies project "workflow-mcp-dev"

3. Poll the indexing status every 5 seconds until it completes or fails.

4. Report the final status with these details:
   - job_id
   - status (should be "completed")
   - database_name (should be cb_proj_workflow_mcp_dev_04f99cfe)
   - files_indexed (should be > 0)
   - error_message (should be null)

This tests whether background indexing auto-creates the database from config.
```

---

### Expected Result

**Success Output**:
```json
{
  "job_id": "550e8400-...",
  "status": "completed",
  "files_indexed": 200,
  "chunks_created": 1500,
  "database_name": "cb_proj_workflow_mcp_dev_04f99cfe",
  "error_message": null,
  "project_id": "04f99cfe-..."
}
```

**Key Success Indicators**:
- ✅ status: "completed" (NOT "failed")
- ✅ files_indexed > 0 (actual file count from workflow-mcp repo)
- ✅ database_name: "cb_proj_workflow_mcp_dev_04f99cfe" (matches config)
- ✅ error_message: null (no "database does not exist" error)

---

### Success Criteria

- [ ] Database auto-created: `cb_proj_workflow_mcp_dev_04f99cfe`
- [ ] Indexing completed successfully
- [ ] files_indexed > 0
- [ ] status: "completed"
- [ ] No "database does not exist" error

---

### If Test Fails

**Symptom**: "database does not exist" error returns

**Possible Causes**:
1. codebase-mcp server not restarted (still running old code)
2. Server not on branch `fix/project-resolution-auto-create`
3. Config file at `/Users/cliffclarke/Claude_Code/workflow-mcp/.codebase-mcp/config.json` missing or malformed

**Debug Steps**:
```bash
# 1. Verify config file exists
cat /Users/cliffclarke/Claude_Code/workflow-mcp/.codebase-mcp/config.json

# Expected:
# {
#   "version": "1.0",
#   "project": {
#     "name": "workflow-mcp-dev",
#     "id": "04f99cfe-..."
#   },
#   "auto_switch": true
# }

# 2. Check codebase-mcp server logs for auto-creation messages
# Look for: "Auto-created/verified database from [config_path]"

# 3. Verify server picked up the fix
# Check if start_indexing_background passes config_path to worker
```

---

## Test 2: Bug 3 - Error Status Reporting (VERIFICATION)

### What We're Testing

**Bug 3 Fix**: Failed indexing jobs should report `status="failed"` (not incorrectly "completed").

**This test verifies the fix still works** (already passed once in codebase-mcp).

---

### Test Steps for workflow-mcp AI Chat

```
I need to verify that indexing errors are reported correctly.

1. Start background indexing for a NON-EXISTENT repository:
   - repo_path: /tmp/nonexistent-repo-12345
   - project_id: "test-error-status"

2. Poll the job status every 2 seconds until it reaches a terminal state.

3. Report the final status:
   - status (should be "failed", NOT "completed")
   - error_message (should contain error details)
   - files_indexed (should be 0)

This verifies that indexing errors result in status="failed".
```

---

### Expected Result

```json
{
  "job_id": "...",
  "status": "failed",
  "error_message": "Indexing failed: [Errno 2] No such file or directory: '/tmp/nonexistent-repo-12345'",
  "files_indexed": 0,
  "chunks_created": 0
}
```

**Key Success Indicators**:
- ✅ status: "failed" (NOT "completed")
- ✅ error_message: populated with error details
- ✅ files_indexed: 0

---

### Success Criteria

- [ ] Status is "failed" (not incorrectly "completed")
- [ ] error_message is populated
- [ ] files_indexed is 0

---

## Test 3: Verify Foreground Tool Removed

### What We're Testing

**Bug 1 Context**: Foreground `index_repository` tool had response formatting issues. While the tool itself is now fixed, we want to verify that only background indexing is available through MCP (foreground indexing is deprecated).

---

### Test Steps for workflow-mcp AI Chat

```
List all MCP tools available from the codebase-mcp server and verify which indexing tools are present.

Specifically check:
1. Is "start_indexing_background" available?
2. Is "get_indexing_status" available?
3. Is "index_repository" (foreground) available or removed?

Report the list of indexing-related tools.
```

---

### Expected Result

**Available Tools**:
- ✅ `mcp__codebase-mcp__start_indexing_background` - Present
- ✅ `mcp__codebase-mcp__get_indexing_status` - Present
- ✅ `mcp__codebase-mcp__index_repository` - **PRESENT** (Bug 1 fixed, tool works now)
- ✅ `mcp__codebase-mcp__search_code` - Present
- ✅ `mcp__codebase-mcp__set_working_directory` - Present

**Note**: The foreground `index_repository` tool is NOT removed - it was fixed in Bug 1. Background indexing is preferred for large repositories, but foreground indexing is still available for small repositories and synchronous use cases.

---

### Success Criteria

- [ ] start_indexing_background: Present ✅
- [ ] get_indexing_status: Present ✅
- [ ] index_repository: Present (fixed, not removed) ✅

---

## Troubleshooting

### If Bug 2 Still Fails

**Symptom**: "database does not exist" error persists

**Step 1**: Check codebase-mcp server logs
```bash
# Look for these log messages:
# - "Resolved config path: /Users/cliffclarke/Claude_Code/workflow-mcp/.codebase-mcp/config.json"
# - "Auto-created/verified database from [config_path]"

# If NOT present, server may not be running latest code
```

**Step 2**: Verify fix is deployed
```bash
# In codebase-mcp repo
git log --oneline -1 src/mcp/tools/background_indexing.py
# Should show: 972e08bf fix(background): trigger auto-creation from captured config path

git log --oneline -1 src/services/background_worker.py
# Should show: 972e08bf fix(background): trigger auto-creation from captured config path
```

**Step 3**: Check config file format
```bash
cat /Users/cliffclarke/Claude_Code/workflow-mcp/.codebase-mcp/config.json | jq .

# Required fields:
# - project.name (string)
# - project.id (UUID, optional but recommended)
# - version: "1.0"
```

**Step 4**: Test with minimal repo
```bash
# Create a test repository with config
mkdir -p /tmp/test-indexing/.codebase-mcp
echo '{
  "version": "1.0",
  "project": {"name": "test-minimal"},
  "auto_switch": true
}' > /tmp/test-indexing/.codebase-mcp/config.json

echo "def hello(): pass" > /tmp/test-indexing/main.py

# Then test indexing in workflow-mcp:
# start_indexing_background(repo_path="/tmp/test-indexing")
# Expected: Database cb_proj_test_minimal_* auto-created
```

---

### If Server Not Responding

**Symptom**: MCP tools timeout or return errors

**Restart Procedure**:
```bash
# 1. Stop codebase-mcp server (method depends on how it's running)
# 2. Verify no stale processes
# 3. Restart server with latest code on branch fix/project-resolution-auto-create
# 4. Test with simple MCP call: set_working_directory
```

---

### If Bug 3 Regression

**Symptom**: Error jobs show status="completed" instead of "failed"

**This would indicate the fix was lost** (highly unlikely if server is on correct branch).

**Check**:
```bash
# Verify Bug 3 fix is present
git log --oneline -1 src/services/background_worker.py
# Should show: f70791d7 fix(background): check IndexResult.status before marking job completed

# Check for status check code
grep -A 5 'if result.status == "failed"' src/services/background_worker.py
# Should show the error handling block
```

---

## Success Summary

All tests pass when:

- [ ] **Bug 2**: Background auto-creation works
  - Database `cb_proj_workflow_mcp_dev_04f99cfe` created automatically
  - Indexing completes successfully
  - No "database does not exist" error

- [ ] **Bug 3**: Error status correct (re-verified)
  - Failed jobs show status="failed"
  - error_message populated

- [ ] **Foreground Tool**: index_repository present and working
  - Tool available in MCP tool list
  - Bug 1 fix verified (returns JSON responses)

---

## Report Template

After completing all tests, report results using this format:

```markdown
# codebase-mcp Bug Fix Verification - workflow-mcp Testing

**Date**: [DATE]
**Tester**: workflow-mcp AI Chat
**Server Branch**: fix/project-resolution-auto-create

## Test Results

### Bug 2: Background Auto-Creation
- Status: ✅ PASS / ❌ FAIL
- Database Created: [database_name]
- Files Indexed: [count]
- Error Message: [null or error text]
- Notes: [any observations]

### Bug 3: Error Status (Re-verification)
- Status: ✅ PASS / ❌ FAIL
- Failed Job Status: [completed or failed]
- Error Message Present: [yes/no]
- Notes: [any observations]

### Foreground Tool Availability
- start_indexing_background: ✅ Present / ❌ Missing
- get_indexing_status: ✅ Present / ❌ Missing
- index_repository: ✅ Present / ❌ Missing
- Notes: [any observations]

## Overall Status

- [ ] All tests passed - Ready for production
- [ ] Some tests failed - See notes above
- [ ] Server issues - Needs restart/debugging

## Recommendations

[Next steps based on test results]
```

---

## Additional Verification (Optional)

If all tests pass, you can perform additional confidence checks:

### Test 4: Search After Background Indexing

After Test 1 completes successfully, verify search works:

```
Search the workflow-mcp codebase that was just indexed for:
"FastMCP server implementation"

Use the codebase-mcp search_code tool with:
- query: "FastMCP server implementation"
- limit: 5

Report the top 3 results with similarity scores.
```

**Expected**:
- Results from workflow-mcp code (not other projects)
- Similarity scores > 0.7
- Relevant files (server.py, main.py, etc.)

---

### Test 5: Re-Indexing (Idempotency)

Test that re-indexing the same repository works:

```
Start background indexing again for:
- repo_path: /Users/cliffclarke/Claude_Code/workflow-mcp

This should:
1. Skip re-creating the database (already exists)
2. Update the index with any new files
3. Complete successfully

Report if any errors occur.
```

**Expected**:
- No "database already exists" error
- Indexing completes successfully
- files_indexed reflects current repo state

---

## Completion Checklist

Before reporting success, verify:

- [ ] codebase-mcp server restarted on correct branch
- [ ] All 3 core tests passed (Bug 2, Bug 3, Tool availability)
- [ ] Database auto-created with correct name
- [ ] No "database does not exist" errors
- [ ] Error status reporting works correctly
- [ ] Results reported in template format above

---

## References

**Bug Documentation**:
- Bug 2 Fix: `/docs/bugs/mcp-indexing-failures/bug2-background-auto-create-plan.md`
- Bug 3 Fix: `/docs/bugs/mcp-indexing-failures/bug3-error-status-plan.md`
- Completion Summary: `/docs/bugs/mcp-indexing-failures/COMPLETION-SUMMARY.md`

**Relevant Commits**:
- Bug 2: `972e08bf`, `00ca2314`, `68ed9fad`
- Bug 3: `f70791d7`, `39d36d28`

---

**End of Re-Test Guide**

**Last Updated**: 2025-10-18
**Status**: Ready for workflow-mcp testing
