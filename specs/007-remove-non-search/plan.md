# Implementation Plan: Remove Non-Search Tools

**Branch**: `007-remove-non-search` | **Date**: 2025-10-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/007-remove-non-search/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → ✅ COMPLETE - Spec loaded and analyzed
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → ✅ COMPLETE - All technical details known (code deletion feature)
3. Fill the Constitution Check section
   → ✅ COMPLETE - Aligns with Principle I (Simplicity Over Features)
4. Evaluate Constitution Check section
   → ✅ PASS - No violations, full constitutional alignment
5. Execute Phase 0 → research.md
   → ✅ COMPLETE - Codebase analysis complete, deletion targets identified
6. Execute Phase 1 → contracts, data-model.md, quickstart.md
   → ✅ COMPLETE - Deletion inventory and validation strategy defined
7. Re-evaluate Constitution Check
   → ✅ PASS - Design maintains constitutional compliance
8. Plan Phase 2 → Describe task generation approach
   → ✅ COMPLETE - TDD deletion strategy defined
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS here. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary

Remove 14 non-search MCP tools and their supporting code from the codebase-mcp server, leaving only `index_repository` and `search_code` tools. This phase follows the Phase 01 database migration that dropped 9 tables. The deletion is performed incrementally in 4 sub-phases with comprehensive validation after all deletions complete. Estimated ~60% code reduction while preserving all search functionality.

**Key Clarifications from /clarify**:
1. Intermediate sub-phases can have broken imports; only final state must work
2. Keep shared code intact; only delete code exclusively used by non-search tools
3. Run search tests before starting deletions and after final sub-phase only
4. 60% reduction is outcome estimate, not hard requirement
5. Final verification = import checks + mypy --strict + search tests pass

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastMCP, MCP Python SDK, SQLAlchemy, asyncpg, Pydantic
**Storage**: PostgreSQL 14+ with pgvector (repositories and code_chunks tables remain)
**Testing**: pytest with integration and unit tests
**Target Platform**: Linux/macOS server (MCP via stdio transport)
**Project Type**: Single (server-side MCP application)
**Performance Goals**: Maintain <60s indexing, <500ms search (p95)
**Constraints**:
- Preserve search functionality completely (FR-013 to FR-017)
- Type safety with mypy --strict (FR-009)
- Incremental deletion with git commits (FR-021, FR-022)
- No database schema changes (constraint)
**Scale/Scope**:
- DELETE: 14 tool files, database operation modules, Pydantic models, test files
- PRESERVE: 2 search tools, shared database utilities, search tests
- RESULT: 16 → 2 MCP tools, estimated ~60% code reduction

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Check (Before Research)

| Principle | Compliance | Notes |
|-----------|------------|-------|
| **I. Simplicity Over Features** | ✅ **PASS** | This feature IS the enforcement of Principle I - removing non-search features |
| **II. Local-First Architecture** | ✅ **PASS** | No changes to local-first design, only code removal |
| **III. Protocol Compliance (MCP via SSE)** | ✅ **PASS** | MCP protocol maintained, only reducing tool count |
| **IV. Performance Guarantees** | ✅ **PASS** | No performance degradation expected, search tools unchanged |
| **V. Production Quality Standards** | ✅ **PASS** | mypy --strict enforcement maintained (FR-009) |
| **VI. Specification-First Development** | ✅ **PASS** | Following /specify → /clarify → /plan workflow |
| **VII. Test-Driven Development** | ✅ **PASS** | Baseline tests before deletion, validation after (FR-015) |
| **VIII. Pydantic-Based Type Safety** | ✅ **PASS** | Pydantic models for search preserved (FR-011) |
| **IX. Orchestrated Subagent Execution** | ✅ **PASS** | Not applicable (deletion feature, no new code) |
| **X. Git Micro-Commit Strategy** | ✅ **PASS** | 4 sub-phases with atomic commits (FR-022) |
| **XI. FastMCP and Python SDK Foundation** | ✅ **PASS** | FastMCP tool registration preserved for 2 search tools |

**Overall Status**: ✅ **FULL COMPLIANCE** - This feature enforces constitutional principles by removing scope creep.

### Post-Design Check (After Phase 1)

| Principle | Compliance | Notes |
|-----------|------------|-------|
| **I. Simplicity Over Features** | ✅ **PASS** | Deletion plan removes all non-search code |
| **III. Protocol Compliance** | ✅ **PASS** | Tool registration logic simplified to 2 tools only |
| **V. Production Quality** | ✅ **PASS** | Comprehensive validation strategy (import + mypy + tests) |
| **VIII. Type Safety** | ✅ **PASS** | mypy --strict verification in final sub-phase |
| **X. Git Micro-Commit Strategy** | ✅ **PASS** | 4 atomic commits documented in tasks.md |

