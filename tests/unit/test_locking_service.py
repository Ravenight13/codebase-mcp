"""Unit tests for optimistic locking service.

Tests:
- OptimisticLockError exception creation and serialization
- get_current_version retrieval for VendorExtractor and WorkItem
- update_with_version_check version validation
- Concurrent update conflict detection
- Error handling for invalid entities and version mismatches

Constitutional Compliance:
- Principle VII: Test-Driven Development (comprehensive test coverage)
- Principle VIII: Type safety (type-annotated test functions)
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.exc import StaleDataError

from src.services.locking import (
    OptimisticLockError,
    VersionInfo,
    get_current_version,
    update_with_version_check,
)


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def vendor_id() -> UUID:
    """Generate test vendor UUID."""
    return uuid4()


@pytest.fixture
def work_item_id() -> UUID:
    """Generate test work item UUID."""
    return uuid4()


@pytest.fixture
def mock_vendor() -> MagicMock:
    """Create mock VendorExtractor entity."""
    vendor = MagicMock()
    vendor.id = uuid4()
    vendor.version = 5
    vendor.name = "test_vendor"
    vendor.created_by = "test-client"
    vendor.__class__.__name__ = "VendorExtractor"
    return vendor


@pytest.fixture
def mock_work_item() -> MagicMock:
    """Create mock WorkItem entity."""
    work_item = MagicMock()
    work_item.id = uuid4()
    work_item.version = 3
    work_item.title = "Test Task"
    work_item.created_by = "test-client"
    work_item.__class__.__name__ = "WorkItem"
    return work_item


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create mock AsyncSession."""
    return AsyncMock(spec=AsyncSession)


# ==============================================================================
# OptimisticLockError Tests
# ==============================================================================


def test_optimistic_lock_error_initialization() -> None:
    """Test OptimisticLockError initialization with all fields."""
    entity_id = uuid4()
    error = OptimisticLockError(
        current_version=10,
        expected_version=8,
        last_updated_by="client-abc",
        entity_type="VendorExtractor",
        entity_id=entity_id,
    )

    assert error.current_version == 10
    assert error.expected_version == 8
    assert error.last_updated_by == "client-abc"
    assert error.entity_type == "VendorExtractor"
    assert error.entity_id == entity_id


def test_optimistic_lock_error_message() -> None:
    """Test OptimisticLockError error message formatting."""
    entity_id = uuid4()
    error = OptimisticLockError(
        current_version=10,
        expected_version=8,
        last_updated_by="client-abc",
        entity_type="VendorExtractor",
        entity_id=entity_id,
    )

    message = str(error)
    assert "VendorExtractor" in message
    assert str(entity_id) in message
    assert "expected version 8" in message
    assert "current version is 10" in message
    assert "client-abc" in message


def test_optimistic_lock_error_to_dict() -> None:
    """Test OptimisticLockError serialization to dictionary."""
    entity_id = uuid4()
    error = OptimisticLockError(
        current_version=10,
        expected_version=8,
        last_updated_by="client-abc",
        entity_type="WorkItem",
        entity_id=entity_id,
    )

    error_dict = error.to_dict()

    assert error_dict["error_type"] == "OptimisticLockError"
    assert error_dict["entity_type"] == "WorkItem"
    assert error_dict["entity_id"] == str(entity_id)
    assert error_dict["current_version"] == 10
    assert error_dict["expected_version"] == 8
    assert error_dict["last_updated_by"] == "client-abc"
    assert error_dict["http_status"] == 409


# ==============================================================================
# VersionInfo Pydantic Model Tests
# ==============================================================================


def test_version_info_creation() -> None:
    """Test VersionInfo model creation with valid data."""
    entity_id = uuid4()
    version_info = VersionInfo(
        entity_id=entity_id,
        entity_type="VendorExtractor",
        current_version=5,
    )

    assert version_info.entity_id == entity_id
    assert version_info.entity_type == "VendorExtractor"
    assert version_info.current_version == 5


def test_version_info_frozen() -> None:
    """Test VersionInfo is immutable (frozen)."""
    entity_id = uuid4()
    version_info = VersionInfo(
        entity_id=entity_id,
        entity_type="WorkItem",
        current_version=3,
    )

    with pytest.raises(Exception):  # Pydantic raises ValidationError or AttributeError
        version_info.current_version = 10  # type: ignore[misc]


def test_version_info_validates_version_positive() -> None:
    """Test VersionInfo validates version >= 1."""
    entity_id = uuid4()

    # Valid version (>= 1)
    version_info = VersionInfo(
        entity_id=entity_id,
        entity_type="VendorExtractor",
        current_version=1,
    )
    assert version_info.current_version == 1

    # Invalid version (< 1) should raise validation error
    with pytest.raises(Exception):  # Pydantic ValidationError
        VersionInfo(
            entity_id=entity_id,
            entity_type="VendorExtractor",
            current_version=0,
        )


