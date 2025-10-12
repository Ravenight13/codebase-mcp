# Research & Design Decisions
**Feature**: Database Schema Refactoring for Multi-Project Support
**Date**: 2025-10-11
**Phase**: 0 (Research)

## Overview

This document consolidates research findings and design decisions for the database schema refactoring feature. All decisions are made to satisfy the 31 functional requirements defined in spec.md while adhering to constitutional principles.

## R1: Migration Tool Selection

### Decision
Use **Alembic** (existing migration framework) with transactional DDL execution

### Rationale
- Project already uses Alembic (001_initial_schema.py, 003_project_tracking.py, 005_case_insensitive_vendor_name.py exist)
- Alembic handles transactions automatically (single transaction per upgrade/downgrade)
- Built-in migration tracking via `alembic_version` table
- Better integration with SQLAlchemy (existing ORM)
- Automatic rollback on any error (connection loss, constraint violation, etc.)
- Standard tooling: `alembic upgrade head`, `alembic downgrade -1`
- Constitutional principle alignment: Production Quality (comprehensive error handling), Pydantic-Based Type Safety (Python migrations)
- Satisfies FR-018 (single atomic transaction requirement)

### Alternatives Considered
1. **Raw SQL scripts with psql**
   - Rejected: Creates parallel migration system
   - Rejected: Manual tracking required
   - Rejected: Less integration with Python codebase
   - Rejected: More complexity (need custom wrapper scripts)

2. **Manual transactions in SQL**
   - Rejected: Alembic handles this correctly
   - Rejected: More error-prone
   - Rejected: Less standardized

3. **Other migration frameworks (Flyway, Liquibase)**
   - Rejected: Not Python-native
   - Rejected: Alembic already installed and working

### Implementation Pattern
```python
# migrations/versions/002_remove_non_search_tables.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

def upgrade():
    """Forward migration - executed in single transaction"""
    conn = op.get_bind()

    logger.info("Step 1/10: Checking prerequisites...")
    # ... DDL operations ...
    logger.info("Step 1/10: Complete")

    # Alembic automatically wraps in BEGIN/COMMIT

def downgrade():
    """Rollback migration - executed in single transaction"""
    conn = op.get_bind()

    logger.info("Rollback Step 1/6: Dropping performance index...")
    # ... inverse DDL operations ...
    logger.info("Rollback Step 1/6: Complete")
```

**Alembic Execution**:
```bash
# Forward migration
alembic upgrade head

# Rollback
alembic downgrade -1

# Check current state
alembic current
```

## R2: project_id Validation Strategy

### Decision
Multi-layer validation (database CHECK constraint + Pydantic validator in Phase 02)

### Rationale
- **Database CHECK constraint**: Last line of defense, prevents SQL injection, enforces at insert/update
- **Pydantic validator (Phase 02)**: Early validation in application code, better error messages
- **Regex pattern** `^[a-z0-9-]{1,50}$`: Simple, database-native, no extensions needed
- Satisfies FR-009 through FR-012 (pattern validation requirements)
- Satisfies FR-024 through FR-026 (validation enforcement requirements)

### Alternatives Considered
1. **Application-only validation**
   - Rejected: Can be bypassed via direct DB access
   - Rejected: Violates defense-in-depth security principle

2. **Custom PostgreSQL domain type**
   - Rejected: Unnecessary complexity for simple pattern
   - Rejected: Violates Simplicity Over Features principle

3. **ENUM type**
   - Rejected: Inflexible, requires DDL for each new project_id
   - Rejected: Doesn't scale to arbitrary project identifiers

### Implementation Pattern
```python
# In Alembic migration upgrade() function
def upgrade():
    conn = op.get_bind()

    # Add CHECK constraints
    conn.execute(text("""
        ALTER TABLE repositories
          ADD CONSTRAINT check_repositories_project_id
          CHECK (project_id ~ '^[a-z0-9-]{1,50}$')
    """))

    conn.execute(text("""
        ALTER TABLE code_chunks
          ADD CONSTRAINT check_code_chunks_project_id
          CHECK (project_id ~ '^[a-z0-9-]{1,50}$')
    """))
```

