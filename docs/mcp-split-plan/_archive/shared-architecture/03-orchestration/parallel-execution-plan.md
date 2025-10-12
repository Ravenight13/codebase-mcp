# Parallel Execution Plan: Orchestrated Subagent Patterns

## Overview

The MCP split project uses orchestrated subagent execution to maximize development velocity while maintaining quality. This document defines when to use parallel vs sequential execution, coordination patterns, and real-world examples from the codebase-mcp and workflow-mcp implementation.

---

## Parallel vs Sequential Decision Framework

### When to Use Parallel Subagents

**Criteria for parallelization:**
- ✅ Tasks modify independent files
- ✅ Tasks have no shared state or dependencies
- ✅ Tasks can be tested independently
- ✅ Tasks belong to different modules/packages
- ✅ Errors in one task don't block others

**Examples:**
```markdown
# Parallel: Different files, no dependencies
- [P] T001: Add project_id column to repositories table
- [P] T002: Implement ProjectCache class
- [P] T003: Write integration test for multi-project search

# Parallel: Different modules
- [P] T010: Create work item tools (workflow-mcp)
- [P] T011: Create project tools (workflow-mcp)
- [P] T012: Create entity system (workflow-mcp)
```

### When to Use Sequential Execution

**Criteria for sequential execution:**
- 🔗 Task B depends on Task A output
- 🔗 Tasks modify same file
- 🔗 Tasks share database state that can't be isolated
- 🔗 Task B tests functionality created by Task A
- 🔗 Integration test requires all prior implementations complete

**Examples:**
```markdown
# Sequential: Dependency chain
- [ ] T001: Create migration with project_id columns
- [ ] T002: Run migration (depends on T001)
- [ ] T003: Update search_code to use project_id (depends on T002)

# Sequential: Same file modifications
- [ ] T005: Add project_id parameter to search_code
- [ ] T006: Add error handling to search_code (modifies same function)

# Sequential: Test depends on implementation
- [ ] T007: Implement get_active_project
- [ ] T008: Test get_active_project (depends on T007)
```

### Mixed Patterns (Parallel Then Sequential)

```markdown
# Phase 1: Parallel foundation work
- [P] T001: Database schema changes
- [P] T002: Cache implementation
- [P] T003: Helper functions

# Phase 2: Sequential integration (depends on Phase 1)
- [ ] T004: Update search_code to use helpers (depends on T003)
- [ ] T005: Integration test (depends on T004)
```

---

## Coordination Patterns

### Pattern 1: Independent Module Development

**Use Case:** Building separate tools or modules with no shared code

**Structure:**
```
Orchestrator
  ├─→ Subagent A: Build Tool 1
  ├─→ Subagent B: Build Tool 2
  ├─→ Subagent C: Build Tool 3
  └─→ Subagent D: Build Tool 4

Wait for all subagents (barrier)
  ↓
Orchestrator: Review outputs, run integration tests
```

**Example (Workflow-MCP Tools):**
```markdown
# Parallel subagents
- Subagent A: create_project tool
  - File: src/tools/create_project.py
  - Tests: tests/test_create_project.py

- Subagent B: switch_project tool
  - File: src/tools/switch_project.py
  - Tests: tests/test_switch_project.py

- Subagent C: list_projects tool
  - File: src/tools/list_projects.py
  - Tests: tests/test_list_projects.py

# Sequential orchestrator work (after barrier)
- Orchestrator: Register all tools in FastMCP
  - File: src/server.py
  - Verify: All tools appear in mcp.list_tools()
```

**Coordination:**
1. Orchestrator launches all subagents with clear file paths
2. Each subagent works independently
3. Orchestrator waits for all completions (barrier synchronization)
4. Orchestrator resolves any conflicts (rare if files are truly independent)
5. Orchestrator runs integration tests

### Pattern 2: Dependency Chain with Parallelism

**Use Case:** Some tasks depend on foundation, but can parallelize after

**Structure:**
```
Orchestrator
  ↓
Foundation Task (sequential)
  ↓
Barrier
  ↓
  ├─→ Subagent A: Feature 1 (depends on foundation)
  ├─→ Subagent B: Feature 2 (depends on foundation)
  └─→ Subagent C: Feature 3 (depends on foundation)

Wait for all subagents (barrier)
  ↓
Integration Task (sequential)
```

