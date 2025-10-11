# Codebase MCP Server Constitution

## Preamble

This constitution defines the non-negotiable principles and constraints for the Codebase MCP Server. These principles guide all design decisions, implementation approaches, and feature development. Any violation of these principles must be treated as a CRITICAL issue in planning and analysis phases.

## Core Principles

### Principle I: Simplicity Over Features

**Statement**: The Codebase MCP Server focuses EXCLUSIVELY on semantic code search. Feature requests outside this scope must be rejected.

**Rationale**: A single-purpose tool excels at its core function. Complexity creep leads to maintenance burden, performance degradation, and architectural compromise.

**Constraints**:
- NO work item tracking, task management, or project management features
- NO deployment tracking or CI/CD integration
- NO vendor integrations or vendor status management
- NO code analysis, linting, or refactoring tools beyond search
- Tool surface limited to: `index_repository`, `search_code`

**Acceptable Deviations**: None. This is a non-negotiable principle.

**Enforcement**:
- Design reviews must reject features outside semantic search scope
- PRs adding non-search functionality will be rejected
- `/analyze` flags scope violations as CRITICAL

---

### Principle II: Local-First Architecture

**Statement**: The Codebase MCP Server must operate entirely offline with no cloud dependencies.

**Rationale**: Developers need reliable tools that work without internet connectivity. Cloud dependencies introduce latency, privacy concerns, and availability risks.

**Constraints**:
- Local Ollama instance for embeddings (no OpenAI, no cloud APIs)
- Local PostgreSQL database (no managed database services)
- All models downloaded and cached locally (nomic-embed-text)
- Configuration stored in local files (no remote config servers)

**Acceptable Deviations**:
- Initial model download requires internet (one-time setup)
- Documentation links to external resources (non-functional)

**Enforcement**:
- Integration tests run in airplane mode
- No API keys or cloud credentials in configuration
- `/analyze` checks for cloud service imports

---

### Principle III: Protocol Compliance

**Statement**: The Codebase MCP Server must implement the Model Context Protocol (MCP) specification correctly via Server-Sent Events (SSE) transport with no stdout/stderr pollution.

**Rationale**: Protocol compliance ensures compatibility with all MCP clients (Claude Code, Cline, Zed, etc.). Stdout pollution breaks SSE communication.

**Constraints**:
- Use FastMCP framework with MCP Python SDK
- SSE transport ONLY (no stdio transport)
- All logging via Python logging module to files (not stdout/stderr)
- All errors returned as structured MCP error responses
- No print() statements or debug output to console

**Acceptable Deviations**: None during runtime. Development debugging via file logging only.

**Enforcement**:
- mcp-inspector validation in CI/CD pipeline
- Protocol compliance tests for all tools
- `/analyze` checks for stdout/stderr writes
- Pre-commit hooks block print() statements

---

### Principle IV: Performance Guarantees

**Statement**: The Codebase MCP Server must meet strict performance requirements for indexing and search operations.

**Rationale**: Slow tools disrupt developer flow. Sub-second search is essential for interactive coding workflows.

**Performance Targets**:
- **Indexing**: <60 seconds for 10,000 files
- **Search**: <500ms p95 latency (end-to-end, including embedding generation)
- **Embedding Generation**: <200ms for single query (batched: 50 embeddings <2s)
- **Database Queries**: <100ms for similarity search (with HNSW indexes)

**Constraints**:
- Batched processing for indexing (100 files/batch)
- Batched embedding requests (50 embeddings/batch to Ollama)
- HNSW indexes on embedding columns (not IVFFlat)
- Connection pooling for database (min 5, max 20 connections)
- Async I/O throughout (AsyncPG, aiohttp for Ollama)

**Acceptable Deviations**:
- First-time indexing on cold database (no indexes built yet)
- Ollama model loading delay (first request only)

**Enforcement**:
- Performance benchmarks in CI/CD pipeline
- Profiling on representative codebases (10k files)
- `/analyze` requires performance test results in plan.md

---

### Principle V: Production Quality

**Statement**: All code must meet production-grade standards for error handling, type safety, logging, and observability.

**Rationale**: Production systems fail gracefully, provide actionable diagnostics, and prevent runtime errors through static analysis.

**Constraints**:
- **Error Handling**: All exceptions caught and logged, never silently swallowed
- **Type Safety**: Pydantic models for all data structures, mypy --strict passes
- **Logging**: Structured logging with context (project_id, operation, duration)
- **Validation**: Input validation at API boundaries (tool parameters)
- **Observability**: Metrics for indexing throughput, search latency, error rates