# ==============================================================================
# get_current_version Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_get_current_version_vendor_extractor(
    vendor_id: UUID,
    mock_vendor: MagicMock,
    mock_session: AsyncMock,
) -> None:
    """Test get_current_version retrieves version for VendorExtractor."""
    # Mock database query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_vendor
    mock_session.execute.return_value = mock_result

    # Call function
    version = await get_current_version(
        entity_id=vendor_id,
        entity_type="VendorExtractor",
        session=mock_session,
    )

    # Verify result
    assert version == 5

    # Verify query was executed
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_current_version_work_item(
    work_item_id: UUID,
    mock_work_item: MagicMock,
    mock_session: AsyncMock,
) -> None:
    """Test get_current_version retrieves version for WorkItem."""
    # Mock database query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_work_item
    mock_session.execute.return_value = mock_result

    # Call function
    version = await get_current_version(
        entity_id=work_item_id,
        entity_type="WorkItem",
        session=mock_session,
    )

    # Verify result
    assert version == 3

    # Verify query was executed
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_current_version_entity_not_found(
    vendor_id: UUID,
    mock_session: AsyncMock,
) -> None:
    """Test get_current_version raises ValueError when entity not found."""
    # Mock database query returns None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    # Call function and expect ValueError
    with pytest.raises(ValueError, match="VendorExtractor with id .* not found"):
        await get_current_version(
            entity_id=vendor_id,
            entity_type="VendorExtractor",
            session=mock_session,
        )


@pytest.mark.asyncio
async def test_get_current_version_invalid_entity_type(
    vendor_id: UUID,
    mock_session: AsyncMock,
) -> None:
    """Test get_current_version raises ValueError for invalid entity_type."""
    # Call function with invalid entity_type
    with pytest.raises(ValueError, match="Invalid entity_type"):
        await get_current_version(
            entity_id=vendor_id,
            entity_type="InvalidType",  # type: ignore[arg-type]
            session=mock_session,
        )


# ==============================================================================
# update_with_version_check Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_update_with_version_check_success(
    mock_vendor: MagicMock,
    mock_session: AsyncMock,
) -> None:
    """Test update_with_version_check successfully updates with matching version."""
    # Setup
    updates = {"status": "broken"}
    expected_version = 5

    # Call function
    result = await update_with_version_check(
        entity=mock_vendor,
        updates=updates,
        expected_version=expected_version,
        session=mock_session,
    )

    # Verify entity was updated
    assert mock_vendor.status == "broken"

    # Verify entity was added to session
    mock_session.add.assert_called_once_with(mock_vendor)

    # Verify session was flushed
    mock_session.flush.assert_awaited_once()

    # Verify result is updated entity
    assert result is mock_vendor


@pytest.mark.asyncio
async def test_update_with_version_check_version_conflict(
    mock_vendor: MagicMock,
    mock_session: AsyncMock,
) -> None:
    """Test update_with_version_check raises OptimisticLockError on version mismatch."""
    # Setup - current version is 5, but client expects 3
    updates = {"status": "broken"}
    expected_version = 3

    # Call function and expect OptimisticLockError
    with pytest.raises(OptimisticLockError) as exc_info:
        await update_with_version_check(
            entity=mock_vendor,
            updates=updates,
            expected_version=expected_version,
            session=mock_session,
        )

    # Verify error details
    error = exc_info.value
    assert error.current_version == 5
    assert error.expected_version == 3
    assert error.entity_type == "VendorExtractor"
    assert error.entity_id == mock_vendor.id

    # Verify session was NOT flushed (pre-check failed)
    mock_session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_with_version_check_multiple_fields(
    mock_work_item: MagicMock,
    mock_session: AsyncMock,
) -> None:
    """Test update_with_version_check updates multiple fields."""
    # Setup
    updates = {
        "status": "completed",
        "branch_name": "feature-001",
        "commit_hash": "abc123",
    }
    expected_version = 3

    # Call function
    await update_with_version_check(
        entity=mock_work_item,
        updates=updates,
        expected_version=expected_version,
        session=mock_session,
    )

    # Verify all fields were updated
    assert mock_work_item.status == "completed"
    assert mock_work_item.branch_name == "feature-001"
    assert mock_work_item.commit_hash == "abc123"


@pytest.mark.asyncio
async def test_update_with_version_check_invalid_field(
    mock_vendor: MagicMock,
    mock_session: AsyncMock,
) -> None:
    """Test update_with_version_check raises ValueError for invalid field."""
    # Create a class that doesn't allow arbitrary attributes
    class LimitedEntity:
        def __init__(self) -> None:
            self.id = mock_vendor.id
            self.version = 5
            self.name = "test"
            self.created_by = "test-client"

    entity = LimitedEntity()

    # Setup with invalid field name
    updates = {"nonexistent_field": "value"}
    expected_version = 5

    # Call function and expect ValueError
    with pytest.raises(ValueError, match="Invalid field"):
        await update_with_version_check(
            entity=entity,  # type: ignore[type-var]
            updates=updates,
            expected_version=expected_version,
            session=mock_session,
        )