**Example (Codebase-MCP Schema Migration):**
```markdown
# Sequential foundation
- [ ] T001: Create migration 008_add_project_support.sql
  - Adds project_id columns to tables
  - Must complete before any code uses project_id

# Parallel feature development (depends on T001)
- [P] T002: Update index_repository to use project_id
  - File: src/tools/index_repository.py
  - Depends on: Schema migration (T001)

- [P] T003: Update search_code to use project_id
  - File: src/tools/search_code.py
  - Depends on: Schema migration (T001)

- [P] T004: Add project_id validation helper
  - File: src/helpers/validation.py
  - Depends on: Schema migration (T001)

# Sequential integration (depends on T002-T004)
- [ ] T005: Integration test for multi-project workflow
  - Depends on: All tools updated
```

**Coordination:**
1. Orchestrator runs foundation task first (T001)
2. Orchestrator verifies schema changes applied
3. Orchestrator launches parallel subagents (T002-T004)
4. Each subagent implements feature independently
5. Orchestrator waits for all completions (barrier)
6. Orchestrator runs integration test (T005)

### Pattern 3: Iterative Review with Parallel Tracks

**Use Case:** Independent review subagents for same artifact

**Structure:**
```
Orchestrator
  ↓
Create Artifact (sequential)
  ↓
  ├─→ Review Subagent A: Planning Review
  └─→ Review Subagent B: Architectural Review

Wait for both reviews (barrier)
  ↓
Revision Subagent (sequential, integrates both reviews)
```

**Example (4-Step Planning Workflow):**
```markdown
# Step 1: Initial Plan (sequential)
- Orchestrator: Create initial-plan.md

# Step 2+3: Parallel Reviews
- [P] Planning Review Subagent
  - Input: initial-plan.md
  - Output: planning-review.md
  - Focus: Gaps, ambiguities, completeness

- [P] Architectural Review Subagent
  - Input: initial-plan.md
  - Output: architectural-review.md
  - Focus: Constitutional compliance, tech stack

# Step 4: Final Revision (sequential, depends on Step 2+3)
- Orchestrator: Integrate reviews into plan.md
  - Input: initial-plan.md, planning-review.md, architectural-review.md
  - Output: plan.md (final)
```

**Coordination:**
1. Orchestrator creates initial plan
2. Orchestrator launches both review subagents in parallel
3. Each reviewer focuses on different aspects (no overlap)
4. Orchestrator waits for both reviews (barrier)
5. Orchestrator integrates feedback and produces final plan

### Pattern 4: Fan-Out, Fan-In for Testing

**Use Case:** Run independent test suites in parallel, aggregate results

**Structure:**
```
Orchestrator
  ↓
Implementation Complete (sequential)
  ↓
  ├─→ Test Subagent A: Unit Tests
  ├─→ Test Subagent B: Integration Tests
  ├─→ Test Subagent C: Performance Tests
  └─→ Test Subagent D: MCP Compliance Tests

Wait for all tests (barrier)
  ↓
Orchestrator: Aggregate results, decide pass/fail
```

**Example (Codebase-MCP Test Suite):**
```markdown
# Parallel test execution
- [P] Unit Tests Subagent
  - pytest tests/unit/ -v
  - Focus: Individual functions, classes

- [P] Integration Tests Subagent
  - pytest tests/integration/ -v
  - Focus: Tool interactions, database queries

- [P] Performance Tests Subagent
  - pytest tests/performance/ -v
  - Focus: Latency, throughput benchmarks

- [P] MCP Compliance Subagent
  - pytest tests/mcp_compliance/ -v
  - Focus: Protocol validation, schema checks

# Sequential aggregation
- Orchestrator: Collect all test results
  - All green: Proceed to PR
  - Any red: Identify failures, rerun specific tests
```

**Coordination:**
1. Orchestrator waits for implementation to complete
2. Orchestrator launches all test subagents in parallel
3. Each subagent runs independent test suite
4. Orchestrator collects results from all subagents
5. Orchestrator makes pass/fail decision
6. If failures, orchestrator identifies root cause and reruns

---

## Real-World Examples

### Example 1: Codebase-MCP Refactor (Remove Features)

**Goal:** Remove work items, vendors, and tasks from codebase-mcp

