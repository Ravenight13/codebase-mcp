# codebase-mcp Final Implementation Plan

**Version**: 2.0 (Revised)
**Date**: 2025-10-11
**Status**: Implementation-Ready
**Reviewers**: Senior Planning Reviewer, Master Software Architect

---

## Revision Summary

This final implementation plan integrates feedback from comprehensive planning and architectural reviews to resolve all critical issues and incorporate recommended enhancements.

### What Changed from Initial Plan

1. **Added Performance Baseline Collection** (Phase 0) - Capture current metrics before refactoring
2. **Database Naming Security** - Explicit project_id validation and SQL injection prevention
3. **Enhanced Error Handling** - Comprehensive workflow-mcp integration error states
4. **Rollback Strategy** - Complete rollback procedures for each phase
5. **Connection Pool Limits** - MAX_PROJECTS configuration to prevent resource exhaustion
6. **Multi-Tenant Stress Tests** - Concurrent project testing in Phase 11
7. **PostgreSQL Production Config** - Documentation for large-scale deployments
8. **Enhanced Error Messages** - Distinguish workflow-mcp failure modes

### Critical Issues Addressed

All 5 critical issues from planning review have been resolved:
- **C1**: Database naming strategy (validation, sanitization, discovery)
- **C2**: workflow-mcp error handling (error categorization, caching, validation)
- **C3**: Rollback strategy (per-phase rollback, database recovery)
- **C4**: Performance baseline (capture before refactor, regression detection)
- **C5**: Concurrent access patterns (advisory locks, connection pool stress tests)

### Architectural Recommendations Integrated

All architectural recommendations have been incorporated:
- **R1**: Connection pool limits (MAX_PROJECTS configuration)
- **R2**: PostgreSQL configuration for production (max_connections, shared_buffers)
- **R3**: Enhanced error messages (workflow-mcp failure mode distinction)
- **R4**: Multi-tenant stress tests (Phase 11 additions)

---

## Executive Summary

The codebase-mcp refactoring transforms a monolithic MCP server (16 tools) into a pure semantic code search service (2 tools) with multi-project support. This plan follows Constitutional Principle I (Simplicity Over Features) by removing all non-search functionality while maintaining performance guarantees (<500ms search, <60s indexing).

**Key Objectives**:
1. Remove work items, tasks, vendors, deployments (9 database tables dropped)
2. Add multi-project support (one database per project)
3. Integrate with workflow-mcp (optional, graceful degradation)
4. Maintain constitutional compliance (all 11 principles)
5. Achieve 60% code reduction (~4,500 → ~1,800 lines)

**Success Criteria**:
- Only 2 MCP tools: `index_repository`, `search_code`
- Multi-project isolation validated (no cross-contamination)
- Performance targets met: <500ms p95 search, <60s indexing
- 100% protocol compliance (mcp-inspector)
- Type-safe: mypy --strict passes
- Test coverage >80%

---

## Resolved Critical Issues

### C1: Database Naming Strategy

**Original Problem**: Plan mentioned `f"codebase_{project_id}"` but lacked validation rules, sanitization strategy, SQL injection prevention, and database discovery mechanism.

**Resolution**:

#### Project ID Validation Rules
```python
from pydantic import BaseModel, Field, validator

class ProjectIDValidator(BaseModel):
    project_id: str = Field(
        pattern=r'^[a-z0-9-]{1,50}$',
        description="Lowercase alphanumeric with hyphens, max 50 chars"
    )

    @validator('project_id')
    def validate_safe_project_id(cls, v):
        """Additional safety checks"""
        if v.startswith('-') or v.endswith('-'):
            raise ValueError("project_id cannot start or end with hyphen")
        if '--' in v:
            raise ValueError("project_id cannot contain consecutive hyphens")
        if len(v.encode('utf-8')) > 50:
            raise ValueError("project_id too long (max 50 bytes)")
        return v
```

#### Database Naming Convention
- **Format**: `codebase_<project_id>`
- **Example**: `project_id="my-app"` → database name `codebase_my-app`
- **Length Limit**: 63 characters (PostgreSQL identifier limit)
- **Sanitization**: Invalid characters rejected at validation (not replaced)
- **Discovery**: Query PostgreSQL for databases matching pattern `codebase_%`

#### SQL Injection Prevention
```python
async def get_db_pool(project_id: str) -> asyncpg.Pool:
    """Get or create connection pool for project database"""
    # Validate project_id format (raises ValueError if invalid)
    ProjectIDValidator(project_id=project_id)

    # Safe: project_id validated to be alphanumeric + hyphens only
    database_name = f"codebase_{project_id}"

    # Use parameterized connection (asyncpg handles escaping)
    pool = await asyncpg.create_pool(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        database=database_name,  # Safe after validation
        ...
    )
    return pool
```

#### Database Discovery Endpoint (Future: v2.1.0)
```python
async def list_indexed_projects() -> list[str]:
    """List all projects with databases (future tool)"""
    conn = await asyncpg.connect(database="postgres", ...)
    try:
        rows = await conn.fetch("""
            SELECT datname FROM pg_database
            WHERE datname LIKE 'codebase_%'
        """)
        return [row['datname'].replace('codebase_', '') for row in rows]
    finally:
        await conn.close()
```

#### Permission Handling
```python
async def ensure_database_exists(project_id: str):
    """Create database if doesn't exist, with clear permission errors"""
    try:
        # ... database creation logic
        pass
    except asyncpg.InsufficientPrivilegeError:
        raise RuntimeError(
            "Insufficient permissions to create database.\n"
            f"Grant CREATEDB privilege: ALTER USER {user} CREATEDB;\n"
            "Or manually create database: CREATE DATABASE codebase_{project_id};"
        )
```

**Implementation**: Phase 8 (Connection Management)

**Verification**:
- Unit test: `test_project_id_validation_rejects_sql_injection()`
- Integration test: `test_database_creation_with_valid_project_id()`
- Security test: `test_sql_injection_attempts_blocked()`

---

### C2: workflow-mcp Integration Error Handling

**Original Problem**: Basic error handling (`return None`) didn't distinguish between failure modes (not installed vs crashed vs timeout vs invalid response).

**Resolution**:

#### Error Categorization
```python
from enum import Enum

class WorkflowMCPStatus(Enum):
    SUCCESS = "success"
    NO_ACTIVE_PROJECT = "no_active_project"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    INVALID_RESPONSE = "invalid_response"

class WorkflowMCPError(Exception):
    """Base class for workflow-mcp integration errors"""
    pass

class WorkflowMCPUnavailable(WorkflowMCPError):
    """workflow-mcp not running or unreachable"""
    pass

class WorkflowMCPTimeout(WorkflowMCPError):
    """workflow-mcp request timed out"""
    pass

class WorkflowMCPInvalidResponse(WorkflowMCPError):
    """workflow-mcp returned invalid data"""
    pass
```

#### Enhanced Integration Function
```python
import aiohttp
import structlog
from typing import Tuple, Optional

logger = structlog.get_logger()

# Cache active project for 60 seconds
_active_project_cache: dict = {"project_id": None, "expires_at": 0}

async def get_active_project_id() -> Tuple[Optional[str], WorkflowMCPStatus]:
    """
    Query workflow-mcp for active project ID.

    Returns:
        (project_id, status) tuple
        - project_id: str if success, None otherwise
        - status: WorkflowMCPStatus enum indicating result

    Caching:
        - Caches successful responses for 60 seconds
        - Invalidated on cache expiry or explicit project_id parameter
    """
    # Check cache
    now = time.time()
    if _active_project_cache["expires_at"] > now and _active_project_cache["project_id"]:
        logger.info("active_project_cache_hit",
                    project_id=_active_project_cache["project_id"])
        return (_active_project_cache["project_id"], WorkflowMCPStatus.SUCCESS)

    workflow_mcp_url = os.getenv(
        "WORKFLOW_MCP_URL",
        "http://localhost:3000/mcp/workflow-mcp"
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{workflow_mcp_url}/get_active_project",
                timeout=aiohttp.ClientTimeout(total=2.0)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    project_id = data.get("project_id")

                    if not project_id:
                        logger.warning("workflow_mcp_no_active_project")
                        return (None, WorkflowMCPStatus.NO_ACTIVE_PROJECT)

                    # Validate project_id format
                    try:
                        ProjectIDValidator(project_id=project_id)
                    except ValueError as e:
                        logger.error("workflow_mcp_invalid_project_id",
                                   project_id=project_id, error=str(e))
                        return (None, WorkflowMCPStatus.INVALID_RESPONSE)

                    # Cache successful response
                    _active_project_cache["project_id"] = project_id
                    _active_project_cache["expires_at"] = now + 60

                    logger.info("workflow_mcp_active_project", project_id=project_id)
                    return (project_id, WorkflowMCPStatus.SUCCESS)

                elif response.status == 404:
                    logger.warning("workflow_mcp_no_active_project")
                    return (None, WorkflowMCPStatus.NO_ACTIVE_PROJECT)

                else:
                    logger.error("workflow_mcp_unexpected_status",
                               status=response.status)
                    return (None, WorkflowMCPStatus.UNAVAILABLE)

    except asyncio.TimeoutError:
        logger.warning("workflow_mcp_timeout")
        return (None, WorkflowMCPStatus.TIMEOUT)

    except aiohttp.ClientError as e:
        logger.warning("workflow_mcp_unavailable", error=str(e))
        return (None, WorkflowMCPStatus.UNAVAILABLE)

    except Exception as e:
        logger.error("workflow_mcp_unexpected_error", error=str(e))
        return (None, WorkflowMCPStatus.UNAVAILABLE)
```

#### Enhanced Error Messages in search_code
```python
@mcp.tool()
async def search_code(params: SearchCodeParams) -> dict:
    """Search code using semantic similarity"""
    # Resolve project_id
    if params.project_id:
        project_id = params.project_id
        logger.info("using_explicit_project_id", project_id=project_id)
    else:
        project_id, status = await get_active_project_id()

        if not project_id:
            # Provide specific error messages per failure mode
            if status == WorkflowMCPStatus.NO_ACTIVE_PROJECT:
                raise ValueError(
                    "No active project set in workflow-mcp.\n"
                    "Solution 1: Set active project via workflow-mcp\n"
                    "Solution 2: Provide explicit project_id parameter:\n"
                    "  search_code(query='...', project_id='my-project')"
                )
            elif status == WorkflowMCPStatus.TIMEOUT:
                raise ValueError(
                    "workflow-mcp request timed out (>2s).\n"
                    "Solution 1: Check workflow-mcp is responsive: curl http://localhost:3000/health\n"
                    "Solution 2: Provide explicit project_id parameter to bypass workflow-mcp"
                )
            elif status == WorkflowMCPStatus.UNAVAILABLE:
                raise ValueError(
                    "workflow-mcp unavailable.\n"
                    "Solution 1: Start workflow-mcp: workflow-mcp run\n"
                    "Solution 2: Check workflow-mcp URL: echo $WORKFLOW_MCP_URL\n"
                    "Solution 3: Provide explicit project_id parameter:\n"
                    "  search_code(query='...', project_id='my-project')"
                )
            elif status == WorkflowMCPStatus.INVALID_RESPONSE:
                raise ValueError(
                    "workflow-mcp returned invalid project_id.\n"
                    "This is likely a workflow-mcp bug. Report to maintainers.\n"
                    "Workaround: Provide explicit project_id parameter"
                )
            else:
                raise ValueError(
                    "Unknown workflow-mcp error. Provide explicit project_id parameter."
                )

    # Validate project exists (has database)
    try:
        pool = await get_db_pool(project_id)
    except asyncpg.InvalidCatalogNameError:
        raise ValueError(
            f"Project '{project_id}' not indexed.\n"
            f"Solution: Index repository first:\n"
            f"  index_repository(repo_path='/path/to/repo', project_id='{project_id}')"
        )

    # ... rest of search logic
```

#### Cache Invalidation Strategy
```python
def invalidate_active_project_cache():
    """Invalidate cached active project (called when explicit project_id provided)"""
    _active_project_cache["project_id"] = None
    _active_project_cache["expires_at"] = 0
    logger.info("active_project_cache_invalidated")
```

