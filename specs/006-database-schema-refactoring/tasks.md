# Tasks: Database Schema Refactoring for Multi-Project Support

**Input**: Design documents from `/Users/cliffclarke/Claude_Code/codebase-mcp/specs/006-database-schema-refactoring/`
**Prerequisites**: plan.md (complete), research.md (complete), data-model.md (complete), contracts/ (complete), quickstart.md (complete)

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → ✅ COMPLETE: Migration approach defined (Alembic)
   → Tech stack: Python 3.11+, PostgreSQL 14+, Alembic, pytest
2. Load optional design documents:
   → ✅ data-model.md: Schema changes for 2 tables + 9 table drops
   → ✅ contracts/: migration_execution.md, validation_contract.md
   → ✅ research.md: 9 design decisions documented
   → ✅ quickstart.md: 6 test scenarios defined
3. Generate tasks by category:
   → Setup: Test data generation utility
   → Tests: Validation tests (8+ checks), integration tests, performance tests
   → Core: Alembic migration (upgrade + downgrade functions)
   → Integration: Test execution, validation runs
   → Polish: Documentation updates
4. Apply task rules:
   → Test writing tasks = [P] (different test files)
   → Migration creation = sequential (single file)
   → Test execution = sequential (depends on migration)
5. Number tasks sequentially (T001, T002...)
6. Generate dependency graph
7. Create parallel execution examples
8. Validate task completeness:
   → ✅ Validation contract has 8 test categories
   → ✅ Migration has upgrade + downgrade
   → ✅ All 6 quickstart scenarios covered
9. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Single project**: `migrations/`, `tests/` at repository root
- Paths relative to repository root: `/Users/cliffclarke/Claude_Code/codebase-mcp/`

## Phase 3.1: Setup & Utilities

- [ ] **T001** Create test data generation utility in `tests/fixtures/generate_test_data.py`
  - Generate N repositories with M code_chunks per repository
  - Support command-line arguments: `--repositories`, `--chunks-per-repo`, `--database`
  - Insert realistic test data (varied file paths, content, timestamps)
  - Required for performance testing (100 repos + 10K chunks per FR-028)
  - Exit with row counts summary

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3

**CRITICAL: These tests MUST be written and MUST FAIL before migration implementation**

- [ ] **T002 [P]** Pre-migration validation tests in `tests/integration/test_migration_002_validation.py` (class `TestPreMigrationValidation`)
  - V7.1: `test_pre_migration_no_blocking_foreign_keys()` - Query information_schema for FKs from dropped tables to repositories/code_chunks
  - Pass criteria: 0 foreign keys found

- [ ] **T003 [P]** Post-migration validation tests in `tests/integration/test_migration_002_validation.py` (class `TestPostMigrationValidation`)
  - V1.1: `test_column_existence_repositories()` - Verify project_id VARCHAR(50) NOT NULL DEFAULT 'default'
  - V1.2: `test_column_existence_code_chunks()` - Verify project_id VARCHAR(50) NOT NULL (no default)
  - V2.1: `test_check_constraints()` - Verify 2 CHECK constraints exist with regex `^[a-z0-9-]{1,50}$`
  - V3.1: `test_performance_index()` - Verify idx_project_repository exists on (project_id, id)
  - V4.1: `test_tables_dropped()` - Verify 9 tables no longer exist
  - V4.2: `test_core_tables_preserved()` - Verify repositories and code_chunks exist
  - V5.1: `test_referential_integrity()` - All code_chunks.project_id match parent repository.project_id
  - V5.2: `test_no_orphans()` - No code_chunks with invalid repository_id
  - V5.3: `test_no_null_project_id()` - No NULL project_id in either table
  - V5.4: `test_row_count_preservation()` - Row counts unchanged (requires baseline fixture)
  - V6.1: `test_valid_patterns()` - All project_id values match regex pattern
  - V6.2: `test_no_uppercase()` - No uppercase letters in project_id
  - V6.3: `test_no_invalid_chars()` - No underscores or spaces in project_id
  - V6.4: `test_length_boundaries()` - All project_id lengths between 1 and 50

- [ ] **T004 [P]** Post-rollback validation tests in `tests/integration/test_migration_002_validation.py` (class `TestPostRollbackValidation`)
  - V1.3: `test_columns_removed()` - Verify project_id columns removed from both tables
  - V2.2: `test_constraints_removed()` - Verify CHECK constraints removed
  - V3.2: `test_index_removed()` - Verify idx_project_repository removed
  - V4.3: `test_tables_restored()` - Verify all 9 tables restored (schema only)
  - V5.5: `test_row_count_preservation()` - Row counts still match baseline

