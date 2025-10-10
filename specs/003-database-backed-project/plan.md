# Implementation Plan: Project Status and Work Item Tracking MCP System

**Branch**: `003-database-backed-project` | **Date**: 2025-10-10 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-database-backed-project/spec.md`

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

Add database-backed project status and work item tracking system as MCP tools, replacing manual .project_status.md with queryable PostgreSQL storage supporting multiple AI clients. System tracks vendors (45+), work items (hierarchical with dependencies), deployments, and configuration with performance targets (<1ms vendor queries, <10ms work item hierarchies, <100ms full status). Features 4-layer fallback (PostgreSQL → SQLite cache → Git → Markdown), optimistic locking for concurrent updates, automatic archiving (1 year threshold), and 100% data migration with validation.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: FastMCP, MCP Python SDK, SQLAlchemy 2.0+, AsyncPG, Pydantic 2.0+, aiosqlite
**Storage**: PostgreSQL 14+ (primary), SQLite (cache/fallback), Markdown files (legacy compatibility)
**Testing**: pytest with async support, contract tests, integration tests, performance validation
**Target Platform**: Linux/macOS server, offline-capable
**Project Type**: single (MCP server extension)
**Performance Goals**: <1ms vendor queries, <10ms work item hierarchy queries, <100ms full status generation
**Constraints**: No hard failures, 4-layer fallback, offline operation, optimistic locking, <0 custom observability overhead
**Scale/Scope**: 45+ vendors, 1,200+ work items over 5 years, automatic archiving after 1 year

**User-Provided Context**: Complete 28,000 token implementation plan available at: `/Users/cliffclarke/Claude_Code/commission-processing-vendor-extractors/docs/subagent-reports/framework-research/database-project-status/2025-10-10-revised-plan.md`

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Initial Evaluation (Pre-Research)

| Principle | Compliance Status | Notes |
|-----------|-------------------|-------|
| **I. Simplicity Over Features** | ⚠️ PARTIAL | Adding project tracking extends beyond core semantic search - REQUIRES JUSTIFICATION |
| **II. Local-First Architecture** | ✅ PASS | PostgreSQL + SQLite fallback, no cloud dependencies |
| **III. Protocol Compliance (MCP via SSE)** | ✅ PASS | New MCP tools follow existing FastMCP patterns |
| **IV. Performance Guarantees** | ✅ PASS | Specific targets defined: <1ms, <10ms, <100ms |
| **V. Production Quality Standards** | ✅ PASS | Pydantic validation, error handling, fallback mechanisms |
| **VI. Specification-First Development** | ✅ PASS | Complete spec with clarifications before planning |
| **VII. Test-Driven Development** | ✅ PASS | TDD workflow planned with contract/integration tests |
| **VIII. Pydantic-Based Type Safety** | ✅ PASS | All JSONB metadata validated via Pydantic |
| **IX. Orchestrated Subagent Execution** | ✅ PASS | Parallel task execution planned for implementation |
| **X. Git Micro-Commit Strategy** | ✅ PASS | Feature branch 003-database-backed-project, atomic commits planned |
| **XI. FastMCP and Python SDK Foundation** | ✅ PASS | 8 new MCP tools using FastMCP decorators |

**GATE STATUS**: ⚠️ CONDITIONAL PASS - Requires complexity justification for Principle I

### Complexity Justification Required

**Violation**: Adding project status tracking extends beyond core MCP server purpose (semantic code search)

**Why Needed**:
- MCP servers inherently require development project tracking to coordinate multi-client AI assistant work
- Existing .project_status.md proves inadequate for concurrent AI client access
- Task tracking already exists in database (src/models/task.py) - this extends existing capability
- Enables AI assistants to self-coordinate work across sessions and clients

**Simpler Alternative Rejected Because**:
- External project tracking tools don't integrate with MCP protocol
- Manual markdown maintenance breaks AI assistant workflows
- Existing task model needs vendor tracking and deployment history for commission processing domain
- Separate tool would duplicate database infrastructure and break single-source-of-truth

**Decision**: JUSTIFIED - This is infrastructure for MCP server development workflow, not feature creep. Extends existing task tracking with domain-specific entities (vendors, deployments).

## Project Structure

### Documentation (this feature)
```
specs/003-database-backed-project/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
│   ├── mcp-tools.yaml   # OpenAPI-style MCP tool contracts
│   └── pydantic-schemas.py  # Pydantic models for JSONB validation
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
src/
├── models/
│   ├── __init__.py
│   ├── task.py              # Existing - extend for work item polymorphism
│   ├── tracking.py          # NEW - vendor, deployment, configuration models
│   └── database.py          # Existing - extend with new tables
├── services/
│   ├── __init__.py
│   ├── tasks.py             # Existing - extend for hierarchical queries
│   ├── project_status.py    # NEW - status generation, migration, archiving
│   └── fallback.py          # NEW - 4-layer fallback orchestration
├── mcp/
│   ├── __init__.py
│   ├── server_fastmcp.py    # Existing - register new tools
│   └── tools/
│       ├── __init__.py
│       ├── tasks.py         # Existing - extend with new operations
│       └── project_tracking.py  # NEW - 8 new MCP tools
└── migrations/
    └── versions/
        └── 003_project_tracking.py  # Alembic migration

