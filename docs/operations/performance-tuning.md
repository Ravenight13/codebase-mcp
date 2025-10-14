# Performance Tuning Operations Guide

**Version**: 1.0.0
**Last Updated**: 2025-10-13
**Feature**: 011-performance-validation-multi
**Phase**: 8
**Task**: T053
**Constitutional Compliance**: Principle IV (Performance Guarantees)

## Overview

This guide provides comprehensive performance tuning strategies for the dual-server MCP architecture. It covers connection pool optimization, database indexing, query tuning, caching strategies, and production deployment recommendations to maintain constitutional performance targets.

## Connection Pool Sizing Recommendations

### Current Configuration Analysis

```yaml
# Current Settings
codebase-mcp:
  POOL_MIN_SIZE: 10
  POOL_MAX_SIZE: 100
  POOL_TIMEOUT: 30.0

workflow-mcp:
  POOL_MIN_SIZE: 5
  POOL_MAX_SIZE: 50
  POOL_TIMEOUT: 30.0
```

### Optimal Pool Sizing Formula

```python
def calculate_optimal_pool_size(
    expected_qps: int,           # Queries per second
    avg_query_time_ms: float,    # Average query duration
    target_utilization: float = 0.75  # Target pool utilization
) -> dict:
    """Calculate optimal connection pool configuration."""

    # Calculate concurrent connections needed
    concurrent_queries = (expected_qps * avg_query_time_ms) / 1000

    # Add buffer for target utilization
    max_pool_size = int(concurrent_queries / target_utilization)

    # Min pool should be 25-40% of max
    min_pool_size = max(5, int(max_pool_size * 0.3))

    return {
        "min_size": min_pool_size,
        "max_size": max_pool_size,
        "recommended_timeout": 30.0,
        "expected_utilization": target_utilization
    }

# Example calculations
codebase_config = calculate_optimal_pool_size(
    expected_qps=100,
    avg_query_time_ms=340,  # From performance tests
    target_utilization=0.75
)
# Result: min=14, max=45

workflow_config = calculate_optimal_pool_size(
    expected_qps=200,
    avg_query_time_ms=80,   # From performance tests
    target_utilization=0.75
)
# Result: min=7, max=22
```

### Production Recommendations by Load Profile

| Load Profile | Concurrent Users | Codebase Pool | Workflow Pool | Notes |
|--------------|-----------------|---------------|---------------|--------|
| **Light** | 1-10 | min:5, max:20 | min:3, max:10 | Development/staging |
| **Medium** | 10-25 | min:10, max:50 | min:5, max:25 | Small production |
| **Heavy** | 25-50 | min:20, max:100 | min:10, max:50 | Standard production |
| **Enterprise** | 50-200 | min:50, max:200 | min:25, max:100 | Large-scale deployment |

### Connection Pool Tuning Script

```bash
#!/bin/bash
# tune_connection_pool.sh - Dynamic pool sizing based on load

# Monitor current utilization
get_pool_stats() {
    curl -s http://localhost:8000/health/status | \
        jq '.connection_pool.pool_utilization'
}

# Adjust pool size based on utilization
adjust_pool() {
    local utilization=$(get_pool_stats)
    local current_max=$POOL_MAX_SIZE

    if (( $(echo "$utilization > 0.8" | bc -l) )); then
        # Increase pool size by 20%
        new_max=$(echo "$current_max * 1.2" | bc)
        export POOL_MAX_SIZE=$new_max
        echo "Increased pool to $new_max (utilization: $utilization)"

    elif (( $(echo "$utilization < 0.3" | bc -l) )); then
        # Decrease pool size by 10%
        new_max=$(echo "$current_max * 0.9" | bc)
        export POOL_MAX_SIZE=$new_max
        echo "Decreased pool to $new_max (utilization: $utilization)"
    fi
}

# Run adjustment loop
while true; do
    adjust_pool
    sleep 60  # Check every minute
done
```

## Index Optimization Strategies

### Current Index Analysis

```sql
-- Analyze existing indexes
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    idx_scan AS index_scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;
```

### GIN Index Optimization for JSONB

```sql
-- Optimize GIN indexes for entity queries
-- Current index
CREATE INDEX idx_entities_data_gin ON entities USING gin(data);

-- Optimized with specific paths for common queries
CREATE INDEX idx_entities_status ON entities USING gin((data->'status'));
CREATE INDEX idx_entities_version ON entities USING gin((data->'version'));
CREATE INDEX idx_entities_tags ON entities USING gin(tags);

-- Partial indexes for filtered queries
CREATE INDEX idx_entities_active ON entities (entity_type, name)
    WHERE deleted_at IS NULL;

-- Multi-column index for common query pattern
CREATE INDEX idx_entities_type_name ON entities (entity_type, name)
    WHERE deleted_at IS NULL;
```