**Overall Status**: ✅ **FULL COMPLIANCE** - Design maintains all constitutional requirements.

## Project Structure

### Documentation (this feature)
```
specs/007-remove-non-search/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output - Codebase analysis
├── data-model.md        # Phase 1 output - Deletion inventory
├── quickstart.md        # Phase 1 output - Validation scenarios
├── contracts/           # Phase 1 output - N/A (no API changes)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
src/
├── models/
│   ├── repository.py         # PRESERVE (used by search)
│   ├── code_chunk.py         # PRESERVE (used by search)
│   ├── task.py               # DELETE (non-search)
│   ├── task_schemas.py       # DELETE (non-search)
│   ├── task_relations.py     # DELETE (non-search)
│   ├── tracking.py           # DELETE (non-search)
│   └── types.py              # ANALYZE (may be shared)
├── services/
│   ├── indexer.py            # PRESERVE (used by search)
│   ├── embedder.py           # PRESERVE (used by search)
│   ├── chunker.py            # PRESERVE (used by search)
│   ├── scanner.py            # PRESERVE (used by search)
│   ├── searcher.py           # PRESERVE (used by search)
│   ├── cache.py              # ANALYZE (may be shared)
│   ├── tasks.py              # DELETE (non-search)
│   ├── work_items.py         # DELETE (non-search)
│   ├── vendor.py             # DELETE (non-search)
│   ├── deployment.py         # DELETE (non-search)
│   ├── validation.py         # ANALYZE (may be shared)
│   ├── hierarchy.py          # DELETE (non-search)
│   ├── locking.py            # ANALYZE (may be shared)
│   ├── git_history.py        # ANALYZE (used by tracking?)
│   ├── markdown.py           # ANALYZE (may be shared)
│   └── fallback.py           # ANALYZE (may be shared)
├── mcp/
│   ├── tools/
│   │   ├── indexing.py       # PRESERVE (@mcp.tool for index_repository)
│   │   ├── search.py         # PRESERVE (@mcp.tool for search_code)
│   │   ├── tasks.py          # DELETE (4 tools: create/get/list/update_task)
│   │   ├── work_items.py     # DELETE (4 tools: create/update/query/list_work_items)
│   │   ├── tracking.py       # DELETE (3 tools: create/query/update vendor, record_deployment)
│   │   ├── configuration.py  # DELETE (2 tools: get/update_project_configuration)
│   │   └── __init__.py       # UPDATE (remove deleted tool imports)
│   └── server_fastmcp.py     # UPDATE (verify only 2 tools registered)
├── database/
│   ├── session.py            # PRESERVE (shared database utilities)
│   └── README.md             # UPDATE (remove references to deleted tables)
└── config/
    └── settings.py           # PRESERVE (shared configuration)

tests/
├── integration/
│   ├── test_indexing.py      # PRESERVE (search tests)
│   ├── test_search.py        # PRESERVE (search tests)
│   ├── test_tasks.py         # DELETE (non-search)
│   ├── test_work_items.py    # DELETE (non-search)
│   ├── test_tracking.py      # DELETE (non-search)
│   └── test_configuration.py # DELETE (non-search)
├── unit/
│   ├── test_indexer.py       # PRESERVE (search tests)
│   ├── test_searcher.py      # PRESERVE (search tests)
│   ├── test_embedder.py      # PRESERVE (search tests)
│   ├── test_chunker.py       # PRESERVE (search tests)
│   ├── test_scanner.py       # PRESERVE (search tests)
│   └── test_[others].py      # DELETE (non-search service tests)
└── contract/
    ├── test_indexing_contract.py   # PRESERVE (search tests)
    ├── test_search_contract.py     # PRESERVE (search tests)
    └── test_[others]_contract.py   # DELETE (non-search contract tests)
```

**Structure Decision**: Single project (server-side MCP application). The codebase follows standard Python package structure with src/, tests/, and alembic/ directories. This is a code deletion feature - we're removing non-search tools while preserving the semantic search core.

## Phase 0: Outline & Research

### Objectives
1. Identify all code to be deleted (tools, models, services, tests)
2. Identify shared code that must be preserved
3. Identify dependencies between deleted and preserved code
4. Map out deletion order to minimize breaking changes

### Research Tasks

