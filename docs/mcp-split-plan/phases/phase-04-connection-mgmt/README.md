# Phase 04: Connection Management

**Phase**: 04 - Connection Management (Phase 8 from FINAL-IMPLEMENTATION-PLAN.md)
**Duration**: 4-6 hours
**Dependencies**: Phase 03 (multi-project support implemented)
**Status**: Planned

---

## Objective

Implement production-grade per-project connection pooling with LRU eviction, monitoring, and resource limits.

**Key Feature**: Efficient connection pool management for unlimited projects without resource exhaustion

---

## Scope

### What's Included

- **Connection Pool Manager**
  - LRU cache for connection pools (configurable size)
  - Lazy pool creation (only when needed)
  - Automatic eviction of least-recently-used pools
  - Thread-safe pool access

- **Resource Limits**
  - `MAX_PROJECTS` configuration (default: 10 active pools)
  - `MAX_CONNECTIONS_PER_POOL` (default: 20)
  - Total connection limit validation
  - Clear error messages when limits exceeded

- **Pool Monitoring**
  - Pool usage statistics (hits, misses, evictions)
  - Connection count per pool
  - Health check endpoint (pool status)
  - Logging for pool lifecycle events

- **Graceful Shutdown**
  - Close all pools on server shutdown
  - Wait for in-flight queries to complete
  - Log pool closure statistics

### What's NOT Included

- Advanced load balancing (single PostgreSQL instance)
- Connection retry logic (PostgreSQL handles this)
- Pool warming (lazy creation only)

---

## Key Deliverables

1. **Connection Pool Manager**:
   - `src/codebase_mcp/database/pool_manager.py` - LRU pool cache
   - `get_pool(project_id: str) -> asyncpg.Pool` - Main interface
   - `close_all_pools() -> None` - Cleanup on shutdown

2. **Configuration**:
   - Environment variables: `MAX_PROJECTS`, `MAX_CONNECTIONS_PER_POOL`
   - Validation: Total connections <= PostgreSQL max_connections

3. **Monitoring**:
   - Pool statistics endpoint (internal)
   - Structured logging for pool events

4. **Tests**:
   - `tests/unit/test_pool_manager.py` - Pool lifecycle
   - `tests/integration/test_pool_limits.py` - Resource limits

---

## Acceptance Criteria

- [ ] Connection pool manager implemented with LRU eviction
- [ ] `MAX_PROJECTS` configurable (default: 10)
- [ ] `MAX_CONNECTIONS_PER_POOL` configurable (default: 20)
- [ ] Pools created lazily (not at startup)
- [ ] LRU eviction works (oldest pool closed when limit exceeded)
- [ ] Graceful shutdown closes all pools
- [ ] Pool statistics available (hits, misses, evictions)
- [ ] Thread-safe pool access (asyncio.Lock)
- [ ] All tests passing (unit + integration)
- [ ] No connection leaks (verified with PostgreSQL queries)
- [ ] Git commit: "feat(database): add connection pool manager with LRU eviction"

---

## Connection Pool Manager Design

### LRU Cache Implementation

```python
from collections import OrderedDict
import asyncpg

class ConnectionPoolManager:
    def __init__(
        self,
        max_projects: int = 10,
        max_connections_per_pool: int = 20
    ):
        self._pools: OrderedDict[str, asyncpg.Pool] = OrderedDict()
        self._max_projects = max_projects
        self._max_connections_per_pool = max_connections_per_pool
        self._lock = asyncio.Lock()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}

    async def get_pool(self, project_id: str) -> asyncpg.Pool:
        """Get or create connection pool for project"""
        async with self._lock:
            # Cache hit
            if project_id in self._pools:
                self._pools.move_to_end(project_id)  # Mark as recently used
                self._stats["hits"] += 1
                return self._pools[project_id]

            # Cache miss - create new pool
            self._stats["misses"] += 1

            # Evict LRU pool if at capacity
            if len(self._pools) >= self._max_projects:
                lru_project_id, lru_pool = self._pools.popitem(last=False)
                await lru_pool.close()
                self._stats["evictions"] += 1
                logger.info(f"Evicted LRU pool: {lru_project_id}")

            # Create new pool
            pool = await self._create_pool(project_id)
            self._pools[project_id] = pool
            return pool
```

