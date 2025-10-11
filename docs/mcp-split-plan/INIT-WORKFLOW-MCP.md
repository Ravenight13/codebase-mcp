# Workflow-MCP Initialization Prompt

## Purpose

This document provides a complete initialization prompt for the **workflow-mcp** repository. Use this prompt to create the repository structure and foundational CLAUDE.md file BEFORE executing Phase 0A (infrastructure setup).

The workflow-mcp server provides AI-assisted project management with multi-project workspace support and a generic entity system. It complements codebase-mcp (code intelligence) by handling work items, tasks, deployments, and domain-specific entities.

---

## Copy-Paste Into New Chat

```
I need to initialize a new repository called workflow-mcp. This is an MCP server for AI-assisted project management with multi-project workspace support and a generic entity system.

**Project Overview:**
- Name: workflow-mcp
- Purpose: AI project management MCP server with multi-project workspaces
- Architecture: Database-per-project isolation, JSONB generic entities, FastMCP framework
- Relationship: Complements codebase-mcp (code intelligence) by providing project management

**Repository Location:**
/Users/cliffclarke/Claude_Code/workflow-mcp

**Task:**
1. Create the repository directory: /Users/cliffclarke/Claude_Code/workflow-mcp
2. Initialize git repository
3. Create comprehensive CLAUDE.md file in the repository root
4. Create initial commit with CLAUDE.md
5. Confirm the repository is ready for Phase 0A execution

**CLAUDE.md Requirements:**
The CLAUDE.md file must include:
- Repository overview (workflow-mcp purpose and scope)
- Workflow architecture (Specify framework: /specify → /clarify → /plan → /tasks → /analyze → /implement)
- Key directories (.specify/, .claude/commands/, specs/)
- Constitutional principles (12 principles summary)
- Important workflow rules (specification, planning, task generation, implementation phases)
- Git workflow (branch-per-feature, micro-commits, Conventional Commits)
- Common development tasks
- Template placeholders
- File path conventions
- Error handling patterns
- Agent context files

**Constitutional Principles (12 Total):**
1. Simplicity Over Features (project management only, NO code intelligence)
2. Local-First Architecture (PostgreSQL, no cloud dependencies)
3. MCP Protocol Compliance (FastMCP + SSE)
4. Performance Guarantees (<50ms project switching, <200ms work items, <100ms entities)
5. Production Quality (mypy --strict, >90% coverage, comprehensive error handling)
6. Specification-First Development (requirements before implementation)
7. Test-Driven Development (tests before code, protocol compliance validation)
8. Pydantic-Based Type Safety (all models use Pydantic, mypy --strict)
9. Orchestrated Subagent Execution (parallel task execution where safe)
10. Git Micro-Commit Strategy (atomic commits, branch-per-feature, Conventional Commits)
11. FastMCP and Python SDK Foundation (use FastMCP framework exclusively)
12. Generic Entity Adaptability (JSONB storage, runtime schema registration, NO domain tables)

**Technical Stack (Non-Negotiable):**
- Python 3.11+
- PostgreSQL 14+ (multiple databases: registry + per-project)
- FastMCP framework with MCP Python SDK
- AsyncPG (connection pooling)
- Pydantic (data validation)
- JSON Schema (entity type validation)

**Key Architectural Features:**
- Multi-project isolation (one database per project)
- Generic entity system (JSONB storage with runtime JSON Schema validation)
- Hierarchical work items (project → session → task → research, up to 5 levels)
- Git integration (branch/commit tracking per task)
- Deployment history recording
- LRU connection pool management (max 50 active pools)

**Reference Documentation:**
Complete planning documentation is available at:
/Users/cliffclarke/Claude_Code/codebase-mcp/docs/mcp-split-plan/02-workflow-mcp/

Key files:
- constitution.md - Full constitutional principles
- FINAL-IMPLEMENTATION-PLAN.md - Complete implementation plan
- HANDOFF-PHASE-0A-WORKFLOW-MCP.md - Phase 0A handoff (execute AFTER initialization)

**Next Steps After Initialization:**
After this initialization is complete and CLAUDE.md is committed, I will proceed to Phase 0A using the handoff document at:
/Users/cliffclarke/Claude_Code/codebase-mcp/docs/mcp-split-plan/02-workflow-mcp/HANDOFF-PHASE-0A-WORKFLOW-MCP.md

Please create the repository, initialize git, create the comprehensive CLAUDE.md file, and commit it.
```