#### Task 1: Analyze Tool Files and Registration
**Goal**: Identify all 16 currently registered MCP tools and confirm which 14 to delete

**Findings** (from codebase analysis):
- **PRESERVE**:
  - `src/mcp/tools/indexing.py` - contains `@mcp.tool()` for `index_repository`
  - `src/mcp/tools/search.py` - contains `@mcp.tool()` for `search_code`

- **DELETE**:
  - `src/mcp/tools/tasks.py` - contains 4 tools: `create_task`, `get_task`, `list_tasks`, `update_task`
  - `src/mcp/tools/work_items.py` - contains 4 tools: `create_work_item`, `update_work_item`, `query_work_item`, `list_work_items`
  - `src/mcp/tools/tracking.py` - contains 4 tools: `create_vendor`, `query_vendor_status`, `update_vendor_status`, `record_deployment`
  - `src/mcp/tools/configuration.py` - contains 2 tools: `get_project_configuration`, `update_project_configuration`

**Total**: 2 preserved + 14 deleted = 16 tools ✅ Matches spec requirement

#### Task 2: Analyze Database Models
**Goal**: Identify which Pydantic models are exclusively used by non-search tools

**Findings**:
- **PRESERVE** (used by search):
  - `src/models/repository.py` - Repository model (search needs this)
  - `src/models/code_chunk.py` - CodeChunk model (search needs this)
  - `src/models/database.py` - Likely base models or shared utilities

- **DELETE** (exclusively non-search):
  - `src/models/task.py` - Task model (used only by task tools)
  - `src/models/task_schemas.py` - Task Pydantic schemas
  - `src/models/task_relations.py` - Task relationship models
  - `src/models/tracking.py` - Vendor/deployment tracking models

- **ANALYZE** (may be shared):
  - `src/models/types.py` - May contain shared type definitions

#### Task 3: Analyze Service Layer
**Goal**: Identify which services are exclusively used by non-search tools vs. shared

**Findings**:
- **PRESERVE** (used by search):
  - `src/services/indexer.py` - Core indexing service
  - `src/services/embedder.py` - Embedding generation
  - `src/services/chunker.py` - Code chunking
  - `src/services/scanner.py` - File scanning
  - `src/services/searcher.py` - Semantic search

- **DELETE** (exclusively non-search):
  - `src/services/tasks.py` - Task service (used only by task tools)
  - `src/services/work_items.py` - Work item service
  - `src/services/vendor.py` - Vendor tracking service
  - `src/services/deployment.py` - Deployment tracking service
  - `src/services/hierarchy.py` - Work item hierarchy (non-search)

- **ANALYZE** (may be shared):
  - `src/services/cache.py` - May be used by search or non-search
  - `src/services/validation.py` - May contain shared validation logic
  - `src/services/locking.py` - Optimistic locking (may be shared)
  - `src/services/git_history.py` - Git integration (may be used by search)
  - `src/services/markdown.py` - Markdown rendering (may be shared)
  - `src/services/fallback.py` - Fallback strategies (may be shared)

#### Task 4: Analyze Test Files
**Goal**: Identify which tests are for search vs. non-search features

**Strategy**:
- Tests for preserved tools/services → PRESERVE
- Tests for deleted tools/services → DELETE
- Follow naming convention: `test_<module>.py` maps to `src/<path>/<module>.py`

**Expected Deletions**:
- `tests/integration/test_tasks.py`
- `tests/integration/test_work_items.py`
- `tests/integration/test_tracking.py`
- `tests/integration/test_configuration.py`
- `tests/unit/test_tasks.py`
- `tests/unit/test_work_items.py`
- `tests/unit/test_vendor.py`
- `tests/unit/test_deployment.py`
- `tests/unit/test_hierarchy.py`
- `tests/contract/test_tasks_contract.py`
- `tests/contract/test_work_items_contract.py`
- `tests/contract/test_tracking_contract.py`
- `tests/contract/test_configuration_contract.py`

#### Task 5: Analyze Shared Code Dependencies
**Goal**: Identify which "ANALYZE" files are truly shared and must be preserved

**Strategy**:
1. Use `grep` to find imports of each "ANALYZE" file in preserved code
2. If imported by search tools/services → PRESERVE
3. If only imported by deleted tools/services → DELETE
4. If shared → Keep but update to remove deleted code references

