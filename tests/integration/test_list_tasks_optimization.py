"""Integration test for list_tasks token efficiency optimization (Feature 004).

Tests verify:
- PR-001: list_tasks with 15 tasks returns <2000 tokens
- Token efficiency meets ~6x reduction target from 12,000+ baseline

TDD Compliance:
- Test MUST FAIL initially - current list_tasks returns full TaskResponse
- Expected failure: token_count > 2000 (likely ~12,000+ tokens)
- Test will pass after implementing TaskSummary response format

Constitutional Compliance:
- Principle IV: Performance Guarantees (token efficiency)
- Principle VII: Test-Driven Development (failing test first)
- Principle VIII: Pydantic Type Safety (mypy --strict compliance)
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, AsyncGenerator

import pytest

from src.database import get_session_factory

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for tests."""
    async with get_session_factory()() as session:
        yield session


@pytest.fixture
async def sample_tasks(db_session: AsyncSession) -> list[dict[str, Any]]:
    """Create 15 test tasks with realistic data.

    Creates tasks with:
    - Realistic titles (~50 characters each)
    - Long descriptions (~600 characters each)
    - Additional notes (~150 characters each)
    - Planning references

    This data structure simulates real-world task complexity to validate
    token efficiency improvements.

    Returns:
        List of 15 task dictionaries with id, title, status, etc.
    """
    # Import service function, not MCP tool
    from src.models import TaskCreate, TaskResponse
    from src.services import create_task

    tasks: list[dict[str, Any]] = []

    async with get_session_factory()() as db:
        for i in range(15):
            # Create task with realistic data using service
            task_data = TaskCreate(
                title=f"Feature Task {i+1:02d}: Implement component module",
                description=(
                    f"Detailed description for task {i+1}. "
                    f"This task requires implementing a complete component with "
                    f"unit tests, integration tests, and documentation. "
                    f"The component must follow type safety requirements, "
                    f"use Pydantic models for validation, and integrate with "
                    f"the existing database layer. Performance requirements "
                    f"must be validated with appropriate test coverage. "
                    f"All code must pass mypy --strict validation and ruff linting."
                ),
                notes=(
                    f"Additional implementation notes for task {i+1}. "
                    f"Review architecture decisions with team before starting. "
                    f"Consider edge cases and error handling scenarios."
                ),
                planning_references=[
                    f"specs/{i+1:03d}-feature/spec.md",
                    f"specs/{i+1:03d}-feature/plan.md",
                ],
            )

            task_response: TaskResponse = await create_task(db=db, task_data=task_data)

            # Convert to dict format
            task_dict: dict[str, Any] = {
                "id": str(task_response.id),
                "title": task_response.title,
                "description": task_response.description,
                "notes": task_response.notes,
                "status": task_response.status,
                "created_at": task_response.created_at.isoformat(),
                "updated_at": task_response.updated_at.isoformat(),
                "planning_references": task_response.planning_references,
                "branches": task_response.branches,
                "commits": task_response.commits,
            }

            tasks.append(task_dict)

        await db.commit()

    return tasks


# ==============================================================================
# Token Counting Utilities
# ==============================================================================


def count_tokens(text: str) -> int:
    """Count tokens in text using tiktoken cl100k_base encoding.

    Args:
        text: Text to count tokens for

    Returns:
        Number of tokens in text

    Note:
        This test will FAIL if tiktoken is not installed.
        Expected error: ModuleNotFoundError: No module named 'tiktoken'

        To fix:
        1. Add tiktoken to pyproject.toml [project.optional-dependencies.dev]
        2. Run: pip install tiktoken
    """
    try:
        import tiktoken
    except ImportError as e:
        pytest.fail(
            f"tiktoken not installed: {e}\n"
            f"Add tiktoken to pyproject.toml dev dependencies and run: pip install tiktoken"
        )

    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


