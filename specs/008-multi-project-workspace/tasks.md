# Tasks: Multi-Project Workspace Support

**Feature**: 008-multi-project-workspace
**Branch**: `008-multi-project-workspace`
**Input**: Design documents from `/specs/008-multi-project-workspace/`
**Prerequisites**: plan.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

## Execution Summary

**Total Tasks**: 42
**Parallel Tasks**: 21 (marked [P])
**Sequential Tasks**: 21
**Estimated Duration**: 8-12 hours (with parallel execution)

## Path Conventions

This is a **single Python project** (MCP server architecture). All paths relative to repository root:
- **Source**: `src/`
- **Tests**: `tests/`
- **Migrations**: `migrations/versions/`
- **Models**: `src/models/`
- **Services**: `src/services/`
- **MCP Tools**: `src/mcp/tools/`

## Phase 3.1: Setup & Foundation (Sequential)

Foundation tasks must complete before service layer. These establish the core data models and database schema required by all subsequent tasks.

- [X] **T001** Create ProjectIdentifier Pydantic model in `src/models/project_identifier.py`
  - **Description**: Implement Pydantic model with regex validation for project IDs (lowercase alphanumeric + hyphens)
  - **Validation**: Field validator with pattern `^[a-z0-9]+(-[a-z0-9]+)*$`, max length 50
  - **Methods**: `to_schema_name()` returns `project_{identifier}`
  - **Dependencies**: None
  - **Traces to**: FR-004, FR-005, FR-006, FR-007, FR-008, FR-016 (security)
  - **File**: `src/models/project_identifier.py` (NEW)
  - **Completed**: Commit 27aed973

- [X] **T002** Create WorkspaceConfig Pydantic model in `src/models/workspace_config.py`
  - **Description**: Implement immutable workspace metadata model with frozen=True
  - **Fields**: project_id (str), schema_name (str), created_at (datetime), metadata (dict)
  - **Validation**: ConfigDict(frozen=True) for immutability
  - **Dependencies**: T001 (imports ProjectIdentifier)
  - **Traces to**: FR-009, FR-010
  - **File**: `src/models/workspace_config.py` (NEW)
  - **Completed**: Commit 83c8127c

- [X] **T003** Create WorkflowIntegrationContext Pydantic model in `src/models/workflow_context.py`
  - **Description**: Implement workflow-mcp integration context with TTL caching logic
  - **Fields**: active_project_id (str | None), status (Literal), retrieved_at (datetime), cache_ttl_seconds (int)
  - **Methods**: `is_expired() -> bool` (check TTL)
  - **Dependencies**: None
  - **Traces to**: FR-012, FR-013, FR-014, FR-015
  - **File**: `src/models/workflow_context.py` (NEW)
  - **Completed**: Commit 256cdfd5

- [X] **T004** Create Alembic migration for project_registry schema
  - **Description**: Create migration to add global registry schema and workspace_config table
  - **SQL**: `CREATE SCHEMA IF NOT EXISTS project_registry;`
  - **Table**: `project_registry.workspace_config` (project_id PK, schema_name UNIQUE, created_at, metadata JSONB)
  - **Indexes**: UNIQUE on schema_name, INDEX on created_at DESC
  - **Dependencies**: None
  - **Traces to**: FR-009, FR-010
  - **File**: `migrations/versions/006_add_project_registry_schema.py` (NEW)
  - **Completed**: Commit 02fc27ec

- [X] **T005** Run Alembic migration to create project_registry schema
  - **Description**: Execute migration script to provision global registry in database
  - **Command**: `alembic upgrade head`
  - **Validation**: Query `information_schema.schemata` for 'project_registry'
  - **Dependencies**: T004
  - **File**: N/A (command execution)
  - **Completed**: Commit 02fc27ec

- [X] **T005a** Provision default workspace schema for backward compatibility
  - **Description**: Create project_default schema to support existing users without project_id parameter
  - **SQL**:
    1. `CREATE SCHEMA IF NOT EXISTS project_default;`
    2. `SET search_path TO project_default;`
    3. Create tables in default schema (copy structure from base schema)
  - **Validation**: Query `information_schema.schemata` for 'project_default'
  - **Dependencies**: T005 (requires registry schema first)
  - **Traces to**: FR-018 (backward compatibility)
  - **File**: `migrations/versions/007_provision_default_workspace.py` (NEW)
  - **Completed**: Commit e1daec18

