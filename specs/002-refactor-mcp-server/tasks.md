# Tasks: FastMCP Framework Migration

**Input**: Design documents from `/Users/cliffclarke/Claude_Code/codebase-mcp/specs/002-refactor-mcp-server/`
**Prerequisites**: plan.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

## Execution Context

**Feature**: Migrate MCP server from custom protocol handling to FastMCP framework
**Tech Stack**: Python 3.11+, FastMCP, MCP Python SDK, Pydantic 2.x, SQLAlchemy async, PostgreSQL+pgvector
**Migration Strategy**: Full cutover (all tools refactored before deployment)
**Rollback Method**: Version control reversion (no parallel instances)

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions
- Commit after each completed task

## Phase 3.1: Setup & Dependencies

- [ ] **T001** Install FastMCP and MCP Python SDK dependencies
  - File: `pyproject.toml` or `requirements.txt`
  - Action: Add `fastmcp>=0.1.0` and `mcp>=0.1.0` to dependencies
  - Validation: Run `uv sync` or `pip install -r requirements.txt` successfully
  - Commit: `chore(deps): add FastMCP and MCP Python SDK`

- [ ] **T002** Create FastMCP server instance at `src/mcp/server_fastmcp.py`
  - File: `src/mcp/server_fastmcp.py` (NEW)
  - Action: Initialize FastMCP instance using pattern from `contracts/server_example.py`
  - Include: Server initialization, stdio transport config, import structure
  - Validation: File created with proper imports, mypy --strict passes
  - Commit: `feat(mcp): create FastMCP server instance`

- [ ] **T003** Configure structured logging integration with FastMCP context
  - File: `src/mcp/server_fastmcp.py`
  - Action: Implement dual logging pattern (Context for client + Python logging for `/tmp/codebase-mcp.log`)
  - Reference: research.md section "Context Logging Integration"
  - Validation: Logging configuration present, no stdout/stderr pollution
  - Commit: `feat(mcp): configure dual logging pattern`

- [ ] **T004** Implement startup validation function `validate_server_startup()`
  - File: `src/mcp/server_fastmcp.py`
  - Action: Create validation function checking tool registration, database connectivity, schema validity
  - Reference: research.md section "Decorator Failure Modes"
  - Validation: Function raises clear errors if validation fails
  - Commit: `feat(mcp): add fail-fast startup validation`

## Phase 3.2: Contract Tests (TDD) ⚠️ MUST COMPLETE BEFORE 3.3

**CRITICAL: These tests MUST be written and MUST FAIL before ANY tool migration**

- [ ] **T005 [P]** Contract test: Tool registration validation in `tests/contract/test_tool_registration.py`
  - File: `tests/contract/test_tool_registration.py` (NEW)
  - Action: Verify all 6 tools register correctly with @mcp.tool() decorator
  - Expected: Test fails (tools not yet decorated)
  - Validation: Test exists, fails with clear message, uses pytest async
  - Commit: `test(mcp): add tool registration contract test`

- [ ] **T006 [P]** Contract test: Schema generation validation in `tests/contract/test_schema_generation.py`
  - File: `tests/contract/test_schema_generation.py` (NEW)
  - Action: Validate automatic schemas match expected MCP protocol format
  - Compare: Generated schemas vs `contracts/*.json`
  - Expected: Test fails (tools not yet decorated)
  - Validation: Test exists, fails with clear message
  - Commit: `test(mcp): add schema generation contract test`

- [ ] **T007 [P]** Contract test: Stdio transport compliance in `tests/contract/test_transport_compliance.py`
  - File: `tests/contract/test_transport_compliance.py` (NEW)
  - Action: Confirm stdio transport works with Claude Desktop config pattern
  - Test: Server starts with stdio, accepts JSON-RPC 2.0 requests
  - Expected: Test fails (server not fully configured)
  - Validation: Test exists, fails with clear message
  - Commit: `test(mcp): add stdio transport contract test`

## Phase 3.3: Tool Migration (ONLY after contract tests are failing)

**Prerequisites**: T005-T007 must be failing

