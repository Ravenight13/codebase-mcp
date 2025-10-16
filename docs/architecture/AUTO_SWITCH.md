# Auto-Switch Architecture

## Overview

The Auto-Switch architecture enables automatic project workspace switching based on directory context, allowing multiple Claude Code instances and users to work on different projects simultaneously using a shared MCP server.

## Core Principles

1. **Zero Configuration Overhead**: Projects auto-switch based on `.codebase-mcp/config.json` files
2. **Session Isolation**: Each MCP client connection maintains independent state
3. **Performance First**: Sub-50ms config discovery with intelligent caching
4. **Graceful Fallback**: 4-tier resolution chain ensures operations always succeed

## Architecture Components

### Component Diagram

```mermaid
graph TB
    subgraph "MCP Clients"
        C1[Claude Code Instance A]
        C2[Claude Code Instance B]
        C3[VS Code MCP Extension]
    end

    subgraph "Codebase MCP Server"
        SM[Session Manager]
        CR[Config Resolver]
        CC[Config Cache]
        PS[Project Switcher]

        subgraph "Tool Handlers"
            IR[index_repository]
            SC[search_code]
            SWD[set_working_directory]
        end
    end

    subgraph "External Integration"
        WF[workflow-mcp Server]
    end

    subgraph "Storage"
        PG[(PostgreSQL)]
        FS[File System<br/>.codebase-mcp/config.json]
    end

    C1 -->|set_working_directory| SM
    C2 -->|set_working_directory| SM
    C3 -->|set_working_directory| SM

    SM -->|session_id| CR
    CR -->|1. Check Cache| CC
    CR -->|2. Read Config| FS
    CR -->|3. Query workflow-mcp| WF
    CR -->|4. Default| PS

    PS -->|Switch Schema| PG
    IR -->|Use Project| PG
    SC -->|Use Project| PG
```

## Resolution Chain Flow

The project resolution follows a 4-tier priority system:

### Tier 1: Explicit Parameter (Highest Priority)
```python
# Always takes precedence
await index_repository(
    repo_path="/path/to/repo",
    project_id="explicit-project-id"  # <-- Tier 1
)
```

### Tier 2: Session-Based Config
```python
# Set once per session
await set_working_directory(directory="/Users/alice/project-a")

# Auto-discovers .codebase-mcp/config.json
# Searches up to 20 parent directories
# Cached with mtime-based invalidation
```

**Discovery Algorithm:**
```python
def discover_config(start_dir: Path) -> Optional[Config]:
    current = start_dir
    for _ in range(20):  # Max 20 levels
        config_path = current / ".codebase-mcp" / "config.json"
        if config_path.exists():
            return load_config(config_path)
        if current.parent == current:  # Root reached
            break
        current = current.parent
    return None
```

### Tier 3: workflow-mcp Integration
```python
# External project tracking
response = await workflow_client.get_active_project()
if response and response.project_id:
    return response.project_id
```

### Tier 4: Default Workspace
```python
# Fallback when no other resolution succeeds
return "project_default"
```

## Session Isolation

Each MCP client connection maintains an isolated session:

```python
class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, SessionState] = {}

    async def set_working_directory(
        self,
        session_id: str,
        directory: Path
    ) -> None:
        """Each session has independent working directory"""
        self.sessions[session_id] = SessionState(
            working_dir=directory,
            created_at=datetime.now(),
            last_accessed=datetime.now()
        )
```

**Key Properties:**
- Sessions identified by unique MCP connection ID
- No cross-contamination between concurrent clients
- Automatic cleanup of stale sessions (>24h inactive)
- Thread-safe operations with async locks

## Cache Architecture

### Config Cache Design

```python
@dataclass
class CacheEntry:
    config: ProjectConfig
    file_path: Path
    mtime: float  # File modification time
    last_checked: datetime

class ConfigCache:
    def __init__(self):
        self.entries: Dict[Path, CacheEntry] = {}
        self.max_age = timedelta(minutes=5)

    def is_valid(self, entry: CacheEntry) -> bool:
        # Check file modification time
        current_mtime = entry.file_path.stat().st_mtime
        if current_mtime != entry.mtime:
            return False

        # Check cache age
        age = datetime.now() - entry.last_checked
        return age < self.max_age
```

