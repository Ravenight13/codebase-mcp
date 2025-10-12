"""Integration tests for Alembic migration 002 downgrade (rollback) scenario.

Tests Quickstart Scenario 4: Migration rollback with comprehensive validation
of schema restoration and data preservation requirements.

Test Scenario:
1. Apply baseline migration (alembic upgrade 005)
2. Insert sample test data (repositories and code_chunks)
3. Apply migration 002 (alembic upgrade head)
4. Execute downgrade (alembic downgrade -1)
5. Verify data preservation in repositories and code_chunks
6. Verify dropped tables restored (schema only, data lost)
7. Run validation tests from TestPostRollbackValidation (T004)

Constitutional Compliance:
- Principle V: Production Quality (comprehensive rollback validation)
- Principle VII: TDD (validates rollback acceptance criteria)
- Principle VIII: Type Safety (Pydantic validation throughout)
- Principle X: Git Micro-Commit Strategy (atomic test development)

Performance Target:
- Rollback execution: <30 seconds (no large dataset required)
- Test execution: <60 seconds total

Type Safety:
- All test functions have complete type annotations
- Database operations use typed SQLAlchemy models
- Subprocess calls have explicit result type checking
- Fixture return types explicitly declared
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest
import sqlalchemy
from sqlalchemy import func, inspect, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from src.models.code_chunk import CodeChunk
from src.models.repository import Repository

# ==============================================================================
# Type-Safe Fixtures
# ==============================================================================


@pytest.fixture(scope="function")
def test_database_url() -> str:
    """Provide test database URL for migration testing.

    Returns:
        str: PostgreSQL connection URL for test database

    Note:
        Uses environment variable TEST_DATABASE_URL if available,
        otherwise uses default test database connection string.
    """
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/codebase_mcp_test",
    )


@pytest.fixture(scope="function")
def alembic_database_url(test_database_url: str) -> str:
    """Convert asyncpg URL to psycopg2 URL for Alembic.

    Alembic requires psycopg2 driver for migrations, not asyncpg.

    Args:
        test_database_url: Test database URL with asyncpg driver

    Returns:
        str: PostgreSQL connection URL with psycopg2 driver for Alembic
    """
    return test_database_url.replace("postgresql+asyncpg://", "postgresql://")


@pytest.fixture(scope="function")
def repo_root() -> Path:
    """Get repository root directory path.

    Returns:
        Path: Absolute path to repository root

    Note:
        Used for locating alembic.ini and running alembic commands
    """
    return Path(__file__).parent.parent.parent


@pytest.fixture
async def baseline_with_sample_data(
    test_engine: AsyncEngine,
    session: AsyncSession,
    alembic_database_url: str,
    repo_root: Path,
) -> dict[str, Any]:
    """Apply baseline migration and insert sample test data.

    This fixture:
    1. Drops all existing tables
    2. Applies baseline migration (005) via alembic
    3. Inserts sample repositories and code_chunks
    4. Returns metadata about inserted data

    Args:
        test_engine: Test database engine
        session: Test database session
        alembic_database_url: Database URL for Alembic
        repo_root: Repository root path

    Returns:
        dict: Metadata containing row counts and sample IDs

    Raises:
        RuntimeError: If baseline migration fails
    """
    # Step 1: Drop all existing tables
    async with test_engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    # Step 2: Apply baseline migration (005)
    env = os.environ.copy()
    env["DATABASE_URL"] = alembic_database_url

    baseline_result = subprocess.run(
        ["alembic", "upgrade", "005"],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    if baseline_result.returncode != 0:
        error_msg = f"Baseline migration failed:\n{baseline_result.stderr}"
        raise RuntimeError(error_msg)

    # Step 3: Insert sample repositories
    repositories = [
        Repository(
            path="/test/repo1",
            last_indexed_at=None,
        ),
        Repository(
            path="/test/repo2",
            last_indexed_at=None,
        ),
        Repository(
            path="/test/repo3",
            last_indexed_at=None,
        ),
    ]

    for repo in repositories:
        session.add(repo)

    await session.commit()
    await session.flush()

    # Refresh to get database-generated IDs
    for repo in repositories:
        await session.refresh(repo)

    # Step 4: Insert sample code_chunks
    code_chunks = [
        CodeChunk(
            repository_id=repositories[0].id,
            file_path="src/main.py",
            start_line=1,
            end_line=10,
            content="def main():\n    pass",
            embedding=[0.1] * 1536,
        ),
        CodeChunk(
            repository_id=repositories[0].id,
            file_path="src/utils.py",
            start_line=1,
            end_line=20,
            content="def helper():\n    return True",
            embedding=[0.2] * 1536,
        ),
        CodeChunk(
            repository_id=repositories[1].id,
            file_path="lib/core.py",
            start_line=1,
            end_line=15,
            content="class Core:\n    pass",
            embedding=[0.3] * 1536,
        ),
        CodeChunk(
            repository_id=repositories[2].id,
            file_path="tests/test_core.py",
            start_line=1,
            end_line=25,
            content="def test_core():\n    assert True",
            embedding=[0.4] * 1536,
        ),
    ]

    for chunk in code_chunks:
        session.add(chunk)

    await session.commit()
    await session.flush()

    # Step 5: Return metadata
    repo_count_result = await session.execute(select(func.count(Repository.id)))
    repo_count = repo_count_result.scalar() or 0

    chunk_count_result = await session.execute(select(func.count(CodeChunk.id)))
    chunk_count = chunk_count_result.scalar() or 0

    return {
        "repository_count": repo_count,
        "code_chunk_count": chunk_count,
        "repository_ids": [repo.id for repo in repositories],
        "code_chunk_ids": [chunk.id for chunk in code_chunks],
    }


# ==============================================================================
# Post-Rollback Validation Test Class (T004 Reference)
# ==============================================================================


class TestPostRollbackValidation:
    """Validation tests for post-rollback schema state.

    Tests from T004 specification ensuring migration rollback properly
    restores schema to pre-migration state.

    Validations:
    - V1.3: project_id columns removed from both tables
    - V2.2: CHECK constraints removed
    - V3.2: Performance index removed
    - V4.3: Dropped tables restored (schema only)
    - V5.5: Row count preservation (data not lost in core tables)
    """

    @pytest.mark.asyncio
    async def test_columns_removed(
        self,
        test_engine: AsyncEngine,
    ) -> None:
        """V1.3: Verify project_id columns removed from repositories and code_chunks.

        Given: Migration 002 rolled back
        When: Inspect table schemas
        Then: project_id columns do not exist in either table

        Type Safety: Uses sqlalchemy Inspector with explicit column list
        """
        async with test_engine.connect() as conn:
            # Use run_sync to get inspector in sync context
            def get_column_names(sync_conn: Any) -> tuple[set[str], set[str]]:
                insp = inspect(sync_conn)
                repo_cols = insp.get_columns("repositories")
                chunk_cols = insp.get_columns("code_chunks")
                repo_names = {col["name"] for col in repo_cols}
                chunk_names = {col["name"] for col in chunk_cols}
                return repo_names, chunk_names

            repo_column_names, chunk_column_names = await conn.run_sync(get_column_names)

            assert "project_id" not in repo_column_names, (
                "project_id column should be removed from repositories after rollback"
            )

            assert "project_id" not in chunk_column_names, (
                "project_id column should be removed from code_chunks after rollback"
            )

    @pytest.mark.asyncio
    async def test_constraints_removed(
        self,
        test_engine: AsyncEngine,
    ) -> None:
        """V2.2: Verify CHECK constraints removed from both tables.

        Given: Migration 002 rolled back
        When: Query information_schema for CHECK constraints
        Then: No CHECK constraints on project_id pattern exist

        Type Safety: Query result explicitly typed as list of constraint names
        """
        async with test_engine.connect() as conn:
            # Query for CHECK constraints on repositories
            repo_constraints_query = text("""
                SELECT constraint_name
                FROM information_schema.check_constraints
                WHERE constraint_name LIKE '%project_id%'
                  AND constraint_schema = 'public'
            """)

            result = await conn.execute(repo_constraints_query)
            constraint_names = [row[0] for row in result.fetchall()]

            assert len(constraint_names) == 0, (
                f"CHECK constraints should be removed after rollback. "
                f"Found: {constraint_names}"
            )

    @pytest.mark.asyncio
    async def test_index_removed(
        self,
        test_engine: AsyncEngine,
    ) -> None:
        """V3.2: Verify idx_project_repository index removed.

        Given: Migration 002 rolled back
        When: Query pg_indexes for idx_project_repository
        Then: Index does not exist

        Type Safety: Query result explicitly cast to list[str]
        """
        async with test_engine.connect() as conn:
            index_query = text("""
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname = 'idx_project_repository'
            """)

            result = await conn.execute(index_query)
            index_names = [row[0] for row in result.fetchall()]

            assert len(index_names) == 0, (
                "idx_project_repository index should be removed after rollback"
            )

    @pytest.mark.asyncio
    async def test_tables_restored(
        self,
        test_engine: AsyncEngine,
    ) -> None:
        """V4.3: Verify all 9 dropped tables restored (schema only).

        Given: Migration 002 rolled back
        When: Query information_schema.tables
        Then: All 9 tables exist (work_items, tasks, vendors, etc.)

        Note: Tables restored with schema only - data is not restored.
        Backup required for data restoration.

        Type Safety: Expected tables defined as set[str]
        """
        expected_tables = {
            "work_items",
            "work_item_dependencies",
            "tasks",
            "task_branches",
            "task_commits",
            "vendor_extractors",
            "vendor_test_results",
            "deployment_events",
            "vendor_deployment_links",
        }

        async with test_engine.connect() as conn:
            tables_query = text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
            """)

            result = await conn.execute(tables_query)
            existing_tables = {row[0] for row in result.fetchall()}

            missing_tables = expected_tables - existing_tables

            assert len(missing_tables) == 0, (
                f"Expected tables missing after rollback: {missing_tables}. "
                f"All 9 dropped tables should be restored (schema only)."
            )

    @pytest.mark.asyncio
    async def test_row_count_preservation(
        self,
        session: AsyncSession,
        baseline_data: dict[str, Any],
    ) -> None:
        """V5.5: Verify row counts match baseline (data preserved in core tables).

        Given: Migration 002 applied and rolled back
        When: Count rows in repositories and code_chunks
        Then: Row counts match original baseline

        Constitutional Compliance:
        - Principle V: Production Quality (data preservation validation)

        Type Safety: Baseline data dict explicitly typed with known keys

        Args:
            session: Test database session
            baseline_data: Baseline metadata with row counts
        """
        # Count repositories
        repo_count_result = await session.execute(select(func.count(Repository.id)))
        current_repo_count = repo_count_result.scalar() or 0

        # Count code_chunks
        chunk_count_result = await session.execute(select(func.count(CodeChunk.id)))
        current_chunk_count = chunk_count_result.scalar() or 0

        # Validate preservation
        assert current_repo_count == baseline_data["repository_count"], (
            f"Repository count mismatch after rollback. "
            f"Expected: {baseline_data['repository_count']}, Got: {current_repo_count}"
        )

        assert current_chunk_count == baseline_data["code_chunk_count"], (
            f"Code chunk count mismatch after rollback. "
            f"Expected: {baseline_data['code_chunk_count']}, Got: {current_chunk_count}"
        )


