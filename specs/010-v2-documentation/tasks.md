---
description: "Task list for v2.0 documentation overhaul with migration guide"
---

# Tasks: Documentation Overhaul & Migration Guide for v2.0 Architecture

**Input**: Design documents from `/specs/010-v2-documentation/`
**Prerequisites**: plan.md (completed), spec.md (completed), research.md (completed), data-model.md (completed), contracts/documentation-structure.yaml (completed), quickstart.md (completed)

**Tests**: Manual validation procedures only (FR-032, FR-033). Automated testing deferred to Phase 07.

**Organization**: Tasks are grouped by user story priority to enable independent documentation authoring and validation of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4, US5)
- Include exact file paths in descriptions

## Path Conventions
- Documentation root: `docs/`
- README: `README.md` (repository root)
- Glossary: `docs/glossary.md`
- Migration: `docs/migration/`
- Configuration: `docs/configuration/`
- Architecture: `docs/architecture/`
- API Reference: `docs/api/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create directory structure and shared resources for all documentation artifacts

**Duration Estimate**: 2-3 hours

- [X] T001 Create documentation directory structure (docs/migration/, docs/configuration/, docs/architecture/, docs/api/)
- [X] T002 [P] Create glossary.md with 6 canonical terms (project_id, connection pool, LRU eviction, database-per-project, workflow-mcp integration, default project) - FR-034
- [X] T003 [P] Create markdown style guide document with formatting conventions (code blocks, heading hierarchy, table formatting, file naming) - FR-035

**Checkpoint**: Directory structure and shared resources ready for artifact authoring

---

## Phase 2: Foundational (Common Sections)

**Purpose**: Sections shared across multiple documentation artifacts

**Duration Estimate**: 3-4 hours

**⚠️ CRITICAL**: These sections are referenced by multiple user stories and must be complete before artifact-specific work

- [X] T004 [P] Document all 14 removed tools with names and categories in shared reference (for Migration Guide and API Reference) - FR-010, FR-008
- [X] T005 [P] Document new environment variables table (8-10 variables with defaults) for Configuration Guide - FR-013, FR-021
- [X] T006 [P] Create connection pool calculation formula with 3-5 example scenarios - FR-024

**Checkpoint**: Common sections ready for inclusion in multiple artifacts

---

## Phase 3: User Story 1 (P1) - Existing User Upgrades from v1.x 🎯 MVP

**Goal**: Enable safe production upgrades with clear migration guidance

**Independent Test**: Follow migration guide with v1.x installation, verify successful upgrade to v2.0 with rollback capability

**Priority Rationale**: Highest priority - existing users face breaking changes that could cause production issues without clear migration guidance

### Validation for User Story 1 (Perform BEFORE authoring)

**NOTE: Review validation procedures in quickstart.md BEFORE writing content to understand success criteria**

- [ ] T007 [US1] Review quickstart.md Test Scenario 3 (Migration Guide Validation) - understand validation requirements before authoring

### Implementation for User Story 1

**File**: `docs/migration/v1-to-v2-migration.md`

- [ ] T008 [US1] Write Migration Guide: Title and Overview section (purpose, scope, target audience, data preservation policy) - FR-019
- [ ] T009 [US1] Write Migration Guide: Breaking Changes Summary section (upfront before procedures) - FR-009
  - Tool API Changes subsection (14 tools removed, 2 tools modified) - FR-010, FR-012
  - Database Schema Changes subsection (9 tables dropped, project_id added) - FR-011
  - Environment Variable Changes subsection (new required variables) - FR-013
  - Data Preservation Policy callout (repositories preserved, v1.x data discarded) - FR-019
- [ ] T010 [US1] Write Migration Guide: Removed Tools List section with all 14 tools by name - FR-010
  - Removed Project Management Tools (4 tools): create_project, switch_project, get_active_project, list_projects
  - Removed Entity Management Tools (6 tools): register_entity_type, create_entity, query_entities, update_entity, delete_entity, update_entity_type_schema
  - Removed Work Item Management Tools (4 tools): create_work_item, update_work_item, query_work_items, get_work_item_hierarchy
- [ ] T011 [US1] Write Migration Guide: Prerequisites section (v1.x running, PostgreSQL access, disk space, downtime window)
- [ ] T012 [US1] Write Migration Guide: Pre-Migration Checklist section (review breaking changes, verify versions, test rollback in non-prod)
- [ ] T013 [US1] Write Migration Guide: Backup Procedures section with exact commands - FR-015
  - Database Backup subsection with pg_dump command
  - Configuration Backup subsection with cp command
  - Verification steps for backups
- [ ] T014 [US1] Write Migration Guide: Upgrade Procedure section with 6 step-by-step instructions - FR-014, FR-018
  - Step 1: Stop v1.x Server (command, validation)
  - Step 2: Update Dependencies (command, validation)
  - Step 3: Run Migration Script (command, expected output) - FR-018
  - Step 4: Update Configuration (new env vars, changed defaults)
  - Step 5: Restart Server (command, validation)
  - Step 6: Verify Migration Success (validation commands), optional: document checkpoint resume if migration script supports it (FR-037 SHOULD requirement)
- [ ] T015 [US1] Write Migration Guide: Post-Migration Validation section - FR-017
  - Verify v2.0 Functionality subsection (test index_repository, test search_code)
  - Verify Existing Repositories Searchable subsection
- [ ] T016 [US1] Write Migration Guide: Diagnostic Commands section with SQL queries - FR-036
  - Check v2.0 schema present query
  - Verify v1.x tables dropped query
  - Detect partial migration state queries
- [ ] T017 [US1] Write Migration Guide: Rollback Procedure section with complete restoration - FR-016
  - When to Roll Back guidance
  - Rollback Steps (6 steps mirroring upgrade procedure)
  - Rollback Validation subsection - FR-017
- [ ] T018 [US1] Write Migration Guide: Troubleshooting section
  - Common Issues: Migration script fails midway, Missing env vars, PostgreSQL connection errors, Data validation failures
  - Support Resources: GitHub Issues, Discussion forum links
- [ ] T019 [US1] Write Migration Guide: FAQ section
  - What data is lost during migration?
  - Can I migrate incrementally?
  - How long does migration take? (See FR-020 in spec.md - timing guidance deferred to Phase 06 performance testing)

### Manual Validation for User Story 1

- [ ] T020 [US1] Validate Migration Guide: Test backup procedures with v1.x environment (quickstart.md Step 2)
- [ ] T021 [US1] Validate Migration Guide: Test upgrade procedure end-to-end with v1.x to v2.0 (quickstart.md Step 3)
- [ ] T022 [US1] Validate Migration Guide: Test post-migration validation commands (quickstart.md Step 4)
- [ ] T023 [US1] Validate Migration Guide: Test rollback procedure with v1.x restoration (quickstart.md Step 5)
- [ ] T024 [US1] Validate Migration Guide: Test diagnostic commands for partial migration detection (quickstart.md Step 7)
- [ ] T025 [US1] Validate Migration Guide: Verify all 14 removed tools listed by name - SC-002
- [ ] T026 [US1] Validate Migration Guide: Verify breaking changes documented upfront before procedures - FR-009

**Checkpoint**: User Story 1 (Migration Guide) complete and validated - MVP ready for existing users upgrading from v1.x

---

## Phase 4: User Story 2 (P2) - New User First-Time Installation

**Goal**: Enable rapid onboarding (15 minutes to first index and search)

**Independent Test**: Follow README installation with no prior codebase-mcp installation, complete first index and search successfully

**Priority Rationale**: New user adoption drives ecosystem growth, accurate documentation accelerates onboarding

### Validation for User Story 2 (Perform BEFORE authoring)

- [ ] T027 [US2] Review quickstart.md Test Scenario 2 (Code Example Testing) - understand example validation requirements

### Implementation for User Story 2

**File**: `README.md`

- [ ] T028 [US2] Write README: Title and Description (1-2 sentences) - project title with brief description
- [ ] T029 [US2] Write README: What's New in v2.0 section - breaking changes summary with link to migration guide (docs/migration/v1-to-v2-migration.md)
- [ ] T030 [US2] Write README: Features section - list exactly 2 tools (index_repository, search_code) with multi-project support explanation - FR-001, FR-002
- [ ] T031 [US2] Write README: Installation section - FR-004
  - Prerequisites subsection (PostgreSQL 14+, Python 3.11+, Ollama)
  - Installation Commands subsection (pip install command)
  - Verification Steps subsection (verify installation successful)
- [ ] T032 [US2] Write README: Quick Start section with 2 examples - FR-002
  - Basic Usage (Default Project) subsection with example command
  - Multi-Project Usage subsection with project_id parameter example
- [ ] T033 [US2] Write README: workflow-mcp Integration (Optional) section - FR-003
  - Mark workflow-mcp as optional feature
  - Document standalone usage first
  - Provide integration example with WORKFLOW_MCP_URL
  - Document fallback behavior to default project
- [ ] T034 [US2] Write README: Documentation section with links to 4 specialized guides
  - Link to Migration Guide (docs/migration/v1-to-v2-migration.md)
  - Link to Configuration Guide (docs/configuration/production-config.md)
  - Link to Architecture Docs (docs/architecture/multi-project-design.md)
  - Link to API Reference (docs/api/tool-reference.md)
- [ ] T035 [US2] Write README: Contributing section with link to architecture docs for maintainers

### Manual Validation for User Story 2

- [ ] T036 [US2] Validate README: Test installation commands (pip install) - quickstart.md Step 3
- [ ] T037 [US2] Validate README: Test Quick Start basic usage example - quickstart.md Step 3
- [ ] T038 [US2] Validate README: Test Quick Start multi-project usage example - quickstart.md Step 3
- [ ] T039 [US2] Validate README: Verify exactly 2 tools documented (index_repository, search_code) - SC-001, FR-001
- [ ] T040 [US2] Validate README: Verify multi-project support explanation present - FR-002
- [ ] T041 [US2] Validate README: Verify workflow-mcp marked optional with standalone usage first - FR-003

**Checkpoint**: User Story 2 (README for new users) complete and validated - new users can install and use within 15 minutes

---

## Phase 5: User Story 3 (P2) - Administrator Configures Production Deployment

**Goal**: Enable optimal production deployments with correct configuration

**Independent Test**: Follow configuration guide in staging environment with correct PostgreSQL tuning and connection pool settings validated

**Priority Rationale**: Misconfigured production deployments lead to performance issues, proper configuration documentation prevents these problems

### Validation for User Story 3 (Perform BEFORE authoring)

- [ ] T042 [US3] Review quickstart.md Test Scenario 4 (Configuration Guide Validation) - understand staging environment validation requirements

### Implementation for User Story 3

**File**: `docs/configuration/production-config.md`

- [ ] T043 [US3] Write Configuration Guide: Title and Overview section (purpose, quick links to major sections)
- [ ] T044 [US3] Write Configuration Guide: Environment Variables Reference section with tables - FR-021
  - Core Configuration subsection (DATABASE_URL, OLLAMA_BASE_URL, EMBEDDING_MODEL) with table format
  - Multi-Project Configuration subsection (MAX_PROJECTS, MAX_CONNECTIONS_PER_POOL, PROJECT_POOL_TIMEOUT) with table format
  - workflow-mcp Integration subsection (WORKFLOW_MCP_URL, WORKFLOW_MCP_TIMEOUT) with table format - FR-026
  - Table columns: Variable, Required, Default, Description, Example
- [ ] T045 [US3] Write Configuration Guide: Connection Pool Tuning section - FR-022, FR-023
  - Understanding the Calculation subsection with formula - FR-024
  - Example Scenarios table (Small/Medium/Large Deployment)
  - PostgreSQL max_connections Requirement subsection with formula and buffer explanation - FR-024
  - Configuration Validation commands (check current max_connections)
  - Tuning MAX_PROJECTS subsection with tradeoffs (✅ higher/lower, ❌ higher/lower) - FR-022
  - Tuning MAX_CONNECTIONS_PER_POOL subsection with tradeoffs - FR-023
  - Recommendations for different deployment sizes
- [ ] T046 [US3] Write Configuration Guide: PostgreSQL Configuration section - FR-025
  - Production Tuning Parameters subsection with postgresql.conf settings (max_connections, shared_buffers, effective_cache_size, work_mem, etc.)
  - Rationale for Settings subsection explaining why each setting matters for codebase-mcp workload
- [ ] T047 [US3] Write Configuration Guide: Monitoring & Health Checks section - FR-038
  - Key Indicators subsection (active pool count, connections per pool, pool eviction frequency, query latency)
  - Monitoring Queries subsection with SQL queries (active databases, connection count per database, total connections)
  - Health Check Endpoints subsection (document any health check endpoints if they exist)
- [ ] T048 [US3] Write Configuration Guide: Configuration Validation Checklist section with commands - FR-027 (DATABASE_URL connects, OLLAMA_BASE_URL responds, embedding model available, PostgreSQL max_connections sufficient, MAX_PROJECTS × MAX_CONNECTIONS_PER_POOL calculation valid, workflow-mcp URL reachable if configured, connection pool creation successful, indexing test completes)
- [ ] T049 [US3] Write Configuration Guide: Troubleshooting section
  - "Too many connections" error (symptom, cause, solution)
  - Slow query performance (symptom, cause, solution)
  - Frequent pool evictions (symptom, cause, solution)

### Manual Validation for User Story 3

- [ ] T050 [US3] Validate Configuration Guide: Test environment variable examples in staging (quickstart.md Step 1)
- [ ] T051 [US3] Validate Configuration Guide: Test connection calculation examples (quickstart.md Step 2)
- [ ] T052 [US3] Validate Configuration Guide: Test PostgreSQL tuning examples in staging (quickstart.md Step 3)
- [ ] T053 [US3] Validate Configuration Guide: Test validation checklist commands (quickstart.md Step 4)
- [ ] T054 [US3] Validate Configuration Guide: Test monitoring queries (quickstart.md Step 5)
- [ ] T055 [US3] Validate Configuration Guide: Verify all environment variables documented with defaults - SC-006, FR-021
- [ ] T056 [US3] Validate Configuration Guide: Verify MAX_PROJECTS tradeoffs documented - FR-022
- [ ] T057 [US3] Validate Configuration Guide: Verify MAX_CONNECTIONS_PER_POOL tradeoffs documented - FR-023
- [ ] T058 [US3] Validate Configuration Guide: Test monitoring queries from quickstart.md Scenario 4 Step 5 - FR-038

**Checkpoint**: User Story 3 (Configuration Guide) complete and validated - administrators can deploy to production with correct configuration

---

## Phase 6: User Story 4 (P3) - Developer Integrates workflow-mcp

**Goal**: Enable workflow-mcp integration for automatic project detection

**Independent Test**: Follow integration documentation to configure workflow-mcp connection and verify automatic project detection works

**Priority Rationale**: workflow-mcp integration is optional and serves advanced use cases, not required for basic usage

### Validation for User Story 4 (Perform BEFORE authoring)

- [ ] T059 [US4] Review quickstart.md Test Scenario 2 (Code Example Testing) for integration examples

### Implementation for User Story 4

**File**: `docs/api/tool-reference.md`

- [ ] T060 [P] [US4] Write API Reference: Title and Overview section - list exactly 2 tools with breaking changes callout
- [ ] T061 [P] [US4] Write API Reference: index_repository section - FR-005
  - Parameters table (repo_path, project_id, force_reindex)
  - Parameter Details subsections with project_id default behavior and workflow-mcp auto-resolution
  - Return Value subsection (JSON schema + table)
  - Examples subsections (basic, multi-project, force re-index)
  - Error Handling table
- [ ] T062 [P] [US4] Write API Reference: search_code section - FR-006
  - Parameters table (query, project_id, repository_id, file_type, directory, limit)
  - Parameter Details subsections with project_id default behavior and workflow-mcp auto-resolution
  - Return Value subsection (JSON schema + table with Result Object details)
  - Examples subsections (basic, multi-project, filtered)
  - Error Handling table
- [ ] T063 [US4] Write API Reference: Removed Tools section - FR-007, FR-008
  - List all 14 tools by name with ❌ "Removed in v2.0" notation
  - Removed Project Management Tools subsection (4 tools)
  - Removed Entity Management Tools subsection (6 tools)
  - Removed Work Item Management Tools subsection (4 tools)
  - Link to workflow-mcp as alternative
  - Link to migration guide for upgrade instructions
- [ ] T064 [P] [US4] Write API Reference: Tool Discovery section (MCP tool discovery via SSE, JSON schema validation)

### Manual Validation for User Story 4

- [ ] T065 [US4] Validate API Reference: Test index_repository JSON examples - quickstart.md Step 5
- [ ] T066 [US4] Validate API Reference: Test search_code JSON examples - quickstart.md Step 5
- [ ] T067 [US4] Validate API Reference: Test tool invocation with MCP client (if available)
- [ ] T068 [US4] Validate API Reference: Verify exactly 2 tools documented - SC-001
- [ ] T069 [US4] Validate API Reference: Verify all 14 removed tools listed by name - SC-002, FR-007, FR-008
- [ ] T070 [US4] Validate API Reference: Verify project_id parameter default behavior documented - FR-005, FR-006

**Checkpoint**: User Story 4 (API Reference) complete and validated - developers can integrate workflow-mcp using API documentation

---

## Phase 7: User Story 5 (P3) - Maintainer Contributes to Project

**Goal**: Enable contributors to understand architecture and make meaningful contributions

**Independent Test**: Follow contributor documentation to set up development environment and understand architecture well enough to make contributions

**Priority Rationale**: Maintainer documentation supports long-term sustainability but doesn't block user adoption

### Implementation for User Story 5

**File**: `docs/architecture/multi-project-design.md`

- [ ] T071 [P] [US5] Write Architecture Docs: Title and Overview section (high-level description of system components and design philosophy)
- [ ] T072 [P] [US5] Write Architecture Docs: Multi-Project Architecture Diagram section - FR-028
  - Mermaid graph TB diagram showing: MCP Client, codebase-mcp Server, Connection Pool Manager, workflow-mcp Server (optional), PostgreSQL databases
  - Component Responsibilities subsection explaining each component's role
- [ ] T073 [US5] Write Architecture Docs: Database-Per-Project Strategy section - FR-029
  - Design Decision subsection with naming convention: codebase_{sanitized_project_id}
  - Examples table with 5-10 examples (default, my-app, frontend.ui, client_a, etc.) showing sanitization rules
  - Sanitization Rules subsection (non-alphanumeric → underscore, lowercase, max length 54 chars)
  - Rationale subsection (schema independence, query performance, data locality, backup granularity, multi-tenancy, resource limits)
  - Tradeoffs subsection (pros and cons)
  - Schema Structure subsection with simplified SQL schema
- [ ] T074 [US5] Write Architecture Docs: Connection Pool Design section - FR-030
  - Pool Lifecycle subsection with Mermaid stateDiagram-v2 (Uninitialized → Creating → Active → Idle → Evicted)
  - State Descriptions subsection
  - LRU Eviction Policy subsection with example timeline
  - Performance Implications subsection (pool creation time, eviction time, frequent eviction indicators)
  - Connection Pool Configuration subsection (min connections, max connections, timeout, idle timeout)
  - Concurrency Example subsection
- [ ] T075 [US5] Write Architecture Docs: workflow-mcp Integration Architecture section - FR-031
  - Mermaid sequenceDiagram showing integration points and fallback behavior
  - Integration Behavior subsection (5 steps: project_id provided, workflow-mcp call, response, timeout, fallback)
  - Fallback Rationale subsection (local-first architecture, no external dependencies, graceful degradation)
- [ ] T076 [US5] Write Architecture Docs: Component Interactions section
  - Indexing Flow subsection (ASCII flow diagram)
  - Search Flow subsection (ASCII flow diagram)
- [ ] T077 [US5] Write Architecture Docs: Design Rationale Summary section
  - Why Multi-Project Architecture?
  - Why Database-Per-Project?
  - Why Connection Pool Manager?
  - Why Optional workflow-mcp?

### Manual Validation for User Story 5

- [ ] T078 [US5] Validate Architecture Docs: Verify Mermaid diagrams render correctly in GitHub
- [ ] T079 [US5] Validate Architecture Docs: Verify database naming examples accurate - FR-029
- [ ] T080 [US5] Validate Architecture Docs: Verify LRU eviction explanation with timeline example - FR-030
- [ ] T081 [US5] Validate Architecture Docs: Test workflow-mcp integration sequence with live workflow-mcp instance (optional if workflow-mcp unavailable) - FR-031

**Checkpoint**: User Story 5 (Architecture Docs) complete and validated - maintainers can understand architecture and contribute confidently

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Cross-artifact consistency, final validation, and quality assurance

**Duration Estimate**: 4-6 hours

### Cross-Artifact Validation

- [ ] T082 [P] Validate All Docs: Run link verification procedure (quickstart.md Scenario 1) - create link inventory spreadsheet - FR-032
- [ ] T083 [P] Validate All Docs: Run code example testing procedure (quickstart.md Scenario 2) - create code example test log - FR-033
- [ ] T084 Validate All Docs: Run cross-artifact consistency check (quickstart.md Scenario 5) - FR-034, FR-035
  - Terminology consistency check (6 glossary terms)
  - Abbreviation check (LRU, MCP, SSE)
  - Markdown style guide check (code blocks, heading hierarchy, table formatting, file naming)
  - Cross-reference consistency check (tool count, removed tools list, env vars, project_id behavior)
  - Link cross-reference check (bidirectional links between artifacts)

### Deliverables & Quality Metrics

- [ ] T085 Prepare link inventory spreadsheet deliverable with 100% pass rate - SC-003
- [ ] T086 Prepare code example test log deliverable with 100% pass rate - SC-004
- [ ] T087 Verify all 38 functional requirements addressed in documentation
- [ ] T088 Verify all 11 edge cases addressed in relevant docs
- [ ] T089 Verify all 5 user personas served (README, migration, config, architecture, API reference)

### Final Review

- [ ] T090 Final consistency pass: Verify exactly 2 tools documented throughout (no other tools mentioned) - SC-001
- [ ] T091 Final consistency pass: Verify all 14 removed tools documented in both Migration Guide and API Reference - SC-002
- [ ] T092 Final consistency pass: Verify 0 broken links across all artifacts - SC-003
- [ ] T093 Final consistency pass: Verify 100% of code examples tested successfully - SC-004
- [ ] T094 Final consistency pass: Verify 100% of breaking changes mapped to migration steps - SC-005
- [ ] T095 Final consistency pass: Verify 100% of environment variables documented with defaults - SC-006

### Review and Approval

- [ ] T096 Author: Mark all documentation artifacts as reviewed status (ready for peer review)
- [ ] T097 Peer Reviewer: Spot-check 20% of links (link inventory spreadsheet)
- [ ] T098 Peer Reviewer: Spot-check 20% of code examples (code example test log)
- [ ] T099 Peer Reviewer: Run full migration guide test in separate environment (quickstart.md Scenario 3)
- [ ] T100 Peer Reviewer: Approve all documentation artifacts (reviewed → approved status)
- [ ] T101 Final: Prepare PR with master validation checklist (quickstart.md) and commit documentation artifacts

**Checkpoint**: All documentation complete, validated, and ready for publication (merge to main branch)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) completion - provides shared resources
- **User Stories (Phase 3-7)**: All depend on Foundational (Phase 2) completion
  - User stories can proceed in priority order: US1 (P1) → US2 (P2) → US3 (P2) → US4 (P3) → US5 (P3)
  - US2 and US3 can run in parallel (both P2, different files)
  - US4 and US5 can run in parallel (both P3, different files)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1) - Migration Guide**: Can start after Foundational (Phase 2) - No dependencies on other stories - HIGHEST PRIORITY, MUST COMPLETE FIRST
- **User Story 2 (P2) - README**: Can start after Foundational (Phase 2) - May reference Migration Guide (US1) but independently testable
- **User Story 3 (P2) - Configuration Guide**: Can start after Foundational (Phase 2) - May reference Migration Guide (US1) for env vars but independently testable
- **User Story 4 (P3) - API Reference**: Can start after Foundational (Phase 2) - References removed tools list from US1 but independently testable
- **User Story 5 (P3) - Architecture Docs**: Can start after Foundational (Phase 2) - No dependencies on other stories

### Within Each User Story

- Review validation procedures BEFORE authoring (understand success criteria)
- Write content sections in order (follow contract structure)
- Validate content AFTER authoring (manual testing procedures)
- Complete all validation tasks before marking story complete

### Parallel Opportunities

- **Phase 1 Setup**: T002 and T003 can run in parallel (glossary and style guide are independent)
- **Phase 2 Foundational**: T004, T005, and T006 can run in parallel (shared sections for different artifacts)
- **Phase 3 (US1)**: Within Migration Guide, some sections can be written in parallel once structure is defined
- **Phase 4 and Phase 5**: US2 (README) and US3 (Configuration Guide) can run in parallel - both P2 priority, different files
- **Phase 6 and Phase 7**: US4 (API Reference) and US5 (Architecture Docs) can run in parallel - both P3 priority, different files
  - Within API Reference (US4): T060, T061, T062, T064 can run in parallel (different tool sections)
  - Within Architecture Docs (US5): T071, T072 can run in parallel (overview and diagrams are independent)
- **Phase 8 Polish**: T082 and T083 can run in parallel (link verification and code example testing are independent validation procedures)

---

## Parallel Example: Phase 4 and Phase 5 (P2 User Stories)

```bash
# Both P2 user stories can proceed in parallel with different team members:

