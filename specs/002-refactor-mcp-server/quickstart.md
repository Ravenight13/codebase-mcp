# Quickstart: FastMCP Migration Validation

This document outlines 5 validation scenarios to verify the FastMCP migration maintains 100% compatibility with the existing MCP server implementation.

## Validation Scenarios

### 1. Server Startup and Tool Registration

**Purpose**: Verify FastMCP server starts successfully and registers all 6 tools with correct schemas

**Prerequisites**:
- FastMCP installed: `pip install fastmcp`
- PostgreSQL running with codebase_mcp database
- Ollama running with nomic-embed-text model

**Step-by-Step Commands**:

```bash
# 1. Navigate to project root
cd /Users/cliffclarke/Claude_Code/codebase-mcp

# 2. Activate virtual environment (if using)
source venv/bin/activate

# 3. Start FastMCP server in development mode
uv run mcp dev src/mcp/fastmcp_server.py

# Expected output should include:
# - "Starting FastMCP server with stdio transport"
# - "Server startup validation passed: 6 tools registered"
# - List of registered tools:
#   - search_code
#   - index_repository
#   - create_task
#   - get_task
#   - list_tasks
#   - update_task

# 4. Verify tool schemas are generated
# Development mode should show tool schemas in JSON format
# Each tool should have:
#   - name (string)
#   - description (string from docstring)
#   - inputSchema (JSON Schema object)
```

**Expected Output**:

```
2025-10-06 10:00:00 - INFO - Server startup validation passed: 6 tools registered
2025-10-06 10:00:00 - INFO - Starting FastMCP server with stdio transport

Registered tools:
{
  "tools": [
    {
      "name": "search_code",
      "description": "Search codebase using semantic similarity...",
      "inputSchema": {
        "type": "object",
        "properties": {
          "query": {"type": "string", "minLength": 1, "maxLength": 500},
          ...
        },
        "required": ["query"]
      }
    },
    ...
  ]
}
```

**Success Criteria**:
- Server starts without errors
- All 6 tools registered
- Each tool has valid inputSchema and description
- No stdout/stderr pollution (logs only in /tmp/codebase-mcp.log)
- Process listens on stdio (not HTTP)

---

### 2. Search Tool Execution via Stdio

**Purpose**: Verify search_code tool responds correctly via stdio transport with MCP protocol-compliant messages

**Prerequisites**:
- FastMCP server running (from Scenario 1)
- Test repository indexed (can use existing test data)

**Step-by-Step Commands**:

```bash
# 1. Create test MCP request file
cat > /tmp/search_request.json <<EOF
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
EOF

# 2. Send request via stdio to FastMCP server
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search_code","arguments":{"query":"authentication middleware","limit":5}}}' | uv run mcp dev src/mcp/fastmcp_server.py

# 3. Verify response format matches MCP protocol
# Response should be JSON-RPC 2.0 format:
# {
#   "jsonrpc": "2.0",
#   "id": 1,
#   "result": {
#     "results": [...],
#     "total_count": N,
#     "latency_ms": M
#   }
# }
```

**Expected Output**:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "results": [
      {
        "chunk_id": "550e8400-e29b-41d4-a716-446655440000",
        "file_path": "src/middleware/auth.py",
        "content": "async def authenticate_user(token: str) -> User:\n    ...",
        "start_line": 15,
        "end_line": 20,
        "similarity_score": 0.95,
        "context_before": "",
        "context_after": ""
      }
    ],
    "total_count": 1,
    "latency_ms": 250
  }
}
```

**Success Criteria**:
- Response follows JSON-RPC 2.0 format
- Result contains `results`, `total_count`, `latency_ms` fields
- Each result has all required fields (chunk_id, file_path, content, etc.)
- Latency is <500ms (p95 target)
- No errors in /tmp/codebase-mcp.log
- Context logging visible in client (if using MCP inspector)

---

### 3. Integration Test Suite Execution

**Purpose**: Run existing integration tests and confirm 100% pass rate with FastMCP server

**Prerequisites**:
- FastMCP server code migrated
- Test suite unchanged (uses existing test fixtures)
- PostgreSQL test database available

**Step-by-Step Commands**:

```bash
# 1. Set environment variables for testing
export DATABASE_URL="postgresql+asyncpg://localhost/codebase_mcp_test"
export OLLAMA_HOST="http://localhost:11434"

