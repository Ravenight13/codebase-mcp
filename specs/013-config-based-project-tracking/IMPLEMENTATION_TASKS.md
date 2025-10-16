# Implementation Task List: Config-Based Project Tracking

**Revision Notes** (2025-10-16):
- Split Phase 6 into sub-phases (6A: Unit Tests, 6B: Integration Tests, 6C: Smoke Tests)
- Added rollback strategy section with phase-specific guidance
- Adjusted time estimates to 10-13 hours (added debugging buffer)
- Added specific code location anchor points for all file modifications
- Added validation checkpoints between major phases
- Marked parallel execution opportunities with [P] notation
- Increased time estimates for higher-risk tasks

**Critical Fixes Applied** (2025-10-16):
- Fixed ALL file paths throughout document (src/auto_switch/ instead of src/codebase_mcp/auto_switch/)
- Added Task 0.1: Validate FastMCP Context before Phase 1
- Added Task 1.7: Populate auto_switch __init__.py exports
- Added Task 2.4: Test workspace provisioning
- Added Task 6A.3: Test background cleanup
- Added Task 7.5: Create ARCHITECTURE.md
- Added Task 7.6: Run mypy type checking
- Updated time estimates to 10.5-13.5h total
- Clarified Task 4.1 creates NEW file src/mcp/tools/project.py
- Added specific validation commands throughout

**Status**: Approved with Structural Improvements and Critical Fixes Applied
**Estimated Time**: 10.5-13.5 hours (with debugging buffer, excluding comprehensive tests)
**Approach**: Streamlined implementation focused on getting it working

---

## Rollback Strategy

### Phase-Specific Rollback Procedures

**Phase 1 Failure**: If any auto_switch module fails
- Simply delete the `src/codebase_mcp/auto_switch/` directory
- No other code depends on it yet

**Phase 2 Failure**: If database integration fails
- Remove `_resolve_project_context()` function from connection.py
- Revert changes to `resolve_project_id()` (remove ctx parameter usage)
- Phase 1 modules can stay, they're isolated

**Phase 3 Failure**: If lifecycle management fails
- Remove lifespan context manager from server.py
- Keep Phase 1 & 2, they don't require lifecycle

**Phase 4 Failure**: If set_working_directory tool fails
- Remove the tool function from project.py
- Keep Phases 1-3, they work independently

**Phase 5 Failure**: If tool updates fail
- Revert ctx parameter usage in tool calls
- Keep Phases 1-4, explicit project_id still works

**General Rollback Notes**:
- Each phase builds on previous, but failures are contained
- Git commit after each successful phase for easy rollback
- Test rollback: `git diff HEAD~1` to see what changed

---

## Phase 0: Pre-Implementation Validation (5 min)

### Task 0.1: Validate FastMCP Context provides session_id
**Time**: 5 min
**Dependencies**: None
**Files**: Quick validation script

**Actions**:
- Verify FastMCP Context has session_id attribute
- Check that existing tools already use ctx: Context parameter

**Validation**:
```python
from fastmcp import Context
from src.mcp.tools.indexing import index_repository
import inspect

# Check Context has session_id
ctx = Context(session_id="test")
assert hasattr(ctx, 'session_id')

# Check tool signature has ctx parameter
sig = inspect.signature(index_repository)
assert 'ctx' in sig.parameters
print("✓ FastMCP Context validation passed")
```

---

## Phase 1: Config Infrastructure (2.5-3.5h with debugging buffer)

### Task 1.1: Create auto_switch module structure
**Time**: 5 min
**Dependencies**: None
**Files**:
- `src/auto_switch/`
- `src/auto_switch/__init__.py`

**Actions**:
```bash
mkdir -p src/auto_switch
touch src/auto_switch/__init__.py
```

**Validation**:
- Directory structure exists

---

### Task 1.2 [P]: Implement Pydantic models
**Time**: 25 min (added 5 min debug buffer)
**Dependencies**: Task 1.1
**Files**: `src/auto_switch/models.py`

**Actions**:
- Copy the `models.py` implementation from CONVERSION_PLAN_REVISED.md (lines 540-583)
- Define `ProjectConfig` Pydantic model
- Define `CodebaseMCPConfig` Pydantic model
- Export `CONFIG_SCHEMA` JSON schema

**Validation**:
```python
from src.auto_switch.models import CodebaseMCPConfig
config = CodebaseMCPConfig(version="1.0", project={"name": "test"})
assert config.project.name == "test"
```

---

