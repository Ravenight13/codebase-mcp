# Foreground Indexing Removal - Quick Reference

## TL;DR

**What**: Delete broken `index_repository` foreground tool, keep only background indexing.

**Why**: Bug 1 not worth fixing, background indexing is superior, aligns with Constitutional Principle I (Simplicity).

**Risk**: LOW (foreground tool is broken, no production users)

**Effort**: 4-5 hours

---

## Files to Delete (3 files, 944 lines)

```bash
# Tool implementation
rm src/mcp/tools/indexing.py  # 388 lines

# Unit tests
rm tests/unit/mcp/tools/test_indexing.py  # 258 lines

# Contract tests
rm tests/contract/test_index_repository_contract.py  # 298 lines
```

---

## Files to Modify (21 files)

### Integration Tests (16 files)
Convert from foreground to background indexing:

```python
# OLD (broken)
from src.mcp.tools.indexing import index_repository
result = await index_repository(repo_path="/path/to/repo")

# NEW (working)
from src.mcp.tools.background_indexing import start_indexing_background, get_indexing_status
job = await start_indexing_background(repo_path="/path/to/repo")
while True:
    status = await get_indexing_status(job_id=job["job_id"])
    if status["status"] in ["completed", "failed"]:
        break
    await asyncio.sleep(0.1)
```

**Files**:
- `tests/integration/test_auto_provisioning.py`
- `tests/integration/test_backward_compatibility.py`
- `tests/integration/test_config_based_project_creation.py`
- `tests/integration/test_data_isolation.py`
- `tests/integration/test_invalid_identifier.py`
- `tests/integration/test_project_switching.py`
- `tests/integration/test_registry_sync.py`
- `tests/integration/test_workflow_integration.py`
- `tests/integration/test_workflow_timeout.py`
- `tests/security/test_sql_injection.py`
- `tests/contract/test_index_project_id.py`
- `tests/contract/test_invalid_project_id.py`
- `tests/contract/test_permission_denied.py`
- `tests/contract/test_schema_generation.py`
- `tests/contract/test_tool_registration.py`
- `tests/performance/test_baseline.py`
- `tests/performance/test_switching_latency.py`

### Documentation (5 files)
Update references to foreground tool:

1. `README.md` - Lines 25-35 (Features section)
2. `CLAUDE.md` - Lines 167-191 (Background Indexing section)
3. `docs/architecture/background-indexing.md`
4. `docs/bugs/mcp-indexing-failures/MASTER-PLAN.md`
5. `docs/bugs/mcp-indexing-failures/COMPLETION-SUMMARY.md`

---

## Files to Keep (No Changes)

### Core Services
- `src/services/indexer.py` - Shared indexing service (used by background worker)
- `src/services/background_worker.py` - Background indexing implementation

### Background Indexing Tools
- `src/mcp/tools/background_indexing.py` - Working background indexing tools

### Background Indexing Tests
- `tests/integration/test_background_indexing.py`
- `tests/integration/test_background_auto_create_e2e.py`
- `tests/integration/test_background_indexing_errors.py`
- `tests/unit/test_background_auto_create.py`
- `tests/unit/services/test_background_worker.py`

---

## Execution Sequence

```bash
# Phase 1: Create test helper (optional)
# Add to tests/conftest.py or tests/helpers.py

# Phase 2: Update integration tests (16 files)
# Convert index_repository -> background approach

# Phase 3: Delete tool and tests
rm src/mcp/tools/indexing.py
rm tests/unit/mcp/tools/test_indexing.py
rm tests/contract/test_index_repository_contract.py

# Phase 4: Update documentation
# Edit README.md, CLAUDE.md, etc.

# Phase 5: Verify
pytest tests/ -v
grep -r "from.*indexing import index_repository" src/ tests/
```

---

## Verification Commands

```bash
# Should return NO matches after deletion
grep -r "index_repository" src/mcp/tools/ --exclude-dir=.git

# Should only find service layer and docs
grep -r "index_repository" src/ docs/ tests/

# All tests should pass
pytest tests/ -v

# Server should start without errors
uv run src/mcp/server_fastmcp.py
```

---

## User Migration (1-Liner)

**For Claude Desktop users**: Replace `index_repository` with background indexing pattern (see README.md).

**For test writers**: Use test helper function (see tests/conftest.py).

---

## Rollback (If Needed)

```bash
# Revert tool deletion
git checkout HEAD~1 -- src/mcp/tools/indexing.py

# Revert test changes
git checkout HEAD~1 -- tests/

# Note: NOT RECOMMENDED - foreground tool is broken
```

---

## Success Metrics

- [ ] 944 lines of broken code deleted
- [ ] All tests pass
- [ ] Server exposes only background indexing tools
- [ ] Documentation updated
- [ ] No remaining imports of foreground tool

---

## Full Details

See: `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/bugs/foreground-indexing-removal/DELETION-PLAN.md`
