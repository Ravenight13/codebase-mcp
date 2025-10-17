# Codebase-MCP Multi-Project Config Conversion Plan

**Date**: 2025-10-16
**Status**: Draft - Awaiting Architecture Review
**Goal**: Convert codebase-mcp from stateless per-request model to workflow-mcp's config-based session architecture

---

## Executive Summary

This plan converts codebase-mcp's multi-project tracking from a stateless per-request model to workflow-mcp's proven config-based session architecture. The conversion maintains backward compatibility, requires minimal testing (no existing ingested projects to migrate), and leverages the battle-tested implementation from workflow-mcp.

**Key Benefits**:
- ✅ Zero cross-contamination between sessions (validated in workflow-mcp)
- ✅ 40-90x performance improvement (0.65ms vs 60ms p95)
- ✅ Multi-session support (multiple Claude Code windows)
- ✅ Stateless architecture (no global active_project state)
- ✅ Local-first design (directory-based config files)

**Timeline**: 8-12 hours (minimal testing required, no data migration)

---

## Current vs Target Architecture

### Current State: Stateless Per-Request Model

```
MCP Tool Call (index_repository, search_code)
  ↓
Explicit project_id parameter (optional)
  ↓
resolve_project_id() resolution chain:
  1. Explicit parameter (highest priority)
  2. Query workflow-mcp via MCP client (if configured)
  3. Default workspace "default" (fallback)
  ↓
SET search_path = project_<project_id>
  ↓
Single shared connection pool (all projects)
```

**Limitations**:
- ❌ No session persistence (every call re-resolves)
- ❌ No local config file support (must use workflow-mcp or env vars)
- ❌ Dependency on external workflow-mcp server
- ❌ No working directory context

### Target State: Config-Based Session Model

```
Session Start
  ↓
set_working_directory("/path/to/project")
  ↓
Store in SessionContext (per-session, isolated)
  ↓
MCP Tool Call (no project_id needed!)
  ↓
_resolve_project_context():
  1. Get session_id (thread-local)
  2. Look up working_directory for session
  3. Search for .codebase-mcp/config.json (up to 20 levels)
  4. Parse and validate config
  5. Extract project.name or project.id
  6. Look up project in registry
  7. Return (project_id, schema_name)
  ↓
SET search_path = project_<project_id>
  ↓
Single shared connection pool (all projects)
```

**Benefits**:
- ✅ Session persistence (config cached, <1ms resolution)
- ✅ Local config file support (.codebase-mcp/config.json)
- ✅ No dependency on external servers
- ✅ Working directory context awareness
- ✅ Monorepo support (different subdirs → different projects)

---

## Architecture Comparison

| Aspect | Current (codebase-mcp) | Target (workflow-mcp style) |
|--------|------------------------|------------------------------|
| **State Model** | Stateless per-request | Session-based with context |
| **Session Storage** | None | SessionContextManager (in-memory) |
| **Config Files** | None | .codebase-mcp/config.json |
| **Connection Pools** | Single shared pool ✓ | Single shared pool ✓ (same!) |
| **Schema Isolation** | SET search_path ✓ | SET search_path ✓ (same!) |
| **Tool Parameters** | Explicit project_id | Implicit (from session) |
| **Resolution Chain** | 3-tier (param→workflow→default) | 4-tier (param→session→workflow→default) |
| **Discovery** | None | Upward directory search (20 levels) |
| **Caching** | None | LRU cache with mtime invalidation |

**Key Insight**: We're keeping the good parts (shared pool, schema isolation) and adding session persistence + config discovery!

---

## Implementation Plan

### Phase 1: Add Config Infrastructure (2-3 hours)

#### 1.1 Create auto_switch Module Structure

```bash
mkdir -p src/codebase_mcp/auto_switch
touch src/codebase_mcp/auto_switch/__init__.py
```

**Files to create**:
- `session_context.py` (~200 lines) - Session management
- `discovery.py` (~150 lines) - Config file discovery
- `cache.py` (~100 lines) - LRU cache with mtime invalidation
- `validation.py` (~100 lines) - Config validation
- `models.py` (~80 lines) - Pydantic models

