<!--
Sync Impact Report:
- Version change: 2.2.0 → 3.0.0 (MAJOR - structural enhancement for governance compliance)
- Principles added: None (all 11 principles remain unchanged)
- Sections added:
  * Preamble - Establishes constitutional authority and governance framework
  * Verification subsections added to ALL 11 principles (Automated/Manual/Tooling enforcement)
  * Enforcement Matrix - Documents automation coverage (64% automated, exceeds >50% threshold)
  * Exception Handling Process - Defines exception request, approval, tracking workflow
  * Compliance Tracking - Documents automated monitoring, manual review, violation response
- Sections modified:
  * Governance expanded significantly (2 new subsections: Exception Handling, Compliance Tracking)
  * All Core Principles (I-XI) now include Verification subsections with enforcement details
- Removed sections: None
- Templates requiring updates:
  * ⚠️ .specify/templates/plan-template.md - Should reference Enforcement Matrix during Phase 0 validation
  * ⚠️ .claude/commands/analyze.md - Should validate against Verification sections per principle
  * ⚠️ .claude/commands/plan.md - Should cross-reference Exception Handling Process
  * ✅ .specify/templates/spec-template.md - No changes needed (tech-agnostic)
- Follow-up TODOs:
  * Create .specify/memory/exceptions.md file for exception tracking
  * Update /analyze command to leverage Verification sections for compliance checks
  * Consider adding pre-commit hooks for automated enforcement (see Enforcement Matrix)
- Previous version history:
  * 2.1.0 → 2.2.0: Added FastMCP and Python SDK Foundation principle
  * 2.0.0 → 2.1.0: Added Git Micro-Commit Strategy principle
  * 1.1.0 → 2.0.0: Project identity change from Specify Template to Codebase MCP Server
  * 1.0.0 → 1.1.0: Added Pydantic and Orchestration principles
  * Initial: 1.0.0 - Specify Template constitution
-->

# Codebase MCP Server Constitution

## Project Identity

**Purpose**: A focused, production-grade MCP server that indexes code repositories into PostgreSQL with pgvector for semantic search, designed specifically for AI coding assistants.

**Scope**: Do one thing exceptionally well - semantic code search. Not a generic knowledge base, not a full IDE, not reinventing RAG infrastructure.

## Preamble

This constitution defines the non-negotiable architectural and quality principles for the Codebase MCP Server. All feature specifications, implementation plans, and code contributions MUST comply with these standards. The `/analyze` command validates compliance before implementation begins. Constitutional violations flagged as CRITICAL block feature progression.

This document serves as the authoritative governance framework for all development decisions. When in doubt, defer to constitutional principles. When principles conflict, follow the priority order defined in the Governance section.

## Core Principles

### I. Simplicity Over Features (NON-NEGOTIABLE)

The MCP server MUST focus exclusively on semantic code search. Feature requests that extend beyond indexing, embedding, and searching code repositories MUST be rejected. Each component MUST have a single, clear responsibility. Complexity MUST be justified against measurable user value.

**Rationale**: Feature creep destroys maintainability and performance. A tool that does one thing perfectly is more valuable than one that does many things poorly. Semantic search is complex enough without additional concerns.

**Verification**:
- Automated: Ruff complexity checks (configured in pyproject.toml), `/analyze` command flags scope violations as CRITICAL
- Manual: Specification review during `/specify` phase validates features against scope boundaries, code review rejects PRs extending beyond semantic search
- Tooling: Project Non-Goals section in constitution serves as rejection criteria checklist

### II. Local-First Architecture

The system MUST operate completely offline after initial setup. All dependencies MUST be locally hosted (PostgreSQL, Ollama). Zero cloud API calls are permitted except to local Ollama instance. The database schema MUST be standard PostgreSQL, allowing data reuse across tools.

**Rationale**: Privacy, reliability, and speed require local execution. External APIs introduce latency, costs, privacy risks, and single points of failure. Standard schemas enable interoperability.

**Verification**:
- Automated: Integration tests validate offline operation after initial setup (`tests/integration/test_ai_assistant_integration.py`), httpx client configured to only allow localhost connections
- Manual: Code review inspects all HTTP client instantiations for external API calls, architecture review validates database schema portability
- Tooling: Network monitoring tests detect unauthorized external connections during test suite execution