**Parallel Strategy:**
```markdown
# Phase 1: Parallel removal (independent modules)
- [P] Subagent A: Remove work item tools
  - Delete: src/tools/create_work_item.py, query_work_item.py, list_work_items.py, update_work_item.py
  - Delete: tests/test_work_items.py
  - Modify: src/server.py (remove tool registrations)

- [P] Subagent B: Remove vendor tools
  - Delete: src/tools/query_vendor_status.py, update_vendor_status.py, create_vendor.py
  - Delete: tests/test_vendors.py
  - Modify: src/server.py (remove tool registrations)

- [P] Subagent C: Remove task tools
  - Delete: src/tools/get_task.py, list_tasks.py, create_task.py, update_task.py
  - Delete: tests/test_tasks.py
  - Modify: src/server.py (remove tool registrations)

# Phase 2: Sequential integration (after all removals)
- [ ] Orchestrator: Consolidate server.py changes
  - Merge all tool registration removals
  - Verify no references to deleted modules

- [ ] Orchestrator: Update database schema
  - Remove tables: work_items, vendors, tasks
  - Create migration: 009_remove_project_features.sql

- [ ] Orchestrator: Run integration tests
  - Verify: Only index_repository, search_code remain
  - Verify: MCP protocol compliance
  - Verify: No broken imports
```

**Why This Works:**
- ✅ Tool files are independent (no shared code)
- ✅ Test files are independent (different fixtures)
- ✅ server.py conflicts resolved by orchestrator (expected)
- ✅ Fast: 3x speedup vs sequential deletion

**Orchestrator Responsibilities:**
- Launch all subagents with file paths
- Wait for all completions (barrier)
- Resolve server.py merge conflicts
- Validate no broken references remain
- Run final integration tests

### Example 2: Workflow-MCP Build (Greenfield)

**Goal:** Build workflow-mcp with project management, entity system, and work items

**Parallel Strategy:**
```markdown
# Phase 1: Foundation (sequential)
- [ ] Orchestrator: Database schema
  - Create: schema.sql (projects, entities, work_items, sessions tables)
  - Create: migrations/001_init.sql

- [ ] Orchestrator: Connection manager
  - Create: src/database/connection.py
  - Create: src/database/queries.py

# Phase 2: Parallel tool development (depends on Phase 1)
- [P] Subagent A: Project tools
  - Create: src/tools/create_project.py
  - Create: src/tools/switch_project.py
  - Create: src/tools/list_projects.py
  - Create: src/tools/get_active_project.py
  - Tests: tests/test_project_tools.py

- [P] Subagent B: Entity system tools
  - Create: src/tools/create_entity.py
  - Create: src/tools/query_entity.py
  - Create: src/tools/list_entities.py
  - Tests: tests/test_entity_tools.py

- [P] Subagent C: Work item tools
  - Create: src/tools/create_work_item.py
  - Create: src/tools/query_work_item.py
  - Create: src/tools/list_work_items.py
  - Create: src/tools/update_work_item.py
  - Tests: tests/test_work_item_tools.py

- [P] Subagent D: Session tools
  - Create: src/tools/create_session.py
  - Create: src/tools/update_session.py
  - Create: src/tools/query_session.py
  - Tests: tests/test_session_tools.py

# Phase 3: Sequential integration (depends on Phase 2)
- [ ] Orchestrator: FastMCP server setup
  - Create: src/server.py
  - Register all tools from Phase 2
  - Verify: mcp.list_tools() returns all 15+ tools

- [ ] Orchestrator: Integration tests
  - Create: tests/test_integration.py
  - Test: Create project → Create entity → Create work item → Query work item
  - Test: Switch project → Verify entity isolation

- [ ] Orchestrator: MCP compliance tests
  - Create: tests/test_mcp_compliance.py
  - Verify: Tool schemas valid
  - Verify: No stdout/stderr pollution
```

**Why This Works:**
- ✅ Foundation must complete first (database schema, connection)
- ✅ Tools are completely independent (different modules)
- ✅ Each subagent has clear ownership (no file conflicts)
- ✅ Orchestrator integrates at end (server registration)
- ✅ Fast: 4x speedup on Phase 2 (4 subagents in parallel)

**Orchestrator Responsibilities:**
- Complete foundation work first (database)
- Launch 4 subagents with clear module boundaries
- Wait for all tool completions (barrier)
- Register all tools in FastMCP server
- Run cross-tool integration tests
- Verify MCP protocol compliance

