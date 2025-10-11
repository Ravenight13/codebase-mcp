# Deployment Configuration

## Overview

This document describes how to run both **codebase-mcp** and **workflow-mcp** simultaneously, sharing a single PostgreSQL instance with database-per-project isolation.

## System Requirements

### PostgreSQL

- **Version**: 14+ (for pgvector support)
- **Extensions**:
  - `uuid-ossp` (UUID generation)
  - `pgvector` (embedding storage for codebase-mcp)
- **Configuration**:
  - `max_connections`: 200 (default sufficient for < 20 projects)
  - `shared_buffers`: 256MB minimum
  - `effective_cache_size`: 1GB minimum

### Python

- **Version**: 3.11+
- **Dependencies**:
  - `fastmcp` - FastMCP framework
  - `mcp` - MCP Python SDK
  - `asyncpg` - PostgreSQL driver
  - `pydantic` - Type validation
  - `pgvector` - Vector operations (codebase-mcp only)
  - `sentence-transformers` - Embeddings (codebase-mcp only)
  - `jsonschema` - JSON Schema validation (workflow-mcp only)

### System Resources

- **Memory**: 4GB minimum (8GB recommended)
- **Disk**: 10GB minimum for databases
- **CPU**: 2+ cores recommended for parallel indexing

## PostgreSQL Setup

### Installation

```bash
# macOS (Homebrew)
brew install postgresql@14
brew services start postgresql@14

# Ubuntu/Debian
sudo apt-get install postgresql-14 postgresql-contrib-14
sudo systemctl start postgresql

# Verify installation
psql --version  # Should show 14.x or higher
```

### Extension Installation

```bash
# Install pgvector (required for codebase-mcp)
# macOS
brew install pgvector

# Ubuntu/Debian
sudo apt-get install postgresql-14-pgvector

# Verify extension availability
psql -U postgres -c "SELECT * FROM pg_available_extensions WHERE name = 'vector';"
```

### Database Initialization

```bash
# Create MCP user and registry database
psql -U postgres <<EOF
-- Create MCP user
CREATE USER mcp_user WITH PASSWORD 'your_secure_password';

-- Create registry database
CREATE DATABASE mcp_registry OWNER mcp_user;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE mcp_registry TO mcp_user;
ALTER USER mcp_user CREATEDB;  -- Allow creating project databases

-- Connect to registry and create extensions
\c mcp_registry
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
EOF

# Initialize registry schema
psql -U mcp_user -d mcp_registry <<EOF
CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL UNIQUE,
    database_name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by TEXT NOT NULL DEFAULT 'claude-code',

    CONSTRAINT valid_name CHECK (name ~ '^[a-z0-9_]+$'),
    CONSTRAINT valid_db_name CHECK (database_name ~ '^project_[a-z0-9_]+$')
);

CREATE INDEX idx_projects_name ON projects(name);
CREATE INDEX idx_projects_database_name ON projects(database_name);
EOF
```

### Create Example Project Database

```bash
# Create a test project database
psql -U mcp_user -d mcp_registry <<EOF
-- Insert project into registry
INSERT INTO projects (name, database_name, description)
VALUES ('myapp', 'project_myapp', 'Example application project');
EOF

# Create project database with schemas
psql -U postgres <<EOF
CREATE DATABASE project_myapp OWNER mcp_user;
GRANT ALL PRIVILEGES ON DATABASE project_myapp TO mcp_user;
EOF

psql -U mcp_user -d project_myapp <<EOF
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schemas
CREATE SCHEMA IF NOT EXISTS codebase;
CREATE SCHEMA IF NOT EXISTS workflow;

-- Grant permissions
GRANT ALL ON SCHEMA codebase TO mcp_user;
GRANT ALL ON SCHEMA workflow TO mcp_user;
EOF

# Initialize codebase schema (run DDL from database-design.md)
psql -U mcp_user -d project_myapp -f /path/to/create_codebase_schema.sql

# Initialize workflow schema (run DDL from database-design.md)
psql -U mcp_user -d project_myapp -f /path/to/create_workflow_schema.sql
```

## Environment Configuration

### Shared Environment Variables

Both MCPs use the same PostgreSQL connection details:

```bash
# .env (place in workspace root or MCP directories)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=mcp_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_REGISTRY_DB=mcp_registry

# Optional: Logging configuration
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### codebase-mcp Configuration

```bash
# codebase-mcp/.env
MCP_PORT=8001
MCP_NAME=codebase-mcp

