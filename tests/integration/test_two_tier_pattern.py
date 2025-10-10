"""Integration test for two-tier browse pattern (list summaries → get details).

This test validates the efficient workflow described in quickstart.md Scenario 3:
1. List tasks to get lightweight summaries
2. User identifies task of interest
3. Get full details for specific task only
4. Compare token efficiency vs loading all full details upfront

Constitutional Compliance:
- Principle VII: Test-Driven Development (test written before implementation)
- Principle VIII: Type Safety (full type annotations, mypy --strict)

Expected Behavior (TDD):
- This test MUST FAIL initially because summary mode is not implemented
- Failure expected: list_tasks() returns full TaskResponse (all 10 fields)
- Success after T013-T014: list_tasks() returns TaskSummary (5 fields only)
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import pytest

# tiktoken import will be needed once test passes
# For now, we'll skip if not available
try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

from src.database import get_session_factory
from src.services.tasks import create_task as create_task_service, get_task as get_task_service, list_tasks as list_tasks_service
from src.models import TaskCreate


# ==============================================================================
# Helper Functions
# ==============================================================================


def _task_response_to_dict(task_response: Any) -> dict[str, Any]:
    """Convert TaskResponse to dictionary with proper type handling.

    Args:
        task_response: TaskResponse object from service layer

    Returns:
        Dictionary representation of task with all fields

    Raises:
        AssertionError: If task_response is None
    """
    assert task_response is not None, "Task response must not be None"

    return {
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


# ==============================================================================
# Test Data Setup
# ==============================================================================


@pytest.fixture
async def sample_tasks() -> list[UUID]:
    """Create 15 sample tasks for testing.

    Returns:
        List of task UUIDs created in the database
    """
    task_ids: list[UUID] = []

    async with get_session_factory()() as db:
        for i in range(15):
            task_data = TaskCreate(
                title=f"Feature Task {i+1}: Implement component",
                description=(
                    f"Detailed description for task {i+1}. "
                    "This includes implementation details, technical requirements, "
                    "and acceptance criteria. " * 3
                ),  # ~200 chars
                notes=(
                    f"Additional notes and considerations for task {i+1}. "
                    "Review with team before starting."
                ),
                planning_references=[f"specs/{i+1:03d}-feature/spec.md"],
            )
            task_response = await create_task_service(db=db, task_data=task_data)
            task_ids.append(task_response.id)

        await db.commit()

    return task_ids


# ==============================================================================
# Integration Tests
# ==============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.skipif(
    not TIKTOKEN_AVAILABLE,
    reason="tiktoken not installed - required for token counting",
)
async def test_two_tier_pattern_token_efficiency(
    sample_tasks: list[UUID],
) -> None:
    """Test two-tier browse pattern for token efficiency.

    Validates quickstart.md Scenario 3:
    1. list_tasks() returns lightweight summaries
    2. Select one task of interest
    3. get_task(task_id) retrieves full details for that task only
    4. Two-tier pattern (list + get) uses fewer tokens than list(full_details=True)

    Expected Behavior (TDD):
    - FAILS initially: list_tasks() returns full TaskResponse with all 10 fields
    - PASSES after T013-T014: list_tasks() returns TaskSummary with 5 fields only

    Success Criteria:
    - Two-tier pattern saves >50% tokens vs full list
    - Two-tier total: list_tokens + detail_tokens < full_list_tokens * 0.5
    """
    encoding = tiktoken.get_encoding("cl100k_base")

    # Step 1: List tasks (should return summaries in final implementation)
    async with get_session_factory()() as db:
        tasks = await list_tasks_service(db=db, status=None, branch=None, limit=50)
        list_response: dict[str, Any] = {
            "tasks": [_task_response_to_dict(task) for task in tasks],
            "total_count": len(tasks),
        }
        await db.commit()

    # Validate response structure
    assert "tasks" in list_response, "Response must have 'tasks' field"
    assert "total_count" in list_response, "Response must have 'total_count' field"
    assert list_response["total_count"] == 15, f"Expected 15 tasks, got {list_response['total_count']}"

    # Calculate token cost for list operation
    list_json = json.dumps(list_response)
    list_tokens = len(encoding.encode(list_json))

    # TDD Assertion: This will FAIL initially
    # Current behavior: list_tasks returns full TaskResponse (~12000 tokens for 15 tasks)
    # Expected after implementation: ~2000 tokens
    # For now, just document what we get
    print(f"List operation token cost: {list_tokens} tokens")

    # Step 2: Select one task of interest (simulate user selection)
    target_task_summary = list_response["tasks"][0]
    task_id = target_task_summary["id"]
    print(f"Selected task: {target_task_summary['title']}")
    print(f"Task ID: {task_id}")

    # Step 3: Get full details for selected task
    async with get_session_factory()() as db:
        task_response = await get_task_service(db=db, task_id=UUID(task_id))
        task_details = _task_response_to_dict(task_response)
        await db.commit()

    # Validate TaskResponse has all fields
    required_fields = {
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
    actual_fields = set(task_details.keys())
    assert required_fields == actual_fields, (
        f"TaskResponse must have {required_fields}, got {actual_fields}"
    )

    # Calculate token cost for get_task operation
    detail_json = json.dumps(task_details)
    detail_tokens = len(encoding.encode(detail_json))
    print(f"Get detail operation token cost: {detail_tokens} tokens")

    # Step 4: Compare token efficiency
    total_two_tier = list_tokens + detail_tokens

    # Get baseline: full list with all details
    # NOTE: In current implementation, list_tasks() already returns full details
    # After implementation, we'd call list_tasks(full_details=True)
    # For now, we'll simulate by calculating expected full list cost
    async with get_session_factory()() as db:
        full_tasks = await list_tasks_service(db=db, status=None, branch=None, limit=50)
        full_list_response: dict[str, Any] = {
            "tasks": [_task_response_to_dict(task) for task in full_tasks],
            "total_count": len(full_tasks),
        }
        await db.commit()

    full_list_json = json.dumps(full_list_response)
    full_list_tokens = len(encoding.encode(full_list_json))

    print(f"\nToken Efficiency Comparison:")
    print(f"  Two-tier pattern (list + get_task): {total_two_tier} tokens")
    print(f"  Full list pattern: {full_list_tokens} tokens")

    # Calculate savings
    savings = full_list_tokens - total_two_tier
    savings_pct = (savings / full_list_tokens) * 100 if full_list_tokens > 0 else 0

    print(f"  Token savings: {savings} tokens ({savings_pct:.1f}% reduction)")

    # TDD Critical Assertion: This WILL FAIL initially
    # Expected failure reason: list_tokens is too high (~12000 instead of ~2000)
    # After implementation (T013-T014), this should pass with >50% savings
    #
    # Current behavior:
    #   - list_tokens: ~12000 (full details for 15 tasks)
    #   - detail_tokens: ~800 (1 task full details)
    #   - total_two_tier: ~12800
    #   - full_list_tokens: ~12000
    #   - savings_pct: NEGATIVE (worse, not better!)
    #
    # Expected after implementation:
    #   - list_tokens: ~2000 (summaries for 15 tasks)
    #   - detail_tokens: ~800 (1 task full details)
    #   - total_two_tier: ~2800
    #   - full_list_tokens: ~12000
    #   - savings_pct: ~78% (much better!)

    assert (
        savings_pct > 50.0
    ), f"Two-tier pattern must save >50% tokens, got {savings_pct:.1f}%"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_two_tier_pattern_schema_validation(
    sample_tasks: list[UUID],
) -> None:
    """Test that two-tier pattern returns correct schemas.

    Validates:
    1. list_tasks() returns TaskSummary schema (5 fields)
    2. get_task() returns TaskResponse schema (10 fields)

    Expected Behavior (TDD):
    - FAILS initially: list_tasks() returns 10 fields instead of 5
    - PASSES after T013-T014: list_tasks() returns 5 fields only

    Success Criteria:
    - List response has only 5 fields per task
    - Get response has all 10 fields
    """
    # Step 1: List tasks
    async with get_session_factory()() as db:
        tasks = await list_tasks_service(db=db, status=None, branch=None, limit=50)
        list_response: dict[str, Any] = {
            "tasks": [_task_response_to_dict(task) for task in tasks],
            "total_count": len(tasks),
        }
        await db.commit()

    assert "tasks" in list_response, "Response must have 'tasks' field"
    assert isinstance(list_response["tasks"], list), "tasks must be a list"
    assert len(list_response["tasks"]) > 0, "Must have at least one task"

    # Get first task from list
    task_summary: dict[str, Any] = list_response["tasks"][0]

    # TDD Critical Assertion: This WILL FAIL initially
    # Expected failure: task_summary has 10 fields, not 5
    # After implementation: task_summary has exactly 5 fields
    expected_summary_fields = {"id", "title", "status", "created_at", "updated_at"}
    actual_summary_fields = set(task_summary.keys())

    # This assertion will FAIL in TDD (current: 10 fields, expected: 5)
    assert expected_summary_fields == actual_summary_fields, (
        f"TaskSummary must have exactly {expected_summary_fields}, "
        f"got {actual_summary_fields}"
    )

    # Step 2: Get full details for that task
    task_id = task_summary["id"]
    async with get_session_factory()() as db:
        task_response = await get_task_service(db=db, task_id=UUID(task_id))
        task_details = _task_response_to_dict(task_response)
        await db.commit()

    # Get response should have all 10 fields (this should already pass)
    expected_detail_fields = {
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
    actual_detail_fields = set(task_details.keys())

    assert expected_detail_fields == actual_detail_fields, (
        f"TaskResponse must have {expected_detail_fields}, "
        f"got {actual_detail_fields}"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_two_tier_pattern_workflow(
    sample_tasks: list[UUID],
) -> None:
    """Test complete two-tier workflow without token counting.

    This test verifies the workflow logic without requiring tiktoken.
    Useful for environments where tiktoken is not available.

    Expected Behavior:
    - list_tasks() returns array of tasks
    - User can select task by ID
    - get_task() returns full details for selected task
    """
    # Step 1: List tasks
    async with get_session_factory()() as db:
        tasks = await list_tasks_service(db=db, status=None, branch=None, limit=50)
        list_response: dict[str, Any] = {
            "tasks": [_task_response_to_dict(task) for task in tasks],
            "total_count": len(tasks),
        }
        await db.commit()

    assert "tasks" in list_response
    assert "total_count" in list_response
    assert isinstance(list_response["total_count"], int)
    assert list_response["total_count"] > 0, "Must have tasks"
    assert isinstance(list_response["tasks"], list)

    # Step 2: Select first task
    first_task: dict[str, Any] = list_response["tasks"][0]
    task_id: str = first_task["id"]

    # Validate task_id is a valid UUID string
    try:
        UUID(task_id)
    except (ValueError, AttributeError) as e:
        pytest.fail(f"Task ID must be valid UUID string: {task_id}, error: {e}")

    # Step 3: Get full details
    async with get_session_factory()() as db:
        task_response = await get_task_service(db=db, task_id=UUID(task_id))
        task_details = _task_response_to_dict(task_response)
        await db.commit()

    # Validate response
    assert task_details["id"] == task_id, "Task ID must match"
    assert "title" in task_details
    assert "status" in task_details

    # Validate description exists (full details)
    assert "description" in task_details, "Full details must include description"
    assert "notes" in task_details, "Full details must include notes"
    assert "planning_references" in task_details
    assert "branches" in task_details
    assert "commits" in task_details


# ==============================================================================
# Cleanup
# ==============================================================================


@pytest.fixture(autouse=True, scope="function")
async def cleanup_test_data() -> Any:
    """Clean up test data after each test.

    Note: This is a placeholder. In production, we'd clean up the created tasks.
    For now, tests run against test database that can be reset.

    Returns:
        None before test, None after test (async generator pattern)
    """
    yield
    # Future: Delete created tasks from database
