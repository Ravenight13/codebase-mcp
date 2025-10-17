"""Integration tests for config-based project auto-creation.

Tests validate that projects are automatically created from .codebase-mcp/config.json
files when they don't exist in the persistent registry database.

Bug Fix Validation:
- Before fix: All operations defaulted to "default" database
- After fix: Projects auto-created from config files using in-memory registry

Constitutional Compliance:
- Principle VII: TDD (validates bug fix with regression tests)
- Principle V: Production Quality (comprehensive error scenarios)
- Principle VIII: Type Safety (type-annotated test functions)
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastmcp import Context


@pytest.mark.integration
@pytest.mark.asyncio
async def test_project_auto_creation_from_config(tmp_path: Path) -> None:
    """Verify projects are auto-created from config files.

    Validates the bug fix:
    1. Create .codebase-mcp/config.json with project name
    2. Set working directory for session
    3. Index repository (should auto-create project from config)
    4. Verify correct project_id and database_name (not "default")
    5. Verify config file updated with project.id

    Args:
        tmp_path: Pytest temporary directory fixture
    """
    # Setup: Create test repository with config file
    test_repo = tmp_path / "test-repo"
    test_repo.mkdir()

    config_dir = test_repo / ".codebase-mcp"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    # Initial config without project.id
    config_data = {
        "version": "1.0",
        "project": {
            "name": "test-auto-create"
        },
        "auto_switch": True
    }
    config_file.write_text(json.dumps(config_data, indent=2))

    # Create some Python files to index
    (test_repo / "main.py").write_text("def main(): pass\n" * 10)
    (test_repo / "utils.py").write_text("def helper(): pass\n" * 10)

    # Import MCP tools
    from src.mcp.tools.project import set_working_directory
    from src.mcp.tools.indexing import index_repository

    # Create mock Context with session_id
    mock_ctx = MagicMock(spec=Context)
    mock_ctx.session_id = "test-session-auto-create"

    # Step 1: Set working directory (enables session-based resolution)
    session_result = await set_working_directory.fn(
        directory=str(test_repo),
        ctx=mock_ctx
    )

    assert session_result["config_found"] is True, "Config file should be found"
    assert session_result["project_info"]["name"] == "test-auto-create"

    # Step 2: Index repository (should auto-create project from config)
    index_result = await index_repository.fn(
        repo_path=str(test_repo),
        ctx=mock_ctx
    )

    # Verify project was NOT defaulted (bug fix validation)
    assert index_result["project_id"] != "default", (
        f"BUG: Project defaulted to 'default' instead of auto-creating. "
        f"Got project_id='{index_result['project_id']}'"
    )
    assert "cb_proj_test_auto_create_" in index_result["database_name"], (
        f"BUG: Wrong database name. Expected 'cb_proj_test_auto_create_*', "
        f"got '{index_result['database_name']}'"
    )

    # Verify indexing succeeded
    assert index_result["status"] == "success"
    # Note: May index 2 or 3 files (main.py, utils.py, and possibly config.json)
    assert index_result["files_indexed"] >= 2
    assert index_result["chunks_created"] > 0

    # Step 3: Verify config file was updated with project.id
    updated_config = json.loads(config_file.read_text())
    assert "id" in updated_config["project"], "Config should be updated with project.id"

    project_id = updated_config["project"]["id"]
    assert len(project_id) == 36, f"project.id should be UUID format, got '{project_id}'"
    assert project_id == index_result["project_id"], "Config project.id should match indexing result"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_existing_project_id_in_config(tmp_path: Path) -> None:
    """Verify existing project.id in config is used correctly.

    Validates:
    1. Config already has project.id (from previous run)
    2. Index repository
    3. Verify same project_id is used (not regenerated)

    Args:
        tmp_path: Pytest temporary directory fixture
    """
    # Setup: Create config with existing project.id
    test_repo = tmp_path / "test-repo"
    test_repo.mkdir()

    config_dir = test_repo / ".codebase-mcp"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    existing_project_id = "550e8400-e29b-41d4-a716-446655440000"
    config_data = {
        "version": "1.0",
        "project": {
            "name": "existing-project",
            "id": existing_project_id
        },
        "auto_switch": True
    }
    config_file.write_text(json.dumps(config_data, indent=2))

    (test_repo / "main.py").write_text("def main(): pass\n")

    # Import MCP tools
    from src.mcp.tools.project import set_working_directory
    from src.mcp.tools.indexing import index_repository

    mock_ctx = MagicMock(spec=Context)
    mock_ctx.session_id = "test-session-existing"

    # Set working directory and index
    await set_working_directory.fn(directory=str(test_repo), ctx=mock_ctx)
    index_result = await index_repository.fn(repo_path=str(test_repo), ctx=mock_ctx)

    # Verify existing project_id was used (not regenerated)
    assert index_result["project_id"] == existing_project_id

    # Verify config wasn't modified
    updated_config = json.loads(config_file.read_text())
    assert updated_config["project"]["id"] == existing_project_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fallback_to_default_without_config(tmp_path: Path) -> None:
    """Verify fallback to 'default' when no config exists.

    Validates graceful degradation:
    1. Repository has NO .codebase-mcp/config.json
    2. No explicit project_id provided
    3. Should fall back to "default" database

    Args:
        tmp_path: Pytest temporary directory fixture
    """
    # Setup: Repository WITHOUT config file
    test_repo = tmp_path / "test-repo"
    test_repo.mkdir()
    (test_repo / "main.py").write_text("def main(): pass\n")

    from src.mcp.tools.indexing import index_repository

    # Index without config or explicit project_id
    index_result = await index_repository.fn(repo_path=str(test_repo))

    # Should fall back to default
    assert index_result["project_id"] == "default"
    assert index_result["database_name"].startswith("cb_proj_default_")
    assert index_result["status"] == "success"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_uses_correct_project_database(tmp_path: Path) -> None:
    """Verify search operations use project-specific database.

    Validates end-to-end workflow:
    1. Create project from config
    2. Index repository
    3. Search code
    4. Verify search uses same project database (not default)

    Args:
        tmp_path: Pytest temporary directory fixture
    """
    # Setup
    test_repo = tmp_path / "test-repo"
    test_repo.mkdir()

    config_dir = test_repo / ".codebase-mcp"
    config_dir.mkdir()
    config_file = config_dir / "config.json"

    config_data = {
        "version": "1.0",
        "project": {"name": "test-search"},
        "auto_switch": True
    }
    config_file.write_text(json.dumps(config_data, indent=2))

    # Create searchable content
    (test_repo / "auth.py").write_text(
        "def authenticate(username, password):\n"
        "    '''Handle user authentication'''\n"
        "    return validate_credentials(username, password)\n"
    )

    from src.mcp.tools.session import set_working_directory
    from src.mcp.tools.indexing import index_repository
    from src.mcp.tools.search import search_code

    mock_ctx = MagicMock(spec=Context)
    mock_ctx.session_id = "test-session-search"

    # Set working directory, index, and search
    await set_working_directory.fn(directory=str(test_repo), ctx=mock_ctx)

    index_result = await index_repository.fn(repo_path=str(test_repo), ctx=mock_ctx)
    project_id = index_result["project_id"]
    database_name = index_result["database_name"]

    # Verify not using default
    assert project_id != "default"
    assert "cb_proj_test_search_" in database_name

    # Search for authentication logic
    search_result = await search_code.fn(
        query="user authentication",
        ctx=mock_ctx
    )

    # Verify search used same project database
    assert search_result["project_id"] == project_id
    assert search_result["database_name"] == database_name
    assert len(search_result["results"]) > 0

    # Verify we found the authentication function
    found_auth = any("authenticate" in r["content"] for r in search_result["results"])
    assert found_auth, "Should find authentication-related code"