# Embedding model configuration
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384

# Indexing configuration
INDEXING_BATCH_SIZE=100
INDEXING_MAX_WORKERS=4
```

### workflow-mcp Configuration

```bash
# workflow-mcp/.env
MCP_PORT=8002
MCP_NAME=workflow-mcp

# Entity validation
ENABLE_STRICT_VALIDATION=true
```

## Port Configuration

### Recommended Ports

- **codebase-mcp**: 8001 (semantic code search)
- **workflow-mcp**: 8002 (AI project management)
- **PostgreSQL**: 5432 (default)

### Firewall Rules

```bash
# Allow local connections only (recommended for development)
# No firewall rules needed for localhost

# Allow remote connections (production)
sudo ufw allow 8001/tcp  # codebase-mcp
sudo ufw allow 8002/tcp  # workflow-mcp
sudo ufw allow 5432/tcp  # PostgreSQL (use with caution)
```

## Running the MCPs

### Manual Startup

#### Terminal 1: Start codebase-mcp

```bash
cd /path/to/codebase-mcp
source .env

# Install dependencies
pip install -r requirements.txt

# Run server
python -m codebase_mcp.server --port 8001
```

Expected output:
```
INFO: Connection manager initialized
INFO: Registry pool connected: mcp_registry
INFO: codebase-mcp listening on http://localhost:8001
INFO: MCP server ready
```

#### Terminal 2: Start workflow-mcp

```bash
cd /path/to/workflow-mcp
source .env

# Install dependencies
pip install -r requirements.txt

# Run server
python -m workflow_mcp.server --port 8002
```

Expected output:
```
INFO: Connection manager initialized
INFO: Registry pool connected: mcp_registry
INFO: workflow-mcp listening on http://localhost:8002
INFO: MCP server ready
```

### Server Implementation

#### codebase-mcp/server.py

```python
"""
MCP server for semantic code search.
"""
import asyncio
import logging
from fastmcp import FastMCP
from .connection_manager import ProjectConnectionManager
from .tools import indexing, search
import os

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastMCP
mcp = FastMCP(
    name="codebase-mcp",
    description="Semantic code search with pgvector embeddings"
)

# Global connection manager
conn_mgr: ProjectConnectionManager = None


@mcp.server.startup()
async def on_startup():
    """Initialize resources on server startup."""
    global conn_mgr

    logger.info("Starting codebase-mcp server")

    # Initialize connection manager
    conn_mgr = ProjectConnectionManager(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "mcp_user"),
        password=os.getenv("POSTGRES_PASSWORD"),
        registry_database=os.getenv("POSTGRES_REGISTRY_DB", "mcp_registry"),
    )
    await conn_mgr.initialize()
    logger.info("Connection manager initialized")

    # Register tools
    indexing.register_tools(mcp, conn_mgr)
    search.register_tools(mcp, conn_mgr)

    logger.info("codebase-mcp server ready")


@mcp.server.shutdown()
async def on_shutdown():
    """Clean up resources on server shutdown."""
    global conn_mgr

    logger.info("Shutting down codebase-mcp server")

    if conn_mgr:
        await conn_mgr.close()
        logger.info("Connection manager closed")

    logger.info("codebase-mcp server stopped")


def main():
    """Run the MCP server."""
    port = int(os.getenv("MCP_PORT", "8001"))
    mcp.run(port=port, transport="sse")


if __name__ == "__main__":
    main()
```

#### workflow-mcp/server.py

```python
"""
MCP server for AI project management.
"""
import asyncio
import logging
from fastmcp import FastMCP
from .connection_manager import ProjectConnectionManager
from .tools import entities, projects
import os

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastMCP
mcp = FastMCP(
    name="workflow-mcp",
    description="AI project management with generic JSONB entities"
)

# Global connection manager
conn_mgr: ProjectConnectionManager = None


@mcp.server.startup()
async def on_startup():
    """Initialize resources on server startup."""
    global conn_mgr

    logger.info("Starting workflow-mcp server")

    # Initialize connection manager
    conn_mgr = ProjectConnectionManager(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_USER", "mcp_user"),
        password=os.getenv("POSTGRES_PASSWORD"),
        registry_database=os.getenv("POSTGRES_REGISTRY_DB", "mcp_registry"),
    )
    await conn_mgr.initialize()
    logger.info("Connection manager initialized")

    # Register tools
    entities.register_tools(mcp, conn_mgr)
    projects.register_tools(mcp, conn_mgr)

    logger.info("workflow-mcp server ready")


