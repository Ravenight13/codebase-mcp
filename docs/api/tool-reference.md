# API Reference

This document provides detailed API reference for the codebase-mcp server's MCP tools. The v2.0 architecture simplifies the API surface to exactly 2 tools focused exclusively on semantic code search.

> **Breaking Change**: codebase-mcp v2.0 reduces the API from 16 tools to 2 tools. The 14 removed tools (project management, entity management, work item tracking) have been removed to focus exclusively on the core semantic search capability. See the [Migration Guide](../migration/v1-to-v2-migration.md) for upgrade details and removed tool reference.

---

## index_repository

Index a code repository for semantic search with multi-project workspace isolation.

Orchestrates the complete repository indexing workflow including file scanning, code chunking, embedding generation via Ollama, and storage in PostgreSQL with pgvector. Supports optional project workspace isolation for multi-tenant deployments and force re-indexing for schema updates or corruption recovery.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| repo_path | string | Yes | *(none)* | Absolute path to repository directory |
| project_id | string | No | `"default"` | Project workspace identifier for data isolation |
| force_reindex | boolean | No | `false` | Force full re-index even if already indexed |

### Parameter details

#### repo_path

The absolute path to the code repository directory to index.

**Requirements**:
- Must be an absolute path (not relative)
- Path must exist on the filesystem
- Path must be a directory (not a file)
- Directory must be readable by the codebase-mcp process

**Validation behavior**:
- Empty or whitespace-only paths are rejected with `ValueError`
- Relative paths are rejected with error: "Repository path must be absolute"
- Non-existent paths are rejected with error: "Repository path does not exist"
- File paths (not directories) are rejected with error: "Repository path must be a directory"

**Example valid paths**:
- `/Users/username/projects/my-app`
- `/home/developer/repos/backend-service`
- `/opt/repositories/client-project`

#### project_id

Optional project workspace identifier for multi-project workspace isolation.

**Default behavior**: When `project_id` is not provided or is `null`, the tool uses the default workspace with database schema `project_default`. All operations without explicit project context are isolated to this default workspace.

**Multi-project behavior**: When `project_id` is provided, the tool creates or uses an isolated database schema for that project (format: `project_{identifier}`). Each project workspace maintains separate repositories, chunks, and embeddings with complete data isolation.

**workflow-mcp auto-resolution (optional)**: If the `WORKFLOW_MCP_URL` environment variable is configured, the tool attempts to resolve the active project ID automatically from workflow-mcp. This provides seamless integration with workflow-mcp's project context management. If workflow-mcp is unavailable or times out, the tool falls back to the default workspace.

**Sanitization rules**: Project identifiers must use alphanumeric characters and underscores only. Hyphens in project IDs are automatically converted to underscores in database schema names. Maximum length: 50 characters.

**Example project IDs**:
- `"client-a"` → schema name: `project_client_a`
- `"my_app"` → schema name: `project_my_app`
- `"backend-service-v2"` → schema name: `project_backend_service_v2`

#### force_reindex

Force complete re-indexing even if the repository is already indexed.

**When to use**:
- **Schema changes**: Database schema has been upgraded and existing data needs to be regenerated
- **Corruption recovery**: Existing index data is corrupted or inconsistent
- **Configuration changes**: Embedding model or chunking strategy has changed
- **Testing**: Validating indexing performance or behavior

**Default behavior (`false`)**: The tool performs incremental indexing, skipping files and chunks that are already indexed and unchanged. This is the recommended setting for most use cases.

**Force reindex behavior (`true`)**: The tool deletes all existing chunks for the repository and re-indexes all files from scratch, regardless of previous indexing state.

**Performance impact**: Force re-indexing a large repository (10,000+ files) can take 60+ seconds. Use this option only when necessary.

### Return value

Returns a JSON object with indexing operation results and metadata.

#### Schema

