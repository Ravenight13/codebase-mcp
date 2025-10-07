# Implementation Plan: FastMCP Framework Migration

**Branch**: `002-refactor-mcp-server` | **Date**: 2025-10-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/Users/cliffclarke/Claude_Code/codebase-mcp/specs/002-refactor-mcp-server/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path ✅
2. Fill Technical Context ✅
3. Fill Constitution Check ✅
4. Evaluate Constitution Check → Initial Constitution Check PASS ✅
5. Execute Phase 0 → research.md ✅
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, CLAUDE.md ✅
7. Re-evaluate Constitution Check → Post-Design Constitution Check ✅
8. Plan Phase 2 → Describe task generation approach ✅
9. STOP - Ready for /tasks command ✅
```

## Summary

Migrate the existing MCP server from custom protocol handling to FastMCP framework with official Python SDK. This refactoring maintains 100% backward compatibility while reducing implementation complexity through framework abstractions. All 6 existing MCP tools (search_code, index_repository, create_task, get_task, list_tasks, update_task) will be converted to use FastMCP's @mcp.tool() decorator pattern with automatic schema generation from type hints. The migration uses a full cutover deployment strategy with rollback capability via version control.

## Technical Context

**Language/Version**: Python 3.11+ (3.13 compatible, as currently deployed)
**Primary Dependencies**: FastMCP framework, MCP Python SDK, Pydantic 2.x, SQLAlchemy 2.0 (async), AsyncPG
**Storage**: PostgreSQL 14+ with pgvector extension (unchanged from current implementation)
**Testing**: pytest with async support, protocol compliance validation, performance benchmarks
**Target Platform**: Local development (macOS/Linux), Claude Desktop integration via stdio transport
**Project Type**: Single project (Python MCP server with CLI/stdio interface)
**Performance Goals**: Maintain existing targets - 60s indexing for 10k LOC, 500ms p95 search latency
**Constraints**: Zero protocol violations, no stdout/stderr pollution, mypy --strict compliance, full test suite pass
**Scale/Scope**: 6 MCP tools, ~2000 LOC server implementation, existing PostgreSQL schema (11 tables)

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Principle Alignment:**

✅ **I. Simplicity Over Features**: Migration reduces complexity by eliminating custom protocol handling (~400 LOC) in favor of FastMCP abstractions. Single responsibility maintained - semantic search only.

✅ **II. Local-First Architecture**: No change to local-first design. FastMCP runs locally, no cloud dependencies introduced.

✅ **III. Protocol Compliance (MCP via SSE)**: FastMCP enforces protocol compliance through framework-level validation. Transport abstraction handles stdio/SSE correctly. Logging to `/tmp/codebase-mcp.log` preserved via FastMCP context integration.

✅ **IV. Performance Guarantees**: FastMCP adds negligible overhead (<5ms per request based on framework benchmarks). Async operations fully supported. Performance targets maintained through existing service layer (unchanged).

✅ **V. Production Quality Standards**: FastMCP's fail-fast startup validation improves error handling. Type hints drive automatic schema generation. Pydantic validation at boundaries enforced by framework.

✅ **VI. Specification-First Development**: This migration follows spec → plan → tasks workflow. Specification completed with clarifications before planning.

✅ **VII. Test-Driven Development**: Existing test suite (protocol compliance, integration, performance) must pass unchanged. FastMCP decorator tests will be written before migration (Phase 1).

✅ **VIII. Pydantic-Based Type Safety**: FastMCP relies on Pydantic models for schema generation. Existing Pydantic models reused with minimal adaptation. mypy --strict compliance maintained.

✅ **IX. Orchestrated Subagent Execution**: Implementation phase will use parallel subagents for independent tool migrations (6 tools can be refactored concurrently).

✅ **X. Git Micro-Commit Strategy**: Each tool migration = atomic commit. Full cutover deployment on feature branch `002-refactor-mcp-server`.

✅ **XI. FastMCP and Python SDK Foundation** (**NEW CONSTITUTIONAL REQUIREMENT**): This migration directly implements Principle XI by adopting FastMCP as mandated. Uses @mcp.tool() decorators, automatic schema generation, context injection, and transport abstraction as required.

**Gate Result**: ✅ PASS - All constitutional principles aligned. No violations. Migration directly fulfills newly added Principle XI.

## Post-Design Constitution Check
*Re-evaluation after Phase 1 design artifacts completed*

**Design Review:**

✅ **Principle III (Protocol Compliance)**:
- Design confirms stdio transport via `mcp.run()` (no explicit config needed)
- Dual logging pattern documented: Context for client + Python logging for `/tmp/codebase-mcp.log`
- No stdout/stderr pollution confirmed in server_example.py

✅ **Principle V (Production Quality)**:
- Fail-fast validation implemented in server_example.py (`validate_server_startup()`)
- Comprehensive error handling documented in data-model.md
- Type hints complete throughout all tool signatures

✅ **Principle VII (Test-Driven Development)**:
- Contract tests designed before implementation (test_tool_registration.py, test_schema_generation.py, test_transport_compliance.py)
- Quickstart.md includes integration test validation (Scenario 3)
- Performance benchmarks defined (Scenario 4)

✅ **Principle VIII (Pydantic-Based Type Safety)**:
- All existing Pydantic models confirmed compatible (research.md findings)
- No model changes needed
- mypy --strict compliance maintained via complete type hints

✅ **Principle XI (FastMCP and Python SDK Foundation)**:
- All 6 tools use @mcp.tool() decorator pattern (data-model.md)
- Automatic schema generation from type hints (contracts/*.json)
- Context injection for logging and progress (documented throughout)
- Transport abstraction via FastMCP's mcp.run()

**New Findings from Design Phase:**
- Simplified architecture: SSE complexity removed, stdio is default
- Pydantic model compatibility: Zero code changes needed (better than expected)
- Dual logging pattern: Clear separation between client and file logging
- Fail-fast validation: Custom implementation needed (FastMCP limitation identified)

**Gate Result**: ✅ PASS - Design maintains constitutional compliance. No new violations introduced. Implementation simplifies architecture while maintaining all quality standards.

## Project Structure

### Documentation (this feature)
```
specs/002-refactor-mcp-server/
├── spec.md              # Feature specification (WHAT/WHY)
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output - FastMCP integration research
├── data-model.md        # Phase 1 output - Tool handler signatures
├── quickstart.md        # Phase 1 output - Migration validation scenarios
└── contracts/           # Phase 1 output - FastMCP tool schemas
    ├── search_tool.json
    ├── indexing_tool.json
    ├── task_tools.json
    └── server_example.py    # FastMCP server contract example