**Acceptable Deviations**: None. These are baseline quality standards.

**Enforcement**:
- mypy --strict in CI/CD (no errors allowed)
- Code coverage >80% (unit + integration tests)
- `/analyze` checks for unhandled exceptions and missing type hints

---

### Principle VI: Specification-First Development

**Statement**: All features must be fully specified before implementation begins. Specifications describe WHAT and WHY, not HOW.

**Rationale**: Clear requirements prevent wasted implementation effort, scope creep, and misalignment with user needs.

**Workflow**:
1. `/specify` creates feature specification (WHAT, WHY, success criteria)
2. `/clarify` resolves ambiguities via targeted Q&A (max 5 questions)
3. `/plan` generates implementation plan (HOW: design artifacts)
4. `/tasks` creates dependency-ordered task breakdown
5. `/implement` executes tasks with micro-commits

**Constraints**:
- NO implementation without approved spec.md and plan.md
- spec.md contains ZERO implementation details (no code, no APIs, no tech stack)
- plan.md validates against constitution at Phase 0 and Phase 1
- All `[NEEDS CLARIFICATION]` markers resolved before planning

**Acceptable Deviations**: Emergency hotfixes (must create retroactive spec within 24h).

**Enforcement**:
- `/plan` errors if spec.md missing or has unresolved clarifications
- `/tasks` errors if plan.md incomplete (Phase 1 not done)
- `/implement` errors if tasks.md missing

---

### Principle VII: Test-Driven Development (TDD)

**Statement**: Tests must be written before implementation code. All tests must pass before merging.

**Rationale**: TDD catches bugs early, validates requirements, and serves as living documentation.

**TDD Cycle**:
1. Write failing test (unit or integration)
2. Implement minimal code to pass test
3. Refactor with tests as safety net
4. Commit when all tests pass

**Test Requirements**:
- **Unit Tests**: All functions/methods with non-trivial logic
- **Integration Tests**: Tool implementations, database operations, Ollama interactions
- **Protocol Tests**: MCP compliance validation (via mcp-inspector)
- **Performance Tests**: Indexing throughput, search latency benchmarks

**Constraints**:
- Tasks in tasks.md follow pattern: Test task → Implementation task
- No implementation task starts without passing tests
- CI/CD blocks merges if tests fail
- Coverage >80% (enforced by pytest-cov)

**Acceptable Deviations**: None. TDD is non-negotiable.

**Enforcement**:
- `/tasks` generates test tasks before implementation tasks
- `/implement` halts on test failures
- Pre-commit hooks run tests (fast unit tests only)

---

### Principle VIII: Pydantic-Based Type Safety

**Statement**: All data structures use Pydantic models. All code passes mypy --strict validation.

**Rationale**: Runtime validation catches invalid data at boundaries. Static type checking prevents entire classes of bugs before code runs.

**Constraints**:
- **Pydantic Models**: MCP tool parameters, database records, API responses
- **Type Hints**: All function signatures, class attributes, module-level variables
- **mypy Configuration**: `--strict` mode (no implicit Any, no untyped definitions)
- **Runtime Validation**: Pydantic validates all external inputs (tool calls, database reads)

**Acceptable Deviations**:
- Third-party library types (use `# type: ignore` with comment explaining why)
- Dynamic metaprogramming (rare, must be justified in code review)

**Enforcement**:
- mypy --strict in CI/CD pipeline (blocks merge on errors)
- Pydantic models for all MCP tool parameter schemas
- `/analyze` checks for missing type hints

---

### Principle IX: Orchestrated Subagent Execution

**Statement**: Implementation uses parallel execution of specialized subagents where tasks are independent.

**Rationale**: Parallel execution reduces implementation time. Specialized subagents focus on single tasks without context switching.

**Execution Model**:
- **Sequential by Default**: Tasks within same file run sequentially
- **Parallel When Safe**: Tasks marked `[P]` run in parallel if file-independent
- **Subagent Specialization**: Each subagent handles one task.md entry
- **Orchestration**: Main agent coordinates subagents, aggregates results

**Constraints**:
- Only mark tasks `[P]` if they modify different files
- No `[P]` for tasks with shared dependencies (database migrations, config)
- Fail fast: Halt parallel batch if any non-optional task fails

**Acceptable Deviations**: Serial execution during debugging (for clearer logs).

**Enforcement**:
- `/tasks` validates `[P]` markers against file dependencies
- `/implement` runs parallel-safe tasks concurrently
- Task failures logged with clear subagent context

---

