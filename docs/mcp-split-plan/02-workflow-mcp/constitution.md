# Workflow MCP Constitution

## Purpose

This constitution defines the non-negotiable principles, constraints, and quality standards for the **Workflow MCP Server** - an AI project management system with multi-project workspace support and a generic entity system.

These principles ensure the server remains focused, performant, and production-ready while supporting diverse project types (commission work, game development, etc.) through a flexible, domain-agnostic architecture.

## Core Principles

### Principle I: Simplicity Over Features

**The Problem**: Feature creep destroys focus and maintainability.

**The Principle**: workflow-mcp does ONE thing exceptionally well: **AI-assisted project management with multi-project workspaces**.

**Non-Negotiable Constraints**:
- NO code intelligence features (semantic search, embeddings, AST parsing) - delegate to codebase-mcp
- NO cloud synchronization or remote state management
- NO workflow automation engines or event processing beyond deployment recording
- NO hardcoded domain tables (vendor, game_mechanic, etc.) - use generic entity system only
- NO cross-project queries or aggregations (strict isolation per project)

**Allowed Scope**:
- Multi-project workspace management (create, switch, list, delete)
- Hierarchical work items (project → session → task → research)
- Task management with git integration
- Generic entity system with runtime schema registration
- Deployment history recording with relationships

**Deviation Protocol**: Any feature addition requires constitutional amendment with 2-week review period.

---

### Principle II: Local-First Architecture

**The Problem**: Cloud dependencies create latency, cost, and availability risks.

**The Principle**: workflow-mcp operates entirely on local infrastructure with no cloud dependencies.

**Non-Negotiable Requirements**:
- PostgreSQL databases run locally (registry + per-project databases)
- Connection pooling managed in-process (AsyncPG)
- All data persisted to local disk
- No API keys, tokens, or remote service dependencies
- Offline-capable: full functionality without internet

**Allowed Network Operations**:
- MCP protocol communication (SSE transport)
- Query codebase-mcp for active project context (local IPC)

**Performance Target**: <50ms project switching latency on consumer hardware (M1/M2 MacBook, Ryzen desktop).

---

### Principle III: MCP Protocol Compliance

**The Problem**: Breaking MCP protocol breaks all client integrations.

**The Principle**: workflow-mcp is a **strict, compliant MCP server** using Server-Sent Events (SSE) transport.

**Non-Negotiable Requirements**:
- FastMCP framework with MCP Python SDK
- SSE-based transport only (no stdio pollution)
- All tools exposed via FastMCP decorators
- Structured logging to file/syslog (NEVER stdout/stderr)
- Progress reporting via MCP progress notifications
- Error responses use MCP error schema

**Forbidden Practices**:
- Print statements or logging to stdout/stderr
- Custom JSON-RPC implementations
- Protocol extensions outside MCP spec
- Synchronous blocking operations in tool handlers

**Validation**: Integration tests MUST verify Claude Desktop/CLI can invoke all tools.

---

### Principle IV: Performance Guarantees

**The Problem**: Slow project management creates friction in AI workflows.

**The Principle**: workflow-mcp provides predictable, sub-second performance for all operations.

**Performance Targets (p95 latency)**:
- **Project switching**: <50ms (registry query + connection pool lookup)
- **Work item operations**: <200ms (hierarchy queries, dependency resolution)
- **Entity queries**: <100ms (JSONB filtering with GIN indexing)
- **Task listing**: <150ms (summary mode, token-efficient)
- **Deployment recording**: <200ms (event + relationships)

**Scaling Requirements**:
- Support 100+ projects without degradation
- Work item hierarchies up to 5 levels deep
- Entity tables with 10,000+ records per project
- Connection pools with <10MB overhead per project

**Measurement**: All tools MUST log latency; CI fails on p95 regression >20%.

---

### Principle V: Production Quality

**The Problem**: Prototypes fail in production with data loss and cryptic errors.

**The Principle**: workflow-mcp is production-ready from day one with comprehensive error handling, type safety, and observability.

**Non-Negotiable Standards**:
- **Error handling**: Every tool has try/except with MCP error responses
- **Type safety**: mypy --strict passes with no ignores
- **Validation**: Pydantic models for all inputs/outputs
- **Logging**: Structured JSON logs with correlation IDs
- **Health checks**: Database connectivity checks before operations
- **Graceful degradation**: Failed project databases don't crash server
- **Optimistic locking**: Version-based concurrency control for entities and work items

**Testing Requirements**:
- Unit tests: >90% coverage
- Integration tests: All MCP tools invocable
- Isolation tests: Multi-project operations never leak data
- Performance tests: p95 latency validation in CI

---

### Principle VI: Specification-First Development

**The Problem**: Implementation without requirements leads to misalignment and rework.

**The Principle**: Every feature begins with a specification that defines WHAT and WHY before HOW.

