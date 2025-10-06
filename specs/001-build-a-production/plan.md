# Implementation Plan: Production-Grade MCP Server for Semantic Code Search

**Branch**: `001-build-a-production` | **Date**: 2025-10-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-build-a-production/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from file system structure or context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code, or `AGENTS.md` for all other agents).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Build a production-grade MCP server that indexes code repositories into PostgreSQL with pgvector for semantic search, designed for AI coding assistants. The system provides semantic code search (60s indexing for 10K files, 500ms query latency) and task tracking with git integration (status, branch, commits). Uses Python 3.11+, FastAPI, PostgreSQL 14+ with pgvector, Ollama for embeddings, and Tree-sitter for AST-based code parsing.

## Technical Context
**Language/Version**: Python 3.11+ (required for modern type hints and async features)
**Primary Dependencies**: FastAPI (async web framework), SQLAlchemy with AsyncPG (async ORM), Pydantic (data validation), MCP SDK for Python with SSE transport, Tree-sitter (AST parsing)
**Storage**: PostgreSQL 14+ with pgvector extension for vector similarity search
**Testing**: pytest with pytest-asyncio for async tests, MCP protocol compliance tests
**Target Platform**: Linux/macOS server (local-first, offline-capable after setup)
**Project Type**: Single (MCP server with indexing, search, and task management)
**Performance Goals**: Index 10,000 files (1M lines) in 60s, search queries <500ms p95 latency
**Constraints**: Local-first (no cloud APIs), MCP protocol compliance (SSE only, no stdout/stderr pollution), async operations throughout
**Scale/Scope**: Medium repositories (up to 10K files/1M lines), language-agnostic text file indexing

**Clarified Requirements** (from /clarify session):
- Performance: 60s indexing for medium repos (10K files/1M lines), 500ms search p95
- Deletion policy: Mark deleted, retain 90 days before removal
- File filtering: .gitignore + custom .mcpignore patterns
- Language support: All text files, language-agnostic with auto-detection

**Remaining Ambiguities** (deferred to implementation):
- FR-013: Search result context lines (propose: 10 lines before/after)
- FR-014: Search filtering criteria (propose: file type, directory, date range)
- FR-017: Task planning references format (propose: relative file paths)
- FR-021: Task history detail (propose: status changes, timestamps, user)
- FR-026/FR-037: Concurrency level (propose: 10 concurrent AI assistants)
- FR-031: Transaction requirements (propose: SERIALIZABLE for consistency)
- FR-032: Backup strategy (propose: manual pg_dump with documented process)
- FR-040: Health checks (propose: /health endpoint with DB connectivity)

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Simplicity Over Features
✅ **COMPLIANT** - Feature scope is tightly bounded to semantic code search and task tracking. No scope creep into IDE features, generic knowledge bases, or RAG infrastructure. Each component has single responsibility: indexer, embedder, searcher, task manager.

### Principle II: Local-First Architecture
✅ **COMPLIANT** - All dependencies are local (PostgreSQL, Ollama). Zero cloud API calls. Offline operation after setup. Standard PostgreSQL schema for interoperability.

### Principle III: Protocol Compliance (MCP via SSE)
✅ **COMPLIANT** - MCP communication uses SSE transport exclusively. Logging goes to `/tmp/codebase-mcp.log`. No stdout/stderr pollution. MCP specification compliance required.

### Principle IV: Performance Guarantees
✅ **COMPLIANT** - Targets align with constitution: 60s indexing for 10K files, 500ms search p95. Async operations throughout. Batch embedding generation planned.

### Principle V: Production Quality Standards
✅ **COMPLIANT** - Comprehensive error handling, mypy --strict type safety, Pydantic validation, config validation on startup, structured JSON logging to file.

### Principle VI: Specification-First Development
✅ **COMPLIANT** - Specification completed before planning. Clarifications session resolved key ambiguities. Acceptance criteria and test scenarios defined.

### Principle VII: Test-Driven Development
✅ **COMPLIANT** - Plan includes contract tests before implementation. Integration tests for MCP protocol. Performance tests for 60s/500ms targets. Unit tests for edge cases.

### Principle VIII: Pydantic-Based Type Safety
✅ **COMPLIANT** - All models use Pydantic. MCP messages inherit BaseModel. Configuration uses pydantic_settings.BaseSettings. SQLAlchemy models with full type hints. Field-level validation errors.

### Principle IX: Orchestrated Subagent Execution
✅ **COMPLIANT** - Implementation phase will use parallel subagents for independent components (indexer, embedder, searcher, task manager). Orchestrator coordinates and validates.

### Principle X: Git Micro-Commit Strategy
✅ **COMPLIANT** - Feature branch `001-build-a-production` created. Tasks will specify commit points. Conventional Commits format enforced. Each commit must pass tests.

**Initial Constitution Check**: ✅ PASS - No violations detected

## Project Structure

