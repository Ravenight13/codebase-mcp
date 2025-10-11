# Phase 00: Preparation

**Phase**: 00 - Preparation (Phases 0-1 from FINAL-IMPLEMENTATION-PLAN.md)
**Duration**: 2-3 hours
**Dependencies**: None (first phase)
**Status**: Ready to Execute

---

## Objective

Validate prerequisites, establish performance baseline, and prepare refactor branch with rollback points.

This phase ensures we have:
1. Baseline performance metrics to detect regression
2. Complete backup and rollback capability
3. Clean feature branch for refactoring work
4. Documented starting state for comparison

---

## Scope

### What's Included (Phase 0)

- **Prerequisite Validation**
  - PostgreSQL 14+ with pgvector extension
  - CREATEDB permission verification
  - Python 3.11+ environment check
  - Ollama with nomic-embed-text model

- **Performance Baseline Collection**
  - Generate test repository (10,000 files, seed=42)
  - Benchmark indexing time
  - Benchmark search latency (p50, p95, p99)
  - Document baseline metrics in `docs/baseline/performance-before.md`

- **Rollback Preparation**
  - Create database backup (`pg_dump`)
  - Create git tag: `pre-refactor`
  - Snapshot codebase (`tar.gz` archive)
  - Verify backup integrity

### What's Included (Phase 1)

- **Feature Branch Creation**
  - Create branch: `002-refactor-pure-search` from `main`
  - Capture baseline code metrics (LOC, test count, coverage)
  - Document in `docs/baseline/baseline-state.md`
  - Initial commit with baseline documentation

### What's NOT Included

