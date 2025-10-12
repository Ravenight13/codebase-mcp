# MCP Split Project: Implementation Roadmap

## Document Purpose

This roadmap provides a complete, step-by-step guide for executing the MCP split project from planning to production. All subagent reviews are complete, all critical issues resolved, and both MCPs are ready for implementation.

---

## Project Status: READY FOR IMPLEMENTATION ✅

**Planning Complete:** 10 subagents executed in parallel
**Critical Issues:** All 10 resolved
**Architectural Reviews:** Both MCPs approved
**Constitutional Compliance:** 100%
**Documentation:** 100% complete

---

## Quick Start

### Phase 0: Foundation Setup (Week 0)
```bash
# Read Phase 0 plan first
cat docs/mcp-split-plan/PHASE-0-FOUNDATION.md

# Start with workflow-mcp foundation
mkdir -p /Users/cliffclarke/Claude_Code/workflow-mcp
cd /Users/cliffclarke/Claude_Code/workflow-mcp
git init

# Follow Phase 0A checklist (25 hours)
# - Repository initialization
# - FastMCP server boilerplate
# - Database setup scripts
# - CI/CD pipeline
# - Documentation

# Parallel: codebase-mcp preparation
cd /Users/cliffclarke/Claude_Code/codebase-mcp
git checkout -b 004-multi-project-refactor

# Follow Phase 0B checklist (15 hours)
# - Performance baseline collection
# - Database validation
# - Rollback procedures
```

### For codebase-mcp Refactoring (After Phase 0):
```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp
# Already on branch: 004-multi-project-refactor

# Read the final plan
cat docs/mcp-split-plan/01-codebase-mcp/FINAL-IMPLEMENTATION-PLAN.md

# Use the /specify command
cat docs/mcp-split-plan/01-codebase-mcp/specify-prompt.txt | pbcopy
# Then: /specify [paste]
```

### For workflow-mcp Creation (After Phase 0):
```bash
cd /Users/cliffclarke/Claude_Code/workflow-mcp
git checkout -b 001-project-management-core

# Read the final plan (from codebase-mcp docs)
cat /Users/cliffclarke/Claude_Code/codebase-mcp/docs/mcp-split-plan/02-workflow-mcp/FINAL-IMPLEMENTATION-PLAN.md

# Use the /specify command
cat /Users/cliffclarke/Claude_Code/codebase-mcp/docs/mcp-split-plan/02-workflow-mcp/specify-prompt.txt | pbcopy
# Then: /specify [paste]
```

---

## Implementation Sequence (Modified Sequential)

### Phase 0: Foundation Setup (Week 0)

**Goal:** Establish complete infrastructure foundation for both MCPs before feature implementation

**Why First:** Prevents infrastructure issues mid-implementation, enables TDD, validates database permissions

**Deliverables:**

**Phase 0A: workflow-mcp Foundation (25 hours)**
- Repository initialization with proper structure
- FastMCP server boilerplate with health check
- Database setup scripts (PostgreSQL + CREATEDB validation)
- CI/CD pipeline skeleton (GitHub Actions)
- Development tools (Makefile, VSCode settings, linting)
- Comprehensive documentation (README, CONTRIBUTING)

**Phase 0B: codebase-mcp Preparation (15 hours, parallel)**
- Performance baseline collection (indexing + search)
- Test repository generation (10,000 files)
- Database permission validation (CREATEDB, pgvector)
- Refactor branch creation (004-multi-project-refactor)
- Rollback procedures (backup tag + emergency script)
- Documentation updates (refactoring journal)

**Acceptance Criteria:**
- ✅ workflow-mcp server starts and health check returns 200 OK
- ✅ workflow-mcp CI/CD pipeline runs and passes
- ✅ codebase-mcp baseline collected and meets targets (<60s indexing, <500ms search)
- ✅ Both databases validated with CREATEDB permission
- ✅ Rollback procedures tested and documented
- ✅ All Phase 0 scripts executable and documented

**Timeline:** 1 week (40 hours total, can be parallelized)

---

### Phase 1: workflow-mcp Core (Weeks 1-3)

**Goal:** Build project management foundation + minimal entity system

**Why First:** codebase-mcp needs to query workflow-mcp for active project

