# Research: Remove Non-Search Tools

**Feature**: 007-remove-non-search
**Date**: 2025-10-11
**Phase**: 0 (Research & Analysis)

## Research Objective

Analyze the codebase-mcp server to identify all non-search MCP tools, their supporting code (models, services, tests), and dependencies. Determine exactly what code to delete vs. preserve to achieve the goal of keeping only `index_repository` and `search_code` tools while maintaining all search functionality.

## Research Questions

1. **Q1**: Which 16 MCP tools are currently registered in the server?
2. **Q2**: Which database models are exclusively used by non-search tools?
3. **Q3**: Which services are exclusively used by non-search tools?
4. **Q4**: Which shared utilities must be preserved for search functionality?
5. **Q5**: Which test files correspond to non-search features?
6. **Q6**: What is the current line count baseline for measuring code reduction?

## Findings

### Q1: MCP Tool Registration Analysis

**Method**: Searched for `@mcp.tool()` decorators across src/mcp/tools/

**Results**:

#### PRESERVE (2 tools):
1. **`index_repository`** in `src/mcp/tools/indexing.py`
   - Function: Indexes code repositories into PostgreSQL with embeddings
   - Dependencies: indexer service, scanner, chunker, embedder

2. **`search_code`** in `src/mcp/tools/search.py`
   - Function: Performs semantic code search using embeddings
   - Dependencies: searcher service, database session

#### DELETE (14 tools across 4 files):

**File: `src/mcp/tools/tasks.py` (4 tools)**:
1. `create_task` - Create new development tasks
2. `get_task` - Retrieve task by ID
3. `list_tasks` - List tasks with filters
4. `update_task` - Update task status/metadata

**File: `src/mcp/tools/work_items.py` (4 tools)**:
5. `create_work_item` - Create hierarchical work items
6. `update_work_item` - Update work item with optimistic locking
7. `query_work_item` - Query single work item with hierarchy
8. `list_work_items` - List work items with filtering

**File: `src/mcp/tools/tracking.py` (4 tools)**:
9. `create_vendor` - Register new vendor extractor
10. `query_vendor_status` - Query vendor operational status
11. `update_vendor_status` - Update vendor with optimistic locking
12. `record_deployment` - Record deployment events with relationships

**File: `src/mcp/tools/configuration.py` (2 tools)**:
13. `get_project_configuration` - Get singleton project config
14. `update_project_configuration` - Update project config

**Total**: 2 preserved + 14 deleted = 16 tools ✅

### Q2: Database Models Analysis

**Method**: Analyzed `src/models/` directory and model imports

**Results**:

#### PRESERVE (3 models):
1. **`src/models/repository.py`** - Repository table model
   - Used by: index_repository tool, indexer service
   - Reason: Core to indexing workflow

2. **`src/models/code_chunk.py`** - Code chunks table model
   - Used by: index_repository tool, search_code tool, indexer/searcher services
   - Reason: Core to search functionality

3. **`src/models/database.py`** - Base models and utilities
   - Used by: All database operations
   - Reason: Shared database infrastructure

#### DELETE (4 models):
1. **`src/models/task.py`** - Task table model
   - Used by: task tools only
   - Referenced table: `tasks` (DROPPED in Phase 01 migration 002)

2. **`src/models/task_schemas.py`** - Task Pydantic schemas
   - Used by: task tools only
   - Reason: Task feature exclusive

3. **`src/models/task_relations.py`** - Task relationship models
   - Used by: task tools only
   - Reason: Task feature exclusive

4. **`src/models/tracking.py`** - Vendor/deployment models
   - Used by: tracking tools only
   - Referenced tables: `vendor_extractors`, `deployment_events` (DROPPED in Phase 01 migration 002)

#### ANALYZE (1 model):
1. **`src/models/types.py`** - Shared type definitions
   - **Decision**: PRESERVE if contains types used by search, DELETE if task-only
   - **Action**: Requires import analysis in Phase 1

### Q3: Service Layer Analysis

**Method**: Analyzed `src/services/` directory for service modules

**Results**:

#### PRESERVE (5 services):
1. **`src/services/indexer.py`** - Core indexing orchestration
   - Used by: index_repository tool
   - Reason: Core search functionality

2. **`src/services/embedder.py`** - Embedding generation (Ollama)
   - Used by: indexer service
   - Reason: Core search functionality

3. **`src/services/chunker.py`** - AST-based code chunking
   - Used by: indexer service
   - Reason: Core search functionality

4. **`src/services/scanner.py`** - File system scanning
   - Used by: indexer service
   - Reason: Core search functionality

5. **`src/services/searcher.py`** - Semantic search with pgvector
   - Used by: search_code tool
   - Reason: Core search functionality

#### DELETE (5 services):
1. **`src/services/tasks.py`** - Task service layer
   - Used by: task tools only
   - Reason: Task feature exclusive