## Phase 3.2: Service Layer (Parallel after Foundation)

Service implementations are independent and can run in parallel. Each service operates on different modules.

- [X] **T006 [P]** Implement ProjectWorkspaceManager service in `src/services/workspace_manager.py`
  - **Description**: Create workspace provisioning and validation service
  - **Methods**:
    - `ensure_workspace_exists(project_id: str) -> str`: Auto-provision schema on first use
    - `_schema_exists(schema_name: str) -> bool`: Check if schema exists (cached)
    - `_create_schema(schema_name: str) -> None`: Create schema + table structure + pgvector extension
    - `_register_workspace(project_id, schema_name) -> None`: Register in workspace_config
  - **Dependencies**: T001, T002, T005 (requires Pydantic models and registry schema)
  - **Traces to**: FR-009, FR-010, FR-011
  - **File**: `src/services/workspace_manager.py` (NEW)
  - **Completed**: Commit 6c55a3f8

- [X] **T007 [P]** Implement WorkflowIntegrationClient service in `src/services/workflow_client.py`
  - **Description**: Create optional HTTP client for workflow-mcp integration
  - **Methods**:
    - `get_active_project() -> str | None`: Query workflow-mcp with timeout and caching
    - `_handle_timeout()`, `_handle_connection_error()`, `_handle_invalid_response()`
  - **HTTP Client**: httpx.AsyncClient with 1-second timeout
  - **Cache**: In-memory dict with TTL expiration (60 seconds default)
  - **Dependencies**: T003 (imports WorkflowIntegrationContext)
  - **Traces to**: FR-012, FR-013, FR-014, FR-015
  - **File**: `src/services/workflow_client.py` (NEW)
  - **Completed**: Commit b2e7f0c7

- [X] **T008 [P]** Add Settings fields for workflow-mcp in `src/config/settings.py`
  - **Description**: Extend Settings Pydantic model with workflow-mcp configuration
  - **New Fields**:
    - `workflow_mcp_url: HttpUrl | None = None` (optional)
    - `workflow_mcp_timeout: float = 1.0` (1-second default)
    - `workflow_mcp_cache_ttl: int = 60` (seconds)
  - **Dependencies**: None (independent config change)
  - **File**: `src/config/settings.py` (EDIT)
  - **Completed**: Commit 4df5ed25

## Phase 3.3: Database Layer (Sequential)

Database layer changes modify shared session management. Must complete in order.

- [X] **T009** Update get_session() to accept project_id parameter in `src/database/session.py`
  - **Description**: Add optional project_id parameter and SET search_path logic
  - **Signature**: `async def get_session(project_id: str | None = None) -> AsyncGenerator[AsyncSession, None]`
  - **Logic**:
    1. Resolve schema_name from project_id (use ProjectWorkspaceManager)
    2. Execute `SET search_path TO {schema_name}` after session creation
    3. Maintain existing commit/rollback/close behavior
  - **Dependencies**: T006 (uses ProjectWorkspaceManager)
  - **Traces to**: FR-001, FR-002, FR-003, FR-009
  - **File**: `src/database/session.py` (EDIT)
  - **Completed**: Commit 277b884b

- [X] **T009a** Test get_session() backward compatibility in `tests/unit/test_session_backward_compat.py`
  - **Description**: Validate get_session() with project_id=None uses default workspace
  - **Test Cases**:
    - Call get_session(project_id=None) → verify search_path set to "project_default"
    - Call get_session() (parameter omitted) → verify search_path set to "project_default"
    - Test backward compatibility logging
    - Test WorkspaceManager not called for None (performance optimization)
  - **Expected**: Tests PASS (validates backward compatibility)
  - **Dependencies**: T009, T005a (requires get_session updated and default schema exists)
  - **Traces to**: FR-018 (backward compatibility)
  - **File**: `tests/unit/test_session_backward_compat.py` (NEW)
  - **Completed**: Commit 57c5707c

