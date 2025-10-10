# Quickstart: Project Status and Work Item Tracking Integration Tests

**Feature**: 003-database-backed-project
**Branch**: `003-database-backed-project`
**Date**: 2025-10-10
**Related**: [spec.md](./spec.md) | [plan.md](./plan.md) | [data-model.md](./data-model.md)

## Overview

This quickstart maps all 8 acceptance scenarios from the feature specification to executable integration tests. Each test validates functional requirements, performance targets, and error handling behaviors for the database-backed project status tracking system.

## Prerequisites

### Database Setup
```bash
# 1. Ensure PostgreSQL 14+ is running
pg_ctl status

# 2. Create test database
createdb codebase_mcp_test

# 3. Run migrations
alembic upgrade head

# 4. Verify pgvector extension
psql codebase_mcp_test -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

### Test Data Seeding
```bash
# Seed test fixtures (vendors, work items, deployments)
python scripts/seed_test_data.py --environment test

# Verify seeded data
psql codebase_mcp_test -c "SELECT COUNT(*) FROM vendor_extractors;"  # Should show 45+
psql codebase_mcp_test -c "SELECT COUNT(*) FROM work_items;"          # Should show 100+
```

### Environment Configuration
```bash
# Set test environment variables
export DATABASE_URL="postgresql://localhost/codebase_mcp_test"
export SQLITE_CACHE_PATH="/tmp/codebase_mcp_cache.db"
export MARKDOWN_FALLBACK_PATH=".project_status.md"
export ENABLE_FALLBACK="true"
```

## Integration Test Scenarios

### Scenario 1: Vendor Query Performance

**Acceptance Criteria**: Given an AI assistant needs to check vendor extractor health, when it queries vendor status via MCP tool, then it receives current operational status, test results (passing/total/skipped), format support flags, and version information in under 1ms.

**Test File**: `tests/integration/test_vendor_query_performance.py`

**Test Setup**:
```python
@pytest.fixture
async def seeded_vendors(test_db):
    """Seed 45 vendor extractors with operational status"""
    vendors = [
        VendorExtractor(
            name=f"vendor_{i}",
            operational=True,
            metadata={
                "format_support": {"excel": True, "csv": True, "pdf": False, "ocr": False},
                "test_results": {"passing": 10, "total": 12, "skipped": 2},
                "extractor_version": "1.2.3",
                "manifest_compliant": True
            }
        )
        for i in range(45)
    ]
    async with test_db.session() as session:
        session.add_all(vendors)
        await session.commit()
    return vendors
```

**Test Scenario (Given-When-Then)**:
```python
async def test_vendor_query_performance(mcp_client, seeded_vendors):
    """Given: 45 vendors in database
       When: Query specific vendor via query_vendor_status MCP tool
       Then: Response received in <1ms with complete metadata
    """
    vendor_name = "vendor_0"

    # Measure query performance
    start_time = time.perf_counter()
    response = await mcp_client.call_tool("query_vendor_status", {"name": vendor_name})
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # Performance assertion
    assert elapsed_ms < 1.0, f"Vendor query took {elapsed_ms:.3f}ms (target: <1ms)"

    # Data correctness assertions
    assert response["name"] == vendor_name
    assert response["operational"] is True
    assert response["metadata"]["test_results"]["passing"] == 10
    assert response["metadata"]["test_results"]["total"] == 12
    assert response["metadata"]["test_results"]["skipped"] == 2
    assert response["metadata"]["format_support"]["excel"] is True
    assert response["metadata"]["extractor_version"] == "1.2.3"
    assert response["metadata"]["manifest_compliant"] is True
```

**Expected Execution Time**: 0.5-0.8ms (target: <1ms)

---

### Scenario 2: Concurrent Work Item Updates

**Acceptance Criteria**: Given an AI assistant is working on a task within a work session, when it updates task status via MCP tool, then the change is persisted with audit trail (created_by = AI client identifier, updated_at) and immediately visible to other AI clients.

**Test File**: `tests/integration/test_concurrent_work_item_updates.py`

**Test Setup**:
```python
@pytest.fixture
async def work_item_with_version(test_db):
    """Create a work item with initial version=1"""
    item = WorkItem(
        item_type="task",
        title="Test Task",
        version=1,
        created_by="claude-code",
        metadata={"estimated_hours": 2.0}
    )
    async with test_db.session() as session:
        session.add(item)
        await session.commit()
        await session.refresh(item)
    return item