**Deliverables:**
- Registry database with projects table
- `create_project`, `switch_active_project`, `get_active_project`, `list_projects`
- Minimal entity system: `register_entity_type`, `create_entity`, `query_entities`
- Connection pool with LRU eviction (max 50 active pools)
- Database lifecycle with transactional rollback

**Acceptance Criteria:**
- ✅ Can create commission project with "vendor" entity type
- ✅ Can create TTRPG project with "game_mechanic" entity type
- ✅ Projects are completely isolated (different databases)
- ✅ Connection pools evict after 50 projects
- ✅ codebase-mcp can query active project via registry

**Timeline:** 3 weeks (120 hours)

**Note:** Starts after Phase 0 completion

---

### Phase 2: codebase-mcp Refactor (Weeks 4-6)

**Goal:** Remove non-search features, add multi-project support

**Prerequisites:** workflow-mcp Phase 1 complete and deployed

**Deliverables:**
- Remove work items, vendors, tasks, deployments (16 → 2 tools)
- Add multi-project support to `index_repository`, `search_code`
- Query workflow-mcp for active project (with graceful fallback)
- Database-per-project connection management
- Performance baseline + regression tests

**Acceptance Criteria:**
- ✅ Only 2 tools remain: `index_repository`, `search_code`
- ✅ Multi-project isolation verified (20 projects concurrent search)
- ✅ Performance: <500ms search p95, <60s indexing 10k files
- ✅ Integration: Queries workflow-mcp successfully
- ✅ Constitutional compliance: 100%

**Timeline:** 3 weeks (37 hours + testing)

---

### Phase 3: workflow-mcp Complete (Weeks 7-9)

**Goal:** Add work items, tasks, deployments, entity enhancements

**Prerequisites:** codebase-mcp refactor complete

**Deliverables:**
- Work item hierarchy (project/session/task/research)
- Task management with status tracking
- Deployment tracking with relationships
- Entity enhancements (relationships, advanced queries)
- Schema evolution strategy (additive-only)
- Performance benchmarks in CI

**Acceptance Criteria:**
- ✅ Full work item hierarchy with 5-level depth
- ✅ Generic entity system supports any domain
- ✅ Commission + TTRPG projects work independently
- ✅ Performance: <50ms switch, <200ms work items, <100ms entities
- ✅ All 22 user stories satisfied

**Timeline:** 3 weeks (estimates TBD after Phase 1)

---

## Total Timeline: 10 Weeks

| Phase | Duration | Deliverable | Dependency |
|-------|----------|-------------|------------|
| Phase 0 | Week 0 | Foundation Setup | None |
| Phase 1 | Weeks 1-3 | workflow-mcp Core | Phase 0 |
| Phase 2 | Weeks 4-6 | codebase-mcp Refactor | Phase 1 |
| Phase 3 | Weeks 7-9 | workflow-mcp Complete | Phase 2 |

---

## Documentation Structure