**Process Requirements**:
1. `/specify` creates spec.md with user needs and success criteria
2. `/clarify` resolves ambiguities before planning
3. `/plan` generates design artifacts only after spec approval
4. `/tasks` creates implementation breakdown from validated plan
5. `/implement` executes tasks with working state at each commit

**Specification Quality**:
- NO implementation details in spec.md (no tech stack, APIs, schemas)
- Success criteria MUST be testable
- Edge cases and error scenarios documented
- Performance requirements quantified

**Deviation**: NO code written without approved spec.md. Constitutional violations flagged as CRITICAL in `/analyze`.

---

### Principle VII: Test-Driven Development

**The Problem**: Untested code breaks in production and during refactoring.

**The Principle**: Tests are written BEFORE implementation, starting with protocol compliance.

**TDD Workflow**:
1. **Protocol tests first**: MCP tool invocation contracts
2. **Unit tests**: Business logic and validation
3. **Integration tests**: Database operations and transactions
4. **Isolation tests**: Multi-project data separation
5. **Implementation**: Code to make tests pass

**Test Requirements**:
- All MCP tools have contract tests (input/output schemas)
- All database queries have isolation tests (no cross-project leaks)
- All Pydantic models have validation tests
- All error paths have failure tests
- CI runs full suite on every commit (<5 min total)

**Coverage Target**: >90% line coverage, 100% for critical paths (project isolation, entity validation).

---

### Principle VIII: Pydantic-Based Type Safety

**The Problem**: Runtime type errors crash production systems.

**The Principle**: All data structures use Pydantic for validation, serialization, and type safety.

**Implementation Requirements**:
- **Tool inputs/outputs**: Pydantic models for all MCP tools
- **Entity schemas**: JSON Schema validated via Pydantic at runtime
- **Database models**: Pydantic models for all table rows
- **Configuration**: Pydantic BaseSettings for environment variables
- **Type checking**: mypy --strict with no type: ignore

**Validation Strategy**:
- Input validation at API boundary (FastMCP decorators)
- Entity data validation against registered JSON Schema
- Enum validation for status fields (active/completed/blocked)
- Foreign key validation for relationships (work items, entities)

**Error Handling**: ValidationError → MCP error response with field-level details.

---

### Principle IX: Orchestrated Subagent Execution

**The Problem**: Sequential task execution is slow; monolithic agents lack specialization.

**The Principle**: Complex workflows execute via specialized subagents in parallel where safe.

**Implementation Strategy**:
- `/implement` spawns subagents per parallelizable task
- Tasks marked `[P]` in tasks.md can run concurrently (different files/modules)
- Non-parallel tasks block until completion
- Subagents report progress via MCP notifications
- Orchestrator aggregates results and handles failures

**Safety Constraints**:
- Database operations within a project are serialized (transaction safety)
- Entity type registration blocks entity creation for that type
- Work item hierarchy modifications are serialized
- Connection pool management is thread-safe (AsyncPG)

**Failure Handling**: Non-parallel task failure halts workflow; parallel task failures logged and retried.

---

### Principle X: Git Micro-Commit Strategy

**The Problem**: Large commits obscure intent and complicate code review.

**The Principle**: Every completed task in tasks.md generates an atomic, tested commit.

**Commit Requirements**:
- **Frequency**: Commit after EACH task in tasks.md
- **Atomicity**: One logical change per commit
- **Working state**: All tests pass at every commit
- **Convention**: Conventional Commits format (`type(scope): description`)
  - Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`
  - Example: `feat(entities): add generic entity registration`

**Branch Strategy**:
- **Feature branches**: `###-feature-name` (3-digit prefix)
- **Created by**: `/specify` command automatically
- **Base branch**: `main` or `master`
- **Merge strategy**: Squash merge after PR approval

**Commit Hooks**: Pre-commit runs type checks (mypy), linters (ruff), and fast tests (<30s).

---

### Principle XI: FastMCP and Python SDK Foundation

**The Problem**: Custom MCP implementations diverge from spec and lack tooling.

**The Principle**: workflow-mcp uses FastMCP framework with MCP Python SDK for all MCP functionality.

**Implementation Requirements**:
- **Framework**: FastMCP for server setup and tool registration
- **SDK**: MCP Python SDK for protocol types and SSE transport
- **No custom protocol code**: Use FastMCP decorators exclusively
- **Tool registration**: `@mcp.tool()` decorators for all exposed functions
- **Progress reporting**: FastMCP progress API for long operations
- **Resource exposure**: FastMCP resource API for project metadata

**Forbidden Practices**:
- Manual JSON-RPC message construction
- Custom SSE transport implementations
- Direct stdout/stderr protocol communication
- Bypassing FastMCP validation

**Benefits**: Protocol compliance, automatic schema generation, built-in error handling.

---

### Principle XII: Generic Entity Adaptability