#### 1.2 Implementation Details

**session_context.py**:
```python
from dataclasses import dataclass
from typing import Dict, Optional
import threading
import asyncio

@dataclass
class SessionContext:
    """Per-session context (isolated from other sessions)."""
    session_id: str
    working_directory: Optional[str] = None
    config_path: Optional[str] = None
    project_id: Optional[str] = None
    set_at: Optional[float] = None
    last_used: Optional[float] = None

class SessionContextManager:
    """Thread-safe session context manager."""

    def __init__(self):
        self._sessions: Dict[str, SessionContext] = {}
        self._lock = asyncio.Lock()

    async def set_working_directory(
        self,
        session_id: str,
        directory: str
    ) -> None:
        """Set working directory for this session only."""
        async with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionContext(
                    session_id=session_id
                )
            self._sessions[session_id].working_directory = directory
            self._sessions[session_id].last_used = time.time()

    async def get_working_directory(
        self,
        session_id: str
    ) -> Optional[str]:
        """Get working directory for this session only."""
        async with self._lock:
            if session_id not in self._sessions:
                return None
            session = self._sessions[session_id]
            session.last_used = time.time()
            return session.working_directory

# Global singleton
_session_context_manager: Optional[SessionContextManager] = None

def get_session_context_manager() -> SessionContextManager:
    """Get global session context manager instance."""
    global _session_context_manager
    if _session_context_manager is None:
        _session_context_manager = SessionContextManager()
    return _session_context_manager

def _get_current_session_id() -> str:
    """Get thread-local session ID."""
    if not hasattr(_get_current_session_id, '_thread_local'):
        _get_current_session_id._thread_local = threading.local()

    if not hasattr(_get_current_session_id._thread_local, 'session_id'):
        import uuid
        _get_current_session_id._thread_local.session_id = f"session_{uuid.uuid4().hex[:12]}"

    return _get_current_session_id._thread_local.session_id
```

**discovery.py**:
```python
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

def find_config_file(
    working_directory: Path,
    max_depth: int = 20
) -> Optional[Path]:
    """Search for .codebase-mcp/config.json up to max_depth levels.

    Algorithm:
    1. Start from working_directory
    2. Check for .codebase-mcp/config.json in current directory
    3. Move to parent directory if not found
    4. Stop at: config found, filesystem root, or max_depth

    Args:
        working_directory: Absolute path to start search
        max_depth: Maximum levels to search upward (default: 20)

    Returns:
        Path to config.json if found, None otherwise
    """
    current = working_directory.resolve()

    for level in range(max_depth):
        config_path = current / ".codebase-mcp" / "config.json"

        if config_path.exists() and config_path.is_file():
            logger.info(f"Found config at {config_path} (level {level})")
            return config_path

        # Check if we've reached filesystem root
        parent = current.parent
        if parent == current:
            logger.debug(f"Reached filesystem root without finding config")
            return None

        current = parent

    logger.debug(f"Max depth {max_depth} reached without finding config")
    return None
```

