# Health Check API Contract

**Purpose**: Health monitoring endpoint for connection pool observability

**Endpoint**: Internal API (accessed via FastMCP context)

## Response Schema

### Success Response (200 OK)

```json
{
  "status": "healthy" | "degraded" | "unhealthy",
  "timestamp": "2025-10-13T14:30:00.000Z",
  "database": {
    "status": "connected" | "disconnected" | "connecting",
    "pool": {
      "total": 5,
      "idle": 3,
      "active": 2,
      "waiting": 0
    },
    "latency_ms": 2.3,
    "last_error": null | "error message"
  },
  "uptime_seconds": 3600.5
}
```

**Field Descriptions**:
- `status`: Overall health (healthy: >80% capacity, degraded: 50-79%, unhealthy: <50%)
- `timestamp`: ISO 8601 timestamp of health check execution
- `database.status`: Connection state (connected/disconnected/connecting)
- `database.pool.total`: Current total connections in pool
- `database.pool.idle`: Available connections
- `database.pool.active`: Connections currently in use
- `database.pool.waiting`: Requests waiting for connection
- `database.latency_ms`: Last successful query latency (null if no queries)
- `database.last_error`: Most recent error message (null if no errors)
- `uptime_seconds`: Server uptime since pool initialization

**Performance Requirements**:
- Response time: <10ms (p99) per SC-003
- No database query executed (in-memory statistics only)
- Thread-safe concurrent access supported

## Example Scenarios

### Healthy Pool
```json
{
  "status": "healthy",
  "timestamp": "2025-10-13T14:30:00.000Z",
  "database": {
    "status": "connected",
    "pool": {
      "total": 10,
      "idle": 8,
      "active": 2,
      "waiting": 0
    },
    "latency_ms": 1.8,
    "last_error": null
  },
  "uptime_seconds": 7200.0
}
```

### Degraded Pool (High Load)
```json
{
  "status": "degraded",
  "timestamp": "2025-10-13T14:35:00.000Z",
  "database": {
    "status": "connected",
    "pool": {
      "total": 10,
      "idle": 2,
      "active": 8,
      "waiting": 3
    },
    "latency_ms": 45.2,
    "last_error": null
  },
  "uptime_seconds": 7500.0
}
```

### Unhealthy Pool (Database Down)
```json
{
  "status": "unhealthy",
  "timestamp": "2025-10-13T14:40:00.000Z",
  "database": {
    "status": "disconnected",
    "pool": {
      "total": 0,
      "idle": 0,
      "active": 0,
      "waiting": 5
    },
    "latency_ms": null,
    "last_error": "Connection refused: database server unavailable"
  },
  "uptime_seconds": 7800.0
}
```

## Integration

### FastMCP Integration
```python
from fastmcp import Context

@mcp.resource("health://connection-pool")
async def get_pool_health(ctx: Context) -> dict:
    """Get connection pool health status."""
    pool_manager = ctx.state.pool_manager
    health_status = await pool_manager.health_check()
    return health_status.model_dump()
```

### Client Usage
```python
# Via FastMCP context
health = await ctx.request_resource("health://connection-pool")
if health["status"] == "unhealthy":
    logger.error(f"Pool unhealthy: {health['database']['last_error']}")
```
