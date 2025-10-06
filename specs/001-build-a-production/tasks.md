# Tasks: Production-Grade MCP Server for Semantic Code Search

**Input**: Design documents from `/specs/001-build-a-production/`
**Prerequisites**: plan.md, research.md, data-model.md, contracts/mcp-protocol.json, quickstart.md
**Branch**: `001-build-a-production`
**Tech Stack**: Python 3.11+, FastAPI, PostgreSQL 14+ with pgvector, SQLAlchemy async, Pydantic, MCP SDK, Tree-sitter, Ollama

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → Extract: Python 3.11+, FastAPI, PostgreSQL, pgvector, MCP SDK, Tree-sitter
2. Load design documents:
   → data-model.md: 11 entities (Repository, CodeFile, CodeChunk, Task, etc.)
   → contracts/mcp-protocol.json: 6 MCP tools (search_code, index_repository, task CRUD)
   → quickstart.md: 7 integration scenarios
3. Generate tasks by category:
   → Setup: Python project, PostgreSQL, dependencies
   → Tests: Contract tests (6 tools), Integration tests (7 scenarios)
   → Core: Models (11 entities), Services (indexer, embedder, searcher, tasks)
   → Integration: MCP server, database, logging
   → Polish: Unit tests, performance validation, documentation
4. Apply TDD ordering: Tests before implementation
5. Mark [P] for parallel execution (different files)
6. Validate: All contracts tested, all entities modeled, TDD compliance
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions
- Commit after each task completion

## Path Conventions
**Single project structure** (from plan.md):
- Source: `src/` (config, models, services, mcp)
- Tests: `tests/` (contract, integration, unit)
- Scripts: `scripts/`
- Migrations: `migrations/versions/`

---

## Phase 3.1: Setup & Foundation

- [ ] **T001** Create Python project structure with directories: `src/`, `tests/{contract,integration,unit}/`, `scripts/`, `migrations/`
  - **Files**: Create directory structure per plan.md
  - **Commit**: `chore(setup): initialize project structure`

- [ ] **T002** Initialize Python 3.11+ project with pyproject.toml and dependencies
  - **Files**: `pyproject.toml`, `requirements.txt`
  - **Dependencies**: fastapi, sqlalchemy[asyncpg], pydantic-settings, mcp, tree-sitter, httpx, pytest, pytest-asyncio, mypy, alembic, pgvector
  - **Commit**: `chore(setup): add project dependencies`

- [ ] **T003** [P] Configure linting and type checking
  - **Files**: `.pre-commit-config.yaml`, `mypy.ini`, `pyproject.toml` (ruff config)
  - **Tools**: mypy --strict, ruff for linting/formatting
  - **Commit**: `chore(setup): configure linting and type checking`

- [ ] **T004** [P] Setup structured logging configuration
  - **Files**: `src/mcp/logging.py`
  - **Requirements**: JSON logging to `/tmp/codebase-mcp.log`, no stdout/stderr pollution
  - **Commit**: `feat(logging): add structured file logging`

- [ ] **T005** Create Pydantic settings configuration
  - **Files**: `src/config/settings.py`
  - **Config**: DATABASE_URL, OLLAMA_BASE_URL, OLLAMA_MODEL, batch sizes, performance params
  - **Validation**: fail-fast on startup with clear error messages
  - **Commit**: `feat(config): add Pydantic settings with validation`

---

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Contract Tests (from contracts/mcp-protocol.json)

- [ ] **T006** [P] Contract test for `search_code` MCP tool
  - **File**: `tests/contract/test_search_code_contract.py`
  - **Validates**: Input schema (query, filters, limit), output schema (results, total_count, latency_ms), p95 <500ms
  - **Must fail**: Tool not implemented yet
  - **Commit**: `test(contract): add search_code tool contract test`

- [ ] **T007** [P] Contract test for `index_repository` MCP tool
  - **File**: `tests/contract/test_index_repository_contract.py`
  - **Validates**: Input schema (path, name, force_reindex), output schema (repository_id, files_indexed, duration_seconds)
  - **Must fail**: Tool not implemented yet
  - **Commit**: `test(contract): add index_repository tool contract test`

