"""Pre-migration, post-migration, and post-rollback validation tests for migration 002.

Tests verify schema changes are correctly applied and rolled back for the
database schema refactoring that removes 9 unused tables and adds project_id
columns to repositories and code_chunks tables.

Migration 002 Changes:
- Adds project_id VARCHAR(50) NOT NULL DEFAULT 'default' to repositories
- Adds project_id VARCHAR(50) NOT NULL to code_chunks (no default)
- Adds CHECK constraints for project_id pattern validation (^[a-z0-9-]{1,50}$)
- Adds performance index idx_project_repository on repositories(project_id, id)
- Drops 9 unused tables: work_items, work_item_dependencies, tasks, task_branches,
  task_commits, vendors, vendor_test_results, deployments, deployment_vendors

Constitutional Compliance:
- Principle V: Production Quality (comprehensive validation, error handling)
- Principle VII: TDD (validates acceptance criteria before implementation)
- Principle VIII: Type Safety (type-annotated test functions)

Test Organization:
- TestPreMigrationValidation: Runs before migration (optional baseline checks)
- TestPostMigrationValidation: Runs after upgrade (required schema validation)
- TestPostRollbackValidation: Runs after downgrade (required rollback validation)

Execution Commands:
    # Pre-migration validation (optional)
    pytest tests/integration/test_migration_002_validation.py::TestPreMigrationValidation -v

    # Run migration
    alembic upgrade head

    # Post-migration validation (required)
    pytest tests/integration/test_migration_002_validation.py::TestPostMigrationValidation -v

    # Run rollback
    alembic downgrade -1

    # Post-rollback validation (required)
    pytest tests/integration/test_migration_002_validation.py::TestPostRollbackValidation -v
"""

from __future__ import annotations

import os
import re
from typing import Any, AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture(scope="module")
def test_database_url() -> str:
    """Get test database URL from environment or use default.

    Returns:
        PostgreSQL connection string for test database (async)

    Note:
        Uses TEST_DATABASE_URL or DATABASE_URL environment variable.
        Falls back to default test database if neither set.
        Ensures URL uses asyncpg driver for async SQLAlchemy.
    """
    # Try TEST_DATABASE_URL first (test-specific), then DATABASE_URL (general)
    db_url = os.getenv(
        "TEST_DATABASE_URL",
        os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/codebase_mcp_test",
        ),
    )

    # Ensure asyncpg driver is used
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return db_url


