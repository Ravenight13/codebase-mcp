# Implementation Plan: Database Schema Refactoring for Multi-Project Support

**Branch**: `006-database-schema-refactoring` | **Date**: 2025-10-11 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/Users/cliffclarke/Claude_Code/codebase-mcp/specs/006-database-schema-refactoring/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → ✅ COMPLETE: Spec loaded successfully
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → ✅ COMPLETE: Context filled, single Python project detected
3. Fill the Constitution Check section based on the content of the constitution document.
   → IN PROGRESS
4. Evaluate Constitution Check section below
   → PENDING
5. Execute Phase 0 → research.md
   → PENDING
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, CLAUDE.md
   → PENDING
7. Re-evaluate Constitution Check section
   → PENDING
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
   → PENDING
9. STOP - Ready for /tasks command
   → PENDING
```

**IMPORTANT**: The /plan command STOPS at step 8. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary

Refactor the Codebase MCP Server database schema to remove 9 unused tables from non-search features (work tracking, vendor management, deployments) and add `project_id` columns to `repositories` and `code_chunks` tables. This establishes the foundation for multi-project support (Phase 03) while simplifying the database to focus exclusively on semantic code search functionality.

**Key Technical Approach**:
- Alembic migration with atomic transaction execution
- Database-level validation via CHECK constraints (regex pattern `^[a-z0-9-]{1,50}$`)
- Referential integrity preservation (code_chunks copy project_id from parent repository)
- Performance target: < 5 minutes migration duration
- Safety: Single transaction with automatic rollback, comprehensive logging

## Technical Context

**Language/Version**: Python 3.11+ (confirmed in constitution)
**Primary Dependencies**: PostgreSQL 14+ with pgvector, SQLAlchemy (async), psycopg2/asyncpg
**Storage**: PostgreSQL 14+ (existing database, migration-based schema changes)
**Testing**: pytest with contract tests, integration tests, performance validation
**Target Platform**: Linux/macOS server (local-first architecture)
**Project Type**: Single Python project (MCP server)
**Performance Goals**: Migration < 5 minutes, no impact to search query performance (< 500ms p95)
**Constraints**:
- Single atomic transaction (all-or-nothing rollback)
- Zero data loss for repositories/code_chunks
- Database-level validation enforcement
- Transactional DDL support (PostgreSQL standard)
**Scale/Scope**:
- Testing: 100 repositories, 10,000 code chunks minimum
- Production: Supports fresh start with workflow-mcp integration
- 9 tables dropped, 2 tables modified, 3 SQL scripts created

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Simplicity Over Features
**Status**: ✅ PASS
- **Rationale**: This feature REMOVES complexity (9 unused tables) while adding minimal foundation (project_id columns) for future multi-project support. Directly serves the "Simplicity Over Features" principle by cleaning up schema cruft.

### Principle II: Local-First Architecture
**Status**: ✅ PASS
- **Rationale**: Database migration is purely local. No cloud dependencies, no external API calls. PostgreSQL remains the single source of truth.

### Principle III: Protocol Compliance (MCP via SSE)
**Status**: ✅ PASS
- **Rationale**: Schema changes are orthogonal to MCP protocol. No changes to protocol communication, logging remains file-based (`/tmp/codebase-mcp.log`).

### Principle IV: Performance Guarantees
**Status**: ✅ PASS (with monitoring)
- **Rationale**:
  - Migration performance explicitly specified (< 5 minutes - FR-031)
  - Index added on (project_id, repository_id) for search performance (FR-008)
  - No degradation to existing 500ms search p95 target (verified through testing)

### Principle V: Production Quality Standards
**Status**: ✅ PASS
- **Rationale**:
  - Comprehensive error handling: Single transaction with automatic rollback (FR-018)
  - Clear error messages: Fail fast with explicit errors (FR-019)
  - Logging: All major migration steps logged (FR-020)
  - Validation: CHECK constraints at database level (FR-024)
  - Testing: Requires testing on database copy before production (FR-027)

### Principle VI: Specification-First Development
**Status**: ✅ PASS
- **Rationale**: Spec completed with clarifications before planning. 31 functional requirements defined with measurable acceptance criteria.

### Principle VII: Test-Driven Development
**Status**: ✅ PASS
- **Rationale**: Migration requires validation script (FR-015), schema validation tests (FR-030), and rollback testing (FR-029). Tests verify correctness before and after migration.

### Principle VIII: Pydantic-Based Type Safety
**Status**: ✅ PASS (post-migration)
- **Rationale**: While Alembic migrations don't use Pydantic directly, Phase 02 will update Pydantic models (Repository, CodeChunk) to include project_id field with validation. This phase lays database foundation.

### Principle IX: Orchestrated Subagent Execution
**Status**: ✅ PASS
- **Rationale**: Implementation phase (Phase 02+) will use subagents for parallel test writing and script creation where appropriate.

### Principle X: Git Micro-Commit Strategy
**Status**: ✅ PASS
- **Rationale**: Feature branch `006-database-schema-refactoring` already created. Implementation will use micro-commits per task with Conventional Commits format.

### Principle XI: FastMCP and Python SDK Foundation
**Status**: ✅ PASS (no changes required)
- **Rationale**: Schema changes don't affect FastMCP tool registration. MCP server continues using FastMCP decorators unchanged.

**Initial Assessment**: NO VIOLATIONS - All constitutional principles satisfied.

## Project Structure

### Documentation (this feature)
```
specs/006-database-schema-refactoring/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (in progress)
├── data-model.md        # Phase 1 output (pending)
├── quickstart.md        # Phase 1 output (pending)
├── contracts/           # Phase 1 output (pending)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
src/
├── models/              # Pydantic models (Phase 02: update for project_id)
├── services/            # Business logic (Phase 02: update queries)
├── database/            # Database connection & schema
└── mcp/                 # FastMCP server implementation

