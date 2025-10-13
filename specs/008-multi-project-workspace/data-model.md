# Data Model: Multi-Project Workspace Support

**Feature**: 008-multi-project-workspace
**Date**: 2025-10-12
**Status**: Phase 1 Complete

## Overview

This document defines the data models required for multi-project workspace support. All models use Pydantic for runtime validation and mypy --strict type safety (Constitutional Principle VIII).

---

## Pydantic Models

### 1. ProjectIdentifier

**Purpose**: Validated project identifier with security guarantees

**Lifecycle**:
- Created: When user provides project_id parameter in MCP tool call
- Validated: Immediately upon construction (Pydantic validator)
- Used: Converted to PostgreSQL schema name

**Fields**:
```python
class ProjectIdentifier(BaseModel):
    """Validated project identifier preventing SQL injection."""

    value: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Project identifier (lowercase alphanumeric with hyphens)",
        examples=["client-a", "frontend", "my-project-123"]
    )

    @field_validator('value')
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate project identifier format and security constraints.

        Rules:
        - Lowercase alphanumeric with hyphens only
        - Cannot start or end with hyphen
        - No consecutive hyphens
        - Prevents SQL injection via strict character whitelist

        Raises:
            ValueError: If identifier format is invalid
        """
        # Length already validated by Field(min_length=1, max_length=50)

        # Format validation (security-critical)
        pattern = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
        if not pattern.match(v):
            raise ValueError(
                "Project identifier must be lowercase alphanumeric with hyphens. "
                "Cannot start/end with hyphen or have consecutive hyphens. "
                f"Found: {v}\n\n"
                "Examples:\n"
                "  ✅ client-a\n"
                "  ✅ my-project-123\n"
                "  ❌ My_Project (uppercase and underscore)\n"
                "  ❌ -project (starts with hyphen)\n"
                "  ❌ project-- (consecutive hyphens)"
            )

        return v

    def to_schema_name(self) -> str:
        """Convert validated identifier to PostgreSQL schema name.

        Returns:
            Schema name in format: project_{identifier}
        """
        return f"project_{self.value}"
```

**Validation Examples**:
- ✅ Valid: `"client-a"`, `"frontend"`, `"my-project-123"`
- ❌ Invalid: `"My_Project"` (uppercase, underscore), `"-project"` (starts with hyphen)
- ❌ Blocked: `"project'; DROP TABLE--"` (SQL injection attempt)

**Traces to**:
- FR-004: System MUST validate project identifiers before use
- FR-005: System MUST enforce lowercase alphanumeric with hyphen format
- FR-006: System MUST enforce maximum 50-character length
- FR-007: System MUST prevent identifiers starting or ending with hyphens
- FR-008: System MUST prevent consecutive hyphens
- FR-016: System MUST prevent security vulnerabilities via identifier validation

---

### 2. WorkspaceConfig

**Purpose**: Configuration for a project workspace

**Lifecycle**:
- Created: When project schema is first provisioned
- Stored: In `project_registry.workspace_config` table (PostgreSQL)
- Updated: Never (immutable after creation)
- Deleted: Future feature (not in scope)

**Fields**:
```python
class WorkspaceConfig(BaseModel):
    """Project workspace metadata and configuration."""

    project_id: str = Field(
        ...,
        description="Validated project identifier (immutable)",
    )

    schema_name: str = Field(
        ...,
        description="PostgreSQL schema name (e.g., project_client_a)",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when workspace was provisioned",
    )

    # Future extensibility (not used in initial implementation)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata (reserved for future features)",
    )

    model_config = ConfigDict(frozen=True)  # Immutable after creation
```

**Storage**:
```sql
-- Stored in global registry schema (shared across all projects)
CREATE SCHEMA IF NOT EXISTS project_registry;

CREATE TABLE project_registry.workspace_config (
    project_id VARCHAR(50) PRIMARY KEY,
    schema_name VARCHAR(60) NOT NULL UNIQUE,  -- "project_" + project_id
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Index for schema name lookups
CREATE UNIQUE INDEX idx_workspace_schema ON project_registry.workspace_config(schema_name);
```

**Traces to**:
- FR-009: System MUST create isolated workspace for each unique project identifier
- FR-010: System MUST automatically provision workspace on first use

---

### 3. WorkflowIntegrationContext

**Purpose**: Cached context from workflow-mcp server (optional integration)

**Lifecycle**:
- Created: When workflow-mcp query succeeds
- Cached: In-memory for 60 seconds (TTL)
- Expired: After TTL or on cache invalidation
- Deleted: On server shutdown

