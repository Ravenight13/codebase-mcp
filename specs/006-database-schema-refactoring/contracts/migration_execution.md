# Migration Execution Contract
**Feature**: Database Schema Refactoring for Multi-Project Support
**Migration**: 002_remove_non_search_tables
**Tool**: Alembic (existing migration framework)
**Date**: 2025-10-11

## Contract Overview

This document defines the execution contract for migration 002 using **Alembic**, the existing migration framework for this project. Alembic provides automatic tracking, transactional safety, and standardized upgrade/downgrade commands.

## Execution Interface

### Forward Migration (Upgrade)

**Migration File**: `migrations/versions/002_remove_non_search_tables.py`

**Prerequisites**:
- PostgreSQL 14+ database with pgvector extension
- Database backup created (Phase 00 requirement)
- Alembic configured (migrations/env.py exists)
- `DATABASE_URL` environment variable set or alembic.ini configured
- Python 3.11+ with dependencies installed (`uv sync` or `pip install -r requirements.txt`)

**Execution Command**:
```bash
# Standard upgrade to latest
DATABASE_URL=postgresql://localhost/codebase_mcp alembic upgrade head

# Or if DATABASE_URL already in environment
alembic upgrade head

# Upgrade to specific revision
alembic upgrade 002
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
INFO  [migration.002] Migration 002 completed successfully in 12.35s
INFO  [alembic.runtime.migration] Running upgrade 005 -> 002
```

**Success Criteria**:
- Command exits with code 0
- No ERROR or CRITICAL log messages
- `alembic current` shows revision 002
- Execution time < 5 minutes (FR-031)

**Failure Behavior**:
- Any exception causes automatic ROLLBACK (Alembic transaction handling)
- Database returns to pre-migration state
- Error includes Python stack trace and SQL error context
- `alembic current` still shows 005 (migration not applied)
- Exit code 1

### Rollback Migration (Downgrade)

**Downgrade Function**: `downgrade()` in same migration file

**Prerequisites**:
- Migration 002 has been applied (`alembic current` shows 002 or later)
- Database backup available (for data restoration if needed)
- `DATABASE_URL` configured

**Execution Command**:
```bash
# Downgrade one revision
DATABASE_URL=postgresql://localhost/codebase_mcp alembic downgrade -1

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
INFO  [migration.002] Migration 002 rollback completed successfully in 0.85s
INFO  [alembic.runtime.migration] Running downgrade 002 -> 005
```

**Success Criteria**:
- Command exits with code 0
- Schema matches pre-migration state
- repositories and code_chunks data preserved
- `alembic current` shows revision 005

**Data Restoration** (manual, if needed):
```bash
# Restore dropped tables data from backup
pg_restore -h localhost -U postgres -d codebase_mcp \
  --table=work_items --table=tasks ... backup_file.dump
```

### Migration Status

**Check Current State**:
```bash
# Show current revision
alembic current

# Show migration history
alembic history --verbose

# Show pending migrations
alembic heads
```

**Expected Output** (after migration 002):
```bash
$ alembic current
002 (head)

$ alembic history
005 -> 002 (head), Remove non-search tables and add project_id columns
003a -> 005, Fix version column for optimistic locking
003 -> 003a, Add missing work item columns
001 -> 003, Project tracking
<base> -> 001, Initial schema
```

### Validation

**Validation Test Suite**: `tests/integration/test_migration_002_validation.py`

**Prerequisites**:
- Migration state (applied or rolled back)
- pytest installed

**Execution Command**:
```bash
# Run all validation tests
DATABASE_URL=postgresql://localhost/codebase_mcp_test pytest tests/integration/test_migration_002_validation.py -v

# Run specific validation
pytest tests/integration/test_migration_002_validation.py::test_post_migration_validation -v
pytest tests/integration/test_migration_002_validation.py::test_post_rollback_validation -v
```

**Expected Output** (post-migration):
```
tests/integration/test_migration_002_validation.py::test_post_migration_validation PASSED
  ✓ project_id column exists in repositories (VARCHAR(50), NOT NULL, DEFAULT 'default')
  ✓ project_id column exists in code_chunks (VARCHAR(50), NOT NULL)
  ✓ CHECK constraints exist (2 found)
  ✓ Performance index exists (idx_project_repository)
  ✓ Unused tables dropped (0 of 9 tables found)
  ✓ Data integrity check (all code_chunks have matching repository project_id)
  ✓ Pattern validation (all project_id values match ^[a-z0-9-]{1,50}$)
  ✓ No orphaned code_chunks
```