```json
{
  "repository_id": "string (UUID)",
  "files_indexed": 1234,
  "chunks_created": 5678,
  "duration_seconds": 45.2,
  "project_id": "client-a",
  "schema_name": "project_client_a",
  "status": "success"
}
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| repository_id | string (UUID) | Unique identifier for the indexed repository (UUIDv4 format) |
| files_indexed | integer | Total number of files successfully indexed during operation |
| chunks_created | integer | Total number of code chunks created from indexed files |
| duration_seconds | float | Total indexing duration in seconds (includes scanning, chunking, embedding) |
| project_id | string or null | Project workspace identifier used for operation (null if default workspace) |
| schema_name | string | PostgreSQL schema name used for data storage (e.g., "project_client_a" or "project_default") |
| status | string | Operation status: "success" (all files indexed), "partial" (some files failed), or "failed" (critical failure) |
| errors | array of strings | List of error messages (only present if status is "partial" or "failed") |

**Status values**:
- **"success"**: All files indexed successfully with no errors
- **"partial"**: Some files indexed successfully, but some files failed (errors array contains details)
- **"failed"**: Critical failure prevented indexing (errors array contains failure reason)

### Examples

#### Basic usage (default project)

Index a repository using the default workspace without explicit project context.

**Input**:
```json
{
  "repo_path": "/Users/developer/projects/my-app"
}
```

**Output**:
```json
{
  "repository_id": "550e8400-e29b-41d4-a716-446655440000",
  "files_indexed": 1234,
  "chunks_created": 5678,
  "duration_seconds": 45.2,
  "project_id": null,
  "schema_name": "project_default",
  "status": "success"
}
```

#### Multi-project usage

Index a repository into a specific project workspace for data isolation.

**Input**:
```json
{
  "repo_path": "/Users/developer/projects/client-backend",
  "project_id": "client-a"
}
```

**Output**:
```json
{
  "repository_id": "770e8400-e29b-41d4-a716-446655440001",
  "files_indexed": 2456,
  "chunks_created": 8921,
  "duration_seconds": 52.7,
  "project_id": "client-a",
  "schema_name": "project_client_a",
  "status": "success"
}
```

#### Force re-index

Force complete re-indexing of a previously indexed repository.

**Input**:
```json
{
  "repo_path": "/Users/developer/projects/legacy-app",
  "force_reindex": true
}
```

**Output**:
```json
{
  "repository_id": "660e8400-e29b-41d4-a716-446655440002",
  "files_indexed": 892,
  "chunks_created": 3421,
  "duration_seconds": 28.4,
  "project_id": null,
  "schema_name": "project_default",
  "status": "success"
}
```

#### Partial failure example

Indexing completes with some files failing (e.g., binary files, permission errors).

**Output**:
```json
{
  "repository_id": "440e8400-e29b-41d4-a716-446655440003",
  "files_indexed": 1150,
  "chunks_created": 5234,
  "duration_seconds": 41.8,
  "project_id": null,
  "schema_name": "project_default",
  "status": "partial",
  "errors": [
    "Failed to process /path/to/binary.exe: Binary file not supported",
    "Failed to process /path/to/large.json: File exceeds size limit"
  ]
}
```

### Error handling

The tool returns structured error responses following MCP protocol conventions.

| Error Code | Condition | Description |
|------------|-----------|-------------|
| VALIDATION_ERROR | Invalid repo_path | Path does not exist, is not absolute, or is not a directory |
| VALIDATION_ERROR | Invalid project_id | Project ID contains non-alphanumeric characters (except underscore) or exceeds 50 characters |
| DATABASE_ERROR | Connection failed | PostgreSQL connection unavailable or database operation failed |
| INDEXING_ERROR | Partial failure | Some files failed to index (returned as "partial" status with errors array) |
| RUNTIME_ERROR | Critical failure | Indexing operation failed critically (e.g., Ollama unavailable, schema corruption) |

**Error response format**:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Repository path must be absolute: relative/path/to/repo"
  }
}
```

**Common error scenarios**:

1. **Relative path provided**:
   - Error: "Repository path must be absolute: relative/path"
   - Resolution: Provide absolute path starting with `/` (Unix) or drive letter (Windows)

2. **Path does not exist**:
   - Error: "Repository path does not exist: /nonexistent/path"
   - Resolution: Verify path is correct and accessible

3. **Invalid project ID**:
   - Error: "Invalid project_id format: Project identifier must be alphanumeric with underscores/hyphens"
   - Resolution: Use only alphanumeric characters, hyphens, and underscores in project ID

4. **PostgreSQL unavailable**:
   - Error: "Failed to index repository: Database connection failed"
   - Resolution: Verify `DATABASE_URL` environment variable and PostgreSQL server status

5. **Ollama unavailable**:
   - Error: "Failed to index repository: Embedding generation failed"
   - Resolution: Verify Ollama is running and `OLLAMA_BASE_URL` is correct