- [ ] **T008** [P] Contract test for `get_task` MCP tool
  - **File**: `tests/contract/test_get_task_contract.py`
  - **Validates**: Input schema (task_id UUID), output schema (Task object with all fields)
  - **Must fail**: Tool not implemented yet
  - **Commit**: `test(contract): add get_task tool contract test`

- [ ] **T009** [P] Contract test for `list_tasks` MCP tool
  - **File**: `tests/contract/test_list_tasks_contract.py`
  - **Validates**: Input schema (status, branch, limit), output schema (tasks array, total_count)
  - **Must fail**: Tool not implemented yet
  - **Commit**: `test(contract): add list_tasks tool contract test`

- [ ] **T010** [P] Contract test for `create_task` MCP tool
  - **File**: `tests/contract/test_create_task_contract.py`
  - **Validates**: Input schema (title, description, notes, planning_references), output schema (Task object)
  - **Must fail**: Tool not implemented yet
  - **Commit**: `test(contract): add create_task tool contract test`

- [ ] **T011** [P] Contract test for `update_task` MCP tool
  - **File**: `tests/contract/test_update_task_contract.py`
  - **Validates**: Input schema (task_id, optional updates, branch, commit), output schema (updated Task)
  - **Must fail**: Tool not implemented yet
  - **Commit**: `test(contract): add update_task tool contract test`

### Integration Tests (from quickstart.md scenarios)

- [ ] **T012** [P] Integration test: Repository indexing with ignore patterns
  - **File**: `tests/integration/test_repository_indexing.py`
  - **Scenario**: Index `/tmp/test-repo`, verify files indexed, chunks created, .gitignore respected
  - **Must fail**: Indexing not implemented yet
  - **Commit**: `test(integration): add repository indexing test`

- [ ] **T013** [P] Integration test: Incremental updates for modified files
  - **File**: `tests/integration/test_incremental_updates.py`
  - **Scenario**: Modify file, verify only changed file re-indexed, change event recorded
  - **Must fail**: Incremental update logic not implemented yet
  - **Commit**: `test(integration): add incremental updates test`

- [ ] **T014** [P] Integration test: Semantic code search with filters
  - **File**: `tests/integration/test_semantic_search.py`
  - **Scenario**: Search "add two numbers", verify relevant results with high similarity, test filters
  - **Must fail**: Search not implemented yet
  - **Commit**: `test(integration): add semantic search test`

- [ ] **T015** [P] Integration test: Task creation and status tracking
  - **File**: `tests/integration/test_task_lifecycle.py`
  - **Scenario**: Create task, update to in-progress with branch, complete with commit, verify history
  - **Must fail**: Task management not implemented yet
  - **Commit**: `test(integration): add task lifecycle test`

- [ ] **T016** [P] Integration test: AI assistant context queries
  - **File**: `tests/integration/test_ai_assistant_integration.py`
  - **Scenario**: List in-progress tasks, search code, verify context linking
  - **Must fail**: AI integration not implemented yet
  - **Commit**: `test(integration): add AI assistant integration test`

- [ ] **T017** [P] Integration test: File deletion 90-day retention
  - **File**: `tests/integration/test_file_deletion_retention.py`
  - **Scenario**: Delete file, verify marked deleted with retention, test cleanup after 90 days
  - **Must fail**: Deletion retention not implemented yet
  - **Commit**: `test(integration): add file deletion retention test`

- [ ] **T018** [P] Integration test: Performance validation (60s indexing, 500ms search)
  - **File**: `tests/integration/test_performance_validation.py`
  - **Scenario**: Index 10K files in <60s, run 100 searches with p95 <500ms
  - **Must fail**: Performance not optimized yet
  - **Commit**: `test(integration): add performance validation test`

---

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### Database Models & Schema

- [ ] **T019** [P] Create database base and engine setup
  - **File**: `src/models/database.py`
  - **Content**: AsyncEngine, Base, async session factory
  - **Commit**: `feat(database): add async SQLAlchemy engine setup`

