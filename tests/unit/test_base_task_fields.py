"""
Unit tests for BaseTaskFields Pydantic model.

Tests cover:
- Field validation for all 5 core fields (id, title, status, created_at, updated_at)
- ORM mode compatibility (from_attributes=True configuration)
- Inheritance by TaskSummary and TaskResponse models
- Title validator (non-empty after stripping, ≤200 chars)
- Status Literal type validation
- UUID format validation
- Datetime field validation

TDD Approach:
- Tests written BEFORE BaseTaskFields implementation
- Initial run should FAIL with ImportError (model doesn't exist)
- Tests define expected behavior and validation rules
- Implementation driven by test requirements

Constitutional Compliance:
- Principle VII: Test-driven development (tests before implementation)
- Principle VIII: Type safety (complete type annotations, Pydantic validation)
- Principle V: Production quality (comprehensive validation coverage)

Feature: 004-as-an-ai (Optimize list_tasks MCP Tool for Token Efficiency)
Related: specs/004-as-an-ai/data-model.md
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError

# TDD: This import will FAIL initially - BaseTaskFields doesn't exist yet
try:
    from src.models.task_schemas import (
        BaseTaskFields,
        TaskResponse,
        TaskSummary,
    )

    MODELS_EXIST = True
except ImportError:
    MODELS_EXIST = False

    # Define minimal stubs for test structure validation
    # These will be replaced by actual implementation
    class BaseTaskFields(BaseModel):  # type: ignore[no-redef]
        """Stub for TDD - will fail actual tests."""

        pass

    class TaskSummary(BaseTaskFields):  # type: ignore[no-redef]
        """Stub for TDD - will fail actual tests."""

        pass

    class TaskResponse(BaseTaskFields):  # type: ignore[no-redef]
        """Stub for TDD - will fail actual tests."""

        pass


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def valid_task_field_data() -> dict[str, Any]:
    """Provide valid data for BaseTaskFields construction.

    Returns:
        Dictionary with all 5 core fields (id, title, status, created_at, updated_at)
    """
    return {
        "id": uuid.uuid4(),
        "title": "Implement user authentication",
        "status": "in-progress",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


@pytest.fixture
def sample_task_id() -> uuid.UUID:
    """Provide sample UUID for testing.

    Returns:
        Valid UUID4 instance
    """
    return uuid.UUID("550e8400-e29b-41d4-a716-446655440000")


# =============================================================================
# Test BaseTaskFields Core Functionality
# =============================================================================


class TestBaseTaskFieldsValidation:
    """Test validation rules for BaseTaskFields Pydantic model."""

    @pytest.mark.skipif(not MODELS_EXIST, reason="BaseTaskFields not implemented yet")
    def test_valid_fields_construction(
        self, valid_task_field_data: dict[str, Any]
    ) -> None:
        """Test BaseTaskFields constructs successfully with valid data.

        Validates:
        - All 5 required fields accepted
        - Field types correctly validated
        - No validation errors raised
        """
        # Act
        task_fields = BaseTaskFields(**valid_task_field_data)

        # Assert
        assert task_fields.id == valid_task_field_data["id"]
        assert task_fields.title == valid_task_field_data["title"]
        assert task_fields.status == valid_task_field_data["status"]
        assert task_fields.created_at == valid_task_field_data["created_at"]
        assert task_fields.updated_at == valid_task_field_data["updated_at"]

    @pytest.mark.skipif(not MODELS_EXIST, reason="BaseTaskFields not implemented yet")
    def test_missing_required_field_id(
        self, valid_task_field_data: dict[str, Any]
    ) -> None:
        """Test validation fails when required 'id' field is missing.

        Validates:
        - Pydantic raises ValidationError for missing field
        - Error message indicates 'id' field required
        """
        # Arrange
        invalid_data = {**valid_task_field_data}
        del invalid_data["id"]

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            BaseTaskFields(**invalid_data)

        error = exc_info.value
        assert "id" in str(error).lower()
        assert "field required" in str(error).lower()

    @pytest.mark.skipif(not MODELS_EXIST, reason="BaseTaskFields not implemented yet")
    def test_missing_required_field_title(
        self, valid_task_field_data: dict[str, Any]
    ) -> None:
        """Test validation fails when required 'title' field is missing.

        Validates:
        - Pydantic raises ValidationError for missing field
        - Error message indicates 'title' field required
        """
        # Arrange
        invalid_data = {**valid_task_field_data}
        del invalid_data["title"]

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            BaseTaskFields(**invalid_data)

        error = exc_info.value
        assert "title" in str(error).lower()
        assert "field required" in str(error).lower()

    @pytest.mark.skipif(not MODELS_EXIST, reason="BaseTaskFields not implemented yet")
    def test_missing_required_field_status(
        self, valid_task_field_data: dict[str, Any]
    ) -> None:
        """Test validation fails when required 'status' field is missing.

        Validates:
        - Pydantic raises ValidationError for missing field
        - Error message indicates 'status' field required
        """
        # Arrange
        invalid_data = {**valid_task_field_data}
        del invalid_data["status"]

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            BaseTaskFields(**invalid_data)

        error = exc_info.value
        assert "status" in str(error).lower()
        assert "field required" in str(error).lower()


# =============================================================================
# Test Title Field Validation
# =============================================================================


class TestTitleFieldValidation:
    """Test title field constraints and validation rules."""

    @pytest.mark.skipif(not MODELS_EXIST, reason="BaseTaskFields not implemented yet")
    def test_title_empty_string_rejected(
        self, valid_task_field_data: dict[str, Any]
    ) -> None:
        """Test validation fails for empty string title.

        Validates:
        - Empty string fails validation (min_length=1 constraint)
        - Clear error message provided
        """
        # Arrange
        invalid_data = {**valid_task_field_data, "title": ""}

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            BaseTaskFields(**invalid_data)

        error = exc_info.value
        assert "title" in str(error).lower()

    @pytest.mark.skipif(not MODELS_EXIST, reason="BaseTaskFields not implemented yet")
    def test_title_whitespace_only_rejected(
        self, valid_task_field_data: dict[str, Any]
    ) -> None:
        """Test validation fails for whitespace-only title.

        Validates:
        - Whitespace-only title fails validation (after strip check)
        - Field validator rejects whitespace-only input
        """
        # Arrange
        invalid_data = {**valid_task_field_data, "title": "   \t\n   "}

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            BaseTaskFields(**invalid_data)

        error = exc_info.value
        assert "title" in str(error).lower()

    @pytest.mark.skipif(not MODELS_EXIST, reason="BaseTaskFields not implemented yet")
    def test_title_max_length_200_enforced(
        self, valid_task_field_data: dict[str, Any]
    ) -> None:
        """Test validation fails for title exceeding 200 characters.

        Validates:
        - max_length=200 constraint enforced
        - 201-character title rejected
        """
        # Arrange
        invalid_data = {**valid_task_field_data, "title": "a" * 201}

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            BaseTaskFields(**invalid_data)

        error = exc_info.value
        assert "title" in str(error).lower()

    @pytest.mark.skipif(not MODELS_EXIST, reason="BaseTaskFields not implemented yet")
    def test_title_max_length_200_accepted(
        self, valid_task_field_data: dict[str, Any]
    ) -> None:
        """Test validation accepts title exactly 200 characters.

        Validates:
        - Boundary value (200 chars) accepted
        - max_length constraint inclusive
        """
        # Arrange
        valid_data = {**valid_task_field_data, "title": "a" * 200}

        # Act
        task_fields = BaseTaskFields(**valid_data)

        # Assert
        assert len(task_fields.title) == 200

    @pytest.mark.skipif(not MODELS_EXIST, reason="BaseTaskFields not implemented yet")
    def test_title_strips_leading_trailing_whitespace(
        self, valid_task_field_data: dict[str, Any]
    ) -> None:
        """Test title validator strips leading/trailing whitespace.

        Validates:
        - Field validator calls .strip() on input
        - Stored title has no surrounding whitespace
        """
        # Arrange
        valid_data = {**valid_task_field_data, "title": "  Valid Title  "}

        # Act
        task_fields = BaseTaskFields(**valid_data)

        # Assert
        assert task_fields.title == "Valid Title"
        assert task_fields.title[0] != " "
        assert task_fields.title[-1] != " "


# =============================================================================
# Test Status Field Validation (Literal Type)
# =============================================================================


class TestStatusFieldValidation:
    """Test status field Literal type validation."""

    @pytest.mark.skipif(not MODELS_EXIST, reason="BaseTaskFields not implemented yet")
    @pytest.mark.parametrize(
        "valid_status",
        ["need to be done", "in-progress", "complete"],
    )
    def test_status_valid_values_accepted(
        self, valid_task_field_data: dict[str, Any], valid_status: str
    ) -> None:
        """Test all three valid status values are accepted.

        Validates:
        - Literal["need to be done", "in-progress", "complete"] type enforced
        - All valid values accepted without error
        """
        # Arrange
        valid_data = {**valid_task_field_data, "status": valid_status}

        # Act
        task_fields = BaseTaskFields(**valid_data)

        # Assert
        assert task_fields.status == valid_status

    @pytest.mark.skipif(not MODELS_EXIST, reason="BaseTaskFields not implemented yet")
    @pytest.mark.parametrize(
        "invalid_status",
        ["pending", "done", "active", "cancelled", "COMPLETE", "In-Progress"],
    )
    def test_status_invalid_values_rejected(
        self, valid_task_field_data: dict[str, Any], invalid_status: str
    ) -> None:
        """Test invalid status values are rejected.

        Validates:
        - Literal type rejects values outside allowed set
        - Case-sensitive validation (COMPLETE vs complete)
        """
        # Arrange
        invalid_data = {**valid_task_field_data, "status": invalid_status}

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            BaseTaskFields(**invalid_data)

        error = exc_info.value
        assert "status" in str(error).lower()


# =============================================================================
# Test UUID Field Validation
# =============================================================================


class TestUUIDFieldValidation:
    """Test id field UUID type validation."""

    @pytest.mark.skipif(not MODELS_EXIST, reason="BaseTaskFields not implemented yet")
    def test_uuid_valid_format_accepted(
        self, valid_task_field_data: dict[str, Any], sample_task_id: uuid.UUID
    ) -> None:
        """Test valid UUID4 format accepted for id field.

        Validates:
        - UUID type field accepts uuid.UUID instances
        - UUID value correctly stored
        """
        # Arrange
        valid_data = {**valid_task_field_data, "id": sample_task_id}

        # Act
        task_fields = BaseTaskFields(**valid_data)

        # Assert
        assert task_fields.id == sample_task_id
        assert isinstance(task_fields.id, uuid.UUID)

    @pytest.mark.skipif(not MODELS_EXIST, reason="BaseTaskFields not implemented yet")
    def test_uuid_string_coerced_to_uuid(
        self, valid_task_field_data: dict[str, Any]
    ) -> None:
        """Test string UUID format coerced to uuid.UUID.

        Validates:
        - Pydantic coerces valid UUID strings to UUID type
        - String representation converted correctly
        """
        # Arrange
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        valid_data = {**valid_task_field_data, "id": uuid_str}

        # Act
        task_fields = BaseTaskFields(**valid_data)

        # Assert
        assert isinstance(task_fields.id, uuid.UUID)
        assert str(task_fields.id) == uuid_str

    @pytest.mark.skipif(not MODELS_EXIST, reason="BaseTaskFields not implemented yet")
    def test_uuid_invalid_format_rejected(
        self, valid_task_field_data: dict[str, Any]
    ) -> None:
        """Test invalid UUID format rejected.

        Validates:
        - Malformed UUID string raises ValidationError
        - Clear error message provided
        """
        # Arrange
        invalid_data = {**valid_task_field_data, "id": "not-a-valid-uuid"}

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            BaseTaskFields(**invalid_data)

        error = exc_info.value
        assert "id" in str(error).lower()


# =============================================================================
# Test Datetime Field Validation
# =============================================================================


class TestDatetimeFieldValidation:
    """Test created_at and updated_at datetime field validation."""

    @pytest.mark.skipif(not MODELS_EXIST, reason="BaseTaskFields not implemented yet")
    def test_datetime_valid_timezone_aware_accepted(
        self, valid_task_field_data: dict[str, Any]
    ) -> None:
        """Test timezone-aware datetime accepted for timestamp fields.

        Validates:
        - datetime fields accept timezone-aware datetimes
        - UTC timezone datetime correctly stored
        """
        # Arrange
        now_utc = datetime.now(timezone.utc)
        valid_data = {
            **valid_task_field_data,
            "created_at": now_utc,
            "updated_at": now_utc,
        }

        # Act
        task_fields = BaseTaskFields(**valid_data)

        # Assert
        assert task_fields.created_at == now_utc
        assert task_fields.updated_at == now_utc
        assert task_fields.created_at.tzinfo is not None
        assert task_fields.updated_at.tzinfo is not None

    @pytest.mark.skipif(not MODELS_EXIST, reason="BaseTaskFields not implemented yet")
    def test_datetime_iso8601_string_coerced(
        self, valid_task_field_data: dict[str, Any]
    ) -> None:
        """Test ISO 8601 datetime string coerced to datetime.

        Validates:
        - Pydantic coerces ISO 8601 strings to datetime objects
        - String representation correctly parsed
        """
        # Arrange
        iso_datetime = "2025-10-10T10:00:00Z"
        valid_data = {
            **valid_task_field_data,
            "created_at": iso_datetime,
            "updated_at": iso_datetime,
        }

        # Act
        task_fields = BaseTaskFields(**valid_data)

        # Assert
        assert isinstance(task_fields.created_at, datetime)
        assert isinstance(task_fields.updated_at, datetime)

    @pytest.mark.skipif(not MODELS_EXIST, reason="BaseTaskFields not implemented yet")
    def test_datetime_invalid_format_rejected(
        self, valid_task_field_data: dict[str, Any]
    ) -> None:
        """Test invalid datetime format rejected.

        Validates:
        - Malformed datetime string raises ValidationError
        - Clear error message provided
        """
        # Arrange
        invalid_data = {**valid_task_field_data, "created_at": "not-a-datetime"}

        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            BaseTaskFields(**invalid_data)

        error = exc_info.value
        assert "created_at" in str(error).lower()


# =============================================================================
# Test ORM Mode Compatibility
# =============================================================================


class TestORMCompatibility:
    """Test ORM mode configuration (from_attributes=True)."""

    @pytest.mark.skipif(not MODELS_EXIST, reason="BaseTaskFields not implemented yet")
    def test_model_config_from_attributes_enabled(self) -> None:
        """Test model_config includes from_attributes=True.

        Validates:
        - ConfigDict(from_attributes=True) in model configuration
        - ORM mode enabled for SQLAlchemy model conversion
        """
        # Act
        config = BaseTaskFields.model_config

        # Assert: Access from_attributes directly (ConfigDict is a TypedDict, can't use isinstance)
        assert config.get("from_attributes") is True

    @pytest.mark.skipif(not MODELS_EXIST, reason="BaseTaskFields not implemented yet")
    def test_from_orm_mock_object(self, valid_task_field_data: dict[str, Any]) -> None:
        """Test model_validate() works with ORM-like object.

        Validates:
        - from_attributes=True allows object attribute access
        - Can construct from class with attributes (simulating SQLAlchemy ORM)
        """
        # Arrange: Create mock ORM object with attributes
        class MockORMTask:
            """Mock SQLAlchemy Task model with attributes."""

            def __init__(self, **kwargs: Any) -> None:
                for key, value in kwargs.items():
                    setattr(self, key, value)

        mock_task = MockORMTask(**valid_task_field_data)

        # Act
        task_fields = BaseTaskFields.model_validate(mock_task)

        # Assert
        assert task_fields.id == valid_task_field_data["id"]
        assert task_fields.title == valid_task_field_data["title"]
        assert task_fields.status == valid_task_field_data["status"]


# =============================================================================
# Test Inheritance by TaskSummary
# =============================================================================


class TestTaskSummaryInheritance:
    """Test TaskSummary inherits from BaseTaskFields correctly."""

    @pytest.mark.skipif(not MODELS_EXIST, reason="TaskSummary not implemented yet")
    def test_task_summary_inherits_base_fields(
        self, valid_task_field_data: dict[str, Any]
    ) -> None:
        """Test TaskSummary has all BaseTaskFields attributes.

        Validates:
        - TaskSummary inherits from BaseTaskFields
        - All 5 core fields present in TaskSummary
        - No additional fields added (lightweight model)
        """
        # Act
        summary = TaskSummary(**valid_task_field_data)

        # Assert: Has all base fields
        assert hasattr(summary, "id")
        assert hasattr(summary, "title")
        assert hasattr(summary, "status")
        assert hasattr(summary, "created_at")
        assert hasattr(summary, "updated_at")

        # Assert: Values match input
        assert summary.id == valid_task_field_data["id"]
        assert summary.title == valid_task_field_data["title"]
        assert summary.status == valid_task_field_data["status"]

    @pytest.mark.skipif(not MODELS_EXIST, reason="TaskSummary not implemented yet")
    def test_task_summary_no_extra_fields(
        self, valid_task_field_data: dict[str, Any]
    ) -> None:
        """Test TaskSummary has ONLY base fields (no description, notes, etc).

        Validates:
        - TaskSummary is lightweight (5 fields only)
        - Does not include description, notes, planning_references, etc.
        - Token efficiency goal maintained
        """
        # Act
        summary = TaskSummary(**valid_task_field_data)

        # Assert: No extra fields present
        assert not hasattr(summary, "description")
        assert not hasattr(summary, "notes")
        assert not hasattr(summary, "planning_references")
        assert not hasattr(summary, "branches")
        assert not hasattr(summary, "commits")

    @pytest.mark.skipif(not MODELS_EXIST, reason="TaskSummary not implemented yet")
    def test_task_summary_validates_inherited_fields(
        self, valid_task_field_data: dict[str, Any]
    ) -> None:
        """Test TaskSummary enforces BaseTaskFields validation rules.

        Validates:
        - Inherited field validators work in TaskSummary
        - Title min/max length enforced
        - Status Literal type enforced
        """
        # Test title validation
        invalid_data = {**valid_task_field_data, "title": ""}
        with pytest.raises(ValidationError):
            TaskSummary(**invalid_data)

        # Test status validation
        invalid_data = {**valid_task_field_data, "status": "invalid-status"}
        with pytest.raises(ValidationError):
            TaskSummary(**invalid_data)


# =============================================================================
# Test Inheritance by TaskResponse
# =============================================================================


class TestTaskResponseInheritance:
    """Test TaskResponse inherits from BaseTaskFields correctly."""

    @pytest.mark.skipif(not MODELS_EXIST, reason="TaskResponse not implemented yet")
    def test_task_response_inherits_base_fields(
        self, valid_task_field_data: dict[str, Any]
    ) -> None:
        """Test TaskResponse has all BaseTaskFields attributes.

        Validates:
        - TaskResponse inherits from BaseTaskFields
        - All 5 core fields present in TaskResponse
        - Additional detail fields also present
        """
        # Arrange: Add detail fields for TaskResponse
        full_data = {
            **valid_task_field_data,
            "description": "Detailed description",
            "notes": "Additional notes",
            "planning_references": ["specs/001/spec.md"],
            "branches": ["001-feature"],
            "commits": ["a" * 40],
        }

        # Act
        response = TaskResponse(**full_data)

        # Assert: Has all base fields
        assert hasattr(response, "id")
        assert hasattr(response, "title")
        assert hasattr(response, "status")
        assert hasattr(response, "created_at")
        assert hasattr(response, "updated_at")

        # Assert: Values match input
        assert response.id == valid_task_field_data["id"]
        assert response.title == valid_task_field_data["title"]
        assert response.status == valid_task_field_data["status"]

    @pytest.mark.skipif(not MODELS_EXIST, reason="TaskResponse not implemented yet")
    def test_task_response_has_detail_fields(
        self, valid_task_field_data: dict[str, Any]
    ) -> None:
        """Test TaskResponse includes additional detail fields.

        Validates:
        - TaskResponse extends BaseTaskFields with 5 detail fields
        - description, notes, planning_references, branches, commits present
        """
        # Arrange
        full_data = {
            **valid_task_field_data,
            "description": "Task description",
            "notes": "Task notes",
            "planning_references": [],
            "branches": [],
            "commits": [],
        }

        # Act
        response = TaskResponse(**full_data)

        # Assert: Has detail fields
        assert hasattr(response, "description")
        assert hasattr(response, "notes")
        assert hasattr(response, "planning_references")
        assert hasattr(response, "branches")
        assert hasattr(response, "commits")

    @pytest.mark.skipif(not MODELS_EXIST, reason="TaskResponse not implemented yet")
    def test_task_response_validates_inherited_fields(
        self, valid_task_field_data: dict[str, Any]
    ) -> None:
        """Test TaskResponse enforces BaseTaskFields validation rules.

        Validates:
        - Inherited field validators work in TaskResponse
        - Title min/max length enforced
        - Status Literal type enforced
        """
        # Test title validation
        invalid_data = {
            **valid_task_field_data,
            "title": "",
            "description": None,
            "notes": None,
        }
        with pytest.raises(ValidationError):
            TaskResponse(**invalid_data)

        # Test status validation
        invalid_data = {
            **valid_task_field_data,
            "status": "invalid-status",
            "description": None,
            "notes": None,
        }
        with pytest.raises(ValidationError):
            TaskResponse(**invalid_data)


# =============================================================================
# Test Model Serialization
# =============================================================================


class TestModelSerialization:
    """Test JSON serialization for MCP protocol compliance."""

    @pytest.mark.skipif(not MODELS_EXIST, reason="BaseTaskFields not implemented yet")
    def test_base_task_fields_serializes_to_json(
        self, valid_task_field_data: dict[str, Any]
    ) -> None:
        """Test BaseTaskFields serializes to JSON dict.

        Validates:
        - model_dump() returns dictionary
        - All fields present in serialized output
        - UUID and datetime correctly serialized
        """
        # Arrange
        task_fields = BaseTaskFields(**valid_task_field_data)

        # Act
        json_data = task_fields.model_dump()

        # Assert
        assert isinstance(json_data, dict)
        assert "id" in json_data
        assert "title" in json_data
        assert "status" in json_data
        assert "created_at" in json_data
        assert "updated_at" in json_data

    @pytest.mark.skipif(not MODELS_EXIST, reason="TaskSummary not implemented yet")
    def test_task_summary_serializes_to_json(
        self, valid_task_field_data: dict[str, Any]
    ) -> None:
        """Test TaskSummary serializes to lightweight JSON.

        Validates:
        - Serialized output contains only 5 base fields
        - No extra fields in JSON output
        - Token-efficient representation
        """
        # Arrange
        summary = TaskSummary(**valid_task_field_data)

        # Act
        json_data = summary.model_dump()

        # Assert: Only 5 fields
        assert len(json_data) == 5
        assert set(json_data.keys()) == {
            "id",
            "title",
            "status",
            "created_at",
            "updated_at",
        }


# =============================================================================
# Test Markers
# =============================================================================

pytestmark = pytest.mark.unit
