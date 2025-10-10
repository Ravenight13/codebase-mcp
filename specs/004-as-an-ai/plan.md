# Implementation Plan: Optimize list_tasks MCP Tool for Token Efficiency

**Branch**: `004-as-an-ai` | **Date**: 2025-10-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-as-an-ai/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   ✅ COMPLETED - spec.md loaded and analyzed
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   ✅ COMPLETED - no ambiguities, all technical details known
3. Fill the Constitution Check section
   ✅ COMPLETED - validated against 11 constitutional principles
4. Evaluate Constitution Check section
   ✅ COMPLETED - no violations, ready for Phase 0
5. Execute Phase 0 → research.md
   ✅ COMPLETED - 5 research areas documented with decisions
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, CLAUDE.md
   ✅ COMPLETED - all design artifacts generated
7. Re-evaluate Constitution Check
   ✅ COMPLETED - no new violations, design validated
8. Plan Phase 2 → Describe task generation approach
   ✅ COMPLETED - 19-task breakdown documented
9. STOP - Ready for /tasks command
   ✅ COMPLETED - planning phase complete
```

**IMPORTANT**: The /plan command STOPS at step 9. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary

**Primary Requirement**: Optimize the `list_tasks` MCP tool to return lightweight task summaries (id, title, status, timestamps) by default instead of full task details, reducing token usage from 12,000+ to <2,000 tokens for 15 tasks (~6x improvement).

**Technical Approach**: Implement two-tier response pattern by modifying the existing `list_tasks` tool handler to return minimal fields by default, with an optional parameter to request full details when needed. This follows established API design patterns (list returns summaries, get returns details) and maintains MCP protocol compliance.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastMCP, MCP Python SDK, Pydantic, SQLAlchemy, AsyncPG
**Storage**: PostgreSQL 14+ (existing task database schema)
**Testing**: pytest with async support, contract tests, integration tests
**Target Platform**: MCP server via stdio transport (Claude Desktop integration)
**Project Type**: Single project (FastMCP server)
**Performance Goals**: <200ms p95 latency for list_tasks, <2000 tokens for 15-task response
**Constraints**: <200ms p95 query latency, immediate breaking change acceptable, MCP protocol compliance required
**Scale/Scope**: Existing task management system with database-backed storage, handles dozens of tasks

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Constitution Check (Pre-Research)

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Simplicity Over Features** | ✅ PASS | Optimization of existing tool, no new features added |
| **II. Local-First Architecture** | ✅ PASS | No changes to local-first operation |
| **III. Protocol Compliance (MCP via SSE)** | ✅ PASS | Maintains MCP protocol compliance, response format optimization only |
| **IV. Performance Guarantees** | ✅ PASS | Improves performance (token efficiency), maintains <200ms p95 latency |
| **V. Production Quality Standards** | ✅ PASS | Maintains error handling, type safety, validation |
| **VI. Specification-First Development** | ✅ PASS | Spec completed with clarifications before planning |
| **VII. Test-Driven Development** | ✅ PASS | Will create contract tests before implementation |
| **VIII. Pydantic-Based Type Safety** | ✅ PASS | Will use Pydantic models for TaskSummary response schema |
| **IX. Orchestrated Subagent Execution** | ✅ PASS | Implementation will use subagents for parallel tasks |
| **X. Git Micro-Commit Strategy** | ✅ PASS | Feature branch created, will commit after each task |
| **XI. FastMCP and Python SDK Foundation** | ✅ PASS | Modifying existing FastMCP tool, maintains framework compliance |

**Gate Result**: ✅ PASS - No constitutional violations detected

## Project Structure

### Documentation (this feature)
```
specs/004-as-an-ai/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
│   ├── list_tasks_summary.yaml
│   └── list_tasks_full.yaml
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
src/
├── models/
│   ├── task.py              # Add TaskSummary Pydantic model
│   └── types.py             # Existing type definitions
├── services/
│   └── tasks.py             # Modify list_tasks service to support summary mode
├── mcp/
│   └── tools/
│       └── tasks.py         # Modify list_tasks tool handler (line 159-254)
└── database/
    └── session.py           # Existing session management

tests/
├── contract/
│   └── test_list_tasks_summary.py    # New contract tests for summary response
├── integration/
│   └── test_list_tasks_optimization.py  # Integration tests for token efficiency
└── unit/
    └── test_task_summary_model.py    # Unit tests for TaskSummary model