- [ ] **T020** [P] Repository model and Pydantic schema
  - **File**: `src/models/repository.py`
  - **Content**: SQLAlchemy Repository model, RepositoryCreate/Response schemas
  - **Commit**: `feat(models): add Repository model and schemas`

- [ ] **T021** [P] CodeFile model and Pydantic schema
  - **File**: `src/models/code_file.py`
  - **Content**: SQLAlchemy CodeFile model with deletion tracking, CodeFileResponse schema
  - **Commit**: `feat(models): add CodeFile model and schemas`

- [ ] **T022** [P] CodeChunk model with pgvector embedding
  - **File**: `src/models/code_chunk.py`
  - **Content**: SQLAlchemy CodeChunk model with Vector(768) embedding, HNSW index, CodeChunkCreate/Response schemas
  - **Commit**: `feat(models): add CodeChunk model with pgvector`

- [ ] **T023** [P] Task model and Pydantic schemas
  - **File**: `src/models/task.py`
  - **Content**: SQLAlchemy Task model with status constraint, TaskCreate/Update/Response schemas
  - **Commit**: `feat(models): add Task model and schemas`

- [ ] **T024** [P] Task relationship models (planning, branch, commit, history)
  - **File**: `src/models/task_relations.py`
  - **Content**: TaskPlanningReference, TaskBranchLink, TaskCommitLink, TaskStatusHistory models
  - **Commit**: `feat(models): add Task relationship models`

- [ ] **T025** [P] ChangeEvent and EmbeddingMetadata models
  - **File**: `src/models/tracking.py`
  - **Content**: ChangeEvent, EmbeddingMetadata, SearchQuery models
  - **Commit**: `feat(models): add tracking models`

- [ ] **T026** Create Alembic migration for initial schema
  - **File**: `migrations/versions/001_initial_schema.py`
  - **Content**: Create all tables, pgvector extension, HNSW indexes, constraints
  - **Dependencies**: T019-T025 (all models must exist)
  - **Commit**: `feat(database): add initial schema migration`

- [ ] **T027** Create database initialization script
  - **File**: `scripts/init_db.py`
  - **Content**: Run migrations, verify pgvector extension, validate schema
  - **Commit**: `feat(scripts): add database initialization script`

### Core Services

- [ ] **T028** [P] File scanner service with ignore pattern support
  - **File**: `src/services/scanner.py`
  - **Content**: Scan repository, respect .gitignore + .mcpignore, detect changes by mtime
  - **Commit**: `feat(services): add file scanner with ignore patterns`

- [ ] **T029** [P] Tree-sitter code chunker service
  - **File**: `src/services/chunker.py`
  - **Content**: AST-based chunking, function/class detection, fallback for unsupported languages
  - **Commit**: `feat(services): add Tree-sitter code chunker`

- [ ] **T030** [P] Ollama embedder service with batching
  - **File**: `src/services/embedder.py`
  - **Content**: HTTP calls to Ollama, batch embeddings (50-100), retry logic, timeout handling
  - **Commit**: `feat(services): add Ollama embedder with batching`

- [ ] **T031** Repository indexer orchestration service
  - **File**: `src/services/indexer.py`
  - **Content**: Orchestrate scan → chunk → embed → store, incremental updates, performance tracking
  - **Dependencies**: T028, T029, T030 (scanner, chunker, embedder)
  - **Commit**: `feat(services): add repository indexer orchestration`

- [ ] **T032** [P] Semantic search service with pgvector
  - **File**: `src/services/searcher.py`
  - **Content**: Generate query embedding, pgvector cosine similarity search, filter by file type/directory, context lines (10 before/after)
  - **Commit**: `feat(services): add semantic search with pgvector`

- [ ] **T033** [P] Task CRUD service with git integration
  - **File**: `src/services/tasks.py`
  - **Content**: Create/update/query tasks, manage status transitions, link branches/commits, record history
  - **Commit**: `feat(services): add task CRUD service`

### MCP Protocol Implementation