- [ ] **T008 [P]** Refactor search_code tool with @mcp.tool() decorator
  - File: `src/mcp/tools/search.py`
  - Action: Add @mcp.tool() decorator, update signature per data-model.md, add Context parameter
  - Reference: `data-model.md` section "1. search_code"
  - Keep: Existing service layer logic (SearcherService) unchanged
  - Validation: Tool registers, contract tests T005-T006 pass for search_code
  - Commit: `refactor(mcp): migrate search_code to FastMCP`

- [ ] **T009 [P]** Refactor index_repository tool with @mcp.tool() decorator
  - File: `src/mcp/tools/indexing.py`
  - Action: Add @mcp.tool() decorator, update signature per data-model.md, add Context parameter for progress reporting
  - Reference: `data-model.md` section "2. index_repository"
  - Keep: Existing IndexerService logic unchanged
  - Validation: Tool registers, contract tests T005-T006 pass for index_repository
  - Commit: `refactor(mcp): migrate index_repository to FastMCP`

- [ ] **T010 [P]** Refactor create_task tool with @mcp.tool() decorator
  - File: `src/mcp/tools/tasks.py`
  - Action: Add @mcp.tool() decorator to create_task function, update signature per data-model.md
  - Reference: `data-model.md` section "3. create_task"
  - Keep: Existing TaskService.create_task logic unchanged
  - Validation: Tool registers, contract tests T005-T006 pass for create_task
  - Commit: `refactor(mcp): migrate create_task to FastMCP`

- [ ] **T011 [P]** Refactor get_task tool with @mcp.tool() decorator
  - File: `src/mcp/tools/tasks.py`
  - Action: Add @mcp.tool() decorator to get_task function, update signature per data-model.md
  - Reference: `data-model.md` section "4. get_task"
  - Keep: Existing TaskService.get_task logic unchanged
  - Validation: Tool registers, contract tests T005-T006 pass for get_task
  - Commit: `refactor(mcp): migrate get_task to FastMCP`

- [ ] **T012 [P]** Refactor list_tasks tool with @mcp.tool() decorator
  - File: `src/mcp/tools/tasks.py`
  - Action: Add @mcp.tool() decorator to list_tasks function, update signature per data-model.md
  - Reference: `data-model.md` section "5. list_tasks"
  - Keep: Existing TaskService.list_tasks logic unchanged
  - Validation: Tool registers, contract tests T005-T006 pass for list_tasks
  - Commit: `refactor(mcp): migrate list_tasks to FastMCP`

- [ ] **T013 [P]** Refactor update_task tool with @mcp.tool() decorator
  - File: `src/mcp/tools/tasks.py`
  - Action: Add @mcp.tool() decorator to update_task function, update signature per data-model.md
  - Reference: `data-model.md` section "6. update_task"
  - Keep: Existing TaskService.update_task logic unchanged
  - Validation: Tool registers, contract tests T005-T006 pass for update_task
  - Commit: `refactor(mcp): migrate update_task to FastMCP`

## Phase 3.4: Integration & Validation

**Prerequisites**: T008-T013 must be complete, all contract tests passing

- [ ] **T014** Run existing protocol compliance tests (must pass unchanged)
  - Command: `pytest tests/integration/test_tool_handlers.py -v`
  - Expected: All tests pass without modification
  - Reference: `quickstart.md` Scenario 3
  - Validation: 100% pass rate, no test file changes
  - Notes: If failures occur, fix FastMCP implementation, not tests

- [ ] **T015** Run existing integration tests (must pass unchanged)
  - Command: `pytest tests/integration/test_embeddings.py -v`
  - Expected: All tests pass without modification
  - Validation: Integration with PostgreSQL, Ollama, pgvector works
  - Notes: Service layer unchanged, should pass as-is

- [ ] **T016** Execute quickstart Scenario 1: Server startup validation
  - Reference: `quickstart.md` Scenario 1
  - Command: `uv run mcp dev src/mcp/server_fastmcp.py`
  - Validation: 6 tools registered, valid schemas logged, no stdout/stderr pollution
  - Success: Server starts cleanly, T004 validation passes
  - Time: 5 minutes