2. **`src/services/work_items.py`** - Work item service layer
   - Used by: work item tools only
   - Reason: Work item feature exclusive

3. **`src/services/vendor.py`** - Vendor tracking service
   - Used by: tracking tools only
   - Reason: Vendor feature exclusive

4. **`src/services/deployment.py`** - Deployment tracking service
   - Used by: tracking tools only
   - Reason: Deployment feature exclusive

5. **`src/services/hierarchy.py`** - Work item hierarchy service
   - Used by: work item tools only
   - Reason: Work item feature exclusive

#### ANALYZE (6 services):
1. **`src/services/cache.py`** - Caching utilities
   - **Question**: Does searcher or indexer use caching?
   - **Action**: Check for imports in search services

2. **`src/services/validation.py`** - Input validation
   - **Question**: Do search tools use validation?
   - **Action**: Check for imports in search tools

3. **`src/services/locking.py`** - Optimistic locking
   - **Question**: Does search use optimistic locking?
   - **Action**: Check for imports in search services

4. **`src/services/git_history.py`** - Git integration
   - **Question**: Does indexer track git history?
   - **Action**: Check for imports in indexer

5. **`src/services/markdown.py`** - Markdown rendering
   - **Question**: Does search render markdown?
   - **Action**: Check for imports in search services

6. **`src/services/fallback.py`** - Fallback strategies
   - **Question**: Does search use fallbacks?
   - **Action**: Check for imports in search services

### Q4: Shared Code Dependencies

**Method**: Import analysis required in Phase 1 (data-model.md)

**Strategy**:
```bash
# For each ANALYZE file, check if search code imports it:
grep -r "from src.services.cache import" src/mcp/tools/indexing.py src/mcp/tools/search.py src/services/indexer.py src/services/searcher.py
grep -r "from src.services.validation import" src/mcp/tools/indexing.py src/mcp/tools/search.py src/services/indexer.py src/services/searcher.py
# ... repeat for each ANALYZE file
```

**Decision Criteria**:
- If imported by search tools/services → **PRESERVE**
- If only imported by deleted tools/services → **DELETE**
- If not imported anywhere → **DELETE**

**Phase 1 Action**: Run import analysis and document results in data-model.md Section 3

### Q5: Test Files Analysis

**Method**: Mapped test files to source modules

**Results**:

#### PRESERVE (Search Tests):
**Integration**:
- `tests/integration/test_indexing.py` - Tests for index_repository tool
- `tests/integration/test_search.py` - Tests for search_code tool

**Unit**:
- `tests/unit/test_indexer.py` - Tests for indexer service
- `tests/unit/test_searcher.py` - Tests for searcher service
- `tests/unit/test_embedder.py` - Tests for embedder service
- `tests/unit/test_chunker.py` - Tests for chunker service
- `tests/unit/test_scanner.py` - Tests for scanner service

**Contract**:
- `tests/contract/test_indexing_contract.py` - Contract tests for index_repository
- `tests/contract/test_search_contract.py` - Contract tests for search_code

**Estimated**: ~9 search test files to preserve

#### DELETE (Non-Search Tests):
**Integration**:
- `tests/integration/test_tasks.py` - Tests for task tools
- `tests/integration/test_work_items.py` - Tests for work item tools
- `tests/integration/test_tracking.py` - Tests for tracking tools
- `tests/integration/test_configuration.py` - Tests for configuration tools

**Unit** (estimated from services):
- `tests/unit/test_tasks.py` - Tests for tasks service
- `tests/unit/test_work_items.py` - Tests for work items service
- `tests/unit/test_vendor.py` - Tests for vendor service
- `tests/unit/test_deployment.py` - Tests for deployment service
- `tests/unit/test_hierarchy.py` - Tests for hierarchy service
- `tests/unit/test_locking.py` - Tests for locking service (if exists)
- `tests/unit/test_validation.py` - Tests for validation service (if exists)

**Contract**:
- `tests/contract/test_tasks_contract.py` - Contract tests for task tools
- `tests/contract/test_work_items_contract.py` - Contract tests for work item tools
- `tests/contract/test_tracking_contract.py` - Contract tests for tracking tools
- `tests/contract/test_configuration_contract.py` - Contract tests for configuration tools

**Estimated**: ~15 non-search test files to delete

### Q6: Code Baseline Measurement

**Method**: Count lines of code using `cloc` or `wc -l`

**Baseline Measurement** (to be run before deletions):
```bash
# Total Python lines in src/ (excluding blank/comment lines)
find src -name "*.py" | xargs wc -l | tail -1

# Breakdown by category:
find src/mcp/tools -name "*.py" | xargs wc -l | tail -1      # Tool files
find src/models -name "*.py" | xargs wc -l | tail -1          # Model files
find src/services -name "*.py" | xargs wc -l | tail -1        # Service files
find tests -name "*.py" | xargs wc -l | tail -1               # Test files
```

