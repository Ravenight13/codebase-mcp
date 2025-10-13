"""Integration test for multi-project data isolation (T017).

Tests complete data isolation between project workspaces to ensure
zero cross-contamination.

Test Scenario: Quickstart Scenario 1 - Complete Data Isolation
Validates: Primary Workflow steps 1-12, Acceptance Scenario 1
Traces to: FR-009 (isolated workspace), FR-017 (complete data isolation)

Constitutional Compliance:
- Principle VII: TDD (validates implementation correctness)
- Principle V: Production quality (comprehensive isolation testing)
- Principle I: Simplicity (focused on single concern: isolation)
"""

from __future__ import annotations

from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.mcp.tools.indexing import index_repository
from src.mcp.tools.search import search_code


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def repo_a(tmp_path: Path) -> str:
    """Fixture: Client A codebase with authentication logic.

    Creates a minimal Python repository with distinct authentication
    implementation for Client A.

    Args:
        tmp_path: Pytest fixture providing temporary directory

    Returns:
        Absolute path to repository directory
    """
    repo_dir = tmp_path / "repo-a"
    repo_dir.mkdir()

    # Create distinct Python file for Client A
    (repo_dir / "auth.py").write_text(
        """
def authenticate_user_a(username: str, password: str) -> bool:
    '''Client A authentication implementation'''
    return validate_credentials_a(username, password)

def validate_credentials_a(username: str, password: str) -> bool:
    '''Validate user credentials for Client A'''
    # Implementation details here
    return True
"""
    )

    return str(repo_dir)


@pytest.fixture
def repo_b(tmp_path: Path) -> str:
    """Fixture: Client B codebase with authentication logic.

    Creates a minimal Python repository with distinct authentication
    implementation for Client B.

    Args:
        tmp_path: Pytest fixture providing temporary directory

    Returns:
        Absolute path to repository directory
    """
    repo_dir = tmp_path / "repo-b"
    repo_dir.mkdir()

    # Create distinct Python file for Client B
    (repo_dir / "auth.py").write_text(
        """
def authenticate_user_b(credentials: dict) -> bool:
    '''Client B authentication implementation'''
    return verify_token_b(credentials.get('token'))

def verify_token_b(token: str) -> bool:
    '''Verify authentication token for Client B'''
    # Implementation details here
    return True
"""
    )

    return str(repo_dir)


