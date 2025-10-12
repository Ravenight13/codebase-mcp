# Codebase MCP Planning Summary

**Date**: 2025-10-11
**Status**: Initial planning complete
**Approach**: Option B Sequential (workflow-mcp exists first)

---

## Planning Artifacts Created

### 1. README.md (7.0 KB)
**Purpose**: Overview of codebase-mcp's scope and architecture

**Key Content**:
- What codebase-mcp does (semantic code search ONLY)
- What it explicitly does NOT do (work items, tasks, vendors, deployments)
- Relationship to workflow-mcp (integration for project context)
- Tool surface: 2 tools (down from 16)
- Success criteria for refactor

**Key Decisions**:
- Pure semantic search MCP (no feature creep)
- Multi-project support via one database per project
- Optional workflow-mcp integration (fallback to explicit project_id)
- Performance guarantees: <500ms search, <60s indexing for 10k files

---

### 2. constitution.md (14 KB)
**Purpose**: Non-negotiable principles for codebase-mcp

**11 Core Principles**:
1. **Simplicity Over Features** - Search ONLY, reject scope creep
2. **Local-First Architecture** - No cloud dependencies, works offline
3. **Protocol Compliance** - MCP via SSE, no stdout pollution
4. **Performance Guarantees** - <500ms search, <60s indexing
5. **Production Quality** - Error handling, type safety, logging
6. **Specification-First Development** - /specify → /clarify → /plan → /tasks → /implement
7. **Test-Driven Development** - Tests before code, TDD cycle
8. **Pydantic-Based Type Safety** - All models use Pydantic, mypy --strict
9. **Orchestrated Subagent Execution** - Parallel implementation where safe
10. **Git Micro-Commit Strategy** - One commit per task, working state
11. **FastMCP and Python SDK Foundation** - Use FastMCP + MCP Python SDK

**Technical Stack** (Non-Negotiable):
- Python 3.11+, PostgreSQL 14+ with pgvector
- Ollama with nomic-embed-text (768 dimensions)
- FastMCP framework, AsyncPG driver
- Tree-sitter for code chunking
- Pydantic 2.x, mypy --strict

**Enforcement**:
- `/analyze` flags constitutional violations as CRITICAL
- Design reviews reject features outside search scope
- CI/CD blocks merges if mypy/tests fail

---

### 3. user-stories.md (16 KB)
**Purpose**: User stories for semantic code search

**8 User Stories**:
1. **Search Code Across Active Project** - Natural language search with <500ms response
2. **Index New Repository for Project** - Index 10k files in <60s
3. **Switch Projects and Search New Context** - No cross-contamination between projects
4. **Filter Search by File Type and Directory** - Narrow results to relevant code areas
5. **Fast Search Performance on Large Codebases** - Maintain <500ms even with 250k chunks
6. **Work Offline with Local Embeddings** - No internet required after model download
7. **Accurate Relevance Ranking** - Results sorted by cosine similarity
8. **Clear Error Messages and Debugging** - Actionable error messages with suggested fixes

**Test Scenarios**: Each story includes concrete test scenarios with expected inputs/outputs

**Non-Functional Requirements**:
- Performance: <60s indexing, <500ms search, 20 concurrent searches
- Reliability: Graceful degradation, no silent failures
- Scalability: Support up to 100k files (500k chunks), 10+ projects
- Security: All data local (no external transmission)

---

### 4. specify-prompt.txt (7.7 KB)
**Purpose**: Ready-to-use prompt for `/specify` command

**Key Sections**:
- **Problem Statement**: Monolithic codebase-mcp violates SRP, needs separation
- **What We Need**: Pure search MCP with multi-project support
- **Success Criteria**: Functional, performance, quality, architecture requirements
- **Constraints**: Technical stack (non-negotiable), development approach
- **Out of Scope**: Work items, tasks, vendors, deployments (moved to workflow-mcp)
- **Current State**: 16 tools → 2 tools, single DB → per-project DBs
- **Business Value**: Faster searches, multi-project support, clearer separation
- **Acceptance Criteria**: Refactoring complete, tests pass, performance meets targets
- **Migration Notes**: How users migrate from v1.x to v2.0.0
- **Questions to Address**: Database discovery, workflow-mcp fallback, naming conventions

**Usage**: Copy-paste into `/specify` command to generate spec.md

---

### 5. tech-stack.md (16 KB)
**Purpose**: Detailed technical stack documentation

