<!--
Sync Impact Report:
- Version change: 2.1.0 → 2.2.0 (MINOR - new principle added)
- Principles added:
  * XI. FastMCP and Python SDK Foundation (MCP server implementation framework)
- Sections modified:
  * Technical Constraints → Required Stack (updated MCP framework dependencies)
  * Architectural Decisions (added FastMCP design pattern requirement)
- Removed sections: None
- Templates requiring updates:
  * ✅ .specify/templates/plan-template.md - Technical Context includes MCP dependencies
  * ✅ .specify/templates/spec-template.md - No changes needed (tech-agnostic)
  * ⚠ Future plans should validate against FastMCP decorative patterns
- Follow-up TODOs: None
- Previous version history:
  * 2.0.0 → 2.1.0: Added Git Micro-Commit Strategy principle
  * 1.1.0 → 2.0.0: Project identity change from Specify Template to Codebase MCP Server
  * 1.0.0 → 1.1.0: Added Pydantic and Orchestration principles
  * Initial: 1.0.0 - Specify Template constitution
-->

# Codebase MCP Server Constitution

## Project Identity

**Purpose**: A focused, production-grade MCP server that indexes code repositories into PostgreSQL with pgvector for semantic search, designed specifically for AI coding assistants.

**Scope**: Do one thing exceptionally well - semantic code search. Not a generic knowledge base, not a full IDE, not reinventing RAG infrastructure.

## Core Principles

### I. Simplicity Over Features (NON-NEGOTIABLE)

The MCP server MUST focus exclusively on semantic code search. Feature requests that extend beyond indexing, embedding, and searching code repositories MUST be rejected. Each component MUST have a single, clear responsibility. Complexity MUST be justified against measurable user value.

**Rationale**: Feature creep destroys maintainability and performance. A tool that does one thing perfectly is more valuable than one that does many things poorly. Semantic search is complex enough without additional concerns.

### II. Local-First Architecture

The system MUST operate completely offline after initial setup. All dependencies MUST be locally hosted (PostgreSQL, Ollama). Zero cloud API calls are permitted except to local Ollama instance. The database schema MUST be standard PostgreSQL, allowing data reuse across tools.

**Rationale**: Privacy, reliability, and speed require local execution. External APIs introduce latency, costs, privacy risks, and single points of failure. Standard schemas enable interoperability.

### III. Protocol Compliance (MCP via SSE)

All MCP communication MUST use SSE transport. Stdout and stderr MUST NEVER contain protocol messages or application logs. Logging MUST go exclusively to `/tmp/codebase-mcp.log`. The server MUST implement MCP specification correctly with no protocol violations.

**Rationale**: MCP protocol violations break AI assistant integrations. Stdout/stderr pollution causes parsing failures. File-based logging enables debugging without breaking the protocol.

### IV. Performance Guarantees

The system MUST meet these performance targets:
- Index 10,000 line codebase in under 60 seconds
- Search queries MUST return in under 500ms (p95)
- Database operations MUST be fully asynchronous
- Embedding generation MUST batch efficiently

**Rationale**: Slow tools break developer flow. These targets ensure the MCP server enhances rather than hinders AI assistant responsiveness. Async operations prevent blocking.

### V. Production Quality Standards

Error handling MUST be comprehensive with specific error messages. All exceptions MUST be caught and logged with context. Type hints MUST be complete and enforced with mypy --strict. Configuration MUST validate on startup, failing fast with clear error messages. File-based structured logging MUST capture all errors with timestamps and context.

**Rationale**: Production systems fail gracefully. Users need actionable error messages. Type safety catches bugs before runtime. Fast failure prevents silent corruption.

### VI. Specification-First Development

Feature specifications MUST be completed before implementation planning. Specifications focus on user requirements (WHAT/WHY) without implementation details (HOW). All specifications MUST include acceptance criteria and test scenarios.

**Rationale**: Clear requirements prevent implementation drift and enable effective testing. Separating concerns allows specification by domain experts and implementation by engineers.

### VII. Test-Driven Development

