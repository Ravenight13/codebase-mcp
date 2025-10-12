"""T013: Contract tests for index_repository with project_id parameter.

Tests validate that index_repository correctly handles the optional project_id
parameter for multi-project workspace isolation.

Constitutional Compliance:
- Principle III: Protocol Compliance (MCP-compliant tool parameters)
- Principle VII: Test-Driven Development (contract validation)
- Principle VIII: Type Safety (mypy --strict compliance)

Functional Requirements:
- FR-002: Project workspace isolation via project_id parameter
- FR-003: Backward compatibility (null project_id uses default workspace)
- FR-009: Auto-provisioning of project schemas on first use
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.mcp.tools.indexing import index_repository

# Extract underlying function from FastMCP FunctionTool wrapper
index_repository_fn = index_repository.fn


@pytest.mark.contract
@pytest.mark.asyncio
async def test_index_repository_with_valid_project_id() -> None:
    """Test index_repository accepts valid project_id parameter.

    Validates:
    - Valid project_id "client-a" is accepted
    - Returns project_id in response
    - Returns schema_name "project_client_a" in response
    - Status is "success"

    Traces to: contracts/mcp-tools.yaml lines 93-160
    """
    # Mock dependencies to avoid actual database operations
    mock_repo_id = uuid4()

    with patch("src.mcp.tools.indexing.get_session") as mock_session_ctx, \
         patch("src.mcp.tools.indexing.index_repository_service") as mock_service:

        # Configure mock async context manager
        mock_db = AsyncMock()
        mock_session_ctx.return_value.__aenter__.return_value = mock_db

        # Configure mock indexer service result
        mock_result = MagicMock()
        mock_result.repository_id = mock_repo_id
        mock_result.files_indexed = 150
        mock_result.chunks_created = 3500
        mock_result.duration_seconds = 12.5
        mock_result.status = "success"
        mock_result.errors = []
        mock_service.return_value = mock_result

        # Create temporary directory for testing
        test_repo = Path("/tmp/test-repo-client-a")
        test_repo.mkdir(exist_ok=True, parents=True)

        try:
            # Call tool with valid project_id
            result = await index_repository_fn(
                repo_path=str(test_repo),
                project_id="client-a",
                force_reindex=False,
            )

            # Validate response structure
            assert result["status"] == "success"
            assert result["project_id"] == "client-a"
            assert result["schema_name"] == "project_client_a"
            assert result["repository_id"] == str(mock_repo_id)
            assert result["files_indexed"] == 150
            assert result["chunks_created"] == 3500
            assert result["duration_seconds"] == 12.5

            # Verify get_session was called with project_id
            mock_session_ctx.assert_called_once_with(project_id="client-a")

        finally:
            # Cleanup
            if test_repo.exists():
                test_repo.rmdir()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_index_repository_with_null_project_id() -> None:
    """Test backward compatibility with null project_id.

    Validates:
    - Null project_id is accepted (backward compatibility)
    - Returns null project_id in response
    - Returns default schema_name "project_default"
    - Status is "success"

    Traces to: contracts/mcp-tools.yaml lines 93-160
    """
    # Mock dependencies
    mock_repo_id = uuid4()

    with patch("src.mcp.tools.indexing.get_session") as mock_session_ctx, \
         patch("src.mcp.tools.indexing.index_repository_service") as mock_service, \
         patch("src.mcp.tools.indexing.resolve_project_id") as mock_resolve:

        # Configure resolve_project_id to return None (no workflow-mcp fallback)
        mock_resolve.return_value = None

        # Configure mock async context manager
        mock_db = AsyncMock()
        mock_session_ctx.return_value.__aenter__.return_value = mock_db

        # Configure mock indexer service result
        mock_result = MagicMock()
        mock_result.repository_id = mock_repo_id
        mock_result.files_indexed = 100
        mock_result.chunks_created = 2000
        mock_result.duration_seconds = 8.3
        mock_result.status = "success"
        mock_result.errors = []
        mock_service.return_value = mock_result

        # Create temporary directory for testing
        test_repo = Path("/tmp/test-repo-default")
        test_repo.mkdir(exist_ok=True, parents=True)

        try:
            # Call tool with null project_id (backward compatibility)
            result = await index_repository_fn(
                repo_path=str(test_repo),
                project_id=None,
                force_reindex=False,
            )

            # Validate response structure
            assert result["status"] == "success"
            assert result["project_id"] is None
            assert result["schema_name"] == "project_default"
            assert result["repository_id"] == str(mock_repo_id)
            assert result["files_indexed"] == 100
            assert result["chunks_created"] == 2000

            # Verify get_session was called with None (default workspace)
            mock_session_ctx.assert_called_once_with(project_id=None)

        finally:
            # Cleanup
            if test_repo.exists():
                test_repo.rmdir()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_index_repository_project_id_with_hyphens() -> None:
    """Test project_id with multiple hyphens (valid format).

    Validates:
    - Multi-hyphen project_id "my-project-123" is accepted
    - Schema name correctly converts hyphens to underscores
    - Returns "project_my_project_123" as schema_name

    Traces to: contracts/mcp-tools.yaml lines 28-37
    """
    # Mock dependencies
    mock_repo_id = uuid4()

    with patch("src.mcp.tools.indexing.get_session") as mock_session_ctx, \
         patch("src.mcp.tools.indexing.index_repository_service") as mock_service:

        # Configure mock async context manager
        mock_db = AsyncMock()
        mock_session_ctx.return_value.__aenter__.return_value = mock_db

        # Configure mock indexer service result
        mock_result = MagicMock()
        mock_result.repository_id = mock_repo_id
        mock_result.files_indexed = 50
        mock_result.chunks_created = 1000
        mock_result.duration_seconds = 5.2
        mock_result.status = "success"
        mock_result.errors = []
        mock_service.return_value = mock_result

        # Create temporary directory for testing
        test_repo = Path("/tmp/test-repo-multi-hyphen")
        test_repo.mkdir(exist_ok=True, parents=True)

        try:
            # Call tool with multi-hyphen project_id
            result = await index_repository_fn(
                repo_path=str(test_repo),
                project_id="my-project-123",
                force_reindex=False,
            )

            # Validate response structure
            assert result["status"] == "success"
            assert result["project_id"] == "my-project-123"
            assert result["schema_name"] == "project_my_project_123"

            # Verify get_session was called with correct project_id
            mock_session_ctx.assert_called_once_with(project_id="my-project-123")

        finally:
            # Cleanup
            if test_repo.exists():
                test_repo.rmdir()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_index_repository_project_id_max_length() -> None:
    """Test project_id at maximum allowed length (50 characters).

    Validates:
    - 50-character project_id is accepted
    - Schema name correctly generated
    - No truncation occurs

    Traces to: contracts/mcp-tools.yaml lines 28-37
    """
    # Create 50-character valid identifier (lowercase alphanumeric with hyphens)
    max_length_id = "a" * 20 + "-" + "b" * 20 + "-" + "c" * 8  # Total: 50 chars
    assert len(max_length_id) == 50

    # Mock dependencies
    mock_repo_id = uuid4()

    with patch("src.mcp.tools.indexing.get_session") as mock_session_ctx, \
         patch("src.mcp.tools.indexing.index_repository_service") as mock_service:

        # Configure mock async context manager
        mock_db = AsyncMock()
        mock_session_ctx.return_value.__aenter__.return_value = mock_db

        # Configure mock indexer service result
        mock_result = MagicMock()
        mock_result.repository_id = mock_repo_id
        mock_result.files_indexed = 10
        mock_result.chunks_created = 100
        mock_result.duration_seconds = 1.0
        mock_result.status = "success"
        mock_result.errors = []
        mock_service.return_value = mock_result

        # Create temporary directory for testing
        test_repo = Path("/tmp/test-repo-max-len")
        test_repo.mkdir(exist_ok=True, parents=True)

        try:
            # Call tool with max-length project_id
            result = await index_repository_fn(
                repo_path=str(test_repo),
                project_id=max_length_id,
                force_reindex=False,
            )

            # Validate response structure
            assert result["status"] == "success"
            assert result["project_id"] == max_length_id
            assert len(result["project_id"]) == 50

            # Schema name should have hyphens replaced with underscores
            expected_schema = f"project_{max_length_id.replace('-', '_')}"
            assert result["schema_name"] == expected_schema

        finally:
            # Cleanup
            if test_repo.exists():
                test_repo.rmdir()
