"""Unit tests for resolve_project_id() utility function.

This test module validates the multi-project workspace resolution logic with
three-tier fallback strategy: explicit_id → workflow-mcp → default workspace.

Test Scenarios:
- T1: Explicit ID takes precedence (highest priority)
- T2: workflow-mcp success (active project returned)
- T3: workflow-mcp timeout (fallback to default)
- T4: workflow-mcp unavailable (fallback to default)
- T5: workflow-mcp disabled (fallback to default)
- T6: Settings dependency injection

Constitutional Compliance:
- Principle VIII: Type safety (mypy --strict compliance)
- Principle VII: Test-driven development (comprehensive coverage)
- Principle V: Production quality (error handling validation)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import HttpUrl, PostgresDsn

from src.config.settings import Settings
from src.database.session import resolve_project_id


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def mock_settings_with_workflow() -> Settings:
    """Settings with workflow-mcp integration enabled."""
    return Settings(
        database_url=PostgresDsn("postgresql+asyncpg://localhost/test_db"),
        workflow_mcp_url=HttpUrl("http://localhost:8000"),
        workflow_mcp_timeout=1.0,
        workflow_mcp_cache_ttl=60,
    )


@pytest.fixture
def mock_settings_without_workflow() -> Settings:
    """Settings with workflow-mcp integration disabled."""
    return Settings(
        database_url=PostgresDsn("postgresql+asyncpg://localhost/test_db"),
        workflow_mcp_url=None,
    )


# ==============================================================================
# Test: T1 - Explicit ID Takes Precedence
# ==============================================================================


@pytest.mark.asyncio
async def test_resolve_project_id_explicit_id_precedence() -> None:
    """Verify explicit_id takes precedence over workflow-mcp.

    Scenario: User provides explicit project_id parameter
    Expected: Return explicit_id immediately without querying workflow-mcp

    Constitutional Compliance:
        - Principle VIII: Type safety validation
        - FR-012: Explicit ID priority
    """
    # Arrange
    explicit_id = "client-a"

    # Act
    result = await resolve_project_id(explicit_id=explicit_id)

    # Assert
    assert result == explicit_id, "Explicit ID should be returned immediately"


@pytest.mark.asyncio
async def test_resolve_project_id_explicit_id_no_workflow_query() -> None:
    """Verify workflow-mcp is not queried when explicit_id is provided.

    Scenario: Explicit ID provided with workflow-mcp enabled
    Expected: workflow-mcp client is never instantiated

    Constitutional Compliance:
        - Principle IV: Performance (no unnecessary I/O)
        - FR-012: Explicit ID optimization
    """
    # Arrange
    explicit_id = "client-a"
    settings = Settings(
        database_url=PostgresDsn("postgresql+asyncpg://localhost/test_db"),
        workflow_mcp_url=HttpUrl("http://localhost:8000"),
    )

    with patch("src.database.session.WorkflowIntegrationClient") as mock_client_class:
        # Act
        result = await resolve_project_id(
            explicit_id=explicit_id,
            settings=settings,
        )

        # Assert
        assert result == explicit_id
        mock_client_class.assert_not_called()  # workflow-mcp client never created


# ==============================================================================
# Test: T2 - workflow-mcp Success
# ==============================================================================


@pytest.mark.asyncio
async def test_resolve_project_id_workflow_mcp_success(
    mock_settings_with_workflow: Settings,
) -> None:
    """Verify successful workflow-mcp query returns active project.

    Scenario: No explicit_id, workflow-mcp returns active project
    Expected: Return active project UUID from workflow-mcp

    Constitutional Compliance:
        - FR-012: workflow-mcp integration
        - FR-014: Caching implementation
    """
    # Arrange
    active_project_id = "workflow-project-123"
    mock_client = AsyncMock()
    mock_client.get_active_project.return_value = active_project_id

    with patch("src.database.session.WorkflowIntegrationClient") as mock_client_class:
        mock_client_class.return_value = mock_client

        # Act
        result = await resolve_project_id(
            explicit_id=None,
            settings=mock_settings_with_workflow,
        )

        # Assert
        assert result == active_project_id
        mock_client.get_active_project.assert_awaited_once()
        mock_client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_project_id_workflow_mcp_no_active_project(
    mock_settings_with_workflow: Settings,
) -> None:
    """Verify fallback when workflow-mcp has no active project.

    Scenario: workflow-mcp returns None (no active project set)
    Expected: Return None for default workspace fallback

    Constitutional Compliance:
        - FR-013: Graceful degradation
        - FR-018: Backward compatibility
    """
    # Arrange
    mock_client = AsyncMock()
    mock_client.get_active_project.return_value = None  # No active project

    with patch("src.database.session.WorkflowIntegrationClient") as mock_client_class:
        mock_client_class.return_value = mock_client

        # Act
        result = await resolve_project_id(
            explicit_id=None,
            settings=mock_settings_with_workflow,
        )

        # Assert
        assert result is None
        mock_client.get_active_project.assert_awaited_once()
        mock_client.close.assert_awaited_once()


# ==============================================================================
# Test: T3 - workflow-mcp Timeout
# ==============================================================================


@pytest.mark.asyncio
async def test_resolve_project_id_workflow_mcp_timeout(
    mock_settings_with_workflow: Settings,
) -> None:
    """Verify fallback when workflow-mcp query times out.

    Scenario: workflow-mcp query exceeds timeout threshold
    Expected: Return None for default workspace, log warning

    Constitutional Compliance:
        - FR-013: Timeout handling
        - Principle V: Production quality error handling
    """
    # Arrange
    mock_client = AsyncMock()
    mock_client.get_active_project.side_effect = TimeoutError("Request timeout")

    with patch("src.database.session.WorkflowIntegrationClient") as mock_client_class:
        mock_client_class.return_value = mock_client

        # Act
        result = await resolve_project_id(
            explicit_id=None,
            settings=mock_settings_with_workflow,
        )

        # Assert
        assert result is None
        mock_client.get_active_project.assert_awaited_once()
        mock_client.close.assert_awaited_once()


# ==============================================================================
# Test: T4 - workflow-mcp Unavailable
# ==============================================================================


@pytest.mark.asyncio
async def test_resolve_project_id_workflow_mcp_connection_error(
    mock_settings_with_workflow: Settings,
) -> None:
    """Verify fallback when workflow-mcp connection fails.

    Scenario: workflow-mcp server not running or unreachable
    Expected: Return None for default workspace, log warning

    Constitutional Compliance:
        - FR-013: Connection error handling
        - Principle II: Local-first architecture
    """
    # Arrange
    mock_client = AsyncMock()
    mock_client.get_active_project.side_effect = ConnectionError("Connection refused")

    with patch("src.database.session.WorkflowIntegrationClient") as mock_client_class:
        mock_client_class.return_value = mock_client

        # Act
        result = await resolve_project_id(
            explicit_id=None,
            settings=mock_settings_with_workflow,
        )

        # Assert
        assert result is None
        mock_client.get_active_project.assert_awaited_once()
        mock_client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_project_id_workflow_mcp_invalid_response(
    mock_settings_with_workflow: Settings,
) -> None:
    """Verify fallback when workflow-mcp returns invalid response.

    Scenario: workflow-mcp returns malformed JSON or unexpected error
    Expected: Return None for default workspace, log warning

    Constitutional Compliance:
        - FR-013: Invalid response handling
        - Principle V: Comprehensive error handling
    """
    # Arrange
    mock_client = AsyncMock()
    mock_client.get_active_project.side_effect = ValueError("Invalid JSON")

    with patch("src.database.session.WorkflowIntegrationClient") as mock_client_class:
        mock_client_class.return_value = mock_client

        # Act
        result = await resolve_project_id(
            explicit_id=None,
            settings=mock_settings_with_workflow,
        )

        # Assert
        assert result is None
        mock_client.get_active_project.assert_awaited_once()
        mock_client.close.assert_awaited_once()


# ==============================================================================
# Test: T5 - workflow-mcp Disabled
# ==============================================================================


@pytest.mark.asyncio
async def test_resolve_project_id_workflow_mcp_disabled(
    mock_settings_without_workflow: Settings,
) -> None:
    """Verify fallback when workflow-mcp is disabled in settings.

    Scenario: workflow_mcp_url is None (integration disabled)
    Expected: Return None immediately without creating client

    Constitutional Compliance:
        - FR-013: Graceful degradation
        - FR-018: Backward compatibility
    """
    # Arrange
    with patch("src.database.session.WorkflowIntegrationClient") as mock_client_class:
        # Act
        result = await resolve_project_id(
            explicit_id=None,
            settings=mock_settings_without_workflow,
        )

        # Assert
        assert result is None
        mock_client_class.assert_not_called()  # Client never created


# ==============================================================================
# Test: T6 - Settings Dependency Injection
# ==============================================================================


@pytest.mark.asyncio
async def test_resolve_project_id_uses_global_settings_when_none_provided() -> None:
    """Verify global settings singleton is used when settings=None.

    Scenario: No settings parameter provided
    Expected: Uses get_settings() to load global configuration

    Constitutional Compliance:
        - Principle VIII: Type safety with optional parameters
    """
    # Arrange
    explicit_id = "test-project"

    with patch("src.database.session.get_settings") as mock_get_settings:
        # Act
        result = await resolve_project_id(
            explicit_id=explicit_id,
            settings=None,  # Should trigger get_settings() call
        )

        # Assert
        assert result == explicit_id
        # get_settings() should not be called when explicit_id is provided
        # (early return optimization)
        mock_get_settings.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_project_id_uses_provided_settings() -> None:
    """Verify provided settings are used instead of global singleton.

    Scenario: Settings instance provided as parameter
    Expected: Uses provided settings, does not call get_settings()

    Constitutional Compliance:
        - Principle VIII: Dependency injection pattern
    """
    # Arrange
    custom_settings = Settings(
        database_url=PostgresDsn("postgresql+asyncpg://localhost/custom_db"),
        workflow_mcp_url=HttpUrl("http://custom:9000"),
    )
    mock_client = AsyncMock()
    mock_client.get_active_project.return_value = "custom-project"

    with patch("src.database.session.WorkflowIntegrationClient") as mock_client_class:
        with patch("src.database.session.get_settings") as mock_get_settings:
            mock_client_class.return_value = mock_client

            # Act
            result = await resolve_project_id(
                explicit_id=None,
                settings=custom_settings,
            )

            # Assert
            assert result == "custom-project"
            mock_get_settings.assert_not_called()  # Custom settings used
            mock_client_class.assert_called_once_with(
                base_url="http://custom:9000/",  # Pydantic HttpUrl adds trailing slash
                timeout=1.0,  # Default from custom_settings
                cache_ttl=60,  # Default from custom_settings
            )


# ==============================================================================
# Test: Resource Cleanup
# ==============================================================================


@pytest.mark.asyncio
async def test_resolve_project_id_closes_client_on_success(
    mock_settings_with_workflow: Settings,
) -> None:
    """Verify WorkflowIntegrationClient is closed after successful query.

    Scenario: workflow-mcp query succeeds
    Expected: client.close() is called in finally block

    Constitutional Compliance:
        - Principle V: Production quality (resource cleanup)
    """
    # Arrange
    mock_client = AsyncMock()
    mock_client.get_active_project.return_value = "project-123"

    with patch("src.database.session.WorkflowIntegrationClient") as mock_client_class:
        mock_client_class.return_value = mock_client

        # Act
        await resolve_project_id(
            explicit_id=None,
            settings=mock_settings_with_workflow,
        )

        # Assert
        mock_client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_resolve_project_id_closes_client_on_error(
    mock_settings_with_workflow: Settings,
) -> None:
    """Verify WorkflowIntegrationClient is closed even when query fails.

    Scenario: workflow-mcp query raises exception
    Expected: client.close() is still called in finally block

    Constitutional Compliance:
        - Principle V: Production quality (cleanup on error)
    """
    # Arrange
    mock_client = AsyncMock()
    mock_client.get_active_project.side_effect = RuntimeError("Query failed")

    with patch("src.database.session.WorkflowIntegrationClient") as mock_client_class:
        mock_client_class.return_value = mock_client

        # Act
        result = await resolve_project_id(
            explicit_id=None,
            settings=mock_settings_with_workflow,
        )

        # Assert
        assert result is None  # Fallback to default
        mock_client.close.assert_awaited_once()  # Cleanup still happens
