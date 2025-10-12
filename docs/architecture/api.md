# API Documentation

Complete API reference for the Codebase MCP Server's six MCP tools.

## Overview

The Codebase MCP Server implements the Model Context Protocol (MCP) specification for tool-based interactions with AI assistants. All communication occurs via Server-Sent Events (SSE) transport.

### Protocol Basics

- **Transport**: Server-Sent Events (SSE)
- **Base URL**: `http://localhost:3000`
- **Content-Type**: `application/json`
- **Protocol Version**: MCP v1.0

### Request Format

All tool invocations follow the MCP protocol structure:

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "tool_name",
    "arguments": {
      // Tool-specific parameters
    }
  },
  "id": "unique-request-id"
}
```

### Response Format

Responses are delivered via SSE with the following structure:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Tool execution result as JSON string"
      }
    ]
  },
  "id": "unique-request-id"
}
```

### Error Handling

Errors follow the JSON-RPC 2.0 error format:

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32603,
    "message": "Internal error",
    "data": {
      "details": "Specific error information"
    }
  },
  "id": "unique-request-id"
}
```

**Common Error Codes:**

- `-32700`: Parse error
- `-32600`: Invalid request
- `-32601`: Method not found (unknown tool)
- `-32602`: Invalid params
- `-32603`: Internal error
- `-32000`: Server error (custom)

---

## Tool: search_code

Performs semantic search across indexed code repositories using natural language queries.

### Description

Searches for code chunks that semantically match the provided query. Returns ranked results with similarity scores and surrounding context.

### Input Schema

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Natural language search query",
      "minLength": 1,
      "maxLength": 500
    },
    "repository_id": {
      "type": "string",
      "format": "uuid",
      "description": "Optional repository filter"
    },
    "file_type": {
      "type": "string",
      "description": "Optional file extension filter (e.g., 'py', 'js')",
      "pattern": "^[a-zA-Z0-9]+$"
    },
    "directory": {
      "type": "string",
      "description": "Optional directory path filter",
      "maxLength": 500
    },
    "limit": {
      "type": "integer",
      "minimum": 1,
      "maximum": 50,
      "default": 10,
      "description": "Maximum number of results"
    }
  },
  "required": ["query"],
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "properties": {
    "results": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "chunk_id": {
            "type": "string",
            "format": "uuid",
            "description": "Unique identifier for the code chunk"
          },
          "file_path": {
            "type": "string",
            "description": "Full path to the source file"
          },
          "content": {
            "type": "string",
            "description": "The actual code chunk content"
          },
          "start_line": {
            "type": "integer",
            "description": "Starting line number in the source file"
          },
          "end_line": {
            "type": "integer",
            "description": "Ending line number in the source file"
          },
          "similarity_score": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Cosine similarity score (higher is better)"
          },
          "context_before": {
            "type": "string",
            "description": "10 lines of code before the chunk"
          },
          "context_after": {
            "type": "string",
            "description": "10 lines of code after the chunk"
          }
        },
        "required": ["chunk_id", "file_path", "content", "start_line", "end_line", "similarity_score"]
      }
    },
    "total_count": {
      "type": "integer",
      "description": "Total matching chunks before limit applied"
    },
    "latency_ms": {
      "type": "integer",
      "description": "Query execution time in milliseconds"
    }
  },
  "required": ["results", "total_count", "latency_ms"]
}
```

### Example Request

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "search_code",
    "arguments": {
      "query": "function to calculate fibonacci sequence",
      "file_type": "py",
      "limit": 5
    }
  },
  "id": "search-001"
}
```

### Example Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"results\":[{\"chunk_id\":\"abc123\",\"file_path\":\"/repo/src/math_utils.py\",\"content\":\"def fibonacci(n):\\n    if n <= 1:\\n        return n\\n    return fibonacci(n-1) + fibonacci(n-2)\",\"start_line\":45,\"end_line\":48,\"similarity_score\":0.92,\"context_before\":\"# Math utility functions\\n\\n\",\"context_after\":\"\\ndef factorial(n):\\n    if n == 0:\\n        return 1\"}],\"total_count\":3,\"latency_ms\":145}"
      }
    ]
  },
  "id": "search-001"
}
```

### Performance

- **Target Latency**: <500ms (p95)
- **Actual Performance**: 100-300ms typical
- **Optimization**: Results are retrieved using pgvector's HNSW index

