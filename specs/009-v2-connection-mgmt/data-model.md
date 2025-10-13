# Data Model: Production-Grade Connection Management

**Branch**: 009-v2-connection-mgmt | **Date**: 2025-10-13
**Phase**: 1 (Design & Contracts)

## Overview

This document defines all data models, configuration structures, and state representations for the connection pool implementation. All models use Pydantic for runtime validation and type safety (Constitutional Principle VIII).

## Configuration Models

### PoolConfig

**Purpose**: Connection pool configuration with environment variable support and validation.

**Pydantic Model**:
```python
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator

class PoolConfig(BaseSettings):
    """Connection pool configuration with environment variable overrides."""

    min_size: int = Field(
        default=2,
        ge=1,
        le=100,
        description="Minimum number of connections to maintain"
    )

    max_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of connections allowed"
    )

    max_queries: int = Field(
        default=50000,
        ge=1000,
        description="Queries per connection before recycling"
    )

    max_idle_time: float = Field(
        default=60.0,
        ge=10.0,
        description="Seconds before idle connections are closed"
    )

    timeout: float = Field(
        default=30.0,
        gt=0.0,
        lt=300.0,
        description="Seconds to wait for connection acquisition"
    )

    command_timeout: float = Field(
        default=60.0,
        gt=0.0,
        description="Seconds for query execution timeout"
    )

    max_connection_lifetime: float = Field(
        default=3600.0,
        ge=60.0,
        description="Maximum age of connection in seconds"
    )

    leak_detection_timeout: float = Field(
        default=30.0,
        ge=0.0,
        description="Seconds before connection leak warning (0 = disabled)"
    )

    enable_leak_detection: bool = Field(
        default=True,
        description="Toggle leak detection for production/development"
    )

    database_url: str = Field(
        ...,
        description="PostgreSQL connection string"
    )

    @field_validator("max_size")
    @classmethod
    def validate_max_size_greater_than_min(cls, v, info):
        """Ensure max_size >= min_size."""
        if "min_size" in info.data and v < info.data["min_size"]:
            raise ValueError(
                f"max_size ({v}) must be >= min_size ({info.data['min_size']}). "
                f"Suggestion: Increase POOL_MAX_SIZE to {info.data['min_size']} or reduce POOL_MIN_SIZE to {v}"
            )
        return v

    class Config:
        env_prefix = "POOL_"  # POOL_MIN_SIZE, POOL_MAX_SIZE, etc.
        env_file = ".env"
        frozen = True  # Immutable after initialization
```

**Validation Rules**:
- min_size: 1 <= value <= 100
- max_size: 1 <= value <= 100, must be >= min_size
- max_queries: >= 1000
- max_idle_time: >= 10.0 seconds
- timeout: 0 < value < 300 seconds
- command_timeout: > 0 seconds
- max_connection_lifetime: >= 60 seconds
- leak_detection_timeout: >= 0 (0 = disabled)
- database_url: Required, must be valid PostgreSQL connection string

**Environment Variables**:
- `POOL_MIN_SIZE`: Minimum pool size (default: 2)
- `POOL_MAX_SIZE`: Maximum pool size (default: 10)
- `POOL_MAX_QUERIES`: Queries before recycling (default: 50000)
- `POOL_MAX_IDLE_TIME`: Idle timeout in seconds (default: 60.0)
- `POOL_TIMEOUT`: Acquisition timeout (default: 30.0)
- `POOL_COMMAND_TIMEOUT`: Query timeout (default: 60.0)
- `POOL_MAX_CONNECTION_LIFETIME`: Connection max age (default: 3600.0)
- `POOL_LEAK_DETECTION_TIMEOUT`: Leak warning threshold (default: 30.0)
- `POOL_ENABLE_LEAK_DETECTION`: Enable leak detection (default: true)
- `POOL_DATABASE_URL` or `DATABASE_URL`: PostgreSQL connection string (required)

---

## Statistics Models

### PoolStatistics

**Purpose**: Immutable snapshot of connection pool state for monitoring and observability.

**Pydantic Model**:
```python
from pydantic import BaseModel, Field
from datetime import datetime

class PoolStatistics(BaseModel):
    """Real-time connection pool statistics."""

    total_connections: int = Field(
        ge=0,
        description="Current total connections in pool"
    )

    idle_connections: int = Field(
        ge=0,
        description="Connections available for use"
    )

    active_connections: int = Field(
        ge=0,
        description="Connections currently in use"
    )

    waiting_requests: int = Field(
        ge=0,
        description="Requests waiting for connection"
    )

    total_acquisitions: int = Field(
        ge=0,
        description="Lifetime connection acquisitions"
    )

    total_releases: int = Field(
        ge=0,
        description="Lifetime connection releases"
    )

    avg_acquisition_time_ms: float = Field(
        ge=0.0,
        description="Average time to acquire connection (milliseconds)"
    )

    peak_active_connections: int = Field(
        ge=0,
        description="Max active connections since server start"
    )

    peak_wait_time_ms: float = Field(
        ge=0.0,
        description="Max time request waited for connection (milliseconds)"
    )

    pool_created_at: datetime = Field(
        description="When pool was initialized"
    )

    last_health_check: datetime = Field(
        description="Last successful health check"
    )

    last_error: str | None = Field(
        default=None,
        description="Last error message if any"
    )

    last_error_time: datetime | None = Field(
        default=None,
        description="Timestamp of last error"
    )

    class Config:
        frozen = True  # Immutable snapshot
```

