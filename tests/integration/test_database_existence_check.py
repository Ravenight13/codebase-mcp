"""Integration tests for database existence check bug fix.

Tests validate that get_or_create_project() now properly checks database existence
before returning projects from the PostgreSQL registry. This prevents the bug where
orphaned registry entries (project exists but database doesn't) caused indexing
operations to fail with "database does not exist" errors.

Bug Report: docs/bugs/registry-database-existence-check/BUG_REPORT.md

Test Cases:
1. Registry entry exists, database missing -> auto-provision scenario
2. Registry entry correct, database exists -> no-op scenario
3. Multiple calls are idempotent -> no re-provisioning

Constitutional Compliance:
- Principle VII: TDD (comprehensive test coverage for bug fix)
- Principle V: Production Quality (validates edge cases and recovery)
- Principle VIII: Type Safety (type-annotated test functions)
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastmcp import Context

from src.database.session import _initialize_registry_pool


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auto_provision_missing_database(tmp_path: Path) -> None:
    """Test automatic database provisioning when registry entry orphaned.

    Validates the bug fix where get_or_create_project() now:
    1. Finds project in PostgreSQL registry
    2. Checks if database actually exists
    3. Auto-provisions database if missing
    4. Initializes schema (repositories, code_files, code_chunks tables)

    Scenario: Manual registry corruption or failed database provisioning

    Args:
        tmp_path: Pytest temporary directory fixture
    """
    from src.database.auto_create import get_or_create_project_from_config

    # Setup: Create config file with project metadata
    test_repo = tmp_path / "test-repo"
    test_repo.mkdir()

    config_dir = test_repo / ".codebase-mcp"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    # Create config WITHOUT project.id (will be auto-generated)
    config_data = {
        "version": "1.0",
        "project": {
            "name": "orphaned-registry-project"
        },
        "auto_switch": True
    }
    config_file.write_text(json.dumps(config_data, indent=2))

    # Step 1: Create project and get registry entry with database
    project_v1 = await get_or_create_project_from_config(config_file)
    project_id = project_v1.project_id
    database_name = project_v1.database_name

    # Verify database was created
    registry_pool = await _initialize_registry_pool()
    async with registry_pool.acquire() as conn:
        db_exists_before = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            database_name
        )

    assert db_exists_before == 1, f"Database {database_name} should exist after first creation"

    # Step 2: Manually drop the database to simulate orphaned registry entry
    # This simulates the bug scenario: registry entry exists but database doesn't
    async with registry_pool.acquire() as conn:
        # Terminate active connections to the database
        await conn.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{database_name}'
            AND pid <> pg_backend_pid()
        """)

        # Drop the database
        await conn.execute(f"DROP DATABASE IF EXISTS {database_name}")

        # Verify database is gone
        db_exists_after_drop = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            database_name
        )

    assert db_exists_after_drop is None, f"Database {database_name} should be dropped"

    # Step 3: Verify registry entry still exists (orphaned)
    async with registry_pool.acquire() as conn:
        registry_row = await conn.fetchrow(
            "SELECT id, name, database_name FROM projects WHERE id = $1",
            project_id
        )

    assert registry_row is not None, "Registry entry should still exist (orphaned)"
    assert registry_row['database_name'] == database_name

    # Step 4: Clear in-memory registry to force PostgreSQL lookup
    # This simulates server restart scenario where in-memory registry is empty
    from src.database.auto_create import get_registry
    registry = get_registry()
    registry._projects_by_id.clear()
    registry._projects_by_name.clear()

    # Step 5: Call get_or_create_project again - should auto-provision
    # This is the bug fix validation: should detect missing database and re-provision
    project_v2 = await get_or_create_project_from_config(config_file)

    # Verify same project returned (not a new one)
    assert project_v2.project_id == project_id, "Should reuse same project ID"
    assert project_v2.database_name == database_name, "Should reuse same database name"

    # Step 6: Verify database was auto-provisioned
    async with registry_pool.acquire() as conn:
        db_exists_after_recovery = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            database_name
        )

    assert db_exists_after_recovery == 1, (
        f"BUG FIX FAILED: Database {database_name} was not auto-provisioned. "
        f"Registry entry was orphaned but database existence check did not trigger recovery."
    )

    # Step 7: Verify schema initialized (tables exist)
    from src.database.session import get_or_create_project_pool

    project_pool = await get_or_create_project_pool(database_name)
    async with project_pool.acquire() as conn:
        tables = await conn.fetch("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            AND tablename IN ('repositories', 'code_files', 'code_chunks')
        """)

        table_names = {row['tablename'] for row in tables}

    assert len(table_names) >= 3, (
        f"Schema not initialized correctly. Expected repositories, code_files, code_chunks. "
        f"Found: {table_names}"
    )
    assert 'repositories' in table_names
    assert 'code_files' in table_names
    assert 'code_chunks' in table_names


@pytest.mark.integration
@pytest.mark.asyncio
async def test_no_provision_when_database_exists(tmp_path: Path) -> None:
    """Test no unnecessary provisioning when database already exists.

    Validates that get_or_create_project():
    1. Finds project in registry
    2. Checks database exists
    3. Returns project WITHOUT re-provisioning
    4. No database creation overhead

    Scenario: Normal operation with healthy registry and database

    Args:
        tmp_path: Pytest temporary directory fixture
    """
    from src.database.auto_create import get_or_create_project_from_config

    # Setup: Create config and initialize project
    test_repo = tmp_path / "test-repo"
    test_repo.mkdir()

    config_dir = test_repo / ".codebase-mcp"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    config_data = {
        "version": "1.0",
        "project": {
            "name": "healthy-project"
        },
        "auto_switch": True
    }
    config_file.write_text(json.dumps(config_data, indent=2))

    # Step 1: Create project (registry + database)
    project_v1 = await get_or_create_project_from_config(config_file)
    project_id_v1 = project_v1.project_id
    database_name_v1 = project_v1.database_name

    # Verify database exists
    registry_pool = await _initialize_registry_pool()
    async with registry_pool.acquire() as conn:
        db_exists_v1 = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            database_name_v1
        )

    assert db_exists_v1 == 1, "Database should exist after creation"

    # Step 2: Call get_or_create_project again (should be no-op)
    # Track database count before second call
    async with registry_pool.acquire() as conn:
        db_count_before = await conn.fetchval(
            "SELECT COUNT(*) FROM pg_database WHERE datname LIKE 'cb_proj_healthy_project_%'"
        )

    project_v2 = await get_or_create_project_from_config(config_file)

    # Track database count after second call
    async with registry_pool.acquire() as conn:
        db_count_after = await conn.fetchval(
            "SELECT COUNT(*) FROM pg_database WHERE datname LIKE 'cb_proj_healthy_project_%'"
        )

    # Verify no new database created
    assert db_count_after == db_count_before, (
        f"BUG: Database was re-provisioned unnecessarily. "
        f"Before: {db_count_before}, After: {db_count_after}"
    )

    # Verify same project returned
    assert project_v2.project_id == project_id_v1, "Should return same project ID"
    assert project_v2.database_name == database_name_v1, "Should return same database name"

    # Step 3: Verify registry entry unchanged
    async with registry_pool.acquire() as conn:
        registry_rows = await conn.fetch(
            "SELECT id FROM projects WHERE name = $1",
            "healthy-project"
        )

    assert len(registry_rows) == 1, (
        f"Expected exactly 1 registry entry, found {len(registry_rows)}. "
        f"Duplicate projects created!"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_idempotent_multiple_calls(tmp_path: Path) -> None:
    """Test multiple calls to get_or_create_project are idempotent.

    Validates that:
    1. Create orphaned registry entry (registry exists, database missing)
    2. First call auto-provisions database
    3. Second call finds database and doesn't re-provision
    4. Third call also no-ops
    5. No errors on any call

    Scenario: Recovery followed by normal operation

    Args:
        tmp_path: Pytest temporary directory fixture
    """
    from src.database.auto_create import get_or_create_project_from_config

    # Setup
    test_repo = tmp_path / "test-repo"
    test_repo.mkdir()

    config_dir = test_repo / ".codebase-mcp"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    config_data = {
        "version": "1.0",
        "project": {
            "name": "idempotent-test"
        },
        "auto_switch": True
    }
    config_file.write_text(json.dumps(config_data, indent=2))

    # Step 1: Create initial project
    project_v1 = await get_or_create_project_from_config(config_file)
    project_id = project_v1.project_id
    database_name = project_v1.database_name

    # Step 2: Drop database to create orphaned registry entry
    registry_pool = await _initialize_registry_pool()
    async with registry_pool.acquire() as conn:
        await conn.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{database_name}'
            AND pid <> pg_backend_pid()
        """)
        await conn.execute(f"DROP DATABASE IF EXISTS {database_name}")

    # Step 3: Clear in-memory registry to force PostgreSQL lookup
    from src.database.auto_create import get_registry
    registry = get_registry()
    registry._projects_by_id.clear()
    registry._projects_by_name.clear()

    # Step 4: First recovery call - should auto-provision
    project_v2 = await get_or_create_project_from_config(config_file)

    assert project_v2.project_id == project_id
    assert project_v2.database_name == database_name

    # Verify database provisioned
    async with registry_pool.acquire() as conn:
        db_exists_v2 = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            database_name
        )
    assert db_exists_v2 == 1, "Database should be provisioned after first recovery call"

    # Step 5: Second call - should be no-op (database already exists)
    project_v3 = await get_or_create_project_from_config(config_file)

    assert project_v3.project_id == project_id
    assert project_v3.database_name == database_name

    # Step 6: Third call - also no-op
    project_v4 = await get_or_create_project_from_config(config_file)

    assert project_v4.project_id == project_id
    assert project_v4.database_name == database_name

    # Step 7: Verify only ONE project in registry
    async with registry_pool.acquire() as conn:
        project_count = await conn.fetchval(
            "SELECT COUNT(*) FROM projects WHERE name = $1",
            "idempotent-test"
        )

    assert project_count == 1, (
        f"Expected exactly 1 project, found {project_count}. "
        f"Multiple calls created duplicate projects!"
    )

    # Step 8: Verify only ONE database exists
    async with registry_pool.acquire() as conn:
        db_count = await conn.fetchval(
            "SELECT COUNT(*) FROM pg_database WHERE datname LIKE 'cb_proj_idempotent_test_%'"
        )

    assert db_count == 1, (
        f"Expected exactly 1 database, found {db_count}. "
        f"Database was re-provisioned on subsequent calls!"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_end_to_end_indexing_with_orphaned_registry(tmp_path: Path) -> None:
    """Test complete indexing workflow with orphaned registry entry.

    Validates end-to-end user scenario:
    1. Project created and indexed successfully
    2. Database manually deleted (simulating corruption)
    3. User attempts to index again
    4. System detects missing database and auto-recovers
    5. Indexing proceeds successfully

    Scenario: Real-world recovery from database corruption

    Args:
        tmp_path: Pytest temporary directory fixture
    """
    # Setup test repository with Python files
    test_repo = tmp_path / "test-repo"
    test_repo.mkdir()

    config_dir = test_repo / ".codebase-mcp"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    config_data = {
        "version": "1.0",
        "project": {
            "name": "e2e-recovery-test"
        },
        "auto_switch": True
    }
    config_file.write_text(json.dumps(config_data, indent=2))

    # Create test files to index
    (test_repo / "auth.py").write_text(
        "def authenticate(user, password):\n"
        "    '''Authenticate user credentials'''\n"
        "    return validate(user, password)\n"
    )
    (test_repo / "utils.py").write_text(
        "def helper():\n"
        "    '''Helper function'''\n"
        "    pass\n"
    )

    # Import MCP tools
    from src.mcp.tools.project import set_working_directory
    from src.mcp.tools.background_indexing import start_indexing_background, get_indexing_status
    from src.mcp.tools.search import search_code
    import asyncio

    # Create mock context
    mock_ctx = MagicMock(spec=Context)
    mock_ctx.session_id = "test-session-e2e-recovery"

    # Step 1: Initial indexing - should succeed
    await set_working_directory.fn(directory=str(test_repo), ctx=mock_ctx)

    # Start background indexing job
    job_result = await start_indexing_background.fn(
        repo_path=str(test_repo),
        ctx=mock_ctx
    )
    job_id = job_result["job_id"]

    # Poll for completion
    for _ in range(30):  # Max 30 seconds
        status_result = await get_indexing_status.fn(job_id=job_id, ctx=mock_ctx)
        if status_result["status"] in ["completed", "failed"]:
            break
        await asyncio.sleep(1)

    assert status_result["status"] == "completed", f"Indexing failed: {status_result.get('error_message')}"
    assert status_result["files_indexed"] >= 2
    project_id = job_result["project_id"]
    database_name = job_result["database_name"]

    # Verify search works
    search_result_v1 = await search_code.fn(
        query="authentication",
        ctx=mock_ctx
    )
    assert len(search_result_v1["results"]) > 0

    # Step 2: Simulate database corruption (drop database)
    registry_pool = await _initialize_registry_pool()
    async with registry_pool.acquire() as conn:
        await conn.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{database_name}'
            AND pid <> pg_backend_pid()
        """)
        await conn.execute(f"DROP DATABASE IF EXISTS {database_name}")

        # Verify database is gone
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            database_name
        )
        assert db_exists is None, "Database should be dropped"

    # Step 3: Clear in-memory registry to force PostgreSQL lookup
    from src.database.auto_create import get_registry
    registry = get_registry()
    registry._projects_by_id.clear()
    registry._projects_by_name.clear()

    # Step 4: Attempt to index again - should auto-recover
    # Reset working directory to force config re-load
    await set_working_directory.fn(directory=str(test_repo), ctx=mock_ctx)

    # Start background indexing job again
    job_result_v2 = await start_indexing_background.fn(
        repo_path=str(test_repo),
        ctx=mock_ctx
    )
    job_id_v2 = job_result_v2["job_id"]

    # Poll for completion
    for _ in range(30):
        status_result_v2 = await get_indexing_status.fn(job_id=job_id_v2, ctx=mock_ctx)
        if status_result_v2["status"] in ["completed", "failed"]:
            break
        await asyncio.sleep(1)

    # Verify indexing succeeded after auto-recovery
    assert status_result_v2["status"] == "completed", (
        f"BUG: Indexing failed after database recovery. "
        f"Status: {status_result_v2.get('status')}, "
        f"Error: {status_result_v2.get('error_message')}"
    )
    assert job_result_v2["project_id"] == project_id
    assert job_result_v2["database_name"] == database_name
    assert status_result_v2["files_indexed"] >= 2

    # Step 5: Verify search works after recovery
    search_result_v2 = await search_code.fn(
        query="authentication",
        ctx=mock_ctx
    )

    assert len(search_result_v2["results"]) > 0, (
        "Search should work after database recovery"
    )

    # Step 6: Verify database was re-provisioned
    async with registry_pool.acquire() as conn:
        db_exists_after_recovery = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            database_name
        )

    assert db_exists_after_recovery == 1, (
        "Database should exist after auto-recovery"
    )
