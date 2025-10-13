
# Implementation Plan: Multi-Project Workspace Support

**Branch**: `008-multi-project-workspace` | **Date**: 2025-10-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-multi-project-workspace/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from file system structure or context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code, or `AGENTS.md` for all other agents).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary

This feature introduces multi-project workspace support to the codebase-mcp server, enabling users to maintain isolated code indexes for multiple projects simultaneously. Each project workspace provides complete data isolation, preventing cross-contamination during indexing and search operations. The implementation adds optional `project_id` parameters to MCP tools, validates project identifiers, automatically provisions isolated PostgreSQL schemas/tables, and optionally integrates with workflow-mcp for automatic project context detection.

## Technical Context
**Language/Version**: Python 3.11+
**Primary Dependencies**: FastMCP, MCP Python SDK, SQLAlchemy 2.0+, AsyncPG, Pydantic 2.0+, PostgreSQL 14+
**Storage**: PostgreSQL 14+ with pgvector extension (multi-schema isolation strategy)
**Testing**: pytest, pytest-asyncio, pytest-cov (95%+ coverage), pytest-benchmark
**Target Platform**: Local development machine (macOS/Linux), offline-capable
**Project Type**: Single Python project (MCP server architecture)
**Performance Goals**: Project switching <50ms (Constitutional Principle IV), maintain 60s indexing / 500ms search targets per project
**Constraints**: Complete data isolation (zero cross-project leakage), backward compatibility (existing users unaffected), security (SQL injection prevention via validation)
**Scale/Scope**: Support 10-20 concurrent projects per user, 50-character max project identifier, optional workflow-mcp integration with 1-minute cache TTL

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Enforcement Reference**: Consult the Enforcement Matrix in `.specify/memory/constitution.md` to understand which constitutional principles have automated enforcement (64% automation coverage) versus manual validation. This helps identify:
- Which design decisions can be validated automatically (CI/CD, pre-commit hooks)
- Which require human architectural review
- Where to invest in additional automation tooling

### Initial Constitution Validation

**I. Simplicity Over Features** ✅ PASS
- Feature scope: Multi-project workspace isolation only
- Single responsibility: Namespace management for existing functionality
- No feature creep: Explicitly excludes project management UI, analytics, cross-project search
- Rationale: Adds isolation layer without duplicating or extending core search capabilities

**II. Local-First Architecture** ✅ PASS
- No cloud dependencies introduced
- PostgreSQL schema-based isolation (local database)
- Optional workflow-mcp integration degrades gracefully to local-only operation
- Rationale: Maintains offline-capable architecture

**III. Protocol Compliance (MCP via SSE)** ✅ PASS
- Changes limited to adding optional `project_id` parameter to existing MCP tools
- No protocol message modifications
- Logging continues to `/tmp/codebase-mcp.log`
- Rationale: Backward-compatible parameter addition, no stdout/stderr pollution

**IV. Performance Guarantees** ⚠️ REQUIRES VALIDATION
- New requirement: Project switching <50ms (per Constitutional Principle IV)
- Existing requirements maintained: 60s indexing, 500ms search (per-project basis)
- Risk: Schema switching overhead must be measured
- Mitigation: Connection pooling per schema, benchmark project switching latency
- **Action**: Phase 0 research must validate schema-switching performance
  - **Resolution**: See research.md "Performance Characteristics" section for benchmark results
  - **Validated**: <5ms schema switching latency (well under 50ms target)

**V. Production Quality Standards** ✅ PASS
- Project identifier validation prevents SQL injection
- Comprehensive error handling (permission denied, timeout, invalid format)
- Pydantic models for all new data structures
- mypy --strict compliance enforced
- Rationale: Defensive programming for user-controlled identifiers

**VI. Specification-First Development** ✅ PASS
- Feature spec complete with 3 resolved clarifications
- No ambiguities remaining (NEEDS CLARIFICATION items addressed)
- Acceptance criteria defined for all functional requirements
- Rationale: Spec-driven workflow followed correctly