- [ ] **T034** MCP server setup with SSE transport
  - **File**: `src/mcp/server.py`
  - **Content**: Initialize MCP Server, configure SSE transport, tool registration framework
  - **Commit**: `feat(mcp): add MCP server with SSE transport`

- [ ] **T035** Implement `search_code` MCP tool
  - **File**: `src/mcp/tools/search.py`
  - **Content**: Tool handler for semantic search, input validation, response formatting
  - **Dependencies**: T032 (searcher service)
  - **Commit**: `feat(mcp): implement search_code tool`

- [ ] **T036** Implement `index_repository` MCP tool
  - **File**: `src/mcp/tools/indexing.py`
  - **Content**: Tool handler for repository indexing, progress tracking, error handling
  - **Dependencies**: T031 (indexer service)
  - **Commit**: `feat(mcp): implement index_repository tool`

- [ ] **T037** Implement task management MCP tools
  - **File**: `src/mcp/tools/tasks.py`
  - **Content**: Tool handlers for get_task, list_tasks, create_task, update_task
  - **Dependencies**: T033 (task service)
  - **Commit**: `feat(mcp): implement task management tools`

- [ ] **T038** Main application entry point
  - **File**: `src/main.py`
  - **Content**: FastAPI app, MCP server initialization, config loading, health check endpoint
  - **Dependencies**: T034, T035, T036, T037 (MCP server and tools)
  - **Commit**: `feat(app): add main application entry point`

---

## Phase 3.4: Integration & Polish

### Integration

- [ ] **T039** Database connection management and pooling
  - **File**: `src/database.py`
  - **Content**: AsyncPG connection pool (20 connections), session dependency injection for FastAPI
  - **Dependencies**: T019 (database setup)
  - **Commit**: `feat(database): add connection pooling and session management`

- [ ] **T040** Error handling and logging middleware
  - **File**: `src/mcp/middleware.py`
  - **Content**: Catch exceptions, format MCP error responses, log to file (no stdout/stderr)
  - **Dependencies**: T004 (logging setup)
  - **Commit**: `feat(mcp): add error handling middleware`

- [ ] **T041** Scheduled cleanup job for 90-day retention
  - **File**: `scripts/cleanup_deleted_files.py`
  - **Content**: Find files deleted >90 days ago, cascade delete chunks/embeddings
  - **Commit**: `feat(scripts): add 90-day retention cleanup job`

### Unit Tests & Performance

- [ ] **T042** [P] Unit tests for file scanner ignore patterns
  - **File**: `tests/unit/test_scanner.py`
  - **Content**: Test .gitignore/.mcpignore parsing, pattern matching, change detection
  - **Dependencies**: T028 (scanner implementation)
  - **Commit**: `test(unit): add scanner unit tests`

- [ ] **T043** [P] Unit tests for Tree-sitter chunker
  - **File**: `tests/unit/test_chunker.py`
  - **Content**: Test AST parsing, chunk boundary detection, fallback for unsupported languages
  - **Dependencies**: T029 (chunker implementation)
  - **Commit**: `test(unit): add chunker unit tests`

- [ ] **T044** [P] Unit tests for Ollama embedder
  - **File**: `tests/unit/test_embedder.py`
  - **Content**: Test batch generation, retry logic, timeout handling, error cases
  - **Dependencies**: T030 (embedder implementation)
  - **Commit**: `test(unit): add embedder unit tests`

- [ ] **T045** [P] Unit tests for task status transitions
  - **File**: `tests/unit/test_task_transitions.py`
  - **Content**: Test status changes, history recording, validation rules
  - **Dependencies**: T033 (task service implementation)
  - **Commit**: `test(unit): add task transition unit tests`

- [ ] **T046** Performance benchmark script (60s indexing, 500ms search)
  - **File**: `scripts/benchmark.py`
  - **Content**: Generate 10K file test repo, measure indexing time, run 100 searches, report p50/p95/p99 latencies
  - **Commit**: `test(perf): add performance benchmark script`

### Documentation & Final Polish

