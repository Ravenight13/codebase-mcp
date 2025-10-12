# Validation Contract
**Feature**: Database Schema Refactoring for Multi-Project Support
**Migration**: 002_remove_non_search_tables
**Tool**: pytest with SQLAlchemy
**Date**: 2025-10-11

## Contract Overview

This document defines validation expectations for migration 002 using **pytest test suites** instead of SQL scripts. Validation runs in three contexts:
1. **Pre-migration**: Verify database ready for migration (optional baseline checks)
2. **Post-migration**: Verify schema changes applied correctly
3. **Post-rollback**: Verify schema restored to pre-migration state

**Test File**: `tests/integration/test_migration_002_validation.py`

## Validation Categories

### V1: Schema Structure Validation

#### V1.1: Column Existence (Post-Migration)

**Test Function**: `test_post_migration_column_existence_repositories()`

**Purpose**: Verify `project_id` column exists in `repositories` table with correct specifications

**Implementation**:
```python
def test_post_migration_column_existence_repositories(db_session):
    """Verify project_id column exists in repositories with correct type"""
    result = db_session.execute(text("""
        SELECT column_name, data_type, character_maximum_length,
               column_default, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'repositories' AND column_name = 'project_id'
    """))
    row = result.fetchone()

    assert row is not None, "project_id column missing in repositories"
    assert row.data_type == 'character varying', f"Expected VARCHAR, got {row.data_type}"
    assert row.character_maximum_length == 50, f"Expected length 50, got {row.character_maximum_length}"
    assert 'default' in str(row.column_default).lower(), f"Expected DEFAULT 'default', got {row.column_default}"
    assert row.is_nullable == 'NO', "project_id should be NOT NULL"
```

**Pass Criteria**:
- Column exists with exact specifications
- data_type = 'character varying'
- character_maximum_length = 50
- column_default contains 'default'
- is_nullable = 'NO'

#### V1.2: Column Existence (Post-Migration)

**Test Function**: `test_post_migration_column_existence_code_chunks()`

**Purpose**: Verify `project_id` column exists in `code_chunks` table

**Implementation**:
```python
def test_post_migration_column_existence_code_chunks(db_session):
    """Verify project_id column exists in code_chunks with correct type"""
    result = db_session.execute(text("""
        SELECT column_name, data_type, character_maximum_length, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'code_chunks' AND column_name = 'project_id'
    """))
    row = result.fetchone()

    assert row is not None, "project_id column missing in code_chunks"
    assert row.data_type == 'character varying'
    assert row.character_maximum_length == 50
    assert row.is_nullable == 'NO'
    # Note: code_chunks.project_id has NO default (populated via UPDATE)
```

**Pass Criteria**:
- Column exists
- data_type = 'character varying'
- character_maximum_length = 50
- is_nullable = 'NO'
- No default value (intended behavior)

#### V1.3: Column Removal (Post-Rollback)

**Test Function**: `test_post_rollback_columns_removed()`

**Purpose**: Verify `project_id` columns removed from both tables

**Implementation**:
```python
def test_post_rollback_columns_removed(db_session):
    """Verify project_id columns removed after rollback"""
    result = db_session.execute(text("""
        SELECT COUNT(*) AS column_count
        FROM information_schema.columns
        WHERE table_name IN ('repositories', 'code_chunks')
          AND column_name = 'project_id'
    """))
    count = result.scalar()

    assert count == 0, f"Expected 0 project_id columns after rollback, found {count}"
```

**Pass Criteria**: No rows with column_name = 'project_id'

### V2: Constraint Validation

#### V2.1: CHECK Constraints Exist (Post-Migration)

**Test Function**: `test_post_migration_check_constraints()`

**Purpose**: Verify pattern validation constraints exist on both tables

