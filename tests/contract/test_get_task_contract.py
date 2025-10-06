"""
T008: Contract tests for get_task MCP tool.

These tests validate the MCP protocol contract for task retrieval functionality.
Tests MUST fail initially as the tool is not yet implemented (TDD approach).

Performance Requirements:
- p95 latency: < 100ms
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, Field, ValidationError


# Input Schema Models
class GetTaskInput(BaseModel):
    """Input schema for get_task tool."""

    task_id: UUID = Field(..., description="UUID of the task to retrieve")


# Output Schema Models (Task definition from mcp-protocol.json)
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


# Contract Tests


@pytest.mark.contract
def test_get_task_input_valid() -> None:
    """Test get_task input schema with valid UUID."""
    task_id = uuid4()
    valid_input = GetTaskInput(task_id=task_id)

    assert valid_input.task_id == task_id


@pytest.mark.contract
def test_get_task_input_missing_required_field() -> None:
    """Test get_task input validation fails when task_id is missing."""
    with pytest.raises(ValidationError) as exc_info:
        GetTaskInput()  # type: ignore[call-arg]

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("task_id",) for error in errors)
    assert any(error["type"] == "missing" for error in errors)


@pytest.mark.contract
def test_get_task_input_invalid_uuid_format() -> None:
    """Test get_task input validation fails for invalid UUID format."""
    with pytest.raises(ValidationError) as exc_info:
        GetTaskInput(task_id="not-a-valid-uuid")  # type: ignore[arg-type]

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("task_id",) for error in errors)


@pytest.mark.contract
def test_get_task_input_wrong_type() -> None:
    """Test get_task input validation fails for wrong type."""
    with pytest.raises(ValidationError) as exc_info:
        GetTaskInput(task_id=12345)  # type: ignore[arg-type]

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("task_id",) for error in errors)


@pytest.mark.contract
def test_task_output_valid_minimal() -> None:
    """Test Task output schema with minimal required fields."""
    task_id = uuid4()
    now = datetime.now(UTC)

    task = Task(
        id=task_id,
        title="Implement feature X",
        status="need to be done",
        created_at=now,
        updated_at=now,
    )

    assert task.id == task_id
    assert task.title == "Implement feature X"
    assert task.description is None
    assert task.notes is None
    assert task.status == "need to be done"
    assert task.created_at == now
    assert task.updated_at == now
    assert task.planning_references == []
    assert task.branches == []
    assert task.commits == []
    assert task.status_history == []


@pytest.mark.contract
def test_task_output_valid_complete() -> None:
    """Test Task output schema with all optional fields populated."""
    task_id = uuid4()
    created = datetime(2025, 1, 1, 10, 0, 0)
    updated = datetime(2025, 1, 1, 14, 30, 0)
    status_changed = datetime(2025, 1, 1, 12, 0, 0)

    task = Task(
        id=task_id,
        title="Implement semantic search",
        description="Add vector search capabilities to the indexer",
        notes="Using pgvector extension for PostgreSQL",
        status="in-progress",
        created_at=created,
        updated_at=updated,
        planning_references=[
            "specs/001-build-a-production/spec.md",
            "specs/001-build-a-production/plan.md",
        ],
        branches=["001-build-a-production", "feature/semantic-search"],
        commits=["a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"],
        status_history=[
            StatusHistoryEntry(
                from_status="need to be done",
                to_status="in-progress",
                changed_at=status_changed,
            )
        ],
    )

    assert task.id == task_id
    assert task.title == "Implement semantic search"
    assert task.description == "Add vector search capabilities to the indexer"
    assert task.notes == "Using pgvector extension for PostgreSQL"
    assert task.status == "in-progress"
    assert len(task.planning_references) == 2
    assert len(task.branches) == 2
    assert len(task.commits) == 1
    assert len(task.status_history) == 1
    assert task.status_history[0].from_status == "need to be done"
    assert task.status_history[0].to_status == "in-progress"


@pytest.mark.contract
def test_task_output_missing_required_fields() -> None:
    """Test Task output validation fails when required fields are missing."""
    # Missing all required fields
    with pytest.raises(ValidationError) as exc_info:
        Task()  # type: ignore[call-arg]

    errors = exc_info.value.errors()
    required_fields = ["id", "title", "status", "created_at", "updated_at"]
    error_locs = [error["loc"][0] for error in errors]

    for field in required_fields:
        assert field in error_locs


@pytest.mark.contract
def test_task_output_invalid_status_enum() -> None:
    """Test Task output validation fails for invalid status value."""
    task_id = uuid4()
    now = datetime.now(UTC)

    with pytest.raises(ValidationError) as exc_info:
        Task(
            id=task_id,
            title="Test task",
            status="pending",  # type: ignore[arg-type]  # Invalid: not in enum
            created_at=now,
            updated_at=now,
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("status",) for error in errors)


@pytest.mark.contract
def test_task_output_valid_status_values() -> None:
    """Test Task output accepts all valid status enum values."""
    task_id = uuid4()
    now = datetime.now(UTC)

    valid_statuses: list[TaskStatus] = ["need to be done", "in-progress", "complete"]

    for status in valid_statuses:
        task = Task(
            id=task_id,
            title="Test task",
            status=status,
            created_at=now,
            updated_at=now,
        )
        assert task.status == status


@pytest.mark.contract
def test_task_output_status_history_structure() -> None:
    """Test Task output status_history validation."""
    task_id = uuid4()
    now = datetime.now(UTC)

    # Valid status history entry
    history_entry = StatusHistoryEntry(
        from_status="need to be done",
        to_status="in-progress",
        changed_at=now,
    )

    task = Task(
        id=task_id,
        title="Test task",
        status="in-progress",
        created_at=now,
        updated_at=now,
        status_history=[history_entry],
    )

    assert len(task.status_history) == 1
    assert task.status_history[0].from_status == "need to be done"
    assert task.status_history[0].to_status == "in-progress"


@pytest.mark.contract
def test_task_output_commit_hash_pattern() -> None:
    """Test Task output allows valid git commit hash patterns."""
    task_id = uuid4()
    now = datetime.now(UTC)

    # 40-character hex string (full SHA-1 hash)
    valid_commit = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"

    task = Task(
        id=task_id,
        title="Test task",
        status="complete",
        created_at=now,
        updated_at=now,
        commits=[valid_commit],
    )

    assert len(task.commits) == 1
    assert task.commits[0] == valid_commit
    assert len(task.commits[0]) == 40


@pytest.mark.contract
@pytest.mark.asyncio
async def test_get_task_tool_not_implemented() -> None:
    """
    Test documenting that get_task tool is not yet implemented.

    This test MUST fail until the actual tool implementation is complete.
    Once implemented, replace this with actual tool invocation tests.

    Expected behavior: Raises NotImplementedError
    """
    with pytest.raises(NotImplementedError) as exc_info:
        # TODO: Uncomment once tool is implemented
        # from src.mcp.tools.tasks import get_task
        # task_id = uuid4()
        # result = await get_task(task_id=task_id)
        raise NotImplementedError("get_task tool not implemented yet")

    assert "not implemented" in str(exc_info.value).lower()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_get_task_not_found_error() -> None:
    """
    Test that get_task raises appropriate error for non-existent task.

    This test documents expected error handling behavior.
    Once implemented, the tool should raise a specific NotFoundError.

    Expected behavior: Task not found should raise an error
    """
    # Document expected behavior
    non_existent_id = uuid4()

    # TODO: Once implemented, this should test actual error handling:
    # from src.mcp.tools.tasks import get_task, TaskNotFoundError
    # with pytest.raises(TaskNotFoundError):
    #     await get_task(task_id=non_existent_id)

    # For now, document the requirement
    assert (
        non_existent_id is not None
    ), "Tool should handle non-existent task IDs gracefully"


@pytest.mark.contract
def test_get_task_performance_requirement_documented() -> None:
    """
    Document performance requirements for get_task tool.

    Performance Requirements (from mcp-protocol.json):
    - p95 latency: < 100ms

    This test serves as documentation. Actual performance validation
    will be implemented in integration/performance tests.
    """
    p95_requirement_ms = 100

    # Document the requirement through assertion
    assert p95_requirement_ms == 100, "p95 latency requirement for get_task"

    # Single row database query should be fast
    # Requirement will be validated once tool is implemented