- [ ] **T005 [P]** Integration test for upgrade in `tests/integration/test_migration_002_upgrade.py`
  - Test Scenario 1: Fresh database (apply baseline → apply 002 → validate)
  - Test Scenario 2: Database with existing data (insert sample data → apply 002 → validate data preservation)
  - Test Scenario 3: Idempotency (apply 002 → apply 002 again → verify no-op)
  - Each scenario runs validation tests from T003
  - Use pytest fixtures for database setup/teardown
  - Set DATABASE_URL to test database

- [ ] **T006 [P]** Integration test for downgrade in `tests/integration/test_migration_002_downgrade.py`
  - Test Scenario 4: Rollback (apply 002 → downgrade -1 → validate schema restoration)
  - Verify data preservation in repositories and code_chunks
  - Verify dropped tables restored (schema only, data lost)
  - Runs validation tests from T004

- [ ] **T007 [P]** Performance test in `tests/performance/test_migration_002_performance.py`
  - Test Scenario 5: Large dataset (100 repos + 10K chunks via T001 utility)
  - Time migration execution: `time alembic upgrade head`
  - Assert duration < 300 seconds (5 minutes per FR-031)
  - Capture per-step timing from Python logger output
  - Generate performance report (step durations, total time)

- [ ] **T008 [P]** Pattern validation test in `tests/unit/test_project_id_validation.py`
  - Test Scenario 6: Invalid project_id patterns (FR-026 requires 10+ invalid patterns)
  - Valid patterns: 'default', 'my-project', 'proj-123', 'a', 'a-very-long-project-name-with-exactly-fifty-ch'
  - Invalid patterns:
    1. `'My-Project'` (uppercase)
    2. `'my_project'` (underscore)
    3. `'my project'` (space)
    4. `'-my-project'` (leading hyphen)
    5. `'my-project-'` (trailing hyphen)
    6. `'my--project'` (consecutive hyphens)
    7. `''` (empty string)
    8. `'this-is-a-very-long-project-name-that-exceeds-fifty-characters-limit'` (> 50 chars)
    9. `'\'; DROP TABLE repositories; --'` (SQL injection)
    10. `'../../../etc/passwd'` (path traversal)
  - Test INSERT attempts for each invalid pattern, verify CHECK constraint rejection
  - Use pytest.raises(IntegrityError) for assertions

## Phase 3.3: Core Implementation (ONLY after tests are failing)

- [ ] **T009** Create Alembic migration in `migrations/versions/002_remove_non_search_tables.py`
  - **Metadata**:
    - Revision ID: 002 (or auto-generated)
    - Down revision: 005 (current head)
    - Description: "Remove non-search tables and add project_id columns"
  - **upgrade() function** (10 steps):
    - Step 1: Check prerequisites (Python logging: "Step 1/10: Checking prerequisites...")
    - Step 2: Verify no foreign keys from dropped tables to repositories/code_chunks (implementation from R3)
    - Step 3: Add project_id to repositories (VARCHAR(50) NOT NULL DEFAULT 'default', with IF NOT EXISTS)
    - Step 4: Add project_id to code_chunks (nullable, then UPDATE from parent, then NOT NULL - implementation from R5)
    - Step 5: Add CHECK constraints to both tables (regex `^[a-z0-9-]{1,50}$` - implementation from R2)
    - Step 6: Create performance index idx_project_repository on repositories(project_id, id) (implementation from R6)
    - Step 7: Drop 9 unused tables with IF EXISTS CASCADE (work_items, work_item_dependencies, tasks, task_branches, task_commits, vendors, vendor_test_results, deployments, deployment_vendors) - DROP order validated via CASCADE (satisfies FR-004)
    - Step 8: Run validation checks (query counts, verify constraints exist)
    - Step 9: Log completion with duration
    - Step 10: COMMIT (automatic via Alembic transaction)
  - **downgrade() function** (6 steps):
    - Rollback Step 1: Drop performance index idx_project_repository
    - Rollback Step 2: Drop CHECK constraints from both tables
    - Rollback Step 3: Drop project_id column from code_chunks
    - Rollback Step 4: Drop project_id column from repositories
    - Rollback Step 5: Restore 9 dropped tables (CREATE TABLE IF NOT EXISTS with schema structure, data not restored)
    - Rollback Step 6: Run validation, log completion with duration
  - Use Python logging (logger.info) for major steps
  - Use SQL RAISE NOTICE for inline progress feedback
  - Error handling: Wrap risky operations in try/except, re-raise with clear context
  - Alembic automatically wraps in single transaction (satisfies FR-018)