**The Problem**: Hardcoded domain tables (vendors, mechanics) require schema migrations for new domains.

**The Principle**: workflow-mcp supports ANY domain via runtime entity type registration without code or schema changes.

**Architecture Requirements**:
- **Single entities table**: Generic JSONB storage per project
- **Runtime schemas**: JSON Schema registration via `register_entity_type` tool
- **Pydantic validation**: Entity data validated against registered schema at creation
- **Query flexibility**: JSONB operators (@>, ->, ->>) for domain-specific queries
- **GIN indexing**: Fast queries on JSONB columns

**Example Domains**:
- **Commission work**: vendors (status, extractor_version, supports_html)
- **Game development**: game_mechanics (mechanic_type, implementation_status, complexity)
- **Research projects**: papers (citation_count, publication_date, peer_reviewed)

**Non-Negotiable Constraint**: NO domain-specific tables. Adding a vendor table requires constitutional amendment.

**Validation**: Integration tests MUST demonstrate commission + game dev projects using same codebase.

---

## Technical Stack (Non-Negotiable)

### Core Technologies
- **Python 3.11+**: Type hints, async/await, dataclasses
- **PostgreSQL 14+**: JSONB, GIN indexing, materialized paths, recursive CTEs
- **FastMCP**: Framework for MCP server implementation
- **MCP Python SDK**: Official protocol implementation
- **AsyncPG**: High-performance async PostgreSQL driver
- **Pydantic**: Data validation and settings management
- **JSON Schema**: Entity type schema validation

### Development Tools
- **mypy**: Type checking (--strict mode)
- **ruff**: Linting and formatting
- **pytest**: Testing framework with async support
- **pytest-asyncio**: Async test fixtures
- **pytest-postgresql**: Database fixture management

### Infrastructure
- **PostgreSQL**: Multiple databases (registry + per-project)
- **Connection pooling**: AsyncPG pools per project
- **Structured logging**: JSON logs to file (loguru or stdlib logging)

---

## Success Criteria

### Functional Requirements
1. **Multi-project isolation**: Commission data never visible in game dev project queries
2. **Generic entities**: New entity types registered without code deployment
3. **Hierarchy traversal**: Work items queryable up/down 5 levels in <200ms
4. **Task tracking**: Git integration tracks branch/commit per task
5. **Deployment history**: Full audit trail of production changes

### Performance Requirements
1. **Project switching**: <50ms p95 latency
2. **Work item operations**: <200ms p95 latency (hierarchy queries)
3. **Entity queries**: <100ms p95 latency (JSONB filtering)
4. **Scalability**: 100+ projects without degradation

### Quality Requirements
1. **Type safety**: mypy --strict passes with zero errors
2. **Test coverage**: >90% line coverage, 100% for critical paths
3. **Protocol compliance**: All tools invocable from Claude Desktop/CLI
4. **Error handling**: All failure paths return structured MCP errors

### Operational Requirements
1. **Zero downtime**: Project database failures don't crash server
2. **Graceful degradation**: Failed project marked offline, others continue
3. **Connection management**: <10MB overhead per project connection pool
4. **Health checks**: Database connectivity verified before operations

---

## Complexity Management

### Allowed Complexity
- Multi-database connection pooling (AsyncPG pools per project)
- Recursive CTEs for work item hierarchy traversal
- JSONB GIN indexing for entity queries
- Materialized path for ancestor queries
- Optimistic locking for concurrent entity updates

### Forbidden Complexity
- Custom query planners or ORMs (use raw SQL with AsyncPG)
- Event sourcing or CQRS patterns (simple CRUD operations)
- Distributed transactions or two-phase commit
- Custom serialization formats (use Pydantic JSON)
- Workflow state machines (simple status enums only)

### Deviation Protocol
Any complexity addition requires:
1. Justification in plan.md "Complexity Tracking" section
2. Performance impact analysis (latency, memory)
3. Alternative approaches considered and rejected
4. Constitutional principle violated and mitigation strategy

---

## Amendment Process

1. **Proposal**: Document proposed change with rationale
2. **Review period**: 2-week community discussion
3. **Vote**: 2/3 majority required for amendment
4. **Update cascade**: Update CLAUDE.md, plan template, constitution template
5. **Retroactive compliance**: Existing code has 4-week grace period for alignment

---

## Enforcement

- **CI checks**: Automated validation of type safety, test coverage, performance
- **PR reviews**: Constitutional compliance checklist required
- **`/analyze` command**: Flags violations as CRITICAL before implementation
- **Post-implementation audit**: Spot checks on merged features

**Violation consequences**:
- CRITICAL violations block PR merge
- MAJOR violations require issue creation and 2-sprint remediation
- MINOR violations logged for retrospective discussion

---

*This constitution is the single source of truth for workflow-mcp's architecture and quality standards. All development decisions must align with these principles.*