Developer A (User Story 2 - README):
Task T028: "Write README: Title and Description"
Task T029: "Write README: What's New in v2.0 section"
...
Task T041: "Validate README: Verify workflow-mcp marked optional"

Developer B (User Story 3 - Configuration Guide):
Task T043: "Write Configuration Guide: Title and Overview"
Task T044: "Write Configuration Guide: Environment Variables Reference"
...
Task T058: "Validate Configuration Guide: Test monitoring queries"
```

---

## Parallel Example: Phase 6 and Phase 7 (P3 User Stories)

```bash
# Both P3 user stories can proceed in parallel with different team members:

Developer A (User Story 4 - API Reference):
Task T059: "Review quickstart.md Test Scenario 2"
Task T060: "Write API Reference: Title and Overview"
Task T061: "Write API Reference: index_repository section"
Task T062: "Write API Reference: search_code section"
...
Task T070: "Validate API Reference: Verify project_id default behavior"

Developer B (User Story 5 - Architecture Docs):
Task T071: "Write Architecture Docs: Title and Overview"
Task T072: "Write Architecture Docs: Multi-Project Architecture Diagram"
...
Task T081: "Validate Architecture Docs: Test workflow-mcp integration sequence"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only) - RECOMMENDED

1. Complete Phase 1: Setup (T001-T003) → ~2-3 hours
2. Complete Phase 2: Foundational (T004-T006) → ~3-4 hours
3. Complete Phase 3: User Story 1 - Migration Guide (T007-T026) → ~10-12 hours
4. **STOP and VALIDATE**: Test Migration Guide with v1.x environment (quickstart.md Scenario 3)
5. Deliver Migration Guide to existing users upgrading from v1.x (HIGHEST PRIORITY)