---

## Expected Actions

When you paste the above prompt into a new chat, Claude should:

1. **Create Repository Directory**
   - Path: `/Users/cliffclarke/Claude_Code/workflow-mcp`
   - Verify parent directory exists
   - Create workflow-mcp directory

2. **Initialize Git**
   ```bash
   cd /Users/cliffclarke/Claude_Code/workflow-mcp
   git init
   git branch -M main
   ```

3. **Create Comprehensive CLAUDE.md**
   - Write complete CLAUDE.md file (see content below)
   - Place at repository root: `/Users/cliffclarke/Claude_Code/workflow-mcp/CLAUDE.md`

4. **Create Initial Commit**
   ```bash
   git add CLAUDE.md
   git commit -m "docs: initialize repository with comprehensive CLAUDE.md guidance

Add foundational CLAUDE.md file that explains:
- Repository purpose (AI project management MCP)
- Workflow architecture (Specify framework)
- Constitutional principles (12 principles)
- Git workflow (branch-per-feature, micro-commits)
- Technical stack (Python, PostgreSQL, FastMCP)

Ready for Phase 0A infrastructure setup."
   ```

5. **Confirm Readiness**
   - Verify CLAUDE.md exists and is committed
   - Confirm repository ready for Phase 0A
   - Provide next steps instructions

---

## CLAUDE.md Content

Below is the complete CLAUDE.md file content for workflow-mcp:

```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the **Workflow MCP Server** - a focused, production-grade MCP server that provides AI-assisted project management with multi-project workspace support and a generic entity system, designed specifically for AI coding assistants.

**Purpose:**
- Manage hierarchical work items (projects → sessions → tasks → research)
- Track domain-specific entities (vendors, game mechanics, research papers) via generic JSONB storage
- Record deployment history with relationships
- Support multiple isolated project workspaces (one database per project)

**NOT in Scope:**
- Code intelligence (semantic search, indexing) - see codebase-mcp
- Cloud synchronization or remote state management
- Workflow automation engines or complex event processing

**Relationship to codebase-mcp:**
- **codebase-mcp**: Code intelligence (semantic search, repository indexing)
- **workflow-mcp**: Project management (work items, entities, deployments)
- **Integration**: codebase-mcp queries workflow-mcp for active project context

The project uses the **Specify** spec-driven development workflow for AI-assisted software engineering. It provides a structured process for feature development through slash commands that guide specification, planning, task generation, and implementation.

## Workflow Architecture

The workflow follows a sequential, phase-gated approach:

1. **`/specify <feature_description>`** - Creates feature specification from natural language
2. **`/clarify`** - Interactive Q&A to resolve ambiguities in the spec (run before `/plan`)
3. **`/plan`** - Generates implementation plan with design artifacts
4. **`/tasks`** - Creates dependency-ordered task breakdown
5. **`/analyze`** - Validates consistency across spec/plan/tasks artifacts
6. **`/implement`** - Executes the task plan

### Command Dependencies

- `/clarify` requires `/specify` to have run first
- `/plan` should run after `/clarify` (warns if clarifications missing)
- `/tasks` requires `/plan` completion
- `/analyze` requires `/tasks` completion
- `/implement` requires `/tasks` completion

## Key Directories

```
.specify/
├── memory/
│   └── constitution.md      # Project-specific constitutional principles
├── scripts/bash/
│   ├── create-new-feature.sh      # Initializes feature branch & spec
│   ├── check-prerequisites.sh     # Validates workflow state
│   ├── setup-plan.sh              # Prepares planning phase
│   └── update-agent-context.sh    # Updates agent guidance files
└── templates/
    ├── spec-template.md     # Feature specification structure
    ├── plan-template.md     # Implementation plan structure
    └── tasks-template.md    # Task breakdown structure

.claude/commands/           # Slash command definitions for Claude Code