migrations/              # Alembic database migration scripts
├── versions/            # Alembic migration versions
│   ├── 001_initial_schema.py             # Existing baseline (Alembic)
│   ├── 003_project_tracking.py           # Existing (Alembic)
│   ├── 005_case_insensitive_vendor.py    # Existing (Alembic)
│   └── 002_remove_non_search_tables.py   # NEW: This migration (Alembic)
├── env.py               # Alembic environment configuration
└── script.py.mako       # Alembic template

tests/
├── contract/            # Contract tests (minimal for schema changes)
├── integration/         # Migration integration tests
│   ├── test_migration_002_upgrade.py     # NEW: Test upgrade execution
│   ├── test_migration_002_downgrade.py   # NEW: Test downgrade execution
│   └── test_migration_002_validation.py  # NEW: Validation test suite
├── unit/                # Unit tests for validation logic
└── performance/         # Migration performance tests
    └── test_migration_002_performance.py # NEW: Performance test

tests/fixtures/
└── generate_test_data.py    # NEW: Test data generation utility
```

**Structure Decision**: Single Python project with standard src/tests layout. Database migrations use **Alembic** (existing migration tool), with migrations in `migrations/versions/` following Alembic's auto-generated revision IDs. This feature adds migration 002 as an Alembic Python migration that revises 005.

## Phase 0: Research & Design Decisions

**Research Complete**: ✅

### R1: Migration Tool Selection
**Decision**: Use Alembic (existing migration framework) with transactional DDL execution
**Rationale**:
- Project already uses Alembic (001_initial_schema.py, 003, 005 exist)
- Alembic handles transactions automatically (single transaction per upgrade/downgrade)
- Built-in migration tracking via `alembic_version` table
- Better integration with SQLAlchemy (existing ORM)
- Automatic rollback on any error (connection loss, constraint violation, etc.)
- Standard tooling: `alembic upgrade head`, `alembic downgrade -1`
**Alternatives Considered**:
- Raw SQL scripts: Rejected (creates parallel migration system, manual tracking required)
- Manual transactions: Rejected (Alembic handles this correctly)

### R2: project_id Validation Strategy
**Decision**: Multi-layer validation (database CHECK constraint + Pydantic validator)
**Rationale**:
- Database CHECK constraint: Last line of defense, prevents SQL injection, enforces at insert/update
- Pydantic validator (Phase 02): Early validation in application code, better error messages
- Regex pattern `^[a-z0-9-]{1,50}$`: Simple, database-native, no extensions needed
**Alternatives Considered**:
- Application-only validation: Rejected (can be bypassed via direct DB access)
- Custom PostgreSQL domain type: Rejected (unnecessary complexity for simple pattern)
- ENUM type: Rejected (inflexible, requires DDL for each new project_id)

### R3: Foreign Key Verification Approach
**Decision**: Query `information_schema.table_constraints` and `information_schema.referential_constraints` before dropping tables
**Rationale**:
- Standard SQL approach, works across PostgreSQL versions
- Explicit verification prevents accidental data corruption
- Clear error message identifies problematic foreign keys
- Fails fast before any destructive operations
**Alternatives Considered**:
- `DROP TABLE ... CASCADE`: Rejected (too aggressive, hides potential issues)
- Manual inspection: Rejected (error-prone, not automatable)
- Rely on PostgreSQL error: Rejected (less clear error messages, fails after starting drops)

### R4: Migration Idempotency Strategy
**Decision**: Rely on Alembic's built-in tracking with defensive IF EXISTS/IF NOT EXISTS clauses
**Rationale**:
- Alembic's `alembic_version` table tracks applied migrations automatically
- `alembic upgrade head` only runs unapplied migrations
- Use `IF EXISTS` / `IF NOT EXISTS` as defense-in-depth (protects against manual schema changes)
- Clear status: `alembic current` shows current migration state
- Idempotency built into framework: running `alembic upgrade head` twice is safe (no-op on second run)
**Alternatives Considered**:
- Manual version tracking: Rejected (Alembic provides this)
- No idempotency checks: Rejected (defensive programming principle)
- Schema comparison: Rejected (Alembic tracks at migration level, not schema level)

### R5: Code Chunk project_id Population Strategy
**Decision**: Three-step ADD COLUMN approach with UPDATE between steps
**Rationale**:
```sql
-- Step 1: Add nullable column
ALTER TABLE code_chunks ADD COLUMN project_id VARCHAR(50);