**VII. Test-Driven Development** ✅ PASS
- Contract tests for project workspace isolation required
- Integration tests for workflow-mcp fallback scenarios
- Performance tests for schema-switching latency
- Security tests for identifier validation (SQL injection)
- Rationale: Testable requirements enable TDD approach

**VIII. Pydantic-Based Type Safety** ✅ PASS
- ProjectIdentifier validation model required (lowercase alphanumeric + hyphen, max 50 chars)
- WorkspaceConfig model for project metadata
- WorkflowIntegrationContext model for optional workflow-mcp integration
- Rationale: User-controlled identifiers require strict validation

**IX. Orchestrated Subagent Execution** ✅ PASS
- Independent tasks: Validator module, workspace manager, workflow integration client
- Parallel implementation opportunities identified
- Orchestrator validates cross-component integration
- Rationale: Clear component boundaries enable parallel development

**X. Git Micro-Commit Strategy** ✅ PASS
- Feature branch: `008-multi-project-workspace` created
- Atomic tasks enable micro-commits per task completion
- Conventional Commits applicable to all changes
- Rationale: Branch-per-feature workflow established

**XI. FastMCP and Python SDK Foundation** ✅ PASS
- Tool parameter additions only (no protocol handling changes)
- FastMCP decorators remain unchanged (@mcp.tool())
- Context injection used for project resolution
- Rationale: Parameter additions compatible with FastMCP framework

### Gate Decision: **PASS** (with Phase 0 performance validation required)

**Post-Design Re-Check Required**: After Phase 1 design, re-validate Principle IV (Performance Guarantees) with concrete schema-switching implementation approach.

---

### Post-Design Constitution Re-Check

**Re-validation Date**: 2025-10-12 (after Phase 1 design completion)

**I. Simplicity Over Features** ✅ PASS (no change)
- Design maintains single-responsibility focus (workspace isolation only)
- No new features added beyond spec requirements
- Service layer clean: ProjectWorkspaceManager, WorkflowIntegrationClient

**II. Local-First Architecture** ✅ PASS (no change)
- Design uses local PostgreSQL schemas (no cloud)
- Optional workflow-mcp integration via localhost HTTP (no external APIs)
- All data stored in local database schemas

**III. Protocol Compliance (MCP via SSE)** ✅ PASS (validated)
- MCP tool contracts use optional parameters (backward compatible)
- No protocol message changes
- Error responses via MCP error format (not stdout/stderr)
- Contracts documented in `contracts/mcp-tools.yaml`

**IV. Performance Guarantees** ✅ PASS (VALIDATED)
- **Design approach**: `SET search_path` per session (in-memory operation)
- **Research validation**: <5ms schema switching (benchmark completed in Phase 0)
- **Target**: <50ms project switching (validated: <5ms << 50ms target)
- **Connection pooling**: Reuses existing pool (no additional overhead)
- **Provisioning**: ~65ms first-time (one-time cost, acceptable)
- **Conclusion**: Design meets Constitutional Principle IV performance guarantees

**V. Production Quality Standards** ✅ PASS (validated)
- Comprehensive error handling: ValidationError, PermissionError, timeout scenarios
- Pydantic models enforce runtime validation: ProjectIdentifier, WorkspaceConfig, WorkflowIntegrationContext
- Error messages include field-level context and suggested actions
- mypy --strict compliance enforced via type annotations

**VI. Specification-First Development** ✅ PASS (no change)
- Design derived directly from spec.md requirements
- All FR-001 through FR-018 addressed in data model
- Acceptance criteria mapped to quickstart scenarios

**VII. Test-Driven Development** ✅ PASS (validated)
- Contract tests defined in `contracts/mcp-tools.yaml`
- Integration tests defined in `quickstart.md` (9 scenarios)
- Performance tests planned: <50ms switching, <100ms provisioning
- Security tests planned: SQL injection prevention
- TDD task ordering documented in Phase 2