```

**Test Scenario (Given-When-Then)**:
```python
async def test_optimistic_locking_prevents_conflicts(mcp_client1, mcp_client2, work_item_with_version):
    """Given: Two AI clients (claude-code, claude-desktop) access same work item
       When: Both attempt concurrent updates with same version
       Then: First succeeds, second fails with version mismatch error
    """
    item_id = str(work_item_with_version.id)

    # Client 1 updates with version=1
    response1 = await mcp_client1.call_tool(
        "update_work_item",
        {
            "id": item_id,
            "version": 1,
            "metadata": {"estimated_hours": 3.0},
            "created_by": "claude-code"
        }
    )
    assert response1["success"] is True
    assert response1["version"] == 2  # Version incremented

    # Client 2 attempts update with stale version=1 (should fail)
    with pytest.raises(VersionMismatchError) as exc_info:
        await mcp_client2.call_tool(
            "update_work_item",
            {
                "id": item_id,
                "version": 1,  # Stale version
                "metadata": {"estimated_hours": 4.0},
                "created_by": "claude-desktop"
            }
        )

    assert "version mismatch" in str(exc_info.value).lower()
    assert exc_info.value.expected_version == 1
    assert exc_info.value.actual_version == 2

    # Verify audit trail
    final_item = await mcp_client1.call_tool("query_work_item", {"id": item_id})
    assert final_item["metadata"]["estimated_hours"] == 3.0
    assert final_item["version"] == 2
    assert final_item["created_by"] == "claude-code"
    assert "updated_at" in final_item
```

**Additional Test Case**: Immediate visibility across clients
```python
async def test_concurrent_updates_immediate_visibility(mcp_client1, mcp_client2, work_item_with_version):
    """Given: Multiple AI clients querying work items
       When: One client updates a work item
       Then: Other clients see change on next query
    """
    item_id = str(work_item_with_version.id)

    # Client 1 updates
    await mcp_client1.call_tool(
        "update_work_item",
        {"id": item_id, "version": 1, "title": "Updated by Client 1"}
    )

    # Client 2 queries immediately
    result = await mcp_client2.call_tool("query_work_item", {"id": item_id})

    # Assert immediate visibility
    assert result["title"] == "Updated by Client 1"
    assert result["version"] == 2
```

**Expected Execution Time**: 5-10ms per update

---

### Scenario 3: Deployment Event Recording

**Acceptance Criteria**: Given a deployment has occurred, when deployment metadata is recorded via MCP tool, then the system captures PR merge details, commit hash, timestamp, related work items, affected vendors, test results, and constitutional compliance status.

**Test File**: `tests/integration/test_deployment_event_recording.py`

**Test Setup**:
```python
@pytest.fixture
async def deployment_context(test_db):
    """Seed vendors and work items for deployment"""
    vendors = [
        VendorExtractor(name="vendor_a", operational=True),
        VendorExtractor(name="vendor_b", operational=True)
    ]
    work_items = [
        WorkItem(item_type="task", title="Task 1"),
        WorkItem(item_type="task", title="Task 2")
    ]
    async with test_db.session() as session:
        session.add_all(vendors + work_items)
        await session.commit()
        for item in vendors + work_items:
            await session.refresh(item)
    return {
        "vendor_ids": [v.id for v in vendors],
        "work_item_ids": [w.id for w in work_items]
    }
```

**Test Scenario (Given-When-Then)**:
```python
async def test_deployment_event_recording(mcp_client, deployment_context):
    """Given: Deployment with PR merge, affected vendors, and work items
       When: Record deployment via record_deployment MCP tool
       Then: Complete metadata persisted with relationships
    """
    deployment_data = {
        "metadata": {
            "pr_number": 123,
            "pr_title": "Add vendor support for XYZ",
            "commit_hash": "a" * 40,  # Valid 40-char hex
            "test_summary": {"passed": 45, "failed": 0, "skipped": 2},
            "constitutional_compliance": True
        },
        "vendor_ids": deployment_context["vendor_ids"],
        "work_item_ids": deployment_context["work_item_ids"]
    }

    response = await mcp_client.call_tool("record_deployment", deployment_data)

    # Assertions
    assert response["success"] is True
    deployment_id = response["id"]

    # Verify deployment metadata
    deployment = await mcp_client.call_tool("query_deployment", {"id": deployment_id})
    assert deployment["metadata"]["pr_number"] == 123
    assert deployment["metadata"]["pr_title"] == "Add vendor support for XYZ"
    assert deployment["metadata"]["commit_hash"] == "a" * 40
    assert deployment["metadata"]["test_summary"]["passed"] == 45
    assert deployment["metadata"]["constitutional_compliance"] is True
    assert "timestamp" in deployment

    # Verify vendor relationships
    assert len(deployment["affected_vendors"]) == 2
    vendor_names = [v["name"] for v in deployment["affected_vendors"]]
    assert "vendor_a" in vendor_names
    assert "vendor_b" in vendor_names

    # Verify work item relationships
    assert len(deployment["related_work_items"]) == 2
    work_item_titles = [w["title"] for w in deployment["related_work_items"]]
    assert "Task 1" in work_item_titles
    assert "Task 2" in work_item_titles
