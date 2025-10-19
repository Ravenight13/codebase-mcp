"""Integration tests for database_name override in config files.

Tests validate the optional database_name field in .codebase-mcp/config.json:
1. Explicit database_name override from config
2. Fallback to computed database_name when not provided
3. Validation of database_name format (cb_proj_ prefix)
4. Recovery from database mismatches
5. Integration with existing project creation flow

Constitutional Compliance:
- Principle VII: TDD - Comprehensive test coverage for new feature
- Principle VIII: Type Safety - Full type hints in tests
- Principle V: Production Quality - Edge cases and error scenarios
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.database.auto_create import (
    get_or_create_project_from_config,
    write_config,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_name_override_from_config(tmp_path: Path) -> None:
    """Verify explicit database_name from config is used.

    Validates:
    1. Config with explicit database_name field
    2. get_or_create_project_from_config uses explicit value (not computed)
    3. Database is created with the explicit name
    4. Project metadata matches config

    Args:
        tmp_path: Pytest temporary directory fixture
    """
    # Create config with explicit database_name
    config_dir = tmp_path / ".codebase-mcp"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "config.json"

    project_id = "550e8400-e29b-41d4-a716-446655440000"
    explicit_db_name = "cb_proj_test_override_550e8400"

    config = {
        "version": "1.0",
        "project": {
            "name": "test-override",
            "id": project_id,
            "database_name": explicit_db_name
        }
    }
    write_config(config_path, config)

    # Call get_or_create_project_from_config
    project = await get_or_create_project_from_config(config_path)

    # Verify explicit database_name was used (NOT computed)
    assert project.database_name == explicit_db_name, (
        f"Expected explicit database_name '{explicit_db_name}', "
        f"but got '{project.database_name}' (likely computed)"
    )
    assert project.name == "test-override"
    assert project.project_id == project_id

    # Verify database exists in PostgreSQL
    from src.database.session import _initialize_registry_pool

    registry_pool = await _initialize_registry_pool()
    async with registry_pool.acquire() as conn:
        # Check database exists
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            explicit_db_name
        )
        assert db_exists == 1, f"Database {explicit_db_name} should exist"

        # Check registry entry
        row = await conn.fetchrow(
            "SELECT id, name, database_name FROM projects WHERE id = $1",
            project_id
        )
        assert row is not None
        assert row['database_name'] == explicit_db_name


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_name_fallback_to_computed(tmp_path: Path) -> None:
    """Verify fallback to computed database_name when not provided.

    Validates:
    1. Config WITHOUT database_name field
    2. get_or_create_project_from_config computes database_name
    3. Computed name follows format: cb_proj_{name}_{uuid8}
    4. Behavior matches existing logic (backward compatibility)

    Args:
        tmp_path: Pytest temporary directory fixture
    """
    # Create config WITHOUT database_name field
    config_dir = tmp_path / ".codebase-mcp"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "config.json"

    project_id = "660e8400-e29b-41d4-a716-446655440001"

    config = {
        "version": "1.0",
        "project": {
            "name": "test-computed",
            "id": project_id
            # NO database_name field
        }
    }
    write_config(config_path, config)

    # Call get_or_create_project_from_config
    project = await get_or_create_project_from_config(config_path)

    # Verify database_name was computed (not from config)
    # Format: cb_proj_{sanitized_name}_{uuid8}
    expected_prefix = "cb_proj_test_computed_"
    assert project.database_name.startswith(expected_prefix), (
        f"Computed database_name should start with '{expected_prefix}', "
        f"got '{project.database_name}'"
    )

    # Verify UUID suffix (first 8 chars of project_id)
    uuid_suffix = project_id.replace("-", "")[:8]
    assert project.database_name.endswith(uuid_suffix), (
        f"Computed database_name should end with UUID suffix '{uuid_suffix}', "
        f"got '{project.database_name}'"
    )

    # Verify database exists
    from src.database.session import _initialize_registry_pool

    registry_pool = await _initialize_registry_pool()
    async with registry_pool.acquire() as conn:
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            project.database_name
        )
        assert db_exists == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_name_validation_invalid_prefix(tmp_path: Path) -> None:
    """Verify validation rejects database_name without cb_proj_ prefix.

    Validates:
    1. Config with database_name missing 'cb_proj_' prefix
    2. get_or_create_project_from_config raises ValueError
    3. Error message is helpful and explains requirement

    Args:
        tmp_path: Pytest temporary directory fixture
    """
    # Create config with INVALID database_name (missing prefix)
    config_dir = tmp_path / ".codebase-mcp"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "config.json"

    config = {
        "version": "1.0",
        "project": {
            "name": "test-invalid",
            "id": "770e8400-e29b-41d4-a716-446655440002",
            "database_name": "invalid_database_name"  # Missing cb_proj_ prefix
        }
    }
    write_config(config_path, config)

    # Should raise ValueError with helpful message
    with pytest.raises(ValueError) as exc_info:
        await get_or_create_project_from_config(config_path)

    error_message = str(exc_info.value)
    assert "cb_proj_" in error_message, (
        "Error message should explain cb_proj_ prefix requirement"
    )
    assert "invalid_database_name" in error_message, (
        "Error message should include the invalid database_name"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_name_validation_edge_cases(tmp_path: Path) -> None:
    """Verify validation handles edge cases for database_name.

    Tests:
    1. Empty string database_name (should fall back to computed)
    2. Invalid prefix variations (should reject)

    Args:
        tmp_path: Pytest temporary directory fixture
    """
    config_dir = tmp_path / ".codebase-mcp"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "config.json"

    # Test 1: Empty string (falsy, should fall back to computed)
    config = {
        "version": "1.0",
        "project": {
            "name": "test-empty",
            "id": "880e8400-e29b-41d4-a716-446655440003",
            "database_name": ""
        }
    }
    write_config(config_path, config)

    # Empty string is falsy, so should fall back to computed
    project = await get_or_create_project_from_config(config_path)
    assert project.database_name.startswith("cb_proj_test_empty_")

    # Test 2: Invalid prefix variations
    invalid_cases = [
        ("cbproj_test", "880e8400-e29b-41d4-a716-446655440004"),  # Missing underscore
        ("CB_PROJ_test", "880e8400-e29b-41d4-a716-446655440005"),  # Uppercase
        ("cb-proj-test", "880e8400-e29b-41d4-a716-446655440006"),  # Hyphens
        ("codebase_proj_test", "880e8400-e29b-41d4-a716-446655440007"),  # Wrong prefix
    ]

    for invalid_name, test_id in invalid_cases:
        config["project"]["id"] = test_id
        config["project"]["database_name"] = invalid_name
        write_config(config_path, config)

        with pytest.raises(ValueError):
            await get_or_create_project_from_config(config_path)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_name_override_with_existing_database(tmp_path: Path) -> None:
    """Verify override works with existing database.

    Validates:
    1. Create database manually with specific name
    2. Create config pointing to that database
    3. Verify connection works
    4. Verify no duplicate databases created

    Args:
        tmp_path: Pytest temporary directory fixture
    """
    from src.database.provisioning import create_project_database

    # Step 1: Create database manually
    project_id = "990e8400-e29b-41d4-a716-446655440008"
    project_name = "test-existing-db"
    manual_db_name = await create_project_database(project_name, project_id)

    # Step 2: Create config pointing to that database
    config_dir = tmp_path / ".codebase-mcp"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "config.json"

    config = {
        "version": "1.0",
        "project": {
            "name": project_name,
            "id": project_id,
            "database_name": manual_db_name
        }
    }
    write_config(config_path, config)

    # Step 3: Call get_or_create_project_from_config (should reuse database)
    project = await get_or_create_project_from_config(config_path)

    # Verify it reused the existing database
    assert project.database_name == manual_db_name

    # Step 4: Verify no duplicate databases created
    from src.database.session import _initialize_registry_pool

    registry_pool = await _initialize_registry_pool()
    async with registry_pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM pg_database WHERE datname LIKE 'cb_proj_test_existing_db%'"
        )
        assert count == 1, (
            f"Expected exactly 1 database, found {count}. "
            "Duplicate databases may have been created!"
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_name_mismatch_recovery(tmp_path: Path) -> None:
    """Verify recovery when database_name points to non-existent database.

    Validates:
    1. Config with database_name pointing to non-existent database
    2. Auto-provisioning creates the database
    3. Verify database is created successfully

    Args:
        tmp_path: Pytest temporary directory fixture
    """
    # Create config with database_name that doesn't exist yet
    config_dir = tmp_path / ".codebase-mcp"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "config.json"

    # Use a very unique ID to avoid conflicts with previous test runs
    import time
    unique_suffix = str(int(time.time() * 1000000))[-8:]  # Last 8 digits of microsecond timestamp
    project_id = f"aa0e8400-e29b-41d4-a716-4466554400{unique_suffix[:2]}"
    nonexistent_db_name = f"cb_proj_test_recovery_{unique_suffix}"

    config = {
        "version": "1.0",
        "project": {
            "name": "test-recovery",
            "id": project_id,
            "database_name": nonexistent_db_name
        }
    }
    write_config(config_path, config)

    # Verify database does NOT exist yet
    from src.database.session import _initialize_registry_pool

    registry_pool = await _initialize_registry_pool()
    async with registry_pool.acquire() as conn:
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            nonexistent_db_name
        )
        # If database exists from previous run, skip this test
        if db_exists:
            pytest.skip(f"Database {nonexistent_db_name} already exists from previous run")

    # Call get_or_create_project_from_config (should auto-provision)
    project = await get_or_create_project_from_config(config_path)

    # Verify database was auto-provisioned
    async with registry_pool.acquire() as conn:
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            nonexistent_db_name
        )
        assert db_exists == 1, "Database should be auto-provisioned"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_name_override_idempotency(tmp_path: Path) -> None:
    """Verify idempotency when calling with explicit database_name multiple times.

    Validates:
    1. Call get_or_create_project_from_config twice with same config
    2. Verify database created only once
    3. Verify both calls return same project metadata

    Args:
        tmp_path: Pytest temporary directory fixture
    """
    config_dir = tmp_path / ".codebase-mcp"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "config.json"

    project_id = "bb0e8400-e29b-41d4-a716-446655440009"
    explicit_db_name = "cb_proj_test_idempotent_bb0e8400"

    config = {
        "version": "1.0",
        "project": {
            "name": "test-idempotent",
            "id": project_id,
            "database_name": explicit_db_name
        }
    }
    write_config(config_path, config)

    # Call 1: Create project
    project1 = await get_or_create_project_from_config(config_path)
    assert project1.database_name == explicit_db_name

    # Call 2: Should reuse existing project
    project2 = await get_or_create_project_from_config(config_path)
    assert project2.database_name == explicit_db_name
    assert project2.project_id == project1.project_id

    # Verify only ONE database exists
    from src.database.session import _initialize_registry_pool

    registry_pool = await _initialize_registry_pool()
    async with registry_pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM pg_database WHERE datname = $1",
            explicit_db_name
        )
        assert count == 1, f"Expected 1 database, found {count}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_name_with_existing_project_id(tmp_path: Path) -> None:
    """Verify database_name override works with existing project.id in config.

    Validates:
    1. Config has both project.id and database_name
    2. Both should be respected (no conflicts)
    3. Verify database_name matches config (not recomputed from ID)

    Args:
        tmp_path: Pytest temporary directory fixture
    """
    config_dir = tmp_path / ".codebase-mcp"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "config.json"

    explicit_project_id = "cc0e8400-e29b-41d4-a716-446655440010"
    explicit_db_name = "cb_proj_existing_id_cc0e8400"

    config = {
        "version": "1.0",
        "project": {
            "name": "existing-id-test",
            "id": explicit_project_id,
            "database_name": explicit_db_name
        }
    }
    write_config(config_path, config)

    # Call get_or_create_project_from_config
    project = await get_or_create_project_from_config(config_path)

    # Verify both project_id and database_name from config are used
    assert project.project_id == explicit_project_id
    assert project.database_name == explicit_db_name

    # Verify config wasn't modified
    updated_config = json.loads(config_path.read_text())
    assert updated_config["project"]["id"] == explicit_project_id
    assert updated_config["project"]["database_name"] == explicit_db_name


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_name_override_takes_precedence_over_registry(tmp_path: Path) -> None:
    """Verify config's database_name overrides registry's database_name.

    This is the critical test for the database_name override fix.

    Scenario:
    1. Project exists in PostgreSQL registry with database_name = "cb_proj_old_name"
    2. Config file specifies database_name = "cb_proj_new_name"
    3. get_or_create_project_from_config is called

    Expected:
    - The returned Project should have database_name = "cb_proj_new_name" (from config)
    - NOT "cb_proj_old_name" (from registry)
    - This validates the fix in auto_create.py lines 360-368

    Args:
        tmp_path: Pytest temporary directory fixture
    """
    from src.database.session import _initialize_registry_pool

    # Step 1: Create project in PostgreSQL registry with OLD database_name
    project_id = "dd0e8400-e29b-41d4-a716-446655440011"
    project_name = "test-registry-override"
    old_db_name = "cb_proj_old_name_dd0e8400"
    new_db_name = "cb_proj_new_name_dd0e8400"

    # Insert directly into PostgreSQL registry
    registry_pool = await _initialize_registry_pool()
    async with registry_pool.acquire() as conn:
        # Ensure clean state (delete if exists from previous runs)
        await conn.execute(
            "DELETE FROM projects WHERE id = $1",
            project_id
        )

        # Insert project with OLD database_name
        await conn.execute(
            """
            INSERT INTO projects (id, name, description, database_name, created_at, updated_at, metadata)
            VALUES ($1, $2, $3, $4, NOW(), NOW(), $5::jsonb)
            """,
            project_id,
            project_name,
            "Test project for database_name override",
            old_db_name,  # OLD database_name in registry
            json.dumps({})
        )

        # Verify registry has OLD database_name
        row = await conn.fetchrow(
            "SELECT database_name FROM projects WHERE id = $1",
            project_id
        )
        assert row["database_name"] == old_db_name, "Setup failed: registry should have old_db_name"

    # Step 2: Create config with NEW database_name (different from registry)
    config_dir = tmp_path / ".codebase-mcp"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "config.json"

    config = {
        "version": "1.0",
        "project": {
            "name": project_name,
            "id": project_id,
            "database_name": new_db_name  # NEW database_name in config
        }
    }
    write_config(config_path, config)

    # Step 3: Call get_or_create_project_from_config
    project = await get_or_create_project_from_config(config_path)

    # Step 4: CRITICAL ASSERTION - Config's database_name takes precedence
    assert project.database_name == new_db_name, (
        f"FAILED: Config's database_name should override registry's database_name.\n"
        f"Expected: {new_db_name} (from config)\n"
        f"Got: {project.database_name}\n"
        f"Registry had: {old_db_name}\n"
        f"This indicates the fix in auto_create.py lines 360-368 is not working correctly."
    )

    # Verify other fields are correct
    assert project.project_id == project_id
    assert project.name == project_name

    # Step 5: Verify the NEW database exists in PostgreSQL
    async with registry_pool.acquire() as conn:
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            new_db_name
        )
        assert db_exists == 1, f"Database {new_db_name} should exist (auto-provisioned)"

        # Verify OLD database was NOT created
        old_db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            old_db_name
        )
        assert old_db_exists is None, (
            f"Database {old_db_name} should NOT exist. "
            f"Only the config's database_name ({new_db_name}) should be provisioned."
        )
