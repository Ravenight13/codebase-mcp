# Quickstart Integration Tests

**Feature**: Production-Grade MCP Server for Semantic Code Search
**Date**: 2025-10-06
**Purpose**: End-to-end validation scenarios derived from user stories

## Prerequisites

1. **PostgreSQL 14+** with pgvector extension installed
2. **Ollama** running locally with `nomic-embed-text` model
3. **Python 3.11+** with dependencies installed
4. **Test Repository** at `/tmp/test-repo` with sample code files

## Setup

```bash
# Start PostgreSQL (ensure pgvector extension available)
createdb codebase_mcp_test

# Start Ollama
ollama serve

# Pull embedding model
ollama pull nomic-embed-text

# Initialize database
python scripts/init_db.py --database-url postgresql+asyncpg://localhost/codebase_mcp_test

# Create test repository
mkdir -p /tmp/test-repo/src
cat > /tmp/test-repo/src/calculator.py << 'EOF'
def add(a: int, b: int) -> int:
    """Add two numbers and return the result."""
    return a + b

def multiply(a: int, b: int) -> int:
    """Multiply two numbers and return the result."""
    return a * b

class Calculator:
    """A simple calculator class."""

    def __init__(self):
        self.history = []

    def calculate(self, operation: str, a: int, b: int) -> int:
        """Perform calculation and store in history."""
        if operation == "add":
            result = add(a, b)
        elif operation == "multiply":
            result = multiply(a, b)
        else:
            raise ValueError(f"Unknown operation: {operation}")

        self.history.append((operation, a, b, result))
        return result
EOF

cat > /tmp/test-repo/src/utils.py << 'EOF'
def format_result(value: int, decimals: int = 2) -> str:
    """Format a numeric result as a string."""
    return f"{value:.{decimals}f}"

def log_message(message: str, level: str = "INFO") -> None:
    """Log a message to console."""
    print(f"[{level}] {message}")
EOF

# Create .gitignore
cat > /tmp/test-repo/.gitignore << 'EOF'
__pycache__/
*.pyc
.env
EOF

# Start MCP server
python -m src.main
```

---

## Scenario 1: Repository Indexing (FR-001 to FR-006)

**Given**: A code repository exists at `/tmp/test-repo`
**When**: The repository is indexed via MCP tool
**Then**: All source files are scanned, embeddings generated, and stored

### Test Steps

1. **Call `index_repository` tool**:
```json
{
  "path": "/tmp/test-repo",
  "name": "Test Repository",
  "force_reindex": false
}
```

2. **Verify response**:
- `status`: "success"
- `files_indexed`: 2 (calculator.py, utils.py)
- `chunks_created`: ≥5 (functions and class)
- `duration_seconds`: <60

3. **Verify database state**:
```sql
-- Check repository created
SELECT * FROM repositories WHERE path = '/tmp/test-repo';

-- Check files indexed
SELECT relative_path, language, is_deleted FROM code_files
WHERE repository_id = '<repo_id>';
-- Expected: 2 rows (calculator.py, utils.py), is_deleted=false

-- Check chunks created
SELECT chunk_type, start_line, end_line FROM code_chunks
JOIN code_files ON code_chunks.code_file_id = code_files.id
WHERE code_files.repository_id = '<repo_id>';
-- Expected: function chunks for add, multiply, calculate; class chunk for Calculator

-- Check embeddings generated
SELECT COUNT(*) FROM code_chunks
WHERE embedding IS NOT NULL;
-- Expected: All chunks have embeddings
```

4. **Verify .gitignore respected**:
```sql
SELECT relative_path FROM code_files
WHERE relative_path LIKE '%__pycache__%' OR relative_path LIKE '%.pyc';
-- Expected: 0 rows (ignored files not indexed)
```

**Success Criteria**: ✅ Repository indexed in <60s, all text files processed, ignore patterns respected

---

## Scenario 2: Incremental Updates (FR-007 to FR-010)

**Given**: Repository is already indexed
**When**: A file is modified
**Then**: Only changed file is re-indexed

### Test Steps

1. **Modify file**:
```bash
# Add new function to calculator.py
cat >> /tmp/test-repo/src/calculator.py << 'EOF'

def subtract(a: int, b: int) -> int:
    """Subtract b from a and return the result."""
    return a - b
EOF
```

