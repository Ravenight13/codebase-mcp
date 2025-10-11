# Testing Strategy: Minimal but Effective

## Overview

The MCP split project adopts a "minimal but sufficient" testing approach focused on MCP protocol compliance and basic functionality. This strategy balances quality assurance with development velocity, avoiding over-testing while ensuring production readiness.

---

## Testing Philosophy

### Minimal but Sufficient

**What We Test:**
- ✅ MCP protocol compliance (tool schemas, error formats)
- ✅ Core functionality (index → search → results)
- ✅ Basic error handling (invalid inputs, missing data)
- ✅ Performance targets (latency SLAs)
- ✅ Integration points (codebase-mcp ↔ workflow-mcp)

**What We Don't Test:**
- ❌ Edge cases beyond common scenarios
- ❌ Exhaustive input validation (trust Pydantic)
- ❌ UI/UX testing (no UI in MCP servers)
- ❌ Load testing beyond performance targets
- ❌ Security testing (trust-based, local-first)

**Rationale:**
- MCPs are internal tools (not public APIs)
- FastMCP + Pydantic provide built-in validation
- Local-first architecture limits attack surface
- Development velocity prioritized over exhaustive coverage

---

## Test Categories

### 1. MCP Protocol Compliance Tests

**Purpose:** Ensure MCP specification adherence

**What to Test:**

#### Tool Registration
```python
# tests/test_mcp_compliance.py
import pytest
from fastmcp import FastMCP

def test_tool_registration():
    """Verify all tools registered with FastMCP."""
    from src.server import mcp

    tools = mcp.list_tools()
    tool_names = [tool["name"] for tool in tools]

    # Codebase-MCP expected tools
    assert "index_repository" in tool_names
    assert "search_code" in tool_names

    # Verify tool count (catch missing registrations)
    assert len(tool_names) == 2
```

#### Tool Schema Validation
```python
def test_search_code_schema():
    """Verify search_code tool schema follows MCP spec."""
    from src.server import mcp

    schema = mcp.get_tool_schema("search_code")

    # Required MCP fields
    assert "name" in schema
    assert "description" in schema
    assert "parameters" in schema

    # Parameter structure
    params = schema["parameters"]
    assert params["type"] == "object"
    assert "properties" in params
    assert "required" in params

    # Specific parameters
    properties = params["properties"]
    assert "query" in properties
    assert properties["query"]["type"] == "string"

    # Optional parameter marked correctly
    assert "project_id" in properties
    assert "query" in params["required"]
    assert "project_id" not in params["required"]  # Optional
```

#### Error Format Compliance
```python
def test_mcp_error_format():
    """Verify errors follow MCP error format (JSON-RPC 2.0)."""
    from src.tools.search_code import search_code
    from fastmcp import McpError

    # Trigger error (invalid project_id)
    with pytest.raises(McpError) as exc_info:
        await search_code(query="test", project_id="invalid-uuid")

    error = exc_info.value

    # MCP error structure
    assert hasattr(error, "code")
    assert hasattr(error, "message")
    assert hasattr(error, "data")

    # JSON-RPC 2.0 error codes
    assert error.code == -32602  # Invalid params

    # Error message is descriptive
    assert len(error.message) > 0
    assert "project_id" in error.message.lower()

    # Error data provides context
    assert "project_id" in error.data
    assert error.data["project_id"] == "invalid-uuid"
```

#### No stdout/stderr Pollution
```python
def test_no_stdout_pollution(capsys):
    """Verify no stdout/stderr output during tool execution."""
    from src.tools.search_code import search_code

    # Execute tool
    await search_code(
        query="test",
        project_id="550e8400-e29b-41d4-a716-446655440000"
    )

    # Capture output
    captured = capsys.readouterr()

    # MCP protocol requires no stdout/stderr
    assert captured.out == ""
    assert captured.err == ""

    # Note: Logging to file is allowed, just not stdout/stderr
```

**When to Run:**
- After tool implementation
- After schema changes
- Before every PR merge
- In CI/CD pipeline