### Performance characteristics

**Target performance** (Constitutional Principle IV):
- **Indexing speed**: <60 seconds for 10,000 files
- **Batch processing**: Files processed in batches of 100
- **Embedding batching**: Text chunks embedded in batches of 50 (configurable via `EMBEDDING_BATCH_SIZE`)

**Actual performance varies by**:
- Repository size (file count and total size)
- Hardware (CPU, disk I/O, network for Ollama)
- PostgreSQL configuration (connection pool size, shared_buffers)
- Ollama model performance (nomic-embed-text is default)

**Performance monitoring**: Duration exceeding target triggers warning log entry for investigation.

**Optimization tips**:
- Use SSD storage for repository and PostgreSQL
- Tune `EMBEDDING_BATCH_SIZE` (default: 50, range: 1-1000)
- Increase `DB_POOL_SIZE` for concurrent operations (default: 20)
- Configure PostgreSQL `shared_buffers` and `work_mem` appropriately

---

## search_code

Perform semantic code search across indexed repositories using natural language queries with multi-project workspace isolation.

Uses embeddings and pgvector similarity matching to find code chunks semantically similar to the search query. Supports filtering by repository, file type, and directory path for precise results. Performance target: <500ms p95 latency.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| query | string | Yes | *(none)* | Natural language search query |
| project_id | string | No | `"default"` | Project workspace to search |
| repository_id | string (UUID) | No | *(none)* | Filter by specific repository |
| file_type | string | No | *(none)* | File extension filter (e.g., "py", "js") |
| directory | string | No | *(none)* | Directory path filter (supports wildcards) |
| limit | integer | No | `10` | Maximum results (1-50) |

### Parameter details

#### query

Natural language search query describing the code to find. The query is converted to an embedding vector using the same model as indexed code, then matched against stored chunk embeddings using cosine similarity.

**Natural language support**: Queries support plain English descriptions like "authentication function", "JSON parser", "database connection logic". The semantic search understands intent and context, not just keywords.

**Semantic similarity matching**: Unlike keyword search, semantic search finds code conceptually similar to your query even if exact terms don't match. For example, "user login" matches code containing "authenticate", "sign in", "credentials".

**Best practices**:
- Be specific: "function that validates email addresses" vs. "email"
- Include technical context: "React component for authentication" vs. "component"
- Use domain terminology: "async handler", "REST endpoint", "SQL query"

**Validation**:
- Cannot be empty or whitespace-only
- Maximum length: 500 characters
- Trimmed before processing

#### project_id

Optional project workspace identifier for multi-project workspace isolation.

**Default behavior**: When `project_id` is not provided or is `null`, the tool searches the default workspace with database schema `project_default`. All operations without explicit project context search this default workspace.

**Multi-project behavior**: When `project_id` is provided, the tool searches an isolated database schema for that project (format: `project_{identifier}`). Each project workspace maintains separate repositories, chunks, and embeddings with complete data isolation - no cross-project search capability.

**workflow-mcp auto-resolution (optional)**: If the `WORKFLOW_MCP_URL` environment variable is configured, the tool attempts to resolve the active project ID automatically from workflow-mcp. This provides seamless integration with workflow-mcp's project context management. If workflow-mcp is unavailable or times out, the tool falls back to the default workspace.

**Sanitization rules**: Project identifiers must use alphanumeric characters and underscores only. Hyphens in project IDs are automatically converted to underscores in database schema names. Maximum length: 50 characters.

**Example project IDs**:
- `"client-a"` → searches schema: `project_client_a`
- `"my_app"` → searches schema: `project_my_app`
- `"frontend-v2"` → searches schema: `project_frontend_v2`

#### repository_id

Optional UUID string to filter search results to a specific repository.

**Use cases**:
- Search within a specific codebase when multiple repositories are indexed in the same project
- Narrow search scope for better precision
- Isolate search to a known repository

**Obtaining repository_id**: The `repository_id` is returned by the `index_repository` tool in the `repository_id` field. Each indexed repository receives a unique UUID that persists across re-indexing (same repo path = same repository_id).

**Format**: UUID string (e.g., `"550e8400-e29b-41d4-a716-446655440000"`). Validated as proper UUID format.

**Behavior**: When provided, only chunks from the specified repository are searched. When omitted (null), all repositories in the project workspace are searched.

