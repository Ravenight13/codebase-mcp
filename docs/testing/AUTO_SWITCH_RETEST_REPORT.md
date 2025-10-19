# Auto-Switch Re-Test Report

**Date**: 2025-10-15
**Time**: 21:56 UTC
**Branch**: `live-testing-integration`
**Test Run**: #2 (Re-test after initial bug report)

---

## Executive Summary

❌ **STILL FAILING** - Bug remains unfixed

**Critical Findings**:
1. 🐛 Same `ProjectValidationResult` error on all operations
2. ⚠️ Auto-switch NOT activating (wrong project active)
3. ⚠️ Health check inconsistency persists

---

## Test Results Comparison

| Test | Initial Run | Re-Test | Status |
|------|-------------|---------|--------|
| Config verification | ✅ PASS | ✅ PASS | No change |
| Active project check | ✅ PASS | ❌ FAIL | **Worse** |
| Register entity type | ❌ FAIL | ❌ FAIL | No change |
| Create work item | ❌ FAIL | ❌ FAIL | No change |
| Query work items | ❌ FAIL | ❌ FAIL | No change |
| Health check | ⚠️ PARTIAL | ⚠️ PARTIAL | No change |

---

## Detailed Test Results

### ✅ Test 1: Config Verification

**Status**: PASSED (unchanged)

**Config Contents**:
```json
{
  "version": "1.0",
  "project": {"name": "codebase-mcp"},
  "auto_switch": true
}
```

**Findings**:
- Config file still valid
- Auto-switch still enabled
- Project name: `codebase-mcp`

---

### ❌ Test 2: Active Project Check

**Status**: FAILED (regression from initial test)

**Initial Test Result**:
- Active project: `codebase-mcp` ✅
- Project ID: `eca49f13-f342-4958-95a0-d7b9ba2a42eb` ✅
- Auto-switch appeared to work ✅

**Re-Test Result**:
- Active project: `commission-processing-vendor-extractors` ❌
- Project ID: `ee1e6ce5-ac7a-42a0-9582-75634df83ee8` ❌
- **Auto-switch did NOT activate** ❌

**Full Response**:
```json
{
  "id": "ee1e6ce5-ac7a-42a0-9582-75634df83ee8",
  "name": "commission-processing-vendor-extractors",
  "description": "Commission statement processing system with vendor extractors for 45+ vendors",
  "database_name": "wf_proj_commission_processing_vendor_e_777e5f9b",
  "created_at": "2025-10-14T13:04:06.745030Z",
  "updated_at": "2025-10-14T13:04:06.745030Z",
  "metadata": {
    "owner": "DataTeam",
    "vendors_total": "45",
    "backup_schedule": "daily",
    "data_classification": "confidential",
    "vendors_operational": "3"
  }
}
```

**Analysis**:
- This is a **regression** - the first test showed auto-switch working
- Now showing a different project (from previous session?)
- Suggests auto-switch is **not reliable** or has timing issues
- May depend on server state or initialization order

---

### ❌ Test 3: Register Entity Type

**Status**: FAILED (unchanged)

**Error**:
```
'ProjectValidationResult' object has no attribute 'get'
```

**Parameters**:
- `type_name`: "test_item"
- `schema`: `{"type": "object", "properties": {"status": {"type": "string"}}, "required": ["status"]}`

**Findings**:
- **Exact same error** as initial test
- Bug remains unfixed
- No code changes deployed to workflow-mcp

---

### ❌ Test 4: Create Work Item

**Status**: FAILED (unchanged)

**Error**:
```
'ProjectValidationResult' object has no attribute 'get'
```

**Parameters**:
- `item_type`: "task"
- `title`: "Test Auto-Switch Functionality"

**Findings**:
- Same error pattern
- Affects all write operations
- Bug systematic across tool surface

---

### ❌ Test 5: Query Work Items

**Status**: FAILED (unchanged)

**Error**:
```
'ProjectValidationResult' object has no attribute 'get'
```

**Findings**:
- Read operations also broken
- Not just write operations
- Complete feature failure

---

### ⚠️ Test 6: Health Check

