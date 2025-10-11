# Constitution Initialization Prompt for workflow-mcp

## Overview

This prompt should be used AFTER Phase 0A completes to initialize the workflow-mcp constitution using the `/constitution` command.

---

## When to Use This

**Timing:** After Phase 0A foundation is complete (repository created, structure in place)

**Location:** In the workflow-mcp repository

**Command:** `/constitution` with the content below as arguments

---

## Copy-Paste This Into `/constitution` Command

```
Create the workflow-mcp constitution with 12 principles. This is an AI project management MCP with multi-project workspace support and a generic entity system.

**Project Identity:**
- Name: workflow-mcp
- Purpose: AI project management system with multi-project workspace support and generic entity system
- Scope: Project management, work item tracking, task management, generic entities (NO code intelligence, NO cloud sync, NO hardcoded domain tables)

**Ratification Date:** 2025-10-11 (today)
**Version:** 1.0.0 (initial constitution)

**Principles (12 total):**

I. Simplicity Over Features
- Focus: AI-assisted project management with multi-project workspaces only
- Forbidden: Code intelligence (delegate to codebase-mcp), cloud sync, workflow automation, hardcoded domain tables, cross-project queries
- Allowed: Multi-project management, hierarchical work items, task management with git, generic entity system, deployment history

II. Local-First Architecture
- All data local (PostgreSQL registry + per-project databases)
- No cloud dependencies, API keys, or remote services
- Offline-capable with full functionality
- Target: <50ms project switching on consumer hardware

III. MCP Protocol Compliance
- FastMCP framework with MCP Python SDK
- SSE transport only (no stdio pollution)
- Structured logging to file/syslog (NEVER stdout/stderr)
- Integration tests verify Claude Desktop/CLI can invoke all tools

IV. Performance Guarantees
- Project switching: <50ms p95
- Work item operations: <200ms p95
- Entity queries: <100ms p95
- Task listing: <150ms p95
- Deployment recording: <200ms p95
- Scale: 100+ projects, 5-level hierarchies, 10k+ entities per project
- CI fails on >20% p95 regression

V. Production Quality
- Error handling: Try/except in all tools with MCP error responses
- Type safety: mypy --strict with no ignores
- Validation: Pydantic models for all inputs/outputs
- Logging: Structured JSON with correlation IDs
- Health checks: Database connectivity before operations
- Optimistic locking: Version-based concurrency control
- Testing: >90% coverage, all MCP tools invocable, isolation tests, performance validation

VI. Specification-First Development
- Process: /specify → /clarify → /plan → /tasks → /implement
- Spec quality: No implementation details, testable success criteria, edge cases documented
- Deviation: NO code without approved spec.md

VII. Test-Driven Development
- Workflow: Protocol tests → Unit tests → Integration tests → Isolation tests → Implementation
- Requirements: MCP tool contracts, database isolation tests, Pydantic validation tests, error path tests
- Coverage: >90% line, 100% for critical paths (isolation, validation)
- CI: Full suite on every commit (<5 min)

VIII. Pydantic-Based Type Safety
- All structures use Pydantic: Tool I/O, entity schemas, database models, configuration
- Validation: Input at API boundary, entity data against JSON Schema, enums, foreign keys
- Type checking: mypy --strict with no type: ignore
- Error handling: ValidationError → MCP error with field details

IX. Orchestrated Subagent Execution
- /implement spawns subagents per parallelizable task
- Tasks marked [P] run concurrently (different files/modules)
- Safety: Database ops serialized, entity registration blocks creation, work item mods serialized
- Failure: Non-parallel halts workflow, parallel logged and retried

X. Git Micro-Commit Strategy
- Frequency: Commit after EACH task in tasks.md
- Format: Conventional Commits (feat/fix/docs/test/refactor/perf/chore)
- Working state: All tests pass at every commit
- Branches: ###-feature-name from main, squash merge after PR

XI. FastMCP and Python SDK Foundation
- Framework: FastMCP for server + MCP Python SDK for protocol
- Registration: @mcp.tool() decorators exclusively
- Forbidden: Manual JSON-RPC, custom SSE, stdout protocol, bypassing validation
- Benefits: Protocol compliance, auto schema generation, built-in error handling

XII. Generic Entity Adaptability (NEW - workflow-mcp specific)
- Architecture: Single entities table with JSONB storage per project
- Runtime schemas: JSON Schema registration via register_entity_type tool
- Validation: Pydantic validates entity data against registered schema
- Queries: JSONB operators (@>, ->, ->>) with GIN indexing
- Examples: vendors (commission work), game_mechanics (game dev), papers (research)
- Constraint: NO domain-specific tables. Adding vendor table requires amendment.
- Test: Commission + game dev projects use same codebase

**Technical Stack (Non-Negotiable):**
- Python 3.11+, PostgreSQL 14+, FastMCP, MCP Python SDK, AsyncPG, Pydantic, JSON Schema
- Dev tools: mypy (--strict), ruff, pytest, pytest-asyncio, pytest-postgresql
- Infrastructure: Multiple PostgreSQL databases, AsyncPG pooling, structured logging (JSON to file)

**Success Criteria:**
- Functional: Multi-project isolation, generic entities, 5-level hierarchy <200ms, git-tracked tasks, deployment audit
- Performance: <50ms switching, <200ms work items, <100ms entities, 100+ projects
- Quality: mypy --strict passes, >90% coverage, protocol compliant, structured errors
- Operational: Zero downtime on project DB failures, graceful degradation, <10MB per pool, health checks

**Allowed Complexity:**
- Multi-database connection pooling, recursive CTEs, JSONB GIN indexing, materialized paths, optimistic locking

**Forbidden Complexity:**
- Custom ORMs/query planners, event sourcing/CQRS, distributed transactions, custom serialization, workflow state machines

**Amendment Process:**
1. Proposal with rationale
2. 2-week review period
3. 2/3 majority vote
4. Update cascade (CLAUDE.md, templates)
5. 4-week grace period for code alignment

**Enforcement:**
- CI checks: Type safety, coverage, performance
- PR reviews: Constitutional compliance checklist
- /analyze: Flags violations as CRITICAL
- Post-audit: Spot checks on merged features
```