### Documentation (this feature)
```
specs/001-build-a-production/
├── spec.md              # Feature specification
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
│   ├── mcp-protocol.json    # MCP SSE transport contract
│   ├── search-api.json      # Semantic search endpoints
│   └── tasks-api.json       # Task management endpoints
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
src/
├── config/              # Pydantic settings, environment config
├── models/              # SQLAlchemy models, Pydantic schemas
│   ├── database.py      # DB models (CodeFile, Task, Embedding)
│   └── schemas.py       # Pydantic request/response schemas
├── services/            # Core business logic
│   ├── indexer.py       # Repository scanning, file detection
│   ├── embedder.py      # Ollama integration, embedding generation
│   ├── searcher.py      # Vector similarity search
│   ├── chunker.py       # Tree-sitter AST-based code chunking
│   └── tasks.py         # Task CRUD, git integration
├── mcp/                 # MCP protocol implementation
│   ├── server.py        # SSE transport, protocol handler
│   ├── tools.py         # MCP tool definitions
│   └── logging.py       # Structured file logging
└── main.py              # Application entry point

tests/
├── contract/            # API contract validation tests
│   ├── test_mcp_protocol.py
│   ├── test_search_api.py
│   └── test_tasks_api.py
├── integration/         # End-to-end workflow tests
│   ├── test_indexing_flow.py
│   ├── test_search_flow.py
│   └── test_task_flow.py
└── unit/                # Component unit tests
    ├── test_indexer.py
    ├── test_embedder.py
    ├── test_searcher.py
    ├── test_chunker.py
    └── test_tasks.py

migrations/              # Database schema migrations
└── versions/

scripts/                 # Utility scripts
├── init_db.py          # Database setup with pgvector
└── benchmark.py        # Performance validation
```

**Structure Decision**: Single project structure chosen - this is an MCP server (backend service) without frontend. All components are in unified `src/` with clear separation: config, models, services (core logic), and mcp (protocol). Tests mirror the source structure with contract/integration/unit separation per TDD requirements.

## Phase 0: Outline & Research
*Executed by /plan command*

### Research Tasks
1. ✅ **MCP SDK Python SSE Transport** - Use `mcp` SDK with SSE, file logging to `/tmp/codebase-mcp.log`
2. ✅ **Tree-sitter for Multi-Language Parsing** - AST-based chunking with dynamic grammar loading, fallback for unsupported languages
3. ✅ **PostgreSQL pgvector Extension** - HNSW indexing with cosine distance for 768-dim vectors
4. ✅ **Ollama HTTP API Integration** - Direct HTTP calls with `httpx`, batch embeddings (50-100 texts)
5. ✅ **Async SQLAlchemy Patterns** - SQLAlchemy 2.0+ with AsyncPG, connection pooling (20 connections)
6. ✅ **File Change Detection** - Timestamp-based polling for reliability and cross-platform support
7. ✅ **Pydantic Settings Management** - `pydantic-settings` BaseSettings with validation and .env support
8. ✅ **Performance Profiling Strategy** - Custom timing decorators, SQL logging, targeted optimization

**Output**: ✅ research.md created with all technical decisions documented

## Phase 1: Design & Contracts
*Executed by /plan command after Phase 0*

### Design Artifacts
1. ✅ **data-model.md** - 11 entities with SQLAlchemy models, Pydantic schemas, indexes, state transitions
2. ✅ **contracts/mcp-protocol.json** - MCP SSE tool contracts: search_code, index_repository, task CRUD
3. ✅ **quickstart.md** - 7 integration test scenarios covering all acceptance criteria
4. ✅ **CLAUDE.md** - Updated agent context with Python 3.11+, FastAPI, PostgreSQL, pgvector

**Output**: ✅ All Phase 1 artifacts generated and validated

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `.specify/templates/tasks-template.md` as base
- Generate TDD-ordered tasks from Phase 1 artifacts
- Contract tests first (one per API contract)
- Model creation tasks (database models + Pydantic schemas)
- Integration test tasks (from quickstart.md scenarios)
- Implementation tasks to make tests pass
- Performance validation tasks (60s indexing, 500ms search)

**Ordering Strategy**:
- **Phase 1 - Foundation**: Database setup, config, models [P]
- **Phase 2 - Core Services**: Indexer, embedder, chunker, searcher [P]
- **Phase 3 - MCP Protocol**: SSE transport, tool registration, logging
- **Phase 4 - Task Management**: CRUD operations, git integration
- **Phase 5 - Integration**: End-to-end workflows, performance tests
- Mark [P] for parallel execution where tasks touch different files

**Estimated Output**: 30-35 numbered, dependency-ordered tasks in tasks.md

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)
**Phase 4**: Implementation (execute tasks.md with orchestrated subagents, git micro-commits)
**Phase 5**: Validation (MCP protocol tests, performance benchmarks, quickstart execution)

## Complexity Tracking
*No constitutional violations detected - section empty per template requirements*

## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [X] Phase 0: Research complete (/plan command) ✅
- [X] Phase 1: Design complete (/plan command) ✅
- [X] Phase 2: Task planning complete (/plan command - describe approach only) ✅
- [X] Phase 3: Tasks generated (/tasks command) ✅
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [X] Initial Constitution Check: PASS ✅
- [X] Post-Design Constitution Check: PASS ✅
- [X] All NEEDS CLARIFICATION resolved (deferred items documented in Technical Context) ✅
- [X] Complexity deviations documented (none - fully compliant) ✅

---
*Based on Constitution v2.1.0 - See `.specify/memory/constitution.md`*