- [X] **T010** Create resolve_project_id() utility function in `src/database/session.py`
  - **Description**: Resolve project_id with workflow-mcp fallback logic
  - **Signature**: `async def resolve_project_id(explicit_id: str | None) -> str | None`
  - **Logic**:
    1. If explicit_id provided: return explicit_id
    2. If workflow_client available: query workflow-mcp (with timeout)
    3. If workflow-mcp unavailable or timeout: return None (default workspace)
  - **Dependencies**: T007 (uses WorkflowIntegrationClient)
  - **Traces to**: FR-012, FR-013, FR-014
  - **Completed**: Commit 660f73ce
  - **File**: `src/database/session.py` (EDIT)

## Phase 3.4: MCP Tool Updates (Parallel after Database Layer)

MCP tools are independent endpoints. Can be updated in parallel.

- [X] **T011 [P]** Update index_repository tool to accept project_id in `src/mcp/tools/indexing.py`
  - **Description**: Add optional project_id parameter to index_repository MCP tool
  - **Parameter**: `project_id: str | None = None` (optional, backward compatible)
  - **Logic**:
    1. Resolve project_id (explicit or workflow-mcp)
    2. Validate project_id via ProjectIdentifier Pydantic model
    3. Pass project_id to get_session()
    4. Ensure workspace exists (auto-provision if needed)
    5. Return project_id and schema_name in response
  - **Dependencies**: T009 (uses updated get_session)
  - **Traces to**: FR-001, FR-009, FR-010
  - **Completed**: Commit 8f59103f
  - **File**: `src/mcp/tools/indexing.py` (EDIT)

- [ ] **T012 [P]** Update search_code tool to accept project_id in `src/mcp/tools/search.py`
  - **Description**: Add optional project_id parameter to search_code MCP tool
  - **Parameter**: `project_id: str | None = None` (optional, backward compatible)
  - **Logic**:
    1. Resolve project_id (explicit or workflow-mcp)
    2. Validate project_id via ProjectIdentifier Pydantic model
    3. Pass project_id to get_session()
    4. Return project_id and schema_name in response
  - **Dependencies**: T009, T010 (uses updated get_session and resolve_project_id)
  - **Traces to**: FR-002, FR-012, FR-013
  - **File**: `src/mcp/tools/search.py` (EDIT)

## Phase 3.5: Contract Tests (Parallel, TDD)

⚠️ **CRITICAL: These tests MUST be written and MUST FAIL before implementation**

Contract tests validate MCP tool parameter additions per contracts/mcp-tools.yaml. All are independent test files.

- [ ] **T013 [P]** Contract test: index_repository with valid project_id in `tests/contract/test_index_project_id.py`
  - **Description**: Test index_repository accepts valid project_id parameter
  - **Test Cases**:
    - Valid project_id "client-a" returns status 200, schema_name "project_client_a"
    - Null project_id returns default workspace (backward compatibility)
  - **Expected**: Tests FAIL (implementation in T011 not done yet)
  - **Dependencies**: None (write tests first)
  - **Traces to**: contracts/mcp-tools.yaml lines 93-174
  - **File**: `tests/contract/test_index_project_id.py` (NEW)

- [ ] **T014 [P]** Contract test: search_code with valid project_id in `tests/contract/test_search_project_id.py`
  - **Description**: Test search_code accepts valid project_id parameter
  - **Test Cases**:
    - Valid project_id "frontend" returns results from that schema only
    - Null project_id uses default workspace
  - **Expected**: Tests FAIL (implementation in T012 not done yet)
  - **Dependencies**: None (write tests first)
  - **Traces to**: contracts/mcp-tools.yaml lines 175-274
  - **File**: `tests/contract/test_search_project_id.py` (NEW)

- [ ] **T015 [P]** Contract test: invalid project_id validation in `tests/contract/test_invalid_project_id.py`
  - **Description**: Test ValidationError for invalid project identifiers
  - **Test Cases**:
    - Uppercase "My_Project" returns 400 ValidationError
    - Leading hyphen "-project" returns 400 ValidationError
    - SQL injection attempt "project'; DROP TABLE--" returns 400 ValidationError
    - 51+ character identifier returns 400 ValidationError
  - **Expected**: Tests FAIL (validation in T001 not integrated yet)
  - **Dependencies**: None (write tests first)
  - **Traces to**: contracts/mcp-tools.yaml lines 50-71, FR-016 (security)
  - **File**: `tests/contract/test_invalid_project_id.py` (NEW)