Test tasks MUST precede implementation tasks. Integration tests MUST validate MCP protocol compliance. Unit tests MUST cover edge cases and error conditions. Performance tests MUST validate against guarantees (60s indexing, 500ms search).

**Rationale**: Tests define correct behavior before implementation. Protocol compliance testing prevents integration breakage. Performance tests prevent regression of guarantees.

### VIII. Pydantic-Based Type Safety

All data models MUST use Pydantic with explicit types and validators. MCP protocol messages MUST inherit from `pydantic.BaseModel`. Configuration MUST use `pydantic_settings.BaseSettings` for environment variables. Database models MUST use SQLAlchemy with full type hints. Validation errors MUST be caught at system boundaries with clear field-level messages.

**Rationale**: Pydantic provides runtime validation preventing invalid data propagation. Configuration validation fails fast on startup. Type safety catches bugs before production. Clear error messages enable quick debugging.

### IX. Orchestrated Subagent Execution

During implementation, the orchestrating agent MUST delegate code-writing tasks to specialized subagents. Independent tasks MUST be executed in parallel using concurrent subagent launches. Each subagent receives complete context (spec, plan, contracts, data model). The orchestrator coordinates results, resolves conflicts, and validates completion.

**Rationale**: Specialized subagents focus without context switching. Parallel execution reduces implementation time. Orchestrator-level coordination maintains consistency and quality.

### X. Git Micro-Commit Strategy

Every feature MUST be developed on a dedicated branch created from main. Commits MUST be atomic and frequent (micro-commits after each completed task or logical unit). Commit messages MUST follow Conventional Commits format (`type(scope): description`). Each commit MUST represent a working state (tests pass). Branch names MUST follow `###-feature-name` pattern with 3-digit prefix. Features MUST NOT be merged until all acceptance criteria pass.

**Rationale**: Micro-commits create granular history enabling precise debugging and rollback. Branch-per-feature isolates work and enables parallel development. Atomic commits ensure bisectability. Conventional Commits enable automated changelog generation and semantic versioning.

### XI. FastMCP and Python SDK Foundation