**Expected Output** (post-rollback):
```
tests/integration/test_migration_002_validation.py::test_post_rollback_validation PASSED
  ✓ project_id columns removed (0 columns found)
  ✓ CHECK constraints removed (0 constraints found)
  ✓ Performance index removed (idx_project_repository not found)
  ✓ Dropped tables restored (9 tables found)
  ✓ repositories data preserved (row count matches baseline)
  ✓ code_chunks data preserved (row count matches baseline)
```

## Contract Guarantees

### Atomicity (FR-018)
- All operations wrapped in single transaction (Alembic default behavior)
- Any error triggers automatic ROLLBACK
- No partial schema changes possible

### Idempotency (FR-016)
- Alembic tracks applied migrations in `alembic_version` table
- Running `alembic upgrade head` when already at head is safe (no-op)
- Migration code uses IF EXISTS / IF NOT EXISTS as defense-in-depth

### Performance (FR-031)
- Execution time < 5 minutes on production-scale database
- Tested with 100 repositories, 10,000 code chunks
- Logging captures duration for each step

### Safety (FR-019)
- Fail fast with clear error messages (Python exceptions + SQL errors)
- Foreign key verification before dropping tables
- Orphan detection before adding NOT NULL constraints
- Alembic transaction ensures rollback on any failure

### Logging (FR-020)
- Python logger (INFO level) for major steps
- SQL RAISE NOTICE for inline progress
- Structured logging with timestamps
- Logs to stdout (captured by Alembic) and optionally to file

### Data Integrity (FR-017, FR-022)
- repositories data: Preserved, project_id added with 'default'
- code_chunks data: Preserved, project_id copied from parent
- Dropped tables: Schema structure documented, data lost (backup required for restoration)

## Error Scenarios

### E1: Foreign Key Violation

**Trigger**: Foreign key exists from dropped table to repositories/code_chunks

**Error Message**:
```
sqlalchemy.exc.IntegrityError: (psycopg2.errors.ForeignKeyViolation)
Foreign key constraint detected from 'work_items' to 'repositories'
DETAIL:  Cannot safely drop tables. Remove foreign key first.
HINT:   Run: ALTER TABLE work_items DROP CONSTRAINT fk_name;

ROLLBACK (automatic)
```

**Recovery**:
1. Migration automatically rolled back (no manual action needed)
2. Remove blocking foreign key manually
3. Re-run migration: `alembic upgrade head`

### E2: Orphaned Code Chunks

**Trigger**: code_chunk exists with invalid repository_id

**Error Message**:
```
sqlalchemy.exc.IntegrityError: (psycopg2.errors.NotNullViolation)
Cannot add NOT NULL constraint to code_chunks.project_id
DETAIL:  X rows have NULL project_id (orphaned chunks with no parent repository)
HINT:   Fix data integrity: DELETE FROM code_chunks WHERE repository_id NOT IN (SELECT id FROM repositories);

ROLLBACK (automatic)
```

**Recovery**:
1. Migration automatically rolled back
2. Delete orphaned chunks or fix repository_id
3. Re-run migration

### E3: Pattern Violation

**Trigger**: Existing data violates project_id pattern

**Error Message**:
```
sqlalchemy.exc.IntegrityError: (psycopg2.errors.CheckViolation)
Check constraint "check_repositories_project_id" violated
DETAIL:  Row with id=X has project_id='INVALID_VALUE' which violates pattern ^[a-z0-9-]{1,50}$

ROLLBACK (automatic)
```

**Recovery**:
1. Migration automatically rolled back
2. Fix invalid project_id values
3. Re-run migration

### E4: Performance Timeout

**Trigger**: Execution exceeds 5 minutes

**Error Message**:
```
TimeoutError: Migration timeout exceeded (300 seconds)
DETAIL:  Consider running on smaller dataset or optimizing index creation

ROLLBACK (automatic)
```

**Recovery**:
1. Investigate slow operations (check `EXPLAIN ANALYZE` on UPDATE queries)
2. Run `VACUUM ANALYZE` on tables
3. Consider using `CREATE INDEX CONCURRENTLY` manually (see note below)
4. Re-run migration

## Testing Contract

### Unit Tests
- Pattern validation tested with 10+ invalid inputs (FR-026)
- Pytest fixtures for database setup/teardown
- Edge cases: empty string, special characters, boundary lengths

### Integration Tests
```bash
# Test upgrade
pytest tests/integration/test_migration_002_upgrade.py

# Test downgrade
pytest tests/integration/test_migration_002_downgrade.py

# Test validation
pytest tests/integration/test_migration_002_validation.py

# Test idempotency
pytest tests/integration/test_migration_002_upgrade.py::test_idempotency
```

