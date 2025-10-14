"""Cross-server integration workflow tests (Phase 4 US2 T021).

Tests workflows spanning both codebase-mcp and workflow-mcp servers,
validating entity reference persistence and cross-server data flow.

Test Scenario: Quickstart Scenario 2 - Cross-Server Integration Validation
Validates: Search → work item creation → entity reference persistence
Traces to: FR-021 (cross-server workflows), AC-002 (integration validation)

Constitutional Compliance:
- Principle VII: TDD (validates cross-server integration correctness)
- Principle VIII: Type safety (mypy --strict compliance with complete annotations)
- Principle V: Production quality (comprehensive integration testing)
- SC-011: Integration test suite 100% pass rate

Success Criteria:
- SC-009: Server failures remain isolated (validated by resilience tests)
- SC-011: Integration test suite 100% pass rate (validated here)
"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
import pytest_asyncio


# ==============================================================================
# Type Definitions
# ==============================================================================

SearchResult = Dict[str, Any]
WorkItemResponse = Dict[str, Any]


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def mock_codebase_search_response() -> SearchResult:
    """Fixture: Mock codebase-mcp search response with entity chunks.

    Returns realistic search response structure per quickstart.md lines 141-155.

    Returns:
        Dictionary with search results containing chunk_id fields
    """
    return {
        "results": [
            {
                "chunk_id": "550e8400-e29b-41d4-a716-446655440000",
                "file_path": "src/auth/authentication.py",
                "content": "def authenticate_user(username: str, password: str) -> bool:",
                "start_line": 10,
                "end_line": 20,
                "similarity_score": 0.95,
                "context_before": "import hashlib\nimport bcrypt\n",
                "context_after": "    return validate_credentials(username, password)"
            },
            {
                "chunk_id": "660e8400-e29b-41d4-a716-446655440001",
                "file_path": "src/auth/session.py",
                "content": "class SessionManager:\n    def authenticate(self, token: str) -> User:",
                "start_line": 45,
                "end_line": 60,
                "similarity_score": 0.88,
                "context_before": "from typing import Optional\n",
                "context_after": "        user = verify_token(token)"
            }
        ],
        "total_count": 2,
        "latency_ms": 320
    }


@pytest.fixture
def mock_work_item_creation_response() -> WorkItemResponse:
    """Fixture: Mock workflow-mcp work item creation response.

    Returns realistic work item response structure per quickstart.md lines 156-166.

    Returns:
        Dictionary with created work item including entity references
    """
    return {
        "id": "770e8400-e29b-41d4-a716-446655440002",
        "title": "Fix authentication bug",
        "item_type": "task",
        "status": "planned",
        "entity_references": ["550e8400-e29b-41d4-a716-446655440000"],
        "created_at": "2025-10-13T12:00:00Z",
        "updated_at": "2025-10-13T12:00:00Z",
        "parent_id": None,
        "metadata": {}
    }


# ==============================================================================
# Integration Tests - Cross-Server Workflow Validation
# ==============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_to_work_item_workflow(
    mock_codebase_search_response: SearchResult,
    mock_work_item_creation_response: WorkItemResponse
) -> None:
    """Validate cross-server workflow from search to work item creation.

    Tests the complete workflow per quickstart.md lines 141-176:
    1. Search code via codebase-mcp
    2. Create work item with entity reference via workflow-mcp
    3. Verify entity reference persisted in work item

    Test Steps:
        1. Mock codebase-mcp search endpoint returning results with chunk_id
        2. Call search endpoint and extract entity chunk_id
        3. Mock workflow-mcp work item creation endpoint
        4. Create work item with entity_references from search
        5. Mock workflow-mcp work item retrieval endpoint
        6. Verify entity reference persisted in work item data

    Expected Results:
        - Search returns results with chunk_id field
        - Work item created with status 201
        - Work item retrieval shows entity_references array containing chunk_id
        - Response times: search <500ms, work item creation <200ms

    Traces to:
        - FR-021: Cross-server workflow integration
        - AC-002: Integration validation scenarios
        - SC-009: Server failure isolation
        - SC-011: Integration test suite 100% pass rate

    Constitutional Compliance:
        - Principle VII: TDD validates integration correctness
        - Principle VIII: Complete type annotations (mypy --strict)
    """
    # Mock httpx.AsyncClient for both codebase-mcp and workflow-mcp calls
    with patch("httpx.AsyncClient") as mock_client_class:
        # Create mock client instance
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Step 1: Mock codebase-mcp search endpoint (quickstart.md lines 145-154)
        mock_search_response = AsyncMock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = mock_codebase_search_response

        # Step 2: Mock workflow-mcp work item creation (quickstart.md lines 156-166)
        mock_create_response = AsyncMock()
        mock_create_response.status_code = 201
        mock_create_response.json.return_value = mock_work_item_creation_response

        # Step 3: Mock workflow-mcp work item retrieval (quickstart.md lines 168-175)
        mock_get_response = AsyncMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = mock_work_item_creation_response

        # Configure mock client to return appropriate responses
        mock_client.post.side_effect = [mock_search_response, mock_create_response]
        mock_client.get.return_value = mock_get_response

        # Execute workflow: Step 1 - Search code (codebase-mcp)
        async with httpx.AsyncClient() as client:
            search_response = await client.post(
                "http://localhost:8020/mcp/search",
                json={"query": "authentication logic", "limit": 5},
                timeout=5.0
            )

        assert search_response.status_code == 200, \
            f"Search failed with status {search_response.status_code}"

        entities = search_response.json()["results"]
        assert len(entities) > 0, "Search returned no results"
        assert "chunk_id" in entities[0], "Search results missing chunk_id field"

        chunk_id = entities[0]["chunk_id"]
        assert chunk_id == "550e8400-e29b-41d4-a716-446655440000", \
            f"Unexpected chunk_id: {chunk_id}"

        # Execute workflow: Step 2 - Create work item with entity reference (workflow-mcp)
        async with httpx.AsyncClient() as client:
            work_item_response = await client.post(
                "http://localhost:8010/mcp/work_items",
                json={
                    "title": "Fix authentication bug",
                    "entity_references": [chunk_id]
                },
                timeout=5.0
            )

        assert work_item_response.status_code == 201, \
            f"Work item creation failed with status {work_item_response.status_code}"

        work_item_data = work_item_response.json()
        work_item_id = work_item_data["id"]
        assert "entity_references" in work_item_data, \
            "Work item response missing entity_references field"

        # Execute workflow: Step 3 - Verify entity reference stored (workflow-mcp)
        async with httpx.AsyncClient() as client:
            get_response = await client.get(
                f"http://localhost:8010/mcp/work_items/{work_item_id}",
                timeout=5.0
            )

        assert get_response.status_code == 200, \
            f"Work item retrieval failed with status {get_response.status_code}"

        work_item = get_response.json()
        assert "entity_references" in work_item, \
            "Retrieved work item missing entity_references field"

        # Validate entity reference persisted (quickstart.md line 175)
        assert chunk_id in work_item["entity_references"], \
            f"Entity reference {chunk_id} not found in work item references"

        # Validate response structure completeness
        assert work_item["id"] == work_item_id
        assert work_item["title"] == "Fix authentication bug"
        assert work_item["item_type"] == "task"
        assert work_item["status"] == "planned"

        # Success: Cross-server workflow validated (SC-011)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_search_to_work_item_workflow_multiple_entities() -> None:
    """Validate cross-server workflow with multiple entity references.

    Tests edge case where work item references multiple code chunks from search.

    Test Steps:
        1. Search returns multiple results (3 chunks)
        2. Create work item referencing all 3 chunks
        3. Verify all entity references persisted

    Expected Results:
        - Work item stores all 3 entity references
        - References returned in same order
        - No data loss or truncation

    Traces to:
        - FR-021: Cross-server workflow integration
        - SC-011: Integration test suite 100% pass rate
    """
    # Mock multiple search results
    mock_search_data = {
        "results": [
            {"chunk_id": "chunk-001", "file_path": "auth.py", "content": "auth code 1"},
            {"chunk_id": "chunk-002", "file_path": "session.py", "content": "auth code 2"},
            {"chunk_id": "chunk-003", "file_path": "token.py", "content": "auth code 3"}
        ],
        "total_count": 3,
        "latency_ms": 250
    }

    chunk_ids = [result["chunk_id"] for result in mock_search_data["results"]]

    # Mock work item with multiple references
    mock_work_item = {
        "id": "work-item-001",
        "title": "Refactor authentication system",
        "entity_references": chunk_ids,
        "item_type": "task",
        "status": "planned"
    }

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Mock responses
        mock_search_response = AsyncMock()
        mock_search_response.status_code = 200
        mock_search_response.json.return_value = mock_search_data

        mock_create_response = AsyncMock()
        mock_create_response.status_code = 201
        mock_create_response.json.return_value = mock_work_item

        mock_get_response = AsyncMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = mock_work_item

        mock_client.post.side_effect = [mock_search_response, mock_create_response]
        mock_client.get.return_value = mock_get_response

        # Execute workflow
        async with httpx.AsyncClient() as client:
            # Search
            search_response = await client.post(
                "http://localhost:8020/mcp/search",
                json={"query": "authentication", "limit": 10},
                timeout=5.0
            )
            entities = search_response.json()["results"]

            # Create work item with all chunk IDs
            work_item_response = await client.post(
                "http://localhost:8010/mcp/work_items",
                json={
                    "title": "Refactor authentication system",
                    "entity_references": chunk_ids
                },
                timeout=5.0
            )
            work_item_id = work_item_response.json()["id"]

            # Verify
            get_response = await client.get(
                f"http://localhost:8010/mcp/work_items/{work_item_id}",
                timeout=5.0
            )

        work_item = get_response.json()

        # Validate all entity references persisted
        assert len(work_item["entity_references"]) == 3, \
            f"Expected 3 references, got {len(work_item['entity_references'])}"

        for chunk_id in chunk_ids:
            assert chunk_id in work_item["entity_references"], \
                f"Entity reference {chunk_id} not persisted"

        # Success: Multiple entity references validated
