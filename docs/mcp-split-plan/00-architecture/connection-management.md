# Connection Management Architecture

## Overview

The `ProjectConnectionManager` pattern provides connection pooling for multi-project workspaces. It maintains a persistent pool to the registry database and creates lazy, cached pools for project databases.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│         ProjectConnectionManager                    │
│                                                     │
│  ┌───────────────────────────────────────────┐    │
│  │  Registry Pool (persistent)               │    │
│  │  - min_size: 2, max_size: 10              │    │
│  │  - Always connected                       │    │
│  │  - Shared by both MCPs                    │    │
│  └───────────────────────────────────────────┘    │
│                                                     │
│  ┌───────────────────────────────────────────┐    │
│  │  Project Pools (lazy, cached)             │    │
│  │                                            │    │
│  │  project_myapp    -> Pool (1-5 conns)     │    │
│  │  project_website  -> Pool (1-5 conns)     │    │
│  │  project_game     -> Pool (1-5 conns)     │    │
│  │                                            │    │
│  │  Created on first access                  │    │
│  │  Cached in memory                         │    │
│  └───────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

## Implementation

### Core Class

```python
"""
connection_manager.py - Shared connection pooling for multi-project MCPs
"""
import asyncpg
from typing import Dict, Optional, AsyncContextManager
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)


class ProjectConnectionManager:
    """
    Manages PostgreSQL connection pools for multi-project workspaces.

    Registry pool is persistent and shared. Project pools are lazy-created
    and cached. Supports up to 20 projects without performance degradation.
    """

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        registry_database: str = "mcp_registry",
        registry_pool_min: int = 2,
        registry_pool_max: int = 10,
        project_pool_min: int = 1,
        project_pool_max: int = 5,
    ):
        """
        Initialize connection manager.

        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            user: PostgreSQL user
            password: PostgreSQL password
            registry_database: Registry database name (default: mcp_registry)
            registry_pool_min: Minimum registry connections (default: 2)
            registry_pool_max: Maximum registry connections (default: 10)
            project_pool_min: Minimum project connections (default: 1)
            project_pool_max: Maximum project connections (default: 5)
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.registry_database = registry_database

        self.registry_pool_min = registry_pool_min
        self.registry_pool_max = registry_pool_max
        self.project_pool_min = project_pool_min
        self.project_pool_max = project_pool_max

        # Connection pools
        self.registry_pool: Optional[asyncpg.Pool] = None
        self.project_pools: Dict[str, asyncpg.Pool] = {}

    async def initialize(self) -> None:
        """
        Initialize registry pool. Call once at MCP server startup.

        Raises:
            ConnectionError: If registry connection fails
        """
        try:
            logger.info(f"Initializing registry pool: {self.registry_database}")
            self.registry_pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.registry_database,
                min_size=self.registry_pool_min,
                max_size=self.registry_pool_max,
                max_queries=50000,
                max_inactive_connection_lifetime=300.0,  # 5 minutes
                command_timeout=60.0,  # 1 minute
            )
            logger.info("Registry pool initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize registry pool: {e}")
            raise ConnectionError(f"Failed to connect to registry database: {e}")

    async def close(self) -> None:
        """
        Close all connection pools. Call at MCP server shutdown.
        """
        logger.info("Closing all connection pools")

        # Close registry pool
        if self.registry_pool:
            await self.registry_pool.close()
            logger.info("Registry pool closed")

        # Close all project pools
        for project_name, pool in self.project_pools.items():
            await pool.close()
            logger.info(f"Project pool closed: {project_name}")

        self.project_pools.clear()

    async def _get_project_database_name(self, project_name: str) -> str:
        """
        Lookup project database name from registry.

        Args:
            project_name: Project name

        Returns:
            Database name for the project

        Raises:
            ValueError: If project not found
            RuntimeError: If registry pool not initialized
        """
        if not self.registry_pool:
            raise RuntimeError("Registry pool not initialized. Call initialize() first.")

        async with self.registry_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT database_name FROM projects WHERE name = $1",
                project_name
            )

        if not row:
            raise ValueError(f"Project '{project_name}' not found in registry")

        return row["database_name"]

    async def _create_project_pool(self, project_name: str, database_name: str) -> asyncpg.Pool:
        """
        Create a new connection pool for a project database.

        Args:
            project_name: Project name (for logging)
            database_name: PostgreSQL database name

        Returns:
            New asyncpg connection pool

        Raises:
            ConnectionError: If connection fails
        """
        try:
            logger.info(f"Creating connection pool for project: {project_name} (db: {database_name})")
            pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=database_name,
                min_size=self.project_pool_min,
                max_size=self.project_pool_max,
                max_queries=50000,
                max_inactive_connection_lifetime=600.0,  # 10 minutes
                command_timeout=120.0,  # 2 minutes (indexing can be slow)
            )
            logger.info(f"Connection pool created for project: {project_name}")
            return pool
        except Exception as e:
            logger.error(f"Failed to create pool for project {project_name}: {e}")
            raise ConnectionError(f"Failed to connect to project database '{database_name}': {e}")

    async def get_project_pool(self, project_name: str) -> asyncpg.Pool:
        """
        Get or create connection pool for a project.

        Lazy-creates pool on first access and caches it. Safe for concurrent access.

        Args:
            project_name: Project name

        Returns:
            Connection pool for the project

        Raises:
            ValueError: If project not found
            ConnectionError: If connection fails
        """
        # Check cache first
        if project_name in self.project_pools:
            return self.project_pools[project_name]

        # Lookup database name from registry
        database_name = await self._get_project_database_name(project_name)

        # Create and cache pool
        pool = await self._create_project_pool(project_name, database_name)
        self.project_pools[project_name] = pool

        return pool

    @asynccontextmanager
    async def get_project_connection(
        self, project_name: str
    ) -> AsyncContextManager[asyncpg.Connection]:
        """
        Context manager for getting a project database connection.

        Usage:
            async with conn_mgr.get_project_connection("myapp") as conn:
                result = await conn.fetch("SELECT * FROM codebase.repositories")

        Args:
            project_name: Project name

        Yields:
            Database connection

        Raises:
            ValueError: If project not found
            ConnectionError: If connection fails
        """
        pool = await self.get_project_pool(project_name)
        async with pool.acquire() as connection:
            yield connection

    @asynccontextmanager
    async def get_registry_connection(self) -> AsyncContextManager[asyncpg.Connection]:
        """
        Context manager for getting a registry database connection.

        Usage:
            async with conn_mgr.get_registry_connection() as conn:
                projects = await conn.fetch("SELECT * FROM projects")

        Yields:
            Registry database connection

        Raises:
            RuntimeError: If registry pool not initialized
        """
        if not self.registry_pool:
            raise RuntimeError("Registry pool not initialized. Call initialize() first.")

        async with self.registry_pool.acquire() as connection:
            yield connection

    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of all connection pools.

        Returns:
            Dictionary with health status for registry and each project
        """
        health = {}

        # Check registry pool
        try:
            async with self.get_registry_connection() as conn:
                await conn.fetchval("SELECT 1")
            health["registry"] = True
        except Exception as e:
            logger.error(f"Registry health check failed: {e}")
            health["registry"] = False

        # Check project pools
        for project_name in self.project_pools.keys():
            try:
                async with self.get_project_connection(project_name) as conn:
                    await conn.fetchval("SELECT 1")
                health[f"project:{project_name}"] = True
            except Exception as e:
                logger.error(f"Project {project_name} health check failed: {e}")
                health[f"project:{project_name}"] = False

        return health

    def get_pool_stats(self) -> Dict[str, dict]:
        """
        Get connection pool statistics.

        Returns:
            Dictionary with stats for each pool
        """
        stats = {}

        # Registry pool stats
        if self.registry_pool:
            stats["registry"] = {
                "size": self.registry_pool.get_size(),
                "min_size": self.registry_pool.get_min_size(),
                "max_size": self.registry_pool.get_max_size(),
                "idle_connections": self.registry_pool.get_idle_size(),
            }

        # Project pool stats
        for project_name, pool in self.project_pools.items():
            stats[f"project:{project_name}"] = {
                "size": pool.get_size(),
                "min_size": pool.get_min_size(),
                "max_size": pool.get_max_size(),
                "idle_connections": pool.get_idle_size(),
            }

        return stats
```