tests/
├── contract/
│   ├── test_vendor_tracking_contract.py     # NEW
│   ├── test_deployment_tracking_contract.py # NEW
│   ├── test_work_item_crud_contract.py      # NEW
│   └── test_configuration_contract.py       # NEW
├── integration/
│   ├── test_concurrent_updates.py           # NEW - optimistic locking
│   ├── test_fallback_mechanisms.py          # NEW - 4-layer fallback
│   ├── test_archiving_workflow.py           # NEW - 1-year threshold
│   └── test_migration_validation.py         # NEW - 100% data preservation
└── unit/
    ├── test_pydantic_schemas.py             # NEW - JSONB validation
    └── test_hierarchical_queries.py         # NEW - 5-level depth
```

**Structure Decision**: Single project (MCP server) - extend existing `src/models/`, `src/services/`, `src/mcp/tools/` with new project tracking capabilities. Aligns with constitutional simplicity by building on existing task tracking foundation rather than creating separate system.

## Phase 0: Outline & Research
*Generating research.md to resolve technical decisions*

### Research Tasks

1. **Optimistic Locking Patterns in SQLAlchemy**
   - Decision: Version column strategy
   - Research: SQLAlchemy 2.0 ORM-level optimistic locking with `version_id_col`
   - Alternatives: Application-level timestamp comparison, database triggers

2. **SQLite Cache for Offline Fallback**
   - Decision: aiosqlite with async context managers
   - Research: Schema synchronization strategies between PostgreSQL and SQLite
   - Alternatives: In-memory dict cache, Redis (rejected - external dependency)

3. **JSONB Pydantic Validation Integration**
   - Decision: Store serialized Pydantic models, validate on read/write
   - Research: SQLAlchemy JSON column with Pydantic validators
   - Alternatives: Separate validation layer, JSON schema validation

4. **Automatic Archiving Strategy**
   - Decision: Background task with configurable threshold (default 1 year)
   - Research: Alembic migration patterns for archive table creation
   - Alternatives: Soft-delete flag only, manual archiving, time-based partitioning

5. **Hierarchical Query Performance**
   - Decision: Recursive CTEs with materialized path or closure table
   - Research: PostgreSQL recursive CTE performance for 5-level depth
   - Alternatives: Adjacency list with application-level recursion, nested sets

6. **YAML Frontmatter Parsing**
   - Decision: python-frontmatter library with schema versioning
   - Research: Malformed YAML error handling strategies
   - Alternatives: Custom regex parsing, TOML frontmatter

7. **Markdown Status Report Generation**
   - Decision: Template-based generation with Jinja2
   - Research: Legacy format compatibility requirements
   - Alternatives: String formatting, custom template engine

**Output**: research.md with decisions, rationale, and alternatives for each technical choice

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

### 1. Data Model Design (data-model.md)

**Entities** (from spec):
- **VendorExtractor** (NEW)
- **DeploymentEvent** (NEW)
- **WorkItem** (extend existing Task model with polymorphism)
- **ProjectConfiguration** (NEW - singleton)
- **FutureEnhancement** (NEW)
- **WorkItemDependency** (NEW - junction table)
- **VendorDeploymentLink** (NEW - junction table)
- **WorkItemDeploymentLink** (NEW - junction table)
- **ArchivedWorkItem** (NEW - archive table)

**Relationships**:
- WorkItem.parent → WorkItem (self-referential, 5 levels)
- WorkItem.dependencies → WorkItemDependency → WorkItem
- DeploymentEvent.vendors → VendorDeploymentLink → VendorExtractor
- DeploymentEvent.work_items → WorkItemDeploymentLink → WorkItem

**Validation Rules** (Pydantic schemas):
- VendorMetadata: format_support flags, test_results structure
- WorkItemMetadata: type-specific schemas (project/session/task/research)
- DeploymentMetadata: PR details, commit hash format, compliance flags

**State Transitions**:
- WorkItem: active → archived (after 1 year)
- VendorExtractor: operational ↔ broken

### 2. API Contracts (contracts/mcp-tools.yaml)

**8 New MCP Tools**:
1. **create_work_item** - Create project/session/task/research with metadata
2. **update_work_item** - Update with optimistic locking (version check)
3. **query_work_item** - Get single item with full hierarchy
4. **list_work_items** - Filter by type, status, parent, with pagination
5. **record_deployment** - Record deployment event with vendor/work item links
6. **query_vendor_status** - Get vendor operational status (<1ms target)
7. **update_vendor_status** - Update vendor test results, version, flags
8. **get_project_configuration** - Retrieve singleton configuration

**Contract Structure** (per tool):
```yaml
tool_name: create_work_item
description: Create hierarchical work item with type-specific metadata
parameters:
  type: object
  properties:
    item_type:
      type: string
      enum: [project, session, task, research]
    title:
      type: string
      maxLength: 200
    parent_id:
      type: string
      format: uuid
      nullable: true
    metadata:
      type: object  # Pydantic-validated JSONB
  required: [item_type, title]