All MCP server implementations MUST be built using FastMCP (https://github.com/jlowin/fastmcp) as the primary framework and the official MCP Python SDK (https://github.com/modelcontextprotocol/python-sdk) for protocol compliance. FastMCP's decorative patterns MUST be used for tool, resource, and prompt registration. The server MUST leverage FastMCP's built-in context injection, automatic schema generation from type hints, and transport abstraction. Direct protocol handling MUST be avoided in favor of FastMCP's high-level API.

**Rationale**: FastMCP provides the shortest path from implementation to production while maintaining protocol compliance. Automatic schema generation from type hints ensures consistency between code and API contracts. Framework-level transport abstraction prevents protocol violations. Decorator patterns keep tool implementations clean and focused. Using established frameworks prevents reinventing protocol machinery and reduces maintenance burden.

## Technical Constraints

### Required Stack

- **Python**: 3.11+ (required for modern type hints and async features)
- **Database**: PostgreSQL 14+ with pgvector extension
- **Embeddings**: Ollama with nomic-embed-text model (768 dimensions)
- **MCP Framework**: FastMCP with MCP Python SDK for protocol compliance
- **Web Framework**: FastAPI patterns (FastMCP compatible)
- **Database ORM**: SQLAlchemy with AsyncPG driver
- **Code Parsing**: Tree-sitter for AST-based chunking

**Rationale**: These technologies are chosen for production quality, async capabilities, and local-first operation. They are NON-NEGOTIABLE for this project's architecture.

### Architectural Decisions

- **Async Everything**: All I/O operations MUST be asynchronous
- **AST-Based Chunking**: Tree-sitter over regex for proper code structure
- **Direct HTTP**: Ollama HTTP API over Python SDK (simpler, more reliable)
- **Structured Logging**: JSON logs to file, never stdout/stderr
- **Standard Schema**: PostgreSQL schema compatible with other tools
- **FastMCP Decorators**: Use @mcp.tool(), @mcp.resource(), @mcp.prompt() for registration

## Quality Standards

### Code Quality

- Type hints MUST be comprehensive (mypy --strict compliance)
- All public functions MUST have docstrings
- Error messages MUST include context and suggested actions
- Configuration MUST validate on startup
- Logs MUST be structured JSON with timestamps

### Testing Requirements

- MCP protocol compliance tests MUST pass
- Integration tests MUST validate indexing workflow
- Performance tests MUST validate 60s/500ms targets
- Unit tests MUST cover error conditions
- All tests MUST be runnable locally without external services

### Documentation Standards

- README MUST include setup instructions
- API contracts MUST be documented with examples
- Configuration options MUST list required vs optional
- Error messages MUST appear in troubleshooting guide

### Version Control Standards

- Branch names MUST follow `###-feature-name` format (e.g., `001-semantic-search`)
- Commits MUST use Conventional Commits: `type(scope): description`
- Commit types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`
- Each commit MUST pass all tests (working state)
- Commit after completing each task in tasks.md
- Feature branches MUST be created from main
- No direct commits to main (all changes via feature branches)

## Success Criteria

The MCP server is production-ready when:

1. ✅ Indexes 10k line codebase in under 60 seconds
2. ✅ Search returns in under 500ms (p95)
3. ✅ Works completely offline after initial setup
4. ✅ Zero MCP protocol violations in integration tests
5. ✅ Can import existing PostgreSQL data
6. ✅ Clean logs to `/tmp/codebase-mcp.log`, never stdout
7. ✅ All mypy --strict checks pass
8. ✅ All integration tests pass locally

## Non-Goals

Explicitly OUT OF SCOPE:

- Generic knowledge base functionality (use Memorizer instead)
- Full IDE or code editor features
- Reinventing RAG infrastructure
- Cloud-based or SaaS deployment
- Real-time code watching or live updates
- Code modification or refactoring tools

**Rationale**: Scope creep prevention requires explicit boundaries. These features belong in other tools or violate core principles.

## Development Workflow

### Specification Phase

- Use `/specify` to create feature specifications
- Focus on user value and search quality improvements
- Define acceptance criteria and performance impact
- Mark ambiguities for clarification

### Planning Phase

- Use `/plan` to generate implementation plan
- Research technical approaches (AST parsing, embedding strategies)
- Design data models and API contracts
- Validate against constitutional principles

### Implementation Phase

- Use `/tasks` to generate TDD-ordered task breakdown
- Use `/implement` with orchestrated subagent execution
- Parallel subagents for independent components
- Sequential validation of MCP protocol compliance
- **Git workflow**: Commit after each completed task using `type(scope): description` format
- Each commit MUST pass tests (working state requirement)

### Validation Phase

- Run performance tests against 60s/500ms targets
- Validate MCP protocol compliance
- Test offline operation
- Review logs for protocol pollution

## Governance

### Amendment Process

Constitution changes require:
1. Version increment (MAJOR for scope changes, MINOR for new principles, PATCH for clarifications)
2. Sync Impact Report documenting affected components
3. Validation that changes don't violate core principles
4. Update to this document with clear rationale

### Version Bump Rules

- **MAJOR**: Scope change, principle removal, architectural pivot
- **MINOR**: New principle added, expanded quality standards
- **PATCH**: Clarifications, wording improvements, non-semantic refinements

### Principle Priority

In conflicts, principles are prioritized:
1. **Protocol Compliance** (breaks integrations if violated)
2. **Simplicity Over Features** (prevents scope creep)
3. **Local-First Architecture** (core value proposition)
4. **Performance Guarantees** (user experience requirement)
5. **Production Quality** (reliability requirement)
6. All others (quality of life, development efficiency)

### Complexity Justification

When implementation requires complexity:
- Document the tradeoff explicitly
- Explain why simpler alternatives are insufficient
- Ensure complexity serves a constitutional principle
- Get approval before implementation begins

**Version**: 2.2.0 | **Ratified**: 2025-10-06 | **Last Amended**: 2025-10-06