## Connection Lifecycle

### Initialization (Startup)

```python
# In MCP server startup (both codebase-mcp and workflow-mcp)
from connection_manager import ProjectConnectionManager

async def startup():
    """Initialize MCP server."""
    global conn_mgr

    conn_mgr = ProjectConnectionManager(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "mcp_user"),
        password=os.getenv("POSTGRES_PASSWORD"),
        registry_database=os.getenv("POSTGRES_REGISTRY_DB", "mcp_registry"),
    )

    await conn_mgr.initialize()
    logger.info("Connection manager initialized")

# FastMCP startup hook
@mcp.server.startup()
async def on_startup():
    await startup()
```

### Tool Execution (Runtime)

```python
# In MCP tool implementation
from fastmcp import FastMCP

mcp = FastMCP("codebase-mcp")

@mcp.tool()
async def search_code(
    query: str,
    project_name: str,
    file_type: Optional[str] = None,
    limit: int = 10
) -> dict:
    """
    Search codebase using semantic similarity.

    Args:
        query: Search query
        project_name: Project name
        file_type: Optional file type filter (e.g., "py", "js")
        limit: Maximum results (default: 10)

    Returns:
        Search results with similarity scores
    """
    # Generate query embedding (not shown)
    query_embedding = await generate_embedding(query)

    # Get project connection (lazy pool creation + caching)
    async with conn_mgr.get_project_connection(project_name) as conn:
        # Execute semantic search
        sql = """
            SELECT
                id,
                file_path,
                content,
                start_line,
                end_line,
                1 - (embedding <=> $1::vector) as similarity
            FROM codebase.code_chunks
            WHERE ($2::text IS NULL OR file_type = $2)
            ORDER BY embedding <=> $1::vector
            LIMIT $3
        """
        rows = await conn.fetch(sql, query_embedding, file_type, limit)

    # Format results
    results = [
        {
            "chunk_id": str(row["id"]),
            "file_path": row["file_path"],
            "content": row["content"],
            "start_line": row["start_line"],
            "end_line": row["end_line"],
            "similarity": float(row["similarity"]),
        }
        for row in rows
    ]

    return {
        "results": results,
        "total_count": len(results),
    }
```

