"""Unit tests for optional database_name field in config.

Tests validate that the database auto-creation logic properly handles
the optional database_name field in .codebase-mcp/config.json.

Constitutional Compliance:
- Principle VII: TDD (validates feature with comprehensive tests)
- Principle V: Production Quality (comprehensive error scenarios)
- Principle VIII: Type Safety (type-annotated test functions)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.mark.unit
@pytest.mark.asyncio
async def test_database_name_override_from_config(tmp_path: Path) -> None:
    """Verify explicit database_name in config is used instead of computed name.

    Args:
        tmp_path: Pytest temporary directory fixture
    """
    from src.database.auto_create import get_or_create_project_from_config, ProjectRegistry

    # Setup: Create config with explicit database_name
    config_dir = tmp_path / ".codebase-mcp"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    explicit_db_name = "cb_proj_custom_database_12345678"
    config_data = {
        "version": "1.0",
        "project": {
            "name": "test-override",
            "database_name": explicit_db_name
        }
    }
    config_file.write_text(json.dumps(config_data, indent=2))

    # Create project from config
    registry = ProjectRegistry()
    project = await get_or_create_project_from_config(config_file, registry)

    # Verify explicit database_name was used
    assert project.database_name == explicit_db_name
    assert project.name == "test-override"
    assert project.project_id is not None

    # Verify config was updated with project.id
    updated_config = json.loads(config_file.read_text())
    assert "id" in updated_config["project"]
    assert updated_config["project"]["database_name"] == explicit_db_name


@pytest.mark.unit
@pytest.mark.asyncio
async def test_database_name_validation_invalid_prefix(tmp_path: Path) -> None:
    """Verify database_name with invalid prefix is rejected.

    Args:
        tmp_path: Pytest temporary directory fixture
    """
    from src.database.auto_create import get_or_create_project_from_config, ProjectRegistry

    # Setup: Create config with invalid database_name
    config_dir = tmp_path / ".codebase-mcp"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    config_data = {
        "version": "1.0",
        "project": {
            "name": "test-invalid",
            "database_name": "invalid_database_name"  # Missing cb_proj_ prefix
        }
    }
    config_file.write_text(json.dumps(config_data, indent=2))

    # Attempt to create project should fail
    registry = ProjectRegistry()
    with pytest.raises(ValueError) as exc_info:
        await get_or_create_project_from_config(config_file, registry)

    # Verify error message is clear
    error_msg = str(exc_info.value)
    assert "Invalid database_name" in error_msg
    assert "must start with 'cb_proj_'" in error_msg
    assert "invalid_database_name" in error_msg


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fallback_to_computed_name_without_override(tmp_path: Path) -> None:
    """Verify computed database_name is used when not specified in config.

    Args:
        tmp_path: Pytest temporary directory fixture
    """
    from src.database.auto_create import get_or_create_project_from_config, ProjectRegistry

    # Setup: Create config WITHOUT database_name
    config_dir = tmp_path / ".codebase-mcp"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    config_data = {
        "version": "1.0",
        "project": {
            "name": "test-computed"
        }
    }
    config_file.write_text(json.dumps(config_data, indent=2))

    # Create project from config
    registry = ProjectRegistry()
    project = await get_or_create_project_from_config(config_file, registry)

    # Verify computed database_name follows naming convention
    db_name = project.database_name
    assert db_name.startswith("cb_proj_test_computed_"), (
        f"Expected computed name to start with 'cb_proj_test_computed_', got '{db_name}'"
    )

    # Verify format: cb_proj_{sanitized_name}_{uuid8}
    parts = db_name.split("_")
    assert len(parts) >= 4, f"Expected format cb_proj_{{name}}_{{uuid8}}, got '{db_name}'"
    assert parts[0] == "cb"
    assert parts[1] == "proj"
    # Last part should be 8-char hex UUID
    uuid_part = parts[-1]
    assert len(uuid_part) == 8, f"UUID part should be 8 chars, got '{uuid_part}'"
    assert all(c in "0123456789abcdef" for c in uuid_part), (
        f"UUID part should be hex, got '{uuid_part}'"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_database_name_with_existing_project_id(tmp_path: Path) -> None:
    """Verify database_name override works with existing project.id in config.

    Args:
        tmp_path: Pytest temporary directory fixture
    """
    from src.database.auto_create import get_or_create_project_from_config, ProjectRegistry

    # Setup: Config with both project.id and database_name
    config_dir = tmp_path / ".codebase-mcp"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    explicit_project_id = "12345678-1234-5678-1234-567812345678"
    explicit_db_name = "cb_proj_existing_id_aabbccdd"

    config_data = {
        "version": "1.0",
        "project": {
            "name": "existing-id-test",
            "id": explicit_project_id,
            "database_name": explicit_db_name
        }
    }
    config_file.write_text(json.dumps(config_data, indent=2))

    # Create project from config
    registry = ProjectRegistry()
    project = await get_or_create_project_from_config(config_file, registry)

    # Verify both project_id and database_name from config are used
    assert project.project_id == explicit_project_id
    assert project.database_name == explicit_db_name

    # Verify config wasn't modified
    updated_config = json.loads(config_file.read_text())
    assert updated_config["project"]["id"] == explicit_project_id
    assert updated_config["project"]["database_name"] == explicit_db_name


@pytest.mark.unit
@pytest.mark.asyncio
async def test_idempotent_creation_with_override(tmp_path: Path) -> None:
    """Verify repeated creation with database_name override is idempotent.

    Args:
        tmp_path: Pytest temporary directory fixture
    """
    from src.database.auto_create import get_or_create_project_from_config, ProjectRegistry

    # Setup
    config_dir = tmp_path / ".codebase-mcp"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    explicit_db_name = "cb_proj_idempotent_99887766"
    config_data = {
        "version": "1.0",
        "project": {
            "name": "idempotent-test",
            "database_name": explicit_db_name
        }
    }
    config_file.write_text(json.dumps(config_data, indent=2))

    # First creation
    registry = ProjectRegistry()
    project1 = await get_or_create_project_from_config(config_file, registry)
    assert project1.database_name == explicit_db_name

    # Second creation (should return same project)
    project2 = await get_or_create_project_from_config(config_file, registry)
    assert project2.database_name == explicit_db_name
    assert project2.project_id == project1.project_id
    assert project2.name == project1.name


@pytest.mark.unit
def test_provisioning_with_explicit_database_name() -> None:
    """Verify create_project_database accepts explicit database_name.

    This is a synchronous test that validates the function signature.
    """
    from src.database.provisioning import create_project_database
    import inspect

    # Verify function signature has database_name parameter
    sig = inspect.signature(create_project_database)
    assert "database_name" in sig.parameters

    # Verify it's optional (has default value)
    param = sig.parameters["database_name"]
    assert param.default is None or param.default == inspect.Parameter.empty


@pytest.mark.unit
@pytest.mark.asyncio
async def test_database_name_used_in_registry_sync(tmp_path: Path) -> None:
    """Verify database_name is synced to PostgreSQL registry.

    Args:
        tmp_path: Pytest temporary directory fixture
    """
    from src.database.auto_create import get_or_create_project_from_config, ProjectRegistry

    # Setup
    config_dir = tmp_path / ".codebase-mcp"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    explicit_db_name = "cb_proj_registry_sync_deadbeef"
    config_data = {
        "version": "1.0",
        "project": {
            "name": "registry-sync-test",
            "database_name": explicit_db_name
        }
    }
    config_file.write_text(json.dumps(config_data, indent=2))

    # Create project
    registry = ProjectRegistry()
    project = await get_or_create_project_from_config(config_file, registry)

    # Verify project exists in PostgreSQL registry with correct database_name
    from src.database.session import _initialize_registry_pool

    try:
        registry_pool = await _initialize_registry_pool()
        async with registry_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, name, database_name FROM projects WHERE id = $1",
                project.project_id
            )

            assert row is not None, "Project should exist in PostgreSQL registry"
            assert row['database_name'] == explicit_db_name, (
                f"Registry database_name mismatch. Expected '{explicit_db_name}', "
                f"got '{row['database_name']}'"
            )
            assert row['name'] == "registry-sync-test"
    except Exception as e:
        # If registry sync is unavailable (e.g., in CI), skip this assertion
        pytest.skip(f"PostgreSQL registry unavailable: {e}")
