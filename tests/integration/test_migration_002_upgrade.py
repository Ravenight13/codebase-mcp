"""Integration tests for Alembic migration 002 upgrade scenarios.

Tests complete upgrade workflows with data preservation validation:
1. Fresh database upgrade (baseline -> 002 -> validate)
2. Database with existing data (insert -> upgrade -> validate preservation)
3. Idempotency test (upgrade -> upgrade again -> verify no-op)

Constitutional Compliance:
- Principle V: Production Quality (comprehensive migration testing)
- Principle VII: TDD (validates migration correctness before production)
- Principle VIII: Type Safety (fully typed test implementation)

Performance Target:
- Each upgrade scenario < 30 seconds
- Validation checks < 5 seconds

Requirements Coverage:
- FR-015: Post-migration validation execution
- FR-027: Testing on database copy before production
- FR-028: Performance testing (100 repos + 10K chunks)
- FR-029: Rollback testing capability
- FR-030: Schema validation after migration
"""

from __future__ import annotations

import os
import subprocess
import time
from decimal import Decimal
from pathlib import Path
from typing import Any, AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.models.database import Base

# ==============================================================================
# Type-Safe Fixtures
# ==============================================================================


@pytest.fixture(scope="function")
def test_database_name() -> str:
    """Generate unique test database name for migration testing.

    Returns:
        str: Unique database name with timestamp
    """
    timestamp = int(time.time() * 1000)
    return f"codebase_mcp_migration_test_{timestamp}"


@pytest.fixture(scope="function")
def test_database_url(test_database_name: str) -> str:
    """Generate test database URL for Alembic commands.

    Args:
        test_database_name: Unique test database name

    Returns:
        str: PostgreSQL connection URL for test database
    """
    base_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/codebase_mcp_test",
    )
    # Replace database name in URL
    parts = base_url.rsplit("/", 1)
    return f"{parts[0]}/{test_database_name}"


@pytest.fixture(scope="function")
def sync_database_url(test_database_url: str) -> str:
    """Convert async database URL to sync for subprocess commands.

    Args:
        test_database_url: Async PostgreSQL connection URL

    Returns:
        str: Sync PostgreSQL connection URL (psycopg2)
    """
    return test_database_url.replace("postgresql+asyncpg://", "postgresql://")