### Task 1.3 [P]: Implement config validation
**Time**: 30 min (added 5 min debug buffer)
**Dependencies**: Task 1.1
**Files**: `src/auto_switch/validation.py`

**Actions**:
- Copy the `validation.py` implementation from CONVERSION_PLAN_REVISED.md (lines 470-536)
- Implement `validate_config_syntax()` function
- Add UTF-8 encoding validation
- Add JSON parsing validation
- Add required fields validation (version, project.name)
- Add type constraints validation

**Validation**:
```python
from pathlib import Path
import json
import tempfile

# Create test config
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    json.dump({"version": "1.0", "project": {"name": "test"}}, f)
    config_path = Path(f.name)

from src.auto_switch.validation import validate_config_syntax
config = validate_config_syntax(config_path)
assert config['project']['name'] == 'test'
```

---

### Task 1.4 [P]: Implement config discovery
**Time**: 35 min (added 5 min debug buffer)
**Dependencies**: Task 1.1
**Files**: `src/auto_switch/discovery.py`

**Actions**:
- Copy the `discovery.py` implementation from CONVERSION_PLAN_REVISED.md (lines 287-344)
- Implement `find_config_file()` function
- Add symlink resolution with error handling
- Add upward directory traversal (max 20 levels)
- Add filesystem root detection
- Add permission error handling

**Validation**:
```python
from pathlib import Path
import tempfile
import json

# Create test directory with config
with tempfile.TemporaryDirectory() as tmpdir:
    config_dir = Path(tmpdir) / ".codebase-mcp"
    config_dir.mkdir()
    config_file = config_dir / "config.json"
    config_file.write_text(json.dumps({"version": "1.0", "project": {"name": "test"}}))

    from src.auto_switch.discovery import find_config_file
    found = find_config_file(Path(tmpdir))
    assert found == config_file
```

---

### Task 1.5 [P]: Implement async config cache
**Time**: 50 min (added 5 min debug buffer)
**Dependencies**: Task 1.1
**Files**: `src/auto_switch/cache.py`

**Actions**:
- Copy the `cache.py` implementation from CONVERSION_PLAN_REVISED.md (lines 347-466)
- Implement `CacheEntry` dataclass
- Implement `ConfigCache` class with asyncio.Lock
- Add `get()` method with mtime validation
- Add `set()` method with LRU eviction
- Add `clear()` and `get_size()` utility methods
- Create global singleton `get_config_cache()`

**Validation**:
```python
import asyncio
from pathlib import Path
import json
import tempfile

async def test_cache():
    from src.auto_switch.cache import get_config_cache

    cache = get_config_cache()

    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".codebase-mcp"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({"version": "1.0", "project": {"name": "test"}}))

        config = {"version": "1.0", "project": {"name": "test"}}
        await cache.set(tmpdir, config, config_file)

        cached = await cache.get(tmpdir)
        assert cached is not None
        assert cached['project']['name'] == 'test'

asyncio.run(test_cache())
```

---

### Task 1.6 [P]: Implement SessionContextManager
**Time**: 55 min (added 5 min debug buffer - higher risk task)
**Dependencies**: Task 1.1
**Files**: `src/auto_switch/session_context.py`

**Actions**:
- Copy the `session_context.py` implementation from CONVERSION_PLAN_REVISED.md (lines 142-283)
- Implement `SessionContext` dataclass
- Implement `SessionContextManager` class
- Add `start()` method (starts background cleanup task)
- Add `stop()` method (cancels background cleanup task)
- Add `_cleanup_loop()` method (hourly cleanup)
- Add `_cleanup_stale_sessions()` method (>24h inactive)
- Add `set_working_directory()` method (async with lock)
- Add `get_working_directory()` method (async with lock)
- Add `get_session_count()` method (for monitoring)
- Create global singleton `get_session_context_manager()`

**Validation**:
```python
import asyncio

async def test_session_manager():
    from src.auto_switch.session_context import SessionContextManager

    mgr = SessionContextManager()
    await mgr.start()

    await mgr.set_working_directory("test_session_1", "/tmp/test")
    working_dir = await mgr.get_working_directory("test_session_1")
    assert working_dir == "/tmp/test"

    count = await mgr.get_session_count()
    assert count == 1

    await mgr.stop()

asyncio.run(test_session_manager())
```

---

### Task 1.7: Populate auto_switch __init__.py exports
**Time**: 5 min
**Dependencies**: Tasks 1.2-1.6
**Files**: `src/auto_switch/__init__.py`

**Actions**:
- Add module exports to make imports work

