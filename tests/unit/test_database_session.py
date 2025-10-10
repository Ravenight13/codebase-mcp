"""Unit tests for database session factory and health checks.

Tests:
- Session factory creation and configuration
- Context manager transaction management (commit/rollback)
- Database health check functionality
- Error handling and cleanup

Constitutional Compliance:
- Principle VII: Test-Driven Development (comprehensive test coverage)
- Principle VIII: Type safety (type-annotated test functions)
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.session import (
    check_database_health,
    get_session,
    get_session_factory,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import async_sessionmaker


# ==============================================================================
# Session Factory Tests
# ==============================================================================


def test_get_session_factory_returns_sessionmaker() -> None:
    """Test that get_session_factory returns the correct sessionmaker type."""
    factory = get_session_factory()

    # Verify return type
    assert factory is not None
    assert callable(factory)

    # Verify factory configuration is set
    # Note: async_sessionmaker stores configuration internally
    # We can't easily inspect internal state, so we verify it's callable
    assert hasattr(factory, "__call__")


# ==============================================================================
# Session Context Manager Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_get_session_commits_on_success() -> None:
    """Test that get_session automatically commits on successful exit."""
    # Mock session
    mock_session = AsyncMock(spec=AsyncSession)

    # Mock SessionLocal factory
    with patch("src.database.session.SessionLocal") as mock_factory:
        # Configure factory to return mock session
        mock_factory.return_value.__aenter__.return_value = mock_session
        mock_factory.return_value.__aexit__.return_value = None

        # Use session context manager
        async with get_session() as session:
            # Simulate database operation
            await session.execute(MagicMock())

        # Verify commit was called
        mock_session.commit.assert_awaited_once()

        # Verify close was called
        mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_session_rolls_back_on_error() -> None:
    """Test that get_session automatically rolls back on exception."""
    # Mock session
    mock_session = AsyncMock(spec=AsyncSession)

    # Mock SessionLocal factory
    with patch("src.database.session.SessionLocal") as mock_factory:
        # Configure factory to return mock session
        mock_factory.return_value.__aenter__.return_value = mock_session
        mock_factory.return_value.__aexit__.return_value = None

        # Use session context manager with error
        with pytest.raises(SQLAlchemyError):
            async with get_session() as session:
                # Simulate database error
                raise SQLAlchemyError("Test error")

        # Verify rollback was called
        mock_session.rollback.assert_awaited_once()

        # Verify commit was NOT called
        mock_session.commit.assert_not_awaited()

        # Verify close was called even after error
        mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_session_closes_on_any_exception() -> None:
    """Test that get_session closes session even on unexpected exceptions."""
    # Mock session
    mock_session = AsyncMock(spec=AsyncSession)

    # Mock SessionLocal factory
    with patch("src.database.session.SessionLocal") as mock_factory:
        # Configure factory to return mock session
        mock_factory.return_value.__aenter__.return_value = mock_session
        mock_factory.return_value.__aexit__.return_value = None

        # Use session context manager with unexpected error
        with pytest.raises(RuntimeError):
            async with get_session() as session:
                # Simulate unexpected runtime error
                raise RuntimeError("Unexpected error")

        # Verify rollback was called
        mock_session.rollback.assert_awaited_once()

        # Verify close was called
        mock_session.close.assert_awaited_once()


# ==============================================================================
# Health Check Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_check_database_health_returns_true_on_success() -> None:
    """Test that check_database_health returns True when database is accessible."""
    # Mock the entire engine object
    with patch("src.database.session.engine") as mock_engine:
        # Create mock connection
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        # Configure connect to return mock connection
        mock_engine.connect.return_value.__aenter__.return_value = mock_conn
        mock_engine.connect.return_value.__aexit__.return_value = None

        # Call health check
        result = await check_database_health()

        # Verify result
        assert result is True

        # Verify execute was called
        mock_conn.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_check_database_health_returns_false_on_error() -> None:
    """Test that check_database_health returns False when database is unavailable."""
    # Mock the entire engine object
    with patch("src.database.session.engine") as mock_engine:
        # Configure connect to raise exception
        mock_engine.connect.side_effect = SQLAlchemyError("Connection failed")

        # Call health check
        result = await check_database_health()

        # Verify result
        assert result is False


@pytest.mark.asyncio
async def test_check_database_health_logs_errors() -> None:
    """Test that check_database_health logs errors with proper context."""
    # Mock logger
    with patch("src.database.session.logger") as mock_logger:
        # Mock the entire engine object
        with patch("src.database.session.engine") as mock_engine:
            # Configure connect to raise exception
            mock_engine.connect.side_effect = SQLAlchemyError("Connection failed")

            # Call health check
            await check_database_health()

            # Verify error was logged
            mock_logger.error.assert_called_once()

            # Verify log includes context
            call_args = mock_logger.error.call_args
            assert "extra" in call_args.kwargs
            assert "context" in call_args.kwargs["extra"]
            assert "error" in call_args.kwargs["extra"]["context"]


# ==============================================================================
# Configuration Tests
# ==============================================================================


def test_session_factory_configuration() -> None:
    """Test that session factory has correct configuration."""
    factory = get_session_factory()

    # Verify factory is callable (internal configuration is opaque)
    assert callable(factory)

    # Verify factory has expected attributes
    assert hasattr(factory, "__call__")


@pytest.mark.asyncio
async def test_session_context_manager_pattern() -> None:
    """Test that session supports async context manager protocol."""
    # Mock session
    mock_session = AsyncMock(spec=AsyncSession)

    # Mock SessionLocal factory
    with patch("src.database.session.SessionLocal") as mock_factory:
        # Configure factory to return mock session
        mock_factory.return_value.__aenter__.return_value = mock_session
        mock_factory.return_value.__aexit__.return_value = None

        # Verify context manager protocol
        async with get_session() as session:
            assert session is mock_session


# ==============================================================================
# Error Handling Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_get_session_propagates_exceptions() -> None:
    """Test that get_session propagates exceptions after cleanup."""
    # Mock session
    mock_session = AsyncMock(spec=AsyncSession)

    # Mock SessionLocal factory
    with patch("src.database.session.SessionLocal") as mock_factory:
        # Configure factory to return mock session
        mock_factory.return_value.__aenter__.return_value = mock_session
        mock_factory.return_value.__aexit__.return_value = None

        # Custom exception class
        class CustomError(Exception):
            pass

        # Verify exception is propagated
        with pytest.raises(CustomError):
            async with get_session() as session:
                raise CustomError("Test error")

        # Verify cleanup happened
        mock_session.rollback.assert_awaited_once()
        mock_session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_session_logs_transaction_lifecycle() -> None:
    """Test that get_session logs transaction start, commit, and close."""
    # Mock logger
    with patch("src.database.session.logger") as mock_logger:
        # Mock session
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock SessionLocal factory
        with patch("src.database.session.SessionLocal") as mock_factory:
            # Configure factory to return mock session
            mock_factory.return_value.__aenter__.return_value = mock_session
            mock_factory.return_value.__aexit__.return_value = None

            # Use session
            async with get_session() as session:
                pass

            # Verify logging calls (debug level)
            assert mock_logger.debug.call_count >= 2  # Start and close logs


# ==============================================================================
# Integration-Style Tests (without actual database)
# ==============================================================================


@pytest.mark.asyncio
async def test_session_factory_creates_independent_sessions() -> None:
    """Test that session factory creates independent session instances."""
    factory = get_session_factory()

    # Mock the actual session creation
    with patch("src.database.session.SessionLocal") as mock_factory:
        mock_session1 = AsyncMock(spec=AsyncSession)
        mock_session2 = AsyncMock(spec=AsyncSession)

        # Configure factory to return different sessions
        mock_factory.return_value.__aenter__.side_effect = [
            mock_session1,
            mock_session2,
        ]
        mock_factory.return_value.__aexit__.return_value = None

        # Create two sessions
        async with get_session() as session1:
            pass

        async with get_session() as session2:
            pass

        # Verify both sessions were committed and closed
        mock_session1.commit.assert_awaited_once()
        mock_session1.close.assert_awaited_once()
        mock_session2.commit.assert_awaited_once()
        mock_session2.close.assert_awaited_once()