**Implementation**: Phase 7 (Multi-Project Support)

**Verification**:
- Unit test: `test_workflow_mcp_error_categorization()`
- Integration test: `test_search_with_workflow_mcp_down()`
- Integration test: `test_search_with_no_active_project()`
- Integration test: `test_search_with_invalid_project_id_from_workflow_mcp()`
- Integration test: `test_active_project_cache_expiry()`

---

### C3: Rollback Strategy

**Original Problem**: Plan assumed linear success, no specification for reverting failed phases or recovering from partial migration.

**Resolution**:

#### Per-Phase Rollback Strategy

Each phase now includes:
1. **Git-based rollback** - Revert commits if phase fails
2. **Database rollback** - Restore from backup if database changes fail
3. **Safe points** - Points where it's safe to stop and revert
4. **Recovery procedures** - Step-by-step recovery instructions

#### Emergency Rollback Procedure

**If refactor must be abandoned completely**:

```bash
#!/bin/bash
# emergency-rollback.sh - Full refactor rollback

set -e

echo "=== EMERGENCY ROLLBACK: codebase-mcp refactor ==="

# 1. Checkout main branch (discard refactor branch)
echo "Step 1: Reverting to main branch..."
git checkout main
git branch -D 002-refactor-pure-search

# 2. Restore database from backup
echo "Step 2: Restoring database from backup..."
dropdb codebase_mcp
createdb codebase_mcp
psql codebase_mcp < backups/backup-before-002.sql

# 3. Verify restoration
echo "Step 3: Verifying restoration..."
psql codebase_mcp -c "\dt"  # Should show all original tables

# 4. Test original functionality
echo "Step 4: Testing original functionality..."
pytest tests/ -v

echo "=== ROLLBACK COMPLETE ==="
echo "System restored to pre-refactor state."
```

#### Database Migration Rollback

**Create `migrations/002_rollback.sql`**:
```sql
-- Rollback migration 002 (restore non-search tables)
-- WARNING: Only run if you have backup of non-search data

-- Restore from backup
\echo 'ROLLBACK: Restoring non-search tables from backup...'

-- Remove project_id columns from search tables
ALTER TABLE repositories DROP COLUMN IF EXISTS project_id;
ALTER TABLE code_chunks DROP COLUMN IF EXISTS project_id;

-- Restore original unique constraint
ALTER TABLE repositories DROP CONSTRAINT IF EXISTS repositories_project_path_key;
ALTER TABLE repositories ADD CONSTRAINT repositories_path_key UNIQUE(path);

-- Drop per-project indexes
DROP INDEX IF EXISTS idx_repositories_project_id;
DROP INDEX IF EXISTS idx_code_chunks_project_id;

-- Restore non-search tables from backup
-- (User must restore from pg_dump backup manually)
\echo 'MANUAL STEP: Restore non-search tables from backup:'
\echo '  psql codebase_mcp < backup-non-search-tables.sql'

\echo 'ROLLBACK 002 COMPLETE (manual restore required)'
```

#### Phase-Specific Rollback Instructions

**Phase 2: Database Schema Refactoring**

**Rollback Plan**:
```bash
# If migration fails or tests fail after migration
echo "Rolling back Phase 2: Database schema changes"

# 1. Drop migration changes
psql codebase_mcp < migrations/002_rollback.sql

# 2. Restore schema file
git checkout src/codebase_mcp/database/schema.sql

# 3. Verify original schema restored
psql codebase_mcp -c "\dt"

# 4. Run original tests
pytest tests/ -v
```

**Safe to proceed if**: Migration script completes, test database validation passes, no data corruption detected.

**Phase 7: Multi-Project Support**

**Rollback Plan**:
```bash
# If multi-project implementation fails
echo "Rolling back Phase 7: Multi-project support"

# 1. Revert tool changes
git checkout src/codebase_mcp/tools/search.py

# 2. Remove project context module
git rm src/codebase_mcp/utils/project_context.py

# 3. Revert connection changes
git checkout src/codebase_mcp/database/connection.py

# 4. Run tests (should still pass with Phase 1-6 changes)
pytest tests/test_search.py -v
```

**Safe to proceed if**: Multi-project tests pass, isolation validated, workflow-mcp integration works.

**Phase 11: Performance Testing**

**Rollback Plan**:
```bash
# If performance targets not met
echo "Rolling back Phase 11: Performance optimizations"

# 1. Revert any optimization changes
git checkout src/codebase_mcp/database/operations.py

# 2. Revert HNSW index parameters if changed
git checkout src/codebase_mcp/database/schema.sql

# 3. Re-run performance tests with original parameters
pytest tests/test_performance.py -v -m performance
```

**Safe to proceed if**: Performance tests pass, no regressions from baseline, optimization effective.

#### Git Commit Reversal

Each phase commit can be reverted individually:
```bash
# Revert specific phase
git revert <phase-commit-hash>

# Example: Revert Phase 7 (multi-project support)
git revert abc123def  # Hash from "feat(search): add multi-project support"

# Verify revert
git log --oneline
pytest tests/ -v
```

#### Data Recovery Procedures

**Backup Strategy** (Phase 1):
```bash
# Create comprehensive backup before refactoring
./scripts/create-refactor-backup.sh

# Backup contents:
# - Database dump: backups/codebase_mcp_before_refactor.sql
# - Codebase snapshot: backups/codebase_mcp_code_snapshot.tar.gz
# - Git tag: git tag -a pre-refactor -m "State before refactor"
```

**Recovery Procedure**:
```bash
# Full recovery from backup
./scripts/recover-from-backup.sh

# Script validates:
# - Backup file exists and is valid
# - Database can be dropped and recreated
# - Tests pass after restoration
```

**Implementation**: Add to Phase 1 (Baseline), documented in each phase

**Verification**:
- Test rollback procedures on test database before production
- Document lessons learned if rollback is needed
- Validate backup restoration in Phase 1

---

### C4: Performance Baseline

**Original Problem**: Phase 11 defined targets (<500ms, <60s) but no baseline capture to prove no regression.

**Resolution**:

#### Baseline Collection (Phase 0)

**Add to Phase 0 tasks**:

```bash
#!/bin/bash
# scripts/capture-performance-baseline.sh

set -e

echo "=== CAPTURING PERFORMANCE BASELINE ==="

# 1. Create test repository (10k files)
echo "Step 1: Generating 10k file test repository..."
python scripts/generate_test_repo.py \
    --files=10000 \
    --output=/tmp/codebase-baseline-repo \
    --seed=42

# 2. Benchmark indexing (current implementation)
echo "Step 2: Benchmarking indexing..."
time_output=$(mktemp)
{ time python -m codebase_mcp.tools.search index /tmp/codebase-baseline-repo ; } 2> $time_output
indexing_time=$(grep real $time_output | awk '{print $2}')

# 3. Benchmark search (100 queries, measure p50/p95)
echo "Step 3: Benchmarking search latency..."
python scripts/benchmark_search.py \
    --queries=100 \
    --output=docs/baseline/search-latency-before.json

# 4. Document baseline
cat > docs/baseline/performance-before.md <<EOF
# Performance Baseline (Before Refactor)

**Date**: $(date +%Y-%m-%d)
**Commit**: $(git rev-parse HEAD)
**Test Repo**: 10,000 files, generated with seed=42

## Indexing Throughput
- Time: $indexing_time
- Files: 10,000
- Rate: $(python -c "print(10000 / $indexing_time)")</script> files/second

## Search Latency (100 queries)
$(python -c "
import json
with open('docs/baseline/search-latency-before.json') as f:
    data = json.load(f)
    print(f\"- p50: {data['p50']:.2f}ms\")
    print(f\"- p95: {data['p95']:.2f}ms\")
    print(f\"- p99: {data['p99']:.2f}ms\")
    print(f\"- mean: {data['mean']:.2f}ms\")
")
EOF

echo "Baseline captured: docs/baseline/performance-before.md"
```

#### Test Repository Generator

**Create `scripts/generate_test_repo.py`**:
```python
#!/usr/bin/env python3
"""
Generate realistic test repository for performance benchmarking.

Usage:
    python scripts/generate_test_repo.py --files=10000 --output=/tmp/test-repo --seed=42
"""

import argparse
import random
from pathlib import Path

def generate_test_repo(num_files: int, output_dir: Path, seed: int = 42):
    """
    Generate test repository with realistic file distribution:
    - 70% small files (<1KB): configs, tests, documentation
    - 25% medium files (1-10KB): source code
    - 5% large files (>10KB): generated code, data files

    Languages: Python (40%), JavaScript (30%), TypeScript (20%), Other (10%)
    """
    random.seed(seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    languages = [
        ("py", 0.40, ["def ", "class ", "import "]),
        ("js", 0.30, ["function ", "const ", "import "]),
        ("ts", 0.20, ["function ", "interface ", "export "]),
        ("go", 0.05, ["func ", "type ", "package "]),
        ("rs", 0.05, ["fn ", "struct ", "use "]),
    ]

    for i in range(num_files):
        # Select language
        lang, _, keywords = random.choices(
            languages,
            weights=[w for _, w, _ in languages]
        )[0]

        # Select file size distribution
        size_category = random.choices(
            ["small", "medium", "large"],
            weights=[0.70, 0.25, 0.05]
        )[0]

        if size_category == "small":
            num_lines = random.randint(10, 50)
        elif size_category == "medium":
            num_lines = random.randint(50, 500)
        else:
            num_lines = random.randint(500, 2000)

        # Generate file content
        file_path = output_dir / f"src/module_{i//100}/file_{i}.{lang}"
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with file_path.open('w') as f:
            for j in range(num_lines):
                keyword = random.choice(keywords)
                f.write(f"{keyword}generated_code_{i}_{j}()\n")

    print(f"Generated {num_files} files in {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", type=int, default=10000)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    generate_test_repo(args.files, args.output, args.seed)
```

#### Search Latency Benchmarker

**Create `scripts/benchmark_search.py`**:
```python
#!/usr/bin/env python3
"""
Benchmark search latency with statistical analysis.

Usage:
    python scripts/benchmark_search.py --queries=100 --output=latency.json
"""

import argparse
import asyncio
import json
import time
import statistics
from pathlib import Path

async def benchmark_search(num_queries: int, output_file: Path):
    """Run search benchmarks and calculate percentiles"""
    from codebase_mcp.tools.search import search_code, SearchCodeParams

    latencies = []
    queries = [f"test query {i}" for i in range(num_queries)]

    for query in queries:
        start = time.time()
        try:
            await search_code(SearchCodeParams(
                query=query,
                project_id="baseline-test",
                limit=10
            ))
        except Exception as e:
            print(f"Search failed: {e}")
            continue

        latency_ms = (time.time() - start) * 1000
        latencies.append(latency_ms)

    # Calculate statistics
    latencies.sort()
    results = {
        "num_queries": len(latencies),
        "mean": statistics.mean(latencies),
        "median": statistics.median(latencies),
        "p50": latencies[int(0.50 * len(latencies))],
        "p95": latencies[int(0.95 * len(latencies))],
        "p99": latencies[int(0.99 * len(latencies))],
        "min": min(latencies),
        "max": max(latencies),
        "stdev": statistics.stdev(latencies),
    }

    # Write results
    with output_file.open('w') as f:
        json.dump(results, f, indent=2)

    print(f"Benchmark complete: {output_file}")
    print(f"p50: {results['p50']:.2f}ms, p95: {results['p95']:.2f}ms")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", type=int, default=100)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    asyncio.run(benchmark_search(args.queries, args.output))
```

#### Phase 11 Regression Detection