### Error Scenarios

- **Empty Query**: Returns error with code -32602
- **Invalid Repository ID**: Returns empty results
- **Database Timeout**: Returns error with code -32603

---

## Tool: index_repository

Indexes a code repository for semantic search by scanning files, generating embeddings, and storing in the database.

### Description

Scans all source code files in a repository (respecting .gitignore), chunks them using tree-sitter AST parsing, generates embeddings via Ollama, and stores in PostgreSQL with pgvector.

### Input Schema

```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "Absolute path to repository",
      "pattern": "^/.*",
      "maxLength": 500
    },
    "name": {
      "type": "string",
      "description": "Display name for repository",
      "minLength": 1,
      "maxLength": 200
    },
    "force_reindex": {
      "type": "boolean",
      "default": false,
      "description": "Force full re-index even if already indexed"
    }
  },
  "required": ["path", "name"],
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "properties": {
    "repository_id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique identifier for the indexed repository"
    },
    "files_indexed": {
      "type": "integer",
      "description": "Number of files successfully indexed"
    },
    "chunks_created": {
      "type": "integer",
      "description": "Total number of code chunks created"
    },
    "duration_seconds": {
      "type": "number",
      "description": "Total indexing time in seconds"
    },
    "status": {
      "type": "string",
      "enum": ["success", "partial", "failed"],
      "description": "Overall indexing status"
    },
    "errors": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "List of errors encountered during indexing"
    }
  },
  "required": ["repository_id", "files_indexed", "chunks_created", "duration_seconds", "status"]
}
```

### Example Request

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "index_repository",
    "arguments": {
      "path": "/home/user/projects/my-app",
      "name": "My Application",
      "force_reindex": false
    }
  },
  "id": "index-001"
}
```

### Example Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"repository_id\":\"550e8400-e29b-41d4-a716-446655440000\",\"files_indexed\":247,\"chunks_created\":1823,\"duration_seconds\":45.7,\"status\":\"success\",\"errors\":[]}"
      }
    ]
  },
  "id": "index-001"
}
```

### Performance

- **Target**: 10,000 files in <60 seconds
- **Actual Performance**: 200-250 files/second typical
- **Optimization**: Batch embedding generation, parallel file processing

### Error Scenarios

- **Invalid Path**: Returns error "Repository path does not exist"
- **Permission Denied**: Returns partial status with errors list
- **Ollama Unavailable**: Returns failed status with connection error

---

## Tool: get_task

Retrieves a specific development task by its unique identifier.

### Description

Fetches complete details of a development task including title, description, status, and git integration metadata.

### Input Schema

```json
{
  "type": "object",
  "properties": {
    "task_id": {
      "type": "string",
      "format": "uuid",
      "description": "Unique task identifier"
    }
  },
  "required": ["task_id"],
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid"
    },
    "title": {
      "type": "string"
    },
    "description": {
      "type": "string",
      "nullable": true
    },
    "notes": {
      "type": "string",
      "nullable": true
    },
    "status": {
      "type": "string",
      "enum": ["need to be done", "in-progress", "complete"]
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time"
    },
    "branch": {
      "type": "string",
      "nullable": true,
      "description": "Associated git branch"
    },
    "commit": {
      "type": "string",
      "nullable": true,
      "pattern": "^[a-f0-9]{40}$",
      "description": "Associated git commit hash"
    },
    "planning_references": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Paths to planning documents"
    }
  },
  "required": ["id", "title", "status", "created_at", "updated_at"]
}
```

### Example Request

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "get_task",
    "arguments": {
      "task_id": "123e4567-e89b-12d3-a456-426614174000"
    }
  },
  "id": "get-task-001"
}
```

### Example Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"id\":\"123e4567-e89b-12d3-a456-426614174000\",\"title\":\"Implement rate limiting\",\"description\":\"Add rate limiting to all API endpoints\",\"notes\":\"Use Redis for distributed rate limiting\",\"status\":\"in-progress\",\"created_at\":\"2024-01-15T10:30:00Z\",\"updated_at\":\"2024-01-15T14:45:00Z\",\"branch\":\"feature/rate-limiting\",\"commit\":null,\"planning_references\":[\"specs/rate-limiting.md\"]}"
      }
    ]
  },
  "id": "get-task-001"
}
```

