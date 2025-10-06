# Troubleshooting Guide

Comprehensive troubleshooting guide for common issues with the Codebase MCP Server.

## Table of Contents

1. [Database Issues](#database-issues)
2. [Ollama Issues](#ollama-issues)
3. [Performance Issues](#performance-issues)
4. [MCP Protocol Issues](#mcp-protocol-issues)
5. [Configuration Issues](#configuration-issues)
6. [File System Issues](#file-system-issues)
7. [Logging and Debugging](#logging-and-debugging)
8. [Recovery Procedures](#recovery-procedures)
9. [Monitoring and Health Checks](#monitoring-and-health-checks)
10. [Getting Help](#getting-help)

---

## Database Issues

### Connection Refused

**Symptoms:**
- Error: `connection refused` or `could not connect to server`
- Server fails to start with database error
- Health check shows database as "disconnected"

**Solutions:**

1. **Check PostgreSQL is running:**
```bash
# Check status
sudo systemctl status postgresql
# or
pg_ctl status

# Start PostgreSQL
sudo systemctl start postgresql
# or
pg_ctl start
```

2. **Verify connection parameters:**
```bash
# Test connection
psql -d postgresql://user:password@localhost:5432/codebase_mcp

# Check environment variable
echo $DATABASE_URL
```

3. **Check PostgreSQL logs:**
```bash
# Ubuntu/Debian
tail -f /var/log/postgresql/postgresql-14-main.log

# macOS
tail -f /usr/local/var/log/postgresql@14.log
```

### pgvector Extension Not Found

**Symptoms:**
- Error: `extension "vector" does not exist`
- Error: `type "vector" does not exist`

**Solutions:**

1. **Install pgvector:**
```bash
# Ubuntu/Debian
sudo apt install postgresql-14-pgvector

# macOS
brew install pgvector

# From source
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

2. **Enable extension in database:**
```sql
-- Connect as superuser
psql -U postgres -d codebase_mcp

-- Create extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
\dx vector
```

3. **Check extension is available:**
```sql
SELECT * FROM pg_available_extensions WHERE name = 'vector';
```

### Migration Failures

**Symptoms:**
- Error: `alembic.util.exc.CommandError`
- Database schema out of sync
- Tables or columns missing

**Solutions:**

1. **Check current migration status:**
```bash
alembic current
```

2. **Reset to specific revision:**
```bash
# Downgrade to previous
alembic downgrade -1

# Upgrade to latest
alembic upgrade head
```

3. **Force recreation (CAUTION - data loss):**
```bash
# Drop all tables
psql -d codebase_mcp -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Reinitialize
python scripts/init_db.py
```

### Connection Pool Exhausted

**Symptoms:**
- Error: `QueuePool limit of size N overflow N reached`
- Intermittent connection timeouts
- Slow response times

**Solutions:**

1. **Increase pool size in .env:**
```bash
DATABASE_POOL_SIZE=40
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_TIMEOUT=60
```

2. **Check for connection leaks:**
```sql
-- View active connections
SELECT pid, usename, application_name, state, query_start
FROM pg_stat_activity
WHERE datname = 'codebase_mcp';

-- Kill idle connections
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'codebase_mcp' AND state = 'idle' AND query_start < now() - interval '10 minutes';
```

3. **Restart application to reset pool:**
```bash
pkill -f "uvicorn src.main"
uvicorn src.main:app --reload
```

### Slow Queries

**Symptoms:**
- Search operations taking >500ms
- Indexing taking >60s for small repositories
- Database CPU usage high

**Solutions:**

1. **Check missing indexes:**
```sql
-- List all indexes
\di

-- Create missing vector index
CREATE INDEX ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create missing btree indexes
CREATE INDEX ON files(repository_id);
CREATE INDEX ON chunks(file_id);
CREATE INDEX ON tasks(status, created_at);
```

2. **Analyze query performance:**
```sql
-- Enable query timing
\timing on

-- Explain query plan
EXPLAIN ANALYZE SELECT * FROM chunks ORDER BY embedding <=> '[...]' LIMIT 10;
```

3. **Tune PostgreSQL:**
```sql
-- Increase work memory
ALTER SYSTEM SET work_mem = '256MB';
ALTER SYSTEM SET shared_buffers = '1GB';
ALTER SYSTEM SET effective_cache_size = '3GB';
SELECT pg_reload_conf();
```

---

## Ollama Issues

### Ollama Not Running

**Symptoms:**
- Error: `Connection refused` to Ollama
- Error: `Failed to connect to localhost:11434`

**Solutions:**

1. **Start Ollama service:**
```bash
# Start Ollama
ollama serve

# Or as background service
nohup ollama serve > /tmp/ollama.log 2>&1 &

# Check if running
curl http://localhost:11434/api/tags
```

2. **Check Ollama logs:**
```bash
# View logs
tail -f ~/.ollama/logs/server.log

# Check for port conflicts
lsof -i :11434
```

3. **Restart Ollama:**
```bash
# Kill existing process
pkill ollama

# Start fresh
ollama serve
```

### Model Not Found

**Symptoms:**
- Error: `model 'nomic-embed-text' not found`
- Embedding generation fails

**Solutions:**

1. **Pull the model:**
```bash
# Download model
ollama pull nomic-embed-text

# Verify installation
ollama list | grep nomic-embed-text
```

2. **Check model size and disk space:**
```bash
# Check disk space
df -h ~/.ollama

# Model size
du -sh ~/.ollama/models/manifests/registry.ollama.ai/library/nomic-embed-text
```

3. **Try alternative model:**
```bash
# Edit .env
OLLAMA_EMBEDDING_MODEL=all-minilm

# Pull alternative
ollama pull all-minilm
```

### Timeout Errors

**Symptoms:**
- Error: `Read timeout` during embedding generation
- Slow indexing performance

**Solutions:**

1. **Increase timeout in code:**
```python
# In src/services/embedder.py
timeout = httpx.Timeout(60.0, connect=10.0)
```

2. **Reduce batch size:**
```bash
# In .env
EMBEDDING_BATCH_SIZE=25  # Reduce from 50
```

3. **Check Ollama performance:**
```bash
# Test embedding speed
time curl -X POST http://localhost:11434/api/embeddings \
  -H "Content-Type: application/json" \
  -d '{"model": "nomic-embed-text", "prompt": "test text"}'
```

### Embedding Generation Slow

**Symptoms:**
- Indexing takes longer than expected
- High CPU/GPU usage

**Solutions:**

1. **Use GPU acceleration (if available):**
```bash
# Check CUDA availability
nvidia-smi

# Set GPU for Ollama
export CUDA_VISIBLE_DEVICES=0
ollama serve
```

2. **Optimize batch processing:**
```bash
# Adjust batch size based on available memory
EMBEDDING_BATCH_SIZE=100  # For GPU
EMBEDDING_BATCH_SIZE=25   # For CPU
```

3. **Monitor resource usage:**
```bash
# Monitor GPU
watch -n 1 nvidia-smi

# Monitor CPU
htop
```

---

## Performance Issues

### Indexing Too Slow

**Symptoms:**
- Indexing takes >60s for 10K files
- Progress seems stuck

**Solutions:**

1. **Optimize file scanning:**
```bash
# Check for large ignored files
find /path/to/repo -size +10M -type f

# Ensure .gitignore is respected
cat /path/to/repo/.gitignore
```

2. **Parallel processing:**
```python
# Increase concurrent requests in .env
MAX_CONCURRENT_REQUESTS=20  # Default is 10
```

3. **Monitor bottlenecks:**
```bash
# Check I/O wait
iostat -x 1

# Check network (for remote repos)
iftop
```

### Search Too Slow

**Symptoms:**
- Search queries take >500ms
- Timeout errors on search

**Solutions:**

1. **Optimize vector index:**
```sql
-- Recreate index with more lists for larger datasets
DROP INDEX IF EXISTS chunks_embedding_idx;
CREATE INDEX chunks_embedding_idx ON chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 200);  -- Increase for larger datasets

-- Analyze table
ANALYZE chunks;
```

2. **Limit search scope:**
```python
# Add filters to reduce search space
{
    "query": "authentication",
    "repository_id": "specific-repo-id",
    "file_type": "py",
    "limit": 10
}
```

3. **Check vector dimension:**
```sql
-- Verify embedding dimensions match
SELECT vector_dims(embedding) FROM chunks LIMIT 1;
```

### Memory Usage High

**Symptoms:**
- Server consuming >2GB RAM
- Out of memory errors
- System becoming unresponsive

**Solutions:**

1. **Reduce batch sizes:**
```bash
EMBEDDING_BATCH_SIZE=25
DATABASE_POOL_SIZE=10
```

2. **Enable memory profiling:**
```bash
# Install memory profiler
pip install memory_profiler

# Run with profiling
python -m memory_profiler src/main.py
```

3. **Check for memory leaks:**
```python
# Add garbage collection
import gc
gc.collect()

# Monitor object counts
import objgraph
objgraph.show_most_common_types()
```

### CPU Usage High

**Symptoms:**
- Constant high CPU usage
- System responsiveness degraded

**Solutions:**

1. **Profile CPU usage:**
```bash
# Install py-spy
pip install py-spy

# Profile running process
py-spy top --pid $(pgrep -f "uvicorn src.main")
```

2. **Optimize tree-sitter parsing:**
```python
# Cache parsers in memory
# Reuse parser instances
```

3. **Limit concurrent operations:**
```bash
MAX_CONCURRENT_REQUESTS=5  # Reduce from 10
```

---

## MCP Protocol Issues

### SSE Connection Failures

**Symptoms:**
- Client can't establish SSE connection
- Connection drops frequently

**Solutions:**

1. **Check server is responding:**
```bash
# Test SSE endpoint
curl -N http://localhost:3000/sse

# Test with headers
curl -H "Accept: text/event-stream" http://localhost:3000/sse
```

2. **Nginx/proxy configuration (if using):**
```nginx
location /sse {
    proxy_pass http://localhost:3000;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_buffering off;
    proxy_cache off;
}
```

3. **Firewall/network issues:**
```bash
# Check port is open
netstat -an | grep 3000

# Test from client machine
telnet server-ip 3000
```

### Tool Execution Timeout

**Symptoms:**
- Tools timing out before completion
- Partial results returned

**Solutions:**

1. **Increase timeout settings:**
```python
# In MCP handler
TOOL_TIMEOUT = 120  # seconds
```

2. **Optimize long-running operations:**
```python
# Add progress reporting
async def index_repository(...):
    yield {"progress": 0.5, "message": "Scanning files..."}
```

### Invalid Request Format

**Symptoms:**
- Error: `Invalid JSON-RPC request`
- Error code -32600 or -32602

**Solutions:**

1. **Validate request structure:**
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "tool_name",
    "arguments": {}
  },
  "id": "unique-id"
}
```

2. **Check required fields:**
```python
# Ensure all required fields present
required_fields = ["jsonrpc", "method", "params", "id"]
```

3. **Validate arguments against schema:**
```python
# Use jsonschema validation
from jsonschema import validate
validate(arguments, tool_schema)
```

### Error Responses Not Understood

**Symptoms:**
- Client can't parse error responses
- Errors shown as generic messages

**Solutions:**

1. **Follow JSON-RPC error format:**
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32603,
    "message": "Internal error",
    "data": "Detailed error information"
  },
  "id": "request-id"
}
```

2. **Include helpful error data:**
```python
return {
    "error": {
        "code": -32000,
        "message": "Database error",
        "data": {
            "details": str(exception),
            "type": "PostgreSQLError",
            "query": failed_query
        }
    }
}
```

---

## Configuration Issues

### Invalid DATABASE_URL Format

**Symptoms:**
- Error parsing DATABASE_URL
- Connection string errors

**Solutions:**

1. **Correct format:**
```bash
# PostgreSQL with asyncpg
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database

# Examples
DATABASE_URL=postgresql+asyncpg://postgres:secret@localhost:5432/codebase_mcp
DATABASE_URL=postgresql+asyncpg://localhost/codebase_mcp  # Uses peer auth
```

2. **URL encode special characters:**
```python
from urllib.parse import quote_plus
password = quote_plus("p@ssw#rd!")
url = f"postgresql+asyncpg://user:{password}@localhost/db"
```

3. **Test connection:**
```python
import asyncpg
import asyncio

async def test():
    conn = await asyncpg.connect('postgresql://localhost/codebase_mcp')
    print(await conn.fetchval('SELECT 1'))
    await conn.close()

asyncio.run(test())
```

### Missing Environment Variables

**Symptoms:**
- KeyError for environment variables
- Using default values unexpectedly

**Solutions:**

1. **Check .env file exists:**
```bash
ls -la .env
cat .env
```

2. **Verify variables are set:**
```bash
# Check all environment variables
env | grep -E "(DATABASE|OLLAMA|LOG)"

# Source .env manually
export $(cat .env | xargs)
```

3. **Use python-dotenv:**
```python
from dotenv import load_dotenv
load_dotenv()  # Load from .env file
```

### Invalid Settings Values

**Symptoms:**
- Validation errors on startup
- Settings not taking effect

**Solutions:**

1. **Check value types:**
```bash
# Numbers should not have quotes
EMBEDDING_BATCH_SIZE=50  # Correct
EMBEDDING_BATCH_SIZE="50"  # May cause issues

# Booleans
LOG_JSON=true  # Correct
LOG_JSON=True  # Incorrect
```

2. **Validate ranges:**
```bash
# Check constraints
EMBEDDING_BATCH_SIZE=200  # May be too large
DATABASE_POOL_SIZE=100  # May exceed PostgreSQL max_connections
```

### .env Not Loading

**Symptoms:**
- Environment variables not found
- Using defaults despite .env file

**Solutions:**

1. **Check working directory:**
```bash
# Run from project root
cd /path/to/codebase-mcp
python -m src.main
```

2. **Explicit loading:**
```python
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)
```

3. **Check file permissions:**
```bash
chmod 600 .env  # Readable by owner only
```

---

## File System Issues

### Repository Path Not Found

**Symptoms:**
- Error: `Repository path does not exist`
- Indexing fails immediately

**Solutions:**

1. **Verify path exists:**
```bash
ls -la /path/to/repository
```

2. **Check for symlinks:**
```bash
# Resolve symlinks
readlink -f /path/to/repository
```

3. **Use absolute paths:**
```python
from pathlib import Path
repo_path = Path(user_input).resolve()
if not repo_path.exists():
    raise ValueError(f"Path does not exist: {repo_path}")
```

### Permission Denied

**Symptoms:**
- Error reading files during indexing
- Partial indexing results

**Solutions:**

1. **Check file permissions:**
```bash
# Find files without read permission
find /repo -type f ! -readable

# Fix permissions
chmod -R u+r /repo
```

2. **Run as appropriate user:**
```bash
# Check current user
whoami

# Switch user if needed
su - appropriate_user
```

3. **Handle permission errors gracefully:**
```python
try:
    content = file_path.read_text()
except PermissionError:
    logger.warning(f"Permission denied: {file_path}")
    continue
```

### .gitignore Not Working

**Symptoms:**
- Ignored files being indexed
- node_modules, .git included

**Solutions:**

1. **Verify .gitignore parsing:**
```python
from pathspec import PathSpec
gitignore = PathSpec.from_lines('gitwildmatch',
                                Path('.gitignore').read_text().splitlines())
if gitignore.match_file(file_path):
    continue  # Skip ignored file
```

2. **Check .gitignore syntax:**
```bash
# Common patterns
node_modules/
*.pyc
__pycache__/
.env
```

3. **Debug pattern matching:**
```python
import logging
logging.getLogger('pathspec').setLevel(logging.DEBUG)
```

### File Scanning Errors

**Symptoms:**
- Crashes on certain files
- Unicode decode errors

**Solutions:**

1. **Handle encoding errors:**
```python
try:
    content = file_path.read_text(encoding='utf-8')
except UnicodeDecodeError:
    # Try alternative encoding
    content = file_path.read_text(encoding='latin-1', errors='ignore')
```

2. **Skip binary files:**
```python
import mimetypes
mime_type, _ = mimetypes.guess_type(file_path)
if mime_type and not mime_type.startswith('text/'):
    continue  # Skip binary file
```

3. **File size limits:**
```python
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
if file_path.stat().st_size > MAX_FILE_SIZE:
    logger.warning(f"File too large: {file_path}")
    continue
```

---

## Logging and Debugging

### Where Logs Are Located

**Default locations:**
```bash
# Application log (configured in .env)
/tmp/codebase-mcp.log

# PostgreSQL logs
/var/log/postgresql/postgresql-14-main.log  # Ubuntu/Debian
/usr/local/var/log/postgresql@14.log  # macOS

# Ollama logs
~/.ollama/logs/server.log
```

### How to Increase Log Level

1. **Set in .env:**
```bash
LOG_LEVEL=DEBUG  # Options: DEBUG, INFO, WARNING, ERROR
```

2. **Set at runtime:**
```bash
LOG_LEVEL=DEBUG uvicorn src.main:app
```

3. **In code:**
```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)
```

### Understanding Log Format

**Standard format:**
```
2024-01-15 10:30:45.123 [INFO] [correlation_id] [module] Message
```

**With stack trace:**
```
2024-01-15 10:30:45.123 [ERROR] [abc-123] [searcher] Search failed
Traceback (most recent call last):
  File "searcher.py", line 45, in search
    ...
Exception: Database connection lost
```

### Common Log Patterns for Issues

**Database issues:**
```bash
grep -i "error.*database\|connection.*refused\|pool.*exhausted" /tmp/codebase-mcp.log
```

**Ollama issues:**
```bash
grep -i "ollama\|embedding.*failed\|timeout" /tmp/codebase-mcp.log
```

**Performance issues:**
```bash
grep "latency_ms" /tmp/codebase-mcp.log | awk '{print $NF}' | sort -n | tail -20
```

### Using Correlation IDs

**Track request flow:**
```bash
# Find all logs for a request
grep "correlation_id=abc-123" /tmp/codebase-mcp.log

# Extract correlation IDs with errors
grep ERROR /tmp/codebase-mcp.log | grep -o "correlation_id=[^ ]*"
```

**Add correlation ID in code:**
```python
import uuid
correlation_id = str(uuid.uuid4())
logger = logging.getLogger(__name__)
logger = logging.LoggerAdapter(logger, {'correlation_id': correlation_id})
```

---

## Recovery Procedures

### Database Corruption

**Symptoms:**
- Inconsistent query results
- Crashes during queries
- Index errors

**Recovery steps:**

1. **Backup current state:**
```bash
pg_dump codebase_mcp > backup_$(date +%Y%m%d).sql
```

2. **Check database integrity:**
```sql
-- Check for corruption
REINDEX DATABASE codebase_mcp;

-- Vacuum and analyze
VACUUM FULL ANALYZE;
```

3. **Restore from backup if needed:**
```bash
# Create new database
createdb codebase_mcp_new

# Restore
psql codebase_mcp_new < backup.sql

# Rename databases
psql -c "ALTER DATABASE codebase_mcp RENAME TO codebase_mcp_old"
psql -c "ALTER DATABASE codebase_mcp_new RENAME TO codebase_mcp"
```

### Migration Rollback

**When to rollback:**
- Migration fails partially
- Schema changes cause issues
- Need to revert to previous version

**Rollback procedure:**

1. **Check current state:**
```bash
alembic current
alembic history
```

2. **Rollback to previous:**
```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade abc123

# Rollback all
alembic downgrade base
```

3. **Fix and retry:**
```bash
# Edit migration file if needed
vim alembic/versions/xxx_migration.py

# Retry upgrade
alembic upgrade head
```

### Index Corruption

**Symptoms:**
- Search returns wrong results
- Vector similarity scores incorrect

**Recovery steps:**

1. **Drop and recreate indexes:**
```sql
-- Drop vector index
DROP INDEX chunks_embedding_idx;

-- Recreate
CREATE INDEX chunks_embedding_idx ON chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Reindex all
REINDEX TABLE chunks;
```

2. **Verify embeddings:**
```sql
-- Check embedding dimensions
SELECT COUNT(*), vector_dims(embedding)
FROM chunks
GROUP BY vector_dims(embedding);

-- Should all be same dimension (e.g., 768)
```

### Clearing Cache

**When to clear:**
- Stale search results
- After major updates
- Testing changes

**Clear procedures:**

1. **Application cache:**
```python
# No built-in cache, but if added:
cache.clear()
```

2. **Database query cache:**
```sql
-- Clear PostgreSQL cache
DISCARD ALL;

-- Reset query statistics
SELECT pg_stat_reset();
```

3. **Ollama model cache:**
```bash
# Restart Ollama
pkill ollama
ollama serve
```

### Fresh Start Procedure

**Complete reset for major issues:**

1. **Stop all services:**
```bash
# Stop application
pkill -f "uvicorn src.main"

# Stop Ollama
pkill ollama

# Stop PostgreSQL (optional)
sudo systemctl stop postgresql
```

2. **Clean database:**
```bash
# Drop and recreate database
psql -U postgres << EOF
DROP DATABASE IF EXISTS codebase_mcp;
CREATE DATABASE codebase_mcp;
EOF

# Add vector extension
psql -U postgres -d codebase_mcp -c "CREATE EXTENSION vector;"
```

3. **Reinitialize:**
```bash
# Clean Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Initialize database
python scripts/init_db.py

# Start services
ollama serve &
uvicorn src.main:app
```

---

## Monitoring and Health Checks

### Health Check Endpoint

**Basic health check:**
```bash
curl http://localhost:3000/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "ollama": "connected",
  "version": "0.1.0",
  "uptime_seconds": 3600
}
```

**Automated monitoring:**
```bash
# Simple monitoring script
while true; do
    if ! curl -f http://localhost:3000/health > /dev/null 2>&1; then
        echo "Health check failed at $(date)"
        # Send alert or restart service
    fi
    sleep 60
done
```

### Database Connection Health

**Check connections:**
```sql
-- Active connections
SELECT count(*) FROM pg_stat_activity
WHERE datname = 'codebase_mcp';

-- Connection states
SELECT state, count(*)
FROM pg_stat_activity
WHERE datname = 'codebase_mcp'
GROUP BY state;
```

**Monitor connection pool:**
```python
# In application
from src.database import db
pool_status = db.pool.status()
logger.info(f"Pool: {pool_status}")
```

### Ollama Connection Health

**Check Ollama status:**
```bash
# API check
curl http://localhost:11434/api/tags

# Model check
curl -X POST http://localhost:11434/api/generate \
  -d '{"model": "nomic-embed-text", "prompt": "test"}'
```

**Monitor response times:**
```bash
# Time embedding generation
time curl -X POST http://localhost:11434/api/embeddings \
  -d '{"model": "nomic-embed-text", "prompt": "test text"}'
```

### Performance Metrics

**Database metrics:**
```sql
-- Slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE mean_exec_time > 100
ORDER BY mean_exec_time DESC;

-- Cache hit ratio
SELECT
    sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as cache_hit_ratio
FROM pg_statio_user_tables;
```

**Application metrics:**
```python
# Add to application
import time
import psutil

start_time = time.time()
process = psutil.Process()

def get_metrics():
    return {
        "uptime": time.time() - start_time,
        "memory_mb": process.memory_info().rss / 1024 / 1024,
        "cpu_percent": process.cpu_percent(),
        "num_threads": process.num_threads()
    }
```

### Alert Thresholds

**Recommended thresholds:**

| Metric | Warning | Critical |
|--------|---------|----------|
| Search latency | >400ms | >500ms |
| Index time (10K files) | >50s | >60s |
| Database connections | >80% pool | >95% pool |
| Memory usage | >1.5GB | >2GB |
| CPU usage | >70% | >90% |
| Error rate | >1% | >5% |
| Ollama timeout | >30s | >60s |

**Setting up alerts:**
```bash
# Example alert script
#!/bin/bash
THRESHOLD=500
LATENCY=$(grep "search_code.*latency_ms" /tmp/codebase-mcp.log | tail -1 | awk '{print $NF}')

if [ "$LATENCY" -gt "$THRESHOLD" ]; then
    echo "ALERT: Search latency $LATENCY ms exceeds threshold $THRESHOLD ms"
    # Send notification (email, Slack, etc.)
fi
```

---

## Getting Help

### Logs to Include

When reporting issues, include:

1. **Application logs:**
```bash
# Last 100 lines with errors
grep -E "ERROR|CRITICAL" /tmp/codebase-mcp.log | tail -100

# Full log for correlation ID
grep "correlation_id=problematic-request-id" /tmp/codebase-mcp.log
```

2. **Database logs:**
```bash
# PostgreSQL errors
sudo grep ERROR /var/log/postgresql/postgresql-14-main.log | tail -50
```

3. **System information:**
```bash
# One-liner to collect info
echo "=== System Info ===" && \
uname -a && \
echo "=== Python Version ===" && \
python --version && \
echo "=== PostgreSQL Version ===" && \
psql --version && \
echo "=== Installed Packages ===" && \
pip freeze | grep -E "fastapi|sqlalchemy|pgvector|mcp|pydantic" && \
echo "=== Disk Space ===" && \
df -h && \
echo "=== Memory ===" && \
free -h
```

### System Information to Provide

**Environment details:**
```bash
# Create diagnostic report
cat > diagnostic_report.txt << EOF
Date: $(date)
Hostname: $(hostname)
OS: $(uname -srm)
Python: $(python --version 2>&1)
PostgreSQL: $(psql --version)
Ollama: $(ollama --version 2>&1)

Environment Variables:
$(env | grep -E "DATABASE|OLLAMA|LOG" | sed 's/password=.*/password=***/')

Database Status:
$(psql -d codebase_mcp -c "SELECT version();" 2>&1)
$(psql -d codebase_mcp -c "SELECT * FROM pg_available_extensions WHERE name='vector';" 2>&1)

Ollama Status:
$(curl -s http://localhost:11434/api/tags | head -20)

Recent Errors:
$(grep ERROR /tmp/codebase-mcp.log | tail -10)
EOF
```

### Issue Reporting Guidelines

**Good issue report includes:**

1. **Clear description:**
   - What you were trying to do
   - What happened instead
   - What you expected to happen

2. **Reproduction steps:**
   - Exact commands run
   - Input data used
   - Configuration settings

3. **Error messages:**
   - Complete error message
   - Stack trace if available
   - Correlation ID

4. **Context:**
   - Recent changes made
   - When issue started
   - Frequency of occurrence

5. **Attempted solutions:**
   - What you've already tried
   - Temporary workarounds found

**Example issue template:**
```markdown
### Description
Search queries timeout when repository has >10,000 files

### Steps to Reproduce
1. Index large repository: `{"tool": "index_repository", "arguments": {"path": "/large/repo"}}`
2. Search for common term: `{"tool": "search_code", "arguments": {"query": "function"}}`
3. Request times out after 30 seconds

### Expected Behavior
Search should return within 500ms

### Actual Behavior
Request times out with error: "Operation timed out"

### Environment
- OS: Ubuntu 22.04
- Python: 3.11.5
- PostgreSQL: 14.9
- codebase-mcp: 0.1.0
- Repository size: 15,000 files

### Logs
[Attach relevant logs]

### Attempted Solutions
- Increased DATABASE_POOL_SIZE to 50
- Rebuilt vector index with more lists
- Still experiencing timeouts
```

---

## Quick Reference

### Common Commands

```bash
# Service management
uvicorn src.main:app --reload          # Start dev server
pkill -f "uvicorn src.main"           # Stop server
ollama serve                          # Start Ollama
psql -d codebase_mcp                  # Database console

# Diagnostics
curl http://localhost:3000/health     # Health check
alembic current                       # Migration status
tail -f /tmp/codebase-mcp.log        # Watch logs

# Database
psql -c "SELECT count(*) FROM chunks" # Count chunks
psql -c "VACUUM ANALYZE chunks"       # Optimize table
psql -c "REINDEX TABLE chunks"        # Rebuild indexes

# Testing
pytest tests/unit -v                  # Run unit tests
pytest tests/integration -v           # Run integration tests
pytest --cov=src                      # With coverage
```

### Environment Variables

```bash
# Essential
DATABASE_URL=postgresql+asyncpg://localhost/codebase_mcp
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Performance
EMBEDDING_BATCH_SIZE=50
MAX_CONCURRENT_REQUESTS=10
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Logging
LOG_LEVEL=INFO
LOG_FILE=/tmp/codebase-mcp.log
```

### Key File Locations

```
/tmp/codebase-mcp.log              # Application logs
~/.ollama/                         # Ollama data
/var/lib/postgresql/14/main/       # PostgreSQL data
.env                                # Configuration
alembic.ini                         # Migration config
pyproject.toml                      # Project config
```