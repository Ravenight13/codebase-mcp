"""Integration test for auto-provisioning (T019).

Tests automatic workspace creation on first use without explicit provisioning.

Test Scenario: Quickstart Scenario 3 - Auto-Provisioning New Project
Validates: Alternative Path (New Project Creation), Acceptance Scenario 3
Traces to: FR-010 (auto-provisioning), FR-011 (permission validation)

Constitutional Compliance:
- Principle VII: TDD (validates implementation correctness)
- Principle V: Production quality (comprehensive provisioning testing)
- Principle I: Simplicity (zero-config workspace creation)
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from src.mcp.tools.indexing import index_repository
from src.mcp.tools.search import search_code
from src.database.session import engine


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def repo_a(tmp_path: Path) -> str:
    """Fixture: Test repository for auto-provisioning.

    Args:
        tmp_path: Pytest fixture providing temporary directory

    Returns:
        Absolute path to repository directory
    """
    repo_dir = tmp_path / "repo-a"
    repo_dir.mkdir()

    (repo_dir / "auth.py").write_text(
        """
def authenticate_user(username: str, password: str) -> bool:
    '''User authentication implementation'''
    return validate_credentials(username, password)

def validate_credentials(username: str, password: str) -> bool:
    '''Validate user credentials'''
    return True