#### file_type

Optional file extension filter to limit search results to specific file types.

**Format**:
- Extension without leading dot: `"py"`, `"js"`, `"md"` (not `".py"`, `".js"`, `".md"`)
- Case-insensitive: `"py"` matches `.py`, `.PY`, `.Py`
- Single extension only (no comma-separated lists)

**Common file types**:
- Python: `"py"`
- JavaScript: `"js"`
- TypeScript: `"ts"`, `"tsx"`
- Go: `"go"`
- Rust: `"rs"`
- Java: `"java"`
- Markdown: `"md"`
- YAML: `"yaml"`, `"yml"`
- JSON: `"json"`

**Use cases**:
- Find Python functions only: `file_type="py"`
- Search TypeScript components: `file_type="tsx"`
- Locate configuration files: `file_type="yaml"`

**Validation**: Rejects file_type with leading dot (e.g., `".py"`) - use `"py"` instead.

#### directory

Optional directory path filter to limit search results to files within a specific directory.

**Format**:
- Relative path from repository root: `"src/auth"`, `"lib/parsers"`
- No leading slash (use `"src"` not `"/src"`)
- Case-sensitive path matching
- Supports wildcards: `"src/*"` matches all subdirectories under `src/`

**Use cases**:
- Search within a module: `directory="src/auth"`
- Search across multiple modules: `directory="src/*"`
- Focus on specific codebase area: `directory="backend/api"`

**Behavior**: Matches file paths starting with the directory prefix. Supports wildcard patterns for flexible matching. Empty string or null means no directory filtering (search all directories).

#### limit

Maximum number of search results to return. Results are ordered by similarity score descending (best matches first).

**Range**:
- Minimum: `1`
- Maximum: `50`
- Default: `10`

**Behavior**:
- If total matches exceed limit, only top N results returned
- `total_count` field shows actual number of matches (may exceed limit)
- Results always ordered by similarity score (highest first)

**Use cases**:
- Quick preview: `limit=5`
- Standard search: `limit=10` (default)
- Comprehensive results: `limit=50`

**Performance**: Larger limits may increase query latency. Target latency (<500ms p95) tested with default limit of 10.

### Return value

Returns a JSON object with search results, metadata, and performance metrics.

#### Schema

```json
{
  "results": [
    {
      "chunk_id": "string (UUID)",
      "file_path": "string",
      "content": "string",
      "start_line": 42,
      "end_line": 58,
      "similarity_score": 0.95,
      "context_before": "string",
      "context_after": "string"
    }
  ],
  "total_count": 1,
  "project_id": "string or null",
  "schema_name": "string",
  "latency_ms": 285.3
}
```

#### Fields

| Field | Type | Description |
|-------|------|-------------|
| results | array | Array of result objects (see Result Object structure below) |
| total_count | integer | Total matching chunks found (may exceed limit parameter) |
| project_id | string or null | Project workspace searched (null if default workspace) |
| schema_name | string | PostgreSQL schema name searched (e.g., "project_client_a" or "project_default") |
| latency_ms | float | Query execution time in milliseconds (includes embedding generation and search) |

#### Result Object structure

Each object in the `results` array contains:

| Field | Type | Description |
|-------|------|-------------|
| chunk_id | string (UUID) | Unique identifier for this code chunk |
| file_path | string | Relative path to file from repository root |
| content | string | Code snippet matching the query |
| start_line | integer | Starting line number in file (1-indexed) |
| end_line | integer | Ending line number in file (1-indexed) |
| similarity_score | float (0-1) | Semantic similarity score (higher = better match, see interpretation below) |
| context_before | string | Lines immediately before the chunk (for context) |
| context_after | string | Lines immediately after the chunk (for context) |

#### Similarity score interpretation

Results are ordered by similarity score descending (best matches first). Typical score ranges:

- **0.90 - 1.00**: Excellent match (highly relevant)
- **0.80 - 0.89**: Good match (relevant)
- **0.70 - 0.79**: Fair match (somewhat relevant)
- **0.60 - 0.69**: Weak match (may be tangentially relevant)
- **< 0.60**: Poor match (likely not relevant)

**Note**: Absolute score values depend on embedding model quality and query specificity. Focus on relative ranking rather than absolute thresholds.

### Examples

#### Basic search (default project)

Search for authentication-related code in the default workspace.

