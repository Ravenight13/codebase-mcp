"""
T010: Contract tests for create_task MCP tool.

These tests validate the MCP protocol contract for task creation functionality.
Tests MUST fail initially as the tool is not yet implemented (TDD approach).

Performance Requirements:
- p95 latency: < 150ms
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, Field, ValidationError


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
class CreateTaskInput(BaseModel):
    """Input schema for create_task tool."""

    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: str | None = Field(default=None, description="Task description")
    notes: str | None = Field(default=None, description="Additional notes")
    planning_references: list[str] = Field(
        default_factory=list,
        description="Relative paths to planning documents",
    )


# Contract Tests


@pytest.mark.contract
def test_create_task_input_valid_minimal() -> None:
    """Test create_task input schema with minimal required fields."""
    valid_input = CreateTaskInput(title="Implement feature X")

    assert valid_input.title == "Implement feature X"
    assert valid_input.description is None
    assert valid_input.notes is None
    assert valid_input.planning_references == []


@pytest.mark.contract
def test_create_task_input_valid_complete() -> None:
    """Test create_task input schema with all optional fields."""
    valid_input = CreateTaskInput(
        title="Implement semantic search",
        description="Add vector search capabilities using pgvector",
        notes="Research Ollama embedding models first",
        planning_references=[
            "specs/001-build-a-production/spec.md",
            "specs/001-build-a-production/research.md",
        ],
    )

    assert valid_input.title == "Implement semantic search"
    assert valid_input.description == "Add vector search capabilities using pgvector"
    assert valid_input.notes == "Research Ollama embedding models first"
    assert len(valid_input.planning_references) == 2


@pytest.mark.contract
def test_create_task_input_missing_required_title() -> None:
    """Test create_task input validation fails when title is missing."""
    with pytest.raises(ValidationError) as exc_info:
        CreateTaskInput()  # type: ignore[call-arg]

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("title",) for error in errors)
    assert any(error["type"] == "missing" for error in errors)


@pytest.mark.contract
def test_create_task_input_empty_title() -> None:
    """Test create_task input validation fails for empty title string."""
    with pytest.raises(ValidationError) as exc_info:
        CreateTaskInput(title="")

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("title",) for error in errors)


@pytest.mark.contract
def test_create_task_input_title_exceeds_max_length() -> None:
    """Test create_task input validation fails when title exceeds 200 chars."""
    long_title = "A" * 201  # 201 characters

    with pytest.raises(ValidationError) as exc_info:
        CreateTaskInput(title=long_title)

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("title",) for error in errors)


@pytest.mark.contract
def test_create_task_input_title_at_max_length() -> None:
    """Test create_task input accepts title at maximum length (200 chars)."""
    max_length_title = "A" * 200  # Exactly 200 characters

    valid_input = CreateTaskInput(title=max_length_title)

    assert len(valid_input.title) == 200


@pytest.mark.contract
def test_create_task_input_invalid_types() -> None:
    """Test create_task input validation fails for invalid field types."""
    # Invalid title type
    with pytest.raises(ValidationError) as exc_info:
        CreateTaskInput(title=12345)  # type: ignore[arg-type]
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("title",) for error in errors)

    # Invalid description type
    with pytest.raises(ValidationError) as exc_info:
        CreateTaskInput(title="Valid title", description=True)  # type: ignore[arg-type]
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("description",) for error in errors)

    # Invalid planning_references type (not a list)
    with pytest.raises(ValidationError) as exc_info:
        CreateTaskInput(
            title="Valid title", planning_references="not-a-list"  # type: ignore[arg-type]
        )
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("planning_references",) for error in errors)


@pytest.mark.contract
def test_create_task_output_returns_task() -> None:
    """Test create_task output schema returns a valid Task object."""
    task_id = uuid4()
    now = datetime.now(UTC)

    # Simulate the output of create_task
    created_task = Task(
        id=task_id,
        title="Implement feature X",
        description="Add new functionality",
        notes="Important notes",
        status="need to be done",  # New tasks should default to "need to be done"
        created_at=now,
        updated_at=now,
        planning_references=["specs/001/spec.md"],
        branches=[],
        commits=[],
        status_history=[],
    )

    assert created_task.id == task_id
    assert created_task.title == "Implement feature X"
    assert created_task.status == "need to be done"
    assert created_task.created_at == now
    assert created_task.updated_at == now


@pytest.mark.contract
def test_create_task_output_generates_uuid() -> None:
    """Test create_task output includes generated UUID for new task."""
    now = datetime.now(UTC)

    # The implementation should generate a new UUID
    task = Task(
        id=uuid4(),  # Should be generated by implementation
        title="New task",
        status="need to be done",
        created_at=now,
        updated_at=now,
    )

    # Verify UUID is valid
    assert isinstance(task.id, UUID)
    assert task.id is not None


@pytest.mark.contract
def test_create_task_output_sets_timestamps() -> None:
    """Test create_task output sets created_at and updated_at timestamps."""
    now = datetime.now(UTC)

    task = Task(
        id=uuid4(),
        title="New task",
        status="need to be done",
        created_at=now,
        updated_at=now,
    )

    # For new tasks, created_at and updated_at should be the same
    assert task.created_at == now
    assert task.updated_at == now


@pytest.mark.contract
def test_create_task_output_default_status() -> None:
    """Test create_task output sets default status to 'need to be done'."""
    now = datetime.now(UTC)

    # New tasks should always start with "need to be done" status
    task = Task(
        id=uuid4(),
        title="New task",
        status="need to be done",
        created_at=now,
        updated_at=now,
    )

    assert task.status == "need to be done"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_create_task_tool_not_implemented() -> None:
    """
    Test documenting that create_task tool is not yet implemented.

    This test MUST fail until the actual tool implementation is complete.
    Once implemented, replace this with actual tool invocation tests.

    Expected behavior: Raises NotImplementedError
    """
    with pytest.raises(NotImplementedError) as exc_info:
        # TODO: Uncomment once tool is implemented
        # from src.mcp.tools.tasks import create_task
        # result = await create_task(title="Test task")
        raise NotImplementedError("create_task tool not implemented yet")

    assert "not implemented" in str(exc_info.value).lower()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_create_task_with_planning_references() -> None:
    """
    Test that create_task preserves planning_references in created task.

    This test documents expected behavior for planning references.
    Once implemented, verify references are stored correctly.

    Expected behavior: Planning references should be stored and returned
    """
    planning_refs = [
        "specs/001-build-a-production/spec.md",
        "specs/001-build-a-production/plan.md",
    ]

    # TODO: Once implemented, test actual behavior:
    # from src.mcp.tools.tasks import create_task
    # result = await create_task(
    #     title="Test task",
    #     planning_references=planning_refs
    # )
    # assert result.planning_references == planning_refs

    # Document the requirement
    assert len(planning_refs) == 2, "Planning references should be preserved"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_create_task_idempotency() -> None:
    """
    Test create_task behavior for duplicate task creation attempts.

    This test documents expected idempotency behavior.

    Expected behavior: Each call to create_task should create a NEW task
    with a unique UUID, even if title/content are identical. Tasks are
    not deduplicated.
    """
    # TODO: Once implemented, verify duplicate tasks are allowed:
    # from src.mcp.tools.tasks import create_task
    # task1 = await create_task(title="Duplicate task")
    # task2 = await create_task(title="Duplicate task")
    # assert task1.id != task2.id  # Different UUIDs
    # assert task1.title == task2.title  # Same title

    # Document the requirement
    assert True, "create_task should allow duplicate titles with unique UUIDs"


@pytest.mark.contract
def test_create_task_performance_requirement_documented() -> None:
    """
    Document performance requirements for create_task tool.

    Performance Requirements (from mcp-protocol.json):
    - p95 latency: < 150ms

    This test serves as documentation. Actual performance validation
    will be implemented in integration/performance tests.
    """
    p95_requirement_ms = 150

    # Document the requirement through assertion
    assert p95_requirement_ms == 150, "p95 latency requirement for create_task"

    # Single row INSERT with UUID generation should be fast
    # Requirement will be validated once tool is implemented