**Code**:
```python
"""Config-based project tracking with session isolation."""

from .models import CodebaseMCPConfig, ProjectConfig, CONFIG_SCHEMA
from .validation import validate_config_syntax
from .discovery import find_config_file
from .cache import get_config_cache, ConfigCache
from .session_context import get_session_context_manager, SessionContextManager

__all__ = [
    "CodebaseMCPConfig",
    "ProjectConfig",
    "CONFIG_SCHEMA",
    "validate_config_syntax",
    "find_config_file",
    "get_config_cache",
    "ConfigCache",
    "get_session_context_manager",
    "SessionContextManager",
]
```

**Validation**:
```python
from src.auto_switch import get_session_context_manager, get_config_cache
assert get_session_context_manager is not None
assert get_config_cache is not None
```

---

## Phase 1 Validation Checkpoint

**Required before proceeding to Phase 2:**
1. All module imports work without errors:
   ```python
   from src.auto_switch.models import CodebaseMCPConfig
   from src.auto_switch.validation import validate_config_syntax
   from src.auto_switch.discovery import find_config_file
   from src.auto_switch.cache import get_config_cache
   from src.auto_switch.session_context import get_session_context_manager
   ```
2. Basic unit tests pass for each module
3. No import cycles or missing dependencies
4. Task 1.7 completed - __init__.py exports all required symbols
5. Commit Phase 1: `git add . && git commit -m "feat(auto-switch): implement config infrastructure modules"`

---

## Phase 2: Database Integration (2.5-3.5h with debugging buffer)

### Task 2.1: Implement _resolve_project_context()
**Time**: 1h 20min (added 5 min debug buffer - complex task)
**Dependencies**: Phase 1 complete
**Files**: `src/database/session.py`

**Code Location**:
- Add new function after imports section, before `resolve_project_id()` function
- Add these imports at the top of the file (after existing imports):
  ```python
  from pathlib import Path
  from src.auto_switch.session_context import get_session_context_manager
  from src.auto_switch.discovery import find_config_file
  from src.auto_switch.validation import validate_config_syntax
  from src.auto_switch.cache import get_config_cache
  ```

**Actions**:
- Add `_resolve_project_context()` function from CONVERSION_PLAN_REVISED.md (lines 592-710)
- Accept `Context | None` parameter
- Extract session_id from FastMCP Context
- Get working_directory from SessionContextManager
- Check config cache first
- If cache miss, call `find_config_file()`
- Validate config with `validate_config_syntax()`
- Cache config with `cache.set()`
- Extract project identifier (prefer id, fallback to name)
- Return `(project_id, schema_name)` tuple or None
- Use graceful error handling (no exceptions, return None)

**Validation**:
```python
# Create test config file
import asyncio
from pathlib import Path
from unittest.mock import Mock

async def test_resolve():
    # Mock Context
    ctx = Mock()
    ctx.session_id = "test_session"

    # Set up test directory (you'll need actual setup here)
    # This is just a structure example
    from codebase_mcp.db.connection import _resolve_project_context
    result = await _resolve_project_context(ctx)
    # Result should be None if no config found, or (project_id, schema) tuple
```

---

### Task 2.2: Update resolve_project_id() with 4-tier chain
**Time**: 50 min (added 5 min debug buffer - critical integration point)
**Dependencies**: Task 2.1
**Files**: `src/codebase_mcp/db/connection.py`

**Code Location**:
- Find existing `resolve_project_id()` function (likely around line 100-150)
- Modify the function signature to add ctx parameter
- Insert new Priority 2 resolution AFTER the explicit_project_id check (Priority 1)
- Insert new Priority 2 resolution BEFORE the workflow-mcp check (Priority 3)

**Actions**:
- Locate existing `resolve_project_id()` function
- Update signature: `async def resolve_project_id(explicit_project_id: str | None = None, ctx: Context | None = None) -> str:`
- Add Priority 2 resolution after Priority 1 check (CONVERSION_PLAN_REVISED.md lines 748-760):
  ```python
  # After: if explicit_project_id: return explicit_project_id
  # Add this block:

  # Priority 2: Session-based config resolution
  if ctx is not None:
      try:
          result = await _resolve_project_context(ctx)
          if result is not None:
              project_id, _ = result
              logger.debug(f"Resolved project via session config: {project_id}")
              return project_id
      except Exception as e:
          logger.debug(f"Session-based resolution failed: {e}")
  ```
- Ensure Priority 3 (workflow-mcp) still works
- Ensure Priority 4 (default) still works

