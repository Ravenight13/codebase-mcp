# workflow-mcp Final Implementation Plan

**Status:** APPROVED FOR IMPLEMENTATION
**Version:** 1.0 (Final Revision)
**Date:** 2025-10-11
**Reviewer:** Senior Architectural Review Agent

---

## Revision Summary

This final plan integrates feedback from planning and architectural reviews to address all critical issues and incorporate key recommendations.

### Major Changes from Initial Plan

1. **Phase 1 Enhanced**: Minimal entity system moved from Phase 3 to Phase 1 (C3)
2. **Connection Pool Management**: LRU eviction strategy added (C2, AR-1)
3. **Schema Evolution Strategy**: Additive-only policy with versioning (C1, AR-2)
4. **Database Lifecycle**: Transactional rollback on failure (C4)
5. **Performance Measurement**: pytest-benchmark framework with CI integration (C5)
6. **Entity Relationships**: Application-level validation documented (AR-3)

### Critical Issues Resolved

- **C1**: Schema evolution strategy with versioning and additive-only policy
- **C2**: Connection pool eviction (LRU cache, max 50 pools)
- **C3**: Phase 1 includes minimal entity system for immediate codebase-mcp value
- **C4**: Database creation with transactional rollback
- **C5**: Performance measurement framework in CI

### Architectural Recommendations Integrated

- **AR-1**: Connection pool eviction strategy (LRU cache, max 50 active pools)
- **AR-2**: Schema versioning for entity types
- **AR-3**: Entity relationship limitations documented
- **AR-4**: First-time pool creation latency clarified (<100ms, amortized)
- **AR-5**: Cross-MCP integration examples added
- **AR-6**: Automated backup strategy documented

---

## Executive Summary

workflow-mcp is a production-grade MCP server that provides AI-assisted project management with multi-project workspace support and a **generic entity system**. It enables AI coding assistants to track work items, manage tasks, record deployments, and handle domain-specific entities (vendors, game mechanics, research papers) across isolated project workspaces.

### Core Innovation

The **generic entity system** uses JSONB storage with runtime JSON Schema validation to support ANY domain without hardcoded tables or schema migrations. This enables:

- Commission work: Track vendor extractor status (operational/broken)
- Game development: Track game mechanics (design → prototype → complete)
- Research: Track papers, citations, experiments
- ANY domain: Register custom entity types at runtime

### Relationship to codebase-mcp

- **codebase-mcp**: Code intelligence (semantic search, indexing)
- **workflow-mcp**: Project management (work items, entities, deployments)
- **Integration**: codebase-mcp queries workflow-mcp for active project context

### Success Criteria

1. **Isolation**: Commission data never visible in game dev queries
2. **Flexibility**: New entity types without code changes
3. **Performance**: <50ms project switching, <200ms work items, <100ms entities
4. **Scalability**: 100+ projects with independent databases
5. **Type Safety**: Pydantic validation, mypy --strict passes

---

## Resolved Critical Issues

### C1: Schema Evolution Strategy

**Original Problem:** No migration path for evolving entity type schemas after entities exist.

**Scenario:**
1. Register vendor schema v1 with fields: status, extractor_version
2. Create 50 vendor entities with v1 schema
3. Need to add "last_updated" as required field (breaking change)
4. Existing 50 entities lack "last_updated" → validation fails

**Resolution:**

1. **Additive-Only Evolution Policy:**
   - ✅ ALLOWED: Adding optional fields
   - ✅ ALLOWED: Making required fields optional
   - ❌ FORBIDDEN: Adding required fields
   - ❌ FORBIDDEN: Removing fields
   - ❌ FORBIDDEN: Changing field types

2. **Schema Versioning:**
   ```sql
   -- Add to entity_types table
   ALTER TABLE entity_types ADD COLUMN schema_version INT DEFAULT 1;

   -- Store version history
   CREATE TABLE entity_type_versions (
       entity_type VARCHAR(100) REFERENCES entity_types(type_name),
       version INT NOT NULL,
       schema JSONB NOT NULL,
       created_at TIMESTAMPTZ DEFAULT NOW(),
       PRIMARY KEY (entity_type, version)
   );
   ```

3. **Evolution Example:**
   ```python
   # Original schema (v1)
   schema_v1 = {
       "properties": {
           "status": {"enum": ["operational", "broken"]},
           "version": {"type": "string"}
       },
       "required": ["status", "version"]
   }

   # Evolved schema (v2) - additive only
   schema_v2 = {
       "properties": {
           "status": {"enum": ["operational", "broken"]},
           "version": {"type": "string"},
           "test_coverage": {"type": "number"}  # NEW OPTIONAL FIELD
       },
       "required": ["status", "version"]  # Same required fields
   }
   ```

**Implementation:** Phase 3, Week 8 (Entity System)

**Verification:**
- Test additive schema changes (add optional field)
- Test forbidden changes raise ValidationError
- Test v1 entities validate against v2 schema (backward compatibility)

---

### C2: Connection Pool Exhaustion

**Original Problem:**
- 100 projects × 5 connections/project = 500 connections
- PostgreSQL default max_connections = 200
- Server fails after ~40 projects

**Math Breakdown:**
```
Registry pool:     10 connections (max_size=10)
100 projects:     500 connections (100 × 5)
Total:            510 connections > 200 (EXCEEDS LIMIT)
```

**Resolution:**

1. **LRU Pool Eviction:**
   ```python
   from cachetools import LRUCache

   class ConnectionPoolManager:
       def __init__(self, max_active_pools: int = 50):
           self.registry_pool: asyncpg.Pool = None
           # Max 50 active project pools (LRU eviction)
           self.project_pools: LRUCache[str, asyncpg.Pool] = LRUCache(
               maxsize=max_active_pools,
               on_evict=self._close_pool_callback
           )

       async def _close_pool_callback(self, project_id: str, pool: asyncpg.Pool):
           await pool.close()
           logger.info(f"Evicted pool for project {project_id}")

       async def get_project_pool(self, project_id: str) -> asyncpg.Pool:
           if project_id not in self.project_pools:
               # Lazy load pool
               pool = await asyncpg.create_pool(
                   dsn=f"postgresql://localhost/workflow_project_{project_id}",
                   min_size=1,
                   max_size=5,
                   timeout=30,
                   max_inactive_connection_lifetime=3600  # 1 hour
               )
               self.project_pools[project_id] = pool
           return self.project_pools[project_id]
   ```

2. **Resource Calculations:**
   ```
   Registry pool:     10 connections
   50 active pools:  250 connections (50 × 5)
   Total:            260 connections (within limit)
   Buffer:            40 connections (for spikes)
   Recommendation:   max_connections = 300
   ```

3. **Pool Lifecycle:**
   - **Create**: Lazy-loaded on first access to project
   - **Use**: Reused across tool invocations (<1ms overhead)
   - **Evict**: LRU cache evicts least-recently-used pool after 50th
   - **Close**: Gracefully closed on eviction
   - **Reload**: Re-created on next access (amortized cost)

**Implementation:** Phase 1, Week 2 (Connection Pool Management)

**Verification:**
- Load test: Create 100 projects, switch between them
- Verify only 50 pools active at any time
- Measure eviction/reload latency (<100ms)
- Check PostgreSQL connection count < 300

---

### C3: Phase 1 Deliverable Value

**Original Problem:**
- Phase 1 only had project management (create, switch, list)
- No entities → codebase-mcp can't track vendors
- No immediate value until Phase 3 complete

**Assessment:**
- ✅ Can tag code chunks with project_id
- ❌ Cannot track vendor status (operational/broken)
- ❌ Cannot link code to entities

**Resolution: Enhanced Phase 1**

Move **minimal entity system** from Phase 3 to Phase 1:

**Phase 1 Enhanced Deliverables:**
1. Project management (create, switch, list projects) ✅
2. **NEW: Minimal entity system** ✅
   - register_entity_type tool
   - create_entity tool
   - query_entities tool
   - update_entity tool (basic, no optimistic locking yet)
3. Connection pool eviction (LRU cache)
4. Database lifecycle with rollback

**Phase 3 Reduced Scope:**
- Work items, tasks, deployments (unchanged)
- Entity enhancements:
  - Optimistic locking for update_entity
  - Schema evolution tools
  - Advanced query patterns
  - Entity relationships validation

**Rationale:**
- codebase-mcp needs vendor tracking NOW (not in Phase 3)
- Entity system provides immediate value for commission work
- Simple entity CRUD is ~30% of full entity system effort
- Phase 3 can focus on advanced features

**New Phase 1 Acceptance Criteria:**
- ✅ codebase-mcp can query active project
- ✅ Commission project can register "vendor" entity type
- ✅ Create EPSON vendor entity with status="operational"
- ✅ Query vendors with status="broken"
- ✅ Connection pools evict after 50 projects

**Implementation:** Phase 1, Week 2-3 (Minimal Entity System)

**Verification:**
- End-to-end test: Commission work scenario
  1. Create commission project
  2. Register vendor entity type
  3. Create 3 vendors (2 operational, 1 broken)
  4. Query broken vendors (returns 1)
  5. Update broken vendor to operational
  6. Verify isolation: Game dev project sees 0 vendors

---

### C4: Database Creation Failure Rollback

**Original Problem:**

**Failure Scenario:**
1. `create_project("commission-work")` called
2. INSERT into registry.projects succeeds
3. CREATE DATABASE workflow_project_<uuid> succeeds
4. Schema initialization (002_project_schema.sql) fails (syntax error)
5. **Result**: Orphaned project entry with broken database

**Impact:**
- Project exists in registry but unusable
- Retry fails due to unique constraint on name
- Manual cleanup required
- System integrity violated

**Resolution:**

**Transactional Database Creation:**
```python
@mcp.tool()
async def create_project(
    name: str,
    description: str,
    metadata: dict | None = None
) -> dict:
    """Create project with transactional rollback on failure."""
    project_id = str(uuid.uuid4())
    database_name = f"workflow_project_{project_id}"

    # Start registry transaction
    async with registry_pool.acquire() as registry_conn:
        async with registry_conn.transaction():
            # Step 1: Insert into registry
            await registry_conn.execute(
                """
                INSERT INTO projects (project_id, name, description, database_name, metadata)
                VALUES ($1, $2, $3, $4, $5)
                """,
                project_id, name, description, database_name, metadata or {}
            )

            try:
                # Step 2: Create database (outside transaction, cannot rollback)
                await registry_conn.execute(f"CREATE DATABASE {database_name}")

                # Step 3: Initialize schema
                async with asyncpg.connect(f"postgresql://localhost/{database_name}") as db_conn:
                    schema_sql = Path("migrations/002_project_schema.sql").read_text()
                    await db_conn.execute(schema_sql)

                # Success: commit registry transaction
                logger.info(f"Created project {name} with database {database_name}")

            except Exception as schema_error:
                # Rollback: Drop database + registry entry
                logger.error(f"Schema initialization failed: {schema_error}")

                try:
                    await registry_conn.execute(f"DROP DATABASE IF EXISTS {database_name}")
                except Exception as drop_error:
                    logger.error(f"Failed to drop database: {drop_error}")

                # Re-raise to trigger registry transaction rollback
                raise RuntimeError(
                    f"Project creation failed: {schema_error}. "
                    f"Database and registry entry rolled back."
                )

    return {
        "project_id": project_id,
        "name": name,
        "database_name": database_name,
        "created_at": datetime.utcnow().isoformat()
    }
```