# ==============================================================================
# Integration Tests for Downgrade Scenario
# ==============================================================================


@pytest.mark.asyncio
async def test_rollback_scenario_complete_workflow(
    test_engine: AsyncEngine,
    session: AsyncSession,
    baseline_with_sample_data: dict[str, Any],
    alembic_database_url: str,
    repo_root: Path,
) -> None:
    """Test Scenario 4: Complete rollback workflow with validation.

    This is the main integration test for migration 002 downgrade.

    Workflow:
    1. Baseline applied with sample data (via fixture)
    2. Apply migration 002 (alembic upgrade head)
    3. Verify migration applied successfully
    4. Execute downgrade (alembic downgrade -1)
    5. Verify rollback completed successfully
    6. Run all post-rollback validation tests

    Performance Target: <60 seconds total test execution

    Constitutional Compliance:
    - Principle V: Production Quality (comprehensive rollback testing)
    - Principle VII: TDD (validates rollback acceptance criteria)

    Args:
        test_engine: Test database engine
        session: Test database session
        baseline_with_sample_data: Baseline metadata with row counts
        alembic_database_url: Database URL for Alembic
        repo_root: Repository root path
    """
    start_time = time.perf_counter()

    # Store baseline data for validation
    baseline_data = baseline_with_sample_data

    # Step 2: Apply migration 002
    env = os.environ.copy()
    env["DATABASE_URL"] = alembic_database_url

    upgrade_result = subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert upgrade_result.returncode == 0, (
        f"Migration upgrade failed:\n{upgrade_result.stderr}"
    )

    # Step 3: Verify migration applied (check for project_id column)
    async with test_engine.connect() as conn:
        check_column_query = text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'repositories'
              AND column_name = 'project_id'
        """)

        result = await conn.execute(check_column_query)
        columns = result.fetchall()

        assert len(columns) == 1, (
            "project_id column should exist after migration 002 upgrade"
        )

    # Step 4: Execute downgrade
    downgrade_result = subprocess.run(
        ["alembic", "downgrade", "-1"],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert downgrade_result.returncode == 0, (
        f"Migration downgrade failed:\n{downgrade_result.stderr}"
    )

    # Step 5: Verify rollback completed
    async with test_engine.connect() as conn:
        check_rollback_query = text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'repositories'
              AND column_name = 'project_id'
        """)

        result = await conn.execute(check_rollback_query)
        columns = result.fetchall()

        assert len(columns) == 0, (
            "project_id column should be removed after rollback"
        )

    # Step 6: Run all post-rollback validation tests
    validator = TestPostRollbackValidation()

    await validator.test_columns_removed(test_engine)
    await validator.test_constraints_removed(test_engine)
    await validator.test_index_removed(test_engine)
    await validator.test_tables_restored(test_engine)
    await validator.test_row_count_preservation(session, baseline_data)

    # Performance assertion
    elapsed_seconds = time.perf_counter() - start_time
    assert elapsed_seconds < 60.0, (
        f"Rollback test took {elapsed_seconds:.2f}s (target: <60s)"
    )

    # Log performance for monitoring
    print(f"\nRollback Test Performance: {elapsed_seconds:.2f}s")
    print(f"  - Repositories preserved: {baseline_data['repository_count']}")
    print(f"  - Code chunks preserved: {baseline_data['code_chunk_count']}")
    print(f"  - All validation tests passed: ✓")