# 2. Run integration tests with pytest
pytest tests/integration/ -v --tb=short

# Expected test files to run:
# - tests/integration/test_mcp_tools.py (all 6 tools)
# - tests/integration/test_protocol_compliance.py (MCP protocol validation)
# - tests/integration/test_indexing_workflow.py (end-to-end indexing)

# 3. Run specific tool tests
pytest tests/integration/test_mcp_tools.py::test_search_code -v
pytest tests/integration/test_mcp_tools.py::test_index_repository -v
pytest tests/integration/test_mcp_tools.py::test_create_task -v
pytest tests/integration/test_mcp_tools.py::test_get_task -v
pytest tests/integration/test_mcp_tools.py::test_list_tasks -v
pytest tests/integration/test_mcp_tools.py::test_update_task -v

# 4. Run protocol compliance tests
pytest tests/integration/test_protocol_compliance.py -v

# 5. Generate coverage report
pytest tests/integration/ --cov=src/mcp --cov-report=html
```

**Expected Output**:

```
============================= test session starts ==============================
collected 42 items

tests/integration/test_mcp_tools.py::test_search_code PASSED           [  2%]
tests/integration/test_mcp_tools.py::test_search_code_with_filters PASSED [ 4%]
tests/integration/test_mcp_tools.py::test_search_code_invalid_query PASSED [ 7%]
tests/integration/test_mcp_tools.py::test_index_repository PASSED       [  9%]
tests/integration/test_mcp_tools.py::test_index_repository_force_reindex PASSED [ 11%]
tests/integration/test_mcp_tools.py::test_index_repository_invalid_path PASSED [ 14%]
tests/integration/test_mcp_tools.py::test_create_task PASSED            [ 16%]
tests/integration/test_mcp_tools.py::test_get_task PASSED               [ 19%]
tests/integration/test_mcp_tools.py::test_get_task_not_found PASSED     [ 21%]
tests/integration/test_mcp_tools.py::test_list_tasks PASSED             [ 23%]
tests/integration/test_mcp_tools.py::test_list_tasks_with_filters PASSED [ 26%]
tests/integration/test_mcp_tools.py::test_update_task PASSED            [ 28%]
tests/integration/test_mcp_tools.py::test_update_task_not_found PASSED  [ 30%]
tests/integration/test_protocol_compliance.py::test_tool_schemas PASSED [ 33%]
tests/integration/test_protocol_compliance.py::test_jsonrpc_format PASSED [ 35%]
tests/integration/test_protocol_compliance.py::test_error_handling PASSED [ 38%]
tests/integration/test_indexing_workflow.py::test_end_to_end_indexing PASSED [ 40%]
...

============================== 42 passed in 12.5s ===============================

Coverage report:
src/mcp/fastmcp_server.py    95%
src/mcp/tools/search.py      98%
src/mcp/tools/indexing.py    97%
src/mcp/tools/tasks.py       96%
```

**Success Criteria**:
- 100% test pass rate (all 42+ tests pass)
- No test modifications needed (existing tests work as-is)
- Coverage >95% for MCP-related code
- Performance tests pass (60s indexing, 500ms search)
- Protocol compliance tests pass (JSON-RPC 2.0, schema validation)

---

### 4. Performance Benchmark Comparison

**Purpose**: Compare performance metrics before and after migration to ensure no regression

**Prerequisites**:
- Both v3 server (old) and FastMCP server (new) available
- Test repository with 10,000 files
- Benchmarking tools installed: `hyperfine`, `ab` (Apache Bench)

**Step-by-Step Commands**:

```bash
# 1. Prepare test repository
# Clone a large repo or use existing test data
git clone https://github.com/python/cpython /tmp/cpython-benchmark
cd /tmp/cpython-benchmark
git checkout v3.11.0  # Consistent test data