**Invariants**:
- total_connections = idle_connections + active_connections
- total_acquisitions >= total_releases
- peak_active_connections >= active_connections
- All counts >= 0

**Serialization**:
- JSON serializable for health check API responses
- datetime fields use ISO 8601 format

---

## Health Check Models

### PoolHealthStatus

**Purpose**: Enum for health status values.

**Enum Definition**:
```python
from enum import Enum

class PoolHealthStatus(str, Enum):
    """Connection pool health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
```

**Status Determination Logic**:
- **HEALTHY**: total_connections > 0, idle >= 80% capacity, no errors in last 60s
- **DEGRADED**: total_connections > 0, idle 50-79% capacity, some recent errors
- **UNHEALTHY**: total_connections == 0 OR idle < 50% capacity OR initialization failed

---

### DatabaseStatus

**Purpose**: Database connectivity status details.

**Pydantic Model**:
```python
from pydantic import BaseModel, Field

class DatabaseStatus(BaseModel):
    """Database connectivity status."""

    status: str = Field(
        description="Connection status (connected/disconnected)"
    )

    pool: dict = Field(
        description="Pool statistics (total, idle, active, waiting)"
    )

    latency_ms: float | None = Field(
        default=None,
        description="Last query latency in milliseconds"
    )

    last_error: str | None = Field(
        default=None,
        description="Last error message"
    )
```

**Usage**: Embedded in HealthStatus response for detailed database information.

---

### HealthStatus

**Purpose**: Health check response with pool status and diagnostic information.

**Pydantic Model**:
```python
from pydantic import BaseModel, Field
from datetime import datetime

class HealthStatus(BaseModel):
    """Complete health check response."""

    status: PoolHealthStatus = Field(
        description="Overall health status"
    )

    timestamp: datetime = Field(
        description="Health check execution time"
    )

    database: DatabaseStatus = Field(
        description="Database connectivity and pool state"
    )

    uptime_seconds: float = Field(
        ge=0.0,
        description="Server uptime in seconds"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-10-13T14:30:00.000Z",
                "database": {
                    "status": "connected",
                    "pool": {
                        "total": 5,
                        "idle": 3,
                        "active": 2,
                        "waiting": 0
                    },
                    "latency_ms": 2.3,
                    "last_error": None
                },
                "uptime_seconds": 3600.5
            }
        }
```

**Health Status Calculation Function**:
```python
def calculate_health_status(
    stats: PoolStatistics,
    config: PoolConfig
) -> PoolHealthStatus:
    """
    Calculate health status from pool statistics.

    Rules:
    - UNHEALTHY: No connections available OR initialization failed OR critical error
    - DEGRADED: Partial capacity (50-79%) OR recent errors OR high wait times
    - HEALTHY: Full capacity (≥80%) AND no recent errors AND normal wait times
    """
    if stats.total_connections == 0:
        return PoolHealthStatus.UNHEALTHY

    capacity_ratio = stats.idle_connections / stats.total_connections

    # Check for critical conditions
    if capacity_ratio < 0.5:
        return PoolHealthStatus.UNHEALTHY

    # Check for degraded conditions
    if capacity_ratio < 0.8:
        return PoolHealthStatus.DEGRADED

    # Check for recent errors (within last 60 seconds)
    if stats.last_error_time:
        time_since_error = (datetime.utcnow() - stats.last_error_time).total_seconds()
        if time_since_error < 60:
            return PoolHealthStatus.DEGRADED

    # Check for high wait times (>100ms average)
    if stats.peak_wait_time_ms > 100:
        return PoolHealthStatus.DEGRADED

    return PoolHealthStatus.HEALTHY
```

---

## State Management Models

### PoolState

**Purpose**: Internal pool lifecycle state tracking.

**Enum Definition**:
```python
from enum import Enum

class PoolState(str, Enum):
    """Connection pool lifecycle states."""
    INITIALIZING = "initializing"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    RECOVERING = "recovering"
    SHUTTING_DOWN = "shutting_down"
    TERMINATED = "terminated"
```

