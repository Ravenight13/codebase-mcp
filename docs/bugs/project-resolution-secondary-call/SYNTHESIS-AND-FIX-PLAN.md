# Project Resolution Bug - Synthesis & Fix Plan

**Date:** 2025-10-17
**Status:** 🔴 **CRITICAL** - Production-breaking bug with clear fix path
**Decision:** Option B - Proper Fix (1-2 days)

---

## Executive Summary

**What's Broken:** Secondary calls to `get_session()` with an explicit `project_id` fail to find auto-created projects, causing all operations to silently fall back to the default database and breaking data isolation.

**Why It's Broken:** Dual-registry architecture with no synchronization - auto-created projects exist only in-memory while explicit lookups query the persistent PostgreSQL registry.

**How We'll Fix It:** Two-part fix: (1) Pass context to `get_session()` and (2) Persist auto-created projects to PostgreSQL registry immediately.

**Timeline:** 8-12 hours implementation + 4-6 hours testing = 1-2 days total

---

## Findings Synthesis

### What All Reviewers Agree On (100% Consensus)

All four investigators identified the **same root cause** with high confidence:

1. **Missing Context Pass (Reviewer 1, 3, 4)** - CONFIRMED
   - `indexing.py` line 172: `get_session(project_id=resolved_id)` missing `ctx` parameter
   - Causes Tier 2 resolution to fail (requires context)
   - Confidence: HIGH (code evidence clear)

2. **Registry Desync (Reviewer 1, 2, 4)** - CONFIRMED
   - Auto-created projects stored in in-memory registry only
   - Never written to persistent PostgreSQL `projects` table
   - Tier 1 lookups always fail for auto-created projects
   - Confidence: VERY HIGH (no INSERT statement exists)

3. **Architectural Flaw (All Reviewers)** - CONFIRMED
   - Dual-registry pattern creates split-brain syndrome
   - Two sources of truth with zero synchronization
   - Non-deterministic behavior based on call order
   - Confidence: ABSOLUTE (by design)

### Where Reviewers Disagree

**Config Cache Design (Reviewer 3 vs Others)**
- **Reviewer 3 Position:** Cache returns only config, not config_path, causing redundant filesystem search
- **Other Reviewers:** Didn't focus on caching layer
- **Reconciliation:** Caching issue is REAL but SECONDARY. It exacerbates the problem but isn't the root cause. The cache design flaw should be fixed in Phase 3 cleanup.

**Severity Assessment**
- **Reviewers 1-3:** Critical bug, needs immediate fix
- **Architect (Reviewer 4):** Systemic failure, requires architectural refactor
- **Reconciliation:** Both are correct. We'll do tactical fix now (Option B), architectural refactor later (Option A from architect review).

---

## Root Cause Analysis

### The ONE True Root Cause

**ARCHITECTURAL FLAW: Dual-Registry with Zero Synchronization**

The system has TWO project registries that NEVER communicate:

```
IN-MEMORY REGISTRY (auto_create.py)        PERSISTENT REGISTRY (PostgreSQL)
├─ Python dict (process-scoped)            ├─ projects table (durable)
├─ Created by Tier 2 resolution            ├─ Queried by Tier 1 resolution
├─ Lost on restart                         ├─ Survives restarts
└─ ❌ NEVER SYNCED TO DB ❌                └─ ❌ NEVER QUERIES IN-MEMORY ❌
```

**Why This Breaks:**
1. First call (Tier 2): Creates project in in-memory registry → SUCCESS
2. Second call (Tier 1): Queries PostgreSQL registry → NOT FOUND → FAIL
3. Second call tries Tier 2 but `ctx` is missing → FAIL
4. Falls back to Tier 4: "default" → SILENT DATA CORRUPTION

### Not Root Causes (Symptoms/Consequences)

❌ **Missing `ctx` parameter** - This is a symptom, not root cause. Even with `ctx`, the registry desync would still cause issues on server restart.