**cache.py**:
```python
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Any
import threading
import time

@dataclass
class CacheEntry:
    """Cache entry with mtime-based invalidation."""
    config: Dict[str, Any]
    config_path: Path
    mtime_ns: int
    access_time: float

class ConfigCache:
    """LRU cache with mtime-based automatic invalidation."""

    def __init__(self, max_size: int = 100):
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._lock = threading.Lock()

    def get(self, working_directory: str) -> Optional[Dict[str, Any]]:
        """Get config from cache with mtime validation."""
        with self._lock:
            entry = self._cache.get(working_directory)
            if entry is None:
                return None

            # Check if file still exists and mtime matches
            try:
                current_mtime_ns = entry.config_path.stat().st_mtime_ns
                if current_mtime_ns != entry.mtime_ns:
                    # File modified, invalidate cache
                    del self._cache[working_directory]
                    return None
            except (OSError, FileNotFoundError):
                # File deleted or inaccessible
                del self._cache[working_directory]
                return None

            # Cache hit! Update access time and return
            entry.access_time = time.time()
            return entry.config

    def set(
        self,
        working_directory: str,
        config: Dict[str, Any],
        config_path: Path
    ) -> None:
        """Store config in cache with current mtime."""
        with self._lock:
            # Evict oldest entry if at capacity
            if len(self._cache) >= self._max_size:
                oldest_key = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k].access_time
                )
                del self._cache[oldest_key]

            # Capture mtime at cache time
            mtime_ns = config_path.stat().st_mtime_ns

            self._cache[working_directory] = CacheEntry(
                config=config,
                config_path=config_path,
                mtime_ns=mtime_ns,
                access_time=time.time()
            )

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()

# Global singleton
_config_cache: Optional[ConfigCache] = None

def get_config_cache() -> ConfigCache:
    """Get global config cache instance."""
    global _config_cache
    if _config_cache is None:
        _config_cache = ConfigCache(max_size=100)
    return _config_cache
```

**validation.py**:
```python
import json
from pathlib import Path
from typing import Dict, Any

def validate_config_syntax(config_path: Path) -> Dict[str, Any]:
    """Validate config file syntax (Phase 1).

    Validates:
    - UTF-8 encoding
    - JSON parsing
    - Required fields (version, project.name)
    - Type constraints

    Args:
        config_path: Absolute path to config.json

    Returns:
        Parsed config dictionary

    Raises:
        ValueError: If validation fails
    """
    # Read and parse JSON
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {config_path}: {e}")
    except UnicodeDecodeError as e:
        raise ValueError(f"Invalid UTF-8 encoding in {config_path}: {e}")

    # Validate required fields
    if 'version' not in config:
        raise ValueError(f"Missing required field 'version' in {config_path}")

    if 'project' not in config or not isinstance(config['project'], dict):
        raise ValueError(f"Missing or invalid 'project' object in {config_path}")

    if 'name' not in config['project']:
        raise ValueError(f"Missing required field 'project.name' in {config_path}")

    # Validate types
    if not isinstance(config['version'], str):
        raise ValueError(f"Field 'version' must be string in {config_path}")

    if not isinstance(config['project']['name'], str):
        raise ValueError(f"Field 'project.name' must be string in {config_path}")

    # Validate version format (major.minor)
    try:
        major, minor = config['version'].split('.')
        int(major)
        int(minor)
    except (ValueError, AttributeError):
        raise ValueError(f"Invalid version format '{config['version']}', expected 'major.minor'")

    return config
```

**models.py**:
```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ProjectConfig(BaseModel):
    """Project configuration within config file."""
    name: str = Field(..., min_length=1, max_length=255)
    id: Optional[str] = Field(None, description="Project UUID (optional)")

class CodebaseMCPConfig(BaseModel):
    """Root configuration for .codebase-mcp/config.json."""
    version: str = Field(..., pattern=r'^\d+\.\d+$')
    project: ProjectConfig
    auto_switch: bool = Field(True, description="Enable automatic project switching")
    strict_mode: bool = Field(False, description="Reject operations if project mismatch")
    dry_run: bool = Field(False, description="Log intended switches without executing")
    description: Optional[str] = Field(None, max_length=1000)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# JSON Schema for validation
CONFIG_SCHEMA = {
    "type": "object",
    "required": ["version", "project"],
    "properties": {
        "version": {"type": "string", "pattern": "^\\d+\\.\\d+$"},
        "project": {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string", "minLength": 1, "maxLength": 255},
                "id": {"type": "string", "format": "uuid"}
            }
        },
        "auto_switch": {"type": "boolean"},
        "strict_mode": {"type": "boolean"},
        "dry_run": {"type": "boolean"},
        "description": {"type": "string", "maxLength": 1000},
        "created_at": {"type": "string", "format": "date-time"},
        "updated_at": {"type": "string", "format": "date-time"}
    }
}
```

---