**VIII. Pydantic-Based Type Safety** ✅ PASS (validated)
- ProjectIdentifier: Pydantic model with regex validator (security-critical)
- WorkspaceConfig: Pydantic model with frozen=True (immutability)
- WorkflowIntegrationContext: Pydantic model with TTL logic
- All models enforce mypy --strict compliance

**IX. Orchestrated Subagent Execution** ✅ PASS (no change)
- Task breakdown identifies parallel opportunities ([P] markers)
- Independent components: Models, services, contract tests
- Orchestrator validates integration tests sequentially

**X. Git Micro-Commit Strategy** ✅ PASS (no change)
- Feature branch: `008-multi-project-workspace` active
- Task breakdown enables atomic commits per completed task
- Conventional Commits format applicable

**XI. FastMCP and Python SDK Foundation** ✅ PASS (validated)
- Design uses FastMCP @mcp.tool() decorators (no changes)
- Parameter additions compatible with FastMCP framework
- Context injection for project resolution
- No direct protocol handling introduced

### Post-Design Gate Decision: **PASS** ✅

**Performance Guarantee Validated**: Schema-switching approach (<5ms measured) meets Constitutional Principle IV target (<50ms). No constitutional violations introduced by design.

**Ready for Phase 2**: Proceed to `/tasks` command for task generation.

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
src/                          # Main source code
├── config/                   # Configuration management
├── database/                 # Database session and utilities
├── mcp/                      # MCP server implementation (FastMCP)
├── models/                   # Pydantic models and SQLAlchemy entities
└── services/                 # Business logic services
    ├── indexer.py           # Repository indexing
    ├── searcher.py          # Semantic search
    ├── embedder.py          # Embedding generation
    ├── chunker.py           # Code chunking (AST-based)
    └── scanner.py           # File system scanning

tests/                        # Test suite
├── contract/                 # MCP protocol compliance tests
├── integration/              # End-to-end workflow tests
├── unit/                     # Component unit tests
├── performance/              # Benchmark tests (60s/500ms targets)
└── fixtures/                 # Test data and helpers

migrations/                   # Alembic database migrations
├── env.py                   # Migration environment config
└── versions/                # Versioned migration scripts

scripts/                      # Utility scripts
├── init_db.py               # Database initialization
├── reset_database.sh        # Development database reset
└── collect_baseline.sh      # Performance baseline collection

docs/                         # Documentation
├── architecture/            # Architecture decision records
├── guides/                  # User and developer guides
├── operations/              # Operational procedures
└── specifications/          # Technical specifications

specs/                        # Feature specifications (per-feature)
└── ###-feature-name/        # Individual feature directories
    ├── spec.md              # Feature specification
    ├── plan.md              # Implementation plan
    ├── research.md          # Research decisions
    ├── data-model.md        # Data model definitions
    ├── contracts/           # API contracts
    ├── quickstart.md        # Integration test scenarios
    └── tasks.md             # Ordered task breakdown