**Core Technologies**:
- **Python 3.11+**: Async/await, type hints, match statements
- **PostgreSQL 14+ with pgvector**: Vector similarity search with HNSW indexes
- **Ollama with nomic-embed-text**: Local embeddings (768 dimensions)
- **FastMCP Framework**: Ergonomic MCP server implementation
- **AsyncPG**: Fastest Python PostgreSQL driver (async native)
- **Tree-sitter**: AST-aware code chunking for 50+ languages
- **Pydantic 2.x**: Runtime validation, type safety
- **mypy**: Static type checking (--strict mode)
- **pytest + pytest-asyncio**: Testing framework

**Supporting Libraries**:
- aiohttp (Ollama HTTP client)
- numpy (optional, for embeddings)
- black (code formatter)
- ruff (linter)
- pre-commit (git hooks)

**Architecture Diagram**: Visualizes FastMCP → AsyncPG/Ollama → PostgreSQL/workflow-mcp

**Why This Stack**:
- Local-first (no cloud)
- Performance (async I/O, HNSW indexes)
- Type safety (Pydantic + mypy)
- Production quality (PostgreSQL ACID, error handling)
- Developer experience (FastMCP, tree-sitter, Docker optional)

**Non-Negotiable**: Constitutional Principle XI enforces this stack

---

### 6. refactoring-plan.md (26 KB)
**Purpose**: File-by-file refactoring plan

**Current State Analysis**:
- 16 tools (2 search + 14 non-search)
- Multiple database tables (repositories, code_chunks + 7 non-search tables)

**10 Refactoring Phases**:
1. **Branch and Baseline** - Create feature branch, document current state
2. **Database Schema Refactoring** - Remove non-search tables, add project_id
3. **Remove Non-Search Tool Implementations** - Delete 5 tool files
4. **Remove Non-Search Database Operations** - Delete CRUD functions
5. **Update MCP Server Tool Registration** - Register only 2 tools
6. **Remove Non-Search Tests** - Delete 5 test files
7. **Add Multi-Project Support** - Implement project_id parameter, workflow-mcp integration
8. **Update Database Connection Management** - Per-project connection pools
9. **Remove Non-Search Documentation** - Update README, API docs, architecture
10. **Create Migration Guide** - Step-by-step migration for users

**Code Reduction**:
- Before: ~4,500 lines
- After: ~1,800 lines
- Reduction: 60%

**Tool Reduction**:
- Before: 16 tools
- After: 2 tools
- Reduction: 87.5%

**Risk Mitigation**:
- Breaking changes: Semantic versioning (v2.0.0), migration guide
- Data loss: Backup instructions, tested migration script
- Integration failures: Fallback to explicit project_id
- Performance regression: Benchmarks before/after

**Timeline Estimate**: 17 hours (2-3 days with testing)

---

### 7. implementation-phases.md (39 KB)
**Purpose**: Phase-by-phase implementation breakdown with git strategy

**12 Implementation Phases** (includes Phase 0 prerequisites):
0. **Prerequisites and Planning** - Verify workflow-mcp, validate artifacts
1. **Create Feature Branch and Baseline** - Branch + document current state
2. **Database Schema Refactoring** - Migration script, schema updates
3. **Remove Non-Search Tool Implementations** - Delete tool files
4. **Remove Non-Search Database Operations** - Delete CRUD functions
5. **Update MCP Server Tool Registration** - Register only search tools
6. **Remove Non-Search Tests** - Delete test files
7. **Add Multi-Project Support to Search Tools** - project_id parameter, workflow-mcp integration
8. **Update Database Connection Management** - Per-project pools, auto-create databases
9. **Update Documentation** - README, API docs, CHANGELOG
10. **Create Migration Guide** - User migration instructions
11. **Performance Testing and Optimization** - Validate <500ms search, <60s indexing
12. **Final Validation and Release Preparation** - Full test suite, mypy, mcp-inspector, v2.0.0 tag

**Post-Implementation**: PR creation, code review, merge to main

**Git Strategy**:
- Branch: `002-refactor-pure-search`
- Commit format: Conventional Commits (`type(scope): description`)
- Micro-commits: One per phase (working state)
- Tag: `v2.0.0` after final validation

**Testing Strategy**:
- Unit tests for individual functions
- Integration tests for database/Ollama
- Protocol tests via mcp-inspector
- Performance benchmarks (search latency, indexing throughput)
- Multi-project isolation tests (no cross-contamination)

**Timeline**: 23-25 hours (3-4 days with testing and validation)