❌ **Config cache design** - This is an optimization bug, not a correctness bug. It doesn't cause wrong behavior, just inefficiency.

❌ **4-tier resolution complexity** - This is technical debt that makes debugging hard, but the bug would exist even with 2 tiers.

---

## Fix Strategy Decision

### Options Evaluated

**Option A: Quick Patch (2-4 hours)**
- Add `ctx` parameter to `get_session()` call
- ✅ Pro: Fixes immediate symptom
- ❌ Con: Still broken after server restart
- ❌ Con: Doesn't fix root cause
- **Verdict:** ❌ NOT ACCEPTABLE - Kicks can down road

**Option B: Proper Fix (1-2 days)** ⭐ **SELECTED**
- Fix 1: Pass `ctx` to `get_session()` (tactical)
- Fix 2: Persist to PostgreSQL on auto-create (strategic)
- Fix 3: Fix cache interface (cleanup)
- ✅ Pro: Actually fixes the bug
- ✅ Pro: Survives server restart
- ✅ Pro: Manageable scope (8-12 hours)
- ⚠️ Con: Requires database writes
- **Verdict:** ✅ CHOSEN - Right balance of fix/time

**Option C: Architectural Refactor (1-2 weeks)**
- Eliminate in-memory registry entirely
- Single source of truth (PostgreSQL only)
- Simplify 4-tier → 2-tier resolution
- ✅ Pro: Perfect long-term solution
- ⚠️ Con: 1-2 week timeline
- ⚠️ Con: Higher refactor risk
- **Verdict:** 📋 DEFER to Phase 4 - Do this after fixing the bug

### Decision Rationale

**Why Option B:**
1. **Urgency:** Bug breaks data isolation (CRITICAL)
2. **Risk:** Low - adds one INSERT, preserves existing logic
3. **Time:** 1-2 days is acceptable for production fix
4. **Reversibility:** Can rollback via git, no schema changes
5. **Future-proof:** Enables Option C refactor later

---

## Implementation Plan

### Phase 1: Critical Fixes (Must Fix - 8 hours)

#### Task 1.1: Pass Context to get_session()
**Priority:** P0 (CRITICAL)
**File:** `/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/tools/indexing.py`
**Line:** 172

**Current Code:**
```python
async with get_session(project_id=resolved_id) as db:
```

**Fixed Code:**
```python
async with get_session(project_id=resolved_id, ctx=ctx) as db:
```

**Test:**
```bash
pytest tests/integration/test_config_based_project_creation.py::test_project_auto_creation_from_config -v
```

**Expected Result:** Test should progress further (may still fail on registry sync)

**Estimated Time:** 30 minutes (change + test)

---

#### Task 1.2: Persist Auto-Created Projects to PostgreSQL
**Priority:** P0 (CRITICAL)
**File:** `/Users/cliffclarke/Claude_Code/codebase-mcp/src/database/auto_create.py`
**Lines:** After line 385 (after `registry.add(project)`)

**Change:**
```python
# Add to in-memory registry
registry.add(project)

# NEW: Sync to persistent PostgreSQL registry
try:
    from src.database.session import _initialize_registry_pool
    registry_pool = await _initialize_registry_pool()
    async with registry_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO projects (id, name, description, database_name, created_at, updated_at, metadata)
            VALUES ($1, $2, $3, $4, NOW(), NOW(), $5)
            ON CONFLICT (id) DO UPDATE SET
                updated_at = NOW(),
                database_name = EXCLUDED.database_name
        """, project.project_id, project.name, project.description or "",
            project.database_name, {})

    logger.info(
        f"✓ Project synced to persistent registry: {project.name}",
        extra={
            "context": {
                "operation": "auto_create_sync",
                "project_id": project.project_id,
                "database_name": project.database_name,
            }
        }
    )
except Exception as e:
    logger.error(
        f"Failed to sync project to persistent registry: {e}",
        extra={
            "context": {
                "operation": "auto_create_sync",
                "project_name": project.name,
                "error": str(e),
            }
        },
        exc_info=True
    )
    # Continue anyway - in-memory registry still works
    # This allows graceful degradation if registry DB is unavailable
```