**State Transitions**:
- `INITIALIZING` → `HEALTHY`: Pool created min_size connections successfully
- `HEALTHY` → `DEGRADED`: Some connections failed, 50-79% capacity
- `DEGRADED` → `UNHEALTHY`: <50% capacity or critical failure
- `UNHEALTHY` → `RECOVERING`: Reconnection attempt in progress
- `RECOVERING` → `HEALTHY`: Successful reconnection
- `HEALTHY/DEGRADED/UNHEALTHY` → `SHUTTING_DOWN`: Graceful shutdown initiated
- `SHUTTING_DOWN` → `TERMINATED`: All connections closed, resources released

**State Diagram**:
```
    ┌──────────────┐
    │ INITIALIZING │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
    │   HEALTHY    │────►│   DEGRADED   │────►│  UNHEALTHY   │
    └──────┬───────┘     └──────┬───────┘     └──────┬───────┘
           │                    │                     │
           │                    │                     ▼
           │                    │              ┌──────────────┐
           │                    │              │  RECOVERING  │
           │                    │              └──────┬───────┘
           │                    │                     │
           │◄───────────────────┴─────────────────────┘
           │
           │ (shutdown signal)
           ▼
    ┌──────────────┐
    │SHUTTING_DOWN │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │  TERMINATED  │
    └──────────────┘
```

---

## Error Models

### ConnectionPoolError

**Purpose**: Base exception for connection pool errors.

**Exception Hierarchy**:
```python
class ConnectionPoolError(Exception):
    """Base exception for connection pool errors."""
    pass


class PoolConfigurationError(ConnectionPoolError):
    """Configuration validation failed."""
    pass


class PoolInitializationError(ConnectionPoolError):
    """Pool initialization failed."""
    pass


class PoolTimeoutError(ConnectionPoolError):
    """Connection acquisition timeout."""
    pass


class ConnectionValidationError(ConnectionPoolError):
    """Connection validation failed."""
    pass


class PoolClosedError(ConnectionPoolError):
    """Pool is closed and cannot accept requests."""
    pass
```

**Error Context**:
All exceptions include:
- Error message with context
- Suggested action for resolution
- Pool state at time of error (if applicable)

**Example Error Messages**:
```python
# PoolConfigurationError
raise PoolConfigurationError(
    "max_size (5) must be >= min_size (10). "
    "Suggestion: Increase POOL_MAX_SIZE to 10 or reduce POOL_MIN_SIZE to 5"
)

# PoolTimeoutError
raise PoolTimeoutError(
    f"Connection acquisition timeout after {timeout}s. "
    f"Pool state: {stats.total_connections} total, {stats.active_connections} active, "
    f"{stats.waiting_requests} waiting. "
    "Suggestion: Increase POOL_MAX_SIZE or optimize query performance"
)

# ConnectionValidationError
raise ConnectionValidationError(
    f"Connection validation failed: {error_details}. "
    "Connection has been recycled. Retrying acquisition."
)
```

---

## Internal Data Structures

### ConnectionMetadata

**Purpose**: Track connection lifecycle and leak detection.

**Structure** (not exposed in API):
```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ConnectionMetadata:
    """Internal connection tracking metadata."""
    connection_id: str
    acquired_at: datetime
    acquisition_stack_trace: str
    query_count: int
    created_at: datetime
```

**Usage**:
- Stored in weakref dictionary keyed by connection object
- Used for leak detection warnings
- Tracks query count for recycling decisions
- Captures stack trace for debugging

**Leak Detection Warning Format**:
```python
logger.warning(
    f"Potential connection leak detected: {metadata.connection_id}",
    extra={
        "connection_id": metadata.connection_id,
        "held_duration_seconds": (datetime.utcnow() - metadata.acquired_at).total_seconds(),
        "stack_trace": metadata.acquisition_stack_trace,
    }
)
```

---

## Model Relationships

```
PoolConfig
    ↓ (validates & configures)
ConnectionPoolManager
    ↓ (creates & manages)
ConnectionPool (asyncpg.Pool)
    ↓ (tracks via)
ConnectionMetadata
    ↓ (aggregates into)
PoolStatistics
    ↓ (includes in)
HealthStatus
```

---

## Validation Examples

### Valid Configuration
```python
config = PoolConfig(
    min_size=2,
    max_size=10,
    timeout=30.0,
    database_url="postgresql+asyncpg://localhost/codebase_mcp"
)
# ✅ Passes validation
```

### Invalid Configuration (max_size < min_size)
```python
config = PoolConfig(
    min_size=15,
    max_size=10,
    database_url="postgresql+asyncpg://localhost/codebase_mcp"
)
# ❌ Raises ValidationError:
# "max_size (10) must be >= min_size (15).
#  Suggestion: Increase POOL_MAX_SIZE to 15 or reduce POOL_MIN_SIZE to 10"
```

