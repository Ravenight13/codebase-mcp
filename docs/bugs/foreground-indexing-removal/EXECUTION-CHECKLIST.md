# Foreground Indexing Removal - Execution Checklist

**Project**: Remove broken `index_repository` foreground tool
**Estimated Time**: 4-5 hours
**Risk Level**: LOW
**Status**: ⏸️ NOT STARTED

---

## Pre-Execution Checklist

- [ ] Read `DELETION-PLAN.md` completely
- [ ] Understand rationale (Bug 1 not worth fixing)
- [ ] Review Constitutional Principle I (Simplicity Over Features)
- [ ] Backup current branch: `git checkout -b backup-before-foreground-removal`
- [ ] Create feature branch: `git checkout -b remove-foreground-indexing`
- [ ] All tests passing on main: `pytest tests/ -v`

---

## Phase 1: Test Infrastructure (2-3 hours)

### Step 1.1: Create Test Helper Function
- [ ] Open `tests/conftest.py` or create `tests/helpers.py`
- [ ] Add `index_repository_background()` helper function:
  ```python
  async def index_repository_background(repo_path: str, **kwargs):
      """Helper to index repository using background approach."""
      from src.mcp.tools.background_indexing import (
          start_indexing_background,
          get_indexing_status,
      )

      job = await start_indexing_background(repo_path=repo_path, **kwargs)
      job_id = job["job_id"]

      while True:
          status = await get_indexing_status(job_id=job_id)
          if status["status"] in ["completed", "failed"]:
              break
          await asyncio.sleep(0.1)

      if status["status"] == "failed":
          raise RuntimeError(f"Indexing failed: {status['error_message']}")

      return status
  ```
- [ ] Test helper function works: `pytest tests/integration/test_background_indexing.py -v`

### Step 1.2: Update Integration Tests (16 files)

**Contract Tests** (5 files):
- [ ] `tests/contract/test_index_project_id.py`
- [ ] `tests/contract/test_invalid_project_id.py`
- [ ] `tests/contract/test_permission_denied.py`
- [ ] `tests/contract/test_schema_generation.py`
- [ ] `tests/contract/test_tool_registration.py`

**Integration Tests** (9 files):
- [ ] `tests/integration/test_auto_provisioning.py`
- [ ] `tests/integration/test_backward_compatibility.py`
- [ ] `tests/integration/test_config_based_project_creation.py`
- [ ] `tests/integration/test_data_isolation.py`
- [ ] `tests/integration/test_invalid_identifier.py`
- [ ] `tests/integration/test_project_switching.py`
- [ ] `tests/integration/test_registry_sync.py`
- [ ] `tests/integration/test_workflow_integration.py`
- [ ] `tests/integration/test_workflow_timeout.py`

**Security Tests** (1 file):
- [ ] `tests/security/test_sql_injection.py`

**Performance Tests** (2 files):
- [ ] `tests/performance/test_baseline.py`
- [ ] `tests/performance/test_switching_latency.py`

**For each file**:
1. [ ] Replace import: `from src.mcp.tools.indexing import index_repository` → helper function
2. [ ] Replace calls: `index_repository(...)` → `index_repository_background(...)`
3. [ ] Run file tests: `pytest <file> -v`
4. [ ] Commit: `git add <file> && git commit -m "test: migrate <file> to background indexing"`

### Step 1.3: Verify All Tests Pass
- [ ] Run full test suite: `pytest tests/ -v`
- [ ] All integration tests pass: `pytest tests/integration/ -v`
- [ ] All contract tests pass: `pytest tests/contract/ -v`
- [ ] All security tests pass: `pytest tests/security/ -v`
- [ ] All performance tests pass: `pytest tests/performance/ -v`

**If any tests fail**:
- [ ] Debug failing test
- [ ] Fix and re-run
- [ ] Document issue in `ISSUES.md`

---

## Phase 2: Tool Removal (30 minutes)

### Step 2.1: Delete Foreground Tool
- [ ] Verify file exists: `ls -lh src/mcp/tools/indexing.py`
- [ ] Delete tool: `rm src/mcp/tools/indexing.py`
- [ ] Commit: `git add src/mcp/tools/indexing.py && git commit -m "feat: remove broken foreground indexing tool"`