### III. Protocol Compliance (MCP via SSE)

All MCP communication MUST use SSE transport. Stdout and stderr MUST NEVER contain protocol messages or application logs. Logging MUST go exclusively to `/tmp/codebase-mcp.log`. The server MUST implement MCP specification correctly with no protocol violations.

**Rationale**: MCP protocol violations break AI assistant integrations. Stdout/stderr pollution causes parsing failures. File-based logging enables debugging without breaking the protocol.

**Verification**:
- Automated: Contract tests validate MCP protocol compliance (`tests/contract/test_transport_compliance.py`, `test_schema_generation.py`, `test_tool_registration.py`), structured logging tests ensure no stdout/stderr pollution
- Manual: Manual integration testing with Claude Code CLI validates end-to-end protocol behavior (`tests/manual/test_fastmcp_startup.py`)
- Tooling: FastMCP framework provides built-in protocol validation, pytest markers segregate contract tests (`@pytest.mark.contract`)

### IV. Performance Guarantees

The system MUST meet these performance targets:
- Index 10,000 line codebase in under 60 seconds
- Search queries MUST return in under 500ms (p95)
- Database operations MUST be fully asynchronous
- Embedding generation MUST batch efficiently

**Rationale**: Slow tools break developer flow. These targets ensure the MCP server enhances rather than hinders AI assistant responsiveness. Async operations prevent blocking.

**Verification**:
- Automated: pytest-benchmark validates indexing and search performance baselines (`tests/performance/test_baseline.py`), performance validation tests enforce 60s/500ms targets (`tests/integration/test_performance_validation.py`)
- Manual: py-spy profiling during code review identifies blocking operations, manual load testing with realistic codebases validates production performance
- Tooling: pytest-benchmark for baseline tracking, scripts/collect_baseline.sh establishes performance regression detection

### V. Production Quality Standards

Error handling MUST be comprehensive with specific error messages. All exceptions MUST be caught and logged with context. Type hints MUST be complete and enforced with mypy --strict. Configuration MUST validate on startup, failing fast with clear error messages. File-based structured logging MUST capture all errors with timestamps and context.

**Rationale**: Production systems fail gracefully. Users need actionable error messages. Type safety catches bugs before runtime. Fast failure prevents silent corruption.

**Verification**:
- Automated: mypy --strict enforces complete type coverage (configured in pyproject.toml with strict=true), Ruff linter validates error handling patterns and logging format, pytest-cov enforces 95%+ coverage threshold blocking merges
- Manual: Code review validates error message clarity and context propagation, manual testing of failure scenarios validates graceful degradation
- Tooling: Pydantic validators enforce configuration schema at runtime, structured logging tests validate JSON format and field completeness (`tests/unit/test_logging.py`)

### VI. Specification-First Development

Feature specifications MUST be completed before implementation planning. Specifications focus on user requirements (WHAT/WHY) without implementation details (HOW). All specifications MUST include acceptance criteria and test scenarios.

**Rationale**: Clear requirements prevent implementation drift and enable effective testing. Separating concerns allows specification by domain experts and implementation by engineers.

**Verification**:
- Automated: `/plan` command validates spec.md existence before generating implementation plan, `/tasks` command validates plan.md existence before task generation, `/analyze` command flags missing acceptance criteria as HIGH severity
- Manual: `/clarify` command facilitates interactive requirements refinement before planning, workflow gates enforce sequential `/specify` → `/plan` → `/tasks` → `/implement` progression
- Tooling: check-prerequisites.sh script validates artifact dependencies, spec-template.md structure enforces WHAT/WHY separation from HOW implementation details

### VII. Test-Driven Development

Test tasks MUST precede implementation tasks. Integration tests MUST validate MCP protocol compliance. Unit tests MUST cover edge cases and error conditions. Performance tests MUST validate against guarantees (60s indexing, 500ms search).

**Rationale**: Tests define correct behavior before implementation. Protocol compliance testing prevents integration breakage. Performance tests prevent regression of guarantees.

