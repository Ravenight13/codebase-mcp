# Data Model & Configuration Schema

**Feature**: 015-add-support-docker
**Date**: 2025-11-06
**Context**: Containerized deployment requires explicit definition of configuration entities and relationships.

## Configuration Entities

### DockerConfig

**Purpose**: Represents Docker image and container configuration.

**Attributes**:
- `base_image`: `str` - Base image identifier (e.g., "python:3.12-slim")
- `image_name`: `str` - Final image name (e.g., "codebase-mcp")
- `image_tag`: `str` - Version tag (e.g., "latest", "0.15.0")
- `target_size_mb`: `int` - Maximum image size target (e.g., 500)
- `build_stages`: `List[BuildStage]` - Multi-stage build definition

**Relationships**:
- `has_many`: BuildStage
- `has_one`: HealthCheckConfig
- `has_many`: EnvironmentVariable

**Validation Rules**:
- `base_image` must be valid Docker image reference (RFC 6125)
- `target_size_mb` >= 320 (practical minimum for python:3.12-slim with dependencies)
- `build_stages` minimum 2 (builder + runtime per research)

### BuildStage

**Purpose**: Represents a stage in multi-stage Docker build.

**Attributes**:
- `stage_name`: `str` - Stage identifier (e.g., "builder", "runtime")
- `base_image`: `str` - Base image for this stage
- `instructions`: `List[str]` - Build instructions (FROM, COPY, RUN, etc.)
- `order`: `int` - Execution order (0-indexed)

**Relationships**:
- `belongs_to`: DockerConfig

**Validation Rules**:
- `order` must be sequential starting from 0
- First stage must be named "builder"
- Last stage must be named "runtime" (or "production")

### ComposeServiceConfig

**Purpose**: Represents a service in docker-compose.yml orchestration.

**Attributes**:
- `service_name`: `str` - Service identifier (e.g., "postgresql", "ollama", "codebase-mcp")
- `image`: `str` - Docker image (e.g., "postgres:14")
- `container_name`: `str` - Runtime container name
- `environment_variables`: `Dict[str, str]` - Environment variable mapping
- `volumes`: `List[Volume]` - Volume mount specifications
- `ports`: `Dict[str, str]` - Port mappings (host:container)
- `depends_on`: `List[str]` - Service dependencies (startup ordering)
- `health_check`: `HealthCheckConfig` - Service health check
- `networks`: `List[str]` - Docker networks to attach

**Relationships**:
- `has_many`: EnvironmentVariable
- `has_many`: Volume
- `has_one`: HealthCheckConfig
- `belongs_to`: ComposeConfig

**Validation Rules**:
- `service_name` must be unique within compose configuration
- `depends_on` must reference valid service names
- `ports` format: `"<host_port>:<container_port>"` or `"<host_port>:<container_port>/<protocol>"`
- Health check `depends_on` required for: postgresql, ollama

**Service Specifications**:

**PostgreSQL Service**:
- Image: `postgres:14`
- Ports: `5432:5432`
- Volumes: `postgres_data:/var/lib/postgresql/data`
- Environment: `POSTGRES_DB=codebase_mcp`, `POSTGRES_PASSWORD=<from .env>`
- Startup order: First (no dependencies)

**Ollama Service**:
- Image: `ollama/ollama:latest`
- Ports: `11434:11434`
- Volumes: `ollama_data:/root/.ollama`
- Depends on: `postgresql` (implicit: waits for network)
- Startup order: Second

**Codebase MCP Service**:
- Image: `codebase-mcp:latest` (or `codebase-mcp:0.15.0`)
- Build: Dockerfile in root directory
- Volumes: `.:/workspace:cached` (development), `None` (production)
- Environment: `REGISTRY_DATABASE_URL`, `OLLAMA_BASE_URL`, `OLLAMA_EMBEDDING_MODEL`
- Depends on: `postgresql`, `ollama`
- Startup order: Third (waits for both dependencies)

### HealthCheckConfig

**Purpose**: Docker health check configuration for service availability monitoring.

