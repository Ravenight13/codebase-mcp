# Feature 003 Testing Prompt

## Context
This is Feature 003: Database-Backed Project Tracking System for the Codebase MCP Server. The implementation adds polymorphic work items (project, session, task, research) with hierarchical relationships, optimistic locking, and vendor tracking.

## Testing Tasks

### 1. Database Migration Verification
```bash
# Check current migration status
alembic current
# Expected: 003b (head)

# Verify all tables exist
psql -d codebase_mcp -c "\dt"
# Expected tables: tasks, vendor_extractors, deployment_events,
# project_configuration, future_enhancements, work_item_dependencies,
# vendor_deployment_links, work_item_deployment_links, archived_work_items
```

### 2. Model Import Test
```bash
# Verify all models import without errors
python -c "from src.models.task import WorkItem, Task
from src.models.tracking import VendorExtractor, DeploymentEvent, ProjectConfiguration
from src.services.locking import OptimisticLockError
print('✓ All models import successfully')"
```

### 3. Service Layer Tests
```bash
# Test hierarchy service
python -c "from src.services.hierarchy import get_ancestors, get_descendants
print('✓ Hierarchy service available')"

# Test locking service
python -c "from src.services.locking import get_current_version, update_with_version_check
print('✓ Locking service available')"

# Test vendor service
python -c "from src.services.vendor import query_vendor_by_name
print('✓ Vendor service available')"
```

### 4. MCP Tools Registration
```bash
# Start the MCP server and verify tools are registered
# Expected new tools:
# - create_work_item
# - update_work_item
# - query_work_item
# - list_work_items

# Test via Claude Desktop or MCP Inspector
```

### 5. Run Unit Tests
```bash
# Run existing unit tests to ensure backward compatibility
pytest tests/unit/ -v --tb=short

# Expected: All tests pass (142 tests)
```

### 6. Run Integration Tests (if available)
```bash
# Run vendor query performance test
pytest tests/integration/test_vendor_query_performance.py -v -s

# Run concurrent work item updates test
pytest tests/integration/test_concurrent_work_item_updates.py -v -s

# Run hierarchical work item query test
pytest tests/integration/test_hierarchical_work_item_query.py -v -s
```

### 7. Manual Functional Tests

#### Test 7.1: Create Hierarchical Work Items
```python
# In Python REPL or notebook
import asyncio
from src.database.session import get_session
from src.models.task import WorkItem
from uuid import uuid4

async def test_hierarchy():
    async with get_session() as session:
        # Create parent project
        project = WorkItem(
            item_type="project",
            title="Test Project",
            status="active",
            path="/",
            depth=0,
            created_by="test-user"
        )
        session.add(project)
        await session.flush()

        # Create child task
        task = WorkItem(
            item_type="task",
            title="Child Task",
            status="active",
            parent_id=project.id,
            path=f"/{project.id}",
            depth=1,
            created_by="test-user"
        )
        session.add(task)
        await session.commit()

        print(f"✓ Created project {project.id} with child task {task.id}")

asyncio.run(test_hierarchy())
```

#### Test 7.2: Optimistic Locking
```python
import asyncio
from src.database.session import get_session
from src.models.task import WorkItem
from src.services.locking import update_with_version_check, OptimisticLockError

async def test_locking():
    async with get_session() as session:
        # Create work item
        item = WorkItem(
            item_type="task",
            title="Locking Test",
            status="active",
            path="/",
            depth=0,
            created_by="test-user"
        )
        session.add(item)
        await session.flush()
        initial_version = item.version

        # First update succeeds
        updated = await update_with_version_check(
            entity=item,
            updates={"title": "Updated Title"},
            expected_version=initial_version,
            session=session
        )
        await session.commit()
        print(f"✓ First update succeeded, version: {updated.version}")

        # Second update with old version fails
        try:
            await update_with_version_check(
                entity=updated,
                updates={"title": "Another Update"},
                expected_version=initial_version,  # Old version
                session=session
            )
            print("✗ Should have raised OptimisticLockError")
        except OptimisticLockError as e:
            print(f"✓ Optimistic locking works: {e}")

asyncio.run(test_locking())
```

#### Test 7.3: Vendor Tracking
```python
import asyncio
from src.database.session import get_session
from src.models.tracking import VendorExtractor

async def test_vendor():
    async with get_session() as session:
        # Create vendor
        vendor = VendorExtractor(
            name="test-vendor",
            status="operational",
            created_by="test-user"
        )
        session.add(vendor)
        await session.commit()
        print(f"✓ Created vendor {vendor.id}: {vendor.name}")

asyncio.run(test_vendor())
```

## Expected Results

✅ **Success Criteria**:
1. All migrations applied (003b)
2. All models import successfully
3. All services import successfully
4. MCP tools registered and callable
5. Unit tests pass (142/142)
6. Hierarchical relationships work correctly
7. Optimistic locking prevents concurrent update conflicts
8. Vendor tracking operational

❌ **Known Issues** (from HANDOFF.md):
1. 14 contract test failures (Pydantic validation incomplete - expected)
2. 2 integration test failures (application logic bugs - documented)
3. 6 hierarchical test failures (async fixture issues - documented)

## Performance Targets

- Vendor queries: <1ms p95 (FR-002)
- Hierarchical queries: <10ms p95 for 5 levels (FR-013)
- Status generation: <100ms (FR-023)

## Documentation

See these files for comprehensive information:
- `HANDOFF.md` - Complete handoff guide with troubleshooting
- `docs/2025-10-10-FINAL-IMPLEMENTATION-SUMMARY.md` - Implementation summary
- `docs/2025-10-10-phase-3.6-validation-summary.md` - Validation results
- `specs/003-database-backed-project/tasks.md` - Task breakdown (48/52 complete)

## Branch Information

- **Current Branch**: `003-database-backed-project`
- **Base Branch**: `master` (rebased)
- **Status**: 92.3% complete (48/52 tasks)
- **Ready for**: Integration testing and bug fixes

## Contact

For issues or questions, refer to:
- HANDOFF.md troubleshooting section
- Known issues in docs/2025-10-10-phase-3.6-validation-summary.md