**Error Handling Flow:**
```
CREATE DATABASE succeeds
↓
Schema initialization FAILS
↓
DROP DATABASE (cleanup)
↓
Registry transaction ROLLBACK
↓
No orphaned entries
```

**Implementation:** Phase 1, Week 1 (Project Management Tools)

**Verification:**
- Test: Schema initialization fails (simulate syntax error)
- Assert: No project in registry
- Assert: No database exists
- Test: Retry with same name succeeds

---

### C5: Performance Measurement Strategy

**Original Problem:**
- Constitution mandates p95 latency targets
- No measurement framework documented
- No CI integration for performance regression
- Targets are aspirational, not enforceable

**Constitutional Targets:**
- Project switching: <50ms p95
- Work item operations: <200ms p95
- Entity queries: <100ms p95
- Task listing: <150ms p95

**Resolution:**

**1. Performance Testing Framework:**
```python
# tests/performance/test_latency.py
import pytest
from pytest_benchmark.fixture import BenchmarkFixture

@pytest.fixture
async def large_dataset():
    """Fixture: 100 projects, 10K entities each."""
    projects = []
    for i in range(100):
        project = await create_project(f"project-{i}", "Test")
        # Create 10K entities per project
        for j in range(10000):
            await create_entity(
                project["project_id"],
                "vendor",
                f"vendor-{j}",
                {"status": "operational", "version": "1.0.0"}
            )
        projects.append(project)
    yield projects

@pytest.mark.benchmark(group="project-switching")
def test_project_switching_latency(benchmark: BenchmarkFixture, large_dataset):
    """Benchmark project switching p95 latency."""
    projects = large_dataset

    def switch():
        # Switch to random project
        project = random.choice(projects)
        return switch_active_project(project["project_id"])

    result = benchmark.pedantic(switch, iterations=100, rounds=10)

    # Assert p95 < 50ms (excluding first-time pool creation)
    assert result.stats.percentile_95 < 0.050, \
        f"p95 latency {result.stats.percentile_95*1000:.1f}ms exceeds 50ms target"

@pytest.mark.benchmark(group="entity-queries")
def test_entity_query_latency(benchmark: BenchmarkFixture, large_dataset):
    """Benchmark entity query p95 latency."""
    project = large_dataset[0]

    def query():
        return query_entities(
            project["project_id"],
            "vendor",
            filters={"data": {"status": "broken"}},
            limit=10
        )

    result = benchmark.pedantic(query, iterations=100, rounds=10)

    # Assert p95 < 100ms
    assert result.stats.percentile_95 < 0.100, \
        f"p95 latency {result.stats.percentile_95*1000:.1f}ms exceeds 100ms target"
```

**2. CI Integration:**
```yaml
# .github/workflows/performance.yml
name: Performance Tests

on: [push, pull_request]

jobs:
  performance:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres

    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
          pip install pytest-benchmark

      - name: Run performance tests
        run: |
          pytest tests/performance/ \
            --benchmark-only \
            --benchmark-json=benchmark.json

      - name: Check p95 regression
        run: |
          python scripts/check_performance_regression.py \
            --threshold=0.20 \
            --baseline=baseline_benchmark.json \
            --current=benchmark.json
```

**3. Regression Detection:**
```python
# scripts/check_performance_regression.py
import json
import sys

def check_regression(baseline_file: str, current_file: str, threshold: float = 0.20):
    """Fail CI if p95 latency regresses by >20%."""
    with open(baseline_file) as f:
        baseline = json.load(f)

    with open(current_file) as f:
        current = json.load(f)

    regressions = []

    for benchmark_name in baseline["benchmarks"]:
        baseline_p95 = baseline[benchmark_name]["stats"]["percentile_95"]
        current_p95 = current[benchmark_name]["stats"]["percentile_95"]

        regression = (current_p95 - baseline_p95) / baseline_p95

        if regression > threshold:
            regressions.append({
                "benchmark": benchmark_name,
                "baseline_p95": baseline_p95 * 1000,  # Convert to ms
                "current_p95": current_p95 * 1000,
                "regression": regression * 100  # Percentage
            })

    if regressions:
        print("❌ Performance Regressions Detected:")
        for r in regressions:
            print(f"  {r['benchmark']}: {r['baseline_p95']:.1f}ms → {r['current_p95']:.1f}ms (+{r['regression']:.1f}%)")
        sys.exit(1)
    else:
        print("✅ No performance regressions (threshold: {:.0f}%)".format(threshold * 100))
```

**Implementation:** Phase 1, Week 3 (Testing Suite)

**Verification:**
- Run performance tests locally
- Generate baseline benchmark.json
- Commit baseline to repo
- CI fails if p95 regresses >20%

---

## Incorporated Architectural Recommendations

### AR-1: Connection Pool Eviction Strategy

**Recommendation:** LRU cache with max 50 active pools to prevent connection exhaustion.

**Implementation:** See C2 resolution above.

**Benefits:**
- Reduces memory from ~500MB (100 pools) to ~250MB (50 pools)
- Prevents PostgreSQL connection limit (max_connections=200)
- Automatic eviction of least-recently-used pools

---

### AR-2: Schema Versioning for Entity Types

**Recommendation:** Add schema_version column to entity_types table.

**Implementation:** See C1 resolution above.

**Benefits:**
- Enables schema evolution with backward compatibility
- Tracks schema history for audit trail
- Supports future migration tools

---

### AR-3: Entity Relationship Limitations

**Recommendation:** Document that JSONB entity references have no foreign key enforcement.

**Documentation:**
```markdown
# docs/entity-system.md

## Entity Relationships

Entities can reference each other via JSONB data (e.g., `"dependencies": ["Attribute System"]`), but these are **NOT enforced by foreign keys**.

### Limitations

1. **No Referential Integrity:**
   - Database does not validate referenced entities exist
   - Deleting entity A does not cascade to entities referencing A
   - Broken references possible if entity deleted

2. **Application-Level Validation Required:**
   ```python
   async def validate_dependencies(entity_type: str, data: dict) -> None:
       """Validate entity references exist."""
       if "dependencies" in data:
           for dep_name in data["dependencies"]:
               dep_entity = await query_entities(
                   entity_type=entity_type,
                   filters={"data": {"name": dep_name}}
               )
               if not dep_entity:
                   raise ValueError(f"Dependency '{dep_name}' not found")
   ```

3. **Soft Delete Recommended:**
   - Use deleted_at timestamp instead of hard delete
   - Preserves reference integrity
   - Enables audit trail

### Example: Game Mechanic Dependencies

```python
# Create base mechanic
attribute_system = create_entity(
    entity_type="game_mechanic",
    name="Attribute System",
    data={"status": "complete"}
)

# Create dependent mechanic
skill_check = create_entity(
    entity_type="game_mechanic",
    name="Skill Check System",
    data={
        "status": "prototype",
        "dependencies": ["Attribute System"]  # String reference (no FK)
    }
)

# Application validates "Attribute System" exists
# Database does NOT enforce this constraint
```
```

**Implementation:** Phase 3, Week 8 (Documentation)

**Benefits:**
- Developers understand limitations
- Implement proper validation
- Avoid broken references

---

### AR-4: First-Time Pool Creation Latency

**Recommendation:** Clarify that <50ms target excludes first-time pool creation.

**Constitutional Update:**
```markdown
# constitution.md (Principle IV)

**Performance Targets (p95 latency)**:
- **Project switching**: <50ms (excluding first-time pool creation ~100ms, amortized)
  - Subsequent switches to same project: <5ms (pool reuse)
  - First switch to new project: ~100ms (pool creation, one-time cost)
  - p95 measured across all switches, dominated by pool reuse
- **Work item operations**: <200ms (hierarchy queries, dependency resolution)
- **Entity queries**: <100ms (JSONB filtering with GIN indexing)
- **Task listing**: <150ms (summary mode, token-efficient)
- **Deployment recording**: <200ms (event + relationships)
```

**Implementation:** Phase 1, Week 3 (Documentation)

**Benefits:**
- Sets accurate expectations
- Prevents false performance regressions
- Clarifies amortized cost model

---

### AR-5: Cross-MCP Integration Examples

**Recommendation:** Document workflow-mcp ↔ codebase-mcp communication patterns.

**Documentation:**
```markdown
# docs/integration.md

## Cross-MCP Communication

### Pattern 1: codebase-mcp Queries Active Project

**Use Case:** Filter semantic search by active project

```python
# codebase-mcp implementation
async def search_code_in_active_project(query: str) -> list[dict]:
    """Search code filtered by active project."""

    # Step 1: Query workflow-mcp for active project
    async with workflow_mcp_client as session:
        active_project = await session.call_tool("get_active_project", {})

    if not active_project:
        # No active project, search all code
        return await search_code(query)

    # Step 2: Filter search by project_id
    return await search_code(
        query=query,
        project_id=active_project["project_id"]
    )
```

**Example Flow:**
```
User: "Search for vendor extraction logic"
↓
codebase-mcp: What is the active project?
↓
workflow-mcp: {"project_id": "uuid", "name": "commission-work"}
↓
codebase-mcp: search_code(query="vendor extraction", project_id="uuid")
↓
Returns: Code chunks filtered by commission project
```

### Pattern 2: workflow-mcp Queries Code References

**Use Case:** Show code related to entity

```python
# workflow-mcp implementation
@mcp.tool()
async def get_entity_with_code_references(
    entity_id: str,
    include_code: bool = True
) -> dict:
    """Get entity with related code references."""

    # Step 1: Fetch entity
    entity = await query_entity(entity_id)

    if not include_code:
        return entity

    # Step 2: Query codebase-mcp for related code
    async with codebase_mcp_client as session:
        code_refs = await session.call_tool("search_code", {
            "query": entity["name"],
            "project_id": entity["project_id"],
            "limit": 5
        })

    return {
        **entity,
        "code_references": code_refs
    }
