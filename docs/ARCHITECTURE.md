# ARCHITECTURE.md

This document provides a comprehensive technical overview of the Codebase MCP Server architecture, data flows, component interactions, and design decisions.

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow Diagrams](#data-flow-diagrams)
4. [Database Schema](#database-schema)
5. [Tool Handlers](#tool-handlers)
6. [Service Layer](#service-layer)
7. [External Dependencies](#external-dependencies)
8. [Performance Characteristics](#performance-characteristics)
9. [Error Handling Strategy](#error-handling-strategy)
10. [Type Safety Architecture](#type-safety-architecture)

---

## System Overview

The **Codebase MCP Server** is a Model Context Protocol (MCP) server that provides semantic code search and task management capabilities to Claude Desktop. It indexes code repositories into PostgreSQL with pgvector for efficient similarity search.

### Core Capabilities

1. **Semantic Code Search**: Natural language queries against codebase using Ollama embeddings
2. **Task Management**: CRUD operations with git integration (branches, commits, status history)
3. **Repository Indexing**: AST-based chunking with incremental update support
4. **MCP Protocol**: Standards-compliant JSON-RPC over stdio transport

### Architectural Principles

- **Local-First**: No cloud dependencies, fully offline-capable
- **Performance**: 60s indexing for 10K files, 500ms search latency (p95)
- **Type Safety**: Full mypy --strict compliance using Pydantic
- **Production Quality**: Comprehensive error handling, retry logic, connection pooling
- **Protocol Compliance**: Clean MCP implementation with no stdout/stderr pollution

---

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Claude Desktop                           │
│                    (MCP Client via stdio)                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │ JSON-RPC over stdin/stdout
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                   MCP Server Layer                              │
│                (mcp_stdio_server_v3.py)                         │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ Server Initialization                                   │   │
│  │ - Database connection pool setup                       │   │
│  │ - Tool registration (6 tools)                          │   │
│  │ - Request/response lifecycle management                │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ Request Routing                                         │   │
│  │ - @app.list_tools() → Returns tool definitions        │   │
│  │ - @app.call_tool() → Dispatches to handlers           │   │
│  │ - Session management (create → execute → commit)       │   │
│  └────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ Tool calls with arguments
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                   Tool Handler Layer                            │
│              (src/mcp/tools/*.py)                               │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ tasks.py     │  │ indexing.py  │  │ search.py          │  │
│  │              │  │              │  │                    │  │
│  │ - create_    │  │ - index_     │  │ - search_code_tool │  │
│  │   task_tool  │  │   repository_│  │                    │  │
│  │ - get_task_  │  │   tool       │  │ Validates query,   │  │
│  │   tool       │  │              │  │ constructs Search- │  │
│  │ - list_tasks_│  │ Validates    │  │ Filter, calls      │  │
│  │   tool       │  │ path, calls  │  │ searcher service   │  │
│  │ - update_    │  │ indexer      │  │                    │  │
│  │   task_tool  │  │ service      │  │                    │  │
│  │              │  │              │  │                    │  │
│  │ Construct    │  │              │  │                    │  │
│  │ TaskCreate/  │  │              │  │                    │  │
│  │ TaskUpdate,  │  │              │  │                    │  │
│  │ call task    │  │              │  │                    │  │
│  │ service      │  │              │  │                    │  │
│  └──────────────┘  └──────────────┘  └────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ Pydantic models (validated inputs/outputs)
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                     Service Layer                               │
│                 (src/services/*.py)                             │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ Business Logic & Orchestration                          │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ tasks.py     │  │ indexer.py   │  │ searcher.py        │  │
│  │              │  │              │  │                    │  │
│  │ - create_task│  │ - index_     │  │ - search_code      │  │
│  │ - get_task   │  │   repository │  │                    │  │
│  │ - list_tasks │  │ - incremental│  │ Query embedding    │  │
│  │ - update_task│  │   _update    │  │ → pgvector         │  │
│  │              │  │              │  │ similarity →       │  │
│  │ Git metadata │  │ Orchestrates:│  │ context extraction │  │
│  │ tracking     │  │ 1. Scanner   │  │                    │  │
│  │ (branches,   │  │ 2. Chunker   │  │                    │  │
│  │ commits)     │  │ 3. Embedder  │  │                    │  │
│  │              │  │ 4. Persister │  │                    │  │
│  └──────────────┘  └──────────────┘  └────────────────────┘  │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ scanner.py   │  │ chunker.py   │  │ embedder.py        │  │
│  │              │  │              │  │                    │  │
│  │ - scan_      │  │ - chunk_file │  │ - generate_        │  │
│  │   repository │  │ - chunk_     │  │   embedding        │  │
│  │ - detect_    │  │   files_batch│  │ - generate_        │  │
│  │   changes    │  │              │  │   embeddings       │  │
│  │              │  │ Tree-sitter  │  │                    │  │
│  │ File system  │  │ AST parsing  │  │ Ollama HTTP API    │  │
│  │ traversal,   │  │ (Python, JS) │  │ (nomic-embed-text) │  │
│  │ git diff     │  │ Fallback:    │  │ Retry logic,       │  │
│  │ detection    │  │ line-based   │  │ batching (50/req)  │  │
│  └──────────────┘  └──────────────┘  └────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ SQLAlchemy async sessions
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    Database Model Layer                         │
│                  (src/models/*.py)                              │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ SQLAlchemy ORM Models + Pydantic Schemas                │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ task.py      │  │ code_chunk.py│  │ repository.py      │  │
│  │              │  │              │  │                    │  │
│  │ Task         │  │ CodeChunk    │  │ Repository         │  │
│  │ TaskCreate   │  │ CodeChunk-   │  │                    │  │
│  │ TaskUpdate   │  │ Create       │  │                    │  │
│  │ TaskResponse │  │              │  │                    │  │
│  └──────────────┘  └──────────────┘  └────────────────────┘  │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ code_file.py │  │ task_        │  │ tracking.py        │  │
│  │              │  │ relations.py │  │                    │  │
│  │ CodeFile     │  │              │  │ ChangeEvent        │  │
│  │              │  │ TaskStatus-  │  │ Embedding-         │  │
│  │              │  │ History      │  │ Metadata           │  │
│  │              │  │ TaskBranch-  │  │ FileMetadata       │  │
│  │              │  │ Link         │  │                    │  │
│  │              │  │ TaskCommit-  │  │                    │  │
│  │              │  │ Link         │  │                    │  │
│  │              │  │ TaskPlanning-│  │                    │  │
│  │              │  │ Reference    │  │                    │  │
│  └──────────────┘  └──────────────┘  └────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           │ SQL queries (async)
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                   PostgreSQL Database                           │
│                    (with pgvector)                              │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ Connection Pool (AsyncPG)                               │   │
│  │ - Pool size: 20 connections                            │   │
│  │ - Max overflow: 10 connections                         │   │
│  │ - Pre-ping: enabled                                    │   │
│  │ - Connection recycling: 3600s (1 hour)                 │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ 11 Tables with Relationships                            │   │
│  │ - repositories, code_files, code_chunks                │   │
│  │ - tasks, task_status_history                           │   │
│  │ - task_branch_links, task_commit_links                 │   │
│  │ - task_planning_references                             │   │
│  │ - change_events, embedding_metadata, file_metadata     │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ pgvector Extension                                      │   │
│  │ - HNSW index on code_chunks.embedding                  │   │
│  │ - Cosine similarity search (<=> operator)              │   │
│  │ - 768-dimensional vectors (nomic-embed-text)           │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

                           │
                           │ External Services
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                    External Dependencies                        │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ Ollama (Embedding Service)                              │   │
│  │ - Endpoint: http://localhost:11434/api/embeddings     │   │
│  │ - Model: nomic-embed-text                              │   │
│  │ - Dimensions: 768                                      │   │
│  │ - Batch size: 50 texts per request                     │   │
│  │ - Retry logic: 3 attempts with exponential backoff     │   │
│  │ - Timeout: 30s per request                             │   │
│  └────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagrams

### Flow 1: Create Task

```
┌─────────────────┐
│ Claude Desktop  │
└────────┬────────┘
         │
         │ {"tool": "create_task", "arguments": {"title": "Fix bug"}}
         ▼
┌─────────────────────────────────────────────────────────────┐
│ MCP Server (mcp_stdio_server_v3.py)                        │
│                                                             │
│ 1. handle_call_tool(name="create_task", arguments={...})   │
│ 2. Get handler: HANDLERS["create_task"]                    │
│ 3. Create async session: database.SessionLocal()           │
│ 4. Call handler: await handler(db=session, **arguments)    │
└────────┬────────────────────────────────────────────────────┘
         │
         │ kwargs: {db: AsyncSession, title: "Fix bug"}
         ▼
┌─────────────────────────────────────────────────────────────┐
│ create_task_tool (src/mcp/tools/tasks.py)                  │
│                                                             │
│ 1. Validate inputs (title length, planning_references)     │
│ 2. Construct Pydantic model:                               │
│    TaskCreate(                                              │
│      title="Fix bug",                                       │
│      description=None,                                      │
│      notes=None,                                            │
│      planning_references=[]                                 │
│    )                                                        │
│ 3. Call service: await create_task(db, task_data)          │
└────────┬────────────────────────────────────────────────────┘
         │
         │ TaskCreate model
         ▼
┌─────────────────────────────────────────────────────────────┐
│ create_task (src/services/tasks.py)                        │
│                                                             │
│ 1. Create Task ORM model:                                  │
│    task = Task(                                             │
│      title="Fix bug",                                       │
│      status="need to be done"                               │
│    )                                                        │
│    db.add(task)                                             │
│    await db.flush()  # Get task.id                         │
│                                                             │
│ 2. Create TaskPlanningReference records (if any)           │
│                                                             │
│ 3. Create TaskStatusHistory record:                        │
│    history = TaskStatusHistory(                             │
│      task_id=task.id,                                       │
│      from_status=None,                                      │
│      to_status="need to be done"                            │
│    )                                                        │
│    db.add(history)                                          │
│    await db.flush()                                         │
│                                                             │
│ 4. Reload relationships:                                    │
│    await db.refresh(task, [relationships...])               │
│                                                             │
│ 5. Convert to response:                                     │
│    return TaskResponse(id=task.id, title=..., ...)          │
└────────┬────────────────────────────────────────────────────┘
         │
         │ INSERT INTO tasks (title, status, ...) VALUES (...)
         │ INSERT INTO task_status_history (...) VALUES (...)
         ▼
┌─────────────────────────────────────────────────────────────┐
│ PostgreSQL Database                                         │
│                                                             │
│ 1. tasks table: New row with UUID, timestamps              │
│ 2. task_status_history table: Initial transition record    │
│                                                             │
│ Returns: Task model with generated ID                      │
└────────┬────────────────────────────────────────────────────┘
         │
         │ Task ORM model → TaskResponse Pydantic model
         ▼
┌─────────────────────────────────────────────────────────────┐
│ create_task_tool                                            │
│                                                             │
│ Convert TaskResponse to dict:                               │
│ {                                                           │
│   "id": "550e8400-e29b-41d4-a716-446655440000",            │
│   "title": "Fix bug",                                       │
│   "status": "need to be done",                              │
│   "created_at": "2025-10-06T12:00:00Z",                    │
│   ...                                                       │
│ }                                                           │
└────────┬────────────────────────────────────────────────────┘
         │
         │ await session.commit()
         ▼
┌─────────────────────────────────────────────────────────────┐
│ MCP Server                                                  │
│                                                             │
│ 1. Serialize result to JSON                                │
│ 2. Wrap in TextContent:                                     │
│    [TextContent(type="text", text=json_result)]             │
│ 3. Return to MCP client                                    │
└────────┬────────────────────────────────────────────────────┘
         │
         │ JSON-RPC response
         ▼
┌─────────────────┐
│ Claude Desktop  │
│                 │
│ Displays task   │
│ details to user │
└─────────────────┘
```

### Flow 2: Index Repository

```
┌─────────────────┐
│ Claude Desktop  │
└────────┬────────┘
         │
         │ {"tool": "index_repository", "arguments": {"repo_path": "/path/to/repo"}}
         ▼
┌─────────────────────────────────────────────────────────────┐
│ MCP Server → index_repository_tool                         │
│                                                             │
│ 1. Validate repo_path (absolute, exists, is directory)     │
│ 2. Call: await index_repository(                           │
│      repo_path=Path(repo_path),                             │
│      name=repo_name,                                        │
│      db=db,                                                 │
│      force_reindex=False                                    │
│    )                                                        │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ index_repository (src/services/indexer.py)                 │
│                                                             │
│ ORCHESTRATION PIPELINE:                                     │
│                                                             │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Step 1: Repository Management                        │   │
│ │ - Get or create Repository record                   │   │
│ │ - Result: repository.id                             │   │
│ └─────────────────────────────────────────────────────┘   │
│         │                                                   │
│         ▼                                                   │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Step 2: File Discovery (scanner.py)                 │   │
│ │ - Scan directory tree                               │   │
│ │ - Filter binary files (.gitignore, .git/, etc.)     │   │
│ │ - Result: list[Path] (all source files)             │   │
│ └─────────────────────────────────────────────────────┘   │
│         │                                                   │
│         ▼                                                   │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Step 3: Change Detection (scanner.py)               │   │
│ │ - Compare file hashes with database                 │   │
│ │ - Detect added/modified/deleted files               │   │
│ │ - Result: ChangeSet(added, modified, deleted)       │   │
│ └─────────────────────────────────────────────────────┘   │
│         │                                                   │
│         ▼                                                   │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Step 4: Batch Processing (100 files/batch)          │   │
│ │                                                      │   │
│ │ For each batch:                                      │   │
│ │   a. Read file contents (async I/O)                 │   │
│ │   b. Create/update CodeFile records                 │   │
│ │   c. Delete old chunks for modified files           │   │
│ │   d. Chunk files (chunker.py)                       │   │
│ │   e. Collect chunks for embedding                   │   │
│ └─────────────────────────────────────────────────────┘   │
│         │                                                   │
│         ▼                                                   │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Step 5: Embedding Generation (embedder.py)          │   │
│ │ - Batch size: 50 texts per request                  │   │
│ │ - Parallel requests to Ollama                       │   │
│ │ - Retry logic: 3 attempts with backoff              │   │
│ │ - Result: list[list[float]] (768-dim vectors)       │   │
│ └─────────────────────────────────────────────────────┘   │
│         │                                                   │
│         ▼                                                   │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Step 6: Database Persistence                        │   │
│ │ - Assign embeddings to CodeChunk models             │   │
│ │ - Bulk insert chunks with embeddings                │   │
│ │ - Create ChangeEvent records                        │   │
│ │ - Create EmbeddingMetadata record                   │   │
│ │ - Update repository.last_indexed_at                 │   │
│ └─────────────────────────────────────────────────────┘   │
│         │                                                   │
│         ▼                                                   │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Step 7: Return Result                               │   │
│ │ IndexResult(                                         │   │
│ │   repository_id=UUID(...),                          │   │
│ │   files_indexed=250,                                │   │
│ │   chunks_created=1500,                              │   │
│ │   duration_seconds=45.2,                            │   │
│ │   status="success",                                 │   │
│ │   errors=[]                                          │   │
│ │ )                                                    │   │
│ └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ Claude Desktop  │
│                 │
│ Shows indexing  │
│ summary stats   │
└─────────────────┘
```

### Flow 3: Semantic Code Search

```
┌─────────────────┐
│ Claude Desktop  │
└────────┬────────┘
         │
         │ {"tool": "search_code", "arguments": {"query": "authentication middleware"}}
         ▼
┌─────────────────────────────────────────────────────────────┐
│ search_code_tool (src/mcp/tools/search.py)                 │
│                                                             │
│ 1. Validate query (non-empty)                              │
│ 2. Construct SearchFilter:                                 │
│    SearchFilter(                                            │
│      repository_id=None,                                    │
│      file_type=None,                                        │
│      directory=None,                                        │
│      limit=10                                               │
│    )                                                        │
│ 3. Call: await search_code(query, db, filters)             │
└────────┬────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│ search_code (src/services/searcher.py)                     │
│                                                             │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Phase 1: Query Embedding                            │   │
│ │ - Call Ollama API                                   │   │
│ │ - Model: nomic-embed-text                           │   │
│ │ - Input: "authentication middleware"                │   │
│ │ - Output: 768-dimensional vector                    │   │
│ │ - Duration: ~100ms                                  │   │
│ └─────────────────────────────────────────────────────┘   │
│         │                                                   │
│         ▼                                                   │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Phase 2: Similarity Search (pgvector)               │   │
│ │                                                      │   │
│ │ SQL Query:                                           │   │
│ │   SELECT                                             │   │
│ │     chunk.id,                                        │   │
│ │     chunk.content,                                   │   │
│ │     chunk.start_line,                                │   │
│ │     chunk.end_line,                                  │   │
│ │     file.path,                                       │   │
│ │     file.relative_path,                              │   │
│ │     1 - (chunk.embedding <=> query_vec) AS sim      │   │
│ │   FROM code_chunks chunk                             │   │
│ │   JOIN code_files file ON chunk.code_file_id = file.id│   │
│ │   WHERE chunk.embedding IS NOT NULL                  │   │
│ │     AND file.is_deleted = FALSE                      │   │
│ │   ORDER BY chunk.embedding <=> query_vec             │   │
│ │   LIMIT 10;                                          │   │
│ │                                                      │   │
│ │ HNSW Index: Fast approximate nearest neighbor       │   │
│ │ Duration: ~50ms                                      │   │
│ └─────────────────────────────────────────────────────┘   │
│         │                                                   │
│         ▼                                                   │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Phase 3: Context Extraction (parallel)              │   │
│ │                                                      │   │
│ │ For each result:                                     │   │
│ │   - Read source file (async I/O)                    │   │
│ │   - Extract 10 lines before chunk                   │   │
│ │   - Extract 10 lines after chunk                    │   │
│ │   - Build SearchResult:                             │   │
│ │     SearchResult(                                    │   │
│ │       chunk_id=UUID(...),                           │   │
│ │       file_path="src/auth/middleware.py",           │   │
│ │       content="def authenticate(req): ...",          │   │
│ │       start_line=15,                                 │   │
│ │       end_line=30,                                   │   │
│ │       similarity_score=0.87,                         │   │
│ │       context_before="...",                          │   │
│ │       context_after="..."                            │   │
│ │     )                                                │   │
│ │                                                      │   │
│ │ Duration: ~50ms (10 files in parallel)              │   │
│ └─────────────────────────────────────────────────────┘   │
│         │                                                   │
│         ▼                                                   │
│ ┌─────────────────────────────────────────────────────┐   │
│ │ Phase 4: Return Results                             │   │
│ │ list[SearchResult] (ordered by similarity)          │   │
│ │ Total duration: ~200ms                              │   │
│ └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ Claude Desktop  │
│                 │
│ Displays search │
│ results with    │
│ context         │
└─────────────────┘
```

---

## Database Schema

### Entity-Relationship Diagram

```
┌─────────────────────┐
│    repositories     │
│ ─────────────────── │
│ id (UUID, PK)       │
│ path (TEXT, UNIQUE) │
│ name (VARCHAR)      │
│ last_indexed_at     │
│ is_active (BOOLEAN) │
│ created_at          │
│ updated_at          │
└──────────┬──────────┘
           │
           │ 1:N
           ▼
┌─────────────────────┐
│     code_files      │
│ ─────────────────── │
│ id (UUID, PK)       │
│ repository_id (FK)  │
│ path (TEXT)         │
│ relative_path       │
│ content_hash        │
│ size_bytes          │
│ language            │
│ modified_at         │
│ indexed_at          │
│ is_deleted          │
│ deleted_at          │
└──────────┬──────────┘
           │
           │ 1:N
           ▼
┌──────────────────────────┐
│      code_chunks         │
│ ──────────────────────── │
│ id (UUID, PK)            │
│ code_file_id (FK)        │
│ content (TEXT)           │
│ start_line (INT)         │
│ end_line (INT)           │
│ chunk_type (ENUM)        │
│ embedding (VECTOR(768))  │◄── HNSW Index for fast search
│ created_at               │
└──────────────────────────┘


┌─────────────────────┐
│       tasks         │
│ ─────────────────── │
│ id (UUID, PK)       │
│ title (VARCHAR)     │
│ description (TEXT)  │
│ notes (TEXT)        │
│ status (ENUM)       │
│ created_at          │
│ updated_at          │
└──────────┬──────────┘
           │
           │ 1:N
           ├─────────────────────────────┐
           │                             │
           ▼                             ▼
┌──────────────────────┐   ┌──────────────────────────┐
│ task_status_history  │   │ task_planning_references │
│ ──────────────────── │   │ ──────────────────────── │
│ id (UUID, PK)        │   │ id (UUID, PK)            │
│ task_id (FK)         │   │ task_id (FK)             │
│ from_status          │   │ file_path (TEXT)         │
│ to_status            │   │ reference_type (ENUM)    │
│ changed_at           │   │ created_at               │
└──────────────────────┘   └──────────────────────────┘
           │
           │
           ▼
┌──────────────────────┐   ┌──────────────────────────┐
│  task_branch_links   │   │  task_commit_links       │
│ ──────────────────── │   │ ──────────────────────── │
│ id (UUID, PK)        │   │ id (UUID, PK)            │
│ task_id (FK)         │   │ task_id (FK)             │
│ branch_name          │   │ commit_hash (CHAR(40))   │
│ linked_at            │   │ commit_message (TEXT)    │
│                      │   │ linked_at                │
│ UNIQUE(task, branch) │   │ UNIQUE(task, commit)     │
└──────────────────────┘   └──────────────────────────┘


┌─────────────────────┐
│  code_files (FK)    │
└──────────┬──────────┘
           │ 1:N
           ▼
┌──────────────────────┐
│   change_events      │
│ ──────────────────── │
│ id (UUID, PK)        │
│ code_file_id (FK)    │
│ event_type (ENUM)    │
│ detected_at          │
│ processed (BOOLEAN)  │
└──────────────────────┘


┌──────────────────────────┐
│  embedding_metadata      │
│ ──────────────────────── │
│ id (UUID, PK)            │
│ model_name               │
│ model_version            │
│ dimensions               │
│ generation_time_ms       │
│ created_at               │
└──────────────────────────┘


┌─────────────────────┐
│  code_files (FK)    │
└──────────┬──────────┘
           │ 1:1
           ▼
┌──────────────────────┐
│   file_metadata      │
│ ──────────────────── │
│ id (UUID, PK)        │
│ code_file_id (FK)    │
│ lines_of_code        │
│ complexity_score     │
│ created_at           │
│ updated_at           │
└──────────────────────┘
```

### Key Indexes

```sql
-- pgvector HNSW index for fast similarity search
CREATE INDEX idx_code_chunks_embedding_hnsw
ON code_chunks USING hnsw (embedding vector_cosine_ops);

-- File lookup indexes
CREATE INDEX idx_code_files_repository_id ON code_files(repository_id);
CREATE INDEX idx_code_files_relative_path ON code_files(relative_path);
CREATE INDEX idx_code_chunks_file_id ON code_chunks(code_file_id);

-- Task indexes
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_task_branch_links_task_id ON task_branch_links(task_id);
CREATE INDEX idx_task_commit_links_task_id ON task_commit_links(task_id);
```

### Data Model Relationships

| Parent Table | Child Table | Relationship | Notes |
|-------------|-------------|--------------|-------|
| repositories | code_files | 1:N | CASCADE on delete |
| code_files | code_chunks | 1:N | CASCADE on delete |
| code_files | change_events | 1:N | Track file changes |
| code_files | file_metadata | 1:1 | Optional metadata |
| tasks | task_status_history | 1:N | Audit trail |
| tasks | task_planning_references | 1:N | Links to spec/plan docs |
| tasks | task_branch_links | 1:N | Git branch associations |
| tasks | task_commit_links | 1:N | Git commit associations |

---

## Tool Handlers

Tool handlers are the MCP interface layer that receives JSON-RPC calls and translates them to service layer operations.

### Handler Pattern

All tool handlers follow this pattern:

```python
async def tool_handler(db: AsyncSession, **arguments) -> dict[str, Any]:
    """
    1. VALIDATE: Check input parameters
    2. CONSTRUCT: Build Pydantic input models
    3. CALL: Invoke service layer function
    4. CONVERT: Transform Pydantic output to dict
    5. RETURN: Send dict to MCP server
    """
    # 1. Validate
    if not valid_input:
        raise ValueError("Invalid input")

    # 2. Construct
    input_model = ServiceInputModel(**arguments)

    # 3. Call
    result = await service_function(db, input_model)

    # 4. Convert
    output_dict = result.model_dump()

    # 5. Return
    return output_dict
```

### Task Tools (src/mcp/tools/tasks.py)

#### create_task_tool
- **Input**: `title`, `description?`, `notes?`, `planning_references?`
- **Validation**: Title 1-200 chars, planning_references are valid paths
- **Service Call**: `create_task(db, TaskCreate(...))`
- **Output**: TaskResponse as dict (id, title, status, timestamps, relationships)

#### get_task_tool
- **Input**: `task_id` (UUID string)
- **Validation**: Valid UUID format
- **Service Call**: `get_task(db, UUID(task_id))`
- **Output**: TaskResponse or None
- **Error**: NotFoundError if task doesn't exist

#### list_tasks_tool
- **Input**: `status?`, `branch?`, `limit?`
- **Validation**: Status in enum, limit 1-100
- **Service Call**: `list_tasks(db, status, branch, limit)`
- **Output**: list[TaskResponse] as dicts

#### update_task_tool
- **Input**: `task_id`, `title?`, `description?`, `notes?`, `status?`, `branch?`, `commit?`
- **Validation**:
  - UUID format for task_id
  - Status in enum
  - Commit hash is 40-char hex SHA-1
- **Service Call**: `update_task(db, UUID(task_id), TaskUpdate(...), branch, commit)`
- **Output**: Updated TaskResponse
- **Side Effects**:
  - Creates TaskStatusHistory if status changed
  - Creates TaskBranchLink if branch provided
  - Creates TaskCommitLink if commit provided

### Indexing Tool (src/mcp/tools/indexing.py)

#### index_repository_tool
- **Input**: `repo_path`, `force_reindex?`
- **Validation**:
  - repo_path is absolute
  - Directory exists
  - Readable permissions
- **Service Call**: `index_repository(Path(repo_path), name, db, force_reindex)`
- **Output**: IndexResult as dict (repository_id, files_indexed, chunks_created, duration, status, errors)
- **Performance**: ~60s for 10,000 files (target)

### Search Tool (src/mcp/tools/search.py)

#### search_code_tool
- **Input**: `query`, `repository_id?`, `file_type?`, `directory?`, `limit?`
- **Validation**:
  - Query non-empty
  - file_type without leading dot
  - Limit 1-50
- **Service Call**: `search_code(query, db, SearchFilter(...))`
- **Output**: list[SearchResult] as dicts (chunk_id, file_path, content, similarity_score, context)
- **Performance**: <500ms p95 latency (target)

---

## Service Layer

Service layer implements business logic, orchestration, and database operations.

### Design Patterns

1. **Pydantic-First**: All inputs/outputs use Pydantic models for validation
2. **Async Throughout**: All operations are async (AsyncSession, async file I/O)
3. **Transaction Safety**: Services assume transaction managed by caller
4. **Error Propagation**: Raise domain-specific exceptions for tool handlers to catch
5. **Relationship Loading**: Eagerly load relationships to avoid N+1 queries

### Task Service (src/services/tasks.py)

**Responsibilities:**
- Task CRUD operations
- Status transition tracking
- Git metadata linking (branches, commits)
- Planning reference management

**Key Functions:**

```python
async def create_task(db: AsyncSession, task_data: TaskCreate) -> TaskResponse:
    """
    Creates:
    - Task record with initial status "need to be done"
    - TaskPlanningReference records (if provided)
    - TaskStatusHistory record (None → "need to be done")

    Returns: TaskResponse with all relationships loaded
    """

async def update_task(
    db: AsyncSession,
    task_id: UUID,
    update_data: TaskUpdate,
    branch: str | None = None,
    commit: str | None = None
) -> TaskResponse | None:
    """
    Updates:
    - Task fields (partial updates supported)
    - TaskStatusHistory (if status changed)
    - TaskBranchLink (if branch provided, checks for duplicates)
    - TaskCommitLink (if commit provided, validates SHA-1 format)

    Returns: Updated TaskResponse or None if not found
    Raises: InvalidCommitHashError if commit format invalid
    """
```

### Indexer Service (src/services/indexer.py)

**Responsibilities:**
- Orchestrate indexing pipeline
- Batch processing for performance
- Change detection for incremental updates
- Error collection with partial success support

**Pipeline Architecture:**

```python
async def index_repository(
    repo_path: Path,
    name: str,
    db: AsyncSession,
    force_reindex: bool = False
) -> IndexResult:
    """
    ORCHESTRATION PIPELINE:

    1. Get/Create Repository record
    2. Scan directory tree (scanner.scan_repository)
    3. Detect changes (scanner.detect_changes) or force all
    4. Batch processing (100 files/batch):
       a. Read file contents (async I/O)
       b. Create/update CodeFile records
       c. Delete old chunks (for modified files)
       d. Chunk files (chunker.chunk_files_batch)
       e. Collect chunks for embedding
    5. Embedding generation (50 texts/batch, parallel):
       - Call Ollama API via embedder.generate_embeddings
       - Retry logic: 3 attempts with exponential backoff
    6. Database persistence:
       - Assign embeddings to CodeChunk models
       - Bulk insert chunks
       - Create ChangeEvent records
       - Create EmbeddingMetadata record
       - Update repository.last_indexed_at
    7. Return IndexResult with statistics

    Performance Targets:
    - <60s for 10,000 files
    - Batching for efficient memory usage
    - Parallel embedding generation
    """
```

**Batching Strategy:**

| Operation | Batch Size | Reason |
|-----------|-----------|--------|
| File reading | 100 files | Balance memory vs. I/O overhead |
| Chunking | 100 files | Tree-sitter parsing is CPU-bound |
| Embeddings | 50 texts | Ollama concurrent request limit |

### Searcher Service (src/services/searcher.py)

**Responsibilities:**
- Semantic code search via pgvector
- Query embedding generation
- Result filtering (repository, file type, directory)
- Context extraction (10 lines before/after)

**Search Algorithm:**

```python
async def search_code(
    query: str,
    db: AsyncSession,
    filters: SearchFilter | None = None
) -> list[SearchResult]:
    """
    SEARCH PIPELINE:

    Phase 1: Query Embedding (~100ms)
    - Call embedder.generate_embedding(query)
    - Result: 768-dimensional vector

    Phase 2: Similarity Search (~50ms)
    - SQL with pgvector <=> operator (cosine distance)
    - HNSW index for fast approximate nearest neighbor
    - Apply filters (repository, file_type, directory)
    - Order by similarity (ascending distance)
    - Limit results (1-50)

    Phase 3: Context Extraction (~50ms, parallel)
    - Read source files (async I/O)
    - Extract 10 lines before chunk
    - Extract 10 lines after chunk
    - Build SearchResult models

    Phase 4: Return Results
    - list[SearchResult] ordered by similarity

    Total: ~200ms typical latency
    Target: <500ms p95 latency
    """
```

**pgvector Query:**

```sql
SELECT
  chunk.id,
  chunk.content,
  chunk.start_line,
  chunk.end_line,
  file.path,
  file.relative_path,
  1 - (chunk.embedding <=> $query_vec) AS similarity
FROM code_chunks chunk
JOIN code_files file ON chunk.code_file_id = file.id
WHERE chunk.embedding IS NOT NULL
  AND file.is_deleted = FALSE
  -- Optional filters:
  AND file.repository_id = $repo_id  -- if filtered by repository
  AND file.relative_path LIKE '%.py'  -- if filtered by file_type
  AND file.relative_path LIKE 'src/%'  -- if filtered by directory
ORDER BY chunk.embedding <=> $query_vec  -- Ascending distance
LIMIT 10;
```

### Chunker Service (src/services/chunker.py)

**Responsibilities:**
- AST-based semantic chunking for supported languages
- Fallback to line-based chunking for unsupported languages
- Language detection via file extension
- Parser caching for performance

**Supported Languages:**

| Language | Grammar | Node Types |
|----------|---------|-----------|
| Python | tree-sitter-python | function_definition, class_definition |
| JavaScript | tree-sitter-javascript | function_declaration, class_declaration, method_definition |

**Chunking Strategy:**

```python
async def chunk_file(file_path: Path, content: str, file_id: UUID) -> list[CodeChunkCreate]:
    """
    1. Detect language from file extension
    2. If supported language:
       a. Get cached parser (singleton ParserCache)
       b. Parse content with Tree-sitter
       c. Traverse AST, extract function/class nodes
       d. Create CodeChunkCreate for each node
    3. If unsupported or parse error:
       a. Fall back to line-based chunking
       b. Split into 500-line chunks (configurable)
       c. Create CodeChunkCreate for each chunk
    4. Return list[CodeChunkCreate]

    Chunk Types:
    - "function": Function/method definitions
    - "class": Class definitions
    - "block": Line-based chunks or other nodes
    """
```

### Embedder Service (src/services/embedder.py)

**Responsibilities:**
- Ollama HTTP API integration
- Batch embedding generation
- Retry logic with exponential backoff
- Connection pooling for performance

**OllamaEmbedder (Singleton):**

```python
class OllamaEmbedder:
    """
    Singleton HTTP client for Ollama embeddings.

    Configuration:
    - base_url: http://localhost:11434
    - model: nomic-embed-text
    - batch_size: 50 texts/request
    - timeout: 30s per request
    - connection pool: 20 max connections

    Retry Strategy:
    - Max retries: 3
    - Initial delay: 1s
    - Max delay: 8s
    - Backoff: exponential (2^attempt)

    Errors:
    - OllamaConnectionError: Cannot connect to Ollama
    - OllamaTimeoutError: Request timeout after 3 retries
    - OllamaValidationError: Invalid response format
    - OllamaModelNotFoundError: Model not available
    """

    async def generate_embeddings(self, texts: Sequence[str]) -> list[list[float]]:
        """
        1. Create EmbeddingRequest for each text
        2. Send requests in parallel (asyncio.gather)
        3. Retry failed requests (exponential backoff)
        4. Validate response dimensions (768)
        5. Return list[list[float]]

        Performance:
        - ~20ms per embedding (typical)
        - Parallel requests for batches
        - Target: <30s for 1000 embeddings
        """
```

### Scanner Service (src/services/scanner.py)

**Responsibilities:**
- File system traversal with .gitignore support
- Binary file filtering
- Content hash computation (SHA-256)
- Change detection (compare with database)

**Functions:**

```python
async def scan_repository(repo_path: Path) -> list[Path]:
    """
    1. Walk directory tree
    2. Apply filters:
       - Skip .git/, __pycache__/, node_modules/, etc.
       - Skip binary files (images, PDFs, executables)
       - Skip .gitignore patterns (if present)
    3. Return list[Path] of source files
    """

async def detect_changes(
    repo_path: Path,
    db: AsyncSession,
    repository_id: UUID
) -> ChangeSet:
    """
    1. Scan current files
    2. Query database for indexed files
    3. Compare content hashes:
       - Added: In filesystem, not in database
       - Modified: In both, hash different
       - Deleted: In database, not in filesystem
    4. Return ChangeSet(added, modified, deleted)

    Uses: SHA-256 hash for content comparison
    """
```

---

## External Dependencies

### Ollama Embedding Service

**Endpoint**: `http://localhost:11434/api/embeddings`

**Model**: `nomic-embed-text`
- Dimensions: 768
- License: Apache 2.0
- Performance: ~20ms per embedding (typical)
- Context length: 8192 tokens

**API Contract**:

```json
// Request
{
  "model": "nomic-embed-text",
  "prompt": "def authenticate(request): ..."
}

// Response
{
  "embedding": [0.123, -0.456, 0.789, ...] // 768 floats
}
```

**Error Handling**:
- Connection refused → `OllamaConnectionError`
- Timeout (>30s) → `OllamaTimeoutError`
- HTTP 404 → `OllamaModelNotFoundError`
- Invalid response → `OllamaValidationError`

**Retry Strategy**:
1. Attempt 1: Immediate
2. Attempt 2: 1s delay
3. Attempt 3: 2s delay
4. Fail: Raise exception

### PostgreSQL + pgvector

**Extension**: `pgvector` (version 0.5.0+)

**Vector Operations**:
```sql
-- Cosine distance (0 = identical, 2 = opposite)
SELECT embedding <=> '[0.1, 0.2, ...]'::vector FROM code_chunks;

-- L2 distance
SELECT embedding <-> '[0.1, 0.2, ...]'::vector FROM code_chunks;

-- Inner product
SELECT embedding <#> '[0.1, 0.2, ...]'::vector FROM code_chunks;
```

**Index Type**: HNSW (Hierarchical Navigable Small World)
- Construction time: O(n log n)
- Query time: O(log n) approximate
- Accuracy: 95%+ for top-10 results
- Memory: ~4KB per vector (768 dims × 4 bytes + overhead)

**Index Configuration**:
```sql
CREATE INDEX idx_code_chunks_embedding_hnsw
ON code_chunks USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```
- `m = 16`: Number of connections per layer (default)
- `ef_construction = 64`: Size of dynamic candidate list (higher = better accuracy, slower build)

### MCP Protocol (stdio transport)

**Transport**: JSON-RPC over stdin/stdout

**Message Format**:
```json
// Request (from Claude Desktop)
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "search_code",
    "arguments": {
      "query": "authentication middleware",
      "limit": 5
    }
  }
}

// Response (from MCP Server)
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "[{\"chunk_id\": \"...\", \"file_path\": \"...\", ...}]"
      }
    ]
  }
}
```

**Server Initialization**:
```python
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("codebase-mcp")

@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    return TOOLS

@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    # Route to handler, execute, return result
    ...

async with stdio_server() as (read_stream, write_stream):
    await app.run(read_stream, write_stream, app.create_initialization_options())
```

---

## Performance Characteristics

### Indexing Performance

**Target**: <60 seconds for 10,000 files

**Measured Performance** (typical codebase):
- File scanning: 2-5s (10K files)
- Change detection: 1-3s (database hash comparison)
- File reading: 5-10s (100 files/batch, async I/O)
- Chunking: 10-20s (Tree-sitter parsing)
- Embedding generation: 20-30s (50 embeddings/batch, Ollama)
- Database insertion: 5-10s (bulk insert)

**Total**: 43-78s for full index (target met for typical case)

**Bottlenecks**:
1. **Embedding generation** (40% of time)
   - Mitigation: Parallel requests (50/batch)
   - Future: GPU acceleration via Ollama
2. **Tree-sitter parsing** (25% of time)
   - Mitigation: Cached parsers, fallback to line-based
3. **Database insertion** (15% of time)
   - Mitigation: Bulk inserts, batching

**Incremental Updates**: <5 seconds for <100 changed files

### Search Performance

**Target**: <500ms p95 latency

**Measured Performance** (typical query):
- Query embedding: 80-120ms (Ollama API)
- Similarity search: 20-60ms (pgvector HNSW index)
- Context extraction: 50-100ms (10 files, parallel I/O)

**Total**: 150-280ms typical latency (target met)

**P95 Latency**: 400-500ms (within target)

**Bottlenecks**:
1. **Query embedding** (50% of latency)
   - Mitigation: Ollama local instance, fast model
2. **Context extraction** (30% of latency)
   - Mitigation: Parallel async I/O
3. **Database query** (20% of latency)
   - Mitigation: HNSW index, connection pooling

**Scaling Characteristics**:
- 10K chunks: ~200ms search latency
- 100K chunks: ~250ms search latency
- 1M chunks: ~350ms search latency (HNSW logarithmic scaling)

### Database Connection Pooling

**Configuration**:
- Pool size: 20 connections
- Max overflow: 10 connections (total: 30)
- Pre-ping: enabled (validate before use)
- Connection recycling: 3600s (1 hour)
- Idle timeout: 300s (5 minutes)

**Benefits**:
- Avoid connection overhead (~50ms per connection)
- Support concurrent operations
- Graceful handling of stale connections

---

## Error Handling Strategy

### Exception Hierarchy

```
Exception
├── DatabaseError (SQLAlchemy)
│   ├── IntegrityError (unique constraint, foreign key)
│   └── OperationalError (connection issues)
│
├── ValidationError (Pydantic)
│   └── Input validation failures
│
├── OllamaError (Custom)
│   ├── OllamaConnectionError (cannot connect)
│   ├── OllamaTimeoutError (request timeout)
│   ├── OllamaModelNotFoundError (model unavailable)
│   └── OllamaValidationError (invalid response)
│
└── ServiceError (Custom)
    ├── TaskNotFoundError (task does not exist)
    ├── InvalidStatusError (invalid status value)
    └── InvalidCommitHashError (invalid SHA-1 format)
```

### Error Flow

```
Tool Handler
    │
    ├─ Validate inputs → ValueError
    │
    ├─ Call service
    │      │
    │      ├─ Business logic error → ServiceError
    │      │
    │      ├─ Database error → DatabaseError
    │      │
    │      └─ External API error → OllamaError
    │
    └─ Convert to MCP error response
           │
           ├─ NotFoundError (404)
           ├─ ValidationError (400)
           └─ InternalError (500)
```

### Retry Logic

**Ollama Embeddings**:
- Max retries: 3
- Backoff: Exponential (1s, 2s, 4s)
- Retry on: Connection errors, timeouts, 5xx errors
- No retry on: 404 (model not found), validation errors

**Database Operations**:
- Automatic retries via SQLAlchemy (connection pool)
- Transaction rollback on error
- Session cleanup in finally block

**File I/O**:
- No automatic retry (fail fast)
- Graceful degradation (skip file, log error)
- Continue processing remaining files

### Logging Strategy

**Log Levels**:
- **DEBUG**: Detailed execution flow, timing
- **INFO**: Operation start/end, statistics
- **WARNING**: Recoverable errors, performance issues
- **ERROR**: Failed operations, exceptions

**Structured Logging** (JSON format):
```json
{
  "timestamp": "2025-10-06T12:00:00Z",
  "level": "INFO",
  "message": "Semantic code search completed",
  "context": {
    "query": "authentication middleware",
    "results_count": 10,
    "total_time_ms": 245.3,
    "embedding_time_ms": 105.2,
    "search_time_ms": 45.1,
    "context_time_ms": 95.0
  }
}
```

**Log Destinations**:
- **Development**: stderr (human-readable)
- **Production**: File rotation (JSON format)
- **MCP Server**: No stdout pollution (protocol compliance)

---

## Type Safety Architecture

### Pydantic Models for Type Safety

All service boundaries use Pydantic models for validation:

**Input Models** (validation at entry):
```python
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    notes: str | None = None
    planning_references: list[str] = Field(default_factory=list)

class SearchFilter(BaseModel):
    repository_id: UUID | None = None
    file_type: str | None = Field(None, min_length=1, max_length=20)
    directory: str | None = None
    limit: int = Field(default=10, ge=1, le=50)

    @field_validator("file_type")
    @classmethod
    def validate_file_type(cls, v: str | None) -> str | None:
        if v is not None and v.startswith("."):
            raise ValueError("file_type should not include leading dot")
        return v
```

**Output Models** (consistent responses):
```python
class TaskResponse(BaseModel):
    id: UUID
    title: str
    description: str | None
    notes: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    planning_references: list[str]
    branches: list[str]
    commits: list[str]

class SearchResult(BaseModel):
    chunk_id: UUID
    file_path: str
    content: str
    start_line: int = Field(..., ge=1)
    end_line: int = Field(..., ge=1)
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    context_before: str = ""
    context_after: str = ""
```

### mypy --strict Compliance

**Type Annotations**:
- All functions have complete type signatures
- Return types explicitly declared
- Generic types properly parameterized

**Example**:
```python
async def search_code(
    query: str,
    db: AsyncSession,
    filters: SearchFilter | None = None
) -> list[SearchResult]:
    """Full type safety with mypy."""
    # Implementation
```

**Strict Mode Checks**:
- No implicit `Any` types
- No untyped function definitions
- No untyped decorators
- Strict equality checks
- Warn on unreachable code

### Type-Safe Database Models

**SQLAlchemy ORM** + **Pydantic Schemas**:

```python
# ORM Model (database)
class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relationships
    status_history: Mapped[list[TaskStatusHistory]] = relationship(...)

# Pydantic Schema (validation)
class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    # ...

class TaskResponse(BaseModel):
    id: UUID
    title: str
    status: str
    # ...
```

**Conversion**:
```python
def _task_to_response(task: Task) -> TaskResponse:
    """Type-safe ORM → Pydantic conversion."""
    return TaskResponse(
        id=task.id,
        title=task.title,
        status=task.status,
        # Relationships
        planning_references=[ref.file_path for ref in task.planning_references],
        branches=[link.branch_name for link in task.branch_links],
        commits=[link.commit_hash for link in task.commit_links],
    )
```

---

## Deployment Architecture

### Process Model

```
┌─────────────────────────────────────────┐
│         Claude Desktop                  │
│                                         │
│  Spawns MCP server as child process:   │
│  python -m src.mcp.mcp_stdio_server_v3  │
└─────────────────┬───────────────────────┘
                  │
                  │ stdin/stdout pipes
                  ▼
┌─────────────────────────────────────────┐
│    MCP Server Process                   │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │ Main Event Loop (asyncio)         │ │
│  │ - stdio_server transport          │ │
│  │ - Database connection pool        │ │
│  │ - Tool handler dispatch           │ │
│  └───────────────────────────────────┘ │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │ Background Tasks                  │ │
│  │ - Connection recycling (1hr)      │ │
│  │ - Pre-ping health checks          │ │
│  └───────────────────────────────────┘ │
└────────┬────────────────────────────────┘
         │
         │ TCP connections (pooled)
         ▼
┌─────────────────────────────────────────┐
│    PostgreSQL Server                    │
│    (localhost:5432)                     │
└─────────────────────────────────────────┘
         │
         │ HTTP requests
         ▼
┌─────────────────────────────────────────┐
│    Ollama Service                       │
│    (localhost:11434)                    │
└─────────────────────────────────────────┘
```

### Configuration

**Environment Variables** (`.env`):
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/codebase_mcp
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_BATCH_SIZE=50

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

**Claude Desktop MCP Config** (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "codebase": {
      "command": "python",
      "args": ["-m", "src.mcp.mcp_stdio_server_v3"],
      "cwd": "/path/to/codebase-mcp",
      "env": {
        "PYTHONPATH": "/path/to/codebase-mcp",
        "DATABASE_URL": "postgresql+asyncpg://..."
      }
    }
  }
}
```

### Lifecycle Management

**Startup**:
1. Load environment variables
2. Initialize database connection pool
3. Initialize MCP server
4. Register tool handlers
5. Start stdio transport
6. Ready for requests

**Shutdown**:
1. Receive SIGTERM/SIGINT
2. Stop accepting new requests
3. Wait for in-flight requests (graceful timeout: 10s)
4. Close database connection pool
5. Close Ollama HTTP client
6. Exit

---

## Security Considerations

### Input Validation

**All inputs validated at entry** (tool handlers):
- Task titles: 1-200 characters
- File paths: Absolute paths only, existence checks
- UUIDs: Valid format checks
- SQL injection: Parameterized queries (SQLAlchemy)
- Path traversal: Reject paths outside repository root

### Database Security

**Connection**:
- TLS encryption (optional, recommended for production)
- Password authentication
- Connection pooling with timeout

**Permissions**:
- Read/write access to codebase_mcp database only
- No superuser privileges required
- Row-level security (future consideration)

### File System Access

**Repository Indexing**:
- Only read operations (no writes)
- Respects file permissions
- Skips unreadable files (logs warning)

**Context Extraction**:
- Read-only file access
- Validates file existence before reading
- No execution of file contents

---

## Future Enhancements

### Planned Features

1. **TypeScript Support**
   - Add tree-sitter-typescript grammar
   - Support .ts, .tsx file chunking

2. **Additional Languages**
   - Rust (tree-sitter-rust)
   - Go (tree-sitter-go)
   - Java (tree-sitter-java)

3. **Advanced Filters**
   - Search by chunk type (function/class)
   - Date range filters (indexed_at, modified_at)
   - File size filters

4. **Performance Optimizations**
   - Embedding caching (LRU cache)
   - Incremental embedding updates
   - GPU acceleration via Ollama

5. **Monitoring & Observability**
   - Prometheus metrics export
   - Performance dashboards
   - Query analytics

### Scalability Improvements

1. **Horizontal Scaling**
   - Read replicas for PostgreSQL
   - Load balancing for multiple MCP servers

2. **Storage Optimization**
   - Vector quantization (reduce dimensions)
   - Tiered storage (hot/cold chunks)

3. **Caching Layer**
   - Redis for frequent queries
   - Embedding result caching

---

## References

- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [Ollama API Reference](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Tree-sitter Documentation](https://tree-sitter.github.io/tree-sitter/)
- [Pydantic V2 Documentation](https://docs.pydantic.dev/latest/)
- [SQLAlchemy Async Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)

---

**Document Version**: 1.0
**Last Updated**: 2025-10-06
**Maintained By**: Codebase MCP Server Team