**Input**:
```json
{
  "query": "authentication function"
}
```

**Output**:
```json
{
  "results": [
    {
      "chunk_id": "880e8400-e29b-41d4-a716-446655440003",
      "file_path": "src/auth.py",
      "content": "def authenticate(user, password):\n    \"\"\"Authenticate user with password.\"\"\"\n    if not user or not password:\n        return False\n    hashed = hashlib.sha256(password.encode()).hexdigest()\n    return hashed == user.password_hash",
      "start_line": 42,
      "end_line": 48,
      "similarity_score": 0.95,
      "context_before": "# User authentication module\nimport hashlib\n\n",
      "context_after": "\n\ndef logout(user):\n    user.session.clear()"
    }
  ],
  "total_count": 1,
  "project_id": null,
  "schema_name": "project_default",
  "latency_ms": 285.3
}
```

#### Multi-project search

Search for database connection logic within a specific project workspace.

**Input**:
```json
{
  "query": "database connection",
  "project_id": "my-project"
}
```

**Output**:
```json
{
  "results": [
    {
      "chunk_id": "990e8400-e29b-41d4-a716-446655440004",
      "file_path": "lib/db.py",
      "content": "def connect_to_database(config):\n    \"\"\"Establish database connection.\"\"\"\n    conn = psycopg2.connect(\n        host=config['host'],\n        port=config['port'],\n        database=config['database'],\n        user=config['user'],\n        password=config['password']\n    )\n    return conn",
      "start_line": 15,
      "end_line": 25,
      "similarity_score": 0.92,
      "context_before": "import psycopg2\nfrom typing import Dict\n\n",
      "context_after": "\n\ndef close_connection(conn):\n    conn.close()"
    }
  ],
  "total_count": 1,
  "project_id": "my-project",
  "schema_name": "project_my_project",
  "latency_ms": 312.7
}
```

#### Filtered search

Search for JSON parsing code with multiple filters applied.

**Input**:
```json
{
  "query": "parse JSON",
  "file_type": "py",
  "directory": "src/parsers",
  "limit": 5
}
```

**Output**:
```json
{
  "results": [
    {
      "chunk_id": "aa0e8400-e29b-41d4-a716-446655440005",
      "file_path": "src/parsers/json_parser.py",
      "content": "def parse_json_file(file_path):\n    \"\"\"Parse JSON file and return dict.\"\"\"\n    with open(file_path, 'r') as f:\n        data = json.load(f)\n    return data",
      "start_line": 8,
      "end_line": 13,
      "similarity_score": 0.94,
      "context_before": "import json\nfrom pathlib import Path\n\n",
      "context_after": "\n\ndef validate_json_schema(data, schema):"
    },
    {
      "chunk_id": "bb0e8400-e29b-41d4-a716-446655440006",
      "file_path": "src/parsers/config_parser.py",
      "content": "def parse_config(content):\n    \"\"\"Parse JSON configuration string.\"\"\"\n    config = json.loads(content)\n    return config",
      "start_line": 22,
      "end_line": 26,
      "similarity_score": 0.88,
      "context_before": "import json\n\n",
      "context_after": "\n\ndef apply_config(config):\n    settings.update(config)"
    }
  ],
  "total_count": 8,
  "project_id": null,
  "schema_name": "project_default",
  "latency_ms": 198.5
}
```

#### No results found

Search query with no matching code chunks.

**Input**:
```json
{
  "query": "quantum entanglement algorithm"
}
```

**Output**:
```json
{
  "results": [],
  "total_count": 0,
  "project_id": null,
  "schema_name": "project_default",
  "latency_ms": 145.2
}
```

### Error handling

The tool returns structured error responses following MCP protocol conventions.

| Error Code | Condition | Description |
|------------|-----------|-------------|
| VALIDATION_ERROR | Empty query | Query is empty or whitespace-only |
| VALIDATION_ERROR | Query too long | Query exceeds 500 characters |
| VALIDATION_ERROR | Invalid limit | Limit outside range 1-50 |
| VALIDATION_ERROR | Invalid project_id | Project ID format invalid (non-alphanumeric, too long, etc.) |
| VALIDATION_ERROR | Invalid repository_id | Repository ID is not a valid UUID |
| VALIDATION_ERROR | Invalid file_type | File type includes leading dot (use "py" not ".py") |
| PROJECT_NOT_FOUND | Unknown project_id | Project has not been indexed or does not exist |
| DATABASE_ERROR | Connection failed | PostgreSQL database unavailable |
| DATABASE_ERROR | Schema not found | Project database does not exist (project not initialized) |
| EMBEDDING_ERROR | Ollama unavailable | Cannot generate query embedding for semantic search |