```
/docs/mcp-split-plan/
├── README.md                          ← Executive summary (YOU ARE HERE)
├── IMPLEMENTATION-ROADMAP.md          ← This file
├── PHASE-0-FOUNDATION.md              ← Phase 0 detailed plan ⭐
├── PHASE-0-REVIEW.md                  ← Phase 0 planning review
├── PHASE-0-ARCHITECTURAL-REVIEW.md    ← Phase 0 architectural review
│
├── 00-architecture/
│   ├── overview.md                    ← System architecture diagram
│   ├── database-design.md             ← PostgreSQL schemas + indexes
│   ├── connection-management.md       ← ProjectConnectionManager pattern
│   ├── entity-system.md               ← JSONB + JSON Schema design
│   └── deployment-config.md           ← Port config, env vars, systemd
│
├── 01-codebase-mcp/
│   ├── README.md                      ← MCP purpose and scope
│   ├── constitution.md                ← 11 constitutional principles
│   ├── user-stories.md                ← 8 user stories with acceptance criteria
│   ├── specify-prompt.txt             ← Ready for /specify command ⭐
│   ├── tech-stack.md                  ← Python, PostgreSQL, FastMCP
│   ├── refactoring-plan.md            ← File-by-file removal plan
│   ├── implementation-phases.md       ← 12 phases with git strategy
│   ├── PLANNING-REVIEW.md             ← Planning review (5 critical issues)
│   ├── ARCHITECTURAL-REVIEW.md        ← Architecture review (4 recommendations)
│   └── FINAL-IMPLEMENTATION-PLAN.md   ← Final plan (all issues resolved) ⭐
│
├── 02-workflow-mcp/
│   ├── README.md                      ← MCP purpose and scope
│   ├── constitution.md                ← 12 constitutional principles
│   ├── user-stories.md                ← 22 user stories with acceptance criteria
│   ├── specify-prompt.txt             ← Ready for /specify command ⭐
│   ├── tech-stack.md                  ← Python, PostgreSQL, JSONB, FastMCP
│   ├── entity-system-examples.md      ← Vendor vs game mechanic examples
│   ├── implementation-phases.md       ← Phase 1 + Phase 3 breakdown
│   ├── PLANNING-REVIEW.md             ← Planning review (5 critical issues)
│   ├── ARCHITECTURAL-REVIEW.md        ← Architecture review (6 recommendations)
│   └── FINAL-IMPLEMENTATION-PLAN.md   ← Final plan (all issues resolved) ⭐
│
└── 03-orchestration/
    ├── subagent-workflow.md           ← 4-step review process
    ├── git-strategy.md                ← Micro-commits + Conventional Commits
    ├── parallel-execution-plan.md     ← When to parallelize subagents
    └── testing-strategy.md            ← Minimal but effective testing
```

**⭐ Key Files:**
- `PHASE-0-FOUNDATION.md` - Foundation setup guide (must complete first)
- `specify-prompt.txt` - Copy-paste into `/specify` command
- `FINAL-IMPLEMENTATION-PLAN.md` - Complete implementation guide with all issues resolved

---

## Critical Issues Resolved

### codebase-mcp (5 issues)

| Issue | Resolution | Phase |
|-------|-----------|-------|
| C1: Database naming strategy incomplete | ProjectIDValidator + SQL injection prevention | Phase 0 |
| C2: workflow-mcp error handling underspecified | Error categorization enum + enhanced messages | Phase 3 |
| C3: No rollback strategy | Per-phase rollback + emergency script | All phases |
| C4: Performance baseline missing | Baseline capture + regression detection | Phase 0, 11 |
| C5: Concurrent access patterns undefined | Advisory locks + stress tests | Phase 11 |

### workflow-mcp (5 issues)

| Issue | Resolution | Phase |
|-------|-----------|-------|
| C1: Schema evolution strategy missing | Additive-only policy + schema versioning | Phase 1 |
| C2: Connection pool exhaustion risk | LRU eviction (max 50 active pools) | Phase 1 |
| C3: Phase 1 deliverable value unclear | Move minimal entity system to Phase 1 | Phase 1 |
| C4: Database creation failure rollback missing | Transactional creation + automatic rollback | Phase 1 |
| C5: Performance measurement strategy missing | pytest-benchmark + CI integration | Phase 1 |

**All 10 critical issues resolved** with specific implementations and verification steps.

---

## Architectural Recommendations Integrated

### codebase-mcp (4 recommendations)
- ✅ Connection pool limits (MAX_PROJECTS=50)
- ✅ PostgreSQL production config (max_connections=1200)
- ✅ Enhanced error messages (workflow-mcp failure modes)
- ✅ Multi-tenant stress tests (20 projects concurrent)

### workflow-mcp (6 recommendations)
- ✅ LRU pool eviction (250MB memory vs 500MB)
- ✅ Schema versioning for entity types
- ✅ Entity relationship limitations documented
- ✅ First-time pool creation latency clarified
- ✅ Cross-MCP integration examples
- ✅ Automated backup strategy

---

## Development Workflow (Per MCP)

### Step 1: Specification Phase

```bash
# Use the prepared specify-prompt.txt
/specify [paste content from specify-prompt.txt]

# This creates: specs/###-feature/spec.md
```

**Output:** `spec.md` with WHAT/WHY (no HOW)

---

### Step 2: Clarification Phase

```bash
/clarify

# Answer clarification questions (max 5)
```