**Attributes**:
- `enabled`: `bool` - Whether health check is active
- `test`: `str` - Command to execute (e.g., "pgrep -f python.*server_fastmcp")
- `interval_seconds`: `int` - Check frequency
- `timeout_seconds`: `int` - Maximum execution time
- `start_period_seconds`: `int` - Grace period after container start
- `retries`: `int` - Failures before marking unhealthy

**Relationships**:
- `belongs_to`: ComposeServiceConfig or DockerConfig

**Validation Rules**:
- `interval_seconds` >= 5 (Docker minimum)
- `timeout_seconds` < `interval_seconds`
- `start_period_seconds` >= 0
- `retries` >= 1

**Service-Specific Configurations**:

**PostgreSQL Health Check**:
- Test: `pg_isready -U postgres`
- Interval: 10s
- Timeout: 5s
- Start period: 10s
- Retries: 5

**Ollama Health Check**:
- Test: `curl -f http://localhost:11434/api/tags || exit 1`
- Interval: 30s
- Timeout: 5s
- Start period: 20s
- Retries: 3

**MCP Server Health Check**:
- Test: `pgrep -f "python.*server_fastmcp"`
- Interval: 30s
- Timeout: 5s
- Start period: 20s
- Retries: 3

### EnvironmentVariable

**Purpose**: Represents environment variable for container configuration.

**Attributes**:
- `variable_name`: `str` - Variable name (e.g., "REGISTRY_DATABASE_URL")
- `value`: `str | null` - Variable value (null if should come from .env)
- `required`: `bool` - Whether variable is mandatory
- `description`: `str` - Human-readable description
- `example_value`: `str` - Example value for documentation

**Relationships**:
- `belongs_to`: ComposeServiceConfig or DockerConfig

**Validation Rules**:
- `variable_name` must be uppercase snake_case
- Required variables must have non-null `value` or inherit from .env
- `example_value` should not contain secrets

**Required Environment Variables**:

| Variable | Description | Example | Service |
|----------|-------------|---------|---------|
| `REGISTRY_DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:password@postgresql:5432/codebase_mcp` | codebase-mcp |
| `OLLAMA_BASE_URL` | Ollama service URL | `http://ollama:11434` | codebase-mcp |
| `POSTGRES_PASSWORD` | PostgreSQL admin password | `changeme` (from .env) | postgresql |
| `POSTGRES_DB` | PostgreSQL initial database | `codebase_mcp` | postgresql |

**Optional Environment Variables**:

| Variable | Description | Default | Service |
|----------|-------------|---------|---------|
| `OLLAMA_EMBEDDING_MODEL` | Model for embeddings | `nomic-embed-text` | codebase-mcp |
| `EMBEDDING_BATCH_SIZE` | Batch size for embeddings | `32` | codebase-mcp |
| `LOG_LEVEL` | Logging verbosity | `INFO` | codebase-mcp |
| `DATABASE_POOL_SIZE` | Connection pool size | `20` | codebase-mcp |
| `POSTGRES_USER` | PostgreSQL username | `postgres` | postgresql |

### Volume

**Purpose**: Represents Docker volume mount for data persistence or source code access.

**Attributes**:
- `host_path`: `str` - Path on host machine (e.g., ".", "/var/data")
- `container_path`: `str` - Path inside container (e.g., "/workspace", "/var/lib/postgresql/data")
- `volume_type`: `enum` - Type: "bind" (host directory), "named" (Docker-managed), "tmpfs" (memory)
- `readonly`: `bool` - Read-only or read-write
- `consistency_mode`: `str` - (macOS Docker Desktop) "consistent", "cached", "delegated"

**Relationships**:
- `belongs_to`: ComposeServiceConfig

**Validation Rules**:
- `container_path` must be absolute path
- `host_path` required for "bind" type, optional for "named"
- `readonly` defaults to false
- `consistency_mode` only applies to macOS Docker Desktop

**Standard Volumes**:

**PostgreSQL Data Persistence**:
- Host path: `postgres_data` (named volume)
- Container path: `/var/lib/postgresql/data`
- Type: `named`
- Purpose: Persist database between container restarts

**Ollama Model Cache**:
- Host path: `ollama_data` (named volume)
- Container path: `/root/.ollama`
- Type: `named`
- Purpose: Cache downloaded embedding models