.specify/                     # Workflow automation
├── memory/                  # Project memory (constitution, exceptions)
├── scripts/bash/            # Workflow scripts
└── templates/               # Document templates
```

**Structure Decision**: Single Python project with MCP server architecture. The codebase follows a service-oriented structure with clear separation between MCP protocol handling (src/mcp/), core services (src/services/), and data models (src/models/). Test organization mirrors constitutional requirements: contract tests for protocol compliance, integration tests for workflows, unit tests for components, and performance tests for 60s/500ms guarantees.

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/bash/update-agent-context.sh claude`
     **IMPORTANT**: Execute it exactly as specified above. Do not add or remove any arguments.
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `.specify/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Each Pydantic model → model creation task [P]
- Each contract endpoint → contract test task [P]
- Each quickstart scenario → integration test task
- Implementation tasks to make tests pass (TDD order)

**Task Categories**:

1. **Foundation Tasks** (Sequential):
   - Create ProjectIdentifier Pydantic model with validation
   - Create WorkspaceConfig Pydantic model
   - Create WorkflowIntegrationContext Pydantic model
   - Create project_registry schema migration
   - Create workspace_config table migration

2. **Service Layer Tasks** (Parallel after foundation):
   - [P] Implement ProjectWorkspaceManager service
   - [P] Implement WorkflowIntegrationClient service
   - [P] Create schema existence check utility
   - [P] Create schema provisioning utility

3. **Database Layer Tasks** (Sequential):
   - Update get_session() to support project_id parameter
   - Implement search_path switching logic
   - Add connection pooling validation tests

4. **MCP Tool Updates** (Parallel after database layer):
   - [P] Update index_repository tool with project_id parameter
   - [P] Update search_code tool with project_id parameter
   - [P] Add workflow-mcp integration to project resolution

5. **Contract Tests** (Parallel, TDD):
   - [P] Contract test: index_repository with project_id
   - [P] Contract test: search_code with project_id
   - [P] Contract test: invalid project_id validation
   - [P] Contract test: permission denied error

6. **Integration Tests** (Sequential, from quickstart.md):
   - Integration test: Complete data isolation (Scenario 1)
   - Integration test: Project switching (Scenario 2)
   - Integration test: Auto-provisioning (Scenario 3)
   - Integration test: Workflow-MCP integration (Scenario 4)
   - Integration test: Workflow-MCP timeout (Scenario 5)
   - Integration test: Invalid identifier (Scenario 6)
   - Integration test: Backward compatibility (Scenario 7)

7. **Performance Tests** (Parallel):
   - [P] Performance test: Project switching <50ms
   - [P] Performance test: Schema creation <100ms

8. **Security Tests** (Parallel):
   - [P] Security test: SQL injection prevention
   - [P] Security test: Identifier validation

**Ordering Strategy**:
- **TDD order**: Contract tests → Integration tests → Implementation → Tests pass
- **Dependency order**: Models → Services → Database layer → MCP tools
- **Parallel execution**: Mark [P] for independent tasks (different files/components)
- **Sequential validation**: Integration tests run after all implementations complete

**Estimated Output**: 35-40 numbered, dependency-ordered tasks in tasks.md

**Parallel Execution Opportunities**:
- Pydantic models (independent)
- Service implementations (after model creation)
- Contract tests (independent test files)
- Performance/security tests (independent test files)

**Sequential Requirements**:
- Foundation (models, schema) before services
- Services before MCP tool updates
- All implementation before integration tests
- Integration tests before feature complete

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

**Status**: No constitutional violations detected.

All design decisions align with constitutional principles (see Post-Design Constitution Re-Check above). No complexity deviations require justification.

**Validation**:
- ✅ Initial Constitution Check: PASS (all 11 principles)
- ✅ Post-Design Constitution Check: PASS (all 11 principles)
- ✅ Performance validation completed (schema switching: <5ms vs 50ms target)
- ✅ No speculative features beyond spec requirements
- ✅ Tech stack appropriately sized (schema-based isolation vs complex microservices)


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [X] Phase 0: Research complete (/plan command) ✅
- [X] Phase 1: Design complete (/plan command) ✅
- [X] Phase 2: Task planning complete (/plan command - describe approach only) ✅
- [X] Phase 3: Tasks generated (/tasks command) ✅
- [ ] Phase 4: Implementation complete (/implement command)
- [ ] Phase 5: Validation passed

**Gate Status**:
- [X] Initial Constitution Check: PASS ✅
- [X] Post-Design Constitution Check: PASS ✅
- [X] All NEEDS CLARIFICATION resolved ✅
- [X] Complexity deviations documented: NONE (no violations) ✅

**Artifacts Generated**:
- [X] research.md (Phase 0) - 8 research decisions documented
- [X] data-model.md (Phase 1) - 3 Pydantic models, database schema
- [X] contracts/mcp-tools.yaml (Phase 1) - MCP tool parameter contracts
- [X] quickstart.md (Phase 1) - 9 integration test scenarios
- [X] CLAUDE.md updated (Phase 1) - Agent context file
- [X] tasks.md (Phase 3) - 40 numbered tasks with dependency ordering

---
*Based on Constitution v3.0.0 - See `.specify/memory/constitution.md`*