---

## Resource Limit Configuration

### Environment Variables

- `MAX_PROJECTS`: Max concurrent connection pools (default: 10)
- `MAX_CONNECTIONS_PER_POOL`: Max connections per pool (default: 20)
- `POSTGRES_MAX_CONNECTIONS`: PostgreSQL server limit (default: 100)

### Validation

```python
# Total connections must not exceed PostgreSQL limit
total_connections = MAX_PROJECTS * MAX_CONNECTIONS_PER_POOL
if total_connections > POSTGRES_MAX_CONNECTIONS:
    raise ValueError(
        f"Total connections ({total_connections}) exceeds "
        f"PostgreSQL limit ({POSTGRES_MAX_CONNECTIONS})"
    )
```

### Recommended Settings

| Scenario | MAX_PROJECTS | MAX_CONNECTIONS_PER_POOL | Total Connections |
|----------|--------------|--------------------------|-------------------|
| Development | 5 | 10 | 50 |
| Production (small) | 10 | 20 | 200 |
| Production (large) | 20 | 10 | 200 |

---

## Pool Monitoring

### Statistics Endpoint

```python
async def get_pool_stats() -> dict:
    """Get connection pool statistics (internal use)"""
    return {
        "active_pools": len(pool_manager._pools),
        "max_projects": pool_manager._max_projects,
        "cache_hits": pool_manager._stats["hits"],
        "cache_misses": pool_manager._stats["misses"],
        "evictions": pool_manager._stats["evictions"],
        "pools": [
            {
                "project_id": pid,
                "size": pool.get_size(),
                "idle_connections": pool.get_idle_size(),
            }
            for pid, pool in pool_manager._pools.items()
        ]
    }
```

### Logging

- **INFO**: Pool created, pool evicted, pool closed
- **WARNING**: Approaching connection limit
- **ERROR**: Pool creation failed, connection leak detected

---

## Graceful Shutdown

```python
async def shutdown():
    """Close all connection pools gracefully"""
    logger.info("Closing all connection pools...")
    await pool_manager.close_all_pools()
    logger.info(f"Closed {len(pool_manager._pools)} pools")

# Register shutdown handler
@app.on_shutdown
async def on_shutdown():
    await shutdown()
```

---

## Testing Connection Limits

```python
async def test_pool_eviction():
    """Test LRU eviction when MAX_PROJECTS exceeded"""
    manager = ConnectionPoolManager(max_projects=3)

    # Create 3 pools (at capacity)
    pool1 = await manager.get_pool("project-1")
    pool2 = await manager.get_pool("project-2")
    pool3 = await manager.get_pool("project-3")

    # Create 4th pool - should evict project-1
    pool4 = await manager.get_pool("project-4")

    # project-1 should be evicted
    assert "project-1" not in manager._pools
    assert "project-4" in manager._pools
    assert manager._stats["evictions"] == 1
```

---

## Rollback Procedure

```bash
# Undo connection pool changes
git checkout 002-refactor-pure-search
git reset --hard <commit-before-phase-04>

# No database changes needed (pools are in-memory)
```

---

## Next Phase

After completing Phase 04:
- Verify pool manager working correctly
- Verify resource limits enforced
- Navigate to `../phase-05-docs-migration/`
- Ready for documentation and migration guide

---

## Related Documentation

- **Phase 8 details**: See `../../_archive/01-codebase-mcp/FINAL-IMPLEMENTATION-PLAN.md` lines 2081-2142
- **Critical Issue C5**: Concurrent access patterns (resolved)
- **Recommendation R1**: Connection pool limits (implemented)
- **Connection management**: See `../../_archive/shared-architecture/00-architecture/connection-management.md`

---

**Status**: Planned
**Last Updated**: 2025-10-11
**Estimated Time**: 4-6 hours