### Example 3: Multi-Project Search Feature (Mixed Pattern)

**Goal:** Add multi-project support to codebase-mcp

**Parallel Strategy:**
```markdown
# Phase 1: Parallel foundation (independent components)
- [P] Subagent A: Database migration
  - Create: migrations/008_add_project_support.sql
  - Test: migrations run without errors

- [P] Subagent B: Project cache implementation
  - Create: src/cache/project_cache.py
  - Test: tests/test_project_cache.py

- [P] Subagent C: Integration test scaffolding (RED)
  - Create: tests/test_multi_project_search.py
  - Write: Failing tests for multi-project isolation

# Phase 2: Sequential core functionality (depends on Phase 1)
- [ ] Orchestrator: Run migration (depends on Subagent A)
  - Execute: 008_add_project_support.sql
  - Verify: project_id columns exist

- [ ] Subagent D: Update search_code (depends on Subagent B, C)
  - Modify: src/tools/search_code.py
  - Add: project_id filtering
  - Add: Active project fallback using ProjectCache
  - Verify: Integration tests pass (GREEN)

- [ ] Subagent E: Update index_repository (depends on migration)
  - Modify: src/tools/index_repository.py
  - Add: project_id parameter (required)
  - Verify: Indexes store project_id

# Phase 3: Parallel edge case testing (depends on Phase 2)
- [P] Subagent F: Project switching tests
  - Create: tests/test_project_switching.py

- [P] Subagent G: Edge case tests
  - Create: tests/test_edge_cases.py

- [P] Subagent H: MCP compliance tests
  - Create: tests/test_mcp_compliance.py

# Phase 4: Sequential finalization (depends on Phase 3)
- [ ] Orchestrator: Run all tests
  - Execute: pytest tests/ -v
  - Verify: All tests pass

- [ ] Orchestrator: Update documentation
  - Modify: docs/api/search-tool.md
  - Modify: CLAUDE.md (workflow updates)
```

**Why This Works:**
- ✅ Phase 1: Foundation components are independent
- ✅ Phase 2: Core functionality needs foundation first
- ✅ Phase 3: Tests can be written in parallel (different files)
- ✅ Phase 4: Final validation by orchestrator
- ✅ Speedup: ~2.5x vs fully sequential

**Orchestrator Responsibilities:**
- Launch Phase 1 subagents in parallel
- Wait for Phase 1 completion (barrier)
- Run migration before Phase 2
- Launch Phase 2 subagents (sequential, with dependencies)
- Launch Phase 3 subagents in parallel
- Aggregate all test results
- Finalize documentation

---

## FastMCP-Specific Patterns

### Pattern: Independent Tool Development

**FastMCP Advantage:** Each tool is self-contained with decorator-based registration

**Parallel Strategy:**
```python
# Each subagent creates one tool file

# Subagent A: src/tools/tool_a.py
from fastmcp import FastMCP
mcp = FastMCP("codebase-mcp")

@mcp.tool()
async def tool_a(param: str) -> dict:
    """Tool A implementation"""
    return {"result": "a"}

# Subagent B: src/tools/tool_b.py
from fastmcp import FastMCP
mcp = FastMCP("codebase-mcp")

@mcp.tool()
async def tool_b(param: str) -> dict:
    """Tool B implementation"""
    return {"result": "b"}

# Orchestrator: src/server.py (integrates all)
from fastmcp import FastMCP
from tools import tool_a, tool_b  # Import triggers registration

mcp = FastMCP("codebase-mcp")

if __name__ == "__main__":
    mcp.run()  # All tools registered via decorators
```

**Why This Works:**
- ✅ No manual tool registration needed (decorator-based)
- ✅ No central registry to merge (imports handle it)
- ✅ Each subagent completely independent
- ✅ Orchestrator just imports all modules

### Pattern: Shared Database, Independent Queries

**Challenge:** Multiple subagents need database access

**Solution: Connection Pool Pattern:**
```python
# Foundation: src/database/connection.py (created first)
import asyncpg

_pool: Optional[asyncpg.Pool] = None

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(...)
    return _pool

# Subagent A: Uses connection pool
from database.connection import get_pool

@mcp.tool()
async def tool_a():
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetch("SELECT * FROM table_a")
    return result

# Subagent B: Uses same connection pool (no conflict)
from database.connection import get_pool

@mcp.tool()
async def tool_b():
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetch("SELECT * FROM table_b")
    return result
```