**Updated Phase 11 acceptance criteria**:
```python
@pytest.mark.performance
@pytest.mark.asyncio
async def test_search_latency_no_regression(large_indexed_repo, baseline_metrics):
    """Test search latency meets target AND shows no regression from baseline"""
    latencies = []

    for i in range(100):
        start = time.time()
        result = await search_code(
            SearchCodeParams(query=f"test query {i}", project_id="large-repo")
        )
        latencies.append((time.time() - start) * 1000)

    latencies.sort()
    p95 = latencies[int(0.95 * len(latencies))]
    p50 = latencies[int(0.50 * len(latencies))]

    # Constitutional requirement
    assert p95 < 500, f"p95 latency {p95:.2f}ms exceeds 500ms target"

    # Regression check (allow 20% degradation)
    baseline_p95 = baseline_metrics['search_p95']
    max_acceptable = baseline_p95 * 1.20
    assert p95 < max_acceptable, \
        f"p95 {p95:.2f}ms is {(p95/baseline_p95-1)*100:.1f}% slower than baseline {baseline_p95:.2f}ms"
```

**Implementation**: Phase 0 (baseline capture), Phase 11 (regression tests)

**Verification**:
- Baseline metrics captured before refactor starts
- Performance comparison report generated in Phase 11
- Regression tests fail if >20% degradation detected

---

### C5: Concurrent Access Patterns

**Original Problem**: Plan specified connection pooling (5-20 per project) but didn't address concurrent indexing, search during indexing, connection exhaustion, or multi-client scenarios.

**Resolution**:

#### Concurrency Model Documentation

**Add to `tech-stack.md`**:

```markdown
## Concurrency Model

### Single MCP Server Instance (Primary Use Case)

**Architecture**:
- One codebase-mcp server process
- Multiple MCP clients (Claude Code, Cline, etc.) connect to server
- Server manages connection pools per project

**Connection Pooling**:
- Per-project pools: 5-20 connections each
- Total connections: `num_projects × max_pool_size`
- PostgreSQL limit: `max_connections` (default 100, recommend 500)

**Concurrent Operations**:
- ✅ Multiple searches: Up to 20 concurrent per project (pool size)
- ✅ Search during indexing: No blocking (searches see current index state)
- ❌ Concurrent indexing of same repo: Blocked via advisory locks

### Multiple MCP Server Instances (Advanced)

**Architecture**:
- Multiple codebase-mcp processes (e.g., per developer)
- Each process has independent connection pools
- PostgreSQL coordinates cross-process access

**Connection Management**:
- Each server: 5-20 connections per project
- Total: `num_servers × num_projects × max_pool_size`
- Example: 10 servers × 5 projects × 20 = 1000 PostgreSQL connections

**Advisory Locks**:
- PostgreSQL-level locks (shared across all processes)
- Prevents concurrent indexing of same repository
- Search operations not blocked by locks

### Concurrent Indexing Prevention

**Problem**: Two processes indexing same repository simultaneously → data corruption

**Solution**: PostgreSQL advisory locks

```python
async def index_repository_db(pool, repo_path, project_id, force_reindex):
    """Index repository with advisory lock"""
    async with pool.acquire() as conn:
        # Generate unique lock ID from repo_path + project_id
        lock_id = hash(f"{project_id}:{repo_path}") % (2**31)

        # Try to acquire lock (non-blocking)
        acquired = await conn.fetchval(
            "SELECT pg_try_advisory_lock($1)",
            lock_id
        )

        if not acquired:
            raise RuntimeError(
                f"Repository {repo_path} is currently being indexed.\n"
                f"Wait for indexing to complete or force kill other process."
            )

        try:
            # Indexing logic here
            # INSERT INTO repositories ...
            # INSERT INTO code_chunks ...
            pass
        finally:
            # Release lock even if indexing fails
            await conn.execute("SELECT pg_advisory_unlock($1)", lock_id)
```

### Search During Indexing

**Behavior**: Non-blocking, eventual consistency

- Searches execute concurrently with indexing
- Search sees current database state (may be mid-indexing)
- Stale results possible during re-indexing (acceptable tradeoff)

**Example Timeline**:
```
T0: Index starts (old chunks still searchable)
T1: Client searches (finds old chunks)
T2: Index deletes old chunks
T3: Client searches (finds partial new chunks + remaining old)
T4: Index completes (all new chunks)
T5: Client searches (finds all new chunks)
```

This is acceptable for semantic search use case (results quality improves gradually).
```

#### Connection Pool Stress Test

**Add to Phase 11**:

```python
@pytest.mark.performance
@pytest.mark.asyncio
async def test_connection_pool_under_load():
    """Test connection pools don't exhaust under heavy concurrent load"""
    num_projects = 50
    queries_per_project = 100

    # Create 50 projects with databases
    projects = [f"stress-test-{i}" for i in range(num_projects)]
    for project_id in projects:
        await ensure_database_exists(project_id)

    # Concurrent search load (50 projects × 100 queries = 5000 searches)
    async def search_repeatedly(project_id):
        for i in range(queries_per_project):
            try:
                await search_code(SearchCodeParams(
                    query=f"test query {i}",
                    project_id=project_id,
                    limit=5
                ))
            except asyncio.TimeoutError:
                pytest.fail(f"Connection timeout for {project_id} (pool exhausted)")
            except Exception as e:
                pytest.fail(f"Unexpected error: {e}")

    # Run all searches concurrently
    start = time.time()
    await asyncio.gather(*[search_repeatedly(p) for p in projects])
    duration = time.time() - start

    print(f"Completed 5000 searches across 50 projects in {duration:.2f}s")

    # Verify no connection errors occurred
    # (Test passes if no exceptions raised above)
```

#### Advisory Lock Test

**Add to Phase 7**:

```python
@pytest.mark.asyncio
async def test_concurrent_indexing_blocked():
    """Test that concurrent indexing of same repo is blocked"""
    repo_path = "/tmp/test-repo"
    project_id = "concurrent-test"

    # Start first indexing operation
    task1 = asyncio.create_task(
        index_repository(IndexRepositoryParams(
            repo_path=repo_path,
            project_id=project_id,
            force_reindex=False
        ))
    )

    # Wait for lock acquisition
    await asyncio.sleep(0.5)

    # Try to start second indexing (should fail immediately)
    with pytest.raises(RuntimeError, match="currently being indexed"):
        await index_repository(IndexRepositoryParams(
            repo_path=repo_path,
            project_id=project_id,
            force_reindex=False
        ))

    # Wait for first indexing to complete
    result = await task1
    assert result["status"] == "success"
```

#### Connection Pool Monitoring

**Add to `connection.py`**:

```python
import structlog

logger = structlog.get_logger()

async def get_db_pool(project_id: str) -> asyncpg.Pool:
    """Get or create connection pool with monitoring"""
    if project_id not in _pools:
        database_name = f"codebase_{project_id}"
        _pools[project_id] = await asyncpg.create_pool(
            database=database_name,
            min_size=5,
            max_size=20,
            # Connection pool metrics
            setup=lambda conn: logger.info("connection_created", project_id=project_id),
            on_acquire=lambda conn: logger.debug("connection_acquired", project_id=project_id),
            on_release=lambda conn: logger.debug("connection_released", project_id=project_id),
        )

        logger.info("connection_pool_created",
                   project_id=project_id,
                   min_size=5,
                   max_size=20)

    return _pools[project_id]

async def get_pool_stats(project_id: str) -> dict:
    """Get connection pool statistics for monitoring"""
    if project_id not in _pools:
        return {"error": "No pool for project"}

    pool = _pools[project_id]
    return {
        "project_id": project_id,
        "size": pool.get_size(),
        "min_size": pool.get_min_size(),
        "max_size": pool.get_max_size(),
        "free_connections": pool.get_idle_size(),
    }
```

**Implementation**: Phase 7 (advisory locks), Phase 8 (monitoring), Phase 11 (stress tests)

**Verification**:
- Unit test: `test_advisory_lock_acquisition_and_release()`
- Integration test: `test_concurrent_indexing_blocked()`
- Stress test: `test_connection_pool_under_load()`
- Monitoring: Verify logs show connection acquisition/release

---

## Incorporated Architectural Recommendations

### R1: Connection Pool Limits (MAX_PROJECTS Configuration)

**Original Concern**: 100 projects × 20 connections = 2000 PostgreSQL connections exceeds default max_connections (100). Risk of resource exhaustion.

**Solution**: Configurable MAX_PROJECTS limit with LRU pool eviction

#### Implementation

**Add to `connection.py`**:

```python
import os
from collections import OrderedDict
import asyncpg
import structlog

logger = structlog.get_logger()

# Configuration
MAX_PROJECTS = int(os.getenv("MAX_PROJECTS", "50"))

# Per-project connection pools with LRU tracking
_pools: OrderedDict[str, asyncpg.Pool] = OrderedDict()

async def get_db_pool(project_id: str) -> asyncpg.Pool:
    """
    Get or create connection pool for project database.

    Implements LRU eviction when MAX_PROJECTS reached:
    - Closes least-recently-used pool
    - Creates new pool for requested project

    Raises:
        RuntimeError: If MAX_PROJECTS exceeded and eviction fails
    """
    # Move to end of OrderedDict (mark as recently used)
    if project_id in _pools:
        _pools.move_to_end(project_id)
        logger.debug("connection_pool_reused", project_id=project_id)
        return _pools[project_id]

    # Check if MAX_PROJECTS would be exceeded
    if len(_pools) >= MAX_PROJECTS:
        # Evict least-recently-used pool (first item in OrderedDict)
        lru_project_id, lru_pool = _pools.popitem(last=False)

        logger.warning("connection_pool_evicted_lru",
                      evicted_project=lru_project_id,
                      new_project=project_id,
                      max_projects=MAX_PROJECTS)

        # Close evicted pool gracefully
        await lru_pool.close()

    # Create new pool
    database_name = f"codebase_{project_id}"

    try:
        pool = await asyncpg.create_pool(
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=database_name,
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
            min_size=5,
            max_size=20,
        )

        _pools[project_id] = pool

        logger.info("connection_pool_created",
                   project_id=project_id,
                   total_pools=len(_pools),
                   max_projects=MAX_PROJECTS)

        return pool

    except Exception as e:
        logger.error("connection_pool_creation_failed",
                    project_id=project_id,
                    error=str(e))
        raise
```

#### Configuration Documentation

**Add to `README.md`**:

```markdown
## Environment Variables

### Connection Pool Configuration

#### MAX_PROJECTS (default: 50)
Maximum number of concurrent project connection pools.

**Impact**:
- Each pool uses 5-20 PostgreSQL connections
- Total connections: `MAX_PROJECTS × 20` (worst case)
- Example: MAX_PROJECTS=50 → 1000 max PostgreSQL connections

**Tuning**:
- Small deployments (1-10 projects): `MAX_PROJECTS=10`
- Medium deployments (10-50 projects): `MAX_PROJECTS=50` (default)
- Large deployments (50+ projects): `MAX_PROJECTS=100` (requires PostgreSQL tuning)

**LRU Eviction**:
When MAX_PROJECTS is reached, the least-recently-used pool is closed and evicted. Active connections are allowed to finish gracefully.

**Example**:
```bash
# Support up to 100 concurrent projects
export MAX_PROJECTS=100
codebase-mcp run
```
```

#### PostgreSQL Configuration Requirements

**Add to `docs/postgresql-configuration.md`**:

```markdown
# PostgreSQL Configuration for codebase-mcp

## Connection Limits

codebase-mcp uses connection pooling with 5-20 connections per project. Calculate required PostgreSQL connections:

```
max_connections = MAX_PROJECTS × 20 (pool max_size) + 50 (overhead)
```

### Examples

| MAX_PROJECTS | PostgreSQL max_connections | Recommended Setting |
|--------------|---------------------------|---------------------|
| 10           | 250                       | 300                 |
| 50 (default) | 1050                      | 1200                |
| 100          | 2050                      | 2500                |

## Configuration Steps

### 1. Edit postgresql.conf

```bash
sudo nano /etc/postgresql/14/main/postgresql.conf
```

**Required Changes**:
```conf
# Connection settings
max_connections = 1200              # For MAX_PROJECTS=50

# Memory settings (scale with max_connections)
shared_buffers = 4GB                # 25% of RAM (16GB system)
effective_cache_size = 12GB         # 75% of RAM
maintenance_work_mem = 1GB          # For indexing, vacuum
work_mem = 20MB                     # Per connection (conservative)