### Embedding Vector Index Optimization

```sql
-- Optimize pgvector indexes for similarity search
-- Current index
CREATE INDEX idx_chunks_embedding ON code_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- Optimized with tuned parameters
-- lists = sqrt(number_of_rows) for optimal performance
SELECT COUNT(*) FROM code_chunks; -- Example: 100,000 rows

CREATE INDEX idx_chunks_embedding_optimized ON code_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 316);  -- sqrt(100000) ≈ 316

-- Alternative: HNSW for better recall
CREATE INDEX idx_chunks_embedding_hnsw ON code_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

### Index Maintenance Schedule

```sql
-- Regular maintenance tasks
-- Run weekly during low-traffic periods

-- Update statistics
ANALYZE code_chunks;
ANALYZE entities;
ANALYZE work_items;

-- Reindex for bloat reduction (monthly)
REINDEX INDEX CONCURRENTLY idx_chunks_embedding;
REINDEX INDEX CONCURRENTLY idx_entities_data_gin;

-- Monitor index bloat
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
    ROUND(100 * (pg_relation_size(indexrelid) - pg_relation_size(indexrelid::regclass)) /
          pg_relation_size(indexrelid)::numeric, 2) AS bloat_percent
FROM pg_stat_user_indexes
WHERE pg_relation_size(indexrelid) > 1000000  -- Only indexes > 1MB
ORDER BY bloat_percent DESC;
```

## Caching Strategies

### 1. Embedding Cache Implementation

```python
class EmbeddingCache:
    """LRU cache for embedding generation results."""

    def __init__(self, max_size: int = 10000, ttl_seconds: int = 3600):
        self.cache = {}
        self.max_size = max_size
        self.ttl = ttl_seconds
        self.access_count = defaultdict(int)
        self.last_access = {}

    def get_cache_key(self, text: str, model: str) -> str:
        """Generate cache key from text and model."""
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        return f"{model}:{text_hash}"

    async def get_or_generate(
        self,
        text: str,
        model: str,
        generate_func: Callable
    ) -> np.ndarray:
        """Get from cache or generate new embedding."""
        key = self.get_cache_key(text, model)

        # Check cache
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry["timestamp"] < self.ttl:
                self.access_count[key] += 1
                self.last_access[key] = time.time()
                return entry["embedding"]

        # Generate new embedding
        embedding = await generate_func(text, model)

        # Store in cache (with LRU eviction)
        if len(self.cache) >= self.max_size:
            self._evict_lru()

        self.cache[key] = {
            "embedding": embedding,
            "timestamp": time.time()
        }

        return embedding

    def _evict_lru(self):
        """Evict least recently used entry."""
        lru_key = min(self.last_access, key=self.last_access.get)
        del self.cache[lru_key]
        del self.last_access[lru_key]
        del self.access_count[lru_key]

# Usage
embedding_cache = EmbeddingCache(max_size=10000, ttl_seconds=3600)

async def get_embedding_with_cache(text: str) -> np.ndarray:
    return await embedding_cache.get_or_generate(
        text=text,
        model="nomic-embed-text",
        generate_func=generate_embedding
    )
```

### 2. Query Result Cache

```python
class QueryResultCache:
    """Redis-backed cache for search results."""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis = aioredis.from_url(redis_url)
        self.default_ttl = 300  # 5 minutes

    def get_cache_key(self, query: str, filters: dict) -> str:
        """Generate cache key from query and filters."""
        query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
        filter_hash = hashlib.sha256(
            json.dumps(filters, sort_keys=True).encode()
        ).hexdigest()[:16]
        return f"search:{query_hash}:{filter_hash}"

    async def get(self, query: str, filters: dict) -> Optional[List[dict]]:
        """Get cached search results."""
        key = self.get_cache_key(query, filters)
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)
        return None

    async def set(
        self,
        query: str,
        filters: dict,
        results: List[dict],
        ttl: int = None
    ):
        """Cache search results."""
        key = self.get_cache_key(query, filters)
        ttl = ttl or self.default_ttl
        await self.redis.setex(
            key,
            ttl,
            json.dumps(results)
        )

# Integration with search endpoint
async def search_with_cache(query: str, filters: dict) -> List[dict]:
    # Try cache first
    cached_results = await query_cache.get(query, filters)
    if cached_results:
        return cached_results

    # Perform actual search
    results = await perform_search(query, filters)

    # Cache results
    await query_cache.set(query, filters, results)

    return results
