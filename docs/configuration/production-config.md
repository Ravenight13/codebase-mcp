# Production Configuration Guide

**Version**: v2.0
**Audience**: System administrators deploying codebase-mcp to production
**Purpose**: This guide provides comprehensive configuration information for deploying and tuning codebase-mcp v2.0 in production environments, with emphasis on multi-project workspace isolation and connection pool management.

---

## Table of Contents

- [Overview](#overview)
- [Environment Variables Reference](#environment-variables-reference)
  - [Core Configuration](#core-configuration)
  - [Multi-Project Configuration](#multi-project-configuration)
  - [workflow-mcp Integration](#workflow-mcp-integration)
- [Connection Pool Tuning](#connection-pool-tuning)
  - [Understanding the Calculation](#understanding-the-calculation)
  - [Example Scenarios](#example-scenarios)
  - [PostgreSQL max_connections Requirement](#postgresql-max_connections-requirement)
  - [Configuration Validation](#configuration-validation)
  - [Tuning MAX_PROJECTS](#tuning-max_projects)
  - [Tuning MAX_CONNECTIONS_PER_POOL](#tuning-max_connections_per_pool)
  - [Recommendations by Deployment Size](#recommendations-by-deployment-size)
- [PostgreSQL Performance Tuning](#postgresql-performance-tuning)
- [Monitoring and Observability](#monitoring-and-observability)
- [Security Configuration](#security-configuration)
- [Troubleshooting](#troubleshooting)

---

## Overview

Codebase-mcp v2.0 introduces **multi-project workspace isolation** with database-per-project architecture. Each project workspace maintains its own PostgreSQL connection pool, which requires careful planning to avoid connection exhaustion.

**Key Configuration Areas**:
1. **Environment Variables**: Database connections, Ollama integration, logging
2. **Connection Pool Management**: Per-project pools, PostgreSQL capacity planning
3. **Performance Tuning**: PostgreSQL settings for optimal semantic search performance
4. **Monitoring**: Connection pool metrics, query performance tracking

**Prerequisites**:
- PostgreSQL 14+ with admin access to configure max_connections
- Ollama server running with embedding model available
- Understanding of expected concurrent users and project count

---

## Environment Variables Reference

Codebase-mcp uses environment variables for all configuration. Variables can be set via `.env` file, shell exports, or container environment.

### Core Configuration

Core variables control database connectivity, embedding generation, and logging. These are the foundational settings required for basic operation.

| Variable | Required | Default | Description | Example |
|----------|----------|---------|-------------|---------|
| `DATABASE_URL` | **Required** | *(none)* | PostgreSQL connection URL with asyncpg driver. Format: `postgresql+asyncpg://user:password@host:port/database`. Must use `asyncpg` driver for async operations. | `postgresql+asyncpg://user:password@localhost:5432/codebase_mcp` |
| `OLLAMA_BASE_URL` | Optional | `http://localhost:11434` | Ollama API base URL for embedding generation. Must be accessible from the server. The Ollama server must be running with the embedding model pulled. | `http://localhost:11434` |
| `OLLAMA_EMBEDDING_MODEL` | Optional | `nomic-embed-text` | Ollama embedding model name. Must be pulled locally using `ollama pull <model>` before use. | `nomic-embed-text` |
| `EMBEDDING_BATCH_SIZE` | Optional | `50` | Number of text chunks to embed per Ollama API request. Larger batches improve throughput but increase latency. Valid range: 1-1000. Recommended: 50-100 for optimal performance. | `50` |
| `LOG_LEVEL` | Optional | `INFO` | Logging verbosity level. Valid values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. | `INFO` |
| `LOG_FILE` | Optional | `/tmp/codebase-mcp.log` | File path for structured JSON logs. CRITICAL: Never log to stdout/stderr (MCP protocol violation). | `/tmp/codebase-mcp.log` |

**Configuration Example (Core Only)**:
```bash
# Minimal production configuration
DATABASE_URL=postgresql+asyncpg://codebase:password@db.internal:5432/codebase_mcp
OLLAMA_BASE_URL=http://ollama.internal:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
LOG_LEVEL=INFO
LOG_FILE=/var/log/codebase-mcp/server.log
```

### Multi-Project Configuration

Multi-project variables control workspace isolation and connection pool behavior. These settings determine how many concurrent projects can be active and how connections are allocated.

| Variable | Required | Default | Description | Example |
|----------|----------|---------|-------------|---------|
| `MAX_PROJECTS` | Optional | `10` | Maximum number of concurrent project workspaces. Each project maintains its own database connection pool. Higher values increase PostgreSQL connection requirements. See [Connection Pool Tuning](#connection-pool-tuning) for capacity planning. | `10` |
| `MAX_CONNECTIONS_PER_POOL` | Optional | `20` | Maximum connections allocated per project database pool. Higher values support more concurrent operations per project but increase total PostgreSQL connection usage. Valid range: 5-50. | `20` |
| `PROJECT_POOL_TIMEOUT` | Optional | `30.0` | Timeout for acquiring connection from project pool (seconds). If timeout exceeded, operation fails with DATABASE_ERROR. Valid range: 5.0-120.0. | `30.0` |
| `MAX_CONCURRENT_REQUESTS` | Optional | `10` | Maximum concurrent AI assistant connections across all projects. Limits total system load. Valid range: 1-100. | `10` |
| `DB_POOL_SIZE` | Optional | `20` | SQLAlchemy connection pool size per database (v1.x compatibility). In v2.0, use `MAX_CONNECTIONS_PER_POOL` instead. This setting applies per-database in multi-project setups. | `20` |
| `DB_MAX_OVERFLOW` | Optional | `10` | Maximum overflow connections beyond pool_size per database. Handles traffic spikes. In v2.0, overflow connections are per-workspace. Valid range: 0-20. | `10` |

**Configuration Example (Multi-Project)**:
```bash
# Production configuration for 10 concurrent projects
MAX_PROJECTS=10
MAX_CONNECTIONS_PER_POOL=20
PROJECT_POOL_TIMEOUT=30.0
MAX_CONCURRENT_REQUESTS=20
```

**Connection Requirements**:
```
Total PostgreSQL connections required = (MAX_PROJECTS × MAX_CONNECTIONS_PER_POOL) + buffer
Example: (10 × 20) + 30 = 230 connections
```

See [Connection Pool Tuning](#connection-pool-tuning) for detailed capacity planning.

### workflow-mcp Integration

workflow-mcp integration variables enable automatic project detection when codebase-mcp is used alongside workflow-mcp. These settings are **optional** - codebase-mcp functions independently without workflow-mcp.

| Variable | Required | Default | Description | Example |
|----------|----------|---------|-------------|---------|
| `WORKFLOW_MCP_URL` | Optional | *(none)* | workflow-mcp server URL for automatic project detection. If not set, multi-project workspace features fall back to default workspace. Enables automatic `project_id` resolution from repository paths. | `http://localhost:8000` |
| `WORKFLOW_MCP_TIMEOUT` | Optional | `1.0` | Timeout for workflow-mcp queries (seconds). Should be low to avoid blocking indexing operations. If timeout exceeded, falls back to default workspace. Valid range: 0.1-5.0. | `1.0` |
| `WORKFLOW_MCP_CACHE_TTL` | Optional | `60` | Cache TTL for workflow-mcp responses (seconds). Reduces query overhead for repeated repository checks. Cached responses are invalidated after TTL expires. Valid range: 10-300. | `60` |

**Configuration Example (workflow-mcp Integration)**:
```bash
# Optional workflow-mcp integration
WORKFLOW_MCP_URL=http://workflow-mcp.internal:8000
WORKFLOW_MCP_TIMEOUT=2.0
WORKFLOW_MCP_CACHE_TTL=120
```

**Behavior Without workflow-mcp**:
- `project_id` parameter must be provided explicitly in tool calls
- If `project_id` omitted, operations use default workspace (`project_default`)
- No automatic project detection from repository paths
- All other functionality remains operational

**Behavior With workflow-mcp**:
- `project_id` automatically resolved from repository path
- Falls back to default workspace if:
  - workflow-mcp unreachable
  - Query times out (exceeds `WORKFLOW_MCP_TIMEOUT`)
  - Repository not associated with workflow-mcp project
- Cached responses reduce query overhead for repeated checks

---

## Connection Pool Tuning

Connection pool tuning is critical for production deployments with multiple concurrent projects. Insufficient connections cause operation failures; excessive connections waste resources.

### Understanding the Calculation

The connection pool calculation determines the minimum PostgreSQL `max_connections` required for codebase-mcp to function correctly.

**Formula**:
```
Required max_connections = (MAX_PROJECTS × MAX_CONNECTIONS_PER_POOL) + buffer
```

**Components**:
- **MAX_PROJECTS**: Maximum number of concurrent project workspaces
- **MAX_CONNECTIONS_PER_POOL**: Connections allocated per project database pool
- **buffer**: Additional connections for system overhead (recommended: 20-30)

**Buffer Explanation**:

The buffer accounts for:
- **System processes**: PostgreSQL background workers (autovacuum, stats collector, WAL writer)
- **Admin connections**: Superuser-reserved connections for maintenance and troubleshooting
- **Registry database**: Connections for the central registry database pool
- **Overhead**: Temporary connections during database operations
- **Safety margin**: Prevents connection exhaustion under peak load

A buffer of 20-30 connections is recommended for production deployments. For high-availability setups or frequent administrative access, consider a buffer of 30-50.

**Example**:
```
Scenario: 10 projects, 20 connections per pool
Calculation: (10 × 20) + 25 = 225
PostgreSQL config: max_connections = 225
```

### Example Scenarios

| Deployment Size | MAX_PROJECTS | MAX_CONNECTIONS_PER_POOL | Project Connections | Buffer | **Required max_connections** |
|----------------|--------------|--------------------------|---------------------|--------|------------------------------|
| **Small**      | 5            | 10                       | 50                  | 20     | **70**                       |
| **Medium**     | 10           | 15                       | 150                 | 25     | **175**                      |
| **Large**      | 20           | 20                       | 400                 | 30     | **430**                      |
| **Enterprise** | 50           | 20                       | 1000                | 50     | **1050**                     |
| **Minimal**    | 2            | 5                        | 10                  | 15     | **25**                       |

**Scenario Details**:

#### Small Deployment (5 projects, 70 connections)
**Use case**: Development team, low-concurrency workloads
- **Calculation**: (5 × 10) + 20 = 70
- **PostgreSQL config**: `max_connections = 70`
- **Per-project capacity**: 10 concurrent operations per workspace
- **Suitable for**: 2-5 developers, non-production environments

#### Medium Deployment (10 projects, 175 connections)
**Use case**: Mid-sized team, moderate concurrency
- **Calculation**: (10 × 15) + 25 = 175
- **PostgreSQL config**: `max_connections = 175`
- **Per-project capacity**: 15 concurrent operations per workspace
- **Suitable for**: 10-20 developers, staging + production environments

#### Large Deployment (20 projects, 430 connections)
**Use case**: Large organization, high concurrency
- **Calculation**: (20 × 20) + 30 = 430
- **PostgreSQL config**: `max_connections = 430`
- **Per-project capacity**: 20 concurrent operations per workspace
- **Suitable for**: 30-50 developers, multiple production workspaces

#### Enterprise Deployment (50 projects, 1050 connections)
**Use case**: Multi-tenant or large-scale deployments
- **Calculation**: (50 × 20) + 50 = 1050
- **PostgreSQL config**: `max_connections = 1050`
- **Per-project capacity**: 20 concurrent operations per workspace
- **Suitable for**: 100+ developers, multi-tenant SaaS, high-availability clusters

#### Minimal Deployment (2 projects, 25 connections)
**Use case**: Personal use, single developer
- **Calculation**: (2 × 5) + 15 = 25
- **PostgreSQL config**: `max_connections = 25`
- **Per-project capacity**: 5 concurrent operations per workspace
- **Suitable for**: Individual developers, experimentation, low-resource environments

### PostgreSQL max_connections Requirement

After calculating the required connection count, configure PostgreSQL `max_connections` to accommodate codebase-mcp's needs.

**Step 1: Calculate Required Connections**

Use the formula:
```
Required max_connections = (MAX_PROJECTS × MAX_CONNECTIONS_PER_POOL) + buffer
```

**Step 2: Configure PostgreSQL**

Edit `postgresql.conf` or use `ALTER SYSTEM`:

```sql
-- Set max_connections to calculated value
ALTER SYSTEM SET max_connections = 225;

-- Restart PostgreSQL to apply
-- systemctl restart postgresql
```

**Step 3: Verify Configuration**

```sql
SHOW max_connections;
-- Expected output: 225
```

**Warnings**:

**Insufficient Connections** - If PostgreSQL `max_connections` is set below the required value, you will encounter:

1. **Connection Pool Exhaustion**
   ```
   ERROR: remaining connection slots are reserved for non-replication superuser connections
   ```
   - Projects fail to initialize connection pools
   - MCP operations fail with `DATABASE_ERROR`
   - Server becomes unresponsive under load

2. **Performance Degradation**
   - Connection pool contention causes timeouts
   - Queries queue waiting for available connections
   - P95 latency exceeds constitutional guarantees (<100ms entity queries, <500ms semantic search)

3. **Cascading Failures**
   - New project creation fails during database provisioning
   - Active projects experience intermittent errors
   - Client operations timeout while waiting for connections

**Resource Considerations**:

- **Memory**: Each connection consumes ~2-10MB RAM
  - Example: 1000 connections = ~2-10GB RAM for PostgreSQL alone
- **File Descriptors**: PostgreSQL requires ~2 file descriptors per connection
  - Example: 1000 connections requires `ulimit -n` ≥ 2500
- **CPU**: More connections increase context switching overhead

**Best Practice**: Always set `max_connections` 10-20% higher than calculated minimum to provide safety margin.

### Configuration Validation

After configuring connection pools, validate the setup:

**1. Check PostgreSQL Setting**:
```sql
SHOW max_connections;
-- Verify value matches calculated requirement
```

**2. Verify Health Check**:
```bash
# Use workflow-mcp health_check tool if integrated
# Inspect database.registry.pool and database.active_project.pool
```

**3. Test Project Creation**:
```bash
# Create test project and verify connection pool initializes
# Check logs for connection pool initialization messages
```

**4. Monitor Connection Usage**:
```sql
-- Check active connections
SELECT count(*) FROM pg_stat_activity;

-- Check connections per database
SELECT datname, count(*)
FROM pg_stat_activity
WHERE datname LIKE 'codebase_%'
GROUP BY datname;
```

**5. Load Test** (staging environment):
- Create `MAX_PROJECTS` workspaces
- Execute concurrent operations on each project
- Monitor connection pool statistics
- Verify no connection exhaustion errors

### Tuning MAX_PROJECTS

`MAX_PROJECTS` determines how many concurrent project workspaces can be active simultaneously. Tuning this value involves tradeoffs.

**Increasing MAX_PROJECTS**:

**Pros**:
- More concurrent projects supported
- Better multi-tenancy support
- Reduced LRU eviction frequency (projects stay cached longer)

**Cons**:
- Higher PostgreSQL connection requirements
- Increased memory usage for connection pools
- Longer startup time (more pools to initialize)
- Higher risk of connection exhaustion if PostgreSQL max_connections insufficient

**Decreasing MAX_PROJECTS**:

**Pros**:
- Lower PostgreSQL connection requirements
- Reduced memory footprint
- Faster startup time
- Lower risk of connection exhaustion

**Cons**:
- Frequent LRU eviction for active projects (performance impact)
- Limited multi-tenancy capacity
- Projects may be evicted and re-initialized multiple times per session

**Recommendations**:

1. **Calculate based on active projects**: Set `MAX_PROJECTS` to expected number of concurrently active projects + 20% buffer
2. **Monitor eviction rate**: If projects are frequently evicted (check logs), increase `MAX_PROJECTS`
3. **Start conservative**: Begin with `MAX_PROJECTS=10`, increase if eviction rate high
4. **Consider workload patterns**:
   - Sustained concurrent work across many projects → Higher `MAX_PROJECTS`
   - Sequential work across projects → Lower `MAX_PROJECTS` acceptable

**Example Configuration**:

```bash
# Development/small team (2-5 concurrent projects)
MAX_PROJECTS=5

# Production/medium team (5-15 concurrent projects)
MAX_PROJECTS=10

# Enterprise/large team (15-30 concurrent projects)
MAX_PROJECTS=20

# Multi-tenant SaaS (30+ concurrent projects)
MAX_PROJECTS=50
```

### Tuning MAX_CONNECTIONS_PER_POOL

`MAX_CONNECTIONS_PER_POOL` determines how many concurrent operations each project workspace can handle. Tuning this value affects per-project concurrency.

**Increasing MAX_CONNECTIONS_PER_POOL**:

**Pros**:
- More concurrent operations per project (higher throughput)
- Reduced connection contention within project
- Better support for multiple AI assistants per project

**Cons**:
- Higher total PostgreSQL connection requirements
- More memory usage per project pool
- Increased risk of connection exhaustion

**Decreasing MAX_CONNECTIONS_PER_POOL**:

**Pros**:
- Lower total PostgreSQL connection requirements
- Reduced memory footprint per project
- More projects can fit within PostgreSQL connection limit

**Cons**:
- Lower per-project concurrency (operations may queue)
- Connection contention under load
- Operations may timeout waiting for connections

**Recommendations**:

1. **Calculate based on concurrent AI assistants**: Each active AI assistant requires 1-2 connections
   - Example: 5 concurrent assistants → `MAX_CONNECTIONS_PER_POOL=10-15`
2. **Consider query complexity**: Complex semantic searches may hold connections longer
3. **Start with 15-20**: Good balance for most workloads, adjust based on monitoring
4. **Monitor pool utilization**: If pools frequently saturated (check logs), increase per-pool connections

**Example Configuration**:

```bash
# Low concurrency (1-2 assistants per project)
MAX_CONNECTIONS_PER_POOL=10

# Medium concurrency (2-5 assistants per project)
MAX_CONNECTIONS_PER_POOL=15

# High concurrency (5-10 assistants per project)
MAX_CONNECTIONS_PER_POOL=20

# Very high concurrency (10+ assistants per project)
MAX_CONNECTIONS_PER_POOL=30
```

**Tradeoff Example**:

```
Scenario A: MAX_PROJECTS=10, MAX_CONNECTIONS_PER_POOL=10
- Total connections: 10 × 10 = 100
- Per-project capacity: 10 concurrent operations
- Good for: Many projects, low per-project concurrency

Scenario B: MAX_PROJECTS=5, MAX_CONNECTIONS_PER_POOL=20
- Total connections: 5 × 20 = 100
- Per-project capacity: 20 concurrent operations
- Good for: Few projects, high per-project concurrency
```

### Recommendations by Deployment Size

**Small Deployment (2-5 developers)**:
```bash
MAX_PROJECTS=5
MAX_CONNECTIONS_PER_POOL=10
# Required max_connections = (5 × 10) + 20 = 70
```

**Medium Deployment (10-20 developers)**:
```bash
MAX_PROJECTS=10
MAX_CONNECTIONS_PER_POOL=15
# Required max_connections = (10 × 15) + 25 = 175
```

**Large Deployment (30-50 developers)**:
```bash
MAX_PROJECTS=20
MAX_CONNECTIONS_PER_POOL=20
# Required max_connections = (20 × 20) + 30 = 430
```

**Enterprise Deployment (100+ developers)**:
```bash
MAX_PROJECTS=50
MAX_CONNECTIONS_PER_POOL=20
# Required max_connections = (50 × 20) + 50 = 1050
```

**Adjust based on**:
- Actual concurrent usage patterns (monitor logs)
- PostgreSQL server resources (RAM, CPU)
- Workload characteristics (query complexity, operation duration)
- Performance requirements (target latency, throughput)

---

## PostgreSQL Configuration

Optimize PostgreSQL settings for codebase-mcp workload characteristics: embedding storage (JSONB with pgvector), frequent INSERT operations during indexing, and high-volume similarity searches.

### Production Tuning Parameters

Edit `postgresql.conf` (typically in `/etc/postgresql/<version>/main/postgresql.conf` or `/var/lib/postgresql/data/postgresql.conf`):

```ini
# postgresql.conf

# Connection Management (calculated based on deployment size)
max_connections = 225  # Adjust based on connection calculation from formula above

# Memory Configuration
shared_buffers = 4GB              # 25% of system RAM (for 16GB system)
effective_cache_size = 12GB       # 50-75% of system RAM
work_mem = 50MB                   # RAM / max_connections / 2 (e.g., 16GB / 200 / 2 = 40MB, round up to 50MB)
maintenance_work_mem = 1GB        # RAM / 16 (e.g., 16GB / 16 = 1GB)

# Checkpoint Settings
checkpoint_completion_target = 0.9  # Spread checkpoints over 90% of checkpoint interval

# Write-Ahead Log (WAL)
wal_buffers = 16MB                # 16MB for write-heavy workloads

# Query Planner Settings
random_page_cost = 1.1            # SSD-optimized (1.1-1.5); HDD use 4.0
effective_io_concurrency = 200    # SSD concurrent I/O operations

# Parallel Query Execution
max_parallel_workers_per_gather = 4
max_parallel_workers = 8
max_wal_size = 2GB
```

**Apply Settings Dynamically** (requires superuser):

```sql
ALTER SYSTEM SET shared_buffers = '4GB';
ALTER SYSTEM SET effective_cache_size = '12GB';
ALTER SYSTEM SET work_mem = '50MB';
ALTER SYSTEM SET maintenance_work_mem = '1GB';
ALTER SYSTEM SET random_page_cost = 1.1;

-- Reload configuration (for non-restart settings)
SELECT pg_reload_conf();

-- Verify changes applied
SHOW shared_buffers;
SHOW effective_cache_size;
```

**Restart Required Settings**:

Some settings (e.g., `shared_buffers`, `max_connections`) require PostgreSQL restart:

```bash
# Restart PostgreSQL (systemd)
sudo systemctl restart postgresql

# Restart PostgreSQL (Docker)
docker restart codebase-postgres
```

### Rationale for Settings

#### max_connections
**Why it matters for codebase-mcp**: Determines how many project connection pools can be active simultaneously. Under-provisioning causes "too many connections" errors; over-provisioning wastes memory (~2-5MB per connection).

**Indexing operations**: Multiple projects may index repositories concurrently, each requiring dedicated connections.

**Search operations**: Concurrent semantic search queries across different projects require isolated connection pools.

**Configuration**: Set based on connection calculation formula: `(MAX_PROJECTS × MAX_CONNECTIONS_PER_POOL) + buffer`.

#### shared_buffers
**Why it matters for codebase-mcp**: PostgreSQL's main data cache. Higher values reduce disk I/O by caching frequently accessed data.

**Indexing operations**: Caches code chunk metadata during batch INSERT operations, improving indexing throughput.

**Search operations**: Caches embedding vectors (pgvector data) for similarity searches, dramatically improving p95 latency.

**Embedding storage requirements**: Large repositories with 100K+ chunks benefit significantly from larger shared_buffers (8GB+).

**Configuration**: 25% of system RAM (e.g., 4GB for 16GB system, 8GB for 32GB system).

#### effective_cache_size
**Why it matters for codebase-mcp**: Informs query planner about total memory available for caching (OS cache + shared_buffers). Influences whether PostgreSQL uses index scans or sequential scans.

**Indexing operations**: Query planner decisions during bulk inserts affect overall indexing performance.

**Search operations**: Directly impacts pgvector index usage vs. sequential scans. Higher values encourage index usage (faster semantic search).

**Configuration**: 50-75% of system RAM (e.g., 12GB for 16GB system).

#### work_mem
**Why it matters for codebase-mcp**: Memory per sort/hash operation. Too low causes disk-based sorting (slow); too high risks out-of-memory when many concurrent operations run.

**Indexing operations**: Used for sorting during GIN index creation on embeddings column. Larger values speed up index builds.

**Search operations**: Used for hash joins in complex similarity queries with filters (file_type, directory).

**Configuration**: `RAM / max_connections / 2` (e.g., 16GB / 200 / 2 = 40MB, round up to 50MB). For very large repositories, increase to 128MB.

#### maintenance_work_mem
**Why it matters for codebase-mcp**: Memory for maintenance operations (VACUUM, CREATE INDEX, ALTER TABLE). Higher values speed up index creation and VACUUM.

**Indexing operations**: CREATE INDEX on embeddings column (pgvector GIN/HNSW index) benefits significantly. Large repositories (100K+ files) may require 2GB+ for efficient index builds.

**Configuration**: `RAM / 16` (e.g., 16GB / 16 = 1GB). For enterprise deployments with massive codebases, use 2GB.

#### checkpoint_completion_target
**Why it matters for codebase-mcp**: Spreads checkpoint writes over time to avoid I/O spikes. Higher values (0.9) smooth out disk writes.

**Indexing operations**: Heavy INSERT activity during repository indexing generates significant WAL traffic. Spreading checkpoint I/O prevents write stalls.

**Configuration**: 0.9 (spread checkpoints over 90% of interval).

#### wal_buffers
**Why it matters for codebase-mcp**: Write-Ahead Log buffer size. Larger buffers reduce WAL writes during heavy INSERT workloads.

**Indexing operations**: Batch inserts of code chunks and embeddings generate significant WAL traffic. 16MB buffers improve write throughput.

**Configuration**: 16MB for write-heavy workloads (default -1 auto-tunes to 16MB on most systems).

#### random_page_cost
**Why it matters for codebase-mcp**: Cost estimate for random I/O vs. sequential I/O. Default 4.0 is for HDDs; SSDs have much lower random I/O penalty.

**Search operations**: Lower value (1.1) encourages pgvector index scans over sequential scans, improving semantic search performance (p95 latency target: <500ms).

**Configuration**: 1.1 for SSDs, 4.0 for HDDs.

---

## Monitoring & Health Checks

Monitor connection pool health and query performance to detect issues early and prevent production incidents.

### Key Indicators

Track these metrics to assess system health:

| Indicator | Description | Healthy Range | Warning Threshold | Critical Threshold |
|-----------|-------------|---------------|-------------------|-------------------|
| **Active pool count** | Number of active project connection pools | ≤ 80% of MAX_PROJECTS | > 80% of MAX_PROJECTS | > 90% of MAX_PROJECTS |
| **Connections per pool** | Average connections in use per project pool | 1-3 connections | > 70% of MAX_CONNECTIONS_PER_POOL | > 90% of MAX_CONNECTIONS_PER_POOL |
| **Pool eviction frequency** | How often LRU eviction occurs (evictions/hour) | < 1/hour | > 5/hour | > 10/hour |
| **Query latency (p95)** | 95th percentile query duration | < 100ms | > 500ms | > 1000ms |
| **Query latency (p99)** | 99th percentile query duration | < 200ms | > 1000ms | > 2000ms |
| **Total connections** | Total active PostgreSQL connections | < 60% of max_connections | > 80% of max_connections | > 95% of max_connections |

**Interpreting Indicators**:

- **Active pool count** approaching MAX_PROJECTS: Projects will be evicted frequently, causing performance degradation. Consider increasing MAX_PROJECTS or reducing concurrent project usage.

- **High connections per pool**: Connection contention within project. Operations may queue. Consider increasing MAX_CONNECTIONS_PER_POOL.

- **High pool eviction frequency**: MAX_PROJECTS too low for access patterns. Increase MAX_PROJECTS and recalculate PostgreSQL max_connections.

- **High query latency**: Either connection pool saturation, slow queries, or insufficient PostgreSQL tuning. Check connection pool utilization and PostgreSQL performance settings.

- **High total connections**: Approaching PostgreSQL max_connections limit. Risk of "too many connections" errors. Increase max_connections or reduce MAX_PROJECTS/MAX_CONNECTIONS_PER_POOL.

### Monitoring Queries

Run these SQL queries periodically (cron job or monitoring dashboard integration) to track connection health:

#### Active Databases

Check how many project databases are currently in use:

```sql
SELECT
    datname AS database_name,
    numbackends AS active_connections,
    xact_commit AS committed_transactions,
    xact_rollback AS rolled_back_transactions,
    blks_read AS disk_blocks_read,
    blks_hit AS cache_blocks_hit,
    ROUND(100.0 * blks_hit / NULLIF(blks_hit + blks_read, 0), 2) AS cache_hit_ratio
FROM pg_stat_database
WHERE datname LIKE 'codebase_%'
ORDER BY numbackends DESC;
```

**Interpretation**:
- `active_connections`: Number of active connections to each project database.
- `cache_hit_ratio`: Percentage of blocks served from cache (higher is better, target > 95%).
- High `disk_blocks_read` with low `cache_hit_ratio` indicates insufficient shared_buffers.

**Expected Output**:
```
database_name            | active_connections | committed_transactions | rolled_back_transactions | cache_hit_ratio
-------------------------+--------------------+------------------------+-------------------------+----------------
codebase_project_a       | 5                  | 10234                  | 12                      | 98.45
codebase_project_b       | 3                  | 8901                   | 8                       | 97.23
codebase_default         | 2                  | 5432                   | 5                       | 99.12
```

#### Connection Count Per Database

Monitor connections per project database to identify pool saturation:

```sql
SELECT
    datname AS database_name,
    COUNT(*) AS connection_count,
    COUNT(*) FILTER (WHERE state = 'active') AS active_count,
    COUNT(*) FILTER (WHERE state = 'idle') AS idle_count,
    COUNT(*) FILTER (WHERE state = 'idle in transaction') AS idle_in_transaction_count,
    STRING_AGG(DISTINCT application_name, ', ') AS applications
FROM pg_stat_activity
WHERE datname LIKE 'codebase_%'
GROUP BY datname
ORDER BY connection_count DESC;
```

**Interpretation**:
- `connection_count` approaching MAX_CONNECTIONS_PER_POOL: Pool saturation, operations may queue or timeout.
- High `idle_in_transaction_count`: Potential connection leaks or long-running transactions holding connections.
- `active_count` consistently high: Heavy query load, may need to increase MAX_CONNECTIONS_PER_POOL.

**Expected Output**:
```
database_name       | connection_count | active_count | idle_count | idle_in_transaction_count | applications
--------------------+------------------+--------------+------------+---------------------------+---------------------------
codebase_project_a  | 8                | 3            | 5          | 0                         | codebase-mcp
codebase_project_b  | 5                | 2            | 3          | 0                         | codebase-mcp
codebase_default    | 3                | 1            | 2          | 0                         | codebase-mcp
```

#### Total Connections vs. max_connections

Check total active connections against PostgreSQL limit to prevent exhaustion:

```sql
SELECT
    (SELECT COUNT(*) FROM pg_stat_activity) AS total_connections,
    (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') AS max_connections,
    (SELECT setting::int FROM pg_settings WHERE name = 'superuser_reserved_connections') AS reserved_connections,
    (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') -
    (SELECT setting::int FROM pg_settings WHERE name = 'superuser_reserved_connections') AS available_connections,
    ROUND(100.0 * (SELECT COUNT(*) FROM pg_stat_activity) /
          (SELECT setting::int FROM pg_settings WHERE name = 'max_connections'), 2) AS percent_used;
```

**Interpretation**:
- `percent_used` > 80%: Approaching connection limit, risk of "too many connections" errors. Monitor closely.
- `percent_used` > 90%: **CRITICAL** - Immediate action required. Increase max_connections or reduce MAX_PROJECTS.
- `total_connections` approaching `available_connections`: Non-superuser connections exhausted, new connections will fail.

**Expected Output**:
```
total_connections | max_connections | reserved_connections | available_connections | percent_used
------------------+-----------------+---------------------+----------------------+-------------
85                | 225             | 3                   | 222                  | 37.78
```

### Health Check Endpoints

codebase-mcp provides internal health monitoring via logging. Monitor log file for health indicators:

#### Log Monitoring Commands

```bash
# Monitor connection pool events (real-time)
tail -f /var/log/codebase-mcp.log | grep -E "pool_created|pool_evicted|connection_timeout"

# Count pool creations in last hour
grep "pool_created" /var/log/codebase-mcp.log | grep "$(date +%Y-%m-%d\ %H)" | wc -l

# Count pool evictions in last hour (high count indicates MAX_PROJECTS too low)
grep "pool_evicted" /var/log/codebase-mcp.log | grep "$(date +%Y-%m-%d\ %H)" | wc -l

# Find connection timeout errors (indicates pool saturation or PostgreSQL overload)
grep "connection_timeout" /var/log/codebase-mcp.log | tail -20
```

**Log Events and Meanings**:

| Event | Log Pattern | Meaning | Action |
|-------|-------------|---------|--------|
| **Pool created** | `pool_created project_id="project-a"` | New project pool initialized (normal on first access) | None (expected behavior) |
| **Pool evicted** | `pool_evicted project_id="project-b" reason="LRU"` | LRU eviction occurred (frequent = MAX_PROJECTS too low) | If > 5/hour, increase MAX_PROJECTS |
| **Connection timeout** | `connection_timeout project_id="project-c" timeout=30s` | Connection acquisition timeout (pool saturation or PostgreSQL overload) | Increase MAX_CONNECTIONS_PER_POOL or max_connections |
| **Connection exhausted** | `connection_exhausted remaining_slots=0` | PostgreSQL max_connections limit reached | Increase max_connections or reduce pool sizes |

#### Health Check Endpoint (Future)

**Note**: HTTP health check endpoint planned for Phase 06. Current implementation uses log-based monitoring.

**Planned Endpoint**: `GET /health` returning JSON:

```json
{
  "status": "healthy",
  "timestamp": "2025-10-13T12:34:56Z",
  "database": {
    "registry": {
      "status": "connected",
      "pool": {"size": 3, "free": 2}
    },
    "active_projects": 8,
    "max_projects": 10
  },
  "connection_usage": {
    "total": 85,
    "max": 225,
    "percent_used": 37.78
  },
  "metrics": {
    "pool_evictions_last_hour": 2,
    "query_p95_latency_ms": 87
  }
}
```

**Current Workaround**: Use SQL monitoring queries above in combination with log monitoring for health assessment.

---

## Security Configuration

**Database Access Control**:

```sql
-- Create dedicated codebase-mcp user (not superuser)
CREATE USER codebase_mcp WITH PASSWORD 'strong_password';

-- Grant necessary privileges
GRANT CREATE ON DATABASE codebase_registry TO codebase_mcp;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO codebase_mcp;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO codebase_mcp;

-- Restrict superuser access
-- Use separate superuser account for administrative tasks
```

**Environment Variable Security**:

```bash
# Store .env file with restricted permissions
chmod 600 .env
chown codebase-mcp:codebase-mcp .env

# Avoid logging sensitive values
# LOG_LEVEL=INFO (not DEBUG in production)
```

**Network Security**:

```bash
# PostgreSQL listen_addresses (postgresql.conf)
listen_addresses = 'localhost'  # Or specific internal IP

# Firewall rules (iptables)
# Allow PostgreSQL only from application server IP
iptables -A INPUT -p tcp -s 10.0.1.50 --dport 5432 -j ACCEPT
iptables -A INPUT -p tcp --dport 5432 -j DROP
```

---

## Configuration Validation Checklist

Before deploying to production, validate all configuration settings with these executable commands. All validations must pass to ensure correct operation.

| # | Validation Item | Command | Expected Result |
|---|-----------------|---------|-----------------|
| 1 | **DATABASE_URL connects** | `psql "${DATABASE_URL/+asyncpg/}" -c "SELECT 1;"` | Output: `1` (row returned) |
| 2 | **OLLAMA_BASE_URL responds** | `curl -f "${OLLAMA_BASE_URL}/api/version"` | HTTP 200, JSON response with version |
| 3 | **Embedding model available** | `curl -f "${OLLAMA_BASE_URL}/api/tags" \| grep "${OLLAMA_EMBEDDING_MODEL}"` | Model name appears in output |
| 4 | **PostgreSQL max_connections sufficient** | `psql "${DATABASE_URL/+asyncpg/}" -c "SHOW max_connections;"` | Value ≥ (MAX_PROJECTS × MAX_CONNECTIONS_PER_POOL) + buffer |
| 5 | **MAX_PROJECTS × MAX_CONNECTIONS_PER_POOL calculation valid** | Manual calculation | Total ≤ PostgreSQL max_connections - buffer |
| 6 | **workflow-mcp URL reachable (if configured)** | `curl -f "${WORKFLOW_MCP_URL}/health" \|\| echo "Not configured"` | HTTP 200 or "Not configured" (optional) |
| 7 | **Connection pool creation successful** | Start codebase-mcp, check logs | No connection errors in logs |
| 8 | **Indexing test completes** | Index small test repository via MCP client | Successful indexing, no timeout errors |

### Step-by-Step Validation Procedure

Follow these steps sequentially to validate your configuration:

#### Step 1: Verify Environment Variables Set

```bash
# Check all required variables are set
echo "DATABASE_URL: ${DATABASE_URL:0:30}..."  # Truncate for security
echo "OLLAMA_BASE_URL: ${OLLAMA_BASE_URL}"
echo "OLLAMA_EMBEDDING_MODEL: ${OLLAMA_EMBEDDING_MODEL}"
echo "MAX_PROJECTS: ${MAX_PROJECTS:-10}"  # Default: 10
echo "MAX_CONNECTIONS_PER_POOL: ${MAX_CONNECTIONS_PER_POOL:-20}"  # Default: 20
```

**Expected Output**: All variables should have values. DATABASE_URL should not be empty.

#### Step 2: Test DATABASE_URL Connectivity

```bash
# Test PostgreSQL connection (remove +asyncpg for psql compatibility)
psql "${DATABASE_URL/+asyncpg/}" -c "SELECT 1 AS test;"
```

**Expected Output**:
```
 test
------
    1
(1 row)
```

**Troubleshooting**:
- `psql: error: could not connect`: PostgreSQL not running or network issue.
- `FATAL: password authentication failed`: Incorrect credentials in DATABASE_URL.
- `FATAL: database "..." does not exist`: Database not created yet, run initialization script.

#### Step 3: Verify OLLAMA_BASE_URL Responds

```bash
# Test Ollama API availability
curl -f "${OLLAMA_BASE_URL}/api/version"
```

**Expected Output**:
```json
{"version":"0.1.14"}
```

**Troubleshooting**:
- `curl: (7) Failed to connect`: Ollama server not running or OLLAMA_BASE_URL incorrect.
- `curl: (22) The requested URL returned error: 404`: Ollama API endpoint changed, verify version.

#### Step 4: Confirm Embedding Model Available

```bash
# List available models and check for embedding model
curl -s "${OLLAMA_BASE_URL}/api/tags" | jq '.models[].name' | grep "${OLLAMA_EMBEDDING_MODEL}"
```

**Expected Output**:
```
"nomic-embed-text"
```

**Troubleshooting**:
- No output: Model not pulled yet. Run: `ollama pull ${OLLAMA_EMBEDDING_MODEL}`
- `jq: command not found`: Install jq or use: `curl -s "${OLLAMA_BASE_URL}/api/tags" | grep "${OLLAMA_EMBEDDING_MODEL}"`

#### Step 5: Check PostgreSQL max_connections Sufficient

```bash
# Calculate required connections
REQUIRED_CONNECTIONS=$(( ${MAX_PROJECTS:-10} * ${MAX_CONNECTIONS_PER_POOL:-20} + 30 ))
echo "Required connections: ${REQUIRED_CONNECTIONS}"

# Check PostgreSQL max_connections
CURRENT_MAX=$(psql "${DATABASE_URL/+asyncpg/}" -t -c "SHOW max_connections;" | xargs)
echo "PostgreSQL max_connections: ${CURRENT_MAX}"

# Validate sufficient capacity
if [ "${CURRENT_MAX}" -ge "${REQUIRED_CONNECTIONS}" ]; then
  echo "✅ PASS: max_connections (${CURRENT_MAX}) >= required (${REQUIRED_CONNECTIONS})"
else
  echo "❌ FAIL: max_connections (${CURRENT_MAX}) < required (${REQUIRED_CONNECTIONS})"
  echo "Action: Increase max_connections in postgresql.conf to at least ${REQUIRED_CONNECTIONS}"
fi
```

**Expected Output**:
```
Required connections: 230
PostgreSQL max_connections: 300
✅ PASS: max_connections (300) >= required (230)
```

**Troubleshooting**:
- **FAIL**: Increase `max_connections` in postgresql.conf and restart PostgreSQL.

#### Step 6: Validate MAX_PROJECTS × MAX_CONNECTIONS_PER_POOL Calculation

```bash
# Manual calculation validation
MAX_PROJECTS=${MAX_PROJECTS:-10}
MAX_CONNECTIONS_PER_POOL=${MAX_CONNECTIONS_PER_POOL:-20}
BUFFER=30
TOTAL=$(( MAX_PROJECTS * MAX_CONNECTIONS_PER_POOL ))
REQUIRED=$(( TOTAL + BUFFER ))

echo "Calculation Breakdown:"
echo "  MAX_PROJECTS: ${MAX_PROJECTS}"
echo "  MAX_CONNECTIONS_PER_POOL: ${MAX_CONNECTIONS_PER_POOL}"
echo "  Project connections: ${TOTAL}"
echo "  Buffer: ${BUFFER}"
echo "  Total required: ${REQUIRED}"
echo ""
echo "Formula: (${MAX_PROJECTS} × ${MAX_CONNECTIONS_PER_POOL}) + ${BUFFER} = ${REQUIRED}"
```

**Expected Output**:
```
Calculation Breakdown:
  MAX_PROJECTS: 10
  MAX_CONNECTIONS_PER_POOL: 20
  Project connections: 200
  Buffer: 30
  Total required: 230

Formula: (10 × 20) + 30 = 230
```

#### Step 7: Test workflow-mcp URL (If Configured)

```bash
# Test workflow-mcp connectivity (optional)
if [ -n "${WORKFLOW_MCP_URL}" ]; then
  curl -f -m 5 "${WORKFLOW_MCP_URL}/health" && echo "✅ workflow-mcp reachable" || echo "⚠️  workflow-mcp unreachable (fallback to default project)"
else
  echo "ℹ️  workflow-mcp not configured (standalone mode)"
fi
```

**Expected Output** (if configured):
```
✅ workflow-mcp reachable
```

**Expected Output** (if not configured):
```
ℹ️  workflow-mcp not configured (standalone mode)
```

**Note**: workflow-mcp integration is optional. Failure to connect triggers fallback to default project (expected behavior).

#### Step 8: Validate Connection Pool Creation

```bash
# Start codebase-mcp server
python -m mcp.server_fastmcp &
SERVER_PID=$!

# Wait for server startup
sleep 5

# Check logs for connection pool initialization
grep -i "connection pool" /var/log/codebase-mcp.log | tail -5

# Check for errors
if grep -i "error.*connection" /var/log/codebase-mcp.log | tail -1; then
  echo "❌ FAIL: Connection errors detected"
else
  echo "✅ PASS: No connection errors"
fi

# Cleanup (optional)
# kill $SERVER_PID
```

**Expected Output**:
```
✅ PASS: No connection errors
```

**Troubleshooting**:
- Connection pool errors: Review DATABASE_URL, max_connections, and PostgreSQL logs.

#### Step 9: Test Indexing Operation

```bash
# Create small test repository
mkdir -p /tmp/test-repo
echo "def hello(): print('test')" > /tmp/test-repo/test.py

# Index via MCP client (adapt to your MCP client)
# Example using mcp CLI tool:
# mcp call index_repository '{"repo_path": "/tmp/test-repo", "project_id": "validation-test"}'

# Check logs for successful indexing
grep -i "indexing.*complete" /var/log/codebase-mcp.log | tail -1

# Verify no timeout errors
if grep -i "timeout.*indexing" /var/log/codebase-mcp.log | tail -1; then
  echo "❌ FAIL: Indexing timeout detected"
else
  echo "✅ PASS: Indexing completed without timeout"
fi
```

**Expected Output**:
```
✅ PASS: Indexing completed without timeout
```

**Troubleshooting**:
- Indexing timeout: Increase PROJECT_POOL_TIMEOUT or check PostgreSQL performance.
- Connection errors during indexing: Verify max_connections and pool configuration.

### Validation Checklist Summary

After completing all 8 validation steps:

- [ ] DATABASE_URL connects successfully
- [ ] OLLAMA_BASE_URL responds with version
- [ ] Embedding model available in Ollama
- [ ] PostgreSQL max_connections sufficient for calculated load
- [ ] Connection calculation verified (manual check)
- [ ] workflow-mcp URL reachable (or not configured, optional)
- [ ] Connection pool creates without errors
- [ ] Test indexing completes successfully

**All checks must pass before production deployment.**

---

## Troubleshooting

### Issue 1: "Too Many Connections" Error

**Symptom**:
```
psycopg2.OperationalError: FATAL:  sorry, too many clients already
```

Or:

```
ERROR: remaining connection slots are reserved for non-replication superuser connections
```

**Cause**:
- PostgreSQL `max_connections` limit exceeded.
- Total connections from codebase-mcp (and other services) exceed `max_connections`.
- MAX_PROJECTS × MAX_CONNECTIONS_PER_POOL exceeds available connections.

**Diagnosis**:

```sql
-- Check current connection usage vs. limit
SELECT
  (SELECT COUNT(*) FROM pg_stat_activity) AS current_connections,
  (SELECT setting::int FROM pg_settings WHERE name = 'max_connections') AS max_connections,
  ROUND(100.0 * (SELECT COUNT(*) FROM pg_stat_activity) /
        (SELECT setting::int FROM pg_settings WHERE name = 'max_connections'), 2) AS percent_used;
```

If `percent_used` > 95%, you're at risk of connection exhaustion.

**Solution**:

1. **Option A - Increase PostgreSQL max_connections** (recommended if sufficient RAM):
   ```sql
   -- In PostgreSQL
   ALTER SYSTEM SET max_connections = 300;  -- Increase from current value
   ```

   Then restart PostgreSQL:
   ```bash
   sudo systemctl restart postgresql
   ```

2. **Option B - Reduce codebase-mcp connection pools**:
   ```bash
   # In .env
   MAX_PROJECTS=5  # Reduce from 10
   MAX_CONNECTIONS_PER_POOL=15  # Reduce from 20
   ```

   Recalculate required max_connections: (5 × 15) + 25 = 100

   Then restart codebase-mcp.

3. **Option C - Identify and terminate leaked connections**:
   ```sql
   -- Find long-running idle transactions holding connections
   SELECT pid, usename, application_name, state, state_change, query
   FROM pg_stat_activity
   WHERE state = 'idle in transaction'
   AND (now() - state_change) > interval '10 minutes';

   -- Terminate problematic connections (use with caution)
   -- SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid = <problematic_pid>;
   ```

**Prevention**:
- Always provision `max_connections` with 50-100% headroom above calculated total.
- Monitor connection usage regularly (see [Monitoring Queries](#monitoring-queries)).
- Set alerts for `percent_used` > 80%.

### Issue 2: Slow Query Performance

**Symptom**:
- Search queries taking > 1 second.
- Indexing operations slower than expected.
- High CPU usage on PostgreSQL server.
- P95 latency exceeds 500ms (constitutional guarantee).

**Cause**:
- Suboptimal PostgreSQL configuration (shared_buffers, work_mem too low).
- Missing or outdated pgvector indexes.
- Connection pool saturation causing query queueing.
- Insufficient `random_page_cost` tuning (sequential scans instead of index scans).

**Diagnosis**:

```sql
-- Check pgvector index existence
SELECT schemaname, tablename, indexname, indexdef
FROM pg_indexes
WHERE tablename = 'code_chunks' AND indexdef LIKE '%embeddings%';

-- Check query performance (requires pg_stat_statements extension)
SELECT
  query,
  calls,
  mean_exec_time,
  max_exec_time
FROM pg_stat_statements
WHERE query LIKE '%code_chunks%' OR query LIKE '%embeddings%'
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Check connection pool saturation
SELECT datname, COUNT(*) AS active_connections
FROM pg_stat_activity
WHERE datname LIKE 'codebase_%' AND state = 'active'
GROUP BY datname
HAVING COUNT(*) > 15;  -- Threshold: 75% of MAX_CONNECTIONS_PER_POOL
```

**Solution**:

1. **Tune PostgreSQL memory settings** (see [PostgreSQL Configuration](#postgresql-configuration)):
   ```sql
   ALTER SYSTEM SET shared_buffers = '8GB';  -- Increase from 4GB
   ALTER SYSTEM SET effective_cache_size = '24GB';  -- Increase from 12GB
   ALTER SYSTEM SET work_mem = '128MB';  -- Increase from 50MB
   SELECT pg_reload_conf();
   ```

   Or edit `postgresql.conf` directly and restart PostgreSQL.

2. **Verify pgvector index exists and is being used**:
   ```sql
   -- Check index exists (HNSW or IVFFlat index for vector similarity)
   SELECT * FROM pg_indexes
   WHERE tablename = 'code_chunks'
   AND indexdef LIKE '%USING hnsw%';

   -- If missing, create index (may take hours for large repositories)
   -- CREATE INDEX idx_code_chunks_embedding ON code_chunks USING hnsw (embeddings vector_cosine_ops);
   ```

3. **Increase connection pool size if contention detected**:
   ```bash
   # In .env
   MAX_CONNECTIONS_PER_POOL=25  # Increase from 20
   ```

   Recalculate max_connections: (10 × 25) + 30 = 280

4. **Optimize query planner settings for SSDs**:
   ```sql
   ALTER SYSTEM SET random_page_cost = 1.1;  -- Encourage index scans on SSDs
   ALTER SYSTEM SET effective_io_concurrency = 200;
   SELECT pg_reload_conf();
   ```

5. **Run VACUUM ANALYZE to update statistics**:
   ```sql
   VACUUM ANALYZE code_chunks;
   ```

**Prevention**:
- Follow production tuning recommendations from [PostgreSQL Configuration](#postgresql-configuration).
- Run `VACUUM ANALYZE` weekly to keep query planner statistics current.
- Monitor query latency metrics (p95, p99) via logs or monitoring dashboard.

### Issue 3: Frequent Pool Evictions

**Symptom**:
- Log entries showing frequent `pool_evicted` messages (> 5/hour).
- Noticeable latency when switching between projects.
- Users report indexing delays when accessing projects not recently used.
- Performance degradation due to repeated pool initialization overhead.

**Cause**:
- `MAX_PROJECTS` set too low for actual usage patterns.
- Many projects accessed in short time window exceeding LRU cache capacity.
- High project diversity with limited connection pool slots.

**Diagnosis**:

```bash
# Count pool evictions in last hour
EVICTIONS=$(grep "pool_evicted" /var/log/codebase-mcp.log | grep "$(date +%Y-%m-%d\ %H)" | wc -l)
echo "Pool evictions in last hour: ${EVICTIONS}"

if [ "${EVICTIONS}" -gt 5 ]; then
  echo "⚠️  WARNING: High eviction rate (> 5/hour)"
  echo "Action: Increase MAX_PROJECTS"
fi

# Count unique projects accessed in last hour
UNIQUE_PROJECTS=$(grep "pool_created\|pool_accessed" /var/log/codebase-mcp.log | grep "$(date +%Y-%m-%d\ %H)" | awk '{print $NF}' | sort -u | wc -l)
echo "Unique projects accessed: ${UNIQUE_PROJECTS}"

# Compare to MAX_PROJECTS
MAX_PROJECTS=${MAX_PROJECTS:-10}
echo "MAX_PROJECTS limit: ${MAX_PROJECTS}"

if [ "${UNIQUE_PROJECTS}" -gt "${MAX_PROJECTS}" ]; then
  echo "⚠️  WARNING: ${UNIQUE_PROJECTS} projects accessed exceeds MAX_PROJECTS (${MAX_PROJECTS})"
fi
```

**Solution**:

1. **Increase MAX_PROJECTS to match concurrent usage**:
   ```bash
   # In .env
   MAX_PROJECTS=20  # Increase from 10
   ```

2. **Recalculate and update PostgreSQL max_connections**:
   ```bash
   # New required connections: (20 × 20) + 30 = 430
   # Update postgresql.conf:
   # max_connections = 430
   ```

   Restart PostgreSQL:
   ```bash
   sudo systemctl restart postgresql
   ```

3. **Restart codebase-mcp with new configuration**:
   ```bash
   # Reload .env and restart server
   systemctl restart codebase-mcp
   ```

4. **Monitor eviction rate after changes**:
   ```bash
   # Wait 1 hour, then recheck eviction rate
   sleep 3600
   grep "pool_evicted" /var/log/codebase-mcp.log | grep "$(date +%Y-%m-%d\ %H)" | wc -l
   ```

**Prevention**:
- Set `MAX_PROJECTS` based on peak concurrent project usage (not total projects in system).
- For teams with > 20 projects, start with `MAX_PROJECTS=25` and monitor eviction rate.
- Monitor eviction frequency weekly via logs:
  ```bash
  # Weekly eviction report
  grep "pool_evicted" /var/log/codebase-mcp.log | grep "$(date +%Y-%m-%d)" | wc -l
  ```
- Set alerts for eviction rate > 10/day.

---

## Example Configurations

### Development Environment

```bash
# .env - Development
DATABASE_URL=postgresql+asyncpg://localhost/codebase_mcp_dev
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_BATCH_SIZE=50
MAX_PROJECTS=5
MAX_CONNECTIONS_PER_POOL=10
MAX_CONCURRENT_REQUESTS=5
LOG_LEVEL=DEBUG
LOG_FILE=/tmp/codebase-mcp-dev.log
```

**PostgreSQL Configuration**:
```ini
max_connections = 70  # (5 × 10) + 20
shared_buffers = 256MB
effective_cache_size = 1GB
```

### Production Environment (Medium)

```bash
# .env - Production Medium
DATABASE_URL=postgresql+asyncpg://codebase:password@db.internal:5432/codebase_mcp
OLLAMA_BASE_URL=http://ollama.internal:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_BATCH_SIZE=100
MAX_PROJECTS=10
MAX_CONNECTIONS_PER_POOL=20
MAX_CONCURRENT_REQUESTS=20
LOG_LEVEL=INFO
LOG_FILE=/var/log/codebase-mcp/server.log
WORKFLOW_MCP_URL=http://workflow-mcp.internal:8000
WORKFLOW_MCP_TIMEOUT=2.0
WORKFLOW_MCP_CACHE_TTL=120
```

**PostgreSQL Configuration**:
```ini
max_connections = 230  # (10 × 20) + 30
shared_buffers = 4GB
effective_cache_size = 12GB
work_mem = 64MB
maintenance_work_mem = 1GB
random_page_cost = 1.1
```

### Production Environment (Enterprise)

```bash
# .env - Production Enterprise
DATABASE_URL=postgresql+asyncpg://codebase:password@db.internal:5432/codebase_mcp
OLLAMA_BASE_URL=http://ollama.internal:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_BATCH_SIZE=100
MAX_PROJECTS=50
MAX_CONNECTIONS_PER_POOL=20
MAX_CONCURRENT_REQUESTS=50
LOG_LEVEL=INFO
LOG_FILE=/var/log/codebase-mcp/server.log
WORKFLOW_MCP_URL=http://workflow-mcp.internal:8000
WORKFLOW_MCP_TIMEOUT=2.0
WORKFLOW_MCP_CACHE_TTL=120
```

**PostgreSQL Configuration**:
```ini
max_connections = 1050  # (50 × 20) + 50
shared_buffers = 16GB
effective_cache_size = 48GB
work_mem = 128MB
maintenance_work_mem = 2GB
random_page_cost = 1.1
max_parallel_workers_per_gather = 4
max_parallel_workers = 16
```

---

## Additional Resources

- **Migration Guide**: [docs/migration/v1-to-v2-migration.md](/Users/cliffclarke/Claude_Code/codebase-mcp/docs/migration/v1-to-v2-migration.md) - Upgrade procedures from v1.x to v2.0
- **Architecture Documentation**: [docs/architecture/](/Users/cliffclarke/Claude_Code/codebase-mcp/docs/architecture/) - Multi-project workspace design and connection pool architecture
- **API Reference**: [docs/api/](/Users/cliffclarke/Claude_Code/codebase-mcp/docs/api/) - Tool parameters including `project_id`
- **Glossary**: [docs/glossary.md](/Users/cliffclarke/Claude_Code/codebase-mcp/docs/glossary.md) - Terminology definitions

---

**Document Version**: v2.0
**Last Updated**: 2025-10-13
**Authors**: codebase-mcp maintainers