```

**Expected Execution Time**: 10-15ms

---

### Scenario 4: Database Unavailable Fallback

**Acceptance Criteria**: Given the database becomes unavailable, when an AI assistant queries project status, then the system falls back through cache (30-min TTL) → git history → manual markdown file without hard failure, returning warnings instead of errors.

**Test File**: `tests/integration/test_database_unavailable_fallback.py`

**Test Setup**:
```python
@pytest.fixture
async def fallback_context(test_db, tmp_path):
    """Setup 4-layer fallback infrastructure"""
    # Layer 1: PostgreSQL (will be disabled in test)
    # Layer 2: SQLite cache
    sqlite_path = tmp_path / "cache.db"
    cache = SQLiteCache(sqlite_path)

    # Layer 3: Git history (mock)
    git_history = GitHistoryFallback()

    # Layer 4: Markdown file
    markdown_path = tmp_path / ".project_status.md"
    markdown_path.write_text("""
    # Project Status
    ## Vendors
    - vendor_a: operational
    - vendor_b: operational
    """)

    return {
        "cache": cache,
        "git_history": git_history,
        "markdown_path": markdown_path
    }
```

**Test Scenario (Given-When-Then)**:
```python
async def test_four_layer_fallback_cascade(mcp_client, fallback_context, mock_db_failure):
    """Given: Database becomes unavailable
       When: Query vendor status via MCP tool
       Then: System falls back through 4 layers without hard failure
    """
    # Simulate PostgreSQL failure
    mock_db_failure.enable()

    # Attempt query (should fall back to SQLite cache)
    response = await mcp_client.call_tool("query_vendor_status", {"name": "vendor_a"})

    # Assertions
    assert response["success"] is True
    assert response["name"] == "vendor_a"
    assert response["operational"] is True
    assert "warnings" in response
    assert "using_fallback_cache" in response["warnings"]

    # Verify fallback layer used
    assert response["data_source"] == "sqlite_cache"
    assert response["cache_age_minutes"] < 30  # Within TTL

async def test_cache_miss_falls_back_to_git(mcp_client, fallback_context, mock_db_failure):
    """Given: Database down AND cache miss
       When: Query vendor status
       Then: Falls back to git history
    """
    mock_db_failure.enable()
    fallback_context["cache"].clear()  # Force cache miss

    response = await mcp_client.call_tool("query_vendor_status", {"name": "vendor_a"})

    assert response["success"] is True
    assert response["data_source"] == "git_history"
    assert "using_git_history_fallback" in response["warnings"]

async def test_final_fallback_to_markdown(mcp_client, fallback_context, mock_db_failure, mock_git_failure):
    """Given: Database down, cache miss, git unavailable
       When: Query vendor status
       Then: Falls back to manual markdown file
    """
    mock_db_failure.enable()
    mock_git_failure.enable()
    fallback_context["cache"].clear()

    response = await mcp_client.call_tool("query_vendor_status", {"name": "vendor_a"})

    assert response["success"] is True
    assert response["data_source"] == "markdown_file"
    assert "using_markdown_fallback" in response["warnings"]
    assert response["name"] == "vendor_a"
    assert response["operational"] is True

async def test_writes_during_database_unavailability(mcp_client, fallback_context, mock_db_failure):
    """Given: Database unavailable
       When: AI client updates work item
       Then: Writes to SQLite cache AND markdown file in parallel
    """
    mock_db_failure.enable()

    response = await mcp_client.call_tool(
        "update_work_item",
        {"id": str(uuid.uuid4()), "version": 1, "title": "Updated During Outage"}
    )

    # Verify parallel writes
    assert response["success"] is True
    assert response["wrote_to_cache"] is True
    assert response["wrote_to_markdown"] is True
    assert "database_unavailable" in response["warnings"]

    # Verify cache contains update
    cached_item = await fallback_context["cache"].get_work_item(response["id"])
    assert cached_item["title"] == "Updated During Outage"

    # Verify markdown file contains update
    markdown_content = fallback_context["markdown_path"].read_text()
    assert "Updated During Outage" in markdown_content