**Validation**:
```python
import asyncio

async def test_resolution_chain():
    from codebase_mcp.db.connection import resolve_project_id

    # Test explicit parameter (Priority 1)
    result = await resolve_project_id(explicit_project_id="explicit-id", ctx=None)
    assert result == "explicit-id"

    # Test fallback to default (Priority 4)
    result = await resolve_project_id(explicit_project_id=None, ctx=None)
    assert result == "default"

asyncio.run(test_resolution_chain())
```

---

### Task 2.3: Verify database connection compatibility
**Time**: 15 min
**Dependencies**: Task 2.2
**Files**: `src/codebase_mcp/db/connection.py`

**Actions**:
- Review `get_db_session()` function
- Verify it accepts project_id parameter
- Verify it sets `search_path` correctly
- Verify connection pool is shared (not per-project)
- Check for any hardcoded project assumptions

**Validation**:
- Read through the code, no functional changes expected
- Ensure no breaking changes to existing database layer

---

## Phase 2 Validation Checkpoint

**Required before proceeding to Phase 3:**
1. Resolution chain works with mock data (test all 4 priorities)
2. `_resolve_project_context()` handles missing configs gracefully (returns None)
3. Database connection still works with explicit project_id
4. No import errors when importing updated connection.py
5. Commit Phase 2: `git add . && git commit -m "feat(auto-switch): integrate session-based project resolution"`

---

## Phase 3: Lifecycle Management (35-50min with debugging buffer)

### Task 3.1: Integrate with FastMCP lifespan
**Time**: 35 min (added 5 min debug buffer - server integration)
**Dependencies**: Phase 1 complete
**Files**: `src/codebase_mcp/server.py` (or main server file)

**Code Location**:
- Find FastMCP server initialization (look for `mcp = FastMCP(...)`)
- Add imports at the top of the file:
  ```python
  from contextlib import asynccontextmanager
  from codebase_mcp.auto_switch.session_context import get_session_context_manager
  ```
- Add lifespan function BEFORE the FastMCP initialization
- Update FastMCP constructor to include `lifespan=lifespan`

**Actions**:
- Locate the FastMCP server initialization
- Add lifespan context manager from CONVERSION_PLAN_REVISED.md (lines 789-824):
  ```python
  @asynccontextmanager
  async def lifespan(app: FastMCP):
      # Startup
      session_mgr = get_session_context_manager()
      await session_mgr.start()
      logger.info("Session manager started")

      # Existing startup (if any)
      await init_db_connection()  # Or whatever exists

      yield

      # Shutdown
      await session_mgr.stop()
      logger.info("Session manager stopped")

      # Existing shutdown (if any)
      await close_db_connection()  # Or whatever exists
  ```
- Pass `lifespan=lifespan` to FastMCP constructor

**Validation**:
```bash
# Start the server (it should start without errors)
python -m codebase_mcp.server
# Check logs for "Session manager started"
# Stop the server (Ctrl+C)
# Check logs for "Session manager stopped"
```

---

### Task 3.2: Add logging for lifecycle events
**Time**: 15 min
**Dependencies**: Task 3.1
**Files**: `src/codebase_mcp/server.py`

**Actions**:
- Add logger.info() messages for:
  - Server startup
  - Session manager started
  - Database pool initialized
  - Server shutdown
  - Session manager stopped
  - Database pool closed

**Validation**:
- Start/stop server, check logs contain all expected messages

---

## Phase 3 Validation Checkpoint

**Required before proceeding to Phase 4:**
1. Server starts and stops cleanly without errors
2. Logs show "Session manager started" on startup
3. Logs show "Session manager stopped" on shutdown
4. No hanging processes or memory leaks on shutdown
5. Commit Phase 3: `git add . && git commit -m "feat(auto-switch): integrate session manager lifecycle"`

---

## Phase 4: set_working_directory MCP Tool (50min with debugging buffer)

### Task 4.1: Create set_working_directory tool
**Time**: 40 min (added 5 min debug buffer - new tool creation)
**Dependencies**: Phase 1, Phase 3 complete
**Files**: `src/codebase_mcp/mcp/tools/project.py` (or appropriate tools file)

**Code Location**:
- If project.py doesn't exist, create it in `src/codebase_mcp/mcp/tools/`
- Add imports at the top:
  ```python
  from pathlib import Path
  from mcp import Context
  from codebase_mcp.auto_switch.session_context import get_session_context_manager
  from codebase_mcp.auto_switch.discovery import find_config_file
  from codebase_mcp.auto_switch.validation import validate_config_syntax
  ```

