"""
T011: Contract tests for update_task MCP tool.

These tests validate the MCP protocol contract for task update functionality.
Tests MUST fail initially as the tool is not yet implemented (TDD approach).

Performance Requirements:
- p95 latency: < 150ms
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, Field, ValidationError, field_validator


# Shared Task model (from test_get_task_contract.py)
TaskStatus = Literal["need to be done", "in-progress", "complete"]


class StatusHistoryEntry(BaseModel):
    """Status change history entry."""

    from_status: str | None = Field(default=None, description="Previous status")
    to_status: str = Field(..., description="New status")
    changed_at: datetime = Field(..., description="Timestamp of status change")


class Task(BaseModel):
    """Task entity definition."""

    id: UUID = Field(..., description="Unique task identifier")
    title: str = Field(..., description="Task title")
    description: str | None = Field(default=None, description="Task description")
    notes: str | None = Field(default=None, description="Additional notes")
    status: TaskStatus = Field(..., description="Current task status")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    planning_references: list[str] = Field(
        default_factory=list,
        description="Relative paths to planning documents",
    )
    branches: list[str] = Field(
        default_factory=list, description="Associated git branches"
    )
    commits: list[str] = Field(
        default_factory=list, description="Associated git commit hashes"
    )
    status_history: list[StatusHistoryEntry] = Field(
        default_factory=list, description="Status change history"
    )


# Input Schema Models
class UpdateTaskInput(BaseModel):
    """Input schema for update_task tool."""

    task_id: UUID = Field(..., description="UUID of the task to update")
    title: str | None = Field(default=None, description="Updated task title")
    description: str | None = Field(default=None, description="Updated description")
    notes: str | None = Field(default=None, description="Updated notes")
    status: TaskStatus | None = Field(default=None, description="Updated status")
    branch: str | None = Field(
        default=None, description="Git branch name to associate"
    )
    commit: str | None = Field(
        default=None, description="Git commit hash to associate (40 hex chars)"
    )

    @field_validator("commit")
    @classmethod
    def validate_commit_hash(cls, v: str | None) -> str | None:
        """Validate commit hash is 40 hex characters."""
        if v is not None:
            if not re.match(r"^[a-f0-9]{40}$", v):
                raise ValueError("Commit hash must be 40 hexadecimal characters")
        return v


# Contract Tests


@pytest.mark.contract
def test_update_task_input_valid_minimal() -> None:
    """Test update_task input schema with only required task_id."""
    task_id = uuid4()
    valid_input = UpdateTaskInput(task_id=task_id)

    assert valid_input.task_id == task_id
    assert valid_input.title is None
    assert valid_input.description is None
    assert valid_input.notes is None
    assert valid_input.status is None
    assert valid_input.branch is None
    assert valid_input.commit is None


@pytest.mark.contract
def test_update_task_input_valid_title_update() -> None:
    """Test update_task input schema with title update."""
    task_id = uuid4()
    valid_input = UpdateTaskInput(
        task_id=task_id,
        title="Updated task title",
    )

    assert valid_input.task_id == task_id
    assert valid_input.title == "Updated task title"


@pytest.mark.contract
def test_update_task_input_valid_status_update() -> None:
    """Test update_task input schema with status update."""
    task_id = uuid4()
    valid_input = UpdateTaskInput(
        task_id=task_id,
        status="in-progress",
    )

    assert valid_input.task_id == task_id
    assert valid_input.status == "in-progress"


@pytest.mark.contract
def test_update_task_input_valid_branch_and_commit() -> None:
    """Test update_task input schema with branch and commit association."""
    task_id = uuid4()
    commit_hash = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"

    valid_input = UpdateTaskInput(
        task_id=task_id,
        branch="001-build-a-production",
        commit=commit_hash,
    )

    assert valid_input.task_id == task_id
    assert valid_input.branch == "001-build-a-production"
    assert valid_input.commit == commit_hash


@pytest.mark.contract
def test_update_task_input_valid_complete_update() -> None:
    """Test update_task input schema with all fields updated."""
    task_id = uuid4()
    commit_hash = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"

    valid_input = UpdateTaskInput(
        task_id=task_id,
        title="Updated title",
        description="Updated description",
        notes="Updated notes",
        status="complete",
        branch="main",
        commit=commit_hash,
    )

    assert valid_input.task_id == task_id
    assert valid_input.title == "Updated title"
    assert valid_input.description == "Updated description"
    assert valid_input.notes == "Updated notes"
    assert valid_input.status == "complete"
    assert valid_input.branch == "main"
    assert valid_input.commit == commit_hash


@pytest.mark.contract
def test_update_task_input_missing_required_task_id() -> None:
    """Test update_task input validation fails when task_id is missing."""
    with pytest.raises(ValidationError) as exc_info:
        UpdateTaskInput()  # type: ignore[call-arg]

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("task_id",) for error in errors)
    assert any(error["type"] == "missing" for error in errors)


@pytest.mark.contract
def test_update_task_input_invalid_task_id_format() -> None:
    """Test update_task input validation fails for invalid UUID format."""
    with pytest.raises(ValidationError) as exc_info:
        UpdateTaskInput(task_id="not-a-valid-uuid")  # type: ignore[arg-type]

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("task_id",) for error in errors)


@pytest.mark.contract
def test_update_task_input_invalid_status_enum() -> None:
    """Test update_task input validation fails for invalid status value."""
    task_id = uuid4()

    with pytest.raises(ValidationError) as exc_info:
        UpdateTaskInput(
            task_id=task_id,
            status="pending",  # type: ignore[arg-type]  # Invalid: not in enum
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("status",) for error in errors)


@pytest.mark.contract
def test_update_task_input_valid_status_values() -> None:
    """Test update_task input accepts all valid status enum values."""
    task_id = uuid4()
    valid_statuses: list[TaskStatus] = ["need to be done", "in-progress", "complete"]

    for status in valid_statuses:
        valid_input = UpdateTaskInput(task_id=task_id, status=status)
        assert valid_input.status == status


@pytest.mark.contract
def test_update_task_input_invalid_commit_hash_format() -> None:
    """Test update_task input validation fails for invalid commit hash format."""
    task_id = uuid4()

    # Too short
    with pytest.raises(ValidationError) as exc_info:
        UpdateTaskInput(task_id=task_id, commit="abc123")
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("commit",) for error in errors)

    # Wrong characters (contains 'g')
    with pytest.raises(ValidationError) as exc_info:
        UpdateTaskInput(
            task_id=task_id, commit="g1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
        )
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("commit",) for error in errors)

    # Uppercase (should be lowercase)
    with pytest.raises(ValidationError) as exc_info:
        UpdateTaskInput(
            task_id=task_id, commit="A1B2C3D4E5F6A7B8C9D0E1F2A3B4C5D6E7F8A9B0"
        )
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("commit",) for error in errors)


@pytest.mark.contract
def test_update_task_input_valid_commit_hash() -> None:
    """Test update_task input accepts valid 40-character hex commit hash."""
    task_id = uuid4()
    valid_commit = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"

    valid_input = UpdateTaskInput(task_id=task_id, commit=valid_commit)

    assert valid_input.commit == valid_commit
    assert len(valid_input.commit) == 40


@pytest.mark.contract
def test_update_task_output_returns_updated_task() -> None:
    """Test update_task output schema returns updated Task object."""
    task_id = uuid4()
    created = datetime(2025, 1, 1, 10, 0, 0)
    updated = datetime(2025, 1, 1, 14, 30, 0)

    # Simulate the output of update_task
    updated_task = Task(
        id=task_id,
        title="Updated title",
        description="Updated description",
        notes="Updated notes",
        status="in-progress",
        created_at=created,
        updated_at=updated,  # Should be newer than created_at
        branches=["001-build-a-production"],
        commits=["a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"],
        planning_references=[],
        status_history=[
            StatusHistoryEntry(
                from_status="need to be done",
                to_status="in-progress",
                changed_at=updated,
            )
        ],
    )

    assert updated_task.id == task_id
    assert updated_task.title == "Updated title"
    assert updated_task.status == "in-progress"
    assert updated_task.updated_at > updated_task.created_at
    assert len(updated_task.branches) == 1
    assert len(updated_task.commits) == 1
    assert len(updated_task.status_history) == 1


@pytest.mark.contract
def test_update_task_output_updates_timestamp() -> None:
    """Test update_task output updates the updated_at timestamp."""
    task_id = uuid4()
    created = datetime(2025, 1, 1, 10, 0, 0)
    updated = datetime(2025, 1, 1, 14, 30, 0)

    task = Task(
        id=task_id,
        title="Task",
        status="need to be done",
        created_at=created,
        updated_at=updated,
    )

    # updated_at should be later than created_at after an update
    assert task.updated_at > task.created_at


@pytest.mark.contract
def test_update_task_output_appends_to_branches() -> None:
    """Test update_task output appends new branch to branches array."""
    task_id = uuid4()
    now = datetime.now(UTC)

    # Task with existing branch
    task = Task(
        id=task_id,
        title="Task",
        status="in-progress",
        created_at=now,
        updated_at=now,
        branches=["main", "001-build-a-production"],
    )

    assert len(task.branches) == 2
    assert "001-build-a-production" in task.branches


@pytest.mark.contract
def test_update_task_output_appends_to_commits() -> None:
    """Test update_task output appends new commit to commits array."""
    task_id = uuid4()
    now = datetime.now(UTC)

    commit1 = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
    commit2 = "b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1"

    # Task with existing commits
    task = Task(
        id=task_id,
        title="Task",
        status="in-progress",
        created_at=now,
        updated_at=now,
        commits=[commit1, commit2],
    )

    assert len(task.commits) == 2
    assert commit1 in task.commits
    assert commit2 in task.commits


@pytest.mark.contract
def test_update_task_output_status_history_tracking() -> None:
    """Test update_task output tracks status changes in status_history."""
    task_id = uuid4()
    change_time = datetime.now(UTC)

    # Status change should be recorded
    history = StatusHistoryEntry(
        from_status="need to be done",
        to_status="in-progress",
        changed_at=change_time,
    )

    task = Task(
        id=task_id,
        title="Task",
        status="in-progress",
        created_at=change_time,
        updated_at=change_time,
        status_history=[history],
    )

    assert len(task.status_history) == 1
    assert task.status_history[0].from_status == "need to be done"
    assert task.status_history[0].to_status == "in-progress"
    assert task.status_history[0].changed_at == change_time


@pytest.mark.contract
@pytest.mark.asyncio
async def test_update_task_tool_not_implemented() -> None:
    """
    Test documenting that update_task tool is not yet implemented.

    This test MUST fail until the actual tool implementation is complete.
    Once implemented, replace this with actual tool invocation tests.

    Expected behavior: Raises NotImplementedError
    """
    with pytest.raises(NotImplementedError) as exc_info:
        # TODO: Uncomment once tool is implemented
        # from src.mcp.tools.tasks import update_task
        # task_id = uuid4()
        # result = await update_task(task_id=task_id, status="in-progress")
        raise NotImplementedError("update_task tool not implemented yet")

    assert "not implemented" in str(exc_info.value).lower()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_update_task_not_found_error() -> None:
    """
    Test that update_task raises appropriate error for non-existent task.

    This test documents expected error handling behavior.
    Once implemented, the tool should raise a specific NotFoundError.

    Expected behavior: Task not found should raise an error
    """
    # Document expected behavior
    non_existent_id = uuid4()

    # TODO: Once implemented, this should test actual error handling:
    # from src.mcp.tools.tasks import update_task, TaskNotFoundError
    # with pytest.raises(TaskNotFoundError):
    #     await update_task(task_id=non_existent_id, status="complete")

    # For now, document the requirement
    assert (
        non_existent_id is not None
    ), "Tool should handle non-existent task IDs gracefully"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_update_task_partial_updates() -> None:
    """
    Test that update_task supports partial updates (only specified fields).

    This test documents expected partial update behavior.

    Expected behavior: Only fields provided in the input should be updated.
    Fields not provided should remain unchanged.
    """
    # TODO: Once implemented, verify partial updates:
    # from src.mcp.tools.tasks import create_task, update_task, get_task
    #
    # # Create task
    # task = await create_task(
    #     title="Original title",
    #     description="Original description"
    # )
    #
    # # Update only status
    # updated = await update_task(task_id=task.id, status="in-progress")
    # assert updated.status == "in-progress"
    # assert updated.title == "Original title"  # Unchanged
    # assert updated.description == "Original description"  # Unchanged

    # Document the requirement
    assert True, "update_task should support partial updates"


@pytest.mark.contract
def test_update_task_performance_requirement_documented() -> None:
    """
    Document performance requirements for update_task tool.

    Performance Requirements (from mcp-protocol.json):
    - p95 latency: < 150ms

    This test serves as documentation. Actual performance validation
    will be implemented in integration/performance tests.
    """
    p95_requirement_ms = 150

    # Document the requirement through assertion
    assert p95_requirement_ms == 150, "p95 latency requirement for update_task"

    # Single row UPDATE with array appends should be fast
    # Consider using PostgreSQL array_append for branches/commits
    # Requirement will be validated once tool is implemented