**Source Code (Development)**:
- Host path: `.` (current directory)
- Container path: `/workspace`
- Type: `bind`
- Consistency mode: `cached` (macOS optimization)
- Purpose: Enable hot reload during development

### ComposeConfig

**Purpose**: Top-level docker-compose configuration.

**Attributes**:
- `version`: `str` - Compose file format version (e.g., "3.9", "3.8")
- `services`: `Dict[str, ComposeServiceConfig]` - Service definitions
- `volumes`: `Dict[str, VolumeDefinition]` - Named volume definitions
- `networks`: `Dict[str, NetworkDefinition]` - Network definitions
- `environment_file`: `str` - Path to .env file (e.g., ".env")

**Relationships**:
- `has_many`: ComposeServiceConfig
- `has_many`: Volume
- `has_many`: Network

**Validation Rules**:
- `version` >= "3.8" (required for advanced features)
- All service names must be valid identifiers (lowercase, no special chars)
- No circular dependencies in `depends_on`

**Files**:
- **docker-compose.yml**: Development environment
- **docker-compose.test.yml**: Testing environment (no volumes, isolated network)
- **docker-compose.prod.yml**: Production environment (external database option)

## Relationships Summary

```
DockerConfig
├── has_many: BuildStage
├── has_one: HealthCheckConfig
└── has_many: EnvironmentVariable

ComposeConfig
├── has_many: ComposeServiceConfig
├── has_many: Volume (named)
└── has_many: Network

ComposeServiceConfig
├── belongs_to: ComposeConfig
├── has_one: HealthCheckConfig
├── has_many: EnvironmentVariable
├── has_many: Volume (bind)
└── many-to-many: depends_on (ComposeServiceConfig)

HealthCheckConfig
├── belongs_to: ComposeServiceConfig OR DockerConfig

EnvironmentVariable
├── belongs_to: ComposeServiceConfig OR DockerConfig

Volume
└── belongs_to: ComposeServiceConfig
```

## State Transitions

### Service Lifecycle

```
[Not Created]
     ↓ (docker-compose up)
[Starting]
     ↓ (pass health check)
[Running/Healthy]
     ↓ (health check fails)
[Unhealthy]
     ↓ (restart policy)
[Restarting]
     ↓ (docker stop)
[Stopped]
     ↓ (docker rm)
[Deleted]
```

## Validation Rules

**Startup Order Constraints**:
1. PostgreSQL must be healthy before Ollama starts
2. Ollama must be healthy before Codebase MCP starts
3. Enforced via `depends_on` in compose file

**Database Constraints**:
- `REGISTRY_DATABASE_URL` must be valid connection string
- Database user must have `CREATE` permissions (for migrations)
- PostgreSQL 14+ with pgvector extension required

**Network Constraints**:
- Services communicate via Docker internal network (not host network)
- Host port `5432`, `11434` must be available (or mapped to different ports)
- MCP server runs on stdio (no port binding)

## Edge Cases

1. **PostgreSQL unavailable at startup**: Entrypoint script retries with backoff. Docker restart policy handles repeated failures.

2. **Ollama model not cached**: First startup downloads model from Hugging Face (~100 MB). Cached in `ollama_data` volume. Subsequent startups reuse.

3. **Volume mount permissions (Windows/WSL)**: Docker Desktop handles automatically. WSL2 mount points use WSL filesystem.

4. **Port conflict (5432 already in use)**: docker-compose.yml documents how to change `ports:` mapping. Users should modify before `docker-compose up`.

5. **Database connection pool exhaustion**: ConfigError at startup (FastAPI cannot create pool). Documented in troubleshooting guide.

## Configuration Examples

### Development (.env example)

```bash
REGISTRY_DATABASE_URL=postgresql+asyncpg://postgres:dev-password@postgresql:5432/codebase_mcp
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
POSTGRES_PASSWORD=dev-password
```

### Production (.env example)

```bash
REGISTRY_DATABASE_URL=postgresql+asyncpg://produser:secure-password@db.example.com:5432/codebase_prod
OLLAMA_BASE_URL=http://ollama-internal.example.com:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

### Testing (.env example)

```bash
REGISTRY_DATABASE_URL=postgresql+asyncpg://postgres:test-password@postgresql:5432/codebase_test
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```