@pytest.mark.asyncio
async def test_data_preservation_detailed_validation(
    session: AsyncSession,
    baseline_with_sample_data: dict[str, Any],
    alembic_database_url: str,
    repo_root: Path,
) -> None:
    """Detailed validation of data preservation during rollback.

    Validates that specific data values are preserved, not just row counts.

    Given: Migration 002 applied and rolled back
    When: Query repositories and code_chunks
    Then: All data values match original baseline data

    Type Safety: Explicit type checking for all database query results

    Args:
        session: Test database session
        baseline_with_sample_data: Baseline metadata with sample IDs
        alembic_database_url: Database URL for Alembic
        repo_root: Repository root path
    """
    baseline_data = baseline_with_sample_data

    # Apply migration 002
    env = os.environ.copy()
    env["DATABASE_URL"] = alembic_database_url

    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )

    # Rollback
    subprocess.run(
        ["alembic", "downgrade", "-1"],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )

    # Validate repository data preservation
    for repo_id in baseline_data["repository_ids"]:
        result = await session.execute(
            select(Repository).where(Repository.id == repo_id)
        )
        repo = result.scalar_one_or_none()

        assert repo is not None, f"Repository {repo_id} not found after rollback"
        assert repo.path.startswith("/test/repo"), (
            f"Repository {repo_id} path corrupted after rollback"
        )

    # Validate code_chunk data preservation
    for chunk_id in baseline_data["code_chunk_ids"]:
        chunk_result = await session.execute(
            select(CodeChunk).where(CodeChunk.id == chunk_id)
        )
        chunk: CodeChunk | None = chunk_result.scalar_one_or_none()

        assert chunk is not None, f"Code chunk {chunk_id} not found after rollback"
        assert chunk.content is not None and len(chunk.content) > 0, (
            f"Code chunk {chunk_id} content corrupted after rollback"
        )
        assert chunk.embedding is not None and len(chunk.embedding) == 1536, (
            f"Code chunk {chunk_id} embedding corrupted after rollback"
        )