**Test:**
```bash
# After fix, verify project appears in PostgreSQL
psql -d codebase_mcp_registry -c "SELECT id, name, database_name FROM projects WHERE name = 'test-auto-create';"
```

**Expected Result:** Project should be found in PostgreSQL table

**Estimated Time:** 2 hours (implement + test + error handling)

---

#### Task 1.3: Add Integration Test for Registry Sync
**Priority:** P0 (CRITICAL)
**File:** `/Users/cliffclarke/Claude_Code/codebase-mcp/tests/integration/test_config_based_project_creation.py`
**New Test:** `test_auto_created_project_persists_to_registry`

**Test Code:**
```python
@pytest.mark.asyncio
async def test_auto_created_project_persists_to_registry(setup_test_repo):
    """Verify auto-created projects are persisted to PostgreSQL registry."""
    repo_path, config_path = setup_test_repo

    # Mock Context
    mock_ctx = MagicMock(spec=Context)
    mock_ctx.session_id = "test-session-registry-sync"

    # Set working directory
    await set_working_directory(str(repo_path), mock_ctx)

    # Index repository (triggers auto-create)
    result = await index_repository(
        repo_path=str(repo_path),
        ctx=mock_ctx
    )

    project_id = result["project_id"]

    # Verify project exists in PostgreSQL registry
    from src.database.session import _initialize_registry_pool
    registry_pool = await _initialize_registry_pool()

    async with registry_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, name, database_name FROM projects WHERE id = $1",
            project_id
        )

        assert row is not None, f"Project {project_id} not found in persistent registry"
        assert row['name'] == "test-auto-create"
        assert row['database_name'].startswith("cb_proj_test_auto_create_")
```

**Expected Result:** Test passes, confirming registry sync works

**Estimated Time:** 1.5 hours (write test + verify)

---

#### Task 1.4: Verify Secondary Resolution Works
**Priority:** P0 (CRITICAL)
**File:** Run existing test that currently fails
**Test:** `tests/integration/test_config_based_project_creation.py::test_search_uses_correct_project_database`

**Expected Result:** Test now passes (was failing before)

**Verification Steps:**
1. Run test: `pytest tests/integration/test_config_based_project_creation.py::test_search_uses_correct_project_database -v`
2. Check logs for: "Using project workspace" with correct database name
3. Verify NO fallback to default database
4. Confirm search returns results from correct database

**Success Criteria:**
- ✅ Test passes
- ✅ No "Creating new pool for database: cb_proj_default_00000000" in logs
- ✅ Second resolution finds project in registry

**Estimated Time:** 1 hour (run + debug)

---

#### Task 1.5: Test Server Restart Scenario
**Priority:** P0 (CRITICAL)
**New Test:** Manual verification with actual server

**Steps:**
```bash
# 1. Start server
python -m src.main

# 2. Create project via config (MCP client or test)
# ... trigger auto-create ...

# 3. Verify project in registry
psql -d codebase_mcp_registry -c "SELECT name, database_name FROM projects;"

# 4. Restart server
# ... stop + start ...

# 5. Use project immediately (should work without re-creating)
# ... MCP call with project_id ...

# Expected: Project resolves successfully (no auto-create triggered)
```

**Success Criteria:**
- ✅ Project survives restart
- ✅ No "Creating new project database" log on second call
- ✅ Operations use correct database immediately

**Estimated Time:** 2 hours (manual testing + verification)

---

#### Task 1.6: Fix Cache Interface (Return Tuple)
**Priority:** P1 (HIGH but not blocking)
**Files:**
- `/Users/cliffclarke/Claude_Code/codebase-mcp/src/auto_switch/cache.py` (line 114)
- `/Users/cliffclarke/Claude_Code/codebase-mcp/src/database/session.py` (lines 344-395)

**Changes:**

