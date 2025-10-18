# Bug 1: Foreground Indexing Returns No Output - Task List

**Input**: `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/bugs/mcp-indexing-failures/bug1-foreground-hang-plan.md`
**Bug Type**: Missing return statement (unreachable code)
**Root Cause**: Response formatting code (lines 330-376) placed after try/except block, never executes
**Fix Strategy**: Option A - Move response formatting inside try block (minimal reorganization)

## Prerequisites

**CRITICAL**: Bug 3 must be fixed first to ensure proper error status handling infrastructure is in place.

## Execution Flow

```
1. Load bug1-foreground-hang-plan.md
   → ✅ Root cause: Response formatting code unreachable (after try/except)
   → ✅ Fix: Move lines 330-376 inside try block (after async with, before exceptions)
2. Verify dependencies:
   → Bug 3 status handling tests must exist
   → Test infrastructure for MCP tool responses must be available
3. Generate tasks by category:
   → Setup: Test fixtures and utilities
   → Tests: Response contract tests, error handling tests (TDD)
   → Core: Move response formatting code (minimal change)
   → Verification: Integration tests, manual testing
4. Apply task rules:
   → Test writing tasks = [P] (different test files)
   → Code move operation = sequential (single file)
   → Verification = sequential (depends on implementation)
5. Number tasks sequentially (T001, T002...)
6. Validate constitutional compliance:
   → Principle I: Simplicity (minimal change, no new complexity)
   → Principle III: Protocol Compliance (MCP tools MUST return values)
   → Principle V: Production Quality (fix critical return value bug)
   → Principle VIII: Type Safety (matches declared return type)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths and line numbers from plan

## Phase 1: Preparation & Test Infrastructure

- [ ] **T001** Verify Bug 3 completion and dependency readiness
  - Check that Bug 3 tasks are complete (error status handling infrastructure)
  - Verify `tests/unit/services/test_indexer_error_paths.py` exists and passes
  - Verify test fixtures for repository creation exist
  - Exit with summary: "✅ Dependencies ready" or "❌ Bug 3 must be completed first"
  - **Micro-commit point**: None (verification only)
  - **Estimate**: 5 minutes

- [ ] **T002** Create test repository fixture generator
  - File: `tests/fixtures/test_repository_generator.py`
  - Function: `create_test_repository(tmp_path: Path, num_files: int = 10) -> Path`
  - Generate realistic test repositories with:
    - Python files with actual code (not empty)
    - Nested directory structure
    - Valid file extensions (.py, .js, .md)
    - Configurable file count (default: 10 for fast tests)
  - Return absolute path to created repository
  - Required for T003-T008 test execution
  - **Micro-commit point**: After fixture creation and self-test
  - **Commit message**: `test(fixtures): add test repository generator for indexing tests`
  - **Estimate**: 20 minutes

## Phase 2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE PHASE 3

**CRITICAL: These tests MUST be written and MUST FAIL before implementation**

- [ ] **T003 [P]** Response contract test - success case
  - File: `tests/unit/mcp_tools/test_indexing_tool_contract.py`
  - Class: `TestIndexRepositoryContract`
  - Test: `test_successful_indexing_returns_complete_response()`
  - **Before fix**: Test FAILS with assertion error (result is None)
  - **After fix**: Test PASSES
  - Assertions:
    ```python
    assert result is not None, "index_repository must return a value"
    assert isinstance(result, dict), "Result must be a dictionary"
    assert set(result.keys()) >= {
        "repository_id", "files_indexed", "chunks_created",
        "duration_seconds", "project_id", "database_name", "status"
    }, "Response must include all required fields"
    assert result["status"] in ["success", "partial", "failed"]
    assert isinstance(result["files_indexed"], int)
    assert isinstance(result["chunks_created"], int)
    assert isinstance(result["duration_seconds"], float)
    assert isinstance(result["repository_id"], str)
    assert len(result["repository_id"]) == 36  # UUID format
    ```
  - Use mock for `index_repository_service` to return controlled `IndexResult`
  - **Micro-commit point**: After test creation (will fail)
  - **Commit message**: `test(mcp): add response contract test for foreground indexing (fails before fix)`
  - **Estimate**: 25 minutes

- [ ] **T004 [P]** Response contract test - partial success with errors
  - File: `tests/unit/mcp_tools/test_indexing_tool_contract.py` (same file as T003)
  - Class: `TestIndexRepositoryContract`
  - Test: `test_partial_indexing_includes_errors_array()`
  - **Before fix**: Test FAILS (result is None)
  - **After fix**: Test PASSES
  - Mock `IndexResult` with `status="partial"` and `errors=["file1.py: parse error", "file2.js: encoding error"]`
  - Assertions:
    ```python
    assert result is not None
    assert result["status"] == "partial"
    assert "errors" in result, "Partial results must include errors array"
    assert isinstance(result["errors"], list)
    assert len(result["errors"]) == 2
    assert all(isinstance(e, str) for e in result["errors"])
    ```
  - **Micro-commit point**: After test creation (will fail)
  - **Commit message**: `test(mcp): add error array contract test for partial indexing (fails before fix)`
  - **Estimate**: 15 minutes

- [ ] **T005 [P]** Response contract test - type validation
  - File: `tests/unit/mcp_tools/test_indexing_tool_contract.py`
  - Class: `TestIndexRepositoryContract`
  - Test: `test_response_types_match_contract()`
  - **Before fix**: Test FAILS (result is None)
  - **After fix**: Test PASSES
  - Validate exact types for all fields:
    ```python
    assert isinstance(result["repository_id"], str)
    assert isinstance(result["files_indexed"], int)
    assert isinstance(result["chunks_created"], int)
    assert isinstance(result["duration_seconds"], (int, float))
    assert isinstance(result["project_id"], str)
    assert isinstance(result["database_name"], str)
    assert isinstance(result["status"], str)
    if "errors" in result:
        assert isinstance(result["errors"], list)
    ```
  - **Micro-commit point**: After test creation (will fail)
  - **Commit message**: `test(mcp): add type validation contract test for indexing response (fails before fix)`
  - **Estimate**: 15 minutes

- [ ] **T006 [P]** Exception handling preservation test
  - File: `tests/unit/mcp_tools/test_indexing_tool_errors.py`
  - Class: `TestIndexRepositoryExceptions`
  - Tests:
    1. `test_pool_timeout_raises_mcp_error()`
    2. `test_connection_validation_raises_mcp_error()`
    3. `test_pool_closed_raises_runtime_error()`
    4. `test_invalid_path_raises_value_error()`
  - **Goal**: Ensure exception handlers still work after code move
  - Mock `get_session()` to raise each exception type
  - Verify correct exception types and messages
  - **Micro-commit point**: After test creation (should PASS even before fix)
  - **Commit message**: `test(mcp): add exception handling preservation tests for indexing tool`
  - **Estimate**: 30 minutes

- [ ] **T007 [P]** Variable scope validation test
  - File: `tests/unit/mcp_tools/test_indexing_tool_internals.py`
  - Class: `TestIndexRepositoryInternals`
  - Test: `test_result_variable_accessible_after_async_with()`
  - **Goal**: Verify `result` variable remains in scope after `async with` block
  - Use real `get_session()` with test database
  - Create small test repository (3 files)
  - Execute full indexing flow
  - Assert result is returned and contains expected data
  - **Before fix**: Test FAILS (result is None)
  - **After fix**: Test PASSES
  - **Micro-commit point**: After test creation (will fail)
  - **Commit message**: `test(mcp): add variable scope test for result accessibility (fails before fix)`
  - **Estimate**: 20 minutes

- [ ] **T008 [P]** Performance warning logging test
  - File: `tests/unit/mcp_tools/test_indexing_tool_logging.py`
  - Class: `TestIndexRepositoryLogging`
  - Tests:
    1. `test_success_logging_emitted()`
    2. `test_performance_warning_emitted_when_slow()`
    3. `test_no_performance_warning_when_fast()`
  - Use `caplog` fixture to capture logger output
  - Mock `IndexResult` with controlled duration values:
    - Fast: 1000 files in 3s (target: 6s, no warning)
    - Slow: 1000 files in 15s (target: 6s, warning expected)
  - **Before fix**: Tests may pass/fail depending on execution path
  - **After fix**: All tests PASS consistently
  - **Micro-commit point**: After test creation
  - **Commit message**: `test(mcp): add logging behavior tests for indexing tool`
  - **Estimate**: 25 minutes

## Phase 3: Core Implementation (ONLY after Phase 2 tests are failing)

- [ ] **T009** Move response formatting inside try block
  - File: `/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/tools/indexing.py`
  - **Changes**:
    1. Cut lines 330-376 (response formatting code)
    2. Paste after line 194 (immediately after `async with get_session()` block completes)
    3. Indent to match try block scope (8 spaces)
    4. Verify `return response` is last statement before exception handlers (line 195+)
  - **Exact line mapping**:
    - **BEFORE**: Lines 330-376 (after all exception handlers)
    - **AFTER**: Lines 195-241 (inside try block, before exception handlers)
    - Exception handlers shift from lines 195-328 to lines 242-375
  - **NO logic changes**: Pure code movement, preserve all formatting/comments
  - **Validation**: Run mypy to verify type safety maintained
  - **Micro-commit point**: After code move and mypy validation
  - **Commit message**: `fix(mcp): move response formatting inside try block to fix unreachable code