**Why This Works:**
- ✅ Shared connection pool (efficient)
- ✅ Subagents use independent tables (no conflicts)
- ✅ Transactions isolate changes (if needed)

---

## Conflict Resolution Strategies

### Conflict Type 1: Same File Modified by Multiple Subagents

**Scenario:** Two subagents modify `src/server.py` to register their tools

**Detection:**
```bash
# Subagent A commits
git add src/server.py
git commit -m "feat(tools): register tool_a"

# Subagent B commits (conflict!)
git add src/server.py
git commit -m "feat(tools): register tool_b"
# Error: merge conflict
```

**Resolution (Orchestrator):**
```python
# Orchestrator reviews both changes
# Subagent A added:
from tools import tool_a

# Subagent B added:
from tools import tool_b

# Orchestrator merges:
from tools import tool_a, tool_b

# Commit merged result
git add src/server.py
git commit -m "feat(tools): register tool_a and tool_b"
```

**Prevention:**
- Assign non-overlapping files to subagents
- Use FastMCP's import-based registration (no central file)
- Have orchestrator handle server.py integration

### Conflict Type 2: Database Schema Conflicts

**Scenario:** Two subagents create migrations with same number

**Detection:**
```bash
# Subagent A creates: migrations/008_add_feature_a.sql
# Subagent B creates: migrations/008_add_feature_b.sql
# Conflict: Same migration number
```

**Resolution (Orchestrator):**
```bash
# Orchestrator renames migrations sequentially
mv migrations/008_add_feature_b.sql migrations/009_add_feature_b.sql

# Update migration tracker
echo "009_add_feature_b.sql" >> migrations/applied.txt
```

**Prevention:**
- Have orchestrator assign migration numbers before launching subagents
- Use timestamp-based migration numbers (001_20251011_feature_a.sql)

### Conflict Type 3: Test Fixture Conflicts

**Scenario:** Two subagents modify same test fixture

**Detection:**
```python
# Subagent A modifies: tests/conftest.py
@pytest.fixture
def test_project():
    return {"id": "proj-a", "name": "Project A"}

# Subagent B modifies: tests/conftest.py
@pytest.fixture
def test_project():
    return {"id": "proj-b", "name": "Project B"}
# Conflict: Same fixture name
```

**Resolution (Orchestrator):**
```python
# Orchestrator creates separate fixtures
@pytest.fixture
def test_project_a():
    return {"id": "proj-a", "name": "Project A"}

@pytest.fixture
def test_project_b():
    return {"id": "proj-b", "name": "Project B"}

# Update subagent tests to use specific fixtures
```

**Prevention:**
- Assign unique fixture names to each subagent
- Use fixture factories instead of concrete fixtures
- Create subagent-specific conftest.py files

---

## Performance Analysis

### Speedup Calculation

**Sequential Baseline:**
```
Total time = Sum of all task times
Example: 10 tasks × 30 min each = 300 min (5 hours)
```

**Parallel with N subagents:**
```
Total time = Max(task times) + orchestration overhead
Example: 10 tasks, 3 subagents
  - Subagent A: Tasks 1-3 (90 min)
  - Subagent B: Tasks 4-6 (90 min)
  - Subagent C: Tasks 7-10 (120 min)
Total time = 120 min + 10 min overhead = 130 min
Speedup = 300 / 130 = 2.3x
```

**Realistic Speedup (with dependencies):**
```
Phase 1: Foundation (sequential) = 30 min
Phase 2: Parallel development (3 subagents) = 40 min (vs 120 min sequential)
Phase 3: Integration (sequential) = 20 min
Total = 90 min (vs 170 min sequential)
Speedup = 170 / 90 = 1.9x
```

### Orchestration Overhead

**Per-subagent overhead:**
- Launch subagent: ~1 min (context loading, instruction parsing)
- Wait for completion: 0 min (barrier)
- Review output: ~5 min (validate correctness)
- Merge results: ~5 min (resolve conflicts, commit)

**Total overhead for N subagents:**
```
Overhead = N × (1 min launch + 5 min review) + 5 min merge
Example: 4 subagents
Overhead = 4 × 6 + 5 = 29 min
```