### Performance

- **Target Latency**: <100ms (p95)
- **Actual Performance**: 10-30ms typical
- **Optimization**: Direct primary key lookup

### Error Scenarios

- **Task Not Found**: Returns error "Task not found"
- **Invalid UUID**: Returns error with code -32602

---

## Tool: list_tasks

Lists development tasks with optional filtering by status, branch, or limit.

### Description

Retrieves a list of development tasks with support for filtering and pagination. Results are ordered by creation date (newest first).

### Input Schema

```json
{
  "type": "object",
  "properties": {
    "status": {
      "type": "string",
      "enum": ["need to be done", "in-progress", "complete"],
      "description": "Filter by task status"
    },
    "branch": {
      "type": "string",
      "description": "Filter by git branch name",
      "maxLength": 200
    },
    "limit": {
      "type": "integer",
      "minimum": 1,
      "maximum": 100,
      "default": 20,
      "description": "Maximum number of tasks to return"
    }
  },
  "additionalProperties": false
}
```

### Output Schema

```json
{
  "type": "object",
  "properties": {
    "tasks": {
      "type": "array",
      "items": {
        "$ref": "#/definitions/Task"
      },
      "description": "Array of task objects"
    },
    "total_count": {
      "type": "integer",
      "description": "Total number of tasks matching filters (before limit)"
    }
  },
  "required": ["tasks", "total_count"]
}
```

### Example Request

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "list_tasks",
    "arguments": {
      "status": "in-progress",
      "limit": 10
    }
  },
  "id": "list-001"
}
```

### Example Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"tasks\":[{\"id\":\"task-1\",\"title\":\"Fix authentication bug\",\"description\":null,\"status\":\"in-progress\",\"created_at\":\"2024-01-15T10:00:00Z\",\"updated_at\":\"2024-01-15T10:00:00Z\",\"branch\":\"bugfix/auth\",\"commit\":null},{\"id\":\"task-2\",\"title\":\"Update documentation\",\"description\":\"Update API docs\",\"status\":\"in-progress\",\"created_at\":\"2024-01-14T15:00:00Z\",\"updated_at\":\"2024-01-14T15:00:00Z\",\"branch\":null,\"commit\":null}],\"total_count\":2}"
      }
    ]
  },
  "id": "list-001"
}
```

### Performance

- **Target Latency**: <200ms (p95)
- **Actual Performance**: 20-50ms typical
- **Optimization**: Indexed status and branch columns

### Error Scenarios

- **Invalid Status**: Returns error with code -32602
- **Database Timeout**: Returns error with code -32603

---

## Tool: create_task

Creates a new development task with optional planning references.

### Description

Creates a new task in the system for tracking development work. Tasks start with "need to be done" status and can be associated with planning documents.

### Input Schema

```json
{
  "type": "object",
  "properties": {
    "title": {
      "type": "string",
      "minLength": 1,
      "maxLength": 200,
      "description": "Task title (required)"
    },
    "description": {
      "type": "string",
      "maxLength": 2000,
      "description": "Detailed task description"
    },
    "notes": {
      "type": "string",
      "maxLength": 5000,
      "description": "Additional notes or context"
    },
    "planning_references": {
      "type": "array",
      "items": {
        "type": "string",
        "maxLength": 500
      },
      "maxItems": 10,
      "description": "Relative paths to planning documents"
    }
  },
  "required": ["title"],
  "additionalProperties": false
}
```

### Output Schema

Returns the complete created task object (same as get_task output).

### Example Request

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "create_task",
    "arguments": {
      "title": "Implement caching layer",
      "description": "Add Redis caching for frequently accessed data",
      "notes": "Consider using cache-aside pattern",
      "planning_references": ["specs/caching.md", "docs/architecture.md"]
    }
  },
  "id": "create-001"
}
```

### Example Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"id\":\"new-task-id\",\"title\":\"Implement caching layer\",\"description\":\"Add Redis caching for frequently accessed data\",\"notes\":\"Consider using cache-aside pattern\",\"status\":\"need to be done\",\"created_at\":\"2024-01-15T16:00:00Z\",\"updated_at\":\"2024-01-15T16:00:00Z\",\"branch\":null,\"commit\":null,\"planning_references\":[\"specs/caching.md\",\"docs/architecture.md\"]}"
      }
    ]
  },
  "id": "create-001"
}
```

