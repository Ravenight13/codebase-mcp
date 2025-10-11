# User Stories for Codebase MCP Server

## Epic: Multi-Project Semantic Code Search

The Codebase MCP Server enables developers to search code semantically across multiple projects using natural language queries, with fast (<500ms) responses and accurate relevance ranking.

---

## Story 1: Search Code Across Active Project

**As a** developer working in Claude Code
**I need** to search for code patterns using natural language in my current project
**So that** I can quickly locate relevant implementations without manually grepping files

### Acceptance Criteria

1. When I query "authentication middleware that checks JWT tokens"
   - THEN I receive top 10 results ranked by relevance
   - AND each result includes file path, line numbers, and code snippet
   - AND results include 3 lines of context before/after the match
   - AND response time is <500ms (p95)

2. When I query "error handling for database connections"
   - THEN results are filtered to the active project only
   - AND no results from other projects appear
   - AND similarity scores are visible (0.0 to 1.0 scale)

3. When no results match my query
   - THEN I receive a clear "No results found" message
   - AND suggestions for refining the query (if applicable)

### Test Scenarios

```python
# Scenario 1: Successful search
search_code(
    query="authentication middleware that checks JWT tokens",
    project_id="abc-123",
    limit=10
)
# Expected: 10 results, <500ms, relevance >0.7 for top result

# Scenario 2: Empty results
search_code(
    query="quantum entanglement flux capacitor",
    project_id="abc-123",
    limit=10
)
# Expected: Empty results list, helpful message

# Scenario 3: Context lines
search_code(
    query="database connection pooling",
    project_id="abc-123",
    limit=5
)
# Expected: Results include context_before and context_after fields
```

---

## Story 2: Index New Repository for Project

**As a** developer starting work on a new codebase
**I need** to index a repository for semantic search
**So that** I can search its code using natural language queries

### Acceptance Criteria

1. When I index a repository with 5,000 files
   - THEN indexing completes in <30 seconds
   - AND I receive a summary: files indexed, chunks created, duration
   - AND indexing status is "success"

2. When I index a repository with 10,000 files
   - THEN indexing completes in <60 seconds (within performance target)
   - AND progress is reported during indexing (via logging)
   - AND errors are captured and reported without halting entire process

3. When indexing fails for some files (binary files, access denied)
   - THEN indexing continues for other files (partial success)
   - AND I receive a detailed error report (which files failed, why)
   - AND status is "partial" with error count

4. When I re-index an already-indexed repository
   - THEN by default, indexing is skipped (already indexed)
   - AND I can force re-indexing with `force_reindex=True`
   - AND force re-indexing removes old chunks before creating new ones

### Test Scenarios

```python
# Scenario 1: First-time indexing
index_repository(
    repo_path="/Users/dev/myproject",
    project_id="abc-123",
    force_reindex=False
)
# Expected: {
#   "repository_id": "uuid",
#   "files_indexed": 5234,
#   "chunks_created": 12056,
#   "duration_seconds": 28.4,
#   "status": "success",
#   "errors": []
# }

# Scenario 2: Re-indexing (skipped)
index_repository(
    repo_path="/Users/dev/myproject",
    project_id="abc-123",
    force_reindex=False
)
# Expected: Status "skipped", message "Repository already indexed"

# Scenario 3: Force re-indexing
index_repository(
    repo_path="/Users/dev/myproject",
    project_id="abc-123",
    force_reindex=True
)
# Expected: Status "success", old chunks removed, new chunks created

# Scenario 4: Partial failure (some files unreadable)
index_repository(
    repo_path="/Users/dev/project-with-binaries",
    project_id="abc-123",
    force_reindex=False
)
# Expected: {
#   "status": "partial",
#   "files_indexed": 4800,
#   "errors": [
#     "Failed to read /path/to/image.png: Binary file",
#     "Failed to read /path/to/secret: Permission denied"
#   ]
# }
```

---

## Story 3: Switch Projects and Search New Context

**As a** developer working across multiple codebases
**I need** to switch between projects and search within the active project
**So that** I can work on different projects without cross-contamination

### Acceptance Criteria

1. When workflow-mcp sets active project to "project-alpha"
   - AND I search for "user authentication"
   - THEN results come ONLY from project-alpha's indexed code
   - AND no results from project-beta or project-gamma appear

2. When workflow-mcp switches active project to "project-beta"
   - AND I search for "user authentication" again
   - THEN results come ONLY from project-beta's indexed code
   - AND results differ from project-alpha (different codebase)

3. When I explicitly provide project_id parameter
   - THEN that project_id overrides workflow-mcp's active project
   - AND I can search non-active projects explicitly

4. When workflow-mcp is not available
   - AND I provide project_id parameter explicitly
   - THEN search works normally (no workflow-mcp dependency required)

### Test Scenarios