### Step 2.2: Delete Foreground Tests
- [ ] Delete unit tests: `rm tests/unit/mcp/tools/test_indexing.py`
- [ ] Delete contract tests: `rm tests/contract/test_index_repository_contract.py`
- [ ] Commit: `git add tests/ && git commit -m "test: remove foreground indexing tests"`

### Step 2.3: Verify No Remaining Imports
- [ ] Check tool directory: `grep -r "index_repository" src/mcp/tools/ --exclude-dir=.git`
  - **Expected**: NO MATCHES (except comments)
- [ ] Check for imports in tests: `grep -r "from.*indexing import index_repository" tests/`
  - **Expected**: NO MATCHES
- [ ] Check for imports in src: `grep -r "from.*indexing import index_repository" src/`
  - **Expected**: Only service layer (`src/services/indexer.py`)

### Step 2.4: Run Test Suite
- [ ] All tests pass: `pytest tests/ -v`
- [ ] No import errors
- [ ] Server starts: `uv run src/mcp/server_fastmcp.py` (Ctrl+C after startup)

---

## Phase 3: Documentation Updates (1 hour)

### Step 3.1: High Priority - User Facing

**README.md**:
- [ ] Open `/Users/cliffclarke/Claude_Code/codebase-mcp/README.md`
- [ ] Find "Features" section (lines 25-35)
- [ ] Replace foreground tool with background tools:
  ```markdown
  # OLD
  1. **`index_repository`**: Index a code repository for semantic search

  # NEW
  1. **`start_indexing_background`**: Start background indexing job
  2. **`get_indexing_status`**: Query indexing job status
  3. **`search_code`**: Semantic code search...
  ```
- [ ] Commit: `git add README.md && git commit -m "docs: update README to background-only indexing"`

**CLAUDE.md**:
- [ ] Open `/Users/cliffclarke/Claude_Code/codebase-mcp/CLAUDE.md`
- [ ] Find "Background Indexing" section (lines 167-191)
- [ ] Update "When to Use" subsection:
  ```markdown
  # OLD
  - **Foreground** (`index_repository`): Repositories <5,000 files
  - **Background** (`start_indexing_background`): Repositories 10,000+ files

  # NEW
  ### When to Use
  - **All repositories**: Use background indexing (`start_indexing_background`)
  - Small repos (<5K files): Complete in <60s
  - Large repos (10K+ files): Complete in 5-10 minutes
  ```
- [ ] Commit: `git add CLAUDE.md && git commit -m "docs: update CLAUDE.md to background-only indexing"`

### Step 3.2: Medium Priority - Architecture Docs

**Background Indexing Design**:
- [ ] Open `docs/architecture/background-indexing.md`
- [ ] Add note at top: "**NOTE**: As of 2025-10-18, foreground indexing has been removed. Background indexing is the only supported method."
- [ ] Commit: `git add docs/architecture/ && git commit -m "docs: note foreground indexing removal in architecture"`

**Bug Tracker**:
- [ ] Open `docs/bugs/mcp-indexing-failures/MASTER-PLAN.md`
- [ ] Update Bug 1 status: "RESOLVED by removing foreground tool (2025-10-18)"
- [ ] Open `docs/bugs/mcp-indexing-failures/COMPLETION-SUMMARY.md`
- [ ] Add resolution section for Bug 1
- [ ] Commit: `git add docs/bugs/ && git commit -m "docs: mark Bug 1 as resolved by removal"`

### Step 3.3: Create Migration Guide
- [ ] Create `docs/migration/foreground-to-background.md`
- [ ] Include before/after examples from README
- [ ] Include test migration examples
- [ ] Commit: `git add docs/migration/ && git commit -m "docs: add foreground to background migration guide"`

### Step 3.4: Low Priority - Specs/Archive (Optional)
- [ ] Review `DOCUMENTATION-UPDATE-PLAN.md` for additional files
- [ ] Update spec documents if time permits
- [ ] Add deprecation notices to archived docs

---

## Phase 4: Verification (30 minutes)

### Step 4.1: Code Verification
- [ ] No foreground tool in src: `ls src/mcp/tools/indexing.py` (should fail)
- [ ] No foreground imports: `grep -r "from.*indexing import index_repository" src/ tests/`
- [ ] Only service layer remains: `grep -r "index_repository" src/services/indexer.py`
- [ ] Type checking passes: `mypy src/ --strict`