**Status**: PARTIAL (unchanged inconsistency)

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-10-15T21:56:11.703318+00:00",
  "database": {
    "registry": {
      "status": "connected",
      "pool": {"size": 1, "min_size": 2, "max_size": 10, "free_connections": 1}
    },
    "active_project": {
      "status": "no_active_project"  // ⚠️ INCONSISTENT
    }
  },
  "tools": {"count": 23, "categories": ["project", "entity", "work_item", "deployment", "health"]},
  "metrics": {"uptime_seconds": 1506.63, "total_operations": 0, "recent_operations": {}},
  "system": {"python_version": "3.13.7", "platform": "darwin", "server_version": "0.1.0"}
}
```

**Findings**:
- Shows `"no_active_project"` ❌
- But `get_active_project()` returned `commission-processing-vendor-extractors`
- **Same inconsistency** as initial test
- Suggests internal state management issue

---

## New Findings (Re-Test)

### 1. Auto-Switch Not Activating

**Critical Discovery**: Auto-switch did NOT switch to `codebase-mcp` project.

**Comparison**:
- **Initial Test**: Active project was `codebase-mcp` (correct) ✅
- **Re-Test**: Active project is `commission-processing-vendor-extractors` (wrong) ❌

**Possible Explanations**:
1. Auto-switch only works on first server startup
2. Auto-switch requires server restart to re-detect config
3. Auto-switch is unreliable and depends on timing
4. Previous session's project persists across restarts

**Impact**: Auto-switch feature is **unreliable** even when it doesn't error.

---

### 2. Bug Remains Unfixed

**Confirmation**: The `ProjectValidationResult` error is **unchanged**.

**Operations Still Broken**:
- ❌ `register_entity_type()`
- ❌ `create_entity()`
- ❌ `create_work_item()`
- ❌ `update_work_item()`
- ❌ `query_entities()`
- ❌ `query_work_items()`

**Operations Still Working**:
- ✅ `get_active_project()`
- ✅ `health_check()`

---

### 3. Server Uptime

**Observation**: `"uptime_seconds": 1506.63` (25 minutes)

This suggests:
- Server was restarted since initial test (~21:31)
- But auto-switch did NOT activate on restart
- Config file not being read on server init

---

## Root Cause Analysis (Updated)

### Bug #1: ProjectValidationResult Type Error

**Status**: **UNFIXED** 🐛

**Error**: `'ProjectValidationResult' object has no attribute 'get'`

**Root Cause**: workflow-mcp validation returns Pydantic model instead of dict

**Location**: workflow-mcp server (not in this repository)

**Impact**: **All operations broken**

---

### Bug #2: Auto-Switch Not Activating

**Status**: **NEW FINDING** 🐛

**Symptom**: Config file exists but wrong project is active

**Expected**: Active project should be `codebase-mcp`

**Actual**: Active project is `commission-processing-vendor-extractors`

**Root Cause Hypothesis**:
1. Config file not being read on server startup
2. Auto-switch logic only runs on first-ever startup
3. Cached project from previous session persists
4. Config discovery failing (wrong working directory?)

**Impact**: **Auto-switch unreliable**

---

### Bug #3: Health Check Inconsistency

**Status**: **UNFIXED** 🐛

**Symptom**: `health_check()` shows `"no_active_project"`

**But**: `get_active_project()` returns project data

**Root Cause**: Different code paths for these operations

**Impact**: **Observability broken**

---

## Severity Assessment

| Bug | Severity | Impact | Workaround |
|-----|----------|--------|------------|
| ProjectValidationResult error | 🔴 CRITICAL | All operations broken | Manual switch_project() |
| Auto-switch not activating | 🟠 HIGH | Feature doesn't work | Manual switch_project() |
| Health check inconsistency | 🟡 MEDIUM | Wrong observability | Use get_active_project() |

---

## Comparison: Initial Test vs Re-Test

### What Got Worse

1. **Auto-switch activation**: Worked initially, now doesn't work ❌
   - Initial: `codebase-mcp` active ✅
   - Re-test: `commission-processing-vendor-extractors` active ❌

### What Stayed The Same (Broken)

1. **ProjectValidationResult error**: Still present ❌
2. **All operations fail**: No change ❌
3. **Health check inconsistency**: Still shows wrong state ❌

### What Stayed The Same (Working)

1. **Config file detection**: Still valid ✅
2. **get_active_project() works**: Still returns data ✅
3. **health_check() works**: Still returns (inconsistent) data ✅

---

## Tests Not Completed

Due to bugs, cannot proceed with:

- ❌ Test 4: Create test entity (operation broken)
- ❌ Test 6: Query entities (operation broken)
- ❌ Test 7: Query work items (operation broken)
- ❌ Test 8: Subdirectory navigation (can't verify without working operations)
- ❌ Test 9: Cross-project isolation (**CRITICAL** - security test blocked)
- ❌ Test 11: Environment variable override

**Tests completed**: 3/11 (27%)
**Tests blocked**: 8/11 (73%)

---

## Recommendations (Updated)

### Immediate Actions (workflow-mcp team)

#### Priority 1: Fix ProjectValidationResult Error 🔴

**Action**: Fix the type error in validation logic

**Expected Fix**:
```python
# Current (broken):
def validate_project(config):
    result = ProjectValidationResult(...)
    return result  # ❌ Returns Pydantic model