**Output:** Updated `spec.md` with resolved ambiguities

---

### Step 3: Planning Phase

```bash
/plan

# This generates:
# - research.md
# - data-model.md
# - contracts/
# - quickstart.md
# - plan.md (Phase 0-1 complete, Phase 2 described)
```

**Output:** Complete technical design artifacts

---

### Step 4: Task Generation

```bash
/tasks

# This generates: tasks.md (dependency-ordered)
```

**Output:** Actionable task breakdown with `[P]` parallel markers

---

### Step 5: Implementation

```bash
/implement

# Orchestrator executes tasks.md
# Marks completed tasks with [X]
# Git micro-commits after each task
```

**Output:** Production-ready MCP with tests passing

---

## Git Strategy

### Branch Naming
```
###-feature-name

Examples:
004-multi-project-refactor  (codebase-mcp)
001-project-management-core (workflow-mcp)
002-generic-entity-system   (workflow-mcp)
```

### Commit Strategy

**Format:** `type(scope): description`

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `refactor` - Code restructuring
- `test` - Test addition/modification
- `docs` - Documentation
- `perf` - Performance improvement
- `chore` - Maintenance

**Examples:**
```bash
git commit -m "feat(search): add project_id filter to search_code"
git commit -m "test(search): add multi-project isolation tests"
git commit -m "refactor(connection): extract project resolution helper"
git commit -m "fix(search): handle missing active project gracefully"
git commit -m "docs(api): update search_code tool documentation"
```

**Micro-Commit Cadence:** After each completed task in tasks.md

---

## Testing Strategy

### Minimal but Effective

**What We Test:**
1. MCP protocol compliance (tool registration, schema, errors)
2. Core functionality (index → search, project lifecycle)
3. Basic error handling (missing project, timeout, invalid input)
4. Performance targets (p95 latency, indexing time)

**What We DON'T Test:**
- Exhaustive edge cases (trust Pydantic)
- Private methods (test public API)
- Implementation details (test behavior)

### Test Execution

```bash
# During development
pytest tests/unit -v                    # Fast feedback

# Before PR
pytest tests/ -v --cov=src --cov-report=term-missing

# Performance validation
pytest tests/performance -v --benchmark-only
```

### CI Integration

```yaml
# .github/workflows/ci.yml
- run: pytest tests/unit
- run: pytest tests/integration
- run: pytest tests/performance --benchmark-compare
```

---

## Performance Targets

### codebase-mcp
- **Search latency:** <500ms (p95)
- **Indexing time:** <60s for 10,000 files
- **Multi-tenant:** 20 projects concurrent search without degradation
- **Connection pool:** Max 260 connections (50 projects × 5 + 10 registry)

### workflow-mcp
- **Project switching:** <50ms (after pool created)
- **Project creation:** <200ms (including database creation)
- **Work item operations:** <200ms (p95, 5-level hierarchy)
- **Entity queries:** <100ms (p95, 10,000+ entities with GIN index)
- **Connection pool:** Max 260 connections (50 active pools × 5 + 10 registry)

---

## Risk Mitigation

### High-Priority Risks

| Risk | Mitigation | Phase |
|------|-----------|-------|
| Connection pool exhaustion | LRU eviction (max 50) | Phase 1 (workflow) |
| SQL injection in project_id | Pydantic validation + CHECK constraints | Phase 0 (codebase) |
| workflow-mcp unavailable | Graceful fallback to explicit project_id | Phase 3 (codebase) |
| Schema evolution breaking changes | Additive-only policy enforced | Phase 1 (workflow) |
| Performance regression | Baseline + automated regression tests | Phase 0, 11 (codebase) |

---

## Success Criteria

### codebase-mcp
- ✅ Only 2 tools remain: `index_repository`, `search_code`
- ✅ 60% code reduction (4,500 → 1,800 LOC)
- ✅ 87.5% tool reduction (16 → 2 tools)
- ✅ Multi-project isolation verified
- ✅ Performance targets met (<500ms search, <60s indexing)
- ✅ Constitutional compliance: 100%
- ✅ All tests passing (unit, integration, protocol, performance)