```python
# Scenario 1: Active project via workflow-mcp
# workflow-mcp.get_active_project_id() returns "project-alpha"
search_code(
    query="user authentication",
    project_id=None  # Uses active project from workflow-mcp
)
# Expected: Results from project-alpha only

# Scenario 2: Switch projects
# workflow-mcp.get_active_project_id() returns "project-beta"
search_code(
    query="user authentication",
    project_id=None  # Uses new active project
)
# Expected: Results from project-beta only, different from Scenario 1

# Scenario 3: Explicit project_id (override)
search_code(
    query="user authentication",
    project_id="project-gamma"  # Explicit, ignores active project
)
# Expected: Results from project-gamma only

# Scenario 4: No workflow-mcp available
search_code(
    query="user authentication",
    project_id="project-alpha"  # Must provide explicitly
)
# Expected: Results from project-alpha, no error
```

---

## Story 4: Filter Search by File Type and Directory

**As a** developer searching for specific implementations
**I need** to filter search results by file type and directory
**So that** I can narrow results to relevant code areas (e.g., tests only, backend only)

### Acceptance Criteria

1. When I search with `file_type="py"`
   - THEN results include ONLY Python files (.py)
   - AND no JavaScript, TypeScript, or other files appear

2. When I search with `directory="backend/api"`
   - THEN results include ONLY files in backend/api/ and subdirectories
   - AND no frontend/ or scripts/ files appear

3. When I search with both filters: `file_type="ts"` AND `directory="frontend/components"`
   - THEN results match BOTH criteria (TypeScript files in frontend/components/)
   - AND results are correctly narrowed (not OR logic, but AND logic)

4. When I search with invalid filters (e.g., `directory="nonexistent/"`)
   - THEN I receive empty results (not an error)
   - AND a message indicating no matches in specified directory

### Test Scenarios

```python
# Scenario 1: File type filter
search_code(
    query="database connection",
    project_id="abc-123",
    file_type="py"
)
# Expected: Only .py files in results

# Scenario 2: Directory filter
search_code(
    query="HTTP request handler",
    project_id="abc-123",
    directory="backend/api"
)
# Expected: Only files in backend/api/* in results

# Scenario 3: Combined filters
search_code(
    query="React component hooks",
    project_id="abc-123",
    file_type="tsx",
    directory="frontend/components"
)
# Expected: Only .tsx files in frontend/components/* in results

# Scenario 4: No results due to filters
search_code(
    query="authentication",
    project_id="abc-123",
    directory="nonexistent/"
)
# Expected: Empty results, message "No results in directory nonexistent/"
```

---

## Story 5: Fast Search Performance on Large Codebases

**As a** developer working on a large monorepo
**I need** search to remain fast even with 100,000+ indexed chunks
**So that** I can maintain flow state without waiting for search results

### Acceptance Criteria

1. When searching a project with 10,000 files (50,000 chunks)
   - THEN search response time is <500ms (p95)
   - AND response time is <300ms (p50)

2. When searching a project with 50,000 files (250,000 chunks)
   - THEN search response time remains <500ms (p95)
   - AND HNSW index is used for vector similarity (not brute force)

3. When Ollama embedding generation is slow (>200ms)
   - THEN embedding latency is logged as warning
   - AND total search time still meets <500ms target (or fails gracefully)

4. When database connection pool is exhausted
   - THEN new requests wait for available connection (with timeout)
   - AND timeout is 5 seconds (error after 5s)
   - AND error message indicates connection pool exhaustion

### Test Scenarios

```python
# Scenario 1: Performance benchmark (medium codebase)
# Index 10,000 files, measure search latency
search_code(query="error handling patterns", project_id="medium-repo")
# Expected: p95 latency <500ms, p50 latency <300ms

# Scenario 2: Performance benchmark (large codebase)
# Index 50,000 files, measure search latency
search_code(query="database migrations", project_id="large-monorepo")
# Expected: p95 latency <500ms (HNSW index scales well)

# Scenario 3: Slow embedding generation
# Mock Ollama to return embedding in 250ms
search_code(query="async task queue", project_id="abc-123")
# Expected: Warning logged, total time <550ms, degraded but acceptable

# Scenario 4: Connection pool exhaustion
# Saturate connection pool with concurrent searches
# 21st concurrent search (pool size = 20)
search_code(query="anything", project_id="abc-123")
# Expected: Waits up to 5s for connection, then errors with clear message
```

---

## Story 6: Work Offline with Local Embeddings

**As a** developer on a plane or in a cafe with no WiFi
**I need** semantic search to work without internet connectivity
**So that** I can remain productive in offline environments

### Acceptance Criteria

1. When my laptop has no internet connection
   - AND Ollama and PostgreSQL are running locally
   - THEN I can index new repositories
   - AND I can search existing indexed repositories
   - AND all functionality works identically to online mode

2. When I first set up codebase-mcp
   - THEN I must download nomic-embed-text model once (requires internet)
   - AND after download, no further internet is required

3. When Ollama model is not downloaded
   - THEN indexing fails with clear error: "Model nomic-embed-text not found. Run: ollama pull nomic-embed-text"
   - AND error message includes actionable fix

4. When PostgreSQL is not running
   - THEN operations fail with clear error: "Cannot connect to database at localhost:5432"
   - AND error message includes actionable fix

### Test Scenarios