- [ ] **T047** [P] README with setup instructions
  - **File**: `README.md`
  - **Content**: Prerequisites (PostgreSQL, Ollama), installation, configuration, running MCP server
  - **Commit**: `docs: add README with setup instructions`

- [ ] **T048** [P] API documentation from contracts
  - **File**: `docs/api.md`
  - **Content**: MCP tool schemas, examples, performance requirements
  - **Commit**: `docs: add API documentation`

- [ ] **T049** [P] Troubleshooting guide
  - **File**: `docs/troubleshooting.md`
  - **Content**: Common errors, configuration issues, performance tuning
  - **Commit**: `docs: add troubleshooting guide`

- [ ] **T050** Run all integration tests from quickstart.md
  - **Action**: Execute quickstart.md scenarios, verify all pass
  - **Dependencies**: All implementation tasks complete
  - **Commit**: `test: validate quickstart integration scenarios`

- [ ] **T051** Run mypy --strict type checking
  - **Action**: Ensure all files pass mypy --strict, fix type errors
  - **Dependencies**: All implementation tasks complete
  - **Commit**: `refactor: fix mypy --strict type errors`

- [ ] **T052** Final code review and refactoring
  - **Action**: Remove duplication, improve error messages, optimize hot paths
  - **Dependencies**: All tasks complete
  - **Commit**: `refactor: final code cleanup and optimization`

---

## Dependencies

### Critical Paths
1. **Setup** (T001-T005) → All other tasks
2. **Contract Tests** (T006-T011) → Must fail before implementation
3. **Integration Tests** (T012-T018) → Must fail before implementation
4. **Models** (T019-T027) → Services (T028-T033)
5. **Services** (T028-T033) → MCP Tools (T034-T038)
6. **MCP Tools** (T034-T038) → Integration (T039-T041)
7. **Implementation Complete** → Unit Tests (T042-T045) & Polish (T046-T052)

### Blocking Relationships
- T026 (migration) blocks T027 (init script)
- T028, T029, T030 (scanner, chunker, embedder) block T031 (indexer)
- T031 (indexer) blocks T036 (index_repository tool)
- T032 (searcher) blocks T035 (search_code tool)
- T033 (task service) blocks T037 (task tools)
- T034-T037 (MCP tools) block T038 (main app)
- T019 (database setup) blocks T039 (connection pooling)
- T004 (logging) blocks T040 (middleware)

---

## Parallel Execution Examples

### Phase 3.1 - Setup (launch in parallel)
```bash
# T003-T005 can run together (different files):
Task: "Configure linting and type checking in .pre-commit-config.yaml, mypy.ini"
Task: "Setup structured logging in src/mcp/logging.py"
Task: "Create Pydantic settings in src/config/settings.py"
```

### Phase 3.2 - Contract Tests (launch all in parallel)
```bash
# T006-T011 can run together (independent test files):
Task: "Contract test for search_code MCP tool in tests/contract/test_search_code_contract.py"
Task: "Contract test for index_repository MCP tool in tests/contract/test_index_repository_contract.py"
Task: "Contract test for get_task MCP tool in tests/contract/test_get_task_contract.py"
Task: "Contract test for list_tasks MCP tool in tests/contract/test_list_tasks_contract.py"
Task: "Contract test for create_task MCP tool in tests/contract/test_create_task_contract.py"
Task: "Contract test for update_task MCP tool in tests/contract/test_update_task_contract.py"
```

### Phase 3.2 - Integration Tests (launch all in parallel)
```bash
# T012-T018 can run together (independent test files):
Task: "Integration test: Repository indexing in tests/integration/test_repository_indexing.py"
Task: "Integration test: Incremental updates in tests/integration/test_incremental_updates.py"
Task: "Integration test: Semantic search in tests/integration/test_semantic_search.py"
Task: "Integration test: Task lifecycle in tests/integration/test_task_lifecycle.py"
Task: "Integration test: AI assistant in tests/integration/test_ai_assistant_integration.py"
Task: "Integration test: File deletion in tests/integration/test_file_deletion_retention.py"
Task: "Integration test: Performance in tests/integration/test_performance_validation.py"
```