# ==============================================================================
# Integration Tests
# ==============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_tasks_token_efficiency_under_2000_tokens(
    sample_tasks: list[dict[str, Any]],
) -> None:
    """Test that list_tasks returns <2000 tokens for 15 tasks (PR-001).

    Expected behavior (AFTER implementation):
    - Create 15 tasks with realistic data
    - Call list_tasks() with default parameters
    - Response contains TaskSummary objects (5 fields only)
    - Token count is <2000 tokens (~6x improvement from 12,000+ baseline)

    Expected failure (CURRENT implementation):
    - Test WILL FAIL because list_tasks returns full TaskResponse objects
    - Current implementation includes all fields: description, notes,
      planning_references, branches, commits
    - Token count will be ~12,000+ tokens (exceeds 2000 target)

    This test validates:
    - PR-001: list_tasks with 15 tasks loads <2,000 tokens
    - Token efficiency requirement from spec.md
    - TDD methodology: test written before implementation

    Performance target:
    - Token count: <2000 tokens
    - Improvement ratio: ~6x reduction from 12,000+ baseline
    """
    # Import service function for list_tasks
    from src.services import list_tasks

    # Step 1: Call list_tasks service with default parameters
    async with get_session_factory()() as db:
        task_responses = await list_tasks(db=db)
        await db.commit()

    # Step 2: Convert to response format (MCP tool format)
    response: dict[str, Any] = {
        "tasks": [
            {
                "id": str(task.id),
                "title": task.title,
                "description": task.description,
                "notes": task.notes,
                "status": task.status,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
                "planning_references": task.planning_references,
                "branches": task.branches,
                "commits": task.commits,
            }
            for task in task_responses
        ],
        "total_count": len(task_responses),
    }

    # Step 3: Validate response structure
    assert "tasks" in response, "Response missing 'tasks' field"
    assert "total_count" in response, "Response missing 'total_count' field"
    assert isinstance(response["tasks"], list), "'tasks' must be a list"
    assert isinstance(response["total_count"], int), "'total_count' must be an integer"

    # Step 4: Validate task count
    assert response["total_count"] >= 15, (
        f"Expected at least 15 tasks, got {response['total_count']}"
    )

    # Step 5: Serialize response to JSON for token counting
    response_json = json.dumps(response)

    # Step 6: Count tokens using tiktoken
    token_count = count_tokens(response_json)

    # Step 7: Log diagnostic information
    print("\n" + "=" * 70)
    print("TOKEN EFFICIENCY VALIDATION (PR-001)")
    print("=" * 70)
    print(f"Tasks returned: {response['total_count']}")
    print(f"Response JSON length: {len(response_json)} characters")
    print(f"Token count: {token_count} tokens")
    print(f"Target: <2000 tokens")
    print("-" * 70)

    # Calculate improvement ratio (baseline: 12,000 tokens)
    baseline_tokens = 12000
    if token_count < baseline_tokens:
        improvement_ratio = baseline_tokens / token_count
        print(f"Improvement: ~{improvement_ratio:.1f}x reduction from baseline")
    else:
        print(f"Current: {token_count} tokens (exceeds baseline of {baseline_tokens})")

    print("=" * 70)

    # Step 8: Assert token efficiency requirement
    # THIS ASSERTION WILL FAIL until TaskSummary is implemented
    assert token_count < 2000, (
        f"Token count {token_count} exceeds 2000 target (PR-001 failed)\n"
        f"Current implementation returns full TaskResponse objects.\n"
        f"Expected: TaskSummary with 5 fields (id, title, status, created_at, updated_at)\n"
        f"Actual: TaskResponse with 10 fields (includes description, notes, references, etc.)\n"
        f"\n"
        f"To fix:\n"
        f"1. Implement TaskSummary response model in src/models/task.py\n"
        f"2. Update list_tasks() in src/mcp/tools/tasks.py to return summaries\n"
        f"3. Add optional full_details parameter for backward compatibility\n"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_tasks_baseline_token_count_measurement(
    sample_tasks: list[dict[str, Any]],
) -> None:
    """Measure baseline token count for full TaskResponse objects.

    This test documents the current implementation's token usage to
    establish the baseline for comparison. This is NOT a failing test -
    it's a measurement/documentation test.

    Expected behavior:
    - Call list_tasks() with current implementation
    - Measure token count for full TaskResponse objects
    - Document baseline for comparison with optimized implementation

    Performance baseline:
    - Expected token count: ~12,000+ tokens for 15 tasks
    - This establishes the "before" measurement for the 6x improvement goal
    """
    # Import service function
    from src.services import list_tasks

    # Step 1: Call list_tasks service with default parameters
    async with get_session_factory()() as db:
        task_responses = await list_tasks(db=db)
        await db.commit()

    # Step 2: Convert to response format
    response: dict[str, Any] = {
        "tasks": [
            {
                "id": str(task.id),
                "title": task.title,
                "description": task.description,
                "notes": task.notes,
                "status": task.status,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
                "planning_references": task.planning_references,
                "branches": task.branches,
                "commits": task.commits,
            }
            for task in task_responses
        ],
        "total_count": len(task_responses),
    }

    # Step 3: Serialize response to JSON
    response_json = json.dumps(response)

    # Step 4: Count tokens
    token_count = count_tokens(response_json)

    # Step 5: Document baseline metrics
    print("\n" + "=" * 70)
    print("BASELINE TOKEN COUNT MEASUREMENT")
    print("=" * 70)
    print(f"Tasks returned: {response['total_count']}")
    print(f"Response JSON length: {len(response_json)} characters")
    print(f"Token count: {token_count} tokens (BASELINE)")
    print(f"Average tokens per task: {token_count / response['total_count']:.1f}")
    print("-" * 70)
    print("This baseline will be compared against optimized implementation")
    print("Target: <2000 tokens (~6x reduction)")
    print("=" * 70)

    # Step 6: Validate that baseline is reasonably high
    # (confirming we have a real optimization opportunity)
    assert token_count > 2000, (
        f"Baseline token count {token_count} is unexpectedly low. "
        f"Expected >2000 tokens for full TaskResponse objects with 15 tasks."
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_tasks_response_schema_full_details(
    sample_tasks: list[dict[str, Any]],
) -> None:
    """Validate current list_tasks response schema (full TaskResponse).

    This test documents the current response structure to ensure we
    understand what fields are being returned. This helps validate that
    the optimization is meaningful (removing unnecessary fields).

    Expected behavior:
    - Response contains full TaskResponse objects
    - Each task has 10 fields: id, title, description, notes, status,
      created_at, updated_at, planning_references, branches, commits
    """
    # Import service function
    from src.services import list_tasks

    # Step 1: Call list_tasks service
    async with get_session_factory()() as db:
        task_responses = await list_tasks(db=db)
        await db.commit()

    # Step 2: Convert to response format
    response: dict[str, Any] = {
        "tasks": [
            {
                "id": str(task.id),
                "title": task.title,
                "description": task.description,
                "notes": task.notes,
                "status": task.status,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
                "planning_references": task.planning_references,
                "branches": task.branches,
                "commits": task.commits,
            }
            for task in task_responses
        ],
        "total_count": len(task_responses),
    }

    # Step 3: Validate at least one task returned
    assert len(response["tasks"]) > 0, "Expected at least one task"

    # Step 3: Check schema of first task
    task = response["tasks"][0]
    expected_fields = {
        "id",
        "title",
        "description",
        "notes",
        "status",
        "created_at",
        "updated_at",
        "planning_references",
        "branches",
        "commits",
    }
    actual_fields = set(task.keys())

    print("\n" + "=" * 70)
    print("CURRENT RESPONSE SCHEMA (TaskResponse)")
    print("=" * 70)
    print(f"Fields in response: {sorted(actual_fields)}")
    print(f"Total fields: {len(actual_fields)}")
    print("-" * 70)
    print("Expected after optimization: 5 fields (TaskSummary)")
    print("  - id, title, status, created_at, updated_at")
    print("=" * 70)

    assert expected_fields == actual_fields, (
        f"Response schema does not match expected TaskResponse structure.\n"
        f"Expected: {sorted(expected_fields)}\n"
        f"Actual: {sorted(actual_fields)}\n"
    )


# ==============================================================================
# Module Exports
# ==============================================================================

__all__ = [
    "test_list_tasks_token_efficiency_under_2000_tokens",
    "test_list_tasks_baseline_token_count_measurement",
    "test_list_tasks_response_schema_full_details",
]
