# Implementation Plan: Production-Grade Connection Management

**Branch**: `009-v2-connection-mgmt` | **Date**: 2025-10-13 | **Spec**: [../specs/009-v2-connection-mgmt/spec.md](./spec.md)
**Input**: Feature specification from `/specs/009-v2-connection-mgmt/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement production-grade connection pooling for the Codebase MCP Server to ensure reliable database operations with automatic reconnection, health monitoring, and resource leak prevention. The connection pool will manage PostgreSQL connections with configurable min/max sizes (default 2-10), exponential backoff reconnection (1s to 16s), and real-time statistics for observability.

**Key Capabilities**:
- Pool initialization within 2 seconds (p95)
- Connection validation with <10ms overhead (p95)
- Automatic reconnection with exponential backoff
- Real-time pool statistics and health monitoring
- Connection leak detection with 30s timeout
- Graceful shutdown with 30s active query timeout

## Technical Context

**Language/Version**: Python 3.11+ (required for modern async features and type hints per Constitutional Principle XI)
**Primary Dependencies**: asyncpg (PostgreSQL async driver), pydantic (data validation), pydantic-settings (configuration management), FastMCP (MCP server framework)
**Storage**: PostgreSQL 14+ with pgvector extension (local database per Constitutional Principle II)
**Testing**: pytest, pytest-asyncio (async test support), pytest-cov (coverage enforcement 95%+), pytest-benchmark (performance validation)
**Target Platform**: Linux/macOS server (MCP server component, local-first architecture)
**Project Type**: Single project (MCP server infrastructure component)
**Performance Goals**:
- Pool initialization: <2s (p95) per SC-001
- Connection acquisition: <10ms (p95) per SC-002
- Health check endpoint: <10ms (p99) per SC-003
- Automatic reconnection: <30s (p95) recovery per SC-004
- Graceful shutdown: <30s (p99) per SC-005
- Sustained throughput: 100 concurrent database requests per SC-008
- Health check endpoint: >1000 requests/second per SC-013

**Constraints**:
- Maximum connection pool size: default max_size=10, configurable
- Minimum connection pool size: default min_size=2, configurable
- Connection acquisition timeout: 30s default per FR-009
- Leak detection timeout: 30s default per FR-006
- Maximum connection lifetime: 3600s (1 hour) default per FR-009
- Maximum idle time: 60s default per FR-009
- Graceful shutdown timeout: 30s for active queries per FR-005
- Memory consumption: <100MB for max_size=10 pool per SC-011
- Startup overhead: <200ms added to server startup per SC-012

**Scale/Scope**:
- Supports up to 100 concurrent database requests without timeout errors (SC-008)
- Designed for single MCP server instance (per-server pool statistics)
- Connection pool handles 50,000 queries per connection before recycling (FR-009)
- Exponential backoff: 1s, 2s, 4s, 8s, 16s intervals, max 5 initial attempts (FR-003)
- FIFO connection acquisition queuing (FR-010)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Simplicity Over Features

**Status**: ✅ PASS

**Analysis**: Connection management is essential infrastructure for semantic code search, not feature creep. The feature focuses exclusively on database connection lifecycle (pooling, health checks, reconnection) without extending beyond core responsibilities. Each component has a single, clear purpose: ConnectionPoolManager coordinates lifecycle, ConnectionPool manages connections, PoolConfig validates configuration, PoolStatistics provides observability. No unnecessary abstractions or premature optimization.

The feature directly supports the core mission (semantic code search) by ensuring reliable database access for indexing and search operations. Without connection management, the MCP server cannot function. The scope is minimal but complete: pool initialization, connection validation, automatic reconnection, health monitoring, graceful shutdown.

### II. Local-First Architecture

**Status**: ✅ PASS

**Analysis**: All connections target local PostgreSQL instance via DATABASE_URL environment variable. No cloud API calls or external dependencies. The feature operates entirely within the local-first architecture defined by Constitutional Principle II. Connection pool connects to localhost PostgreSQL, requires no internet connectivity after initial setup.

Configuration supports standard PostgreSQL connection strings (postgresql+asyncpg://localhost/codebase_mcp), enabling complete offline operation. Database schema remains standard PostgreSQL, ensuring data portability. No external connection pooling services (AWS RDS Proxy, PgBouncer cloud) are introduced.

### III. Protocol Compliance (MCP via SSE)

**Status**: ✅ PASS

**Analysis**: Connection management is transparent to MCP protocol. All logging goes to `/tmp/codebase-mcp.log` per FR-010 (file-based structured logging), with zero stdout/stderr pollution. Health check endpoint integrates with FastMCP server's existing health monitoring (FR-008) without introducing protocol violations.

Connection pool initialization occurs during server startup, before MCP protocol communication begins. Reconnection logic logs to file only. Pool statistics are queryable via internal API without stdout output. The feature maintains complete protocol compliance by keeping all diagnostic output in log files.

### IV. Performance Guarantees

**Status**: ✅ PASS

**Analysis**: Feature explicitly defines performance targets that align with constitutional requirements:
- Pool initialization <2s (p95) per SC-001 - ensures fast server startup
- Connection acquisition <10ms (p95) per SC-002 - minimal query overhead
- Health check <10ms (p99) per SC-003 - responsive monitoring
- Automatic reconnection <30s (p95) per SC-004 - quick recovery
- Graceful shutdown <30s (p99) per SC-005 - clean termination
- 100 concurrent requests supported per SC-008 - high throughput
- Health endpoint >1000 req/s per SC-013 - scalable monitoring

Performance targets are measurable via pytest-benchmark (SC-001, SC-002, SC-003) and integration tests (SC-004, SC-005, SC-008, SC-013). Connection validation (<5ms per FR-002) ensures minimal overhead. Async operations prevent blocking (FR-010).

### V. Production Quality Standards

**Status**: ✅ PASS

**Analysis**: Feature implements comprehensive production quality requirements:
- **Error Handling**: FR-007 mandates configuration validation with detailed error messages and actionable suggestions. FR-003 defines exponential backoff with clear logging. FR-006 implements connection leak detection with stack traces.
- **Type Safety**: FR-010 requires Pydantic models for all configuration (PoolConfig uses pydantic_settings.BaseSettings). All entities (ConnectionPoolManager, ConnectionPool, PoolStatistics, HealthStatus) use explicit type annotations compatible with mypy --strict.
- **Logging**: SC-010 ensures all connection lifecycle events are logged with clear, actionable messages. FR-010 specifies file-based structured logging to `/tmp/codebase-mcp.log` with JSON format.
- **Configuration Validation**: FR-007 requires fail-fast startup validation. PoolConfig validates min_size <= max_size, positive timeouts, valid database URLs before pool creation.
- **Resource Management**: FR-009 implements connection recycling based on lifetime, idle time, and query count to prevent resource leaks. FR-005 implements graceful shutdown with timeout.

### VI. Specification-First Development

**Status**: ✅ PASS

**Analysis**: Complete feature specification exists at `/specs/009-v2-connection-mgmt/spec.md` with:
- 4 detailed user stories with acceptance scenarios (US-001 through US-004)
- 10 functional requirements traced to user stories (FR-001 through FR-010)
- 5 key entities with explicit responsibilities
- 13 measurable success criteria (SC-001 through SC-013)
- Edge cases documented (database outage, connection exhaustion, configuration conflicts)
- Alternative paths defined (reconnection mode, FIFO queuing, leak detection, graceful shutdown)

No [NEEDS CLARIFICATION] markers remain in spec. All requirements are testable with clear acceptance criteria. Planning phase can proceed with complete requirements.

### VII. Test-Driven Development

**Status**: ✅ PASS

**Analysis**: Feature specification defines clear test scenarios enabling TDD approach:
- **Contract Tests**: Pool initialization (US-001 scenarios 1-4), configuration validation (FR-007), Pydantic model validation
- **Integration Tests**: Automatic reconnection (US-002 scenarios 1-5), health check integration (US-003), graceful shutdown (FR-005)
- **Performance Tests**: SC-001 through SC-013 define measurable performance targets validated via pytest-benchmark
- **Unit Tests**: Connection validation (FR-002), leak detection (US-004), statistics calculation (FR-004), configuration validation (FR-007)

Tasks.md (generated by `/tasks` command) will order test tasks before implementation tasks. Each functional requirement traces to testable acceptance criteria in spec.md. Performance benchmarks validate constitutional targets (2s init, 10ms acquisition, 500ms search).

### VIII. Pydantic-Based Type Safety

**Status**: ✅ PASS

**Analysis**: Feature explicitly requires Pydantic throughout:
- **PoolConfig**: Uses `pydantic_settings.BaseSettings` for environment variable support (DATABASE_URL), with validators for min_size <= max_size, positive timeouts, valid connection strings (FR-007)
- **PoolStatistics**: Pydantic model with explicit types (total_connections: int, idle_connections: int, active_connections: int, waiting_requests: int, avg_acquisition_time_ms: float, peak metrics)
- **HealthStatus**: Pydantic model containing status enum (healthy/degraded/unhealthy), timestamp, database connectivity, pool statistics, latency metrics (FR-008)
- **ConnectionPoolManager**: Type-hinted methods with Pydantic model return types, mypy --strict compliance

All configuration parameters validated at model instantiation. Invalid input fails fast with field-level error messages (FR-007). Database models use SQLAlchemy with full type hints (AsyncPG driver compatibility).

### IX. Orchestrated Subagent Execution

**Status**: ✅ PASS

**Analysis**: Feature structure enables parallel implementation via orchestrated subagents during `/implement` phase:
- **Independent Components**: PoolConfig (configuration validation), PoolStatistics (statistics calculation), HealthStatus (health check response), ConnectionPool (pool abstraction), ConnectionPoolManager (lifecycle coordination) can be implemented in parallel
- **Clear Contracts**: Pydantic models define interfaces between components, enabling subagents to work independently with type safety
- **Test-First Approach**: Contract tests for each component can be written in parallel before implementation, validating subagent outputs independently
- **Integration Validation**: Integration tests validate all components work together (pool initialization, automatic reconnection, health checks, graceful shutdown)

Tasks.md will mark parallel tasks with [P] for concurrent subagent execution. Orchestrator coordinates results and resolves conflicts through type-checked interfaces.

### X. Git Micro-Commit Strategy

**Status**: ✅ PASS

**Analysis**: Feature branch `009-v2-connection-mgmt` exists and follows naming convention (3-digit prefix). Implementation will follow micro-commit strategy:
- **Atomic Commits**: Each task in tasks.md (generated by `/tasks`) produces one commit using Conventional Commits format: `feat(pool): initialize connection pool`, `test(pool): validate automatic reconnection`, `fix(pool): handle graceful shutdown timeout`
- **Working State**: Each commit must pass all tests (TDD approach ensures tests exist before implementation)
- **Granular History**: Separate commits for PoolConfig, PoolStatistics, ConnectionPool, ConnectionPoolManager, health check integration
- **Branch Isolation**: All work on 009-v2-connection-mgmt branch, no direct commits to main

Feature completion requires all acceptance criteria (SC-001 through SC-013) passing before merge. Branch-per-feature enables parallel development with other Phase-04 components.

### XI. FastMCP and Python SDK Foundation

**Status**: ✅ PASS

**Analysis**: Feature integrates with FastMCP framework for MCP server compliance:
- **Health Check Integration**: FR-008 specifies integration with server's health check endpoint, which uses FastMCP's built-in health monitoring patterns
- **Context Injection**: Connection pool accessed via FastMCP context injection, avoiding global state
- **Type Hints**: FastMCP automatically generates schemas from Pydantic type hints (PoolConfig, PoolStatistics, HealthStatus models)
- **Transport Abstraction**: Connection pool operates transparently under FastMCP's SSE transport, with no direct protocol handling

Connection management is infrastructure supporting FastMCP tools (index_repository, search_code). Pool statistics queryable via FastMCP context without custom protocol handling. Health check endpoint leverages FastMCP's automatic endpoint generation from type-hinted functions.

No direct MCP Python SDK usage required - FastMCP wrapper provides all necessary protocol compliance. Decorator patterns (@mcp.tool(), @mcp.resource()) used by tools that depend on connection pool, not by pool itself.

## Constitution Check (Post-Design Re-evaluation)

*GATE: Completed after Phase 1 artifacts. Validates no complexity creep during detailed design.*

**Phase 1 artifacts reviewed**:
- research.md (technical decisions with alternatives)
- data-model.md (Pydantic models with validation)
- contracts/ (API specifications)
- quickstart.md (integration test scenarios)

**Re-validation results**:

### Principle I: Simplicity Over Features
**Status**: ✅ MAINTAINED
**Evidence**: asyncpg pool selected over SQLAlchemy ORM (research.md Decision 1), reducing abstraction layers. No feature scope expansion during design.

### Principle V: Production Quality Standards
**Status**: ✅ MAINTAINED
**Evidence**: Comprehensive error handling defined in contracts/pool-manager-api.md. All exceptions include context and suggested actions. data-model.md documents complete validation rules.

### Principle VIII: Pydantic-Based Type Safety
**Status**: ✅ MAINTAINED
**Evidence**: All models in data-model.md use Pydantic BaseModel or BaseSettings. PoolConfig uses pydantic_settings for environment variables. Field validators enforce constraints (max_size >= min_size).

### Cross-Cutting Validation
- ✅ **No implementation leaks in design**: Contracts describe behavior, not code structure
- ✅ **Performance targets preserved**: All SC metrics referenced in contracts (SC-001, SC-002, SC-003)
- ✅ **Test-first approach maintained**: quickstart.md provides executable test scenarios before implementation
- ✅ **No new constitutional violations introduced**: All design decisions comply with principles I-XI

**Complexity assessment**:
- Decision count: 7 major decisions (connection pool library, config management, validation strategy, backoff algorithm, health status, leak detection, graceful shutdown)
- Abstraction layers: Minimal (ConnectionPoolManager → asyncpg pool → PostgreSQL)
- External dependencies: 3 core (asyncpg, pydantic, pydantic-settings) - all justified

**Conclusion**: Technical approach maintains constitutional alignment. No violations introduced during Phase 1 design. Ready for task generation.

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)
```
src/                          # Main source code
├── config/                   # Configuration management
├── database/                 # Database session and utilities
├── mcp/                      # MCP server implementation (FastMCP)
├── models/                   # Pydantic models and SQLAlchemy entities
└── services/                 # Business logic services
    ├── indexer.py           # Repository indexing
    ├── searcher.py          # Semantic search
    ├── embedder.py          # Embedding generation
    ├── chunker.py           # Code chunking (AST-based)
    └── scanner.py           # File system scanning

