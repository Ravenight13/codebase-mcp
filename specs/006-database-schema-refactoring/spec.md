# Feature Specification: Database Schema Refactoring for Multi-Project Support

**Feature Branch**: `006-database-schema-refactoring`
**Created**: 2025-10-11
**Status**: Draft
**Input**: User description: "Database schema refactoring to remove unused tables and add project_id columns for multi-project support"

## Execution Flow (main)
```
1. Parse user description from Input
   → If empty: ERROR "No feature description provided"
2. Extract key concepts from description
   → Identified: database administrators, developers, security engineers, devops engineers
   → Actions: remove tables, add columns, validate, rollback
   → Data: repositories, code_chunks, project_id
   → Constraints: validation patterns, data isolation, reversibility
3. For each unclear aspect:
   → None - feature description is comprehensive
4. Fill User Scenarios & Testing section
   → User flows defined for all actor types
5. Generate Functional Requirements
   → Each requirement is testable and unambiguous
6. Identify Key Entities (if data involved)
   → Entities: Repository, CodeChunk, Project
7. Run Review Checklist
   → No [NEEDS CLARIFICATION] markers
   → No implementation details (only data model requirements)
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

---

## Clarifications

### Session 2025-10-11
- Q: What is the maximum acceptable duration for the forward migration to complete on a production-scale database? → A: < 5 minutes (acceptable for standard maintenance windows)
- Q: During migration, when the project_id column is added to code_chunks, how should existing code_chunks be assigned their project_id value? → A: Copy from parent repository (JOIN repositories ON code_chunks.repository_id)
- Q: How should foreign key constraints between the 9 tables being dropped be handled during migration? → A: Verify no foreign keys to repositories/code_chunks; others can be dropped in any order
- Q: Should the entire forward migration execute as a single transaction or multiple transactions? → A: Single atomic transaction (all-or-nothing with clean rollback)
- Q: If the forward migration fails partway through, what should the recovery procedure be? → A: Fail fast with clear error message; require explicit rollback script execution (no auto-recovery)

### Context Notes
- User plans to start fresh with workflow-mcp integration, ingesting code from scratch
- Data preservation requirements (FR-017, FR-018, FR-019) are "nice to have" but not critical since no production data exists
- Migration primarily focused on schema cleanup (drop 9 tables) and foundation for multi-project (add project_id columns)

---

## User Scenarios & Testing

### Primary User Story
As a developer working on the Codebase MCP Server, I need the database schema to reflect only the semantic search functionality we're keeping, with proper support for multiple projects through data isolation. This enables cleaner architecture and sets the foundation for multi-project features.

### Acceptance Scenarios

#### Scenario 1: Database Administrator Removes Unused Tables
1. **Given** the database contains 9 unused tables from non-search features
2. **When** the Alembic migration is executed
3. **Then** only repositories and code_chunks tables remain
4. **And** all unused tables are cleanly removed without affecting search functionality

#### Scenario 2: Developer Adds New Project
1. **Given** the database has project_id columns with validation constraints
2. **When** a developer attempts to insert data with project_id "my-project-123"
3. **Then** the data is accepted and stored successfully
4. **And** future queries can filter by this project_id

#### Scenario 3: Security Engineer Tests SQL Injection Prevention
1. **Given** the database has strict CHECK constraints on project_id
2. **When** an attacker attempts to insert project_id "'; DROP TABLE repositories; --"
3. **Then** the database rejects the value due to pattern validation
4. **And** no SQL injection occurs

#### Scenario 4: DevOps Engineer Rolls Back Migration
1. **Given** a migration has been applied to production
2. **When** an issue is discovered requiring rollback
3. **Then** the rollback script successfully restores the previous schema
4. **And** existing data is preserved (except for dropped tables which are restored from backup)

### Edge Cases
- What happens when existing repositories/code_chunks data exists during migration? (Repositories assigned to 'default' via DEFAULT value; code_chunks copy project_id from parent repository to maintain referential integrity)
- How does the system handle invalid project_id patterns at insertion? (Database CHECK constraint rejects them immediately)
- What if migration is run twice accidentally? (Script should be idempotent or error gracefully)
- How are dropped tables recovered if rollback is needed? (Only from backup created before migration)
- What if a code_chunk's parent repository doesn't exist during migration? (Migration should fail with clear error; indicates data corruption)
- What if foreign keys exist from dropped tables to repositories/code_chunks? (Migration verification check fails with clear error; tables cannot be dropped safely until references are resolved)
- What if migration fails partway through execution? (Single transaction ensures automatic rollback to pre-migration state; no partial schema changes remain; operator must investigate error, fix issue, and re-run)
- What if database connection is lost during migration? (Transaction automatically rolls back; database returns to pre-migration state; operator re-runs migration after verifying connectivity)

## Requirements

### Functional Requirements

#### Table Removal
- **FR-001**: System MUST drop exactly 9 unused tables: work_items, work_item_dependencies, tasks, task_branches, task_commits, vendors, vendor_test_results, deployments, deployment_vendors
- **FR-002**: System MUST preserve repositories and code_chunks tables with all existing data
- **FR-003**: System MUST verify no foreign key constraints exist from dropped tables pointing to repositories or code_chunks tables before dropping
- **FR-004**: System MUST support dropping the 9 tables in any order (foreign keys between dropped tables can be handled with CASCADE)

#### Project ID Column Addition
- **FR-005**: System MUST add project_id column to repositories table with type VARCHAR(50), NOT NULL constraint, and DEFAULT value 'default'
- **FR-006**: System MUST add project_id column to code_chunks table with type VARCHAR(50) and NOT NULL constraint
- **FR-007**: System MUST apply CHECK constraint on both tables: CHECK (project_id ~ '^[a-z0-9-]{1,50}$')
- **FR-008**: System MUST create database index on (project_id, repository_id) for search performance optimization

#### Pattern Validation
- **FR-009**: System MUST enforce lowercase-only project_id values (no uppercase letters)
- **FR-010**: System MUST reject project_id values containing underscores or spaces
- **FR-011**: System MUST enforce project_id length between 1 and 50 characters
- **FR-012**: System MUST reject project_id values with leading, trailing, or consecutive hyphens

#### Migration Safety
- **FR-013**: System MUST provide forward migration in migrations/versions/002_remove_non_search_tables.py with upgrade() function using Alembic framework
- **FR-014**: System MUST provide rollback in same migration file with downgrade() function for schema restoration
- **FR-015**: System MUST provide validation test suite at tests/integration/test_migration_002_validation.py using pytest framework
- **FR-016**: System MUST ensure Alembic migration is idempotent or fails gracefully if run multiple times
- **FR-017**: System MUST preserve all existing data in repositories and code_chunks tables during migration
- **FR-018**: System MUST execute forward migration as a single atomic transaction (all-or-nothing with automatic rollback on any error)
- **FR-019**: System MUST fail fast with clear error messages if migration encounters any error (no auto-recovery, require explicit rollback script execution)
- **FR-020**: System MUST log all major migration steps including table drops, column additions, data updates, constraint creations, and validation checks

#### Data Isolation Foundation
- **FR-021**: System MUST assign existing repositories (if any) to 'default' project automatically during migration via DEFAULT value
- **FR-022**: System MUST assign existing code_chunks their project_id by copying from their parent repository (JOIN on repository_id) to maintain data model integrity
- **FR-023**: System MUST provide foundation for future database-per-project architecture where each project gets database named codebase_<project_id> (foundation established in Phase 01, full implementation in Phase 03)

#### Validation Enforcement
- **FR-024**: System MUST validate project_id values at database level via CHECK constraints
- **FR-025**: System MUST reject malicious project_id values that attempt SQL injection
- **FR-026**: System MUST test validation with at least 10 invalid project_id patterns

#### Testing Requirements
- **FR-027**: Migration MUST be tested on a copy of production database before production deployment
- **FR-028**: Migration testing MUST use realistic data volume (minimum 100 repositories, 10,000 code chunks) to validate performance and correctness
- **FR-029**: Rollback script MUST be tested successfully before production deployment
- **FR-030**: All schema validation tests MUST pass after migration

#### Performance Requirements
- **FR-031**: Forward migration MUST complete within 5 minutes on production-scale database to fit standard maintenance windows

### Key Entities

- **Repository**: Represents a code repository indexed for semantic search
  - Attributes: id, path, project_id (NEW), indexed_at, metadata
  - Relationships: Contains many CodeChunks
  - Project Isolation: project_id identifies which project owns this repository

- **CodeChunk**: Represents a semantic chunk of code from a repository
  - Attributes: id, repository_id, project_id (NEW), file_path, content, start_line, end_line, embedding
  - Relationships: Belongs to one Repository
  - Project Isolation: project_id matches parent repository's project_id

- **Project**: Conceptual entity representing a distinct codebase workspace
  - Attributes: project_id (identifier following pattern ^[a-z0-9-]{1,50}$)
  - Relationships: Owns many Repositories and CodeChunks
  - Isolation: Each project's data is segregated via project_id column

---

## Review & Acceptance Checklist

### Content Quality
- [X] No implementation details (languages, frameworks, APIs)
- [X] Focused on user value and business needs
- [X] Written for non-technical stakeholders
- [X] All mandatory sections completed

### Requirement Completeness
- [X] No [NEEDS CLARIFICATION] markers remain
- [X] Requirements are testable and unambiguous
- [X] Success criteria are measurable
- [X] Scope is clearly bounded
- [X] Dependencies and assumptions identified

---

## Execution Status

- [X] User description parsed
- [X] Key concepts extracted
- [X] Ambiguities marked (none found)
- [X] User scenarios defined
- [X] Requirements generated
- [X] Entities identified
- [X] Review checklist passed

---

## Business Value

### Reduced Maintenance Burden
Removing 9 unused tables reduces database complexity by approximately 80%, making the database easier to maintain, backup, and optimize. This directly supports the constitutional principle of "Simplicity Over Features."

### Foundation for Multi-Project Support
The project_id column establishes the data foundation for multi-project functionality, enabling users to work with multiple codebases simultaneously without data contamination. This is critical for Phase 03 implementation.

### Improved Security
Strict validation on project_id through database-level CHECK constraints prevents SQL injection attacks and ensures data integrity across projects. This aligns with the constitutional principle of "Production Quality."

### Cleaner Architecture
A focused database schema containing only search-related tables creates a clearer separation of concerns and reduces the cognitive load for developers working on the system.

---

## Constraints & Assumptions

### NON-NEGOTIABLE Constraints
1. **Database Naming Strategy**: Database-per-project architecture where each project gets its own database named `codebase_<project_id>` (foundation laid in this phase, implemented in Phase 03)
2. **Pattern Validation**: project_id MUST match regex `^[a-z0-9-]{1,50}$` (enforced at database level)
3. **Data Safety**: No data loss for repositories and code_chunks tables
4. **Reversibility**: Migration must be reversible via rollback script

### Assumptions
1. Database backup exists before migration (created in Phase 00) as safety measure
2. No active connections to dropped tables at migration time
3. Existing data (if any) is minimal since user plans fresh start with workflow-mcp integration
4. Any existing repositories/code_chunks data is compatible with 'default' project_id assignment
5. Database supports regex CHECK constraints (PostgreSQL 14+ confirmed)
6. Database supports transactional DDL (PostgreSQL standard behavior)

---

## Out of Scope

### Not Included in This Phase
- Removing Python code that references dropped tables (Phase 02)
- Implementing multi-project search/indexing logic (Phase 03)
- Connection pool implementation for database-per-project (Phase 04)
- Database performance optimization beyond basic indexing (Phase 06)

### Explicitly NOT Doing
- Creating new database functionality beyond schema changes
- Modifying search or indexing algorithms
- Changing existing data in repositories/code_chunks tables (except project_id assignment)
- Adding new tables or features

---

## Dependencies

### Prerequisite Phases
- **Phase 00**: Baseline established, feature branch created, backup created

### Successor Phases (Blocked Until This Completes)
- **Phase 02**: Tool removal (requires database changes to be complete)
- **Phase 03**: Multi-project support (requires project_id foundation)

---

## Additional Context

This feature corresponds to Phase 01 (originally labeled Phase 2) from FINAL-IMPLEMENTATION-PLAN.md in the multi-project refactor plan. It is estimated to take 4-6 hours to complete.

The migration strategy prioritizes safety and reversibility. While forward migration removes tables permanently, the rollback script can restore schema structure (but not data in dropped tables unless backup is restored).

This phase is intentionally narrow in scope - it only modifies the database schema. All code changes to use the new schema are handled in subsequent phases.