### workflow-mcp
- ✅ Complete project management (create/switch/list/delete)
- ✅ Generic entity system works for any domain
- ✅ Commission + TTRPG projects independent
- ✅ Work item hierarchy (5 levels deep)
- ✅ Performance targets met (<50ms switch, <200ms work items)
- ✅ Constitutional compliance: 100%
- ✅ All 22 user stories satisfied

### Integration
- ✅ Both MCPs run simultaneously (ports 8001, 8002)
- ✅ codebase-mcp queries workflow-mcp successfully
- ✅ Project switching affects both MCPs
- ✅ No cross-project data leakage
- ✅ Easy backup/restore per project (pg_dump one database)

---

## Next Steps (You Are Here)

### Immediate Actions

1. **Review Documentation**
   - [ ] Read this roadmap completely
   - [ ] Review executive summary (README.md)
   - [ ] Review Phase 0 plan (PHASE-0-FOUNDATION.md) ⭐
   - [ ] Review architecture overview (00-architecture/overview.md)

2. **Execute Phase 0: Foundation Setup**
   - [ ] Start with Phase 0A: workflow-mcp foundation (25 hours)
   - [ ] Parallel: Phase 0B: codebase-mcp preparation (15 hours)
   - [ ] Verify all Phase 0 acceptance criteria met

3. **Backup Current State**
   ```bash
   cd /Users/cliffclarke/Claude_Code/codebase-mcp
   git tag backup-before-split
   git push origin backup-before-split
   ```

4. **Begin Phase 0A: workflow-mcp Foundation**
   ```bash
   mkdir -p /Users/cliffclarke/Claude_Code/workflow-mcp
   cd /Users/cliffclarke/Claude_Code/workflow-mcp
   git init

   # Follow Phase 0A checklist from PHASE-0-FOUNDATION.md
   # - Repository initialization (2 hours)
   # - Project configuration (3 hours)
   # - Base directory structure (2 hours)
   # - FastMCP server boilerplate (4 hours)
   # - Database setup scripts (4 hours)
   # - CI/CD pipeline skeleton (3 hours)
   # - Development tools configuration (2 hours)
   # - Documentation (3 hours)
   # - Installation and verification (2 hours)
   ```

5. **Parallel: Begin Phase 0B: codebase-mcp Preparation**
   ```bash
   cd /Users/cliffclarke/Claude_Code/codebase-mcp
   git checkout -b 004-multi-project-refactor
   git tag backup-before-refactor
   git push origin backup-before-refactor

   # Follow Phase 0B checklist from PHASE-0-FOUNDATION.md
   # - Performance baseline collection (3 hours)
   # - Refactor branch preparation (2 hours)
   # - Database validation (2 hours)
   # - Documentation updates (3 hours)
   # - Dependencies update (2 hours)
   # - Phase 0 execution and verification (3 hours)
   ```

6. **After Phase 0 Complete: Begin Phase 1**
   ```bash
   # workflow-mcp
   cd /Users/cliffclarke/Claude_Code/workflow-mcp
   git checkout -b 001-project-management-core

   # Copy specify prompt
   cat /Users/cliffclarke/Claude_Code/codebase-mcp/docs/mcp-split-plan/02-workflow-mcp/specify-prompt.txt | pbcopy

   # Run /specify command
   /specify [paste]
   ```

---

## Subagent Execution Summary

### Batch 1: Foundation (Parallel)
- ✅ Architecture documentation (5 files)
- ✅ codebase-mcp initial plan (8 files)
- ✅ workflow-mcp initial plan (7 files)
- ✅ Orchestration documentation (4 files)

**Total:** 24 files created in parallel (~60 minutes)

### Batch 2: Reviews (Parallel)
- ✅ codebase-mcp planning review (5 critical issues found)
- ✅ codebase-mcp architectural review (4 recommendations)
- ✅ workflow-mcp planning review (5 critical issues found)
- ✅ workflow-mcp architectural review (6 recommendations)

**Total:** 4 review files created in parallel (~45 minutes)

### Batch 3: Final Plans (Parallel)
- ✅ codebase-mcp final implementation plan (all 5 critical issues resolved)
- ✅ workflow-mcp final implementation plan (all 5 critical issues resolved)

**Total:** 2 final plans created in parallel (~40 minutes)