### Performance

- **Target Latency**: <150ms (p95)
- **Actual Performance**: 20-40ms typical
- **Optimization**: Single INSERT with RETURNING clause

### Error Scenarios

- **Missing Title**: Returns error with code -32602
- **Title Too Long**: Returns validation error
- **Database Error**: Returns error with code -32603

---

## Tool: update_task

Updates an existing development task, including status changes and git integration.

### Description

Modifies an existing task's properties. Supports partial updates (only provided fields are updated). Can associate tasks with git branches and commits for tracking implementation.

### Input Schema

```json
{
  "type": "object",
  "properties": {
    "task_id": {
      "type": "string",
      "format": "uuid",
      "description": "Task ID to update (required)"
    },
    "title": {
      "type": "string",
      "minLength": 1,
      "maxLength": 200,
      "description": "New title"
    },
    "description": {
      "type": "string",
      "maxLength": 2000,
      "description": "New description"
    },
    "notes": {
      "type": "string",
      "maxLength": 5000,
      "description": "New notes"
    },
    "status": {
      "type": "string",
      "enum": ["need to be done", "in-progress", "complete"],
      "description": "New status"
    },
    "branch": {
      "type": "string",
      "maxLength": 200,
      "description": "Git branch name to associate"
    },
    "commit": {
      "type": "string",
      "pattern": "^[a-f0-9]{40}$",
      "description": "Git commit hash to associate (40 chars)"
    }
  },
  "required": ["task_id"],
  "additionalProperties": false
}
```

### Output Schema

Returns the complete updated task object (same as get_task output).

### Example Request

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "update_task",
    "arguments": {
      "task_id": "123e4567-e89b-12d3-a456-426614174000",
      "status": "complete",
      "branch": "feature/caching",
      "commit": "a1b2c3d4e5f6789012345678901234567890abcd"
    }
  },
  "id": "update-001"
}
```

### Example Response

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"id\":\"123e4567-e89b-12d3-a456-426614174000\",\"title\":\"Implement caching layer\",\"description\":\"Add Redis caching for frequently accessed data\",\"notes\":\"Consider using cache-aside pattern\",\"status\":\"complete\",\"created_at\":\"2024-01-15T16:00:00Z\",\"updated_at\":\"2024-01-15T17:30:00Z\",\"branch\":\"feature/caching\",\"commit\":\"a1b2c3d4e5f6789012345678901234567890abcd\",\"planning_references\":[\"specs/caching.md\"]}"
      }
    ]
  },
  "id": "update-001"
}
```

### Performance

- **Target Latency**: <150ms (p95)
- **Actual Performance**: 20-40ms typical
- **Optimization**: Single UPDATE with RETURNING clause

### Error Scenarios

- **Task Not Found**: Returns error "Task not found"
- **Invalid Task ID**: Returns error with code -32602
- **Invalid Commit Hash**: Returns validation error
- **Database Error**: Returns error with code -32603

---

## Common Patterns

### Error Handling

All tools implement consistent error handling:

```python
try:
    result = await tool_function(**arguments)
    return {"success": True, "data": result}
except ValidationError as e:
    return {"error": {"code": -32602, "message": "Invalid params", "data": str(e)}}
except NotFoundError as e:
    return {"error": {"code": -32000, "message": str(e)}}
except Exception as e:
    return {"error": {"code": -32603, "message": "Internal error", "data": str(e)}}
```

### Pagination

Tools that return lists support pagination via `limit` parameter:

- Default limit: 10-20 items depending on tool
- Maximum limit: 50-100 items depending on tool
- Total count always returned for client-side pagination

### Filtering

List operations support multiple filter types:

- **Exact match**: `status`, `file_type`
- **Prefix match**: `directory`, `branch`
- **UUID match**: `repository_id`, `task_id`

### Sorting

- Search results: Sorted by similarity score (descending)
- Task lists: Sorted by creation date (newest first)
- File lists: Sorted alphabetically by path

---

## Performance Requirements

### Latency Targets (p95)

| Tool | Target | Actual |
|------|--------|--------|
| search_code | <500ms | 100-300ms |
| index_repository | <60s for 10K files | 40-50s |
| get_task | <100ms | 10-30ms |
| list_tasks | <200ms | 20-50ms |
| create_task | <150ms | 20-40ms |
| update_task | <150ms | 20-40ms |