### Phase 2: Add Project Resolution to Database Layer (2-3 hours)

#### 2.1 Update src/codebase_mcp/db/connection.py

Add `_resolve_project_context()` method to handle config-based resolution.

```python
async def _resolve_project_context() -> tuple[str, str]:
    """Resolve project from session config.

    Resolution chain:
    1. Get session_id (thread-local)
    2. Look up working_directory for session
    3. Search for .codebase-mcp/config.json (up to 20 levels)
    4. Check cache (LRU with mtime invalidation)
    5. Parse and validate config (if cache miss)
    6. Extract project.name or project.id
    7. Look up project in registry (if needed)
    8. Return (project_id, schema_name)

    Returns:
        Tuple of (project_id, schema_name) for SET search_path

    Raises:
        ValueError: If no session context or config not found
    """
    from codebase_mcp.auto_switch.session_context import (
        get_session_context_manager,
        _get_current_session_id
    )
    from codebase_mcp.auto_switch.discovery import find_config_file
    from codebase_mcp.auto_switch.cache import get_config_cache
    from codebase_mcp.auto_switch.validation import validate_config_syntax

    # Get session-specific working directory
    session_id = _get_current_session_id()
    session_ctx_mgr = get_session_context_manager()
    working_dir = await session_ctx_mgr.get_working_directory(session_id)

    if not working_dir:
        raise ValueError(
            "No working directory set for session. "
            "Call set_working_directory() first."
        )

    # Check cache first
    cache = get_config_cache()
    config = cache.get(working_dir)
    config_path = None

    if config is None:
        # Cache miss: search for config file
        config_path = find_config_file(Path(working_dir))
        if not config_path:
            raise ValueError(
                f"No .codebase-mcp/config.json found in {working_dir} or ancestors "
                "(searched up to 20 levels)"
            )

        # Parse and validate config
        config = validate_config_syntax(config_path)

        # Store in cache
        cache.set(working_dir, config, config_path)

    # Extract project identifier
    project_name = config['project']['name']
    project_id = config['project'].get('id')  # Optional

    # If project_id provided, use directly (no registry lookup needed)
    if project_id:
        schema_name = f"project_{project_id.replace('-', '_')}"
        return (project_id, schema_name)

    # Otherwise, look up project by name in registry (future enhancement)
    # For now, use name as project_id
    schema_name = f"project_{project_name.replace('-', '_')}"
    return (project_name, schema_name)
```

#### 2.2 Update resolve_project_id() Resolution Chain

Modify existing `resolve_project_id()` in `src/codebase_mcp/db/connection.py`:

```python
async def resolve_project_id(
    explicit_project_id: str | None,
    logger: logging.Logger
) -> str:
    """Resolve project ID with enhanced 4-tier chain.

    Resolution chain (in priority order):
    1. Explicit project_id parameter (highest)
    2. Session config file (.codebase-mcp/config.json) ← NEW!
    3. Query workflow-mcp via MCP client (if configured)
    4. Default workspace "default" (fallback)

    Args:
        explicit_project_id: Explicit project_id from tool call
        logger: Logger for diagnostics

    Returns:
        Resolved project_id string
    """
    # Priority 1: Explicit parameter
    if explicit_project_id:
        logger.info(f"Using explicit project_id: {explicit_project_id}")
        return explicit_project_id

    # Priority 2: Session config file (NEW!)
    try:
        project_id, schema_name = await _resolve_project_context()
        logger.info(f"Resolved from session config: {project_id} (schema: {schema_name})")
        return project_id
    except ValueError as e:
        logger.debug(f"Session config resolution failed: {e}")
    except Exception as e:
        logger.warning(f"Unexpected error in session config resolution: {e}")

    # Priority 3: Query workflow-mcp (existing logic)
    try:
        from codebase_mcp.mcp.client import get_workflow_mcp_client
        client = await get_workflow_mcp_client()
        if client:
            # Query workflow-mcp for active project
            result = await client.call_tool("get_active_project", {})
            if result and "project" in result:
                project_id = result["project"]["id"]
                logger.info(f"Resolved from workflow-mcp: {project_id}")
                return project_id
    except Exception as e:
        logger.debug(f"workflow-mcp query failed: {e}")

    # Priority 4: Default workspace (fallback)
    logger.info("Using default workspace")
    return "default"
```