returns:
  type: object
  properties:
    id: {type: string, format: uuid}
    version: {type: integer}
    created_at: {type: string, format: date-time}
    created_by: {type: string}  # AI client identifier
```

### 3. Pydantic Schemas (contracts/pydantic-schemas.py)

```python
from pydantic import BaseModel, Field, validator
from typing import Literal, Optional
from datetime import datetime
from uuid import UUID

class VendorMetadata(BaseModel):
    """Vendor-specific JSONB metadata"""
    format_support: dict[Literal["excel", "csv", "pdf", "ocr"], bool]
    test_results: dict[Literal["passing", "total", "skipped"], int]
    extractor_version: str
    manifest_compliant: bool

class ProjectMetadata(BaseModel):
    """Project work item metadata"""
    description: str
    target_quarter: Optional[str] = None
    constitutional_principles: list[str] = []

class SessionMetadata(BaseModel):
    """Session work item metadata"""
    token_budget: int
    prompts_count: int
    yaml_frontmatter: dict

class TaskMetadata(BaseModel):
    """Task work item metadata"""
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    blocked_reason: Optional[str] = None

class DeploymentMetadata(BaseModel):
    """Deployment event metadata"""
    pr_number: int
    pr_title: str
    commit_hash: str = Field(pattern=r'^[a-f0-9]{40}$')
    test_summary: dict[str, int]
    constitutional_compliance: bool

class WorkItemCreate(BaseModel):
    """MCP tool input for create_work_item"""
    item_type: Literal["project", "session", "task", "research"]
    title: str = Field(max_length=200)
    parent_id: Optional[UUID] = None
    metadata: ProjectMetadata | SessionMetadata | TaskMetadata | dict

class WorkItemUpdate(BaseModel):
    """MCP tool input for update_work_item"""
    id: UUID
    version: int  # Optimistic locking
    title: Optional[str] = Field(None, max_length=200)
    metadata: Optional[dict] = None
    deleted_at: Optional[datetime] = None  # Soft delete