**Fields**:
```python
class WorkflowIntegrationContext(BaseModel):
    """Context from workflow-mcp server with caching metadata."""

    active_project_id: str | None = Field(
        None,
        description="Active project from workflow-mcp (None if unavailable)",
    )

    status: Literal["success", "timeout", "unavailable", "invalid_response"] = Field(
        ...,
        description="Integration status for error handling",
    )

    retrieved_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Cache timestamp for TTL calculation",
    )

    cache_ttl_seconds: int = Field(
        default=60,
        description="Time-to-live for cached value",
    )

    def is_expired(self) -> bool:
        """Check if cached context has exceeded TTL.

        Returns:
            True if cache expired, False otherwise
        """
        age_seconds = (datetime.utcnow() - self.retrieved_at).total_seconds()
        return age_seconds > self.cache_ttl_seconds
```

**Cache Implementation**:
```python
# In-memory cache (simple dictionary)
_workflow_context_cache: dict[str, WorkflowIntegrationContext] = {}

async def get_workflow_context() -> WorkflowIntegrationContext:
    """Get workflow-mcp context with TTL-based caching."""
    # Check cache
    cached = _workflow_context_cache.get("active_project")
    if cached and not cached.is_expired():
        return cached

    # Query workflow-mcp (with timeout)
    try:
        response = await workflow_client.get("/api/v1/projects/active", timeout=1.0)
        context = WorkflowIntegrationContext(
            active_project_id=response.json().get("project_id"),
            status="success",
        )
    except httpx.TimeoutException:
        context = WorkflowIntegrationContext(
            active_project_id=None,
            status="timeout",
        )
    # ... other error cases

    # Update cache
    _workflow_context_cache["active_project"] = context
    return context
```

**Traces to**:
- FR-012: System SHOULD query workflow-mcp for active project when available
- FR-013: System MUST gracefully handle workflow-mcp unavailability
- FR-014: System MUST categorize workflow-mcp integration failures
- FR-015: System SHOULD cache workflow-mcp responses temporarily

---

## Database Schema Changes

### Global Registry Schema

**Purpose**: Store workspace metadata across all projects

```sql
-- Create global registry schema (one-time initialization)
CREATE SCHEMA IF NOT EXISTS project_registry;

-- Workspace configuration table
CREATE TABLE project_registry.workspace_config (
    project_id VARCHAR(50) PRIMARY KEY,
    schema_name VARCHAR(60) NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Index for fast schema lookups
CREATE UNIQUE INDEX idx_workspace_schema
ON project_registry.workspace_config(schema_name);

-- Index for creation date queries (future archival features)
CREATE INDEX idx_workspace_created
ON project_registry.workspace_config(created_at DESC);
```

### Per-Project Schemas

**Purpose**: Isolate codebase data per project

**Schema creation** (auto-provisioned on first use):
```sql
-- Create project schema
CREATE SCHEMA IF NOT EXISTS project_client_a;

-- Set search_path to new schema
SET search_path TO project_client_a;

-- Create tables (same structure as default schema)
CREATE TABLE repositories (
    id SERIAL PRIMARY KEY,
    path VARCHAR(500) NOT NULL UNIQUE,
    indexed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE code_chunks (
    id SERIAL PRIMARY KEY,
    repository_id INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    file_path VARCHAR(500) NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    embedding vector(768),  -- pgvector type
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE(repository_id, file_path, chunk_index)
);

-- pgvector index for semantic search
CREATE INDEX idx_chunks_embedding
ON code_chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Index for file path queries
CREATE INDEX idx_chunks_file_path
ON code_chunks(file_path);
```

**Key points**:
- **Structure consistency**: All project schemas have identical table definitions
- **pgvector extension**: Database-level, available in all schemas
- **Isolation**: Each schema has independent indexes and statistics
- **Migration support**: Alembic can manage schema structure upgrades

---

## SQLAlchemy Model Changes

### No Model Changes Required

**Current models** (e.g., `src/models/repository.py`) work unchanged:
```python
from src.models.database import Base

class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True)
    path: Mapped[str] = mapped_column(String(500))
    indexed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
```

**Schema resolution** via `search_path`:
```python
async def get_session(project_id: str | None = None) -> AsyncSession:
    """Get database session scoped to project schema."""
    async with SessionLocal() as session:
        # Resolve schema name
        schema_name = resolve_schema_name(project_id)

        # Set search_path (all queries use this schema)
        await session.execute(text(f"SET search_path TO {schema_name}"))

        yield session
```

**Benefits**:
- **Zero model duplication**: Single model definition serves all projects
- **Session-scoped isolation**: Each request targets correct schema
- **Migration simplicity**: Single Alembic migration for all schemas

---

## Service Layer Changes

### New Services

#### ProjectWorkspaceManager

**Purpose**: Manage project workspace lifecycle