```

**Structure Decision**: Single project structure (default). This is a modification to existing MCP tool handlers in `src/mcp/tools/tasks.py` and service layer in `src/services/tasks.py`. The feature touches existing files rather than creating new modules, maintaining the established architecture.

## Phase 0: Outline & Research

### Research Areas

No NEEDS CLARIFICATION items remain after clarification phase. All technical decisions are known:

1. **Pydantic Model Design**: Research best practices for summary vs full model patterns in Pydantic
   - **Question**: How to structure TaskSummary and TaskResponse models to maximize code reuse?
   - **Context**: Need to avoid duplication while maintaining clear separation

2. **SQLAlchemy Query Optimization**: Research column selection in SQLAlchemy async queries
   - **Question**: How to selectively load columns in SQLAlchemy queries for performance?
   - **Context**: Currently using `select(Task)` which loads all columns

3. **FastMCP Response Patterns**: Research FastMCP tool return type patterns for variable responses
   - **Question**: How to handle optional full_details parameter in FastMCP tool signature?
   - **Context**: Need clean type hints for conditional response shapes

4. **MCP Contract Evolution**: Research MCP protocol guidance on breaking changes
   - **Question**: Are there MCP protocol patterns for versioning or response schema evolution?
   - **Context**: Implementing immediate breaking change per clarification

5. **Token Counting Validation**: Research approaches for measuring token count in response payloads
   - **Question**: How to validate <2000 token requirement in tests?
   - **Context**: Need measurable validation for PR-001 performance requirement

**Output**: `research.md` with findings and recommendations for each area

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

### 1. Data Model Design → `data-model.md`

**Entities to Define**:

1. **TaskSummary** (new Pydantic model)
   - Fields: id (UUID), title (str), status (str), created_at (datetime), updated_at (datetime)
   - Purpose: Lightweight response for list_tasks default behavior
   - Relationship: Subset of TaskResponse

2. **TaskResponse** (existing, may need restructuring)
   - Fields: All TaskSummary fields + description, notes, planning_references, branches, commits
   - Purpose: Full task details for get_task and list_tasks with full_details=True
   - Relationship: Superset of TaskSummary

**State Transitions**: No changes to task status enum

**Validation Rules**:
- TaskSummary must validate same core fields as TaskResponse
- Both models must serialize to MCP-compliant JSON

### 2. API Contract Generation → `contracts/`

**Contract Files**:

1. `contracts/list_tasks_summary.yaml` (OpenAPI)
   - Endpoint: list_tasks (default behavior)
   - Request: status (optional), branch (optional), limit (optional), full_details=false (default)
   - Response: `{ tasks: TaskSummary[], total_count: int }`
   - Token target: <2000 for 15 tasks

2. `contracts/list_tasks_full.yaml` (OpenAPI)
   - Endpoint: list_tasks with full_details=true
   - Request: status (optional), branch (optional), limit (optional), full_details=true
   - Response: `{ tasks: TaskResponse[], total_count: int }`
   - Token target: No constraint (full details)

### 3. Contract Tests → `tests/contract/`

**Test Files**:
- `test_list_tasks_summary.py`: Validate summary response schema
- `test_list_tasks_full_details.py`: Validate full details response schema
- `test_list_tasks_token_efficiency.py`: Validate <2000 token requirement

**Test Approach**: These tests MUST fail initially (TDD), then pass after implementation

### 4. Integration Test Scenarios → `quickstart.md`

**Scenario 1**: List tasks and get summary (primary user story)
- Given: 15 tasks in database
- When: Call list_tasks()
- Then: Receive 15 TaskSummary objects, <2000 tokens

**Scenario 2**: List tasks with full details (edge case)
- Given: 15 tasks in database
- When: Call list_tasks(full_details=True)
- Then: Receive 15 TaskResponse objects with all fields

**Scenario 3**: Get specific task details (two-tier pattern)
- Given: Task summary list received
- When: Call get_task(task_id)
- Then: Receive full TaskResponse for specific task

### 5. Agent File Update → `CLAUDE.md`

Run: `.specify/scripts/bash/update-agent-context.sh claude`
- Add: TaskSummary model pattern
- Add: list_tasks optimization approach
- Preserve: Existing MCP tool patterns
- Keep: Under 150 lines

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, CLAUDE.md updated

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:

1. Load `.specify/templates/tasks-template.md` as base structure
2. Generate tasks from Phase 1 design artifacts in TDD order:

**Phase A: Test Preparation** (Parallel)
- [P] T001: Create contract test for TaskSummary response schema
- [P] T002: Create contract test for full_details parameter behavior
- [P] T003: Create integration test for token efficiency (<2000 tokens)
- [P] T004: Create unit test for TaskSummary Pydantic model

**Phase B: Model Layer** (Parallel after tests)
- [P] T005: Create TaskSummary Pydantic model in src/models/task.py
- [P] T006: Update TaskResponse model if needed for consistency

**Phase C: Service Layer** (Sequential, depends on models)
- T007: Modify list_tasks_service to support summary mode (column selection)
- T008: Add full_details parameter to list_tasks_service signature

**Phase D: MCP Tool Layer** (Sequential, depends on service)
- T009: Modify list_tasks tool handler to accept full_details parameter
- T010: Update tool response to use TaskSummary by default
- T011: Implement conditional full response when full_details=True

**Phase E: Error Handling** (Parallel)
- [P] T012: Add error handling for invalid full_details parameter
- [P] T013: Update error response schemas in contracts

**Phase F: Documentation** (Parallel)
- [P] T014: Update tool docstrings for new parameter
- [P] T015: Create release notes documenting breaking change

**Phase G: Validation** (Sequential, final)
- T016: Run all contract tests (must pass)
- T017: Run integration tests (must pass)
- T018: Validate token count <2000 for 15 tasks
- T019: Validate latency <200ms p95

**Ordering Strategy**:
- TDD order: Tests (Phase A) before models (Phase B) before implementation (Phase C-D)
- Dependency order: Models → Services → Tools → Documentation
- Parallel markers [P]: Independent files that can be modified concurrently
- Sequential tasks: Same file modifications must be done in order

**Estimated Output**: 19 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)
**Phase 4**: Implementation (execute tasks.md with orchestrated subagents following Principle IX)
**Phase 5**: Validation (run tests, execute quickstart.md scenarios, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

No constitutional violations detected. This optimization aligns with all 11 principles:
- Simplicity: Reduces response payload complexity
- Performance: Improves token efficiency 6x
- Type Safety: Uses Pydantic models throughout
- Protocol Compliance: Maintains MCP standards

**No complexity justifications required.**

## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [x] Phase 3: Tasks generated (/tasks command - 21 tasks in tasks.md)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved (clarification session completed)
- [x] Complexity deviations documented (none required)

---
*Based on Constitution v2.2.0 - See `.specify/memory/constitution.md`*