-- Step 2: Populate from parent repository
UPDATE code_chunks
SET project_id = (
  SELECT project_id FROM repositories
  WHERE repositories.id = code_chunks.repository_id
);

-- Step 3: Add NOT NULL constraint + CHECK constraint
ALTER TABLE code_chunks
  ALTER COLUMN project_id SET NOT NULL,
  ADD CONSTRAINT check_project_id_pattern
    CHECK (project_id ~ '^[a-z0-9-]{1,50}$');
```
- Approach: Separate steps within single transaction
- Handles existing data gracefully (copies from parent)
- Validates referential integrity (UPDATE fails if orphan chunks exist)
- NOT NULL constraint applied after population ensures no NULLs
**Alternatives Considered**:
- Direct ADD COLUMN with NOT NULL + UPDATE: Rejected (PostgreSQL doesn't allow UPDATE between constraint checks)
- Default value: Rejected (loses referential integrity, assigns 'default' to all chunks)
- Two separate transactions: Rejected (violates single-transaction requirement)

### R6: Migration Performance Optimization
**Decision**: Create index AFTER data population, use CONCURRENTLY for production (optional step)
**Rationale**:
- Index creation on existing data: Faster to populate first, then index
- `CREATE INDEX CONCURRENTLY`: Optional for production (allows reads during index build, but not transactional)
- For initial migration (minimal data): Standard index creation acceptable (< 1 second)
- Performance target: < 5 minutes easily met with up to 100K rows
**Alternatives Considered**:
- Index before populating: Rejected (slower, each UPDATE incurs index maintenance cost)
- No performance optimization: Rejected (violates FR-031 performance requirement)

### R7: Logging and Observability Strategy
**Decision**: Use Python logging within Alembic migration + SQL RAISE NOTICE statements
**Rationale**:
- Python `logger.info()` statements in migration code: Structured, timestamped, configurable
- `RAISE NOTICE` for SQL-level progress: Inline visibility during SQL execution
- Alembic CLI captures all output by default (stdout/stderr)
- Log to `/tmp/codebase-mcp-migration.log` via Python logging configuration
- Better exception context: Python stack traces + SQL error messages
**Alternatives Considered**:
- SQL-only logging: Rejected (less structured, harder to parse)
- No logging: Rejected (violates FR-020 logging requirement)
- Custom logging table: Rejected (overkill, complicates transaction isolation)

### R8: Rollback Design Pattern (Alembic Downgrade)
**Decision**: Implement `downgrade()` function with inverse operations + data restoration caveat
**Rationale**:
- Alembic's `downgrade()` function mirrors `upgrade()`: Inverse DDL operations
- `DROP COLUMN` mirrors `ADD COLUMN`, `CREATE TABLE` mirrors `DROP TABLE`
- Schema-only rollback: Structure restored, data in dropped tables lost (acceptable per spec)
- Data restoration requires backup: Documented in migration docstring
- Fast execution: `alembic downgrade -1` runs in < 30 seconds
- Version tracking: Alembic updates `alembic_version` table automatically
**Alternatives Considered**:
- Separate rollback script: Rejected (Alembic provides downgrade function)
- No downgrade implementation: Rejected (violates FR-014 reversibility requirement)
- Data restoration in downgrade: Rejected (slow, requires backup in migration code)

### R9: Database Connection Configuration (Alembic)
**Decision**: Use existing Alembic `env.py` configuration with `DATABASE_URL` environment variable
**Rationale**:
- Alembic already configured in project (`migrations/env.py` exists)
- Follows standard pattern: `DATABASE_URL=postgresql://user:pass@host/dbname`
- Existing config likely reads from environment or application config
- For testing: Override via `alembic -x dbname=codebase_mcp_test upgrade head`
- Production: Use existing `DATABASE_URL` from application deployment
**Alternatives Considered**:
- Hardcoded connection strings: Rejected (insecure, inflexible)
- Custom config file: Rejected (Alembic env.py is standard)
- Command-line arguments: Rejected (env vars more secure, standard practice)