## R3: Foreign Key Verification Approach

### Decision
Query `information_schema.table_constraints` and `information_schema.referential_constraints` before dropping tables

### Rationale
- Standard SQL approach, works across PostgreSQL versions
- Explicit verification prevents accidental data corruption
- Clear error message identifies problematic foreign keys
- Fails fast before any destructive operations
- Satisfies FR-003 (foreign key verification requirement)

### Alternatives Considered
1. **`DROP TABLE ... CASCADE`**
   - Rejected: Too aggressive, hides potential issues
   - Rejected: Could accidentally drop data from repositories/code_chunks

2. **Manual inspection**
   - Rejected: Error-prone, not automatable
   - Rejected: Violates Production Quality principle

3. **Rely on PostgreSQL error**
   - Rejected: Less clear error messages
   - Rejected: Fails after starting drops (less safe)

### Implementation Pattern
```python
# In Alembic migration upgrade() function
def upgrade():
    conn = op.get_bind()

    logger.info("Step 2/10: Verifying foreign key constraints...")

    # Check for blocking foreign keys
    result = conn.execute(text("""
        SELECT COUNT(*) AS fk_count
        FROM information_schema.referential_constraints rc
        JOIN information_schema.table_constraints tc
          ON rc.constraint_name = tc.constraint_name
        WHERE tc.table_name IN ('work_items', 'tasks', 'vendors', ...)
          AND rc.unique_constraint_name IN (
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name IN ('repositories', 'code_chunks')
          )
    """))

    fk_count = result.scalar()
    if fk_count > 0:
        raise ValueError(f"Found {fk_count} foreign keys from dropped tables to core tables")

    logger.info("Step 2/10: Complete - No blocking foreign keys found")
```

## R4: Migration Idempotency Strategy

### Decision
Use **Alembic's migration tracking** (`alembic_version` table) + `IF EXISTS`/`IF NOT EXISTS` as defense-in-depth

### Rationale
- **Alembic tracking**: Automatic, standard approach, prevents duplicate migrations
- **IF EXISTS clauses**: Defense-in-depth, handles manual database modifications
- `alembic upgrade head` when already at head is safe no-op
- Clear status via `alembic current` command
- Satisfies FR-016 (idempotency requirement)

### Alternatives Considered
1. **IF EXISTS only (no Alembic tracking)**
   - Rejected: Alembic already provides better tracking
   - Rejected: Less visibility into migration state

2. **No idempotency checks**
   - Rejected: Operational risk, requires careful orchestration
   - Rejected: Violates FR-016

3. **Custom version tracking table**
   - Rejected: Alembic's `alembic_version` table already does this
   - Rejected: Unnecessary duplication

### Implementation Pattern
```python
# Alembic automatically handles migration tracking
# Each migration applied is recorded in alembic_version table

# Check if migration applied
$ alembic current
002 (head)  # Migration 002 is applied

# Running upgrade when already at head is safe
$ alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade  -> 002
# No-op, no changes made

# Defense-in-depth: Use IF EXISTS in DDL
def upgrade():
    conn = op.get_bind()

    # Safe to run multiple times
    conn.execute(text("""
        ALTER TABLE repositories
        ADD COLUMN IF NOT EXISTS project_id VARCHAR(50) NOT NULL DEFAULT 'default'
    """))

    conn.execute(text("""
        DROP TABLE IF EXISTS work_items CASCADE
    """))
```

## R5: Code Chunk project_id Population Strategy

### Decision
Three-step ADD COLUMN approach with UPDATE between steps

### Rationale
- **Step 1**: Add nullable column (allows UPDATE to succeed)
- **Step 2**: Populate from parent repository (maintains referential integrity)
- **Step 3**: Add NOT NULL + CHECK constraint (enforces future integrity)
- Handles existing data gracefully (copies from parent)
- Validates referential integrity (UPDATE fails if orphan chunks exist)
- Satisfies FR-022 (data integrity requirement)

