
# Implementation Plan: Create Vendor MCP Function

**Branch**: `005-create-vendor` | **Date**: 2025-10-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/Users/cliffclarke/Claude_Code/codebase-mcp/specs/005-create-vendor/spec.md`

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

**IMPORTANT**: The /plan command STOPS at step 9. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Add create_vendor() MCP tool function to enable programmatic initialization of vendor tracking records during vendor scaffolding workflow. This completes the vendor management contract by allowing AI assistants to atomically create vendor database records with proper initial state (status="broken", all format flags false) and metadata (scaffolder version, timestamps) when scripts/new_vendor.sh generates vendor extractor code skeletons.

## Technical Context
**Language/Version**: Python 3.11+
**Primary Dependencies**: FastMCP, MCP Python SDK, Pydantic, SQLAlchemy, AsyncPG
**Storage**: PostgreSQL 14+ with existing vendors table schema
**Testing**: pytest with contract, integration, and unit test structure
**Target Platform**: Linux/macOS server (local-first MCP server)
**Project Type**: Single project (MCP server with Python backend)
**Performance Goals**: <100ms p95 latency for create_vendor() function (per clarifications)
**Constraints**: Must comply with MCP protocol via SSE, no stdout/stderr pollution, file-based logging to /tmp/codebase-mcp.log
**Scale/Scope**: Single MCP tool function extending existing vendor management tools (query_vendor_status, update_vendor_status)

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Simplicity Over Features
✅ **PASS** - Adding a single create operation to complete CRUD pattern for vendor management. Natural extension of existing vendor tools (query, update).

### Principle II: Local-First Architecture
✅ **PASS** - PostgreSQL-only operation, no external APIs, completely offline capable.

### Principle III: Protocol Compliance (MCP via SSE)
✅ **PASS** - Will use FastMCP @mcp.tool() decorator, consistent with existing tools, no stdout/stderr violations.

### Principle IV: Performance Guarantees
✅ **PASS** - Target <100ms p95 latency specified in requirements (FR-015), consistent with existing vendor tools. Single INSERT operation with validation.

### Principle V: Production Quality Standards
✅ **PASS** - Will include comprehensive error handling (duplicate name, validation errors, database errors per FR-009), Pydantic validation for inputs, mypy --strict compliance.

### Principle VI: Specification-First Development
✅ **PASS** - Feature specification completed and clarified before planning.

### Principle VII: Test-Driven Development
✅ **PASS** - Plan includes contract tests, integration tests, and unit tests before implementation.

### Principle VIII: Pydantic-Based Type Safety
✅ **PASS** - Will use Pydantic models for request/response validation, consistent with existing vendor tools.

### Principle IX: Orchestrated Subagent Execution
✅ **PASS** - Planning for parallel task execution where appropriate during implementation phase.

### Principle X: Git Micro-Commit Strategy
✅ **PASS** - Feature on dedicated branch (005-create-vendor), will commit after each task completion.

### Principle XI: FastMCP and Python SDK Foundation
✅ **PASS** - Will use FastMCP @mcp.tool() decorator pattern, leveraging automatic schema generation from type hints.

**Initial Assessment**: NO VIOLATIONS - Feature aligns with all constitutional principles.

## Project Structure

### Documentation (this feature)
```
specs/005-create-vendor/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
│   └── create_vendor.yml
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
src/
├── mcp/
│   ├── tools/
│   │   ├── tracking.py          # ← Add create_vendor() here (vendor tools module)
│   │   └── __init__.py
│   ├── server_fastmcp.py        # MCP server registration (add tool)
│   └── errors.py                # Error definitions
├── models/
│   └── vendor.py                # ← Vendor Pydantic models (if not exists, else extend)
├── services/
│   └── vendor_service.py        # ← Vendor business logic (create/validate)
└── database/
    └── session.py               # Database session management

scripts/
└── new_vendor.sh                # Vendor scaffolding script (new)