- [ ] **T017** Execute quickstart Scenario 2: Search tool stdio execution
  - Reference: `quickstart.md` Scenario 2
  - Command: Send JSON-RPC 2.0 request via stdin to server_fastmcp.py
  - Validation: Protocol-compliant response, <500ms latency, all fields present
  - Success: search_code returns valid MCP response via stdio
  - Time: 10 minutes

- [ ] **T018** Execute quickstart Scenario 4: Performance benchmark comparison
  - Reference: `quickstart.md` Scenario 4
  - Tools: hyperfine, time command
  - Metrics: Indexing <60s, Search p95 <500ms
  - Validation: <5% performance regression vs v3 server
  - Success: Performance targets maintained
  - Time: 30 minutes
  - Commit: `perf(mcp): validate FastMCP performance benchmarks`

## Phase 3.5: Deployment Preparation

- [ ] **T019** Update Claude Desktop config to use server_fastmcp.py
  - File: `~/Library/Application Support/Claude/claude_desktop_config.json`
  - Action: Change server path from `mcp_stdio_server_v3.py` to `server_fastmcp.py`
  - Validation: Claude Desktop connects successfully, all 6 tools available
  - Reference: `quickstart.md` Scenario 1
  - Commit: `chore(config): update Claude Desktop to FastMCP server`

- [ ] **T020 [P]** Update README.md with FastMCP server instructions
  - File: `README.md`
  - Action: Replace MCP SDK references with FastMCP framework, update setup instructions
  - Include: New dependencies (fastmcp, mcp), server startup command, migration notes
  - Validation: Documentation accurate, setup instructions work for new users
  - Commit: `docs(readme): update with FastMCP migration`

- [ ] **T021 [P]** Document rollback procedure in `docs/ROLLBACK.md`
  - File: `docs/ROLLBACK.md` (NEW)
  - Action: Create rollback guide per `quickstart.md` Scenario 5
  - Include: Git checkout steps, Claude Desktop config reversion, validation commands
  - Validation: Procedure complete, testable, <5 minute rollback time
  - Reference: `quickstart.md` Scenario 5
  - Commit: `docs(rollback): add FastMCP rollback procedure`

## Phase 3.6: Final Validation & Polish

- [ ] **T022** Execute complete quickstart validation suite
  - Reference: `quickstart.md` all scenarios (1-5)
  - Time: 70 minutes total
  - Validation: All 5 scenarios pass success criteria
  - Success: Migration sign-off checklist complete
  - Notes: This is the final gate before deployment

- [ ] **T023** Verify mypy --strict compliance across all modified files
  - Command: `mypy src/mcp/server_fastmcp.py src/mcp/tools/ --strict`
  - Validation: Zero type errors, all type hints complete
  - Files: server_fastmcp.py, tools/search.py, tools/indexing.py, tools/tasks.py
  - Commit: `chore(types): verify mypy --strict compliance`

- [ ] **T024** Remove or archive legacy server files (post-validation)
  - Files: `src/mcp/mcp_stdio_server_v3.py`, `src/mcp/server.py`
  - Action: Keep for rollback capability (git history), add deprecation comments
  - Alternative: Move to `src/mcp/legacy/` directory
  - Validation: Legacy files documented as deprecated, not deleted
  - Commit: `chore(mcp): deprecate legacy server files`

## Dependencies

**Phase Order**:
1. Setup (T001-T004) before Tests
2. Tests (T005-T007) before Tool Migration
3. Tool Migration (T008-T013) before Integration
4. Integration (T014-T018) before Deployment
5. Deployment (T019-T021) before Final Validation
6. Final Validation (T022-T024) before production

**Critical Path**:
- T001 → T002 → T003 → T004
- T004 → T005-T007 (parallel)
- T005-T007 → T008-T013 (parallel)
- T008-T013 → T014-T018 (sequential)
- T014-T018 → T019-T021 (parallel)
- T019-T021 → T022-T024 (sequential)

