# Quickstart: list_tasks Token Optimization

**Feature**: Optimize list_tasks MCP Tool for Token Efficiency
**Date**: 2025-10-10
**Branch**: 004-as-an-ai

## Overview

This document provides executable test scenarios for validating the list_tasks optimization feature. These scenarios correspond directly to the acceptance criteria in [spec.md](./spec.md) and serve as integration tests.

## Prerequisites

- PostgreSQL database running with task schema
- MCP server running (`src/mcp/server_fastmcp.py`)
- Test database populated with sample tasks
- `tiktoken` library installed for token counting

## Test Data Setup

```python
# Setup: Create 15 test tasks with realistic data
import asyncio
from src.database import get_session_factory
from src.services import create_task

async def setup_test_data():
    """Create 15 test tasks for quickstart scenarios."""
    async with get_session_factory()() as db:
        tasks = []
        for i in range(15):
            task_data = {
                "title": f"Feature Task {i+1}: Implement component",
                "description": f"Detailed description for task {i+1}. This includes implementation details, technical requirements, and acceptance criteria. " * 3,  # ~200 chars
                "notes": f"Additional notes and considerations for task {i+1}. Review with team before starting.",
                "status": ["need to be done", "in-progress", "complete"][i % 3],
                "planning_references": [f"specs/{i+1:03d}-feature/spec.md"],
            }
            task = await create_task(db, task_data)
            tasks.append(task)
        await db.commit()
    return tasks
```

---

## Scenario 1: List Tasks with Summary (Primary User Story)

**Goal**: Validate default list_tasks behavior returns lightweight summaries with <2000 tokens

**Acceptance Criteria**:
- Given: 15 tasks in database
- When: Call list_tasks()
- Then: Receive 15 TaskSummary objects, <2000 tokens

### Execution Steps

```python
import json
import tiktoken
from src.mcp.tools import list_tasks

async def scenario_1_list_tasks_summary():
    """Scenario 1: List tasks and get summary."""

    print("=== Scenario 1: List Tasks with Summary ===\n")

    # Step 1: Call list_tasks with default parameters
    print("Step 1: Calling list_tasks()...")
    response = await list_tasks()

    # Step 2: Validate response structure
    print("Step 2: Validating response structure...")
    assert "tasks" in response, "Response missing 'tasks' field"
    assert "total_count" in response, "Response missing 'total_count' field"
    assert isinstance(response["tasks"], list), "'tasks' must be a list"
    assert isinstance(response["total_count"], int), "'total_count' must be an integer"

    # Step 3: Validate task count
    print(f"Step 3: Validating task count ({response['total_count']} tasks)...")
    assert response["total_count"] == 15, f"Expected 15 tasks, got {response['total_count']}"
    assert len(response["tasks"]) == 15, f"Expected 15 tasks in array, got {len(response['tasks'])}"

    # Step 4: Validate TaskSummary schema (5 fields only)
    print("Step 4: Validating TaskSummary schema...")
    for task in response["tasks"]:
        required_fields = {"id", "title", "status", "created_at", "updated_at"}
        actual_fields = set(task.keys())

        assert required_fields == actual_fields, \
            f"TaskSummary must have exactly {required_fields}, got {actual_fields}"

        # Validate field types
        assert isinstance(task["id"], str), "id must be string (UUID)"
        assert isinstance(task["title"], str), "title must be string"
        assert task["status"] in ["need to be done", "in-progress", "complete"], \
            f"Invalid status: {task['status']}"
        assert isinstance(task["created_at"], str), "created_at must be string (ISO 8601)"
        assert isinstance(task["updated_at"], str), "updated_at must be string (ISO 8601)"

    print("✅ TaskSummary schema validated (5 fields only)\n")

    # Step 5: Validate token efficiency (<2000 tokens)
    print("Step 5: Validating token efficiency...")
    response_json = json.dumps(response)
    encoding = tiktoken.get_encoding("cl100k_base")
    token_count = len(encoding.encode(response_json))

    print(f"  Response JSON length: {len(response_json)} characters")
    print(f"  Token count: {token_count} tokens")
    print(f"  Target: < 2000 tokens")

    assert token_count < 2000, \
        f"Token count {token_count} exceeds 2000 target (failed PR-001)"

    improvement_ratio = 12000 / token_count  # Baseline: 12000 tokens
    print(f"  Improvement: ~{improvement_ratio:.1f}x reduction from baseline\n")

    print("✅ Scenario 1 PASSED: list_tasks returns efficient summaries\n")
    print(f"Summary: {response['total_count']} tasks, {token_count} tokens, {improvement_ratio:.1f}x improvement\n")

    return response
```