BREAKING: Foreground indexing now returns JSON response as specified in MCP contract

The response formatting code (lines 330-376) was unreachable because it was
placed after the try/except block. When the happy path completed, Python
skipped all exception handlers (no exception occurred) and implicitly returned
None at the function end.

This commit moves the response formatting code inside the try block, immediately
after the async with get_session() block completes. The result variable remains
in scope, and the return statement now executes before exception handlers.

Changes:
- Move lines 330-376 to lines 195-241 (inside try block)
- No logic changes (pure code reorganization)
- Exception handlers shift down but remain unchanged

Fixes: Bug 1 (Foreground Indexing Returns No Output)
Refs: docs/bugs/mcp-indexing-failures/bug1-foreground-hang-plan.md`
  - **Estimate**: 15 minutes

## Phase 4: Verification & Integration

- [ ] **T010** Run unit tests and verify all pass
  - Execute: `pytest tests/unit/mcp_tools/test_indexing_tool_contract.py -v`
  - Execute: `pytest tests/unit/mcp_tools/test_indexing_tool_errors.py -v`
  - Execute: `pytest tests/unit/mcp_tools/test_indexing_tool_internals.py -v`
  - Execute: `pytest tests/unit/mcp_tools/test_indexing_tool_logging.py -v`
  - **Expected**: All 10+ tests PASS (T003-T008 tests now pass after fix)
  - **If failures**: Debug and fix before proceeding
  - **Micro-commit point**: None (verification only)
  - **Estimate**: 10 minutes

- [ ] **T011** Integration test with real repository
  - File: `tests/integration/test_foreground_indexing_e2e.py`
  - Class: `TestForegroundIndexingE2E`
  - Test: `test_small_repository_returns_complete_response()`
  - Use `create_test_repository()` fixture from T002 (10 files)
  - Call `index_repository()` with real database session
  - Assertions:
    ```python
    assert result is not None
    assert result["files_indexed"] == 10
    assert result["chunks_created"] > 0
    assert result["status"] == "success"
    assert result["duration_seconds"] > 0
    assert "repository_id" in result
    # Verify repository actually indexed in database
    async with get_session() as db:
        repo = await db.get(Repository, UUID(result["repository_id"]))
        assert repo is not None
        assert repo.name == "test-repo"
    ```
  - **Micro-commit point**: After test creation and passing
  - **Commit message**: `test(integration): add end-to-end test for foreground indexing response`
  - **Estimate**: 25 minutes

- [ ] **T012** Integration test with force_reindex
  - File: `tests/integration/test_foreground_indexing_e2e.py` (same as T011)
  - Test: `test_force_reindex_returns_updated_response()`
  - Index same repository twice with `force_reindex=True`
  - Verify:
    - First indexing: `repository_id` returned
    - Second indexing: Same `repository_id` returned
    - Both responses have same structure
    - Database has only one repository record (not duplicate)
  - **Micro-commit point**: After test creation and passing
  - **Commit message**: `test(integration): add force reindex test for idempotency verification`
  - **Estimate**: 20 minutes

- [ ] **T013** Compare foreground vs background indexing responses
  - File: `tests/integration/test_indexing_consistency.py`
  - Test: `test_foreground_background_response_consistency()`
  - Index same repository using both methods:
    1. Foreground: `index_repository()`
    2. Background: `start_indexing_background()` + poll `get_indexing_status()`
  - Compare response structures:
    ```python
    # Both should have these fields
    common_fields = {"repository_id", "files_indexed", "chunks_created", "status"}
    assert set(fg_result.keys()) >= common_fields
    assert set(bg_result.keys()) >= common_fields
    # Values should match (same repository)
    assert fg_result["files_indexed"] == bg_result["files_indexed"]
    assert fg_result["chunks_created"] == bg_result["chunks_created"]
    ```
  - **Micro-commit point**: After test creation and passing
  - **Commit message**: `test(integration): verify foreground/background indexing response consistency`
  - **Estimate**: 30 minutes

## Phase 5: Manual Testing & Documentation

- [ ] **T014** Manual MCP client testing
  - **Prerequisites**: Start codebase-mcp server: `uv run python -m src.mcp.server_fastmcp`
  - **Test 1**: Call `mcp__codebase-mcp__index_repository` via Claude Code
    - Repo: Small test repository (10 files)
    - **Before fix**: `<system>Tool ran without output or errors</system>`
    - **After fix**: JSON response with all fields
  - **Test 2**: Call with `force_reindex=True`
    - Verify response structure identical
  - **Test 3**: Call with large repository (100 files)
    - Verify response includes `files_indexed=100`
    - Verify `duration_seconds` is reasonable
  - Document results in `docs/bugs/mcp-indexing-failures/bug1-verification.md`
  - **Micro-commit point**: None (manual testing only)
  - **Estimate**: 20 minutes

- [ ] **T015** Update bug documentation with fix results
  - File: `docs/bugs/mcp-indexing-failures/bug1-foreground-hang-plan.md`
  - Add section at end: `## Fix Verification Results`
  - Include:
    - Test results summary (T010-T013)
    - Manual testing results (T014)
    - Performance impact: None (pure code reorganization)
    - Breaking changes: None (only fixes broken behavior)
    - Screenshot/example of successful response
  - **Micro-commit point**: After documentation update
  - **Commit message**: `docs(bugs): add verification results for Bug 1 fix`
  - **Estimate**: 15 minutes

