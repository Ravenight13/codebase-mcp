#!/usr/bin/env python3
"""Comprehensive MCP Tools Integration Test.

Tests all 6 tools in realistic workflow:
1. Create task
2. Get task
3. List tasks
4. Index repository
5. Search code
6. Update task with results

Constitutional Compliance:
- Principle III: Protocol Compliance (validates MCP contract responses)
- Principle V: Production Quality (comprehensive error handling)
- Principle VII: Test-Driven Development (validates tool behavior)
- Principle VIII: Type Safety (mypy --strict compliance)
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

import src.database as database
from src.mcp.tools import (
    create_task_tool,
    get_task_tool,
    index_repository_tool,
    list_tasks_tool,
    search_code_tool,
    update_task_tool,
)

# ==============================================================================
# Test State Tracking
# ==============================================================================

tests_passed: int = 0
tests_failed: int = 0


# ==============================================================================
# Helper Functions
# ==============================================================================


def print_test_header(test_num: int, test_name: str) -> None:
    """Print standardized test header."""
    print(f"\n[TEST {test_num}] {test_name}")
    print("-" * 80)


def print_pass(message: str, details: dict[str, Any] | None = None) -> None:
    """Print success message with optional details."""
    global tests_passed
    tests_passed += 1
    print(f"✅ PASS - {message}")
    if details:
        for key, value in details.items():
            print(f"   {key}: {value}")


def print_fail(message: str, error: Exception | None = None) -> None:
    """Print failure message with error details."""
    global tests_failed
    tests_failed += 1
    print(f"❌ FAIL - {message}")
    if error:
        print(f"   Error: {type(error).__name__}: {error}")


def print_skip(message: str) -> None:
    """Print skip message."""
    print(f"⚠️  SKIP - {message}")


# ==============================================================================
# Main Test Function
# ==============================================================================


async def main() -> None:
    """Run comprehensive MCP tool tests."""
    global tests_passed, tests_failed

    print("=" * 80)
    print("MCP TOOLS COMPREHENSIVE INTEGRATION TEST")
    print("=" * 80)

    # Initialize database
    print("\n[SETUP] Initializing database connection...")
    try:
        await database.init_db_connection()
        if database.SessionLocal is None:
            print("❌ Database initialization failed - SessionLocal is None")
            sys.exit(1)
        print("✅ Database connection initialized")
    except Exception as e:
        print(f"❌ Database initialization failed: {type(e).__name__}: {e}")
        sys.exit(1)

    # Test variables
    task_id: str | None = None
    repo_id: str | None = None

    async with database.SessionLocal() as session:
        # ======================================================================
        # TEST 1: create_task
        # ======================================================================
        print_test_header(1, "create_task")
        try:
            task = await create_task_tool(
                db=session,
                title="Integration Test Task",
                description="Testing all MCP tools in sequence",
                notes="Created by test_mcp_tools.py",
                planning_references=["test_small_repo/README.md"],
            )

            # Validate response structure
            assert "id" in task, "Response missing 'id' field"
            assert "title" in task, "Response missing 'title' field"
            assert "status" in task, "Response missing 'status' field"
            assert task["title"] == "Integration Test Task"
            assert task["status"] == "need to be done"

            task_id = task["id"]
            print_pass(
                f"Created task: {task_id}",
                {
                    "Title": task["title"],
                    "Status": task["status"],
                    "Planning Refs": len(task.get("planning_references", [])),
                },
            )
        except Exception as e:
            print_fail("Failed to create task", e)
            await session.rollback()
            # Cannot continue without task_id
            print("\n❌ CRITICAL: Cannot continue without task creation")
            await print_summary()
            return

        # ======================================================================
        # TEST 2: get_task
        # ======================================================================
        print_test_header(2, "get_task")
        try:
            assert task_id is not None, "task_id is None"
            retrieved = await get_task_tool(db=session, task_id=task_id)

            # Validate response structure and data
            assert retrieved["id"] == task_id, "Task ID mismatch"
            assert retrieved["title"] == "Integration Test Task", "Title mismatch"
            assert (
                retrieved["description"] == "Testing all MCP tools in sequence"
            ), "Description mismatch"
            assert retrieved["status"] == "need to be done", "Status mismatch"

            print_pass(
                f"Retrieved task: {task_id}",
                {
                    "Description": retrieved["description"],
                    "Created At": retrieved.get("created_at", "N/A"),
                },
            )
        except Exception as e:
            print_fail("Failed to retrieve task", e)

        # ======================================================================
        # TEST 3: list_tasks
        # ======================================================================
        print_test_header(3, "list_tasks")
        try:
            result = await list_tasks_tool(
                db=session,
                status="need to be done",
                limit=10,
            )

            # Validate response structure
            assert "tasks" in result, "Response missing 'tasks' field"
            assert "total_count" in result, "Response missing 'total_count' field"
            assert isinstance(result["tasks"], list), "tasks is not a list"
            assert result["total_count"] > 0, "No tasks found"

            # Check if our task is in the list
            task_found = any(t["id"] == task_id for t in result["tasks"])
            assert task_found, "Created task not found in list"

            print_pass(
                f"Listed {result['total_count']} task(s)",
                {
                    "Status Filter": "need to be done",
                    "Created Task Found": "Yes" if task_found else "No",
                },
            )
        except Exception as e:
            print_fail("Failed to list tasks", e)

        # ======================================================================
        # TEST 4: index_repository
        # ======================================================================
        print_test_header(4, "index_repository")
        try:
            repo_path = "/Users/cliffclarke/Claude_Code/codebase-mcp/test_small_repo"

            # Verify repository path exists
            if not Path(repo_path).exists():
                raise FileNotFoundError(f"Test repository not found: {repo_path}")

            result = await index_repository_tool(
                db=session,
                repo_path=repo_path,
                force_reindex=True,
            )

            # Validate response structure
            assert "repository_id" in result, "Response missing 'repository_id' field"
            assert "files_indexed" in result, "Response missing 'files_indexed' field"
            assert (
                "chunks_created" in result
            ), "Response missing 'chunks_created' field"
            assert (
                "duration_seconds" in result
            ), "Response missing 'duration_seconds' field"
            assert "status" in result, "Response missing 'status' field"

            # Validate data
            assert result["files_indexed"] > 0, "No files indexed"
            assert result["chunks_created"] > 0, "No chunks created"
            assert result["status"] == "success", f"Status is {result['status']}"

            repo_id = result["repository_id"]
            print_pass(
                f"Indexed repository: {repo_id}",
                {
                    "Files": result["files_indexed"],
                    "Chunks": result["chunks_created"],
                    "Duration": f"{result['duration_seconds']:.2f}s",
                    "Status": result["status"],
                },
            )
        except Exception as e:
            print_fail("Failed to index repository", e)
            repo_id = None

        # ======================================================================
        # TEST 5: search_code
        # ======================================================================
        print_test_header(5, "search_code")
        try:
            if repo_id is None:
                raise ValueError("No repository indexed, cannot perform search")

            results = await search_code_tool(
                db=session,
                query="test function",
                repository_id=repo_id,
                limit=5,
            )

            # Validate response structure
            assert "results" in results, "Response missing 'results' field"
            assert "total_count" in results, "Response missing 'total_count' field"
            assert "latency_ms" in results, "Response missing 'latency_ms' field"
            assert isinstance(results["results"], list), "results is not a list"

            result_count = results["total_count"]

            details: dict[str, Any] = {
                "Results Found": result_count,
                "Latency": f"{results['latency_ms']}ms",
            }

            if result_count > 0:
                top = results["results"][0]
                assert "chunk_id" in top, "Result missing 'chunk_id' field"
                assert "file_path" in top, "Result missing 'file_path' field"
                assert "content" in top, "Result missing 'content' field"
                assert (
                    "similarity_score" in top
                ), "Result missing 'similarity_score' field"

                details["Top Match"] = top["file_path"]
                details["Score"] = f"{top['similarity_score']:.3f}"

            print_pass(f"Found {result_count} result(s)", details)
        except Exception as e:
            print_fail("Failed to search code", e)

        # ======================================================================
        # TEST 6: update_task
        # ======================================================================
        print_test_header(6, "update_task")
        try:
            assert task_id is not None, "task_id is None"

            updated = await update_task_tool(
                db=session,
                task_id=task_id,
                status="in-progress",
                notes="Updated with search results - integration test complete",
                branch="test/integration",
            )

            # Validate response structure
            assert "id" in updated, "Response missing 'id' field"
            assert "status" in updated, "Response missing 'status' field"
            assert "branches" in updated, "Response missing 'branches' field"
            assert "notes" in updated, "Response missing 'notes' field"

            # Validate data
            assert updated["status"] == "in-progress", "Status not updated"
            assert "test/integration" in updated["branches"], "Branch not added"
            assert (
                "integration test complete" in updated["notes"]
            ), "Notes not updated"

            print_pass(
                f"Updated task: {task_id}",
                {
                    "New Status": updated["status"],
                    "Branches": ", ".join(updated["branches"]),
                },
            )
        except Exception as e:
            print_fail("Failed to update task", e)

        # Commit all changes
        try:
            await session.commit()
            print("\n✅ All database changes committed successfully")
        except Exception as e:
            print(f"\n❌ Failed to commit changes: {type(e).__name__}: {e}")
            await session.rollback()

    # Final summary
    await print_summary()


async def print_summary() -> None:
    """Print final test summary and exit."""
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Passed: {tests_passed}/6")
    print(f"Failed: {tests_failed}/6")

    if tests_failed == 0:
        print("\n✅ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print(f"\n❌ {tests_failed} TEST(S) FAILED")
        sys.exit(1)


# ==============================================================================
# Entry Point
# ==============================================================================

if __name__ == "__main__":
    asyncio.run(main())