- [ ] **T016 [P]** Contract test: permission denied error in `tests/contract/test_permission_denied.py`
  - **Description**: Test PermissionError when schema creation fails
  - **Setup**: Mock PostgreSQL to reject CREATE SCHEMA command
  - **Test Case**: New project_id triggers 403 PermissionError with suggested action
  - **Expected**: Tests FAIL (error handling in T006 not done yet)
  - **Dependencies**: None (write tests first)
  - **Traces to**: contracts/mcp-tools.yaml lines 72-91, FR-011
  - **File**: `tests/contract/test_permission_denied.py` (NEW)

## Phase 3.6: Integration Tests (Sequential, from quickstart.md)

Integration tests validate end-to-end user stories. Must run sequentially after all implementations complete.

- [ ] **T017** Integration test: Complete data isolation in `tests/integration/test_data_isolation.py`
  - **Description**: Validate zero cross-project data leakage (Quickstart Scenario 1)
  - **Steps**:
    1. Index repo-a into project_id="client-a"
    2. Index repo-b into project_id="client-b"
    3. Search "authentication" in client-a → only client-a results
    4. Search "authentication" in client-b → only client-b results
    5. Assert file paths disjoint (no overlap)
  - **Expected**: PASS after T011, T012 implementations
  - **Dependencies**: T011, T012 (requires MCP tool updates)
  - **Traces to**: FR-017 (complete isolation), Acceptance Scenario 1
  - **File**: `tests/integration/test_data_isolation.py` (NEW)

- [ ] **T018** Integration test: Project switching in `tests/integration/test_project_switching.py`
  - **Description**: Validate switching between projects returns different results (Quickstart Scenario 2)
  - **Steps**:
    1. Index distinct codebases in project-a and project-b
    2. Search same query in project-a
    3. Switch to project-b with same query
    4. Assert results are completely different
  - **Expected**: PASS after implementations
  - **Dependencies**: T017 (sequential test execution)
  - **Traces to**: FR-002, FR-009, Acceptance Scenario 2
  - **File**: `tests/integration/test_project_switching.py` (NEW)

- [ ] **T019** Integration test: Auto-provisioning in `tests/integration/test_auto_provisioning.py`
  - **Description**: Validate automatic workspace creation on first use (Quickstart Scenario 3)
  - **Steps**:
    1. Verify schema "project_new_project" does NOT exist
    2. Index repository with project_id="new-project"
    3. Verify schema "project_new_project" now exists
    4. Verify registered in project_registry.workspace_config
  - **Expected**: PASS after T006 implementation
  - **Dependencies**: T018 (sequential test execution)
  - **Traces to**: FR-010, Acceptance Scenario 3
  - **File**: `tests/integration/test_auto_provisioning.py` (NEW)

- [ ] **T020** Integration test: Workflow-MCP integration in `tests/integration/test_workflow_integration.py`
  - **Description**: Validate automatic project detection from workflow-mcp (Quickstart Scenario 4)
  - **Setup**: Mock workflow-mcp server returning {"project_id": "active-project"}
  - **Steps**:
    1. Search without specifying project_id (auto-detect)
    2. Verify workflow-mcp was queried
    3. Verify results from "active-project" workspace
  - **Expected**: PASS after T007, T010 implementations
  - **Dependencies**: T019 (sequential test execution)
  - **Traces to**: FR-012, Acceptance Scenario 4
  - **File**: `tests/integration/test_workflow_integration.py` (NEW)

- [ ] **T021** Integration test: Workflow-MCP timeout fallback in `tests/integration/test_workflow_timeout.py`
  - **Description**: Validate fallback to default workspace on timeout (Quickstart Scenario 5)
  - **Setup**: Mock workflow-mcp with httpx.TimeoutException
  - **Steps**:
    1. Search without project_id (triggers timeout)
    2. Verify fallback to default workspace (project_id=None)
    3. Verify results accessible from default workspace
  - **Expected**: PASS after T007 error handling
  - **Dependencies**: T020 (sequential test execution)
  - **Traces to**: FR-013, Acceptance Scenario 5
  - **File**: `tests/integration/test_workflow_timeout.py` (NEW)

- [ ] **T022** Integration test: Invalid identifier rejection in `tests/integration/test_invalid_identifier.py`
  - **Description**: Validate invalid identifiers rejected with clear errors (Quickstart Scenario 6)
  - **Test Cases**: Parameterized test for uppercase, hyphens, SQL injection, 51+ chars
  - **Expected**: ValidationError raised before any database operations
  - **Dependencies**: T021 (sequential test execution)
  - **Traces to**: FR-004, FR-005, FR-006, FR-007, FR-008, Acceptance Scenario 6
  - **File**: `tests/integration/test_invalid_identifier.py` (NEW)