2. **Trigger incremental update** (automatic via file watching or manual):
```json
{
  "path": "/tmp/test-repo",
  "name": "Test Repository",
  "force_reindex": false
}
```

3. **Verify response**:
- `files_indexed`: 1 (only calculator.py)
- `chunks_created`: +1 (new subtract function)
- `duration_seconds`: <10 (much faster than full index)

4. **Verify change event recorded**:
```sql
SELECT event_type, processed FROM change_events
WHERE code_file_id IN (
  SELECT id FROM code_files WHERE relative_path = 'src/calculator.py'
)
ORDER BY detected_at DESC LIMIT 1;
-- Expected: event_type='modified', processed=true
```

**Success Criteria**: ✅ Only modified file re-indexed, update completes in <10s

---

## Scenario 3: Semantic Code Search (FR-011 to FR-015)

**Given**: Repository is indexed with embeddings
**When**: A semantic search query is submitted
**Then**: Relevant code snippets are returned ranked by similarity

### Test Steps

1. **Search for addition functionality**:
```json
{
  "query": "How do I add two numbers together?",
  "limit": 5
}
```

2. **Verify response**:
- `results`: Contains chunk from `add()` function with high similarity score (>0.8)
- `latency_ms`: <500 (p95 target)
- `context_before` and `context_after`: Provide surrounding lines

3. **Search with filters**:
```json
{
  "query": "calculator class",
  "file_type": "py",
  "directory": "src",
  "limit": 3
}
```

4. **Verify filtered results**:
- All results from `.py` files
- All results from `src/` directory
- Calculator class chunk ranked highly

5. **Search with no results**:
```json
{
  "query": "blockchain consensus algorithm",
  "limit": 10
}
```

6. **Verify graceful handling**:
- `results`: [] (empty array)
- `total_count`: 0
- No errors, valid response structure

**Success Criteria**: ✅ Search returns relevant results in <500ms, filters work correctly, handles no-match gracefully

---

## Scenario 4: Task Creation and Tracking (FR-016 to FR-023)

**Given**: MCP server is running
**When**: Developer creates and manages tasks
**Then**: Tasks are stored with metadata and status tracking

### Test Steps

1. **Create task**:
```json
{
  "title": "Implement division operation",
  "description": "Add divide() function to calculator.py",
  "notes": "Remember to handle division by zero",
  "planning_references": ["specs/001-calculator/spec.md", "specs/001-calculator/plan.md"]
}
```

2. **Verify task created**:
- Response contains `id` (UUID)
- `status`: "need to be done"
- `planning_references`: Contains provided file paths
- `branches`: [] (empty initially)
- `commits`: [] (empty initially)

3. **Update task to in-progress with branch**:
```json
{
  "task_id": "<task_id>",
  "status": "in-progress",
  "branch": "feature/division-operation"
}
```

4. **Verify status transition**:
```sql
SELECT from_status, to_status, changed_at FROM task_status_history
WHERE task_id = '<task_id>'
ORDER BY changed_at;
-- Expected: Row with from_status='need to be done', to_status='in-progress'
```

5. **Verify branch link**:
```sql
SELECT branch_name FROM task_branch_links WHERE task_id = '<task_id>';
-- Expected: 'feature/division-operation'
```

6. **Complete task with commit**:
```json
{
  "task_id": "<task_id>",
  "status": "complete",
  "commit": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"
}
```

7. **Verify commit link and history**:
```sql
SELECT commit_hash FROM task_commit_links WHERE task_id = '<task_id>';
-- Expected: 'a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0'

SELECT COUNT(*) FROM task_status_history WHERE task_id = '<task_id>';
-- Expected: 2 (need to be done → in-progress, in-progress → complete)
```

**Success Criteria**: ✅ Task CRUD operations work, status transitions tracked, git metadata stored

---

## Scenario 5: AI Assistant Integration (FR-024 to FR-028)

**Given**: MCP server exposes tools via SSE
**When**: AI assistant queries for code and task context
**Then**: Contextual information is returned

### Test Steps

1. **List tasks for AI context**:
```json
{
  "status": "in-progress",
  "limit": 10
}
```

2. **Verify AI-friendly response**:
- `tasks`: Array of in-progress tasks with full context
- Each task includes: title, description, notes, planning_references, branches, commits
- AI can understand current development state

3. **Combined search + task context**:
```json
{
  "query": "calculator implementation",
  "limit": 5
}
```