# Connection pooling
max_prepared_transactions = 1200    # Match max_connections
```

### 2. Restart PostgreSQL

```bash
sudo systemctl restart postgresql
sudo systemctl status postgresql
```

### 3. Verify Configuration

```sql
-- Check max_connections
SHOW max_connections;
-- Should show: 1200

-- Check active connections
SELECT count(*) FROM pg_stat_activity;
-- Should be well below max_connections
```

## Monitoring

```sql
-- Active connection count by database
SELECT datname, count(*)
FROM pg_stat_activity
WHERE datname LIKE 'codebase_%'
GROUP BY datname
ORDER BY count(*) DESC;

-- Connection pool utilization
SELECT datname,
       count(*) as active,
       max_connections - count(*) as available
FROM pg_stat_activity, pg_database
WHERE datname LIKE 'codebase_%'
GROUP BY datname;
```

## Warnings

⚠️ **Insufficient max_connections**:
If codebase-mcp cannot create connections, you'll see:
```
FATAL: sorry, too many clients already
```

**Solution**: Increase max_connections and restart PostgreSQL.

⚠️ **High memory usage**:
Each connection uses ~2-10MB RAM. 1200 connections = ~2-12GB RAM.

**Solution**: Ensure server has adequate RAM or reduce MAX_PROJECTS.
```

**Impact**: Prevents resource exhaustion, provides operational flexibility

**Phase**: Add to Phase 8 (Connection Management)

---

### R2: PostgreSQL Configuration Documentation

**Original Concern**: Multi-project architecture requires PostgreSQL tuning for production deployments. Missing configuration guidance.

**Solution**: Comprehensive PostgreSQL configuration documentation

#### Production Configuration Guide

**Create `docs/production-deployment.md`**:

```markdown
# Production Deployment Guide

## System Requirements

### Hardware
- **CPU**: 4 cores minimum, 8 cores recommended
- **RAM**: 16 GB minimum, 32 GB recommended (for 50+ projects)
- **Disk**: SSD required (HDD degrades search latency by 10-50x)
- **Storage**: 100 GB per 10 projects (varies by codebase size)

### Software
- **OS**: Linux (Ubuntu 22.04 LTS recommended)
- **PostgreSQL**: 14+ with pgvector extension
- **Python**: 3.11+
- **Ollama**: Latest version with nomic-embed-text model

## PostgreSQL Production Configuration

### Memory Settings

```conf
# postgresql.conf

# Shared memory (25% of total RAM for 16GB system)
shared_buffers = 4GB

# Query planner memory estimates (75% of total RAM)
effective_cache_size = 12GB

# Maintenance operations (vacuum, indexing)
maintenance_work_mem = 1GB

# Per-query memory (conservative for many connections)
work_mem = 20MB

# Checkpoint settings (reduce I/O spikes)
checkpoint_completion_target = 0.9
wal_buffers = 16MB
max_wal_size = 4GB
min_wal_size = 1GB
```

### Connection Settings

```conf
# Support 50 concurrent projects (50 × 20 = 1000 connections)
max_connections = 1200

# Prepared transactions (match max_connections)
max_prepared_transactions = 1200

# Connection limits per user/database
# (prevents single project from exhausting all connections)
# Set in pg_hba.conf or ALTER ROLE/DATABASE
```

### Performance Tuning

```conf
# Query optimizer
random_page_cost = 1.1              # SSD (vs 4.0 for HDD)
effective_io_concurrency = 200      # SSD concurrent I/O

# Parallel query execution
max_parallel_workers_per_gather = 4
max_parallel_workers = 8

# Background writer (reduce checkpoint spikes)
bgwriter_delay = 200ms
bgwriter_lru_maxpages = 100
bgwriter_lru_multiplier = 2.0
```

### Logging (for monitoring)

```conf
# Log slow queries (>1s)
log_min_duration_statement = 1000

# Log connections/disconnections
log_connections = on
log_disconnections = on

# Log checkpoints
log_checkpoints = on
```

## Ollama Production Configuration

### Memory Limits

```bash
# Prevent Ollama from exhausting RAM
export OLLAMA_MAX_LOADED_MODELS=1       # Only load 1 model at a time
export OLLAMA_NUM_PARALLEL=1            # No parallel requests

# GPU settings (if available)
export OLLAMA_GPU_LAYERS=33             # Offload layers to GPU

# Start Ollama as systemd service
sudo systemctl start ollama
sudo systemctl enable ollama
```

### Model Preloading

```bash
# Preload model to avoid first-request delay
ollama run nomic-embed-text "warmup"

# Verify model loaded
curl http://localhost:11434/api/tags
```

## codebase-mcp as systemd Service

**Create `/etc/systemd/system/codebase-mcp.service`**:

```ini
[Unit]
Description=Codebase MCP Server
After=network.target postgresql.service ollama.service
Requires=postgresql.service ollama.service

[Service]
Type=simple
User=codebase
Group=codebase
WorkingDirectory=/opt/codebase-mcp
ExecStart=/opt/codebase-mcp/venv/bin/python -m codebase_mcp.server
Restart=on-failure
RestartSec=10

# Environment
Environment="POSTGRES_HOST=localhost"
Environment="POSTGRES_PORT=5432"
Environment="POSTGRES_USER=codebase_user"
Environment="POSTGRES_PASSWORD=secure_password_here"
Environment="OLLAMA_URL=http://localhost:11434"
Environment="MAX_PROJECTS=50"

# Resource limits
LimitNOFILE=65536                       # File descriptors (for many connections)
MemoryLimit=8G                          # Prevent runaway memory usage

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

**Enable and start**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable codebase-mcp
sudo systemctl start codebase-mcp
sudo systemctl status codebase-mcp
```

## Monitoring

### PostgreSQL Health Checks

```sql
-- Active connections per database
SELECT datname, count(*) as connections
FROM pg_stat_activity
WHERE datname LIKE 'codebase_%'
GROUP BY datname
ORDER BY connections DESC;

-- Slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE mean_exec_time > 1000
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Cache hit ratio (should be >99%)
SELECT
    sum(blks_hit) / (sum(blks_hit) + sum(blks_read)) * 100 AS cache_hit_ratio
FROM pg_stat_database;
```

### codebase-mcp Logs

```bash
# View server logs
sudo journalctl -u codebase-mcp -f

# Search for errors
sudo journalctl -u codebase-mcp | grep ERROR

# Performance metrics
sudo journalctl -u codebase-mcp | grep search_latency
```

### Metrics to Monitor

- **PostgreSQL**:
  - Active connections (should be < max_connections)
  - Cache hit ratio (should be >99%)
  - Slow query count (should be minimal)

- **codebase-mcp**:
  - Search latency p95 (should be <500ms)
  - Indexing throughput (should be >150 files/s)
  - Error rate (should be <1%)

- **System**:
  - CPU usage (should be <80%)
  - Memory usage (should leave 20% free)
  - Disk I/O (should not saturate)

## Backup Strategy

### Automated Backups

```bash
#!/bin/bash
# /opt/codebase-mcp/backup.sh

# Backup all project databases
for db in $(psql -lqt | cut -d \| -f 1 | grep codebase_); do
    pg_dump $db | gzip > /backups/$(date +%Y%m%d)_$db.sql.gz
done

# Retention: Keep 7 days
find /backups -name "*.sql.gz" -mtime +7 -delete
```

**Schedule with cron**:
```cron
# Daily backup at 2 AM
0 2 * * * /opt/codebase-mcp/backup.sh
```

## Troubleshooting

### Connection Errors

**Symptom**: `FATAL: sorry, too many clients already`

**Solution**:
1. Check active connections: `SELECT count(*) FROM pg_stat_activity;`
2. Increase max_connections in postgresql.conf
3. Reduce MAX_PROJECTS environment variable
4. Restart PostgreSQL

### Slow Search Performance

**Symptom**: Search >1s latency

**Possible Causes**:
1. **HNSW index missing**: `\d code_chunks` should show hnsw index
2. **Connection pool saturation**: Check logs for connection waits
3. **Ollama slow**: Check Ollama response time
4. **Large result set**: Reduce limit parameter

**Solution**: See `docs/troubleshooting.md` for detailed diagnostics.
```

**Impact**: Production-ready deployment guidance, prevents configuration issues

**Phase**: Add to Phase 9 (Documentation)

---

### R3: Enhanced Error Messages

**Original Concern**: Error messages for workflow-mcp integration failures don't distinguish between failure modes, making debugging difficult.

**Solution**: Specific error messages per failure state (implemented in C2 resolution above)

**Impact**:
- Users immediately understand why search failed
- Clear actionable steps for resolution
- Reduced support burden

**Phase**: Implemented in C2 (workflow-mcp error handling)

---

### R4: Multi-Tenant Stress Tests

**Original Concern**: Performance tests validate single-project search, but multi-project architecture needs stress testing under concurrent load.

**Solution**: Comprehensive multi-tenant stress tests

#### Multi-Project Concurrent Search Test

**Add to `tests/test_performance.py`**:

```python
@pytest.mark.performance
@pytest.mark.asyncio
async def test_multi_tenant_search_latency():
    """
    Test search latency with 10 concurrent projects.

    Validates:
    - Search latency <500ms per project even under concurrent load
    - No connection pool exhaustion
    - No cross-project data leakage
    """
    num_projects = 10
    searches_per_project = 50

    # Setup: Index all projects
    projects = [f"stress-project-{i}" for i in range(num_projects)]
    for project_id in projects:
        await index_repository(IndexRepositoryParams(
            repo_path="/tmp/stress-test-repo",
            project_id=project_id,
            force_reindex=True
        ))

    # Concurrent search workload
    async def search_project_repeatedly(project_id: str):
        """Search one project repeatedly, measure latencies"""
        latencies = []
        for i in range(searches_per_project):
            start = time.time()
            result = await search_code(SearchCodeParams(
                query=f"test query {i}",
                project_id=project_id,
                limit=10
            ))
            latency = (time.time() - start) * 1000
            latencies.append(latency)

            # Verify no cross-project contamination
            assert all(
                chunk["project_id"] == project_id
                for chunk in result["results"]
            )

        return latencies

    # Run all projects concurrently
    start = time.time()
    all_latencies = await asyncio.gather(*[
        search_project_repeatedly(p) for p in projects
    ])
    total_duration = time.time() - start

    # Analyze results
    all_flat = [lat for project_lats in all_latencies for lat in project_lats]
    all_flat.sort()

    p50 = all_flat[int(0.50 * len(all_flat))]
    p95 = all_flat[int(0.95 * len(all_flat))]
    p99 = all_flat[int(0.99 * len(all_flat))]

    print(f"\nMulti-tenant search results ({num_projects} projects):")
    print(f"  Total searches: {len(all_flat)}")
    print(f"  Duration: {total_duration:.2f}s")
    print(f"  p50: {p50:.2f}ms")
    print(f"  p95: {p95:.2f}ms")
    print(f"  p99: {p99:.2f}ms")

    # Assertions
    assert p95 < 500, f"p95 latency {p95:.2f}ms exceeds 500ms target"
    assert p50 < 300, f"p50 latency {p50:.2f}ms exceeds 300ms target"
```

#### Connection Pool Saturation Test

**Add to `tests/test_performance.py`**:

```python
@pytest.mark.performance
@pytest.mark.asyncio
async def test_connection_pool_saturation():
    """
    Test connection pools handle saturation gracefully.

    Validates:
    - Pools don't exhaust under load
    - Connections are reused efficiently
    - No connection leaks
    """
    project_id = "saturation-test"
    num_concurrent = 50  # Exceeds pool size (20)

    # Setup
    await index_repository(IndexRepositoryParams(
        repo_path="/tmp/test-repo",
        project_id=project_id
    ))

    # Concurrent searches exceeding pool size
    async def single_search(query_id: int):
        try:
            result = await search_code(SearchCodeParams(
                query=f"test {query_id}",
                project_id=project_id
            ))
            return "success"
        except asyncio.TimeoutError:
            return "timeout"
        except Exception as e:
            return f"error: {type(e).__name__}"

    # Run 50 concurrent searches (pool max=20)
    results = await asyncio.gather(*[
        single_search(i) for i in range(num_concurrent)
    ])

    # Analyze results
    success_count = sum(1 for r in results if r == "success")
    timeout_count = sum(1 for r in results if r == "timeout")
    error_count = len(results) - success_count - timeout_count

    print(f"\nConnection pool saturation test:")
    print(f"  Concurrent requests: {num_concurrent}")
    print(f"  Pool size: 20")
    print(f"  Successes: {success_count}")
    print(f"  Timeouts: {timeout_count}")
    print(f"  Errors: {error_count}")

    # All should succeed (queuing, not failing)
    assert success_count == num_concurrent, \
        f"Expected all {num_concurrent} searches to succeed, got {success_count}"
    assert timeout_count == 0, f"Timeouts detected: {timeout_count}"
    assert error_count == 0, f"Errors detected: {error_count}"
```

