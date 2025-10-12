"""Unit tests for get_session() backward compatibility.

Tests that get_session() with project_id=None uses default workspace and
maintains backward compatibility with existing code.

This test suite uses mocking to avoid event loop conflicts with the global
engine. The actual search_path behavior is tested in integration tests.

Constitutional Compliance:
- Principle VII: Test-Driven Development (validates implementation)
- Principle VIII: Type safety (type-annotated test functions)
- Principle V: Production quality (comprehensive test coverage)

Functional Requirements:
- FR-018: Backward compatibility with project_id=None
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import get_session


# ==============================================================================
# Backward Compatibility Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_get_session_with_none_uses_default() -> None:
    """Test explicit project_id=None uses default workspace.

    Validates FR-018: get_session(project_id=None) sets search_path to
    project_default schema for backward compatibility.
    """
    # Mock session and factory
    mock_session = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar.return_value = "project_default, public"
    mock_session.execute.return_value = mock_result

    with patch("src.database.session.SessionLocal") as mock_factory:
        # Configure factory to return mock session
        mock_factory.return_value.__aenter__.return_value = mock_session
        mock_factory.return_value.__aexit__.return_value = None

        # Call get_session with explicit None
        async with get_session(project_id=None) as session:
            # Verify search_path was set to project_default
            calls = mock_session.execute.call_args_list
            # First call should be SET search_path
            assert len(calls) > 0
            # Extract TextClause from first call
            text_clause = calls[0][0][0]  # First positional arg
            sql_text = str(text_clause)
            assert "SET search_path TO project_default, public" in sql_text

        # Verify commit was called
        mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_session_omitted_uses_default() -> None:
    """Test omitted project_id parameter uses default workspace.

    Validates FR-018: get_session() (no parameter) sets search_path to
    project_default schema for backward compatibility.
    """
    # Mock session and factory
    mock_session = AsyncMock(spec=AsyncSession)

    with patch("src.database.session.SessionLocal") as mock_factory:
        # Configure factory to return mock session
        mock_factory.return_value.__aenter__.return_value = mock_session
        mock_factory.return_value.__aexit__.return_value = None

        # Call get_session with parameter omitted (default argument)
        async with get_session() as session:
            # Verify search_path was set to project_default
            calls = mock_session.execute.call_args_list
            assert len(calls) > 0
            # Extract TextClause from first call
            text_clause = calls[0][0][0]  # First positional arg
            sql_text = str(text_clause)
            assert "SET search_path TO project_default, public" in sql_text

        # Verify commit was called
        mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_none_parameter_logs_backward_compat() -> None:
    """Test that using project_id=None logs backward compatibility message.

    Validates FR-018: Proper logging for backward compatibility mode.
    """
    # Mock session and factory
    mock_session = AsyncMock(spec=AsyncSession)

    with patch("src.database.session.SessionLocal") as mock_factory:
        with patch("src.database.session.logger") as mock_logger:
            # Configure factory to return mock session
            mock_factory.return_value.__aenter__.return_value = mock_session
            mock_factory.return_value.__aexit__.return_value = None

            # Call get_session with explicit None
            async with get_session(project_id=None):
                pass

            # Verify logger.debug was called with backward compatibility message
            debug_calls = [call for call in mock_logger.debug.call_args_list]
            assert len(debug_calls) > 0
            # Check that one of the debug calls mentions backward compatibility
            backward_compat_logged = any(
                "backward compatibility" in str(call).lower() for call in debug_calls
            )
            assert backward_compat_logged


@pytest.mark.asyncio
async def test_explicit_none_does_not_call_workspace_manager() -> None:
    """Test that project_id=None does not invoke ProjectWorkspaceManager.

    Validates FR-018: Backward compatibility path bypasses workspace manager
    for performance and simplicity.
    """
    # Mock session
    mock_session = AsyncMock(spec=AsyncSession)

    with patch("src.database.session.SessionLocal") as mock_factory:
        with patch("src.services.workspace_manager.ProjectWorkspaceManager") as mock_manager:
            # Configure factory to return mock session
            mock_factory.return_value.__aenter__.return_value = mock_session
            mock_factory.return_value.__aexit__.return_value = None

            # Call get_session with explicit None
            async with get_session(project_id=None):
                pass

            # Verify ProjectWorkspaceManager was NOT instantiated
            mock_manager.assert_not_called()


@pytest.mark.asyncio
async def test_omitted_parameter_does_not_call_workspace_manager() -> None:
    """Test that omitted project_id does not invoke ProjectWorkspaceManager.

    Validates FR-018: Backward compatibility path bypasses workspace manager
    when parameter is omitted.
    """
    # Mock session
    mock_session = AsyncMock(spec=AsyncSession)

    with patch("src.database.session.SessionLocal") as mock_factory:
        with patch("src.services.workspace_manager.ProjectWorkspaceManager") as mock_manager:
            # Configure factory to return mock session
            mock_factory.return_value.__aenter__.return_value = mock_session
            mock_factory.return_value.__aexit__.return_value = None

            # Call get_session with parameter omitted
            async with get_session():
                pass

            # Verify ProjectWorkspaceManager was NOT instantiated
            mock_manager.assert_not_called()