```

**Expected Execution Time**: 20-50ms (varies by fallback layer)

---

### Scenario 5: Migration Data Preservation

**Acceptance Criteria**: Given legacy .project_status.md data exists, when migration is executed, then 100% of historical data is preserved and validated through five reconciliation checks (vendor count, deployment history, enhancements count, session prompt count, vendor metadata completeness).

**Test File**: `tests/integration/test_migration_data_preservation.py`

**Test Setup**:
```python
@pytest.fixture
def legacy_markdown_file(tmp_path):
    """Create legacy .project_status.md with complete data"""
    content = """
# Project Status

## Vendors (45 total)
- vendor_1: operational (10/12 tests passed, 2 skipped) [Excel, CSV] v1.2.3
- vendor_2: broken (5/10 tests passed, 0 skipped) [PDF, OCR] v2.0.1
... (43 more vendors)

## Deployments (12 total)
### 2025-10-01 - PR #100
- Commit: abc123...
- Work Items: #T001, #T002
- Vendors: vendor_1, vendor_2
- Tests: 45 passed, 0 failed
- Constitutional Compliance: ✓

... (11 more deployments)

## Future Enhancements (8 total)
- Enhancement A (Priority: High, Q1 2026)
- Enhancement B (Priority: Medium, Q2 2026)
... (6 more enhancements)

## Session Prompts (25 total)
### Session 2025-10-01
---
session_id: sess_001
token_budget: 50000
---
Prompt content...
"""
    markdown_path = tmp_path / ".project_status.md"
    markdown_path.write_text(content)
    return markdown_path
```

**Test Scenario (Given-When-Then)**:
```python
async def test_complete_migration_with_validation(test_db, legacy_markdown_file, migration_service):
    """Given: Legacy markdown file with 45 vendors, 12 deployments, 8 enhancements, 25 sessions
       When: Execute migration
       Then: 100% data preserved with all 5 reconciliation checks passing
    """
    # Execute migration
    result = await migration_service.migrate_from_markdown(legacy_markdown_file)

    # Overall success assertion
    assert result["success"] is True
    assert result["data_preservation_percentage"] == 100.0

    # Reconciliation Check 1: Vendor count
    assert result["reconciliation"]["vendor_count"]["source"] == 45
    assert result["reconciliation"]["vendor_count"]["migrated"] == 45
    assert result["reconciliation"]["vendor_count"]["match"] is True

    # Reconciliation Check 2: Deployment history completeness
    assert result["reconciliation"]["deployment_history"]["source"] == 12
    assert result["reconciliation"]["deployment_history"]["migrated"] == 12
    assert result["reconciliation"]["deployment_history"]["match"] is True

    # Reconciliation Check 3: Enhancements count
    assert result["reconciliation"]["enhancements"]["source"] == 8
    assert result["reconciliation"]["enhancements"]["migrated"] == 8
    assert result["reconciliation"]["enhancements"]["match"] is True

    # Reconciliation Check 4: Session prompts count
    assert result["reconciliation"]["session_prompts"]["source"] == 25
    assert result["reconciliation"]["session_prompts"]["migrated"] == 25
    assert result["reconciliation"]["session_prompts"]["match"] is True

    # Reconciliation Check 5: Vendor metadata completeness
    assert result["reconciliation"]["vendor_metadata"]["fields_validated"] == [
        "operational_status", "test_results", "format_support", "version"
    ]
    assert result["reconciliation"]["vendor_metadata"]["completeness_percentage"] == 100.0

    # Verify sample vendor data integrity
    async with test_db.session() as session:
        vendor1 = await session.execute(
            select(VendorExtractor).where(VendorExtractor.name == "vendor_1")
        )
        vendor1 = vendor1.scalar_one()

        assert vendor1.operational is True
        assert vendor1.metadata["test_results"]["passing"] == 10
        assert vendor1.metadata["test_results"]["total"] == 12
        assert vendor1.metadata["test_results"]["skipped"] == 2
        assert vendor1.metadata["format_support"]["excel"] is True
        assert vendor1.metadata["format_support"]["csv"] is True
        assert vendor1.metadata["extractor_version"] == "1.2.3"

async def test_migration_rollback_on_validation_failure(test_db, legacy_markdown_file, migration_service):
    """Given: Migration encounters validation failure
       When: Reconciliation check fails
       Then: Rollback restores original state
    """
    # Corrupt migration to force failure
    migration_service.inject_failure("vendor_count_mismatch")

    result = await migration_service.migrate_from_markdown(legacy_markdown_file)

    # Verify rollback occurred
    assert result["success"] is False
    assert result["rollback_executed"] is True
    assert "validation_failed" in result["errors"]

    # Verify original markdown file restored
    assert legacy_markdown_file.exists()
    assert legacy_markdown_file.read_text().startswith("# Project Status")

    # Verify database state clean (no partial migration)
    async with test_db.session() as session:
        vendor_count = await session.execute(select(func.count(VendorExtractor.id)))
        assert vendor_count.scalar() == 0  # No vendors migrated