```

### 3. Connection Pool Warmup

```python
class PoolWarmupStrategy:
    """Pre-warm connection pools on startup."""

    @staticmethod
    async def warmup_pool(pool_manager: ConnectionPoolManager):
        """Pre-establish minimum connections."""
        tasks = []

        # Create min_size connections
        for _ in range(pool_manager.config.min_size):
            tasks.append(pool_manager._create_connection())

        # Execute in parallel
        connections = await asyncio.gather(*tasks)

        # Return connections to pool
        for conn in connections:
            await pool_manager._release_connection(conn)

        logger.info(f"Warmed up {len(connections)} connections")

# Application startup
async def startup():
    # Initialize pool
    pool_manager = ConnectionPoolManager(config)

    # Warm up connections
    await PoolWarmupStrategy.warmup_pool(pool_manager)

    # Pool is now pre-warmed and ready
    return pool_manager
```

## Query Optimization

### 1. Query Analysis Tools

```sql
-- Enable query performance insights
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET pg_stat_statements.track = 'all';
ALTER SYSTEM SET pg_stat_statements.max = 10000;

-- Analyze slow queries
SELECT
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    stddev_exec_time,
    rows,
    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements
WHERE mean_exec_time > 100  -- Queries slower than 100ms
ORDER BY mean_exec_time DESC
LIMIT 20;
```

### 2. Common Query Optimizations

```python
# BEFORE: Inefficient N+1 query pattern
async def get_work_items_with_children():
    items = await db.fetch("SELECT * FROM work_items WHERE parent_id IS NULL")
    for item in items:
        item['children'] = await db.fetch(
            "SELECT * FROM work_items WHERE parent_id = $1",
            item['id']
        )
    return items

# AFTER: Single query with JOIN
async def get_work_items_with_children_optimized():
    query = """
        WITH RECURSIVE item_tree AS (
            SELECT *, 0 as level
            FROM work_items
            WHERE parent_id IS NULL

            UNION ALL

            SELECT w.*, t.level + 1
            FROM work_items w
            JOIN item_tree t ON w.parent_id = t.id
        )
        SELECT * FROM item_tree
        ORDER BY level, created_at;
    """
    return await db.fetch(query)
```

### 3. Batch Processing Optimization

```python
class BatchProcessor:
    """Optimize bulk operations with batching."""

    @staticmethod
    async def batch_insert_chunks(chunks: List[dict], batch_size: int = 1000):
        """Insert chunks in optimized batches."""
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]

            # Build multi-value insert
            values = []
            params = []
            for j, chunk in enumerate(batch):
                offset = j * 5
                values.append(f"(${offset+1}, ${offset+2}, ${offset+3}, ${offset+4}, ${offset+5})")
                params.extend([
                    chunk['file_id'],
                    chunk['content'],
                    chunk['embedding'],
                    chunk['start_line'],
                    chunk['end_line']
                ])

            query = f"""
                INSERT INTO code_chunks
                (file_id, content, embedding, start_line, end_line)
                VALUES {','.join(values)}
                ON CONFLICT DO NOTHING
            """

            await db.execute(query, *params)

    @staticmethod
    async def parallel_embedding_generation(
        texts: List[str],
        concurrency: int = 10
    ) -> List[np.ndarray]:
        """Generate embeddings with controlled concurrency."""
        semaphore = asyncio.Semaphore(concurrency)

        async def generate_with_limit(text: str) -> np.ndarray:
            async with semaphore:
                return await generate_embedding(text)

        return await asyncio.gather(*[
            generate_with_limit(text) for text in texts
        ])