### Shutdown (Cleanup)

```python
# In MCP server shutdown
async def shutdown():
    """Clean up resources."""
    global conn_mgr

    if conn_mgr:
        await conn_mgr.close()
        logger.info("Connection manager closed")

# FastMCP shutdown hook
@mcp.server.shutdown()
async def on_shutdown():
    await shutdown()
```

## Pool Sizing Strategy

### Registry Pool

- **min_size: 2** - Keep 2 connections warm
- **max_size: 10** - Scale up for bursts
- **Rationale:**
  - Registry queries are fast (< 1ms)
  - Two MCPs × 2 concurrent operations = 4 connections peak
  - Extra capacity for health checks and monitoring

### Project Pool

- **min_size: 1** - Keep 1 connection warm per active project
- **max_size: 5** - Support moderate concurrency
- **Rationale:**
  - Most projects idle most of the time
  - Indexing operations can take time (need headroom)
  - 5 connections × 2 MCPs = 10 connections per active project

### Concurrent Operations

**Expected:**
- Claude Code runs 1-2 operations at a time
- Operations target 1-2 projects simultaneously
- Registry pool handles: 2-4 queries/sec
- Project pools handle: 1-2 queries/sec each

**Peak Load:**
- Registry pool: 10 concurrent queries (rare)
- Project pool: 5 concurrent queries (e.g., parallel indexing)

### Scaling Limits

| Projects | Registry Pool | Project Pools | Total Connections | Status |
|----------|---------------|---------------|-------------------|--------|
| 1 | 2-10 | 1-5 | 3-15 | Excellent |
| 5 | 2-10 | 5-25 | 7-35 | Excellent |
| 10 | 2-10 | 10-50 | 12-60 | Good |
| 20 | 2-10 | 20-100 | 22-110 | Acceptable |
| 50 | 2-10 | 50-250 | 52-260 | Exceeds default max_connections |

**Action Required at 20+ Projects:**
- Reduce project_pool_max to 3 (60 connections total)
- Implement pool eviction for inactive projects
- Consider PgBouncer for connection pooling

## Error Handling

### Project Not Found

```python
@mcp.tool()
async def search_code(query: str, project_name: str) -> dict:
    try:
        async with conn_mgr.get_project_connection(project_name) as conn:
            # ... query ...
            pass
    except ValueError as e:
        # Project not found in registry
        logger.error(f"Project not found: {project_name}")
        return {
            "error": f"Project '{project_name}' not found",
            "hint": "Use list_projects() to see available projects"
        }
```

### Connection Failure

