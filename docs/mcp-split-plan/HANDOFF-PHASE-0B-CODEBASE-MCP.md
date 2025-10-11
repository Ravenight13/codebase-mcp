# Phase 0B: Codebase-MCP Preparation - Handoff Prompt

## Copy-Paste This Into New Chat

```
I'm working on splitting a monolithic MCP into two focused MCPs with multi-project support. All planning is complete. I need to execute Phase 0B: Codebase-MCP Preparation.

**Project Context:**
We're refactoring the existing codebase-mcp repository to prepare for a major transformation:
- Current: Monolithic MCP (16 tools: search + work items + vendors + tasks + deployments)
- Target: Pure semantic code search MCP (2 tools: index_repository, search_code)
- Adding: Multi-project support (one database per project)

**What We're Doing:**
Phase 0B prepares the existing codebase-mcp repository for refactoring by establishing baselines, validation, and rollback procedures. This is preparation work BEFORE any actual refactoring.

**Where We Are:**
- ✅ Planning Complete (10 subagents, all reviews done, all critical issues resolved)
- ✅ Phase 0 Final Plan Ready (includes Phase 0 Review with critical fixes)
- 🚧 Phase 0B: Preparation (Starting Now)

**Documentation Location:**
All planning docs are in `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/mcp-split-plan/`

**Key Files:**
- PHASE-0-FOUNDATION.md - Complete Phase 0 implementation guide
- PHASE-0-REVIEW.md - Critical issues and fixes identified
- IMPLEMENTATION-ROADMAP.md - Overall project roadmap
- 01-codebase-mcp/FINAL-IMPLEMENTATION-PLAN.md - Complete refactoring plan

**Your Task:**
Execute Phase 0B following PHASE-0-FOUNDATION.md section "Phase 0B: codebase-mcp Preparation" (starting at line 880), incorporating critical fixes from PHASE-0-REVIEW.md.

**Deliverables:**
1. Performance baseline collected (indexing time, search latency)
2. Test repository generated (10,000 Python files)
3. Database permissions validated (CREATEDB, pgvector)
4. Refactor branch created (004-multi-project-refactor)
5. Rollback tag created (backup-before-refactor)
6. Emergency rollback script (with database cleanup)
7. Documentation updated (REFACTORING-JOURNAL.md)
8. Phase 0 completion checklist filled

**Success Criteria:**
- ✅ Performance baseline shows <60s indexing, <500ms search
- ✅ PostgreSQL >=14 with pgvector extension available
- ✅ mcp_user has CREATEDB permission
- ✅ Refactor branch created from clean main
- ✅ Rollback procedures tested and verified
- ✅ All Phase 0B scripts executable and working

**Timeline:** 15 hours (2 days)

**Next Steps:**
1. Read PHASE-0-FOUNDATION.md section "Phase 0B" (lines 880-1469)
2. Read PHASE-0-REVIEW.md for critical fixes (especially issues #1-5, 8-9)
3. Create feature branch 004-multi-project-refactor
4. Execute Phase 0B steps with git micro-commits
5. Verify with PHASE-0-CHECKLIST.md

Ready to begin! Please confirm you understand the context and start with reading the Phase 0B section of PHASE-0-FOUNDATION.md.
```

---

## Additional Context for Claude

### Repository Information

**Repository Path:** `/Users/cliffclarke/Claude_Code/codebase-mcp`

**Current State:**
- Existing MCP server with 16 tools
- PostgreSQL database with 9 tables (work items, vendors, tasks, deployments, code chunks, etc.)
- FastMCP-based server at port 8001
- Python 3.11+, asyncpg, Pydantic

**Git State:**
- Current branch: master (clean)
- Recent commits focus on MCP evaluation and multi-project planning
- No uncommitted changes

### Critical Fixes Required

**From PHASE-0-REVIEW.md, these issues MUST be addressed:**