tests/                        # Test suite
├── contract/                 # MCP protocol compliance tests
├── integration/              # End-to-end workflow tests
├── unit/                     # Component unit tests
├── performance/              # Benchmark tests (60s/500ms targets)
└── fixtures/                 # Test data and helpers

migrations/                   # Alembic database migrations
├── env.py                   # Migration environment config
└── versions/                # Versioned migration scripts

scripts/                      # Utility scripts
├── init_db.py               # Database initialization
├── reset_database.sh        # Development database reset
└── collect_baseline.sh      # Performance baseline collection

docs/                         # Documentation
├── architecture/            # Architecture decision records
├── guides/                  # User and developer guides
├── operations/              # Operational procedures
└── specifications/          # Technical specifications

specs/                        # Feature specifications (per-feature)
└── ###-feature-name/        # Individual feature directories
    ├── spec.md              # Feature specification
    ├── plan.md              # Implementation plan
    ├── research.md          # Research decisions
    ├── data-model.md        # Data model definitions
    ├── contracts/           # API contracts
    ├── quickstart.md        # Integration test scenarios
    └── tasks.md             # Ordered task breakdown

.specify/                     # Workflow automation
├── memory/                  # Project memory (constitution, exceptions)
├── scripts/bash/            # Workflow scripts
└── templates/               # Document templates
```

**Structure Decision**:

Single project architecture is appropriate for this feature because connection management is foundational infrastructure, not a standalone application. The connection pool will be implemented as a module within `src/` alongside existing MCP server components (indexer, searcher, embedder). This follows **Constitutional Principle I (Simplicity Over Features)** by integrating as a cohesive module rather than creating unnecessary separation with microservices or separate applications.

The existing codebase already follows a single-project structure with modular services (indexer.py, searcher.py, embedder.py in src/services/). Connection pooling naturally fits this pattern as infrastructure supporting all database-dependent services. Tests are organized by type (contract, integration, unit, performance) to support TDD workflow per **Constitutional Principle VII**.

**Location for connection pool code**: The implementation will integrate into existing `src/database/` directory (or create `src/connection_pool/` if database session management is separate), ensuring co-location with other database infrastructure. The connection pool manager will be initialized during MCP server startup and injected into service layer via FastMCP context.

**Relationship to Existing Code**: The current `src/database/session.py` uses SQLAlchemy's QueuePool for synchronous database operations (pool_size=10, max_overflow=20, pool_timeout=30s, pool_pre_ping=True, pool_recycle=3600s). This feature will refactor the database layer to use asyncpg's native async pool (research.md Decision 1), replacing the SQLAlchemy pool with production-grade async connection management. The refactoring maintains backward compatibility where possible while introducing async-first patterns required by Constitutional Principle IV (async everything). Migration strategy: new async operations use asyncpg pool directly; existing synchronous code paths maintained during transition period with deprecation warnings until full async migration complete.

## Complexity Tracking

*No constitutional violations requiring justification.*

All 11 principles validated with PASS status in Constitution Check (lines 55-183). Technical approach aligns with constitutional requirements:
- Simplicity maintained: asyncpg over SQLAlchemy reduces abstraction
- Single responsibility: Connection pool focuses exclusively on connection lifecycle
- No premature optimization: Performance targets derived from spec success criteria
- Minimal dependencies: 3 core libraries (asyncpg, pydantic, pydantic-settings)

**Complexity Metrics**:
- New modules: 1 (connection_pool)
- New dependencies: 3 (all production-tested, constitutional compliant)
- Abstraction layers: 2 (ConnectionPoolManager → asyncpg.Pool)
- Decision points: 7 (all documented in research.md with rationale)

No exceptions or deviations from constitutional principles required.