- [ ] **T016** Search for similar patterns in codebase
  - Execute: `rg -A 10 'return response' src/mcp/tools/ | rg -B 15 'except.*Error'`
  - **Goal**: Find other tools with response formatting after try/except blocks
  - Check each MCP tool file:
    - `src/mcp/tools/background_indexing.py` (reference implementation, should be correct)
    - `src/mcp/tools/search.py`
    - Any other `@mcp.tool()` decorated functions
  - Document findings in `docs/bugs/mcp-indexing-failures/similar-patterns-audit.md`
  - **If similar patterns found**: Create follow-up bug reports
  - **Micro-commit point**: After audit documentation
  - **Commit message**: `docs(bugs): add audit results for similar return statement patterns`
  - **Estimate**: 25 minutes

## Phase 6: Polish & Final Validation

- [ ] **T017** Run full test suite and verify no regressions
  - Execute: `pytest tests/ -v --tb=short`
  - **Expected**: All tests pass (existing + new tests from T003-T013)
  - Check coverage for `src/mcp/tools/indexing.py`:
    - Execute: `pytest tests/unit/mcp_tools/ --cov=src.mcp.tools.indexing --cov-report=term-missing`
    - **Target**: >90% coverage (response formatting path now covered)
  - **Micro-commit point**: None (verification only)
  - **Estimate**: 15 minutes

