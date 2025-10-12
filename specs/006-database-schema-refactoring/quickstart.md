# Quickstart: Migration 002 Execution
**Feature**: Database Schema Refactoring for Multi-Project Support
**Estimated Time**: 15-30 minutes
**Date**: 2025-10-11

## Overview

This quickstart guides you through executing migration 002 using **Alembic** (the project's existing migration framework). It covers all test scenarios from the specification and provides step-by-step validation procedures.

## Prerequisites

### Required Tools
- PostgreSQL 14+ with pgvector extension
- Python 3.11+ with dependencies installed (`uv sync` or `pip install -r requirements.txt`)
- Alembic migration framework (installed with project dependencies)
- pytest (for automated validation tests)
- Database backup tool (`pg_dump`)

### Environment Setup

```bash
# 1. Verify PostgreSQL version
psql --version  # Should be 14.x or higher

# 2. Set DATABASE_URL environment variable
export DATABASE_URL=postgresql://localhost/codebase_mcp

# 3. Verify database exists and pgvector extension is installed
psql $DATABASE_URL -c "SELECT version();"
psql $DATABASE_URL -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

# 4. Create test database (if testing first)
createdb codebase_mcp_test
psql postgresql://localhost/codebase_mcp_test -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 5. Verify Alembic configuration
alembic --version  # Should show Alembic version
alembic current     # Shows current migration state
```

## Scenario 1: Fresh Database Migration

**Goal**: Execute migration on empty database, verify schema changes

**Duration**: ~5 minutes

### Step 1.1: Prepare Test Database

```bash
# Drop and recreate test database (CAUTION: Destroys all data)
dropdb codebase_mcp_test 2>/dev/null || true
createdb codebase_mcp_test
psql postgresql://localhost/codebase_mcp_test -c "CREATE EXTENSION vector;"

# Set DATABASE_URL for test database
export DATABASE_URL=postgresql://localhost/codebase_mcp_test

# Apply baseline schema (migrations up to 005)
alembic upgrade 005
```

**Expected Output**:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001, Initial schema
INFO  [alembic.runtime.migration] Running upgrade 001 -> 003, Project tracking
INFO  [alembic.runtime.migration] Running upgrade 003 -> 005, Case insensitive vendor name
```

### Step 1.2: Run Pre-Migration Validation

```bash
# Run pre-migration validation tests
pytest tests/integration/test_migration_002_validation.py::TestPreMigrationValidation -v
```

**Expected Output**:
```
tests/integration/test_migration_002_validation.py::TestPreMigrationValidation::test_no_blocking_foreign_keys PASSED

✓ No foreign keys found from dropped tables to repositories/code_chunks
✓ All pre-migration checks passed (1/1)
```

### Step 1.3: Execute Forward Migration

```bash
# Upgrade to migration 002
DATABASE_URL=postgresql://localhost/codebase_mcp_test alembic upgrade head

# Or if DATABASE_URL already in environment
alembic upgrade head
```

**Expected Output**:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 005 -> 002, Remove non-search tables and add project_id columns
INFO  [migration.002] Step 1/10: Checking prerequisites...
INFO  [migration.002] Step 1/10: Complete
INFO  [migration.002] Step 2/10: Verifying foreign key constraints...
NOTICE:  No blocking foreign keys found
INFO  [migration.002] Step 2/10: Complete
INFO  [migration.002] Step 3/10: Adding project_id to repositories table...
NOTICE:  Column added with default 'default'
INFO  [migration.002] Step 3/10: Complete
INFO  [migration.002] Step 4/10: Adding project_id to code_chunks table...
NOTICE:  Column added, populated from parent repositories
INFO  [migration.002] Step 4/10: Complete
INFO  [migration.002] Step 5/10: Adding validation constraints...
NOTICE:  CHECK constraints added
INFO  [migration.002] Step 5/10: Complete
INFO  [migration.002] Step 6/10: Creating performance index...
NOTICE:  Index idx_project_repository created
INFO  [migration.002] Step 6/10: Complete
INFO  [migration.002] Step 7/10: Dropping unused tables...
NOTICE:  9 tables dropped
INFO  [migration.002] Step 7/10: Complete
INFO  [migration.002] Step 8/10: Running validation checks...
INFO  [migration.002] Step 8/10: Complete - All validations passed
INFO  [migration.002] Migration 002 completed successfully in 0.05s
INFO  [alembic.runtime.migration] Running upgrade 005 -> 002
```

### Step 1.4: Verify Migration Applied

```bash
# Check current migration state
alembic current

# View migration history
alembic history --verbose
```

**Expected Output**:
```
$ alembic current
002 (head)

$ alembic history
005 -> 002 (head), Remove non-search tables and add project_id columns
003a -> 005, Fix version column for optimistic locking
003 -> 003a, Add missing work item columns
001 -> 003, Project tracking
<base> -> 001, Initial schema
```

### Step 1.5: Run Post-Migration Validation

```bash
# Run all post-migration validation tests
pytest tests/integration/test_migration_002_validation.py::TestPostMigrationValidation -v
```

**Expected Output**:
```
tests/integration/test_migration_002_validation.py::TestPostMigrationValidation::test_column_existence_repositories PASSED
tests/integration/test_migration_002_validation.py::TestPostMigrationValidation::test_column_existence_code_chunks PASSED
tests/integration/test_migration_002_validation.py::TestPostMigrationValidation::test_check_constraints_exist PASSED
tests/integration/test_migration_002_validation.py::TestPostMigrationValidation::test_performance_index_exists PASSED
tests/integration/test_migration_002_validation.py::TestPostMigrationValidation::test_unused_tables_dropped PASSED
tests/integration/test_migration_002_validation.py::TestPostMigrationValidation::test_data_integrity_check PASSED
tests/integration/test_migration_002_validation.py::TestPostMigrationValidation::test_pattern_validation_check PASSED
tests/integration/test_migration_002_validation.py::TestPostMigrationValidation::test_no_orphaned_chunks PASSED

✓ project_id column exists in repositories (VARCHAR(50), NOT NULL, DEFAULT 'default')
✓ project_id column exists in code_chunks (VARCHAR(50), NOT NULL)
✓ CHECK constraints exist (2 found)
✓ Performance index exists (idx_project_repository)
✓ Unused tables dropped (0 of 9 tables found)
✓ Data integrity check (all code_chunks have matching repository project_id)
✓ Pattern validation (all project_id values match ^[a-z0-9-]{1,50}$)
✓ No orphaned code_chunks

========== 8 passed in 0.25s ==========
```

### Step 1.6: Verify Schema Changes

```bash
# Check repositories table structure
psql $DATABASE_URL -c "\d repositories"

# Check code_chunks table structure
psql $DATABASE_URL -c "\d code_chunks"

# List all tables (should only see repositories and code_chunks)
psql $DATABASE_URL -c "\dt"
```

**Expected Output** (repositories):
```
                                            Table "public.repositories"
   Column    |           Type           | Collation | Nullable |           Default
-------------|--------------------------|-----------|----------|------------------------------
 id          | uuid                     |           | not null | gen_random_uuid()
 path        | text                     |           | not null |
 project_id  | character varying(50)    |           | not null | 'default'::character varying
 indexed_at  | timestamp with time zone |           | not null |
 metadata    | jsonb                    |           |          |
 ...

Check constraints:
    "check_repositories_project_id" CHECK (project_id ~ '^[a-z0-9-]{1,50}$'::text)
```

**Pass Criteria**: ✅ Migration executed successfully on fresh database

---

## Scenario 2: Migration with Existing Data

**Goal**: Execute migration on database with sample data, verify data preservation

**Duration**: ~10 minutes

### Step 2.1: Prepare Database with Sample Data

```bash
# Start from Scenario 1 baseline
dropdb codebase_mcp_test 2>/dev/null || true
createdb codebase_mcp_test
psql postgresql://localhost/codebase_mcp_test -c "CREATE EXTENSION vector;"

# Set DATABASE_URL
export DATABASE_URL=postgresql://localhost/codebase_mcp_test

# Apply baseline schema (up to migration 005)
alembic upgrade 005

# Insert sample data
psql $DATABASE_URL <<EOF
-- Insert 3 repositories
INSERT INTO repositories (id, path, indexed_at) VALUES
  ('00000000-0000-0000-0000-000000000001', '/test/repo1', NOW()),
  ('00000000-0000-0000-0000-000000000002', '/test/repo2', NOW()),
  ('00000000-0000-0000-0000-000000000003', '/test/repo3', NOW());

-- Insert 6 code chunks (2 per repository)
INSERT INTO code_chunks (repository_id, file_path, content, start_line, end_line) VALUES
  ('00000000-0000-0000-0000-000000000001', 'main.py', 'print("hello")', 1, 1),
  ('00000000-0000-0000-0000-000000000001', 'utils.py', 'def foo(): pass', 1, 1),
  ('00000000-0000-0000-0000-000000000002', 'app.py', 'import flask', 1, 1),
  ('00000000-0000-0000-0000-000000000002', 'models.py', 'class User: pass', 1, 1),
  ('00000000-0000-0000-0000-000000000003', 'test.py', 'assert True', 1, 1),
  ('00000000-0000-0000-0000-000000000003', 'lib.py', 'def bar(): return 42', 1, 1);
EOF
```

### Step 2.2: Record Baseline Counts

```bash
psql $DATABASE_URL -c "SELECT COUNT(*) AS repo_count FROM repositories;"
# Expected: repo_count = 3

psql $DATABASE_URL -c "SELECT COUNT(*) AS chunk_count FROM code_chunks;"
# Expected: chunk_count = 6
```

### Step 2.3: Execute Migration

```bash
alembic upgrade head
```

**Expected Output**: (Same as Scenario 1, Step 1.3)

### Step 2.4: Verify Data Preservation

```bash
# Check row counts (should match baseline)
psql $DATABASE_URL -c "SELECT COUNT(*) AS repo_count FROM repositories;"
# Expected: repo_count = 3

psql $DATABASE_URL -c "SELECT COUNT(*) AS chunk_count FROM code_chunks;"
# Expected: chunk_count = 6

# Check project_id assignment
psql $DATABASE_URL -c "SELECT id, path, project_id FROM repositories;"
# Expected: All rows have project_id = 'default'

psql $DATABASE_URL -c "
SELECT cc.id, cc.file_path, cc.project_id, r.project_id AS parent_project_id
FROM code_chunks cc
JOIN repositories r ON cc.repository_id = r.id;
"
# Expected: All cc.project_id = r.project_id = 'default'
```

**Pass Criteria**: ✅ All data preserved, project_id correctly assigned

---

## Scenario 3: Idempotency Test

**Goal**: Run upgrade command twice, verify second run is safe no-op

**Duration**: ~5 minutes

### Step 3.1: Execute Migration First Time

```bash
# Start from Scenario 2 state (migration already applied)
# OR run migration fresh on test database
alembic current  # Should show: 002 (head)
```

### Step 3.2: Execute Migration Second Time

```bash
alembic upgrade head
```

**Expected Output**:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 002
```

**Note**: Alembic automatically tracks applied migrations in the `alembic_version` table. Running `upgrade head` when already at head is a safe no-op.

### Step 3.3: Verify No Changes

```bash
# Check migration state (should still be 002)
alembic current
# Expected: 002 (head)

# Check row counts (should be unchanged)
psql $DATABASE_URL -c "SELECT COUNT(*) FROM repositories;"
# Expected: 3

psql $DATABASE_URL -c "SELECT COUNT(*) FROM code_chunks;"
# Expected: 6

# Run validation (should still pass)
pytest tests/integration/test_migration_002_validation.py::TestPostMigrationValidation -v
```

**Pass Criteria**: ✅ Second run is safe, no changes made, validation passes

---

## Scenario 4: Rollback Test

**Goal**: Apply migration, execute rollback, verify schema restoration

**Duration**: ~10 minutes

### Step 4.1: Apply Migration

```bash
# Start from Scenario 2 state (migration applied with data)
alembic current  # Should show: 002 (head)
```

### Step 4.2: Record Post-Migration State

```bash
# Save schema for comparison
pg_dump -h localhost -U postgres -d codebase_mcp_test --schema-only > /tmp/post_migration_schema.sql

# Save row counts
psql $DATABASE_URL -c "SELECT COUNT(*) FROM repositories;" > /tmp/post_migration_counts.txt
psql $DATABASE_URL -c "SELECT COUNT(*) FROM code_chunks;" >> /tmp/post_migration_counts.txt
```

### Step 4.3: Execute Rollback

```bash
# Downgrade one revision (from 002 to 005)
DATABASE_URL=postgresql://localhost/codebase_mcp_test alembic downgrade -1

# Or downgrade to specific revision
alembic downgrade 005
```

**Expected Output**:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running downgrade 002 -> 005, Rollback: Remove non-search tables
INFO  [migration.002] Rollback Step 1/6: Dropping performance index...
INFO  [migration.002] Rollback Step 1/6: Complete
INFO  [migration.002] Rollback Step 2/6: Dropping validation constraints...
INFO  [migration.002] Rollback Step 2/6: Complete
INFO  [migration.002] Rollback Step 3/6: Dropping project_id from code_chunks...
INFO  [migration.002] Rollback Step 3/6: Complete
INFO  [migration.002] Rollback Step 4/6: Dropping project_id from repositories...
INFO  [migration.002] Rollback Step 4/6: Complete
INFO  [migration.002] Rollback Step 5/6: Restoring dropped tables (schema only)...
WARNING:  Data in dropped tables NOT restored. Restore from backup if needed.
INFO  [migration.002] Rollback Step 5/6: Complete - 9 tables restored
INFO  [migration.002] Rollback Step 6/6: Running validation...
INFO  [migration.002] Rollback Step 6/6: Complete
INFO  [migration.002] Migration 002 rollback completed successfully in 0.03s
INFO  [alembic.runtime.migration] Running downgrade 002 -> 005
```

### Step 4.4: Verify Rollback Applied

```bash
# Check current migration state
alembic current
# Expected: 005

# View migration history
alembic history
```

### Step 4.5: Run Post-Rollback Validation

```bash
# Run all post-rollback validation tests
pytest tests/integration/test_migration_002_validation.py::TestPostRollbackValidation -v
```

**Expected Output**:
```
tests/integration/test_migration_002_validation.py::TestPostRollbackValidation::test_columns_removed PASSED
tests/integration/test_migration_002_validation.py::TestPostRollbackValidation::test_constraints_removed PASSED
tests/integration/test_migration_002_validation.py::TestPostRollbackValidation::test_index_removed PASSED
tests/integration/test_migration_002_validation.py::TestPostRollbackValidation::test_tables_restored PASSED
tests/integration/test_migration_002_validation.py::TestPostRollbackValidation::test_repositories_data_preserved PASSED
tests/integration/test_migration_002_validation.py::TestPostRollbackValidation::test_code_chunks_data_preserved PASSED

✓ project_id columns removed (0 columns found)
✓ CHECK constraints removed (0 constraints found)
✓ Performance index removed (idx_project_repository not found)
✓ Dropped tables restored (9 tables found)
✓ repositories data preserved (row count matches baseline: 3 rows)
✓ code_chunks data preserved (row count matches baseline: 6 rows)

========== 6 passed in 0.18s ==========
```

### Step 4.6: Verify Schema Restoration

```bash
# Check repositories table (project_id column should be gone)
psql $DATABASE_URL -c "\d repositories"

# Check all tables exist (should see 11 tables: 2 core + 9 restored)
psql $DATABASE_URL -c "\dt"

# Verify row counts unchanged
psql $DATABASE_URL -c "SELECT COUNT(*) FROM repositories;"
# Expected: 3

psql $DATABASE_URL -c "SELECT COUNT(*) FROM code_chunks;"
# Expected: 6
```

**Pass Criteria**: ✅ Schema restored to pre-migration state, data preserved

---

## Scenario 5: Performance Test

**Goal**: Execute on 100 repos + 10K chunks, verify < 5 minute duration

**Duration**: ~15 minutes (includes data generation)

### Step 5.1: Generate Performance Test Data

```bash
# Run test data generation script
python tests/fixtures/generate_test_data.py \
  --database codebase_mcp_test \
  --repositories 100 \
  --chunks-per-repo 100

# Verify row counts
psql $DATABASE_URL -c "SELECT COUNT(*) FROM repositories;"
# Expected: 100

psql $DATABASE_URL -c "SELECT COUNT(*) FROM code_chunks;"
# Expected: 10,000
```

### Step 5.2: Execute Migration with Timing

```bash
# Time the migration execution
time alembic upgrade head
```

**Expected Duration**: < 5 minutes (300 seconds per FR-031)

**Sample Output**:
```
INFO  [migration.002] Migration 002 completed successfully in 12.35s
INFO  [alembic.runtime.migration] Running upgrade 005 -> 002

real    0m12.450s
user    0m0.523s
sys     0m0.112s
```

### Step 5.3: Verify Performance Metrics

```bash
# Check Python logger output for step timing breakdown
grep "Step" /tmp/codebase-mcp-migration.log
```

**Expected Breakdown**:
```
INFO [migration.002] Step 1/10: 0.01s (prerequisites)
INFO [migration.002] Step 2/10: 0.05s (foreign key check)
INFO [migration.002] Step 3/10: 0.10s (add repositories.project_id)
INFO [migration.002] Step 4/10: 2.50s (add + populate code_chunks.project_id)
INFO [migration.002] Step 5/10: 0.20s (add constraints)
INFO [migration.002] Step 6/10: 8.50s (create index on 10K+ rows)
INFO [migration.002] Step 7/10: 0.50s (drop 9 tables)
INFO [migration.002] Step 8/10: 0.50s (validation)
INFO [migration.002] Total: 12.36s
```

**Pass Criteria**: ✅ Migration completes in < 5 minutes (FR-031 satisfied)

---

## Scenario 6: Validation Test

**Goal**: Attempt invalid project_id insertions, verify CHECK constraint rejection

**Duration**: ~5 minutes

### Step 6.1: Apply Migration

```bash
# Start from Scenario 1 state (migration applied, no data)
alembic current  # Should show: 002 (head)
```

### Step 6.2: Test Valid Insertions

```bash
psql $DATABASE_URL <<EOF
-- Valid project_id patterns (should succeed)
INSERT INTO repositories (path, project_id, indexed_at) VALUES
  ('/test/repo1', 'default', NOW()),
  ('/test/repo2', 'my-project', NOW()),
  ('/test/repo3', 'proj-123', NOW()),
  ('/test/repo4', 'a', NOW()),  -- minimum length
  ('/test/repo5', 'a-very-long-project-name-with-exactly-fifty-ch', NOW());  -- max length

SELECT path, project_id FROM repositories;
EOF
```

**Expected Output**: 5 rows inserted successfully

### Step 6.3: Test Invalid Patterns (FR-026)

```bash
# Test 1: Uppercase letters
psql $DATABASE_URL <<EOF
INSERT INTO repositories (path, project_id, indexed_at)
VALUES ('/test/fail1', 'My-Project', NOW());
EOF
```

**Expected Error**:
```
ERROR:  new row for relation "repositories" violates check constraint "check_repositories_project_id"
DETAIL:  Failing row contains (..., My-Project, ...).
```

```bash
# Test 2: Underscore
psql $DATABASE_URL -c "
INSERT INTO repositories (path, project_id, indexed_at)
VALUES ('/test/fail2', 'my_project', NOW());
"
# Expected: CHECK constraint violation

# Test 3: Space
psql $DATABASE_URL -c "
INSERT INTO repositories (path, project_id, indexed_at)
VALUES ('/test/fail3', 'my project', NOW());
"
# Expected: CHECK constraint violation

# Test 4: Leading hyphen
psql $DATABASE_URL -c "
INSERT INTO repositories (path, project_id, indexed_at)
VALUES ('/test/fail4', '-my-project', NOW());
"
# Expected: CHECK constraint violation

# Test 5: Trailing hyphen
psql $DATABASE_URL -c "
INSERT INTO repositories (path, project_id, indexed_at)
VALUES ('/test/fail5', 'my-project-', NOW());
"
# Expected: CHECK constraint violation

# Test 6: Empty string
psql $DATABASE_URL -c "
INSERT INTO repositories (path, project_id, indexed_at)
VALUES ('/test/fail6', '', NOW());
"
# Expected: CHECK constraint violation

# Test 7: Exceeds 50 characters
psql $DATABASE_URL -c "
INSERT INTO repositories (path, project_id, indexed_at)
VALUES ('/test/fail7', 'this-is-a-very-long-project-name-that-exceeds-fifty-characters-limit', NOW());
"
# Expected: CHECK constraint violation (also VARCHAR(50) truncation error)

# Test 8: SQL injection attempt
psql $DATABASE_URL -c "
INSERT INTO repositories (path, project_id, indexed_at)
VALUES ('/test/fail8', '''; DROP TABLE repositories; --', NOW());
"
# Expected: CHECK constraint violation

# Test 9: Path traversal attempt
psql $DATABASE_URL -c "
INSERT INTO repositories (path, project_id, indexed_at)
VALUES ('/test/fail9', '../../../etc/passwd', NOW());
"
# Expected: CHECK constraint violation

# Test 10: Special characters
psql $DATABASE_URL -c "
INSERT INTO repositories (path, project_id, indexed_at)
VALUES ('/test/fail10', 'project@#$%', NOW());
"
# Expected: CHECK constraint violation
```

**Pass Criteria**: ✅ All 10 invalid patterns rejected (FR-026 satisfied)

---

## Production Deployment Checklist

### Pre-Deployment

- [ ] All 6 test scenarios passed in development
- [ ] Migration tested on copy of production database (FR-027)
- [ ] Rollback tested successfully (FR-029)
- [ ] Performance validated (< 5 minutes on realistic data - FR-031)
- [ ] Database backup created
- [ ] Maintenance window scheduled
- [ ] Rollback procedure documented and reviewed
- [ ] `alembic current` shows revision 005 or earlier

### Deployment Steps

1. **Create Backup**
   ```bash
   pg_dump -h prod-db -U postgres -d codebase_mcp > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Stop Application Services**
   ```bash
   systemctl stop codebase-mcp-server
   ```

3. **Verify Current State**
   ```bash
   DATABASE_URL=postgresql://prod-db/codebase_mcp alembic current
   # Should show revision 005 or earlier
   ```

4. **Run Pre-Migration Validation**
   ```bash
   DATABASE_URL=postgresql://prod-db/codebase_mcp \
     pytest tests/integration/test_migration_002_validation.py::TestPreMigrationValidation -v
   ```

5. **Execute Migration**
   ```bash
   DATABASE_URL=postgresql://prod-db/codebase_mcp alembic upgrade head
   ```

6. **Verify Migration Applied**
   ```bash
   DATABASE_URL=postgresql://prod-db/codebase_mcp alembic current
   # Should show: 002 (head)
   ```

7. **Run Post-Migration Validation**
   ```bash
   DATABASE_URL=postgresql://prod-db/codebase_mcp \
     pytest tests/integration/test_migration_002_validation.py::TestPostMigrationValidation -v
   ```

8. **Restart Application Services**
   ```bash
   systemctl start codebase-mcp-server
   ```

9. **Monitor Logs**
   ```bash
   tail -f /tmp/codebase-mcp.log
   tail -f /tmp/codebase-mcp-migration.log
   journalctl -u codebase-mcp-server -f
   ```

### Post-Deployment Verification

- [ ] `alembic current` shows 002
- [ ] Validation tests pass (8/8 checks)
- [ ] Application starts successfully
- [ ] Search queries work correctly
- [ ] No errors in application logs

### Rollback (if needed)

1. **Stop Application Services**
   ```bash
   systemctl stop codebase-mcp-server
   ```

2. **Execute Rollback**
   ```bash
   DATABASE_URL=postgresql://prod-db/codebase_mcp alembic downgrade -1
   ```

3. **Verify Rollback**
   ```bash
   DATABASE_URL=postgresql://prod-db/codebase_mcp alembic current
   # Should show: 005

   DATABASE_URL=postgresql://prod-db/codebase_mcp \
     pytest tests/integration/test_migration_002_validation.py::TestPostRollbackValidation -v
   ```

4. **Restore Dropped Table Data** (if needed)
   ```bash
   pg_restore -d codebase_mcp --table=work_items --table=tasks ... backup.dump
   ```

5. **Restart Application Services**
   ```bash
   systemctl start codebase-mcp-server
   ```

## Troubleshooting

### Issue: Foreign Key Violation

**Symptom**: Migration fails with "Foreign key constraint detected"

**Solution**:
```bash
# Identify blocking foreign key
psql -d codebase_mcp -c "
SELECT tc.table_name, tc.constraint_name
FROM information_schema.table_constraints tc
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_name IN ('work_items', 'tasks', ...)
";

# Drop blocking foreign key
psql -d codebase_mcp -c "ALTER TABLE work_items DROP CONSTRAINT fk_name;";

# Re-run migration
alembic upgrade head
```

### Issue: Orphaned Code Chunks

**Symptom**: Migration fails with "NULL project_id (orphaned chunks)"

**Solution**:
```bash
# Identify orphaned chunks
psql -d codebase_mcp -c "
SELECT cc.id, cc.file_path, cc.repository_id
FROM code_chunks cc
LEFT JOIN repositories r ON cc.repository_id = r.id
WHERE r.id IS NULL;
";

# Delete orphaned chunks
psql -d codebase_mcp -c "
DELETE FROM code_chunks
WHERE repository_id NOT IN (SELECT id FROM repositories);
";

# Re-run migration
alembic upgrade head
```

### Issue: Performance Timeout

**Symptom**: Migration exceeds 5 minutes

**Solution**:
```bash
# Run VACUUM ANALYZE on tables
psql -d codebase_mcp -c "VACUUM ANALYZE repositories; VACUUM ANALYZE code_chunks;";

# Check for blocking queries
psql -d codebase_mcp -c "SELECT * FROM pg_stat_activity WHERE state = 'active';";

# Re-run migration
alembic upgrade head
```

### Issue: Alembic Version Conflict

**Symptom**: `alembic current` shows unexpected revision

**Solution**:
```bash
# Check current state
alembic current

# View migration history
alembic history --verbose

# If database is out of sync, manually set revision
# CAUTION: Only use if you're certain of the database state
alembic stamp 005

# Then retry upgrade
alembic upgrade head
```

## Advanced: Concurrent Index Creation

For large production databases (>10K repositories), consider creating the index with `CONCURRENTLY` before running the migration:

**Note**: This is optional and requires manual steps. Use only if index creation time is a concern.

```bash
# 1. Connect to database
psql -d codebase_mcp

# 2. Create index concurrently (non-blocking)
CREATE INDEX CONCURRENTLY idx_project_repository ON repositories(project_id, id);

# 3. Comment out index creation in migration
# Edit migrations/versions/002_remove_non_search_tables.py:
# # op.create_index('idx_project_repository', ...)  # Already created manually

# 4. Run migration (will skip index creation)
alembic upgrade head
```

**Warning**: `CONCURRENTLY` cannot run inside a transaction, so it's incompatible with Alembic's transactional approach. Only use this for very large production databases where index creation is the bottleneck.

## Summary

This quickstart covered:
- ✅ Fresh database migration (Scenario 1)
- ✅ Migration with existing data (Scenario 2)
- ✅ Idempotency testing (Scenario 3)
- ✅ Rollback testing (Scenario 4)
- ✅ Performance validation (Scenario 5)
- ✅ Security validation (Scenario 6)

All 31 functional requirements from spec.md are validated through these scenarios using **Alembic** migration framework and **pytest** validation test suites.

**Next Steps**:
- Execute `/tasks` command to generate implementation task list
- Implement Alembic migrations following TDD approach
- Run automated integration tests (`pytest tests/integration/test_migration_002*.py`)