**Verification**:
- Automated: pytest with pytest-cov for 80%+ coverage gates in CI, mypy --strict for type safety, performance benchmarks in test suite
- Manual: Code review validates tests written before implementation, test scenarios match acceptance criteria in spec.md
- Tooling: pytest-cov with --fail-under=80, pytest-asyncio for async tests, MCP protocol compliance test fixtures

### VIII. Pydantic-Based Type Safety

All data models MUST use Pydantic with explicit types and validators. MCP protocol messages MUST inherit from `pydantic.BaseModel`. Configuration MUST use `pydantic_settings.BaseSettings` for environment variables. Database models MUST use SQLAlchemy with full type hints. Validation errors MUST be caught at system boundaries with clear field-level messages.

**Rationale**: Pydantic provides runtime validation preventing invalid data propagation. Configuration validation fails fast on startup. Type safety catches bugs before production. Clear error messages enable quick debugging.

**Verification**:
- Automated: mypy --strict enforces complete type hints and Pydantic model usage, CI blocks on type errors, pydantic validators run at model instantiation
- Manual: Code review validates BaseModel inheritance for all DTOs, checks pydantic_settings.BaseSettings usage for config
- Tooling: mypy with strict mode, pydantic v2 with model_validator decorators, SQLAlchemy 2.0+ with Mapped[] type annotations

### IX. Orchestrated Subagent Execution

During implementation, the orchestrating agent MUST delegate code-writing tasks to specialized subagents. Independent tasks MUST be executed in parallel using concurrent subagent launches. Each subagent receives complete context (spec, plan, contracts, data model). The orchestrator coordinates results, resolves conflicts, and validates completion.

**Rationale**: Specialized subagents focus without context switching. Parallel execution reduces implementation time. Orchestrator-level coordination maintains consistency and quality.

**Verification**:
- Automated: Task dependency analysis in tasks.md validates parallel task marking ([P]), integration tests verify all subagent outputs integrate correctly
- Manual: /implement command reviews task completion markers ([X]), orchestrator validates subagent context delivery, conflict resolution documented in commit messages
- Tooling: tasks.md template with [P] parallel markers, feature branch isolation for conflict detection, test suite validates cross-component integration

### X. Git Micro-Commit Strategy

Every feature MUST be developed on a dedicated branch created from main. Commits MUST be atomic and frequent (micro-commits after each completed task or logical unit). Commit messages MUST follow Conventional Commits format (`type(scope): description`). Each commit MUST represent a working state (tests pass). Branch names MUST follow `###-feature-name` pattern with 3-digit prefix. Features MUST NOT be merged until all acceptance criteria pass.

**Rationale**: Micro-commits create granular history enabling precise debugging and rollback. Branch-per-feature isolates work and enables parallel development. Atomic commits ensure bisectability. Conventional Commits enable automated changelog generation and semantic versioning.

**Verification**:
- Automated: commitlint validates Conventional Commits format in pre-commit hooks, CI runs full test suite per commit to verify working state, branch naming regex validation
- Manual: Code review validates atomic commits (one logical change per commit), PR review checklist confirms all acceptance criteria met before merge
- Tooling: pre-commit hooks with commitlint, create-new-feature.sh script enforces branch naming pattern, CI pipeline blocks failing tests

### XI. FastMCP and Python SDK Foundation