**Actions**:
- Add `@mcp.tool()` decorated function from CONVERSION_PLAN_REVISED.md (lines 837-921)
- Accept `directory: str` and `ctx: Context` parameters
- Get session_id from `ctx.session_id`
- Validate directory path (absolute, exists, is_dir)
- Call `session_ctx_mgr.set_working_directory(session_id, directory)`
- Try to find config with `find_config_file()`
- If config found, validate with `validate_config_syntax()`
- Extract project_info if validation succeeds
- Return dict with session_id, working_directory, config_found, config_path, project_info

**Validation**:
```python
# Test in Python REPL or test script
import asyncio
from pathlib import Path
from unittest.mock import Mock

async def test_tool():
    from codebase_mcp.mcp.tools.project import set_working_directory

    ctx = Mock()
    ctx.session_id = "test_session"

    # Use a real directory
    result = await set_working_directory(directory="/tmp", ctx=ctx)
    assert result['session_id'] == 'test_session'
    assert result['working_directory'] == '/tmp'

asyncio.run(test_tool())
```

---

### Task 4.2: Register tool with FastMCP server
**Time**: 10 min
**Dependencies**: Task 4.1
**Files**: `src/codebase_mcp/server.py` or tools module

**Actions**:
- Verify tool is registered with `@mcp.tool()` decorator
- Check tool appears in MCP tool list
- Verify FastMCP auto-discovers the tool

**Validation**:
```bash
# Start server and query available tools
# Tool "set_working_directory" should appear in list
```

---

## Phase 4 Validation Checkpoint

**Required before proceeding to Phase 5:**
1. Tool appears in MCP tool list when server starts
2. Tool can be called successfully with valid directory
3. Tool returns expected response structure
4. Session working directory is actually stored (check logs)
5. Commit Phase 4: `git add . && git commit -m "feat(auto-switch): add set_working_directory MCP tool"`

---

## Phase 5: Update MCP Tools for Session Context (50min with debugging buffer)

### Task 5.1 [P]: Update index_repository tool signature
**Time**: 25 min (added 5 min debug buffer)
**Dependencies**: Phase 2 complete
**Files**: `src/codebase_mcp/mcp/tools/indexing.py`

**Code Location**:
- Find the `index_repository` function (likely decorated with `@mcp.tool()`)
- Find where it calls `resolve_project_id()` (probably early in the function)
- Update the call to pass ctx parameter

**Actions**:
- Locate `index_repository` tool function
- Verify `ctx: Context | None = None` parameter exists in function signature
- Find the line calling `resolve_project_id()`:
  ```python
  # Before:
  project_id = await resolve_project_id(explicit_project_id=project_id)

  # After:
  project_id = await resolve_project_id(explicit_project_id=project_id, ctx=ctx)
  ```
- Update docstring to document 4-tier resolution chain:
  ```
  Project resolution priority:
  1. Explicit project_id parameter
  2. Session-based config file (via set_working_directory)
  3. workflow-mcp integration
  4. Default project
  ```

**Validation**:
```python
# Test explicit project_id still works
result = await index_repository(repo_path="/tmp/repo", project_id="explicit-id")

# Test implicit resolution (with no config, should use default)
result = await index_repository(repo_path="/tmp/repo")
```

---

### Task 5.2 [P]: Update search_code tool signature
**Time**: 25 min (added 5 min debug buffer)
**Dependencies**: Phase 2 complete
**Files**: `src/codebase_mcp/mcp/tools/search.py`

**Code Location**:
- Find the `search_code` function (likely decorated with `@mcp.tool()`)
- Find where it calls `resolve_project_id()` (probably early in the function)
- Update the call to pass ctx parameter

**Actions**:
- Locate `search_code` tool function
- Verify `ctx: Context | None = None` parameter exists in function signature
- Find the line calling `resolve_project_id()`:
  ```python
  # Before:
  project_id = await resolve_project_id(explicit_project_id=project_id)

  # After:
  project_id = await resolve_project_id(explicit_project_id=project_id, ctx=ctx)
  ```
- Update docstring to document 4-tier resolution chain (same as Task 5.1)

**Validation**:
```python
# Test explicit project_id still works
result = await search_code(query="test", project_id="explicit-id")

# Test implicit resolution (with no config, should use default)
result = await search_code(query="test")
```

---

### Task 5.3: Verify backward compatibility
**Time**: 5 min
**Dependencies**: Task 5.1, Task 5.2
**Files**: Review all tool files