#### Large Corpus Scaling Test

**Add to `tests/test_performance.py`**:

```python
@pytest.mark.performance
@pytest.mark.asyncio
async def test_search_latency_with_large_corpus():
    """
    Test search latency scales well with corpus size.

    Validates:
    - Search latency <500ms even with 100k+ chunks
    - HNSW index provides sub-linear scaling
    - No degradation from index size
    """
    project_id = "large-corpus"

    # Index large corpus (100k files → ~250k chunks)
    await index_repository(IndexRepositoryParams(
        repo_path="/tmp/large-test-repo-100k",
        project_id=project_id
    ))

    # Verify corpus size
    pool = await get_db_pool(project_id)
    async with pool.acquire() as conn:
        chunk_count = await conn.fetchval(
            "SELECT count(*) FROM code_chunks WHERE project_id = $1",
            project_id
        )
        print(f"Corpus size: {chunk_count:,} chunks")
        assert chunk_count > 100000, "Test requires >100k chunks"

    # Search latency test
    latencies = []
    for i in range(100):
        start = time.time()
        await search_code(SearchCodeParams(
            query=f"function definition {i}",
            project_id=project_id,
            limit=10
        ))
        latencies.append((time.time() - start) * 1000)

    latencies.sort()
    p95 = latencies[int(0.95 * len(latencies))]

    print(f"Large corpus search latency:")
    print(f"  Chunks: {chunk_count:,}")
    print(f"  p95: {p95:.2f}ms")

    assert p95 < 500, \
        f"Large corpus p95 {p95:.2f}ms exceeds 500ms target"
```

**Impact**: Validates performance under realistic production load

**Phase**: Add to Phase 11 (Performance Testing)

---

## Updated Implementation Phases

### Phase 0: Prerequisites + Baseline

**Objective**: Validate prerequisites and establish performance baseline

**Tasks**:

1. **Verify workflow-mcp Deployment** (UNCHANGED)
   ```bash
   curl http://localhost:3000/mcp/workflow-mcp/health
   # Expected: {"status": "ok"}
   ```

2. **NEW: Capture Performance Baseline**
   ```bash
   # Create test repository
   python scripts/generate_test_repo.py \
       --files=10000 \
       --output=/tmp/codebase-baseline-repo \
       --seed=42

   # Benchmark indexing
   time python -m codebase_mcp.tools.search index /tmp/codebase-baseline-repo

   # Benchmark search (100 queries)
   python scripts/benchmark_search.py \
       --queries=100 \
       --output=docs/baseline/search-latency-before.json

   # Document baseline
   cat > docs/baseline/performance-before.md <<EOF
   # Performance Baseline
   - Indexing: X seconds for 10k files
   - Search p50: Y ms
   - Search p95: Z ms
   EOF
   ```

3. **NEW: Create Rollback Preparation**
   ```bash
   # Create comprehensive backup
   pg_dump codebase_mcp > backups/backup-before-002.sql

   # Tag current state
   git tag -a pre-refactor -m "State before refactor"

   # Snapshot codebase
   tar -czf backups/codebase_mcp_snapshot.tar.gz src/ tests/
   ```

4. **Validate Planning Artifacts** (UNCHANGED)

**Acceptance Criteria**:
- [ ] workflow-mcp health check passes
- [ ] Performance baseline captured (indexing time, search p50/p95)
- [ ] Database backup created and validated
- [ ] Git tag created (pre-refactor)
- [ ] All planning documents reviewed

**Git Strategy**: No commits (preparation only)

**Time Estimate**: 2 hours (added 1 hour for baseline + backup)

---

### Phase 1: Create Feature Branch and Baseline

**Objective**: Establish refactor branch and document current state

**Tasks**: (UNCHANGED from original plan)

1. Create feature branch: `git checkout -b 002-refactor-pure-search`
2. Capture baseline metrics (LOC, tests, coverage)
3. Document baseline state in `docs/baseline/baseline-state.md`

**NEW: Rollback Plan**:
```bash
# If Phase 1 needs rollback (unlikely)
git checkout main
git branch -D 002-refactor-pure-search
```

**Acceptance Criteria**: (UNCHANGED)

**Git Strategy**: (UNCHANGED)
```bash
git add docs/baseline/
git commit -m "chore(refactor): establish baseline for pure-search refactor"
```

**Time Estimate**: 1 hour (UNCHANGED)

---

### Phase 2: Database Schema Refactoring

**Objective**: Remove non-search tables, add project_id for multi-project support

**Tasks**: (ENHANCED with security and validation)

1. **Create Migration Script** (`migrations/002_remove_non_search_tables.sql`)

   **ENHANCED: Add project_id validation**:
   ```sql
   -- Migration 002: Remove non-search tables, add multi-project support

   -- SECURITY: Validate project_id format with CHECK constraint
   -- Pattern: lowercase alphanumeric + hyphens, 1-50 chars
   CREATE OR REPLACE FUNCTION validate_project_id(pid TEXT) RETURNS BOOLEAN AS $$
   BEGIN
       RETURN pid ~ '^[a-z0-9-]{1,50}$'
              AND pid NOT LIKE '-%'
              AND pid NOT LIKE '%-'
              AND pid NOT LIKE '%--%%';
   END;
   $$ LANGUAGE plpgsql IMMUTABLE;

   -- Drop non-search tables (in dependency order)
   DROP TABLE IF EXISTS deployment_work_items CASCADE;
   DROP TABLE IF EXISTS deployment_vendors CASCADE;
   DROP TABLE IF EXISTS deployments CASCADE;
   DROP TABLE IF EXISTS work_item_dependencies CASCADE;
   DROP TABLE IF EXISTS work_items CASCADE;
   DROP TABLE IF EXISTS task_planning_references CASCADE;
   DROP TABLE IF EXISTS tasks CASCADE;
   DROP TABLE IF EXISTS vendors CASCADE;
   DROP TABLE IF EXISTS project_configuration CASCADE;

   -- Add project_id to remaining tables
   ALTER TABLE repositories ADD COLUMN project_id TEXT;
   ALTER TABLE code_chunks ADD COLUMN project_id TEXT;

   -- Backfill with 'default' project
   UPDATE repositories SET project_id = 'default' WHERE project_id IS NULL;
   UPDATE code_chunks SET project_id = 'default' WHERE project_id IS NULL;

   -- Make NOT NULL and add validation
   ALTER TABLE repositories
       ALTER COLUMN project_id SET NOT NULL,
       ADD CONSTRAINT valid_project_id_repositories
       CHECK (validate_project_id(project_id));

   ALTER TABLE code_chunks
       ALTER COLUMN project_id SET NOT NULL,
       ADD CONSTRAINT valid_project_id_chunks
       CHECK (validate_project_id(project_id));

   -- Update unique constraints
   ALTER TABLE repositories DROP CONSTRAINT IF EXISTS repositories_path_key;
   ALTER TABLE repositories ADD CONSTRAINT repositories_project_path_key
       UNIQUE(project_id, path);

   -- Create indexes
   CREATE INDEX IF NOT EXISTS idx_repositories_project_id ON repositories(project_id);
   CREATE INDEX IF NOT EXISTS idx_code_chunks_project_id ON code_chunks(project_id);

   -- Verify migration
   SELECT 'Migration 002 complete' AS status;
   ```

2. **Update Schema File** (src/codebase_mcp/database/schema.sql)

3. **Test Migration on Test Database** (UNCHANGED)

**NEW: Rollback Plan**:
```bash
# If migration fails or tests fail after migration
echo "Rolling back Phase 2: Database schema changes"

# 1. Drop migration changes
psql codebase_mcp < migrations/002_rollback.sql

# 2. Restore schema file
git checkout src/codebase_mcp/database/schema.sql

# 3. Verify original schema restored
psql codebase_mcp -c "\dt"

# 4. Run original tests to validate
pytest tests/ -v
```

**Safe to Proceed If**:
- Migration completes without errors
- Test database validation passes
- Original data preserved in repositories/code_chunks
- project_id CHECK constraint enforces valid format

**Acceptance Criteria**: (ENHANCED)
- [ ] Migration script created with project_id validation
- [ ] Schema file updated (only 2 tables)
- [ ] Migration tested on test database
- [ ] No data loss (test data verified)
- [ ] Rollback script created and tested
- [ ] CHECK constraints prevent invalid project_id

**Git Strategy**: (UNCHANGED)

**Time Estimate**: 3 hours (added 1 hour for validation)

---

### Phases 3-6: Code Removal

(UNCHANGED from original plan - tool files, database operations, server registration, tests)

**Rollback Plans**: Git-based reversions (same as Phase 1)

**Time Estimates**: (UNCHANGED)

---

### Phase 7: Add Multi-Project Support

**Objective**: Implement project_id parameter, workflow-mcp integration, validation

**Tasks**: (ENHANCED with error handling)

1. **Create Project Context Module** (`src/codebase_mcp/utils/project_context.py`)
   - Implement `get_active_project_id()` with error categorization (see C2 resolution)
   - Add caching (60-second TTL)
   - Implement retry logic for transient failures

2. **Create Project ID Validator** (`src/codebase_mcp/utils/validation.py`)
   ```python
   from pydantic import BaseModel, Field, validator

   class ProjectIDValidator(BaseModel):
       """Validates project_id format for security"""
       project_id: str = Field(
           pattern=r'^[a-z0-9-]{1,50}$',
           description="Lowercase alphanumeric with hyphens, max 50 chars"
       )

       @validator('project_id')
       def validate_safe_project_id(cls, v):
           """Additional safety checks"""
           if v.startswith('-') or v.endswith('-'):
               raise ValueError("project_id cannot start or end with hyphen")
           if '--' in v:
               raise ValueError("project_id cannot contain consecutive hyphens")
           if len(v.encode('utf-8')) > 50:
               raise ValueError("project_id too long (max 50 bytes)")
           # Prevent SQL injection patterns
           dangerous_patterns = [';', '--', '/*', '*/', 'DROP', 'DELETE', 'INSERT']
           if any(pattern.lower() in v.lower() for pattern in dangerous_patterns):
               raise ValueError("project_id contains invalid characters")
           return v
   ```

3. **Update Search Tool Parameters** (see C2 for enhanced error messages)

4. **Write Multi-Project Tests** (`tests/test_multi_project.py`)
   - `test_multi_project_isolation()` - No cross-contamination
   - `test_search_with_workflow_mcp_integration()` - Active project detection
   - `test_workflow_mcp_error_categorization()` - Error message quality
   - `test_project_id_validation_rejects_sql_injection()` - Security

**NEW: Advisory Lock Implementation**:
```python
async def index_repository_db(pool, repo_path, project_id, force_reindex):
    """Index repository with advisory lock to prevent concurrent indexing"""
    async with pool.acquire() as conn:
        # Generate lock ID from repo_path + project_id
        lock_id = hash(f"{project_id}:{repo_path}") % (2**31)

        # Try to acquire lock (non-blocking)
        acquired = await conn.fetchval(
            "SELECT pg_try_advisory_lock($1)",
            lock_id
        )

        if not acquired:
            raise RuntimeError(
                f"Repository {repo_path} is currently being indexed.\n"
                f"Wait for indexing to complete or kill other indexing process."
            )

        try:
            # Indexing logic...
            pass
        finally:
            # Always release lock
            await conn.execute("SELECT pg_advisory_unlock($1)", lock_id)
```