**Rationale**: US1 is P1 (highest priority) because existing users face breaking changes. Delivering migration guide first enables safe production upgrades while other documentation is authored.

### Incremental Delivery (By Priority)

1. Complete Setup + Foundational (Phase 1-2) → ~5-7 hours
2. Add User Story 1 (P1) - Migration Guide (Phase 3) → Test independently → ~10-12 hours → **DELIVER MVP**
3. Add User Story 2 (P2) - README (Phase 4) → Test independently → ~6-8 hours → **DELIVER for new users**
4. Add User Story 3 (P2) - Configuration Guide (Phase 5) → Test independently → ~8-10 hours → **DELIVER for administrators**
5. Add User Story 4 (P3) - API Reference (Phase 6) → Test independently → ~6-8 hours → **DELIVER for developers**
6. Add User Story 5 (P3) - Architecture Docs (Phase 7) → Test independently → ~6-8 hours → **DELIVER for maintainers**
7. Add Polish (Phase 8) → Final validation and consistency → ~4-6 hours → **COMPLETE documentation overhaul**

**Total Estimated Duration**: ~45-60 hours for complete documentation overhaul across all 5 user stories

### Parallel Team Strategy (If Multiple Authors Available)

With multiple documentation authors:

1. Team completes Setup + Foundational together (Phase 1-2) → ~5-7 hours
2. Once Foundational is done:
   - **Author A (Priority)**: User Story 1 (P1) - Migration Guide → ~10-12 hours
   - Wait for US1 complete before starting US2/US3 (US2 and US3 reference migration guide)