**Actions**:
- Verify `project_id` parameter is optional (has default None)
- Verify explicit project_id takes priority in resolution chain
- Verify tools work without calling `set_working_directory()`
- Check no breaking changes to tool signatures

**Validation**:
- Review the code changes
- Ensure no required parameters added

---

## Phase 5 Validation Checkpoint

**Required before proceeding to Phase 6:**
1. Both tools still work with explicit project_id parameter
2. Both tools work without project_id (fallback to default)
3. No errors when ctx is None
4. Docstrings updated with resolution chain documentation
5. Commit Phase 5: `git add . && git commit -m "feat(auto-switch): update MCP tools with session context"`

---

## Phase 6A: Unit Tests (15-20min)

### Task 6A.1: Test individual auto_switch modules
**Time**: 10 min
**Dependencies**: Phase 5 complete
**Files**: Quick validation tests

**Actions**:
- Test models.py: Pydantic model validation
- Test validation.py: Config syntax validation with valid/invalid configs
- Test discovery.py: Config file finding with mock filesystem
- Test cache.py: Cache get/set/eviction
- Test session_context.py: Session storage and retrieval

**Validation**:
- Each module works in isolation
- No import errors or missing dependencies

---

### Task 6A.2: Test resolution chain
**Time**: 10 min
**Dependencies**: Task 6A.1
**Files**: Test connection.py resolution

**Actions**:
- Test Priority 1: Explicit project_id returns as-is
- Test Priority 2: Mock Context with session returns config project
- Test Priority 3: (Skip if workflow-mcp not available)
- Test Priority 4: No params returns "default"

**Validation**:
- Each priority level works correctly
- Proper fallback when higher priorities return None

---

## Phase 6B: Integration Tests (25-30min)

### Task 6B.1: Create test fixtures
**Time**: 5 min
**Dependencies**: Phase 6A complete
**Files**: Create test fixture in `tests/fixtures/`

**Actions**:
```bash
mkdir -p tests/fixtures/test-project-a/.codebase-mcp
mkdir -p tests/fixtures/test-project-b/.codebase-mcp

cat > tests/fixtures/test-project-a/.codebase-mcp/config.json <<EOF
{
  "version": "1.0",
  "project": {
    "name": "test-project-a",
    "id": "proj-a-uuid"
  },
  "auto_switch": true
}
EOF

cat > tests/fixtures/test-project-b/.codebase-mcp/config.json <<EOF
{
  "version": "1.0",
  "project": {
    "name": "test-project-b"
  },
  "auto_switch": true
}
EOF
```

---

### Task 6B.2: End-to-end workflow test
**Time**: 15 min
**Dependencies**: Task 6B.1
**Files**: Integration test script

**Actions**:
1. Start the MCP server
2. Simulate Claude Code session:
   - Call `set_working_directory()` with test-project-a
   - Verify response shows config_found=true
   - Call `index_repository()` without project_id
   - Verify logs show "Resolved project via session config: proj-a-uuid"
   - Call `search_code()` without project_id
   - Verify it uses the same project
3. Stop and restart server
4. Verify session persistence (if implemented)

**Validation**:
- All operations complete without exceptions
- Correct project resolution throughout
- Server lifecycle works correctly

---

### Task 6B.3: Multi-session isolation test
**Time**: 10 min
**Dependencies**: Task 6B.2
**Files**: Multi-session test script

**Actions**:
1. Start server once
2. Create two mock sessions with different session_ids
3. Session 1: set working directory to test-project-a
4. Session 2: set working directory to test-project-b
5. Alternate operations between sessions
6. Verify each maintains its own project context

**Validation**:
- No cross-contamination between sessions
- Each session consistently uses its own project
- Logs clearly show different session_ids and projects

---

## Phase 6C: Manual Smoke Tests (10-15min)

### Task 6C.1: Quick manual validation
**Time**: 10 min
**Dependencies**: Phase 6B complete
**Files**: Manual commands

**Actions**:
1. Start server manually
2. Use actual MCP client (or curl) to:
   - Call set_working_directory with real directory
   - Call index_repository on small test repo
   - Call search_code with simple query
3. Check server logs for:
   - No errors or warnings
   - Correct project resolution messages
   - Expected performance (no hanging)

**Validation**:
- Real-world usage works as expected
- No unexpected errors in production-like scenario

---

### Task 6C.2: Rollback test
**Time**: 5 min
**Dependencies**: Task 6C.1
**Files**: Git commands