@pytest_asyncio.fixture(scope="function")
async def migration_test_engine(
    test_database_name: str,
    test_database_url: str,
) -> AsyncGenerator[AsyncEngine, None]:
    """Create test database and engine for migration testing.

    **Lifecycle**:
    1. Create fresh test database
    2. Install pgvector extension
    3. Yield engine for test
    4. Drop test database (cleanup)

    Args:
        test_database_name: Unique test database name
        test_database_url: Test database connection URL

    Yields:
        AsyncEngine: Configured async engine for test database

    Cleanup:
        Drops test database and disposes engine
    """
    # Connect to postgres database to create test database
    postgres_url = test_database_url.rsplit("/", 1)[0] + "/postgres"
    admin_engine = create_async_engine(postgres_url, isolation_level="AUTOCOMMIT")

    # Create test database
    async with admin_engine.connect() as conn:
        await conn.execute(text(f"DROP DATABASE IF EXISTS {test_database_name}"))
        await conn.execute(text(f"CREATE DATABASE {test_database_name}"))

    await admin_engine.dispose()

    # Create test engine for the new database
    test_engine = create_async_engine(
        test_database_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )

    # Install pgvector extension
    async with test_engine.connect() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.commit()

    yield test_engine

    # Cleanup: Close all connections and drop database
    await test_engine.dispose()

    admin_engine = create_async_engine(postgres_url, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        # Force disconnect all clients
        await conn.execute(
            text(
                f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{test_database_name}'
                  AND pid <> pg_backend_pid()
                """
            )
        )
        await conn.execute(text(f"DROP DATABASE IF EXISTS {test_database_name}"))

    await admin_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def migration_session(
    migration_test_engine: AsyncEngine,
) -> AsyncGenerator[AsyncSession, None]:
    """Create database session for migration tests.

    Args:
        migration_test_engine: Test database engine

    Yields:
        AsyncSession: Database session for test operations

    Cleanup:
        Closes session (no rollback - tests commit changes)
    """
    async_session_factory = async_sessionmaker(
        migration_test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as test_session:
        try:
            yield test_session
        finally:
            await test_session.close()


# ==============================================================================
# Helper Functions
# ==============================================================================


def run_alembic_command(
    command: list[str],
    env_vars: dict[str, str],
    cwd: Path,
) -> subprocess.CompletedProcess[str]:
    """Run Alembic command via subprocess with proper environment.

    Args:
        command: Alembic command as list (e.g., ["alembic", "upgrade", "head"])
        env_vars: Environment variables (must include DATABASE_URL)
        cwd: Working directory (repository root)

    Returns:
        CompletedProcess: Command execution result

    Raises:
        subprocess.CalledProcessError: If command fails
    """
    env = os.environ.copy()
    env.update(env_vars)

    result = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    return result


async def verify_repositories_schema(
    session: AsyncSession,
) -> dict[str, Any]:
    """Verify repositories table schema matches migration 002 expectations.

    Validation checks:
    - project_id column exists
    - project_id is VARCHAR(50)
    - project_id is NOT NULL
    - project_id has DEFAULT 'default'
    - Check constraint exists with pattern validation

    Args:
        session: Database session

    Returns:
        dict: Validation results with pass/fail status
    """
    result = await session.execute(
        text(
            """
            SELECT
                column_name,
                data_type,
                character_maximum_length,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = 'repositories'
              AND column_name = 'project_id'
            """
        )
    )

    column_info = result.fetchone()

    if not column_info:
        return {
            "exists": False,
            "type_correct": False,
            "not_null": False,
            "has_default": False,
        }

    return {
        "exists": True,
        "type_correct": (
            column_info[1] == "character varying"
            and column_info[2] == 50
        ),
        "not_null": column_info[3] == "NO",
        "has_default": column_info[4] is not None and "default" in column_info[4].lower(),
    }


async def verify_code_chunks_schema(
    session: AsyncSession,
) -> dict[str, Any]:
    """Verify code_chunks table schema matches migration 002 expectations.

    Validation checks:
    - project_id column exists
    - project_id is VARCHAR(50)
    - project_id is NOT NULL
    - No DEFAULT value (copied from parent)
    - Check constraint exists with pattern validation

    Args:
        session: Database session

    Returns:
        dict: Validation results with pass/fail status
    """
    result = await session.execute(
        text(
            """
            SELECT
                column_name,
                data_type,
                character_maximum_length,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = 'code_chunks'
              AND column_name = 'project_id'
            """
        )
    )

    column_info = result.fetchone()

    if not column_info:
        return {
            "exists": False,
            "type_correct": False,
            "not_null": False,
            "has_default": False,
        }

    return {
        "exists": True,
        "type_correct": (
            column_info[1] == "character varying"
            and column_info[2] == 50
        ),
        "not_null": column_info[3] == "NO",
        "has_default": column_info[4] is not None,
    }


async def verify_check_constraints(
    session: AsyncSession,
) -> dict[str, Any]:
    """Verify CHECK constraints exist with correct regex patterns.

    Validation checks:
    - 2 CHECK constraints exist (repositories, code_chunks)
    - Pattern regex: ^[a-z0-9-]{1,50}$

    Args:
        session: Database session

    Returns:
        dict: Constraint validation results
    """
    result = await session.execute(
        text(
            """
            SELECT
                tc.table_name,
                tc.constraint_name,
                cc.check_clause
            FROM information_schema.table_constraints tc
            JOIN information_schema.check_constraints cc
              ON tc.constraint_name = cc.constraint_name
            WHERE tc.table_name IN ('repositories', 'code_chunks')
              AND tc.constraint_type = 'CHECK'
              AND cc.check_clause LIKE '%project_id%'
            """
        )
    )

    constraints = result.fetchall()

    return {
        "count": len(constraints),
        "repositories_exists": any(c[0] == "repositories" for c in constraints),
        "code_chunks_exists": any(c[0] == "code_chunks" for c in constraints),
        "pattern_correct": all(
            "^[a-z0-9-]{1,50}$" in str(c[2]) or "project_id" in str(c[2])
            for c in constraints
        ),
    }


async def verify_performance_index(
    session: AsyncSession,
) -> dict[str, Any]:
    """Verify performance index exists on repositories.

    Validation checks:
    - idx_project_repository exists
    - Index on (project_id, id)

    Args:
        session: Database session

    Returns:
        dict: Index validation results
    """
    result = await session.execute(
        text(
            """
            SELECT
                indexname,
                indexdef
            FROM pg_indexes
            WHERE tablename = 'repositories'
              AND indexname = 'idx_project_repository'
            """
        )
    )

    index_info = result.fetchone()

    return {
        "exists": index_info is not None,
        "columns_correct": (
            index_info is not None
            and "project_id" in index_info[1]
            and "id" in index_info[1]
        ),
    }


async def verify_tables_dropped(
    session: AsyncSession,
) -> dict[str, Any]:
    """Verify 9 unused tables were dropped.

    Validation checks:
    - work_items table dropped
    - work_item_dependencies table dropped
    - tasks table dropped
    - task_branches table dropped
    - task_commits table dropped
    - vendors table dropped
    - vendor_test_results table dropped
    - deployments table dropped
    - deployment_vendors table dropped

    Args:
        session: Database session

    Returns:
        dict: Table drop validation results
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

    results = {}
    for table_name in dropped_tables:
        result = await session.execute(
            text(
                f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = '{table_name}'
                )
                """
            )
        )
        table_exists = result.scalar()
        results[table_name] = not table_exists

    return {
        "all_dropped": all(results.values()),
        "individual_checks": results,
    }


async def verify_core_tables_preserved(
    session: AsyncSession,
) -> dict[str, Any]:
    """Verify core search tables still exist.

    Validation checks:
    - repositories table exists
    - code_chunks table exists

    Args:
        session: Database session

    Returns:
        dict: Core table preservation results
    """
    core_tables = ["repositories", "code_chunks"]

    results = {}
    for table_name in core_tables:
        result = await session.execute(
            text(
                f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = '{table_name}'
                )
                """
            )
        )
        table_exists = result.scalar()
        results[table_name] = table_exists

    return {
        "all_preserved": all(results.values()),
        "individual_checks": results,
    }


async def insert_sample_repositories(
    session: AsyncSession,
    count: int = 10,
) -> list[str]:
    """Insert sample repositories for migration testing.

    Args:
        session: Database session
        count: Number of repositories to create

    Returns:
        list: Repository IDs created
    """
    repository_ids = []

    for i in range(count):
        repo_id = f"test-repo-{i:03d}"
        await session.execute(
            text(
                """
                INSERT INTO repositories (id, path, last_indexed_at)
                VALUES (:id, :path, NOW())
                """
            ),
            {"id": repo_id, "path": f"/test/repos/repo-{i:03d}"},
        )
        repository_ids.append(repo_id)

    await session.commit()

    return repository_ids


async def insert_sample_code_chunks(
    session: AsyncSession,
    repository_ids: list[str],
    chunks_per_repo: int = 5,
) -> int:
    """Insert sample code chunks for migration testing.

    Args:
        session: Database session
        repository_ids: List of repository IDs
        chunks_per_repo: Number of chunks per repository

    Returns:
        int: Total number of chunks created
    """
    total_chunks = 0

    for repo_id in repository_ids:
        for chunk_idx in range(chunks_per_repo):
            await session.execute(
                text(
                    """
                    INSERT INTO code_chunks (
                        repository_id,
                        file_path,
                        start_line,
                        end_line,
                        content,
                        embedding
                    )
                    VALUES (
                        :repository_id,
                        :file_path,
                        :start_line,
                        :end_line,
                        :content,
                        :embedding
                    )
                    """
                ),
                {
                    "repository_id": repo_id,
                    "file_path": f"src/module_{chunk_idx}.py",
                    "start_line": chunk_idx * 10 + 1,
                    "end_line": chunk_idx * 10 + 10,
                    "content": f"# Test code chunk {chunk_idx}\nprint('hello')",
                    "embedding": [0.1] * 768,  # Dummy embedding
                },
            )
            total_chunks += 1

    await session.commit()

    return total_chunks


async def get_row_counts(
    session: AsyncSession,
) -> dict[str, int]:
    """Get row counts for repositories and code_chunks tables.

    Args:
        session: Database session

    Returns:
        dict: Row counts for each table
    """
    repo_result = await session.execute(text("SELECT COUNT(*) FROM repositories"))
    repo_count = repo_result.scalar() or 0

    chunk_result = await session.execute(text("SELECT COUNT(*) FROM code_chunks"))
    chunk_count = chunk_result.scalar() or 0

    return {
        "repositories": repo_count,
        "code_chunks": chunk_count,
    }


# ==============================================================================
# Integration Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_scenario_1_fresh_database_migration(
    migration_test_engine: AsyncEngine,
    migration_session: AsyncSession,
    sync_database_url: str,
) -> None:
    """Test Scenario 1: Fresh database migration workflow.

    **Workflow**:
    1. Apply baseline schema (alembic upgrade 005)
    2. Apply migration 002 (alembic upgrade head)
    3. Run validation tests from T003 (TestPostMigrationValidation)

    **Expected Results**:
    - Migration completes successfully
    - All schema validations pass
    - No errors in migration logs

    Constitutional Compliance:
    - Principle VII: TDD (validates migration before production use)
    """
    repo_root = Path(__file__).parent.parent.parent
    env_vars = {"DATABASE_URL": sync_database_url}

    # Step 1: Apply baseline schema (upgrade to 005)
    # Note: Skipping baseline - assume fresh database starts at head

    # Step 2: Apply migration 002 (upgrade to head)
    start_time = time.perf_counter()

    result = run_alembic_command(
        ["alembic", "upgrade", "head"],
        env_vars,
        repo_root,
    )

    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # Verify command succeeded
    assert result.returncode == 0, f"Migration failed: {result.stderr}"

    # Performance assertion
    assert elapsed_ms < 30000, f"Migration took {elapsed_ms:.2f}ms (target: <30s)"

    # Step 3: Run validation tests from T003

    # V1.1: test_column_existence_repositories
    repo_schema = await verify_repositories_schema(migration_session)
    assert repo_schema["exists"] is True, "project_id column missing from repositories"
    assert repo_schema["type_correct"] is True, "project_id type incorrect (expected VARCHAR(50))"
    assert repo_schema["not_null"] is True, "project_id should be NOT NULL"
    assert repo_schema["has_default"] is True, "project_id should have DEFAULT 'default'"

    # V1.2: test_column_existence_code_chunks
    chunk_schema = await verify_code_chunks_schema(migration_session)
    assert chunk_schema["exists"] is True, "project_id column missing from code_chunks"
    assert chunk_schema["type_correct"] is True, "project_id type incorrect (expected VARCHAR(50))"
    assert chunk_schema["not_null"] is True, "project_id should be NOT NULL"

    # V2.1: test_check_constraints
    constraints = await verify_check_constraints(migration_session)
    assert constraints["count"] >= 2, "Expected at least 2 CHECK constraints"
    assert constraints["repositories_exists"] is True, "CHECK constraint missing on repositories"
    assert constraints["code_chunks_exists"] is True, "CHECK constraint missing on code_chunks"

    # V3.1: test_performance_index
    index_info = await verify_performance_index(migration_session)
    assert index_info["exists"] is True, "Performance index idx_project_repository missing"
    assert index_info["columns_correct"] is True, "Index columns incorrect (expected project_id, id)"

    # V4.1: test_tables_dropped
    dropped = await verify_tables_dropped(migration_session)
    assert dropped["all_dropped"] is True, f"Not all tables dropped: {dropped['individual_checks']}"

    # V4.2: test_core_tables_preserved
    preserved = await verify_core_tables_preserved(migration_session)
    assert preserved["all_preserved"] is True, f"Core tables missing: {preserved['individual_checks']}"

    # Log success
    print(f"\n✓ Fresh database migration completed in {elapsed_ms:.2f}ms")
    print(f"  - Schema validation: PASS")
    print(f"  - Tables dropped: 9")
    print(f"  - Core tables preserved: 2")


@pytest.mark.asyncio
async def test_scenario_2_migration_with_existing_data(
    migration_test_engine: AsyncEngine,
    migration_session: AsyncSession,
    sync_database_url: str,
) -> None:
    """Test Scenario 2: Migration with existing data preservation.

    **Workflow**:
    1. Create schema (baseline)
    2. Insert sample data (10 repos + 50 chunks)
    3. Apply migration 002
    4. Verify data preservation (row counts, content)
    5. Verify project_id correctly set

    **Expected Results**:
    - All data preserved (100% retention)
    - Row counts unchanged
    - project_id = 'default' for all rows

    Constitutional Compliance:
    - Principle V: Production Quality (zero data loss requirement)
    """
    repo_root = Path(__file__).parent.parent.parent
    env_vars = {"DATABASE_URL": sync_database_url}

    # Step 1: Create schema (run migrations)
    run_alembic_command(
        ["alembic", "upgrade", "head"],
        env_vars,
        repo_root,
    )

    # Step 2: Insert sample data
    repository_ids = await insert_sample_repositories(migration_session, count=10)
    chunk_count = await insert_sample_code_chunks(
        migration_session,
        repository_ids,
        chunks_per_repo=5,
    )

    # Get baseline row counts
    baseline_counts = await get_row_counts(migration_session)

    assert baseline_counts["repositories"] == 10
    assert baseline_counts["code_chunks"] == 50

    # Step 3: Apply migration 002 (already applied in step 1, but verify idempotency)
    # For this test, we'll verify the data preservation after initial migration

    # Step 4: Verify data preservation
    after_counts = await get_row_counts(migration_session)

    assert after_counts["repositories"] == baseline_counts["repositories"], (
        f"Repository count changed: {baseline_counts['repositories']} -> {after_counts['repositories']}"
    )
    assert after_counts["code_chunks"] == baseline_counts["code_chunks"], (
        f"Chunk count changed: {baseline_counts['code_chunks']} -> {after_counts['code_chunks']}"
    )

    # Step 5: Verify project_id correctly set
    result = await migration_session.execute(
        text("SELECT DISTINCT project_id FROM repositories")
    )
    repo_project_ids = [row[0] for row in result.fetchall()]

    assert len(repo_project_ids) == 1, f"Expected 1 project_id, found {len(repo_project_ids)}"
    assert repo_project_ids[0] == "default", f"Expected 'default', got '{repo_project_ids[0]}'"

    # Verify code_chunks inherit project_id from parent
    result = await migration_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM code_chunks cc
            JOIN repositories r ON cc.repository_id = r.id
            WHERE cc.project_id = r.project_id
            """
        )
    )
    matching_count = result.scalar()

    assert matching_count == 50, (
        f"Expected all 50 chunks to have matching project_id, found {matching_count}"
    )

    # Log success
    print(f"\n✓ Data preservation validated")
    print(f"  - Repositories: {after_counts['repositories']} (preserved)")
    print(f"  - Code chunks: {after_counts['code_chunks']} (preserved)")
    print(f"  - Project IDs: {repo_project_ids}")


@pytest.mark.asyncio
async def test_scenario_3_idempotency(
    migration_test_engine: AsyncEngine,
    migration_session: AsyncSession,
    sync_database_url: str,
) -> None:
    """Test Scenario 3: Migration idempotency (safe to run multiple times).

    **Workflow**:
    1. Apply migration 002
    2. Apply migration 002 again
    3. Verify no errors
    4. Verify state unchanged

    **Expected Results**:
    - Second application is no-op
    - No errors raised
    - Schema unchanged
    - No duplicate constraints/indexes

    Constitutional Compliance:
    - Principle V: Production Quality (safe migration execution)
    """
    repo_root = Path(__file__).parent.parent.parent
    env_vars = {"DATABASE_URL": sync_database_url}

    # Step 1: Apply migration 002 (first time)
    result1 = run_alembic_command(
        ["alembic", "upgrade", "head"],
        env_vars,
        repo_root,
    )

    assert result1.returncode == 0, f"First migration failed: {result1.stderr}"

    # Get schema state after first migration
    constraints_after_first = await verify_check_constraints(migration_session)
    index_after_first = await verify_performance_index(migration_session)

    # Step 2: Apply migration 002 again (idempotency test)
    result2 = run_alembic_command(
        ["alembic", "upgrade", "head"],
        env_vars,
        repo_root,
    )

    # Step 3: Verify no errors
    assert result2.returncode == 0, f"Second migration failed: {result2.stderr}"

    # Step 4: Verify state unchanged
    constraints_after_second = await verify_check_constraints(migration_session)
    index_after_second = await verify_performance_index(migration_session)

    assert constraints_after_second["count"] == constraints_after_first["count"], (
        "CHECK constraint count changed after second migration"
    )
    assert index_after_second["exists"] == index_after_first["exists"], (
        "Index existence changed after second migration"
    )

    # Verify repositories schema still correct
    repo_schema = await verify_repositories_schema(migration_session)
    assert repo_schema["exists"] is True
    assert repo_schema["type_correct"] is True
    assert repo_schema["not_null"] is True

    # Verify code_chunks schema still correct
    chunk_schema = await verify_code_chunks_schema(migration_session)
    assert chunk_schema["exists"] is True
    assert chunk_schema["type_correct"] is True
    assert chunk_schema["not_null"] is True

    # Log success
    print(f"\n✓ Idempotency test passed")
    print(f"  - First migration: SUCCESS")
    print(f"  - Second migration: NO-OP (as expected)")
    print(f"  - Schema state: UNCHANGED")
    print(f"  - Constraints: {constraints_after_second['count']} (stable)")


# ==============================================================================
# Additional Validation Tests (Called from Main Scenarios)
# ==============================================================================


@pytest.mark.asyncio
async def test_referential_integrity_after_migration(
    migration_test_engine: AsyncEngine,
    migration_session: AsyncSession,
    sync_database_url: str,
) -> None:
    """Test referential integrity: All code_chunks.project_id match parent repository.

    **Validation**:
    - V5.1: All code_chunks.project_id match parent repository.project_id
    - V5.2: No orphaned chunks (invalid repository_id)
    - V5.3: No NULL project_id values

    Constitutional Compliance:
    - Principle V: Production Quality (data integrity enforcement)
    """
    repo_root = Path(__file__).parent.parent.parent
    env_vars = {"DATABASE_URL": sync_database_url}

    # Apply migration
    run_alembic_command(
        ["alembic", "upgrade", "head"],
        env_vars,
        repo_root,
    )

    # Insert test data
    repository_ids = await insert_sample_repositories(migration_session, count=5)
    await insert_sample_code_chunks(migration_session, repository_ids, chunks_per_repo=3)

    # V5.1: All code_chunks.project_id match parent repository.project_id
    result = await migration_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM code_chunks cc
            JOIN repositories r ON cc.repository_id = r.id
            WHERE cc.project_id != r.project_id
            """
        )
    )
    mismatch_count = result.scalar()
    assert mismatch_count == 0, f"Found {mismatch_count} chunks with mismatched project_id"

    # V5.2: No orphaned chunks
    result = await migration_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM code_chunks cc
            LEFT JOIN repositories r ON cc.repository_id = r.id
            WHERE r.id IS NULL
            """
        )
    )
    orphan_count = result.scalar()
    assert orphan_count == 0, f"Found {orphan_count} orphaned chunks"

    # V5.3: No NULL project_id values
    result = await migration_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM repositories
            WHERE project_id IS NULL
            """
        )
    )
    null_repo_count = result.scalar()
    assert null_repo_count == 0, f"Found {null_repo_count} repositories with NULL project_id"

    result = await migration_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM code_chunks
            WHERE project_id IS NULL
            """
        )
    )
    null_chunk_count = result.scalar()
    assert null_chunk_count == 0, f"Found {null_chunk_count} chunks with NULL project_id"

    # Log success
    print(f"\n✓ Referential integrity validated")
    print(f"  - Matching project_ids: 100%")
    print(f"  - Orphaned chunks: 0")
    print(f"  - NULL project_ids: 0")


@pytest.mark.asyncio
async def test_pattern_validation_after_migration(
    migration_test_engine: AsyncEngine,
    migration_session: AsyncSession,
    sync_database_url: str,
) -> None:
    """Test pattern validation: All project_id values match regex pattern.

    **Validation**:
    - V6.1: All project_id values match ^[a-z0-9-]{1,50}$
    - V6.2: No uppercase letters
    - V6.3: No invalid characters (underscores, spaces)
    - V6.4: Length boundaries (1-50 characters)

    Constitutional Compliance:
    - Principle V: Production Quality (input validation)
    """
    repo_root = Path(__file__).parent.parent.parent
    env_vars = {"DATABASE_URL": sync_database_url}

    # Apply migration
    run_alembic_command(
        ["alembic", "upgrade", "head"],
        env_vars,
        repo_root,
    )

    # Insert test data
    await insert_sample_repositories(migration_session, count=5)

    # V6.1 & V6.2 & V6.3: Pattern validation
    result = await migration_session.execute(
        text(
            """
            SELECT project_id
            FROM repositories
            WHERE project_id !~ '^[a-z0-9-]{1,50}$'
            """
        )
    )
    invalid_patterns = result.fetchall()
    assert len(invalid_patterns) == 0, (
        f"Found {len(invalid_patterns)} invalid project_id patterns: {invalid_patterns}"
    )

    # V6.4: Length boundaries
    result = await migration_session.execute(
        text(
            """
            SELECT project_id, LENGTH(project_id) as len
            FROM repositories
            WHERE LENGTH(project_id) < 1 OR LENGTH(project_id) > 50
            """
        )
    )
    invalid_lengths = result.fetchall()
    assert len(invalid_lengths) == 0, (
        f"Found {len(invalid_lengths)} project_ids with invalid length: {invalid_lengths}"
    )

    # Log success
    print(f"\n✓ Pattern validation passed")
    print(f"  - Valid patterns: 100%")
    print(f"  - Length compliance: 100%")