**Acceptance Criteria:**
- All tools registered correctly
- All schemas valid (name, description, parameters, required fields)
- All errors use MCP format (code, message, data)
- No stdout/stderr during tool execution

---

### 2. Basic Functionality Tests

**Purpose:** Validate core workflows work end-to-end

**What to Test:**

#### Codebase-MCP: Index → Search Flow
```python
# tests/test_basic_functionality.py
import pytest
import tempfile
import os

@pytest.fixture
async def test_project():
    """Create a test project with sample code."""
    project_id = "test-proj-001"
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample Python file
        sample_file = os.path.join(tmpdir, "sample.py")
        with open(sample_file, "w") as f:
            f.write("""
def hello_world():
    print("Hello, world!")

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
""")
        yield project_id, tmpdir

async def test_index_then_search(test_project):
    """Test basic workflow: index repository then search."""
    project_id, repo_path = test_project

    # Step 1: Index repository
    from src.tools.index_repository import index_repository
    index_result = await index_repository(
        repo_path=repo_path,
        project_id=project_id
    )

    # Verify indexing succeeded
    assert index_result["status"] == "success"
    assert index_result["files_indexed"] == 1
    assert index_result["chunks_created"] > 0

    # Step 2: Search indexed code
    from src.tools.search_code import search_code
    search_result = await search_code(
        query="fibonacci function",
        project_id=project_id
    )

    # Verify search found results
    assert len(search_result["results"]) > 0

    # Verify result structure
    first_result = search_result["results"][0]
    assert "chunk_id" in first_result
    assert "file_path" in first_result
    assert "content" in first_result
    assert "similarity_score" in first_result

    # Verify content relevance
    assert "fibonacci" in first_result["content"].lower()
```

#### Workflow-MCP: Project Lifecycle
```python
# tests/test_basic_functionality.py
async def test_project_lifecycle():
    """Test basic workflow: create → switch → query."""
    from src.tools.create_project import create_project
    from src.tools.switch_project import switch_project
    from src.tools.get_active_project import get_active_project

    # Step 1: Create project
    project = await create_project(
        name="Test Project",
        description="Integration test project"
    )
    project_id = project["id"]

    assert project["name"] == "Test Project"
    assert project["status"] == "active"

    # Step 2: Switch to project
    await switch_project(project_id=project_id)

    # Step 3: Verify active project
    active = await get_active_project()
    assert active["project_id"] == project_id
```

**When to Run:**
- After core feature implementation
- After refactoring
- Before every PR merge
- In CI/CD pipeline

**Acceptance Criteria:**
- Index → search workflow completes successfully
- Search returns relevant results
- Project lifecycle (create → switch → query) works
- All tool outputs match expected schemas

---

### 3. Integration Tests

**Purpose:** Validate cross-MCP interactions

**What to Test:**

#### Codebase-MCP + Workflow-MCP Integration
```python
# tests/test_integration.py
@pytest.mark.integration
async def test_multi_project_isolation():
    """Test project isolation across both MCPs."""

    # Setup: Create two projects in workflow-mcp
    from workflow_mcp.tools.create_project import create_project as create_wf_project
    project_a = await create_wf_project(name="Project A")
    project_b = await create_wf_project(name="Project B")

    # Setup: Index same code in both projects (codebase-mcp)
    from codebase_mcp.tools.index_repository import index_repository
    await index_repository(
        repo_path="/tmp/shared-repo",
        project_id=project_a["id"]
    )
    await index_repository(
        repo_path="/tmp/shared-repo",
        project_id=project_b["id"]
    )

    # Test: Switch to Project A (workflow-mcp)
    from workflow_mcp.tools.switch_project import switch_project
    await switch_project(project_id=project_a["id"])

    # Test: Search should scope to Project A (codebase-mcp)
    from codebase_mcp.tools.search_code import search_code
    results_a = await search_code(query="test function")

    # Verify: All results from Project A
    assert all(r["project_id"] == project_a["id"] for r in results_a["results"])

    # Test: Switch to Project B
    await switch_project(project_id=project_b["id"])

    # Test: Search should scope to Project B
    results_b = await search_code(query="test function")

    # Verify: All results from Project B
    assert all(r["project_id"] == project_b["id"] for r in results_b["results"])

    # Verify: No cross-project leakage
    project_a_chunk_ids = {r["chunk_id"] for r in results_a["results"]}
    project_b_chunk_ids = {r["chunk_id"] for r in results_b["results"]}
    assert project_a_chunk_ids.isdisjoint(project_b_chunk_ids)
```