```

### 4. Contract Tests (tests/contract/)

Generate failing tests for each MCP tool:
- `test_vendor_tracking_contract.py` - FR-001 through FR-004
- `test_deployment_tracking_contract.py` - FR-005 through FR-007
- `test_work_item_crud_contract.py` - FR-008 through FR-014
- `test_configuration_contract.py` - FR-015 through FR-016

Each test validates:
- Input schema compliance (Pydantic validation)
- Output schema compliance
- Error responses (validation failures, version mismatches)

### 5. Integration Test Scenarios (quickstart.md)

Map acceptance scenarios from spec to integration tests:
- Scenario 1 → `test_vendor_query_performance.py` (< 1ms validation)
- Scenario 2 → `test_concurrent_work_item_updates.py` (optimistic locking)
- Scenario 3 → `test_deployment_event_recording.py` (relationship linkage)
- Scenario 4 → `test_database_unavailable_fallback.py` (4-layer fallback)
- Scenario 5 → `test_migration_data_preservation.py` (100% validation)
- Scenario 6 → `test_hierarchical_work_item_query.py` (<10ms, 5 levels)
- Scenario 7 → `test_multi_client_concurrent_access.py` (immediate visibility)
- Scenario 8 → `test_full_status_generation_performance.py` (<100ms)

### 6. Update Agent Context (CLAUDE.md)

Run: `.specify/scripts/bash/update-agent-context.sh claude`

Adds to CLAUDE.md:
- New MCP tools (8 tools for project tracking)
- Database models (VendorExtractor, DeploymentEvent, WorkItem extensions)
- Performance targets (<1ms, <10ms, <100ms)
- Fallback architecture (4-layer: PostgreSQL → SQLite → Git → Markdown)

**Output**: data-model.md, contracts/mcp-tools.yaml, contracts/pydantic-schemas.py, tests/contract/*, quickstart.md, CLAUDE.md updated

## Phase 1: Post-Design Constitution Re-Check

### Re-Evaluation After Design

| Principle | Compliance Status | Design Notes |
|-----------|-------------------|--------------|
| **I. Simplicity Over Features** | ✅ PASS | Justified as MCP server development infrastructure |
| **II. Local-First Architecture** | ✅ PASS | SQLite fallback ensures offline operation |
| **III. Protocol Compliance** | ✅ PASS | 8 tools follow FastMCP @mcp.tool() decorator pattern |
| **IV. Performance Guarantees** | ✅ PASS | Indexed queries, recursive CTEs, materialized paths |
| **V. Production Quality** | ✅ PASS | Pydantic validation, 4-layer fallback, optimistic locking |
| **VI. Specification-First** | ✅ PASS | Complete spec with clarifications guided design |
| **VII. TDD** | ✅ PASS | Contract tests written before implementation |
| **VIII. Pydantic Type Safety** | ✅ PASS | All JSONB validated, schemas in contracts/ |
| **IX. Orchestrated Subagents** | ✅ PASS | Parallel execution planned for models, services, tools |
| **X. Git Micro-Commits** | ✅ PASS | Feature branch 003, commit after each task |
| **XI. FastMCP Foundation** | ✅ PASS | All tools use @mcp.tool() decorators |

**GATE STATUS**: ✅ PASS - No new violations introduced during design phase

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:

1. **Load Base Template**: `.specify/templates/tasks-template.md`

2. **Generate Contract Test Tasks** (from contracts/):
   - T001: [P] Write contract test for create_work_item
   - T002: [P] Write contract test for update_work_item (optimistic locking)
   - T003: [P] Write contract test for query_work_item (hierarchy)
   - T004: [P] Write contract test for list_work_items (pagination)
   - T005: [P] Write contract test for record_deployment
   - T006: [P] Write contract test for query_vendor_status (<1ms)
   - T007: [P] Write contract test for update_vendor_status
   - T008: [P] Write contract test for get_project_configuration

3. **Generate Database Model Tasks** (from data-model.md):
   - T009: [P] Create VendorExtractor model with Pydantic metadata
   - T010: [P] Create DeploymentEvent model with relationships
   - T011: Extend WorkItem model for polymorphism (project/session/task/research)
   - T012: [P] Create ProjectConfiguration singleton model
   - T013: [P] Create FutureEnhancement model
   - T014: [P] Create junction tables (WorkItemDependency, VendorDeploymentLink, WorkItemDeploymentLink)
   - T015: [P] Create ArchivedWorkItem table
   - T016: Write Alembic migration 003_project_tracking.py
   - T017: Add optimistic locking version columns
   - T018: Add database indexes for performance (<1ms, <10ms targets)

4. **Generate Service Layer Tasks**:
   - T019: Implement hierarchical work item queries (recursive CTE)
   - T020: Implement optimistic locking update logic
   - T021: Implement vendor status query service (<1ms optimization)
   - T022: Implement deployment event recording with relationship links
   - T023: Implement automatic archiving service (1-year threshold)
   - T024: Implement SQLite cache synchronization
   - T025: Implement 4-layer fallback orchestration
   - T026: Implement markdown status report generation
   - T027: Implement data migration from .project_status.md
   - T028: Implement 5 reconciliation checks

5. **Generate MCP Tool Tasks**:
   - T029: [P] Implement create_work_item tool
   - T030: [P] Implement update_work_item tool (version check)
   - T031: [P] Implement query_work_item tool
   - T032: [P] Implement list_work_items tool
   - T033: [P] Implement record_deployment tool
   - T034: [P] Implement query_vendor_status tool
   - T035: [P] Implement update_vendor_status tool
   - T036: [P] Implement get_project_configuration tool
   - T037: Register 8 new tools in server_fastmcp.py

6. **Generate Integration Test Tasks** (from quickstart.md):
   - T038: Write test_vendor_query_performance (<1ms validation)
   - T039: Write test_concurrent_work_item_updates (optimistic locking)
   - T040: Write test_deployment_event_recording
   - T041: Write test_database_unavailable_fallback (4 layers)
   - T042: Write test_migration_data_preservation (100% validation)
   - T043: Write test_hierarchical_work_item_query (<10ms, 5 levels)
   - T044: Write test_multi_client_concurrent_access
   - T045: Write test_full_status_generation_performance (<100ms)

7. **Generate Validation Tasks**:
   - T046: Run all contract tests (must pass)
   - T047: Run all integration tests (must pass)
   - T048: Run performance validation (<1ms, <10ms, <100ms)
   - T049: Execute data migration and validation
   - T050: Test 4-layer fallback scenarios
   - T051: Validate optimistic locking under load
   - T052: Update CLAUDE.md with final implementation notes

**Ordering Strategy**:
- **TDD Order**: Contract tests (T001-T008) → Models (T009-T018) → Services (T019-T028) → Tools (T029-T037) → Integration tests (T038-T045)
- **Dependency Order**: Database schema → Models → Services → MCP tools → Tests
- **Parallel Execution**: Mark [P] for independent tasks (different models, different contract tests, different tools)

**Estimated Output**: 52 numbered, dependency-ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)
**Phase 4**: Implementation via `/implement` with orchestrated subagents
- Parallel execution: Contract tests, models, Pydantic schemas
- Sequential execution: Alembic migrations, service layer, MCP tool registration
- Git micro-commits after each completed task

**Phase 5**: Validation
- Run performance tests against <1ms, <10ms, <100ms targets
- Execute data migration with 100% validation
- Test 4-layer fallback under simulated database failures
- Validate optimistic locking prevents concurrent update conflicts
- Execute quickstart.md integration test scenarios

## Complexity Tracking
*Filled based on Constitution Check violations that required justification*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle I: Simplicity Over Features | Project tracking extends beyond semantic code search | External tools don't integrate with MCP protocol; manual markdown breaks AI workflows; existing task model already in database; AI assistants need self-coordination capability |

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
- [X] Initial Constitution Check: CONDITIONAL PASS (justified)
- [X] Post-Design Constitution Check: PASS
- [X] All NEEDS CLARIFICATION resolved (5 clarifications in spec)
- [X] Complexity deviations documented (Principle I justified)

---
*Based on Constitution v2.2.0 - See `.specify/memory/constitution.md`*
