# Codebase MCP Server

## Overview

The **Codebase MCP Server** is a focused, production-grade Model Context Protocol (MCP) server that provides semantic code search capabilities for AI coding assistants. It indexes code repositories into PostgreSQL with pgvector for fast, accurate semantic search across multiple projects.

## Purpose and Scope

### What This MCP Does

1. **Semantic Code Search** - Natural language search across indexed code repositories using embedding-based similarity matching
2. **Multi-Project Support** - Maintains separate indexes for multiple projects with isolation guarantees
3. **Repository Indexing** - Scans, chunks, and embeds code files with metadata preservation
4. **Context-Aware Results** - Returns code snippets with surrounding context (lines before/after)
5. **Performance Optimization** - Sub-500ms search latency with efficient batching and caching

### What This MCP Does NOT Do

This MCP is explicitly scoped to **semantic code search only**. It does NOT:

- Track work items, tasks, or project management metadata
- Manage deployments or deployment history
- Track vendor integrations or vendor status
- Store project configuration beyond search-related settings
- Implement workflow orchestration or task execution
- Provide code analysis, linting, or refactoring tools

## Relationship to workflow-mcp

The Codebase MCP operates as a **pure search service** within a multi-MCP architecture:

```
┌─────────────────┐
│  workflow-mcp   │  ← Project registry, work items, orchestration
└────────┬────────┘
         │ queries active_project_id
         ▼
┌─────────────────┐
│  codebase-mcp   │  ← Semantic code search ONLY
└─────────────────┘
         │ one database per project
         ▼
┌─────────────────┐
│  PostgreSQL     │  ← pgvector for embeddings
│  (per project)  │
└─────────────────┘
```

**Key Integration Points:**

1. **Project Context**: Codebase MCP queries workflow-mcp to determine the active project ID
2. **Database Isolation**: Each project registered in workflow-mcp has a corresponding codebase database
3. **Single Responsibility**: workflow-mcp handles ALL non-search concerns (tasks, deployments, vendors)
4. **Independent Operation**: Codebase MCP can function standalone with explicit project_id parameters

## Key Features Post-Refactor

### 1. Multi-Project Code Search

- Search across multiple codebases simultaneously or filtered by project
- Automatic project context switching via workflow-mcp integration
- Per-project database isolation (no cross-contamination)

### 2. Simplified Tool Surface

**Before Refactor (13 tools):**
- index_repository, search_code (SEARCH)
- create_work_item, list_work_items, query_work_item, update_work_item (WORK ITEMS)
- create_task, get_task, list_tasks, update_task (TASKS)
- record_deployment (DEPLOYMENTS)
- create_vendor, query_vendor_status, update_vendor_status (VENDORS)

**After Refactor (2 tools):**
- `index_repository(repo_path, project_id)` - Index code for a project
- `search_code(query, project_id, filters)` - Semantic search with optional filters

### 3. Performance Guarantees

- **Indexing**: <60 seconds for 10,000 files (batched processing)
- **Search**: <500ms p95 latency (including embedding generation)
- **Embedding Generation**: Batched requests (50 embeddings/batch)
- **Database Queries**: Optimized pgvector cosine similarity with HNSW indexes

### 4. Local-First Architecture

- No cloud dependencies (runs entirely offline)
- Local Ollama instance for embeddings (nomic-embed-text model)
- PostgreSQL on localhost or local network
- Portable across development environments

### 5. Protocol Compliance

- Clean MCP implementation via FastMCP framework
- SSE (Server-Sent Events) transport only
- No stdout/stderr pollution (structured logging to files)
- Type-safe with Pydantic models and mypy --strict

## Technical Architecture

```
┌──────────────────────────────────────────────────┐
│  MCP Client (Claude Code, Cline, etc.)          │
└────────────────────┬─────────────────────────────┘
                     │ SSE transport
                     ▼
┌──────────────────────────────────────────────────┐
│  codebase-mcp (FastMCP)                          │
│  ┌────────────────────────────────────────────┐  │
│  │  index_repository(repo_path, project_id)   │  │
│  │  search_code(query, project_id, filters)   │  │
│  └────────────────────────────────────────────┘  │
└────────────────────┬─────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   ┌─────────┐  ┌─────────┐  ┌─────────┐
   │ Ollama  │  │ AsyncPG │  │workflow │
   │ (embed) │  │ (pgvec) │  │   -mcp  │
   └─────────┘  └─────────┘  └─────────┘
                     │
              ┌──────┴──────┐
              ▼             ▼
         ┌────────┐    ┌────────┐
         │ proj_1 │    │ proj_2 │  ← One DB per project
         │   DB   │    │   DB   │
         └────────┘    └────────┘
```

## Success Criteria

1. **Functional**:
   - Index and search across 3+ projects simultaneously
   - Sub-500ms search response time (p95)
   - No data leakage between projects

2. **Non-Functional**:
   - 100% MCP protocol compliance (validated via mcp-inspector)
   - Type-safe (mypy --strict passes)
   - All tests pass (unit, integration, protocol compliance)

3. **Operational**:
   - Works offline (no internet required after model download)
   - Single configuration file per project
   - Clear error messages with actionable guidance

## Development Status

**Current State**: Monolithic codebase-mcp with search + work items + vendors + tasks + deployments

**Target State**: Pure semantic search MCP with multi-project support

**Development Approach**: Option B Sequential (workflow-mcp core exists first, then refactor codebase-mcp)

See `implementation-phases.md` for detailed refactoring roadmap.
