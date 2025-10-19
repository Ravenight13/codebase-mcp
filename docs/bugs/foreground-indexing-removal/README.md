# Foreground Indexing Removal - Project Overview

**Status**: PLANNED
**Created**: 2025-10-18
**Decision**: Remove broken `index_repository` foreground tool, keep only background indexing

---

## Documents in This Directory

### 1. DELETION-PLAN.md (534 lines) ⭐ START HERE
**Comprehensive removal plan covering:**
- Executive summary and rationale
- Files to delete (3 files, 944 lines)
- Files to modify (21 files, ~600 lines)
- Tests to remove and keep
- Migration guide for users
- 4-phase implementation plan
- Success criteria and verification
- Risk assessment and rollback plan

**Use this for**: Complete understanding of the removal project

### 2. QUICK-REFERENCE.md (174 lines) 📋 QUICK GUIDE
**One-page cheat sheet with:**
- Files to delete (3 files listed)
- Files to modify (21 files listed)
- Execution sequence (bash commands)
- Verification commands
- Success metrics

**Use this for**: Quick execution during implementation

### 3. DOCUMENTATION-UPDATE-PLAN.md (743 lines) 📚 DOCS ONLY
**Documentation-specific plan with:**
- 161 markdown files requiring updates
- Prioritized file list (High/Medium/Low)
- Standard background indexing pattern
- Search-and-replace patterns

**Use this for**: Documentation cleanup phase (Phase 3)

---

## Quick Decision Summary

### Why Remove Foreground Indexing?

1. **Bug 1 Not Worth Fixing**: Foreground tool returns `None` instead of JSON response
2. **Background is Superior**: Non-blocking, observable, scalable, production-ready
3. **Constitutional Alignment**: Principle I - Simplicity Over Features
4. **Low Risk**: Foreground tool is broken, no production users

### What Gets Deleted?

```
src/mcp/tools/indexing.py                              (388 lines)
tests/unit/mcp/tools/test_indexing.py                  (258 lines)
tests/contract/test_index_repository_contract.py       (298 lines)
-----------------------------------------------------------
TOTAL:                                                  944 lines
```

### What Gets Modified?

- **16 integration test files**: Convert from foreground to background indexing
- **5 documentation files**: Update user-facing docs
- **161 markdown files** (optional): Update historical references

### What Gets Kept?

- `src/services/indexer.py` - Core indexing service (shared by background worker)
- `src/mcp/tools/background_indexing.py` - Background indexing tools
- All background indexing tests (5 files)

---

## Implementation Timeline

| Phase | Duration | Description |
|-------|----------|-------------|
| **Phase 1** | 2-3 hours | Update test infrastructure |
| **Phase 2** | 30 min | Delete tool and tests |
| **Phase 3** | 1 hour | Update documentation |
| **Phase 4** | 30 min | Verification |
| **TOTAL** | **4-5 hours** | Complete removal |

---

## Success Criteria Checklist

### Functional
- [ ] All integration tests pass using background indexing
- [ ] All contract tests pass (except removed foreground tests)
- [ ] Server starts without errors
- [ ] MCP clients can index repositories successfully

### Code Quality
- [ ] No dangling imports of `index_repository` tool
- [ ] All grep searches return only service layer or docs
- [ ] Test helper function documented
- [ ] mypy --strict passes

### Documentation
- [ ] README.md reflects background-only approach
- [ ] CLAUDE.md documents usage pattern
- [ ] Migration guide complete
- [ ] Bug 1 marked "resolved by removal"

### Performance
- [ ] Background indexing <60s for 10K files (unchanged)
- [ ] Search latency <500ms p95 (unchanged)
- [ ] No regression in benchmarks

---

## User Migration Example

### Before (Broken ❌)
```python
from src.mcp.tools.indexing import index_repository

# This returns None due to Bug 1
result = await index_repository(
    repo_path="/path/to/repo",
    project_id="my-project"
)
```

### After (Working ✅)
```python
from src.mcp.tools.background_indexing import (
    start_indexing_background,
    get_indexing_status,
)

# Start indexing job
job = await start_indexing_background(
    repo_path="/path/to/repo",
    project_id="my-project"
)

# Poll for completion
while True:
    status = await get_indexing_status(job_id=job["job_id"])
    if status["status"] in ["completed", "failed"]:
        break
    await asyncio.sleep(2)

# Check result
if status["status"] == "completed":
    print(f"✅ Indexed {status['files_indexed']} files!")
```

---

## Verification Commands

```bash
# 1. Check for remaining references (should be NONE)
grep -r "index_repository" src/mcp/tools/ --exclude-dir=.git

# 2. Run test suite
pytest tests/ -v

# 3. Verify server startup
uv run src/mcp/server_fastmcp.py

# 4. Check exposed tools (should NOT include index_repository)
# Expected tools:
#   - start_indexing_background
#   - get_indexing_status
#   - search_code
#   - set_working_directory
```

---

## Related Documents

- **Bug 1 Analysis**: `docs/bugs/mcp-indexing-failures/bug1-review.md`
- **Bug 1 Tasks**: `docs/bugs/mcp-indexing-failures/bug1-tasks.md`
- **Master Bug Plan**: `docs/bugs/mcp-indexing-failures/MASTER-PLAN.md`
- **Background Indexing Design**: `docs/architecture/background-indexing.md`
- **Constitutional Principles**: `.specify/memory/constitution.md`

---

## Rollback Plan

**If problems occur during implementation:**

```bash
# Revert tool deletion
git checkout HEAD~1 -- src/mcp/tools/indexing.py

# Revert test changes
git checkout HEAD~1 -- tests/

# Document rollback reason
# Create: docs/bugs/foreground-indexing-removal/ROLLBACK.md
```

⚠️ **Note**: Rollback NOT RECOMMENDED - foreground tool is broken, forward-only migration preferred.

---

## Approval Status

- [ ] **Technical Review**: Pending
- [ ] **Architecture Review**: Pending
- [ ] **Security Review**: N/A (removing code, not adding)
- [ ] **Performance Review**: N/A (background indexing faster)
- [ ] **Documentation Review**: Pending
- [ ] **Final Approval**: Pending

---

## Implementation Team

**Primary**: TBD
**Reviewer**: TBD
**Approver**: TBD

---

## Questions?

Contact: [Your contact info here]

---

**Last Updated**: 2025-10-18
**Version**: 1.0
**Status**: Planning Complete, Awaiting Approval