#### Project Switching with Cache Invalidation
```python
@pytest.mark.integration
async def test_project_switch_invalidates_cache():
    """Verify active project cache invalidates on switch."""
    from codebase_mcp.cache.project_cache import _project_cache
    from workflow_mcp.tools.switch_project import switch_project
    from codebase_mcp.helpers.project_helper import get_active_project

    # Setup: Get active project (caches it)
    project_a_id = await get_active_project()
    assert _project_cache.get("active_project") == project_a_id

    # Action: Switch projects
    project_b_id = "different-project-id"
    await switch_project(project_id=project_b_id)

    # Verify: Cache invalidated
    assert _project_cache.get("active_project") is None

    # Verify: Next call fetches new project
    new_active = await get_active_project()
    assert new_active == project_b_id
```

**When to Run:**
- After both MCPs implemented
- After integration point changes
- Before major releases
- In pre-deployment testing

**Acceptance Criteria:**
- Project isolation enforced (no cross-project leakage)
- Project switching updates active context
- Cache invalidation works correctly
- Both MCPs communicate via MCP protocol

---

### 4. Performance Validation Tests

**Purpose:** Ensure performance targets met

**What to Test:**

#### Search Latency (p95)
```python
# tests/test_performance.py
import pytest
import time
import statistics

@pytest.mark.performance
async def test_search_latency_p95():
    """Verify search latency <500ms at p95."""
    project_id = "perf-test-project"
    query = "function implementation"

    # Setup: Index 10K files (~50K chunks)
    await setup_large_codebase(project_id, num_files=10000)

    # Execute: 100 search queries
    latencies = []
    for i in range(100):
        start = time.time()
        await search_code(query=query, project_id=project_id)
        latency_ms = (time.time() - start) * 1000
        latencies.append(latency_ms)

    # Measure: p95 latency
    p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile

    # Verify: <500ms target
    assert p95_latency < 500, f"p95 latency {p95_latency}ms exceeds 500ms target"

    # Report: Additional metrics
    print(f"p50: {statistics.median(latencies):.1f}ms")
    print(f"p95: {p95_latency:.1f}ms")
    print(f"p99: {max(latencies):.1f}ms")
```

#### Index Creation (60s target)
```python
@pytest.mark.performance
async def test_index_creation_latency():
    """Verify indexing <60s for 10K files."""
    project_id = "index-perf-test"
    repo_path = "/tmp/large-repo"  # Pre-created with 10K files

    # Execute: Index repository
    start = time.time()
    result = await index_repository(
        repo_path=repo_path,
        project_id=project_id,
        force_reindex=True
    )
    duration = time.time() - start

    # Verify: <60s target
    assert duration < 60, f"Indexing took {duration:.1f}s, exceeds 60s target"

    # Verify: All files indexed
    assert result["files_indexed"] == 10000
    assert result["status"] == "success"
```

#### Project Switching (<50ms)
```python
@pytest.mark.performance
async def test_project_switch_latency():
    """Verify project switching <50ms."""
    project_a = await create_project(name="Project A")
    project_b = await create_project(name="Project B")

    # Warm up
    await switch_project(project_id=project_a["id"])

    # Measure: 20 switches
    latencies = []
    for i in range(20):
        target = project_a["id"] if i % 2 == 0 else project_b["id"]
        start = time.time()
        await switch_project(project_id=target)
        latency_ms = (time.time() - start) * 1000
        latencies.append(latency_ms)

    # Verify: p95 <50ms
    p95 = statistics.quantiles(latencies, n=20)[18]
    assert p95 < 50, f"Project switching p95 {p95:.1f}ms exceeds 50ms target"
```

**When to Run:**
- After performance-sensitive changes
- Before major releases
- Weekly in CI/CD (separate job)
- Manual before deployment