**Implementation**:
```python
def test_post_migration_check_constraints(db_session):
    """Verify CHECK constraints exist for project_id pattern validation"""
    result = db_session.execute(text("""
        SELECT tc.constraint_name, tc.table_name, cc.check_clause
        FROM information_schema.table_constraints tc
        JOIN information_schema.check_constraints cc
          ON tc.constraint_name = cc.constraint_name
        WHERE tc.table_name IN ('repositories', 'code_chunks')
          AND cc.check_clause LIKE '%project_id%'
    """))
    constraints = result.fetchall()

    assert len(constraints) == 2, f"Expected 2 CHECK constraints, found {len(constraints)}"

    # Verify both constraints use correct regex
    for constraint in constraints:
        assert '^[a-z0-9-]{1,50}$' in constraint.check_clause, \
            f"Constraint {constraint.constraint_name} has incorrect pattern"
```

**Pass Criteria**:
- 2 CHECK constraints found
- Both contain regex pattern `^[a-z0-9-]{1,50}$`

#### V2.2: CHECK Constraints Removed (Post-Rollback)

**Test Function**: `test_post_rollback_constraints_removed()`

**Implementation**:
```python
def test_post_rollback_constraints_removed(db_session):
    """Verify CHECK constraints removed after rollback"""
    result = db_session.execute(text("""
        SELECT COUNT(*) FROM information_schema.table_constraints tc
        JOIN information_schema.check_constraints cc
          ON tc.constraint_name = cc.constraint_name
        WHERE tc.table_name IN ('repositories', 'code_chunks')
          AND cc.check_clause LIKE '%project_id%'
    """))
    count = result.scalar()

    assert count == 0, f"Expected 0 CHECK constraints after rollback, found {count}"
```

**Pass Criteria**: No CHECK constraints on project_id

### V3: Index Validation

#### V3.1: Performance Index Exists (Post-Migration)

**Test Function**: `test_post_migration_performance_index()`

**Implementation**:
```python
def test_post_migration_performance_index(db_session):
    """Verify idx_project_repository index created"""
    result = db_session.execute(text("""
        SELECT indexname, tablename, indexdef
        FROM pg_indexes
        WHERE indexname = 'idx_project_repository'
    """))
    index = result.fetchone()

    assert index is not None, "Index idx_project_repository not found"
    assert index.tablename == 'repositories', f"Index on wrong table: {index.tablename}"
    assert 'project_id' in index.indexdef and 'id' in index.indexdef, \
        f"Index definition incorrect: {index.indexdef}"
```

**Pass Criteria**:
- Index `idx_project_repository` exists
- On `repositories` table
- Contains both `project_id` and `id` columns

#### V3.2: Performance Index Removed (Post-Rollback)

**Test Function**: `test_post_rollback_index_removed()`

**Implementation**:
```python
def test_post_rollback_index_removed(db_session):
    """Verify performance index removed after rollback"""
    result = db_session.execute(text("""
        SELECT COUNT(*) FROM pg_indexes
        WHERE indexname = 'idx_project_repository'
    """))
    count = result.scalar()

    assert count == 0, "Index idx_project_repository should not exist after rollback"
```

**Pass Criteria**: Index not found

### V4: Table Existence Validation

#### V4.1: Unused Tables Dropped (Post-Migration)

**Test Function**: `test_post_migration_tables_dropped()`

**Implementation**:
```python
def test_post_migration_tables_dropped(db_session):
    """Verify 9 unused tables no longer exist"""
    dropped_tables = [
        'work_items', 'work_item_dependencies', 'tasks',
        'task_branches', 'task_commits', 'vendors',
        'vendor_test_results', 'deployments', 'deployment_vendors'
    ]

    result = db_session.execute(text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = ANY(:table_names)
    """), {'table_names': dropped_tables})

    existing = result.fetchall()

    assert len(existing) == 0, \
        f"Expected 0 dropped tables to exist, found: {[row.table_name for row in existing]}"
```

**Pass Criteria**: None of the 9 tables exist

