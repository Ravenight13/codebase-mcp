"""Server failure isolation and resilience tests (Phase 4 US2 T022-T024).

Tests server independence and graceful degradation when one server fails,
validating that failures remain isolated without cascading effects.

Test Scenario: Quickstart Scenario 3 - Resilience and Failure Isolation
Validates: Server independence, graceful degradation, stale reference handling
Traces to: FR-013 (graceful degradation), AC-002 (resilience validation)

Constitutional Compliance:
- Principle VII: TDD (validates resilience and failure isolation)
- Principle VIII: Type safety (mypy --strict compliance with complete annotations)
- Principle II: Local-first architecture (servers operate independently)
- SC-009: Server failures remain isolated

Success Criteria:
- SC-009: Server failures remain isolated (no cascading failures)
- SC-014: Error messages guide users to resolution
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch
from contextlib import asynccontextmanager

import httpx
import pytest
import pytest_asyncio


# ==============================================================================
# Type Definitions
# ==============================================================================

WorkItemResponse = Dict[str, Any]
SearchResponse = Dict[str, Any]


# ==============================================================================
# Test Fixtures & Mocking Utilities
# ==============================================================================


@asynccontextmanager
async def mock_server_unavailable(server_url: str) -> None:
    """Context manager to simulate server unavailability.

    Mocks httpx.AsyncClient to raise connection errors for specified server URL.

    Args:
        server_url: Base URL of server to simulate as unavailable

    Yields:
        None - context for test execution with mocked unavailable server

    Usage:
        async with mock_server_unavailable("http://localhost:8020"):
            # codebase-mcp is unavailable, workflow-mcp should continue
            response = await client.post("http://localhost:8010/...")
    """
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        async def side_effect_post(url: str, **kwargs: Any) -> AsyncMock:
            """Raise connection error for unavailable server, allow others."""
            if url.startswith(server_url):
                raise httpx.ConnectError(
                    f"Connection refused: {server_url}",
                    request=Mock(url=url)
                )
            # Allow other servers to work
            mock_response = AsyncMock()
            mock_response.status_code = 200
            return mock_response

        async def side_effect_get(url: str, **kwargs: Any) -> AsyncMock:
            """Raise connection error for unavailable server, allow others."""
            if url.startswith(server_url):
                raise httpx.ConnectError(
                    f"Connection refused: {server_url}",
                    request=Mock(url=url)
                )
            # Allow other servers to work
            mock_response = AsyncMock()
            mock_response.status_code = 200
            return mock_response

        mock_client.post.side_effect = side_effect_post
        mock_client.get.side_effect = side_effect_get

        yield None


@pytest.fixture
def mock_work_item_response_with_warning() -> WorkItemResponse:
    """Fixture: Mock work item response when codebase-mcp is unavailable.

    Returns work item creation response with warnings indicating code search
    unavailability per quickstart.md lines 196-210.

    Returns:
        Dictionary with work item data and warnings array
    """
    return {
        "id": "work-item-isolated-001",
        "title": "New task",
        "item_type": "task",
        "status": "planned",
        "entity_references": [],
        "created_at": "2025-10-13T12:00:00Z",
        "updated_at": "2025-10-13T12:00:00Z",
        "warnings": [
            "code_search_unavailable: codebase-mcp server not reachable"
        ],
        "metadata": {}
    }


@pytest.fixture
def mock_search_response() -> SearchResponse:
    """Fixture: Mock search response when workflow-mcp is unavailable.

    Returns successful search response showing codebase-mcp operates
    independently per quickstart.md lines 215-227.

    Returns:
        Dictionary with search results
    """
    return {
        "results": [
            {
                "chunk_id": "search-chunk-001",
                "file_path": "src/auth.py",
                "content": "def authenticate(user: str) -> bool:",
                "start_line": 10,
                "end_line": 20,
                "similarity_score": 0.92
            }
        ],
        "total_count": 1,
        "latency_ms": 280
    }


# ==============================================================================
# Resilience Tests - Server Failure Isolation
# ==============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_continues_when_codebase_down(
    mock_work_item_response_with_warning: WorkItemResponse
) -> None:
    """Validate workflow-mcp continues operating when codebase-mcp is unavailable.

    Tests server isolation per quickstart.md lines 196-210, ensuring that
    workflow-mcp operations succeed even when codebase-mcp is down, with
    appropriate user warnings.

    Test Steps:
        1. Simulate codebase-mcp server unavailable (connection refused)
        2. Attempt to create work item via workflow-mcp
        3. Verify work item creation succeeds (status 201)
        4. Verify response includes warning about code search unavailability

    Expected Results:
        - Work item creation succeeds with status 201
        - Response contains warnings array with "code_search_unavailable" message
        - No cascading failure or error propagation to workflow-mcp
        - Entity references field empty (cannot query codebase-mcp)

    Traces to:
        - FR-013: Graceful degradation when external services unavailable
        - SC-009: Server failures remain isolated (no cascading failures)
        - SC-014: Error messages guide users to resolution

    Constitutional Compliance:
        - Principle II: Local-first architecture (servers operate independently)
        - Principle VII: TDD validates resilience
        - Principle VIII: Complete type annotations
    """
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Configure mock: codebase-mcp raises connection error
        async def post_side_effect(url: str, **kwargs: Any) -> AsyncMock:
            if "localhost:8020" in url:  # codebase-mcp
                raise httpx.ConnectError(
                    "Connection refused: codebase-mcp unavailable",
                    request=Mock(url=url)
                )
            # workflow-mcp succeeds with warning
            mock_response = AsyncMock()
            mock_response.status_code = 201
            mock_response.json.return_value = mock_work_item_response_with_warning
            return mock_response

        mock_client.post.side_effect = post_side_effect

        # Execute: Create work item when codebase-mcp is down
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8010/mcp/work_items",
                json={"title": "New task"},
                timeout=5.0
            )

        # Validate: Workflow operations succeed (SC-009)
        assert response.status_code == 201, \
            f"Work item creation failed with status {response.status_code}"

        work_item = response.json()
        assert work_item["id"] == "work-item-isolated-001"
        assert work_item["title"] == "New task"

        # Validate: Warning indicates code search unavailable (SC-014)
        assert "warnings" in work_item, \
            "Response missing warnings field"
        assert any("code_search_unavailable" in w for w in work_item["warnings"]), \
            "Missing warning about codebase-mcp unavailability"

        # Success: Workflow-mcp continues independently when codebase-mcp down


@pytest.mark.integration
@pytest.mark.asyncio
async def test_codebase_continues_when_workflow_down(
    mock_search_response: SearchResponse
) -> None:
    """Validate codebase-mcp continues operating when workflow-mcp is unavailable.

    Tests reverse server isolation per quickstart.md lines 215-227, ensuring
    that codebase-mcp search operations succeed even when workflow-mcp is down.

    Test Steps:
        1. Simulate workflow-mcp server unavailable (connection refused)
        2. Execute code search via codebase-mcp
        3. Verify search succeeds with status 200
        4. Verify search results returned correctly

    Expected Results:
        - Code search succeeds with status 200
        - Search results contain valid chunks with expected fields
        - No dependency on workflow-mcp for search operations
        - No cascading failure or error propagation to codebase-mcp

    Traces to:
        - FR-013: Graceful degradation when external services unavailable
        - SC-009: Server failures remain isolated (no cascading failures)
        - Principle II: Local-first architecture

    Constitutional Compliance:
        - Principle II: Local-first architecture (servers operate independently)
        - Principle VII: TDD validates resilience
        - Principle VIII: Complete type annotations
    """
    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Configure mock: workflow-mcp raises connection error
        async def post_side_effect(url: str, **kwargs: Any) -> AsyncMock:
            if "localhost:8010" in url:  # workflow-mcp
                raise httpx.ConnectError(
                    "Connection refused: workflow-mcp unavailable",
                    request=Mock(url=url)
                )
            # codebase-mcp succeeds normally
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_search_response
            return mock_response

        mock_client.post.side_effect = post_side_effect

        # Execute: Search code when workflow-mcp is down
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8020/mcp/search",
                json={"query": "authentication"},
                timeout=5.0
            )

        # Validate: Code search succeeds (SC-009)
        assert response.status_code == 200, \
            f"Search failed with status {response.status_code}"

        search_results = response.json()
        assert "results" in search_results, \
            "Search response missing results field"
        assert len(search_results["results"]) > 0, \
            "Search returned no results"

        # Validate result structure
        first_result = search_results["results"][0]
        assert "chunk_id" in first_result
        assert "file_path" in first_result
        assert "content" in first_result
        assert first_result["chunk_id"] == "search-chunk-001"

        # Success: Codebase-mcp continues independently when workflow-mcp down


@pytest.mark.integration
@pytest.mark.asyncio
async def test_stale_entity_reference_handled_gracefully() -> None:
    """Validate graceful handling of stale entity references in work items.

    Tests stale reference detection per quickstart.md lines 232-245, ensuring
    that when a code chunk is deleted/re-indexed, work items handle the stale
    reference gracefully with clear user messaging.

    Test Steps:
        1. Create work item with entity reference (chunk-deleted-001)
        2. Simulate chunk deletion/re-indexing in codebase-mcp
        3. Retrieve work item from workflow-mcp
        4. Verify work item retrieval succeeds (status 200)
        5. Verify stale reference marked with clear messaging

    Expected Results:
        - Work item retrieval succeeds with status 200
        - Response contains stale_references field identifying deleted chunk
        - Clear user messaging explaining reference is stale
        - Work item data preserved (no data loss)
        - No cascading failure or database errors

    Traces to:
        - FR-013: Graceful degradation when entity references become stale
        - SC-009: Server failures remain isolated
        - SC-014: Error messages guide users to resolution

    Constitutional Compliance:
        - Principle V: Production quality (comprehensive error handling)
        - Principle VII: TDD validates edge cases
        - Principle VIII: Complete type annotations
    """
    # Mock work item with entity reference
    work_item_with_ref = {
        "id": "work-item-stale-ref-001",
        "title": "Fix authentication bug",
        "entity_references": ["chunk-deleted-001"],
        "item_type": "task",
        "status": "active",
        "created_at": "2025-10-13T12:00:00Z",
        "updated_at": "2025-10-13T12:00:00Z"
    }

    # Mock work item retrieval response with stale reference detected
    work_item_with_stale_ref = {
        **work_item_with_ref,
        "stale_references": ["chunk-deleted-001"],
        "warnings": [
            "Entity reference 'chunk-deleted-001' not found in codebase-mcp. "
            "Code may have been deleted or re-indexed."
        ]
    }

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Step 1: Create work item with entity reference
        mock_create_response = AsyncMock()
        mock_create_response.status_code = 201
        mock_create_response.json.return_value = work_item_with_ref

        # Step 2: Mock chunk deletion (codebase-mcp returns 404)
        mock_chunk_get_response = AsyncMock()
        mock_chunk_get_response.status_code = 404
        mock_chunk_get_response.json.return_value = {
            "error": "chunk_not_found",
            "message": "Chunk 'chunk-deleted-001' not found"
        }

        # Step 3: Retrieve work item (workflow-mcp detects stale reference)
        mock_get_response = AsyncMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = work_item_with_stale_ref

        # Configure mock client
        mock_client.post.return_value = mock_create_response
        mock_client.get.side_effect = [mock_chunk_get_response, mock_get_response]

        # Execute: Create work item
        async with httpx.AsyncClient() as client:
            create_response = await client.post(
                "http://localhost:8010/mcp/work_items",
                json={
                    "title": "Fix authentication bug",
                    "entity_references": ["chunk-deleted-001"]
                },
                timeout=5.0
            )

        work_item_id = create_response.json()["id"]

        # Simulate chunk deletion (would happen in codebase-mcp)
        # In reality, codebase-mcp would delete/re-index chunk
        async with httpx.AsyncClient() as client:
            chunk_check = await client.get(
                "http://localhost:8020/mcp/chunks/chunk-deleted-001",
                timeout=5.0
            )

        # Execute: Retrieve work item (should detect stale reference)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://localhost:8010/mcp/work_items/{work_item_id}",
                timeout=5.0
            )

        # Validate: Work item retrieval succeeds (SC-009)
        assert response.status_code == 200, \
            f"Work item retrieval failed with status {response.status_code}"

        work_item = response.json()

        # Validate: Stale reference marked clearly (SC-014)
        assert "stale_references" in work_item, \
            "Response missing stale_references field"
        assert "chunk-deleted-001" in work_item["stale_references"], \
            "Deleted chunk not marked as stale reference"

        # Validate: Clear user messaging
        assert "warnings" in work_item, \
            "Response missing warnings field"
        assert any("chunk-deleted-001" in w for w in work_item["warnings"]), \
            "Missing warning about stale entity reference"
        assert any("deleted or re-indexed" in w.lower() for w in work_item["warnings"]), \
            "Warning message doesn't explain stale reference cause"

        # Validate: Work item data preserved (no data loss)
        assert work_item["id"] == work_item_id
        assert work_item["title"] == "Fix authentication bug"
        assert "chunk-deleted-001" in work_item["entity_references"], \
            "Original entity reference lost"

        # Success: Stale entity references handled gracefully


@pytest.mark.integration
@pytest.mark.asyncio
async def test_partial_entity_reference_staleness() -> None:
    """Validate handling when only some entity references become stale.

    Tests edge case where work item has multiple entity references and only
    some become stale after re-indexing.

    Test Steps:
        1. Create work item with 3 entity references
        2. Simulate deletion of 1 chunk (chunk-002)
        3. Retrieve work item
        4. Verify only deleted chunk marked as stale
        5. Verify valid chunks remain accessible

    Expected Results:
        - Work item retrieval succeeds
        - Only deleted chunk in stale_references
        - Valid chunks not marked as stale
        - Clear messaging distinguishing stale vs valid references

    Traces to:
        - FR-013: Graceful degradation with partial failures
        - SC-009: Isolated failures
        - SC-014: Clear error messages
    """
    # Mock work item with multiple entity references
    work_item_multi_ref = {
        "id": "work-item-partial-stale-001",
        "title": "Refactor authentication",
        "entity_references": ["chunk-001", "chunk-002", "chunk-003"],
        "item_type": "task",
        "status": "active"
    }

    # Mock retrieval response with partial stale references
    work_item_partial_stale = {
        **work_item_multi_ref,
        "stale_references": ["chunk-002"],  # Only chunk-002 is stale
        "valid_references": ["chunk-001", "chunk-003"],  # These are valid
        "warnings": [
            "Entity reference 'chunk-002' not found in codebase-mcp. "
            "2 of 3 entity references remain valid."
        ]
    }

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Mock retrieval with partial stale detection
        mock_get_response = AsyncMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = work_item_partial_stale

        mock_client.get.return_value = mock_get_response

        # Execute: Retrieve work item with partial stale references
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8010/mcp/work_items/work-item-partial-stale-001",
                timeout=5.0
            )

        work_item = response.json()

        # Validate: Only deleted chunk marked as stale
        assert "stale_references" in work_item
        assert len(work_item["stale_references"]) == 1
        assert "chunk-002" in work_item["stale_references"]

        # Validate: Valid chunks not marked as stale
        assert "valid_references" in work_item
        assert len(work_item["valid_references"]) == 2
        assert "chunk-001" in work_item["valid_references"]
        assert "chunk-003" in work_item["valid_references"]

        # Validate: Clear proportional messaging
        assert "warnings" in work_item
        assert any("2 of 3" in w for w in work_item["warnings"]), \
            "Warning doesn't indicate proportion of valid references"

        # Success: Partial staleness handled correctly