```

**Expected Execution Time**: 500-1000ms (full migration)

---

### Scenario 6: Hierarchical Work Item Query

**Acceptance Criteria**: Given an AI assistant needs hierarchical work item context, when it queries a task, then it receives the full parent chain (session → project) and child tasks with dependency relationships up to 5 levels deep in under 10ms.

**Test File**: `tests/integration/test_hierarchical_work_item_query.py`

**Test Setup**:
```python
@pytest.fixture
async def hierarchical_work_items(test_db):
    """Create 5-level work item hierarchy"""
    async with test_db.session() as session:
        # Level 1: Project
        project = WorkItem(item_type="project", title="Project A")
        session.add(project)
        await session.flush()

        # Level 2: Session
        session_item = WorkItem(item_type="session", title="Session 1", parent_id=project.id)
        session.add(session_item)
        await session.flush()

        # Level 3: Task
        task = WorkItem(item_type="task", title="Task 1", parent_id=session_item.id)
        session.add(task)
        await session.flush()

        # Level 4: Subtask
        subtask = WorkItem(item_type="task", title="Subtask 1", parent_id=task.id)
        session.add(subtask)
        await session.flush()

        # Level 5: Sub-subtask
        subsubtask = WorkItem(item_type="task", title="Sub-subtask 1", parent_id=subtask.id)
        session.add(subsubtask)
        await session.flush()

        await session.commit()
        return {
            "project": project,
            "session": session_item,
            "task": task,
            "subtask": subtask,
            "subsubtask": subsubtask
        }
```

**Test Scenario (Given-When-Then)**:
```python
async def test_hierarchical_query_performance(mcp_client, hierarchical_work_items):
    """Given: 5-level work item hierarchy
       When: Query leaf task (level 5)
       Then: Receive full parent chain in <10ms
    """
    leaf_id = str(hierarchical_work_items["subsubtask"].id)

    # Measure query performance
    start_time = time.perf_counter()
    response = await mcp_client.call_tool("query_work_item", {"id": leaf_id})
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # Performance assertion
    assert elapsed_ms < 10.0, f"Hierarchical query took {elapsed_ms:.3f}ms (target: <10ms)"

    # Verify full parent chain returned
    assert response["title"] == "Sub-subtask 1"
    assert len(response["parent_chain"]) == 4  # Excludes self

    parent_titles = [p["title"] for p in response["parent_chain"]]
    assert parent_titles == ["Project A", "Session 1", "Task 1", "Subtask 1"]

    # Verify hierarchy levels
    assert response["parent_chain"][0]["item_type"] == "project"
    assert response["parent_chain"][1]["item_type"] == "session"
    assert response["parent_chain"][2]["item_type"] == "task"
    assert response["parent_chain"][3]["item_type"] == "task"

async def test_query_with_child_tasks(mcp_client, hierarchical_work_items):
    """Given: Task with children
       When: Query parent task
       Then: Receive child tasks in response
    """
    parent_id = str(hierarchical_work_items["task"].id)

    response = await mcp_client.call_tool(
        "query_work_item",
        {"id": parent_id, "include_children": True}
    )

    # Verify children included
    assert len(response["children"]) == 1
    assert response["children"][0]["title"] == "Subtask 1"

    # Verify recursive children (grandchildren)
    assert len(response["children"][0]["children"]) == 1
    assert response["children"][0]["children"][0]["title"] == "Sub-subtask 1"

async def test_dependency_relationships(mcp_client, hierarchical_work_items, test_db):
    """Given: Tasks with dependency relationships
       When: Query task with dependencies
       Then: Receive blocked-by and depends-on relationships
    """
    async with test_db.session() as session:
        task_a = WorkItem(item_type="task", title="Task A")
        task_b = WorkItem(item_type="task", title="Task B")
        session.add_all([task_a, task_b])
        await session.flush()

        # Task B depends on Task A
        dependency = WorkItemDependency(
            work_item_id=task_b.id,
            depends_on_id=task_a.id,
            dependency_type="depends_on"
        )
        session.add(dependency)
        await session.commit()

    response = await mcp_client.call_tool("query_work_item", {"id": str(task_b.id)})

    # Verify dependency included
    assert len(response["dependencies"]) == 1
    assert response["dependencies"][0]["type"] == "depends_on"
    assert response["dependencies"][0]["related_item"]["title"] == "Task A"
```

**Expected Execution Time**: 3-8ms (target: <10ms)

---

### Scenario 7: Multi-Client Concurrent Access

**Acceptance Criteria**: Given multiple AI clients are accessing project status concurrently, when one client updates a work item, then other clients see the change immediately on their next query without conflicts.

**Test File**: `tests/integration/test_multi_client_concurrent_access.py`

**Test Setup**:
```python
@pytest.fixture
async def multi_client_context(test_db):
    """Setup multiple MCP clients"""
    clients = [
        MCPClient("claude-code"),
        MCPClient("claude-desktop"),
        MCPClient("github-copilot")
    ]

    # Seed shared work items
    work_items = [
        WorkItem(item_type="task", title=f"Task {i}", version=1)
        for i in range(10)
    ]
    async with test_db.session() as session:
        session.add_all(work_items)
        await session.commit()
        for item in work_items:
            await session.refresh(item)

    return {"clients": clients, "work_items": work_items}
