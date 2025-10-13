# Environment Variables Reference

This section documents all environment variables used by codebase-mcp v2.0, including both core configuration variables from v1.x and new v2.0-specific settings for multi-project workspace support.

## Configuration Table

| Variable Name | Required/Optional | Default Value | Description | Example Value |
|--------------|-------------------|---------------|-------------|---------------|
| `DATABASE_URL` | **Required** | *(none)* | PostgreSQL connection URL with asyncpg driver. Format: `postgresql+asyncpg://user:password@host:port/database`. Must use `asyncpg` driver for async operations. | `postgresql+asyncpg://user:password@localhost:5432/codebase_mcp` |
| `OLLAMA_BASE_URL` | Optional | `http://localhost:11434` | Ollama API base URL for embedding generation. Must be accessible from the server. The Ollama server must be running with the embedding model pulled. | `http://localhost:11434` |
| `OLLAMA_EMBEDDING_MODEL` | Optional | `nomic-embed-text` | Ollama embedding model name. Must be pulled locally using `ollama pull <model>` before use. | `nomic-embed-text` |
| `EMBEDDING_BATCH_SIZE` | Optional | `50` | Number of text chunks to embed per Ollama API request. Larger batches improve throughput but increase latency. Valid range: 1-1000. Recommended: 50-100 for optimal performance. | `50` |
| `MAX_CONCURRENT_REQUESTS` | Optional | `10` | Maximum concurrent AI assistant connections. Limits resource usage under load. Valid range: 1-100. | `10` |
| `DB_POOL_SIZE` | Optional | `20` | SQLAlchemy connection pool size per database. Should accommodate max concurrent AI assistants. Valid range: 5-50. | `20` |
| `DB_MAX_OVERFLOW` | Optional | `10` | Maximum overflow connections beyond pool_size per database. Handles traffic spikes. Valid range: 0-20. | `10` |
| `LOG_LEVEL` | Optional | `INFO` | Logging verbosity level. Valid values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. | `INFO` |
| `LOG_FILE` | Optional | `/tmp/codebase-mcp.log` | File path for structured JSON logs. CRITICAL: Never log to stdout/stderr (MCP protocol violation). | `/tmp/codebase-mcp.log` |
| `WORKFLOW_MCP_URL` **[v2.0]** | Optional | *(none)* | Optional workflow-mcp server URL for automatic project detection. If not set, multi-project workspace features fall back to default workspace. Enables automatic project_id resolution. | `http://localhost:8000` |
| `WORKFLOW_MCP_TIMEOUT` **[v2.0]** | Optional | `1.0` | Timeout for workflow-mcp queries (seconds). Should be low to avoid blocking indexing operations. Valid range: 0.1-5.0. | `1.0` |
| `WORKFLOW_MCP_CACHE_TTL` **[v2.0]** | Optional | `60` | Cache TTL for workflow-mcp responses (seconds). Reduces query overhead for repeated repository checks. Valid range: 10-300. | `60` |

## Version Notes

### New in v2.0

The following environment variables are **new in v2.0** and support multi-project workspace isolation and workflow-mcp integration:

- **`WORKFLOW_MCP_URL`**: Enables optional integration with workflow-mcp for automatic project context detection
- **`WORKFLOW_MCP_TIMEOUT`**: Controls timeout behavior for workflow-mcp queries to prevent blocking
- **`WORKFLOW_MCP_CACHE_TTL`**: Optimizes repeated workflow-mcp queries with TTL-based caching

### Changed in v2.0

- **`DB_POOL_SIZE`**: Applies per-database in v2.0 (each project workspace has its own connection pool)
- **`DB_MAX_OVERFLOW`**: Applies per-database in v2.0 (overflow connections are per-workspace)

### Unchanged from v1.x

The following core variables remain unchanged in v2.0:
- `DATABASE_URL`
- `OLLAMA_BASE_URL`
- `OLLAMA_EMBEDDING_MODEL`
- `EMBEDDING_BATCH_SIZE`
- `MAX_CONCURRENT_REQUESTS`
- `LOG_LEVEL`
- `LOG_FILE`

## Configuration Examples

### Minimal Configuration (v2.0)
```bash
# .env file - bare minimum
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/codebase_mcp
```

### Production Configuration (v2.0)
```bash
# .env file - production deployment with workflow-mcp integration
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/codebase_mcp
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_BATCH_SIZE=100
MAX_CONCURRENT_REQUESTS=20
DB_POOL_SIZE=30
DB_MAX_OVERFLOW=15
LOG_LEVEL=INFO
LOG_FILE=/var/log/codebase-mcp/server.log
WORKFLOW_MCP_URL=http://localhost:8000
WORKFLOW_MCP_TIMEOUT=2.0
WORKFLOW_MCP_CACHE_TTL=120
```

### Development Configuration (v2.0)
```bash
# .env file - local development with debug logging
DATABASE_URL=postgresql+asyncpg://localhost/codebase_mcp_dev
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_BATCH_SIZE=50
MAX_CONCURRENT_REQUESTS=5
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=5
LOG_LEVEL=DEBUG
LOG_FILE=/tmp/codebase-mcp-dev.log
```

## Validation

To validate your environment configuration, use the following command:

```bash
# Test configuration loading
python -c "from src.config.settings import get_settings; print(get_settings())"
```

If validation fails, check:
1. `DATABASE_URL` uses `postgresql+asyncpg://` scheme (not `postgresql://`)
2. All numeric values are within valid ranges
3. File paths exist and are writable (for `LOG_FILE`)
4. Required variables are set (only `DATABASE_URL` is required)

## Migration Notes (v1.x → v2.0)

When upgrading from v1.x to v2.0:

1. **No action required** for existing environment variables - all v1.x variables work in v2.0
2. **Optional**: Add `WORKFLOW_MCP_URL` to enable automatic project detection (advanced use case)
3. **Note**: `DB_POOL_SIZE` and `DB_MAX_OVERFLOW` now apply per-database in multi-project setups
4. **Calculate**: Total PostgreSQL connections = `(number_of_projects × DB_POOL_SIZE) + (number_of_projects × DB_MAX_OVERFLOW)` in multi-project deployments

See the Migration Guide for complete upgrade instructions.
