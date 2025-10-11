# Phase 0B: Parallel Execution Plan

**Created:** 2025-10-11
**Status:** Ready for Execution
**Estimated Time Savings:** 4 hours (22% reduction: 18h → 14h)

---

## Overview

This document outlines the parallelization strategy for Phase 0B (codebase-mcp Preparation) using specialized subagents. Tasks are split into two waves:

- **Wave 1:** Parallel creation of scripts, documentation, and branch setup (4 concurrent subagents)
- **Wave 2:** Sequential execution of validation, baseline collection, and verification (main agent)

---

## Wave 1: Parallel Creation Phase (5 hours)

Launch these 4 subagents concurrently:

### Subagent 1: Python Scripts (python-wizard)

**Agent Type:** `python-wizard`
**Duration:** ~5 hours
**Branch:** `004-multi-project-refactor`

**Tasks:**
1. Create `scripts/generate_test_repo.py`
   - Generate deterministic test repository with N files
   - Use seed=42 for reproducibility
   - File sizes: 100-2000 lines each
   - Includes classes, functions, imports

2. Create `scripts/parse_baseline.py`
   - Parse `baseline-results.json` from pytest-benchmark
   - Display key metrics (indexing time, search latency p50/p95/p99)
   - Format output for documentation

3. Create `tests/performance/test_baseline.py`
   - Import real MCP server tools
   - `test_indexing_baseline()`: Measure indexing 10k files
   - `test_search_baseline()`: Measure search latency
   - Assert performance targets (<60s indexing, <500ms p95 search)
   - Use pytest-benchmark for accurate measurements

**Git Commits:**
```bash
git add scripts/generate_test_repo.py scripts/parse_baseline.py
git commit -m "chore(perf): add baseline collection scripts"

git add tests/performance/test_baseline.py
git commit -m "test(perf): add baseline performance tests"
```

**Reference:** PHASE-0-FOUNDATION.md lines 886-998

---

### Subagent 2: Bash Scripts (general-purpose)

**Agent Type:** `general-purpose`
**Duration:** ~3 hours
**Branch:** `004-multi-project-refactor`

**Tasks:**
1. Create `scripts/collect_baseline.sh`
   - Check if test_repos/baseline_repo exists, generate if needed
   - Run pytest with --benchmark-only and --benchmark-json
   - Call parse_baseline.py to display results
   - Make executable: `chmod +x`

2. Create `scripts/validate_db_permissions.sh`
   - Check PostgreSQL version (must be 14+)
   - Verify pgvector extension available
   - Test CREATEDB permission (create/drop temp database)
   - Test dynamic database creation with schema
   - Make executable: `chmod +x`

3. Create `scripts/emergency_rollback.sh`
   - Add pre-flight checks (confirm prompt)
   - Stash uncommitted changes
   - Checkout main branch
   - Reset to backup-before-refactor tag
   - Clean up any test databases
   - Make executable: `chmod +x`

**Git Commits:**
```bash
git add scripts/collect_baseline.sh
git commit -m "chore(perf): add baseline collection orchestration script"

git add scripts/validate_db_permissions.sh
git commit -m "chore(db): add database permission validation"

git add scripts/emergency_rollback.sh
git commit -m "chore: add emergency rollback script with pre-flight checks"
```

**Reference:** PHASE-0-FOUNDATION.md lines 888-1108

---

### Subagent 3: Documentation (general-purpose)

**Agent Type:** `general-purpose`
**Duration:** ~2 hours
**Branch:** `004-multi-project-refactor`

**Tasks:**
1. Create `docs/REFACTORING-JOURNAL.md`
   - Phase 0 section with goals, baseline metrics placeholders
   - Pre-refactor state (branch, tag, database architecture)
   - Sections for Phase 1-12 (to be filled during implementation)

2. Update `README.md`
   - Add refactoring warning banner at top
   - Current status section (Phase 0-12 checklist)
   - Rollback instructions section
   - Link to REFACTORING-JOURNAL.md

3. Create `PHASE-0-CHECKLIST.md`
   - Checklist of all Phase 0B deliverables
   - Baseline metrics recording section (to be filled after collection)
   - Sign-off section (YES/NO ready for Phase 1)

**Git Commits:**
```bash
git add docs/REFACTORING-JOURNAL.md
git commit -m "docs: add refactoring journal for progress tracking"

git add README.md
git commit -m "docs: update README with refactoring status and rollback instructions"

git add PHASE-0-CHECKLIST.md
git commit -m "chore: add Phase 0 completion checklist"
```