**Break-even analysis:**
```
Sequential time > Parallel time + Overhead
Task time × N > Max(task times) + (N × 6 + 5)

Example: 4 tasks, 30 min each
Sequential: 4 × 30 = 120 min
Parallel: 30 + (4 × 6 + 5) = 30 + 29 = 59 min
Speedup: 120 / 59 = 2.0x ✅ Worth it

Example: 4 tasks, 10 min each
Sequential: 4 × 10 = 40 min
Parallel: 10 + (4 × 6 + 5) = 10 + 29 = 39 min
Speedup: 40 / 39 = 1.03x ❌ Not worth it (marginal)
```

**Recommendation:** Use parallel subagents when:
- Task time > 20 minutes each
- N ≥ 3 independent tasks
- Expected speedup > 1.5x

---

## Decision Tree: Parallel or Sequential?

```
Start: Multiple tasks to complete
  │
  ├─→ Do tasks modify same file?
  │   YES → Sequential (no choice)
  │   NO → Continue
  │
  ├─→ Does Task B depend on Task A output?
  │   YES → Sequential (Task A first)
  │   NO → Continue
  │
  ├─→ Are tasks in same module/package?
  │   YES → Consider sequential (easier coordination)
  │   NO → Continue
  │
  ├─→ Is each task > 20 minutes?
  │   NO → Sequential (overhead not worth it)
  │   YES → Continue
  │
  ├─→ Are there ≥ 3 independent tasks?
  │   NO → Sequential (insufficient parallelism)
  │   YES → PARALLEL ✅
```

---

## Best Practices

### 1. Clear Ownership Boundaries
**Good:**
```markdown
- Subagent A: Owns src/tools/project_*.py and tests/test_project_*.py
- Subagent B: Owns src/tools/entity_*.py and tests/test_entity_*.py
```

**Bad:**
```markdown
- Subagent A: Works on project tools
- Subagent B: Also works on project tools
# Collision likely!
```

### 2. Explicit Dependencies in Task Descriptions
**Good:**
```markdown
- [ ] T001: Create database schema (MUST complete first)
- [P] T002: Create tool A (depends on T001)
- [P] T003: Create tool B (depends on T001)
```

**Bad:**
```markdown
- [P] T001: Create schema and tools
# Unclear what can be parallelized
```

### 3. Orchestrator Owns Integration Files
**Good:**
```markdown
- Orchestrator owns: src/server.py, pyproject.toml, README.md
- Subagents own: Individual tool files, test files
```

**Bad:**
```markdown
- All subagents modify: src/server.py
# Guaranteed merge conflicts
```

### 4. Use Barrier Synchronization
**Good:**
```python
# Orchestrator waits for all subagents
results = await asyncio.gather(
    subagent_a.run(),
    subagent_b.run(),
    subagent_c.run()
)
# Proceed only when all complete
```

**Bad:**
```python
# Orchestrator proceeds without waiting
subagent_a.run()  # Launches in background
subagent_b.run()  # Launches in background
orchestrator.integrate()  # Runs before subagents finish!
```

### 5. Fail Fast on Critical Errors
**Good:**
```python
# Subagent A fails (database migration error)
if migration_failed:
    raise CriticalError("Migration failed, cannot proceed")
# Orchestrator stops all subagents immediately
```

**Bad:**
```python
# Subagent A fails, but others continue
# Subagent B builds on top of failed migration
# Waste time, compound errors
```

---

## Summary

**Key Patterns:**
1. **Independent Module Development** - Parallel tools, sequential integration
2. **Dependency Chain** - Foundation first, parallel features, integration last
3. **Iterative Review** - Parallel reviews, sequential revision
4. **Fan-Out, Fan-In** - Parallel tests, sequential aggregation

**Decision Criteria:**
- Use parallel when: Independent files, no dependencies, >20 min tasks
- Use sequential when: Shared files, dependencies, integration tests

**FastMCP Advantages:**
- Decorator-based tool registration (no central registry conflicts)
- Import-based integration (orchestrator just imports modules)
- Connection pool pattern (shared database, no conflicts)

**Performance:**
- Typical speedup: 1.5x - 2.5x (vs sequential)
- Break-even: Tasks > 20 min, N ≥ 3 subagents
- Overhead: ~6 min per subagent (launch + review)

**Quality:**
- Clear ownership boundaries prevent conflicts
- Barrier synchronization ensures correctness
- Fail fast on critical errors saves time
- Orchestrator owns integration (server, docs, final tests)
