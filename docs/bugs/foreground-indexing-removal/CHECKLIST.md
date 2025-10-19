# Documentation Update Checklist: Foreground Indexing Removal

**Track progress as you update each file**

---

## 🔴 PHASE 1: Critical User-Facing (Week 1)

### Core Documentation
- [ ] `/README.md`
  - [ ] Update features list (line 11)
  - [ ] Replace all `index_repository` examples with background pattern
  - [ ] Update tool status table (lines 134-144)
  - [ ] Add breaking change notice
  - [ ] Test all code examples

- [ ] `/CLAUDE.md`
  - [ ] Update "Background Indexing" section (lines 115-143)
  - [ ] Replace foreground examples with background pattern
  - [ ] Update agent guidance for always-background indexing
  - [ ] Verify example code syntax

- [ ] `/SESSION_HANDOFF_MCP_TESTING.md`
  - [ ] Rename "Phase 2: Index Repository (Foreground)" to "Background" (line 97)
  - [ ] Replace tool call `index_repository` → `start_indexing_background` (line 99)
  - [ ] Add polling loop to test workflow (lines 100-145)
  - [ ] Update expected results to show job progression
  - [ ] Update success criteria for background pattern

### API & Tool Documentation
- [ ] `/docs/api/tool-reference.md`
  - [ ] DELETE entire `index_repository` section
  - [ ] ADD `start_indexing_background` section
  - [ ] ADD `get_indexing_status` section
  - [ ] ADD `cancel_indexing_background` section (if implemented)
  - [ ] Update breaking change notice at top
  - [ ] Add migration guide section
  - [ ] Test all example code

- [ ] `/docs/guides/TOOL_EXAMPLES.md`
  - [ ] Remove `index_repository` examples
  - [ ] Add comprehensive `start_indexing_background` examples
  - [ ] Add polling loop examples with error handling
  - [ ] Add timeout handling examples
  - [ ] Add cancellation examples (if available)
  - [ ] Show progress monitoring patterns

### Migration Guide
- [ ] **CREATE** `/docs/migration/foreground-to-background-indexing.md`
  - [ ] Introduction: What changed, why
  - [ ] Side-by-side code comparison (old vs new)
  - [ ] Step-by-step migration guide
  - [ ] Error handling examples
  - [ ] Timeout handling examples
  - [ ] FAQ section (10+ questions)
  - [ ] Troubleshooting section (5+ scenarios)
  - [ ] Rollback instructions
  - [ ] Test migration guide with real user

---

## 🟡 PHASE 2: Operations & Quickstarts (Week 1-2)

### Setup & Operations
- [ ] `/docs/guides/SETUP_GUIDE.md`
  - [ ] Update indexing workflow examples
  - [ ] Add note about indexing duration
  - [ ] Update expected output examples

- [ ] `/docs/operations/MCP-SERVER-DEPLOYMENT.md`
  - [ ] Update deployment test procedures
  - [ ] Update indexing validation steps
  - [ ] Add monitoring guidance for background jobs

- [ ] `/docs/operations/QUICK-RESTART-GUIDE.md`
  - [ ] Update indexing command examples
  - [ ] Add job status check commands
  - [ ] Update troubleshooting for hung jobs

- [ ] `/docs/operations/README-DEPLOYMENT.md`
  - [ ] Search for `index_repository` references
  - [ ] Replace with background pattern
  - [ ] Update deployment validation steps

- [ ] `/docs/operations/troubleshooting.md`
  - [ ] Add "Background Job Troubleshooting" section
  - [ ] Add "Job stuck in pending" scenario
  - [ ] Add "Job failed" scenario
  - [ ] Add "Poll loop never completes" scenario

### Quickstart Guides
- [ ] `/specs/001-build-a-production/quickstart.md`
  - [ ] Replace indexing examples with background pattern
  - [ ] Update validation steps

- [ ] `/specs/002-refactor-mcp-server/quickstart.md`
  - [ ] Replace indexing examples with background pattern
  - [ ] Update test procedures

- [ ] `/specs/007-remove-non-search/quickstart.md`
  - [ ] Replace indexing examples with background pattern
  - [ ] Update integration tests