```python
class ProjectWorkspaceManager:
    """Manage project workspace provisioning and validation."""

    async def ensure_workspace_exists(self, project_id: str) -> str:
        """Ensure project workspace exists, creating if necessary.

        Args:
            project_id: Validated project identifier

        Returns:
            Schema name (e.g., "project_client_a")

        Raises:
            PermissionError: If schema creation fails due to permissions
        """
        # Validate identifier
        identifier = ProjectIdentifier(value=project_id)
        schema_name = identifier.to_schema_name()

        # Check if schema exists (cached)
        if await self._schema_exists(schema_name):
            return schema_name

        # Create schema (one-time operation)
        await self._create_schema(schema_name)

        # Register in workspace_config table
        await self._register_workspace(project_id, schema_name)

        return schema_name

    async def _schema_exists(self, schema_name: str) -> bool:
        """Check if PostgreSQL schema exists."""
        async with engine.connect() as conn:
            result = await conn.execute(text(
                "SELECT 1 FROM information_schema.schemata "
                "WHERE schema_name = :schema_name"
            ), {"schema_name": schema_name})
            return result.scalar() is not None

    async def _create_schema(self, schema_name: str) -> None:
        """Create PostgreSQL schema with table structure."""
        async with engine.begin() as conn:
            # Create schema
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))

            # Set search_path
            await conn.execute(text(f"SET search_path TO {schema_name}"))

            # Create tables (use SQLAlchemy metadata)
            await conn.run_sync(Base.metadata.create_all)

    async def _register_workspace(self, project_id: str, schema_name: str) -> None:
        """Register workspace in global registry."""
        async with get_session() as session:
            await session.execute(text(
                "INSERT INTO project_registry.workspace_config "
                "(project_id, schema_name) VALUES (:project_id, :schema_name) "
                "ON CONFLICT (project_id) DO NOTHING"
            ), {"project_id": project_id, "schema_name": schema_name})
```

#### WorkflowIntegrationClient

**Purpose**: Optional integration with workflow-mcp

```python
class WorkflowIntegrationClient:
    """Optional HTTP client for workflow-mcp integration."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(1.0))
        self._cache: dict[str, WorkflowIntegrationContext] = {}

    async def get_active_project(self) -> str | None:
        """Query workflow-mcp for active project with caching.

        Returns:
            Active project ID or None if unavailable

        Error Handling:
            - Timeout: Returns None, logs warning
            - Connection refused: Returns None, logs info
            - Invalid response: Returns None, logs error
        """
        # Check cache
        cached = self._cache.get("active_project")
        if cached and not cached.is_expired():
            return cached.active_project_id

        # Query workflow-mcp
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/projects/active")
            response.raise_for_status()

            data = response.json()
            context = WorkflowIntegrationContext(
                active_project_id=data.get("project_id"),
                status="success",
            )

        except httpx.TimeoutException:
            logger.warning("workflow-mcp timeout, using default workspace")
            context = WorkflowIntegrationContext(
                active_project_id=None,
                status="timeout",
            )

        except httpx.ConnectError:
            logger.info("workflow-mcp unavailable, using default workspace")
            context = WorkflowIntegrationContext(
                active_project_id=None,
                status="unavailable",
            )

        except Exception as e:
            logger.error(f"workflow-mcp error: {e}")
            context = WorkflowIntegrationContext(
                active_project_id=None,
                status="invalid_response",
            )

        # Update cache
        self._cache["active_project"] = context
        return context.active_project_id
```

---

## Configuration Changes

### Settings Updates

**Add to `src/config/settings.py`**:

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Multi-project workspace settings
    workflow_mcp_url: Annotated[
        HttpUrl | None,
        Field(
            default=None,
            description="Optional workflow-mcp server URL for automatic project detection",
        ),
    ]

    workflow_mcp_timeout: Annotated[
        float,
        Field(
            default=1.0,
            ge=0.1,
            le=5.0,
            description="Timeout for workflow-mcp queries (seconds)",
        ),
    ]

    workflow_mcp_cache_ttl: Annotated[
        int,
        Field(
            default=60,
            ge=10,
            le=300,
            description="Cache TTL for workflow-mcp responses (seconds)",
        ),
    ]
```

---

## Model Summary

### Pydantic Models (Runtime Validation)
1. **ProjectIdentifier**: Validated project ID (security-critical)
2. **WorkspaceConfig**: Workspace metadata (immutable)
3. **WorkflowIntegrationContext**: Cached workflow-mcp context (TTL-based)

### Database Tables (PostgreSQL)
1. **project_registry.workspace_config**: Global workspace registry
2. **project_{id}.repositories**: Per-project repository metadata
3. **project_{id}.code_chunks**: Per-project code chunks with embeddings

### Service Classes (Business Logic)
1. **ProjectWorkspaceManager**: Workspace provisioning and validation
2. **WorkflowIntegrationClient**: Optional workflow-mcp integration

### Key Invariants
- **Immutability**: Project IDs cannot be renamed after creation
- **Isolation**: Complete schema-level data separation
- **Backward Compatibility**: NULL project_id → "project_default" schema
- **Security**: All identifiers validated before SQL operations

**Phase 1 Data Model Complete** ✅
