# Quickstart: Multi-Project Workspace Integration Tests

**Feature**: 008-multi-project-workspace
**Date**: 2025-10-12
**Purpose**: Integration test scenarios validating multi-project workspace isolation

## Prerequisites

- Python 3.11+ installed
- PostgreSQL 14+ with pgvector extension running
- codebase-mcp server configured (see main README.md)
- Test dependencies: `pytest`, `pytest-asyncio`, `pytest-benchmark`

## Quick Validation

Run all integration tests to validate feature:
```bash
# From repository root
pytest specs/008-multi-project-workspace/quickstart.md --doctest-modules -v
```

**Expected result**: All 9 test scenarios pass, confirming:
- ✅ Complete data isolation between projects
- ✅ Project switching <50ms (performance target)
- ✅ SQL injection prevention (security guarantee)
- ✅ Backward compatibility (existing usage works)

## Overview

This document defines executable integration test scenarios that validate the feature specification's user stories and acceptance criteria. Each scenario can be run as a pytest test to verify correct behavior.

---

## Test Scenario 1: Complete Data Isolation

**Validates**: Primary Workflow steps 1-12, Acceptance Scenario 1
**Traces to**: FR-009 (isolated workspace), FR-017 (complete data isolation)

### Setup
```python
# Create two test fixtures with distinct code
@pytest.fixture
def repo_a(tmp_path):
    """Fixture: Client A codebase with authentication logic."""
    repo_dir = tmp_path / "repo-a"
    repo_dir.mkdir()

    # Create distinct Python file
    (repo_dir / "auth.py").write_text("""
def authenticate_user_a(username, password):
    '''Client A authentication implementation'''
    return validate_credentials_a(username, password)
""")

    return str(repo_dir)

@pytest.fixture
def repo_b(tmp_path):
    """Fixture: Client B codebase with authentication logic."""
    repo_dir = tmp_path / "repo-b"
    repo_dir.mkdir()

    # Create distinct Python file
    (repo_dir / "auth.py").write_text("""
def authenticate_user_b(credentials):
    '''Client B authentication implementation'''
    return verify_token_b(credentials.token)
""")

    return str(repo_dir)
```

### Test Steps
```python
@pytest.mark.integration
async def test_complete_data_isolation(repo_a, repo_b):
    """Verify zero cross-project data leakage."""

    # Step 1: Index Client A codebase into project-a workspace
    result_a = await index_repository(
        repo_path=repo_a,
        project_id="client-a"
    )
    assert result_a["status"] == "success"
    assert result_a["project_id"] == "client-a"
    assert result_a["schema_name"] == "project_client_a"
    assert result_a["files_indexed"] == 1

    # Step 2: Index Client B codebase into project-b workspace
    result_b = await index_repository(
        repo_path=repo_b,
        project_id="client-b"
    )
    assert result_b["status"] == "success"
    assert result_b["project_id"] == "client-b"
    assert result_b["schema_name"] == "project_client_b"
    assert result_b["files_indexed"] == 1

    # Step 3: Search "authentication" in project-a
    results_a = await search_code(
        query="authentication logic",
        project_id="client-a"
    )

    # Step 4: Verify only Client A results returned
    assert len(results_a["results"]) > 0
    assert results_a["project_id"] == "client-a"
    assert all("authenticate_user_a" in r["content"] for r in results_a["results"])
    assert all("client-b" not in r["file_path"].lower() for r in results_a["results"])

    # Step 5: Search "authentication" in project-b
    results_b = await search_code(
        query="authentication logic",
        project_id="client-b"
    )

    # Step 6: Verify only Client B results returned
    assert len(results_b["results"]) > 0
    assert results_b["project_id"] == "client-b"
    assert all("authenticate_user_b" in r["content"] for r in results_b["results"])
    assert all("client-a" not in r["file_path"].lower() for r in results_b["results"])

    # Step 7: Verify no overlap between result sets
    files_a = {r["file_path"] for r in results_a["results"]}
    files_b = {r["file_path"] for r in results_b["results"]}
    assert files_a.isdisjoint(files_b), "Cross-project data leakage detected!"
```

### Expected Outcome
✅ Test passes: Zero cross-contamination between projects

---

## Test Scenario 2: Project Switching