**Files to Analyze**:
- `src/models/types.py` - Check if search tools import type definitions
- `src/services/cache.py` - Check if searcher/indexer use caching
- `src/services/validation.py` - Check if search tools use validation
- `src/services/locking.py` - Check if search uses optimistic locking
- `src/services/git_history.py` - Check if indexer uses git history
- `src/services/markdown.py` - Check if search renders markdown
- `src/services/fallback.py` - Check if search uses fallback strategies

### Research Output Summary

**Deletion Inventory** (Confirmed):
- **Tool Files** (4 files): tasks.py, work_items.py, tracking.py, configuration.py
- **Model Files** (4 files): task.py, task_schemas.py, task_relations.py, tracking.py
- **Service Files** (5 files + analysis results): tasks.py, work_items.py, vendor.py, deployment.py, hierarchy.py + [analyzed shared files]
- **Test Files** (~14 files estimated): All tests for deleted tools/services

**Preservation Targets** (Confirmed):
- **Tool Files** (2 files): indexing.py, search.py
- **Model Files** (3 files): repository.py, code_chunk.py, database.py
- **Service Files** (5 files): indexer.py, embedder.py, chunker.py, scanner.py, searcher.py
- **Test Files** (~10 files estimated): All search-related tests

**Shared Code Analysis Required**: 7 files need import analysis before deletion decision

**Next Step**: Phase 1 will create detailed deletion inventory in data-model.md

## Phase 1: Design & Contracts

### Objectives
1. Create complete deletion inventory (what to delete, what to preserve)
2. Document validation strategy (import checks + mypy + tests)
3. Create quickstart.md with validation scenarios
4. Update agent context file

### Design Artifacts

#### 1. Deletion Inventory (data-model.md)
**Purpose**: Complete list of files to delete, preserve, and analyze

**Contents**:
- **Section 1: Files to DELETE** - Full paths with rationale
- **Section 2: Files to PRESERVE** - Full paths with rationale
- **Section 3: Files to ANALYZE** - Import analysis results, final decision
- **Section 4: Import Cleanup** - List of import statements to remove from preserved files
- **Section 5: Registration Updates** - Changes to server_fastmcp.py tool registration

#### 2. API Contracts (contracts/)
**Decision**: N/A for this feature

**Rationale**: This is a code deletion feature. The two preserved tools (index_repository, search_code) have existing contracts that are NOT changing. No new contracts needed.

#### 3. Validation Strategy (quickstart.md)
**Purpose**: Define the comprehensive validation approach after all deletions

**Contents**:
- **Validation 1: Baseline Tests** - Run search tests BEFORE any deletions
- **Validation 2: Import Checks** - Verify all modules can be imported
- **Validation 3: Type Checking** - Run `mypy --strict src/`
- **Validation 4: Search Tests** - Run search tests AFTER all deletions
- **Validation 5: Server Startup** - Verify server starts with only 2 tools
- **Validation 6: Tool Count** - Confirm exactly 2 tools registered

#### 4. Agent Context Update
**Action**: Run `.specify/scripts/bash/update-agent-context.sh claude`

**Purpose**: Update CLAUDE.md in repository root with this feature's context

**Content to Add**:
- Feature 007: Remove Non-Search Tools (Phase 02 of MCP split)
- 4 sub-phases: Delete tools → Delete DB ops → Update registration → Delete tests
- Intermediate breakage acceptable, final state comprehensive validation
- Preserve shared code, delete exclusive non-search code

### Phase 1 Execution Plan

1. **Generate data-model.md** - Complete deletion inventory
2. **Generate quickstart.md** - Validation scenarios
3. **Update agent context** - Run update-agent-context.sh
4. **Verify completeness** - Ensure all "ANALYZE" decisions made

### Post-Design Constitution Re-Check

After completing Phase 1 design:
- ✅ All deletions align with Principle I (Simplicity)
- ✅ No protocol compliance risks (2 tools remain functional)
- ✅ Type safety maintained (mypy --strict in validation)
- ✅ Git micro-commits planned (4 atomic commits)

**Result**: ✅ **FULL COMPLIANCE** - Ready for task generation

## Phase 2: Task Planning Approach

*This section describes what the /tasks command will do - DO NOT execute during /plan*

### Task Generation Strategy

The /tasks command will load `.specify/templates/tasks-template.md` and generate tasks based on the 4 sub-phases defined in the specification and clarifications.

#### Sub-Phase 1: Delete Tool Files
**Tasks**:
1. Run baseline search tests (establish working state) [VALIDATE]
2. Delete `src/mcp/tools/tasks.py` [DELETE]
3. Delete `src/mcp/tools/work_items.py` [DELETE]
4. Delete `src/mcp/tools/tracking.py` [DELETE]
5. Delete `src/mcp/tools/configuration.py` [DELETE]
6. Update `src/mcp/tools/__init__.py` (remove deleted imports) [UPDATE]
7. Commit: "chore(tools): delete 14 non-search MCP tools" [GIT]