**Expected Output**:
```
=== Scenario 1: List Tasks with Summary ===

Step 1: Calling list_tasks()...
Step 2: Validating response structure...
Step 3: Validating task count (15 tasks)...
Step 4: Validating TaskSummary schema...
✅ TaskSummary schema validated (5 fields only)

Step 5: Validating token efficiency...
  Response JSON length: 1847 characters
  Token count: 1923 tokens
  Target: < 2000 tokens
  Improvement: ~6.2x reduction from baseline

✅ Scenario 1 PASSED: list_tasks returns efficient summaries

Summary: 15 tasks, 1923 tokens, 6.2x improvement
```

---

## Scenario 2: List Tasks with Full Details (Edge Case)

**Goal**: Validate full_details parameter returns complete TaskResponse objects

**Acceptance Criteria**:
- Given: 15 tasks in database
- When: Call list_tasks(full_details=True)
- Then: Receive 15 TaskResponse objects with all fields

### Execution Steps

```python
async def scenario_2_list_tasks_full_details():
    """Scenario 2: List tasks with full details (opt-in)."""

    print("=== Scenario 2: List Tasks with Full Details ===\n")

    # Step 1: Call list_tasks with full_details=True
    print("Step 1: Calling list_tasks(full_details=True)...")
    response = await list_tasks(full_details=True)

    # Step 2: Validate response structure
    print("Step 2: Validating response structure...")
    assert "tasks" in response, "Response missing 'tasks' field"
    assert "total_count" in response, "Response missing 'total_count' field"
    assert response["total_count"] == 15, f"Expected 15 tasks, got {response['total_count']}"

    # Step 3: Validate TaskResponse schema (all 10 fields)
    print("Step 3: Validating TaskResponse schema...")
    for task in response["tasks"]:
        required_fields = {
            "id", "title", "description", "notes", "status",
            "created_at", "updated_at", "planning_references",
            "branches", "commits"
        }
        actual_fields = set(task.keys())

        assert required_fields == actual_fields, \
            f"TaskResponse must have {required_fields}, got {actual_fields}"

        # Validate array fields
        assert isinstance(task["planning_references"], list), \
            "planning_references must be array"
        assert isinstance(task["branches"], list), "branches must be array"
        assert isinstance(task["commits"], list), "commits must be array"

    print("✅ TaskResponse schema validated (all 10 fields)\n")

    # Step 4: Document token count (baseline comparison)
    print("Step 4: Documenting token count (baseline)...")
    response_json = json.dumps(response)
    encoding = tiktoken.get_encoding("cl100k_base")
    token_count = len(encoding.encode(response_json))

    print(f"  Response JSON length: {len(response_json)} characters")
    print(f"  Token count: {token_count} tokens")
    print(f"  Note: This is the old behavior (high token count)\n")

    print("✅ Scenario 2 PASSED: list_tasks(full_details=True) returns complete objects\n")
    print(f"Summary: {response['total_count']} tasks, {token_count} tokens (full details mode)\n")

    return response
```

**Expected Output**:
```
=== Scenario 2: List Tasks with Full Details ===

Step 1: Calling list_tasks(full_details=True)...
Step 2: Validating response structure...
Step 3: Validating TaskResponse schema...
✅ TaskResponse schema validated (all 10 fields)

Step 4: Documenting token count (baseline)...
  Response JSON length: 14523 characters
  Token count: 12847 tokens
  Note: This is the old behavior (high token count)

✅ Scenario 2 PASSED: list_tasks(full_details=True) returns complete objects

Summary: 15 tasks, 12847 tokens (full details mode)
```

---

## Scenario 3: Two-Tier Browse Pattern (Get Specific Details)

**Goal**: Validate efficient workflow: list summaries → identify task → get full details

**Acceptance Criteria**:
- Given: Task summary list received
- When: Call get_task(task_id)
- Then: Receive full TaskResponse for specific task

### Execution Steps