**Error response format**:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Limit must be between 1 and 50, got 100"
  }
}
```

**Common error scenarios**:

1. **Empty query**:
   - Error: "Search query cannot be empty"
   - Resolution: Provide a non-empty query string

2. **Invalid limit**:
   - Error: "Limit must be between 1 and 50, got 100"
   - Resolution: Use limit value between 1 and 50

3. **Invalid project ID**:
   - Error: "Invalid project_id: Project identifier must be alphanumeric with underscores/hyphens"
   - Resolution: Use only alphanumeric characters, hyphens, and underscores in project ID

4. **Project not found**:
   - Error: "Project has not been indexed or does not exist"
   - Resolution: Index repository using `index_repository` tool with the same project_id first

5. **PostgreSQL unavailable**:
   - Error: "PostgreSQL database unavailable"
   - Resolution: Verify `DATABASE_URL` environment variable and PostgreSQL server status

6. **Ollama unavailable**:
   - Error: "Cannot generate query embedding for semantic search"
   - Resolution: Verify Ollama is running and `OLLAMA_BASE_URL` is correct

### Performance characteristics

**Target performance** (Constitutional Principle IV):
- **Search latency**: <500ms p95 latency (includes embedding generation and search)

**Latency breakdown**:
- Query embedding generation: ~50-100ms (Ollama)
- PostgreSQL pgvector similarity search: ~100-200ms
- Result formatting: ~10-50ms
- **Total typical**: ~200-350ms, <500ms p95

**Actual performance varies by**:
- Query complexity and length
- Index size (chunk count in project database)
- Hardware (CPU, PostgreSQL performance)
- Ollama model performance (nomic-embed-text is default)
- Filter usage (repository_id, file_type, directory narrow search scope)

**Performance monitoring**: Latency exceeding 500ms target triggers warning log entry for investigation.

**Optimization tips**:
- Use filters (`repository_id`, `file_type`, `directory`) to narrow search scope
- Reduce `limit` parameter for faster queries
- Ensure PostgreSQL has sufficient resources (connection pool, shared_buffers)
- Monitor Ollama service health and response times
- Run `VACUUM ANALYZE` on PostgreSQL tables periodically

---

## Removed Tools

> **⚠️ Breaking Changes in v2.0**
>
> The codebase-mcp server v2.0 removed **14 MCP tools** that provided project management, entity management, and work item tracking capabilities. These tools were extracted to the separate **workflow-mcp** server as part of the architectural simplification focused on semantic code search (Constitutional Principle I: Simplicity Over Features).
>
> **Migration**: Users requiring these capabilities should install the **workflow-mcp** server alongside codebase-mcp. See the [Migration Guide](../migration/v1-to-v2-migration.md) for complete upgrade instructions and data preservation guidance.
>
> **Important**: These tools will **NOT** return in future releases. The codebase-mcp server focuses exclusively on semantic code search capabilities.

### Removed Project Management Tools (4 tools)

The following project management tools were removed in v2.0:

- ❌ **create_project** - Created a new project workspace with an isolated PostgreSQL database for organizing entities and work items in v1.x
- ❌ **switch_project** - Switched the active project context, scoping all subsequent entity and work item operations to the active project
- ❌ **get_active_project** - Retrieved the currently active project workspace metadata or returned null if no project was active
- ❌ **list_projects** - Listed all project workspaces with pagination support, ordered by creation date (newest first)

**Alternative**: Use [workflow-mcp](https://github.com/cyanheads/workflow-mcp) server for project workspace management.

### Removed Entity Management Tools (6 tools)

The following entity management tools were removed in v2.0:

- ❌ **register_entity_type** - Registered a new entity type with JSON Schema validation for storing arbitrary JSONB data with runtime type checking
- ❌ **create_entity** - Created a new entity instance with data validated against the registered entity type's JSON Schema, scoped to the active project
- ❌ **query_entities** - Queried entities with JSONB containment filters and tag matching, supporting complex filtering with GIN-indexed JSONB queries for sub-100ms performance
- ❌ **update_entity** - Updated entity data with optimistic locking via version numbers to prevent concurrent update conflicts, with JSON Schema validation
- ❌ **delete_entity** - Soft-deleted an entity by setting the `deleted_at` timestamp, requiring explicit confirmation to prevent accidental deletions
- ❌ **update_entity_type_schema** - Updated an entity type's JSON Schema with backward compatibility validation, automatically incrementing schema versions and optionally validating existing entities against the new schema

**Alternative**: Use [workflow-mcp](https://github.com/cyanheads/workflow-mcp) server for generic entity storage and querying with JSON Schema validation.

### Removed Work Item Management Tools (4 tools)

The following work item management tools were removed in v2.0:

- ❌ **create_work_item** - Created a new work item in a 5-level hierarchy (project → session → task → research → subtask) with automatic materialized path generation for fast ancestor queries
- ❌ **update_work_item** - Updated work item fields including title, description, and status, automatically setting `completed_at` timestamp when status changed to 'completed'
- ❌ **query_work_items** - Queried work items with filtering by type, status, and parent, supporting recursive descendant queries using materialized paths
- ❌ **get_work_item_hierarchy** - Retrieved complete hierarchy information for a work item including ancestors (parents to root), direct children, and all descendants using materialized path queries (sub-10ms performance)

**Alternative**: Use [workflow-mcp](https://github.com/cyanheads/workflow-mcp) server for hierarchical work item tracking with materialized path queries.

### Migration Guidance

**For Existing v1.x Users**:

1. **Review Breaking Changes**: Read the [Migration Guide](../migration/v1-to-v2-migration.md) for complete details on all removed functionality and data preservation
2. **Install workflow-mcp** (if needed): If you used project management, entity tracking, or work item features, install the [workflow-mcp server](https://github.com/cyanheads/workflow-mcp)
3. **Update Tool Calls**: Replace removed tool calls with workflow-mcp equivalents (see workflow-mcp documentation for tool mapping)
4. **Data Migration**: v2.0 preserves only indexed code repositories. All v1.x project-scoped data (work items, entities, deployments, entity types) is discarded during migration. Export critical data before upgrading.
5. **Test Integration**: Verify workflow-mcp integration works correctly if using automatic project detection (optional feature, see [Configuration Guide](../configuration/production-config.md))

**For New Users**:

- If you only need semantic code search, codebase-mcp v2.0 is complete as-is (2 tools)
- If you need project management or work item tracking, install workflow-mcp alongside codebase-mcp
- Both servers can run independently or in integrated mode for automatic project context resolution (see [Architecture Documentation](../architecture/multi-project-design.md#workflow-mcp-integration-architecture))

---

## Tool Discovery

The codebase-mcp server implements the MCP (Model Context Protocol) tool discovery mechanism via Server-Sent Events (SSE) transport. AI assistants automatically discover available tools and their schemas when connecting to the server.

### MCP Client Discovery

When an MCP client (such as Claude Code, Claude Desktop, or any MCP-compatible AI assistant) connects to the codebase-mcp server, the client automatically enumerates available tools through the MCP protocol's tool discovery endpoint.

**Discovery Process**:

1. **Client Connection**: MCP client establishes SSE connection to server
2. **Tool Enumeration**: Client sends `tools/list` request via MCP protocol
3. **Schema Delivery**: Server responds with complete tool definitions including JSON Schema for parameters
4. **Validation Setup**: Client configures parameter validation using provided schemas

**Result**: The client discovers exactly **2 tools** (`index_repository` and `search_code`) with complete parameter schemas, descriptions, and validation rules.

### Example Discovery Response

The MCP tool discovery mechanism returns a response in the following format (conceptual representation for documentation purposes):

```json
{
  "tools": [
    {
      "name": "index_repository",
      "description": "Index a code repository for semantic search with multi-project workspace isolation.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "repo_path": {
            "type": "string",
            "description": "Absolute path to repository directory"
          },
          "project_id": {
            "type": "string",
            "description": "Project workspace identifier for data isolation",
            "default": "default"
          },
          "force_reindex": {
            "type": "boolean",
            "description": "Force full re-index even if already indexed",
            "default": false
          }
        },
        "required": ["repo_path"]
      }
    },
    {
      "name": "search_code",
      "description": "Search indexed code repositories using natural language queries with semantic similarity matching powered by pgvector.",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": {
            "type": "string",
            "description": "Natural language search query"
          },
          "project_id": {
            "type": "string",
            "description": "Project workspace identifier for data isolation",
            "default": "default"
          },
          "repository_id": {
            "type": "string",
            "description": "Optional UUID to filter by specific repository"
          },
          "file_type": {
            "type": "string",
            "description": "Optional file extension filter (e.g., 'py', 'js')"
          },
          "directory": {
            "type": "string",
            "description": "Optional directory path filter (supports wildcards)"
          },
          "limit": {
            "type": "integer",
            "description": "Maximum number of results (1-50)",
            "default": 10,
            "minimum": 1,
            "maximum": 50
          }
        },
        "required": ["query"]
      }
    }
  ]
}
```

**Note**: This is a conceptual representation for documentation purposes. The actual MCP protocol response includes additional metadata and follows the MCP specification's exact format.

### Schema Validation

The codebase-mcp server uses **JSON Schema Draft 7** for parameter validation, ensuring all tool invocations receive valid inputs before execution.

**Validation Process**:

1. **Schema Definition**: Each tool's parameters are defined using JSON Schema with types, constraints, defaults, and validation rules
2. **Protocol-Level Validation**: The MCP protocol validates parameters against the schema **before** tool invocation
3. **Error Responses**: Invalid parameters trigger `VALIDATION_ERROR` responses with field-level error messages indicating which parameters failed validation
4. **Type Safety**: Pydantic models enforce runtime type safety for all tool parameters (Constitutional Principle VIII: Pydantic-Based Type Safety)

**Validation Guarantees**:

- Required parameters are always present (e.g., `repo_path` for `index_repository`, `query` for `search_code`)
- Optional parameters use documented default values (e.g., `project_id="default"`, `limit=10`)
- Type constraints are enforced (e.g., `limit` must be integer between 1-50)
- Format validation prevents invalid inputs (e.g., `project_id` must be alphanumeric + hyphens only, max 50 characters)

**Example Validation Errors**:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Parameter validation failed",
    "details": {
      "repo_path": "Field required",
      "limit": "Value must be between 1 and 50"
    }
  }
}
```