**Implementation Pattern**:
```python
# migrations/env.py (already exists, use existing pattern)
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))
```

## Phase 1: Design & Contracts

### Data Model Changes

See [data-model.md](./data-model.md) for complete entity definitions.

**Summary of Changes**:
- **repositories table**: Add `project_id VARCHAR(50) NOT NULL DEFAULT 'default'` with CHECK constraint
- **code_chunks table**: Add `project_id VARCHAR(50) NOT NULL` with CHECK constraint
- **Index**: Create `idx_project_repository` on `(project_id, repository_id)` for multi-project queries
- **9 tables dropped**: work_items, work_item_dependencies, tasks, task_branches, task_commits, vendors, vendor_test_results, deployments, deployment_vendors

### API Contracts

**Note**: This feature is database schema-only. No API changes. Phase 02 will update MCP tool implementations to use project_id.

See [contracts/](./contracts/) for:
- `migration_execution.md`: Manual execution contract (SQL script interface)
- `validation_contract.md`: Post-migration validation expectations

### Integration Test Scenarios

See [quickstart.md](./quickstart.md) for complete test execution flow.

**Key Scenarios**:
1. **Fresh database migration**: Execute on empty database, verify schema changes
2. **Migration with existing data**: Execute on database with sample repositories/chunks, verify data preservation
3. **Idempotency test**: Run migration twice, verify second run skips gracefully
4. **Rollback test**: Apply migration, execute rollback, verify schema restoration
5. **Performance test**: Execute on 100 repos + 10K chunks, verify < 5 minute duration
6. **Validation test**: Attempt invalid project_id insertions, verify CHECK constraint rejection

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
1. Load `.specify/templates/tasks-template.md` as base structure
2. Generate tasks from Phase 1 artifacts:
   - **Alembic migration task**: Create `002_remove_non_search_tables.py` with upgrade/downgrade functions
   - **Test utility task**: Create test data generation script
   - **Test tasks**: Validation tests, integration tests (upgrade/downgrade), performance tests
   - **Documentation tasks**: Update migration docs, add troubleshooting guide