**File 1: cache.py**
```python
# Line 114 (current)
return entry.config  # ❌ Only returns config

# Fixed
return (entry.config, entry.config_path)  # ✅ Returns tuple
```

**File 2: session.py**
```python
# Lines 344-348 (current)
config = await cache.get(working_dir)

# Fixed
cache_result = await cache.get(working_dir)

# Lines 351-395 (refactor)
if cache_result is None:
    # Cache miss - find and load config
    config_path = find_config_file(Path(working_dir))
    if not config_path:
        return None
    config = validate_config_syntax(config_path)
    await cache.set(working_dir, config, config_path)
else:
    # Cache hit - unpack tuple
    config, config_path = cache_result

# Remove lines 383-395 (redundant config_path resolution)
```

**Test:**
```python
# Add to test_cache.py
async def test_cache_returns_config_and_path():
    cache = get_config_cache()
    config = {"project": {"name": "test"}}
    path = Path("/test/config.json")

    await cache.set("/test", config, path)
    result = await cache.get("/test")

    assert result is not None
    cached_config, cached_path = result  # Should unpack
    assert cached_config == config
    assert cached_path == path
```

**Expected Result:** Cache hits avoid ALL filesystem operations

**Estimated Time:** 1.5 hours (implement + test)

---

### Phase 2: Validation (Prove It Works - 4 hours)

#### Task 2.1: Run Complete Integration Test Suite
**Priority:** P0 (CRITICAL)

**Command:**
```bash
pytest tests/integration/test_config_based_project_creation.py -v --log-cli-level=DEBUG
```

**Success Criteria:**
- ✅ All 4 tests pass (currently 1/4)
- ✅ No fallback to default database in any test
- ✅ Logs show successful registry sync

**Estimated Time:** 1 hour

---

#### Task 2.2: Manual Verification with workflow-mcp
**Priority:** P0 (CRITICAL)

**Steps:**
```bash
cd /Users/cliffclarke/Claude_Code/workflow-mcp

# Verify config exists
cat .codebase-mcp/config.json

# Use codebase-mcp tools via Claude Desktop or mcp-cli
# 1. set_working_directory (if needed)
# 2. index_repository
# 3. search_code

# Expected: All use cb_proj_workflow_mcp_dev_* database
```

**Success Criteria:**
- ✅ Correct database used (NOT default)
- ✅ Search returns results
- ✅ Project exists in registry table

**Estimated Time:** 1 hour

---

#### Task 2.3: Test Concurrent Project Creation
**Priority:** P1 (HIGH)

**Test Scenario:**
```python
@pytest.mark.asyncio
async def test_concurrent_auto_create_race_condition():
    """Verify no race condition on concurrent project creation."""
    import asyncio

    # Create 10 concurrent requests for same project
    tasks = [
        index_repository(repo_path="/test/repo", ctx=mock_ctx)
        for _ in range(10)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Verify:
    # 1. All succeed (no exceptions)
    # 2. All use same project_id
    # 3. Only ONE database created
    # 4. PostgreSQL UNIQUE constraint prevents duplicates
```

**Expected Result:** No duplicate projects or databases

**Estimated Time:** 1.5 hours (write + test)

---

#### Task 2.4: Performance Verification
**Priority:** P2 (MEDIUM)

**Benchmark:**
```python
import time

# Measure overhead of registry INSERT
start = time.time()
for _ in range(100):
    # Simulate auto-create with registry sync
    await get_or_create_project_from_config(config_path)
duration = time.time() - start

# Expected: <10ms per create (1 second total for 100)
assert duration < 1.0, "Registry sync adds >10ms overhead"
```

**Acceptance Criteria:**
- ✅ Registry INSERT adds <10ms per auto-create
- ✅ No performance regression vs in-memory only

**Estimated Time:** 30 minutes

---

### Phase 3: Cleanup (Optional Improvements - 4 hours)

#### Task 3.1: Add Structured Logging for Registry Sync
**Priority:** P2 (NICE-TO-HAVE)

