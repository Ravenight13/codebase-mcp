# Tasks: Remove Non-Search MCP Tools

**Input**: Design documents from `/specs/007-remove-non-search/`
**Prerequisites**: plan.md, research.md, data-model.md, quickstart.md

## Execution Overview

This feature removes 14 non-search MCP tools through 4 atomic sub-phases with comprehensive final validation. Unlike typical features, this is a **deletion workflow** with intermediate breakage tolerance. Validation occurs only at baseline (before) and final state (after).

**Key Principles**:
- 4 atomic commits, one per sub-phase
- Intermediate breakage acceptable (clarification #1)
- Comprehensive validation only at final state (clarification #3, #5)
- Delete code exclusively used by non-search tools (clarification #2)

**Expected Outcome**: 16 → 2 MCP tools, ~60% code reduction, all search functionality preserved

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[DELETE]**: File deletion task
- **[UPDATE]**: File modification task
- **[VALIDATE]**: Test execution or verification task
- Include exact file paths in descriptions

---

## Phase 3.1: Pre-Deletion Baseline (CRITICAL FIRST STEP)

**Purpose**: Establish passing test baseline before any deletions

### Validation Tasks

- [X] **T000** [VALIDATE] Verify prerequisites before starting
  - Check 1: PostgreSQL running: `pg_isready -h localhost`
  - Check 2: Database exists: `psql -lqt | cut -d \| -f 1 | grep -qw codebase_mcp`
  - Check 3: Migration 002 applied: `cd alembic && alembic current` (expect revision from migration 002)
  - Success: All checks pass
  - Rationale: This feature depends on Phase 01 (migration 002) and working database
  - Dependencies: None
  - Blocker for: T002 (renamed from old T002)

- [X] **T002** [VALIDATE] Run search integration tests to establish baseline
  - File: `tests/integration/test_semantic_search.py`
  - Command: `pytest tests/integration/test_semantic_search.py -v`
  - Success: Record passing test count (use in T070)
  - Rationale: Detect pre-existing failures before deletions
  - Dependencies: T000 must pass
  - Blocker for: T003 (must pass before proceeding)

- [X] **T003** [VALIDATE] Run indexing integration tests to establish baseline
  - File: `tests/integration/test_repository_indexing.py`
  - Command: `pytest tests/integration/test_repository_indexing.py -v`
  - Success: All tests pass, record count
  - Rationale: Verify indexing workflow works before changes
  - Dependencies: T002 must pass
  - Blocker for: T004 (must pass before proceeding)

- [X] **T004** [VALIDATE] Verify server starts and registers 16 tools
  - File: `src/mcp/server_fastmcp.py`
  - Command: `python -m src.mcp.server_fastmcp` (inspect output)
  - Success: Server starts, 16 tools registered
  - Rationale: Baseline tool count for comparison
  - Dependencies: T002, T003 must pass
  - Blocker for: T005 (checkpoint gate)

---

## Phase 3.2: Sub-Phase 1 - Delete Tool Files

**Purpose**: Remove 4 tool files containing 14 non-search MCP tools

**⚠️ Intermediate breakage acceptable after this phase**

### Deletion Tasks

- [X] **T005** [DELETE] Delete task management tools file
  - File: `src/mcp/tools/tasks.py`
  - Command: `rm src/mcp/tools/tasks.py`
  - Contains: get_task, list_tasks, create_task, update_task (4 tools)
  - Dependencies: T004 checkpoint passed

- [X] **T006** [DELETE] Delete work item tools file
  - File: `src/mcp/tools/work_items.py`
  - Command: `rm src/mcp/tools/work_items.py`
  - Contains: create_work_item, update_work_item, query_work_item, list_work_items (4 tools)
  - Dependencies: T004 checkpoint passed

- [X] **T007** [DELETE] Delete vendor tracking tools file
  - File: `src/mcp/tools/tracking.py`
  - Command: `rm src/mcp/tools/tracking.py`
  - Contains: query_vendor_status, update_vendor_status, create_vendor (3 tools)
  - Dependencies: T004 checkpoint passed

- [X] **T008** [DELETE] Delete project configuration tools file
  - File: `src/mcp/tools/configuration.py`
  - Command: `rm src/mcp/tools/configuration.py`
  - Contains: get_project_configuration, update_project_configuration, record_deployment (3 tools)
  - Dependencies: T004 checkpoint passed

- [X] **T009** [UPDATE] Update tools module init to remove deleted tool imports
  - File: `src/mcp/tools/__init__.py`
  - Action: Remove imports for tasks.py, work_items.py, tracking.py, configuration.py
  - Keep: indexing.py, search.py imports only
  - Dependencies: T005-T008 complete

### Git Commit

- [X] **T010** [GIT] Commit Sub-Phase 1 deletion
  - Command: `git add src/mcp/tools/ && git commit -m "chore(tools): delete 14 non-search MCP tools"`
  - Message: Include "Intermediate breakage acceptable. Related: #007-remove-non-search Sub-Phase 1"
  - Files: 4 deletions (tasks.py, work_items.py, tracking.py, configuration.py), 1 update (__init__.py)
  - Dependencies: T005-T009 complete
  - Blocker for: T011 (sub-phase gate)

---

## Phase 3.3: Sub-Phase 2 - Delete Database Operations

**Purpose**: Remove models, services, and analyzed utility files

**⚠️ Intermediate breakage acceptable after this phase**

### Analysis Task

- [X] **T011** [VALIDATE] Run import analysis on 7 ANALYZE files
  - Files: `src/models/types.py`, `src/services/cache.py`, `src/services/validation.py`, `src/services/locking.py`, `src/services/git_history.py`, `src/services/markdown.py`, `src/services/fallback.py`
  - Command: Check imports in all search code AND infrastructure files
  - Example: `grep -r "from src.services.cache import" src/mcp/tools/indexing.py src/mcp/tools/search.py src/services/indexer.py src/services/searcher.py src/services/embedder.py src/services/chunker.py src/services/scanner.py src/models/repository.py src/models/code_chunk.py src/models/code_file.py src/mcp/server_fastmcp.py src/database/session.py src/config/settings.py`
  - Repeat: For each ANALYZE file (7 total)
  - Also check: Infrastructure files may use utilities (server, database session, config)
  - Success: Confirm ZERO imports in search code AND infrastructure (per data-model.md Section 3)
  - Dependencies: T010 commit complete
  - Rationale: Verify deletion safety before removing files

### Model Deletion Tasks

- [X] **T012** [P] [DELETE] Delete Task model
  - File: `src/models/task.py`
  - Rationale: Exclusively used by task tools
  - Dependencies: T011 analysis complete

- [X] **T013** [P] [DELETE] Delete Task schemas
  - File: `src/models/task_schemas.py`
  - Rationale: Exclusively used by task tools
  - Dependencies: T011 analysis complete

- [X] **T014** [P] [DELETE] Delete Task relations
  - File: `src/models/task_relations.py`
  - Rationale: Exclusively used by task tools
  - Dependencies: T011 analysis complete

- [X] **T015** [P] [DELETE] Delete Tracking models
  - File: `src/models/tracking.py`
  - Rationale: Contains Vendor, DeploymentEvent, ProjectConfig models
  - Dependencies: T011 analysis complete

- [X] **T016** [P] [DELETE] Delete Tracking models backup file
  - File: `src/models/tracking.py.backup`
  - Rationale: Backup of deleted tracking.py
  - Dependencies: T011 analysis complete

### Service Deletion Tasks

- [X] **T017** [P] [DELETE] Delete TaskService
  - File: `src/services/tasks.py`
  - Rationale: Exclusively used by task tools
  - Dependencies: T011 analysis complete

- [X] **T018** [P] [DELETE] Delete WorkItemService
  - File: `src/services/work_items.py`
  - Rationale: Exclusively used by work item tools
  - Dependencies: T011 analysis complete

- [X] **T019** [P] [DELETE] Delete VendorService
  - File: `src/services/vendor.py`
  - Rationale: Exclusively used by vendor tracking tools
  - Dependencies: T011 analysis complete

- [X] **T020** [P] [DELETE] Delete DeploymentService
  - File: `src/services/deployment.py`
  - Rationale: Exclusively used by deployment tracking tools
  - Dependencies: T011 analysis complete

- [X] **T021** [P] [DELETE] Delete HierarchyService
  - File: `src/services/hierarchy.py`
  - Rationale: Exclusively used by work item hierarchy
  - Dependencies: T011 analysis complete

- [X] **T022** [P] [DELETE] Delete HierarchyService stub file
  - File: `src/services/hierarchy.pyi`
  - Rationale: Type stub for deleted hierarchy.py
  - Dependencies: T011 analysis complete

### Utility Deletion Tasks (from ANALYZE files)

- [X] **T023** [P] [DELETE] Delete types utility
  - File: `src/models/types.py`
  - Rationale: NOT imported by search code (per import analysis)
  - Dependencies: T011 analysis complete

- [X] **T024** [P] [DELETE] Delete cache utility
  - File: `src/services/cache.py`
  - Rationale: NOT imported by search code (per import analysis)
  - Dependencies: T011 analysis complete

- [X] **T025** [P] [DELETE] Delete validation utility
  - File: `src/services/validation.py`
  - Rationale: NOT imported by search code (per import analysis)
  - Dependencies: T011 analysis complete

- [X] **T026** [P] [DELETE] Delete locking utility
  - File: `src/services/locking.py`
  - Rationale: NOT imported by search code (per import analysis)
  - Dependencies: T011 analysis complete

- [X] **T027** [P] [DELETE] Delete git_history utility
  - File: `src/services/git_history.py`
  - Rationale: NOT imported by search code (per import analysis)
  - Dependencies: T011 analysis complete

- [X] **T028** [P] [DELETE] Delete git_history stub file
  - File: `src/services/git_history.pyi`
  - Rationale: Type stub for deleted git_history.py
  - Dependencies: T011 analysis complete

- [X] **T029** [P] [DELETE] Delete markdown utility
  - File: `src/services/markdown.py`
  - Rationale: NOT imported by search code (per import analysis)
  - Dependencies: T011 analysis complete

- [X] **T030** [P] [DELETE] Delete markdown stub file
  - File: `src/services/markdown.pyi`
  - Rationale: Type stub for deleted markdown.py
  - Dependencies: T011 analysis complete

- [X] **T031** [P] [DELETE] Delete fallback utility
  - File: `src/services/fallback.py`
  - Rationale: NOT imported by search code (per import analysis)
  - Dependencies: T011 analysis complete

- [X] **T032** [P] [DELETE] Delete hierarchy README documentation
  - File: `src/services/README_hierarchy.md`
  - Rationale: Documentation for deleted hierarchy.py
  - Dependencies: T011 analysis complete

### Git Commit

- [X] **T033** [GIT] Commit Sub-Phase 2 deletion
  - Command: `git add src/models/ src/services/ && git commit -m "chore(models,services): delete non-search database operations"`
  - Message: Include "Intermediate breakage acceptable. Related: #007-remove-non-search Sub-Phase 2"
  - Files: 5 model deletions, 5 service deletions, 7 utility deletions, 4 stub/doc deletions (21 total)
  - Dependencies: T012-T032 complete
  - Blocker for: T034 (sub-phase gate)

---

## Phase 3.4: Sub-Phase 3 - Update Server Registration

**Purpose**: Clean up server.py imports and verify 2-tool registration

**⚠️ Intermediate breakage acceptable after this phase**

### Update Tasks

- [X] **T034** [UPDATE] Remove deleted tool imports from server.py
  - File: `src/mcp/server_fastmcp.py`
  - Action: Remove imports for tasks, work_items, tracking, configuration tools
  - Keep: indexing, search tool imports only
  - Verify: Only @mcp.tool() decorators for index_repository and search_code remain
  - Dependencies: T033 commit complete

- [X] **T033b** [UPDATE] Fix pyproject.toml entry point
  - File: `pyproject.toml`
  - Action: Change entry point from `codebase-mcp = "src.main:main"` to `codebase-mcp = "src.mcp.server_fastmcp:main"`
  - Rationale: Current entry point references non-existent src/main.py file
  - Dependencies: T033 commit complete

- [X] **T035** [UPDATE] Update database README to remove deleted table references
  - File: `src/database/README.md`
  - Action: Remove documentation for tasks, work_items, vendors, deployments, project_config tables
  - Keep: Documentation for repositories, code_chunks tables only
  - Dependencies: T033 commit complete

- [X] **T036** [UPDATE] Clean up model module init
  - File: `src/models/__init__.py`
  - Action: Remove imports for task.py, task_schemas.py, task_relations.py, tracking.py
  - Keep: repository.py, code_chunk.py, code_file.py, database.py imports only
  - Dependencies: T033 commit complete

- [X] **T037** [UPDATE] Clean up service module init
  - File: `src/services/__init__.py`
  - Action: Remove imports for tasks.py, work_items.py, vendor.py, deployment.py, hierarchy.py
  - Keep: indexer.py, embedder.py, chunker.py, scanner.py, searcher.py imports only
  - Dependencies: T033 commit complete

### Git Commit

- [X] **T038** [GIT] Commit Sub-Phase 3 cleanup
  - Command: `git add src/mcp/server_fastmcp.py pyproject.toml src/database/README.md src/models/__init__.py src/services/__init__.py && git commit -m "chore(server): verify 2-tool registration and cleanup imports"`
  - Message: Include "Intermediate breakage acceptable. Related: #007-remove-non-search Sub-Phase 3"
  - Files: 5 updates (server.py, pyproject.toml, README.md, 2 __init__.py files)
  - Dependencies: T034-T037 complete
  - Blocker for: T039 (sub-phase gate)

---

## Phase 3.5: Sub-Phase 4 - Delete Tests and Final Validation

**Purpose**: Complete deletion and verify comprehensive success criteria

**✅ NO intermediate breakage - all validations must pass**

**Integration Tests to PRESERVE** (not deleted in this phase):
- `test_semantic_search.py` - Search functionality (used in T002, T081 baseline/validation)
- `test_repository_indexing.py` - Indexing functionality (used in T003, T082 baseline/validation)
- `test_ai_assistant_integration.py` - MCP protocol integration tests
- `test_migration_002_upgrade.py` - Phase 01 migration validation
- `test_migration_002_downgrade.py` - Phase 01 migration validation
- `test_migration_002_validation.py` - Phase 01 migration validation
- `test_migration_data_preservation.py` - Phase 01 data integrity
- `test_performance_validation.py` - Search performance benchmarks
- `test_incremental_updates.py` - Indexing incremental updates
- `test_file_deletion_retention.py` - Indexing file lifecycle

These tests validate search/indexing functionality and Phase 01 migration - they remain to ensure no regression.

**Parallel Execution Example** (40 test deletions):
```bash
# Option 1: Delete by pattern with xargs (8 parallel jobs)
find tests/integration -name "test_task*.py" -o -name "test_*work_item*.py" -o \
     -name "test_*vendor*.py" -o -name "test_deployment*.py" | xargs -P 8 rm

find tests/unit -name "test_base_task*.py" -o -name "test_task_*.py" -o \
     -name "test_hierarchical*.py" -o -name "test_locking*.py" -o \
     -name "test_vendor*.py" -o -name "test_status*.py" | xargs -P 8 rm

find tests/contract -name "test_*task*.py" -o -name "test_*work_item*.py" -o \
     -name "test_*vendor*.py" -o -name "test_deployment*.py" -o \
     -name "test_configuration*.py" | xargs -P 8 rm

find tests -maxdepth 1 -name "test_cache.py" -o -name "test_mcp_server.py" -o \
     -name "test_mcp_tools.py" -o -name "test_tool_handlers.py" -o \
     -name "test_minimal*.py" -o -name "ultra_minimal.py" | xargs -P 8 rm

# Option 2: Explicit file list with parallel deletion
cat > /tmp/delete_tests.txt <<'EOF'
tests/integration/test_task_lifecycle.py
tests/integration/test_list_tasks_optimization.py
[... all 40 files ...]
EOF
cat /tmp/delete_tests.txt | xargs -P 8 -I {} rm {}
```

Note: Parallel deletion is optional - sequential deletion (T039-T078) is safer for tracking.

### Integration Test Deletion Tasks (Task-Related)

- [X] **T039** [P] [DELETE] Delete task lifecycle integration tests
  - File: `tests/integration/test_task_lifecycle.py`
  - Rationale: Tests deleted task tools
  - Dependencies: T038 commit complete

- [X] **T040** [P] [DELETE] Delete list tasks optimization integration tests
  - File: `tests/integration/test_list_tasks_optimization.py`
  - Rationale: Tests deleted task tools
  - Dependencies: T038 commit complete

- [X] **T041** [P] [DELETE] Delete session detachment fix integration tests
  - File: `tests/integration/test_session_detachment_fix.py`
  - Rationale: Tests deleted task/session tools
  - Dependencies: T038 commit complete

- [X] **T042** [P] [DELETE] Delete filtered summary integration tests
  - File: `tests/integration/test_filtered_summary.py`
  - Rationale: Tests deleted task tools
  - Dependencies: T038 commit complete

### Integration Test Deletion Tasks (Work Item-Related)

- [X] **T043** [P] [DELETE] Delete hierarchical work item query integration tests
  - File: `tests/integration/test_hierarchical_work_item_query.py`
  - Rationale: Tests deleted work item tools
  - Dependencies: T038 commit complete

- [X] **T044** [P] [DELETE] Delete concurrent work item updates integration tests
  - File: `tests/integration/test_concurrent_work_item_updates.py`
  - Rationale: Tests deleted work item tools
  - Dependencies: T038 commit complete

- [X] **T045** [P] [DELETE] Delete two-tier pattern integration tests
  - File: `tests/integration/test_two_tier_pattern.py`
  - Rationale: Tests deleted work item tools
  - Dependencies: T038 commit complete

- [X] **T046** [P] [DELETE] Delete multi-client concurrent access integration tests
  - File: `tests/integration/test_multi_client_concurrent_access.py`
  - Rationale: Tests deleted work item tools
  - Dependencies: T038 commit complete

### Integration Test Deletion Tasks (Vendor/Tracking-Related)

- [X] **T047** [P] [DELETE] Delete deployment event recording integration tests
  - File: `tests/integration/test_deployment_event_recording.py`
  - Rationale: Tests deleted deployment tracking tools
  - Dependencies: T038 commit complete

- [X] **T048** [P] [DELETE] Delete create vendor integration tests
  - File: `tests/integration/test_create_vendor_integration.py`
  - Rationale: Tests deleted vendor tracking tools
  - Dependencies: T038 commit complete

- [X] **T049** [P] [DELETE] Delete create vendor performance integration tests
  - File: `tests/integration/test_create_vendor_performance.py`
  - Rationale: Tests deleted vendor tracking tools
  - Dependencies: T038 commit complete

- [X] **T050** [P] [DELETE] Delete vendor query performance integration tests
  - File: `tests/integration/test_vendor_query_performance.py`
  - Rationale: Tests deleted vendor tracking tools
  - Dependencies: T038 commit complete

- [X] **T051** [P] [DELETE] Delete vendor case insensitive uniqueness integration tests
  - File: `tests/integration/test_vendor_case_insensitive_uniqueness.py`
  - Rationale: Tests deleted vendor tracking tools
  - Dependencies: T038 commit complete

- [X] **T052** [P] [DELETE] Delete full status generation performance integration tests
  - File: `tests/integration/test_full_status_generation_performance.py`
  - Rationale: Tests deleted vendor tracking tools
  - Dependencies: T038 commit complete

### Integration Test Deletion Tasks (Utility-Related)

- [X] **T053** [P] [DELETE] Delete database unavailable fallback integration tests
  - File: `tests/integration/test_database_unavailable_fallback.py`
  - Rationale: Tests deleted fallback service
  - Dependencies: T038 commit complete

### Unit Test Deletion Tasks

- [X] **T054** [P] [DELETE] Delete base task fields unit tests
  - File: `tests/unit/test_base_task_fields.py`
  - Rationale: Tests deleted Task model
  - Dependencies: T038 commit complete

- [X] **T055** [P] [DELETE] Delete task summary model unit tests
  - File: `tests/unit/test_task_summary_model.py`
  - Rationale: Tests deleted Task schemas
  - Dependencies: T038 commit complete

- [X] **T056** [P] [DELETE] Delete hierarchical queries unit tests
  - File: `tests/unit/test_hierarchical_queries.py`
  - Rationale: Tests deleted HierarchyService
  - Dependencies: T038 commit complete

- [X] **T057** [P] [DELETE] Delete locking service unit tests
  - File: `tests/unit/test_locking_service.py`
  - Rationale: Tests deleted locking utility
  - Dependencies: T038 commit complete

- [X] **T058** [P] [DELETE] Delete vendor validation unit tests
  - File: `tests/unit/test_vendor_validation.py`
  - Rationale: Tests deleted VendorService
  - Dependencies: T038 commit complete

- [X] **T059** [P] [DELETE] Delete status translation unit tests
  - File: `tests/unit/test_status_translation.py`
  - Rationale: Tests deleted task/work item status translation
  - Dependencies: T038 commit complete

### Contract Test Deletion Tasks (Task-Related)

- [X] **T060** [P] [DELETE] Delete create task contract tests
  - File: `tests/contract/test_create_task_contract.py`
  - Rationale: Contract tests for deleted create_task tool
  - Dependencies: T038 commit complete

- [X] **T061** [P] [DELETE] Delete get task contract tests
  - File: `tests/contract/test_get_task_contract.py`
  - Rationale: Contract tests for deleted get_task tool
  - Dependencies: T038 commit complete

- [X] **T062** [P] [DELETE] Delete list tasks contract tests
  - File: `tests/contract/test_list_tasks_contract.py`
  - Rationale: Contract tests for deleted list_tasks tool
  - Dependencies: T038 commit complete

- [X] **T063** [P] [DELETE] Delete update task contract tests
  - File: `tests/contract/test_update_task_contract.py`
  - Rationale: Contract tests for deleted update_task tool
  - Dependencies: T038 commit complete

- [X] **T064** [P] [DELETE] Delete list tasks full details contract tests
  - File: `tests/contract/test_list_tasks_full_details.py`
  - Rationale: Contract tests for deleted list_tasks tool
  - Dependencies: T038 commit complete

- [X] **T065** [P] [DELETE] Delete list tasks summary contract tests
  - File: `tests/contract/test_list_tasks_summary.py`
  - Rationale: Contract tests for deleted list_tasks tool
  - Dependencies: T038 commit complete

### Contract Test Deletion Tasks (Work Item-Related)

- [X] **T066** [P] [DELETE] Delete list work items contract tests
  - File: `tests/contract/test_list_work_items_contract.py`
  - Rationale: Contract tests for deleted work item tools
  - Dependencies: T038 commit complete

- [X] **T067** [P] [DELETE] Delete update work item contract tests
  - File: `tests/contract/test_update_work_item_contract.py`
  - Rationale: Contract tests for deleted work item tools
  - Dependencies: T038 commit complete

- [X] **T068** [P] [DELETE] Delete work item CRUD contract tests
  - File: `tests/contract/test_work_item_crud_contract.py`
  - Rationale: Contract tests for deleted work item tools
  - Dependencies: T038 commit complete

### Contract Test Deletion Tasks (Vendor/Tracking-Related)

- [X] **T069** [P] [DELETE] Delete vendor tracking contract tests
  - File: `tests/contract/test_vendor_tracking_contract.py`
  - Rationale: Contract tests for deleted vendor tools
  - Dependencies: T038 commit complete

- [X] **T070** [P] [DELETE] Delete deployment tracking contract tests
  - File: `tests/contract/test_deployment_tracking_contract.py`
  - Rationale: Contract tests for deleted deployment tools
  - Dependencies: T038 commit complete

- [X] **T071** [P] [DELETE] Delete create vendor contract tests
  - File: `tests/contract/test_create_vendor_contract.py`
  - Rationale: Contract tests for deleted vendor tools
  - Dependencies: T038 commit complete

- [X] **T072** [P] [DELETE] Delete configuration contract tests
  - File: `tests/contract/test_configuration_contract.py`
  - Rationale: Contract tests for deleted configuration tools
  - Dependencies: T038 commit complete

### Root-Level Test Deletion Tasks

- [X] **T073** [P] [DELETE] Delete cache service root tests
  - File: `tests/test_cache.py`
  - Rationale: Tests deleted cache.py service
  - Dependencies: T038 commit complete

- [X] **T074** [P] [DELETE] Delete MCP server root tests
  - File: `tests/test_mcp_server.py`
  - Rationale: Tests all MCP tools (including deleted ones)
  - Dependencies: T038 commit complete

- [X] **T075** [P] [DELETE] Delete MCP tools root tests
  - File: `tests/test_mcp_tools.py`
  - Rationale: Tests all 6 tools including deleted task tools
  - Dependencies: T038 commit complete

- [X] **T076** [P] [DELETE] Delete tool handlers root tests
  - File: `tests/test_tool_handlers.py`
  - Rationale: Tests deleted task tool handlers
  - Dependencies: T038 commit complete

- [X] **T077** [P] [DELETE] Delete minimal MCP test script
  - File: `tests/test_minimal_mcp.py`
  - Rationale: Test harness for deleted tools
  - Dependencies: T038 commit complete

- [X] **T078** [P] [DELETE] Delete ultra minimal test script
  - File: `tests/ultra_minimal.py`
  - Rationale: Test harness no longer needed
  - Dependencies: T038 commit complete

**Root Test Analysis Rationale**:
- `test_cache.py` - DELETE: Tests cache.py service being deleted
- `test_mcp_server.py` - DELETE: Tests all 16 MCP tools including 14 deleted tools
- `test_mcp_tools.py` - DELETE: Tests task tool implementations being deleted
- `test_tool_handlers.py` - DELETE: Tests task tool handler patterns being removed
- `test_minimal_mcp.py` - DELETE: Minimal test harness for deleted tools
- `ultra_minimal.py` - DELETE: Ultra-minimal test script no longer needed

Analysis: Manual inspection confirmed these root tests exercise deleted functionality.

### Final Validation Tasks (ALL MUST PASS)

- [X] **T079** [VALIDATE] Run import checks on all preserved modules
  - Command: Check all preserved modules can import:
    * `python -c "import src.mcp.server_fastmcp"`
    * `python -c "import src.mcp.tools.indexing"`
    * `python -c "import src.mcp.tools.search"`
    * `python -c "import src.services.indexer"`
    * `python -c "import src.services.searcher"`
    * `python -c "import src.services.embedder"`
    * `python -c "import src.services.chunker"`
    * `python -c "import src.services.scanner"`
    * `python -c "import src.models.repository"`
    * `python -c "import src.models.code_chunk"`
    * `python -c "import src.models.code_file"`
    * `python -c "import src.models.database"`
    * `python -c "import src.config.settings"`
    * `python -c "import src.database.session"`
  - Success: ZERO ImportError or ModuleNotFoundError
  - Dependencies: T039-T078 complete
  - Blocker for: T080 (critical gate)

- [X] **T080** [VALIDATE] Run mypy type checking with strict mode
  - Command: `mypy --strict src/`
  - Success: "Success: no issues found" (zero type errors)
  - Additional Check: Verify no new `type: ignore` comments added (run `git diff main -- src/ | grep "type: ignore"` - expect zero results)
  - Dependencies: T079 passes
  - Blocker for: T081 (critical gate)

- [X] **T081** [VALIDATE] Run search integration tests (verify match baseline)
  - File: `tests/integration/test_semantic_search.py`
  - Command: `pytest tests/integration/test_semantic_search.py -v`
  - Success: All tests pass, count MATCHES T002 baseline
  - Dependencies: T080 passes
  - Blocker for: T082 (critical gate)

- [X] **T082** [VALIDATE] Run indexing integration tests (verify match baseline)
  - File: `tests/integration/test_repository_indexing.py`
  - Command: `pytest tests/integration/test_repository_indexing.py -v`
  - Success: All tests pass, count MATCHES T003 baseline
  - Dependencies: T081 passes
  - Blocker for: T083 (critical gate)

- [X] **T083** [VALIDATE] Verify server startup and 2-tool registration
  - File: `src/mcp/server_fastmcp.py`
  - Command: `python -m src.mcp.server_fastmcp` (inspect output)
  - Success: Server starts, exactly 2 tools registered (index_repository, search_code)
  - Dependencies: T082 passes
  - Blocker for: T084 (critical gate)

- [X] **T084** [VALIDATE] Run full test suite (all preserved tests)
  - Command: `pytest tests/ -v`
  - Success: All preserved tests pass (unit + integration + contract for search/indexing)
  - Dependencies: T083 passes
  - Blocker for: T085 (final commit gate)

### Git Commit

- [X] **T085** [GIT] Commit Sub-Phase 4 deletion and validation results
  - Command: `git add tests/ && git commit -m "chore(tests): delete non-search tests and verify final state"`
  - Message: Include validation results (import ✅, mypy ✅, tests ✅, server ✅, tool count ✅)
  - Message: Include edge case validation checklist:
    * ✅ Edge Case 1: Server starts after tool removal (T083)
    * ✅ Edge Case 2: System handles imports for deleted code (T079)
    * ✅ Edge Case 3: Tests for removed functionality deleted (T039-T078)
    * ✅ Edge Case 4: Search functionality not broken (T002, T081-T082)
  - Message: Include "Related: #007-remove-non-search Sub-Phase 4"
  - Files: 40 test deletions (15 integration, 6 unit, 13 contract, 6 root-level)
  - Dependencies: T039-T084 complete (all validations pass)

---

## Dependencies Graph

```
BASELINE (Phase 3.1):
T002 (search tests baseline) → T003 (indexing tests baseline) → T004 (server verification)
                                                                      ↓
SUB-PHASE 1 (Phase 3.2):
T004 → T005,T006,T007,T008 (delete tool files) → T009 (update __init__) → T010 (commit)
                                                                              ↓
SUB-PHASE 2 (Phase 3.3):
T010 → T011 (import analysis) → T012-T032 [P] (delete 21 files) → T033 (commit)
                                                                      ↓
SUB-PHASE 3 (Phase 3.4):
T033 → T034,T035,T036,T037 (cleanup imports) → T038 (commit)
                                                   ↓
SUB-PHASE 4 (Phase 3.5):
T038 → T039-T078 [P] (delete 40 test files) → T079 (imports) → T080 (mypy) → T081 (search tests)
       → T082 (indexing tests) → T083 (server) → T084 (full suite) → T085 (commit)
```

### Critical Paths

1. **Baseline Path**: T002 → T003 → T004 (must pass before any deletions)
4. **Validation Path**: T079 → T080 → T081 → T082 → T083 → T084 (must pass before final commit)
5. **Commit Path**: T010 → T033 → T038 → T085 (4 atomic commits)

### Parallel Execution Opportunities

**Phase 3.3 (Sub-Phase 2)**:
- T012-T016 [P]: All 5 model deletions can run in parallel
- T017-T022 [P]: All 6 service deletions (including stubs) can run in parallel
- T023-T032 [P]: All 10 utility/stub/doc deletions can run in parallel

**Phase 3.5 (Sub-Phase 4)**:
- T039-T078 [P]: All 40 test deletions can run in parallel

**Example Parallel Task Execution**:
```bash
# Phase 3.3: Delete models in parallel
Task: "Delete Task model (src/models/task.py)"
Task: "Delete Task schemas (src/models/task_schemas.py)"
Task: "Delete Task relations (src/models/task_relations.py)"
Task: "Delete Tracking models (src/models/tracking.py)"
Task: "Delete Tracking models backup (src/models/tracking.py.backup)"

# Phase 3.3: Delete services in parallel
Task: "Delete TaskService (src/services/tasks.py)"
Task: "Delete WorkItemService (src/services/work_items.py)"
Task: "Delete VendorService (src/services/vendor.py)"
Task: "Delete DeploymentService (src/services/deployment.py)"
Task: "Delete HierarchyService (src/services/hierarchy.py)"
Task: "Delete HierarchyService stub (src/services/hierarchy.pyi)"
```

---

## Task Ordering Rules

1. **Baseline First**: T002-T004 establish working state (critical gate)
3. **Sequential Sub-Phases**: Follow spec ordering (tools → DB ops → registration → tests)
4. **Atomic Commits**: One commit per sub-phase (T010, T033, T038, T085)
5. **Comprehensive Validation**: All validation in final sub-phase (T079-T084)
6. **Parallel Within Sub-Phase**: T012-T032 [P] in Phase 3.3, T039-T078 [P] in Phase 3.5
7. **NO Parallelization Across Sub-Phases**: T010 blocks T011, T033 blocks T034, etc.

---

## Success Criteria Checklist

**ALL criteria must be met before marking feature complete**:

### Prerequisites
- [X] T000: Database prerequisites verified (PostgreSQL running, database exists, migration 002 applied)

### Import Validation
- [X] T079: All modules import without errors (ZERO ModuleNotFoundError)

### Type Safety
- [X] T080: mypy --strict passes with 0 errors ("Success: no issues found")

### Search Functionality Preservation
- [X] T081: All search integration tests pass (count matches T002 baseline)
- [X] T082: All indexing integration tests pass (count matches T003 baseline)
- [X] T084: Full test suite passes (all preserved tests)

### Server Health
- [X] T083: Server starts successfully (no exceptions)
- [X] T083: Server responds to MCP protocol

### Tool Count Verification
- [X] T083: Exactly 2 tools registered (index_repository, search_code)
- [X] T083: No deleted tools present in registration

### Git History
- [X] 4 atomic commits created (T010, T033, T038, T085)
- [X] Commit messages follow Conventional Commits format
- [X] Each commit references #007-remove-non-search

### Code Reduction
- [X] ~60% code reduction achieved (outcome estimate, not hard requirement per clarification #4)
- [X] 16 → 2 MCP tools (87.5% tool reduction)

---

## Notes

### TDD Approach
- **NOT APPLICABLE**: This is a deletion feature, not a build feature
- No new code written, so no TDD cycle required
- Validation focuses on preserving existing search functionality

### Intermediate Breakage Strategy
- **Sub-Phase 1-3**: Import errors and test failures EXPECTED and ACCEPTABLE
- **Sub-Phase 4**: All validations MUST pass before final commit
- Per clarification #1: "Intermediate sub-phases can have broken imports; only final state must work"

### Import Analysis (T011)
- **Critical**: Verifies deletion safety before removing ANALYZE files
- Per data-model.md Section 3: ZERO imports expected in search code
- If imports found: STOP and re-evaluate deletion safety

### Commit Messages
- Follow Conventional Commits format: `chore(scope): description`
- Include "Intermediate breakage acceptable" for T010, T033, T038
- Include validation results in T085 commit message
- Reference #007-remove-non-search in all commits

**Commit Message Format**:
```
chore(scope): brief summary (max 50 chars)

Detailed description of changes made in this sub-phase.
Explain what was deleted and why.

Status/Validation:
- Item 1: ✅ Description
- Item 2: ✅ Description

Related: #007-remove-non-search Sub-Phase N
```

For intermediate sub-phases (1-3): Include "Intermediate breakage acceptable"
For final sub-phase (4): Include validation results and edge case checklist

### Rollback Strategy
- Each sub-phase is atomic (single commit)
- Rollback: `git revert <commit-hash>` for problematic sub-phase
- Full rollback: `git revert T085..T010` (revert all 4 commits)

---

## Validation Checklist

*Applied during execution to ensure task completeness*

- [x] All deletion targets identified (50+ files in data-model.md)
- [x] All preservation targets identified (19 files in data-model.md)
- [x] Import analysis strategy defined (T011)
- [x] Parallel tasks truly independent (different files)
- [x] Each task specifies exact file path
- [x] Baseline validation before deletions (T002-T004)
- [x] Comprehensive validation at final state (T079-T084)
- [x] 4 atomic commits planned (T010, T033, T038, T085)
- [x] Success criteria match clarification #5 (import + mypy + tests)

---

## Estimated Timeline

****Total Tasks**: 86 tasks
- Phase 3.1 (Prerequisites & Baseline): 4 tasks (~2 minutes)
- Phase 3.2 (Sub-Phase 1): 6 tasks (~5 minutes)
- Phase 3.3 (Sub-Phase 2): 23 tasks (~12 minutes with parallelization)
- Phase 3.4 (Sub-Phase 3): 6 tasks (~5 minutes)
- Phase 3.5 (Sub-Phase 4): 47 tasks (~25 minutes with parallelization)

****Total Estimated Duration**: 50-55 minutes (with parallel execution)
****Without Parallelization**: ~95 minutes

**Critical Path**: T000 → T002 → T003 → T004 → T010 → T011 → T033 → T038 → T079 → T080 → T081 → T082 → T083 → T084 → T085

---

**Last Updated**: 2025-10-12
**Feature**: 007-remove-non-search
**Task Count**: 86 tasks (1 prerequisite + 3 baseline + 6 sub-phase 1 + 23 sub-phase 2 + 6 sub-phase 3 + 47 sub-phase 4)
**Deletion Scope**: 65 files deleted (4 tools, 21 models/services/utilities/stubs/docs, 40 tests), 5 files updated
**Expected Outcome**: 16 → 2 MCP tools, ~60% code reduction, all search functionality preserved
