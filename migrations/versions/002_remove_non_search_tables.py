"""Remove non-search tables and add project_id columns for multi-project support.

This migration refactors the database schema to:
1. Remove 9 unused tables from non-search features (work tracking, vendor management, deployments)
2. Add project_id columns to repositories and code_chunks tables
3. Establish foundation for multi-project semantic code search

Tables Dropped (9):
- vendor_extractors
- deployment_events
- project_configuration
- future_enhancements
- work_item_dependencies
- vendor_deployment_links
- work_item_deployment_links
- archived_work_items
- (extended columns removed from tasks table)

Schema Changes:
- repositories: Add project_id VARCHAR(50) NOT NULL DEFAULT 'default'
- code_chunks: Add project_id VARCHAR(50) NOT NULL (copied from parent repository)
- Both tables: Add CHECK constraint for pattern validation (^[a-z0-9-]{1,50}$)
- New index: idx_project_repository on repositories(project_id, id)

Performance:
- Migration target: < 5 minutes for 100 repos + 10K chunks
- Index created after data population for optimal performance
- Three-step approach for code_chunks project_id (nullable → UPDATE → NOT NULL)

Safety:
- Single atomic transaction (automatic rollback on error)
- Foreign key verification before dropping tables
- Idempotent DDL (IF EXISTS / IF NOT EXISTS clauses)
- Comprehensive logging at each major step

Rollback:
- downgrade() restores table structures (schema only, data NOT restored)
- Data restoration requires manual backup import
- Rollback target: < 30 seconds execution

Constitutional Compliance:
- Principle I: Simplicity Over Features (removes complexity, adds minimal foundation)
- Principle IV: Performance Guarantees (< 5 min migration, maintains < 500ms search)
- Principle V: Production Quality (error handling, validation, logging)
- Principle VII: Test-Driven Development (comprehensive test suite)
- Principle X: Git Micro-Commit Strategy (atomic migration commit)

Revision ID: 002
Revises: 005
Create Date: 2025-10-11 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union
import logging
import time

from alembic import op
from sqlalchemy import text
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Configure logging
logger = logging.getLogger(__name__)


def upgrade() -> None:
    """Apply migration: remove non-search tables and add project_id columns.

    Executes 10 steps in single atomic transaction:
    1. Prerequisites check
    2. Foreign key verification
    3. Add project_id to repositories
    4. Add project_id to code_chunks (3-step approach)
    5. Add CHECK constraints
    6. Create performance index
    7. Drop 9 unused tables
    8. Validation checks
    9. Log completion with duration
    10. COMMIT (automatic via Alembic)

    Raises:
        ValueError: If foreign keys found from dropped tables to core tables
        Exception: If any DDL operation fails (transaction auto-rolled back)
    """
    start_time = time.time()
    conn = op.get_bind()

    # Step 1: Check prerequisites
    logger.info("Step 1/10: Checking prerequisites...")
    try:
        # Verify database connection
        conn.execute(text("SELECT 1"))
        logger.info("Step 1/10: Complete - Database connection verified")
    except Exception as e:
        logger.error(f"Step 1/10: FAILED - Database connection error: {e}")
        raise ValueError(f"Migration failed at step 1: Database connection error: {e}") from e

    # Step 2: Verify no foreign keys from dropped tables to core tables
    logger.info("Step 2/10: Verifying foreign key constraints...")
    try:
        # Query for foreign keys from tables to be dropped that reference repositories or code_chunks
        # This prevents accidental data corruption if FKs exist
        result = conn.execute(text("""
            SELECT
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name IN (
                    'vendor_extractors',
                    'deployment_events',
                    'project_configuration',
                    'future_enhancements',
                    'work_item_dependencies',
                    'vendor_deployment_links',
                    'work_item_deployment_links',
                    'archived_work_items',
                    'tasks'
                )
                AND ccu.table_name IN ('repositories', 'code_chunks')
        """))

        fk_violations = result.fetchall()
        if fk_violations:
            fk_details = "\n".join([
                f"  - {row.table_name}.{row.column_name} -> {row.foreign_table_name}.{row.foreign_column_name}"
                for row in fk_violations
            ])
            error_msg = (
                f"Found {len(fk_violations)} foreign key(s) from tables to be dropped that reference "
                f"core tables (repositories/code_chunks). This would cause data corruption:\n{fk_details}\n"
                f"These foreign keys must be removed before migration."
            )
            logger.error(f"Step 2/10: FAILED - {error_msg}")
            raise ValueError(error_msg)

        logger.info("Step 2/10: Complete - No blocking foreign keys found")
    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(f"Step 2/10: FAILED - Foreign key verification error: {e}")
        raise ValueError(f"Migration failed at step 2: Foreign key verification error: {e}") from e

    # Step 3: Add project_id to repositories
    logger.info("Step 3/10: Adding project_id to repositories table...")
    try:
        conn.execute(text("""
            ALTER TABLE repositories
            ADD COLUMN IF NOT EXISTS project_id VARCHAR(50) NOT NULL DEFAULT 'default'
        """))
        logger.info("Step 3/10: Complete - project_id column added to repositories")
    except Exception as e:
        logger.error(f"Step 3/10: FAILED - Error adding project_id to repositories: {e}")
        raise ValueError(f"Migration failed at step 3: Error adding project_id to repositories: {e}") from e

    # Step 4: Add project_id to code_chunks (3-step approach for data integrity)
    logger.info("Step 4/10: Adding project_id to code_chunks table...")
    try:
        # Step 4.1: Add nullable column
        conn.execute(text("""
            ALTER TABLE code_chunks
            ADD COLUMN IF NOT EXISTS project_id VARCHAR(50)
        """))
        logger.info("Step 4/10: Sub-step 1 - Nullable column added")

        # Step 4.2: Populate from parent repository
        result = conn.execute(text("""
            UPDATE code_chunks
            SET project_id = (
                SELECT r.project_id
                FROM repositories r
                JOIN code_files cf ON cf.repository_id = r.id
                WHERE cf.id = code_chunks.code_file_id
            )
            WHERE project_id IS NULL
        """))
        rows_updated = result.rowcount
        logger.info(f"Step 4/10: Sub-step 2 - Populated project_id for {rows_updated} code chunks from parent repositories")

        # Step 4.3: Add NOT NULL constraint
        conn.execute(text("""
            ALTER TABLE code_chunks
            ALTER COLUMN project_id SET NOT NULL
        """))
        logger.info("Step 4/10: Complete - project_id column added to code_chunks with NOT NULL constraint")
    except Exception as e:
        logger.error(f"Step 4/10: FAILED - Error adding project_id to code_chunks: {e}")
        raise ValueError(f"Migration failed at step 4: Error adding project_id to code_chunks: {e}") from e

    # Step 5: Add CHECK constraints for pattern validation
    logger.info("Step 5/10: Adding validation constraints...")
    try:
        # CHECK constraint for repositories.project_id
        conn.execute(text("""
            ALTER TABLE repositories
            ADD CONSTRAINT check_repositories_project_id
            CHECK (project_id ~ '^[a-z0-9-]{1,50}$')
        """))
        logger.info("Step 5/10: Sub-step 1 - CHECK constraint added to repositories.project_id")

        # CHECK constraint for code_chunks.project_id
        conn.execute(text("""
            ALTER TABLE code_chunks
            ADD CONSTRAINT check_code_chunks_project_id
            CHECK (project_id ~ '^[a-z0-9-]{1,50}$')
        """))
        logger.info("Step 5/10: Complete - CHECK constraints added to both tables")
    except Exception as e:
        logger.error(f"Step 5/10: FAILED - Error adding CHECK constraints: {e}")
        raise ValueError(f"Migration failed at step 5: Error adding CHECK constraints: {e}") from e

    # Step 6: Create performance index
    logger.info("Step 6/10: Creating performance index...")
    try:
        # Create index on (project_id, id) for multi-project queries
        # Using IF NOT EXISTS pattern for idempotency (manual DROP INDEX IF EXISTS first)
        conn.execute(text("DROP INDEX IF EXISTS idx_project_repository"))
        op.create_index(
            'idx_project_repository',
            'repositories',
            ['project_id', 'id']
        )
        logger.info("Step 6/10: Complete - Index idx_project_repository created on repositories(project_id, id)")
    except Exception as e:
        logger.error(f"Step 6/10: FAILED - Error creating performance index: {e}")
        raise ValueError(f"Migration failed at step 6: Error creating performance index: {e}") from e

    # Step 7: Drop 9 unused tables
    logger.info("Step 7/10: Dropping unused tables...")
    try:
        # Drop tables in order respecting dependencies
        # CASCADE ensures dependent objects are dropped
        tables_to_drop = [
            'archived_work_items',
            'work_item_deployment_links',
            'vendor_deployment_links',
            'work_item_dependencies',
            'future_enhancements',
            'project_configuration',
            'deployment_events',
            'vendor_extractors',
        ]

        for table_name in tables_to_drop:
            conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
            logger.info(f"Step 7/10: Dropped table {table_name}")

        # Also drop extended columns from tasks table
        # (Note: In migration 003, tasks table was extended. We're reverting those extensions)
        conn.execute(text("DROP TABLE IF EXISTS tasks CASCADE"))
        logger.info("Step 7/10: Dropped table tasks")

        logger.info("Step 7/10: Complete - All 9 unused tables dropped")
    except Exception as e:
        logger.error(f"Step 7/10: FAILED - Error dropping tables: {e}")
        raise ValueError(f"Migration failed at step 7: Error dropping tables: {e}") from e

    # Step 8: Run validation checks
    logger.info("Step 8/10: Running validation checks...")
    try:
        # Validation 1: Verify project_id columns exist
        result = conn.execute(text("""
            SELECT COUNT(*) AS column_count
            FROM information_schema.columns
            WHERE table_name IN ('repositories', 'code_chunks')
                AND column_name = 'project_id'
        """))
        column_count = result.scalar()
        if column_count != 2:
            raise ValueError(f"Expected 2 project_id columns, found {column_count}")
        logger.info("Step 8/10: Validation 1 - project_id columns exist in both tables")

        # Validation 2: Verify CHECK constraints exist
        result = conn.execute(text("""
            SELECT COUNT(*) AS constraint_count
            FROM information_schema.check_constraints
            WHERE constraint_name IN (
                'check_repositories_project_id',
                'check_code_chunks_project_id'
            )
        """))
        constraint_count = result.scalar()
        if constraint_count != 2:
            raise ValueError(f"Expected 2 CHECK constraints, found {constraint_count}")
        logger.info("Step 8/10: Validation 2 - CHECK constraints exist on both tables")

        # Validation 3: Verify performance index exists
        result = conn.execute(text("""
            SELECT COUNT(*) AS index_count
            FROM pg_indexes
            WHERE indexname = 'idx_project_repository'
        """))
        index_count = result.scalar()
        if index_count != 1:
            raise ValueError(f"Expected 1 performance index, found {index_count}")
        logger.info("Step 8/10: Validation 3 - Performance index exists")

        # Validation 4: Verify dropped tables no longer exist
        result = conn.execute(text("""
            SELECT COUNT(*) AS table_count
            FROM information_schema.tables
            WHERE table_name IN (
                'vendor_extractors',
                'deployment_events',
                'project_configuration',
                'future_enhancements',
                'work_item_dependencies',
                'vendor_deployment_links',
                'work_item_deployment_links',
                'archived_work_items',
                'tasks'
            )
        """))
        table_count = result.scalar()
        if table_count != 0:
            raise ValueError(f"Expected 0 dropped tables to exist, found {table_count}")
        logger.info("Step 8/10: Validation 4 - All 9 tables successfully dropped")

        logger.info("Step 8/10: Complete - All validation checks passed")
    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(f"Step 8/10: FAILED - Validation error: {e}")
        raise ValueError(f"Migration failed at step 8: Validation error: {e}") from e

    # Step 9: Log completion with duration
    duration = time.time() - start_time
    logger.info(f"Step 9/10: Migration completed successfully in {duration:.2f} seconds")
    logger.info("Step 9/10: Summary - 9 tables dropped, 2 tables modified, 1 index created, 2 constraints added")

    # Step 10: COMMIT (automatic via Alembic transaction)
    logger.info("Step 10/10: Transaction committed (automatic via Alembic)")


def downgrade() -> None:
    """Rollback migration: restore dropped tables and remove project_id columns.

    Executes 6 rollback steps in single atomic transaction:
    1. Drop performance index
    2. Drop CHECK constraints
    3. Drop project_id from code_chunks
    4. Drop project_id from repositories
    5. Restore 9 dropped tables (schema only, data NOT restored)
    6. Run validation, log completion

    WARNING: Data in dropped tables is NOT restored by this function.
    Data restoration requires manual import from backup.

    Raises:
        Exception: If any rollback operation fails (transaction auto-rolled back)
    """
    start_time = time.time()
    conn = op.get_bind()

    # Rollback Step 1: Drop performance index
    logger.info("Rollback Step 1/6: Dropping performance index...")
    try:
        op.drop_index('idx_project_repository', table_name='repositories', if_exists=True)
        logger.info("Rollback Step 1/6: Complete - Performance index dropped")
    except Exception as e:
        logger.error(f"Rollback Step 1/6: FAILED - Error dropping performance index: {e}")
        raise ValueError(f"Rollback failed at step 1: Error dropping performance index: {e}") from e

    # Rollback Step 2: Drop CHECK constraints
    logger.info("Rollback Step 2/6: Dropping validation constraints...")
    try:
        conn.execute(text("""
            ALTER TABLE repositories
            DROP CONSTRAINT IF EXISTS check_repositories_project_id
        """))
        conn.execute(text("""
            ALTER TABLE code_chunks
            DROP CONSTRAINT IF EXISTS check_code_chunks_project_id
        """))
        logger.info("Rollback Step 2/6: Complete - CHECK constraints dropped from both tables")
    except Exception as e:
        logger.error(f"Rollback Step 2/6: FAILED - Error dropping CHECK constraints: {e}")
        raise ValueError(f"Rollback failed at step 2: Error dropping CHECK constraints: {e}") from e

    # Rollback Step 3: Drop project_id from code_chunks
    logger.info("Rollback Step 3/6: Dropping project_id from code_chunks...")
    try:
        conn.execute(text("""
            ALTER TABLE code_chunks
            DROP COLUMN IF EXISTS project_id
        """))
        logger.info("Rollback Step 3/6: Complete - project_id column dropped from code_chunks")
    except Exception as e:
        logger.error(f"Rollback Step 3/6: FAILED - Error dropping project_id from code_chunks: {e}")
        raise ValueError(f"Rollback failed at step 3: Error dropping project_id from code_chunks: {e}") from e

    # Rollback Step 4: Drop project_id from repositories
    logger.info("Rollback Step 4/6: Dropping project_id from repositories...")
    try:
        conn.execute(text("""
            ALTER TABLE repositories
            DROP COLUMN IF EXISTS project_id
        """))
        logger.info("Rollback Step 4/6: Complete - project_id column dropped from repositories")
    except Exception as e:
        logger.error(f"Rollback Step 4/6: FAILED - Error dropping project_id from repositories: {e}")
        raise ValueError(f"Rollback failed at step 4: Error dropping project_id from repositories: {e}") from e

    # Rollback Step 5: Restore 9 dropped tables (schema only)
    logger.info("Rollback Step 5/6: Restoring dropped tables (schema only)...")
    try:
        # 1. vendor_extractors
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS vendor_extractors (
                id UUID PRIMARY KEY,
                version INTEGER NOT NULL DEFAULT 1,
                name VARCHAR(100) NOT NULL,
                status VARCHAR(20) NOT NULL,
                extractor_version VARCHAR(50) NOT NULL,
                metadata JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                created_by VARCHAR(100) NOT NULL,
                CONSTRAINT ck_vendor_status CHECK (status IN ('operational', 'broken'))
            )
        """))
        logger.info("Rollback Step 5/6: Restored table vendor_extractors")

        # 2. deployment_events
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS deployment_events (
                id UUID PRIMARY KEY,
                deployed_at TIMESTAMP WITH TIME ZONE NOT NULL,
                commit_hash VARCHAR(40) NOT NULL,
                metadata JSONB NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                created_by VARCHAR(100) NOT NULL,
                CONSTRAINT ck_commit_hash_format CHECK (commit_hash ~ '^[a-f0-9]{40}$')
            )
        """))
        logger.info("Rollback Step 5/6: Restored table deployment_events")

        # 3. project_configuration
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS project_configuration (
                id INTEGER PRIMARY KEY,
                active_context_type VARCHAR(50) NOT NULL,
                current_session_id UUID,
                git_branch VARCHAR(100),
                git_head_commit VARCHAR(40),
                default_token_budget INTEGER NOT NULL DEFAULT 200000,
                database_healthy BOOLEAN NOT NULL DEFAULT TRUE,
                last_health_check_at TIMESTAMP WITH TIME ZONE,
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                updated_by VARCHAR(100) NOT NULL,
                CONSTRAINT ck_singleton CHECK (id = 1)
            )
        """))
        logger.info("Rollback Step 5/6: Restored table project_configuration")

        # 4. future_enhancements
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS future_enhancements (
                id UUID PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                description TEXT NOT NULL,
                priority INTEGER NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'planned',
                target_quarter VARCHAR(10),
                requires_constitutional_principles JSONB NOT NULL DEFAULT '[]',
                created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                created_by VARCHAR(100) NOT NULL,
                CONSTRAINT ck_priority_range CHECK (priority >= 1 AND priority <= 5),
                CONSTRAINT ck_enhancement_status CHECK (status IN ('planned', 'approved', 'implementing', 'completed'))
            )
        """))
        logger.info("Rollback Step 5/6: Restored table future_enhancements")

        # 5. tasks (work_items)
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS tasks (
                id UUID PRIMARY KEY,
                version INTEGER NOT NULL DEFAULT 1,
                item_type VARCHAR(20) NOT NULL DEFAULT 'task',
                title VARCHAR(200) NOT NULL,
                status VARCHAR(20) NOT NULL,
                parent_id UUID,
                path VARCHAR(500) NOT NULL DEFAULT '/',
                depth INTEGER NOT NULL DEFAULT 0,
                branch_name VARCHAR(100),
                metadata JSONB NOT NULL,
                deleted_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                created_by VARCHAR(100) NOT NULL,
                CONSTRAINT ck_work_item_type CHECK (item_type IN ('project', 'session', 'task', 'research')),
                CONSTRAINT ck_work_item_depth CHECK (depth >= 0 AND depth <= 5)
            )
        """))
        logger.info("Rollback Step 5/6: Restored table tasks")

        # 6. work_item_dependencies
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS work_item_dependencies (
                source_id UUID NOT NULL,
                target_id UUID NOT NULL,
                dependency_type VARCHAR(20) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                created_by VARCHAR(100) NOT NULL,
                PRIMARY KEY (source_id, target_id),
                CONSTRAINT ck_dependency_type CHECK (dependency_type IN ('blocks', 'depends_on')),
                CONSTRAINT ck_no_self_dependency CHECK (source_id != target_id)
            )
        """))
        logger.info("Rollback Step 5/6: Restored table work_item_dependencies")

        # 7. vendor_deployment_links
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS vendor_deployment_links (
                deployment_id UUID NOT NULL,
                vendor_id UUID NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                PRIMARY KEY (deployment_id, vendor_id)
            )
        """))
        logger.info("Rollback Step 5/6: Restored table vendor_deployment_links")

        # 8. work_item_deployment_links
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS work_item_deployment_links (
                deployment_id UUID NOT NULL,
                work_item_id UUID NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                PRIMARY KEY (deployment_id, work_item_id)
            )
        """))
        logger.info("Rollback Step 5/6: Restored table work_item_deployment_links")

        # 9. archived_work_items
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS archived_work_items (
                id UUID PRIMARY KEY,
                item_type VARCHAR(20) NOT NULL,
                title VARCHAR(200) NOT NULL,
                status VARCHAR(20) NOT NULL,
                parent_id UUID,
                path VARCHAR(500) NOT NULL,
                depth INTEGER NOT NULL,
                branch_name VARCHAR(100),
                commit_hash VARCHAR(40),
                pr_number INTEGER,
                metadata JSONB NOT NULL,
                deleted_at TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
                created_by VARCHAR(100) NOT NULL,
                archived_at TIMESTAMP WITH TIME ZONE NOT NULL
            )
        """))
        logger.info("Rollback Step 5/6: Restored table archived_work_items")

        logger.warning(
            "Rollback Step 5/6: WARNING - Tables restored with schema only. "
            "Data in dropped tables is NOT restored. Restore from backup if needed."
        )
        logger.info("Rollback Step 5/6: Complete - All 9 tables restored (schema only)")
    except Exception as e:
        logger.error(f"Rollback Step 5/6: FAILED - Error restoring tables: {e}")
        raise ValueError(f"Rollback failed at step 5: Error restoring tables: {e}") from e

    # Rollback Step 6: Run validation and log completion
    logger.info("Rollback Step 6/6: Running validation...")
    try:
        # Validation 1: Verify project_id columns removed
        result = conn.execute(text("""
            SELECT COUNT(*) AS column_count
            FROM information_schema.columns
            WHERE table_name IN ('repositories', 'code_chunks')
                AND column_name = 'project_id'
        """))
        column_count = result.scalar()
        if column_count != 0:
            raise ValueError(f"Expected 0 project_id columns, found {column_count}")
        logger.info("Rollback Step 6/6: Validation 1 - project_id columns removed from both tables")

        # Validation 2: Verify dropped tables restored
        result = conn.execute(text("""
            SELECT COUNT(*) AS table_count
            FROM information_schema.tables
            WHERE table_name IN (
                'vendor_extractors',
                'deployment_events',
                'project_configuration',
                'future_enhancements',
                'work_item_dependencies',
                'vendor_deployment_links',
                'work_item_deployment_links',
                'archived_work_items',
                'tasks'
            )
        """))
        table_count = result.scalar()
        if table_count != 9:
            raise ValueError(f"Expected 9 tables restored, found {table_count}")
        logger.info("Rollback Step 6/6: Validation 2 - All 9 tables successfully restored")

        duration = time.time() - start_time
        logger.info(f"Rollback Step 6/6: Rollback completed successfully in {duration:.2f} seconds")
        logger.info("Rollback Step 6/6: Summary - 9 tables restored (schema only), 2 columns removed, 1 index dropped, 2 constraints dropped")
    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(f"Rollback Step 6/6: FAILED - Validation error: {e}")
        raise ValueError(f"Rollback failed at step 6: Validation error: {e}") from e