# 2. Benchmark indexing performance (v3 server)
time python -m src.mcp.server index /tmp/cpython-benchmark

# Expected: ~50-60 seconds for 10K files
# Record: files_indexed, chunks_created, duration_seconds

# 3. Benchmark indexing performance (FastMCP server)
time python -m src.mcp.fastmcp_server index /tmp/cpython-benchmark

# Expected: ~50-60 seconds (no regression)
# Record: files_indexed, chunks_created, duration_seconds

# 4. Benchmark search performance (v3 server)
# Use hyperfine for multiple runs
hyperfine --warmup 3 --runs 20 \
  'echo "{\"query\":\"async function\"}" | python -m src.mcp.server search'

# Expected: Mean ~300-400ms, p95 <500ms

# 5. Benchmark search performance (FastMCP server)
hyperfine --warmup 3 --runs 20 \
  'echo "{\"query\":\"async function\"}" | python -m src.mcp.fastmcp_server search'

# Expected: Mean ~300-400ms, p95 <500ms (no regression)

# 6. Generate performance comparison report
cat > /tmp/performance_report.md <<EOF
# Performance Comparison: v3 vs FastMCP

## Indexing (10,000 files)
| Metric | v3 Server | FastMCP Server | Change |
|--------|-----------|----------------|--------|
| Duration | 54.2s | 53.8s | -0.7% ✓ |
| Files/sec | 184 | 186 | +1.1% ✓ |
| Chunks | 45,000 | 45,000 | 0% ✓ |

## Search (async function query)
| Metric | v3 Server | FastMCP Server | Change |
|--------|-----------|----------------|--------|
| Mean | 320ms | 315ms | -1.6% ✓ |
| p95 | 450ms | 440ms | -2.2% ✓ |
| p99 | 490ms | 485ms | -1.0% ✓ |

## Verdict: ✓ PASS (No performance regression)
EOF

cat /tmp/performance_report.md
```

**Expected Output**:

```markdown
# Performance Comparison: v3 vs FastMCP

## Indexing (10,000 files)
| Metric | v3 Server | FastMCP Server | Change |
|--------|-----------|----------------|--------|
| Duration | 54.2s | 53.8s | -0.7% ✓ |
| Files/sec | 184 | 186 | +1.1% ✓ |
| Chunks | 45,000 | 45,000 | 0% ✓ |

## Search (async function query)
| Metric | v3 Server | FastMCP Server | Change |
|--------|-----------|----------------|--------|
| Mean | 320ms | 315ms | -1.6% ✓ |
| p95 | 450ms | 440ms | -2.2% ✓ |
| p99 | 490ms | 485ms | -1.0% ✓ |

## Verdict: ✓ PASS (No performance regression)
```

**Success Criteria**:
- Indexing performance within ±5% (60s target for 10K files)
- Search p95 latency <500ms (no regression)
- Search mean latency within ±10%
- Memory usage comparable (measure with `/usr/bin/time -v`)
- CPU usage comparable during indexing

---

### 5. Rollback Test

**Purpose**: Verify ability to rollback to v3 server if migration encounters production issues

**Prerequisites**:
- Both v3 server and FastMCP server implementations available
- Git tags for both versions
- Claude Desktop configuration for both versions

**Step-by-Step Commands**:

```bash
# 1. Tag current state (v3 server)
git tag v3.0.0-mcp-sdk
git push origin v3.0.0-mcp-sdk

# 2. Deploy FastMCP migration
git checkout 002-refactor-mcp-server
# ... migration code ...
git tag v4.0.0-fastmcp
git push origin v4.0.0-fastmcp

# 3. Update Claude Desktop configuration (FastMCP)
cat > ~/Library/Application\ Support/Claude/claude_desktop_config.json <<EOF
{
  "mcpServers": {
    "codebase-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/cliffclarke/Claude_Code/codebase-mcp",
        "run",
        "mcp",
        "run",
        "src/mcp/fastmcp_server.py"
      ]
    }
  }
}
EOF