- [ ] **T018** Run mypy strict type checking
  - Execute: `mypy src/mcp/tools/indexing.py --strict`
  - **Expected**: No type errors (return type `dict[str, Any]` now satisfied)
  - Verify function signature matches implementation:
    ```python
    async def index_repository(...) -> dict[str, Any]:
        ...
        return response  # ✅ Now reachable
    ```
  - **Micro-commit point**: None (verification only)
  - **Estimate**: 5 minutes

- [ ] **T019** Update MCP tool contract documentation
  - File: Create `docs/mcp/tool-return-value-patterns.md`
  - Document correct pattern for MCP tools:
    ```python
    @mcp.tool()
    async def example_tool(...) -> dict[str, Any]:
        try:
            # Perform work
            result = await do_work()

            # ✅ Format response INSIDE try block
            response = {
                "field1": result.value1,
                "field2": result.value2,
            }

            # ✅ Return BEFORE exception handlers
            return response

        except SpecificError as e:
            # Handle error, raise MCPError
            raise MCPError(...)
    ```
  - **Anti-pattern** (Bug 1):
    ```python
    try:
        result = await do_work()
        # ❌ Missing return here
    except SpecificError as e:
        raise MCPError(...)

    # ❌ UNREACHABLE CODE (after try/except)
    response = {"field": result.value}
    return response
    ```
  - **Micro-commit point**: After documentation creation
  - **Commit message**: `docs(mcp): add tool return value patterns guide with anti-patterns`
  - **Estimate**: 20 minutes