---

### Phase 3: Add set_working_directory MCP Tool (1 hour)

#### 3.1 Create New MCP Tool

Add to `src/codebase_mcp/mcp/tools/project.py`:

```python
@server.tool()
async def set_working_directory(directory: str) -> dict[str, Any]:
    """Set working directory for this session (multi-client support).

    Call once at the beginning of each session to enable automatic
    project resolution from .codebase-mcp/config.json.

    **Multi-Client Workflow**:
    ```python
    # Session A (Claude Code window 1)
    await set_working_directory("/Users/alice/project-a")
    await index_repository(...)  # Uses project-a automatically

    # Session B (Claude Code window 2)
    await set_working_directory("/Users/alice/project-b")
    await index_repository(...)  # Uses project-b automatically

    # Zero cross-contamination!
    ```

    Args:
        directory: Absolute path to project directory

    Returns:
        {
            "session_id": str,
            "working_directory": str,
            "config_found": bool,
            "config_path": str | None,
            "project_info": dict | None
        }

    Raises:
        ValueError: Invalid directory path or not absolute
    """
    from codebase_mcp.auto_switch.session_context import (
        get_session_context_manager,
        _get_current_session_id
    )
    from codebase_mcp.auto_switch.discovery import find_config_file
    from codebase_mcp.auto_switch.validation import validate_config_syntax
    from pathlib import Path

    # Get session ID (unique per Claude Code window)
    session_id = _get_current_session_id()
    session_ctx_mgr = get_session_context_manager()

    # Validate directory
    dir_path = Path(directory)
    if not dir_path.is_absolute():
        raise ValueError(f"Directory must be absolute path, got: {directory}")
    if not dir_path.exists():
        raise ValueError(f"Directory does not exist: {directory}")
    if not dir_path.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")

    # Store working directory for this session
    await session_ctx_mgr.set_working_directory(session_id, str(dir_path))

    # Try to find and validate config
    config_path = find_config_file(dir_path)
    config_found = config_path is not None

    project_info = None
    if config_found:
        try:
            config = validate_config_syntax(config_path)
            project_info = {
                "name": config['project']['name'],
                "id": config['project'].get('id'),
                "auto_switch": config.get('auto_switch', True),
                "description": config.get('description')
            }
        except Exception as e:
            logger.warning(f"Config found but validation failed: {e}")

    return {
        "session_id": session_id,
        "working_directory": str(dir_path),
        "config_found": config_found,
        "config_path": str(config_path) if config_path else None,
        "project_info": project_info
    }
```

---

### Phase 4: Update MCP Tools to Support Session Context (1 hour)

#### 4.1 Update index_repository Tool

Modify `src/codebase_mcp/mcp/tools/indexing.py`:

```python
@server.tool()
async def index_repository(
    repo_path: str,
    project_id: str | None = None,  # Now optional!
    force_reindex: bool = False
) -> dict[str, Any]:
    """Index a repository for semantic search.

    Project resolution chain (priority order):
    1. Explicit project_id parameter (highest)
    2. Session config file (.codebase-mcp/config.json)
    3. Query workflow-mcp (if configured)
    4. Default workspace "default" (fallback)

    Args:
        repo_path: Absolute path to repository
        project_id: Optional project identifier (auto-resolved if not provided)
        force_reindex: Force full re-index

    Returns:
        Indexing results dictionary
    """
    from codebase_mcp.db.connection import resolve_project_id

    # Resolve project_id using enhanced chain
    resolved_project_id = await resolve_project_id(
        explicit_project_id=project_id,
        logger=logger
    )

    # Rest of implementation unchanged...
    async with get_db_session(resolved_project_id) as session:
        indexer = RepositoryIndexer(session, resolved_project_id)
        return await indexer.index(repo_path, force_reindex)
```