specs/###-feature-name/    # Generated per-feature directories
├── spec.md               # Feature requirements (WHAT/WHY, no HOW)
├── plan.md               # Technical design (Phase 0-2 by /plan)
├── research.md           # Technical research decisions
├── data-model.md         # Entity definitions
├── contracts/            # API contracts (OpenAPI/GraphQL)
├── quickstart.md         # Integration test scenarios
└── tasks.md              # Ordered implementation tasks (by /tasks)
```

## Script Usage

### create-new-feature.sh
```bash
# Run from repo root
.specify/scripts/bash/create-new-feature.sh --json "feature description"
# Creates: branch, specs/###-name/ directory, initializes spec.md
# Outputs JSON: {"BRANCH_NAME":"...", "SPEC_FILE":"...", "FEATURE_NUM":"..."}
```

### check-prerequisites.sh
```bash
# Check if plan.md exists (for /tasks)
.specify/scripts/bash/check-prerequisites.sh --json

# Check if tasks.md exists (for /implement)
.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks

# Get paths only without validation (for /clarify)
.specify/scripts/bash/check-prerequisites.sh --json --paths-only
```

### update-agent-context.sh
```bash
# Update Claude Code guidance file (CLAUDE.md in repo root)
.specify/scripts/bash/update-agent-context.sh claude

# Supports: claude, copilot, gemini, qwen, agents (generic)
# Incremental updates preserve manual edits between markers
```

## Constitutional Principles

This project's constitution (`.specify/memory/constitution.md`) defines non-negotiable principles for the Workflow MCP Server. The `/constitution` command manages this file.

**Workflow MCP Core Principles:**
1. **Simplicity Over Features** - Focus exclusively on AI-assisted project management
2. **Local-First Architecture** - No cloud dependencies, offline-capable
3. **MCP Protocol Compliance** - FastMCP + SSE, no stdout/stderr pollution
4. **Performance Guarantees** - <50ms project switching, <200ms work items, <100ms entities
5. **Production Quality** - Comprehensive error handling, type safety, logging
6. **Specification-First Development** - Requirements before implementation
7. **Test-Driven Development** - Tests before code, protocol compliance validation
8. **Pydantic-Based Type Safety** - All models use Pydantic, mypy --strict
9. **Orchestrated Subagent Execution** - Parallel implementation via specialized subagents
10. **Git Micro-Commit Strategy** - Atomic commits after each task, branch-per-feature, Conventional Commits
11. **FastMCP and Python SDK Foundation** - Use FastMCP framework with MCP Python SDK for all MCP implementations
12. **Generic Entity Adaptability** - JSONB storage, runtime schema registration, NO hardcoded domain tables

**Key behaviors:**
- Constitution violations are flagged as CRITICAL in `/analyze`
- `/plan` validates against constitution at Phase 0 (before research) and after Phase 1 (after design)
- Complexity deviations must be justified in plan.md's Complexity Tracking section
- Technical stack is NON-NEGOTIABLE: Python 3.11+, PostgreSQL 14+, FastMCP with MCP Python SDK, AsyncPG, Pydantic

**Unique to workflow-mcp:**
- **Database-per-project isolation**: Each project gets its own PostgreSQL database
- **Generic entity system**: JSONB storage with runtime JSON Schema validation (NO hardcoded vendor/mechanic tables)
- **LRU connection pool management**: Max 50 active project pools to prevent connection exhaustion
- **Multi-project workspaces**: Support 100+ projects without degradation

## Important Workflow Rules

### Specification Phase (`/specify`, `/clarify`)
- Specs describe WHAT users need and WHY (business value)
- **NO** implementation details (no tech stack, APIs, code structure)
- Mark ambiguities with `[NEEDS CLARIFICATION: question]`
- `/clarify` asks max 5 questions to resolve ambiguities

### Planning Phase (`/plan`)
- Stops after Phase 1 (design artifacts generated)
- Phase 2 planning is described but NOT executed
- Generates: research.md, data-model.md, contracts/, quickstart.md, agent file
- Outputs are in `specs/###-feature/` directory

### Task Generation (`/tasks`)
- Uses `.specify/templates/tasks-template.md` as base
- Tasks marked `[P]` can run in parallel (different files)
- Sequential tasks (same file) must not be marked `[P]`
- TDD approach: test tasks before implementation tasks

### Implementation (`/implement`)
- Executes tasks.md sequentially by phase
- Must mark completed tasks as `[X]` in tasks.md
- Halts on non-parallel task failures
- Respects TDD: tests before implementation

## Git Workflow