```python
# Scenario 1: Airplane mode (offline)
# Disable network interface
# Ollama and PostgreSQL running locally
index_repository(repo_path="/Users/dev/myproject", project_id="abc-123")
search_code(query="authentication", project_id="abc-123")
# Expected: Both succeed, no internet required

# Scenario 2: Model not downloaded
# Remove nomic-embed-text model
# ollama list | grep nomic-embed-text  → empty
index_repository(repo_path="/Users/dev/myproject", project_id="abc-123")
# Expected: Error with actionable message

# Scenario 3: PostgreSQL not running
# Stop PostgreSQL service
search_code(query="anything", project_id="abc-123")
# Expected: Connection error with actionable message
```

---

## Story 7: Accurate Relevance Ranking

**As a** developer searching for specific code patterns
**I need** search results ranked by relevance (not alphabetically or by date)
**So that** the most similar code appears first

### Acceptance Criteria

1. When I search for "JWT authentication middleware"
   - THEN the top result has highest cosine similarity score (>0.8)
   - AND results are sorted descending by similarity
   - AND irrelevant results (similarity <0.3) are excluded

2. When I search for "error handling"
   - THEN generic error handling (try/catch, exception classes) appears first
   - AND domain-specific error handling appears lower (still relevant)
   - AND unrelated code (no error handling) does not appear

3. When I search for exact code snippet (copy-paste)
   - THEN the exact match has similarity score ~1.0
   - AND appears as top result

4. When I search with very generic query (e.g., "function")
   - THEN results are still ranked by relevance
   - AND limit parameter prevents overwhelming results (default 10)

### Test Scenarios

```python
# Scenario 1: High relevance query
search_code(query="JWT authentication middleware", project_id="abc-123")
# Expected: Top result similarity >0.8, results sorted descending

# Scenario 2: Medium relevance query
search_code(query="error handling", project_id="abc-123")
# Expected: Mix of high (0.7+) and medium (0.5-0.7) relevance

# Scenario 3: Exact match
search_code(
    query="def authenticate_user(token: str) -> Optional[User]:",
    project_id="abc-123"
)
# Expected: Top result similarity ~0.99-1.0, exact code match

# Scenario 4: Generic query with limit
search_code(query="function", project_id="abc-123", limit=10)
# Expected: Exactly 10 results, highest relevance first
```

---

## Story 8: Clear Error Messages and Debugging

**As a** developer encountering errors during indexing or search
**I need** clear error messages with actionable guidance
**So that** I can quickly resolve issues without consulting documentation

### Acceptance Criteria

1. When indexing fails due to missing directory
   - THEN error message is: "Repository path does not exist: /path/to/repo"
   - AND suggested action: "Verify the path and try again"

2. When search fails due to invalid project_id
   - THEN error message is: "Project not found: invalid-project-id"
   - AND suggested action: "Check project ID or index repository first"

3. When Ollama is not running
   - THEN error message is: "Cannot connect to Ollama at http://localhost:11434"
   - AND suggested action: "Start Ollama: ollama serve"

4. When database schema is outdated
   - THEN error message is: "Database schema version mismatch. Expected: 2.0, Found: 1.5"
   - AND suggested action: "Run migrations: alembic upgrade head"

5. When operations are logged
   - THEN logs include structured context: timestamp, operation, project_id, duration, status
   - AND logs are written to file (not stdout/stderr)

### Test Scenarios

```python
# Scenario 1: Invalid repository path
index_repository(
    repo_path="/nonexistent/path",
    project_id="abc-123"
)
# Expected: ValueError with clear message and suggested action

# Scenario 2: Invalid project_id
search_code(query="anything", project_id="nonexistent-project")
# Expected: ValueError with clear message

# Scenario 3: Ollama not running
# Stop Ollama service
index_repository(repo_path="/Users/dev/myproject", project_id="abc-123")
# Expected: ConnectionError with clear message and fix

# Scenario 4: Schema version mismatch
# Downgrade database schema manually
search_code(query="anything", project_id="abc-123")
# Expected: RuntimeError with version info and migration command

# Scenario 5: Log inspection
# Perform any operation
# Check log file: logs/codebase-mcp.log
# Expected: Structured JSON logs with context fields
```

---

## Non-Functional Requirements (Cross-Story)

### Performance
- **Indexing**: <60s for 10,000 files
- **Search**: <500ms p95 latency
- **Concurrent Searches**: 20 simultaneous searches without degradation

### Reliability
- **Uptime**: N/A (runs on-demand, no server uptime)
- **Data Integrity**: No index corruption during crashes (transactional operations)
- **Error Recovery**: Graceful degradation, no silent failures

### Scalability
- **Codebase Size**: Support up to 100,000 files (500,000 chunks)
- **Concurrent Users**: Support up to 20 concurrent clients (connection pool size)
- **Multi-Project**: Support 10+ projects per developer

### Security
- **Data Privacy**: All data stored locally (no external transmission)
- **Access Control**: Relies on filesystem permissions (no auth layer)

### Usability
- **Error Messages**: Clear, actionable, include suggested fixes
- **Logging**: Structured, contextual, file-based (not stdout)
- **Configuration**: Single YAML file per project, sensible defaults