#### V4.2: Core Tables Preserved (Post-Migration)

**Test Function**: `test_post_migration_core_tables_preserved()`

**Implementation**:
```python
def test_post_migration_core_tables_preserved(db_session):
    """Verify repositories and code_chunks tables still exist"""
    result = db_session.execute(text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name IN ('repositories', 'code_chunks')
    """))
    tables = [row.table_name for row in result.fetchall()]

    assert 'repositories' in tables, "repositories table missing"
    assert 'code_chunks' in tables, "code_chunks table missing"
```

**Pass Criteria**: Both tables exist

#### V4.3: Dropped Tables Restored (Post-Rollback)

**Test Function**: `test_post_rollback_tables_restored()`

**Implementation**:
```python
def test_post_rollback_tables_restored(db_session):
    """Verify all 9 tables restored (schema only) after rollback"""
    expected_tables = [
        'work_items', 'work_item_dependencies', 'tasks',
        'task_branches', 'task_commits', 'vendors',
        'vendor_test_results', 'deployments', 'deployment_vendors'
    ]

    result = db_session.execute(text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = ANY(:table_names)
    """), {'table_names': expected_tables})

    restored = [row.table_name for row in result.fetchall()]

    assert len(restored) == 9, \
        f"Expected 9 tables restored, found {len(restored)}: {restored}"

    for table in expected_tables:
        assert table in restored, f"Table {table} not restored"
```

**Pass Criteria**: All 9 tables exist

### V5: Data Integrity Validation

#### V5.1: Referential Integrity (Post-Migration)

**Test Function**: `test_post_migration_referential_integrity()`

**Purpose**: All `code_chunks.project_id` values match parent `repositories.project_id`

**Implementation**:
```python
def test_post_migration_referential_integrity(db_session):
    """Verify code_chunks.project_id matches parent repository.project_id"""
    result = db_session.execute(text("""
        SELECT COUNT(*) AS mismatch_count
        FROM code_chunks cc
        JOIN repositories r ON cc.repository_id = r.id
        WHERE cc.project_id != r.project_id
    """))
    mismatch_count = result.scalar()

    assert mismatch_count == 0, \
        f"Found {mismatch_count} code_chunks with project_id mismatch"

    # Also check if there are any rows (sanity check)
    total = db_session.execute(text("SELECT COUNT(*) FROM code_chunks")).scalar()
    if total > 0:
        # If data exists, verify all have project_id
        nulls = db_session.execute(text(
            "SELECT COUNT(*) FROM code_chunks WHERE project_id IS NULL"
        )).scalar()
        assert nulls == 0, f"Found {nulls} code_chunks with NULL project_id"
```

**Pass Criteria**: No mismatches, no NULL values

#### V5.2: No Orphaned Code Chunks (Post-Migration)

**Test Function**: `test_post_migration_no_orphans()`

**Implementation**:
```python
def test_post_migration_no_orphans(db_session):
    """Verify all code_chunks have valid repository_id"""
    result = db_session.execute(text("""
        SELECT COUNT(*) AS orphan_count
        FROM code_chunks cc
        LEFT JOIN repositories r ON cc.repository_id = r.id
        WHERE r.id IS NULL
    """))
    orphan_count = result.scalar()

    assert orphan_count == 0, f"Found {orphan_count} orphaned code_chunks"
```

**Pass Criteria**: No orphaned chunks

#### V5.3: No NULL project_id (Post-Migration)

**Test Function**: `test_post_migration_no_null_project_id()`

**Implementation**:
```python
def test_post_migration_no_null_project_id(db_session):
    """Verify all rows have non-NULL project_id"""
    repo_nulls = db_session.execute(text(
        "SELECT COUNT(*) FROM repositories WHERE project_id IS NULL"
    )).scalar()

    chunk_nulls = db_session.execute(text(
        "SELECT COUNT(*) FROM code_chunks WHERE project_id IS NULL"
    )).scalar()

    assert repo_nulls == 0, f"Found {repo_nulls} repositories with NULL project_id"
    assert chunk_nulls == 0, f"Found {chunk_nulls} code_chunks with NULL project_id"
```

