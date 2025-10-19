# Project Cleanup Plan - 2025-10-19

## Executive Summary

Comprehensive cleanup to remove redundant documentation and organize project files properly.

**Impact**:
- Delete 32 bug planning docs (10.6k lines, 76% reduction)
- Move 25 root-level docs to proper locations
- Consolidate 4 deployment guides into 1
- Clean up 2 orphaned test directories
- Remove 144 .pyc cache files

---

## Phase 1: Bug Documentation Cleanup

### Delete Redundant Bug Docs (32 files, ~10,600 lines)

**Keep Pattern**: Bug report + Completion summary per bug
**Delete**: Planning docs, task lists, multiple summaries, reviewer notes

#### Foreground Indexing Removal (7 files):
```bash
rm docs/bugs/foreground-indexing-removal/DELETION-PLAN.md
rm docs/bugs/foreground-indexing-removal/DOCUMENTATION-UPDATE-PLAN.md
rm docs/bugs/foreground-indexing-removal/CHECKLIST.md
rm docs/bugs/foreground-indexing-removal/EXECUTION-CHECKLIST.md
rm docs/bugs/foreground-indexing-removal/UPDATE-SUMMARY.md
rm docs/bugs/foreground-indexing-removal/QUICK-REFERENCE.md
rm docs/bugs/foreground-indexing-removal/INDEX.md
```

#### Incremental Indexing Status Messages (5 files):
```bash
rm docs/bugs/incremental-indexing-status-messages/TASK_COMPLETION_SUMMARY.md
rm docs/bugs/incremental-indexing-status-messages/IMPLEMENTATION_COMPLETE.md
rm docs/bugs/incremental-indexing-status-messages/IMPLEMENTATION_SUMMARY.md
rm docs/bugs/incremental-indexing-status-messages/TESTING_GUIDE.md
rm docs/bugs/incremental-indexing-status-messages/QUICK_TEST.md
```

#### MCP Indexing Failures (11 files):
```bash
rm docs/bugs/mcp-indexing-failures/bug1-foreground-hang-plan.md
rm docs/bugs/mcp-indexing-failures/bug1-tasks.md
rm docs/bugs/mcp-indexing-failures/bug1-review.md
rm docs/bugs/mcp-indexing-failures/bug2-background-auto-create-plan.md
rm docs/bugs/mcp-indexing-failures/bug2-tasks.md
rm docs/bugs/mcp-indexing-failures/bug2-review.md
rm docs/bugs/mcp-indexing-failures/bug3-error-status-plan.md
rm docs/bugs/mcp-indexing-failures/bug3-tasks.md
rm docs/bugs/mcp-indexing-failures/bug3-review.md
rm docs/bugs/mcp-indexing-failures/WORKFLOW-MCP-RETEST-GUIDE.md
rm docs/bugs/mcp-indexing-failures/QUICK-TEST-PROMPTS.md
```

#### Project Resolution Secondary Call (8 files):
```bash
rm docs/bugs/project-resolution-secondary-call/architect-review.md
rm docs/bugs/project-resolution-secondary-call/reviewer1-session-flow.md
rm docs/bugs/project-resolution-secondary-call/reviewer2-registry-sync.md
rm docs/bugs/project-resolution-secondary-call/reviewer3-config-caching.md
rm docs/bugs/project-resolution-secondary-call/fix1-ctx-parameter-DONE.md
rm docs/bugs/project-resolution-secondary-call/fix2-registry-sync-DONE.md
rm docs/bugs/project-resolution-secondary-call/fix3-cache-interface-DONE.md
rm docs/bugs/project-resolution-secondary-call/fix4-tests-DONE.md
```

Also add .summary.txt to .gitignore:
```bash
rm docs/bugs/foreground-indexing-removal/.summary.txt
```

**Git Commit**:
```bash
git add -u docs/bugs/
git commit -m "docs(cleanup): remove 32 redundant bug documentation files

- Remove planning/task/review files from completed bug fixes
- Keep only essential bug reports and completion summaries per directory
- Reduces documentation from 42 files to 10 files (76% reduction)
- Deleted files: planning docs, task lists, checklists, multiple summaries

Retained pattern: Bug report + Completion summary per bug
Rationale: Principle I (Simplicity Over Features) applies to docs"
```

---

## Phase 2: Root-Level Documentation Cleanup

### Move 25 Files to Proper Locations

#### Session Handoffs → docs/session-handoffs/
```bash
git mv SESSION_HANDOFF_MCP_TESTING.md docs/session-handoffs/2025-10-18-mcp-testing.md
```

#### Bug Reports → docs/bugs/
```bash
mkdir -p docs/bugs/project-resolution-auto-create
git mv BUG_FIX_SUMMARY.md docs/bugs/project-resolution-auto-create/BUG_FIX_SUMMARY.md
```

#### Operations → docs/operations/
```bash
git mv DEPLOYMENT-GUIDE-CREATED.md docs/operations/DEPLOYMENT-GUIDE-SUMMARY.md
```