**Acceptance Criteria:**
- Search latency: <500ms p95
- Index creation: <60s for 10K files
- Project switching: <50ms p95
- Project creation: <200ms

**Note:** Performance tests are slower, run separately from unit tests

---

## Test Automation

### Pytest Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

# Markers for test categories
markers = [
    "unit: Unit tests (fast)",
    "integration: Integration tests (require both MCPs)",
    "performance: Performance tests (slow)",
    "mcp_compliance: MCP protocol compliance tests"
]

# Async timeout
asyncio_default_fixture_loop_scope = "function"
timeout = 300  # 5 minutes max per test

# Coverage settings
addopts = "--cov=src --cov-report=html --cov-report=term"
```

### Running Tests

#### All Tests
```bash
pytest tests/ -v
```

#### Unit Tests Only (Fast)
```bash
pytest tests/ -v -m "unit"
```

#### Integration Tests
```bash
# Requires both MCPs running
docker-compose up -d codebase-mcp workflow-mcp
pytest tests/ -v -m "integration"
```

#### Performance Tests
```bash
# Run separately (slow)
pytest tests/ -v -m "performance"
```

#### MCP Compliance Tests
```bash
pytest tests/ -v -m "mcp_compliance"
```

#### Watch Mode (Development)
```bash
pytest-watch tests/ -v
```

---

## Test Fixtures

### Database Fixtures

```python
# tests/conftest.py
import pytest
import asyncpg

@pytest.fixture(scope="session")
async def test_db():
    """Create test database for session."""
    # Create test database
    conn = await asyncpg.connect(
        host="localhost",
        user="postgres",
        password="postgres",
        database="postgres"
    )
    await conn.execute("DROP DATABASE IF EXISTS test_codebase_mcp")
    await conn.execute("CREATE DATABASE test_codebase_mcp")
    await conn.close()

    # Run migrations
    test_conn = await asyncpg.connect(
        host="localhost",
        user="postgres",
        password="postgres",
        database="test_codebase_mcp"
    )

    # Apply schema
    with open("src/database/schema.sql") as f:
        await test_conn.execute(f.read())

    yield test_conn

    # Cleanup
    await test_conn.close()
    conn = await asyncpg.connect(
        host="localhost",
        user="postgres",
        password="postgres",
        database="postgres"
    )
    await conn.execute("DROP DATABASE test_codebase_mcp")
    await conn.close()

@pytest.fixture
async def clean_db(test_db):
    """Clean all tables before each test."""
    await test_db.execute("TRUNCATE TABLE code_chunks, repositories, projects CASCADE")
    yield test_db
```

### Project Fixtures

```python
@pytest.fixture
async def test_project(clean_db):
    """Create a test project."""
    project_id = str(uuid.uuid4())
    await clean_db.execute(
        "INSERT INTO projects (id, name) VALUES ($1, $2)",
        project_id, "Test Project"
    )
    return project_id

@pytest.fixture
async def test_repository(test_project, clean_db):
    """Create a test repository with sample code."""
    repo_id = str(uuid.uuid4())
    repo_path = "/tmp/test-repo"

    # Create sample code
    os.makedirs(repo_path, exist_ok=True)
    with open(f"{repo_path}/sample.py", "w") as f:
        f.write("def test(): pass")

    # Insert into database
    await clean_db.execute(
        "INSERT INTO repositories (id, path, project_id) VALUES ($1, $2, $3)",
        repo_id, repo_path, test_project
    )

    yield repo_id, repo_path

    # Cleanup
    import shutil
    shutil.rmtree(repo_path, ignore_errors=True)