### Throughput

- **Concurrent Searches**: Up to 100 simultaneous queries
- **Indexing**: 200-250 files per second
- **Task Operations**: 1000+ ops/second

### Resource Usage

- **Memory**: <500MB baseline, up to 2GB during indexing
- **CPU**: 1-2 cores typical, up to 4 cores during indexing
- **Database Connections**: 20 pool + 10 overflow
- **Ollama Connections**: 10 concurrent max

---

## Monitoring

### Health Check Endpoint

```bash
GET /health

Response:
{
  "status": "healthy",
  "database": "connected",
  "ollama": "connected",
  "version": "0.1.0",
  "uptime_seconds": 3600
}
```

### Metrics

Key metrics tracked in logs:

- **Request latency**: Per-tool timing
- **Error rates**: By error type and tool
- **Database query time**: Slow query logging
- **Embedding generation time**: Batch performance
- **Cache hit rates**: For repeated searches

### Performance Monitoring

```sql
-- Check slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE mean_exec_time > 100
ORDER BY mean_exec_time DESC;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan;
```

---

## Examples

### Complete Workflow Example

```python
# 1. Index a repository
index_result = await mcp_call("index_repository", {
    "path": "/path/to/repo",
    "name": "My Project"
})
repo_id = index_result["repository_id"]

# 2. Search for authentication code
search_result = await mcp_call("search_code", {
    "query": "user authentication login",
    "repository_id": repo_id,
    "limit": 5
})

# 3. Create a task based on findings
task_result = await mcp_call("create_task", {
    "title": "Refactor authentication module",
    "description": f"Found {search_result['total_count']} auth implementations to consolidate"
})
task_id = task_result["id"]

# 4. Update task when complete
update_result = await mcp_call("update_task", {
    "task_id": task_id,
    "status": "complete",
    "branch": "refactor/auth",
    "commit": "abc123..."
})
```

### Integration with AI Assistants

```python
# Claude/ChatGPT Integration Example
async def handle_ai_request(prompt: str):
    # AI requests code search
    if "find code for" in prompt:
        query = extract_query(prompt)
        results = await mcp_call("search_code", {"query": query})

        # Format results for AI
        formatted = format_search_results(results)
        return {"role": "tool", "content": formatted}

    # AI requests task creation
    elif "create task" in prompt:
        task_info = extract_task_info(prompt)
        task = await mcp_call("create_task", task_info)
        return {"role": "tool", "content": f"Created task: {task['id']}"}
```

### Batch Operations

```python
# Index multiple repositories
repos = [
    {"path": "/repo1", "name": "Frontend"},
    {"path": "/repo2", "name": "Backend"},
    {"path": "/repo3", "name": "Mobile"}
]

results = []
for repo in repos:
    result = await mcp_call("index_repository", repo)
    results.append(result)
    print(f"Indexed {repo['name']}: {result['files_indexed']} files")
```

---

## Rate Limiting

Currently no rate limiting is implemented, but the architecture supports adding it:

```python
# Future rate limit headers
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Authentication

Currently no authentication is required. The server is designed for local use only.

For production deployments, consider:
- API key authentication
- OAuth 2.0 for user-specific tasks
- IP allowlisting for local network access

---

## Optimization Tips

### Search Performance

1. **Use specific queries**: More keywords = better matching
2. **Add filters**: Repository, file type, directory filters reduce search space
3. **Reasonable limits**: Start with limit=10, increase if needed

### Indexing Performance

1. **Batch repositories**: Index during off-hours
2. **Use force_reindex sparingly**: Only when structure changes significantly
3. **Monitor disk I/O**: SSD recommended for large repositories

### Database Optimization

1. **Tune pgvector indexes**: Adjust `lists` parameter based on dataset size
2. **Increase work_mem**: For large result sets
3. **Connection pooling**: Adjust pool size based on concurrent users

---

## Troubleshooting

For detailed troubleshooting information, see [troubleshooting.md](troubleshooting.md).

Common issues:
- **Empty search results**: Check if repository is indexed
- **Slow searches**: Verify pgvector indexes are created
- **Indexing failures**: Check Ollama is running and model is available
- **Connection errors**: Verify DATABASE_URL and OLLAMA_BASE_URL