- [ ] **T023** Integration test: Backward compatibility in `tests/integration/test_backward_compatibility.py`
  - **Description**: Validate existing usage without project_id works unchanged (Quickstart Scenario 7)
  - **Steps**:
    1. Index repository WITHOUT project_id parameter (omitted)
    2. Verify uses default workspace (schema_name="project_default")
    3. Search WITHOUT project_id parameter
    4. Verify searches default workspace successfully
  - **Expected**: PASS (backward compatibility preserved)
  - **Dependencies**: T022 (sequential test execution)
  - **Traces to**: FR-018, Acceptance Scenario 7
  - **File**: `tests/integration/test_backward_compatibility.py` (NEW)

## Phase 3.7: Performance Tests (Parallel)

Performance tests validate Constitutional Principle IV guarantees. Independent test files.

- [ ] **T024 [P]** Performance test: Project switching <50ms in `tests/performance/test_switching_latency.py`
  - **Description**: Validate project switching meets <50ms target (Quickstart Scenario 8)
  - **Setup**: Index two projects, use pytest-benchmark
  - **Benchmark**: Switch between projects via search operations
  - **Assertion**: Mean latency < 50ms, max latency < 150ms
  - **Dependencies**: T023 (integration tests complete)
  - **Traces to**: Constitutional Principle IV, Technical Context performance goals
  - **File**: `tests/performance/test_switching_latency.py` (NEW)

- [ ] **T025 [P]** Performance test: Schema creation <100ms in `tests/performance/test_schema_provisioning.py`
  - **Description**: Validate first-time workspace provisioning performance
  - **Benchmark**: Create new project workspace (schema + tables + indexes)
  - **Assertion**: Total provisioning time < 100ms (acceptable one-time cost)
  - **Dependencies**: None (independent performance test)
  - **Traces to**: research.md performance validation
  - **File**: `tests/performance/test_schema_provisioning.py` (NEW)

## Phase 3.8: Security Tests (Parallel)

Security tests validate SQL injection prevention and identifier validation. Independent test files.

- [ ] **T026 [P]** Security test: SQL injection prevention in `tests/security/test_sql_injection.py`
  - **Description**: Validate SQL injection attempts blocked by validation (Quickstart Scenario 9)
  - **Test Cases**: Parameterized test for various injection patterns
    - `"project'; DROP TABLE code_chunks--"`
    - `"project/**/OR/**/1=1--"`
    - `"project\"; DELETE FROM repositories--"`
    - `"project' UNION SELECT * FROM pg_shadow--"`
  - **Assertion**: ValidationError raised, database integrity preserved
  - **Dependencies**: None (independent security test)
  - **Traces to**: FR-016, Acceptance Scenario (Security)
  - **File**: `tests/security/test_sql_injection.py` (NEW)

- [ ] **T027 [P]** Security test: Identifier validation in `tests/security/test_identifier_validation.py`
  - **Description**: Validate comprehensive identifier format checks
  - **Test Cases**:
    - Valid: "client-a", "frontend", "my-project-123"
    - Invalid: uppercase, underscores, spaces, special chars
    - Edge: 50-char max, leading/trailing hyphens, consecutive hyphens
  - **Assertion**: Only valid formats pass, clear error messages for invalid
  - **Dependencies**: None (independent security test)
  - **Traces to**: FR-005, FR-006, FR-007, FR-008
  - **File**: `tests/security/test_identifier_validation.py` (NEW)

## Phase 3.9: Unit Tests (Parallel)

Unit tests for individual components. Independent test files.

- [ ] **T028 [P]** Unit test: ProjectIdentifier validation in `tests/unit/test_project_identifier.py`
  - **Description**: Test Pydantic model validation logic in isolation
  - **Test Cases**: Valid formats, invalid formats, edge cases, error messages
  - **Dependencies**: T001 (model exists)
  - **File**: `tests/unit/test_project_identifier.py` (NEW)