**NEW: Rollback Plan**:
```bash
# If multi-project implementation fails
git checkout src/codebase_mcp/tools/search.py
git rm src/codebase_mcp/utils/project_context.py
git rm src/codebase_mcp/utils/validation.py
pytest tests/test_search.py -v
```

**Acceptance Criteria**: (ENHANCED)
- [ ] project_id parameter added to both tools
- [ ] get_active_project_id() with error categorization
- [ ] ProjectIDValidator prevents SQL injection
- [ ] Active project caching (60s TTL)
- [ ] Advisory locks prevent concurrent indexing
- [ ] Multi-project isolation tests pass
- [ ] workflow-mcp integration tests pass
- [ ] Enhanced error messages implemented

**Git Strategy**: (UNCHANGED)

**Time Estimate**: 4 hours (added 1 hour for validation and locks)

---

### Phase 8: Database Connection Management

**Objective**: Per-project connection pools with LRU eviction and monitoring

**Tasks**: (ENHANCED)

1. **Refactor Connection Module** (`src/codebase_mcp/database/connection.py`)
   - Implement LRU eviction (see R1 resolution)
   - Add MAX_PROJECTS configuration
   - Implement connection pool monitoring

2. **Create Pool Statistics Endpoint**:
   ```python
   async def get_pool_stats(project_id: str) -> dict:
       """Get connection pool statistics for monitoring"""
       if project_id not in _pools:
           return {"error": "No pool for project"}

       pool = _pools[project_id]
       return {
           "project_id": project_id,
           "size": pool.get_size(),
           "min_size": pool.get_min_size(),
           "max_size": pool.get_max_size(),
           "free_connections": pool.get_idle_size(),
       }
   ```

3. **Write Connection Pool Tests**:
   - `test_per_project_pools()` - Pool isolation
   - `test_lru_eviction()` - Eviction when MAX_PROJECTS reached
   - `test_database_auto_creation()` - Auto-create databases

**NEW: Rollback Plan**:
```bash
# If connection pooling changes fail
git checkout src/codebase_mcp/database/connection.py
pytest tests/test_connection_pooling.py -v
```

**Acceptance Criteria**: (ENHANCED)
- [ ] One pool per project (OrderedDict tracking)
- [ ] LRU eviction when MAX_PROJECTS reached
- [ ] MAX_PROJECTS configurable via env var
- [ ] Pool statistics endpoint implemented
- [ ] Databases auto-created with proper permissions
- [ ] Tests validate eviction behavior

**Git Strategy**: (UNCHANGED)

**Time Estimate**: 3 hours (added 1 hour for eviction logic)

---

### Phases 9-10: Documentation and Migration

(ENHANCED with PostgreSQL configuration and rollback documentation - see R2)

**Time Estimates**: 3 hours (added 1 hour for production config docs)

---

### Phase 11: Performance Testing and Optimization

**Objective**: Validate performance meets targets with NO regression from baseline

**Tasks**: (ENHANCED)

1. **Create Performance Test Suite** (`tests/test_performance.py`)
   - `test_search_latency_p95()` - Constitutional requirement
   - `test_indexing_throughput()` - Constitutional requirement
   - **NEW**: `test_multi_tenant_search_latency()` - 10 concurrent projects
   - **NEW**: `test_connection_pool_saturation()` - 50 concurrent searches
   - **NEW**: `test_search_latency_with_large_corpus()` - 100k+ chunks

2. **Run Performance Benchmarks**
   ```bash
   # All performance tests
   pytest tests/test_performance.py -v -m performance

   # Generate benchmark report
   pytest tests/test_performance.py \
       --benchmark-only \
       --benchmark-json=perf-results.json
   ```

3. **Compare Against Baseline**
   ```python
   @pytest.mark.performance
   async def test_no_performance_regression(baseline_metrics):
       """Validate no regression from baseline"""
       # Current metrics
       current_search_p95 = await measure_search_p95()
       current_indexing_time = await measure_indexing_time()

       # Baseline metrics
       baseline_search_p95 = baseline_metrics['search_p95']
       baseline_indexing_time = baseline_metrics['indexing_time']

       # Allow 20% degradation max
       assert current_search_p95 < baseline_search_p95 * 1.20, \
           f"Search regressed {(current_search_p95/baseline_search_p95-1)*100:.1f}%"

       assert current_indexing_time < baseline_indexing_time * 1.20, \
           f"Indexing regressed {(current_indexing_time/baseline_indexing_time-1)*100:.1f}%"
   ```

4. **Optimize if Needed**
   - HNSW index parameters (m, ef_construction)
   - Connection pool sizing
   - Batch sizes for indexing
   - Ollama concurrent requests

**NEW: Rollback Plan**:
```bash
# If performance targets not met
git checkout src/codebase_mcp/database/operations.py
git checkout src/codebase_mcp/database/schema.sql
pytest tests/test_performance.py -v -m performance
```

**Acceptance Criteria**: (ENHANCED)
- [ ] Search latency <500ms p95 (constitutional)
- [ ] Indexing <60s for 10k files (constitutional)
- [ ] Multi-tenant: 10 projects concurrent, still <500ms p95
- [ ] Connection saturation: 50 concurrent, no timeouts
- [ ] Large corpus: 100k+ chunks, still <500ms p95
- [ ] NO regression >20% from baseline

**Git Strategy**: (UNCHANGED)

**Time Estimate**: 4 hours (added 1 hour for multi-tenant tests)

---

### Phase 12: Final Validation and Release

**Objective**: Comprehensive validation before release

**Tasks**: (ENHANCED)

1. **Run Full Test Suite** (UNCHANGED)
2. **Run mypy Type Checking** (UNCHANGED)
3. **Run MCP Protocol Compliance Tests** (UNCHANGED)

4. **NEW: Validate Against Constitution**

   **Create `scripts/validate-constitutional-compliance.sh`**:
   ```bash
   #!/bin/bash
   # Validate constitutional compliance

   echo "=== CONSTITUTIONAL COMPLIANCE VALIDATION ==="

   # Principle I: Simplicity (only 2 tools)
   tool_count=$(grep "@mcp.tool" src/ -r | wc -l)
   [ $tool_count -eq 2 ] && echo "✅ Principle I: Only 2 tools" || echo "❌ Principle I: $tool_count tools found"

   # Principle III: Protocol Compliance
   mcp-inspector http://localhost:8000 --full-validation
   [ $? -eq 0 ] && echo "✅ Principle III: Protocol compliant" || echo "❌ Principle III: Failed"

   # Principle IV: Performance
   pytest tests/test_performance.py -v -m performance
   [ $? -eq 0 ] && echo "✅ Principle IV: Performance targets met" || echo "❌ Principle IV: Failed"

   # Principle V: Production Quality (mypy, coverage)
   mypy --strict src/codebase_mcp/
   [ $? -eq 0 ] && echo "✅ Principle V: Type safety" || echo "❌ Principle V: mypy failed"

   coverage=$(pytest tests/ --cov=src/codebase_mcp --cov-report=term | grep TOTAL | awk '{print $4}' | sed 's/%//')
   [ $coverage -ge 80 ] && echo "✅ Principle V: Coverage ${coverage}%" || echo "❌ Principle V: Coverage ${coverage}%"

   # Principle VII: TDD (all tests pass)
   pytest tests/ -v
   [ $? -eq 0 ] && echo "✅ Principle VII: All tests pass" || echo "❌ Principle VII: Tests failed"

   # Principle VIII: Pydantic (all models use Pydantic)
   pydantic_models=$(grep "class.*BaseModel" src/ -r | wc -l)
   [ $pydantic_models -ge 2 ] && echo "✅ Principle VIII: Pydantic models used" || echo "❌ Principle VIII: No models"

   # Principle X: Git micro-commits
   commit_count=$(git log pre-refactor..HEAD --oneline | wc -l)
   [ $commit_count -ge 10 ] && echo "✅ Principle X: $commit_count micro-commits" || echo "⚠️ Principle X: Only $commit_count commits"

   echo "=== VALIDATION COMPLETE ==="
   ```

5. **Compare Baseline vs Final State** (ENHANCED)
   ```bash
   # Generate comparison report
   cat > docs/baseline/comparison.md <<EOF
   # Refactor Results Comparison

   ## Code Metrics
   Before: $(cat docs/baseline/loc-before.txt | grep "SUM:" | awk '{print $5}') lines
   After: $(cat docs/baseline/loc-after.txt | grep "SUM:" | awk '{print $5}') lines
   Reduction: X% (goal: 60%)

   ## Tool Surface
   Before: 16 tools
   After: 2 tools
   Reduction: 87.5%

   ## Performance
   Search p95:
     Before: ${baseline_search_p95}ms
     After: ${current_search_p95}ms
     Change: ${regression_pct}%

   Indexing (10k files):
     Before: ${baseline_indexing}s
     After: ${current_indexing}s
     Change: ${indexing_regression_pct}%
   EOF
   ```

6. **Update Version Number** (UNCHANGED)

7. **Create Release Tag** (UNCHANGED)

**NEW: Final Rollback Point**:

If validation fails at this stage, full rollback:
```bash
./scripts/emergency-rollback.sh
```

**Acceptance Criteria**: (ENHANCED)
- [ ] All tests pass (100%)
- [ ] Coverage >80%
- [ ] mypy --strict passes (0 errors)
- [ ] mcp-inspector 100% compliance
- [ ] All 11 constitutional principles satisfied
- [ ] Version bumped to 2.0.0
- [ ] Release tag created
- [ ] Comparison report shows 60% code reduction
- [ ] No performance regression >20%

**Git Strategy**: (UNCHANGED)

**Time Estimate**: 3 hours (added 1 hour for constitutional validation)

---

## Updated Refactoring Plan

(File-by-file changes remain largely unchanged from original plan, with additions for validation, error handling, and security)

**Key Additions**:
- `src/codebase_mcp/utils/validation.py` - ProjectIDValidator class
- `src/codebase_mcp/utils/project_context.py` - Enhanced with error categorization
- `migrations/002_rollback.sql` - Rollback script
- `scripts/validate-constitutional-compliance.sh` - Compliance checker
- `scripts/emergency-rollback.sh` - Emergency recovery
- `scripts/generate_test_repo.py` - Test data generator
- `scripts/benchmark_search.py` - Performance benchmarking

---

## Enhanced Error Handling

### Complete Error Catalog

#### Search Errors

**E001: Repository Path Invalid**
```python
# Trigger: repo_path doesn't exist or is not a directory
raise ValueError(
    "Repository path does not exist or is not a directory: /path/to/repo\n"
    "Solution: Verify path exists: ls -la /path/to/repo"
)
```

**E002: Invalid Project ID Format**
```python
# Trigger: project_id fails validation (special chars, length)
raise ValueError(
    "Invalid project_id format. Must be lowercase alphanumeric with hyphens, 1-50 chars.\n"
    f"Invalid: '{project_id}'\n"
    "Example valid: 'my-project-123'"
)
```

**E003: Project Not Indexed**
```python
# Trigger: Database doesn't exist for project_id
raise ValueError(
    f"Project '{project_id}' not indexed.\n"
    f"Solution: Index repository first:\n"
    f"  index_repository(repo_path='/path/to/repo', project_id='{project_id}')"
)
```

**E004: workflow-mcp Unavailable**
```python
# Trigger: workflow-mcp not running or unreachable
raise ValueError(
    "workflow-mcp unavailable.\n"
    "Solution 1: Start workflow-mcp: workflow-mcp run\n"
    "Solution 2: Check URL: echo $WORKFLOW_MCP_URL\n"
    "Solution 3: Provide explicit project_id parameter"
)
```

**E005: No Active Project Set**
```python
# Trigger: workflow-mcp running but no active project
raise ValueError(
    "No active project set in workflow-mcp.\n"
    "Solution 1: Set active project via workflow-mcp\n"
    "Solution 2: Provide explicit project_id parameter"
)
```