- [ ] `/specs/008-multi-project-workspace/quickstart.md`
  - [ ] Replace multi-project indexing examples
  - [ ] Update project isolation validation

- [ ] `/specs/010-v2-documentation/quickstart.md`
  - [ ] Replace indexing examples with background pattern
  - [ ] Update documentation validation steps

---

## 🟢 PHASE 3: Architecture & Specs (Week 2)

### Architecture Documentation
- [ ] `/docs/architecture/ARCHITECTURE.md`
  - [ ] Update system architecture diagrams
  - [ ] Document background job flow
  - [ ] Remove foreground indexing sections

- [ ] `/docs/architecture/background-indexing.md`
  - [ ] **CRITICAL**: Remove any foreground fallback mentions
  - [ ] Update to background-only pattern
  - [ ] Add note about foreground removal

- [ ] `/docs/architecture/AUTO_SWITCH.md`
  - [ ] Update auto-switching examples with background pattern
  - [ ] Update project resolution flow

- [ ] `/docs/architecture/multi-project-design.md`
  - [ ] Update multi-project indexing examples
  - [ ] Update isolation documentation

- [ ] `/docs/architecture/api.md`
  - [ ] Update API design documentation
  - [ ] Remove foreground tool references

- [ ] `/docs/architecture/logging.md`
  - [ ] Update indexing log examples
  - [ ] Add background job logging patterns

### Spec 014: Background Indexing Feature
- [ ] `/specs/014-add-background-indexing/plan.md`
  - [ ] Add note about foreground removal
  - [ ] Update comparison sections

- [ ] `/specs/014-add-background-indexing/research.md`
  - [ ] Update foreground vs background comparison
  - [ ] Note migration path

- [ ] `/specs/014-add-background-indexing/tasks.md`
  - [ ] Check for foreground removal task
  - [ ] Update status if applicable

- [ ] `/specs/014-add-background-indexing/data-model.md`
  - [ ] Review for foreground references
  - [ ] Update if needed

### Other Active Specs
- [ ] `/specs/001-build-a-production/plan.md`
- [ ] `/specs/001-build-a-production/research.md`
- [ ] `/specs/001-build-a-production/tasks.md`
- [ ] `/specs/002-refactor-mcp-server/plan.md`
- [ ] `/specs/002-refactor-mcp-server/spec.md`
- [ ] `/specs/002-refactor-mcp-server/tasks.md`
- [ ] `/specs/002-refactor-mcp-server/data-model.md`
- [ ] `/specs/007-remove-non-search/plan.md`
- [ ] `/specs/007-remove-non-search/spec.md`
- [ ] `/specs/007-remove-non-search/research.md`
- [ ] `/specs/007-remove-non-search/data-model.md`
- [ ] `/specs/008-multi-project-workspace/plan.md`
- [ ] `/specs/008-multi-project-workspace/research.md`
- [ ] `/specs/010-v2-documentation/plan.md`
- [ ] `/specs/010-v2-documentation/spec.md`
- [ ] `/specs/010-v2-documentation/research.md`
- [ ] `/specs/011-performance-validation-multi/research.md`

---

## ⚪ PHASE 4: Archives (Week 3 - Optional)

### Add Deprecation Notes
- [ ] Add to bug investigation docs:
  - [ ] `/docs/bugs/mcp-indexing-failures/*.md` (13 files)
    - Header: `> **ARCHIVED**: This doc references deprecated foreground indexing. See migration guide.`

- [ ] Add to session artifacts:
  - [ ] `/docs/archive/session-artifacts/2025-10-06/*.md` (8+ files)
    - Header: `> **ARCHIVED SESSION**: Historical record, may contain outdated patterns.`

- [ ] Add to planning archives:
  - [ ] `/docs/mcp-split-plan/_archive/**/*.md` (50+ files)
    - Header: `> **ARCHIVED PLANNING**: Historical planning docs, not current implementation.`

### Review Old Specs (If Actively Referenced)
- [ ] `specs/003-database-backed-project/*`
- [ ] `specs/004-as-an-ai/*`
- [ ] `specs/005-create-vendor/*`
- [ ] `specs/006-database-schema-refactoring/*`
- [ ] `specs/009-v2-connection-mgmt/*`
- [ ] `specs/013-config-based-project-tracking/*`