#### Implementation Summaries → docs/task-reports/
```bash
git mv IMPLEMENTATION_SUMMARY.md docs/task-reports/
git mv IMPLEMENTATION_SUMMARY_test_indexing_perf.md docs/task-reports/
git mv T004-T005_IMPLEMENTATION_SUMMARY.md docs/task-reports/
git mv T021_IMPLEMENTATION_SUMMARY.md docs/task-reports/
git mv T034-T037_SUMMARY.md docs/task-reports/
git mv T045_EXECUTION_SUMMARY.md docs/task-reports/
git mv T045_VALIDATION_REPORT.md docs/task-reports/
git mv TASK_1.4_COMPLETION_SUMMARY.md docs/task-reports/
git mv TASK_1.5_SUMMARY.md docs/task-reports/
git mv TASK_2_2_COMPLETION_SUMMARY.md docs/task-reports/
git mv VALIDATION_SUMMARY_T025_T036_T047.md docs/task-reports/
git mv INFRASTRUCTURE_FIXES_COMPLETE.md docs/task-reports/
git mv REFACTORING_COMPLETE.md docs/task-reports/
git mv TEST_RESULTS_VERIFICATION.md docs/task-reports/
```

#### Testing → docs/testing/
```bash
git mv AUTO_SWITCH_TEST_REPORT.md docs/testing/
git mv AUTO_SWITCH_RETEST_REPORT.md docs/testing/
git mv MCP_TOOLS_TEST_PROMPT.md docs/testing/
git mv REAL_PROJECT_TEST_PROMPTS.md docs/testing/
git mv TESTING_PROMPTS.md docs/testing/
```

#### Architecture → docs/architecture/
```bash
git mv CODEBASE_MCP_ANALYSIS.md docs/architecture/MULTI_PROJECT_TRACKING_ANALYSIS.md
```

#### Quick Reference → docs/
```bash
git mv QUICK_REFERENCE.md docs/QUICK_REFERENCE.md
```

**Git Commit**:
```bash
git add .
git commit -m "docs(organize): move 25 root-level docs to proper directories

- Move session handoffs to docs/session-handoffs/
- Move bug reports to docs/bugs/
- Move task reports to docs/task-reports/
- Move testing docs to docs/testing/
- Move architecture docs to docs/architecture/

Root now contains only README.md and CLAUDE.md (project essentials)
93% reduction in root-level documentation clutter"
```

---

## Phase 3: Test Directory Cleanup

### Delete Orphaned Test Directories
```bash
rm -rf tests/validation/
rm -rf tests/integration/observability/
```

### Clean Python Cache Files
```bash
find tests -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find tests -name "*.pyc" -delete
```

**Git Commit**:
```bash
git add -u tests/
git commit -m "test(cleanup): remove orphaned test directories and cache files

- Delete tests/validation/ (orphaned from unmerged branch)
- Delete tests/integration/observability/ (empty directory)
- Remove 144 .pyc files and 16 __pycache__ directories

Note: tests/contract/test_tool_registration.py and test_schema_generation.py
need updates (reference removed tools) - will address in separate commit"
```

---

## Phase 4: Operations Documentation Consolidation (DEFERRED)

**Recommendation**: Consolidate 4 deployment guides into 1
**Effort**: 4-6 hours
**Files**:
- docs/operations/MCP-SERVER-DEPLOYMENT.md
- docs/operations/README-DEPLOYMENT.md
- docs/operations/QUICK-RESTART-GUIDE.md
- docs/operations/DEPLOYMENT-TROUBLESHOOTING-FLOWCHART.md

**Status**: DEFERRED to separate task (requires careful consolidation and testing)

---

## Phase 5: Session Handoff Archiving (DEFERRED)

**Recommendation**: Archive completed session handoff
```bash
mkdir -p docs/session-handoffs/archive
git mv docs/session-handoffs/2025-10-19-enhanced-error-handling-session.md \
       docs/session-handoffs/archive/
```

**Status**: DEFERRED (low priority, session still recent)

---

## Summary

### Immediate Cleanup (Phases 1-3)
- **Files Deleted**: 32 bug docs + 2 test dirs + 1 .summary.txt
- **Files Moved**: 25 root-level docs
- **Cache Cleaned**: 144 .pyc files, 16 __pycache__ dirs
- **Total Commits**: 3 atomic commits
- **Estimated Time**: 30 minutes

### Deferred (Phases 4-5)
- Deployment guide consolidation (4-6 hours)
- Session handoff archiving (5 minutes)

### Final State
- **Root directory**: 2 files (README.md, CLAUDE.md)
- **Bug docs**: 10 essential files (was 42)
- **Tests**: Clean, no orphans, no cache
- **All historical data preserved in git history**

---

## Constitutional Compliance

✅ **Principle I: Simplicity Over Features**
- Applies to documentation as well as code
- Remove redundant planning artifacts
- Keep only essential reference material

✅ **Principle V: Production Quality**
- Well-organized documentation structure
- Easy to find information
- Reduced maintenance burden

✅ **Principle X: Git Micro-Commit Strategy**
- 3 atomic commits for 3 distinct cleanup operations
- Each commit is self-contained and reversible
- Clear commit messages explaining rationale

---

**Status**: Ready for execution
**Risk**: Low (all files in git history, reversible)
**Next**: Execute Phases 1-3