**Enhancement:**
```python
# Add to auto_create.py after successful sync
logger.info(
    "Project registry synchronization complete",
    extra={
        "context": {
            "operation": "registry_sync",
            "project_id": project.project_id,
            "project_name": project.name,
            "database_name": project.database_name,
            "sync_duration_ms": sync_duration * 1000,
        }
    }
)
```

**Estimated Time:** 1 hour

---

#### Task 3.2: Add Metrics for Registry Operations
**Priority:** P2 (NICE-TO-HAVE)

**Enhancement:**
```python
# Add to auto_create.py
from prometheus_client import Counter, Histogram

registry_sync_total = Counter(
    "registry_sync_total",
    "Count of project registry synchronizations",
    labelnames=["status"]
)

registry_sync_duration = Histogram(
    "registry_sync_duration_seconds",
    "Time spent syncing to registry"
)
```

**Estimated Time:** 1.5 hours

---

#### Task 3.3: Documentation Updates
**Priority:** P2 (NICE-TO-HAVE)

**Files to Update:**
- `docs/architecture/PROJECT_RESOLUTION.md` - Document registry sync
- `BUG_FIX_SUMMARY.md` - Mark as RESOLVED
- `CHANGELOG.md` - Add bugfix entry

**Estimated Time:** 1.5 hours

---

## Risk Assessment

### What Could Go Wrong?

#### Risk 1: PostgreSQL Registry Unavailable
**Probability:** LOW
**Impact:** MEDIUM
**Mitigation:**
- Catch exception and continue with in-memory only (graceful degradation)
- Log error but don't fail auto-create
- Add health check to warn when registry sync is down

**Rollback:** No rollback needed - code handles failure gracefully

---

#### Risk 2: Race Condition on Concurrent Creates
**Probability:** MEDIUM
**Impact:** LOW
**Mitigation:**
- PostgreSQL UNIQUE constraint on `projects.id` prevents duplicates
- Use `ON CONFLICT DO UPDATE` to handle races gracefully
- Second create just updates `updated_at` timestamp

**Rollback:** Not needed - database constraint handles it

---

#### Risk 3: Performance Regression
**Probability:** LOW
**Impact:** LOW
**Mitigation:**
- Single INSERT per auto-create (<5ms typical)
- Async/non-blocking operation
- Benchmark in Phase 2 to verify

**Rollback:** Revert commits if >20ms overhead detected

---

#### Risk 4: Schema Migration Required
**Probability:** NONE
**Impact:** N/A
**Mitigation:**
- `projects` table already exists (used by registry.py)
- No schema changes required
- INSERT uses existing columns

**Rollback:** Not applicable

---

### Rollback Procedure

**If fix fails or causes issues:**

```bash
# 1. Identify the commit to rollback
git log --oneline -5

# 2. Revert the fix commits
git revert <commit-hash-1> <commit-hash-2>

# 3. Push revert
git push origin fix/project-resolution-auto-create

# 4. Verify system returns to previous (broken but known) state
pytest tests/integration/test_config_based_project_creation.py -v

# Expected: Same failures as before (1/4 passing)
```

**Data Safety:**
- No data loss possible (only adds records, never deletes)
- Worst case: Orphaned records in `projects` table (can be cleaned up later)
- No schema changes to rollback

---

## Success Metrics

### Pre-Fix (Current State)
- ❌ Secondary resolution success rate: **0%**
- ❌ Test suite passing: **25%** (1/4 tests)
- ❌ Data isolation: **BROKEN** (silently uses wrong database)
- ❌ Server restart handling: **BROKEN** (loses in-memory projects)
- ❌ Registry synchronization: **NONE**

### Post-Fix (Target State)
- ✅ Secondary resolution success rate: **100%**
- ✅ Test suite passing: **100%** (4/4 tests)
- ✅ Data isolation: **WORKING** (correct database every time)
- ✅ Server restart handling: **WORKING** (projects persist)
- ✅ Registry synchronization: **COMPLETE** (both registries updated)