### Protocol Compliance

The codebase-mcp server strictly adheres to the **MCP (Model Context Protocol)** specification for all tool operations:

- **MCP Specification**: [https://github.com/modelcontextprotocol/specification](https://github.com/modelcontextprotocol/specification)
- **Framework**: Built using [FastMCP](https://github.com/jlowin/fastmcp) with the official [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) (Constitutional Principle XI: FastMCP and Python SDK Foundation)
- **Transport**: SSE (Server-Sent Events) only, no stdout/stderr pollution (Constitutional Principle III: Protocol Compliance)
- **Schema Generation**: Automatic from Pydantic type hints via FastMCP decorators (`@mcp.tool()`)
- **Validation**: JSON Schema validation enforced at protocol layer before tool execution

**Compliance Testing**:

The server includes comprehensive MCP protocol compliance tests:

- Contract tests validate SSE transport behavior (`tests/contract/test_transport_compliance.py`)
- Schema generation tests ensure correct JSON Schema output (`tests/contract/test_schema_generation.py`)
- Tool registration tests verify discovery mechanism (`tests/contract/test_tool_registration.py`)
- Integration tests validate end-to-end MCP client interactions (`tests/integration/test_ai_assistant_integration.py`)

**Constitutional Guarantee**: All protocol violations are flagged as CRITICAL by the `/analyze` command and block feature progression (Constitutional Principle III: Protocol Compliance).

---

## Related documentation

- **Environment Variables**: See [Environment Variables Reference](../configuration/production-config.md#environment-variables-reference) for configuration details
- **Multi-Project Architecture**: See [Architecture Documentation](../architecture/multi-project-design.md) for workspace isolation design
- **workflow-mcp Integration**: See [Integration Guide](../integration/workflow-mcp-integration.md) for automatic project detection setup
- **Configuration Guide**: See [Production Configuration Guide](../configuration/production-config.md) for deployment and tuning
- **Migration Guide**: See [v1.x to v2.0 Migration Guide](../migration/v1-to-v2-migration.md) for removed tools reference and upgrade procedures
- **Glossary**: See [Glossary](../glossary.md) for canonical terminology definitions