**Validates**: Primary Workflow steps 7-10, Acceptance Scenario 2
**Traces to**: FR-002 (search parameter), FR-009 (isolated workspace)

### Test Steps
```python
@pytest.mark.integration
async def test_project_switching(repo_a, repo_b):
    """Verify switching between projects returns different results."""

    # Setup: Index both repositories
    await index_repository(repo_path=repo_a, project_id="project-a")
    await index_repository(repo_path=repo_b, project_id="project-b")

    # Step 1: Search in project-a
    results_first = await search_code(
        query="authentication",
        project_id="project-a"
    )
    assert results_first["project_id"] == "project-a"
    assert len(results_first["results"]) > 0

    # Step 2: Switch to project-b (same query)
    results_second = await search_code(
        query="authentication",
        project_id="project-b"
    )
    assert results_second["project_id"] == "project-b"
    assert len(results_second["results"]) > 0

    # Step 3: Verify results are completely different
    content_a = [r["content"] for r in results_first["results"]]
    content_b = [r["content"] for r in results_second["results"]]

    # No content overlap (different implementations)
    assert all(c not in content_b for c in content_a)
    assert all(c not in content_a for c in content_b)
```

### Expected Outcome
✅ Test passes: Same query returns different results per project

---

## Test Scenario 3: Auto-Provisioning New Project

**Validates**: Alternative Path (New Project Creation), Acceptance Scenario 3
**Traces to**: FR-010 (auto-provisioning), FR-011 (permission validation)

### Test Steps
```python
@pytest.mark.integration
async def test_auto_provisioning(repo_a):
    """Verify automatic workspace creation on first use."""

    # Step 1: Use new project identifier (never created before)
    new_project_id = "client-xyz"

    # Step 2: Verify schema does not exist yet
    async with get_session() as session:
        result = await session.execute(text(
            "SELECT 1 FROM information_schema.schemata "
            "WHERE schema_name = :schema_name"
        ), {"schema_name": f"project_{new_project_id}"})
        assert result.scalar() is None, "Schema should not exist yet"

    # Step 3: Index repository (triggers auto-provisioning)
    result = await index_repository(
        repo_path=repo_a,
        project_id=new_project_id
    )

    # Step 4: Verify workspace was created automatically
    assert result["status"] == "success"
    assert result["project_id"] == new_project_id
    assert result["schema_name"] == f"project_{new_project_id}"

    # Step 5: Verify schema now exists in PostgreSQL
    async with get_session() as session:
        result = await session.execute(text(
            "SELECT 1 FROM information_schema.schemata "
            "WHERE schema_name = :schema_name"
        ), {"schema_name": f"project_{new_project_id}"})
        assert result.scalar() == 1, "Schema should exist after provisioning"

    # Step 6: Verify workspace registered in global registry
    async with get_session() as session:
        result = await session.execute(text(
            "SELECT schema_name FROM project_registry.workspace_config "
            "WHERE project_id = :project_id"
        ), {"project_id": new_project_id})
        schema_name = result.scalar()
        assert schema_name == f"project_{new_project_id}"
```

### Expected Outcome
✅ Test passes: New project workspace created automatically without errors

---

## Test Scenario 4: Workflow-MCP Integration

**Validates**: Alternative Path (Workflow Automation Integration), Acceptance Scenario 4
**Traces to**: FR-012 (workflow-mcp query), FR-013 (graceful degradation)

### Test Steps
```python
@pytest.mark.integration
async def test_workflow_mcp_integration(repo_a, mocker):
    """Verify automatic project detection from workflow-mcp."""

    # Setup: Mock workflow-mcp server response
    mock_response = mocker.Mock()
    mock_response.json.return_value = {"project_id": "active-project"}
    mock_response.raise_for_status.return_value = None

    mocker.patch(
        "httpx.AsyncClient.get",
        return_value=mock_response
    )

    # Step 1: Index repository (workflow-mcp available)
    await index_repository(
        repo_path=repo_a,
        project_id="active-project"  # Explicitly set for setup
    )

    # Step 2: Search WITHOUT specifying project_id (auto-detect)
    results = await search_code(
        query="authentication",
        project_id=None  # Trigger workflow-mcp integration
    )

    # Step 3: Verify workflow-mcp was queried
    assert results["project_id"] == "active-project"
    mock_response.raise_for_status.assert_called_once()
```

