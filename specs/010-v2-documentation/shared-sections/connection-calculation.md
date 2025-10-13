# PostgreSQL Connection Pool Calculation

## Formula

```
Required max_connections = (MAX_PROJECTS × MAX_CONNECTIONS_PER_POOL) + buffer
```

### Components

- **MAX_PROJECTS**: Maximum number of concurrent project workspaces
- **MAX_CONNECTIONS_PER_POOL**: Connections allocated per project database pool
- **buffer**: Additional connections for system overhead (recommended: 20-30)

### Buffer Explanation

The buffer accounts for:
- **System processes**: PostgreSQL background workers (autovacuum, stats collector, WAL writer)
- **Admin connections**: Superuser-reserved connections for maintenance and troubleshooting
- **Registry database**: Connections for the central registry database pool
- **Overhead**: Temporary connections during database operations
- **Safety margin**: Prevents connection exhaustion under peak load

A buffer of 20-30 connections is recommended for production deployments. For high-availability setups or frequent administrative access, consider a buffer of 30-50.

## Example Scenarios

| Deployment Size | MAX_PROJECTS | MAX_CONNECTIONS_PER_POOL | Project Connections | Buffer | **Required max_connections** |
|----------------|--------------|--------------------------|---------------------|--------|------------------------------|
| **Small**      | 5            | 10                       | 50                  | 20     | **70**                       |
| **Medium**     | 10           | 15                       | 150                 | 25     | **175**                      |
| **Large**      | 20           | 20                       | 400                 | 30     | **430**                      |
| **Enterprise** | 50           | 20                       | 1000                | 50     | **1050**                     |
| **Minimal**    | 2            | 5                        | 10                  | 15     | **25**                       |

### Scenario Details

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

## Warnings and Considerations

### Insufficient Connections

If PostgreSQL `max_connections` is set below the required value, you will encounter:

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

### Configuration Best Practices

1. **Always set max_connections higher than calculated minimum**
   - Add safety margin beyond buffer (e.g., +10%)
   - Example: For 175 required, set `max_connections = 200`

2. **Monitor connection usage**
   ```sql
   SELECT count(*) FROM pg_stat_activity;
   ```
   - Alert if usage exceeds 80% of max_connections
   - Track per-project connection patterns

3. **Adjust based on workload**
   - Increase MAX_CONNECTIONS_PER_POOL for high-concurrency projects
   - Reduce MAX_PROJECTS if consistently underutilized
   - Re-calculate after configuration changes

4. **Resource constraints**
   - Each connection consumes ~2-10MB RAM
   - Large max_connections requires adequate system memory
   - Example: 1000 connections = ~2-10GB RAM for PostgreSQL alone

5. **Operating system limits**
   - Verify OS file descriptor limits (ulimit -n)
   - PostgreSQL requires ~2 file descriptors per connection
   - Example: 1000 connections requires `ulimit -n` ≥ 2500

## Validation

After setting max_connections, validate the configuration:

1. **Check PostgreSQL setting**:
   ```sql
   SHOW max_connections;
   ```

2. **Verify health check**:
   ```bash
   # Use MCP health_check tool
   # Inspect database.registry.pool and database.active_project.pool
   ```

3. **Load test**:
   - Create MAX_PROJECTS workspaces
   - Execute concurrent operations on each
   - Monitor connection pool statistics

4. **Rollback if issues occur**:
   - Reduce MAX_PROJECTS or MAX_CONNECTIONS_PER_POOL
   - Increase PostgreSQL max_connections
   - Restart PostgreSQL to apply changes