**Pass Criteria**: Both counts = 0

#### V5.4: Row Count Preservation (Post-Migration)

**Test Function**: `test_post_migration_row_count_preservation()`

**Purpose**: Verify no data lost during migration

**Implementation**:
```python
@pytest.fixture(scope="module")
def baseline_counts(db_session):
    """Capture baseline counts before migration"""
    repos = db_session.execute(text("SELECT COUNT(*) FROM repositories")).scalar()
    chunks = db_session.execute(text("SELECT COUNT(*) FROM code_chunks")).scalar()
    return {'repos': repos, 'chunks': chunks}

def test_post_migration_row_count_preservation(db_session, baseline_counts):
    """Verify row counts unchanged after migration"""
    repos_after = db_session.execute(text("SELECT COUNT(*) FROM repositories")).scalar()
    chunks_after = db_session.execute(text("SELECT COUNT(*) FROM code_chunks")).scalar()

    assert repos_after == baseline_counts['repos'], \
        f"Repository count changed: {baseline_counts['repos']} -> {repos_after}"
    assert chunks_after == baseline_counts['chunks'], \
        f"Code chunk count changed: {baseline_counts['chunks']} -> {chunks_after}"
```

**Pass Criteria**: Counts unchanged

#### V5.5: Row Count Preservation (Post-Rollback)

**Test Function**: `test_post_rollback_row_count_preservation()`

**Implementation**: Same as V5.4, comparing against baseline

**Pass Criteria**: Counts still match pre-migration baseline

### V6: Pattern Validation

#### V6.1: Valid project_id Patterns (Post-Migration)

**Test Function**: `test_post_migration_valid_patterns()`

**Implementation**:
```python
def test_post_migration_valid_patterns(db_session):
    """Verify all project_id values match regex ^[a-z0-9-]{1,50}$"""
    # Check repositories
    result = db_session.execute(text("""
        SELECT COUNT(*) FROM repositories
        WHERE project_id !~ '^[a-z0-9-]{1,50}$'
    """))
    repos_invalid = result.scalar()

    # Check code_chunks
    result = db_session.execute(text("""
        SELECT COUNT(*) FROM code_chunks
        WHERE project_id !~ '^[a-z0-9-]{1,50}$'
    """))
    chunks_invalid = result.scalar()

    assert repos_invalid == 0, f"Found {repos_invalid} repositories with invalid project_id"
    assert chunks_invalid == 0, f"Found {chunks_invalid} code_chunks with invalid project_id"
```

**Pass Criteria**: No invalid patterns

#### V6.2: No Uppercase Letters

**Test Function**: `test_post_migration_no_uppercase()`

**Implementation**:
```python
def test_post_migration_no_uppercase(db_session):
    """Verify no uppercase letters in project_id"""
    result = db_session.execute(text("""
        SELECT COUNT(*) FROM (
          SELECT project_id FROM repositories
          UNION ALL
          SELECT project_id FROM code_chunks
        ) all_project_ids
        WHERE project_id ~ '[A-Z]'
    """))
    uppercase_count = result.scalar()

    assert uppercase_count == 0, f"Found {uppercase_count} project_ids with uppercase letters"
```

**Pass Criteria**: No uppercase letters

#### V6.3: No Underscores or Spaces

**Test Function**: `test_post_migration_no_invalid_chars()`

**Implementation**:
```python
def test_post_migration_no_invalid_chars(db_session):
    """Verify no underscores or spaces in project_id"""
    result = db_session.execute(text("""
        SELECT COUNT(*) FROM (
          SELECT project_id FROM repositories
          UNION ALL
          SELECT project_id FROM code_chunks
        ) all_project_ids
        WHERE project_id ~ '[_ ]'
    """))
    invalid_count = result.scalar()

    assert invalid_count == 0, f"Found {invalid_count} project_ids with underscores or spaces"
```