- [ ] **T020** Create regression test for this bug class
  - File: `tests/unit/mcp_tools/test_tool_contract_compliance.py`
  - Class: `TestMCPToolContractCompliance`
  - Test: `test_all_tools_return_values()`
  - **Goal**: Prevent future bugs of this type
  - Use reflection to find all `@mcp.tool()` decorated functions
  - For each tool:
    1. Verify return type annotation exists
    2. Verify return type is `dict[str, Any]` or similar
    3. Call with minimal valid arguments (mocked)
    4. Assert result is not None
  - **Micro-commit point**: After test creation
  - **Commit message**: `test(mcp): add contract compliance test for all MCP tools return values`
  - **Estimate**: 35 minutes

## Summary

**Total Tasks**: 20 tasks
- **Phase 1** (Preparation): 2 tasks
- **Phase 2** (Tests - TDD): 6 tasks [P] (can run in parallel)
- **Phase 3** (Implementation): 1 task (sequential)
- **Phase 4** (Verification): 4 tasks (sequential)
- **Phase 5** (Manual Testing): 3 tasks
- **Phase 6** (Polish): 4 tasks

**Parallelization Opportunities**:
- T003-T008: All test writing tasks (6 tasks in parallel)

**Micro-commit Points**: 15 commits total
1. T002: Test fixture creation
2. T003: Response contract test (fails)
3. T004: Error array contract test (fails)
4. T005: Type validation test (fails)
5. T006: Exception handling tests (pass)
6. T007: Variable scope test (fails)
7. T008: Logging tests
8. T009: **THE FIX** - Move response formatting
9. T011: E2E integration test
10. T012: Force reindex test
11. T013: Consistency test
12. T015: Documentation update
13. T016: Audit documentation
14. T019: Pattern documentation
15. T020: Regression test

**Total Estimated Time**: 6.0 hours
- Setup: 0.5 hours (T001-T002)
- TDD tests: 2.5 hours (T003-T008)
- Implementation: 0.25 hours (T009) ⚡ **CRITICAL FIX**
- Verification: 1.5 hours (T010-T013)
- Manual testing: 1.0 hour (T014-T016)
- Polish: 1.25 hours (T017-T020)

**Risk Assessment**: LOW
- Pure code reorganization (no logic changes)
- Comprehensive test coverage before and after fix
- No API changes or breaking changes to external contract
- Exception handling preserved (verified by T006)
- Type safety maintained (verified by T018)

**Constitutional Compliance**:
- ✅ Principle I: Simplicity (minimal change, no new complexity)
- ✅ Principle III: Protocol Compliance (MCP tools MUST return values)
- ✅ Principle IV: Performance (no performance impact)
- ✅ Principle V: Production Quality (fix critical return value bug)
- ✅ Principle VII: Test-Driven Development (tests before implementation)
- ✅ Principle VIII: Type Safety (matches declared return type)
- ✅ Principle X: Git Micro-Commit Strategy (15 atomic commits)

**Success Criteria**:
1. ✅ All T003-T008 tests PASS after T009 fix
2. ✅ No existing tests break (T017)
3. ✅ mypy --strict passes (T018)
4. ✅ Manual MCP client returns JSON response (T014)
5. ✅ No similar patterns found in other tools (T016)
6. ✅ Documentation updated with patterns guide (T019)
7. ✅ Regression test prevents future bugs (T020)