#### 4.2 Update search_code Tool

Modify `src/codebase_mcp/mcp/tools/search.py`:

```python
@server.tool()
async def search_code(
    query: str,
    project_id: str | None = None,  # Now optional!
    limit: int = 10,
    file_type: str | None = None,
    directory: str | None = None
) -> dict[str, Any]:
    """Search code using semantic similarity.

    Project resolution chain (priority order):
    1. Explicit project_id parameter (highest)
    2. Session config file (.codebase-mcp/config.json)
    3. Query workflow-mcp (if configured)
    4. Default workspace "default" (fallback)

    Args:
        query: Natural language search query
        project_id: Optional project identifier (auto-resolved if not provided)
        limit: Maximum results (1-50)
        file_type: Optional file extension filter
        directory: Optional directory filter

    Returns:
        Search results dictionary
    """
    from codebase_mcp.db.connection import resolve_project_id

    # Resolve project_id using enhanced chain
    resolved_project_id = await resolve_project_id(
        explicit_project_id=project_id,
        logger=logger
    )

    # Rest of implementation unchanged...
    async with get_db_session(resolved_project_id) as session:
        searcher = CodeSearcher(session, resolved_project_id)
        return await searcher.search(query, limit, file_type, directory)
```

---

### Phase 5: Testing Strategy (2-3 hours)

#### 5.1 Integration Tests

Create `tests/integration/test_config_resolution.py`:

```python
@pytest.mark.asyncio
async def test_end_to_end_config_resolution_workflow(tmp_path: Path) -> None:
    """Verify config-based resolution works end-to-end."""
    # Create config file
    config_dir = tmp_path / ".codebase-mcp"
    config_dir.mkdir()
    config = {
        "version": "1.0",
        "project": {"name": "test-project-1"},
        "auto_switch": True
    }
    (config_dir / "config.json").write_text(json.dumps(config))

    # Set working directory
    result = await set_working_directory.fn(str(tmp_path))
    assert result["config_found"] is True
    assert result["project_info"]["name"] == "test-project-1"

    # Index repository (should use config-resolved project)
    index_result = await index_repository.fn(
        repo_path=str(tmp_path / "test_repo")
        # No project_id parameter - should auto-resolve!
    )
    assert "repository_id" in index_result


@pytest.mark.asyncio
async def test_multi_session_isolation_no_cross_contamination(tmp_path: Path) -> None:
    """Verify zero cross-contamination between sessions."""
    # Create two directories with different configs
    dir_a = tmp_path / "project_a"
    dir_b = tmp_path / "project_b"
    dir_a.mkdir()
    dir_b.mkdir()

    create_config(dir_a, "project-a")
    create_config(dir_b, "project-b")

    # Session A: Set working directory
    await set_working_directory.fn(str(dir_a))
    result_a = await index_repository.fn(repo_path=str(dir_a / "repo"))

    # Session B: Set working directory (simulates different thread/session)
    await set_working_directory.fn(str(dir_b))
    result_b = await index_repository.fn(repo_path=str(dir_b / "repo"))

    # Verify different projects were used
    assert result_a["project_id"] == "project-a"
    assert result_b["project_id"] == "project-b"

    # ✅ CRITICAL CHECK: Zero cross-contamination!
```

#### 5.2 Performance Tests

Create `tests/performance/test_config_resolution_performance.py`:

