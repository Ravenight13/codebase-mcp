# Project Resolution Bug Fix - Summary

**Branch:** `fix/project-resolution-auto-create`
**Date:** 2025-10-17
**Status:** ⚠️ **PARTIAL FIX** - Core integration complete, secondary resolution issue remains

## Problem Statement

All indexing operations were using the "default" database (`cb_proj_default_00000000`) instead of project-specific databases specified in `.codebase-mcp/config.json` files.

**Root Cause:** Two separate systems (persistent registry database and in-memory registry with auto-create) were not integrated, causing all resolution tiers to fail and fallback to "default".

## Changes Made

### 1. Tier 2 Resolution Fix (✅ COMPLETE)
**File:** `src/database/session.py` (lines 383-431)

**Before:** Queried persistent registry database, returned None if not found
**After:** Calls `get_or_create_project_from_config()` to auto-create projects from config files

**Impact:**
- Projects are now auto-created when `.codebase-mcp/config.json` exists
- Config files are updated with `project.id` if missing
- Uses in-memory registry for project tracking

### 2. Tier 1 Resolution Fix (✅ COMPLETE)
**File:** `src/database/session.py` (lines 523-552)

**Before:** Early return to "default" when explicit project_id not found
**After:** Allows fallthrough to Tier 2/3/4 for graceful degradation

**Impact:**
- Better resolution chain behavior
- No premature defaulting
- Enables config-based resolution as fallback

### 3. Test Coverage (✅ ADDED)
**New File:** `tests/integration/test_config_based_project_creation.py`

**Tests Added:**
1. `test_project_auto_creation_from_config` - Verify auto-creation works
2. `test_existing_project_id_in_config` - Verify existing IDs are preserved
3. `test_fallback_to_default_without_config` - Verify graceful degradation
4. `test_search_uses_correct_project_database` - End-to-end workflow validation

## Test Results

```bash
pytest tests/integration/test_config_based_project_creation.py -v
```

**Results:**
- ✅ 1/4 tests passing (`test_fallback_to_default_without_config`)
- ❌ 3/4 tests failing (auto-creation tests)

**Failure Reason:**
Second resolution call (from `get_session()`) still falls back to default database. Auto-create DOES work on first call but subsequent calls fail.

## Known Issues

### Issue: Secondary Resolution Falls Back to Default

**Symptom:**
```
INFO: Auto-created project: cb_proj_test_auto_create_202add49
INFO: Explicit project_id not found in registry: 202add49..., trying other methods
INFO: Creating new pool for database: cb_proj_default_00000000  # ❌ Wrong!
```

**Root Cause (Hypothesis):**
When `get_session(project_id="202add49...")` is called, it invokes `resolve_project_id(explicit_id="202add49...")` again. This:
1. Tier 1: Looks in persistent registry → NOT FOUND → fallthroughs ✅
2. Tier 2: Should call `_resolve_project_context(ctx)` → but appears to fail
3. Falls back to Tier 4: "default"

**Possible Causes:**
1. Exception in `_resolve_project_context()` being silently swallowed (line 572-573)
2. Context not being passed correctly in test mocks
3. In-memory registry not persisting between calls
4. Config path resolution failing on second call

**Next Steps:**
1. Add debug logging to `_resolve_project_context()` to trace execution
2. Verify Context is properly passed through call chain
3. Check if in-memory registry is singleton vs per-call
4. Test with real FastMCP Context instead of MagicMock

## Files Modified

| File | Lines | Change Type |
|------|-------|-------------|
| `src/database/session.py` | 383-431 | Modified (Tier 2 integration) |
| `src/database/session.py` | 523-552 | Modified (Tier 1 fallthrough) |
| `tests/integration/test_background_indexing.py` | 70-72 | Modified (comment update) |
| `tests/integration/test_config_based_project_creation.py` | NEW | Added (4 tests) |

## How to Test Manually

### Test 1: Verify Auto-Creation from Config

