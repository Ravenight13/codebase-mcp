# Feature Specification: Remove Non-Search Tools from Codebase MCP

**Feature Branch**: `007-remove-non-search`
**Created**: 2025-10-11
**Status**: Draft
**Input**: User description: "Remove Non-Search Tools from Codebase MCP"

## Execution Flow (main)
```
1. Parse user description from Input
   → If empty: ERROR "No feature description provided"
2. Extract key concepts from description
   → Identify: actors, actions, data, constraints
3. For each unclear aspect:
   → Mark with [NEEDS CLARIFICATION: specific question]
4. Fill User Scenarios & Testing section
   → If no clear user flow: ERROR "Cannot determine user scenarios"
5. Generate Functional Requirements
   → Each requirement must be testable
   → Mark ambiguous requirements
6. Identify Key Entities (if data involved)
7. Run Review Checklist
   → If any [NEEDS CLARIFICATION]: WARN "Spec has uncertainties"
   → If implementation details found: ERROR "Remove tech details"
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

---

## Problem Statement

The codebase-mcp server currently exposes 16 MCP tools, but we only need 2 (index_repository and search_code) for semantic code search. The 14 non-search tools and their supporting code add ~2,700 unnecessary lines of code, increasing maintenance burden and violating the constitutional principle of "Simplicity Over Features". After Phase 01 used Alembic migration 002 to drop 9 database tables, the code referencing those tables must be removed to avoid errors.

---

## Clarifications

### Session 2025-10-11

- Q: During the 4 sub-phases (delete tools → delete DB ops → update registration → delete tests), should each sub-phase leave the codebase in a working state where imports succeed and tests can run, or is it acceptable for intermediate sub-phases to have broken imports that get fixed in later phases? → A: Intermediate sub-phases can have broken imports; only final state must work
- Q: If database models, utility functions, or base classes are shared between search tools and non-search tools, what should happen to them? → A: Keep shared code intact; only delete code exclusively used by non-search tools
- Q: When should we validate that search tests still pass? → A: Run search tests before starting deletions and after final sub-phase only
- Q: Should the "60% code reduction" (~4,500 to ~1,800 lines) be a functional requirement or just context? → A: Remove as functional requirement; it's a proxy metric that could drive wrong behavior
- Q: For Python, what constitutes "verified working state" after deletions complete? → A: Import checks + mypy --strict + search tests pass (comprehensive validation)

---

## User Scenarios & Testing

### Primary User Stories

**As a Maintainer**
I want non-search MCP tools removed from the server, so that I only have to maintain code relevant to semantic search functionality.

**As a User**
I want a focused MCP server with clear purpose (semantic search only), so that I understand exactly what capabilities it provides without confusion from unrelated features.

**As a Developer**
I want supporting code for removed features deleted (database operations, Pydantic models, tests), so that the codebase is clean and doesn't reference non-existent database tables.

**As a System Administrator**
I want the codebase reduced by 60% (~4,500 to ~1,800 lines), so that deployments are faster, security audits are easier, and the attack surface is smaller.

### Acceptance Scenarios

1. **Given** the server is running with 16 MCP tools, **When** the removal is complete, **Then** only 2 tools (index_repository and search_code) remain registered and functional

2. **Given** the server has supporting code for removed features, **When** cleanup is complete, **Then** no import errors occur and type checking passes with `mypy --strict`

3. **Given** the codebase contains ~4,500 lines including 14 non-search tool implementations, **When** all non-search tools and exclusive supporting code are removed, **Then** the codebase is substantially reduced (estimated 60% reduction)

4. **Given** search functionality exists before removal, **When** non-search tools are removed, **Then** all search-related tests continue to pass without modifications

5. **Given** database tables were dropped in Phase 01, **When** code cleanup is complete, **Then** no code references the deleted tables

### Edge Cases

- What happens when the server starts after tool removal? (Must start successfully with no errors)
- How does the system handle imports for deleted code? (All imports must be cleaned up)
- What if a test references removed functionality? (Test must be deleted)
- How do we ensure search functionality isn't accidentally broken? (All search tests must pass)

---

## Requirements

### Functional Requirements

#### Tools and Registration
- **FR-001**: System MUST expose exactly 2 MCP tools: index_repository and search_code
- **FR-002**: System MUST remove 14 non-search tools from registration: create_work_item, update_work_item, query_work_item, list_work_items, create_task, get_task, list_tasks, update_task, create_vendor, query_vendor_status, update_vendor_status, record_deployment, get_project_configuration, update_project_configuration
- **FR-003**: Server registration code MUST only register the 2 remaining tools

#### Code Deletion
- **FR-004**: System MUST delete 14 tool files from `src/mcp/tools/`
- **FR-005**: System MUST delete models, services, and utilities exclusively used by removed features (preserve shared code used by search tools)
- **FR-006**: System MUST delete Pydantic models exclusively used by removed features (preserve shared models used by search tools)
- **FR-007**: System MUST remove all imports referencing deleted code
- **FR-008**: System MUST delete test files for removed features

*Note: See `data-model.md` Section 1 for the complete deletion inventory (35 files total across 4 tool files, 4 model files, 5 service files, 7 utility files, 14 test files, and 1 README update).*

#### Code Quality
- **FR-009**: System MUST pass type checking with `mypy --strict` after all deletions
- **FR-010**: System MUST not add any `type: ignore` comments (or justify if absolutely necessary)
- **FR-011**: System MUST maintain valid Pydantic models for remaining features
- **FR-012**: Only search tools, their dependencies, and shared infrastructure MUST remain in src/ directory

#### Functional Preservation
- **FR-013**: index_repository tool MUST remain fully functional after cleanup
- **FR-014**: search_code tool MUST remain fully functional after cleanup
- **FR-015**: All search-related tests MUST pass before deletions begin (baseline) and after final sub-phase completes
- **FR-016**: No changes MUST be made to search algorithm or indexing logic
- **FR-017**: MCP protocol compliance MUST be maintained

#### Server Functionality
- **FR-018**: Server MUST start successfully with only 2 tools registered
- **FR-019**: Server MUST have no import errors or references to deleted code
- **FR-020**: Only search-related tests MUST remain in tests/ directory

#### Process Requirements
- **FR-021**: Deletion MUST be performed incrementally in 4 sub-phases: (1) delete tool files, (2) delete database operations, (3) update server registration, (4) delete tests
- **FR-022**: Each sub-phase MUST have its own git commit for clear history
- **FR-023**: Final working state MUST be verified with comprehensive validation: import checks + mypy --strict + search tests pass (intermediate sub-phases may have broken imports)

---

## Constraints

### Non-Negotiable Constraints

**Preserve Search Functionality**
- index_repository tool must remain fully functional
- search_code tool must remain fully functional
- No changes to search algorithm or indexing logic
- All search-related tests must continue to pass

**Type Safety**
- `mypy --strict` must pass after all deletions
- No `type: ignore` comments added (or justified if necessary)
- Pydantic models for remaining features must remain valid

**Incremental Deletion Strategy**
- Delete in 4 sub-phases (tool files, database operations, server registration, tests)
- One git commit per sub-phase for clear history
- Final working state verified after all deletions (intermediate breakage acceptable)

**No Database Changes**
- This phase only removes code, not database schema
- Database changes were completed in Phase 01

---

## Out of Scope

### Not Included in This Phase
- Multi-project feature implementation (that's Phase 03)
- Connection pool implementation (that's Phase 04)
- Documentation updates (that's Phase 05)
- Performance optimization (that's Phase 06)

### Explicitly NOT Doing
- Modifying search or indexing algorithms
- Changing remaining tool interfaces
- Database schema modifications
- Configuration changes

---

## Business Value

### Reduced Maintenance Burden
Removing 14 non-search tools and their supporting code (estimated ~60% code reduction) means fewer files to maintain, fewer dependencies to manage, fewer potential bugs, and simpler onboarding for new developers.

### Improved Security Posture
Smaller codebase means smaller attack surface. Fewer dependencies means fewer potential vulnerabilities. Security audits become faster and more thorough.

### Faster Deployments
Smaller codebase means faster Docker builds, faster deployments, faster startup time, and reduced disk space usage.

### Clearer Purpose
Removing non-search features makes the purpose crystal clear: this is a semantic code search server. No confusion about feature scope or mission creep.

### Constitutional Compliance
Aligns with Constitutional Principle #1: "Simplicity Over Features - Focus exclusively on semantic code search".

---

## Additional Context

This phase corresponds to Phases 3-6 from FINAL-IMPLEMENTATION-PLAN.md. It should take 8-12 hours to complete and depends on Phase 01 (Alembic migration 002 applied: 9 tables dropped and project_id columns added to repositories and code_chunks).

The deletion should be done incrementally in 4 sub-phases:
1. Delete tool implementation files
2. Delete database operation modules
3. Update server registration
4. Delete tests

Each sub-phase should have its own git commit for clear history and easy rollback if needed.

---

## Review & Acceptance Checklist

### Content Quality
- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

### Requirement Completeness
- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

---

## Execution Status

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked (none found - spec is complete)
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified (N/A - code removal feature)
- [x] Review checklist passed