- [ ] **T029 [P]** Unit test: WorkspaceConfig immutability in `tests/unit/test_workspace_config.py`
  - **Description**: Test frozen=True prevents modification
  - **Test Cases**: Attempt to modify fields, verify ValidationError raised
  - **Dependencies**: T002 (model exists)
  - **File**: `tests/unit/test_workspace_config.py` (NEW)

- [ ] **T030 [P]** Unit test: WorkflowIntegrationContext TTL in `tests/unit/test_workflow_context.py`
  - **Description**: Test is_expired() logic with various TTL values
  - **Test Cases**: Fresh cache (not expired), expired cache, edge cases
  - **Dependencies**: T003 (model exists)
  - **File**: `tests/unit/test_workflow_context.py` (NEW)

- [ ] **T031 [P]** Unit test: ProjectWorkspaceManager in `tests/unit/test_workspace_manager.py`
  - **Description**: Test workspace provisioning logic with mocked database
  - **Test Cases**: Schema exists check, schema creation, workspace registration
  - **Dependencies**: T006 (service exists)
  - **File**: `tests/unit/test_workspace_manager.py` (NEW)

- [ ] **T032 [P]** Unit test: WorkflowIntegrationClient in `tests/unit/test_workflow_client.py`
  - **Description**: Test HTTP client with mocked httpx responses
  - **Test Cases**: Success, timeout, connection error, invalid response, caching
  - **Dependencies**: T007 (service exists)
  - **File**: `tests/unit/test_workflow_client.py` (NEW)

- [ ] **T033 [P]** Unit test: resolve_project_id utility in `tests/unit/test_resolve_project_id.py`
  - **Description**: Test project resolution fallback logic
  - **Test Cases**: Explicit ID, workflow-mcp success, workflow-mcp failure, default
  - **Dependencies**: T010 (utility exists)
  - **File**: `tests/unit/test_resolve_project_id.py` (NEW)

## Phase 3.10: Verification & Polish

Final validation tasks. Sequential execution recommended.

- [ ] **T034** Run all contract tests and verify 100% pass
  - **Command**: `pytest tests/contract/ -v`
  - **Assertion**: 4 contract tests pass (T013-T016)
  - **Dependencies**: T011, T012 (implementations complete)
  - **File**: N/A (command execution)

- [ ] **T035** Run all integration tests and verify 100% pass
  - **Command**: `pytest tests/integration/ -v`
  - **Assertion**: 7 integration tests pass (T017-T023)
  - **Dependencies**: T023 (all integration tests written)
  - **File**: N/A (command execution)

- [ ] **T036** Run all performance tests and verify targets met
  - **Command**: `pytest tests/performance/ -v`
  - **Assertion**: Project switching <50ms, schema creation <100ms
  - **Dependencies**: T024, T025 (performance tests exist)
  - **File**: N/A (command execution)

- [ ] **T037** Run all security tests and verify 100% pass
  - **Command**: `pytest tests/security/ -v`
  - **Assertion**: 2 security tests pass (T026-T027)
  - **Dependencies**: T026, T027 (security tests exist)
  - **File**: N/A (command execution)

- [ ] **T038** Run full test suite and verify >95% coverage
  - **Command**: `pytest --cov=src --cov-report=term-missing --cov-fail-under=95`
  - **Assertion**: Coverage ≥95% (Constitutional Principle V)
  - **Dependencies**: T034, T035, T036, T037 (all tests pass)
  - **File**: N/A (command execution)

- [ ] **T039** Run mypy --strict and verify zero errors
  - **Command**: `mypy src/ --strict`
  - **Assertion**: Zero type errors (Constitutional Principle VIII)
  - **Dependencies**: T038 (all implementations complete)
  - **File**: N/A (command execution)

- [ ] **T040** Execute quickstart.md validation scenarios
  - **Command**: `pytest specs/008-multi-project-workspace/quickstart.md --doctest-modules -v`
  - **Assertion**: All 9 quickstart scenarios pass
  - **Dependencies**: T039 (type checking passes)
  - **File**: N/A (command execution)

## Dependencies Graph