1. **Baseline Test Implementation** (Issue #2)
   - The `tests/performance/test_baseline.py` contains TODO placeholders
   - Must import actual `index_repository` implementation
   - Must set up proper database connection
   - Must clean database between runs

2. **Missing Parse Baseline Script** (Issue #8)
   - Create `scripts/parse_baseline.py` to extract metrics from pytest-benchmark JSON
   - Display key metrics: indexing time, search p95, files indexed

3. **Incomplete Emergency Rollback** (Issue #9)
   - Add database cleanup (drop any new test databases)
   - Add virtual environment cleanup
   - Add build artifacts cleanup

4. **Database Password Security** (Issue #7)
   - Note about using environment variables in production
   - Update `.gitignore` to exclude `.env` files

### Phase 0B Step-by-Step Checklist

**Section 1: Performance Baseline Collection (3 hours)**
- [ ] Create `scripts/collect_baseline.sh`
- [ ] Create `scripts/generate_test_repo.py`
- [ ] Create `scripts/parse_baseline.py` (FIX for Issue #8)
- [ ] Create `tests/performance/test_baseline.py` with actual implementation (FIX for Issue #2)
- [ ] Execute baseline collection
- [ ] Verify baseline meets targets (<60s indexing, <500ms search)
- [ ] Git commit: "chore(perf): add baseline collection scripts"
- [ ] Git commit: "test(perf): add baseline performance tests"

**Section 2: Refactor Branch Preparation (2 hours)**
- [ ] Ensure main is clean: `git checkout main && git status`
- [ ] Create refactor branch: `git checkout -b 004-multi-project-refactor`
- [ ] Create rollback tag: `git tag backup-before-refactor`
- [ ] Push tag: `git push origin backup-before-refactor`
- [ ] Create `scripts/emergency_rollback.sh` with enhanced cleanup (FIX for Issue #9)
- [ ] Git commit: "chore: add emergency rollback script"

**Section 3: Database Validation (2 hours)**
- [ ] Create `scripts/validate_db_permissions.sh`
- [ ] Check PostgreSQL version >= 14
- [ ] Check pgvector extension available
- [ ] Check CREATEDB permission for mcp_user
- [ ] Test dynamic database creation/deletion
- [ ] Execute validation script
- [ ] Git commit: "chore(db): add database permission validation"

**Section 4: Documentation Updates (3 hours)**
- [ ] Create `docs/REFACTORING-JOURNAL.md`
- [ ] Record baseline metrics in journal
- [ ] Update `README.md` with refactoring warning
- [ ] Document rollback procedures
- [ ] Git commit: "docs: add refactoring journal and update README"

**Section 5: Dependencies Update (2 hours)**
- [ ] Add `pytest-benchmark>=4.0.0` to `pyproject.toml`
- [ ] Reinstall dependencies: `pip install -e ".[dev]"`
- [ ] Git commit: "chore: add pytest-benchmark for performance testing"

**Section 6: Phase 0 Execution and Verification (3 hours)**
- [ ] Execute: `./scripts/validate_db_permissions.sh`
- [ ] Execute: `python scripts/generate_test_repo.py --files 10000 --output test_repos/baseline_repo`
- [ ] Execute: `./scripts/collect_baseline.sh`
- [ ] Verify: `ls -lh baseline-results.json`
- [ ] Parse results: `python scripts/parse_baseline.py baseline-results.json`
- [ ] Create `PHASE-0-CHECKLIST.md`
- [ ] Fill in baseline metrics in checklist
- [ ] Git commit: "chore: add Phase 0 completion checklist"
- [ ] Git tag: `v2.0.0-phase0-prep`

### Common Issues to Watch For

**Issue: Baseline Test Can't Import MCP Tools**
- **Symptom:** ImportError when importing `index_repository`
- **Solution:** Import from actual server module, not from MCP protocol
- **Example:** `from src.codebase_mcp.tools.indexing import index_repository_impl`

**Issue: PostgreSQL User Lacks CREATEDB**
- **Symptom:** Permission denied when validating database creation
- **Solution:** Grant permission: `psql -U postgres -c "ALTER ROLE mcp_user CREATEDB;"`

**Issue: pgvector Extension Not Found**
- **Symptom:** CREATE EXTENSION vector fails
- **Solution (macOS):** `brew install pgvector`, then restart PostgreSQL

**Issue: Test Repository Generation Slow**
- **Symptom:** Taking >5 minutes for 10,000 files
- **Solution:** Normal behavior, shows progress, don't interrupt

**Issue: Baseline Collection Fails Due to Missing Database**
- **Symptom:** asyncpg connection error
- **Solution:** Ensure test database exists: `createdb test_codebase_mcp`

**Issue: Emergency Rollback Script Not Executable**
- **Symptom:** Permission denied when running script
- **Solution:** `chmod +x scripts/emergency_rollback.sh`

### Verification Commands

After completing Phase 0B, run these commands to verify:

```bash
# 1. Verify branch state
git branch --show-current  # Should show: 004-multi-project-refactor
git log --oneline -5       # Should show Phase 0B commits

# 2. Verify rollback tag exists
git tag -l | grep backup   # Should show: backup-before-refactor

# 3. Verify baseline data
ls -lh baseline-results.json  # Should exist, >1KB
python scripts/parse_baseline.py baseline-results.json  # Should display metrics

# 4. Verify test repository
ls test_repos/baseline_repo/*.py | wc -l  # Should show: 10000

# 5. Verify database permissions
./scripts/validate_db_permissions.sh  # Should show all ✅

# 6. Verify scripts are executable
ls -l scripts/*.sh | grep -E '^-rwx'  # All should be executable

# 7. Verify checklist filled
cat PHASE-0-CHECKLIST.md  # Baseline metrics should be filled in
```

### Performance Baseline Expectations

**Indexing Time:**
- Target: <60 seconds for 10,000 files
- Typical: 30-45 seconds (depending on hardware)
- Warning if: >60 seconds (investigate before proceeding)

**Search Latency (p95):**
- Target: <500ms
- Typical: 200-350ms
- Warning if: >500ms (investigate before proceeding)

**Tool Count:**
- Current: 16 tools
- Post-refactor target: 2 tools (87.5% reduction)

**Lines of Code:**
- Current: ~4,500 LOC
- Post-refactor target: ~1,800 LOC (60% reduction)

### What Comes After Phase 0B

**Immediate Next Steps:**
1. Review Phase 0B outputs with project owner
2. Verify all success criteria met
3. Decision point: Proceed with Phase 1 refactoring or pause

**Phase 1: Remove Project Configuration Tool**
- Duration: 2 hours
- Removes: `get_project_configuration`, `update_project_configuration`
- Preserves: All functionality temporarily
- Git micro-commits: ~2 commits

**Phase 2: Remove Work Items (Core)**
- Duration: 4 hours
- Removes: `create_work_item`, `update_work_item`, `query_work_item`, `list_work_items`
- Database: Drops work_items table
- Git micro-commits: ~6 commits

### Emergency Contacts

If you encounter issues during Phase 0B:

1. **Check PHASE-0-REVIEW.md** for known issues and fixes
2. **Check IMPLEMENTATION-ROADMAP.md FAQ** section for common questions
3. **Review git history** for similar commits in other projects
4. **Use emergency rollback** if critical issues occur

### Final Verification Before Phase 1

Before proceeding to Phase 1 refactoring, ensure:

- [ ] All Phase 0B checklist items completed
- [ ] Baseline metrics recorded and within targets
- [ ] Rollback procedures tested (dry-run)
- [ ] Documentation updated and reviewed
- [ ] Branch pushed to remote for backup
- [ ] All scripts executable and verified
- [ ] No uncommitted changes

---

**Status:** Ready for execution
**Last Updated:** 2025-10-11
**Prepared By:** Claude Code Planning System