**Reference:** PHASE-0-FOUNDATION.md lines 1112-1264

---

### Subagent 4: Branch Setup (general-purpose)

**Agent Type:** `general-purpose`
**Duration:** ~1 hour
**Branch:** Creates `004-multi-project-refactor`

**Tasks:**
1. Verify main branch is clean
   - `git status` should show no uncommitted changes
   - `git pull origin main` to sync with remote

2. Create refactor branch
   - `git checkout -b 004-multi-project-refactor`

3. Create rollback tag
   - `git tag backup-before-refactor`
   - `git push origin backup-before-refactor`

4. Verify branch setup
   - Confirm branch created: `git branch --show-current`
   - Confirm tag exists: `git tag -l backup-before-refactor`

**Git Commits:**
```bash
# First commit on new branch
git commit --allow-empty -m "chore: initialize refactor branch with rollback tag"
```

**Reference:** PHASE-0-FOUNDATION.md lines 1002-1050

---

## Wave 2: Sequential Execution Phase (9 hours)

**Prerequisites:** All Wave 1 subagents completed successfully

Execute these tasks sequentially on the `004-multi-project-refactor` branch:

### Step 1: Update Dependencies (30 minutes)

```bash
# Update pyproject.toml to add pytest-benchmark
# Add to [project.optional-dependencies].dev:
#   "pytest-benchmark>=4.0.0",

git add pyproject.toml
git commit -m "chore: add pytest-benchmark for performance testing"

# Install dependencies
pip install -e ".[dev]"
```

**Reference:** PHASE-0-FOUNDATION.md lines 1181-1205

---

### Step 2: Database Validation (1 hour)

```bash
# Run validation script
./scripts/validate_db_permissions.sh

# Expected output:
# ✅ PostgreSQL version X.Y
# ✅ pgvector extension available
# ✅ mcp_user has CREATEDB permission
# ✅ Dynamic database creation works
# 🎉 Database validation complete!
```

**Troubleshooting:**
- If PostgreSQL < 14: Upgrade PostgreSQL
- If pgvector missing: `brew install pgvector` (macOS) or `apt install postgresql-14-pgvector` (Linux)
- If CREATEDB denied: `psql -U postgres -c "ALTER ROLE mcp_user CREATEDB;"`

---

### Step 3: Generate Test Repository (1 hour)

```bash
# Generate 10,000 file test repository
python scripts/generate_test_repo.py \
    --files 10000 \
    --output test_repos/baseline_repo

# Verify generation
ls -lh test_repos/baseline_repo | head -20
```

**Expected output:** 10,000 Python files (module_00000.py to module_09999.py)

---

### Step 4: Collect Performance Baseline (3 hours)

```bash
# Run baseline collection (includes indexing + search benchmarks)
./scripts/collect_baseline.sh

# Expected output:
# 📊 Collecting performance baseline for codebase-mcp...
# Running baseline benchmarks...
# ✅ Baseline collected: baseline-results.json
#
# Key metrics:
# Indexing time: XX.X seconds (target: <60s)
# Search p50: XXX ms
# Search p95: XXX ms (target: <500ms)
# Search p99: XXX ms
```

**Acceptance Criteria:**
- Indexing time < 60 seconds ✅
- Search p95 latency < 500ms ✅
- baseline-results.json created with valid JSON ✅

---

### Step 5: Fill Completion Checklist (30 minutes)

```bash
# Record baseline metrics in PHASE-0-CHECKLIST.md
# Fill in actual values from baseline-results.json

# Update checklist items:
# - [x] Performance baseline collected
# - [x] Test repository generated (10,000 files)
# - [x] Database permissions validated (CREATEDB)
# - [x] pgvector extension available
# - [x] Refactor branch created (004-multi-project-refactor)
# - [x] Rollback tag created (backup-before-refactor)
# - [x] Emergency rollback script tested
# - [x] Documentation updated
# - [x] Dependencies installed
# - [x] All Phase 0 scripts executable

git add PHASE-0-CHECKLIST.md baseline-results.json
git commit -m "chore: complete Phase 0 checklist with baseline metrics"
```

---

### Step 6: Test Emergency Rollback (1 hour)