### Step 4.2: Test Verification
- [ ] Full test suite passes: `pytest tests/ -v`
- [ ] Integration tests pass: `pytest tests/integration/ -v`
- [ ] Contract tests pass: `pytest tests/contract/ -v`
- [ ] Performance tests pass: `pytest tests/performance/ -v`
- [ ] Background indexing tests pass: `pytest tests/integration/test_background_indexing.py -v`

### Step 4.3: Server Verification
- [ ] Server starts successfully: `uv run src/mcp/server_fastmcp.py`
- [ ] Verify tools exposed (should see):
  - ✅ `start_indexing_background`
  - ✅ `get_indexing_status`
  - ✅ `search_code`
  - ✅ `set_working_directory`
  - ❌ `index_repository` (should NOT appear)
- [ ] Server logs show no errors: `tail -100 /tmp/codebase-mcp.log`

### Step 4.4: Documentation Verification
- [ ] README.md has background-only pattern
- [ ] CLAUDE.md recommends background-only
- [ ] Migration guide exists
- [ ] Bug 1 marked as resolved
- [ ] All docs use correct tool names

### Step 4.5: Final Checks
- [ ] Count lines deleted: `git diff --stat main` (should show ~944 lines deleted)
- [ ] Review all commits: `git log --oneline main..HEAD`
- [ ] Check for any TODOs: `grep -r "TODO.*index_repository" src/ tests/ docs/`
- [ ] No broken links in docs: (manual spot check)

---

## Post-Execution

### Success Metrics
- [ ] ✅ 944 lines of broken code deleted
- [ ] ✅ All tests pass
- [ ] ✅ Server exposes only background indexing tools
- [ ] ✅ Documentation updated
- [ ] ✅ No remaining imports of foreground tool
- [ ] ✅ Migration guide created
- [ ] ✅ Bug 1 marked resolved

### Create Pull Request
- [ ] Push branch: `git push origin remove-foreground-indexing`
- [ ] Create PR with title: "Remove broken foreground indexing tool"
- [ ] PR description includes:
  - Link to `DELETION-PLAN.md`
  - Summary of changes (3 files deleted, 21 files modified)
  - Rationale (Bug 1, Constitutional Principle I)
  - Migration guide link
- [ ] Request review from team

### Cleanup
- [ ] Delete backup branch: `git branch -D backup-before-foreground-removal`
- [ ] Archive removal plan docs for future reference
- [ ] Update project status to COMPLETED

---

## Rollback Procedure (If Needed)

⚠️ **Use only if critical issues discovered**

1. [ ] Revert all commits: `git reset --hard main`
2. [ ] Restore tool file: `git checkout main -- src/mcp/tools/indexing.py`
3. [ ] Restore test files: `git checkout main -- tests/`
4. [ ] Run tests: `pytest tests/ -v`
5. [ ] Document rollback reason: Create `ROLLBACK.md` with issues encountered
6. [ ] Update status to ROLLED_BACK

**Note**: Rollback NOT RECOMMENDED - foreground tool is broken anyway

---

## Troubleshooting

### Issue: Tests fail after conversion
**Solution**: Review helper function implementation, check polling interval

### Issue: Server won't start
**Solution**: Check for syntax errors in modified files, verify imports

### Issue: Import errors
**Solution**: Search for remaining references: `grep -r "index_repository" src/ tests/`

### Issue: Performance regression
**Solution**: Background indexing should be FASTER, check benchmark tests

---

## Time Tracking

| Phase | Estimated | Actual | Notes |
|-------|-----------|--------|-------|
| Phase 1: Tests | 2-3 hours | | |
| Phase 2: Removal | 30 min | | |
| Phase 3: Docs | 1 hour | | |
| Phase 4: Verify | 30 min | | |
| **TOTAL** | **4-5 hours** | | |

---

## Sign-Off

- [ ] All checklist items completed
- [ ] All tests passing
- [ ] Documentation updated
- [ ] PR created and reviewed
- [ ] Changes merged to main

**Executed By**: _________________
**Date**: _________________
**Reviewed By**: _________________
**Date**: _________________

---

**Last Updated**: 2025-10-18
**Status**: ⏸️ NOT STARTED
**Document Version**: 1.0