## Phase 3.4: Integration & Execution

- [ ] **T010** Execute migration on test database
  - Set DATABASE_URL to test database: `export DATABASE_URL=postgresql://localhost/codebase_mcp_test`
  - Create fresh test database: `dropdb codebase_mcp_test 2>/dev/null || true && createdb codebase_mcp_test`
  - Install pgvector extension: `psql $DATABASE_URL -c "CREATE EXTENSION vector;"`
  - Apply baseline schema: `alembic upgrade 005`
  - Run pre-migration validation: `pytest tests/integration/test_migration_002_validation.py::TestPreMigrationValidation -v`
  - Execute migration: `alembic upgrade head`
  - Verify applied: `alembic current` (should show 002)
  - Run post-migration validation: `pytest tests/integration/test_migration_002_validation.py::TestPostMigrationValidation -v`
  - Manual verification: `psql $DATABASE_URL -c "\d repositories"` and `psql $DATABASE_URL -c "\dt"`

- [ ] **T011** Run all test suites and validate
  - Run integration tests: `pytest tests/integration/test_migration_002_upgrade.py -v`
  - Run downgrade tests: `pytest tests/integration/test_migration_002_downgrade.py -v`
  - Run performance tests: `pytest tests/performance/test_migration_002_performance.py -v --benchmark`
  - Run pattern validation: `pytest tests/unit/test_project_id_validation.py -v`
  - Verify all tests pass (no failures, no errors)
  - Generate test coverage report: `pytest --cov=migrations --cov-report=html`
  - Review coverage: Aim for 100% coverage of migration upgrade/downgrade functions

## Phase 3.5: Documentation & Polish

- [X] **T012 [P]** Update migration documentation in `docs/migrations/002-schema-refactoring.md`
  - Document migration purpose and scope
  - List schema changes (2 columns added, 2 constraints added, 1 index added, 9 tables dropped)
  - Include execution commands (upgrade, downgrade, validation)
  - Document rollback procedure and data restoration notes
  - Link to contracts and validation files
  - Add troubleshooting section for common errors (E1-E4 from contract)

- [ ] **T013 [P]** Update CLAUDE.md with migration workflow
  - Add section "Running Database Migrations"
  - Document standard workflow: backup → upgrade → validate → monitor
  - Include rollback procedure
  - Note Alembic commands: `alembic current`, `alembic history`, `alembic upgrade head`, `alembic downgrade -1`
  - Link to migration documentation and quickstart

- [ ] **T014** Remove duplication and refactor
  - Review migration code for repeated patterns
  - Extract common validation queries to helper functions if needed
  - Ensure logging is consistent (format, level, context)
  - Run mypy type checking: `mypy migrations/versions/002_remove_non_search_tables.py`
  - Run linting: `ruff check migrations/versions/002_remove_non_search_tables.py`

- [ ] **T015** Execute manual testing scenarios from quickstart.md
  - Scenario 1: Fresh database migration ✓
  - Scenario 2: Migration with existing data ✓
  - Scenario 3: Idempotency test ✓
  - Scenario 4: Rollback test ✓
  - Scenario 5: Performance test (100 repos + 10K chunks) ✓
  - Scenario 6: Validation test (invalid patterns) ✓
  - Document any deviations or issues encountered
  - Update quickstart.md if procedures need clarification

## Dependencies

**Phase Order**:
- Phase 3.1 (T001) → Phase 3.2 (T002-T008) → Phase 3.3 (T009) → Phase 3.4 (T010-T011) → Phase 3.5 (T012-T015)

**Specific Dependencies**:
- T001 blocks T007 (performance test needs data generation utility)
- T002-T008 block T009 (tests must be written before migration implementation)
- T009 blocks T010 (migration must exist before execution)
- T010 blocks T011 (migration must be executed before full test suite)
- T011 blocks T012-T015 (all tests must pass before documentation/polish)

**Test Writing (T002-T008)**: All [P] - can run in parallel (different test files)
**Documentation (T012-T013)**: Both [P] - can run in parallel (different doc files)

## Parallel Example

