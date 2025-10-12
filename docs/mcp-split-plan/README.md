# codebase-mcp Refactoring Plan

**Status**: Ready for Phase Execution
**Last Updated**: 2025-10-11
**Purpose**: Transform codebase-mcp from monolithic MCP (16 tools) to pure semantic code search (2 tools) with multi-project support

---

## Overview

This directory contains the complete planning and execution documentation for refactoring the codebase-mcp server. The refactoring follows Constitutional Principle I (Simplicity Over Features) by removing all non-search functionality while adding multi-project support.

### Key Objectives

1. **Remove non-search features**: Work items, tasks, vendors, deployments (9 database tables dropped)
2. **Add multi-project support**: One database per project with complete isolation
3. **Maintain performance**: <500ms p95 search, <60s indexing (10k files)
4. **Reduce complexity**: ~60% code reduction (4,500 → 1,800 lines)
5. **Constitutional compliance**: All 11 principles maintained

### Success Criteria

- Only 2 MCP tools remain: `index_repository`, `search_code`
- Multi-project isolation validated (no cross-contamination)
- Performance targets met with NO regression from baseline
- 100% MCP protocol compliance (mcp-inspector)
- Type-safe: mypy --strict passes
- Test coverage >80%

---

## Directory Structure

```
mcp-split-plan/
├── README.md                    # This file - start here
├── START-HERE.md                # Quick start guide (archived original)
│
├── phases/                      # Phase-based execution folders
│   ├── phase-00-preparation/    # Phase 0-1: Prerequisites, baseline, branch
│   ├── phase-01-database-refactor/    # Phase 2: Schema changes
│   ├── phase-02-remove-tools/   # Phases 3-6: Code removal
│   ├── phase-03-multi-project/  # Phase 7: Multi-project support
│   ├── phase-04-connection-mgmt/ # Phase 8: Connection pooling
│   ├── phase-05-docs-migration/ # Phases 9-10: Documentation
│   ├── phase-06-performance/    # Phase 11: Performance testing
│   └── phase-07-final-validation/ # Phase 12: Release validation
│
└── _archive/                    # Historical/reference materials
    ├── workflow-mcp/            # workflow-mcp docs (separate repo)
    ├── shared-architecture/     # Shared architecture docs
    ├── 01-codebase-mcp/         # Original planning docs
    └── IMPLEMENTATION-ROADMAP.md # Original roadmap
```

---

## Execution Strategy: Phase-Based /specify Workflow

Each phase folder is designed to be used with the `/specify` slash command workflow. This enables:

1. **Incremental execution**: Complete one phase before starting the next
2. **Clear scope**: Each phase has well-defined boundaries and deliverables
3. **Rollback points**: Git commits and database backups at each phase boundary
4. **Parallel work**: Some phases can be executed in parallel (documented in each phase README)

### How to Execute a Phase

For each phase:

1. **Navigate to phase folder**: `cd phases/phase-XX-name/`
2. **Read the phase README**: Understand objectives, scope, and prerequisites
3. **Run /specify**: Use the phase materials to create a feature spec
4. **Run /plan**: Generate implementation plan from the spec
5. **Run /tasks**: Break down plan into actionable tasks
6. **Run /implement**: Execute the tasks
7. **Verify completion**: Check acceptance criteria before moving to next phase

---

## Phase Overview

### Phase 0: Preparation (Phase 00)
**Duration**: 2-3 hours
**Scope**: Prerequisites, performance baseline, rollback preparation
**Key Deliverables**: Baseline metrics, database backup, git tag, refactor branch

**Why start here**: Establishes baseline for performance regression detection and creates rollback points.

### Phase 1: Database Refactoring (Phase 01)
**Duration**: 4-6 hours
**Scope**: Remove non-search tables, add project_id column
**Key Deliverables**: Migration script, updated schema, schema tests

**Why this order**: Database changes first prevent orphaned code references.

### Phase 2: Remove Tools (Phase 02)
**Duration**: 8-12 hours
**Scope**: Remove 14 non-search MCP tools and related code
**Key Deliverables**: Clean codebase with only search tools, updated tests

**Why this order**: Remove unused code before adding new features to reduce cognitive load.

### Phase 3: Multi-Project Support (Phase 03)
**Duration**: 6-8 hours
**Scope**: Add project_id parameter, workflow-mcp integration
**Key Deliverables**: Multi-project search/indexing, integration tests

**Why this order**: Core feature implementation after cleanup is complete.

### Phase 4: Connection Management (Phase 04)
**Duration**: 4-6 hours
**Scope**: Per-project connection pools, LRU eviction
**Key Deliverables**: Connection pool manager, monitoring, resource limits

**Why this order**: Infrastructure for multi-project must be robust before docs/testing.

### Phase 5: Documentation & Migration (Phase 05)
**Duration**: 3-4 hours
**Scope**: Update docs, migration guide, configuration examples
**Key Deliverables**: Complete documentation, migration playbook

**Why this order**: Document what exists before final testing reveals gaps.