```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp

# Create test repository
mkdir -p /tmp/test-repo/.codebase-mcp
echo '{
  "version": "1.0",
  "project": {"name": "manual-test"},
  "auto_switch": true
}' > /tmp/test-repo/.codebase-mcp/config.json

# Create some code
echo "def hello(): pass" > /tmp/test-repo/main.py

# Start MCP server and test
# (Use mcp-cli or Claude Desktop)
```

**Expected Behavior:**
1. Project `manual-test` auto-created in in-memory registry
2. Database `cb_proj_manual_test_*` created
3. Config updated with `project.id`
4. Indexing uses project-specific database (NOT default)

**Current Behavior:**
1. ✅ Project auto-created on first call
2. ✅ Database created
3. ✅ Config updated
4. ❌ Subsequent calls fall back to default

### Test 2: Verify with workflow-mcp Project

```bash
cd /Users/cliffclarke/Claude_Code/workflow-mcp

# Config already exists at .codebase-mcp/config.json
cat .codebase-mcp/config.json
# {"project": {"name": "workflow-mcp-dev", "id": "04f99cfe-..."}}

# Use MCP tools
await set_working_directory("/Users/cliffclarke/Claude_Code/workflow-mcp", ctx)
await index_repository(repo_path="/Users/cliffclarke/Claude_Code/workflow-mcp", ctx)

# Verify correct database used
# Expected: cb_proj_workflow_mcp_dev_*
# Current: cb_proj_default_* (BUG)
```

## Success Criteria

### Core Fixes (✅ COMPLETE)
1. ✅ Tier 2 resolution calls auto-create module
2. ✅ Tier 1 allows fallthrough (no early return)
3. ✅ Auto-create module integrated into session.py
4. ✅ Tests created for validation

### Remaining Issues (⚠️ IN PROGRESS)
5. ❌ Secondary resolution works correctly
6. ❌ All integration tests passing
7. ❌ Manual verification with workflow-mcp succeeds
8. ❌ No fallback to default when config exists

## Recommendations

### Immediate Actions
1. **Add Detailed Logging:** Instrument `_resolve_project_context()` with more logging
2. **Debug Secondary Call:** Trace why second `resolve_project_id` call fails
3. **Verify Context Passing:** Ensure `ctx` is properly propagated through `get_session()`
4. **Check Registry Singleton:** Verify in-memory registry persists between calls

### Alternative Approaches
1. **Use Persistent Registry:** Sync in-memory registry to persistent database on create
2. **Cache Project Pools:** Store resolved project_id with pool to avoid re-resolution
3. **Session-Level Caching:** Cache resolved project_id per session_id

## Related Files

### Investigation Documents (in workflow-mcp)
- `CODEBASE_MCP_BUG_HANDOFF.md` - Original bug report with detailed analysis
- `PROJECT_RESOLUTION_INVESTIGATION.md` - Code flow analysis
- `FINDINGS_SUMMARY.md` - Investigation findings
- `RESOLUTION_FLOW_DIAGRAM.txt` - Visual diagram of resolution chain

### Codebase Files
- `src/database/session.py` - Project resolution logic
- `src/database/auto_create.py` - Auto-create module (in-memory registry)
- `src/database/provisioning.py` - Database provisioning
- `src/auto_switch/` - Config discovery and session management

## Git Workflow

```bash
# Current branch
git branch
# * fix/project-resolution-auto-create

# View changes
git log --oneline -1
# 158fe1b3 fix(session): integrate auto-create module for project resolution

# Continue work
# 1. Debug secondary resolution issue
# 2. Fix remaining test failures
# 3. Verify with manual testing
# 4. Push and create PR

git push -u origin fix/project-resolution-auto-create
```

## Contact

**Bug Reported By:** Claude Code session in workflow-mcp
**Fixed By:** Claude Code session in codebase-mcp
**Date:** 2025-10-17

**Status:** Core integration complete, debugging secondary resolution issue. Tests created but not all passing. Ready for continued investigation and manual testing.