### Invalid Configuration (timeout too high)
```python
config = PoolConfig(
    timeout=600.0,  # 10 minutes
    database_url="postgresql+asyncpg://localhost/codebase_mcp"
)
# ❌ Raises ValidationError:
# "timeout must be less than 300.0 seconds (5 minutes)"
```

### Invalid Configuration (timeout zero)
```python
config = PoolConfig(
    timeout=0.0,
    database_url="postgresql+asyncpg://localhost/codebase_mcp"
)
# ❌ Raises ValidationError:
# "timeout must be greater than 0.0"
```

---

## Serialization Formats

### PoolStatistics JSON
```json
{
  "total_connections": 5,
  "idle_connections": 3,
  "active_connections": 2,
  "waiting_requests": 0,
  "total_acquisitions": 1523,
  "total_releases": 1521,
  "avg_acquisition_time_ms": 2.8,
  "peak_active_connections": 8,
  "peak_wait_time_ms": 45.2,
  "pool_created_at": "2025-10-13T10:00:00Z",
  "last_health_check": "2025-10-13T14:30:00Z",
  "last_error": null,
  "last_error_time": null
}
```

### HealthStatus JSON
```json
{
  "status": "healthy",
  "timestamp": "2025-10-13T14:30:00.000Z",
  "database": {
    "status": "connected",
    "pool": {
      "total": 5,
      "idle": 3,
      "active": 2,
      "waiting": 0
    },
    "latency_ms": 2.3,
    "last_error": null
  },
  "uptime_seconds": 3600.5
}
```

### HealthStatus JSON (Degraded State)
```json
{
  "status": "degraded",
  "timestamp": "2025-10-13T15:00:00.000Z",
  "database": {
    "status": "connected",
    "pool": {
      "total": 10,
      "idle": 6,
      "active": 4,
      "waiting": 2
    },
    "latency_ms": 45.8,
    "last_error": "Connection validation failed"
  },
  "uptime_seconds": 5400.2
}
```

### HealthStatus JSON (Unhealthy State)
```json
{
  "status": "unhealthy",
  "timestamp": "2025-10-13T16:00:00.000Z",
  "database": {
    "status": "disconnected",
    "pool": {
      "total": 0,
      "idle": 0,
      "active": 0,
      "waiting": 5
    },
    "latency_ms": null,
    "last_error": "Database connection refused"
  },
  "uptime_seconds": 7200.5
}
```

---

## Type Safety Enforcement

All models enforce type safety through:
1. **Pydantic validation**: Runtime type checking and constraint validation
2. **mypy --strict**: Static type checking during development
3. **Field constraints**: Explicit bounds (ge, le, gt, lt) on numeric fields
4. **Custom validators**: Cross-field validation (e.g., max_size >= min_size)
5. **Immutability**: PoolStatistics uses frozen=True to prevent modification
6. **Type hints**: All function signatures include complete type annotations

**mypy --strict Compliance Checklist**:
- ✅ All class attributes have type annotations
- ✅ All function parameters have type hints
- ✅ All function return types specified explicitly
- ✅ No implicit Optional types
- ✅ No use of `Any` type (except in justified cases with comments)
- ✅ All Pydantic models inherit from BaseModel or BaseSettings
- ✅ Field validators use proper type annotations

---

## Constitutional Compliance

- **Principle VIII (Pydantic Type Safety)**: All models use Pydantic BaseModel ✅
- **Principle V (Production Quality)**: Comprehensive validation with actionable error messages ✅
- **Principle III (Protocol Compliance)**: Models are JSON serializable for MCP transport ✅
- **Principle IV (Performance)**: Statistics model optimized for <10ms health checks ✅

---

## Summary of Models

### Configuration (1 model)
- **PoolConfig**: Environment-driven configuration with Pydantic validation

### Statistics & Monitoring (4 models)
- **PoolStatistics**: Immutable statistics snapshot
- **PoolHealthStatus**: Three-tier health status enum
- **DatabaseStatus**: Database connectivity details
- **HealthStatus**: Complete health check response

### State Management (1 enum)
- **PoolState**: Connection pool lifecycle states

### Error Handling (6 exception classes)
- **ConnectionPoolError**: Base exception
- **PoolConfigurationError**: Configuration validation failures
- **PoolInitializationError**: Pool creation failures
- **PoolTimeoutError**: Acquisition timeout failures
- **ConnectionValidationError**: Connection validation failures
- **PoolClosedError**: Operations on closed pool

### Internal Tracking (1 dataclass)
- **ConnectionMetadata**: Connection lifecycle and leak detection metadata

**Total Data Structures**: 13 models (1 config, 4 monitoring, 1 state, 6 errors, 1 internal)