### Phase 3.3 - Models (launch in parallel)
```bash
# T020-T025 can run together (independent model files):
Task: "Repository model in src/models/repository.py"
Task: "CodeFile model in src/models/code_file.py"
Task: "CodeChunk model in src/models/code_chunk.py"
Task: "Task model in src/models/task.py"
Task: "Task relationship models in src/models/task_relations.py"
Task: "Tracking models in src/models/tracking.py"
```

### Phase 3.3 - Services (launch in parallel where independent)
```bash
# T028-T030, T032-T033 can run together (independent services):
Task: "File scanner in src/services/scanner.py"
Task: "Tree-sitter chunker in src/services/chunker.py"
Task: "Ollama embedder in src/services/embedder.py"
Task: "Semantic searcher in src/services/searcher.py"
Task: "Task CRUD service in src/services/tasks.py"

# T031 must wait for T028-T030 (depends on scanner, chunker, embedder)
```

### Phase 3.4 - Unit Tests (launch in parallel)
```bash
# T042-T045 can run together (independent test files):
Task: "Unit tests for scanner in tests/unit/test_scanner.py"
Task: "Unit tests for chunker in tests/unit/test_chunker.py"
Task: "Unit tests for embedder in tests/unit/test_embedder.py"
Task: "Unit tests for task transitions in tests/unit/test_task_transitions.py"
```

### Phase 3.4 - Documentation (launch in parallel)
```bash
# T047-T049 can run together (independent doc files):
Task: "README in README.md"
Task: "API docs in docs/api.md"
Task: "Troubleshooting guide in docs/troubleshooting.md"
```

---

## Validation Checklist
*GATE: Checked before marking tasks complete*

- [X] All 6 MCP tools have contract tests (T006-T011)
- [X] All 7 integration scenarios have tests (T012-T018)
- [X] All 11 entities have models (T020-T025)
- [X] All contract tests come before implementation (T006-T011 before T035-T037)
- [X] All integration tests come before implementation (T012-T018 before T031-T033)
- [X] Parallel tasks [P] are truly independent (different files, no dependencies)
- [X] Each task specifies exact file path
- [X] No [P] task modifies same file as another [P] task
- [X] TDD enforced: Tests (T006-T018) before Core (T019-T038)
- [X] Dependencies documented and enforced

---

## Notes

### TDD Enforcement
- **CRITICAL**: T006-T018 (all tests) MUST be written first and MUST FAIL
- Do NOT implement T019-T038 until all tests are failing
- Tests define the contract; implementation makes tests pass

### Parallel Execution
- [P] tasks touch different files with no shared dependencies
- Can launch simultaneously for faster implementation
- Examples show exact Task agent commands for parallel execution

### Git Micro-Commits
- Commit after each task completion
- Use Conventional Commits format: `type(scope): description`
- Each commit must pass tests (working state)
- Branch: `001-build-a-production`

### Performance Targets
- Indexing: 10,000 files in <60 seconds (T046 validates)
- Search: p95 latency <500ms (T046 validates)
- Optimize in T031 (indexer) and T032 (searcher)

### Constitutional Compliance
- MCP protocol via SSE only (no stdout/stderr) - T034, T040
- File logging to `/tmp/codebase-mcp.log` - T004, T040
- Type safety with mypy --strict - T051
- Pydantic validation throughout - T005, T020-T025
- Async operations - T019, T031, T032, T033

---

## Summary

**Total Tasks**: 52
**Parallel Opportunities**: 31 tasks marked [P]
**Sequential Tasks**: 21 (due to dependencies)
**Estimated Completion**: 30-35 hours with parallel execution

**Key Milestones**:
1. Setup complete (T001-T005) → 2 hours
2. All tests failing (T006-T018) → 6 hours
3. Core models & services (T019-T033) → 12 hours
4. MCP tools & integration (T034-T041) → 8 hours
5. Unit tests & polish (T042-T052) → 7 hours

**Next Step**: Execute `/implement` to orchestrate subagent implementation with parallel task execution where marked [P].