```

## Production Tuning Checklist

### Pre-Deployment

- [ ] **Database Configuration**
  ```sql
  -- PostgreSQL tuning for MCP workload
  ALTER SYSTEM SET max_connections = 300;
  ALTER SYSTEM SET shared_buffers = '2GB';
  ALTER SYSTEM SET effective_cache_size = '6GB';
  ALTER SYSTEM SET maintenance_work_mem = '512MB';
  ALTER SYSTEM SET work_mem = '16MB';
  ALTER SYSTEM SET random_page_cost = 1.1;  -- For SSD
  ALTER SYSTEM SET effective_io_concurrency = 200;  -- For SSD
  ALTER SYSTEM SET wal_buffers = '16MB';
  ALTER SYSTEM SET checkpoint_completion_target = 0.9;
  ```

- [ ] **Connection Pool Settings**
  ```yaml
  # Environment variables
  POOL_MIN_SIZE: 20
  POOL_MAX_SIZE: 100
  POOL_TIMEOUT: 30
  POOL_COMMAND_TIMEOUT: 5
  POOL_MAX_INACTIVE_CONNECTION_LIFETIME: 300
  ```

- [ ] **Index Creation**
  ```sql
  -- Essential indexes
  CREATE INDEX CONCURRENTLY idx_chunks_file_id ON code_chunks(file_id);
  CREATE INDEX CONCURRENTLY idx_chunks_embedding ON code_chunks USING ivfflat (embedding);
  CREATE INDEX CONCURRENTLY idx_entities_type_name ON entities(entity_type, name);
  CREATE INDEX CONCURRENTLY idx_work_items_path ON work_items USING gin(materialized_path);
  ```

### Post-Deployment Monitoring

- [ ] **Performance Baseline**
  ```bash
  # Capture initial metrics
  curl http://localhost:8000/metrics > baseline_metrics.txt
  python scripts/run_benchmarks.sh > baseline_performance.json
  ```

- [ ] **Query Performance**
  ```sql
  -- Monitor slow queries
  SELECT * FROM pg_stat_statements
  WHERE mean_exec_time > 100
  ORDER BY mean_exec_time DESC;
  ```

- [ ] **Connection Pool Health**
  ```bash
  # Monitor pool utilization
  watch -n 5 'curl -s http://localhost:8000/health/status | jq .connection_pool'
  ```

- [ ] **Resource Usage**
  ```bash
  # Monitor memory and CPU
  htop -p $(pgrep -f "codebase-mcp")
  ```

### Optimization Schedule

| Frequency | Task | Command/Action |
|-----------|------|----------------|
| **Hourly** | Check pool utilization | `curl /health/status` |
| **Daily** | Analyze slow queries | `pg_stat_statements` review |
| **Weekly** | Update table statistics | `ANALYZE` all tables |
| **Monthly** | Reindex for bloat | `REINDEX CONCURRENTLY` |
| **Quarterly** | Review and adjust pool sizes | Load analysis |

## Advanced Tuning Techniques

### 1. Prepared Statement Optimization

```python
class PreparedStatementCache:
    """Cache prepared statements for repeated queries."""

    def __init__(self, max_statements: int = 100):
        self.statements = {}
        self.max_statements = max_statements

    async def execute(self, name: str, query: str, *args):
        """Execute query with prepared statement."""
        if name not in self.statements:
            if len(self.statements) >= self.max_statements:
                # Evict oldest statement
                oldest = min(self.statements, key=lambda k: self.statements[k]['used'])
                await self.statements[oldest]['stmt'].close()
                del self.statements[oldest]

            # Prepare new statement
            stmt = await connection.prepare(query)
            self.statements[name] = {
                'stmt': stmt,
                'used': time.time()
            }

        # Execute prepared statement
        stmt = self.statements[name]['stmt']
        self.statements[name]['used'] = time.time()
        return await stmt.fetch(*args)
```

### 2. Adaptive Query Optimization

```python
class AdaptiveQueryOptimizer:
    """Dynamically adjust query strategies based on performance."""

    def __init__(self):
        self.query_stats = defaultdict(lambda: {'times': [], 'strategy': 'default'})

    async def execute_adaptive(self, query_id: str, strategies: dict):
        """Execute query with adaptive strategy selection."""
        stats = self.query_stats[query_id]

        # Select strategy based on past performance
        if len(stats['times']) > 10:
            avg_time = sum(stats['times'][-10:]) / 10
            if avg_time > 500:  # Slow query
                stats['strategy'] = 'optimized'
            elif avg_time < 50:  # Fast query
                stats['strategy'] = 'simple'

        # Execute with selected strategy
        strategy = strategies[stats['strategy']]
        start = time.time()
        result = await strategy()
        elapsed = (time.time() - start) * 1000

        # Update statistics
        stats['times'].append(elapsed)
        if len(stats['times']) > 100:
            stats['times'] = stats['times'][-50:]  # Keep last 50

        return result
```

## Performance Monitoring Dashboard

```yaml
# Grafana dashboard for performance monitoring
dashboard:
  title: "MCP Performance Tuning"
  panels:
    - title: "Query Performance"
      queries:
        - "histogram_quantile(0.95, query_duration_seconds)"
        - "rate(slow_queries_total[5m])"

    - title: "Connection Pool"
      queries:
        - "pool_connections{state='active'} / pool_connections{state='total'}"
        - "pool_wait_time_seconds"

    - title: "Cache Hit Rates"
      queries:
        - "cache_hits / (cache_hits + cache_misses)"
        - "embedding_cache_size"

    - title: "Index Usage"
      queries:
        - "index_scans / (index_scans + seq_scans)"
        - "index_bloat_percent"
```

## References

- [Performance Validation Report](../performance/validation-report.md)
- [Connection Pool Manager](../../src/connection_pool/manager.py)
- [Database Schema](../../src/database/schema.sql)
- [Constitutional Principles](../../.specify/memory/constitution.md)
- [PostgreSQL Tuning Guide](https://wiki.postgresql.org/wiki/Tuning_Your_PostgreSQL_Server)