3. Task ordering:
   - Phase 01A: Create test data generation utility
   - Phase 01B: Write Alembic migration (upgrade + downgrade functions)
   - Phase 01C: Write validation test suite [P]
   - Phase 01D: Write integration tests (upgrade) [P]
   - Phase 01E: Write integration tests (downgrade) [P]
   - Phase 01F: Write performance tests [P]
   - Phase 01G: Execute migration on test database
   - Phase 01H: Run all tests and validate
   - Phase 01I: Update documentation

**Ordering Strategy**:
- **TDD order**: Tests before migration execution (but migration code needed for testing)
- **Dependency order**: Test data utility first, then migration code, then tests, then execution
- **Parallel execution**: All test writing can happen in parallel ([P] marker) after migration code exists
- **Safety order**: All tests must pass before marking migration complete

**Estimated Output**: 10-12 tasks in tasks.md
- 1 utility creation task
- 1 Alembic migration creation task (upgrade + downgrade in one file)
- 5 test creation tasks (parallel)
- 1 execution task (run alembic upgrade on test DB)
- 1 validation task (run all tests)
- 1 documentation task

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 01 (this phase)**: Alembic migration for database schema changes
**Phase 02**: Update Python code (models, services, MCP tools) to use project_id
**Phase 03**: Implement multi-project search/indexing logic
**Phase 04**: Connection pool for database-per-project architecture

## Complexity Tracking

**No constitutional violations requiring justification**.

All complexity in this feature is essential and serves constitutional principles:
- Alembic migrations: Required for schema evolution (Production Quality)
- Transaction wrapping: Required for atomic operation (Production Quality)
- Three-step column addition: Required for data integrity (Production Quality)
- Validation layers: Required for security (Production Quality)

## Progress Tracking

**Phase Status**:
- [X] Phase 0: Research complete (/plan command)
- [X] Phase 1: Design complete (/plan command)
- [X] Phase 2: Task planning approach described (/plan command)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [X] Initial Constitution Check: PASS
- [X] Post-Design Constitution Check: PASS (re-evaluated after Phase 1)
- [X] All NEEDS CLARIFICATION resolved (none existed after /clarify)
- [X] Complexity deviations documented (none required)

**Execution Flow Status**:
1. ✅ Load feature spec from Input path
2. ✅ Fill Technical Context
3. ✅ Fill Constitution Check section
4. ✅ Evaluate Constitution Check (PASS)
5. ✅ Execute Phase 0 (research decisions documented)
6. ✅ Execute Phase 1 (artifacts generated)
7. ✅ Re-evaluate Constitution Check (PASS)
8. ✅ Plan Phase 2 (approach described)
9. ✅ STOP - Ready for /tasks command

---
*Based on Constitution v2.2.0 - See `.specify/memory/constitution.md`*
*Feature Specification: `specs/006-database-schema-refactoring/spec.md`*
*Branch: `006-database-schema-refactoring` | Created: 2025-10-11*