```

**Test Scenario (Given-When-Then)**:
```python
async def test_immediate_visibility_across_clients(multi_client_context):
    """Given: 3 AI clients connected to same database
       When: Client 1 updates work item
       Then: Clients 2 and 3 see change on next query
    """
    clients = multi_client_context["clients"]
    work_item = multi_client_context["work_items"][0]
    item_id = str(work_item.id)

    # Client 1 updates
    await clients[0].call_tool(
        "update_work_item",
        {"id": item_id, "version": 1, "title": "Updated by Claude Code"}
    )

    # Client 2 queries immediately
    response2 = await clients[1].call_tool("query_work_item", {"id": item_id})
    assert response2["title"] == "Updated by Claude Code"
    assert response2["version"] == 2

    # Client 3 queries immediately
    response3 = await clients[2].call_tool("query_work_item", {"id": item_id})
    assert response3["title"] == "Updated by Claude Code"
    assert response3["version"] == 2

async def test_concurrent_reads_no_conflicts(multi_client_context):
    """Given: Multiple clients reading same work items
       When: All clients query simultaneously
       Then: All receive consistent data without errors
    """
    clients = multi_client_context["clients"]
    work_item = multi_client_context["work_items"][0]
    item_id = str(work_item.id)

    # Execute concurrent reads
    results = await asyncio.gather(*[
        client.call_tool("query_work_item", {"id": item_id})
        for client in clients
    ])

    # Verify all clients received same data
    titles = [r["title"] for r in results]
    assert len(set(titles)) == 1  # All titles identical

    versions = [r["version"] for r in results]
    assert len(set(versions)) == 1  # All versions identical