### Principle X: Git Micro-Commit Strategy

**Statement**: Commit after EVERY completed task in tasks.md. All commits must represent working state (tests pass).

**Rationale**: Small commits simplify debugging, code review, and rollback. Working state ensures bisectability.

**Git Workflow**:
- **Branch per Feature**: `###-feature-name` (e.g., `001-multi-project-search`)
- **Micro-Commits**: One commit per tasks.md entry
- **Conventional Commits**: `type(scope): description`
  - Types: feat, fix, docs, test, refactor, perf, chore
  - Example: `feat(search): add project_id filter parameter`
- **Working State**: All tests pass at every commit
- **Atomic Changes**: One logical change per commit (single file or tightly coupled files)

**Constraints**:
- NO commits with failing tests (CI would reject)
- NO "WIP" or "checkpoint" commits (squash before push)
- NO large commits (>500 lines changed, exceptions: generated code, migrations)

**Acceptable Deviations**:
- Database migrations (schema + data in single commit)
- Refactoring (rename across many files, single commit OK)

**Enforcement**:
- Pre-commit hooks run tests (fast unit tests)
- `/implement` commits after marking task `[X]` complete
- CI runs full test suite on all commits

---

### Principle XI: FastMCP and Python SDK Foundation

**Statement**: The Codebase MCP Server must use the FastMCP framework with the official MCP Python SDK for all MCP functionality.

**Rationale**: FastMCP provides ergonomic abstractions over raw MCP protocol. Using official SDK ensures compatibility and receives upstream updates.

**Constraints**:
- Import `from fastmcp import FastMCP` for server initialization
- Use `@mcp.tool()` decorator for tool registration
- Use Pydantic models for tool parameter schemas
- Use MCP Python SDK types for structured responses
- NO raw JSON-RPC handling or custom protocol implementations

**Technology Stack** (NON-NEGOTIABLE):
- **Python**: 3.11+ (async/await, match statements, type hints)
- **MCP Framework**: FastMCP with MCP Python SDK
- **Database**: PostgreSQL 14+ with pgvector extension
- **Embeddings**: Ollama with nomic-embed-text (768 dimensions)
- **Database Driver**: AsyncPG (async PostgreSQL client)
- **Code Parsing**: Tree-sitter (AST-aware chunking)
- **Validation**: Pydantic 2.x
- **Type Checking**: mypy --strict
- **Testing**: pytest with pytest-asyncio

**Acceptable Deviations**: None. This stack is battle-tested and non-negotiable.

**Enforcement**:
- Dependency pinning in requirements.txt (no alternate implementations)
- `/analyze` checks imports for prohibited libraries (requests vs aiohttp, etc.)
- Architecture reviews validate FastMCP usage patterns

---

## Success Criteria

A feature implementation complies with this constitution if:

1. **Scope**: Only semantic search functionality (Principle I)
2. **Architecture**: Runs entirely offline (Principle II)
3. **Protocol**: Passes mcp-inspector validation (Principle III)
4. **Performance**: Meets latency targets in benchmarks (Principle IV)
5. **Quality**: mypy --strict passes, coverage >80% (Principle V)
6. **Process**: Spec → Plan → Tasks → Implement workflow followed (Principle VI)
7. **Testing**: TDD approach, all tests pass (Principle VII)
8. **Types**: Pydantic models, full type hints (Principle VIII)
9. **Execution**: Parallel tasks where safe (Principle IX)
10. **Git**: Micro-commits, all passing tests (Principle X)
11. **Stack**: FastMCP + Python SDK + required libraries (Principle XI)

---

## Violation Handling

**During Planning** (`/analyze`):
- CRITICAL: Constitutional violations (scope creep, cloud dependencies)
- HIGH: Missing performance benchmarks, mypy errors
- MEDIUM: Incomplete test coverage, missing type hints

**During Implementation** (`/implement`):
- HALT: Test failures, mypy --strict errors
- WARN: Large commits (>500 lines), missing docstrings

**During Code Review**:
- REJECT: Features outside semantic search scope
- REQUEST CHANGES: Protocol violations, performance regressions
- APPROVE: Meets all constitutional requirements

---

## Amendment Process

This constitution is versioned and requires explicit approval to modify:

1. Propose amendment with rationale (GitHub issue or PR)
2. Justify deviation from current principles
3. Update constitution.md with version bump
4. Update dependent templates (spec, plan, tasks)
5. Communicate changes to all contributors

**Current Version**: 1.0.0 (Initial for codebase-mcp refactor)

**Amendment History**: None (initial version)