### Performance Tests
```bash
# Execute with 100 repos + 10K chunks (FR-028)
pytest tests/performance/test_migration_002_performance.py -v --benchmark

# Verify < 5 minutes (FR-031)
```

## Operational Runbook

### Pre-Migration Checklist
- [ ] Database backup created (`pg_dump`)
- [ ] No active connections to dropped tables
- [ ] `alembic current` shows revision 005 or earlier
- [ ] Migration tested on copy of production database (FR-027)
- [ ] Downgrade tested successfully (FR-029)
- [ ] All tests passing

### Execution Steps
1. **Stop application services** using database
   ```bash
   systemctl stop codebase-mcp-server
   ```

2. **Verify current state**
   ```bash
   alembic current
   alembic history
   ```

3. **Run validation tests (baseline)**
   ```bash
   pytest tests/integration/test_migration_002_validation.py::test_pre_migration_checks
   ```

4. **Execute migration**
   ```bash
   DATABASE_URL=postgresql://localhost/codebase_mcp alembic upgrade head
   ```

5. **Verify migration applied**
   ```bash
   alembic current  # Should show 002
   ```

6. **Run validation tests (post-migration)**
   ```bash
   pytest tests/integration/test_migration_002_validation.py::test_post_migration_validation
   ```

7. **Restart application services**
   ```bash
   systemctl start codebase-mcp-server
   ```

8. **Monitor logs**
   ```bash
   tail -f /tmp/codebase-mcp.log
   journalctl -u codebase-mcp-server -f
   ```

### Post-Migration Verification
- [ ] `alembic current` shows 002
- [ ] Validation tests pass (8/8 checks)
- [ ] Application starts successfully
- [ ] Search queries work correctly
- [ ] No errors in application logs

### Rollback Procedure (if needed)
1. **Stop application services**
   ```bash
   systemctl stop codebase-mcp-server
   ```

2. **Execute rollback**
   ```bash
   DATABASE_URL=postgresql://localhost/codebase_mcp alembic downgrade -1
   ```

3. **Verify rollback**
   ```bash
   alembic current  # Should show 005
   pytest tests/integration/test_migration_002_validation.py::test_post_rollback_validation
   ```

4. **Restore dropped table data** (if needed)
   ```bash
   pg_restore -d codebase_mcp --table=work_items ... backup.dump
   ```

5. **Restart application services**
   ```bash
   systemctl start codebase-mcp-server
   ```

## Advanced Topics

### Concurrent Index Creation (Optional)

For large production databases (>10K repositories), consider creating the index with CONCURRENTLY before running the migration:

```bash
# 1. Connect to database
psql -h localhost -U postgres -d codebase_mcp

# 2. Create index concurrently (non-blocking)
CREATE INDEX CONCURRENTLY idx_project_repository ON repositories(project_id, id);

# 3. Comment out index creation in migration
# Edit migrations/versions/002_remove_non_search_tables.py:
# # op.create_index('idx_project_repository', ...)  # Already created manually

# 4. Run migration (will skip index creation)
alembic upgrade head
```

**Note**: CONCURRENTLY cannot run inside a transaction, so it's incompatible with Alembic's transactional approach. Use this only if index creation time is a concern.

### Database Connection Override

```bash
# Test database
DATABASE_URL=postgresql://localhost/codebase_mcp_test alembic upgrade head

# Production database
DATABASE_URL=postgresql://prod-server/codebase_mcp alembic upgrade head

# With explicit credentials
DATABASE_URL=postgresql://user:pass@host:5432/dbname alembic upgrade head
```

### Logging Configuration

Configure Python logging for migration output:

```python
# In migrations/env.py (if not already configured)
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # stdout
        logging.FileHandler('/tmp/codebase-mcp-migration.log')  # file
    ]
)
```

## API Surface

**None**: This feature only modifies database schema. No API changes in this phase.

**Phase 02** will update MCP tools to use project_id:
- `index_repository` tool: Accept optional `project_id` parameter
- `search_code` tool: Accept optional `project_id` filter

## Next Phase

**Phase 2** (via /tasks command): Generate task list for implementation
- Task: Create test data generation utility (`tests/fixtures/generate_test_data.py`)
- Task: Write Alembic migration (`migrations/versions/002_remove_non_search_tables.py`)
- Task: Write validation test suite
- Task: Write integration tests (upgrade/downgrade)
- Task: Write performance tests
- Task: Execute migration on test database
- Task: Run all tests and validate