```

### Source Code (repository root)
```
src/
├── mcp/
│   ├── server_fastmcp.py        # NEW: FastMCP server instance
│   ├── tools/
│   │   ├── search.py            # REFACTOR: Add @mcp.tool() decorator
│   │   ├── indexing.py          # REFACTOR: Add @mcp.tool() decorator
│   │   └── tasks.py             # REFACTOR: Add @mcp.tool() decorator
│   ├── mcp_stdio_server_v3.py   # LEGACY: Keep for rollback
│   └── server.py                # LEGACY: Keep for rollback
├── models/                       # UNCHANGED: Pydantic models
├── services/                     # UNCHANGED: Business logic
├── config/                       # UNCHANGED: Settings
└── database.py                   # UNCHANGED: PostgreSQL connection

tests/
├── contract/                     # NEW: FastMCP decorator tests
│   ├── test_tool_registration.py
│   ├── test_schema_generation.py
│   └── test_transport_compliance.py
├── integration/                  # EXISTING: Must pass unchanged
│   ├── test_tool_handlers.py
│   └── test_embeddings.py
└── unit/                         # EXISTING: Must pass unchanged
    └── test_services.py
```

**Structure Decision**: Single project structure (Option 1) with MCP server as primary component. Refactored code lives alongside legacy implementation during transition. Legacy server files (`mcp_stdio_server_v3.py`, `server.py`) remain in codebase for rollback capability via version control. New FastMCP server (`server_fastmcp.py`) becomes primary entry point post-migration.

## Phase 0: Outline & Research

### Research Tasks

1. **FastMCP Async Support Investigation**
   - **Unknown**: FastMCP compatibility with async database operations (AsyncPG, SQLAlchemy async sessions)
   - **Research**: Review FastMCP documentation and examples for async/await patterns in tool handlers
   - **Output**: Confirmation that @mcp.tool() supports async def functions

2. **FastMCP Context Integration with Structured Logging**
   - **Unknown**: How to route FastMCP's context.log() calls to `/tmp/codebase-mcp.log` instead of stdout
   - **Research**: FastMCP context object API, logging configuration options
   - **Output**: Configuration pattern for file-based logging integration

3. **FastMCP Schema Override Mechanisms**
   - **Unknown**: Syntax and patterns for manually defining schemas when automatic generation conflicts
   - **Research**: FastMCP schema customization API, Pydantic model compatibility
   - **Output**: Example of schema override for complex Pydantic models

4. **FastMCP Stdio Transport Configuration**
   - **Unknown**: How to configure FastMCP for stdio transport compatible with Claude Desktop config
   - **Research**: FastMCP transport layer, stdio vs SSE configuration
   - **Output**: Server initialization code for stdio transport

5. **FastMCP Decorator Failure Modes**
   - **Unknown**: What error messages FastMCP provides when decorator registration fails
   - **Research**: FastMCP startup validation, error handling patterns
   - **Output**: Fail-fast validation strategy during server initialization

6. **Pydantic Model Compatibility**
   - **Unknown**: Which existing Pydantic models might conflict with FastMCP's automatic schema generation
   - **Research**: Review existing models (`Task`, `CodeChunk`, `Repository`) against FastMCP requirements
   - **Output**: List of models requiring schema overrides

### Research Execution

Dispatching research to generate `research.md` with consolidated findings...

**Output**: research.md (generated in Phase 0 execution)

## Phase 1: Design & Contracts

*Prerequisites: research.md complete*

### Artifacts to Generate

1. **data-model.md**: Tool handler signatures
   - Extract each tool from specification (search_code, index_repository, create_task, get_task, list_tasks, update_task)
   - Define FastMCP-decorated function signature with full type hints
   - Document Pydantic input/output models for each tool
   - Note any schema override requirements from research phase

2. **contracts/**: FastMCP tool schemas
   - `search_tool.json`: OpenAPI-style schema for search_code tool
   - `indexing_tool.json`: Schema for index_repository tool
   - `task_tools.json`: Combined schemas for task management tools
   - `server_example.py`: Example FastMCP server initialization showing decorator registration

3. **Contract tests**: FastMCP-specific validation
   - `test_tool_registration.py`: Verify all 6 tools register correctly with @mcp.tool()
   - `test_schema_generation.py`: Validate automatic schema matches expected MCP protocol format
   - `test_transport_compliance.py`: Confirm stdio transport works with Claude Desktop config
   - Tests MUST fail initially (no FastMCP implementation yet)

4. **quickstart.md**: Migration validation scenarios
   - Scenario 1: Start FastMCP server, verify tool registration logs
   - Scenario 2: Execute search_code via stdio, validate protocol-compliant response
   - Scenario 3: Run existing integration test suite, confirm 100% pass rate
   - Scenario 4: Performance benchmark comparison (pre/post migration)
   - Scenario 5: Rollback test (revert to v3 server, validate functionality)

5. **CLAUDE.md update**: Incremental agent context refresh
   - Run: `.specify/scripts/bash/update-agent-context.sh claude`
   - Add FastMCP framework references to technical stack
   - Update MCP server architecture notes
   - Preserve existing manual edits

**Output**: data-model.md, contracts/, failing contract tests, quickstart.md, updated CLAUDE.md

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

### Task Generation Strategy

**Input Sources:**
- data-model.md: 6 tool handler signatures
- contracts/: Tool schema definitions
- quickstart.md: 5 validation scenarios
- Existing test suite: Protocol compliance, integration, performance tests

**Task Categories:**

1. **Infrastructure Tasks** (Sequential):
   - T001: Install FastMCP and MCP Python SDK dependencies
   - T002: Create FastMCP server instance (`server_fastmcp.py`)
   - T003: Configure stdio transport for Claude Desktop compatibility
   - T004: Integrate structured logging with FastMCP context

2. **Contract Test Tasks** (Parallel):
   - T005 [P]: Write test_tool_registration.py (verify decorator registration)
   - T006 [P]: Write test_schema_generation.py (validate auto-generated schemas)
   - T007 [P]: Write test_transport_compliance.py (stdio transport validation)

3. **Tool Migration Tasks** (Parallel after infrastructure):
   - T008 [P]: Refactor search_code tool with @mcp.tool() decorator
   - T009 [P]: Refactor index_repository tool with @mcp.tool() decorator
   - T010 [P]: Refactor create_task tool with @mcp.tool() decorator
   - T011 [P]: Refactor get_task tool with @mcp.tool() decorator
   - T012 [P]: Refactor list_tasks tool with @mcp.tool() decorator
   - T013 [P]: Refactor update_task tool with @mcp.tool() decorator

4. **Schema Override Tasks** (Conditional, based on research findings):
   - T014: Implement schema overrides for conflicting Pydantic models (if needed)

5. **Integration Validation Tasks** (Sequential):
   - T015: Run existing protocol compliance tests (must pass unchanged)
   - T016: Run existing integration tests (must pass unchanged)
   - T017: Run performance benchmarks (must meet 60s/500ms targets)
   - T018: Execute quickstart.md validation scenarios
   - T019: Update Claude Desktop config to use server_fastmcp.py

6. **Documentation Tasks** (Parallel):
   - T020 [P]: Update README.md with FastMCP server instructions
   - T021 [P]: Document rollback procedure (reverting to v3 server)

### Ordering Strategy

**TDD Order**: Contract tests (T005-T007) before tool migrations (T008-T013)
**Dependency Order**: Infrastructure (T001-T004) before tool migrations
**Parallel Execution**: Tool migrations are independent (different files) - marked [P]
**Sequential Validation**: All integration tests run after migrations complete

### Estimated Task Count

**Total**: ~21 tasks
- Infrastructure: 4 tasks
- Contract tests: 3 tasks
- Tool migrations: 6 tasks
- Schema overrides: 1 task (conditional)
- Integration validation: 5 tasks
- Documentation: 2 tasks

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)
**Phase 4**: Implementation
- Use orchestrated subagent execution (Principle IX)
- Parallel execution for independent tool migrations (T008-T013)
- Atomic commits after each task completion (Principle X)
- mypy --strict validation before each commit

**Phase 5**: Validation
- All tests must pass (protocol compliance, integration, performance)
- Execute quickstart.md scenarios
- Performance validation against 60s/500ms targets
- Rollback capability verification

## Complexity Tracking

**No constitutional violations.** This migration simplifies the codebase by:
- Removing ~400 LOC of custom protocol handling
- Delegating schema generation to FastMCP framework
- Enforcing type safety through decorator patterns
- Reducing maintenance burden via framework abstractions

Migration directly implements Constitutional Principle XI (FastMCP and Python SDK Foundation), added via `/constitution` command on 2025-10-06.

## Progress Tracking

**Phase Status**:
- [x] Phase 0: Research complete (/plan command) ✅
- [x] Phase 1: Design complete (/plan command) ✅
- [x] Phase 2: Task planning complete (/plan command - describe approach only) ✅
- [x] Phase 3: Tasks generated (/tasks command) ✅
- [ ] Phase 4: Implementation complete - NEXT
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS ✅
- [x] Post-Design Constitution Check: PASS ✅
- [x] All NEEDS CLARIFICATION resolved ✅ (5 clarifications completed)
- [x] Complexity deviations documented: N/A (no violations)

**Artifacts Generated**:
- [x] research.md (6 research topics with code examples)
- [x] data-model.md (6 tool signatures with type hints)
- [x] contracts/search_tool.json (MCP schema)
- [x] contracts/indexing_tool.json (MCP schema)
- [x] contracts/task_tools.json (MCP schema)
- [x] contracts/server_example.py (Complete FastMCP server)
- [x] quickstart.md (5 validation scenarios)
- [x] CLAUDE.md (Updated with FastMCP context)
- [x] tasks.md (24 tasks in 6 phases with parallel execution guidance)

---
*Based on Constitution v2.2.0 - See `.specify/memory/constitution.md`*
