# MCP Tools Integration Test

## Overview

Comprehensive integration test for all 6 MCP tools in the Codebase MCP Server, testing them in a realistic workflow sequence.

## Files

- **`test_mcp_tools.py`** - Main test script
- **`run_test_mcp_tools.sh`** - Convenience wrapper script that handles virtual environment activation

## Test Coverage

The test script validates all 6 MCP tools in sequence:

### 1. **create_task** ✅
- Creates a task with title, description, notes, and planning references
- Validates response structure (id, title, status, etc.)
- Verifies default status is "need to be done"

### 2. **get_task** ✅
- Retrieves the task created in Test 1 by ID
- Validates all fields match the created task
- Checks timestamp fields (created_at, updated_at)

### 3. **list_tasks** ✅
- Lists all tasks with status filter
- Validates response structure (tasks array, total_count)
- Verifies created task appears in the list

### 4. **index_repository** ✅
- Indexes the `test_small_repo` directory (2 files)
- Captures repository_id, files_indexed, chunks_created
- Validates indexing completed successfully with status="success"
- Tests with `force_reindex=True`

### 5. **search_code** ✅
- Performs semantic search on the indexed repository
- Uses query "test function" to search for relevant code
- Validates results returned with similarity scores
- Checks latency metrics

### 6. **update_task** ✅
- Updates the task with search results in notes
- Changes status to "in-progress"
- Links to a git branch ("test/integration")
- Validates all updates persisted correctly

## Usage

### Quick Run (Recommended)

```bash
./run_test_mcp_tools.sh
```

This script:
1. Checks for virtual environment
2. Activates `.venv`
3. Runs `test_mcp_tools.py`
4. Deactivates virtual environment
5. Returns appropriate exit code

### Manual Run

```bash
source .venv/bin/activate
python test_mcp_tools.py
```

## Output Format

The test provides detailed output for each test:

```
[TEST 1] create_task
--------------------------------------------------------------------------------
✅ PASS - Created task: efb60372-accd-4496-9b21-8fab9b98a872
   Title: Integration Test Task
   Status: need to be done
   Planning Refs: 1
```

Final summary shows pass/fail counts:

```
================================================================================
TEST SUMMARY
================================================================================
Passed: 6/6
Failed: 0/6

✅ ALL TESTS PASSED
```

## Exit Codes

- **0** - All tests passed
- **1** - One or more tests failed or critical error occurred

## Dependencies

- PostgreSQL database (configured via `.env`)
- Virtual environment with all dependencies installed
- `test_small_repo/` directory with test files

## Constitutional Compliance

The test script follows constitutional principles:

- **Principle III**: Protocol Compliance - Validates MCP contract responses
- **Principle V**: Production Quality - Comprehensive error handling
- **Principle VII**: Test-Driven Development - Validates tool behavior
- **Principle VIII**: Type Safety - mypy --strict compliance

## Error Handling

The test script includes robust error handling:

- Database connection failures halt execution immediately
- Task creation failure prevents dependent tests from running
- Repository indexing failure skips search test but continues
- All failures are clearly marked with ❌ and error details
- Database changes are committed only if all operations succeed

## Test Data

Uses `test_small_repo/` directory containing:
- `README.md` - Documentation file
- `test_file.py` - Python test file

Both files are indexed and searched during the test workflow.