### Alternatives Considered
1. **Direct ADD COLUMN with NOT NULL + UPDATE**
   - Rejected: PostgreSQL doesn't allow UPDATE between constraint checks
   - Rejected: Would fail on existing data

2. **Default value approach**
   - Rejected: Loses referential integrity, assigns 'default' to all chunks
   - Rejected: Violates FR-022 (copy from parent repository)

3. **Two separate transactions**
   - Rejected: Violates FR-018 (single transaction requirement)

### Implementation Pattern
```python
def upgrade():
    conn = op.get_bind()

    logger.info("Step 4/10: Adding project_id to code_chunks table...")

    # Step 1: Add nullable column
    conn.execute(text("""
        ALTER TABLE code_chunks
        ADD COLUMN IF NOT EXISTS project_id VARCHAR(50)
    """))

    # Step 2: Populate from parent repository
    conn.execute(text("""
        UPDATE code_chunks
        SET project_id = (
          SELECT project_id FROM repositories
          WHERE repositories.id = code_chunks.repository_id
        )
        WHERE project_id IS NULL
    """))

    # Step 3: Add constraints
    conn.execute(text("""
        ALTER TABLE code_chunks
          ALTER COLUMN project_id SET NOT NULL
    """))

    conn.execute(text("""
        ALTER TABLE code_chunks
          ADD CONSTRAINT check_code_chunks_project_id
          CHECK (project_id ~ '^[a-z0-9-]{1,50}$')
    """))

    logger.info("Step 4/10: Complete - Column added, populated from parent repositories")
```

## R6: Migration Performance Optimization

### Decision
Create index AFTER data population, optionally use CONCURRENTLY for production (manual step)

### Rationale
- Index creation on existing data: Faster to populate first, then index
- `CREATE INDEX CONCURRENTLY`: Optional for production (allows reads during index build)
- For initial migration (minimal data): Standard index creation acceptable (< 1 second)
- Performance target: < 5 minutes easily met with up to 100K rows
- Satisfies FR-031 (< 5 minute performance requirement)

### Alternatives Considered
1. **Index before populating**
   - Rejected: Slower, each UPDATE incurs index maintenance cost
   - Rejected: Could exceed 5 minute target on large datasets

2. **No performance optimization**
   - Rejected: Violates FR-031 performance requirement

3. **Always use CONCURRENTLY**
   - Rejected: CONCURRENTLY can't run in transaction
   - Rejected: Incompatible with Alembic's transactional approach

### Implementation Pattern
```python
def upgrade():
    conn = op.get_bind()

    # After all data population complete
    logger.info("Step 6/10: Creating performance index...")

    # Standard approach (transactional, fast for test data)
    op.create_index(
        'idx_project_repository',
        'repositories',
        ['project_id', 'id']
    )

    logger.info("Step 6/10: Complete - Index idx_project_repository created")

# Optional for production (manual step BEFORE migration):
# CREATE INDEX CONCURRENTLY idx_project_repository
#   ON repositories(project_id, id);
# Then comment out op.create_index() in migration
```

## R7: Logging and Observability Strategy

### Decision
Use **Python logging** in Alembic migration + PostgreSQL `RAISE NOTICE` for SQL-level feedback

### Rationale
- **Python logger**: Standard logging framework, structured output, configurable levels
- **RAISE NOTICE**: SQL-level progress visibility (shows in Alembic output)
- Logs to stdout (captured by Alembic) and optionally to file
- Timestamps added by Python logging framework
- Error context captured via Python exceptions + SQL error messages
- Constitutional principle alignment: Production Quality (comprehensive logging)
- Satisfies FR-020 (logging requirement)

### Alternatives Considered
1. **RAISE NOTICE only**
   - Rejected: No structured logging
   - Rejected: Harder to parse for monitoring

