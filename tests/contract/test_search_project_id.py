"""T014: Contract tests for search_code with project_id parameter.

Tests validate that search_code correctly handles the optional project_id
parameter for multi-project workspace isolation.

Constitutional Compliance:
- Principle III: Protocol Compliance (MCP-compliant tool parameters)
- Principle VII: Test-Driven Development (contract validation)
- Principle VIII: Type Safety (mypy --strict compliance)

Functional Requirements:
- FR-002: Project workspace isolation via project_id parameter
- FR-003: Backward compatibility (null project_id uses default workspace)
- FR-012: workflow-mcp integration for active project detection
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.mcp.tools.search import search_code

# Extract underlying function from FastMCP FunctionTool wrapper
search_code_fn = search_code.fn


@pytest.mark.contract
@pytest.mark.asyncio
async def test_search_code_with_valid_project_id() -> None:
    """Test search_code accepts valid project_id parameter.

    Validates:
    - Valid project_id "frontend" is accepted
    - Returns results from specified project schema only
    - Returns project_id in response
    - Returns schema_name "project_frontend" in response

    Traces to: contracts/mcp-tools.yaml lines 175-274
    """
    # Mock dependencies
    mock_chunk_id = uuid4()
    mock_results = [
        MagicMock(
            chunk_id=mock_chunk_id,
            file_path="src/components/Auth.tsx",
            content="export const AuthProvider = () => { ... }",
            start_line=10,
            end_line=25,
            similarity_score=0.95,
            context_before="import React from 'react';",
            context_after="export default AuthProvider;",
        )
    ]

    with patch("src.mcp.tools.search.get_session") as mock_session_ctx, \
         patch("src.mcp.tools.search.search_code_service") as mock_service:

        # Configure mock async context manager
        mock_db = AsyncMock()
        mock_session_ctx.return_value.__aenter__.return_value = mock_db

        # Configure mock search service result
        mock_service.return_value = mock_results

        # Call tool with valid project_id
        result = await search_code_fn(
            query="authentication middleware",
            project_id="frontend",
            limit=10,
        )

        # Validate response structure
        assert "results" in result
        assert len(result["results"]) == 1
        assert result["project_id"] == "frontend"
        assert result["schema_name"] == "project_frontend"
        assert result["total_count"] == 1
        assert result["latency_ms"] >= 0

        # Validate result contents
        first_result = result["results"][0]
        assert first_result["chunk_id"] == str(mock_chunk_id)
        assert first_result["file_path"] == "src/components/Auth.tsx"
        assert first_result["similarity_score"] == 0.95

        # Verify get_session was called with project_id
        mock_session_ctx.assert_called_once_with(project_id="frontend")


@pytest.mark.contract
@pytest.mark.asyncio
async def test_search_code_with_null_project_id() -> None:
    """Test backward compatibility with null project_id.

    Validates:
    - Null project_id is accepted (backward compatibility)
    - Returns results from default workspace
    - Returns null project_id in response
    - Returns default schema_name "project_default"

    Traces to: contracts/mcp-tools.yaml lines 175-274
    """
    # Mock dependencies
    mock_chunk_id = uuid4()
    mock_results = [
        MagicMock(
            chunk_id=mock_chunk_id,
            file_path="src/utils/logger.py",
            content="def log_info(message: str): ...",
            start_line=5,
            end_line=10,
            similarity_score=0.88,
            context_before="import logging",
            context_after="",
        )
    ]

    with patch("src.mcp.tools.search.get_session") as mock_session_ctx, \
         patch("src.mcp.tools.search.search_code_service") as mock_service, \
         patch("src.mcp.tools.search.resolve_project_id") as mock_resolve:

        # Configure resolve_project_id to return None (no workflow-mcp fallback)
        mock_resolve.return_value = None

        # Configure mock async context manager
        mock_db = AsyncMock()
        mock_session_ctx.return_value.__aenter__.return_value = mock_db

        # Configure mock search service result
        mock_service.return_value = mock_results

        # Call tool with null project_id (backward compatibility)
        result = await search_code_fn(
            query="logging utility",
            project_id=None,
            limit=10,
        )

        # Validate response structure
        assert "results" in result
        assert len(result["results"]) == 1
        assert result["project_id"] is None
        assert result["schema_name"] == "project_default"
        assert result["total_count"] == 1

        # Verify get_session was called with None (default workspace)
        mock_session_ctx.assert_called_once_with(project_id=None)


@pytest.mark.contract
@pytest.mark.asyncio
async def test_search_code_with_project_id_no_results() -> None:
    """Test search_code with valid project_id but no matching results.

    Validates:
    - Valid project_id is accepted
    - Empty results array returned when no matches
    - total_count is 0
    - Response structure is correct

    Traces to: contracts/mcp-tools.yaml lines 175-274
    """
    # Mock dependencies (no results)
    mock_results: list = []

    with patch("src.mcp.tools.search.get_session") as mock_session_ctx, \
         patch("src.mcp.tools.search.search_code_service") as mock_service:

        # Configure mock async context manager
        mock_db = AsyncMock()
        mock_session_ctx.return_value.__aenter__.return_value = mock_db

        # Configure mock search service result (empty)
        mock_service.return_value = mock_results

        # Call tool with valid project_id
        result = await search_code_fn(
            query="nonexistent function",
            project_id="frontend",
            limit=10,
        )

        # Validate response structure
        assert "results" in result
        assert len(result["results"]) == 0
        assert result["project_id"] == "frontend"
        assert result["schema_name"] == "project_frontend"
        assert result["total_count"] == 0

        # Verify get_session was called with project_id
        mock_session_ctx.assert_called_once_with(project_id="frontend")


@pytest.mark.contract
@pytest.mark.asyncio
async def test_search_code_with_workflow_mcp_fallback() -> None:
    """Test search_code with workflow-mcp auto-detection.

    Validates:
    - When project_id is None, resolve_project_id is called
    - workflow-mcp returns active project UUID
    - Returned project_id matches workflow-mcp value
    - Schema name correctly generated from resolved project

    Traces to: contracts/mcp-tools.yaml lines 183-210
    """
    # Mock dependencies
    mock_chunk_id = uuid4()
    mock_results = [
        MagicMock(
            chunk_id=mock_chunk_id,
            file_path="api/users.py",
            content="@router.get('/users'): ...",
            start_line=15,
            end_line=20,
            similarity_score=0.92,
            context_before="from fastapi import APIRouter",
            context_after="return users",
        )
    ]

    with patch("src.mcp.tools.search.get_session") as mock_session_ctx, \
         patch("src.mcp.tools.search.search_code_service") as mock_service, \
         patch("src.mcp.tools.search.resolve_project_id") as mock_resolve:

        # Configure resolve_project_id to return active project from workflow-mcp
        active_project_id = "backend-api"
        mock_resolve.return_value = active_project_id

        # Configure mock async context manager
        mock_db = AsyncMock()
        mock_session_ctx.return_value.__aenter__.return_value = mock_db

        # Configure mock search service result
        mock_service.return_value = mock_results

        # Call tool with null project_id (triggers workflow-mcp detection)
        result = await search_code_fn(
            query="user API endpoint",
            project_id=None,
            limit=10,
        )

        # Validate response structure
        assert "results" in result
        assert len(result["results"]) == 1
        assert result["project_id"] == active_project_id
        assert result["schema_name"] == "project_backend_api"
        assert result["total_count"] == 1

        # Verify resolve_project_id was called with None
        mock_resolve.assert_called_once_with(None)

        # Verify get_session was called with resolved project_id
        mock_session_ctx.assert_called_once_with(project_id=active_project_id)


@pytest.mark.contract
@pytest.mark.asyncio
async def test_search_code_project_id_with_multiple_results() -> None:
    """Test search_code returns multiple results from project workspace.

    Validates:
    - Multiple results returned from same project
    - All results include project_id and schema_name
    - Results are properly formatted
    - total_count matches result array length

    Traces to: contracts/mcp-tools.yaml lines 228-248
    """
    # Mock dependencies (multiple results)
    mock_results = [
        MagicMock(
            chunk_id=uuid4(),
            file_path="src/auth/middleware.py",
            content="def authenticate(request): ...",
            start_line=10,
            end_line=20,
            similarity_score=0.95,
            context_before="import jwt",
            context_after="return user",
        ),
        MagicMock(
            chunk_id=uuid4(),
            file_path="src/auth/utils.py",
            content="def hash_password(password): ...",
            start_line=5,
            end_line=15,
            similarity_score=0.87,
            context_before="import bcrypt",
            context_after="return hashed",
        ),
        MagicMock(
            chunk_id=uuid4(),
            file_path="src/auth/tokens.py",
            content="def generate_token(user_id): ...",
            start_line=8,
            end_line=18,
            similarity_score=0.82,
            context_before="from datetime import datetime",
            context_after="return token",
        ),
    ]

    with patch("src.mcp.tools.search.get_session") as mock_session_ctx, \
         patch("src.mcp.tools.search.search_code_service") as mock_service:

        # Configure mock async context manager
        mock_db = AsyncMock()
        mock_session_ctx.return_value.__aenter__.return_value = mock_db

        # Configure mock search service result
        mock_service.return_value = mock_results

        # Call tool with valid project_id
        result = await search_code_fn(
            query="authentication",
            project_id="backend",
            limit=10,
        )

        # Validate response structure
        assert "results" in result
        assert len(result["results"]) == 3
        assert result["project_id"] == "backend"
        assert result["schema_name"] == "project_backend"
        assert result["total_count"] == 3

        # Validate all results are properly formatted
        for idx, res in enumerate(result["results"]):
            assert "chunk_id" in res
            assert "file_path" in res
            assert "content" in res
            assert "start_line" in res
            assert "end_line" in res
            assert "similarity_score" in res
            assert res["similarity_score"] == mock_results[idx].similarity_score

        # Verify get_session was called with project_id
        mock_session_ctx.assert_called_once_with(project_id="backend")