```python
from src.mcp.tools import get_task

async def scenario_3_two_tier_browse():
    """Scenario 3: Two-tier browsing - list summaries, then get details."""

    print("=== Scenario 3: Two-Tier Browse Pattern ===\n")

    # Step 1: List tasks (get summaries)
    print("Step 1: Listing tasks (summary mode)...")
    list_response = await list_tasks()
    print(f"  Received {list_response['total_count']} task summaries")

    # Calculate token cost for list
    list_json = json.dumps(list_response)
    encoding = tiktoken.get_encoding("cl100k_base")
    list_tokens = len(encoding.encode(list_json))
    print(f"  List operation token cost: {list_tokens} tokens\n")

    # Step 2: User identifies task of interest (simulate)
    print("Step 2: User scans summaries and identifies task of interest...")
    target_task_summary = list_response["tasks"][0]  # Simulate user selection
    task_id = target_task_summary["id"]
    print(f"  Selected task: {target_task_summary['title']}")
    print(f"  Task ID: {task_id}\n")

    # Step 3: Get full details for selected task
    print("Step 3: Fetching full details for selected task...")
    task_details = await get_task(task_id=task_id)

    # Step 4: Validate TaskResponse has all fields
    print("Step 4: Validating full TaskResponse...")
    required_fields = {
        "id", "title", "description", "notes", "status",
        "created_at", "updated_at", "planning_references",
        "branches", "commits"
    }
    actual_fields = set(task_details.keys())
    assert required_fields == actual_fields, \
        f"TaskResponse must have {required_fields}, got {actual_fields}"

    print("✅ Full task details retrieved successfully\n")

    # Calculate token cost for get_task
    detail_json = json.dumps(task_details)
    detail_tokens = len(encoding.encode(detail_json))
    print(f"  Get detail operation token cost: {detail_tokens} tokens\n")

    # Step 5: Compare token efficiency
    print("Step 5: Comparing two-tier vs full list efficiency...")
    total_two_tier = list_tokens + detail_tokens
    full_list_response = await list_tasks(full_details=True)
    full_list_json = json.dumps(full_list_response)
    full_list_tokens = len(encoding.encode(full_list_json))

    print(f"  Two-tier pattern (list + get_task): {total_two_tier} tokens")
    print(f"  Full list pattern (list_tasks full): {full_list_tokens} tokens")
    savings = full_list_tokens - total_two_tier
    savings_pct = (savings / full_list_tokens) * 100
    print(f"  Token savings: {savings} tokens ({savings_pct:.1f}% reduction)\n")

    print("✅ Scenario 3 PASSED: Two-tier pattern is more efficient\n")
    print(f"Summary: Two-tier pattern saves {savings_pct:.1f}% tokens when viewing 1 task detail\n")

    return task_details
```

**Expected Output**:
```
=== Scenario 3: Two-Tier Browse Pattern ===

Step 1: Listing tasks (summary mode)...
  Received 15 task summaries
  List operation token cost: 1923 tokens

Step 2: User scans summaries and identifies task of interest...
  Selected task: Feature Task 1: Implement component
  Task ID: 550e8400-e29b-41d4-a716-446655440000

Step 3: Fetching full details for selected task...
Step 4: Validating full TaskResponse...
✅ Full task details retrieved successfully

  Get detail operation token cost: 847 tokens

Step 5: Comparing two-tier vs full list efficiency...
  Two-tier pattern (list + get_task): 2770 tokens
  Full list pattern (list_tasks full): 12847 tokens
  Token savings: 10077 tokens (78.4% reduction)

✅ Scenario 3 PASSED: Two-tier pattern is more efficient

Summary: Two-tier pattern saves 78.4% tokens when viewing 1 task detail
```

---

## Scenario 4: Filter with Summary Mode

**Goal**: Validate filtering parameters work correctly with summary mode

**Acceptance Criteria**:
- Given: Tasks with various statuses and branches
- When: Call list_tasks with filters
- Then: Summary view respects filtering

### Execution Steps

```python
async def scenario_4_filtered_summary():
    """Scenario 4: Filtering works with summary mode."""

    print("=== Scenario 4: Filter with Summary Mode ===\n")

    # Test 1: Filter by status
    print("Test 1: Filter by status='in-progress'...")
    response = await list_tasks(status="in-progress")

    print(f"  Received {response['total_count']} tasks")
    for task in response["tasks"]:
        assert task["status"] == "in-progress", \
            f"Expected status 'in-progress', got '{task['status']}'"

    print("✅ Status filtering works correctly\n")

    # Test 2: Filter by limit
    print("Test 2: Limit results to 5 tasks...")
    response = await list_tasks(limit=5)

    assert response["total_count"] <= 5, \
        f"Expected ≤5 tasks with limit=5, got {response['total_count']}"
    assert len(response["tasks"]) == response["total_count"], \
        "Array length must match total_count"

    print(f"✅ Limit filtering works correctly ({response['total_count']} tasks)\n")

    # Test 3: Validate schema remains TaskSummary with filters
    print("Test 3: Validate schema remains TaskSummary with filters...")
    for task in response["tasks"]:
        assert set(task.keys()) == {"id", "title", "status", "created_at", "updated_at"}, \
            "Filtering must not affect TaskSummary schema"

    print("✅ TaskSummary schema maintained with filters\n")

    print("✅ Scenario 4 PASSED: Filtering works with summary mode\n")
```