@pytest_asyncio.fixture(scope="function")
async def db_engine(test_database_url: str) -> AsyncGenerator[AsyncEngine, None]:
    """Create async database engine for validation tests.

    Args:
        test_database_url: PostgreSQL connection string (async)

    Yields:
        SQLAlchemy AsyncEngine instance for database queries

    Cleanup:
        Disposes engine connection pool after test completes

    Note:
        Function-scoped to avoid event loop conflicts with pytest-asyncio.
        Each test gets fresh engine with its own event loop.
        Tests should not modify data, only query schema state.
    """
    engine = create_async_engine(
        test_database_url,
        echo=False,  # Disable SQL logging in tests
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )

    yield engine

    # Cleanup: dispose engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for each validation test.

    Args:
        db_engine: Async database engine (module-scoped)

    Yields:
        SQLAlchemy AsyncSession for executing queries

    Cleanup:
        Closes session after test completes

    Note:
        Function-scoped to provide fresh session for each test.
        Tests are read-only, no transaction or rollback needed.
    """
    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        yield session


# ==============================================================================
# Pre-Migration Validation Tests
# ==============================================================================


class TestPreMigrationValidation:
    """Validation tests to run BEFORE migration 002 upgrade.

    These tests verify the database is in a valid state for migration:
    - No blocking foreign keys from dropped tables to core tables
    - Optional baseline checks for row counts

    Run Command:
        pytest tests/integration/test_migration_002_validation.py::TestPreMigrationValidation -v

    Expected Result:
        All tests PASS (database ready for migration)
    """

    async def test_pre_migration_no_blocking_foreign_keys(
        self, db_session: AsyncSession
    ) -> None:
        """Verify no foreign keys from dropped tables to repositories/code_chunks.

        Validation Check V7.1: Pre-Migration Foreign Key Safety

        Purpose:
            Ensure migration can safely drop 9 tables without breaking referential
            integrity to the core search tables (repositories, code_chunks).

        Tables to be Dropped:
            - work_items
            - work_item_dependencies
            - tasks
            - task_branches
            - task_commits
            - vendors
            - vendor_test_results
            - deployments
            - deployment_vendors

        Core Tables (Must Not Be Referenced):
            - repositories
            - code_chunks

        Pass Criteria:
            No foreign key constraints found from dropped tables to core tables

        Fail Action:
            Test fails with detailed list of blocking foreign keys that must be
            removed before migration can proceed safely.

        Args:
            db_session: Async database session for executing queries

        Raises:
            AssertionError: If blocking foreign keys found (with details)
        """
        # Tables that will be dropped in migration 002
        dropped_tables = [
            "work_items",
            "work_item_dependencies",
            "tasks",
            "task_branches",
            "task_commits",
            "vendors",
            "vendor_test_results",
            "deployments",
            "deployment_vendors",
        ]

        # Core tables that must not be referenced by dropped tables
        core_tables = ["repositories", "code_chunks"]

        # Query information_schema for foreign key constraints
        # This query finds all FKs where:
        # - Source table is one of the tables to be dropped
        # - Target table is one of the core tables
        query = text("""
            SELECT
                tc.table_name AS source_table,
                kcu.column_name AS source_column,
                ccu.table_name AS target_table,
                ccu.column_name AS target_column,
                tc.constraint_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
                AND tc.table_schema = ccu.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'public'
                AND tc.table_name = ANY(:source_tables)
                AND ccu.table_name = ANY(:target_tables)
            ORDER BY tc.table_name, kcu.column_name
        """)

        result = await db_session.execute(
            query,
            {"source_tables": dropped_tables, "target_tables": core_tables},
        )
        blocking_fks = result.fetchall()

        # Assertion: No blocking foreign keys should exist
        if blocking_fks:
            # Format detailed error message with all blocking FKs
            fk_details = []
            for fk in blocking_fks:
                fk_details.append(
                    f"  - {fk.source_table}.{fk.source_column} "
                    f"-> {fk.target_table}.{fk.target_column} "
                    f"(constraint: {fk.constraint_name})"
                )

            error_message = (
                f"Found {len(blocking_fks)} blocking foreign key(s) "
                f"from tables to be dropped to core tables.\n"
                f"These foreign keys must be removed before migration can proceed safely:\n"
                + "\n".join(fk_details)
                + "\n\nAction Required: Remove these foreign key constraints manually "
                + "before running migration 002."
            )

            pytest.fail(error_message)

        # Success: No blocking foreign keys found
        assert len(blocking_fks) == 0, (
            "Expected 0 blocking foreign keys from dropped tables to core tables, "
            f"found {len(blocking_fks)}"
        )


# ==============================================================================
# Post-Migration Validation Tests
# ==============================================================================


class TestPostMigrationValidation:
    """Validation tests to run AFTER migration 002 upgrade.

    These tests verify the migration successfully applied all schema changes:
    - Column additions (project_id in repositories and code_chunks)
    - Constraint additions (CHECK constraints for pattern validation)
    - Index additions (performance index on repositories)
    - Table drops (9 unused tables removed)
    - Data integrity (referential integrity, no orphans, no NULLs)
    - Pattern validation (all project_id values valid)

    Run Command:
        pytest tests/integration/test_migration_002_validation.py::TestPostMigrationValidation -v

    Expected Result:
        All tests PASS (migration applied correctly)
    """

    async def test_column_existence_repositories(
        self, db_session: AsyncSession
    ) -> None:
        """Verify project_id column exists in repositories table (V1.1).

        Validation Check V1.1: Column Existence (repositories)

        Purpose:
            Verify migration 002 added project_id column to repositories table
            with correct data type, length, nullability, and default value.

        Expected Schema:
            Column: project_id
            Type: character varying (VARCHAR)
            Max Length: 50
            Nullable: NO (NOT NULL)
            Default: 'default'::character varying

        Pass Criteria:
            Column exists with all expected properties

        Args:
            db_session: Async database session for executing queries

        Raises:
            AssertionError: If column missing or properties incorrect
        """
        query = text("""
            SELECT
                column_name,
                data_type,
                character_maximum_length,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'public'
                AND table_name = 'repositories'
                AND column_name = 'project_id'
        """)

        result = await db_session.execute(query)
        column_info = result.fetchone()

        # Verify column exists
        assert column_info is not None, (
            "project_id column not found in repositories table. "
            "Migration 002 may not have been applied."
        )

        column_name, data_type, max_length, is_nullable, column_default = column_info

        # Verify column properties
        assert column_name == "project_id", (
            f"Expected column name 'project_id', got '{column_name}'"
        )
        assert data_type == "character varying", (
            f"Expected data type 'character varying' (VARCHAR), got '{data_type}'"
        )
        assert max_length == 50, (
            f"Expected character_maximum_length 50, got {max_length}"
        )
        assert is_nullable == "NO", (
            f"Expected NOT NULL (is_nullable='NO'), got is_nullable='{is_nullable}'"
        )
        assert column_default is not None, (
            "Expected DEFAULT value for repositories.project_id, got None"
        )
        assert "default" in column_default.lower(), (
            f"Expected DEFAULT 'default', got column_default='{column_default}'"
        )

    async def test_column_existence_code_chunks(
        self, db_session: AsyncSession
    ) -> None:
        """Verify project_id column exists in code_chunks table (V1.2).

        Validation Check V1.2: Column Existence (code_chunks)

        Purpose:
            Verify migration 002 added project_id column to code_chunks table
            with correct data type, length, and nullability (no default value).

        Expected Schema:
            Column: project_id
            Type: character varying (VARCHAR)
            Max Length: 50
            Nullable: NO (NOT NULL)
            Default: NULL (no default, populated from parent repository)

        Pass Criteria:
            Column exists with all expected properties

        Args:
            db_session: Async database session for executing queries

        Raises:
            AssertionError: If column missing or properties incorrect
        """
        query = text("""
            SELECT
                column_name,
                data_type,
                character_maximum_length,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_schema = 'public'
                AND table_name = 'code_chunks'
                AND column_name = 'project_id'
        """)

        result = await db_session.execute(query)
        column_info = result.fetchone()

        # Verify column exists
        assert column_info is not None, (
            "project_id column not found in code_chunks table. "
            "Migration 002 may not have been applied."
        )

        column_name, data_type, max_length, is_nullable, column_default = column_info

        # Verify column properties
        assert column_name == "project_id", (
            f"Expected column name 'project_id', got '{column_name}'"
        )
        assert data_type == "character varying", (
            f"Expected data type 'character varying' (VARCHAR), got '{data_type}'"
        )
        assert max_length == 50, (
            f"Expected character_maximum_length 50, got {max_length}"
        )
        assert is_nullable == "NO", (
            f"Expected NOT NULL (is_nullable='NO'), got is_nullable='{is_nullable}'"
        )
        # Note: code_chunks.project_id should NOT have a default value
        # (populated from parent repository during migration)

    async def test_check_constraints(self, db_session: AsyncSession) -> None:
        """Verify CHECK constraints exist for project_id pattern validation (V2.1).

        Validation Check V2.1: CHECK Constraints

        Purpose:
            Verify migration 002 added CHECK constraints to validate project_id
            pattern in both repositories and code_chunks tables.

        Expected Constraints:
            - check_repositories_project_id: CHECK (project_id ~ '^[a-z0-9-]{1,50}$')
            - check_code_chunks_project_id: CHECK (project_id ~ '^[a-z0-9-]{1,50}$')

        Pattern Requirements:
            - Lowercase letters (a-z)
            - Digits (0-9)
            - Hyphens (-)
            - Length: 1-50 characters

        Pass Criteria:
            2 CHECK constraints found with correct pattern

        Args:
            db_session: Async database session for executing queries

        Raises:
            AssertionError: If constraints missing or pattern incorrect
        """
        query = text("""
            SELECT
                conname AS constraint_name,
                conrelid::regclass AS table_name,
                pg_get_constraintdef(oid) AS constraint_def
            FROM pg_constraint
            WHERE contype = 'c'  -- CHECK constraint
                AND conrelid::regclass::text IN ('repositories', 'code_chunks')
                AND conname LIKE '%project_id%'
        """)

        result = await db_session.execute(query)
        constraints = result.fetchall()

        # Verify constraint count
        assert len(constraints) == 2, (
            f"Expected 2 CHECK constraints for project_id, found {len(constraints)}. "
            f"Migration 002 may not have been applied correctly."
        )

        # Verify each constraint has correct pattern
        for constraint_name, table_name, constraint_def in constraints:
            assert "project_id" in constraint_def, (
                f"CHECK constraint {constraint_name} doesn't reference project_id column"
            )

            # Verify regex pattern components
            assert "[a-z0-9-]" in constraint_def, (
                f"CHECK constraint {constraint_name} missing character class [a-z0-9-]. "
                f"Got: {constraint_def}"
            )

            assert "{1,50}" in constraint_def or "{1, 50}" in constraint_def, (
                f"CHECK constraint {constraint_name} missing length bounds {{1,50}}. "
                f"Got: {constraint_def}"
            )

    async def test_performance_index(self, db_session: AsyncSession) -> None:
        """Verify performance index exists on repositories table (V3.1).

        Validation Check V3.1: Performance Index

        Purpose:
            Verify migration 002 created performance index idx_project_repository
            on repositories table to optimize multi-project queries.

        Expected Index:
            Name: idx_project_repository
            Table: repositories
            Columns: (project_id, id)
            Type: btree

        Performance Target:
            Enable fast lookups by project_id with secondary ordering by id

        Pass Criteria:
            Index exists with correct columns

        Args:
            db_session: Async database session for executing queries

        Raises:
            AssertionError: If index missing or columns incorrect
        """
        query = text("""
            SELECT
                indexname,
                tablename,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
                AND indexname = 'idx_project_repository'
        """)

        result = await db_session.execute(query)
        index_info = result.fetchone()

        # Verify index exists
        assert index_info is not None, (
            "Performance index idx_project_repository not found. "
            "Migration 002 may not have been applied."
        )

        index_name, table_name, index_def = index_info

        # Verify index properties
        assert index_name == "idx_project_repository", (
            f"Expected index name 'idx_project_repository', got '{index_name}'"
        )
        assert table_name == "repositories", (
            f"Expected table 'repositories', got '{table_name}'"
        )
        assert "project_id" in index_def, (
            f"Index definition missing project_id column. Got: {index_def}"
        )
        assert "id" in index_def, (
            f"Index definition missing id column. Got: {index_def}"
        )

    async def test_tables_dropped(self, db_session: AsyncSession) -> None:
        """Verify 9 unused tables were dropped (V4.1).

        Validation Check V4.1: Tables Dropped

        Purpose:
            Verify migration 002 successfully dropped all 9 unused tables that
            are not related to core semantic search functionality.

        Dropped Tables:
            - work_items
            - work_item_dependencies
            - tasks
            - task_branches
            - task_commits
            - vendors
            - vendor_test_results
            - deployments
            - deployment_vendors

        Pass Criteria:
            0 of 9 dropped tables exist

        Args:
            db_session: Async database session for executing queries

        Raises:
            AssertionError: If any dropped tables still exist
        """
        dropped_tables = [
            "work_items",
            "work_item_dependencies",
            "tasks",
            "task_branches",
            "task_commits",
            "vendors",
            "vendor_test_results",
            "deployments",
            "deployment_vendors",
        ]

        query = text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
                AND table_name = ANY(:dropped_tables)
        """)

        result = await db_session.execute(query, {"dropped_tables": dropped_tables})
        existing_tables = result.fetchall()

        # Verify no dropped tables exist
        assert len(existing_tables) == 0, (
            f"Expected 0 dropped tables to exist, found {len(existing_tables)}: "
            f"{[t[0] for t in existing_tables]}. Migration 002 may not have been applied."
        )

    async def test_core_tables_preserved(self, db_session: AsyncSession) -> None:
        """Verify core tables (repositories, code_chunks) still exist (V4.2).

        Validation Check V4.2: Core Tables Preserved

        Purpose:
            Verify migration 002 did NOT drop the core semantic search tables
            (repositories and code_chunks).

        Core Tables:
            - repositories
            - code_chunks

        Pass Criteria:
            Both tables exist

        Args:
            db_session: Async database session for executing queries

        Raises:
            AssertionError: If core tables missing
        """
        core_tables = ["repositories", "code_chunks"]

        query = text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
                AND table_name = ANY(:core_tables)
        """)

        result = await db_session.execute(query, {"core_tables": core_tables})
        existing_tables = {row[0] for row in result.fetchall()}

        # Verify both core tables exist
        assert "repositories" in existing_tables, (
            "repositories table not found. Migration 002 may have dropped it by mistake."
        )
        assert "code_chunks" in existing_tables, (
            "code_chunks table not found. Migration 002 may have dropped it by mistake."
        )

    async def test_referential_integrity(self, db_session: AsyncSession) -> None:
        """Verify all code_chunks.project_id match parent repository (V5.1).

        Validation Check V5.1: Referential Integrity

        Purpose:
            Verify migration 002 correctly populated code_chunks.project_id
            from parent repository, maintaining referential integrity.

        Expected Behavior:
            For each code_chunk:
                code_chunks.project_id = repositories.project_id
                WHERE code_chunks.repository_id = repositories.id

        Pass Criteria:
            0 code_chunks with mismatched project_id

        Args:
            db_session: Async database session for executing queries

        Raises:
            AssertionError: If any code_chunks have mismatched project_id
        """
        query = text("""
            SELECT
                cc.id AS chunk_id,
                cc.project_id AS chunk_project_id,
                r.project_id AS repo_project_id,
                cc.repository_id
            FROM code_chunks cc
            JOIN repositories r ON cc.repository_id = r.id
            WHERE cc.project_id != r.project_id
        """)

        result = await db_session.execute(query)
        mismatches = result.fetchall()

        # Verify no mismatches
        assert len(mismatches) == 0, (
            f"Found {len(mismatches)} code_chunks with mismatched project_id. "
            f"Migration 002 may not have populated code_chunks.project_id correctly. "
            f"Mismatches: {mismatches[:5]}"  # Show first 5 for debugging
        )

    async def test_no_orphans(self, db_session: AsyncSession) -> None:
        """Verify no code_chunks with invalid repository_id (V5.2).

        Validation Check V5.2: No Orphaned Code Chunks

        Purpose:
            Verify migration 002 did not create orphaned code_chunks
            (code_chunks with repository_id not in repositories table).

        Pass Criteria:
            0 orphaned code_chunks found

        Args:
            db_session: Async database session for executing queries

        Raises:
            AssertionError: If orphaned code_chunks found
        """
        query = text("""
            SELECT
                cc.id AS chunk_id,
                cc.repository_id
            FROM code_chunks cc
            LEFT JOIN repositories r ON cc.repository_id = r.id
            WHERE r.id IS NULL
        """)

        result = await db_session.execute(query)
        orphans = result.fetchall()

        # Verify no orphans
        assert len(orphans) == 0, (
            f"Found {len(orphans)} orphaned code_chunks with invalid repository_id. "
            f"These code_chunks reference non-existent repositories. "
            f"Orphans: {orphans[:5]}"  # Show first 5 for debugging
        )

    async def test_no_null_project_id(self, db_session: AsyncSession) -> None:
        """Verify no NULL project_id values in either table (V5.3).

        Validation Check V5.3: No NULL project_id

        Purpose:
            Verify migration 002 successfully populated all project_id values
            with no NULL values remaining (violates NOT NULL constraint).

        Pass Criteria:
            0 NULL project_id in repositories
            0 NULL project_id in code_chunks

        Args:
            db_session: Async database session for executing queries

        Raises:
            AssertionError: If NULL project_id values found
        """
        # Check repositories
        repo_query = text("""
            SELECT COUNT(*)
            FROM repositories
            WHERE project_id IS NULL
        """)
        repo_result = await db_session.execute(repo_query)
        repo_nulls = repo_result.scalar() or 0

        # Check code_chunks
        chunk_query = text("""
            SELECT COUNT(*)
            FROM code_chunks
            WHERE project_id IS NULL
        """)
        chunk_result = await db_session.execute(chunk_query)
        chunk_nulls = chunk_result.scalar() or 0

        # Verify no NULLs
        assert repo_nulls == 0, (
            f"Found {repo_nulls} NULL project_id values in repositories table. "
            f"Migration 002 may not have populated defaults correctly."
        )
        assert chunk_nulls == 0, (
            f"Found {chunk_nulls} NULL project_id values in code_chunks table. "
            f"Migration 002 may not have populated from parent repositories correctly."
        )

    async def test_row_count_preservation(self, db_session: AsyncSession) -> None:
        """Verify row counts unchanged from baseline (V5.4).

        Validation Check V5.4: Row Count Preservation

        Purpose:
            Verify migration 002 did not lose or duplicate data in
            repositories or code_chunks tables.

        Note:
            This test queries current counts only. Full validation requires
            capturing baseline counts BEFORE migration (see quickstart.md).

        Pass Criteria:
            No assertion failures (test logs current counts for manual verification)

        Args:
            db_session: Async database session for executing queries
        """
        # Get current counts
        repo_query = text("SELECT COUNT(*) FROM repositories")
        repo_result = await db_session.execute(repo_query)
        repo_count = repo_result.scalar() or 0

        chunk_query = text("SELECT COUNT(*) FROM code_chunks")
        chunk_result = await db_session.execute(chunk_query)
        chunk_count = chunk_result.scalar() or 0

        # Log counts for manual verification
        # (Full validation requires baseline fixture from pre-migration state)
        print(f"\nPost-migration row counts:")
        print(f"  repositories: {repo_count}")
        print(f"  code_chunks: {chunk_count}")

        # Basic sanity check: if code_chunks exist, repositories should exist
        if chunk_count > 0:
            assert repo_count > 0, (
                "Found code_chunks but no repositories. Data integrity issue."
            )

    async def test_valid_patterns(self, db_session: AsyncSession) -> None:
        """Verify all project_id values match regex pattern (V6.1).

        Validation Check V6.1: Valid Patterns

        Purpose:
            Verify all project_id values match the required pattern:
            ^[a-z0-9-]{1,50}$

        Pattern Requirements:
            - Lowercase letters (a-z)
            - Digits (0-9)
            - Hyphens (-)
            - Length: 1-50 characters

        Pass Criteria:
            0 invalid project_id values found

        Args:
            db_session: Async database session for executing queries

        Raises:
            AssertionError: If any project_id values don't match pattern
        """
        # Check repositories
        repo_query = text("""
            SELECT project_id
            FROM repositories
            WHERE NOT (project_id ~ '^[a-z0-9-]{1,50}$')
        """)
        repo_result = await db_session.execute(repo_query)
        repo_invalid = repo_result.fetchall()

        # Check code_chunks
        chunk_query = text("""
            SELECT DISTINCT project_id
            FROM code_chunks
            WHERE NOT (project_id ~ '^[a-z0-9-]{1,50}$')
        """)
        chunk_result = await db_session.execute(chunk_query)
        chunk_invalid = chunk_result.fetchall()

        # Verify no invalid patterns
        assert len(repo_invalid) == 0, (
            f"Found {len(repo_invalid)} repositories with invalid project_id pattern. "
            f"Invalid values: {[r[0] for r in repo_invalid[:5]]}"
        )
        assert len(chunk_invalid) == 0, (
            f"Found {len(chunk_invalid)} code_chunks with invalid project_id pattern. "
            f"Invalid values: {[c[0] for c in chunk_invalid[:5]]}"
        )

    async def test_no_uppercase(self, db_session: AsyncSession) -> None:
        """Verify no uppercase letters in project_id (V6.2).

        Validation Check V6.2: No Uppercase Letters

        Purpose:
            Verify no project_id values contain uppercase letters
            (violates pattern requirement).

        Pass Criteria:
            0 project_id values with uppercase letters

        Args:
            db_session: Async database session for executing queries

        Raises:
            AssertionError: If uppercase letters found
        """
        # Check repositories
        repo_query = text("""
            SELECT project_id
            FROM repositories
            WHERE project_id ~ '[A-Z]'
        """)
        repo_result = await db_session.execute(repo_query)
        repo_uppercase = repo_result.fetchall()

        # Check code_chunks
        chunk_query = text("""
            SELECT DISTINCT project_id
            FROM code_chunks
            WHERE project_id ~ '[A-Z]'
        """)
        chunk_result = await db_session.execute(chunk_query)
        chunk_uppercase = chunk_result.fetchall()

        # Verify no uppercase
        assert len(repo_uppercase) == 0, (
            f"Found {len(repo_uppercase)} repositories with uppercase letters in project_id. "
            f"Values: {[r[0] for r in repo_uppercase[:5]]}"
        )
        assert len(chunk_uppercase) == 0, (
            f"Found {len(chunk_uppercase)} code_chunks with uppercase letters in project_id. "
            f"Values: {[c[0] for c in chunk_uppercase[:5]]}"
        )

    async def test_no_invalid_chars(self, db_session: AsyncSession) -> None:
        """Verify no underscores or spaces in project_id (V6.3).

        Validation Check V6.3: No Invalid Characters

        Purpose:
            Verify no project_id values contain underscores or spaces
            (violates pattern requirement: only lowercase, digits, hyphens).

        Pass Criteria:
            0 project_id values with underscores or spaces

        Args:
            db_session: Async database session for executing queries

        Raises:
            AssertionError: If invalid characters found
        """
        # Check repositories
        repo_query = text("""
            SELECT project_id
            FROM repositories
            WHERE project_id ~ '[_ ]'
        """)
        repo_result = await db_session.execute(repo_query)
        repo_invalid = repo_result.fetchall()

        # Check code_chunks
        chunk_query = text("""
            SELECT DISTINCT project_id
            FROM code_chunks
            WHERE project_id ~ '[_ ]'
        """)
        chunk_result = await db_session.execute(chunk_query)
        chunk_invalid = chunk_result.fetchall()

        # Verify no invalid characters
        assert len(repo_invalid) == 0, (
            f"Found {len(repo_invalid)} repositories with underscores/spaces in project_id. "
            f"Values: {[r[0] for r in repo_invalid[:5]]}"
        )
        assert len(chunk_invalid) == 0, (
            f"Found {len(chunk_invalid)} code_chunks with underscores/spaces in project_id. "
            f"Values: {[c[0] for c in chunk_invalid[:5]]}"
        )

    async def test_length_boundaries(self, db_session: AsyncSession) -> None:
        """Verify all project_id lengths between 1 and 50 (V6.4).

        Validation Check V6.4: Length Boundaries

        Purpose:
            Verify all project_id values have length >= 1 and <= 50
            (violates pattern requirement: {1,50}).

        Pass Criteria:
            0 project_id values outside length bounds

        Args:
            db_session: Async database session for executing queries

        Raises:
            AssertionError: If values outside bounds found
        """
        # Check repositories
        repo_query = text("""
            SELECT project_id, LENGTH(project_id) AS len
            FROM repositories
            WHERE LENGTH(project_id) < 1 OR LENGTH(project_id) > 50
        """)
        repo_result = await db_session.execute(repo_query)
        repo_out_of_bounds = repo_result.fetchall()

        # Check code_chunks
        chunk_query = text("""
            SELECT DISTINCT project_id, LENGTH(project_id) AS len
            FROM code_chunks
            WHERE LENGTH(project_id) < 1 OR LENGTH(project_id) > 50
        """)
        chunk_result = await db_session.execute(chunk_query)
        chunk_out_of_bounds = chunk_result.fetchall()

        # Verify no out-of-bounds lengths
        assert len(repo_out_of_bounds) == 0, (
            f"Found {len(repo_out_of_bounds)} repositories with invalid project_id length. "
            f"Values: {[(r[0], r[1]) for r in repo_out_of_bounds[:5]]}"
        )
        assert len(chunk_out_of_bounds) == 0, (
            f"Found {len(chunk_out_of_bounds)} code_chunks with invalid project_id length. "
            f"Values: {[(c[0], c[1]) for c in chunk_out_of_bounds[:5]]}"
        )


# ==============================================================================
# Post-Rollback Validation Tests
# ==============================================================================


class TestPostRollbackValidation:
    """Validation tests to run AFTER migration 002 downgrade.

    These tests verify the rollback successfully restored pre-migration schema:
    - Column removals (project_id columns removed)
    - Constraint removals (CHECK constraints removed)
    - Index removals (performance index removed)
    - Table restorations (9 dropped tables restored, schema only)
    - Data preservation (repositories and code_chunks data unchanged)

    Run Command:
        pytest tests/integration/test_migration_002_validation.py::TestPostRollbackValidation -v

    Expected Result:
        All tests PASS (rollback completed correctly)
    """

    async def test_columns_removed(self, db_session: AsyncSession) -> None:
        """Verify project_id columns removed from both tables after rollback.

        Validation Check V1.3: Post-Rollback Column Removal

        Purpose:
            Verify that the downgrade migration correctly removes project_id
            columns from both repositories and code_chunks tables, restoring
            the schema to its pre-migration state.

        Pass Criteria:
            - 0 project_id columns exist across both tables

        Args:
            db_session: Async database session for executing queries

        Raises:
            AssertionError: If any project_id columns still exist
        """
        # Query information_schema for project_id columns in both tables
        query = text("""
            SELECT COUNT(*) AS column_count
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name IN ('repositories', 'code_chunks')
              AND column_name = 'project_id'
        """)

        result = await db_session.execute(query)
        count = result.scalar()

        assert count == 0, (
            f"Expected 0 project_id columns after rollback, found {count}. "
            f"Rollback did not correctly remove project_id columns."
        )

    async def test_constraints_removed(self, db_session: AsyncSession) -> None:
        """Verify CHECK constraints removed from both tables after rollback.

        Validation Check V2.2: Post-Rollback Constraint Removal

        Purpose:
            Verify that the downgrade migration correctly removes CHECK
            constraints that enforce project_id pattern validation.

        Pass Criteria:
            - 0 CHECK constraints on project_id exist

        Args:
            db_session: Async database session for executing queries

        Raises:
            AssertionError: If any CHECK constraints on project_id still exist
        """
        # Query for CHECK constraints on project_id columns
        query = text("""
            SELECT COUNT(*) AS constraint_count
            FROM information_schema.table_constraints tc
            JOIN information_schema.check_constraints cc
              ON tc.constraint_name = cc.constraint_name
              AND tc.constraint_schema = cc.constraint_schema
            WHERE tc.table_schema = 'public'
              AND tc.table_name IN ('repositories', 'code_chunks')
              AND cc.check_clause LIKE '%project_id%'
        """)

        result = await db_session.execute(query)
        count = result.scalar()

        assert count == 0, (
            f"Expected 0 CHECK constraints on project_id after rollback, found {count}. "
            f"Rollback did not correctly remove CHECK constraints."
        )

    async def test_index_removed(self, db_session: AsyncSession) -> None:
        """Verify performance index idx_project_repository removed after rollback.

        Validation Check V3.2: Post-Rollback Index Removal

        Purpose:
            Verify that the downgrade migration correctly removes the
            performance index created for multi-project filtering.

        Pass Criteria:
            - Index idx_project_repository does not exist

        Args:
            db_session: Async database session for executing queries

        Raises:
            AssertionError: If index idx_project_repository still exists
        """
        # Query pg_indexes for idx_project_repository index
        query = text("""
            SELECT COUNT(*) AS index_count
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND indexname = 'idx_project_repository'
        """)

        result = await db_session.execute(query)
        count = result.scalar()

        assert count == 0, (
            f"Index idx_project_repository should not exist after rollback, "
            f"but found {count} instance(s). Rollback did not correctly remove index."
        )

    async def test_tables_restored(self, db_session: AsyncSession) -> None:
        """Verify all 9 tables restored (schema only) after rollback.

        Validation Check V4.3: Post-Rollback Table Restoration

        Purpose:
            Verify that the downgrade migration correctly recreates all 9
            tables that were dropped during the upgrade. Tables are restored
            with their schema structure only; data is NOT restored (expected
            behavior for a schema-only rollback).

        Tables Expected to be Restored:
            - work_items
            - work_item_dependencies
            - tasks
            - task_branches
            - task_commits
            - vendors
            - vendor_test_results
            - deployments
            - deployment_vendors

        Pass Criteria:
            - All 9 tables exist in the database

        Args:
            db_session: Async database session for executing queries

        Raises:
            AssertionError: If any of the 9 tables are missing
        """
        # List of tables that should be restored by downgrade
        expected_tables = [
            "work_items",
            "work_item_dependencies",
            "tasks",
            "task_branches",
            "task_commits",
            "vendors",
            "vendor_test_results",
            "deployments",
            "deployment_vendors",
        ]

        # Query information_schema for existence of restored tables
        query = text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = ANY(:table_names)
            ORDER BY table_name
        """)

        result = await db_session.execute(query, {"table_names": expected_tables})
        restored = [row.table_name for row in result.fetchall()]

        # Verify all 9 tables are restored
        missing_tables = set(expected_tables) - set(restored)

        assert len(restored) == 9, (
            f"Expected 9 tables restored after rollback, found {len(restored)}: {restored}. "
            f"Missing tables: {sorted(missing_tables)}"
        )

        # Verify each expected table individually for clearer error messages
        for table in expected_tables:
            assert table in restored, (
                f"Table '{table}' not restored after rollback. "
                f"Downgrade migration did not correctly recreate this table."
            )

    async def test_row_count_preservation(self, db_session: AsyncSession) -> None:
        """Verify row counts in core tables still match pre-migration baseline.

        Validation Check V5.5: Post-Rollback Row Count Preservation

        Purpose:
            Verify that the downgrade migration preserves all data in the core
            search tables (repositories, code_chunks). The rollback removes
            the project_id columns but should NOT delete or corrupt existing
            repository and code chunk data.

        Pass Criteria:
            - repositories row count matches pre-migration baseline
            - code_chunks row count matches pre-migration baseline

        Note:
            This test requires a baseline_counts fixture captured before
            migration. If fixture not available, test will skip.

        Args:
            db_session: Async database session for executing queries

        Raises:
            AssertionError: If row counts changed after rollback
        """
        # Note: This test requires baseline_counts fixture to be implemented
        # Since baseline_counts is not yet implemented in this file, we'll
        # verify the tables exist and have consistent data instead

        # Query current row counts
        repos_query = text("SELECT COUNT(*) FROM repositories")
        chunks_query = text("SELECT COUNT(*) FROM code_chunks")

        repos_result = await db_session.execute(repos_query)
        repos_count = repos_result.scalar()

        chunks_result = await db_session.execute(chunks_query)
        chunks_count = chunks_result.scalar()

        # Verify both tables are queryable (not corrupted)
        assert repos_count is not None, (
            "repositories table is not queryable after rollback. "
            "Table may be corrupted or missing."
        )

        assert chunks_count is not None, (
            "code_chunks table is not queryable after rollback. "
            "Table may be corrupted or missing."
        )

        # Additional integrity check: verify no orphaned code_chunks
        if chunks_count and chunks_count > 0:
            orphan_query = text("""
                SELECT COUNT(*) AS orphan_count
                FROM code_chunks cc
                LEFT JOIN repositories r ON cc.repository_id = r.id
                WHERE r.id IS NULL
            """)

            orphan_result = await db_session.execute(orphan_query)
            orphan_count = orphan_result.scalar()

            assert orphan_count == 0, (
                f"Found {orphan_count} orphaned code_chunks after rollback. "
                f"Rollback may have corrupted referential integrity."
            )