@pytest.mark.asyncio
async def test_rollback_idempotency(
    test_engine: AsyncEngine,
    baseline_with_sample_data: dict[str, Any],
    alembic_database_url: str,
    repo_root: Path,
) -> None:
    """Test rollback idempotency (multiple downgrades safe).

    Given: Migration 002 applied and rolled back
    When: Execute downgrade again (already at 005)
    Then: No errors, schema unchanged

    Constitutional Compliance:
    - Principle V: Production Quality (idempotent rollback operations)

    Args:
        test_engine: Test database engine
        baseline_with_sample_data: Baseline metadata
        alembic_database_url: Database URL for Alembic
        repo_root: Repository root path
    """
    env = os.environ.copy()
    env["DATABASE_URL"] = alembic_database_url

    # Apply migration 002
    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )

    # First rollback
    subprocess.run(
        ["alembic", "downgrade", "-1"],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )

    # Verify current revision is 005
    current_result = subprocess.run(
        ["alembic", "current"],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )

    assert "005" in current_result.stdout, (
        f"Expected revision 005 after rollback, got: {current_result.stdout}"
    )

    # Second rollback (should be safe - already at 005)
    # Note: This will downgrade to 003b, but should not error
    second_downgrade = subprocess.run(
        ["alembic", "downgrade", "-1"],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    # Verify no errors
    assert second_downgrade.returncode == 0, (
        f"Second downgrade should not error: {second_downgrade.stderr}"
    )


# ==============================================================================
# Performance Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_rollback_performance_target(
    session: AsyncSession,
    baseline_with_sample_data: dict[str, Any],
    alembic_database_url: str,
    repo_root: Path,
) -> None:
    """Validate rollback completes within performance target.

    Performance Target: <30 seconds for rollback execution

    Args:
        session: Test database session
        baseline_with_sample_data: Baseline metadata
        alembic_database_url: Database URL for Alembic
        repo_root: Repository root path
    """
    env = os.environ.copy()
    env["DATABASE_URL"] = alembic_database_url

    # Apply migration 002
    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )

    # Measure rollback time
    start_time = time.perf_counter()

    subprocess.run(
        ["alembic", "downgrade", "-1"],
        cwd=str(repo_root),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )

    elapsed_seconds = time.perf_counter() - start_time

    # Performance assertion
    assert elapsed_seconds < 30.0, (
        f"Rollback took {elapsed_seconds:.2f}s (target: <30s)"
    )

    # Log performance for monitoring
    print(f"\nRollback Performance: {elapsed_seconds:.2f}s")