**Blocking Dependencies**:
- Tests (T005-T007) MUST fail before tool migrations (T008-T013)
- All tool migrations (T008-T013) MUST complete before integration tests (T014-T015)
- Performance benchmarks (T018) MUST pass before deployment (T019)
- Complete quickstart (T022) MUST pass before production deployment

## Parallel Execution Examples

### Example 1: Contract Tests (T005-T007)
```bash
# Launch all contract tests in parallel (different test files)
Task: "Write contract test for tool registration in tests/contract/test_tool_registration.py - verify all 6 tools register with @mcp.tool() decorator"
Task: "Write contract test for schema generation in tests/contract/test_schema_generation.py - validate auto-generated schemas match contracts/*.json"
Task: "Write contract test for stdio transport in tests/contract/test_transport_compliance.py - confirm JSON-RPC 2.0 over stdio works"
```

### Example 2: Tool Migrations (T008-T013)
```bash
# Launch all tool migrations in parallel (different tool files or independent functions)
Task: "Refactor search_code in src/mcp/tools/search.py - add @mcp.tool() decorator per data-model.md"
Task: "Refactor index_repository in src/mcp/tools/indexing.py - add @mcp.tool() decorator per data-model.md"
Task: "Refactor create_task in src/mcp/tools/tasks.py - add @mcp.tool() decorator per data-model.md"
Task: "Refactor get_task in src/mcp/tools/tasks.py - add @mcp.tool() decorator per data-model.md"
Task: "Refactor list_tasks in src/mcp/tools/tasks.py - add @mcp.tool() decorator per data-model.md"
Task: "Refactor update_task in src/mcp/tools/tasks.py - add @mcp.tool() decorator per data-model.md"
```

### Example 3: Documentation (T020-T021)
```bash
# Launch documentation tasks in parallel (different files)
Task: "Update README.md with FastMCP setup instructions - replace MCP SDK references with FastMCP framework"
Task: "Create docs/ROLLBACK.md with rollback procedure - document git checkout and Claude Desktop config reversion"
```

## Task Execution Notes

**TDD Discipline**:
- Contract tests T005-T007 MUST be written first and MUST fail
- Do not proceed to T008-T013 until tests are failing
- Each tool migration should make corresponding contract tests pass

**Git Micro-Commits**:
- Commit after each completed task (T001, T002, T003, etc.)
- Use Conventional Commits format: `type(scope): description`
- Each commit MUST pass mypy --strict and represent a working state

**Rollback Safety**:
- Legacy server files (mcp_stdio_server_v3.py, server.py) MUST NOT be deleted
- Keep in codebase for version control rollback (Principle X, clarification Q5)
- Add deprecation comments but do not remove until production validation complete

**Performance Validation**:
- T018 is critical gate - must maintain 60s/500ms targets
- If regression >5%, refactor FastMCP implementation before proceeding
- Service layer logic unchanged - performance should be equivalent

**Constitutional Compliance Checkpoints**:
- T004: Principle V (fail-fast startup validation)
- T005-T007: Principle VII (TDD - tests before implementation)
- T008-T013: Principle XI (FastMCP decorator patterns)
- T014-T018: Principle IV (performance guarantees)
- T022: All principles validated via quickstart scenarios

## Success Criteria

Migration is complete when:
- ✅ All 24 tasks completed and committed
- ✅ All contract tests passing (T005-T007)
- ✅ All 6 tools migrated to FastMCP (T008-T013)
- ✅ Existing test suite passes unchanged (T014-T015)
- ✅ Performance benchmarks maintained (T018)
- ✅ Complete quickstart validation passed (T022)
- ✅ mypy --strict compliance verified (T023)
- ✅ Claude Desktop integration working (T019)
- ✅ Rollback procedure documented and tested (T021)

**Total Estimated Time**: ~8-10 hours (with parallel execution)

**Ready for Production**: After T022 complete, all quickstart scenarios passing, and migration sign-off checklist approved.

---

*Generated from plan.md Phase 2 task strategy | Constitution v2.2.0 compliant*