---

## 🔧 PHASE 5: Code Cleanup (Separate Task)

### Remove Foreground Implementation
- [ ] Remove `index_repository` tool from MCP server
- [ ] Remove foreground indexing service code
- [ ] Update type hints and interfaces
- [ ] Remove foreground-specific tests
- [ ] Update integration tests to background pattern

### Test Updates
- [ ] Update all test files using `index_repository`
- [ ] Add background indexing test coverage
- [ ] Add polling loop tests
- [ ] Add timeout handling tests
- [ ] Add error handling tests

### Documentation Strings
- [ ] Update all docstrings mentioning foreground indexing
- [ ] Update type hints in function signatures
- [ ] Update module-level documentation

---

## ✅ PHASE 6: Validation (Week 3)

### Automated Checks
- [ ] Run: `grep -r "index_repository" README.md CLAUDE.md SESSION_HANDOFF* docs/api/ docs/guides/`
  - Expected: 0 matches in active docs
- [ ] Run: `grep -r "start_indexing_background" README.md docs/api/ docs/guides/`
  - Expected: Multiple matches
- [ ] Run: `find specs/ -name "quickstart.md" -exec grep -l "start_indexing_background" {} \;`
  - Expected: All quickstart files
- [ ] Run: `grep -r "start_indexing_background" docs/operations/`
  - Expected: Operations docs updated

### Manual Validation
- [ ] Test every code example in updated docs
- [ ] Validate migration guide with test user
- [ ] Run all updated quickstart guides
- [ ] Verify all links work (internal references)
- [ ] Check formatting (markdown rendering)

### Release Preparation
- [ ] Update `/CHANGELOG.md`
  - [ ] Add "BREAKING CHANGE: Removed foreground indexing"
  - [ ] Link to migration guide
  - [ ] List affected tools

- [ ] Update version number
  - [ ] Decide: v2.1.0 (minor) or v3.0.0 (major)
  - [ ] Update `pyproject.toml` or `setup.py`

- [ ] Create release notes
  - [ ] What changed
  - [ ] Why it changed
  - [ ] Migration path
  - [ ] Link to full documentation

- [ ] Tag release
  - [ ] `git tag -a v2.1.0 -m "Remove foreground indexing, background-only"`
  - [ ] `git push origin v2.1.0`

---

## 📊 Progress Tracking

**Total Tasks**: ~75
**Completed**: 0

**By Phase**:
- Phase 1 (Critical): 0/6 ⬜⬜⬜⬜⬜⬜
- Phase 2 (Operations): 0/10 ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜
- Phase 3 (Architecture): 0/20 ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜
- Phase 4 (Archives): 0/4 ⬜⬜⬜⬜
- Phase 5 (Code): 0/15 ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜
- Phase 6 (Validation): 0/20 ⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜

**Week 1 Goal**: Complete Phase 1 (6 tasks)
**Week 2 Goal**: Complete Phase 2-3 (30 tasks)
**Week 3 Goal**: Complete Phase 4-6 (39 tasks)

---

## 🎯 Daily Goals

### Day 1 (Week 1)
- [ ] Complete README.md update
- [ ] Complete CLAUDE.md update
- [ ] Complete SESSION_HANDOFF update

### Day 2 (Week 1)
- [ ] Complete API reference update
- [ ] Complete tool examples update

### Day 3 (Week 1)
- [ ] Create migration guide
- [ ] Test migration guide with user

### Day 4-5 (Week 1)
- [ ] Complete all 5 quickstart guides
- [ ] Complete setup guide

### Week 2
- [ ] Complete all operations docs (5 files)
- [ ] Complete all architecture docs (6 files)
- [ ] Complete spec 014 updates (4 files)
- [ ] Start other spec updates

### Week 3
- [ ] Finish spec updates
- [ ] Add archive deprecation notes
- [ ] Complete code cleanup
- [ ] Run full validation
- [ ] Prepare release

---

**Update this checklist as you progress. Mark completed items with [x].**