3. After US1 complete:
   - **Author A**: User Story 2 (P2) - README → ~6-8 hours
   - **Author B**: User Story 3 (P2) - Configuration Guide → ~8-10 hours
   - (US2 and US3 run in parallel)
4. After US2 and US3 complete:
   - **Author A**: User Story 4 (P3) - API Reference → ~6-8 hours
   - **Author B**: User Story 5 (P3) - Architecture Docs → ~6-8 hours
   - (US4 and US5 run in parallel)
5. Team performs Polish together (Phase 8) → ~4-6 hours

**Total Duration with 2 Authors**: ~35-45 hours (wall-clock time with parallelization)

---

## Notes

### Documentation-Specific Guidance

- **[P] tasks**: Different files or sections, can be authored in parallel without conflicts
- **[Story] label**: Maps task to specific user story for traceability to spec.md requirements
- **Manual validation**: All validation is manual (FR-032, FR-033). Automated testing deferred to Phase 07.
- **Validation BEFORE implementation**: Review quickstart.md validation procedures before authoring to understand success criteria
- **No code changes**: Phase 05 is documentation-only. No source code modifications permitted.

### File Organization

- **5 documentation artifacts**: README.md (US2), docs/migration/v1-to-v2-migration.md (US1), docs/configuration/production-config.md (US3), docs/architecture/multi-project-design.md (US5), docs/api/tool-reference.md (US4)
- **Shared resources**: docs/glossary.md (FR-034), markdown style guide (FR-035)
- **Validation deliverables**: Link inventory spreadsheet (FR-032), code example test log (FR-033), consistency check report