```
Foundation (T001-T005a):
T001 → T002 → T006
T003 → T007
T004 → T005 → T005a → T006
T005a → T009a (default schema required for backward compat test)

Service Layer (T006-T008):
T006 → T009
T007 → T010
T008 (parallel)

Database Layer (T009-T010):
T009 → T009a (backward compat test)
T009 → T011, T012
T010 → T012

MCP Tools (T011-T012):
T011, T012 → T013-T016 (contract tests)
T011, T012 → T017 (integration tests)

Tests (T013-T027):
T017 → T018 → T019 → T020 → T021 → T022 → T023 (sequential integration)
T013-T016, T024-T027, T028-T033 (parallel)

Verification (T034-T040):
T034 → T035 → T036 → T037 → T038 → T039 → T040 (sequential)
```

## Parallel Execution Examples

### Example 1: Foundation Models (T001-T003)
```bash
# Launch in parallel (independent Pydantic models)
Task: "Create ProjectIdentifier Pydantic model in src/models/project_identifier.py"
Task: "Create WorkflowIntegrationContext Pydantic model in src/models/workflow_context.py"
```

### Example 2: Service Layer (T006-T008)
```bash
# Launch after foundation complete (T001-T005)
Task: "Implement ProjectWorkspaceManager service in src/services/workspace_manager.py"
Task: "Implement WorkflowIntegrationClient service in src/services/workflow_client.py"
Task: "Add Settings fields for workflow-mcp in src/config/settings.py"
```

### Example 3: Contract Tests (T013-T016)
```bash
# Launch after MCP tool updates (T011-T012)
Task: "Contract test: index_repository with valid project_id in tests/contract/test_index_project_id.py"
Task: "Contract test: search_code with valid project_id in tests/contract/test_search_project_id.py"
Task: "Contract test: invalid project_id validation in tests/contract/test_invalid_project_id.py"
Task: "Contract test: permission denied error in tests/contract/test_permission_denied.py"
```

### Example 4: Performance & Security Tests (T024-T027)
```bash
# Launch after integration tests complete (T023)
Task: "Performance test: Project switching <50ms in tests/performance/test_switching_latency.py"
Task: "Performance test: Schema creation <100ms in tests/performance/test_schema_provisioning.py"
Task: "Security test: SQL injection prevention in tests/security/test_sql_injection.py"
Task: "Security test: Identifier validation in tests/security/test_identifier_validation.py"
```

### Example 5: Unit Tests (T028-T033)
```bash
# Launch in parallel (independent unit tests)
Task: "Unit test: ProjectIdentifier validation in tests/unit/test_project_identifier.py"
Task: "Unit test: WorkspaceConfig immutability in tests/unit/test_workspace_config.py"
Task: "Unit test: WorkflowIntegrationContext TTL in tests/unit/test_workflow_context.py"
Task: "Unit test: ProjectWorkspaceManager in tests/unit/test_workspace_manager.py"
Task: "Unit test: WorkflowIntegrationClient in tests/unit/test_workflow_client.py"
Task: "Unit test: resolve_project_id utility in tests/unit/test_resolve_project_id.py"
```

## Task Execution Notes

### TDD Enforcement
- **Contract tests (T013-T016) MUST fail** before implementing MCP tool updates (T011-T012)
- **Integration tests (T017-T023) written AFTER** implementations but BEFORE verification
- **Test-first mindset**: Write test → see it fail → implement → see it pass

### Parallel Execution Rules
- **[P] marker**: Tasks can run simultaneously (different files, no shared state)
- **No [P] marker**: Tasks must run sequentially (modify same file or have dependencies)
- **Orchestrator validates**: All parallel tasks are truly independent

### File Modification Safety
- **Single file modified by one task**: No [P] marker (e.g., T009, T011, T012 edit shared files sequentially)
- **Different files**: [P] marker safe (e.g., T013-T016 create separate test files)

### Git Micro-Commits (Constitutional Principle X)
- **Commit after each task**: `git commit -m "feat(workspace): implement T001 ProjectIdentifier model"`
- **Conventional Commits**: Use `feat`, `test`, `refactor` types appropriately
- **Atomic commits**: Each commit represents working state (tests pass)

## Validation Checklist

*Checked before considering feature complete*