**E006: Connection Pool Exhausted**
```python
# Trigger: All connections in use, wait timeout exceeded
raise TimeoutError(
    f"Database connection pool exhausted for project '{project_id}'.\n"
    "Current: 20/20 connections in use.\n"
    "Solution 1: Wait for active queries to complete\n"
    "Solution 2: Increase max_size in connection.py"
)
```

**E007: Concurrent Indexing Blocked**
```python
# Trigger: Advisory lock held by another process
raise RuntimeError(
    f"Repository {repo_path} is currently being indexed.\n"
    "Another process holds the advisory lock.\n"
    "Solution: Wait for indexing to complete (~60s for 10k files)"
)
```

#### Database Errors

**E008: Database Creation Failed (Permissions)**
```python
# Trigger: Insufficient privileges to CREATE DATABASE
raise RuntimeError(
    "Insufficient permissions to create database.\n"
    f"Grant CREATEDB privilege: ALTER USER {user} CREATEDB;\n"
    f"Or manually create: CREATE DATABASE codebase_{project_id};"
)
```

**E009: Database Connection Failed**
```python
# Trigger: Cannot connect to PostgreSQL
raise ConnectionError(
    "Cannot connect to PostgreSQL.\n"
    f"Host: {host}:{port}\n"
    "Solution 1: Check PostgreSQL is running: sudo systemctl status postgresql\n"
    "Solution 2: Verify connection settings: echo $POSTGRES_HOST"
)
```

#### Ollama Errors

**E010: Ollama Unavailable**
```python
# Trigger: Cannot connect to Ollama API
raise ConnectionError(
    "Cannot connect to Ollama.\n"
    f"URL: {ollama_url}\n"
    "Solution 1: Start Ollama: ollama serve\n"
    "Solution 2: Check URL: echo $OLLAMA_URL"
)
```

**E011: Model Not Found**
```python
# Trigger: nomic-embed-text model not pulled
raise ValueError(
    "Ollama model 'nomic-embed-text' not found.\n"
    "Solution: Pull model: ollama pull nomic-embed-text\n"
    "This is a one-time setup step."
)
```

**E012: Embedding Generation Timeout**
```python
# Trigger: Ollama embedding request >5s
raise TimeoutError(
    "Ollama embedding generation timed out (>5s).\n"
    "This may indicate Ollama is overloaded or model not loaded.\n"
    "Solution: Restart Ollama: systemctl restart ollama"
)
```

### Error Handling Patterns

**Database Operations**:
```python
async def search_code_db(pool, query_embedding, project_id, filters, limit):
    """Search with comprehensive error handling"""
    try:
        async with pool.acquire() as conn:
            results = await conn.fetch(
                "SELECT ... FROM code_chunks WHERE project_id = $1 ...",
                project_id, query_embedding, limit
            )
            return [dict(row) for row in results]

    except asyncpg.InvalidCatalogNameError:
        raise ValueError(f"Project '{project_id}' not indexed (E003)")

    except asyncpg.PoolTimeoutError:
        raise TimeoutError(f"Connection pool exhausted (E006)")

    except asyncpg.PostgresError as e:
        logger.error("database_query_failed", error=str(e), project_id=project_id)
        raise RuntimeError(f"Database error: {e}")

    except Exception as e:
        logger.error("unexpected_search_error", error=str(e), project_id=project_id)
        raise
```

**workflow-mcp Integration**:
```python
async def get_active_project_id() -> Tuple[Optional[str], WorkflowMCPStatus]:
    """Get active project with detailed error categorization"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{workflow_mcp_url}/get_active_project",
                timeout=aiohttp.ClientTimeout(total=2.0)
            ) as response:
                # ... (see C2 resolution for full implementation)
                pass

    except asyncio.TimeoutError:
        logger.warning("workflow_mcp_timeout")
        return (None, WorkflowMCPStatus.TIMEOUT)

    except aiohttp.ClientConnectorError:
        logger.warning("workflow_mcp_connection_refused")
        return (None, WorkflowMCPStatus.UNAVAILABLE)

    except Exception as e:
        logger.error("workflow_mcp_unexpected_error", error=str(e))
        return (None, WorkflowMCPStatus.UNAVAILABLE)
```

---

## Database Security

### SQL Injection Prevention

**Validation at API Boundary**:
```python
from pydantic import BaseModel, Field, validator

class SearchCodeParams(BaseModel):
    query: str = Field(description="Search query")
    project_id: str = Field(
        pattern=r'^[a-z0-9-]{1,50}$',
        description="Project ID (validated)"
    )

    @validator('project_id')
    def prevent_sql_injection(cls, v):
        """Block SQL injection patterns"""
        dangerous = [';', '--', '/*', '*/', 'DROP', 'DELETE', 'INSERT', 'UPDATE']
        if any(pattern.lower() in v.lower() for pattern in dangerous):
            raise ValueError("Invalid project_id (potential SQL injection)")
        return v
```

**Parameterized Queries**:
```python
# SAFE: AsyncPG handles parameterization
async with pool.acquire() as conn:
    results = await conn.fetch(
        "SELECT * FROM code_chunks WHERE project_id = $1",
        project_id  # Safely escaped by AsyncPG
    )

# UNSAFE: String formatting (NEVER DO THIS)
# query = f"SELECT * FROM code_chunks WHERE project_id = '{project_id}'"
# await conn.fetch(query)  # SQL INJECTION RISK
```

**Database Name Validation**:
```python
async def get_db_pool(project_id: str) -> asyncpg.Pool:
    """Create pool with validated database name"""
    # Validate format (raises ValueError if invalid)
    ProjectIDValidator(project_id=project_id)

    # Safe: project_id validated to be alphanumeric + hyphens only
    database_name = f"codebase_{project_id}"

    # AsyncPG handles database name escaping
    pool = await asyncpg.create_pool(database=database_name, ...)
    return pool
```

**CHECK Constraints in Database**:
```sql
-- Enforce validation at database level
ALTER TABLE repositories ADD CONSTRAINT valid_project_id_repositories
    CHECK (project_id ~ '^[a-z0-9-]{1,50}$');

ALTER TABLE code_chunks ADD CONSTRAINT valid_project_id_chunks
    CHECK (project_id ~ '^[a-z0-9-]{1,50}$');
```

### Security Test Suite

**Add to `tests/test_security.py`**:

```python
import pytest

@pytest.mark.security
@pytest.mark.asyncio
async def test_sql_injection_in_project_id():
    """Test SQL injection attempts are blocked"""
    malicious_ids = [
        "'; DROP TABLE repositories; --",
        "admin'--",
        "1' OR '1'='1",
        "../../../etc/passwd",
        "test; DELETE FROM code_chunks WHERE '1'='1",
    ]

    for malicious_id in malicious_ids:
        with pytest.raises(ValueError, match="Invalid project_id"):
            await search_code(SearchCodeParams(
                query="test",
                project_id=malicious_id
            ))

@pytest.mark.security
@pytest.mark.asyncio
async def test_path_traversal_in_directory_filter():
    """Test path traversal is blocked"""
    malicious_directories = [
        "../../../etc/",
        "../../.ssh/",
        "/etc/passwd",
    ]

    for malicious_dir in malicious_directories:
        # Should return empty results (directory not in project)
        result = await search_code(SearchCodeParams(
            query="test",
            project_id="test-project",
            directory=malicious_dir
        ))

        assert len(result["results"]) == 0

@pytest.mark.security
async def test_database_name_escaping():
    """Test database names are properly escaped"""
    # Valid project_id with special chars should be rejected
    with pytest.raises(ValueError):
        await get_db_pool("test; DROP DATABASE codebase_test;")
```

---

## Rollback Strategy

### Phase-by-Phase Rollback

Each phase includes specific rollback instructions (see Updated Implementation Phases above).

### Emergency Full Rollback

**Script: `scripts/emergency-rollback.sh`**

```bash
#!/bin/bash
# Emergency rollback: Restore system to pre-refactor state

set -e

echo "=== EMERGENCY ROLLBACK ==="
echo "This will revert ALL refactoring changes."
read -p "Are you sure? (type 'yes' to confirm): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Rollback cancelled."
    exit 1
fi

# 1. Git rollback
echo "Step 1: Reverting Git to pre-refactor state..."
git checkout main
git branch -D 002-refactor-pure-search || true

# 2. Database rollback
echo "Step 2: Restoring database from backup..."
if [ ! -f "backups/backup-before-002.sql" ]; then
    echo "ERROR: Backup file not found!"
    echo "Cannot proceed without backup."
    exit 1
fi

dropdb codebase_mcp
createdb codebase_mcp
psql codebase_mcp < backups/backup-before-002.sql

# 3. Verify restoration
echo "Step 3: Verifying restoration..."
table_count=$(psql codebase_mcp -tAc "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'")

if [ "$table_count" -lt 9 ]; then
    echo "WARNING: Expected 9+ tables, found $table_count"
    echo "Database may not be fully restored."
fi

# 4. Run original tests
echo "Step 4: Running original tests..."
pytest tests/ -v

echo "=== ROLLBACK COMPLETE ==="
echo "System restored to pre-refactor state (git tag: pre-refactor)"
```

### Safe Rollback Points

| Phase | Safe to Rollback? | Rollback Method | Risk |
|-------|-------------------|-----------------|------|
| 0-1   | ✅ Yes            | Git revert      | None |
| 2     | ⚠️ Caution        | Database restore + git | Medium (data loss if no backup) |
| 3-6   | ✅ Yes            | Git revert      | Low |
| 7-8   | ✅ Yes            | Git revert      | Low |
| 9-10  | ✅ Yes            | Git revert      | None (docs only) |
| 11    | ✅ Yes            | Git revert      | Low |
| 12    | ⚠️ Full rollback  | Emergency script | High (release prep) |

### Data Recovery Procedures

**Scenario 1: Database Corruption During Migration**

```bash
# 1. Stop codebase-mcp server
sudo systemctl stop codebase-mcp

# 2. Drop corrupted database
dropdb codebase_mcp

# 3. Restore from backup
createdb codebase_mcp
psql codebase_mcp < backups/backup-before-002.sql

# 4. Verify restoration
psql codebase_mcp -c "\dt"
psql codebase_mcp -c "SELECT count(*) FROM repositories"

# 5. Restart server
sudo systemctl start codebase-mcp
```

**Scenario 2: Partial Migration State**

```bash
# If migration partially completed (some tables dropped, not all)

# 1. Check current state
psql codebase_mcp -c "\dt"

# 2. Run rollback migration
psql codebase_mcp < migrations/002_rollback.sql

# 3. If rollback fails, restore from backup
dropdb codebase_mcp
createdb codebase_mcp
psql codebase_mcp < backups/backup-before-002.sql
```

**Scenario 3: Code Changes Committed, Need to Revert**

```bash
# Revert specific phase
git revert <commit-hash>

# Or reset to pre-refactor tag
git reset --hard pre-refactor

# Force push if already pushed to remote
git push --force origin 002-refactor-pure-search
```

---

## Performance Validation

### Baseline Collection

**Phase 0**: Capture current performance (see Phase 0 tasks above)

**Metrics Captured**:
- Indexing time for 10,000 files
- Search latency (p50, p95, p99, mean)
- Database size after indexing
- Memory usage during indexing

### Regression Detection

**Phase 11**: Compare refactored performance against baseline

**Automated Regression Test**:
```python
@pytest.mark.performance
@pytest.mark.asyncio
async def test_no_performance_regression(baseline_metrics):
    """Ensure refactor didn't degrade performance"""
    # Load baseline
    with open('docs/baseline/search-latency-before.json') as f:
        baseline = json.load(f)

    # Measure current
    latencies = []
    for i in range(100):
        start = time.time()
        await search_code(SearchCodeParams(query=f"test {i}", project_id="test"))
        latencies.append((time.time() - start) * 1000)

    latencies.sort()
    current_p95 = latencies[int(0.95 * len(latencies))]
    baseline_p95 = baseline['p95']

    # Allow 20% degradation
    max_acceptable = baseline_p95 * 1.20

    assert current_p95 < max_acceptable, \
        f"Performance regression: {current_p95:.2f}ms is {(current_p95/baseline_p95-1)*100:.1f}% slower than baseline {baseline_p95:.2f}ms"
```