### Validation Criteria

**Must Pass Before Merging:**
1. ✅ All 4 integration tests pass
2. ✅ Manual workflow-mcp test succeeds
3. ✅ Server restart test succeeds
4. ✅ No performance regression (>10ms)
5. ✅ Logs show "Project synced to persistent registry"
6. ✅ `psql` shows projects in registry table

**Nice to Have:**
- ✅ Cache optimization working (<1ms cache hits)
- ✅ Concurrent create test passing
- ✅ Documentation updated

---

## Timeline

### Day 1 (8 hours)
- Hour 1-2: Task 1.1, 1.2 (critical fixes)
- Hour 3-4: Task 1.3 (integration test)
- Hour 5-6: Task 1.4, 1.5 (verification)
- Hour 7-8: Task 1.6 (cache fix)

### Day 2 (4 hours)
- Hour 1-2: Phase 2 validation (all tests)
- Hour 3: Phase 2 manual testing
- Hour 4: Phase 3 cleanup (optional)

**Total Estimated Time:** 12 hours (1.5 days)
**Buffer for Issues:** +4 hours (50% contingency)
**Total Timeline:** 2 days maximum

---

## Dependencies

### Internal Dependencies
- PostgreSQL registry database must be running
- `projects` table must exist (already created by Alembic migrations)
- No schema changes required

### External Dependencies
- None (all code changes internal to codebase-mcp)

### Blocking Issues
- None identified

---

## Follow-Up Work (Post-Fix)

### Phase 4: Architectural Refactor (OPTIONAL, 1-2 weeks)
**After this fix is merged and validated in production:**

1. **Eliminate In-Memory Registry Entirely**
   - Replace `auto_create.py` registry with direct PostgreSQL queries
   - Use `registry.py` ProjectRegistry service everywhere
   - Delete singleton pattern

2. **Simplify Resolution Chain**
   - Reduce 4 tiers → 2 tiers (explicit → session → default)
   - Remove workflow-mcp integration from resolution (Tier 3)
   - Make resolution deterministic

3. **Add Session-Level Caching**
   - Cache resolved project_id per session_id
   - Avoid repeated resolution within same session
   - 5-minute TTL for cache entries

**Reference:** See `architect-review.md` Section "Migration Path Recommendation"

---

## Sign-Off

**Prepared By:** Technical Lead (Claude Code - Synthesis Agent)
**Date:** 2025-10-17
**Review Required:** Yes
**Approved By:** [Pending]

**Recommendation:** ✅ **PROCEED WITH IMPLEMENTATION IMMEDIATELY**

This fix addresses a critical data isolation bug with a manageable scope, low risk, and clear rollback path. The 1-2 day timeline is acceptable for a production-breaking issue.

---

## Appendix: Code Evidence Summary

### Bug Location #1: Missing Context
**File:** `src/mcp/tools/indexing.py:172`
```python
async with get_session(project_id=resolved_id) as db:  # ❌ ctx missing
```

### Bug Location #2: No Registry Sync
**File:** `src/database/auto_create.py:385`
```python
registry.add(project)  # ✅ Adds to in-memory
# ❌ MISSING: INSERT INTO projects table
```

### Fix Location #1: Pass Context
**File:** `src/mcp/tools/indexing.py:172`
```python
async with get_session(project_id=resolved_id, ctx=ctx) as db:  # ✅ Fixed
```

### Fix Location #2: Persist to Registry
**File:** `src/database/auto_create.py:386` (after `registry.add()`)
```python
# NEW CODE: Sync to PostgreSQL
registry_pool = await _initialize_registry_pool()
async with registry_pool.acquire() as conn:
    await conn.execute(
        "INSERT INTO projects (...) VALUES (...) ON CONFLICT DO UPDATE ...",
        project.project_id, project.name, ...
    )
```

---

**END OF SYNTHESIS DOCUMENT**