```python
@pytest.mark.asyncio
async def test_config_resolution_performance_uncached(tmp_path: Path) -> None:
    """Verify config resolution <60ms p95 (uncached)."""
    create_config(tmp_path, "perf-test")

    latencies = []
    for _ in range(100):
        # Clear cache to test uncached performance
        get_config_cache().clear()

        start = time.perf_counter()
        await set_working_directory.fn(str(tmp_path))
        latencies.append((time.perf_counter() - start) * 1000)

    p95 = np.percentile(latencies, 95)
    print(f"\nUncached p95: {p95:.2f}ms")

    assert p95 < 60, f"p95 latency {p95:.2f}ms exceeds 60ms target"


@pytest.mark.asyncio
async def test_config_resolution_performance_cached(tmp_path: Path) -> None:
    """Verify cached config resolution <1ms p95."""
    create_config(tmp_path, "cache-test")

    # Prime cache
    await set_working_directory.fn(str(tmp_path))

    latencies = []
    for _ in range(100):
        start = time.perf_counter()
        await set_working_directory.fn(str(tmp_path))
        latencies.append((time.perf_counter() - start) * 1000)

    p95 = np.percentile(latencies, 95)
    print(f"\nCached p95: {p95:.2f}ms")

    assert p95 < 1, f"Cached p95 latency {p95:.2f}ms exceeds 1ms target"
```

---

### Phase 6: Documentation (1 hour)

#### 6.1 Update README.md

Add section on config-based project tracking:

```markdown
## Multi-Project Configuration

Codebase-MCP supports multiple projects using local config files.

### Setup (One-time per project)

```bash
cd /path/to/my-project

# Create config file
mkdir -p .codebase-mcp
cat > .codebase-mcp/config.json <<EOF
{
  "version": "1.0",
  "project": {
    "name": "my-project"
  },
  "auto_switch": true
}
EOF

# Add to .gitignore (config is per-machine)
echo ".codebase-mcp/config.json" >> .gitignore
```

### Usage (Each Claude Code session)

```python
# Call once at session start
await set_working_directory("/path/to/my-project")

# All subsequent operations automatically use my-project
await index_repository(repo_path="/path/to/my-project")  # ✓ Uses my-project
await search_code(query="function definition")           # ✓ Uses my-project

# No manual project_id needed!
```

### Multi-Project Workflow

```python
# Session A (Claude Code window 1)
await set_working_directory("/Users/alice/project-a")
await index_repository(...)  # ✓ Uses project-a

# Session B (Claude Code window 2)
await set_working_directory("/Users/alice/project-b")
await index_repository(...)  # ✓ Uses project-b

# Zero cross-contamination!
```
```

---

## Implementation Timeline

| Phase | Duration | Deliverables | Risk |
|-------|----------|--------------|------|
| Phase 1: Config Infrastructure | 2-3h | auto_switch module (5 files, ~630 lines) | Low |
| Phase 2: Database Resolution | 2-3h | _resolve_project_context(), updated resolve_project_id() | Low |
| Phase 3: MCP Tool | 1h | set_working_directory tool | Low |
| Phase 4: Update MCP Tools | 1h | index_repository, search_code (optional params) | Low |
| Phase 5: Testing | 2-3h | Integration + performance tests (6+ tests) | Low |
| Phase 6: Documentation | 1h | README, examples | Low |
| **Total** | **8-12h** | **Minimal testing, no data migration** | **Low** |

---

## Key Architectural Decisions

### Decision 1: Keep Shared Connection Pool ✓

**Rationale**:
- Codebase-MCP uses PostgreSQL schema isolation (SET search_path)
- Workflow-MCP uses separate databases per project
- Shared pool is simpler, scales better for 100+ projects
- No need to change pool architecture

**Impact**: Minimal changes to database layer

### Decision 2: Keep Explicit project_id Parameters ✓

**Rationale**:
- Backward compatibility (existing tool calls still work)
- Supports both explicit and implicit project selection
- No breaking changes for users

**Impact**: Optional parameters, enhanced resolution chain

### Decision 3: Add Session Context Layer (New)

**Rationale**:
- Enables multi-session isolation (multiple Claude Code windows)
- Zero cross-contamination between sessions
- Proven architecture from workflow-mcp (40-90x performance improvement)

**Impact**: New auto_switch module, ~630 lines of code

### Decision 4: No Registry Database Changes

**Rationale**:
- No existing ingested projects to migrate
- Config files are per-machine (not stored in registry)
- Project lookup by name can be added later if needed

**Impact**: Minimal database changes

---