```

**Example Flow:**
```
User: "Show me code related to EPSON vendor entity"
↓
workflow-mcp: query_entities(entity_type="vendor", filters={"name": "EPSON"})
↓
workflow-mcp: Call codebase-mcp.search_code(query="EPSON", project_id="uuid")
↓
codebase-mcp: Returns [file1.py:45, file2.py:102]
↓
workflow-mcp: Returns entity + code references
```

### Error Handling

**Scenario: Cross-MCP Call Fails**

```python
async def get_active_project_safe() -> dict | None:
    """Query workflow-mcp with error handling."""
    try:
        async with workflow_mcp_client as session:
            result = await session.call_tool("get_active_project", {})
            return result
    except TimeoutError:
        logger.warning("workflow-mcp query timed out")
        return None
    except Exception as e:
        logger.error(f"workflow-mcp query failed: {e}")
        return None
```

**Degraded Behavior:**
- If workflow-mcp unavailable, codebase-mcp continues without project filtering
- If codebase-mcp unavailable, workflow-mcp omits code references
- Graceful degradation, no hard failures
```

**Implementation:** Phase 1, Week 3 (Documentation)

**Benefits:**
- Developers understand cross-MCP patterns
- Implement correct error handling
- Enable rich integrations

---

### AR-6: Automated Backup Strategy

**Recommendation:** Document backup/restore procedures.

**Documentation:**
```markdown
# docs/deployment.md

## Backup Strategy

### Daily Automated Backups

```bash
#!/bin/bash
# scripts/backup-all-projects.sh
# Daily backup of all active projects

BACKUP_DIR="/var/backups/workflow-mcp"
DATE=$(date +%Y%m%d)
RETENTION_DAYS=30

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup registry database
echo "Backing up registry..."
pg_dump workflow_registry > "$BACKUP_DIR/registry_$DATE.sql"

# Backup all active project databases
echo "Backing up active projects..."
psql -t workflow_registry -c "SELECT database_name FROM projects WHERE status='active'" | \
while read -r db; do
    echo "  Backing up $db..."
    pg_dump "$db" > "$BACKUP_DIR/${db}_$DATE.sql"
done

# Cleanup old backups
echo "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "*.sql" -mtime +$RETENTION_DAYS -delete

echo "✅ Backup complete: $BACKUP_DIR"
```

### Cron Configuration

```bash
# Add to crontab: daily at 2 AM
0 2 * * * /path/to/workflow-mcp/scripts/backup-all-projects.sh >> /var/log/workflow-mcp-backup.log 2>&1
```

### Restore Procedures

**Restore Single Project:**
```bash
# Restore project database
createdb workflow_project_<uuid>
psql workflow_project_<uuid> < backups/workflow_project_<uuid>_20251011.sql

# Verify project in registry
psql workflow_registry -c "SELECT * FROM projects WHERE project_id='<uuid>'"
```

**Restore Registry:**
```bash
# Drop and recreate registry
dropdb workflow_registry
createdb workflow_registry
psql workflow_registry < backups/registry_20251011.sql

# Verify projects table
psql workflow_registry -c "SELECT COUNT(*) FROM projects"
```

**Disaster Recovery (Full Restore):**
```bash
# Restore registry first
psql workflow_registry < backups/registry_20251011.sql

# Restore all project databases
for backup in backups/workflow_project_*_20251011.sql; do
    db_name=$(basename $backup | sed 's/_[0-9]\{8\}\.sql//')
    createdb $db_name
    psql $db_name < $backup
done

# Restart workflow-mcp server
systemctl restart workflow-mcp
```

### Backup Verification

**Weekly Test Restore:**
```bash
#!/bin/bash
# Test restore to verify backups are valid

TEST_DB="workflow_test_restore"
LATEST_BACKUP=$(ls -t backups/registry_*.sql | head -1)

echo "Testing restore from $LATEST_BACKUP..."
createdb $TEST_DB
psql $TEST_DB < $LATEST_BACKUP