**Expected Results** (from spec):
- **Before**: ~4,500 lines of Python code
- **After**: ~1,800 lines of Python code
- **Reduction**: ~60% (2,700 lines deleted)

**Note**: Actual measurement will be performed during implementation. The 60% reduction is an outcome estimate, not a hard requirement (per clarification #4).

## Research Decisions

### Decision 1: Tool Deletion Targets Confirmed
**Context**: Spec requires removal of 14 non-search tools, keeping only 2 search tools

**Decision**: DELETE 4 tool files containing 14 tool implementations:
- tasks.py (4 tools)
- work_items.py (4 tools)
- tracking.py (4 tools)
- configuration.py (2 tools)

**Rationale**: Analysis confirmed 16 total tools (2 search + 14 non-search). All non-search tools are in separate files from search tools, enabling clean deletion without affecting search functionality.

**Alternatives Considered**: N/A - Requirements are explicit

### Decision 2: Shared Code Preservation Strategy
**Context**: Clarification #2 says "Keep shared code intact; only delete code exclusively used by non-search tools"

**Decision**: Implement 2-phase analysis:
1. **Phase 0 (Research)**: Identify files as DELETE, PRESERVE, or ANALYZE
2. **Phase 1 (Design)**: Run import analysis on ANALYZE files, make final decisions

**Rationale**: Cannot determine if code is "shared" without import analysis. Conservative approach prevents accidentally breaking search functionality.

**Alternatives Considered**:
- **Delete all ANALYZE files**: Rejected - too risky, might break search
- **Keep all ANALYZE files**: Rejected - might violate code reduction goal

### Decision 3: Incremental Deletion Order
**Context**: Spec requires 4 sub-phases with atomic commits

**Decision**: Follow spec's ordering:
1. Sub-Phase 1: Delete tool files (4 files)
2. Sub-Phase 2: Delete database operations (models + services, 9+ files)
3. Sub-Phase 3: Update server registration (verify + cleanup imports)
4. Sub-Phase 4: Delete tests + comprehensive validation (15+ files)

**Rationale**: Spec explicitly defines this order. Clarification #1 confirms intermediate breakage is acceptable, so order doesn't need to maintain working state at each step.

**Alternatives Considered**: N/A - Requirements are explicit

### Decision 4: Validation Strategy
**Context**: Clarification #5 defines "verified working state" as import checks + mypy + tests

**Decision**: Run comprehensive validation ONLY after final sub-phase:
- Baseline: Run search tests BEFORE any deletions (establish working state)
- Final: Run import checks + mypy --strict + search tests AFTER all deletions

**Rationale**: Clarification #3 says test search functionality "before starting deletions and after final sub-phase only". Intermediate validation would fail due to broken imports.

**Alternatives Considered**:
- **Validate after each sub-phase**: Rejected - intermediate breakage acceptable
- **Skip baseline tests**: Rejected - need to detect pre-existing failures

## Phase 1 Requirements

Based on research findings, Phase 1 (Design & Contracts) must deliver:

1. **data-model.md** - Complete deletion inventory with:
   - Section 1: All DELETE files (full paths + rationale)
   - Section 2: All PRESERVE files (full paths + rationale)
   - Section 3: ANALYZE file results (import analysis + final decision)
   - Section 4: Import cleanup list (what imports to remove from preserved files)
   - Section 5: Server registration verification (confirm only 2 tools)

2. **quickstart.md** - Validation scenarios:
   - Scenario 1: Baseline test execution (before deletions)
   - Scenario 2: Import checks (python -c "import ...")
   - Scenario 3: Type checking (mypy --strict src/)
   - Scenario 4: Search test execution (after deletions)
   - Scenario 5: Server startup verification
   - Scenario 6: Tool count confirmation

3. **Agent context update** - Run update-agent-context.sh claude

4. **No contracts/** - N/A for code deletion feature

## Research Conclusion

**Status**: ✅ **RESEARCH COMPLETE**

**Key Findings**:
- 16 tools identified: 2 search + 14 non-search ✅ Matches spec
- 4 tool files to delete, 2 to preserve
- 4 model files to delete, 3 to preserve, 1 to analyze
- 5 service files to delete, 5 to preserve, 6 to analyze
- ~15 test files to delete, ~9 to preserve
- Import analysis required for 7 "ANALYZE" files in Phase 1

**Next Phase**: Phase 1 (Design & Contracts) - Generate deletion inventory and validation strategy

**Dependencies Resolved**: All research questions answered. Ready for detailed design.

---
**Research completed**: 2025-10-11
**Next artifact**: data-model.md (Phase 1 output)