```bash
# Test rollback procedure (non-destructive)
# This verifies rollback works before we need it

# 1. Note current commit
CURRENT_COMMIT=$(git rev-parse HEAD)

# 2. Make a test commit
echo "# Test" >> test_rollback.txt
git add test_rollback.txt
git commit -m "test: verify rollback procedure"

# 3. Test rollback script
./scripts/emergency_rollback.sh
# Enter "yes" when prompted

# 4. Verify we're back at backup tag
git log -1 --oneline

# 5. Return to refactor branch
git checkout 004-multi-project-refactor
git reset --hard $CURRENT_COMMIT

# 6. Clean up test file
rm -f test_rollback.txt
```

**Expected result:** Rollback script successfully reverts to backup-before-refactor tag

---

### Step 7: Create Phase 0 Tag (15 minutes)

```bash
# Tag Phase 0 completion
git tag v2.0.0-phase0-prep
git push origin 004-multi-project-refactor
git push origin v2.0.0-phase0-prep
```

---

### Step 8: Final Verification (2 hours)

**Verification Checklist:**

```bash
# 1. All scripts exist and are executable
ls -lh scripts/*.sh
ls -lh scripts/*.py

# 2. All documentation exists
ls -lh docs/REFACTORING-JOURNAL.md
ls -lh PHASE-0-CHECKLIST.md

# 3. Branch and tag exist
git branch --list 004-multi-project-refactor
git tag -l backup-before-refactor
git tag -l v2.0.0-phase0-prep

# 4. Baseline results exist
ls -lh baseline-results.json

# 5. Test repository exists
ls -lh test_repos/baseline_repo | wc -l  # Should be ~10,000

# 6. All tests pass
pytest tests/performance/test_baseline.py -v

# 7. Database validation passes
./scripts/validate_db_permissions.sh
```

---

## Success Criteria

### Phase 0B Complete When:

- ✅ All Wave 1 subagents completed successfully
- ✅ All Wave 2 sequential tasks completed
- ✅ Performance baseline collected and meets targets
- ✅ Database permissions validated (PostgreSQL 14+, pgvector, CREATEDB)
- ✅ Refactor branch created with rollback protection
- ✅ Emergency rollback tested and verified
- ✅ All documentation updated
- ✅ PHASE-0-CHECKLIST.md fully filled out with "Ready for Phase 1: YES"

---

## Timeline Summary

**Wave 1 (Parallel):** ~5 hours
- 4 subagents run concurrently
- Longest task determines duration
- Creates all scripts, docs, branch setup

**Wave 2 (Sequential):** ~9 hours
- Dependencies: 0.5h
- Database validation: 1h
- Test repo generation: 1h
- Baseline collection: 3h
- Checklist completion: 0.5h
- Rollback testing: 1h
- Tagging: 0.25h
- Final verification: 2h

**Total:** ~14 hours (vs. 18 hours sequential)
**Time Saved:** 4 hours (22% reduction)

---

## Risk Mitigation

### Wave 1 Risks

| Risk | Mitigation |
|------|------------|
| Subagent creates incorrect script | Code review before Wave 2, can regenerate quickly |
| Git conflicts between subagents | All work on same branch, different files, no conflicts expected |
| Subagent fails to complete | Restart individual subagent, doesn't block others |

### Wave 2 Risks

| Risk | Mitigation |
|------|------------|
| PostgreSQL version too old | Upgrade PostgreSQL before continuing |
| pgvector not installed | Install via package manager (documented) |
| CREATEDB permission denied | ALTER ROLE command provided in validation script |
| Baseline collection fails | Skip if test repo missing, documented in script |
| Performance targets not met | Document actual values, investigate before Phase 1 |

---

## Next Phase

After Phase 0B completion:
1. Review PHASE-0-CHECKLIST.md
2. Verify all acceptance criteria met
3. Navigate to `../phase-01-database-refactor/`
4. Read Phase 1 README before starting
5. Continue with multi-project database refactor

---

## References

- **PHASE-0-FOUNDATION.md:** Lines 880-1279 (Phase 0B detailed tasks)
- **PHASE-0-FINAL-PLAN.md:** Lines 308-314 (Phase 0B timeline)
- **PHASE-0-REVIEW.md:** Critical issues #1-5, 8-9 (fixes applied)
- **README.md:** Phase 0 overview and acceptance criteria

---

**Status:** Ready for Execution
**Last Updated:** 2025-10-11
**Execution Command:** Launch 4 parallel subagents, then run Wave 2 sequentially