### Branch Management
- All features MUST be developed on dedicated branches: `###-feature-name` (e.g., `001-multi-project-workspaces`)
- Create branches from `main`: `git checkout -b 001-feature-name`
- The `/specify` command automatically creates feature branches

### Commit Strategy
- **Micro-commits**: Commit after each completed task in tasks.md
- **Conventional Commits**: `type(scope): description`
  - Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`
  - Example: `feat(workspaces): add project switching with <50ms latency`
- **Working state**: Each commit MUST pass all tests
- **Atomic commits**: One logical change per commit

### Workflow Example
```bash
# Feature branch created by /specify
git checkout -b 001-multi-project-workspaces

# Complete task T001
git add .
git commit -m "feat(workspaces): initialize project structure with registry database"

# Complete task T002
git add .
git commit -m "test(workspaces): add contract tests for project creation"

# Feature complete, all tests pass
git push origin 001-multi-project-workspaces
# Create PR for review
```

## Common Development Tasks

Development consists of:

1. **Enhancing workflow commands**: Edit `.claude/commands/*.md`
2. **Modifying templates**: Edit `.specify/templates/*.md`
3. **Updating scripts**: Edit `.specify/scripts/bash/*.sh`
4. **Customizing constitution**: Use `/constitution` command

## Template Placeholders

Templates use `[UPPERCASE_TOKENS]` as placeholders that must be replaced during execution. Common examples:
- `[FEATURE_NAME]`, `[PROJECT_NAME]`
- `[PRINCIPLE_1_NAME]`, `[PRINCIPLE_1_DESCRIPTION]`
- `[NEEDS CLARIFICATION: specific question]` (marks underspecified areas)

## File Path Conventions

- **All scripts output absolute paths** when using `--json` flag
- Scripts validate feature branch context before execution
- Feature directories: `specs/###-abbreviated-name/`
- Branch names: `###-abbreviated-name` (3-digit prefix, max 3 words)

## Error Handling Patterns

Scripts use consistent error messaging:
```
ERROR: <problem>
<suggested action: which command to run>
```

Example: "ERROR: plan.md not found. Run /plan first to create the implementation plan."

## Agent Context Files

The workflow can generate agent-specific guidance files:
- Claude Code: `CLAUDE.md` (repo root)
- GitHub Copilot: `.github/copilot-instructions.md`
- Gemini CLI: `GEMINI.md`
- Qwen Code: `QWEN.md`
- Generic: `AGENTS.md`

These files are updated incrementally by `update-agent-context.sh`, preserving manual edits between marker comments.

## Architecture Overview

### Database Architecture
- **Registry database**: `workflow_registry` (project metadata, active context)
- **Project databases**: `workflow_project_{uuid}` (one per project)
- **Isolation**: Projects never see each other's data (database-level separation)

### Generic Entity System
- **Single entities table**: JSONB storage per project
- **Runtime schemas**: JSON Schema registration via `register_entity_type` tool
- **Pydantic validation**: Entity data validated against registered schema
- **Example domains**: vendors (commission work), game_mechanics (game dev), papers (research)

### Connection Pool Management
- **Registry pool**: 10 connections (persistent)
- **Project pools**: LRU cache with max 50 active pools (5 connections each)
- **Eviction**: Least-recently-used pools closed automatically
- **Lazy loading**: Pools created on first project access

### Work Item Hierarchy
- **Levels**: project → session → task → research (up to 5 levels deep)
- **Materialized path**: Fast ancestor queries
- **Recursive CTEs**: Efficient descendant traversal
- **Performance target**: <200ms p95 latency for hierarchy operations

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
- **pytest-benchmark**: Performance regression testing

### Infrastructure
- **PostgreSQL**: Multiple databases (registry + per-project)
- **Connection pooling**: AsyncPG pools per project (LRU eviction)
- **Structured logging**: JSON logs to file (loguru or stdlib logging)

## Performance Targets

All performance targets are p95 latency:

- **Project switching**: <50ms (registry query + connection pool lookup)
- **Work item operations**: <200ms (hierarchy queries, dependency resolution)
- **Entity queries**: <100ms (JSONB filtering with GIN indexing)
- **Task listing**: <150ms (summary mode, token-efficient)
- **Deployment recording**: <200ms (event + relationships)

## Testing Requirements

- **Unit tests**: >90% coverage
- **Integration tests**: All MCP tools invocable from Claude Desktop/CLI
- **Isolation tests**: Multi-project operations never leak data
- **Performance tests**: p95 latency validation in CI (fails on >20% regression)
- **Protocol tests**: MCP tool invocation contracts (input/output schemas)

## Reference Documentation

Complete planning documentation is in the codebase-mcp repository at:
`/Users/cliffclarke/Claude_Code/codebase-mcp/docs/mcp-split-plan/02-workflow-mcp/`

Key files:
- `constitution.md` - Full constitutional principles (12 principles)
- `FINAL-IMPLEMENTATION-PLAN.md` - Complete implementation plan with phases
- `HANDOFF-PHASE-*.md` - Phase-specific implementation handoffs
```

---

## Verification Steps

After running the initialization prompt, verify:

1. **Repository Created**
   ```bash
   ls -la /Users/cliffclarke/Claude_Code/workflow-mcp
   # Should show .git/ directory and CLAUDE.md file
   ```

2. **Git Initialized**
   ```bash
   cd /Users/cliffclarke/Claude_Code/workflow-mcp
   git status
   # Should show "On branch main" with clean working tree
   ```

3. **CLAUDE.md Committed**
   ```bash
   git log --oneline
   # Should show initial commit with CLAUDE.md
   ```

4. **CLAUDE.md Content**
   ```bash
   head -20 /Users/cliffclarke/Claude_Code/workflow-mcp/CLAUDE.md
   # Should show "# CLAUDE.md" header and repository overview
   ```

5. **File Size Check**
   ```bash
   wc -l /Users/cliffclarke/Claude_Code/workflow-mcp/CLAUDE.md
   # Should be ~250-300 lines
   ```

---

## Next Steps

After initialization is complete and verified:

1. **Review CLAUDE.md**
   - Ensure all 12 constitutional principles are documented
   - Verify workflow architecture section is complete
   - Check technical stack and performance targets

2. **Proceed to Phase 0A**
   - Open the handoff document: `/Users/cliffclarke/Claude_Code/codebase-mcp/docs/mcp-split-plan/02-workflow-mcp/HANDOFF-PHASE-0A-WORKFLOW-MCP.md`
   - Start a new chat session
   - Copy the Phase 0A prompt into the new chat
   - Execute infrastructure setup tasks

3. **Expected Phase 0A Deliverables**
   - `.specify/` directory structure
   - `.claude/commands/` directory with slash commands
   - `constitution.md` in `.specify/memory/`
   - Basic Python project structure (pyproject.toml, src/, tests/)
   - Git commit with Phase 0A completion

---

## Troubleshooting

### Issue: Repository directory already exists
**Solution:** Remove or rename existing directory:
```bash
mv /Users/cliffclarke/Claude_Code/workflow-mcp /Users/cliffclarke/Claude_Code/workflow-mcp.backup
```

### Issue: Git already initialized
**Solution:** Verify it's correct, or start fresh:
```bash
rm -rf /Users/cliffclarke/Claude_Code/workflow-mcp/.git
git init
```

### Issue: CLAUDE.md content incomplete
**Solution:** Use the complete content from this document's "CLAUDE.md Content" section

### Issue: Commit message format incorrect
**Solution:** Use the exact commit message from "Expected Actions" section above

---

## Summary

This initialization prompt:
1. Creates the workflow-mcp repository at `/Users/cliffclarke/Claude_Code/workflow-mcp`
2. Initializes git with main branch
3. Creates a comprehensive CLAUDE.md file (250-300 lines) with:
   - Repository overview and purpose
   - Workflow architecture (Specify framework)
   - 12 constitutional principles
   - Git workflow and commit strategy
   - Technical stack and performance targets
   - Testing requirements
4. Commits CLAUDE.md with proper Conventional Commits format
5. Prepares repository for Phase 0A execution

**Critical Success Factors:**
- CLAUDE.md must be comprehensive (similar to codebase-mcp)
- All 12 constitutional principles documented
- Workflow architecture clearly explained
- Technical stack and performance targets specified
- Reference to planning documentation location

**After initialization:** Proceed to Phase 0A using HANDOFF-PHASE-0A-WORKFLOW-MCP.md