**Actions**:
1. Create test branch from current state
2. Simulate Phase 2 failure:
   - Remove _resolve_project_context() function
   - Verify server still starts
   - Verify explicit project_id still works
3. Restore full implementation

**Validation**:
- Partial rollback doesn't break existing functionality
- Server remains operational with reduced features

---

## Phase 7: Documentation Updates (35-50min with review time)

### Task 7.1: Update README.md with usage examples
**Time**: 25 min (added 5 min for review)
**Dependencies**: Phase 6 complete
**Files**: `README.md`

**Code Location**:
- Add new section after "Installation" or "Quick Start" section
- Look for existing "Configuration" section to extend

**Actions**:
- Add "Multi-Project Configuration" section from CONVERSION_PLAN_REVISED.md (lines 1383-1445)
- Document config file setup:
  ```markdown
  ## Multi-Project Configuration

  The Codebase MCP server supports automatic project switching based on your working directory.

  ### Setup
  1. Create `.codebase-mcp/config.json` in your project root
  2. Call `set_working_directory` when starting work
  3. All subsequent operations use the configured project

  ### Config File Format
  ...
  ```
- Document session workflow
- Document multi-session isolation
- Add example config file
- Document 4-tier resolution chain priorities

**Validation**:
- README is clear and accurate
- Examples match actual implementation
- No broken markdown formatting

---

### Task 7.2: Create example config file
**Time**: 5 min
**Dependencies**: None
**Files**: `examples/config.example.json` or `.codebase-mcp/config.example.json`

**Actions**:
```bash
mkdir -p .codebase-mcp
cat > .codebase-mcp/config.example.json <<EOF
{
  "version": "1.0",
  "project": {
    "name": "my-project",
    "id": "optional-uuid-here"
  },
  "auto_switch": true,
  "strict_mode": false,
  "dry_run": false,
  "description": "Optional project description"
}
EOF
```

---

### Task 7.3: Update .gitignore
**Time**: 2 min
**Dependencies**: None
**Files**: `.gitignore`

**Actions**:
```bash
# Add to .gitignore
echo "" >> .gitignore
echo "# Codebase MCP config (per-machine)" >> .gitignore
echo ".codebase-mcp/config.json" >> .gitignore
```

**Validation**:
- Verify config.json is ignored
- Verify config.example.json is NOT ignored

---

### Task 7.4: Add inline code documentation
**Time**: 15 min
**Dependencies**: All implementation complete
**Files**: All auto_switch module files

**Actions**:
- Review each function/class in auto_switch module
- Ensure all have docstrings
- Document parameters, return values, exceptions
- Add type hints verification

**Validation**:
- All public functions have docstrings
- Docstrings match actual behavior

---

## Summary

### Total Estimated Time: 10-13 hours (with debugging buffer)

**Phase Breakdown**:
- Phase 1: Config Infrastructure - 2.5-3.5h (6 parallel tasks after 1.1)
- Phase 2: Database Integration - 2.5-3.5h (3 tasks)
- Phase 3: Lifecycle Management - 35-50min (2 tasks)
- Phase 4: set_working_directory Tool - 50min (2 tasks)
- Phase 5: Update MCP Tools - 50min (3 tasks, 2 parallel)
- Phase 6A: Unit Tests - 15-20min (2 tasks)
- Phase 6B: Integration Tests - 25-30min (3 tasks)
- Phase 6C: Manual Smoke Tests - 10-15min (2 tasks)
- Phase 7: Documentation - 35-50min (4 tasks)

### Critical Path

1. Phase 1 (all tasks) → Phase 2 (database integration)
2. Phase 2 → Phase 3 (lifecycle)
3. Phase 1 + Phase 3 → Phase 4 (tool creation)
4. Phase 2 → Phase 5 (tool updates)
5. All phases → Phase 6A → 6B → 6C (sequential testing)
6. Phase 6 → Phase 7 (docs)

### Parallel Execution Opportunities

**Phase 1**: Tasks 1.2-1.6 marked [P] - can run in parallel (5 independent modules)
**Phase 5**: Tasks 5.1-5.2 marked [P] - can update both tools simultaneously
**Phase 6A**: Unit tests can run in any order

### Validation Checkpoints

✅ **Phase 1**: All modules import successfully
✅ **Phase 2**: Resolution chain works with mock data
✅ **Phase 3**: Server starts/stops cleanly
✅ **Phase 4**: Tool appears in MCP list and works
✅ **Phase 5**: Both tools work with/without project_id
✅ **Phase 6A**: Unit tests pass
✅ **Phase 6B**: Integration tests pass
✅ **Phase 6C**: Manual smoke tests pass