```python
@mcp.tool()
async def index_repository(repo_path: str, project_name: str) -> dict:
    try:
        async with conn_mgr.get_project_connection(project_name) as conn:
            # ... indexing logic ...
            pass
    except ConnectionError as e:
        # Failed to connect to project database
        logger.error(f"Connection failed for project {project_name}: {e}")
        return {
            "error": f"Failed to connect to project database",
            "details": str(e)
        }
```

### Pool Exhaustion

```python
# Pool exhaustion is handled by asyncpg automatically
# Connection acquisition will wait (up to command_timeout)
# If timeout exceeded, raises asyncpg.exceptions.TooManyConnectionsError

@mcp.tool()
async def slow_operation(project_name: str) -> dict:
    try:
        async with conn_mgr.get_project_connection(project_name) as conn:
            # Long-running query
            await conn.execute("ANALYZE VERBOSE")
    except asyncpg.exceptions.TooManyConnectionsError:
        logger.error(f"Connection pool exhausted for project: {project_name}")
        return {
            "error": "Too many concurrent operations on this project",
            "hint": "Wait for other operations to complete and retry"
        }
```

### Registry Pool Not Initialized

```python
@mcp.tool()
async def list_projects() -> dict:
    try:
        async with conn_mgr.get_registry_connection() as conn:
            rows = await conn.fetch("SELECT name, description FROM projects")
    except RuntimeError as e:
        # Registry pool not initialized
        logger.critical("Registry pool not initialized!")
        return {
            "error": "MCP server initialization failed",
            "details": str(e)
        }
```

## Advanced Patterns

### Transaction Management

```python
@mcp.tool()
async def create_entity_with_audit(
    project_name: str,
    schema_name: str,
    data: dict
) -> dict:
    """Create entity with audit log in single transaction."""
    async with conn_mgr.get_project_connection(project_name) as conn:
        async with conn.transaction():
            # Insert entity
            entity_id = await conn.fetchval("""
                INSERT INTO workflow.entities (schema_name, data)
                VALUES ($1, $2)
                RETURNING id
            """, schema_name, data)

            # Insert audit log
            await conn.execute("""
                INSERT INTO workflow.audit_log (entity_id, action, data)
                VALUES ($1, 'created', $2)
            """, entity_id, data)

    return {"entity_id": str(entity_id)}
```

### Batch Operations

```python
@mcp.tool()
async def index_repository_batch(
    repo_path: str,
    project_name: str,
    chunks: List[dict]
) -> dict:
    """Index code chunks in batches for performance."""
    async with conn_mgr.get_project_connection(project_name) as conn:
        # Use executemany for bulk insert (faster than individual inserts)
        await conn.executemany("""
            INSERT INTO codebase.code_chunks
                (repository_id, file_path, content, start_line, end_line, embedding)
            VALUES ($1, $2, $3, $4, $5, $6::vector)
        """, [
            (chunk["repo_id"], chunk["file_path"], chunk["content"],
             chunk["start_line"], chunk["end_line"], chunk["embedding"])
            for chunk in chunks
        ])

    return {"chunks_indexed": len(chunks)}
```

### Connection Pooling Metrics

```python
@mcp.tool()
async def get_connection_stats() -> dict:
    """Get connection pool statistics for monitoring."""
    stats = conn_mgr.get_pool_stats()

    return {
        "registry": stats.get("registry", {}),
        "projects": {
            k.replace("project:", ""): v
            for k, v in stats.items()
            if k.startswith("project:")
        }
    }
```

### Health Check Endpoint

```python
@mcp.tool()
async def health_check() -> dict:
    """Check health of all database connections."""
    health = await conn_mgr.health_check()

    all_healthy = all(health.values())

    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "checks": health
    }
```

## Testing

### Unit Tests