### Phase 6: Performance Testing (Phase 06)
**Duration**: 4-6 hours
**Scope**: Benchmark against baseline, multi-tenant stress tests
**Key Deliverables**: Performance report, optimization fixes (if needed)

**Why this order**: Validate performance before final validation/release.

### Phase 7: Final Validation (Phase 07)
**Duration**: 2-3 hours
**Scope**: MCP protocol compliance, security audit, release checklist
**Key Deliverables**: mcp-inspector passing, release candidate

**Why this order**: Comprehensive validation as final gate before release.

---

## Timeline

| Phase | Duration | Cumulative | Status |
|-------|----------|------------|--------|
| **Phase 00: Preparation** | 2-3 hours | 3h | Ready |
| **Phase 01: Database** | 4-6 hours | 9h | Planned |
| **Phase 02: Remove Tools** | 8-12 hours | 21h | Planned |
| **Phase 03: Multi-Project** | 6-8 hours | 29h | Planned |
| **Phase 04: Connection Mgmt** | 4-6 hours | 35h | Planned |
| **Phase 05: Docs/Migration** | 3-4 hours | 39h | Planned |
| **Phase 06: Performance** | 4-6 hours | 45h | Planned |
| **Phase 07: Final Validation** | 2-3 hours | 48h | Planned |
| **TOTAL** | **37-48 hours** | **~1 week** | |

---

## Getting Started

### Prerequisites

Before starting Phase 00:

1. **Backup existing state**:
   ```bash
   cd /Users/cliffclarke/Claude_Code/codebase-mcp
   git tag backup-before-refactor
   git push origin backup-before-refactor
   ```

2. **PostgreSQL setup**:
   - PostgreSQL 14+ with pgvector extension installed
   - CREATEDB permission for MCP user
   - Test: `createdb test_db && dropdb test_db`

3. **Python environment**:
   - Python 3.11+
   - uv package manager
   - Ollama with nomic-embed-text model

### Quick Start

**Option 1: Start Phase 00 (Recommended)**

```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp/docs/mcp-split-plan/phases/phase-00-preparation
cat README.md  # Read phase overview
# Then run /specify workflow
```

**Option 2: Review all planning first**

```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp/docs/mcp-split-plan
cat START-HERE.md  # Original execution guide
cat _archive/01-codebase-mcp/FINAL-IMPLEMENTATION-PLAN.md  # Complete technical plan
```

---

## Key Planning Documents (Archive)

The following documents are in `_archive/` and provide comprehensive planning context:

### Essential Reading

1. **`_archive/01-codebase-mcp/FINAL-IMPLEMENTATION-PLAN.md`** - Complete refactoring plan (2.0)
   - All 12 phases detailed
   - Critical issues resolved (C1-C5)
   - Architectural recommendations integrated (R1-R4)
   - Rollback procedures for each phase

2. **`_archive/01-codebase-mcp/constitution.md`** - Constitutional principles
   - 11 non-negotiable principles
   - Simplicity Over Features (Principle I)
   - Performance guarantees
   - Type safety requirements

3. **`_archive/01-codebase-mcp/SUMMARY.md`** - Executive summary
   - High-level overview
   - Business value
   - Risk assessment

### Reference Materials

4. **`_archive/01-codebase-mcp/ARCHITECTURAL-REVIEW.md`** - Architecture validation
5. **`_archive/01-codebase-mcp/PLANNING-REVIEW.md`** - Planning critique
6. **`_archive/01-codebase-mcp/refactoring-plan.md`** - Initial refactoring approach
7. **`_archive/01-codebase-mcp/user-stories.md`** - User scenarios
8. **`_archive/01-codebase-mcp/tech-stack.md`** - Technical stack decisions

---

## Safety & Rollback

### Emergency Rollback

If critical issues arise during execution:

```bash
# Return to pre-refactor state
cd /Users/cliffclarke/Claude_Code/codebase-mcp
git checkout main
git reset --hard backup-before-refactor

# Restore database (if needed)
dropdb codebase_mcp
psql -U your_user -d postgres -f backups/backup-before-002.sql
```

### Phase-Level Rollback

Each phase includes specific rollback instructions in its README. Always:
1. Create git tag before starting phase
2. Commit after each completed task (micro-commits)
3. Run tests before moving to next phase
4. Document any deviations or issues

---

## Not Applicable to This Repo

The `_archive/workflow-mcp/` directory contains planning for a **separate repository** (workflow-mcp) that handles project management features. This is NOT part of the codebase-mcp refactoring and can be safely ignored.

---

## Questions or Issues

- **Phase scope unclear?** Read the phase README and FINAL-IMPLEMENTATION-PLAN.md
- **Prerequisites not met?** Review Phase 00 prerequisites before starting
- **Performance concerns?** Phase 06 includes comprehensive benchmarking
- **Need to rollback?** Each phase has rollback procedures documented

---

## Status

**Current State**: Planning Complete, Ready for Execution
**Next Action**: Start Phase 00 (Preparation)
**Branch**: `main` (will create `002-refactor-pure-search` in Phase 00)
**Last Verified**: 2025-10-11

---

**Ready to begin? Navigate to `phases/phase-00-preparation/` and read the README!**