2. **No logging**
   - Rejected: Violates FR-020 logging requirement
   - Rejected: Poor operational visibility

3. **Custom logging table**
   - Rejected: Overkill, complicates transaction isolation
   - Rejected: Adds unnecessary complexity

### Implementation Pattern
```python
# migrations/versions/002_remove_non_search_tables.py
import logging

logger = logging.getLogger(__name__)

def upgrade():
    conn = op.get_bind()

    # Python logging for major steps
    logger.info("Step 1/10: Checking prerequisites...")

    # SQL RAISE NOTICE for inline feedback
    conn.execute(text("""
        DO $$
        BEGIN
          RAISE NOTICE 'Verifying foreign key constraints...';
          -- ... query ...
          RAISE NOTICE 'No blocking foreign keys found';
        END $$
    """))

    logger.info("Step 1/10: Complete")

    # Error handling with clear context
    try:
        conn.execute(text("DROP TABLE work_items CASCADE"))
    except Exception as e:
        logger.error(f"Failed to drop work_items: {e}")
        raise ValueError(f"Migration failed at step 7: {e}") from e
```

**Logging Configuration** (in migrations/env.py):
```python
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

## R8: Rollback Design Pattern

### Decision
Use **Alembic downgrade() function** with inverse operations + data restoration caveat

### Rationale
- **Alembic downgrade()**: Standard, automatic, mirrors upgrade() structure
- Inverse DDL operations: `CREATE TABLE` mirrors `DROP TABLE`, `DROP COLUMN` mirrors `ADD COLUMN`
- Schema-only rollback: Structure restored, data lost (acceptable per spec clarifications)
- Data restoration requires backup: Documented in contract
- Fast execution: < 30 seconds (no data restoration by default)
- Single transaction: Alembic handles automatically
- Satisfies FR-014 (rollback script requirement)

### Alternatives Considered
1. **Full data restoration in rollback**
   - Rejected: Slow, requires backup embedded in script
   - Rejected: Complex, prone to errors

2. **No rollback (downgrade not implemented)**
   - Rejected: Violates FR-014 reversibility requirement
   - Rejected: Poor operational safety

3. **Separate rollback file**
   - Rejected: Alembic's downgrade() function is standard
   - Rejected: More files to maintain

### Implementation Pattern
```python
# migrations/versions/002_remove_non_search_tables.py

def upgrade():
    """Forward migration"""
    conn = op.get_bind()

    # Add column
    conn.execute(text("ALTER TABLE repositories ADD COLUMN project_id VARCHAR(50)..."))

    # Drop tables
    conn.execute(text("DROP TABLE IF EXISTS work_items CASCADE"))
    conn.execute(text("DROP TABLE IF EXISTS tasks CASCADE"))
    # ... (9 tables total)

def downgrade():
    """Rollback migration"""
    conn = op.get_bind()

    logger.info("Rollback Step 1/6: Dropping performance index...")
    op.drop_index('idx_project_repository', 'repositories')
    logger.info("Rollback Step 1/6: Complete")

    logger.info("Rollback Step 2/6: Dropping validation constraints...")
    conn.execute(text("ALTER TABLE repositories DROP CONSTRAINT IF EXISTS check_repositories_project_id"))
    conn.execute(text("ALTER TABLE code_chunks DROP CONSTRAINT IF EXISTS check_code_chunks_project_id"))
    logger.info("Rollback Step 2/6: Complete")

    logger.info("Rollback Step 3/6: Dropping project_id from code_chunks...")
    conn.execute(text("ALTER TABLE code_chunks DROP COLUMN IF EXISTS project_id"))
    logger.info("Rollback Step 3/6: Complete")

    logger.info("Rollback Step 4/6: Dropping project_id from repositories...")
    conn.execute(text("ALTER TABLE repositories DROP COLUMN IF EXISTS project_id"))
    logger.info("Rollback Step 4/6: Complete")

    logger.info("Rollback Step 5/6: Restoring dropped tables (schema only)...")
    # Recreate table structures (data NOT restored)
    conn.execute(text("CREATE TABLE IF NOT EXISTS work_items (...)"))
    conn.execute(text("CREATE TABLE IF NOT EXISTS tasks (...)"))
    # ... (9 tables total)
    logger.warning("Data in dropped tables NOT restored. Restore from backup if needed.")
    logger.info("Rollback Step 5/6: Complete - 9 tables restored")

    logger.info("Rollback Step 6/6: Running validation...")
    # Validation checks
    logger.info("Rollback Step 6/6: Complete")