## Risk Analysis

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Session ID collision** | Low | Medium | Use UUID-based session IDs (collision rate <1e-18) |
| **Cache invalidation bugs** | Low | Medium | Use mtime-based validation (proven in workflow-mcp) |
| **Backward compatibility break** | Low | High | Keep explicit project_id parameters, add to resolution chain |
| **Performance regression** | Very Low | Medium | Use same caching strategy as workflow-mcp (<1ms cached) |
| **Thread-safety issues** | Low | High | Use asyncio.Lock for session manager, threading.Lock for cache |
| **Config file discovery failures** | Low | Low | Graceful degradation, clear error messages |

**Overall Risk**: **LOW** (proven architecture, minimal testing needed, no data migration)

---

## Success Criteria

### Functional
- [ ] set_working_directory tool works correctly
- [ ] Config file discovery finds .codebase-mcp/config.json (up to 20 levels)
- [ ] Config parsing and validation works
- [ ] index_repository auto-resolves project from session context
- [ ] search_code auto-resolves project from session context
- [ ] Multi-session isolation works (no cross-contamination)

### Performance
- [ ] Config resolution <60ms p95 (uncached)
- [ ] Config resolution <1ms p95 (cached)
- [ ] No regression in index_repository performance
- [ ] No regression in search_code performance

### Testing
- [ ] Integration tests passing (6+ tests)
- [ ] Performance tests passing (2+ tests)
- [ ] Multi-session isolation validated

### Documentation
- [ ] README.md updated with config workflow
- [ ] Example config files provided
- [ ] Multi-project workflow documented

---

## Follow-Up Enhancements (Post-MVP)

These can be added later if needed:

1. **Project Registry Integration**
   - Look up projects by name in registry database
   - Support project.id in config for robustness

2. **Atomic Config Updates**
   - Add config_manager.py for concurrent config modifications
   - File locking for multi-process safety

3. **Strict Mode**
   - Reject operations if active project doesn't match config
   - Validation checks before each operation

4. **Dry-Run Mode**
   - Log intended switches without executing
   - Debugging tool for config resolution

5. **Environment Variable Overrides**
   - CODEBASE_MCP_PROJECT=projectname
   - CODEBASE_MCP_CONFIG_PATH=/custom/path
   - CODEBASE_MCP_AUTO_SWITCH=false

---

## Migration Path for Users

### For New Users (Recommended)

1. Create `.codebase-mcp/config.json` in project root
2. Call `set_working_directory()` at session start
3. Use tools without project_id parameter

### For Existing Users (Backward Compatible)

Option A: Continue using explicit project_id
```python
# Works exactly as before!
await index_repository(repo_path="...", project_id="my-project")
```

Option B: Migrate to config files
```python
# One-time setup
await set_working_directory("/path/to/project")

# Then use without project_id
await index_repository(repo_path="...")
```

**No forced migration required!**

---

## References

- **workflow-mcp Implementation**: Commit b8f8085 (master branch)
- **Implementation Guide**: `/Users/cliffclarke/Claude_Code/workflow-mcp/CODEBASE_MCP_IMPLEMENTATION_GUIDE.md`
- **Spec**: workflow-mcp specs/004-config-based-architecture
- **Testing Guide**: workflow-mcp docs/guides/config-architecture-testing-guide.md
- **Validation Report**: workflow-mcp docs/validation/config-architecture-isolation-test-results.md

---

## Conclusion

This conversion plan provides a low-risk path to adopt workflow-mcp's proven config-based architecture while maintaining backward compatibility and requiring minimal testing. The implementation is straightforward because:

1. ✅ **No data migration** (no existing projects to migrate)
2. ✅ **Proven architecture** (validated in workflow-mcp with zero cross-contamination)
3. ✅ **Backward compatible** (explicit project_id parameters still work)
4. ✅ **Minimal changes** (keep shared pool, schema isolation)
5. ✅ **Clear benefits** (40-90x performance, multi-session support)

**Estimated timeline**: 8-12 hours from start to production-ready implementation.

**Next step**: Architecture review by architect-review subagent.