async def test_concurrent_writes_with_optimistic_locking(multi_client_context):
    """Given: Multiple clients attempting concurrent writes
       When: All clients update with correct version
       Then: Updates applied sequentially, optimistic locking prevents conflicts
    """
    clients = multi_client_context["clients"]
    work_item = multi_client_context["work_items"][0]
    item_id = str(work_item.id)

    # Attempt concurrent updates with same version (should fail for some)
    tasks = [
        clients[i].call_tool(
            "update_work_item",
            {"id": item_id, "version": 1, "title": f"Updated by Client {i}"}
        )
        for i in range(3)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Verify only one succeeded
    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    assert len(successes) == 1, "Only one concurrent write should succeed"
    assert len(failures) == 2, "Two writes should fail with version mismatch"

    # Verify failures are VersionMismatchError
    for failure in failures:
        assert isinstance(failure, VersionMismatchError)

async def test_high_concurrency_load(multi_client_context):
    """Given: 100 concurrent client operations
       When: Mix of reads and writes
       Then: System maintains consistency without deadlocks
    """
    clients = multi_client_context["clients"]
    work_items = multi_client_context["work_items"]

    async def random_operation(client, item):
        """Randomly read or write"""
        if random.random() < 0.7:  # 70% reads
            return await client.call_tool("query_work_item", {"id": str(item.id)})
        else:  # 30% writes
            try:
                return await client.call_tool(
                    "update_work_item",
                    {"id": str(item.id), "version": item.version, "title": f"Update {uuid.uuid4()}"}
                )
            except VersionMismatchError:
                return None  # Expected conflict

    # Execute 100 concurrent operations
    tasks = [
        random_operation(random.choice(clients), random.choice(work_items))
        for _ in range(100)
    ]

    start_time = time.perf_counter()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    elapsed = time.perf_counter() - start_time

    # Verify no deadlocks (all operations completed)
    assert len(results) == 100
    assert elapsed < 5.0, f"100 operations took {elapsed:.2f}s (should be <5s)"

    # Verify database consistency
    async with multi_client_context["test_db"].session() as session:
        items = await session.execute(select(WorkItem))
        items = items.scalars().all()
        assert len(items) == 10  # No items lost
```

**Expected Execution Time**: 50-200ms (varies by concurrency level)

---

### Scenario 8: Full Status Generation Performance

**Acceptance Criteria**: Given an AI assistant needs full project status, when it requests complete status generation, then the system produces vendor health summary, active work items, recent deployments, and pending enhancements in under 100ms.

**Test File**: `tests/integration/test_full_status_generation_performance.py`

**Test Setup**:
```python
@pytest.fixture
async def full_project_data(test_db):
    """Seed complete project data for status generation"""
    async with test_db.session() as session:
        # 45 vendors
        vendors = [
            VendorExtractor(
                name=f"vendor_{i}",
                operational=(i % 3 != 0),  # 2/3 operational
                metadata={
                    "test_results": {"passing": 10, "total": 12, "skipped": 2},
                    "format_support": {"excel": True, "csv": True, "pdf": False, "ocr": False},
                    "extractor_version": "1.2.3",
                    "manifest_compliant": True
                }
            )
            for i in range(45)
        ]

        # 50 active work items (hierarchical)
        work_items = [
            WorkItem(
                item_type=random.choice(["project", "session", "task"]),
                title=f"Work Item {i}",
                metadata={"priority": random.choice(["high", "medium", "low"])}
            )
            for i in range(50)
        ]

        # 10 recent deployments
        deployments = [
            DeploymentEvent(
                metadata={
                    "pr_number": 100 + i,
                    "pr_title": f"Deployment {i}",
                    "commit_hash": "a" * 40,
                    "test_summary": {"passed": 45, "failed": 0, "skipped": 2},
                    "constitutional_compliance": True
                }
            )
            for i in range(10)
        ]

        # 8 future enhancements
        enhancements = [
            FutureEnhancement(
                title=f"Enhancement {i}",
                priority=random.choice(["high", "medium", "low"]),
                target_quarter="Q1 2026"
            )
            for i in range(8)
        ]

        session.add_all(vendors + work_items + deployments + enhancements)
        await session.commit()

    return {
        "vendor_count": 45,
        "work_item_count": 50,
        "deployment_count": 10,
        "enhancement_count": 8
    }
```

**Test Scenario (Given-When-Then)**:
```python
async def test_full_status_generation_performance(mcp_client, full_project_data):
    """Given: Complete project data (45 vendors, 50 work items, 10 deployments, 8 enhancements)
       When: Request full status generation
       Then: Complete status returned in <100ms
    """
    # Measure generation performance
    start_time = time.perf_counter()
    response = await mcp_client.call_tool("generate_full_status", {})
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # Performance assertion
    assert elapsed_ms < 100.0, f"Status generation took {elapsed_ms:.3f}ms (target: <100ms)"

    # Verify vendor health summary
    vendor_summary = response["vendor_health"]
    assert vendor_summary["total_vendors"] == 45
    assert vendor_summary["operational_count"] == 30  # 2/3 of 45
    assert vendor_summary["broken_count"] == 15
    assert vendor_summary["operational_percentage"] == pytest.approx(66.67, rel=0.1)

    # Verify active work items summary
    work_items_summary = response["active_work_items"]
    assert work_items_summary["total_count"] == 50
    assert "by_type" in work_items_summary
    assert "by_priority" in work_items_summary

    # Verify recent deployments (last 10)
    deployments_summary = response["recent_deployments"]
    assert len(deployments_summary) == 10
    assert all("pr_number" in d for d in deployments_summary)
    assert all("timestamp" in d for d in deployments_summary)

    # Verify pending enhancements
    enhancements_summary = response["pending_enhancements"]
    assert len(enhancements_summary) == 8
    assert all("priority" in e for e in enhancements_summary)
    assert all("target_quarter" in e for e in enhancements_summary)

async def test_generated_markdown_format_compatibility(mcp_client, full_project_data):
    """Given: Full status generation complete
       When: Request markdown output
       Then: Output matches legacy .project_status.md format
    """
    response = await mcp_client.call_tool(
        "generate_full_status",
        {"output_format": "markdown"}
    )

    markdown_content = response["markdown"]

    # Verify legacy format structure
    assert "# Project Status" in markdown_content
    assert "## Vendors" in markdown_content
    assert "## Deployments" in markdown_content
    assert "## Future Enhancements" in markdown_content

    # Verify vendor section format
    assert "vendor_0: operational" in markdown_content or "vendor_0: broken" in markdown_content
    assert "(10/12 tests passed, 2 skipped)" in markdown_content

    # Verify deployment section format
    assert "### 2025-" in markdown_content  # Date header
    assert "PR #" in markdown_content
    assert "Commit:" in markdown_content

    # Verify enhancement section format
    assert "Priority:" in markdown_content
    assert "Q1 2026" in markdown_content or "Q2 2026" in markdown_content

async def test_status_generation_with_archiving(mcp_client, full_project_data, test_db):
    """Given: Work items older than 1 year exist
       When: Generate full status
       Then: Only active items included, archived items excluded
    """
    # Create archived work items (older than 1 year)
    async with test_db.session() as session:
        old_items = [
            WorkItem(
                item_type="task",
                title=f"Old Task {i}",
                created_at=datetime.now() - timedelta(days=400)
            )
            for i in range(20)
        ]
        session.add_all(old_items)
        await session.commit()

    # Trigger automatic archiving
    await mcp_client.call_tool("trigger_archiving", {})

    # Generate status
    response = await mcp_client.call_tool("generate_full_status", {})

    # Verify only active items included
    work_items_summary = response["active_work_items"]
    assert work_items_summary["total_count"] == 50  # Excludes 20 archived
    assert work_items_summary["archived_count"] == 20
```

**Expected Execution Time**: 40-80ms (target: <100ms)

---

## Running the Quickstart

### Execute All Integration Tests
```bash
# Run all 8 integration test scenarios
pytest tests/integration/test_*.py -v

# Run with performance profiling
pytest tests/integration/test_*.py -v --durations=10

# Run with coverage report
pytest tests/integration/test_*.py -v --cov=src --cov-report=html
```

### Execute Individual Scenarios
```bash
# Scenario 1: Vendor query performance
pytest tests/integration/test_vendor_query_performance.py -v

# Scenario 2: Concurrent updates with optimistic locking
pytest tests/integration/test_concurrent_work_item_updates.py -v

# Scenario 3: Deployment event recording
pytest tests/integration/test_deployment_event_recording.py -v

# Scenario 4: 4-layer fallback mechanism
pytest tests/integration/test_database_unavailable_fallback.py -v

# Scenario 5: Migration data preservation
pytest tests/integration/test_migration_data_preservation.py -v

# Scenario 6: Hierarchical work item queries
pytest tests/integration/test_hierarchical_work_item_query.py -v

# Scenario 7: Multi-client concurrent access
pytest tests/integration/test_multi_client_concurrent_access.py -v

# Scenario 8: Full status generation performance
pytest tests/integration/test_full_status_generation_performance.py -v
```

### Performance Validation
```bash
# Run only performance-critical tests
pytest tests/integration/ -v -k "performance"

# Verify all performance targets met
pytest tests/integration/ -v --performance-strict
```

## Success Criteria

All 8 acceptance scenarios pass with:
- ✅ Functional correctness (all assertions pass)
- ✅ Performance targets met (<1ms, <10ms, <100ms)
- ✅ Error handling validated (optimistic locking, fallback mechanisms)
- ✅ Data integrity preserved (100% migration validation)
- ✅ Multi-client concurrency supported (immediate visibility, no conflicts)

### Expected Test Summary
```
tests/integration/test_vendor_query_performance.py .................... PASSED (0.7ms)
tests/integration/test_concurrent_work_item_updates.py ............... PASSED (8ms)
tests/integration/test_deployment_event_recording.py ................. PASSED (12ms)
tests/integration/test_database_unavailable_fallback.py .............. PASSED (45ms)
tests/integration/test_migration_data_preservation.py ................ PASSED (850ms)
tests/integration/test_hierarchical_work_item_query.py ............... PASSED (6ms)
tests/integration/test_multi_client_concurrent_access.py ............. PASSED (180ms)
tests/integration/test_full_status_generation_performance.py ......... PASSED (65ms)

========================== 8 passed in 1.17s ==========================
```

## Troubleshooting

### Performance Target Failures
```bash
# If performance tests fail, run with profiling
pytest tests/integration/test_vendor_query_performance.py -v --profile

# Check database indexes
psql codebase_mcp_test -c "\d+ vendor_extractors"
psql codebase_mcp_test -c "\d+ work_items"

# Verify query plans
psql codebase_mcp_test -c "EXPLAIN ANALYZE SELECT * FROM vendor_extractors WHERE name = 'vendor_0';"
```

### Optimistic Locking Conflicts
```bash
# Verify version columns exist
psql codebase_mcp_test -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'work_items' AND column_name = 'version';"

# Check for stale connections
psql codebase_mcp_test -c "SELECT * FROM pg_stat_activity WHERE datname = 'codebase_mcp_test';"
```

### Fallback Mechanism Issues
```bash
# Verify SQLite cache file exists
ls -lh /tmp/codebase_mcp_cache.db

# Check markdown fallback file
cat .project_status.md

# Test database connectivity
pg_isready -d codebase_mcp_test
```

### Migration Validation Failures
```bash
# Check migration logs
cat logs/migration_*.log

# Verify backup file exists
ls -lh .project_status.md.backup

# Inspect reconciliation report
python scripts/validate_migration.py --report
```

## Next Steps

After all quickstart scenarios pass:
1. Review performance profiling results
2. Execute load testing (1000+ concurrent operations)
3. Validate archiving automation (1-year threshold)
4. Test production deployment with real .project_status.md
5. Update CLAUDE.md with final implementation notes