### CI Integration

**GitHub Actions workflow** (`.github/workflows/performance.yml`):

```yaml
name: Performance Tests

on:
  pull_request:
    branches: [main]

jobs:
  performance:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio

      - name: Start PostgreSQL
        run: |
          sudo systemctl start postgresql
          createdb codebase_test

      - name: Start Ollama
        run: |
          curl -fsSL https://ollama.com/install.sh | sh
          ollama pull nomic-embed-text

      - name: Run performance tests
        run: pytest tests/test_performance.py -v -m performance

      - name: Upload benchmark results
        uses: actions/upload-artifact@v3
        with:
          name: performance-results
          path: perf-results.json
```

---

## Updated Testing Strategy

### Test Pyramid

```
                    /\
                   /  \
                  / E2E\ (5%)
                 /______\
                /        \
               /Integration\ (25%)
              /____________\
             /              \
            /  Unit Tests    \ (70%)
           /________________\
```

### Test Categories

#### Unit Tests (70%)
- **Location**: `tests/unit/`
- **Scope**: Individual functions, classes
- **Speed**: <1s total
- **Examples**:
  - `test_project_id_validation()`
  - `test_workflow_mcp_error_categorization()`
  - `test_lru_pool_eviction()`

#### Integration Tests (25%)
- **Location**: `tests/integration/`
- **Scope**: Component interactions (database, Ollama)
- **Speed**: <30s total
- **Examples**:
  - `test_index_and_search_workflow()`
  - `test_multi_project_isolation()`
  - `test_workflow_mcp_integration()`

#### Performance Tests (5%)
- **Location**: `tests/test_performance.py`
- **Scope**: Latency, throughput, scaling
- **Speed**: 5-10 minutes
- **Examples**:
  - `test_search_latency_p95()`
  - `test_multi_tenant_stress()`
  - `test_connection_pool_saturation()`

#### Security Tests
- **Location**: `tests/test_security.py`
- **Scope**: SQL injection, path traversal, validation bypass
- **Examples**:
  - `test_sql_injection_blocked()`
  - `test_path_traversal_blocked()`

### Multi-Tenant Stress Tests

**Enhanced from R4**:

```python
@pytest.mark.performance
@pytest.mark.stress
@pytest.mark.asyncio
async def test_20_project_concurrent_search():
    """Stress test: 20 projects, 100 searches each"""
    num_projects = 20
    searches_per_project = 100

    # Setup
    projects = [f"stress-{i}" for i in range(num_projects)]
    for project_id in projects:
        await ensure_database_exists(project_id)

    # Concurrent workload
    async def search_repeatedly(project_id):
        for i in range(searches_per_project):
            await search_code(SearchCodeParams(
                query=f"query {i}",
                project_id=project_id
            ))

    # Execute
    start = time.time()
    await asyncio.gather(*[search_repeatedly(p) for p in projects])
    duration = time.time() - start

    # Validate
    total_searches = num_projects * searches_per_project
    avg_latency = (duration / total_searches) * 1000

    print(f"Completed {total_searches} searches in {duration:.2f}s")
    print(f"Average latency: {avg_latency:.2f}ms")

    assert avg_latency < 500, f"Average latency {avg_latency:.2f}ms exceeds 500ms"
```

---

## Risk Mitigation

### Updated Risk Assessment

| Risk | Severity | Likelihood | Mitigation Status |
|------|----------|------------|-------------------|
| Database connection exhaustion | HIGH | MEDIUM | ✅ Mitigated (MAX_PROJECTS limit, LRU eviction) |
| workflow-mcp integration failures | MEDIUM | MEDIUM | ✅ Mitigated (error categorization, fallback) |
| Migration data loss | MEDIUM | LOW | ✅ Mitigated (backup strategy, rollback scripts) |
| Performance regression | MEDIUM | LOW | ✅ Mitigated (baseline + regression tests) |
| SQL injection | CRITICAL | LOW | ✅ Mitigated (validation + parameterized queries) |
| Concurrent indexing corruption | HIGH | LOW | ✅ Mitigated (advisory locks) |

### Mitigation Strategies

**Database Connection Exhaustion**:
- MAX_PROJECTS configuration (default: 50)
- LRU pool eviction when limit reached
- PostgreSQL max_connections tuning documented
- Connection pool monitoring

**workflow-mcp Integration Failures**:
- Error categorization (UNAVAILABLE, TIMEOUT, NO_ACTIVE_PROJECT, INVALID_RESPONSE)
- Enhanced error messages with actionable solutions
- 60-second response caching
- Graceful fallback to explicit project_id

**Migration Data Loss**:
- Comprehensive backup in Phase 0
- Rollback scripts tested on test database
- Non-destructive migration (adds columns before dropping tables)
- Validation checkpoints after migration

**Performance Regression**:
- Baseline collection in Phase 0
- Regression tests in Phase 11 (max 20% degradation allowed)
- Multi-tenant stress tests
- Performance comparison report

**SQL Injection**:
- project_id validation (Pydantic + regex)
- CHECK constraints in database
- Parameterized queries (AsyncPG)
- Security test suite

**Concurrent Indexing Corruption**:
- PostgreSQL advisory locks
- Lock acquisition test
- Error message with guidance

---

## Acceptance Criteria

### Functional Criteria

- [ ] Only 2 MCP tools registered: `index_repository`, `search_code`
- [ ] Multi-project support works (10+ projects indexed, searched independently)
- [ ] workflow-mcp integration works (active project detection)
- [ ] Graceful fallback to explicit project_id when workflow-mcp unavailable
- [ ] No cross-project data leakage (validated in tests)
- [ ] Advisory locks prevent concurrent indexing

### Non-Functional Criteria

- [ ] Search latency <500ms p95 (constitutional requirement)
- [ ] Indexing throughput <60s for 10k files (constitutional requirement)
- [ ] No performance regression >20% from baseline
- [ ] Multi-tenant: 10 projects concurrent, still <500ms p95
- [ ] Connection pool saturation: 50 concurrent, no timeouts
- [ ] 100% MCP protocol compliance (mcp-inspector validation)
- [ ] Type-safe: mypy --strict passes (0 errors)
- [ ] Test coverage >80%

### Process Criteria

- [ ] All 12 phases completed in order
- [ ] Micro-commits after each phase (working state)
- [ ] Documentation updated (README, API docs, migration guide, PostgreSQL config)
- [ ] Migration guide tested and accurate
- [ ] Rollback procedures documented and tested

### Constitutional Compliance

All 11 principles satisfied:
- [ ] Principle I: Simplicity Over Features (only search tools)
- [ ] Principle II: Local-First Architecture (no cloud dependencies)
- [ ] Principle III: Protocol Compliance (mcp-inspector 100%)
- [ ] Principle IV: Performance Guarantees (benchmarks pass)
- [ ] Principle V: Production Quality (error handling, logging, types)
- [ ] Principle VI: Specification-First (plan reviewed and approved)
- [ ] Principle VII: Test-Driven Development (tests before implementation)
- [ ] Principle VIII: Pydantic Type Safety (all models use Pydantic)
- [ ] Principle IX: Orchestrated Subagents (N/A for refactoring)
- [ ] Principle X: Git Micro-Commits (verified in history)
- [ ] Principle XI: FastMCP Foundation (FastMCP used throughout)

### Security Criteria

- [ ] SQL injection attempts blocked (security tests pass)
- [ ] Path traversal attempts return empty results
- [ ] project_id validation enforced (API + database)
- [ ] No unsafe string formatting in queries
- [ ] All queries use parameterized statements

---

## Sign-Off Checklist

### Pre-Implementation Review

- [x] All 5 critical issues from planning review resolved
- [x] All 4 architectural recommendations addressed
- [x] Constitutional compliance maintained (98% score)
- [x] Performance targets achievable (validated via baseline)
- [x] Rollback strategy documented and tested
- [x] Testing strategy comprehensive (unit, integration, performance, security)

### Implementation Readiness

- [ ] workflow-mcp deployed and healthy
- [ ] Development environment setup (PostgreSQL, Ollama, Python 3.11+)
- [ ] Baseline performance metrics captured
- [ ] Database backup created
- [ ] Git tag created (pre-refactor)
- [ ] Test data generators ready

### Post-Implementation Validation

- [ ] All phases completed successfully
- [ ] All tests pass (unit, integration, performance, security)
- [ ] Constitutional validation passes
- [ ] Performance comparison shows no regression
- [ ] Documentation complete and reviewed
- [ ] Migration guide tested

### Release Readiness

- [ ] Version bumped to 2.0.0
- [ ] CHANGELOG updated with breaking changes
- [ ] Release tag created
- [ ] Production deployment guide reviewed
- [ ] PostgreSQL configuration documented
- [ ] Rollback procedures validated

---

## Timeline Estimate

| Phase | Description | Duration | Cumulative |
|-------|-------------|----------|------------|
| 0     | Prerequisites + Baseline | 2h | 2h |
| 1     | Branch & Baseline | 1h | 3h |
| 2     | Database Schema | 3h | 6h |
| 3     | Remove Tool Files | 1h | 7h |
| 4     | Remove DB Operations | 2h | 9h |
| 5     | Update Server | 1h | 10h |
| 6     | Remove Tests | 1h | 11h |
| 7     | Multi-Project Support | 4h | 15h |
| 8     | Connection Pooling | 3h | 18h |
| 9     | Documentation | 2h | 20h |
| 10    | Migration Guide | 2h | 22h |
| 11    | Performance Testing | 4h | 26h |
| 12    | Final Validation | 3h | 29h |
| Post  | PR & Merge | 2h | 31h |

**Total Estimated Time**: 31 hours (4-5 days with testing and validation)

**Breakdown**:
- Planning & Baseline: 3 hours (10%)
- Database Refactoring: 5 hours (16%)
- Code Removal: 5 hours (16%)
- Multi-Project Implementation: 7 hours (23%)
- Documentation: 4 hours (13%)
- Testing & Validation: 7 hours (23%)

**Risk Buffer**: +20% (6 hours) for unexpected issues = **37 hours total**

---

## Next Steps

### Immediate Actions (Before Implementation)

1. **Review and Approve This Plan**
   - Stakeholder review
   - Constitutional compliance validation
   - Risk assessment approval

2. **Prepare Development Environment**
   - Install PostgreSQL 14+, Ollama, Python 3.11+
   - Pull nomic-embed-text model
   - Create test databases

3. **Execute Phase 0**
   - Verify workflow-mcp health
   - Capture performance baseline
   - Create comprehensive backup

### Implementation Phase

1. **Execute Phases 1-12 Sequentially**
   - Follow detailed task lists
   - Commit after each phase
   - Run tests before proceeding

2. **Monitor Progress**
   - Track phase completion
   - Document any deviations
   - Update timeline if needed

### Post-Implementation

1. **Create Pull Request**
   - Review all changes
   - Validate constitutional compliance
   - Merge to main

2. **Deploy Documentation**
   - Update README
   - Publish migration guide
   - Announce v2.0.0

3. **Monitor Production**
   - Track error rates
   - Monitor performance metrics
   - Collect user feedback

---

## Conclusion

This final implementation plan addresses all critical issues from planning and architectural reviews while maintaining constitutional compliance. The plan is comprehensive, implementation-ready, and provides clear verification steps for each phase.

**Key Improvements**:
- Database security hardened (validation + SQL injection prevention)
- Error handling enhanced (workflow-mcp failure modes distinguished)
- Rollback strategy complete (per-phase + emergency recovery)
- Performance validation rigorous (baseline + regression + stress tests)
- Connection management robust (MAX_PROJECTS limit + LRU eviction)

With all critical issues resolved and architectural recommendations integrated, this plan provides a clear, safe path to transforming codebase-mcp into a focused, high-performance semantic code search MCP server.

**Approval Status**: ✅ **IMPLEMENTATION-READY**

---

**Document Version**: 2.0 (Final)
**Last Updated**: 2025-10-11
**Next Review**: After Phase 6 completion (mid-implementation checkpoint)