tests/
├── contract/
│   └── test_create_vendor_contract.py  # MCP contract tests
├── integration/
│   └── test_create_vendor_integration.py  # End-to-end workflow tests
└── unit/
    ├── test_vendor_service.py   # Business logic unit tests
    └── test_vendor_validation.py  # Validation unit tests
```

**Structure Decision**: Single project structure using existing src/ layout. The create_vendor() function fits naturally into src/mcp/tools/tracking.py alongside existing query_vendor_status() and update_vendor_status() tools. Service layer logic will go in src/services/vendor_service.py, with Pydantic models in src/models/vendor.py. This maintains consistency with the established codebase architecture.

## Phase 0: Outline & Research

### Research Tasks
No unknowns in Technical Context - all clarifications resolved during /clarify phase. Research will focus on:

1. **Existing vendor schema analysis**: Review current vendors table structure, constraints, indexes
2. **Existing vendor tools patterns**: Analyze query_vendor_status() and update_vendor_status() implementations for consistency
3. **Database constraint strategy**: Confirm UNIQUE constraint implementation for case-insensitive names
4. **Metadata storage patterns**: Review how metadata JSONB field is used in existing vendor records
5. **FastMCP validation patterns**: Review how existing tools use Pydantic for input validation
6. **Error handling patterns**: Document existing error response formats from vendor tools

### Research Output Format
Will generate research.md with:
- **Database Schema**: Document vendors table structure, constraints, indexes
- **Tool Implementation Patterns**: Document FastMCP decorator usage, Pydantic models, error handling
- **Validation Strategy**: Document name validation approach (regex pattern, case-insensitive uniqueness)
- **Metadata Schema**: Document flexible JSONB validation for known fields (scaffolder_version, created_at)
- **Performance Considerations**: Document query optimization for <100ms target
- **Testing Patterns**: Document contract/integration test structure from existing vendor tests

**Output**: research.md with all technical decisions documented

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

### 1. Data Model (data-model.md)

#### Entities
**Vendor** (existing table, document schema):
- id (UUID, primary key)
- name (VARCHAR(100), UNIQUE constraint, case-insensitive)
- status (ENUM: operational|broken, default: broken)
- format_support_flags (JSONB, default: all false)
- metadata (JSONB, flexible schema with known fields)
- version (INTEGER, for optimistic locking)
- created_by (VARCHAR, default: "claude-code")
- created_at (TIMESTAMP, auto-generated)
- updated_at (TIMESTAMP, auto-updated)

**CreateVendorRequest** (Pydantic model):
- name: str (1-100 chars, alphanumeric + spaces/hyphens/underscores)
- initial_metadata: Optional[Dict[str, Any]] (flexible with validation for known fields)
- created_by: str (default: "claude-code")

**CreateVendorResponse** (Pydantic model):
- id: UUID
- name: str
- status: str (always "broken")
- format_support_flags: Dict[str, bool] (all false)
- metadata: Dict[str, Any]
- version: int (always 1 for new records)
- created_at: datetime
- created_by: str

#### Validation Rules
- Name: 1-100 characters, regex `^[a-zA-Z0-9 \-_]+$`, case-insensitive uniqueness check
- Metadata known fields:
  - scaffolder_version: Optional[str]
  - created_at: Optional[str] (ISO 8601 format validation)
  - Additional fields: allowed without validation

### 2. API Contracts (contracts/create_vendor.yml)
Will generate OpenAPI-style contract documenting:
- Tool name: create_vendor
- Input schema: CreateVendorRequest
- Output schema: CreateVendorResponse
- Error responses: DuplicateVendorError, ValidationError, DatabaseError
- Example requests/responses

### 3. Contract Tests
Generate tests/contract/test_create_vendor_contract.py:
- Test MCP tool registration
- Test input schema validation (Pydantic)
- Test output schema structure
- Test error response format
- Tests MUST fail initially (no implementation)

### 4. Integration Test Scenarios (quickstart.md)
From acceptance scenarios in spec:
1. Create vendor "NewCorp" with full metadata
2. Create vendor "AcmeInc" with partial metadata
3. Attempt duplicate creation (verify error)
4. Query newly created vendor immediately
5. Test case-insensitive duplicate detection
6. Test invalid name validation
7. Test invalid metadata validation

### 5. Vendor Scaffolding Script
Generate scripts/new_vendor.sh:
- Shell script for vendor scaffolding workflow
- Integrates with create_vendor() MCP call
- Automates extractor skeleton generation with database record creation

### 6. Update Agent File
Run: `.specify/scripts/bash/update-agent-context.sh claude`
- Add create_vendor() tool to MCP tools section
- Update vendor management workflow description
- Document atomic vendor onboarding pattern

**Output**: data-model.md, contracts/create_vendor.yml, test_create_vendor_contract.py (failing), quickstart.md, scripts/new_vendor.sh, CLAUDE.md (updated)

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

### Task Generation Strategy
Using `.specify/templates/tasks-template.md` as base, generate tasks:

**Database Migration**:
- T000: Create database migration for functional unique index on LOWER(name)

**Contract Tests** [P]:
- T001: Implement create_vendor MCP contract test

**Data Models** [P]:
- T002: Create CreateVendorRequest Pydantic model with validators
- T003: Create CreateVendorResponse Pydantic model
- T004: Create VendorNameValidator utility class

**Service Layer**:
- T005: Implement vendor name validation logic (regex, length)
- T006: Implement metadata validation logic (known fields)
- T007: Implement vendor creation service method (INSERT with constraints)
- T008: Implement duplicate detection error handling

**MCP Tool**:
- T009: Implement create_vendor() FastMCP tool function
- T010: Register create_vendor tool in server_fastmcp.py

**Integration Tests**:
- T011: Test create vendor with full metadata (acceptance scenario 1)
- T012: Test create vendor with partial metadata (acceptance scenario 2)
- T013: Test duplicate vendor error (acceptance scenario 3)
- T014: Test immediate query after creation (acceptance scenario 4)
- T015: Test case-insensitive duplicate detection
- T016: Test invalid name validation
- T017: Test invalid metadata validation

**Unit Tests** [P]:
- T018: Unit test vendor name validation logic
- T019: Unit test metadata validation logic
- T020: Unit test vendor service creation logic
- T021: Unit test error handling edge cases

**Performance Validation**:
- T022: Test create_vendor latency (<100ms p95)

**Documentation**:
- T023: Update CLAUDE.md with create_vendor usage examples

**Vendor Scaffolding**:
- T024: Create scripts/new_vendor.sh vendor scaffolding script
- T025: Integrate create_vendor() call into scripts/new_vendor.sh

### Ordering Strategy
1. **TDD order**: Migration (T000) → Contract tests (T001) → Models (T002-T004) → Unit tests (T018-T021) → Service (T005-T008) → Tool (T009-T010) → Integration tests (T011-T017) → Performance (T022) → Docs (T023) → Scaffolding (T024-T025)
2. **Dependencies**: Migration first, models before service, service before tool, tool before integration tests and scaffolding script
3. **Parallelization**: [P] marks independent files (contract tests, model files, unit tests can run in parallel)

**Estimated Output**: 27 numbered, ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)
**Phase 4**: Implementation (execute tasks.md following constitutional principles, micro-commits per task)
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation, MCP protocol compliance check)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

NO VIOLATIONS - No complexity deviations to justify.

## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [X] Phase 0: Research complete (/plan command)
- [X] Phase 1: Design complete (/plan command)
- [X] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [X] Initial Constitution Check: PASS
- [X] Post-Design Constitution Check: PASS
- [X] All NEEDS CLARIFICATION resolved
- [X] Complexity deviations documented (none - no violations)

---
*Based on Constitution v2.2.0 - See `.specify/memory/constitution.md`*