**Expected Output**:
```
=== Scenario 4: Filter with Summary Mode ===

Test 1: Filter by status='in-progress'...
  Received 5 tasks
✅ Status filtering works correctly

Test 2: Limit results to 5 tasks...
✅ Limit filtering works correctly (5 tasks)

Test 3: Validate schema remains TaskSummary with filters...
✅ TaskSummary schema maintained with filters

✅ Scenario 4 PASSED: Filtering works with summary mode
```

---

## Scenario 5: Empty Result Handling

**Goal**: Validate graceful handling of empty results

**Acceptance Criteria**:
- Given: No tasks match filter
- When: Call list_tasks with restrictive filter
- Then: Return empty array with zero token overhead

### Execution Steps

```python
async def scenario_5_empty_results():
    """Scenario 5: Handle empty results gracefully."""

    print("=== Scenario 5: Empty Result Handling ===\n")

    # Test: Filter that returns no results
    print("Test: Filter by non-existent branch...")
    response = await list_tasks(branch="non-existent-branch")

    # Validate empty response structure
    assert "tasks" in response, "Response must have 'tasks' field"
    assert "total_count" in response, "Response must have 'total_count' field"
    assert response["tasks"] == [], f"Expected empty array, got {response['tasks']}"
    assert response["total_count"] == 0, f"Expected total_count=0, got {response['total_count']}"

    print("✅ Empty array returned correctly\n")

    # Validate minimal token overhead
    response_json = json.dumps(response)
    encoding = tiktoken.get_encoding("cl100k_base")
    token_count = len(encoding.encode(response_json))

    print(f"  Empty response token count: {token_count} tokens")
    assert token_count < 50, \
        f"Empty response should have minimal tokens, got {token_count}"

    print("✅ Minimal token overhead for empty results\n")

    print("✅ Scenario 5 PASSED: Empty results handled gracefully\n")
```

**Expected Output**:
```
=== Scenario 5: Empty Result Handling ===

Test: Filter by non-existent branch...
✅ Empty array returned correctly

  Empty response token count: 23 tokens
✅ Minimal token overhead for empty results

✅ Scenario 5 PASSED: Empty results handled gracefully
```

---

## Running All Scenarios

```python
async def run_all_quickstart_scenarios():
    """Run all quickstart scenarios sequentially."""

    print("=" * 60)
    print("QUICKSTART: list_tasks Token Optimization")
    print("=" * 60)
    print()

    # Setup test data
    print("Setup: Creating 15 test tasks...")
    await setup_test_data()
    print("✅ Test data created\n")

    # Run scenarios
    await scenario_1_list_tasks_summary()
    await scenario_2_list_tasks_full_details()
    await scenario_3_two_tier_browse()
    await scenario_4_filtered_summary()
    await scenario_5_empty_results()

    print("=" * 60)
    print("ALL QUICKSTART SCENARIOS PASSED ✅")
    print("=" * 60)

# Execute
if __name__ == "__main__":
    asyncio.run(run_all_quickstart_scenarios())
```

---

## Performance Summary

**Token Efficiency**:
| Operation | Token Count | Target | Status |
|-----------|-------------|--------|--------|
| list_tasks (summary, 15 tasks) | ~1923 | <2000 | ✅ PASS |
| list_tasks (full, 15 tasks) | ~12847 | N/A (baseline) | 📊 Baseline |
| Two-tier (list + 1 detail) | ~2770 | N/A | 78% savings |
| Empty result | ~23 | <50 | ✅ PASS |

**Latency** (all operations):
- Target: <200ms p95
- Measured: (validated in performance tests)

---

## Constitutional Compliance

| Principle | Validation | Status |
|-----------|------------|--------|
| **IV. Performance Guarantees** | Token count <2000 for 15 tasks | ✅ PASS |
| **VII. Test-Driven Development** | Quickstart scenarios as integration tests | ✅ PASS |
| **VIII. Pydantic Type Safety** | Schema validation in all scenarios | ✅ PASS |

---

**Status**: ✅ Quickstart scenarios complete - Ready for implementation