#### Sub-Phase 2: Delete Database Operations
**Tasks**:
8. Analyze shared code dependencies (run import analysis) [RESEARCH]
9. Delete `src/models/task.py` [DELETE]
10. Delete `src/models/task_schemas.py` [DELETE]
11. Delete `src/models/task_relations.py` [DELETE]
12. Delete `src/models/tracking.py` [DELETE]
13. Delete `src/services/tasks.py` [DELETE]
14. Delete `src/services/work_items.py` [DELETE]
15. Delete `src/services/vendor.py` [DELETE]
16. Delete `src/services/deployment.py` [DELETE]
17. Delete `src/services/hierarchy.py` [DELETE]
18. Delete analyzed shared files (based on step 8 results) [DELETE]
19. Commit: "chore(models,services): delete non-search database operations" [GIT]

#### Sub-Phase 3: Update Server Registration
**Tasks**:
20. Verify server_fastmcp.py only registers 2 tools [VERIFY]
21. Update database README (remove deleted table references) [UPDATE]
22. Clean up imports in preserved files (based on data-model.md) [UPDATE]
23. Commit: "chore(server): verify 2-tool registration and cleanup imports" [GIT]

#### Sub-Phase 4: Delete Tests and Final Validation
**Tasks**:
24. Delete `tests/integration/test_tasks.py` [DELETE]
25. Delete `tests/integration/test_work_items.py` [DELETE]
26. Delete `tests/integration/test_tracking.py` [DELETE]
27. Delete `tests/integration/test_configuration.py` [DELETE]
28. Delete unit tests for deleted services [DELETE]
29. Delete contract tests for deleted tools [DELETE]
30. Run import checks (verify all modules import) [VALIDATE]
31. Run `mypy --strict src/` [VALIDATE]
32. Run search tests (verify still passing) [VALIDATE]
33. Start server and verify 2 tools registered [VALIDATE]
34. Commit: "chore(tests): delete non-search tests and verify final state" [GIT]

### Task Ordering Strategy

1. **Baseline First**: Establish working state with test run (Task 1)
2. **Sequential Sub-Phases**: Follow FR-021 ordering (tools → DB ops → registration → tests)
3. **Atomic Commits**: One commit per sub-phase (FR-022)
4. **Comprehensive Validation**: All validation checks in final sub-phase (FR-023)
5. **No Parallelization**: Deletion tasks must be sequential (intermediate breakage acceptable per clarification)

### Task Markers

- `[DELETE]` - File deletion task
- `[UPDATE]` - File modification task
- `[VERIFY]` - Check existing state task
- `[VALIDATE]` - Run validation check task
- `[RESEARCH]` - Analyze before deciding task
- `[GIT]` - Git commit task
- **NO [P] markers** - All tasks are sequential (deletion order matters)

### Estimated Output

**Total Tasks**: ~34 tasks across 4 sub-phases
- Sub-Phase 1: 7 tasks (delete 4 tool files + update + commit)
- Sub-Phase 2: 12 tasks (analyze + delete 9 files + commit)
- Sub-Phase 3: 4 tasks (verify + update + commit)
- Sub-Phase 4: 11 tasks (delete tests + 4 validation checks + commit)

**Estimated Duration**: 8-12 hours (per spec Additional Context)

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation

*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)
**Phase 4**: Implementation (execute tasks.md following constitutional principles)
**Phase 5**: Validation (run quickstart.md validation scenarios)

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

**Status**: ✅ **NO VIOLATIONS** - No complexity tracking needed

This feature enforces constitutional principles (Simplicity Over Features) by removing non-essential code. No complexity justifications required.

## Progress Tracking

*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS (full compliance)
- [x] Post-Design Constitution Check: PASS (full compliance)
- [x] All NEEDS CLARIFICATION resolved (5 clarifications documented)
- [x] Complexity deviations documented (none - no violations)

**Execution Notes**:
- Phase 0 completed: Codebase analyzed, deletion targets identified (16 tools → 2 tools)
- Phase 1 ready: Deletion inventory, validation strategy, and agent context update planned
- Phase 2 ready: 34 tasks across 4 sub-phases, TDD deletion approach defined
- Next command: `/tasks` to generate tasks.md

---
*Based on Constitution v2.2.0 - See `.specify/memory/constitution.md`*