### Total Execution
- **10 subagents** executed across 3 batches
- **30 documents** created (~300 pages, 150,000+ words)
- **10 critical issues** identified and resolved
- **10 architectural recommendations** integrated
- **~2.5 hours** total (vs ~5 hours if sequential)

---

## Document Statistics

| Category | Files | Lines | Words |
|----------|-------|-------|-------|
| Architecture | 5 | 3,488 | ~35,000 |
| codebase-mcp | 10 | 4,200+ | ~45,000 |
| workflow-mcp | 10 | 4,066+ | ~50,000 |
| Orchestration | 4 | ~3,000 | ~20,000 |
| **Total** | **29** | **~15,000** | **~150,000** |

---

## Constitutional Compliance

### codebase-mcp: 11/11 Principles ✅

All principles fully compliant after critical issue resolution:
- I. Simplicity Over Features (87.5% tool reduction)
- II. Local-First Architecture (Ollama + PostgreSQL)
- III. Protocol Compliance (FastMCP + SSE)
- IV. Performance Guarantees (<500ms search, <60s indexing)
- V. Production Quality (mypy --strict, 80%+ coverage)
- VI. Specification-First Development (specify-prompt.txt ready)
- VII. Test-Driven Development (TDD phases)
- VIII. Pydantic-Based Type Safety (all models)
- IX. Orchestrated Subagent Execution (parallelization plan)
- X. Git Micro-Commit Strategy (1 commit per task)
- XI. FastMCP Foundation (decorative patterns)

### workflow-mcp: 12/12 Principles ✅

All principles fully compliant after critical issue resolution:
- I-XI: Same as codebase-mcp
- XII. Generic Entity Adaptability (JSONB + JSON Schema)

---

## FAQ

### Q: Can I skip Phase 0 and start directly with Phase 1?
**A:** Not recommended. Phase 0 prevents infrastructure issues (CREATEDB permissions, pgvector, CI/CD) from blocking Phase 1 implementation. Phase 0 takes 1 week but saves much more time by catching issues early.

### Q: Can I start codebase-mcp refactor before workflow-mcp Phase 1?
**A:** No. codebase-mcp needs to query workflow-mcp for active project. Complete Phase 0 for both, then build workflow-mcp Core (Phase 1) first.

### Q: Can I work on both MCPs in parallel?
**A:** Risky but possible. workflow-mcp Phase 1 must complete before codebase-mcp Phase 3 (integration testing).

### Q: Do I need to follow the 4-step review process during implementation?
**A:** No. The 4-step review (initial → planning → architectural → final) is already complete. Follow the FINAL-IMPLEMENTATION-PLAN.md directly.

### Q: What if I find issues during implementation?
**A:** Create a GitHub issue, document the problem and solution, update the plan, continue. Git micro-commits enable easy rollback.

### Q: How do I know if a task can be parallelized?
**A:** Tasks marked `[P]` in tasks.md are parallelizable. Refer to `03-orchestration/parallel-execution-plan.md` for patterns.

### Q: What if performance targets aren't met?
**A:** Phase 11 includes performance tuning. Common fixes: adjust GIN indexes, tune PostgreSQL config, optimize connection pooling.

---

## Support

### Documentation Issues
- File GitHub issue with `documentation` label
- Reference specific file and line number
- Suggest improvement

### Implementation Blockers
- Check FINAL-IMPLEMENTATION-PLAN.md for resolution
- Review ARCHITECTURAL-REVIEW.md for context
- Consult 03-orchestration/ for workflow guidance

### Performance Issues
- Review 00-architecture/database-design.md for index strategy
- Check PostgreSQL configuration in deployment-config.md
- Run performance benchmarks in Phase 11

---

## Conclusion

All planning is complete. All critical issues are resolved. Both MCPs have approved final implementation plans. Phase 0 foundation plan is documented and ready for execution.

**Status:** ✅ READY FOR IMPLEMENTATION
**Next Action:** Begin Phase 0 (Foundation Setup)
**Estimated Completion:** 10 weeks from start (1 week Phase 0 + 9 weeks implementation)

---

**Last Updated:** 2025-10-11
**Version:** 1.0.0
**Owner:** Cliff Clarke