@mcp.server.shutdown()
async def on_shutdown():
    """Clean up resources on server shutdown."""
    global conn_mgr

    logger.info("Shutting down workflow-mcp server")

    if conn_mgr:
        await conn_mgr.close()
        logger.info("Connection manager closed")

    logger.info("workflow-mcp server stopped")


def main():
    """Run the MCP server."""
    port = int(os.getenv("MCP_PORT", "8002"))
    mcp.run(port=port, transport="sse")


if __name__ == "__main__":
    main()
```

### Using systemd (Production)

#### /etc/systemd/system/codebase-mcp.service

```ini
[Unit]
Description=Codebase MCP Server
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=mcp_user
WorkingDirectory=/opt/codebase-mcp
EnvironmentFile=/opt/codebase-mcp/.env
ExecStart=/opt/codebase-mcp/venv/bin/python -m codebase_mcp.server
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

#### /etc/systemd/system/workflow-mcp.service

```ini
[Unit]
Description=Workflow MCP Server
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=mcp_user
WorkingDirectory=/opt/workflow-mcp
EnvironmentFile=/opt/workflow-mcp/.env
ExecStart=/opt/workflow-mcp/venv/bin/python -m workflow_mcp.server
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

#### Enable and start services

```bash
sudo systemctl daemon-reload
sudo systemctl enable codebase-mcp workflow-mcp
sudo systemctl start codebase-mcp workflow-mcp

# Check status
sudo systemctl status codebase-mcp
sudo systemctl status workflow-mcp

# View logs
sudo journalctl -u codebase-mcp -f
sudo journalctl -u workflow-mcp -f
```

### Using Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg14
    environment:
      POSTGRES_USER: mcp_user
      POSTGRES_PASSWORD: your_secure_password
      POSTGRES_DB: mcp_registry
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mcp_user -d mcp_registry"]
      interval: 10s
      timeout: 5s
      retries: 5

  codebase-mcp:
    build:
      context: ./codebase-mcp
      dockerfile: Dockerfile
    ports:
      - "8001:8001"
    environment:
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_USER: mcp_user
      POSTGRES_PASSWORD: your_secure_password
      POSTGRES_REGISTRY_DB: mcp_registry
      MCP_PORT: 8001
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

  workflow-mcp:
    build:
      context: ./workflow-mcp
      dockerfile: Dockerfile
    ports:
      - "8002:8002"
    environment:
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_USER: mcp_user
      POSTGRES_PASSWORD: your_secure_password
      POSTGRES_REGISTRY_DB: mcp_registry
      MCP_PORT: 8002
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

volumes:
  postgres_data:
```

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f codebase-mcp
docker-compose logs -f workflow-mcp

# Stop services
docker-compose down
```

## Claude Code Integration

### MCP Configuration

Add both MCPs to Claude Code's MCP configuration:

```json
{
  "mcpServers": {
    "codebase-mcp": {
      "url": "http://localhost:8001",
      "transport": "sse",
      "description": "Semantic code search with pgvector"
    },
    "workflow-mcp": {
      "url": "http://localhost:8002",
      "transport": "sse",
      "description": "AI project management with generic entities"
    }
  }
}
```

### Usage in Claude Code

Claude Code automatically discovers tools from both MCPs:

```
User: Search for authentication logic in the myapp project

Claude: I'll search the codebase for authentication logic.

[Invokes: codebase-mcp.search_code(
    query="authentication logic",
    project_name="myapp",
    limit=10
)]

Results show 8 relevant code chunks...

User: Create a task to fix the auth bug found at line 45

Claude: I'll create a task for the auth bug fix.

[Invokes: workflow-mcp.create_entity(
    project_name="myapp",
    schema_name="task",
    data={
        "title": "Fix authentication bug at line 45",
        "status": "pending",
        "priority": "high"
    }
)]

Task created with ID: abc-123-def-456
```

### Tool Discovery

```bash
# List all available tools
curl http://localhost:8001/tools  # codebase-mcp tools
curl http://localhost:8002/tools  # workflow-mcp tools

# Example output (codebase-mcp)
{
  "tools": [
    {
      "name": "index_repository",
      "description": "Index a code repository for semantic search",
      "parameters": { ... }
    },
    {
      "name": "search_code",
      "description": "Search codebase using semantic similarity",
      "parameters": { ... }
    }
  ]
}