@pytest.mark.asyncio
async def test_update_with_version_check_stale_data_error(
    mock_vendor: MagicMock,
    mock_session: AsyncMock,
) -> None:
    """Test update_with_version_check handles SQLAlchemy StaleDataError."""
    # Setup
    updates = {"status": "broken"}
    expected_version = 5

    # Mock flush to raise StaleDataError
    mock_session.flush.side_effect = StaleDataError("Version conflict")

    # Mock refresh to update version
    async def mock_refresh(entity: MagicMock) -> None:
        entity.version = 6

    mock_session.refresh.side_effect = mock_refresh

    # Call function and expect OptimisticLockError
    with pytest.raises(OptimisticLockError) as exc_info:
        await update_with_version_check(
            entity=mock_vendor,
            updates=updates,
            expected_version=expected_version,
            session=mock_session,
        )

    # Verify error details
    error = exc_info.value
    assert error.current_version == 6  # Updated after refresh
    assert error.expected_version == 5

    # Verify refresh was called
    mock_session.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_with_version_check_version_auto_incremented(
    mock_vendor: MagicMock,
    mock_session: AsyncMock,
) -> None:
    """Test update_with_version_check relies on SQLAlchemy for version increment."""
    # Setup
    updates = {"status": "broken"}
    expected_version = 5

    # Mock flush to simulate SQLAlchemy auto-incrementing version
    async def mock_flush() -> None:
        mock_vendor.version = 6  # Simulate SQLAlchemy increment

    mock_session.flush.side_effect = mock_flush

    # Call function
    result = await update_with_version_check(
        entity=mock_vendor,
        updates=updates,
        expected_version=expected_version,
        session=mock_session,
    )

    # Verify version was incremented (by SQLAlchemy simulation)
    assert result.version == 6


# ==============================================================================
# Logging Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_get_current_version_logs_retrieval(
    vendor_id: UUID,
    mock_vendor: MagicMock,
    mock_session: AsyncMock,
) -> None:
    """Test get_current_version logs version retrieval."""
    # Mock database query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_vendor
    mock_session.execute.return_value = mock_result

    # Mock logger
    with patch("src.services.locking.logger") as mock_logger:
        # Call function
        await get_current_version(
            entity_id=vendor_id,
            entity_type="VendorExtractor",
            session=mock_session,
        )

        # Verify debug logs were called
        assert mock_logger.debug.call_count == 2  # Initial and result logs


@pytest.mark.asyncio
async def test_update_with_version_check_logs_conflict(
    mock_vendor: MagicMock,
    mock_session: AsyncMock,
) -> None:
    """Test update_with_version_check logs version conflict warnings."""
    # Setup version conflict
    updates = {"status": "broken"}
    expected_version = 3

    # Mock logger
    with patch("src.services.locking.logger") as mock_logger:
        # Call function and expect OptimisticLockError
        with pytest.raises(OptimisticLockError):
            await update_with_version_check(
                entity=mock_vendor,
                updates=updates,
                expected_version=expected_version,
                session=mock_session,
            )

        # Verify warning was logged
        mock_logger.warning.assert_called_once()

        # Verify warning includes context
        call_args = mock_logger.warning.call_args
        assert "extra" in call_args.kwargs
        assert "context" in call_args.kwargs["extra"]


@pytest.mark.asyncio
async def test_update_with_version_check_logs_success(
    mock_vendor: MagicMock,
    mock_session: AsyncMock,
) -> None:
    """Test update_with_version_check logs successful updates."""
    # Setup
    updates = {"status": "broken"}
    expected_version = 5

    # Mock logger
    with patch("src.services.locking.logger") as mock_logger:
        # Call function
        await update_with_version_check(
            entity=mock_vendor,
            updates=updates,
            expected_version=expected_version,
            session=mock_session,
        )

        # Verify info logs were called (initial and success)
        assert mock_logger.info.call_count == 2


# ==============================================================================
# Edge Case Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_update_with_version_check_empty_updates(
    mock_vendor: MagicMock,
    mock_session: AsyncMock,
) -> None:
    """Test update_with_version_check handles empty updates dict."""
    # Setup with no updates
    updates: dict[str, str] = {}
    expected_version = 5

    # Call function (should succeed even with no field changes)
    result = await update_with_version_check(
        entity=mock_vendor,
        updates=updates,
        expected_version=expected_version,
        session=mock_session,
    )

    # Verify session operations still occurred
    mock_session.add.assert_called_once()
    mock_session.flush.assert_awaited_once()
    assert result is mock_vendor


@pytest.mark.asyncio
async def test_update_with_version_check_version_one(
    mock_vendor: MagicMock,
    mock_session: AsyncMock,
) -> None:
    """Test update_with_version_check works with version 1 (initial version)."""
    # Setup entity with initial version
    mock_vendor.version = 1
    updates = {"status": "operational"}
    expected_version = 1

    # Call function
    result = await update_with_version_check(
        entity=mock_vendor,
        updates=updates,
        expected_version=expected_version,
        session=mock_session,
    )

    # Verify update succeeded
    assert result is mock_vendor
    mock_session.flush.assert_awaited_once()