```

**Rollback Execution**:
```bash
# Downgrade one revision
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade 005

# Verify rollback
alembic current  # Should show: 005
```

## R9: Database Connection Configuration

### Decision
Use **DATABASE_URL environment variable** for database connection configuration

### Rationale
- Standard pattern across Python database tools (SQLAlchemy, Alembic, Django, Flask)
- Flexible: Works with local, test, and production databases
- Secure: No hardcoded credentials in code
- Alembic native: `alembic.ini` can reference `${DATABASE_URL}` or detect from environment
- Constitutional principle alignment: Local-First Architecture (configurable for any local PostgreSQL)
- Operational simplicity: Single configuration point

### Alternatives Considered
1. **Hardcoded connection in alembic.ini**
   - Rejected: Not flexible for different environments
   - Rejected: Security risk (credentials in version control)

2. **Separate config file per environment**
   - Rejected: More complexity, more files to maintain
   - Rejected: Doesn't follow Python ecosystem conventions

3. **Command-line arguments**
   - Rejected: More verbose, error-prone
   - Rejected: Harder to script

### Implementation Pattern
```bash
# Environment variable approach (recommended)
export DATABASE_URL=postgresql://localhost/codebase_mcp
alembic upgrade head

# Or inline for single command
DATABASE_URL=postgresql://localhost/codebase_mcp_test alembic upgrade head

# Different environments
DATABASE_URL=postgresql://localhost/codebase_mcp_test alembic upgrade head  # Test
DATABASE_URL=postgresql://prod-server/codebase_mcp alembic upgrade head     # Production
```

**alembic.ini configuration**:
```ini
[alembic]
# Support DATABASE_URL from environment
sqlalchemy.url = ${DATABASE_URL}

# Or with fallback to default
sqlalchemy.url = postgresql://localhost/codebase_mcp
```

**migrations/env.py configuration**:
```python
import os
from alembic import context

# Get DATABASE_URL from environment or alembic.ini
config = context.config
database_url = os.environ.get('DATABASE_URL') or config.get_main_option('sqlalchemy.url')
config.set_main_option('sqlalchemy.url', database_url)
```

## Summary of Research Outcomes

All research decisions satisfy constitutional principles:
- ✅ **Simplicity Over Features** (R1: use existing Alembic, no custom framework; R4: no custom version tracking)
- ✅ **Local-First Architecture** (R9: configurable for any local PostgreSQL, R1: all operations local)
- ✅ **Protocol Compliance** (no impact to MCP protocol)
- ✅ **Performance Guarantees** (R6: < 5 minute target, index optimization strategy)
- ✅ **Production Quality** (R1, R3, R7: error handling, validation, comprehensive logging)
- ✅ **Specification-First** (all decisions traced to functional requirements)
- ✅ **Test-Driven Development** (pytest validation suite, idempotency tests)
- ✅ **Pydantic-Based Type Safety** (R1: Python migrations leverage type safety)

**Key Architectural Decision**: Using Alembic instead of raw SQL provides:
- Automatic transaction management (FR-018)
- Built-in migration tracking (FR-016)
- Better Python integration (Constitutional Principle VIII)
- Production-grade error handling (Constitutional Principle V)
- Standard tooling (`alembic upgrade/downgrade`)

**Next Phase**: Phase 1 (Design & Contracts)