# Example output (workflow-mcp)
{
  "tools": [
    {
      "name": "create_entity",
      "description": "Create a new entity with validation",
      "parameters": { ... }
    },
    {
      "name": "query_entities",
      "description": "Query entities with JSONB filters",
      "parameters": { ... }
    }
  ]
}
```

## Health Monitoring

### Health Check Endpoints

```python
# Add to both MCP servers
@mcp.tool()
async def health_check() -> dict:
    """Check MCP server health."""
    health = await conn_mgr.health_check()
    stats = conn_mgr.get_pool_stats()

    return {
        "status": "healthy" if all(health.values()) else "unhealthy",
        "checks": health,
        "pool_stats": stats,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
```

### Monitoring Script

```bash
#!/bin/bash
# monitor-mcps.sh - Check health of both MCPs

echo "=== MCP Health Check ==="
echo

echo "Codebase MCP (port 8001):"
curl -s http://localhost:8001/health | jq .
echo

echo "Workflow MCP (port 8002):"
curl -s http://localhost:8002/health | jq .
echo

echo "PostgreSQL:"
psql -U mcp_user -d mcp_registry -c "SELECT COUNT(*) as project_count FROM projects;" -t
```

### Prometheus Metrics (Optional)

```python
# Add prometheus-client to requirements.txt
from prometheus_client import Counter, Histogram, start_http_server

# Metrics
tool_calls = Counter('mcp_tool_calls', 'Tool invocations', ['tool_name'])
query_duration = Histogram('mcp_query_duration_seconds', 'Query duration')

# Instrument tools
@mcp.tool()
async def search_code(query: str, project_name: str) -> dict:
    tool_calls.labels(tool_name='search_code').inc()

    with query_duration.time():
        # ... query logic ...
        pass

    return results

# Start metrics server
start_http_server(9090)  # Prometheus metrics on port 9090
```

## Troubleshooting

### Connection Errors

```bash
# Test PostgreSQL connection
psql -U mcp_user -d mcp_registry -c "SELECT 1;"

# Check MCP server logs
tail -f /var/log/codebase-mcp.log
tail -f /var/log/workflow-mcp.log

# Verify ports are listening
netstat -tulpn | grep -E '8001|8002|5432'
```

### Pool Exhaustion

```bash
# Check PostgreSQL connections
psql -U postgres -c "SELECT COUNT(*), state FROM pg_stat_activity GROUP BY state;"

# Check pool stats via health endpoint
curl http://localhost:8001/health | jq .pool_stats
```

### Schema Issues

```bash
# Verify schemas exist
psql -U mcp_user -d project_myapp -c "\dn"

# Verify tables exist
psql -U mcp_user -d project_myapp -c "\dt codebase.*"
psql -U mcp_user -d project_myapp -c "\dt workflow.*"
```

## Performance Tuning

### PostgreSQL Configuration

```ini
# /etc/postgresql/14/main/postgresql.conf

# Connection pooling
max_connections = 200
shared_buffers = 256MB
effective_cache_size = 1GB

# Query performance
random_page_cost = 1.1  # SSD
effective_io_concurrency = 200

# Maintenance
maintenance_work_mem = 256MB
autovacuum = on
```

### Connection Pool Tuning

```python
# Adjust based on project count and workload
conn_mgr = ProjectConnectionManager(
    registry_pool_min=2,
    registry_pool_max=10,
    project_pool_min=1,
    project_pool_max=3,  # Reduce if > 20 projects
)
```

## Security Best Practices

1. **Use strong passwords** for PostgreSQL user
2. **Restrict network access** to localhost in development
3. **Use TLS** for PostgreSQL connections in production
4. **Set environment variables** securely (not in code)
5. **Run MCPs as non-root** user
6. **Enable PostgreSQL SSL** mode: `sslmode=require`
7. **Use connection string with SSL**:
   ```python
   dsn = "postgresql://user:pass@localhost/db?sslmode=require"
   ```

## Summary

This deployment configuration enables:

- **Dual MCP servers** on ports 8001 (codebase) and 8002 (workflow)
- **Shared PostgreSQL** instance with database-per-project isolation
- **Environment-based config** for easy deployment
- **Health monitoring** for production readiness
- **Docker support** for containerized deployment
- **Claude Code integration** with automatic tool discovery