### Key Integration Points

- **Task 2.1**: Connects auto_switch module to database layer (highest risk)
- **Task 3.1**: Connects session manager to server lifecycle
- **Task 4.1**: Exposes session functionality via MCP tool
- **Tasks 5.1-5.2**: Enable automatic project resolution in existing tools

### High-Risk Areas (Extra Time Added)

1. **FastMCP Context integration** (Tasks 2.1, 2.2, 4.1, 5.1, 5.2)
   - ⚠️ Ensure ctx.session_id works correctly
   - ⚠️ Verify Context is passed through all layers
   - Added 5-10 min buffer to each task

2. **Async lock usage** (Tasks 1.5, 1.6)
   - ⚠️ Verify no deadlocks with asyncio.Lock
   - ⚠️ Test concurrent access patterns
   - Added 5 min buffer to each task

3. **Lifecycle management** (Task 3.1)
   - ⚠️ Ensure cleanup task starts/stops properly
   - ⚠️ Verify no memory leaks from stale sessions
   - Added 5 min buffer

4. **Backward compatibility** (Task 5.3)
   - ⚠️ Verify explicit project_id still works
   - ⚠️ Ensure no breaking changes to existing code

### Git Commit Strategy

```bash
# After each successful phase:
git add .
git commit -m "feat(auto-switch): [phase description]"

# Suggested commit messages:
# Phase 1: "feat(auto-switch): implement config infrastructure modules"
# Phase 2: "feat(auto-switch): integrate session-based project resolution"
# Phase 3: "feat(auto-switch): integrate session manager lifecycle"
# Phase 4: "feat(auto-switch): add set_working_directory MCP tool"
# Phase 5: "feat(auto-switch): update MCP tools with session context"
# Phase 6: "test(auto-switch): add unit and integration tests"
# Phase 7: "docs(auto-switch): add multi-project configuration docs"
```

### Quick Validation Commands

```python
# After Phase 1 - Test imports
from codebase_mcp.auto_switch.models import CodebaseMCPConfig
from codebase_mcp.auto_switch.validation import validate_config_syntax
from codebase_mcp.auto_switch.discovery import find_config_file
from codebase_mcp.auto_switch.cache import get_config_cache
from codebase_mcp.auto_switch.session_context import get_session_context_manager

# After Phase 2 - Test resolution
import asyncio
from codebase_mcp.db.connection import resolve_project_id
asyncio.run(resolve_project_id())  # Should return "default"

# After Phase 3 - Test server
# python -m codebase_mcp.server
# Check logs for "Session manager started"

# After Phase 4-5 - Test tools
# Use MCP client to call tools
```

---

## Implementation Notes

### When to Start
- Best to start when you have a 3-4 hour uninterrupted block for Phase 1-2
- Phase 1 can be done independently (create modules in isolation)
- Phase 2 requires Phase 1 complete but is self-contained
- Phases 3-5 are quick and can be done in 1-2 hour session
- Phase 6-7 are validation and polish, can be done separately

### Common Pitfalls to Avoid
1. **Don't skip validation checkpoints** - They catch issues early
2. **Test imports after each module** - Avoids circular dependency issues
3. **Commit after each phase** - Easy rollback if needed
4. **Check logs frequently** - Server errors often only appear in logs
5. **Use absolute paths in tests** - Relative paths cause confusion

### If Things Go Wrong
- **Import errors**: Check for circular imports, missing __init__.py files
- **Server won't start**: Check lifecycle management (Phase 3), look for async/await issues
- **Resolution not working**: Add debug logging to _resolve_project_context()
- **Sessions not isolated**: Check session_id is correctly extracted from Context
- **Cache issues**: Clear cache between tests with cache.clear()

### Success Indicators
✅ Server starts without warnings
✅ set_working_directory returns config_found=true for valid configs
✅ Logs show "Resolved project via session config" when using tools
✅ Multiple sessions maintain separate project contexts
✅ Explicit project_id parameter still overrides everything

### Final Testing Checklist
- [ ] Single session with config works
- [ ] Single session without config uses default
- [ ] Multiple sessions stay isolated
- [ ] Explicit project_id overrides config
- [ ] Server restart doesn't break anything
- [ ] 24-hour old sessions are cleaned up
- [ ] Documentation examples actually work

**Ready to implement!** Start with Phase 1 and work through sequentially. Good luck! 🚀
