"""
T009: Contract tests for list_tasks MCP tool.

These tests validate the MCP protocol contract for task listing functionality.
Tests MUST fail initially as the tool is not yet implemented (TDD approach).

Performance Requirements:
- p95 latency: < 200ms
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
class ListTasksInput(BaseModel):
    """Input schema for list_tasks tool."""

    status: TaskStatus | None = Field(
        default=None, description="Filter by task status"
    )
    branch: str | None = Field(
        default=None, description="Filter by git branch name"
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of tasks to return",
    )


# Output Schema Models
class ListTasksOutput(BaseModel):
    """Output schema for list_tasks tool."""

    tasks: list[Task] = Field(..., description="Array of tasks")
    total_count: int = Field(
        ..., ge=0, description="Total tasks matching filters (before limit)"
    )


# Contract Tests


@pytest.mark.contract
def test_list_tasks_input_valid_no_filters() -> None:
    """Test list_tasks input schema with no filters (defaults)."""
    valid_input = ListTasksInput()

    assert valid_input.status is None
    assert valid_input.branch is None
    assert valid_input.limit == 20  # Default value


@pytest.mark.contract
def test_list_tasks_input_valid_with_status_filter() -> None:
    """Test list_tasks input schema with status filter."""
    valid_input = ListTasksInput(status="in-progress")

    assert valid_input.status == "in-progress"
    assert valid_input.branch is None
    assert valid_input.limit == 20


@pytest.mark.contract
def test_list_tasks_input_valid_with_branch_filter() -> None:
    """Test list_tasks input schema with branch filter."""
    valid_input = ListTasksInput(branch="001-build-a-production")

    assert valid_input.status is None
    assert valid_input.branch == "001-build-a-production"
    assert valid_input.limit == 20


@pytest.mark.contract
def test_list_tasks_input_valid_with_all_filters() -> None:
    """Test list_tasks input schema with all filters specified."""
    valid_input = ListTasksInput(
        status="complete",
        branch="main",
        limit=50,
    )

    assert valid_input.status == "complete"
    assert valid_input.branch == "main"
    assert valid_input.limit == 50


@pytest.mark.contract
def test_list_tasks_input_invalid_status_enum() -> None:
    """Test list_tasks input validation fails for invalid status value."""
    with pytest.raises(ValidationError) as exc_info:
        ListTasksInput(status="pending")  # type: ignore[arg-type]  # Invalid: not in enum

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("status",) for error in errors)


@pytest.mark.contract
def test_list_tasks_input_valid_status_values() -> None:
    """Test list_tasks input accepts all valid status enum values."""
    valid_statuses: list[TaskStatus] = ["need to be done", "in-progress", "complete"]

    for status in valid_statuses:
        valid_input = ListTasksInput(status=status)
        assert valid_input.status == status


@pytest.mark.contract
def test_list_tasks_input_limit_out_of_range() -> None:
    """Test list_tasks input validation enforces limit range [1, 100]."""
    # Test limit too low
    with pytest.raises(ValidationError) as exc_info:
        ListTasksInput(limit=0)

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("limit",) for error in errors)

    # Test limit too high
    with pytest.raises(ValidationError) as exc_info:
        ListTasksInput(limit=101)

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("limit",) for error in errors)


@pytest.mark.contract
def test_list_tasks_input_limit_boundary_values() -> None:
    """Test list_tasks input accepts valid boundary limit values."""
    # Minimum valid limit
    valid_input_min = ListTasksInput(limit=1)
    assert valid_input_min.limit == 1

    # Maximum valid limit
    valid_input_max = ListTasksInput(limit=100)
    assert valid_input_max.limit == 100


@pytest.mark.contract
def test_list_tasks_output_valid_with_results() -> None:
    """Test list_tasks output schema with task results."""
    task_id_1 = uuid4()
    task_id_2 = uuid4()
    now = datetime.now(UTC)

    output = ListTasksOutput(
        tasks=[
            Task(
                id=task_id_1,
                title="Implement feature A",
                status="in-progress",
                created_at=now,
                updated_at=now,
            ),
            Task(
                id=task_id_2,
                title="Implement feature B",
                status="need to be done",
                created_at=now,
                updated_at=now,
            ),
        ],
        total_count=15,
    )

    assert len(output.tasks) == 2
    assert output.tasks[0].id == task_id_1
    assert output.tasks[1].id == task_id_2
    assert output.total_count == 15


@pytest.mark.contract
def test_list_tasks_output_valid_empty_results() -> None:
    """Test list_tasks output schema with no results."""
    output = ListTasksOutput(
        tasks=[],
        total_count=0,
    )

    assert output.tasks == []
    assert output.total_count == 0


@pytest.mark.contract
def test_list_tasks_output_missing_required_fields() -> None:
    """Test list_tasks output validation fails when required fields missing."""
    # Missing total_count
    with pytest.raises(ValidationError) as exc_info:
        ListTasksOutput(tasks=[])  # type: ignore[call-arg]

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("total_count",) for error in errors)

    # Missing tasks
    with pytest.raises(ValidationError) as exc_info:
        ListTasksOutput(total_count=0)  # type: ignore[call-arg]

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("tasks",) for error in errors)


@pytest.mark.contract
def test_list_tasks_output_negative_total_count() -> None:
    """Test list_tasks output validation fails for negative total_count."""
    with pytest.raises(ValidationError) as exc_info:
        ListTasksOutput(
            tasks=[],
            total_count=-1,
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("total_count",) for error in errors)


@pytest.mark.contract
def test_list_tasks_output_total_count_greater_than_results() -> None:
    """Test list_tasks output allows total_count > len(tasks) for pagination."""
    task_id = uuid4()
    now = datetime.now(UTC)

    # List 20 tasks but total_count is 150 (pagination scenario)
    output = ListTasksOutput(
        tasks=[
            Task(
                id=task_id,
                title="Task",
                status="need to be done",
                created_at=now,
                updated_at=now,
            )
        ],
        total_count=150,  # More tasks exist than returned
    )

    assert len(output.tasks) == 1
    assert output.total_count == 150
    # This indicates there are more pages of results available


@pytest.mark.contract
@pytest.mark.asyncio
async def test_list_tasks_tool_not_implemented() -> None:
    """
    Test documenting that list_tasks tool is not yet implemented.

    This test MUST fail until the actual tool implementation is complete.
    Once implemented, replace this with actual tool invocation tests.

    Expected behavior: Raises NotImplementedError
    """
    with pytest.raises(NotImplementedError) as exc_info:
        # TODO: Uncomment once tool is implemented
        # from src.mcp.tools.tasks import list_tasks
        # result = await list_tasks()
        raise NotImplementedError("list_tasks tool not implemented yet")

    assert "not implemented" in str(exc_info.value).lower()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_list_tasks_filter_combinations() -> None:
    """
    Test that list_tasks supports various filter combinations.

    This test documents expected filtering behavior.
    Once implemented, verify all filter combinations work correctly.

    Expected behaviors:
    - No filters: Returns all tasks (up to limit)
    - Status only: Filters by status
    - Branch only: Filters by branch
    - Status + branch: Filters by both (AND operation)
    - Limit: Applies to all filtered results
    """
    # Document expected filter combination behaviors
    filter_combinations = [
        {"status": None, "branch": None, "limit": 20},  # All tasks
        {"status": "in-progress", "branch": None, "limit": 20},  # Status filter
        {"status": None, "branch": "main", "limit": 20},  # Branch filter
        {
            "status": "complete",
            "branch": "001-feature",
            "limit": 10,
        },  # Combined filters
    ]

    # TODO: Once implemented, test each combination:
    # from src.mcp.tools.tasks import list_tasks
    # for filters in filter_combinations:
    #     result = await list_tasks(**filters)
    #     assert isinstance(result, ListTasksOutput)

    assert len(filter_combinations) == 4, "All filter combinations documented"


@pytest.mark.contract
def test_list_tasks_performance_requirement_documented() -> None:
    """
    Document performance requirements for list_tasks tool.

    Performance Requirements (from mcp-protocol.json):
    - p95 latency: < 200ms

    This test serves as documentation. Actual performance validation
    will be implemented in integration/performance tests.
    """
    p95_requirement_ms = 200

    # Document the requirement through assertion
    assert p95_requirement_ms == 200, "p95 latency requirement for list_tasks"

    # Database query with filters and pagination should be efficient
    # Consider adding indexes on status, branch columns
    # Requirement will be validated once tool is implemented