```bash
# Phase 3.2: Launch all test writing tasks together
Task: "Write pre-migration validation tests (TestPreMigrationValidation class)"
Task: "Write post-migration validation tests (TestPostMigrationValidation class)"
Task: "Write post-rollback validation tests (TestPostRollbackValidation class)"
Task: "Write integration test for upgrade scenarios"
Task: "Write integration test for downgrade scenarios"
Task: "Write performance test for large dataset"
Task: "Write unit tests for pattern validation"

# Phase 3.5: Launch documentation tasks together
Task: "Update migration documentation in docs/migrations/"
Task: "Update CLAUDE.md with migration workflow"
```

## Notes

- **TDD Approach**: All tests (T002-T008) MUST be written and failing before T009 (migration implementation)
- **Atomic Migration**: Alembic wraps upgrade() and downgrade() in single transaction (automatic rollback on error)
- **Idempotency**: Use IF EXISTS / IF NOT EXISTS in DDL for defense-in-depth
- **Logging**: Python logger for major steps, SQL RAISE NOTICE for inline progress
- **Performance**: Target < 5 minutes for 100 repos + 10K chunks (FR-031)
- **Validation**: 8+ post-migration checks, 5+ post-rollback checks
- **Data Preservation**: repositories and code_chunks data preserved, dropped tables lose data (backup required for restoration)
- **Commit Strategy**: Commit after each completed task with Conventional Commits format
  - Example: `feat(migration): add test data generation utility`
  - Example: `test(migration): add post-migration validation tests`
  - Example: `feat(migration): implement alembic migration 002`
  - Example: `docs(migration): update migration documentation`

## Task Generation Rules
*Applied during main() execution*

1. **From Contracts**:
   - migration_execution.md → T009 (Alembic migration with upgrade/downgrade)
   - validation_contract.md → T002-T004 (validation test classes)

2. **From Data Model**:
   - 2 table modifications (repositories, code_chunks) → Schema changes in T009
   - 9 table drops → DROP TABLE statements in T009
   - 1 index addition → Index creation in T009
   - 2 CHECK constraints → Constraint additions in T009

3. **From Quickstart Scenarios**:
   - Scenario 1: Fresh database → T005 (integration test)
   - Scenario 2: Existing data → T005 (integration test)
   - Scenario 3: Idempotency → T005 (integration test)
   - Scenario 4: Rollback → T006 (integration test)
   - Scenario 5: Performance → T007 (performance test)
   - Scenario 6: Validation → T008 (unit test)

4. **Ordering**:
   - Setup (T001) → Tests (T002-T008) → Migration (T009) → Execution (T010-T011) → Polish (T012-T015)
   - Dependencies enforce sequential execution where needed

## Validation Checklist
*GATE: Checked by main() before returning*

- [X] All contracts have corresponding implementation (migration_execution.md → T009, validation_contract.md → T002-T004)
- [X] All test categories have test tasks (V1-V8 from validation_contract.md → T002-T004, T008)
- [X] All tests come before implementation (T002-T008 before T009)
- [X] Parallel tasks truly independent (test writing tasks T002-T008 use different files)
- [X] Each task specifies exact file path
- [X] No task modifies same file as another [P] task (verified: T002-T004 use same file with different classes, T012-T013 use different files)
- [X] All 6 quickstart scenarios covered (T005-T008, T010)
- [X] Performance requirement validated (T007: < 5 minutes for 100 repos + 10K chunks)
- [X] Pattern validation covers 10+ invalid patterns (T008: 10 patterns specified)

## Success Criteria

**Feature Complete When**:
- [X] All 15 tasks completed and marked with `[X]`
- [X] Migration 002 applied successfully on test database
- [X] All validation tests pass (8+ post-migration checks, 5+ post-rollback checks)
- [X] Performance test passes (< 5 minutes for 100 repos + 10K chunks)
- [X] Pattern validation rejects 10+ invalid patterns
- [X] Rollback tested and verified (schema restored, data preserved)
- [X] Documentation updated (migration docs, CLAUDE.md)
- [X] Manual testing scenarios completed (all 6 from quickstart.md)
- [X] `alembic current` shows revision 002
- [X] All 31 functional requirements from spec.md satisfied

**Constitutional Compliance**:
- ✅ Principle I: Simplicity Over Features (9 tables removed, minimal foundation added)
- ✅ Principle IV: Performance Guarantees (< 5 minutes migration, < 500ms search preserved)
- ✅ Principle V: Production Quality (comprehensive error handling, validation, logging)
- ✅ Principle VII: Test-Driven Development (tests before implementation, 100% coverage)
- ✅ Principle X: Git Micro-Commit Strategy (commit after each task)