**Cache Invalidation Strategy:**
1. **mtime-based**: Detects file modifications instantly
2. **Time-based**: Re-validates after 5 minutes
3. **Memory-bounded**: LRU eviction after 1000 entries
4. **Thread-safe**: Async locks prevent race conditions

## Background Cleanup Process

```python
class BackgroundCleaner:
    async def cleanup_loop(self):
        """Runs every hour"""
        while True:
            await asyncio.sleep(3600)  # 1 hour

            # Remove stale sessions (>24h inactive)
            cutoff = datetime.now() - timedelta(hours=24)
            stale = [
                sid for sid, state in sessions.items()
                if state.last_accessed < cutoff
            ]

            for session_id in stale:
                del sessions[session_id]
                logger.info(f"Cleaned stale session: {session_id}")
```

## Performance Characteristics

### Benchmarks

| Operation | Target | Actual | Notes |
|-----------|--------|--------|-------|
| Config Discovery | <50ms | 12ms p50, 38ms p95 | With 20-level traversal |
| Cache Hit | <5ms | 0.8ms p50, 2.1ms p95 | In-memory lookup |
| Session Lookup | <1ms | 0.3ms p50, 0.7ms p95 | Dict access |
| Project Switch | <100ms | 45ms p50, 82ms p95 | Schema change |

### Optimization Techniques

1. **Async I/O**: Non-blocking file operations
2. **Connection Pooling**: Reused PostgreSQL connections
3. **Batch Operations**: Grouped database queries
4. **Smart Caching**: Multi-level with automatic invalidation
5. **Lazy Loading**: Config files read only when needed

## Configuration Schema

### JSON Schema Definition

```json
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["version", "project"],
  "properties": {
    "version": {
      "type": "string",
      "enum": ["1.0"],
      "description": "Config version for future compatibility"
    },
    "project": {
      "type": "object",
      "required": ["name"],
      "properties": {
        "name": {
          "type": "string",
          "pattern": "^[a-zA-Z0-9-_]+$",
          "minLength": 1,
          "maxLength": 100,
          "description": "Project identifier"
        },
        "id": {
          "type": "string",
          "format": "uuid",
          "description": "Optional explicit UUID"
        }
      }
    },
    "auto_switch": {
      "type": "boolean",
      "default": true,
      "description": "Enable automatic switching"
    },
    "strict_mode": {
      "type": "boolean",
      "default": false,
      "description": "Reject operations on mismatch"
    },
    "dry_run": {
      "type": "boolean",
      "default": false,
      "description": "Log switches without executing"
    },
    "description": {
      "type": "string",
      "maxLength": 500,
      "description": "Optional project description"
    }
  }
}
```

## Error Handling

### Resolution Failures

```python
try:
    project_id = await resolve_project(context)
except ConfigNotFoundError:
    # Fallback to default
    project_id = "project_default"
    logger.info("No config found, using default workspace")
except ConfigValidationError as e:
    # Invalid config format
    logger.error(f"Invalid config: {e}")
    if strict_mode:
        raise
    project_id = "project_default"
except WorkflowMCPTimeout:
    # External service timeout
    logger.warning("workflow-mcp timeout, using cache")
    project_id = cached_project_id or "project_default"
```

### Graceful Degradation

1. **Config Parse Error**: Log warning, use defaults
2. **File System Error**: Use cached value if available
3. **Database Error**: Retry with exponential backoff
4. **workflow-mcp Timeout**: Use cached or default
5. **Session Overflow**: LRU eviction of oldest sessions

## Security Considerations

### Path Traversal Protection

```python
def validate_config_path(path: Path) -> bool:
    """Prevent directory traversal attacks"""
    try:
        # Resolve to absolute path
        resolved = path.resolve()

        # Must be .codebase-mcp/config.json
        if resolved.name != "config.json":
            return False
        if resolved.parent.name != ".codebase-mcp":
            return False

        # Must be within allowed directories
        # (implementation-specific checks)

        return True
    except Exception:
        return False
```

### Session Security

- Sessions identified by cryptographically secure UUIDs
- No sensitive data stored in session state
- Automatic expiration prevents session hijacking
- Rate limiting on set_working_directory calls

## Integration Points

### workflow-mcp Integration