All MCP server implementations MUST be built using FastMCP (https://github.com/jlowin/fastmcp) as the primary framework and the official MCP Python SDK (https://github.com/modelcontextprotocol/python-sdk) for protocol compliance. FastMCP's decorative patterns MUST be used for tool, resource, and prompt registration. The server MUST leverage FastMCP's built-in context injection, automatic schema generation from type hints, and transport abstraction. Direct protocol handling MUST be avoided in favor of FastMCP's high-level API.

**Rationale**: FastMCP provides the shortest path from implementation to production while maintaining protocol compliance. Automatic schema generation from type hints ensures consistency between code and API contracts. Framework-level transport abstraction prevents protocol violations. Decorator patterns keep tool implementations clean and focused. Using established frameworks prevents reinventing protocol machinery and reduces maintenance burden.

**Verification**:
- Automated: Dependency check validates fastmcp and mcp package versions in requirements.txt, import analysis scans for direct MCP SDK usage (should use FastMCP wrapper), protocol compliance tests validate SSE transport
- Manual: Code review validates @mcp.tool(), @mcp.resource(), @mcp.prompt() decorator usage, checks for direct protocol handling bypassing FastMCP
- Tooling: FastMCP framework for all MCP operations, MCP Python SDK for protocol types, integration tests validate transport abstraction works correctly

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

## Enforcement Matrix

This matrix documents which constitutional principles have automated enforcement and which require manual validation. Target: >50% automation coverage.

| Principle | Enforcement Type | Tool/Process | CI Stage |
|-----------|------------------|--------------|----------|
| I. Simplicity Over Features | Manual | Spec review, /analyze CRITICAL flags | Pre-planning |
| II. Local-First Architecture | Automated | Network call detection, offline tests | Pre-commit, CI |
| III. Protocol Compliance (MCP) | Automated | MCP integration tests, log analysis | CI |
| IV. Performance Guarantees | Automated | pytest-benchmark, k6 load tests | CI |
| V. Production Quality Standards | Automated | mypy --strict, pylint, error checks | Pre-commit, CI |
| VI. Specification-First Development | Manual | Workflow gates (/plan requires spec) | Pre-planning |
| VII. Test-Driven Development | Mixed | pytest-cov (80% gate), task ordering | CI, planning |
| VIII. Pydantic Type Safety | Automated | mypy --strict, pydantic validators | Pre-commit, CI |
| IX. Orchestrated Subagent Execution | Manual | Implementation review, parallelism check | Post-implementation |
| X. Git Micro-Commit Strategy | Automated | commitlint, branch name validation | Pre-push |
| XI. FastMCP Foundation | Automated | Dependency check, import analysis | CI |

**Automation Coverage**: 7/11 (64%) - exceeds >50% threshold ✅

**Notes**:
- **Automated**: Enforcement via CI/CD pipelines, pre-commit hooks, or runtime validation
- **Manual**: Human review required (spec validation, architecture review)
- **Mixed**: Combination of automated metrics + human judgment

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


### Exception Handling Process

When a constitutional principle cannot be met, an exception may be requested:

**Request Process**:
1. Create GitHub issue with label `constitution-exception`
2. Document specific principle(s) requiring exception
3. Provide detailed justification:
   - Why the principle cannot be met
   - What alternatives were considered
   - Quantified impact analysis
   - Proposed mitigation strategy
4. Specify time-bound duration (temporary) or permanent exception

**Approval Requirements**:
- **Temporary Exceptions** (<30 days): Project maintainer approval + documented in `exceptions.md`
- **Extended Exceptions** (30-90 days): 2 approvals (maintainer + technical reviewer)
- **Permanent Exceptions**: Constitution amendment required (MAJOR version bump)

**Tracking**:
- All exceptions logged in `.specify/memory/exceptions.md` with:
  - Exception ID
  - Principle affected
  - Justification summary
  - Approval date and approvers
  - Sunset date (for temporary exceptions)
  - Resolution status

**Grace Periods**:
- New principles have 30-day grace period for existing code
- Breaking changes require migration plan before enforcement
- Performance targets enforceable only after tooling setup complete

### Compliance Tracking

Constitutional compliance is monitored through:

**Automated Monitoring**:
- CI/CD pipeline runs enforcement checks (see Enforcement Matrix)
- Pre-commit hooks block common violations (type safety, commit format)
- `/analyze` command validates specifications against principles

**Manual Review**:
- Quarterly constitution audit reviewing:
  - Active exceptions (review sunset dates)
  - Principle violation trends
  - Enforcement effectiveness
  - Potential principle updates
- Spec review process validates feature requests against scope
- Implementation review validates orchestration and code quality

**Violation Response**:
1. **CRITICAL violations**: Block merge, require fix before proceeding
2. **WARNING violations**: Document in PR, require justification or fix
3. **INFO violations**: Advisory only, tracked for trends

**Metrics**:
- Track exception request rate (target: <5% of PRs)
- Track CRITICAL violation block rate
- Track automation coverage percentage (maintain >50%)

**Version**: 3.0.0 | **Ratified**: 2025-10-06 | **Last Amended**: 2025-10-12