**Pass Criteria**: No invalid characters

#### V6.4: Length Boundaries

**Test Function**: `test_post_migration_length_boundaries()`

**Implementation**:
```python
def test_post_migration_length_boundaries(db_session):
    """Verify all project_id lengths between 1 and 50"""
    result = db_session.execute(text("""
        SELECT
          MIN(LENGTH(project_id)) AS min_length,
          MAX(LENGTH(project_id)) AS max_length
        FROM (
          SELECT project_id FROM repositories
          UNION ALL
          SELECT project_id FROM code_chunks
        ) all_project_ids
    """))
    row = result.fetchone()

    assert row.min_length >= 1, f"Minimum length {row.min_length} < 1"
    assert row.max_length <= 50, f"Maximum length {row.max_length} > 50"
```

**Pass Criteria**:
- min_length >= 1
- max_length <= 50

### V7: Foreign Key Validation (Pre-Migration)

#### V7.1: No Foreign Keys to Core Tables

**Test Function**: `test_pre_migration_no_blocking_foreign_keys()`

**Purpose**: Verify no foreign keys from dropped tables to repositories/code_chunks

**Implementation**:
```python
def test_pre_migration_no_blocking_foreign_keys(db_session):
    """Verify no FKs from dropped tables to core tables"""
    dropped_tables = [
        'work_items', 'work_item_dependencies', 'tasks',
        'task_branches', 'task_commits', 'vendors',
        'vendor_test_results', 'deployments', 'deployment_vendors'
    ]

    result = db_session.execute(text("""
        SELECT
          tc.table_name AS source_table,
          kcu.column_name AS source_column,
          ccu.table_name AS target_table,
          ccu.column_name AS target_column,
          tc.constraint_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu
          ON tc.constraint_name = ccu.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
          AND tc.table_name = ANY(:source_tables)
          AND ccu.table_name IN ('repositories', 'code_chunks')
    """), {'source_tables': dropped_tables})

    blocking_fks = result.fetchall()

    if blocking_fks:
        details = [f"{fk.source_table}.{fk.source_column} -> {fk.target_table}.{fk.target_column}"
                   for fk in blocking_fks]
        pytest.fail(f"Found {len(blocking_fks)} blocking foreign keys:\n" + "\n".join(details))
```

**Pass Criteria**: No blocking foreign keys

**Fail Actions**: Test fails with list of blocking foreign keys

### V8: Performance Validation

#### V8.1: Migration Duration (Post-Migration)

**Test Function**: `test_migration_performance()`

**Purpose**: Verify migration completed within 5 minutes

**Implementation**:
```python
import time

def test_migration_performance(db_session, test_database_url):
    """Verify migration completes within 5 minutes"""
    import subprocess

    start_time = time.time()

    # Run migration
    result = subprocess.run(
        ['alembic', 'upgrade', 'head'],
        env={'DATABASE_URL': test_database_url},
        capture_output=True,
        text=True
    )

    duration = time.time() - start_time

    assert result.returncode == 0, f"Migration failed:\n{result.stderr}"
    assert duration < 300, f"Migration took {duration:.2f}s (exceeds 5 minute limit)"

    print(f"Migration completed in {duration:.2f}s")
```

**Pass Criteria**: Duration < 300 seconds (5 minutes)

**Note**: This test is typically run separately in performance test suite

## Test Suite Structure

**File**: `tests/integration/test_migration_002_validation.py`