### Success Criteria Alignment

- **SC-001**: 100% tool names match (2 tools) - validated in T039, T067, T089
- **SC-002**: 100% removed tools documented (14 tools) - validated in T025, T068, T090
- **SC-003**: 0 broken links - validated in T081, T084, T091
- **SC-004**: 100% code examples tested - validated in T082, T085, T092
- **SC-005**: 100% breaking changes mapped - validated in T093
- **SC-006**: 100% env vars documented - validated in T055, T094

### Quality Assurance

- **Master validation checklist**: quickstart.md contains 5 comprehensive test scenarios
- **Peer review required**: Separate reviewer validates 20% of links/examples and runs full migration test
- **Constitutional compliance**: Simplicity Over Features (documentation-only scope), Local-First Architecture (documents local system), Production Quality (comprehensive migration and configuration docs)

### Commit Strategy

- Commit after each user story phase completion (US1 → commit, US2 → commit, etc.)
- Include validation deliverables in commits (link inventory, test log)
- Use Conventional Commits format: `docs(US1): write migration guide breaking changes section`
- Final commit includes all artifacts and validation reports before PR submission

### Avoid

- Vague tasks (all tasks have specific file paths and section names)
- Cross-story dependencies that break independence (each user story is independently testable)
- Automated testing (explicitly deferred to Phase 07 per FR-032/FR-033)
- Code changes (Phase 05 is documentation-only per Non-Goals)
- Placeholder text (no "TODO", "[FILL IN]", etc. in final documentation)