# Verify schema
TABLES=$(psql -t $TEST_DB -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'")
if [ "$TABLES" -gt 0 ]; then
    echo "✅ Backup restore successful ($TABLES tables)"
else
    echo "❌ Backup restore failed (no tables found)"
fi

# Cleanup
dropdb $TEST_DB
```

### Monitoring

**Backup Alerts:**
```bash
# Check if backup ran today
if [ ! -f "$BACKUP_DIR/registry_$(date +%Y%m%d).sql" ]; then
    echo "❌ ALERT: Backup missing for $(date +%Y-%m-%d)" | mail -s "workflow-mcp backup failed" admin@example.com
fi
```
```

**Implementation:** Phase 1, Week 3 (Documentation)

**Benefits:**
- Automated backups prevent data loss
- Disaster recovery procedures documented
- Weekly verification ensures backups valid

---

## Updated Implementation Phases

### Phase 1 Enhanced: Core + Minimal Entity System (Weeks 1-3)

**Original Phase 1:** Project management only (create, switch, list projects)

**Revised Phase 1:** Project management + minimal entity system

#### New Phase 1 Deliverables

1. **Project Management** ✅ (unchanged)
   - create_project, switch_active_project, get_active_project, list_projects
   - Registry database + connection pooling
   - Database lifecycle with transactional rollback (C4)

2. **Minimal Entity System** ✅ (NEW - moved from Phase 3)
   - register_entity_type tool
   - create_entity tool
   - query_entities tool
   - update_entity tool (basic, no optimistic locking)
   - JSONB storage with GIN indexing
   - JSON Schema validation

3. **Connection Pool Eviction** ✅ (NEW - from C2)
   - LRU cache with max 50 active pools
   - Automatic eviction of least-recently-used
   - Pool lifecycle management

4. **Performance Measurement** ✅ (NEW - from C5)
   - pytest-benchmark framework
   - CI integration for p95 latency
   - Regression detection (fail if >20%)

#### Rationale for Phase 1 Enhancement

**Immediate Value to codebase-mcp:**
- Can query active project (project_id) ✅
- Can track vendor status (operational/broken) ✅ NEW
- Can link code chunks to entities ✅ NEW

**Minimal Entity System Scope:**
- ~30% of full entity system effort
- Basic CRUD only (no optimistic locking, no schema evolution tools)
- Sufficient for commission work vendor tracking
- Phase 3 adds advanced features

**Risk Mitigation:**
- Connection pool eviction prevents exhaustion (C2)
- Database rollback prevents orphaned entries (C4)
- Performance measurement enforces targets (C5)

#### Phase 1 Enhanced Schedule

**Week 1: Infrastructure (Days 1-5)**
- Day 1-2: Project structure, configuration, registry schema
- Day 3-4: Project database template with entity tables
- Day 5: Database creation with transactional rollback (C4)

**Week 2: Core Tools (Days 1-5)**
- Day 1-2: Project management tools (create, switch, get, list)
- Day 3: Connection pool manager with LRU eviction (C2)
- Day 4-5: Minimal entity system (register_entity_type, create_entity)

**Week 3: Entity System + Testing (Days 1-5)**
- Day 1-2: Entity query + update tools
- Day 3: Performance measurement framework (C5)
- Day 4: Testing suite (unit, integration, protocol, performance)
- Day 5: Documentation and integration guide

#### Phase 1 Enhanced Acceptance Criteria

**Functional:**
- ✅ Create project with isolated database
- ✅ Switch active project (<50ms latency)
- ✅ Query active project metadata
- ✅ List projects with pagination
- ✅ Register entity type with JSON Schema
- ✅ Create entity validated against schema
- ✅ Query entities with JSONB filters
- ✅ Update entity (basic, no optimistic locking)

**Performance:**
- ✅ Project creation: <1 second
- ✅ Project switching: <50ms p95 (excluding first-time pool creation)
- ✅ Entity queries: <100ms p95 (10K entities with GIN index)
- ✅ Connection pools evict after 50 active

**Quality:**
- ✅ mypy --strict passes
- ✅ >90% test coverage
- ✅ All MCP tools invocable
- ✅ Performance tests run in CI

**Integration:**
- ✅ codebase-mcp can query active project
- ✅ Commission project can register "vendor" entity type
- ✅ Create + query vendor entities

#### Phase 1 End-to-End Test

```python
@pytest.mark.asyncio
async def test_phase1_commission_workflow():
    """Test complete Phase 1 workflow for commission work."""

    # 1. Create commission project
    project = await create_project(
        name="invoice-extractor-commission",
        description="Commission work for PDF invoice extraction"
    )
    assert project["project_id"]

    # 2. Switch to commission project
    await switch_active_project(project["project_id"])
    active = await get_active_project()
    assert active["project_id"] == project["project_id"]

    # 3. Register vendor entity type
    entity_type = await register_entity_type(
        project_id=project["project_id"],
        type_name="vendor",
        schema={
            "type": "object",
            "properties": {
                "status": {"enum": ["operational", "broken"]},
                "extractor_version": {"type": "string"},
                "supports_html": {"type": "boolean"}
            },
            "required": ["status", "extractor_version"]
        }
    )
    assert entity_type["type_name"] == "vendor"

    # 4. Create vendor entities
    epson = await create_entity(
        project_id=project["project_id"],
        entity_type="vendor",
        name="EPSON",
        data={
            "status": "operational",
            "extractor_version": "1.2.0",
            "supports_html": True
        }
    )
    assert epson["name"] == "EPSON"

    canon = await create_entity(
        project_id=project["project_id"],
        entity_type="vendor",
        name="Canon",
        data={
            "status": "broken",
            "extractor_version": "0.9.0",
            "supports_html": False
        }
    )
    assert canon["name"] == "Canon"

    # 5. Query broken vendors
    broken = await query_entities(
        project_id=project["project_id"],
        entity_type="vendor",
        filters={"data": {"status": "broken"}},
        limit=10
    )
    assert len(broken) == 1
    assert broken[0]["name"] == "Canon"

    # 6. Update Canon to operational
    updated = await update_entity(
        entity_id=canon["entity_id"],
        data_updates={
            "status": "operational",
            "extractor_version": "1.0.0"
        }
    )
    assert updated["data"]["status"] == "operational"

    # 7. Verify isolation: Create game dev project
    game_project = await create_project(
        name="ttrpg-core-system",
        description="Game development"
    )

    # 8. Query vendors in game dev project (should be empty)
    game_vendors = await query_entities(
        project_id=game_project["project_id"],
        entity_type="vendor"
    )
    assert len(game_vendors) == 0  # Isolation confirmed

    print("✅ Phase 1 Enhanced: All acceptance criteria met")
```

---

### Phase 3 Revised: Complete Features (Weeks 7-9)

**Original Phase 3:** Work items + tasks + entities + deployments

**Revised Phase 3:** Work items + tasks + deployments + entity enhancements

#### Changes from Original Plan

**Removed from Phase 3** (moved to Phase 1):
- Basic entity system (register, create, query, update)
- JSONB storage with GIN indexing
- JSON Schema validation

**Added to Phase 3:**
- Entity enhancements:
  - Optimistic locking for update_entity
  - Schema evolution tools (version history)
  - Advanced query patterns
  - Entity relationships validation
- Schema versioning (C1, AR-2)
- Entity relationship documentation (AR-3)
- Performance benchmarks for all features

#### Phase 3 Revised Deliverables

1. **Hierarchical Work Items** (Week 7, Days 1-3)
   - create_work_item, query_work_item, update_work_item, list_work_items
   - Materialized paths for hierarchy traversal
   - Recursive CTEs for descendants (max 5 levels)
   - Dependency tracking (blocked-by, depends-on)

2. **Task Management** (Week 7, Days 4-5)
   - create_task, update_task, list_tasks
   - Git integration (branch/commit associations)
   - Planning references (links to spec.md, plan.md)
   - Token-efficient summary mode

3. **Entity Enhancements** (Week 8, Days 1-4)
   - **Optimistic locking** for update_entity (version-based)
   - **Schema evolution** (additive-only policy, versioning) (C1)
   - **Advanced queries** (nested properties, array contains)
   - **Entity relationships** (application-level validation) (AR-3)

4. **Deployment Tracking** (Week 8, Day 5)
   - record_deployment, list_deployments
   - Relationships to entities and work items (many-to-many)
   - PR details, test results, constitutional compliance

5. **Integration Testing** (Week 9, Days 1-2)
   - End-to-end workflows (commission, game dev)
   - Performance benchmarks (100 projects, 10K entities)
   - Isolation tests (multi-project separation)

6. **Documentation** (Week 9, Days 3-5)
   - Entity system guide with schema evolution examples
   - Cross-MCP integration patterns (AR-5)
   - Deployment guide with backup strategy (AR-6)
   - Constitutional updates (AR-4)

#### Phase 3 Acceptance Criteria

**Functional:**
- ✅ Hierarchical work items (5 levels deep)
- ✅ Task management with git integration
- ✅ Entity optimistic locking (version-based)
- ✅ Schema evolution (additive changes)
- ✅ Deployment tracking with relationships

**Performance:**
- ✅ Work item hierarchy: <200ms p95 (5 levels)
- ✅ Entity queries: <100ms p95 (10K entities)
- ✅ Task listing: <150ms p95 (summary mode)

**Quality:**
- ✅ >90% test coverage (all features)
- ✅ End-to-end tests (commission + game dev)
- ✅ Performance benchmarks in CI

**Integration:**
- ✅ codebase-mcp can query work items
- ✅ workflow-mcp can query code references
- ✅ Multi-MCP workflows documented

---

## Schema Evolution Strategy (Comprehensive)

### Additive-Only Evolution Policy

**Principle:** Entity type schemas can only evolve in backward-compatible ways.

#### Allowed Changes

1. **Adding Optional Fields:**
   ```json
   // Schema v1
   {
       "properties": {
           "status": {"enum": ["operational", "broken"]},
           "version": {"type": "string"}
       },
       "required": ["status", "version"]
   }

   // Schema v2 (backward compatible)
   {
       "properties": {
           "status": {"enum": ["operational", "broken"]},
           "version": {"type": "string"},
           "test_coverage": {"type": "number"}  // NEW OPTIONAL
       },
       "required": ["status", "version"]  // Same required
   }
   ```
   - ✅ v1 entities still validate against v2 schema
   - ✅ v2 entities can include test_coverage

2. **Making Required Fields Optional:**
   ```json
   // Schema v1
   {"required": ["status", "version", "test_coverage"]}

   // Schema v2 (backward compatible)
   {"required": ["status", "version"]}  // Removed test_coverage
   ```
   - ✅ v1 entities still validate (have test_coverage)
   - ✅ v2 entities can omit test_coverage

3. **Expanding Enum Values:**
   ```json
   // Schema v1
   {"status": {"enum": ["operational", "broken"]}}

   // Schema v2 (backward compatible)
   {"status": {"enum": ["operational", "broken", "maintenance"]}}
   ```
   - ✅ v1 entities still validate (operational/broken are valid)
   - ✅ v2 entities can use "maintenance"

#### Forbidden Changes (Breaking)

1. **Adding Required Fields:**
   ```json
   // Schema v1
   {"required": ["status"]}

   // Schema v2 (BREAKING)
   {"required": ["status", "last_updated"]}
   ```
   - ❌ v1 entities fail validation (missing last_updated)

2. **Removing Fields:**
   ```json
   // Schema v1
   {"properties": {"status": {}, "version": {}}}

   // Schema v2 (BREAKING)
   {"properties": {"status": {}}}  // Removed version
   ```
   - ❌ v1 entities may have version field (orphaned data)

3. **Changing Field Types:**
   ```json
   // Schema v1
   {"version": {"type": "string"}}

   // Schema v2 (BREAKING)
   {"version": {"type": "integer"}}
   ```
   - ❌ v1 entities have string version (fails validation)

4. **Restricting Enum Values:**
   ```json
   // Schema v1
   {"status": {"enum": ["operational", "broken", "maintenance"]}}

   // Schema v2 (BREAKING)
   {"status": {"enum": ["operational", "broken"]}}
   ```
   - ❌ v1 entities with "maintenance" fail validation

#### Implementation

**Schema Versioning Table:**
```sql
CREATE TABLE entity_type_versions (
    entity_type VARCHAR(100) REFERENCES entity_types(type_name) ON DELETE CASCADE,
    version INT NOT NULL,
    schema JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100) DEFAULT 'claude-code',
    PRIMARY KEY (entity_type, version)
);

-- Add version to entity_types
ALTER TABLE entity_types ADD COLUMN schema_version INT DEFAULT 1;
```

**Update Entity Type Tool:**
```python
@mcp.tool()
async def update_entity_type_schema(
    entity_type: str,
    new_schema: dict,
    allow_breaking: bool = False
) -> dict:
    """Update entity type schema with version tracking."""

    # 1. Fetch current schema
    current = await get_entity_type(entity_type)
    current_schema = current["schema"]
    current_version = current["schema_version"]

    # 2. Validate new schema is JSON Schema
    jsonschema.Draft7Validator.check_schema(new_schema)

    # 3. Check if breaking change
    is_breaking = not is_backward_compatible(current_schema, new_schema)

    if is_breaking and not allow_breaking:
        raise ValueError(
            "Schema change is BREAKING (adds required fields, removes fields, or changes types). "
            "Set allow_breaking=True to force, but existing entities may fail validation."
        )

    # 4. Create new version
    new_version = current_version + 1
    await conn.execute(
        """
        INSERT INTO entity_type_versions (entity_type, version, schema, created_by)
        VALUES ($1, $2, $3, $4)
        """,
        entity_type, new_version, new_schema, "claude-code"
    )

    # 5. Update current schema
    await conn.execute(
        """
        UPDATE entity_types
        SET schema = $1, schema_version = $2, updated_at = NOW()
        WHERE type_name = $3
        """,
        new_schema, new_version, entity_type
    )

    logger.info(f"Updated {entity_type} schema: v{current_version} → v{new_version}")

    return {
        "entity_type": entity_type,
        "old_version": current_version,
        "new_version": new_version,
        "is_breaking": is_breaking
    }

def is_backward_compatible(old_schema: dict, new_schema: dict) -> bool:
    """Check if new schema is backward compatible with old."""
    old_required = set(old_schema.get("required", []))
    new_required = set(new_schema.get("required", []))

    # Breaking: Added required fields
    if not old_required.issubset(new_required):
        return False

    # Breaking: Removed properties (even if optional)
    old_props = set(old_schema.get("properties", {}).keys())
    new_props = set(new_schema.get("properties", {}).keys())
    if not old_props.issubset(new_props):
        return False

    # Breaking: Changed property types
    for prop in old_props:
        if prop in new_props:
            old_type = old_schema["properties"][prop].get("type")
            new_type = new_schema["properties"][prop].get("type")
            if old_type and new_type and old_type != new_type:
                return False

    return True
```

**Migration Tool for Additive Changes:**
```python
@mcp.tool()
async def migrate_entities_to_new_schema(
    entity_type: str,
    new_version: int,
    default_values: dict | None = None
) -> dict:
    """Migrate entities to new schema version (additive changes only)."""

    # 1. Fetch new schema
    schema = await get_entity_type_version(entity_type, new_version)

    # 2. Fetch all entities
    entities = await query_entities(entity_type=entity_type)

    # 3. Migrate each entity
    migrated_count = 0
    failed_count = 0

    for entity in entities:
        try:
            # Merge with default values
            updated_data = {**entity["data"], **(default_values or {})}

            # Validate against new schema
            jsonschema.validate(instance=updated_data, schema=schema)

            # Update entity
            await update_entity(
                entity_id=entity["entity_id"],
                data_updates=updated_data
            )

            migrated_count += 1
        except Exception as e:
            logger.error(f"Failed to migrate entity {entity['entity_id']}: {e}")
            failed_count += 1

    return {
        "entity_type": entity_type,
        "new_version": new_version,
        "migrated_count": migrated_count,
        "failed_count": failed_count
    }
```

#### Verification Tests

```python
def test_additive_schema_evolution():
    """Test additive schema changes are backward compatible."""

    # Create entity with v1 schema
    register_entity_type(
        type_name="vendor",
        schema={
            "properties": {"status": {"enum": ["operational", "broken"]}},
            "required": ["status"]
        }
    )

    entity = create_entity(
        entity_type="vendor",
        name="EPSON",
        data={"status": "operational"}
    )

    # Update schema to v2 (add optional field)
    update_entity_type_schema(
        entity_type="vendor",
        new_schema={
            "properties": {
                "status": {"enum": ["operational", "broken"]},
                "test_coverage": {"type": "number"}  # NEW OPTIONAL
            },
            "required": ["status"]
        }
    )

    # Verify v1 entity still validates
    entity_v1 = query_entity(entity["entity_id"])
    assert entity_v1["data"] == {"status": "operational"}  # Still valid

    # Create v2 entity with new field
    entity_v2 = create_entity(
        entity_type="vendor",
        name="Canon",
        data={"status": "operational", "test_coverage": 87.5}
    )
    assert entity_v2["data"]["test_coverage"] == 87.5

def test_breaking_schema_change_rejected():
    """Test breaking schema changes are rejected."""

    register_entity_type(
        type_name="vendor",
        schema={
            "properties": {"status": {"enum": ["operational", "broken"]}},
            "required": ["status"]
        }
    )

    create_entity(
        entity_type="vendor",
        name="EPSON",
        data={"status": "operational"}
    )

    # Attempt to add required field (breaking change)
    with pytest.raises(ValueError, match="BREAKING"):
        update_entity_type_schema(
            entity_type="vendor",
            new_schema={
                "properties": {
                    "status": {"enum": ["operational", "broken"]},
                    "last_updated": {"type": "string"}
                },
                "required": ["status", "last_updated"]  # NEW REQUIRED
            },
            allow_breaking=False
        )
```

---

## Connection Pool Management (Comprehensive)

### LRU Eviction Strategy

**Problem:** 100 projects × 5 connections = 500 connections > PostgreSQL max_connections (200)

**Solution:** LRU cache with max 50 active pools, automatic eviction

#### Implementation

```python
# workflow_mcp/database/pools.py
from cachetools import LRUCache
import asyncpg
import logging

logger = logging.getLogger(__name__)

class ConnectionPoolManager:
    """Manages AsyncPG connection pools per project with LRU eviction."""

    def __init__(
        self,
        registry_dsn: str,
        max_active_pools: int = 50,
        pool_min_size: int = 1,
        pool_max_size: int = 5
    ):
        self.registry_dsn = registry_dsn
        self.max_active_pools = max_active_pools
        self.pool_min_size = pool_min_size
        self.pool_max_size = pool_max_size

        # Registry pool (singleton, always active)
        self.registry_pool: asyncpg.Pool | None = None

        # Project pools (LRU eviction)
        self.project_pools: LRUCache[str, asyncpg.Pool] = LRUCache(
            maxsize=max_active_pools
        )

        # Track pool creation/eviction for monitoring
        self.pools_created = 0
        self.pools_evicted = 0

    async def initialize_registry(self) -> None:
        """Initialize registry database connection pool."""
        logger.info(f"Initializing registry pool: {self.registry_dsn}")
        self.registry_pool = await asyncpg.create_pool(
            dsn=self.registry_dsn,
            min_size=2,
            max_size=10,
            timeout=30,
            command_timeout=60
        )
        logger.info("✅ Registry pool initialized")

    async def get_project_pool(self, project_id: str) -> asyncpg.Pool:
        """Get or create connection pool for project (with LRU eviction)."""

        # Check if pool exists in cache
        if project_id in self.project_pools:
            logger.debug(f"Pool cache HIT for project {project_id}")
            return self.project_pools[project_id]

        # Pool not in cache, create new one
        logger.info(f"Pool cache MISS for project {project_id}, creating new pool")

        # Fetch project metadata from registry
        async with self.registry_pool.acquire() as conn:
            project = await conn.fetchrow(
                "SELECT database_name FROM projects WHERE project_id = $1",
                project_id
            )

            if not project:
                raise ValueError(f"Project {project_id} not found in registry")

        database_name = project["database_name"]

        # Create pool
        pool = await asyncpg.create_pool(
            dsn=f"postgresql://localhost/{database_name}",
            min_size=self.pool_min_size,
            max_size=self.pool_max_size,
            timeout=30,
            command_timeout=60,
            max_inactive_connection_lifetime=3600  # 1 hour
        )

        # Check if adding this pool will trigger eviction
        if len(self.project_pools) >= self.max_active_pools:
            # LRU cache will evict least-recently-used pool
            evicted_project_id = next(iter(self.project_pools))  # Get LRU key
            evicted_pool = self.project_pools[evicted_project_id]

            logger.info(f"Evicting pool for project {evicted_project_id} (LRU)")
            await self._close_pool(evicted_pool)
            self.pools_evicted += 1

        # Add to cache (LRU handles eviction automatically)
        self.project_pools[project_id] = pool
        self.pools_created += 1

        logger.info(f"✅ Created pool for project {project_id} (total active: {len(self.project_pools)})")

        return pool

    async def _close_pool(self, pool: asyncpg.Pool) -> None:
        """Close connection pool gracefully."""
        try:
            await pool.close()
            logger.debug("Pool closed successfully")
        except Exception as e:
            logger.error(f"Failed to close pool: {e}")

    async def close_project_pool(self, project_id: str) -> None:
        """Manually close and remove pool from cache."""
        if project_id in self.project_pools:
            pool = self.project_pools.pop(project_id)
            await self._close_pool(pool)
            logger.info(f"Manually closed pool for project {project_id}")

    async def close_all(self) -> None:
        """Close all connection pools on server shutdown."""
        logger.info("Closing all connection pools...")

        # Close all project pools
        for project_id, pool in list(self.project_pools.items()):
            await self._close_pool(pool)
        self.project_pools.clear()

        # Close registry pool
        if self.registry_pool:
            await self.registry_pool.close()
            self.registry_pool = None

        logger.info(f"✅ All pools closed (created: {self.pools_created}, evicted: {self.pools_evicted})")

    def get_metrics(self) -> dict:
        """Get pool metrics for monitoring."""
        return {
            "active_pools": len(self.project_pools),
            "max_pools": self.max_active_pools,
            "pools_created": self.pools_created,
            "pools_evicted": self.pools_evicted,
            "utilization": len(self.project_pools) / self.max_active_pools
        }

# Global pool manager (singleton)
pool_manager: ConnectionPoolManager | None = None

async def get_pool_manager() -> ConnectionPoolManager:
    """Get or create global pool manager."""
    global pool_manager
    if pool_manager is None:
        pool_manager = ConnectionPoolManager(
            registry_dsn="postgresql://localhost/workflow_registry",
            max_active_pools=50
        )
        await pool_manager.initialize_registry()
    return pool_manager
```

#### Pool Lifecycle

```
1. CREATE (Lazy Loading)
   ↓
   User switches to project A
   ↓
   get_project_pool("project-a-uuid")
   ↓
   Pool cache MISS → Create pool (~100ms first time)
   ↓
   Add to LRU cache

2. USE (Connection Reuse)
   ↓
   User queries entities in project A
   ↓
   get_project_pool("project-a-uuid")
   ↓
   Pool cache HIT → Return existing pool (<1ms)
   ↓
   Acquire connection → Execute query → Release connection

3. EVICT (LRU Strategy)
   ↓
   User switches to 51st project (cache full)
   ↓
   get_project_pool("project-51-uuid")
   ↓
   LRU cache evicts least-recently-used pool (project X)
   ↓
   Close pool X gracefully
   ↓
   Create pool for project 51

4. RELOAD (Amortized Cost)
   ↓
   User switches back to project X (previously evicted)
   ↓
   get_project_pool("project-x-uuid")
   ↓
   Pool cache MISS → Create pool (~100ms)
   ↓
   Add to LRU cache (may evict another pool)
```

#### Configuration

**PostgreSQL Configuration:**
```ini
# postgresql.conf
max_connections = 300  # Registry (10) + Projects (250) + Buffer (40)
```

**Pool Manager Configuration:**
```python
pool_manager = ConnectionPoolManager(
    registry_dsn="postgresql://localhost/workflow_registry",
    max_active_pools=50,     # Max 50 project pools
    pool_min_size=1,          # Min 1 connection per pool
    pool_max_size=5           # Max 5 connections per pool
)
```

**Resource Calculations:**
```
Registry pool:        10 connections (max_size=10)
50 project pools:    250 connections (50 × 5)
Total:               260 connections (within 300 limit)
Buffer:               40 connections (13% headroom)
```

#### Monitoring and Metrics

```python
@mcp.tool()
async def get_pool_metrics() -> dict:
    """Get connection pool metrics for monitoring."""
    manager = await get_pool_manager()
    metrics = manager.get_metrics()

    # Add PostgreSQL connection count
    async with manager.registry_pool.acquire() as conn:
        pg_connections = await conn.fetchval(
            "SELECT count(*) FROM pg_stat_activity"
        )

    return {
        **metrics,
        "postgresql_connections": pg_connections,
        "postgresql_max_connections": 300,
        "connection_utilization": pg_connections / 300
    }
```

**Example Output:**
```json
{
    "active_pools": 48,
    "max_pools": 50,
    "pools_created": 127,
    "pools_evicted": 79,
    "utilization": 0.96,
    "postgresql_connections": 252,
    "postgresql_max_connections": 300,
    "connection_utilization": 0.84
}
```

#### Verification Tests

```python
@pytest.mark.asyncio
async def test_pool_eviction_after_max_pools():
    """Test LRU pool eviction after reaching max active pools."""

    # Create 50 projects (max)
    projects = []
    for i in range(50):
        project = await create_project(f"project-{i}", "Test")
        projects.append(project)
        await switch_active_project(project["project_id"])

    # Verify 50 pools active
    metrics = await get_pool_metrics()
    assert metrics["active_pools"] == 50

    # Create 51st project (triggers eviction)
    project_51 = await create_project("project-51", "Test")
    await switch_active_project(project_51["project_id"])

    # Verify still 50 pools active (LRU evicted)
    metrics = await get_pool_metrics()
    assert metrics["active_pools"] == 50
    assert metrics["pools_evicted"] >= 1

    # Switch back to evicted project (pool recreated)
    await switch_active_project(projects[0]["project_id"])
    metrics = await get_pool_metrics()
    assert metrics["pools_created"] >= 51

@pytest.mark.asyncio
async def test_pool_eviction_performance():
    """Test pool eviction and recreation latency."""

    # Create 60 projects (triggers 10 evictions)
    for i in range(60):
        project = await create_project(f"project-{i}", "Test")

        start = time.time()
        await switch_active_project(project["project_id"])
        elapsed = time.time() - start

        # First-time pool creation: <100ms
        assert elapsed < 0.100, f"Switch took {elapsed*1000:.1f}ms (expected <100ms)"

    # Switch back to first project (evicted, pool recreated)
    start = time.time()
    await switch_active_project(projects[0]["project_id"])
    elapsed = time.time() - start

    # Pool recreation: <100ms (amortized)
    assert elapsed < 0.100, f"Reload took {elapsed*1000:.1f}ms (expected <100ms)"
```

---

## Database Lifecycle with Rollback (Comprehensive)

### Transactional Database Creation

**Problem:** If schema initialization fails, project entry is orphaned with broken database.

**Solution:** Wrap database creation in transaction, rollback on failure.

#### Implementation

```python
@mcp.tool()
async def create_project(
    name: str,
    description: str,
    metadata: dict | None = None
) -> dict:
    """Create project with transactional rollback on failure."""

    project_id = str(uuid.uuid4())
    database_name = f"workflow_project_{project_id}"
    created_at = datetime.utcnow()

    logger.info(f"Creating project '{name}' with ID {project_id}")

    # Get pool manager
    manager = await get_pool_manager()

    async with manager.registry_pool.acquire() as registry_conn:
        # Start transaction for registry operations
        async with registry_conn.transaction():

            # Step 1: Validate name is unique
            existing = await registry_conn.fetchval(
                "SELECT COUNT(*) FROM projects WHERE name = $1",
                name
            )
            if existing > 0:
                raise ValueError(f"Project name '{name}' already exists")

            # Step 2: Insert into registry
            await registry_conn.execute(
                """
                INSERT INTO projects (
                    project_id, name, description, database_name, metadata,
                    created_at, created_by
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                project_id, name, description, database_name, metadata or {},
                created_at, "claude-code"
            )

            logger.info(f"  ✅ Inserted project into registry")

            try:
                # Step 3: Create database (CANNOT ROLLBACK - outside transaction)
                await registry_conn.execute(f"CREATE DATABASE {database_name}")
                logger.info(f"  ✅ Created database {database_name}")

                # Step 4: Initialize schema in new database
                async with asyncpg.connect(
                    f"postgresql://localhost/{database_name}"
                ) as db_conn:
                    # Read schema SQL file
                    schema_path = Path(__file__).parent.parent / "migrations" / "002_project_schema.sql"
                    schema_sql = schema_path.read_text()

                    # Execute schema initialization
                    await db_conn.execute(schema_sql)
                    logger.info(f"  ✅ Initialized schema in {database_name}")

                # Success: Commit registry transaction
                logger.info(f"✅ Project '{name}' created successfully")

            except Exception as error:
                # Schema initialization failed - ROLLBACK
                logger.error(f"  ❌ Schema initialization failed: {error}")
                logger.info("  🔄 Rolling back...")

                # Try to drop database (cleanup)
                try:
                    await registry_conn.execute(f"DROP DATABASE IF EXISTS {database_name}")
                    logger.info(f"  ✅ Dropped database {database_name}")
                except Exception as drop_error:
                    logger.error(f"  ❌ Failed to drop database: {drop_error}")

                # Re-raise to trigger registry transaction rollback
                raise RuntimeError(
                    f"Project creation failed: {error}. "
                    f"Database '{database_name}' and registry entry rolled back."
                ) from error

    # Return project metadata
    return {
        "project_id": project_id,
        "name": name,
        "description": description,
        "database_name": database_name,
        "created_at": created_at.isoformat(),
        "metadata": metadata or {}
    }
```

#### Rollback Flow

```
1. HAPPY PATH (Success)
   ↓
   Start registry transaction
   ↓
   INSERT INTO projects → Success
   ↓
   CREATE DATABASE → Success
   ↓
   Initialize schema → Success
   ↓
   Commit registry transaction
   ↓
   ✅ Project created

2. FAILURE PATH (Schema Error)
   ↓
   Start registry transaction
   ↓
   INSERT INTO projects → Success
   ↓
   CREATE DATABASE → Success
   ↓
   Initialize schema → FAILS (syntax error)
   ↓
   DROP DATABASE (cleanup)
   ↓
   Raise exception → Rollback registry transaction
   ↓
   ❌ No orphaned entries

3. FAILURE PATH (Database Creation Error)
   ↓
   Start registry transaction
   ↓
   INSERT INTO projects → Success
   ↓
   CREATE DATABASE → FAILS (permission denied)
   ↓
   Raise exception → Rollback registry transaction
   ↓
   ❌ No orphaned entries
```

#### Error Handling

```python
# workflow_mcp/errors.py
class ProjectCreationError(Exception):
    """Raised when project creation fails with rollback."""

    def __init__(self, message: str, project_id: str, database_name: str):
        super().__init__(message)
        self.project_id = project_id
        self.database_name = database_name

# Usage
try:
    project = await create_project("test-project", "Test")
except ProjectCreationError as e:
    logger.error(f"Project creation failed: {e}")
    logger.error(f"  Project ID: {e.project_id}")
    logger.error(f"  Database: {e.database_name}")
    # Return MCP error response
    return {"error": str(e), "details": {"project_id": e.project_id}}
```

#### Verification Tests

```python
@pytest.mark.asyncio
async def test_schema_initialization_failure_rollback():
    """Test rollback when schema initialization fails."""

    # Mock schema file to cause syntax error
    with mock.patch("Path.read_text", return_value="INVALID SQL SYNTAX;"):
        with pytest.raises(RuntimeError, match="Project creation failed"):
            await create_project("test-project", "Test")

    # Verify no project in registry
    manager = await get_pool_manager()
    async with manager.registry_pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM projects WHERE name = 'test-project'"
        )
        assert count == 0, "Project should not exist in registry"

    # Verify no database exists
    async with manager.registry_pool.acquire() as conn:
        databases = await conn.fetch(
            "SELECT datname FROM pg_database WHERE datname LIKE 'workflow_project_%'"
        )
        db_names = [row["datname"] for row in databases]
        assert not any("test-project" in db for db in db_names), \
            "Database should not exist"

@pytest.mark.asyncio
async def test_retry_after_failed_creation():
    """Test retry with same name succeeds after rollback."""

    # First attempt fails
    with mock.patch("Path.read_text", return_value="INVALID SQL;"):
        with pytest.raises(RuntimeError):
            await create_project("test-project", "Test")

    # Second attempt succeeds (no unique constraint violation)
    project = await create_project("test-project", "Test")
    assert project["name"] == "test-project"
```

---

## Performance Measurement Integration (Comprehensive)

### pytest-benchmark Framework

**Goal:** Measure and enforce p95 latency targets in CI.

**Targets:**
- Project switching: <50ms p95
- Work item operations: <200ms p95
- Entity queries: <100ms p95

#### Implementation

**1. Performance Test Suite:**
```python
# tests/performance/test_latency.py
import pytest
import random
import time
from pytest_benchmark.fixture import BenchmarkFixture

@pytest.fixture
async def performance_dataset():
    """Fixture: Large dataset for performance testing."""

    # Create 100 projects
    projects = []
    for i in range(100):
        project = await create_project(f"perf-project-{i}", "Performance test")

        # Register entity type
        await register_entity_type(
            project_id=project["project_id"],
            type_name="vendor",
            schema={
                "type": "object",
                "properties": {
                    "status": {"enum": ["operational", "broken"]},
                    "version": {"type": "string"}
                },
                "required": ["status", "version"]
            }
        )

        # Create 10,000 entities per project
        for j in range(10000):
            await create_entity(
                project_id=project["project_id"],
                entity_type="vendor",
                name=f"vendor-{j}",
                data={
                    "status": "operational" if j % 10 != 0 else "broken",
                    "version": "1.0.0"
                }
            )

        projects.append(project)

    yield projects

    # Cleanup
    for project in projects:
        await delete_project(project["project_id"])

@pytest.mark.benchmark(group="project-switching")
def test_project_switching_p95_latency(benchmark: BenchmarkFixture, performance_dataset):
    """Benchmark project switching p95 latency (<50ms target)."""

    projects = performance_dataset

    def switch():
        # Switch to random project
        project = random.choice(projects)
        return switch_active_project(project["project_id"])

    # Run benchmark: 100 iterations, 10 rounds
    result = benchmark.pedantic(switch, iterations=100, rounds=10)

    # Extract p95 latency
    p95_ms = result.stats.percentile_95 * 1000

    # Assert target
    assert p95_ms < 50.0, \
        f"❌ p95 latency {p95_ms:.1f}ms exceeds 50ms target"

    print(f"✅ Project switching p95: {p95_ms:.1f}ms (target: <50ms)")

@pytest.mark.benchmark(group="entity-queries")
def test_entity_query_p95_latency(benchmark: BenchmarkFixture, performance_dataset):
    """Benchmark entity query p95 latency (<100ms target)."""

    project = performance_dataset[0]  # Use first project (10K entities)

    def query():
        return query_entities(
            project_id=project["project_id"],
            entity_type="vendor",
            filters={"data": {"status": "broken"}},
            limit=10
        )

    result = benchmark.pedantic(query, iterations=100, rounds=10)
    p95_ms = result.stats.percentile_95 * 1000

    assert p95_ms < 100.0, \
        f"❌ p95 latency {p95_ms:.1f}ms exceeds 100ms target"

    print(f"✅ Entity query p95: {p95_ms:.1f}ms (target: <100ms)")

@pytest.mark.benchmark(group="work-items")
def test_work_item_hierarchy_p95_latency(benchmark: BenchmarkFixture, performance_dataset):
    """Benchmark work item hierarchy query p95 latency (<200ms target)."""

    project = performance_dataset[0]

    # Create 5-level hierarchy
    root = await create_work_item(
        project_id=project["project_id"],
        item_type="project",
        title="Root",
        metadata={}
    )

    current_parent = root["work_item_id"]
    for level in range(4):
        child = await create_work_item(
            project_id=project["project_id"],
            item_type="session",
            title=f"Level-{level+1}",
            parent_id=current_parent,
            metadata={}
        )
        current_parent = child["work_item_id"]

    def query_hierarchy():
        return query_work_item(
            work_item_id=root["work_item_id"],
            include_children=True
        )

    result = benchmark.pedantic(query_hierarchy, iterations=100, rounds=10)
    p95_ms = result.stats.percentile_95 * 1000

    assert p95_ms < 200.0, \
        f"❌ p95 latency {p95_ms:.1f}ms exceeds 200ms target"

    print(f"✅ Work item hierarchy p95: {p95_ms:.1f}ms (target: <200ms)")
```

**2. CI Integration:**
```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Run unit tests
        run: pytest tests/unit/ --cov=workflow_mcp

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Run integration tests
        run: pytest tests/integration/

  performance-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"
          pip install pytest-benchmark

      - name: Run performance tests
        run: |
          pytest tests/performance/ \
            --benchmark-only \
            --benchmark-json=benchmark-current.json

      - name: Download baseline benchmark
        run: |
          # Download from artifacts or use checked-in baseline
          cp benchmark-baseline.json baseline.json || echo "{}" > baseline.json

      - name: Check performance regression
        run: |
          python scripts/check_performance_regression.py \
            --baseline=baseline.json \
            --current=benchmark-current.json \
            --threshold=0.20

      - name: Upload benchmark results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: benchmark-results
          path: benchmark-current.json
```

**3. Regression Detection Script:**
```python
# scripts/check_performance_regression.py
import json
import sys
from pathlib import Path

def check_regression(
    baseline_file: str,
    current_file: str,
    threshold: float = 0.20
) -> bool:
    """
    Check if p95 latency regressed by >threshold (20% default).

    Returns:
        True if no regressions, False if regressions detected
    """

    # Load baseline
    baseline_path = Path(baseline_file)
    if not baseline_path.exists():
        print(f"⚠️  No baseline found at {baseline_file}")
        print("   Creating baseline from current results...")

        # Copy current to baseline
        current_path = Path(current_file)
        baseline_path.write_text(current_path.read_text())

        print("✅ Baseline created. Run tests again to check regression.")
        return True

    with open(baseline_file) as f:
        baseline = json.load(f)

    with open(current_file) as f:
        current = json.load(f)

    # Extract benchmarks
    baseline_benchmarks = {
        b["name"]: b["stats"] for b in baseline.get("benchmarks", [])
    }
    current_benchmarks = {
        b["name"]: b["stats"] for b in current.get("benchmarks", [])
    }

    regressions = []
    improvements = []

    for name in baseline_benchmarks:
        if name not in current_benchmarks:
            print(f"⚠️  Benchmark '{name}' missing in current results")
            continue

        baseline_p95 = baseline_benchmarks[name].get("percentile_95", 0)
        current_p95 = current_benchmarks[name].get("percentile_95", 0)

        if baseline_p95 == 0:
            continue

        # Calculate regression percentage
        regression_pct = (current_p95 - baseline_p95) / baseline_p95

        if regression_pct > threshold:
            regressions.append({
                "benchmark": name,
                "baseline_p95_ms": baseline_p95 * 1000,
                "current_p95_ms": current_p95 * 1000,
                "regression_pct": regression_pct * 100
            })
        elif regression_pct < -0.05:  # Improved by >5%
            improvements.append({
                "benchmark": name,
                "baseline_p95_ms": baseline_p95 * 1000,
                "current_p95_ms": current_p95 * 1000,
                "improvement_pct": -regression_pct * 100
            })

    # Print results
    print("\n" + "="*80)
    print("Performance Regression Analysis")
    print("="*80)

    if improvements:
        print(f"\n✅ Improvements ({len(improvements)}):")
        for imp in improvements:
            print(f"  {imp['benchmark']}")
            print(f"    {imp['baseline_p95_ms']:.1f}ms → {imp['current_p95_ms']:.1f}ms "
                  f"(-{imp['improvement_pct']:.1f}%)")

    if regressions:
        print(f"\n❌ Regressions ({len(regressions)}):")
        for reg in regressions:
            print(f"  {reg['benchmark']}")
            print(f"    {reg['baseline_p95_ms']:.1f}ms → {reg['current_p95_ms']:.1f}ms "
                  f"(+{reg['regression_pct']:.1f}%)")

        print(f"\n❌ FAIL: {len(regressions)} benchmark(s) regressed by >{threshold*100:.0f}%")
        print("="*80)
        return False
    else:
        print(f"\n✅ PASS: No performance regressions (threshold: {threshold*100:.0f}%)")
        print("="*80)
        return True

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Check performance regression")
    parser.add_argument("--baseline", required=True, help="Baseline benchmark JSON")
    parser.add_argument("--current", required=True, help="Current benchmark JSON")
    parser.add_argument("--threshold", type=float, default=0.20,
                        help="Regression threshold (default: 0.20 = 20%%)")

    args = parser.parse_args()

    passed = check_regression(args.baseline, args.current, args.threshold)
    sys.exit(0 if passed else 1)
```

**4. Baseline Management:**
```bash
# scripts/update-baseline.sh
#!/bin/bash
# Update performance baseline after validating improvements

set -e

echo "Running performance tests..."
pytest tests/performance/ --benchmark-only --benchmark-json=benchmark-current.json

echo "Validating improvements..."
python scripts/check_performance_regression.py \
    --baseline=benchmark-baseline.json \
    --current=benchmark-current.json \
    --threshold=0.20

echo "✅ No regressions detected"
echo ""
read -p "Update baseline? (y/n) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    cp benchmark-current.json benchmark-baseline.json
    git add benchmark-baseline.json
    git commit -m "perf: update performance baseline"
    echo "✅ Baseline updated"
else
    echo "❌ Baseline NOT updated"
fi
```

#### Verification

```bash
# Run performance tests locally
pytest tests/performance/ --benchmark-only --benchmark-json=benchmark.json

# Check against baseline
python scripts/check_performance_regression.py \
    --baseline=benchmark-baseline.json \
    --current=benchmark.json \
    --threshold=0.20

# Output:
# ================================================================================
# Performance Regression Analysis
# ================================================================================
#
# ✅ Improvements (1):
#   test_entity_query_p95_latency
#     95.2ms → 87.3ms (-8.3%)
#
# ✅ PASS: No performance regressions (threshold: 20%)
# ================================================================================
```

---

## Enhanced Generic Entity System

### Schema Evolution Examples

See "Schema Evolution Strategy" section above for comprehensive examples.

### Entity Relationship Patterns

**Application-Level Validation:**

```python
# workflow_mcp/validation.py
async def validate_entity_references(
    project_id: str,
    entity_type: str,
    data: dict,
    reference_fields: list[str]
) -> None:
    """
    Validate entity references exist (application-level foreign keys).

    Args:
        project_id: Project ID
        entity_type: Entity type of referenced entities
        data: Entity data containing references
        reference_fields: List of fields that contain entity references

    Raises:
        ValueError: If referenced entity not found
    """

    for field in reference_fields:
        if field not in data:
            continue

        references = data[field]
        if not isinstance(references, list):
            references = [references]

        for ref_name in references:
            # Query referenced entity
            ref_entities = await query_entities(
                project_id=project_id,
                entity_type=entity_type,
                filters={"data": {"name": ref_name}},
                limit=1
            )

            if not ref_entities:
                raise ValueError(
                    f"Referenced entity '{ref_name}' not found in {entity_type}"
                )

# Usage in create_entity
@mcp.tool()
async def create_entity_with_validation(
    project_id: str,
    entity_type: str,
    name: str,
    data: dict,
    validate_references: bool = True
) -> dict:
    """Create entity with optional reference validation."""

    # 1. Validate against JSON Schema
    schema = await get_entity_type_schema(project_id, entity_type)
    jsonschema.validate(instance=data, schema=schema)

    # 2. Validate entity references (optional)
    if validate_references and "dependencies" in data:
        await validate_entity_references(
            project_id=project_id,
            entity_type=entity_type,
            data=data,
            reference_fields=["dependencies"]
        )

    # 3. Create entity
    return await create_entity(project_id, entity_type, name, data)
```

**Soft Delete with Reference Check:**

```python
@mcp.tool()
async def delete_entity_safe(
    entity_id: str,
    check_references: bool = True
) -> dict:
    """Delete entity with optional reference check."""

    # 1. Fetch entity
    entity = await query_entity(entity_id)

    # 2. Check for references (optional)
    if check_references:
        references = await find_entity_references(
            project_id=entity["project_id"],
            entity_type=entity["entity_type"],
            entity_name=entity["name"]
        )

        if references:
            raise ValueError(
                f"Cannot delete '{entity['name']}': "
                f"{len(references)} entity(ies) reference it"
            )

    # 3. Soft delete (set deleted_at)
    await update_entity(
        entity_id=entity_id,
        data_updates={"deleted_at": datetime.utcnow().isoformat()}
    )

    return {"entity_id": entity_id, "status": "deleted"}

async def find_entity_references(
    project_id: str,
    entity_type: str,
    entity_name: str
) -> list[dict]:
    """Find entities that reference given entity."""

    # Query all entities of same type
    all_entities = await query_entities(
        project_id=project_id,
        entity_type=entity_type
    )

    # Check dependencies field
    references = []
    for entity in all_entities:
        dependencies = entity.get("data", {}).get("dependencies", [])
        if entity_name in dependencies:
            references.append(entity)

    return references
```

### Query Performance Optimization

**GIN Index Usage:**

```sql
-- Efficient: Uses GIN index (containment)
SELECT * FROM entities
WHERE data @> '{"status": "operational"}'::jsonb;

-- Efficient: Uses GIN index (nested containment)
SELECT * FROM entities
WHERE data @> '{"test_results": {"coverage_percent": 85}}'::jsonb;

-- Efficient: Uses GIN index (array containment)
SELECT * FROM entities
WHERE data->'dependencies' @> '["Attribute System"]'::jsonb;

-- Inefficient: Full scan (no index)
SELECT * FROM entities
WHERE data->>'notes' LIKE '%bug%';
```

**Query Optimization Guide:**
```markdown
# docs/entity-query-optimization.md

## Query Performance Guide

### Fast Queries (Uses GIN Index)

1. **Simple Containment:**
   ```sql
   WHERE data @> '{"status": "broken"}'
   ```
   - Latency: 5-10ms (10K entities)
   - Index: ✅ GIN

2. **Nested Containment:**
   ```sql
   WHERE data @> '{"test_results": {"tests_passed": 24}}'
   ```
   - Latency: 10-20ms (10K entities)
   - Index: ✅ GIN

3. **Array Containment:**
   ```sql
   WHERE data->'dependencies' @> '["X"]'
   ```
   - Latency: 10-20ms (10K entities)
   - Index: ✅ GIN

### Slow Queries (No Index)

1. **LIKE Pattern Matching:**
   ```sql
   WHERE data->>'notes' LIKE '%bug%'
   ```
   - Latency: 100-200ms (10K entities)
   - Index: ❌ Full scan
   - **Recommendation:** Avoid LIKE, use containment instead

2. **Comparison Operators:**
   ```sql
   WHERE (data->'test_results'->>'coverage_percent')::float > 80
   ```
   - Latency: 50-100ms (10K entities)
   - Index: ⚠️ Partial (scans GIN, filters in memory)
   - **Recommendation:** OK for occasional use, avoid in hot paths

### Best Practices

1. **Use Containment for Exact Matches:**
   ```python
   # Good
   filters = {"data": {"status": "operational"}}

   # Avoid
   filters = {"data": {"status": {"$like": "operational"}}}
   ```

2. **Pre-Filter by Entity Type:**
   ```python
   # Always include entity_type in query
   query_entities(entity_type="vendor", filters={...})
   ```

3. **Limit Result Sets:**
   ```python
   # Always specify limit
   query_entities(entity_type="vendor", limit=100)
   ```

4. **Use Pagination:**
   ```python
   # Cursor-based pagination (future enhancement)
   query_entities(cursor="<token>", limit=100)
   ```
```

### Limitations Documentation

See "Resolved Critical Issues > C1: Schema Evolution Strategy" for complete documentation.

---

## Updated Testing Strategy

### Schema Evolution Tests

```python
# tests/integration/test_schema_evolution.py

def test_additive_schema_change_backward_compatible():
    """Test additive schema changes preserve backward compatibility."""

    # Register v1 schema
    register_entity_type(
        type_name="vendor",
        schema={
            "properties": {"status": {"enum": ["operational", "broken"]}},
            "required": ["status"]
        }
    )

    # Create entity with v1 schema
    entity_v1 = create_entity(
        entity_type="vendor",
        name="EPSON",
        data={"status": "operational"}
    )

    # Update schema to v2 (add optional field)
    update_entity_type_schema(
        entity_type="vendor",
        new_schema={
            "properties": {
                "status": {"enum": ["operational", "broken"]},
                "test_coverage": {"type": "number"}
            },
            "required": ["status"]
        }
    )

    # Verify v1 entity still validates
    entity = query_entity(entity_v1["entity_id"])
    assert entity["data"] == {"status": "operational"}

    # Create entity with v2 schema
    entity_v2 = create_entity(
        entity_type="vendor",
        name="Canon",
        data={"status": "operational", "test_coverage": 87.5}
    )
    assert entity_v2["data"]["test_coverage"] == 87.5

def test_breaking_schema_change_rejected():
    """Test breaking schema changes are rejected by default."""

    register_entity_type(
        type_name="vendor",
        schema={
            "properties": {"status": {"enum": ["operational", "broken"]}},
            "required": ["status"]
        }
    )

    create_entity(
        entity_type="vendor",
        name="EPSON",
        data={"status": "operational"}
    )

    # Attempt breaking change (add required field)
    with pytest.raises(ValueError, match="BREAKING"):
        update_entity_type_schema(
            entity_type="vendor",
            new_schema={
                "properties": {
                    "status": {"enum": ["operational", "broken"]},
                    "last_updated": {"type": "string"}
                },
                "required": ["status", "last_updated"]
            }
        )

def test_schema_version_history():
    """Test schema version history is tracked."""

    register_entity_type(
        type_name="vendor",
        schema={
            "properties": {"status": {"enum": ["operational", "broken"]}},
            "required": ["status"]
        }
    )

    # Update schema twice
    update_entity_type_schema(
        entity_type="vendor",
        new_schema={
            "properties": {
                "status": {"enum": ["operational", "broken"]},
                "version": {"type": "string"}
            },
            "required": ["status"]
        }
    )

    update_entity_type_schema(
        entity_type="vendor",
        new_schema={
            "properties": {
                "status": {"enum": ["operational", "broken"]},
                "version": {"type": "string"},
                "test_coverage": {"type": "number"}
            },
            "required": ["status"]
        }
    )

    # Query version history
    versions = await query_entity_type_versions("vendor")
    assert len(versions) == 3  # v1, v2, v3
    assert versions[0]["version"] == 1
    assert versions[1]["version"] == 2
    assert versions[2]["version"] == 3
```

### Connection Pool Eviction Tests

```python
# tests/integration/test_pool_eviction.py

@pytest.mark.asyncio
async def test_pool_eviction_after_50_projects():
    """Test LRU pool eviction after 50 active projects."""

    # Create 50 projects (max active pools)
    projects = []
    for i in range(50):
        project = await create_project(f"project-{i}", "Test")
        projects.append(project)
        await switch_active_project(project["project_id"])

    # Verify 50 pools active
    metrics = await get_pool_metrics()
    assert metrics["active_pools"] == 50
    assert metrics["pools_evicted"] == 0

    # Create 51st project (triggers eviction)
    project_51 = await create_project("project-51", "Test")
    await switch_active_project(project_51["project_id"])

    # Verify still 50 pools, 1 eviction
    metrics = await get_pool_metrics()
    assert metrics["active_pools"] == 50
    assert metrics["pools_evicted"] == 1

@pytest.mark.asyncio
async def test_evicted_pool_recreation():
    """Test evicted pool is recreated on next access."""

    # Create 60 projects (triggers 10 evictions)
    projects = []
    for i in range(60):
        project = await create_project(f"project-{i}", "Test")
        projects.append(project)
        await switch_active_project(project["project_id"])

    # First 10 projects have evicted pools
    # Switch back to first project (pool recreated)
    start = time.time()
    await switch_active_project(projects[0]["project_id"])
    elapsed = time.time() - start

    # Pool recreation should be fast (<100ms)
    assert elapsed < 0.100, f"Pool recreation took {elapsed*1000:.1f}ms"

@pytest.mark.asyncio
async def test_pool_eviction_prevents_exhaustion():
    """Test pool eviction prevents connection exhaustion."""

    # Create 100 projects (would be 500 connections without eviction)
    for i in range(100):
        project = await create_project(f"project-{i}", "Test")
        await switch_active_project(project["project_id"])

    # Verify only 50 pools active (250 connections)
    metrics = await get_pool_metrics()
    assert metrics["active_pools"] == 50
    assert metrics["postgresql_connections"] < 300  # Within limit
```

### Database Rollback Tests

```python
# tests/integration/test_database_rollback.py

@pytest.mark.asyncio
async def test_schema_failure_rollback():
    """Test database + registry rollback on schema failure."""

    # Mock schema file to cause error
    with mock.patch("Path.read_text", return_value="INVALID SQL;"):
        with pytest.raises(RuntimeError, match="Project creation failed"):
            await create_project("test-project", "Test")

    # Verify no project in registry
    manager = await get_pool_manager()
    async with manager.registry_pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM projects WHERE name = 'test-project'"
        )
        assert count == 0

    # Verify no database exists
    async with manager.registry_pool.acquire() as conn:
        databases = await conn.fetch(
            "SELECT datname FROM pg_database WHERE datname LIKE 'workflow_project_%'"
        )
        db_names = [row["datname"] for row in databases]
        test_dbs = [db for db in db_names if "test-project" in db]
        assert len(test_dbs) == 0

@pytest.mark.asyncio
async def test_retry_after_rollback():
    """Test retry with same name succeeds after rollback."""

    # First attempt fails
    with mock.patch("Path.read_text", return_value="INVALID;"):
        with pytest.raises(RuntimeError):
            await create_project("test-project", "Test")

    # Second attempt succeeds
    project = await create_project("test-project", "Test")
    assert project["name"] == "test-project"
```

### Performance Benchmarks in CI

See "Performance Measurement Integration" section above for CI configuration.

---

## Risk Mitigation

### Updated Risk Assessment

| Risk | Original Level | Mitigation | New Level |
|------|----------------|------------|-----------|
| Connection pool exhaustion | HIGH | LRU eviction (max 50 pools) | LOW |
| Schema evolution challenges | HIGH | Additive-only policy + versioning | MEDIUM |
| JSONB type safety gap | MEDIUM | Pydantic models + JSON Schema | LOW |
| Entity relationship limitations | MEDIUM | Application-level validation | LOW |
| Database rollback on failure | HIGH | Transactional lifecycle | LOW |
| Performance measurement gap | HIGH | pytest-benchmark + CI | LOW |

### All HIGH/CRITICAL Risks Addressed

1. **Connection Pool Exhaustion** → LOW
   - LRU cache limits active pools to 50
   - Automatic eviction of least-recently-used
   - Prevents PostgreSQL connection limit

2. **Schema Evolution** → MEDIUM
   - Additive-only policy documented
   - Schema versioning implemented
   - Breaking changes rejected by default
   - Migration tools for additive changes

3. **Database Rollback** → LOW
   - Transactional creation with rollback
   - Orphaned entries prevented
   - Retry succeeds after failure

4. **Performance Measurement** → LOW
   - pytest-benchmark framework
   - CI integration with regression detection
   - p95 latency targets enforced

---

## Acceptance Criteria

### Phase 1 Enhanced Criteria

**Functional:**
- ✅ Create project with isolated database
- ✅ Switch active project (<50ms p95 excluding first-time)
- ✅ Query active project metadata
- ✅ List projects with pagination
- ✅ Register entity type with JSON Schema
- ✅ Create entity validated against schema
- ✅ Query entities with JSONB filters
- ✅ Update entity (basic)

**Performance:**
- ✅ Project creation: <1 second (with rollback)
- ✅ Project switching: <50ms p95 (subsequent switches)
- ✅ Entity queries: <100ms p95 (10K entities, GIN index)
- ✅ Connection pools: Max 50 active, LRU eviction

**Quality:**
- ✅ mypy --strict passes
- ✅ >90% test coverage
- ✅ All MCP tools invocable
- ✅ Performance tests in CI

**Integration:**
- ✅ codebase-mcp can query active project
- ✅ Commission project can register vendor entity
- ✅ Create + query vendor entities

### Phase 3 Revised Criteria

**Functional:**
- ✅ Hierarchical work items (5 levels)
- ✅ Task management with git integration
- ✅ Entity optimistic locking
- ✅ Schema evolution (additive changes)
- ✅ Deployment tracking

**Performance:**
- ✅ Work item hierarchy: <200ms p95
- ✅ Entity queries: <100ms p95
- ✅ Task listing: <150ms p95

**Quality:**
- ✅ >90% test coverage
- ✅ End-to-end tests (commission + game dev)
- ✅ Performance benchmarks pass

**Integration:**
- ✅ Cross-MCP workflows documented
- ✅ Entity relationships validated

---

## Sign-Off Checklist

### Critical Issues (All Resolved)

- [x] **C1: Schema Evolution Strategy** - Additive-only policy with versioning
- [x] **C2: Connection Pool Exhaustion** - LRU eviction (max 50 pools)
- [x] **C3: Phase 1 Deliverable Value** - Minimal entity system added
- [x] **C4: Database Creation Rollback** - Transactional lifecycle
- [x] **C5: Performance Measurement** - pytest-benchmark + CI

### Architectural Recommendations (All Addressed)

- [x] **AR-1: Connection Pool Eviction** - LRU cache implemented
- [x] **AR-2: Schema Versioning** - entity_type_versions table
- [x] **AR-3: Entity Relationship Limits** - Documentation added
- [x] **AR-4: First-Time Pool Latency** - Constitutional clarification
- [x] **AR-5: Cross-MCP Integration** - Examples documented
- [x] **AR-6: Automated Backup** - Scripts and procedures

### Deliverables

- [x] **Phase 1 Enhanced** - Includes minimal entity system
- [x] **Phase 3 Revised** - Reduced scope, entity enhancements
- [x] **Schema Evolution** - Comprehensive strategy
- [x] **Connection Pool Management** - LRU eviction
- [x] **Database Lifecycle** - Transactional rollback
- [x] **Performance Measurement** - Framework + CI

### Constitutional Compliance

- [x] All 12 principles: COMPLIANT
- [x] Principle XII (Generic Entity Adaptability): Exemplary
- [x] Performance targets: Achievable and measurable
- [x] Type safety: Runtime validation comprehensive

### Ready for Implementation

- [x] All critical issues resolved
- [x] All architectural recommendations integrated
- [x] Phase 1 provides immediate value to codebase-mcp
- [x] Connection pool exhaustion prevented
- [x] Schema evolution strategy complete
- [x] Plan is implementation-ready

---

## Summary

This final implementation plan addresses all critical issues and incorporates architectural recommendations to deliver a production-ready workflow-mcp server. The enhanced Phase 1 provides immediate value to codebase-mcp through vendor tracking, while comprehensive risk mitigations ensure scalability and reliability.

**Key Improvements:**

1. **Phase 1 Enhanced**: Minimal entity system enables vendor tracking from day one
2. **Connection Pool Eviction**: LRU cache prevents exhaustion, supports 100+ projects
3. **Schema Evolution**: Additive-only policy with versioning enables safe changes
4. **Database Lifecycle**: Transactional rollback prevents orphaned entries
5. **Performance Measurement**: pytest-benchmark enforces p95 targets in CI

**Plan Status:** APPROVED FOR IMPLEMENTATION 🚀

The workflow-mcp architecture successfully extends the codebase-mcp constitutional foundation with a novel generic entity system that enables domain-agnostic project management without sacrificing production quality, performance, or type safety.

---

**Document Version:** 1.0 (Final Revision)
**Date:** 2025-10-11
**Next Step:** Proceed to `/tasks` and `/implement` workflow