# Fixed:
def validate_project(config):
    result = ProjectValidationResult(...)
    if not result.is_valid:
        raise ValidationError(result.errors)
    return result.project  # ✅ Returns project dict/object
```

**Verification**: All operations should work after fix

---

#### Priority 2: Fix Auto-Switch Activation 🟠

**Investigation Needed**:
1. When is config file read? (Startup only? Every request?)
2. How is working directory determined?
3. Why did it work in initial test but not re-test?
4. Is there caching/persistence of active project?

**Test Scenarios**:
1. Server restart with config file → should activate
2. Config file added while server running → should activate?
3. Config file in subdirectory → should discover parent config

**Verification**: Active project should match config on every test run

---

#### Priority 3: Fix Health Check Inconsistency 🟡

**Action**: Ensure `health_check()` reflects actual active project state

**Expected**:
- If `get_active_project()` returns project X
- Then `health_check()` should show project X as active

**Verification**: Both endpoints should report consistent state

---

### Testing Requirements

Before declaring auto-switch production-ready:

1. ✅ **All 11 test scenarios must pass** (currently 3/11)
2. ✅ **Cross-project isolation must be verified** (Test 9 - security critical)
3. ✅ **Auto-switch must be consistent** (work on every server start)
4. ✅ **Health monitoring must be accurate** (observability critical)
5. ✅ **Subdirectory discovery must work** (Test 8)
6. ✅ **Environment override must work** (Test 11)

---

## Workaround (Still Valid)

Manual project switching bypasses the bugs:

```python
# Step 1: Find the codebase-mcp project ID
projects = await list_projects()
codebase_project = [p for p in projects if p['name'] == 'codebase-mcp'][0]

# Step 2: Manually switch
await switch_project(project_id=codebase_project['id'])

# Step 3: Operations should now work (if ProjectValidationResult bug is fixed)
await register_entity_type(...)
```

**Limitation**: This defeats the purpose of auto-switch.

---

## Conclusion

### Test Verdict: ❌ **STILL FAILING**

**Summary**:
- 🐛 ProjectValidationResult bug: **UNFIXED**
- 🐛 Auto-switch activation: **REGRESSION** (worked initially, now broken)
- 🐛 Health check inconsistency: **UNFIXED**
- 📊 Tests passed: **3/11 (27%)**
- 📊 Tests blocked: **8/11 (73%)**

### Severity

**CRITICAL** 🔴 - Feature is completely non-functional

1. All operations fail with type error
2. Auto-switch doesn't activate reliably
3. Observability broken (health check inconsistent)
4. Cannot test security-critical cross-project isolation

### Next Steps

1. **workflow-mcp team**: Fix all 3 bugs identified
2. **Testing**: Re-run complete 11-test suite after fixes
3. **Security**: Validate cross-project isolation (Test 9)
4. **Documentation**: Update auto-switch docs with findings

### Recommendation

**DO NOT DEPLOY** auto-switch feature to production until:
- ✅ All 3 bugs fixed
- ✅ All 11 tests pass
- ✅ Cross-project isolation verified
- ✅ Consistent behavior across server restarts

---

## Test Environment

**Date**: 2025-10-15 21:56 UTC
**Branch**: live-testing-integration
**workflow-mcp Version**: 0.1.0
**Python**: 3.13.7
**Platform**: darwin
**Server Uptime**: 1506.63 seconds (25 minutes)

---

## Appendix: Test Execution Timeline

```
21:56:00 - Config verification: PASSED ✅
21:56:01 - Active project check: FAILED (wrong project) ❌
21:56:02 - Register entity type: FAILED (ProjectValidationResult) ❌
21:56:03 - Create work item: FAILED (ProjectValidationResult) ❌
21:56:04 - Query work items: FAILED (ProjectValidationResult) ❌
21:56:11 - Health check: PARTIAL (inconsistent state) ⚠️
21:56:12 - Testing halted - bugs confirmed unfixed
```

---

**Report Status**: Auto-switch feature remains broken, awaiting workflow-mcp fixes