---

## Expected Outcome

After running `/constitution` with the above content, you should have:

1. **File created:** `.specify/memory/constitution.md` in workflow-mcp repository
2. **Version:** 1.0.0 (initial constitution)
3. **Sync Impact Report:** HTML comment at top documenting creation
4. **Template updates:** Any templates updated to reference the constitution
5. **Commit message:** `docs: initialize constitution v1.0.0 (12 principles for workflow-mcp)`

---

## Verification Steps

After constitution creation:

```bash
# Verify file exists
ls -la .specify/memory/constitution.md

# Check version and principles
grep -E "^## |^### Principle" .specify/memory/constitution.md

# Verify no placeholder tokens remain
grep -E '\[([A-Z_]+)\]' .specify/memory/constitution.md
# Should return nothing or only intentional placeholders

# Commit the constitution
git add .specify/memory/constitution.md
git commit -m "docs: initialize constitution v1.0.0 (12 principles for workflow-mcp)"
```

---

## Notes

- This constitution is based on the planning docs in `codebase-mcp/docs/mcp-split-plan/02-workflow-mcp/constitution.md`
- Principle XII (Generic Entity Adaptability) is unique to workflow-mcp
- All other principles are shared with codebase-mcp (with workflow-specific constraints)
- The constitution should be created AFTER Phase 0A completes (repository structure in place)
- The `/constitution` command will handle template creation, placeholder replacement, and sync impact reporting

---

**Status:** Ready to use after Phase 0A completion
**Location:** workflow-mcp repository (not codebase-mcp)
**Command:** `/constitution [paste content above]`