### Expected Outcome
✅ Test passes: workflow-mcp provides active project automatically

---

## Test Scenario 5: Workflow-MCP Timeout Fallback

**Validates**: Edge Case (Workflow Integration Timeout), Acceptance Scenario 5
**Traces to**: FR-013 (graceful degradation), FR-014 (failure categorization)

### Test Steps
```python
@pytest.mark.integration
async def test_workflow_mcp_timeout(repo_a, mocker):
    """Verify fallback to default workspace on timeout."""

    # Setup: Mock workflow-mcp timeout
    mocker.patch(
        "httpx.AsyncClient.get",
        side_effect=httpx.TimeoutException("Request timeout")
    )

    # Setup: Index in default workspace
    await index_repository(repo_path=repo_a, project_id=None)

    # Step 1: Search without project_id (triggers timeout)
    results = await search_code(
        query="authentication",
        project_id=None  # Should timeout and fallback
    )

    # Step 2: Verify fallback to default workspace
    assert results["project_id"] is None  # Default workspace
    assert results["schema_name"] == "project_default"
    assert len(results["results"]) > 0  # Data still accessible

    # Step 3: Verify timeout logged (check logs)
    # Note: Log assertion requires log capture fixture
    # assert "workflow-mcp timeout" in captured_logs
```

### Expected Outcome
✅ Test passes: System falls back to default workspace on timeout

---

## Test Scenario 6: Invalid Project Identifier

**Validates**: Edge Case (Invalid Characters), Acceptance Scenario 6
**Traces to**: FR-004 (validation), FR-005 (format enforcement), FR-016 (security)

### Test Steps
```python
@pytest.mark.parametrize("invalid_id,expected_error", [
    ("My_Project", "lowercase alphanumeric"),
    ("-project", "Cannot start/end with hyphen"),
    ("project-", "Cannot start/end with hyphen"),
    ("project--name", "consecutive hyphens"),
    ("project'; DROP TABLE--", "lowercase alphanumeric"),  # SQL injection
])
@pytest.mark.integration
async def test_invalid_project_identifier(repo_a, invalid_id, expected_error):
    """Verify invalid identifiers rejected with clear errors."""

    # Step 1: Attempt to index with invalid identifier
    with pytest.raises(ValidationError) as exc_info:
        await index_repository(
            repo_path=repo_a,
            project_id=invalid_id
        )

    # Step 2: Verify error message is clear and actionable
    error = exc_info.value
    assert expected_error in str(error).lower()
    assert "project_id" in str(error)  # Field-level error
    assert invalid_id in str(error)  # Shows invalid value

    # Step 3: Verify no database operations occurred
    async with get_session() as session:
        result = await session.execute(text(
            "SELECT 1 FROM information_schema.schemata "
            "WHERE schema_name LIKE :pattern"
        ), {"pattern": f"%{invalid_id}%"})
        assert result.scalar() is None, "No schema should be created"
```

### Expected Outcome
✅ Test passes: Invalid identifiers rejected before database operations

---

## Test Scenario 7: Backward Compatibility

**Validates**: FR-018 (backward compatibility), Default Workspace
**Traces to**: FR-003 (default workspace)

### Test Steps
```python
@pytest.mark.integration
async def test_backward_compatibility(repo_a):
    """Verify existing usage without project_id works unchanged."""

    # Step 1: Index without project_id (legacy behavior)
    result = await index_repository(
        repo_path=repo_a
        # project_id parameter OMITTED (backward compatibility)
    )

    # Step 2: Verify uses default workspace automatically
    assert result["status"] == "success"
    assert result["project_id"] is None  # No explicit project
    assert result["schema_name"] == "project_default"

    # Step 3: Search without project_id (legacy behavior)
    results = await search_code(
        query="authentication"
        # project_id parameter OMITTED
    )

    # Step 4: Verify searches default workspace
    assert results["project_id"] is None
    assert results["schema_name"] == "project_default"
    assert len(results["results"]) > 0  # Data accessible
```

### Expected Outcome
✅ Test passes: Existing users' workflows continue unchanged

---

