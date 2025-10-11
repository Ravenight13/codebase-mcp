# MCP Split Plan: Executive Summary

## Overview

This document outlines the comprehensive plan to split the current monolithic `codebase-mcp` into two focused, independent MCP servers, each with multi-project workspace support.

## What We're Doing

### Current State
- **One monolithic MCP** (`codebase-mcp`) that handles:
  - Semantic code search (pgvector + embeddings)
  - Work item tracking (projects, sessions, tasks, research)
  - Vendor management (commission extraction domain)
  - Task management (legacy)
  - Deployment tracking
- **Single global namespace** - all entities mixed together
- **Constitutional violation** - tool tries to do too much

### Target State
- **Two independent MCPs:**
  1. **`codebase-mcp`** - Pure semantic code search
  2. **`workflow-mcp`** - AI project management with generic entity system
- **Multi-project support** - complete isolation between projects
- **Database per project** - true physical separation
- **Generic entity system** - adaptable to any domain (vendors, game mechanics, etc.)

## Why We're Doing This

### Business Value
1. **Clear Focus** - Each MCP does one thing exceptionally well
2. **Reusability** - Use code search without project management (and vice versa)
3. **Domain Flexibility** - Generic entity system adapts to commission work, game dev, etc.
4. **Scalability** - Multi-project support for unlimited concurrent projects
5. **Constitutional Alignment** - Tools follow "do one thing well" philosophy

### Technical Benefits
1. **True Isolation** - Projects cannot interfere (separate databases)
2. **Easy Cleanup** - Delete project = DROP DATABASE
3. **Performance Isolation** - Heavy indexing doesn't affect other projects
4. **Independent Scaling** - Each MCP can evolve separately
5. **Smaller Codebases** - Easier to maintain and test

## How We're Going to Do It

### Development Strategy: Modified Sequential

**Phase 0: Foundation Setup (Week 1)**
- Establish complete infrastructure foundation before feature implementation
- workflow-mcp: Brand new repository initialization
  - Project structure, pyproject.toml, test framework
  - FastMCP server skeleton, database connection setup
  - CI/CD pipeline, mypy --strict compliance
- codebase-mcp: Baseline and refactor preparation
  - Backup current state, create refactor branch
  - Test framework updates, dependency audit
- Database validation: CREATEDB permissions, pgvector setup

**Phase 1: workflow-mcp Core (Weeks 2-4)**
- Create brand new repository
- Build project management foundation:
  - Registry database
  - `create_project`, `switch_active_project`, `get_active_project`
  - Project-per-database architecture
  - Connection pooling system
- Stop before work items/tasks/entities

**Phase 2: codebase-mcp Refactor (Weeks 5-7)**
- Create refactoring branch in existing repo
- Remove all non-search features (work items, vendors, tasks, deployments)
- Add multi-project support to semantic search
- Query workflow-mcp for active project
- Keep only: `index_repository`, `search_code`

**Phase 3: workflow-mcp Complete (Weeks 8-10)**
- Add work item hierarchy system
- Add task management
- Add generic entity system (vendors, game mechanics, etc.)
- Add deployment tracking
- Complete multi-project feature set

### Architecture Highlights

#### Database Design
```
PostgreSQL Server
├── project_registry (special)
│   └── projects (id, name, slug, codebase_db, workflow_db)
│
├── project_commission_extraction
│   ├── codebase schema (repositories, code_chunks)
│   └── workflow schema (work_items, tasks, entities)
│
└── project_ttrpg_starbound
    ├── codebase schema
    └── workflow schema
```

**Key Features:**
- One database per project
- Both MCPs access same project database (different schemas)
- Registry tracks which database belongs to which project
- Dynamic database creation on project creation
- Connection pooling per project

#### Generic Entity System
```python
# Commission project: Register "vendor" entity
register_entity_type(
    entity_type="vendor",
    json_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "status": {"enum": ["operational", "broken"]},
            "extractor_version": {"type": "string"}
        }
    }
)

# TTRPG project: Register "game_mechanic" entity
register_entity_type(
    entity_type="game_mechanic",
    json_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "mechanic_type": {"enum": ["dice", "skill", "combat"]},
            "implementation_status": {"type": "string"}
        }
    }
)
```

**No hardcoded vendor tables** - completely adaptable to any domain.

## Implementation Principles

Both MCPs follow these shared on-rails principles (duplicated in each constitution):

1. **Foundation-First Development** - Phase 0 establishes test framework and infrastructure before features
2. **Pydantic-Based Type Safety** - All models use Pydantic with full validation
3. **Git Micro-Commit Strategy** - Atomic commits after each task, Conventional Commits format
4. **Orchestrated Subagent Execution** - Parallel subagents for independent tasks
5. **Test-Driven Development** - Tests before implementation
6. **FastMCP Framework** - Decorative patterns for tool registration
7. **mypy --strict Compliance** - Complete type safety
8. **Async Everything** - All I/O operations asynchronous
9. **Protocol Compliance** - MCP via SSE, no stdout pollution