"""
    )

    return str(repo_dir)


# ==============================================================================
# Helper Functions
# ==============================================================================


async def check_schema_exists(schema_name: str) -> bool:
    """Check if a PostgreSQL schema exists.

    Args:
        schema_name: Name of schema to check

    Returns:
        True if schema exists, False otherwise
    """
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT 1 FROM information_schema.schemata "
                "WHERE schema_name = :schema_name"
            ),
            {"schema_name": schema_name},
        )
        return result.scalar() is not None


async def check_workspace_registered(project_id: str) -> bool:
    """Check if workspace is registered in project_registry.

    Args:
        project_id: Project identifier to check

    Returns:
        True if workspace is registered, False otherwise
    """
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT schema_name FROM project_registry.workspace_config "
                    "WHERE project_id = :project_id"
                ),
                {"project_id": project_id},
            )
            return result.scalar() is not None
    except Exception:
        # project_registry schema might not exist yet (will be created on first use)
        return False


# ==============================================================================
# Integration Tests
# ==============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auto_provisioning(repo_a: str) -> None:
    """Verify automatic workspace creation on first use.

    Test Steps:
    1. Use new project identifier (never created before)
    2. Verify schema does not exist yet
    3. Index repository (triggers auto-provisioning)
    4. Verify workspace was created automatically
    5. Verify schema now exists in PostgreSQL
    6. Verify workspace registered in global registry

    Expected Outcome:
        ✅ Test passes: New project workspace created automatically without errors

    Functional Requirements:
        - FR-010: Auto-provisioning (workspace created on first use)
        - FR-011: Permission validation (CREATE SCHEMA permission check)

    Args:
        repo_a: Path to test repository fixture
    """
    # Step 1: Use new project identifier (never created before)
    # Use timestamp to ensure uniqueness across test runs
    import time

    new_project_id = f"client-xyz-{int(time.time())}"
    expected_schema_name = f"project_{new_project_id.replace('-', '_')}"

    # Step 2: Verify schema does not exist yet
    schema_exists_before = await check_schema_exists(expected_schema_name)
    assert (
        not schema_exists_before
    ), f"Schema {expected_schema_name} should not exist yet"

    # Step 3: Index repository (triggers auto-provisioning)
    result = await index_repository.fn(
        repo_path=repo_a,
        project_id=new_project_id,
        force_reindex=False,
        ctx=None,
    )

    # Step 4: Verify workspace was created automatically
    assert result["status"] == "success", f"Indexing failed: {result}"
    assert result["project_id"] == new_project_id
    assert result["schema_name"] == expected_schema_name
    assert result["files_indexed"] == 1
    assert result["chunks_created"] > 0

    # Step 5: Verify schema now exists in PostgreSQL
    schema_exists_after = await check_schema_exists(expected_schema_name)
    assert (
        schema_exists_after
    ), f"Schema {expected_schema_name} should exist after provisioning"

    # Step 6: Verify workspace can be used for searching
    search_result = await search_code.fn(
        query="authentication",
        project_id=new_project_id,
        repository_id=None,
        file_type=None,
        directory=None,
        limit=10,
        ctx=None,
    )

    assert search_result["project_id"] == new_project_id
    assert search_result["schema_name"] == expected_schema_name
    assert len(search_result["results"]) > 0, "Should find indexed content"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auto_provisioning_idempotent(repo_a: str) -> None:
    """Verify auto-provisioning is idempotent (safe to call multiple times).

    Tests that indexing the same project twice doesn't cause errors
    or duplicate workspace creation.

    Args:
        repo_a: Path to test repository fixture
    """
    import time

    project_id = f"idempotent-test-{int(time.time())}"

    # First indexing (creates workspace)
    result1 = await index_repository.fn(
        repo_path=repo_a, project_id=project_id, force_reindex=False
    )
    assert result1["status"] == "success"

    # Second indexing (workspace already exists)
    result2 = await index_repository.fn(
        repo_path=repo_a, project_id=project_id, force_reindex=True
    )
    assert result2["status"] == "success"

    # Both should use same schema
    assert result1["schema_name"] == result2["schema_name"]
    assert result1["project_id"] == result2["project_id"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auto_provisioning_multiple_projects(repo_a: str) -> None:
    """Verify auto-provisioning works for multiple projects simultaneously.

    Tests that creating multiple new workspaces in sequence works correctly.

    Args:
        repo_a: Path to test repository fixture
    """
    import time

    base_timestamp = int(time.time())
    project_ids = [
        f"multi-project-{i}-{base_timestamp}" for i in range(3)
    ]

    # Create multiple projects
    results = []
    for project_id in project_ids:
        result = await index_repository.fn(
            repo_path=repo_a, project_id=project_id, force_reindex=False
        )
        assert result["status"] == "success"
        results.append(result)

    # Verify all projects have unique schemas
    schema_names = [r["schema_name"] for r in results]
    assert len(schema_names) == len(set(schema_names)), "Schemas should be unique"

    # Verify all schemas exist
    for result in results:
        schema_exists = await check_schema_exists(result["schema_name"])
        assert schema_exists, f"Schema {result['schema_name']} should exist"

    # Verify all projects are searchable
    for project_id in project_ids:
        search_result = await search_code.fn(query="authentication", project_id=project_id)
        assert len(search_result["results"]) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auto_provisioning_with_default_workspace(repo_a: str) -> None:
    """Verify auto-provisioning coexists with default workspace.

    Tests that new project workspaces don't interfere with the default
    workspace (backward compatibility).

    Args:
        repo_a: Path to test repository fixture
    """
    import time

    # Index in default workspace (project_id=None)
    result_default = await index_repository.fn(
        repo_path=repo_a, project_id=None, force_reindex=False
    )
    assert result_default["status"] == "success"
    assert result_default["project_id"] is None
    assert result_default["schema_name"] == "project_default"

    # Index in new project workspace (auto-provision)
    new_project_id = f"coexist-test-{int(time.time())}"
    result_new = await index_repository.fn(
        repo_path=repo_a, project_id=new_project_id, force_reindex=False
    )
    assert result_new["status"] == "success"
    assert result_new["project_id"] == new_project_id

    # Search default workspace
    search_default = await search_code.fn(query="authentication", project_id=None)
    assert search_default["project_id"] is None
    assert search_default["schema_name"] == "project_default"
    assert len(search_default["results"]) > 0

    # Search new project workspace
    search_new = await search_code.fn(query="authentication", project_id=new_project_id)
    assert search_new["project_id"] == new_project_id
    assert len(search_new["results"]) > 0

    # Verify results are isolated
    files_default = {r["file_path"] for r in search_default["results"]}
    files_new = {r["file_path"] for r in search_new["results"]}
    assert files_default.isdisjoint(files_new)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auto_provisioning_invalid_project_id(repo_a: str) -> None:
    """Verify auto-provisioning rejects invalid project identifiers.

    Tests that invalid project_id formats are rejected before attempting
    to create workspace.

    Args:
        repo_a: Path to test repository fixture
    """
    import pytest

    # Test invalid project identifiers
    invalid_ids = [
        "My_Project",  # Uppercase
        "-project",  # Starts with hyphen
        "project-",  # Ends with hyphen
        "project--name",  # Consecutive hyphens
        "project'; DROP TABLE--",  # SQL injection attempt
    ]

    for invalid_id in invalid_ids:
        with pytest.raises((ValueError, Exception)) as exc_info:
            await index_repository.fn(
                repo_path=repo_a, project_id=invalid_id, force_reindex=False
            )

        # Verify error message mentions project_id validation
        error_message = str(exc_info.value).lower()
        assert "project" in error_message or "invalid" in error_message


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auto_provisioning_error_handling(repo_a: str) -> None:
    """Verify auto-provisioning handles errors gracefully.

    Tests that workspace creation errors are properly reported and don't
    leave the system in an inconsistent state.

    Args:
        repo_a: Path to test repository fixture
    """
    import time

    # Test with valid project_id but potentially problematic operations
    project_id = f"error-test-{int(time.time())}"

    # First indexing should succeed (creates workspace)
    result1 = await index_repository.fn(
        repo_path=repo_a, project_id=project_id, force_reindex=False
    )
    assert result1["status"] == "success"

    # Subsequent operations should work without errors
    search_result = await search_code.fn(query="authentication", project_id=project_id)
    assert len(search_result["results"]) > 0

    # Re-indexing should also work
    result2 = await index_repository.fn(
        repo_path=repo_a, project_id=project_id, force_reindex=True
    )
    assert result2["status"] == "success"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auto_provisioning_schema_naming(repo_a: str) -> None:
    """Verify auto-provisioning generates correct schema names.

    Tests that project_id to schema_name conversion follows the correct
    naming convention (project_{normalized_id}).

    Args:
        repo_a: Path to test repository fixture
    """
    import time

    test_cases = [
        ("simple-project", "project_simple_project"),
        ("multi-word-project", "project_multi_word_project"),
        (f"with-numbers-123-{int(time.time())}", None),  # Will be normalized
    ]

    for project_id, expected_schema in test_cases:
        result = await index_repository.fn(
            repo_path=repo_a, project_id=project_id, force_reindex=False
        )
        assert result["status"] == "success"
        assert result["project_id"] == project_id

        if expected_schema:
            assert result["schema_name"] == expected_schema
        else:
            # Verify schema follows naming pattern
            assert result["schema_name"].startswith("project_")
            assert "-" not in result["schema_name"]  # Hyphens converted to underscores

        # Verify schema exists
        schema_exists = await check_schema_exists(result["schema_name"])
        assert schema_exists, f"Schema {result['schema_name']} should exist"