## Test Scenario 8: Performance - Project Switching Latency

**Validates**: Constitutional Principle IV (Performance Guarantees)
**Traces to**: Technical Context performance goal (<50ms switching)

### Test Steps
```python
@pytest.mark.performance
async def test_project_switching_performance(repo_a, repo_b, benchmark):
    """Verify project switching meets <50ms latency target."""

    # Setup: Index two projects
    await index_repository(repo_path=repo_a, project_id="perf-a")
    await index_repository(repo_path=repo_b, project_id="perf-b")

    # Benchmark: Switch between projects
    async def switch_and_query():
        # Switch to project-a
        await search_code(query="test", project_id="perf-a", limit=1)

        # Switch to project-b
        await search_code(query="test", project_id="perf-b", limit=1)

    # Run benchmark
    result = benchmark(switch_and_query)

    # Verify latency (50ms target per switch = 100ms total for 2 switches)
    assert result.stats.mean < 0.100, f"Mean latency: {result.stats.mean}s (target: <0.100s)"
    assert result.stats.max < 0.150, f"Max latency: {result.stats.max}s (should be <0.150s)"
```

### Expected Outcome
✅ Test passes: Project switching <50ms per operation

---

## Test Scenario 9: Security - SQL Injection Prevention

**Validates**: Edge Case (SQL Injection Attempt), Acceptance Scenario (Security)
**Traces to**: FR-016 (security vulnerabilities prevention)

### Test Steps
```python
@pytest.mark.security
@pytest.mark.parametrize("injection_attempt", [
    "project'; DROP TABLE code_chunks--",
    "project/**/OR/**/1=1--",
    "project\"; DELETE FROM repositories WHERE 1=1--",
    "project' UNION SELECT * FROM pg_shadow--",
])
async def test_sql_injection_prevention(repo_a, injection_attempt):
    """Verify SQL injection attempts blocked by validation."""

    # Step 1: Attempt injection via project_id parameter
    with pytest.raises(ValidationError) as exc_info:
        await index_repository(
            repo_path=repo_a,
            project_id=injection_attempt
        )

    # Step 2: Verify validation blocked injection BEFORE SQL execution
    error = exc_info.value
    assert "lowercase alphanumeric" in str(error).lower()

    # Step 3: Verify database integrity (no tables dropped)
    async with get_session() as session:
        # Verify code_chunks table still exists
        result = await session.execute(text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_name = 'code_chunks'"
        ))
        assert result.scalar() == 1, "code_chunks table should still exist"

    # Step 4: Verify security event logged
    # Note: Requires log capture fixture
    # assert "SQL injection attempt blocked" in captured_logs
```

### Expected Outcome
✅ Test passes: All SQL injection attempts blocked before reaching database

---

## Test Execution

### Run All Integration Tests
```bash
# Run all quickstart scenarios
pytest specs/008-multi-project-workspace/quickstart.md --doctest-modules -v

# Run specific category
pytest specs/008-multi-project-workspace/quickstart.md -m integration -v
pytest specs/008-multi-project-workspace/quickstart.md -m performance -v
pytest specs/008-multi-project-workspace/quickstart.md -m security -v
```

### Coverage Requirements
- **All scenarios must pass** before feature is considered complete
- **Performance tests** must meet Constitutional Principle IV targets
- **Security tests** must block 100% of injection attempts
- **Isolation tests** must guarantee zero cross-contamination

---

## Success Criteria Validation

| Scenario | Validates | Pass Criteria |
|----------|-----------|---------------|
| 1. Complete Data Isolation | FR-017 | Zero cross-project results |
| 2. Project Switching | FR-002, FR-009 | Different results per project |
| 3. Auto-Provisioning | FR-010, FR-011 | Schema created automatically |
| 4. Workflow-MCP Integration | FR-012 | Auto-detects active project |
| 5. Workflow-MCP Timeout | FR-013, FR-014 | Falls back to default |
| 6. Invalid Identifier | FR-004, FR-005, FR-016 | Rejects with clear error |
| 7. Backward Compatibility | FR-018 | Existing usage works |
| 8. Performance | Principle IV | <50ms switching |
| 9. Security | FR-016 | Blocks all injections |

**Feature Complete When**: All 9 scenarios pass ✅