# ==============================================================================
# Integration Tests
# ==============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_data_isolation(repo_a: str, repo_b: str) -> None:
    """Verify zero cross-project data leakage.

    Test Steps:
    1. Index Client A codebase into project-a workspace
    2. Index Client B codebase into project-b workspace
    3. Search "authentication" in project-a
    4. Verify only Client A results returned
    5. Search "authentication" in project-b
    6. Verify only Client B results returned
    7. Verify no overlap between result sets

    Expected Outcome:
        ✅ Test passes: Zero cross-contamination between projects

    Functional Requirements:
        - FR-009: Isolated workspace (one schema per project)
        - FR-017: Complete data isolation (zero cross-project leakage)

    Args:
        repo_a: Path to Client A repository fixture
        repo_b: Path to Client B repository fixture
    """
    # Step 1: Index Client A codebase into project-a workspace
    result_a = await index_repository.fn(
        repo_path=repo_a,
        project_id="client-a",
        force_reindex=False,
        ctx=None,
    )

    # Verify indexing succeeded
    assert result_a["status"] == "success", f"Client A indexing failed: {result_a}"
    assert result_a["project_id"] == "client-a"
    assert result_a["schema_name"] == "project_client_a"
    assert result_a["files_indexed"] == 1
    assert result_a["chunks_created"] > 0

    # Step 2: Index Client B codebase into project-b workspace
    result_b = await index_repository.fn(
        repo_path=repo_b,
        project_id="client-b",
        force_reindex=False,
        ctx=None,
    )

    # Verify indexing succeeded
    assert result_b["status"] == "success", f"Client B indexing failed: {result_b}"
    assert result_b["project_id"] == "client-b"
    assert result_b["schema_name"] == "project_client_b"
    assert result_b["files_indexed"] == 1
    assert result_b["chunks_created"] > 0

    # Step 3: Search "authentication" in project-a
    results_a = await search_code.fn(
        query="authentication logic",
        project_id="client-a",
        repository_id=None,
        file_type=None,
        directory=None,
        limit=10,
        ctx=None,
    )

    # Step 4: Verify only Client A results returned
    assert len(results_a["results"]) > 0, "Expected results for Client A"
    assert results_a["project_id"] == "client-a"
    assert results_a["schema_name"] == "project_client_a"

    # Verify all results contain Client A specific content
    for result in results_a["results"]:
        content = result["content"]
        assert (
            "authenticate_user_a" in content or "validate_credentials_a" in content
        ), f"Client A result should contain Client A functions: {content}"

        # Verify NO Client B content in Client A results
        assert "authenticate_user_b" not in content, "Client B leakage detected!"
        assert "verify_token_b" not in content, "Client B leakage detected!"

        # Verify file path does not reference client-b
        file_path = result["file_path"].lower()
        assert "client-b" not in file_path, f"Client B path leakage: {file_path}"
        assert "repo-b" not in file_path, f"Client B path leakage: {file_path}"

    # Step 5: Search "authentication" in project-b
    results_b = await search_code.fn(
        query="authentication logic",
        project_id="client-b",
        repository_id=None,
        file_type=None,
        directory=None,
        limit=10,
        ctx=None,
    )

    # Step 6: Verify only Client B results returned
    assert len(results_b["results"]) > 0, "Expected results for Client B"
    assert results_b["project_id"] == "client-b"
    assert results_b["schema_name"] == "project_client_b"

    # Verify all results contain Client B specific content
    for result in results_b["results"]:
        content = result["content"]
        assert (
            "authenticate_user_b" in content or "verify_token_b" in content
        ), f"Client B result should contain Client B functions: {content}"

        # Verify NO Client A content in Client B results
        assert "authenticate_user_a" not in content, "Client A leakage detected!"
        assert "validate_credentials_a" not in content, "Client A leakage detected!"

        # Verify file path does not reference client-a
        file_path = result["file_path"].lower()
        assert "client-a" not in file_path, f"Client A path leakage: {file_path}"
        assert "repo-a" not in file_path, f"Client A path leakage: {file_path}"

    # Step 7: Verify no overlap between result sets
    files_a = {r["file_path"] for r in results_a["results"]}
    files_b = {r["file_path"] for r in results_b["results"]}

    assert files_a.isdisjoint(
        files_b
    ), f"Cross-project data leakage detected! Overlap: {files_a & files_b}"

    # Verify chunk IDs are also distinct (no shared chunks)
    chunks_a = {r["chunk_id"] for r in results_a["results"]}
    chunks_b = {r["chunk_id"] for r in results_b["results"]}

    assert chunks_a.isdisjoint(
        chunks_b
    ), f"Cross-project chunk leakage detected! Overlap: {chunks_a & chunks_b}"


# ==============================================================================
# Additional Isolation Tests
# ==============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_project_schema_isolation(repo_a: str) -> None:
    """Verify each project gets its own isolated PostgreSQL schema.

    Validates that project workspaces are truly isolated at the database
    schema level, not just through application logic.

    Args:
        repo_a: Path to test repository fixture
    """
    # Index into two different projects
    await index_repository.fn(repo_path=repo_a, project_id="isolated-a")
    await index_repository.fn(repo_path=repo_a, project_id="isolated-b")

    # Search in isolated-a
    results_a = await search_code.fn(query="authentication", project_id="isolated-a")

    # Search in isolated-b
    results_b = await search_code.fn(query="authentication", project_id="isolated-b")

    # Both should succeed (no errors)
    assert results_a["status"] != "error"
    assert results_b["status"] != "error"

    # Schema names should be different
    assert results_a["schema_name"] == "project_isolated_a"
    assert results_b["schema_name"] == "project_isolated_b"
    assert results_a["schema_name"] != results_b["schema_name"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_project_access(repo_a: str, repo_b: str) -> None:
    """Verify concurrent access to different projects does not cause interference.

    Tests that multiple projects can be accessed simultaneously without
    cross-contamination or race conditions.

    Args:
        repo_a: Path to Client A repository fixture
        repo_b: Path to Client B repository fixture
    """
    import asyncio

    # Index both projects
    await index_repository.fn(repo_path=repo_a, project_id="concurrent-a")
    await index_repository.fn(repo_path=repo_b, project_id="concurrent-b")

    # Search both projects concurrently
    results_a_task = search_code.fn(query="authentication", project_id="concurrent-a")
    results_b_task = search_code.fn(query="authentication", project_id="concurrent-b")

    results_a, results_b = await asyncio.gather(results_a_task, results_b_task)

    # Both should succeed
    assert len(results_a["results"]) > 0
    assert len(results_b["results"]) > 0

    # Results should be project-specific
    assert results_a["project_id"] == "concurrent-a"
    assert results_b["project_id"] == "concurrent-b"

    # No cross-contamination
    files_a = {r["file_path"] for r in results_a["results"]}
    files_b = {r["file_path"] for r in results_b["results"]}
    assert files_a.isdisjoint(files_b)