```

---

## When to Run Tests

### During Development
- **After each task:** Run relevant tests (not full suite)
  ```bash
  pytest tests/test_search_code.py -v
  ```
- **Before committing:** Run affected tests
  ```bash
  pytest tests/ -k "search or project" -v
  ```

### Before Creating PR
- **Full test suite:** All tests must pass
  ```bash
  pytest tests/ -v
  ```
- **MCP compliance:** Ensure protocol adherence
  ```bash
  pytest tests/ -v -m "mcp_compliance"
  ```
- **Coverage check:** Ensure adequate coverage
  ```bash
  pytest tests/ --cov=src --cov-report=term --cov-fail-under=80
  ```

### CI/CD Pipeline
```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e ".[test]"
      - run: pytest tests/ -v -m "unit"

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e ".[test]"
      - run: pytest tests/ -v -m "integration"

  performance-tests:
    runs-on: ubuntu-latest
    # Run weekly, not on every push
    if: github.event_name == 'schedule'
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e ".[test]"
      - run: pytest tests/ -v -m "performance"
```

---

## Test Coverage Targets

### Codebase-MCP
- **Tools:** 90% coverage (critical path)
- **Database:** 80% coverage (migrations + queries)
- **Cache:** 85% coverage (edge cases important)
- **Helpers:** 75% coverage (utility functions)
- **Overall:** 80% minimum

### Workflow-MCP
- **Tools:** 90% coverage (critical path)
- **Database:** 80% coverage (entity relationships)
- **Session management:** 85% coverage (state critical)
- **Overall:** 80% minimum

**Rationale:**
- Focus on critical paths (tools, database)
- Lower coverage acceptable for utilities
- 80% balances quality with velocity

---

## Testing Anti-Patterns (Avoid)

### ❌ Over-Testing
```python
# Don't test Pydantic validation (trust the library)
def test_search_code_rejects_negative_limit():
    """Pydantic already validates this!"""
    with pytest.raises(ValidationError):
        await search_code(query="test", limit=-1)
```

### ❌ Testing Implementation Details
```python
# Don't test private methods
def test_private_cache_eviction():
    """Internal implementation, may change"""
    cache = ProjectCache()
    cache._evict_lru()  # Private method
    assert cache._size == 0
```

### ❌ Slow Tests in Unit Test Suite
```python
# Don't put slow tests with fast tests
def test_search_with_large_codebase():
    """This belongs in performance tests, not unit tests"""
    # Indexes 100K files...
```

### ❌ Tests with External Dependencies
```python
# Don't rely on external services
def test_search_code():
    """Don't rely on real Ollama server"""
    # Calls live Ollama API...
    # Use mock instead!
```

---

## Mocking Strategies

### Mock External Dependencies

```python
# tests/test_search_code.py
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_search_code_with_mock_embeddings():
    """Test search without calling real embedding service."""

    # Mock embedding generation
    mock_embedding = [0.1] * 768  # Fake embedding vector

    with patch('src.embeddings.generate_embedding', new=AsyncMock(return_value=mock_embedding)):
        result = await search_code(
            query="test query",
            project_id="test-project-id"
        )

    # Verify search executed (with fake embedding)
    assert len(result["results"]) >= 0
```

### Mock Workflow-MCP Integration

```python
@pytest.mark.asyncio
async def test_get_active_project_with_mock():
    """Test active project retrieval without workflow-mcp."""

    mock_project_id = "mock-project-123"

    with patch('src.helpers.project_helper.workflow_mcp.call_tool',
               new=AsyncMock(return_value={"current_session_id": mock_project_id})):
        project_id = await get_active_project()

    assert project_id == mock_project_id
```

---

## Summary

**Test Categories:**
1. **MCP Protocol Compliance** - Tool registration, schemas, error formats
2. **Basic Functionality** - Core workflows (index → search)
3. **Integration Tests** - Cross-MCP interactions
4. **Performance Validation** - Latency SLAs

**When to Run:**
- Unit tests: After each task, before commit
- Integration tests: Before PR, in CI/CD
- Performance tests: Weekly, before releases

**Test Automation:**
- Pytest with async support
- Fixtures for database, projects, repositories
- Docker Compose for integration tests
- CI/CD pipeline with separate jobs

**Coverage Targets:**
- Tools: 90% (critical)
- Database: 80%
- Overall: 80% minimum

**Key Principles:**
- Minimal but sufficient (don't over-test)
- Trust Pydantic + FastMCP (don't test library code)
- Mock external dependencies (Ollama, workflow-mcp)
- Fast unit tests, separate performance tests
- Focus on protocol compliance + core workflows