```python
"""
Validation tests for migration 002
Tests verify schema changes are correctly applied and rolled back
"""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

@pytest.fixture(scope="module")
def db_engine(test_database_url):
    """Create database engine for tests"""
    engine = create_engine(test_database_url)
    yield engine
    engine.dispose()

@pytest.fixture
def db_session(db_engine):
    """Create database session for each test"""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

# Post-migration validation tests
class TestPostMigrationValidation:
    """Tests to run after alembic upgrade head"""

    def test_column_existence_repositories(self, db_session):
        # Implementation from V1.1
        pass

    def test_column_existence_code_chunks(self, db_session):
        # Implementation from V1.2
        pass

    def test_check_constraints(self, db_session):
        # Implementation from V2.1
        pass

    # ... (all V1-V6 tests)

# Post-rollback validation tests
class TestPostRollbackValidation:
    """Tests to run after alembic downgrade -1"""

    def test_columns_removed(self, db_session):
        # Implementation from V1.3
        pass

    def test_constraints_removed(self, db_session):
        # Implementation from V2.2
        pass

    # ... (all rollback tests)

# Pre-migration validation tests (optional)
class TestPreMigrationValidation:
    """Tests to run before alembic upgrade head"""

    def test_no_blocking_foreign_keys(self, db_session):
        # Implementation from V7.1
        pass
```

## Execution Commands

### Run All Validation Tests

```bash
# Set database connection
export DATABASE_URL=postgresql://localhost/codebase_mcp_test

# Run all validation tests
pytest tests/integration/test_migration_002_validation.py -v

# Run specific test class
pytest tests/integration/test_migration_002_validation.py::TestPostMigrationValidation -v
pytest tests/integration/test_migration_002_validation.py::TestPostRollbackValidation -v

# Run specific test
pytest tests/integration/test_migration_002_validation.py::TestPostMigrationValidation::test_column_existence_repositories -v
```

### Validation Workflow

**1. Pre-Migration (Optional)**:
```bash
pytest tests/integration/test_migration_002_validation.py::TestPreMigrationValidation -v
```

**2. Run Migration**:
```bash
alembic upgrade head
```

**3. Post-Migration Validation** (Required):
```bash
pytest tests/integration/test_migration_002_validation.py::TestPostMigrationValidation -v
```

**4. Run Rollback**:
```bash
alembic downgrade -1
```

**5. Post-Rollback Validation** (Required):
```bash
pytest tests/integration/test_migration_002_validation.py::TestPostRollbackValidation -v
```

## Exit Codes

- **0**: All tests passed
- **1**: One or more tests failed
- **>1**: Test framework error

## Test Coverage Requirements

### Required Tests (FR-026)
Pattern validation must test at least 10 invalid patterns:
1. `My-Project` (uppercase)
2. `my_project` (underscore)
3. `my project` (space)
4. `-my-project` (leading hyphen)
5. `my-project-` (trailing hyphen)
6. `my--project` (consecutive hyphens)
7. `` (empty string)
8. `a-very-long-project-name-exceeding-fifty-character-limit` (> 50 chars)
9. `'; DROP TABLE repositories; --` (SQL injection)
10. `../../../etc/passwd` (path traversal)

**Test Function**: `test_pattern_validation_invalid_patterns()` in unit test suite

## Integration with CI/CD

```yaml
# .github/workflows/test-migration-002.yml
name: Test Migration 002

on: [push, pull_request]

jobs:
  test-migration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -e .

      - name: Run pre-migration tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
        run: pytest tests/integration/test_migration_002_validation.py::TestPreMigrationValidation -v

      - name: Run migration
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
        run: alembic upgrade head

      - name: Run post-migration validation
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
        run: pytest tests/integration/test_migration_002_validation.py::TestPostMigrationValidation -v

      - name: Run rollback
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
        run: alembic downgrade -1

      - name: Run post-rollback validation
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
        run: pytest tests/integration/test_migration_002_validation.py::TestPostRollbackValidation -v
```

## Next Phase

**Phase 2** (via /tasks command): Generate task list
- Task: Implement all validation test functions in `test_migration_002_validation.py`
- Task: Write integration tests for upgrade/downgrade
- Task: Write performance tests measuring duration
