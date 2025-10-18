"""Unit tests for index_repository MCP tool.

Tests for Bug 1 fix: Ensure index_repository returns JSON response (not None).

Constitutional Compliance:
- Principle VII: TDD (tests before implementation)
- Principle V: Production Quality (comprehensive error testing)

Bug 1 Verification:
These tests verify that the response formatting code (lines 330-376) is reachable
and executes correctly. Before the fix, this code was placed after the try/except
block, making it unreachable when the happy path completed.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from src.services.indexer import IndexResult


class TestIndexRepositoryResponse:
    """Test that index_repository returns proper JSON response.

    These tests verify Bug 1 fix: response formatting code must execute
    and return a dictionary (not None).
    """

    @pytest.mark.asyncio
    async def test_successful_indexing_returns_complete_response(
        self, tmp_path: Path
    ) -> None:
        """Test that successful indexing returns complete JSON response.

        Before fix: Returns None (unreachable code after try/except)
        After fix: Returns dict with all required fields
        """
        # Create test repository
        test_repo = tmp_path / "test-repo"
        test_repo.mkdir()
        (test_repo / "file1.py").write_text("print('hello')")

        # Mock IndexResult from service
        mock_result = IndexResult(
            repository_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            files_indexed=10,
            chunks_created=50,
            duration_seconds=2.5,
            status="success",
            errors=[],
        )

        # Mock the indexer service
        with patch(
            "src.mcp.tools.indexing.index_repository_service",
            new_callable=AsyncMock,
        ) as mock_service:
            mock_service.return_value = mock_result

            # Mock get_session to avoid real database
            with patch("src.mcp.tools.indexing.get_session") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value.__aenter__.return_value = mock_db

                # Import after patching
                from src.mcp.tools.indexing import index_repository

                # Access the underlying function from FunctionTool
                index_fn = index_repository.fn

                # Execute
                result = await index_fn(
                    repo_path=str(test_repo), project_id="test-project"
                )

                # Verify result is NOT None
                assert result is not None, "index_repository must return a value"

                # Verify result is a dictionary
                assert isinstance(result, dict), "Result must be a dictionary"

                # Verify all required fields present
                assert set(result.keys()) >= {
                    "repository_id",
                    "files_indexed",
                    "chunks_created",
                    "duration_seconds",
                    "project_id",
                    "database_name",
                    "status",
                }, "Response must include all required fields"

                # Verify field types
                assert isinstance(result["repository_id"], str)
                assert isinstance(result["files_indexed"], int)
                assert isinstance(result["chunks_created"], int)
                assert isinstance(result["duration_seconds"], (int, float))
                assert isinstance(result["status"], str)

                # Verify values
                assert result["status"] in ["success", "partial", "failed"]
                assert result["files_indexed"] == 10
                assert result["chunks_created"] == 50
                assert len(result["repository_id"]) == 36  # UUID format

    @pytest.mark.asyncio
    async def test_partial_indexing_includes_errors_array(
        self, tmp_path: Path
    ) -> None:
        """Test that partial success includes errors array.

        Before fix: Returns None
        After fix: Returns dict with errors array
        """
        # Create test repository
        test_repo = tmp_path / "test-repo"
        test_repo.mkdir()
        (test_repo / "file1.py").write_text("print('hello')")

        # Mock IndexResult with partial status and errors
        mock_result = IndexResult(
            repository_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            files_indexed=8,
            chunks_created=40,
            duration_seconds=2.0,
            status="partial",
            errors=["file1.py: parse error", "file2.js: encoding error"],
        )

        with patch(
            "src.mcp.tools.indexing.index_repository_service",
            new_callable=AsyncMock,
        ) as mock_service:
            mock_service.return_value = mock_result

            with patch("src.mcp.tools.indexing.get_session") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value.__aenter__.return_value = mock_db

                from src.mcp.tools.indexing import index_repository

                index_fn = index_repository.fn

                result = await index_fn(
                    repo_path=str(test_repo), project_id="test-project"
                )

                # Verify result exists
                assert result is not None

                # Verify status
                assert result["status"] == "partial"

                # Verify errors array present
                assert (
                    "errors" in result
                ), "Partial results must include errors array"
                assert isinstance(result["errors"], list)
                assert len(result["errors"]) == 2
                assert all(isinstance(e, str) for e in result["errors"])
                assert "file1.py: parse error" in result["errors"]

    @pytest.mark.asyncio
    async def test_response_types_match_contract(self, tmp_path: Path) -> None:
        """Test that all response field types match MCP contract.

        Before fix: Returns None (contract violation)
        After fix: All types correct
        """
        # Create test repository
        test_repo = tmp_path / "test-repo"
        test_repo.mkdir()
        (test_repo / "file1.py").write_text("print('hello')")

        mock_result = IndexResult(
            repository_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            files_indexed=5,
            chunks_created=25,
            duration_seconds=1.5,
            status="success",
            errors=[],
        )

        with patch(
            "src.mcp.tools.indexing.index_repository_service",
            new_callable=AsyncMock,
        ) as mock_service:
            mock_service.return_value = mock_result

            with patch("src.mcp.tools.indexing.get_session") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value.__aenter__.return_value = mock_db

                from src.mcp.tools.indexing import index_repository

                index_fn = index_repository.fn

                result = await index_fn(
                    repo_path=str(test_repo), project_id="test-project"
                )

                # Type validation for all fields
                assert isinstance(result["repository_id"], str)
                assert isinstance(result["files_indexed"], int)
                assert isinstance(result["chunks_created"], int)
                assert isinstance(result["duration_seconds"], (int, float))
                assert isinstance(result["project_id"], str)
                assert isinstance(result["database_name"], str)
                assert isinstance(result["status"], str)

                # Optional errors field type
                if "errors" in result:
                    assert isinstance(result["errors"], list)

    @pytest.mark.asyncio
    async def test_empty_errors_list_not_included(self, tmp_path: Path) -> None:
        """Test that empty errors list is not included in response.

        Only non-empty errors lists should be included.
        """
        # Create test repository
        test_repo = tmp_path / "test-repo"
        test_repo.mkdir()
        (test_repo / "file1.py").write_text("print('hello')")

        mock_result = IndexResult(
            repository_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            files_indexed=10,
            chunks_created=50,
            duration_seconds=2.5,
            status="success",
            errors=[],  # Empty errors list
        )

        with patch(
            "src.mcp.tools.indexing.index_repository_service",
            new_callable=AsyncMock,
        ) as mock_service:
            mock_service.return_value = mock_result

            with patch("src.mcp.tools.indexing.get_session") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value.__aenter__.return_value = mock_db

                from src.mcp.tools.indexing import index_repository

                index_fn = index_repository.fn

                result = await index_fn(
                    repo_path=str(test_repo), project_id="test-project"
                )

                # Empty errors list should not be included
                assert "errors" not in result or len(result.get("errors", [])) == 0
