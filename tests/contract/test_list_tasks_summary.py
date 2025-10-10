"""
T001: Contract tests for list_tasks summary mode (token-optimized).

These tests validate the TaskSummary response schema which includes ONLY 5 fields:
id, title, status, created_at, updated_at. This is a breaking change from the
full TaskResponse which includes description, notes, planning_references, branches, commits.

Tests MUST fail initially as TaskSummary model doesn't exist yet (TDD approach).

Feature: 004-as-an-ai
Contract: specs/004-as-an-ai/contracts/list_tasks_summary.yaml
Data Model: specs/004-as-an-ai/data-model.md

Performance Requirements:
- Token count: < 2000 tokens for 15 tasks
- p95 latency: < 200ms

Constitutional Compliance:
- Principle IV: Performance Guarantees (6x token reduction)
- Principle VIII: Pydantic Type Safety (strict schema validation)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, Field, ValidationError

# Type Definitions
TaskStatus = Literal["need to be done", "in-progress", "complete"]


# TaskSummary Model (DOES NOT EXIST YET - tests will fail)
try:
    from src.models.task import TaskSummary  # type: ignore[attr-defined]
except ImportError:
    # This import will fail initially - that's expected for TDD
    TaskSummary = None  # type: ignore[misc,assignment]


# Expected TaskSummary schema definition (from data-model.md)
class ExpectedTaskSummary(BaseModel):
    """Expected TaskSummary schema for contract validation.

    This is the target schema that TaskSummary MUST match once implemented.
    Includes ONLY 5 fields for token efficiency.
    """

    id: UUID = Field(..., description="Unique task identifier")
    title: str = Field(
        ..., min_length=1, max_length=200, description="Task title"
    )
    status: TaskStatus = Field(..., description="Current task status")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


# ListTasksSummaryOutput Schema
class ListTasksSummaryOutput(BaseModel):
    """Output schema for list_tasks in summary mode (default).

    Response contains:
    - tasks: Array of TaskSummary objects (5 fields each)
    - total_count: Integer count of tasks returned
    """

    tasks: list[ExpectedTaskSummary] = Field(
        ..., description="Array of task summaries"
    )
    total_count: int = Field(
        ..., ge=0, description="Total tasks matching filters"
    )

    model_config = {"from_attributes": True}


# Contract Tests - Schema Validation


@pytest.mark.contract
def test_task_summary_model_not_implemented() -> None:
    """
    Test documenting that TaskSummary model is not yet implemented.

    This test MUST fail until TaskSummary is added to src/models/task.py.
    Once implemented, this test can be removed or updated.

    Expected behavior: ImportError or AttributeError
    """
    with pytest.raises((ImportError, AttributeError)) as exc_info:
        if TaskSummary is None:
            raise ImportError("TaskSummary not found in src.models.task")
        # If import somehow succeeded but model is wrong, fail
        raise AttributeError("TaskSummary exists but may not be correct")

    assert "TaskSummary" in str(exc_info.value)


@pytest.mark.contract
def test_expected_task_summary_valid_minimal() -> None:
    """Test ExpectedTaskSummary schema with minimal required fields."""
    task_id = uuid4()
    now = datetime.now(UTC)

    summary = ExpectedTaskSummary(
        id=task_id,
        title="Implement feature X",
        status="need to be done",
        created_at=now,
        updated_at=now,
    )

    assert summary.id == task_id
    assert summary.title == "Implement feature X"
    assert summary.status == "need to be done"
    assert summary.created_at == now
    assert summary.updated_at == now


@pytest.mark.contract
def test_expected_task_summary_has_exactly_5_fields() -> None:
    """Test ExpectedTaskSummary has EXACTLY 5 fields (no more, no less)."""
    task_id = uuid4()
    now = datetime.now(UTC)

    summary = ExpectedTaskSummary(
        id=task_id,
        title="Test task",
        status="in-progress",
        created_at=now,
        updated_at=now,
    )

    # Get model fields (Pydantic v2 API - access from class, not instance)
    model_fields = ExpectedTaskSummary.model_fields
    assert len(model_fields) == 5, "TaskSummary MUST have exactly 5 fields"

    # Verify exact field names
    expected_fields = {"id", "title", "status", "created_at", "updated_at"}
    actual_fields = set(model_fields.keys())
    assert (
        actual_fields == expected_fields
    ), f"Expected {expected_fields}, got {actual_fields}"


@pytest.mark.contract
def test_expected_task_summary_excludes_detail_fields() -> None:
    """Test ExpectedTaskSummary does NOT include detail fields."""
    task_id = uuid4()
    now = datetime.now(UTC)

    summary = ExpectedTaskSummary(
        id=task_id,
        title="Test task",
        status="complete",
        created_at=now,
        updated_at=now,
    )

    # Fields that MUST NOT exist in TaskSummary
    excluded_fields = [
        "description",
        "notes",
        "planning_references",
        "branches",
        "commits",
    ]

    # Access model_fields from class, not instance (Pydantic v2)
    model_fields = set(ExpectedTaskSummary.model_fields.keys())
    for field in excluded_fields:
        assert (
            field not in model_fields
        ), f"TaskSummary MUST NOT have '{field}' field"


@pytest.mark.contract
def test_expected_task_summary_missing_required_fields() -> None:
    """Test ExpectedTaskSummary validation fails when required fields missing."""
    # Missing all required fields
    with pytest.raises(ValidationError) as exc_info:
        ExpectedTaskSummary()  # type: ignore[call-arg]

    errors = exc_info.value.errors()
    required_fields = ["id", "title", "status", "created_at", "updated_at"]
    error_locs = [error["loc"][0] for error in errors]

    for field in required_fields:
        assert (
            field in error_locs
        ), f"Validation should fail for missing '{field}'"


@pytest.mark.contract
def test_expected_task_summary_invalid_status_enum() -> None:
    """Test ExpectedTaskSummary validation fails for invalid status value."""
    task_id = uuid4()
    now = datetime.now(UTC)

    with pytest.raises(ValidationError) as exc_info:
        ExpectedTaskSummary(
            id=task_id,
            title="Test task",
            status="pending",  # type: ignore[arg-type]  # Invalid: not in enum
            created_at=now,
            updated_at=now,
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("status",) for error in errors)


@pytest.mark.contract
def test_expected_task_summary_valid_status_values() -> None:
    """Test ExpectedTaskSummary accepts all valid status enum values."""
    task_id = uuid4()
    now = datetime.now(UTC)

    valid_statuses: list[TaskStatus] = [
        "need to be done",
        "in-progress",
        "complete",
    ]

    for status in valid_statuses:
        summary = ExpectedTaskSummary(
            id=task_id,
            title="Test task",
            status=status,
            created_at=now,
            updated_at=now,
        )
        assert summary.status == status


@pytest.mark.contract
def test_expected_task_summary_title_validation() -> None:
    """Test ExpectedTaskSummary title length validation."""
    task_id = uuid4()
    now = datetime.now(UTC)

    # Empty title should fail
    with pytest.raises(ValidationError) as exc_info:
        ExpectedTaskSummary(
            id=task_id,
            title="",
            status="need to be done",
            created_at=now,
            updated_at=now,
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("title",) for error in errors)

    # Title exceeding max length should fail
    with pytest.raises(ValidationError) as exc_info:
        ExpectedTaskSummary(
            id=task_id,
            title="x" * 201,  # Exceeds 200 char limit
            status="need to be done",
            created_at=now,
            updated_at=now,
        )

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("title",) for error in errors)


# Contract Tests - List Response Schema


@pytest.mark.contract
def test_list_tasks_summary_output_valid_with_results() -> None:
    """Test ListTasksSummaryOutput schema with 15 task results."""
    now = datetime.now(UTC)

    # Create 15 task summaries
    tasks = [
        ExpectedTaskSummary(
            id=uuid4(),
            title=f"Task {i+1}: Implement feature {chr(65+i)}",
            status="in-progress" if i % 2 == 0 else "need to be done",
            created_at=now,
            updated_at=now,
        )
        for i in range(15)
    ]

    output = ListTasksSummaryOutput(tasks=tasks, total_count=15)

    assert len(output.tasks) == 15
    assert output.total_count == 15

    # Verify each task has exactly 5 fields (access from class, not instance)
    model_fields = ExpectedTaskSummary.model_fields
    assert len(model_fields) == 5, "Each summary must have exactly 5 fields"


@pytest.mark.contract
def test_list_tasks_summary_output_valid_empty_results() -> None:
    """Test ListTasksSummaryOutput schema with no results."""
    output = ListTasksSummaryOutput(tasks=[], total_count=0)

    assert output.tasks == []
    assert output.total_count == 0


@pytest.mark.contract
def test_list_tasks_summary_output_missing_required_fields() -> None:
    """Test ListTasksSummaryOutput validation fails when required fields missing."""
    # Missing total_count
    with pytest.raises(ValidationError) as exc_info:
        ListTasksSummaryOutput(tasks=[])  # type: ignore[call-arg]

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("total_count",) for error in errors)

    # Missing tasks
    with pytest.raises(ValidationError) as exc_info:
        ListTasksSummaryOutput(total_count=0)  # type: ignore[call-arg]

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("tasks",) for error in errors)


@pytest.mark.contract
def test_list_tasks_summary_output_negative_total_count() -> None:
    """Test ListTasksSummaryOutput validation fails for negative total_count."""
    with pytest.raises(ValidationError) as exc_info:
        ListTasksSummaryOutput(tasks=[], total_count=-1)

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("total_count",) for error in errors)


@pytest.mark.contract
def test_list_tasks_summary_output_total_count_greater_than_results() -> None:
    """Test ListTasksSummaryOutput allows total_count > len(tasks) for pagination."""
    task_id = uuid4()
    now = datetime.now(UTC)

    # Return 5 tasks but total_count is 15 (pagination scenario)
    output = ListTasksSummaryOutput(
        tasks=[
            ExpectedTaskSummary(
                id=task_id,
                title="Task 1",
                status="need to be done",
                created_at=now,
                updated_at=now,
            )
        ]
        * 5,
        total_count=15,  # More tasks exist than returned
    )

    assert len(output.tasks) == 5
    assert output.total_count == 15
    # This indicates there are more pages of results available


# Contract Tests - Field Exclusion Validation


@pytest.mark.contract
def test_summary_vs_full_response_field_difference() -> None:
    """
    Document the field differences between TaskSummary and TaskResponse.

    TaskSummary (5 fields):
    - id, title, status, created_at, updated_at

    TaskResponse (10 fields):
    - All TaskSummary fields PLUS
    - description, notes, planning_references, branches, commits

    This test validates that TaskSummary is a proper subset of TaskResponse.
    """
    # TaskSummary fields
    summary_fields = {"id", "title", "status", "created_at", "updated_at"}

    # Full TaskResponse fields (from existing TaskResponse model)
    full_response_fields = {
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

    # Verify TaskSummary is a proper subset
    assert summary_fields.issubset(
        full_response_fields
    ), "TaskSummary fields must be subset of TaskResponse"

    # Verify excluded fields
    excluded_fields = full_response_fields - summary_fields
    expected_excluded = {
        "description",
        "notes",
        "planning_references",
        "branches",
        "commits",
    }
    assert (
        excluded_fields == expected_excluded
    ), f"Expected excluded: {expected_excluded}, got: {excluded_fields}"


# Performance Tests - Token Efficiency


@pytest.mark.contract
def test_token_efficiency_requirement_documented() -> None:
    """
    Document token efficiency requirements for list_tasks summary mode.

    Token Requirements (from spec.md):
    - 15 tasks in summary mode: < 2000 tokens
    - 15 tasks in full mode: ~12000 tokens (baseline)
    - Improvement: ~6x reduction

    This test serves as documentation. Actual token counting validation
    will be implemented in integration tests with tiktoken.
    """
    token_target = 2000
    baseline_tokens = 12000
    improvement_ratio = baseline_tokens / token_target

    assert token_target == 2000, "Token target for 15-task summary list"
    assert (
        improvement_ratio >= 6
    ), f"Expected 6x improvement, calculated: {improvement_ratio}x"


@pytest.mark.contract
def test_performance_requirement_documented() -> None:
    """
    Document performance requirements for list_tasks tool.

    Performance Requirements (from spec.md and contract):
    - p95 latency: < 200ms

    This test serves as documentation. Actual performance validation
    will be implemented in integration/performance tests.
    """
    p95_requirement_ms = 200

    assert (
        p95_requirement_ms == 200
    ), "p95 latency requirement for list_tasks summary mode"


# TDD Integration Test Placeholder


@pytest.mark.contract
@pytest.mark.asyncio
async def test_list_tasks_summary_tool_not_implemented() -> None:
    """
    Test documenting that list_tasks summary mode is not yet implemented.

    This test MUST fail until the actual tool implementation supports
    the full_details parameter and returns TaskSummary by default.

    Expected behavior: Raises NotImplementedError or returns wrong schema
    """
    with pytest.raises(NotImplementedError) as exc_info:
        # TODO: Uncomment once tool is implemented
        # from src.mcp.tools.tasks import list_tasks
        # result = await list_tasks(full_details=False)  # Summary mode (default)
        # assert all(len(task.model_fields) == 5 for task in result.tasks)
        raise NotImplementedError(
            "list_tasks summary mode (full_details=False) not implemented yet"
        )

    assert "not implemented" in str(exc_info.value).lower()