- [X] All contracts have corresponding tests (T013-T016 cover contracts/mcp-tools.yaml)
- [X] All entities have model tasks (T001-T003 create 3 Pydantic models)
- [X] All tests come before implementation (T013-T016 before T011-T012; T017-T023 validate T011-T012)
- [X] Parallel tasks truly independent (21 [P] tasks verified non-overlapping)
- [X] Each task specifies exact file path (all 42 tasks have File: annotations)
- [X] No task modifies same file as another [P] task (T009-T012 sequential, modify shared files)
- [X] TDD order enforced (contract tests T013-T016, then integration T017-T023)
- [X] Performance targets validated (T024-T025 verify <50ms and <100ms)
- [X] Security coverage complete (T026-T027 validate SQL injection prevention)
- [X] Constitutional compliance validated (T038-T040 verify >95% coverage, mypy --strict, quickstart)

## Coverage Mapping

### Requirements → Tasks Traceability

| Requirement | Tasks | Coverage |
|-------------|-------|----------|
| FR-001 (index project_id) | T011, T013, T017 | ✅ Complete |
| FR-002 (search project_id) | T012, T014, T018 | ✅ Complete |
| FR-003 (default workspace) | T009, T023 | ✅ Complete |
| FR-004 (validation) | T001, T015, T022, T027 | ✅ Complete |
| FR-005 (format enforcement) | T001, T027 | ✅ Complete |
| FR-006 (max length) | T001, T027 | ✅ Complete |
| FR-007 (hyphen rules) | T001, T027 | ✅ Complete |
| FR-008 (consecutive hyphens) | T001, T027 | ✅ Complete |
| FR-009 (isolated workspace) | T002, T006, T017, T019 | ✅ Complete |
| FR-010 (auto-provision) | T006, T019 | ✅ Complete |
| FR-011 (permission check) | T006, T016 | ✅ Complete |
| FR-012 (workflow-mcp query) | T007, T010, T020 | ✅ Complete |
| FR-013 (graceful degradation) | T007, T021 | ✅ Complete |
| FR-014 (failure categorization) | T007, T021 | ✅ Complete |
| FR-015 (caching) | T003, T007, T030, T032 | ✅ Complete |
| FR-016 (security) | T001, T015, T026, T027 | ✅ Complete |
| FR-017 (data isolation) | T017 | ✅ Complete |
| FR-018 (backward compat) | T009, T009a, T023, T005a | ✅ Complete |

### Quickstart Scenarios → Tasks Traceability

| Scenario | Tasks | Coverage |
|----------|-------|----------|
| 1. Complete Data Isolation | T017 | ✅ Complete |
| 2. Project Switching | T018 | ✅ Complete |
| 3. Auto-Provisioning | T019 | ✅ Complete |
| 4. Workflow-MCP Integration | T020 | ✅ Complete |
| 5. Workflow-MCP Timeout | T021 | ✅ Complete |
| 6. Invalid Identifier | T022 | ✅ Complete |
| 7. Backward Compatibility | T023 | ✅ Complete |
| 8. Performance | T024 | ✅ Complete |
| 9. Security | T026 | ✅ Complete |

### Constitutional Principles → Tasks Validation

| Principle | Validation Tasks | Enforcement |
|-----------|------------------|-------------|
| I. Simplicity Over Features | T034-T040 (no scope creep) | Manual review |
| II. Local-First Architecture | T007, T020, T021 (localhost only) | Integration tests |
| III. Protocol Compliance | T013-T016 (MCP contracts) | Contract tests |
| IV. Performance Guarantees | T024, T025 (<50ms, <100ms) | Performance tests |
| V. Production Quality | T038 (95%+ coverage) | pytest-cov |
| VI. Specification-First | T034-T040 (spec → tests → impl) | Manual review |
| VII. Test-Driven Development | T013-T016 before T011-T012 | Task ordering |
| VIII. Pydantic Type Safety | T001-T003, T039 (mypy --strict) | Type checking |
| IX. Orchestrated Subagents | Parallel tasks [P] | Orchestration |
| X. Git Micro-Commit Strategy | Commit per task | Git workflow |
| XI. FastMCP Foundation | T011-T012 (MCP tools) | Integration tests |

## Implementation Ready

All 42 tasks are **immediately executable** with:
- ✅ Clear file paths (NEW or EDIT annotations)
- ✅ Explicit dependencies (blocking relationships documented)
- ✅ Parallel markers ([P] for 21 independent tasks)
- ✅ TDD ordering (tests before implementation)
- ✅ Requirement traceability (FR-001 through FR-018 mapped)
- ✅ Constitutional compliance (all 11 principles validated)
- ✅ Quickstart coverage (all 9 scenarios tested)

**Ready for `/implement` command** ✅