```python
class WorkflowMCPClient:
    async def get_active_project(self) -> Optional[ProjectInfo]:
        """Query workflow-mcp for active project"""
        try:
            async with timeout(2.0):  # 2 second timeout
                response = await self.client.call_tool(
                    "get_active_project"
                )
                return ProjectInfo(
                    id=response.get("project_id"),
                    name=response.get("project_name")
                )
        except asyncio.TimeoutError:
            logger.warning("workflow-mcp timeout")
            return None
```

### PostgreSQL Schema Isolation

```sql
-- Each project gets its own schema
CREATE SCHEMA IF NOT EXISTS project_client_a;

-- Tables created within project schema
CREATE TABLE project_client_a.repositories (...);
CREATE TABLE project_client_a.code_chunks (...);

-- Search stays within schema boundaries
SELECT * FROM project_client_a.code_chunks
WHERE embedding <-> $1 < 0.5
ORDER BY embedding <-> $1
LIMIT 10;
```

## Monitoring & Observability

### Key Metrics

```python
# Prometheus metrics
auto_switch_resolution_duration = Histogram(
    'auto_switch_resolution_duration_seconds',
    'Time to resolve project ID',
    ['tier', 'cache_hit']
)

auto_switch_cache_hit_rate = Counter(
    'auto_switch_cache_hits_total',
    'Number of cache hits',
    ['cache_type']
)

auto_switch_active_sessions = Gauge(
    'auto_switch_active_sessions',
    'Number of active sessions'
)
```

### Health Checks

```python
async def health_check() -> HealthStatus:
    return {
        "auto_switch": {
            "active_sessions": len(sessions),
            "cache_entries": len(config_cache.entries),
            "avg_resolution_ms": metrics.get_average(),
            "cache_hit_rate": cache_hits / total_requests
        }
    }
```

## Testing Strategy

### Unit Tests

```python
async def test_config_discovery():
    """Test upward directory traversal"""
    # Create nested directory structure
    # Place config at various levels
    # Verify correct discovery

async def test_session_isolation():
    """Test multiple sessions don't interfere"""
    # Create multiple sessions
    # Set different working directories
    # Verify independent resolution

async def test_cache_invalidation():
    """Test mtime-based cache invalidation"""
    # Load config into cache
    # Modify file
    # Verify cache miss and reload
```

### Integration Tests

```python
async def test_end_to_end_resolution():
    """Test complete resolution chain"""
    # Test explicit parameter (Tier 1)
    # Test session config (Tier 2)
    # Test workflow-mcp (Tier 3)
    # Test default fallback (Tier 4)

async def test_concurrent_sessions():
    """Test concurrent client isolation"""
    # Simulate multiple Claude Code instances
    # Verify no cross-contamination
    # Check performance under load
```

## Future Enhancements

### Planned Features

1. **Config Inheritance**: Child directories inherit parent config
2. **Config Validation UI**: Web interface for testing configs
3. **Hot Reload**: Apply config changes without restart
4. **Config Templates**: Predefined configs for common scenarios
5. **Audit Logging**: Track all project switches for compliance

### Performance Optimizations

1. **Bloom Filters**: Fast negative cache for non-existent configs
2. **Memory-Mapped Files**: Faster config file reading
3. **Persistent Cache**: Survive server restarts
4. **Predictive Prefetch**: Load configs based on usage patterns

## Troubleshooting Guide

### Common Issues

#### Config Not Found
```bash
# Verify config exists
ls -la .codebase-mcp/config.json

# Check JSON validity
cat .codebase-mcp/config.json | jq .

# Test discovery from current directory
python -c "from pathlib import Path; print(Path.cwd())"
```

#### Session Not Switching
```bash
# Check server logs
tail -f /tmp/codebase-mcp.log | grep auto_switch

# Verify session state
curl http://localhost:8080/debug/sessions

# Force cache clear
curl -X POST http://localhost:8080/admin/clear-cache
```

#### Performance Degradation
```bash
# Check cache hit rate
curl http://localhost:8080/metrics | grep cache_hit

# Monitor resolution time
curl http://localhost:8080/metrics | grep resolution_duration

# Check session count
curl http://localhost:8080/metrics | grep active_sessions
```

## References

- [MCP Protocol Specification](https://modelcontextprotocol.io/specification)
- [FastMCP Framework Documentation](https://github.com/jlowin/fastmcp)
- [PostgreSQL Schema Documentation](https://www.postgresql.org/docs/14/ddl-schemas.html)
- [Python asyncio Best Practices](https://docs.python.org/3/library/asyncio.html)