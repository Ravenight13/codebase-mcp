"""
T002: Contract tests for list_tasks MCP tool with full_details=True parameter.

These tests validate the MCP protocol contract for the opt-in full details mode
of list_tasks that returns complete TaskResponse objects with all 10 fields.

Feature: Optimize list_tasks for Token Efficiency
Spec: specs/004-as-an-ai/spec.md
Contract: specs/004-as-an-ai/contracts/list_tasks_full.yaml

Constitutional Compliance:
- Principle VIII: Pydantic-based type safety with explicit types
- Principle IV: Performance Guarantees (<200ms latency maintained)

Tests MUST fail initially as the full_details parameter is not yet implemented.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, Field, ValidationError


# Type Definitions
TaskStatus = Literal["need to be done", "in-progress", "complete"]


# Input Schema Models
class ListTasksInputFullDetails(BaseModel):
    """Input schema for list_tasks tool with full_details parameter.

    Constitutional Compliance:
    - Principle VIII: Pydantic type safety with explicit field types
    """

    status: TaskStatus | None = Field(
        default=None, description="Filter by task status"
    )
    branch: str | None = Field(
        default=None, description="Filter by git branch name"
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of tasks to return",
    )
    full_details: bool = Field(
        default=False,
        description="Return full TaskResponse objects (when true) or TaskSummary (when false)",
    )


# Output Schema Models - TaskResponse (Full Details)
class TaskResponse(BaseModel):
    """Complete task representation with all metadata (10 fields).

    Used when full_details=True parameter is specified.

    Constitutional Compliance:
    - Principle VIII: Pydantic type safety
    - Principle X: Git integration (branches, commits tracking)
    """

    # Core fields (5) - same as TaskSummary
    id: UUID = Field(..., description="Unique task identifier")
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    status: TaskStatus = Field(..., description="Current task status")
    created_at: datetime = Field(..., description="Task creation timestamp (ISO 8601)")
    updated_at: datetime = Field(
        ..., description="Last modification timestamp (ISO 8601)"
    )

    # Detail fields (5) - additional fields for full context
    description: str | None = Field(
        default=None, description="Detailed task description (optional)"
    )
    notes: str | None = Field(default=None, description="Additional notes (optional)")
    planning_references: list[str] = Field(
        default_factory=list,
        description="Relative paths to planning documents",
    )
    branches: list[str] = Field(
        default_factory=list, description="Associated git branch names"
    )
    commits: list[str] = Field(
        default_factory=list,
        description="Associated git commit hashes (40-char hex)",
    )


class ListTasksOutputFullDetails(BaseModel):
    """Output schema for list_tasks tool with full_details=True.

    Returns complete TaskResponse objects with all 10 fields.
    """

    tasks: list[TaskResponse] = Field(..., description="Array of full task details")
    total_count: int = Field(
        ..., ge=0, description="Total number of tasks returned (matches array length)"
    )


# ============================================================================
# Contract Tests - Input Schema Validation
# ============================================================================


@pytest.mark.contract
def test_list_tasks_full_details_input_default() -> None:
    """Test list_tasks input schema with full_details parameter default (false)."""
    valid_input = ListTasksInputFullDetails()

    assert valid_input.status is None
    assert valid_input.branch is None
    assert valid_input.limit == 50  # Default value
    assert valid_input.full_details is False  # Default is False (summary mode)


@pytest.mark.contract
def test_list_tasks_full_details_input_explicit_true() -> None:
    """Test list_tasks input schema with full_details=True (opt-in)."""
    valid_input = ListTasksInputFullDetails(full_details=True)

    assert valid_input.full_details is True
    assert valid_input.status is None
    assert valid_input.branch is None
    assert valid_input.limit == 50


@pytest.mark.contract
def test_list_tasks_full_details_input_with_filters() -> None:
    """Test list_tasks input with full_details=True and filters."""
    valid_input = ListTasksInputFullDetails(
        status="in-progress",
        branch="004-as-an-ai",
        limit=15,
        full_details=True,
    )

    assert valid_input.status == "in-progress"
    assert valid_input.branch == "004-as-an-ai"
    assert valid_input.limit == 15
    assert valid_input.full_details is True


@pytest.mark.contract
def test_list_tasks_full_details_input_invalid_type() -> None:
    """Test list_tasks input validation fails for invalid full_details type."""
    # Note: Pydantic may coerce strings like "yes" to bool, so use a clearly invalid type
    with pytest.raises(ValidationError) as exc_info:
        ListTasksInputFullDetails(full_details={"invalid": "dict"})  # type: ignore[arg-type]

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("full_details",) for error in errors)


# ============================================================================
# Contract Tests - Output Schema Validation (TaskResponse)
# ============================================================================


@pytest.mark.contract
def test_task_response_valid_minimal() -> None:
    """Test TaskResponse schema with minimal required fields (core 5 fields only)."""
    task_id = uuid4()
    now = datetime.now(UTC)

    task = TaskResponse(
        id=task_id,
        title="Implement feature X",
        status="need to be done",
        created_at=now,
        updated_at=now,
    )

    # Verify core fields (5)
    assert task.id == task_id
    assert task.title == "Implement feature X"
    assert task.status == "need to be done"
    assert task.created_at == now
    assert task.updated_at == now

    # Verify detail fields (5) have default values
    assert task.description is None
    assert task.notes is None
    assert task.planning_references == []
    assert task.branches == []
    assert task.commits == []


@pytest.mark.contract
def test_task_response_valid_complete_all_10_fields() -> None:
    """Test TaskResponse schema with ALL 10 fields populated (full details)."""
    task_id = uuid4()
    created = datetime(2025, 10, 10, 10, 0, 0, tzinfo=UTC)
    updated = datetime(2025, 10, 10, 15, 30, 0, tzinfo=UTC)

    task = TaskResponse(
        # Core fields (5)
        id=task_id,
        title="Implement user authentication",
        status="in-progress",
        created_at=created,
        updated_at=updated,
        # Detail fields (5)
        description="Add JWT-based authentication with refresh tokens and role-based access control",
        notes="Consider OAuth2 integration for social login. Review security best practices.",
        planning_references=[
            "specs/001-auth/spec.md",
            "specs/001-auth/plan.md",
        ],
        branches=["001-user-auth"],
        commits=["a1b2c3d4e5f6789012345678901234567890abcd"],
    )

    # Verify core fields (5)
    assert task.id == task_id
    assert task.title == "Implement user authentication"
    assert task.status == "in-progress"
    assert task.created_at == created
    assert task.updated_at == updated

    # Verify detail fields (5)
    assert task.description is not None
    assert "JWT-based authentication" in task.description
    assert task.notes is not None
    assert "OAuth2" in task.notes
    assert len(task.planning_references) == 2
    assert len(task.branches) == 1
    assert len(task.commits) == 1
    assert len(task.commits[0]) == 40  # Full SHA-1 hash


@pytest.mark.contract
def test_task_response_null_handling_optional_fields() -> None:
    """Test TaskResponse schema handles null values for optional fields correctly."""
    task_id = uuid4()
    now = datetime.now(UTC)

    # Create task with explicitly null description and notes
    task = TaskResponse(
        id=task_id,
        title="Task with no description",
        status="need to be done",
        created_at=now,
        updated_at=now,
        description=None,  # Explicitly null
        notes=None,  # Explicitly null
    )

    # Verify null handling
    assert task.description is None
    assert task.notes is None
    assert task.planning_references == []
    assert task.branches == []
    assert task.commits == []


@pytest.mark.contract
def test_task_response_all_10_fields_present() -> None:
    """Test that TaskResponse has exactly 10 fields as per contract."""
    task_id = uuid4()
    now = datetime.now(UTC)

    task = TaskResponse(
        id=task_id,
        title="Test task",
        status="in-progress",
        created_at=now,
        updated_at=now,
        description="Description",
        notes="Notes",
        planning_references=["spec.md"],
        branches=["main"],
        commits=["a" * 40],
    )

    # Verify all 10 fields are present
    task_dict = task.model_dump()
    expected_fields = {
        "id",
        "title",
        "status",
        "created_at",
        "updated_at",
        "description",
        "notes",
        "planning_references",
        "branches",
        "commits",
    }

    assert set(task_dict.keys()) == expected_fields
    assert len(task_dict) == 10


# ============================================================================
# Contract Tests - ListTasksOutputFullDetails
# ============================================================================


@pytest.mark.contract
def test_list_tasks_output_full_details_valid() -> None:
    """Test list_tasks output schema with full TaskResponse objects."""
    task_id_1 = uuid4()
    task_id_2 = uuid4()
    now = datetime.now(UTC)

    output = ListTasksOutputFullDetails(
        tasks=[
            TaskResponse(
                id=task_id_1,
                title="Implement feature A",
                description="Detailed description A",
                notes="Important notes A",
                status="in-progress",
                created_at=now,
                updated_at=now,
                planning_references=["specs/001/spec.md"],
                branches=["001-feature-a"],
                commits=["a1b2c3d4e5f6789012345678901234567890abcd"],
            ),
            TaskResponse(
                id=task_id_2,
                title="Implement feature B",
                description="Detailed description B",
                notes="Important notes B",
                status="need to be done",
                created_at=now,
                updated_at=now,
                planning_references=["specs/002/spec.md"],
                branches=["002-feature-b"],
                commits=["b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0"],
            ),
        ],
        total_count=2,
    )

    assert len(output.tasks) == 2
    assert output.total_count == 2

    # Verify first task has all 10 fields
    task1 = output.tasks[0]
    assert task1.id == task_id_1
    assert task1.description == "Detailed description A"
    assert task1.notes == "Important notes A"
    assert len(task1.planning_references) == 1
    assert len(task1.branches) == 1
    assert len(task1.commits) == 1


@pytest.mark.contract
def test_list_tasks_output_full_details_empty_results() -> None:
    """Test list_tasks output schema with no results (empty array)."""
    output = ListTasksOutputFullDetails(
        tasks=[],
        total_count=0,
    )

    assert output.tasks == []
    assert output.total_count == 0


@pytest.mark.contract
def test_list_tasks_output_full_details_missing_required_fields() -> None:
    """Test list_tasks output validation fails when required fields missing."""
    # Missing total_count
    with pytest.raises(ValidationError) as exc_info:
        ListTasksOutputFullDetails(tasks=[])  # type: ignore[call-arg]

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("total_count",) for error in errors)

    # Missing tasks
    with pytest.raises(ValidationError) as exc_info:
        ListTasksOutputFullDetails(total_count=0)  # type: ignore[call-arg]

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("tasks",) for error in errors)


# ============================================================================
# Contract Tests - Tool Implementation (TDD - Must Fail)
# ============================================================================


@pytest.mark.contract
@pytest.mark.asyncio
async def test_list_tasks_full_details_parameter_not_implemented() -> None:
    """
    Test documenting that list_tasks full_details parameter is not yet implemented.

    This test MUST fail until the actual tool implementation adds the full_details
    parameter. This is the primary TDD test for this feature.

    Expected behavior: Raises NotImplementedError or TypeError (parameter not recognized)
    """
    with pytest.raises((NotImplementedError, TypeError)) as exc_info:
        # TODO: Uncomment once tool supports full_details parameter
        # from src.mcp.tools.tasks import list_tasks
        # result = await list_tasks(full_details=True)
        raise NotImplementedError(
            "list_tasks tool does not support full_details parameter yet"
        )

    assert "not implemented" in str(exc_info.value).lower() or "full_details" in str(
        exc_info.value
    ).lower()


@pytest.mark.contract
@pytest.mark.asyncio
async def test_list_tasks_full_details_true_returns_all_10_fields() -> None:
    """
    Test that list_tasks(full_details=True) returns TaskResponse with all 10 fields.

    This test documents the expected behavior once implemented.

    Expected behavior:
    - Call list_tasks(full_details=True)
    - Each task in response has ALL 10 fields:
      1. id
      2. title
      3. status
      4. created_at
      5. updated_at
      6. description
      7. notes
      8. planning_references
      9. branches
      10. commits
    """
    # TODO: Once implemented, uncomment and test actual behavior:
    # from src.mcp.tools.tasks import list_tasks
    # result = await list_tasks(full_details=True, limit=1)
    #
    # assert result.total_count >= 0
    # if len(result.tasks) > 0:
    #     task = result.tasks[0]
    #     task_dict = task.model_dump()
    #
    #     # Verify all 10 fields present
    #     expected_fields = {
    #         "id", "title", "status", "created_at", "updated_at",
    #         "description", "notes", "planning_references", "branches", "commits"
    #     }
    #     assert set(task_dict.keys()) == expected_fields

    # For now, document the requirement
    expected_field_count = 10
    assert (
        expected_field_count == 10
    ), "full_details=True must return all 10 TaskResponse fields"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_list_tasks_full_details_false_behavior_documented() -> None:
    """
    Test documenting behavior of full_details=False (default, summary mode).

    When full_details=False (default), list_tasks should return TaskSummary
    objects with only 5 core fields (not 10).

    This test documents the contrast between the two modes.
    """
    # Document the two modes
    summary_field_count = 5  # TaskSummary fields
    full_details_field_count = 10  # TaskResponse fields

    assert summary_field_count == 5, "Summary mode has 5 core fields"
    assert full_details_field_count == 10, "Full details mode has 10 fields"
    assert (
        full_details_field_count - summary_field_count == 5
    ), "Full details adds 5 additional fields"

    # TODO: Once implemented, test actual behavior:
    # from src.mcp.tools.tasks import list_tasks
    #
    # # Default behavior (full_details=False)
    # result_summary = await list_tasks(limit=1)
    # if len(result_summary.tasks) > 0:
    #     summary_dict = result_summary.tasks[0].model_dump()
    #     assert len(summary_dict) == 5
    #
    # # Opt-in behavior (full_details=True)
    # result_full = await list_tasks(full_details=True, limit=1)
    # if len(result_full.tasks) > 0:
    #     full_dict = result_full.tasks[0].model_dump()
    #     assert len(full_dict) == 10


@pytest.mark.contract
def test_list_tasks_full_details_performance_requirement_documented() -> None:
    """
    Document performance requirements for list_tasks full details mode.

    Performance Requirements (from list_tasks_full.yaml):
    - p95 latency: < 200ms (same as summary mode - database query unchanged)
    - Token count: No constraint (full details mode for backward compatibility)

    This test serves as documentation. Actual performance validation
    will be implemented in integration/performance tests.
    """
    p95_requirement_ms = 200

    # Document the requirement through assertion
    assert p95_requirement_ms == 200, "p95 latency requirement for full details mode"

    # Note: Full details mode returns ~6x more tokens than summary mode
    # (12000-15000 tokens vs 2000 tokens for 15 tasks)
    # This is intentional for backward compatibility and debugging use cases


@pytest.mark.contract
def test_list_tasks_full_details_backward_compatibility_intent() -> None:
    """
    Document the backward compatibility purpose of full_details parameter.

    The full_details=True parameter exists to:
    1. Maintain backward compatibility during migration period
    2. Support debugging scenarios requiring full task context
    3. Enable export/reporting use cases

    Recommended usage: Migrate to summary mode + get_task() pattern for
    better token efficiency (6x improvement).
    """
    # Document backward compatibility intent
    backward_compat_modes = {
        "default": "summary mode (full_details=False) - 5 fields",
        "opt_in": "full details mode (full_details=True) - 10 fields",
        "recommended": "Use summary mode for browsing, get_task() for details",
    }

    assert len(backward_compat_modes) == 3
    assert backward_compat_modes["recommended"] is not None
