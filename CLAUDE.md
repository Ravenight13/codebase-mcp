# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the **Codebase MCP Server** - a focused, production-grade MCP server that indexes code repositories into PostgreSQL with pgvector for semantic search, designed specifically for AI coding assistants.

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

This project's constitution (`.specify/memory/constitution.md`) defines non-negotiable principles for the Codebase MCP Server. The `/constitution` command manages this file.

**MCP Server Core Principles:**
1. **Simplicity Over Features** - Focus exclusively on semantic code search
2. **Local-First Architecture** - No cloud dependencies, offline-capable
3. **Protocol Compliance** - MCP via SSE, no stdout/stderr pollution
4. **Performance Guarantees** - 60s indexing, 500ms search (p95)
5. **Production Quality** - Comprehensive error handling, type safety, logging
6. **Specification-First Development** - Requirements before implementation
7. **Test-Driven Development** - Tests before code, protocol compliance validation
8. **Pydantic-Based Type Safety** - All models use Pydantic, mypy --strict
9. **Orchestrated Subagent Execution** - Parallel implementation via specialized subagents
10. **Git Micro-Commit Strategy** - Atomic commits after each task, branch-per-feature, Conventional Commits
11. **FastMCP and Python SDK Foundation** - Use FastMCP framework with MCP Python SDK for all MCP implementations

**Key behaviors:**
- Constitution violations are flagged as CRITICAL in `/analyze`
- `/plan` validates against constitution at Phase 0 (before research) and after Phase 1 (after design)
- Complexity deviations must be justified in plan.md's Complexity Tracking section
- Technical stack is NON-NEGOTIABLE: Python 3.11+, PostgreSQL 14+, FastMCP with MCP Python SDK, Ollama

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
- All features MUST be developed on dedicated branches: `###-feature-name` (e.g., `001-semantic-search`)
- Create branches from `main`: `git checkout -b 001-feature-name`
- The `/specify` command automatically creates feature branches

### Commit Strategy
- **Micro-commits**: Commit after each completed task in tasks.md
- **Conventional Commits**: `type(scope): description`
  - Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`
  - Example: `feat(indexer): add tree-sitter AST parsing`
- **Working state**: Each commit MUST pass all tests
- **Atomic commits**: One logical change per commit

### Workflow Example
```bash
# Feature branch created by /specify
git checkout -b 001-semantic-search

# Complete task T001
git add .
git commit -m "feat(indexer): initialize project structure"

# Complete task T002
git add .
git commit -m "test(indexer): add contract tests for embeddings API"

# Feature complete, all tests pass
git push origin 001-semantic-search
# Create PR for review
```

## Common Development Tasks

Development consists of:

1. **Enhancing workflow commands**: Edit `.claude/commands/*.md`
2. **Modifying templates**: Edit `.specify/templates/*.md`
3. **Updating scripts**: Edit `.specify/scripts/bash/*.sh`
4. **Customizing constitution**: Use `/constitution` command

## Running Database Migrations

This project uses Alembic for database schema migrations. Follow these procedures for safe migration execution.

### Standard Migration Workflow

1. **Backup Database** (always backup before migrating):
   ```bash
   pg_dump -h localhost -d codebase_mcp > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Apply Migrations**:
   ```bash
   DATABASE_URL=postgresql+asyncpg://localhost/codebase_mcp alembic upgrade head
   ```

3. **Validate Migration**:
   ```bash
   pytest tests/integration/test_migration_002_validation.py::TestPostMigrationValidation -v
   ```

4. **Monitor Logs** (during migration):
   ```bash
   tail -f /tmp/codebase-mcp-migration.log
   ```

### Rollback Procedure

If issues occur after migration:

1. **Downgrade Migration**:
   ```bash
   DATABASE_URL=postgresql+asyncpg://localhost/codebase_mcp alembic downgrade -1
   ```

2. **Validate Rollback**:
   ```bash
   pytest tests/integration/test_migration_002_validation.py::TestPostRollbackValidation -v
   ```

### Common Alembic Commands

- `alembic current` - Show current migration version
- `alembic history` - Show migration history
- `alembic upgrade head` - Apply all pending migrations
- `alembic downgrade -1` - Rollback one migration step

### Migration Documentation

- **Detailed migration docs**: `docs/migrations/002-schema-refactoring.md`
- **Testing quickstart**: `specs/006-database-schema-refactoring/quickstart.md`

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
