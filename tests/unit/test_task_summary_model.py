"""
Unit tests for TaskSummary Pydantic model validation and serialization.

This test suite validates the lightweight TaskSummary model used for token-efficient
list operations in the list_tasks MCP tool. Following TDD methodology, these tests
are written BEFORE the TaskSummary model implementation.

Tests cover:
- Valid TaskSummary construction with all required fields
- Field validation (title length 1-200, status enum, UUID format)
- JSON serialization via model_dump()
- Construction from SQLAlchemy Task ORM via model_validate()
- Invalid field validation (empty title, invalid status, malformed UUID)
- Timestamp handling and ISO 8601 format validation

Feature: Optimize list_tasks MCP Tool for Token Efficiency
Data Model: /Users/cliffclarke/Claude_Code/codebase-mcp/specs/004-as-an-ai/data-model.md

Constitutional Compliance:
- Principle VII: TDD (tests written before implementation)
- Principle VIII: Type safety (complete type annotations, mypy --strict)
- Principle IV: Performance (TaskSummary achieves 6x token reduction)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
from pydantic import ValidationError

# TDD: Import TaskSummary from task_schemas module (where it's implemented)
from src.models.task_schemas import TaskSummary
from src.models.task import Task as WorkItem


class TestTaskSummaryValidation:
    """Test TaskSummary Pydantic model field validation."""

    def test_valid_task_summary_construction(self) -> None:
        """Test TaskSummary can be constructed with all valid required fields."""
        # Arrange
        task_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        # Act
        summary = TaskSummary(
            id=task_id,
            title="Implement user authentication",
            status="in-progress",
            created_at=now,
            updated_at=now,
        )

        # Assert
        assert summary.id == task_id
        assert summary.title == "Implement user authentication"
        assert summary.status == "in-progress"
        assert summary.created_at == now
        assert summary.updated_at == now

    def test_valid_task_summary_all_statuses(self) -> None:
        """Test TaskSummary accepts all valid status values."""
        task_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        # Test all three valid status values
        valid_statuses = ["need to be done", "in-progress", "complete"]

        for status in valid_statuses:
            summary = TaskSummary(
                id=task_id,
                title="Test task",
                status=status,
                created_at=now,
                updated_at=now,
            )
            assert summary.status == status

    def test_title_length_constraints(self) -> None:
        """Test title field respects min/max length constraints (1-200 chars)."""
        task_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        # Test minimum length (1 character) - should succeed
        summary_min = TaskSummary(
            id=task_id,
            title="A",
            status="in-progress",
            created_at=now,
            updated_at=now,
        )
        assert summary_min.title == "A"

        # Test maximum length (200 characters) - should succeed
        max_title = "A" * 200
        summary_max = TaskSummary(
            id=task_id,
            title=max_title,
            status="in-progress",
            created_at=now,
            updated_at=now,
        )
        assert summary_max.title == max_title
        assert len(summary_max.title) == 200

    def test_title_empty_string_validation_fails(self) -> None:
        """Test TaskSummary rejects empty title."""
        task_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            TaskSummary(
                id=task_id,
                title="",
                status="in-progress",
                created_at=now,
                updated_at=now,
            )

        # Verify error mentions title field
        error_msg = str(exc_info.value)
        assert "title" in error_msg.lower()

    def test_title_exceeds_max_length_validation_fails(self) -> None:
        """Test TaskSummary rejects title longer than 200 characters."""
        task_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        # 201 characters exceeds maximum
        too_long_title = "A" * 201

        with pytest.raises(ValidationError) as exc_info:
            TaskSummary(
                id=task_id,
                title=too_long_title,
                status="in-progress",
                created_at=now,
                updated_at=now,
            )

        # Verify error mentions title field and length constraint
        error_msg = str(exc_info.value)
        assert "title" in error_msg.lower()

    def test_invalid_status_validation_fails(self) -> None:
        """Test TaskSummary rejects invalid status values."""
        task_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        invalid_statuses = ["pending", "cancelled", "archived", "INVALID", ""]

        for invalid_status in invalid_statuses:
            with pytest.raises(ValidationError) as exc_info:
                TaskSummary(
                    id=task_id,
                    title="Test task",
                    status=invalid_status,  # type: ignore
                    created_at=now,
                    updated_at=now,
                )

            # Verify error mentions status field
            error_msg = str(exc_info.value)
            assert "status" in error_msg.lower()

    def test_invalid_uuid_format_validation_fails(self) -> None:
        """Test TaskSummary rejects malformed UUID."""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValidationError) as exc_info:
            TaskSummary(
                id="not-a-valid-uuid",  # type: ignore
                title="Test task",
                status="in-progress",
                created_at=now,
                updated_at=now,
            )

        # Verify error mentions id field or UUID validation
        error_msg = str(exc_info.value).lower()
        assert "id" in error_msg or "uuid" in error_msg

    def test_missing_required_fields_validation_fails(self) -> None:
        """Test TaskSummary rejects construction with missing required fields."""
        # Test missing title
        with pytest.raises(ValidationError) as exc_info:
            TaskSummary(
                id=uuid.uuid4(),
                status="in-progress",  # type: ignore
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        assert "title" in str(exc_info.value).lower()

        # Test missing status
        with pytest.raises(ValidationError) as exc_info:
            TaskSummary(
                id=uuid.uuid4(),
                title="Test task",  # type: ignore
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        assert "status" in str(exc_info.value).lower()

        # Test missing created_at
        with pytest.raises(ValidationError) as exc_info:
            TaskSummary(
                id=uuid.uuid4(),
                title="Test task",
                status="in-progress",  # type: ignore
                updated_at=datetime.now(timezone.utc),
            )
        assert "created_at" in str(exc_info.value).lower()

        # Test missing updated_at
        with pytest.raises(ValidationError) as exc_info:
            TaskSummary(
                id=uuid.uuid4(),
                title="Test task",
                status="in-progress",  # type: ignore
                created_at=datetime.now(timezone.utc),
            )
        assert "updated_at" in str(exc_info.value).lower()


class TestTaskSummarySerialization:
    """Test TaskSummary JSON serialization behavior."""

    def test_model_dump_json_serialization(self) -> None:
        """Test TaskSummary serializes to JSON correctly via model_dump()."""
        # Arrange
        task_id = uuid.uuid4()
        created_at = datetime(2025, 10, 10, 10, 0, 0, tzinfo=timezone.utc)
        updated_at = datetime(2025, 10, 10, 15, 30, 0, tzinfo=timezone.utc)

        summary = TaskSummary(
            id=task_id,
            title="Implement user authentication",
            status="in-progress",
            created_at=created_at,
            updated_at=updated_at,
        )

        # Act
        data = summary.model_dump()

        # Assert - verify all fields present and correct types
        assert data["id"] == task_id
        assert data["title"] == "Implement user authentication"
        assert data["status"] == "in-progress"
        assert data["created_at"] == created_at
        assert data["updated_at"] == updated_at

        # Verify no extra fields present (should only have 5 core fields)
        expected_fields = {"id", "title", "status", "created_at", "updated_at"}
        assert set(data.keys()) == expected_fields

    def test_model_dump_mode_json(self) -> None:
        """Test TaskSummary serializes with mode='json' for MCP transport."""
        # Arrange
        task_id = uuid.uuid4()
        created_at = datetime(2025, 10, 10, 10, 0, 0, tzinfo=timezone.utc)
        updated_at = datetime(2025, 10, 10, 15, 30, 0, tzinfo=timezone.utc)

        summary = TaskSummary(
            id=task_id,
            title="Implement user authentication",
            status="in-progress",
            created_at=created_at,
            updated_at=updated_at,
        )

        # Act
        data = summary.model_dump(mode="json")

        # Assert - UUID and datetime should be serialized as strings
        assert isinstance(data["id"], str)
        assert data["id"] == str(task_id)
        assert isinstance(data["created_at"], str)
        assert isinstance(data["updated_at"], str)

        # Verify ISO 8601 format for timestamps
        assert data["created_at"] == "2025-10-10T10:00:00Z"
        assert data["updated_at"] == "2025-10-10T15:30:00Z"


class TestTaskSummaryFromORM:
    """Test TaskSummary construction from SQLAlchemy Task ORM objects."""

    def test_model_validate_from_task_orm(self) -> None:
        """Test TaskSummary can be constructed from SQLAlchemy Task via model_validate()."""
        # Arrange - Create a SQLAlchemy Task (WorkItem) instance
        task_id = uuid.uuid4()
        created_at = datetime(2025, 10, 10, 10, 0, 0, tzinfo=timezone.utc)
        updated_at = datetime(2025, 10, 10, 15, 30, 0, tzinfo=timezone.utc)

        task_orm = WorkItem(
            id=task_id,
            title="Implement user authentication",
            description="Add JWT-based authentication with refresh tokens",
            notes="Consider OAuth2 integration",
            status="in-progress",
            created_at=created_at,
            updated_at=updated_at,
        )

        # Act - Convert ORM to TaskSummary
        summary = TaskSummary.model_validate(task_orm)

        # Assert - Verify only core fields are present (no description/notes)
        assert summary.id == task_id
        assert summary.title == "Implement user authentication"
        assert summary.status == "in-progress"
        assert summary.created_at == created_at
        assert summary.updated_at == updated_at

        # Verify TaskSummary does NOT include description or notes
        assert not hasattr(summary, "description")
        assert not hasattr(summary, "notes")

    def test_model_validate_preserves_task_status(self) -> None:
        """Test TaskSummary preserves exact status value from Task ORM."""
        task_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        # Test all three valid legacy statuses
        for status in ["need to be done", "in-progress", "complete"]:
            task_orm = WorkItem(
                id=task_id,
                title="Test task",
                status=status,
                created_at=now,
                updated_at=now,
            )

            summary = TaskSummary.model_validate(task_orm)
            assert summary.status == status

    def test_model_validate_handles_timezone_aware_timestamps(self) -> None:
        """Test TaskSummary correctly handles timezone-aware datetime objects from ORM."""
        task_id = uuid.uuid4()
        # Use UTC timezone explicitly
        created_at_utc = datetime(2025, 10, 10, 10, 0, 0, tzinfo=timezone.utc)
        updated_at_utc = datetime(2025, 10, 10, 15, 30, 0, tzinfo=timezone.utc)

        task_orm = WorkItem(
            id=task_id,
            title="Test timezone handling",
            status="in-progress",
            created_at=created_at_utc,
            updated_at=updated_at_utc,
        )

        summary = TaskSummary.model_validate(task_orm)

        # Assert timestamps are preserved with timezone info
        assert summary.created_at == created_at_utc
        assert summary.updated_at == updated_at_utc
        assert summary.created_at.tzinfo == timezone.utc
        assert summary.updated_at.tzinfo == timezone.utc


class TestTaskSummaryConfigDict:
    """Test TaskSummary Pydantic ConfigDict settings."""

    def test_from_attributes_enabled(self) -> None:
        """Test TaskSummary has from_attributes=True for ORM mode."""
        # This is verified implicitly by the model_validate tests above,
        # but we explicitly check the model_config here for clarity
        assert TaskSummary.model_config.get("from_attributes") is True

    def test_json_schema_extra_example(self) -> None:
        """Test TaskSummary has a valid example in json_schema_extra."""
        # Verify json_schema_extra is present and has example data
        json_schema_extra = TaskSummary.model_config.get("json_schema_extra")
        assert json_schema_extra is not None
        assert "example" in json_schema_extra

        # Verify example contains all 5 required fields
        example: dict[str, Any] = json_schema_extra["example"]
        assert "id" in example
        assert "title" in example
        assert "status" in example
        assert "created_at" in example
        assert "updated_at" in example

        # Verify example has valid status value
        assert example["status"] in ["need to be done", "in-progress", "complete"]


class TestTaskSummaryTokenEfficiency:
    """Test TaskSummary token footprint characteristics."""

    def test_field_count_is_five(self) -> None:
        """Test TaskSummary has exactly 5 fields for token efficiency."""
        # Arrange
        task_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        summary = TaskSummary(
            id=task_id,
            title="Test task",
            status="in-progress",
            created_at=now,
            updated_at=now,
        )

        # Act
        data = summary.model_dump()

        # Assert - Should have exactly 5 fields (no more, no less)
        assert len(data) == 5
        expected_fields = {"id", "title", "status", "created_at", "updated_at"}
        assert set(data.keys()) == expected_fields

    def test_no_optional_verbose_fields_present(self) -> None:
        """Test TaskSummary excludes verbose optional fields (description, notes, etc.)."""
        # Arrange
        task_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        summary = TaskSummary(
            id=task_id,
            title="Test task",
            status="in-progress",
            created_at=now,
            updated_at=now,
        )

        # Act
        data = summary.model_dump()

        # Assert - Verify verbose fields are NOT present
        verbose_fields = [
            "description",
            "notes",
            "planning_references",
            "branches",
            "commits",
        ]
        for field in verbose_fields:
            assert field not in data


# ============================================================================
# Test Markers
# ============================================================================

pytestmark = pytest.mark.unit