**Success Criteria**:
- Functional: 2 tools, multi-project works, workflow-mcp integration
- Non-Functional: <500ms search, <60s indexing, 100% MCP compliance
- Process: All phases complete, micro-commits, documentation updated
- Constitutional: All 11 principles satisfied

---

## Key Planning Decisions

### 1. Tool Surface
**Decision**: Reduce from 16 tools to 2 tools
- **Keep**: `index_repository`, `search_code`
- **Remove**: All work item, task, vendor, deployment, configuration tools
- **Rationale**: Single Responsibility Principle, simplicity over features (Principle I)

### 2. Multi-Project Architecture
**Decision**: One database per project
- **Database Naming**: `codebase_{project_id}`
- **Connection Pooling**: One pool per project (5-20 connections)
- **Auto-Creation**: Databases created automatically on first access
- **Rationale**: Isolation guarantee, no cross-contamination, scales to 10+ projects

### 3. workflow-mcp Integration
**Decision**: Optional integration with graceful fallback
- **Active Project Detection**: Query workflow-mcp for `get_active_project_id()`
- **Fallback**: Require explicit `project_id` if workflow-mcp unavailable
- **Timeout**: 2 second timeout for workflow-mcp queries
- **Rationale**: Works standalone or integrated, no hard dependency

### 4. Performance Targets
**Decision**: Constitutional performance guarantees
- **Search Latency**: <500ms (p95), <300ms (p50)
- **Indexing Throughput**: <60s for 10,000 files
- **Concurrent Searches**: 20 simultaneous queries without degradation
- **Rationale**: Interactive coding workflows require sub-second search

### 5. Database Migration Strategy
**Decision**: Destructive migration with backup requirement
- **Approach**: Drop non-search tables after backup
- **Script**: `migrations/002_remove_non_search_tables.sql`
- **Testing**: Test on test database before production
- **Rationale**: Clean break for v2.0.0, migration guide provides safety net

### 6. Breaking Change Communication
**Decision**: Semantic versioning + migration guide
- **Version**: v2.0.0 (major version bump)
- **Migration Guide**: Step-by-step instructions in `docs/migration-guide.md`
- **Tool Mapping**: Clear old → new tool mapping
- **Rationale**: Users expect breaking changes in major versions, guide reduces friction

### 7. Testing Strategy
**Decision**: Multi-layered testing approach
- **Unit Tests**: Individual functions
- **Integration Tests**: Database + Ollama interactions
- **Protocol Tests**: MCP compliance via mcp-inspector
- **Performance Tests**: Latency benchmarks, throughput tests
- **Multi-Project Tests**: Isolation validation
- **Rationale**: Production quality (Principle V), TDD (Principle VII)

### 8. Git Workflow
**Decision**: Micro-commits with working state guarantee
- **Branch**: `002-refactor-pure-search`
- **Commit Frequency**: After each phase (12 commits)
- **Commit Format**: Conventional Commits (feat, fix, refactor, test, docs, chore)
- **Working State**: All tests pass at every commit
- **Rationale**: Git Micro-Commit Strategy (Principle X), bisectability

### 9. Documentation Updates
**Decision**: Comprehensive documentation overhaul
- **README.md**: Search-only scope, multi-project support
- **API docs**: Only 2 tools documented
- **Architecture**: Simplified diagrams (2 tables)
- **CHANGELOG**: Breaking changes clearly documented
- **Migration Guide**: Separate document with step-by-step instructions
- **Rationale**: Production quality (Principle V), user experience

### 10. Constitution Enforcement
**Decision**: Constitution as non-negotiable contract
- **Validation**: `/analyze` flags violations as CRITICAL
- **Amendment Process**: Requires version bump, rationale, approval
- **Scope**: All 11 principles enforced throughout development
- **Rationale**: Specification-First Development (Principle VI), consistency

---

## Next Steps

### Immediate (Before Implementation)
1. ✅ Planning artifacts reviewed and approved
2. ⏳ workflow-mcp deployment verified (prerequisite)
3. ⏳ Feature branch created: `002-refactor-pure-search`

### Short-Term (During Implementation)
1. Follow implementation-phases.md sequentially (Phase 0-12)
2. Commit after each phase (micro-commits)
3. Run tests continuously (TDD approach)
4. Update documentation as code changes

### Medium-Term (After Implementation)
1. Create PR with comprehensive description
2. Code review (constitutional compliance check)
3. Merge to main after approval
4. Tag v2.0.0 release
5. Deploy documentation (migration guide)