- Any code changes to src/
- Database schema modifications
- Tool removal or feature work
- Performance optimization (that's Phase 06)

---

## Prerequisites

Before starting this phase:

1. **Clean working directory**:
   ```bash
   cd /Users/cliffclarke/Claude_Code/codebase-mcp
   git status  # Should show clean
   git pull origin main  # Sync with remote
   ```

2. **PostgreSQL running**:
   ```bash
   pg_isready  # Should return "accepting connections"
   psql -c "SELECT version();"  # Should show PostgreSQL 14+
   ```

3. **Python environment active**:
   ```bash
   python --version  # Should show 3.11+
   which uv  # Should show uv path
   ```

4. **Ollama running**:
   ```bash
   curl http://localhost:11434/api/tags  # Should list models
   # Verify nomic-embed-text is available
   ```

---

## Key Deliverables

### Phase 0 Deliverables

1. **Performance Baseline Report**: `docs/baseline/performance-before.md`
   - Indexing time for 10k files
   - Search p50/p95/p99 latency
   - Memory usage statistics
   - Database size

2. **Backup Files**:
   - `backups/backup-before-002.sql` (database dump)
   - `backups/codebase_mcp_snapshot.tar.gz` (code snapshot)
   - Git tag: `pre-refactor`

3. **Prerequisite Validation Report**: `docs/baseline/prerequisites.md`
   - PostgreSQL version and extensions
   - CREATEDB permission confirmed
   - Python/Ollama versions
   - Disk space available

### Phase 1 Deliverables

4. **Baseline State Report**: `docs/baseline/baseline-state.md`
   - Lines of code (total, src/, tests/)
   - Number of MCP tools (should be 16)
   - Test count and coverage
   - Database table count (should be 9)
   - Key metrics for comparison

5. **Feature Branch**:
   - Branch: `002-refactor-pure-search`
   - Initial commit with baseline docs
   - Clean from main with no divergence

---

## Acceptance Criteria

### Phase 0 Acceptance

- [ ] PostgreSQL health check passes (pg_isready)
- [ ] pgvector extension installed and verified
- [ ] CREATEDB permission confirmed (test with temp database)
- [ ] Performance baseline captured (10k file indexing + 100 searches)
- [ ] Baseline metrics documented in `docs/baseline/performance-before.md`
- [ ] Database backup created and validated (`pg_restore --list` succeeds)
- [ ] Git tag `pre-refactor` created and pushed
- [ ] Codebase snapshot created and verified (`tar -tzf` lists files)

### Phase 1 Acceptance

- [ ] Feature branch `002-refactor-pure-search` created from main
- [ ] Baseline code metrics captured (LOC, tests, coverage)
- [ ] Baseline state documented in `docs/baseline/baseline-state.md`
- [ ] Working directory clean (no uncommitted changes)
- [ ] Initial commit created: "chore(refactor): establish baseline for pure-search refactor"
- [ ] Branch pushed to origin
- [ ] All tests passing (baseline test suite)

---

## Execution Notes

### Generate Test Repository Script

You may need to create `scripts/generate_test_repo.py` if it doesn't exist. Expected behavior:
- Generates N files with realistic Python code patterns
- Uses deterministic seed for reproducibility
- File sizes: 100-2000 lines each
- Includes various code structures (classes, functions, imports)

### Benchmark Search Script

You may need to create `scripts/benchmark_search.py` if it doesn't exist. Expected behavior:
- Runs M search queries against indexed repository
- Measures p50, p95, p99 latency
- Outputs JSON: `{"p50": X, "p95": Y, "p99": Z, "queries": [...]}
- Queries should vary in complexity (simple strings, complex patterns)

### Database Backup Verification

After creating backup:
```bash
# Verify backup integrity
pg_restore --list backups/backup-before-002.sql | head -20

# Verify backup size (should be >1MB if database has data)
ls -lh backups/backup-before-002.sql
```

---

## Rollback Procedure

### If Phase 0 Fails

No rollback needed - no changes made to codebase or database.

### If Phase 1 Fails

```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp
git checkout main
git branch -D 002-refactor-pure-search
rm -f docs/baseline/baseline-state.md
```

---

## Materials in This Folder

- **HANDOFF-PHASE-0B-CODEBASE-MCP.md**: Self-contained execution prompt for Phase 0 (copy-paste into new chat)
- **PHASE-0-FINAL-PLAN.md**: Complete Phase 0 plan with all critical issues resolved
- **PHASE-0-FOUNDATION.md**: Original Phase 0 foundation planning
- **PHASE-0-REVIEW.md**: Planning review with critical issues identified
- **PHASE-0-ARCHITECTURAL-REVIEW.md**: Architectural validation and recommendations
- **planning-docs/**: Complete planning documentation from 01-codebase-mcp
  - **FINAL-IMPLEMENTATION-PLAN.md**: Complete refactoring plan (all 12 phases)
  - **constitution.md**: Constitutional principles
  - **ARCHITECTURAL-REVIEW.md**: Architecture validation
  - **PLANNING-REVIEW.md**: Planning critique with critical issues

### How to Use These Materials

**For /specify workflow**:
1. Read this README first (you're here)
2. Review PHASE-0-FINAL-PLAN.md for detailed technical approach
3. Use planning-docs/FINAL-IMPLEMENTATION-PLAN.md sections 1771-1862 as spec input
4. Run `/specify` with this context to create feature spec
5. Run `/plan`, `/tasks`, `/implement` as usual

**For direct execution** (without /specify):
1. Copy HANDOFF-PHASE-0B-CODEBASE-MCP.md into new chat
2. Claude will execute Phase 0 directly
3. Suitable for quick execution without spec-driven workflow

---

## Next Phase

After completing Phase 00:
- Verify all acceptance criteria met
- Push branch and tags to remote
- Navigate to `../phase-01-database-refactor/`
- Read that phase's README before starting

---

## Questions or Issues

- **Can't create database backup?** Check PostgreSQL permissions and disk space
- **Baseline metrics missing?** Verify scripts exist or implement them (see Execution Notes)
- **pgvector not installed?** Run `CREATE EXTENSION vector;` in PostgreSQL
- **CREATEDB permission denied?** Run `ALTER USER your_user CREATEDB;` as PostgreSQL superuser

---

## Related Documentation

- **Complete Phase 0-1 details**: See PHASE-0-FINAL-PLAN.md in this folder
- **Overall refactoring plan**: See planning-docs/FINAL-IMPLEMENTATION-PLAN.md lines 1771-1862
- **Prerequisites discussion**: See planning-docs/PLANNING-REVIEW.md (Critical Issue C4)

---

**Status**: Ready to Execute
**Last Updated**: 2025-10-11
**Estimated Time**: 2-3 hours