```python
import pytest
import asyncpg
from connection_manager import ProjectConnectionManager


@pytest.mark.asyncio
async def test_registry_pool_initialization():
    """Test registry pool initialization."""
    conn_mgr = ProjectConnectionManager(
        host="localhost",
        port=5432,
        user="test_user",
        password="test_pass",
    )

    await conn_mgr.initialize()
    assert conn_mgr.registry_pool is not None

    # Test query
    async with conn_mgr.get_registry_connection() as conn:
        result = await conn.fetchval("SELECT 1")
        assert result == 1

    await conn_mgr.close()


@pytest.mark.asyncio
async def test_project_pool_lazy_creation():
    """Test lazy project pool creation."""
    conn_mgr = ProjectConnectionManager(
        host="localhost",
        port=5432,
        user="test_user",
        password="test_pass",
    )

    await conn_mgr.initialize()

    # Create test project in registry
    async with conn_mgr.get_registry_connection() as conn:
        await conn.execute("""
            INSERT INTO projects (name, database_name)
            VALUES ('test_project', 'project_test')
        """)

    # First access creates pool
    assert "test_project" not in conn_mgr.project_pools
    pool = await conn_mgr.get_project_pool("test_project")
    assert "test_project" in conn_mgr.project_pools

    # Second access returns cached pool
    pool2 = await conn_mgr.get_project_pool("test_project")
    assert pool is pool2

    await conn_mgr.close()


@pytest.mark.asyncio
async def test_project_not_found():
    """Test error handling for nonexistent project."""
    conn_mgr = ProjectConnectionManager(
        host="localhost",
        port=5432,
        user="test_user",
        password="test_pass",
    )

    await conn_mgr.initialize()

    with pytest.raises(ValueError, match="not found in registry"):
        await conn_mgr.get_project_pool("nonexistent_project")

    await conn_mgr.close()
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_multi_project_isolation():
    """Test that projects are properly isolated."""
    conn_mgr = ProjectConnectionManager(
        host="localhost",
        port=5432,
        user="test_user",
        password="test_pass",
    )

    await conn_mgr.initialize()

    # Create two test projects
    async with conn_mgr.get_registry_connection() as conn:
        await conn.execute("""
            INSERT INTO projects (name, database_name) VALUES
                ('project_a', 'project_a'),
                ('project_b', 'project_b')
        """)

    # Insert data into project A
    async with conn_mgr.get_project_connection("project_a") as conn:
        await conn.execute("""
            INSERT INTO workflow.entities (schema_name, data)
            VALUES ('test', '{"value": "A"}'::jsonb)
        """)

    # Insert data into project B
    async with conn_mgr.get_project_connection("project_b") as conn:
        await conn.execute("""
            INSERT INTO workflow.entities (schema_name, data)
            VALUES ('test', '{"value": "B"}'::jsonb)
        """)

    # Verify isolation
    async with conn_mgr.get_project_connection("project_a") as conn:
        value_a = await conn.fetchval(
            "SELECT data->>'value' FROM workflow.entities LIMIT 1"
        )
        assert value_a == "A"

    async with conn_mgr.get_project_connection("project_b") as conn:
        value_b = await conn.fetchval(
            "SELECT data->>'value' FROM workflow.entities LIMIT 1"
        )
        assert value_b == "B"

    await conn_mgr.close()
```

## Performance Monitoring

### Logging Configuration

```python
import logging

# Configure connection manager logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)

# Set debug level for connection manager
logging.getLogger("connection_manager").setLevel(logging.DEBUG)
```

### Metrics Collection

```python
import time
from typing import Dict
from collections import defaultdict


class ConnectionMetrics:
    """Track connection pool metrics."""

    def __init__(self):
        self.query_counts: Dict[str, int] = defaultdict(int)
        self.query_latencies: Dict[str, list] = defaultdict(list)

    def record_query(self, pool_name: str, latency_ms: float):
        """Record a query execution."""
        self.query_counts[pool_name] += 1
        self.query_latencies[pool_name].append(latency_ms)

    def get_stats(self) -> dict:
        """Get aggregated statistics."""
        return {
            pool_name: {
                "count": self.query_counts[pool_name],
                "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
                "max_latency_ms": max(latencies) if latencies else 0,
            }
            for pool_name, latencies in self.query_latencies.items()
        }


# Usage in tool
metrics = ConnectionMetrics()

@mcp.tool()
async def search_code(query: str, project_name: str) -> dict:
    start = time.time()

    async with conn_mgr.get_project_connection(project_name) as conn:
        results = await conn.fetch("SELECT ...")

    latency_ms = (time.time() - start) * 1000
    metrics.record_query(f"project:{project_name}", latency_ms)

    return {"results": results}
```

## Summary

The `ProjectConnectionManager` provides:

- **Persistent registry pool**: Always connected, shared by both MCPs
- **Lazy project pools**: Created on first access, cached for reuse
- **Automatic cleanup**: Pools closed on shutdown
- **Error handling**: Comprehensive error handling with helpful messages
- **Performance**: Optimized pool sizing for < 20 projects
- **Observability**: Health checks, metrics, and logging