### Long-Term (Post-Release)
1. Monitor production usage (error rates, latency)
2. Collect user feedback on migration experience
3. Plan v2.1.0 enhancements (incremental indexing, query suggestions)
4. Deeper integration with workflow-mcp

---

## Planning Metrics

| Metric | Value |
|--------|-------|
| Planning Documents Created | 7 files |
| Total Planning Documentation | 126 KB |
| Time Spent Planning | ~4 hours |
| Estimated Implementation Time | 23-25 hours |
| Code Reduction Expected | 60% (4,500 → 1,800 lines) |
| Tool Reduction Expected | 87.5% (16 → 2 tools) |
| Constitutional Principles Defined | 11 principles |
| User Stories Documented | 8 stories |
| Implementation Phases Defined | 12 phases |
| Git Commits Expected | ~15 commits |

---

## Files in This Directory

```
01-codebase-mcp/
├── README.md                    (7.0 KB)  - Overview and scope
├── constitution.md              (14 KB)   - 11 non-negotiable principles
├── user-stories.md              (16 KB)   - 8 user stories with test scenarios
├── specify-prompt.txt           (7.7 KB)  - Ready for /specify command
├── tech-stack.md                (16 KB)   - Technical stack details
├── refactoring-plan.md          (26 KB)   - File-by-file refactor plan
├── implementation-phases.md     (39 KB)   - Phase-by-phase breakdown
└── SUMMARY.md                   (this file) - Planning summary
```

**Total Size**: ~126 KB of planning documentation

---

## Constitutional Compliance Check

| Principle | Addressed in Planning | Status |
|-----------|----------------------|--------|
| I: Simplicity Over Features | constitution.md, refactoring-plan.md | ✅ Enforced |
| II: Local-First Architecture | constitution.md, tech-stack.md | ✅ Ollama + PostgreSQL |
| III: Protocol Compliance | constitution.md, implementation-phases.md | ✅ FastMCP + mcp-inspector |
| IV: Performance Guarantees | constitution.md, user-stories.md | ✅ <500ms search, <60s indexing |
| V: Production Quality | constitution.md, implementation-phases.md | ✅ mypy, tests, coverage >80% |
| VI: Specification-First | specify-prompt.txt | ✅ Ready for /specify |
| VII: Test-Driven Development | implementation-phases.md | ✅ TDD approach in phases |
| VIII: Pydantic Type Safety | tech-stack.md, constitution.md | ✅ Pydantic 2.x + mypy --strict |
| IX: Orchestrated Subagents | constitution.md | ⚠️ N/A for refactor (single agent) |
| X: Git Micro-Commits | implementation-phases.md, refactoring-plan.md | ✅ 1 commit per phase |
| XI: FastMCP Foundation | tech-stack.md, constitution.md | ✅ FastMCP + MCP Python SDK |

**Overall Compliance**: 10/11 principles satisfied (Principle IX not applicable for refactor)

---

## Planning Quality Assessment

### Strengths
- ✅ **Comprehensive**: All required planning documents created
- ✅ **Detailed**: File-by-file refactoring plan with code examples
- ✅ **Actionable**: Phase-by-phase breakdown with git strategy
- ✅ **Testable**: User stories with concrete test scenarios
- ✅ **Constitutional**: 11 principles defined and enforced
- ✅ **Time-Estimated**: Realistic timeline (23-25 hours)
- ✅ **Risk-Aware**: Risk mitigation strategies documented
- ✅ **User-Focused**: Migration guide planned for existing users

### Areas for Validation During Implementation
- ⚠️ workflow-mcp API contract (ensure compatible)
- ⚠️ Database naming conventions (validate with workflow-mcp)
- ⚠️ Performance targets (benchmark on real hardware)
- ⚠️ Migration script (test on real v1.x database)

### Recommended Pre-Implementation Actions
1. Validate workflow-mcp is deployed and responding
2. Review planning documents with stakeholders
3. Set up test environment (PostgreSQL + Ollama)
4. Prepare test data (10k file repository for benchmarking)

---

## Conclusion

All initial planning documentation for the codebase-mcp refactor has been completed. The planning is comprehensive, detailed, and ready for implementation via the `/specify` → `/plan` → `/tasks` → `/implement` workflow.

**Ready for**: `/specify` command using `specify-prompt.txt`

**Prerequisites**: workflow-mcp deployment (must be available before starting Phase 0)

**Estimated Timeline**: 3-4 days (23-25 hours) from planning to release

**Confidence Level**: High (comprehensive planning, clear scope, constitutional principles)