4. **Verify results linked to tasks**:
- Search returns code chunks from calculator.py
- If task exists referencing this code, include task reference in metadata
- AI understands which code relates to which tasks

5. **Get specific task details**:
```json
{
  "task_id": "<task_id>"
}
```

6. **Verify complete context**:
- Full task details with history
- Planning references point to spec/plan documents
- Branch and commit information available
- AI can provide informed assistance

**Success Criteria**: ✅ AI assistant receives complete project context, can query code and tasks seamlessly

---

## Scenario 6: File Deletion and Retention (FR-009, Clarification)

**Given**: Repository has indexed files
**When**: File is deleted from filesystem
**Then**: File marked deleted, retained for 90 days

### Test Steps

1. **Delete file**:
```bash
rm /tmp/test-repo/src/utils.py
```

2. **Trigger change detection**:
```json
{
  "path": "/tmp/test-repo",
  "name": "Test Repository",
  "force_reindex": false
}
```

3. **Verify file marked deleted**:
```sql
SELECT is_deleted, deleted_at FROM code_files
WHERE relative_path = 'src/utils.py';
-- Expected: is_deleted=true, deleted_at=NOW
```

4. **Verify chunks still exist**:
```sql
SELECT COUNT(*) FROM code_chunks
WHERE code_file_id IN (
  SELECT id FROM code_files WHERE relative_path = 'src/utils.py'
);
-- Expected: >0 (chunks retained)
```

5. **Simulate 90-day retention**:
```sql
-- Manually set deleted_at to 91 days ago
UPDATE code_files SET deleted_at = NOW() - INTERVAL '91 days'
WHERE relative_path = 'src/utils.py';

-- Run cleanup
SELECT cleanup_deleted_files();
```

6. **Verify permanent deletion**:
```sql
SELECT COUNT(*) FROM code_files WHERE relative_path = 'src/utils.py';
-- Expected: 0 (permanently removed)
```

**Success Criteria**: ✅ Deleted files marked and retained for 90 days, cleanup removes old deletions

---

## Scenario 7: Performance Validation (FR-034, FR-035)

**Given**: Repository with 10,000 files
**When**: Indexing and searching operations execute
**Then**: Performance targets are met

### Test Steps

1. **Generate large test repository**:
```bash
python scripts/generate_test_repo.py --files 10000 --output /tmp/large-repo
# Creates 10,000 Python files with realistic code
```

2. **Index large repository**:
```json
{
  "path": "/tmp/large-repo",
  "name": "Large Test Repository",
  "force_reindex": true
}
```

3. **Verify indexing performance**:
- `duration_seconds`: <60 (target met)
- `files_indexed`: 10,000
- `status`: "success"

4. **Run 100 search queries and measure latency**:
```python
import asyncio
import time

async def benchmark_search():
    latencies = []
    queries = [
        "function to parse JSON",
        "error handling for network requests",
        # ... 98 more diverse queries
    ]

    for query in queries:
        start = time.perf_counter()
        result = await mcp_client.search_code(query=query, limit=10)
        latency_ms = (time.perf_counter() - start) * 1000
        latencies.append(latency_ms)

    latencies.sort()
    p50 = latencies[50]
    p95 = latencies[95]
    p99 = latencies[99]

    print(f"P50: {p50:.0f}ms, P95: {p95:.0f}ms, P99: {p99:.0f}ms")
    assert p95 < 500, f"P95 latency {p95}ms exceeds 500ms target"

asyncio.run(benchmark_search())
```

5. **Verify search performance**:
- P95 latency: <500ms
- P99 latency: <1000ms
- No timeouts or errors

**Success Criteria**: ✅ 10K file indexing in <60s, search p95 latency <500ms

---

## Cleanup

```bash
# Stop MCP server
# Ctrl+C

# Drop test database
dropdb codebase_mcp_test

# Remove test repositories
rm -rf /tmp/test-repo /tmp/large-repo

# Stop Ollama
# Ctrl+C
```

---

## Summary

All acceptance scenarios validated:
1. ✅ Repository indexing with ignore patterns
2. ✅ Incremental updates for modified files
3. ✅ Semantic search with filters and relevance
4. ✅ Task CRUD with git integration
5. ✅ AI assistant context queries
6. ✅ File deletion 90-day retention
7. ✅ Performance targets (60s indexing, 500ms search)

The system meets all functional and non-functional requirements from the specification.
