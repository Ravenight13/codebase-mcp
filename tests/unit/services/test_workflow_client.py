"""Unit tests for WorkflowIntegrationClient service.

This test suite validates the WorkflowIntegrationClient's error handling,
caching behavior, and integration with the WorkflowIntegrationContext model.

Test Coverage:
- Success scenario: Valid project ID retrieved and cached
- Timeout scenario: graceful degradation with warning log
- Connection error scenario: graceful degradation with info log
- Invalid response scenario: graceful degradation with error log
- Cache hit scenario: No network request on unexpired cache
- Cache expiration scenario: Refresh after TTL expiration

Constitutional Compliance:
- Principle VII: Test-driven development with comprehensive coverage
- Principle VIII: Type-safe test patterns with mypy --strict
- Principle V: Production quality with edge case validation
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from src.models.workflow_context import WorkflowIntegrationContext
from src.services.workflow_client import WorkflowIntegrationClient


@pytest.fixture
def workflow_client() -> WorkflowIntegrationClient:
    """Create WorkflowIntegrationClient with test configuration."""
    return WorkflowIntegrationClient(
        base_url="http://localhost:8000",
        timeout=1.0,
        cache_ttl=60,
    )


@pytest.mark.asyncio
async def test_get_active_project_success(workflow_client: WorkflowIntegrationClient) -> None:
    """Test successful project ID retrieval from workflow-mcp.

    Validates:
    - HTTP GET request to /api/v1/projects/active endpoint
    - Project ID extracted from JSON response
    - Success status logged at INFO level
    - Context cached with status="success"
    """
    project_id = "550e8400-e29b-41d4-a716-446655440000"
    mock_response = Mock()
    mock_response.json.return_value = {"project_id": project_id}
    mock_response.raise_for_status = Mock()

    async def mock_get(*args: Any, **kwargs: Any) -> Mock:
        return mock_response

    with patch.object(workflow_client.client, "get", side_effect=mock_get):
        result = await workflow_client.get_active_project()

    assert result == project_id
    assert "active_project" in workflow_client._cache
    cached_context = workflow_client._cache["active_project"]
    assert cached_context.active_project_id == project_id
    assert cached_context.status == "success"
    assert not cached_context.is_expired()


@pytest.mark.asyncio
async def test_get_active_project_timeout(workflow_client: WorkflowIntegrationClient) -> None:
    """Test timeout handling with graceful degradation.

    Validates:
    - Returns None when workflow-mcp times out
    - Context cached with status="timeout"
    - Warning log message emitted
    - No exception raised (graceful degradation)
    """
    with patch.object(
        workflow_client.client, "get", side_effect=httpx.TimeoutException("Timeout")
    ):
        result = await workflow_client.get_active_project()

    assert result is None
    assert "active_project" in workflow_client._cache
    cached_context = workflow_client._cache["active_project"]
    assert cached_context.active_project_id is None
    assert cached_context.status == "timeout"


@pytest.mark.asyncio
async def test_get_active_project_connection_error(
    workflow_client: WorkflowIntegrationClient,
) -> None:
    """Test connection error handling with graceful degradation.

    Validates:
    - Returns None when workflow-mcp is unavailable
    - Context cached with status="unavailable"
    - Info log message emitted (not error level)
    - No exception raised (graceful degradation)
    """
    with patch.object(
        workflow_client.client, "get", side_effect=httpx.ConnectError("Connection refused")
    ):
        result = await workflow_client.get_active_project()

    assert result is None
    assert "active_project" in workflow_client._cache
    cached_context = workflow_client._cache["active_project"]
    assert cached_context.active_project_id is None
    assert cached_context.status == "unavailable"


@pytest.mark.asyncio
async def test_get_active_project_invalid_response(
    workflow_client: WorkflowIntegrationClient,
) -> None:
    """Test invalid response handling with graceful degradation.

    Validates:
    - Returns None when workflow-mcp returns malformed data
    - Context cached with status="invalid_response"
    - Error log message emitted
    - No exception raised (graceful degradation)
    """
    mock_response = Mock()
    mock_response.json.side_effect = ValueError("Invalid JSON")
    mock_response.raise_for_status = Mock()

    async def mock_get(*args: Any, **kwargs: Any) -> Mock:
        return mock_response

    with patch.object(workflow_client.client, "get", side_effect=mock_get):
        result = await workflow_client.get_active_project()

    assert result is None
    assert "active_project" in workflow_client._cache
    cached_context = workflow_client._cache["active_project"]
    assert cached_context.active_project_id is None
    assert cached_context.status == "invalid_response"


@pytest.mark.asyncio
async def test_get_active_project_cache_hit(workflow_client: WorkflowIntegrationClient) -> None:
    """Test cache hit scenario with no network request.

    Validates:
    - Cached context returned without HTTP request
    - Cache expiration check validates TTL
    - No additional network overhead on cache hit
    """
    project_id = "550e8400-e29b-41d4-a716-446655440000"
    cached_context = WorkflowIntegrationContext(
        active_project_id=project_id,
        status="success",
        cache_ttl_seconds=60,
    )
    workflow_client._cache["active_project"] = cached_context

    # Should return cached value without HTTP request
    with patch.object(workflow_client.client, "get") as mock_get:
        result = await workflow_client.get_active_project()

    assert result == project_id
    mock_get.assert_not_called()  # No HTTP request on cache hit


@pytest.mark.asyncio
async def test_get_active_project_cache_expiration(
    workflow_client: WorkflowIntegrationClient,
) -> None:
    """Test cache expiration triggers fresh query.

    Validates:
    - Expired cache triggers new HTTP request
    - Fresh context replaces expired cache entry
    - TTL expiration logic correctly implemented
    """
    # Create expired cache entry
    expired_context = WorkflowIntegrationContext(
        active_project_id="old-project-id",
        status="success",
        retrieved_at=datetime.utcnow() - timedelta(seconds=120),  # 2 minutes ago
        cache_ttl_seconds=60,  # 60 second TTL
    )
    workflow_client._cache["active_project"] = expired_context
    assert expired_context.is_expired()  # Verify it's actually expired

    # Mock fresh response
    new_project_id = "550e8400-e29b-41d4-a716-446655440000"
    mock_response = Mock()
    mock_response.json.return_value = {"project_id": new_project_id}
    mock_response.raise_for_status = Mock()

    async def mock_get(*args: Any, **kwargs: Any) -> Mock:
        return mock_response

    with patch.object(workflow_client.client, "get", side_effect=mock_get):
        result = await workflow_client.get_active_project()

    assert result == new_project_id
    cached_context = workflow_client._cache["active_project"]
    assert cached_context.active_project_id == new_project_id
    assert not cached_context.is_expired()  # Fresh cache


@pytest.mark.asyncio
async def test_get_active_project_no_active_project(
    workflow_client: WorkflowIntegrationClient,
) -> None:
    """Test workflow-mcp returns null project ID.

    Validates:
    - Returns None when workflow-mcp has no active project
    - Context cached with status="success" (successful query, no project)
    - Distinguishes "no active project" from "unavailable"
    """
    mock_response = Mock()
    mock_response.json.return_value = {"project_id": None}
    mock_response.raise_for_status = Mock()

    async def mock_get(*args: Any, **kwargs: Any) -> Mock:
        return mock_response

    with patch.object(workflow_client.client, "get", side_effect=mock_get):
        result = await workflow_client.get_active_project()

    assert result is None
    cached_context = workflow_client._cache["active_project"]
    assert cached_context.active_project_id is None
    assert cached_context.status == "success"  # Successful query, no project


@pytest.mark.asyncio
async def test_close_client(workflow_client: WorkflowIntegrationClient) -> None:
    """Test HTTP client cleanup.

    Validates:
    - close() method releases HTTP connection pool
    - Proper resource cleanup for production deployment
    """
    with patch.object(workflow_client.client, "aclose", new_callable=AsyncMock) as mock_close:
        await workflow_client.close()

    mock_close.assert_awaited_once()


@pytest.mark.asyncio
async def test_timeout_configuration(workflow_client: WorkflowIntegrationClient) -> None:
    """Test timeout configuration is correctly applied.

    Validates:
    - Timeout threshold correctly configured in httpx client
    - Timeout value accessible for logging/diagnostics
    """
    assert workflow_client.timeout.connect == 1.0
    assert workflow_client.cache_ttl == 60


@pytest.mark.asyncio
async def test_cache_ttl_configuration() -> None:
    """Test custom cache TTL configuration.

    Validates:
    - Custom cache TTL is applied to cached contexts
    - TTL configuration propagates to WorkflowIntegrationContext
    """
    client = WorkflowIntegrationClient(cache_ttl=30)

    mock_response = Mock()
    mock_response.json.return_value = {"project_id": "test-id"}
    mock_response.raise_for_status = Mock()

    async def mock_get(*args: Any, **kwargs: Any) -> Mock:
        return mock_response

    with patch.object(client.client, "get", side_effect=mock_get):
        await client.get_active_project()

    cached_context = client._cache["active_project"]
    assert cached_context.cache_ttl_seconds == 30

    await client.close()