# 4. Test FastMCP server in Claude Desktop
# - Open Claude Desktop
# - Try search_code tool
# - Verify results appear correctly

# 5. SIMULATE PRODUCTION ISSUE (for rollback test)
# (In real scenario, this would be an actual bug discovered)

# 6. Rollback to v3 server
git checkout v3.0.0-mcp-sdk

# 7. Update Claude Desktop configuration (v3)
cat > ~/Library/Application\ Support/Claude/claude_desktop_config.json <<EOF
{
  "mcpServers": {
    "codebase-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/cliffclarke/Claude_Code/codebase-mcp",
        "run",
        "python",
        "-m",
        "src.mcp.server"
      ]
    }
  }
}
EOF

# 8. Restart Claude Desktop
# Quit and relaunch Claude Desktop app

# 9. Verify v3 server functionality
# - Open Claude Desktop
# - Try search_code tool
# - Verify results appear correctly
# - Check /tmp/codebase-mcp.log for v3 server logs

# 10. Confirm rollback success
tail -f /tmp/codebase-mcp.log
# Should see v3 server startup messages

# 11. Re-deploy FastMCP after fix (if needed)
git checkout 002-refactor-mcp-server
# ... apply fix ...
git tag v4.0.1-fastmcp
# ... repeat deployment steps ...
```

**Expected Output**:

```
# FastMCP deployment (v4.0.0)
2025-10-06 10:00:00 - INFO - Starting FastMCP server with stdio transport
2025-10-06 10:00:00 - INFO - Server startup validation passed: 6 tools registered

# Rollback to v3 (v3.0.0)
2025-10-06 10:05:00 - INFO - Starting MCP server (Python SDK v3)
2025-10-06 10:05:00 - INFO - Registered tool: search_code
2025-10-06 10:05:00 - INFO - Registered tool: index_repository
...
2025-10-06 10:05:00 - INFO - Server listening on SSE transport

# Claude Desktop working with v3 server
✓ Search results appear
✓ Indexing works
✓ Task management functional
```

**Success Criteria**:
- Rollback completes in <5 minutes
- v3 server starts successfully after rollback
- All 6 tools functional with v3 server
- Claude Desktop reconnects automatically
- No data loss (PostgreSQL data persists across rollback)
- Logs clearly indicate which version is running

---

## Summary of Validation Requirements

| Scenario | Pass Criteria | Time Estimate |
|----------|--------------|---------------|
| 1. Server Startup | 6 tools registered, no errors | 5 min |
| 2. Stdio Execution | Protocol-compliant responses | 10 min |
| 3. Integration Tests | 100% pass rate | 15 min |
| 4. Performance Benchmark | <5% regression | 30 min |
| 5. Rollback Test | v3 server functional | 10 min |

**Total Validation Time**: ~70 minutes

## Post-Migration Checklist

- [ ] All 6 tools pass integration tests
- [ ] Protocol compliance tests pass (JSON-RPC 2.0)
- [ ] Performance benchmarks show no regression
- [ ] Claude Desktop integration working
- [ ] Rollback procedure documented and tested
- [ ] Logging dual pattern verified (Context + file)
- [ ] Type hints pass mypy --strict
- [ ] No stdout/stderr pollution confirmed

## Rollback Triggers

Rollback to v3 server if ANY of the following occur:
1. Integration test pass rate <100%
2. Search p95 latency exceeds 500ms
3. Indexing time exceeds 70s for 10K files (>16% regression)
4. Protocol compliance violations detected
5. Claude Desktop connection failures
6. Data corruption or loss
7. Critical bugs discovered in production

## Migration Sign-Off

- [ ] Technical Lead approval
- [ ] QA verification (all 5 scenarios passed)
- [ ] Performance benchmarks reviewed
- [ ] Rollback plan tested and documented
- [ ] Production deployment scheduled
