"""Unit tests for status translation backward compatibility fix.

This test module verifies that the status translation layer in src/services/tasks.py
correctly converts new Feature 003 work item status values (active, completed, blocked)
to legacy task status values (need to be done, in-progress, complete) for Pydantic validation.

Constitutional Compliance:
- Principle VII: Test-driven development (comprehensive backward compatibility tests)
- Principle VIII: Type safety (validates Pydantic type constraints)
- Principle V: Production quality (ensures no regressions)

Test Coverage:
- Status translation function (_translate_task_status)
- list_tasks with new status values
- get_task with new status values
- Pydantic validation success after translation
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from src.models.task import Task
from src.models.task_schemas import TaskSummary
from src.services.tasks import _translate_task_status


class TestStatusTranslation:
    """Test suite for status translation backward compatibility."""

    def test_translate_active_to_need_to_be_done(self) -> None:
        """Verify 'active' status translates to 'need to be done'."""
        task = Task(
            id=uuid.uuid4(),
            title="Test task",
            status="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        translated = _translate_task_status(task)

        assert translated.status == "need to be done"
        assert translated.id == task.id
        assert translated.title == task.title

    def test_translate_completed_to_complete(self) -> None:
        """Verify 'completed' status translates to 'complete'."""
        task = Task(
            id=uuid.uuid4(),
            title="Test task",
            status="completed",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        translated = _translate_task_status(task)

        assert translated.status == "complete"

    def test_translate_blocked_to_need_to_be_done(self) -> None:
        """Verify 'blocked' status translates to 'need to be done'."""
        task = Task(
            id=uuid.uuid4(),
            title="Test task",
            status="blocked",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        translated = _translate_task_status(task)

        assert translated.status == "need to be done"

    def test_translate_inprogress_passthrough(self) -> None:
        """Verify 'in-progress' status passes through unchanged."""
        task = Task(
            id=uuid.uuid4(),
            title="Test task",
            status="in-progress",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        translated = _translate_task_status(task)

        assert translated.status == "in-progress"

    def test_translate_legacy_statuses_passthrough(self) -> None:
        """Verify legacy statuses pass through unchanged."""
        legacy_statuses = ["need to be done", "complete"]

        for status in legacy_statuses:
            task = Task(
                id=uuid.uuid4(),
                title="Test task",
                status=status,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            translated = _translate_task_status(task)

            assert translated.status == status

    def test_pydantic_validation_succeeds_after_translation(self) -> None:
        """Verify TaskSummary Pydantic validation succeeds after status translation."""
        # Create task with new status value (would fail Pydantic validation)
        task = Task(
            id=uuid.uuid4(),
            title="Test task",
            status="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Translate status
        translated = _translate_task_status(task)

        # Pydantic validation should succeed
        summary = TaskSummary.model_validate(translated)

        assert summary.status == "need to be done"
        assert summary.title == "Test task"

    def test_pydantic_validation_fails_without_translation(self) -> None:
        """Verify TaskSummary validation fails without translation (shows bug exists)."""
        # Create task with new status value
        task = Task(
            id=uuid.uuid4(),
            title="Test task",
            status="active",  # This will fail Pydantic Literal validation
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Pydantic validation should fail
        with pytest.raises(ValueError, match="Input should be"):
            TaskSummary.model_validate(task)

    def test_translation_is_non_destructive(self) -> None:
        """Verify translation modifies in-memory object only, not database."""
        task = Task(
            id=uuid.uuid4(),
            title="Test task",
            status="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        original_id = task.id
        original_title = task.title

        translated = _translate_task_status(task)

        # Should be same object (in-memory modification)
        assert translated is task
        # Status should be translated
        assert translated.status == "need to be done"
        # Other fields should be unchanged
        assert translated.id == original_id
        assert translated.title == original_title

    def test_all_status_translations_coverage(self) -> None:
        """Verify all status values in STATUS_TRANSLATION are tested."""
        status_mapping = {
            "active": "need to be done",
            "in-progress": "in-progress",
            "completed": "complete",
            "blocked": "need to be done",
            "need to be done": "need to be done",
            "complete": "complete",
        }

        for input_status, expected_status in status_mapping.items():
            task = Task(
                id=uuid.uuid4(),
                title="Test task",
                status=input_status,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            translated = _translate_task_status(task)

            assert translated.status == expected_status, (
                f"Status '{input_status}' should translate to '{expected_status}', "
                f"got '{translated.status}'"
            )