## Quality Assurance: 4-Step Review Process

Each MCP's implementation plan goes through rigorous review:

1. **Initial Plan** (Subagent) - Draft implementation plan
2. **Planning Review** (Subagent) - Validate completeness, catch gaps
3. **Architectural Review** (Subagent) - Verify alignment with Specify framework
4. **Final Revised Plan** (Subagent) - Integrate feedback, produce final plan

**Both MCPs developed in parallel tracks** using this process.

## Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 0: Foundation Setup | Week 1 | Infrastructure and test framework |
| Phase 1: workflow-mcp Core | Weeks 2-4 | Project management foundation |
| Phase 2: codebase-mcp Refactor | Weeks 5-7 | Pure semantic search MCP |
| Phase 3: workflow-mcp Complete | Weeks 8-10 | Full project management MCP |
| **Total** | **10 weeks** | **Two production-ready MCPs** |

## Success Criteria

### codebase-mcp
- ✅ Only semantic search tools remain
- ✅ Multi-project support (filter by project_id)
- ✅ <500ms search latency (p95)
- ✅ Constitutional compliance (focus on one thing)
- ✅ Works independently without workflow-mcp

### workflow-mcp
- ✅ Complete project management (create/switch/list/delete projects)
- ✅ Work item hierarchy (projects, sessions, tasks, research)
- ✅ Generic entity system (adaptable to any domain)
- ✅ Task management with status tracking
- ✅ Deployment history with relationships
- ✅ One database per project with true isolation

### Integration
- ✅ Both MCPs run simultaneously on different ports
- ✅ codebase-mcp queries workflow-mcp for active project
- ✅ Seamless project switching affects both MCPs
- ✅ No cross-project data leakage
- ✅ Easy backup/restore per project (pg_dump one database)

## Documentation Structure

```
/docs/mcp-split-plan/
├── README.md (this file)
│
├── 00-architecture/
│   ├── overview.md
│   ├── database-design.md
│   ├── connection-management.md
│   ├── entity-system.md
│   └── deployment-config.md
│
├── 01-codebase-mcp/
│   ├── README.md
│   ├── constitution.md
│   ├── user-stories.md
│   ├── specify-prompt.txt
│   ├── tech-stack.md
│   ├── refactoring-plan.md
│   └── implementation-phases.md
│
├── 02-workflow-mcp/
│   ├── README.md
│   ├── constitution.md
│   ├── user-stories.md
│   ├── specify-prompt.txt
│   ├── tech-stack.md
│   ├── entity-system-examples.md
│   └── implementation-phases.md
│
└── 03-orchestration/
    ├── subagent-workflow.md
    ├── git-strategy.md
    ├── parallel-execution-plan.md
    └── testing-strategy.md
```

## Prerequisites

### Before Starting
1. **Backup current codebase-mcp repository**
   ```bash
   cd /Users/cliffclarke/Claude_Code/codebase-mcp
   git tag backup-before-split
   git push origin backup-before-split
   ```

2. **PostgreSQL setup**
   - Verify PostgreSQL 14+ with pgvector extension
   - Ensure `CREATEDB` permission for MCP user
   - Test database creation: `createdb test_project && dropdb test_project`

3. **Development environment**
   - Python 3.11+
   - uv package manager
   - Ollama with nomic-embed-text model

### Fresh Start Confirmed
- ✅ No migration scripts needed
- ✅ Can start both MCPs from scratch
- ✅ Existing data can be recreated via full ingestion

## Risk Mitigation

### Risks
1. **Database per project overhead** - Many databases = resource usage
2. **Connection pool complexity** - Dynamic pool management
3. **Cross-MCP coordination** - codebase-mcp depends on workflow-mcp
4. **Generic entity validation** - JSONB flexibility vs type safety

### Mitigations
1. **Resource monitoring** - PostgreSQL handles 20+ databases easily
2. **Lazy pooling** - Only create pools for active projects
3. **Registry database** - Shared source of truth for both MCPs
4. **Pydantic validation** - JSON schemas validated at runtime

## Next Steps

1. **Review this documentation** - Ensure alignment with goals
2. **Execute Phase 0** - Establish infrastructure foundation (Week 1)
   - Initialize workflow-mcp repository with complete test framework
   - Prepare codebase-mcp refactor baseline
   - Validate database permissions and pgvector setup
3. **Launch subagent orchestration** - Create detailed plans with 4-step review
4. **Execute Phase 1** - Build workflow-mcp project management core (Weeks 2-4)
5. **Execute Phase 2** - Refactor codebase-mcp to pure search (Weeks 5-7)
6. **Execute Phase 3** - Complete workflow-mcp feature set (Weeks 8-10)

## Questions or Issues

- Review subagent-generated plans before implementation
- Each phase has clear acceptance criteria
- Git micro-commits enable easy rollback if needed
- Both MCPs maintain independent constitutions

---

**Status**: Documentation complete, ready for subagent orchestration
**Last Updated**: 2025-10-11
**Owner**: Cliff Clarke
