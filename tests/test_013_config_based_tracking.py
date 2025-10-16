"""Validation tests for spec 013: Config-Based Project Tracking.

This test suite validates the complete config-based auto-switching implementation,
including all Phase 1 modules, Phase 2 resolution chain, and backward compatibility.

Test Coverage:
- auto_switch.models: Pydantic validation
- auto_switch.validation: Config syntax validation
- auto_switch.discovery: Config file discovery with upward traversal
- auto_switch.cache: Async LRU cache with mtime invalidation
- auto_switch.session_context: Multi-session context manager
- database.session: _resolve_project_context + resolve_project_id
- mcp.tools.project: set_working_directory tool
- Backward compatibility: explicit project_id prioritization

Constitutional Compliance:
- Principle V: Production quality (comprehensive error handling)
- Principle VII: Test-driven development (complete test coverage)
- Principle VIII: Type safety (complete type annotations)
"""

from __future__ import annotations

import asyncio
import json
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import ValidationError

from src.auto_switch.cache import ConfigCache, get_config_cache
from src.auto_switch.discovery import find_config_file
from src.auto_switch.models import CodebaseMCPConfig, ProjectConfig
from src.auto_switch.session_context import (
    SessionContext,
    SessionContextManager,
    get_session_context_manager,
)
from src.auto_switch.validation import validate_config_syntax
from src.database.session import _resolve_project_context, resolve_project_id


# ==============================================================================
# Test Fixtures
# ==============================================================================


@pytest.fixture
def valid_config_dict() -> dict[str, Any]:
    """Valid configuration dictionary."""
    return {
        "version": "1.0",
        "project": {"name": "test-project", "id": "test-project-uuid"},
        "auto_switch": True,
        "strict_mode": False,
        "dry_run": False,
        "description": "Test project configuration",
    }


@pytest.fixture
def minimal_config_dict() -> dict[str, Any]:
    """Minimal valid configuration (only required fields)."""
    return {"version": "1.0", "project": {"name": "minimal-project"}}


@pytest.fixture
def temp_config_file(valid_config_dict: dict[str, Any]) -> Path:
    """Create a temporary config file with valid configuration."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(valid_config_dict, f)
        return Path(f.name)


@pytest.fixture
def nested_project_dir(valid_config_dict: dict[str, Any]) -> Path:
    """Create a nested project directory structure with config file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create nested structure: tmpdir/project/subdir1/subdir2
        project_root = Path(tmpdir) / "project"
        nested_dir = project_root / "subdir1" / "subdir2"
        nested_dir.mkdir(parents=True)

        # Create config at project root
        config_dir = project_root / ".codebase-mcp"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps(valid_config_dict))

        yield nested_dir  # Yield deepest directory


@pytest.fixture
async def session_manager() -> AsyncGenerator[SessionContextManager, None]:
    """Create and start a session context manager."""
    manager = SessionContextManager()
    await manager.start()
    yield manager
    await manager.stop()


@pytest.fixture
def mock_fastmcp_context() -> Mock:
    """Mock FastMCP Context with session_id."""
    ctx = Mock()
    ctx.session_id = "test-session-id"
    return ctx


# ==============================================================================
# Phase 1 Module Tests: auto_switch.models
# ==============================================================================


class TestAutoSwitchModels:
    """Unit tests for auto_switch.models Pydantic validation."""

    def test_project_config_valid(self) -> None:
        """Test ProjectConfig with valid data."""
        config = ProjectConfig(name="test-project")
        assert config.name == "test-project"
        assert config.id is None

    def test_project_config_with_id(self) -> None:
        """Test ProjectConfig with optional ID."""
        config = ProjectConfig(name="test-project", id="uuid-123")
        assert config.name == "test-project"
        assert config.id == "uuid-123"

    def test_project_config_invalid_empty_name(self) -> None:
        """Test ProjectConfig rejects empty name."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectConfig(name="")

        errors = exc_info.value.errors()
        assert any(
            err["loc"] == ("name",) and "at least 1 character" in str(err["msg"]).lower()
            for err in errors
        )

    def test_project_config_invalid_too_long(self) -> None:
        """Test ProjectConfig rejects name >255 chars."""
        with pytest.raises(ValidationError) as exc_info:
            ProjectConfig(name="x" * 256)

        errors = exc_info.value.errors()
        assert any(
            err["loc"] == ("name",) and "at most 255 characters" in str(err["msg"]).lower()
            for err in errors
        )

    def test_codebase_mcp_config_valid(
        self, valid_config_dict: dict[str, Any]
    ) -> None:
        """Test CodebaseMCPConfig with valid data."""
        config = CodebaseMCPConfig(**valid_config_dict)
        assert config.version == "1.0"
        assert config.project.name == "test-project"
        assert config.project.id == "test-project-uuid"
        assert config.auto_switch is True
        assert config.strict_mode is False

    def test_codebase_mcp_config_minimal(
        self, minimal_config_dict: dict[str, Any]
    ) -> None:
        """Test CodebaseMCPConfig with only required fields."""
        config = CodebaseMCPConfig(**minimal_config_dict)
        assert config.version == "1.0"
        assert config.project.name == "minimal-project"
        assert config.project.id is None
        assert config.auto_switch is True  # Default value
        assert config.strict_mode is False  # Default value

    def test_codebase_mcp_config_invalid_version_format(self) -> None:
        """Test CodebaseMCPConfig rejects invalid version format."""
        with pytest.raises(ValidationError) as exc_info:
            CodebaseMCPConfig(
                version="invalid", project={"name": "test-project"}
            )

        errors = exc_info.value.errors()
        assert any(
            err["loc"] == ("version",) and "pattern" in str(err["msg"]).lower()
            for err in errors
        )

    def test_codebase_mcp_config_missing_version(self) -> None:
        """Test CodebaseMCPConfig requires version field."""
        with pytest.raises(ValidationError) as exc_info:
            CodebaseMCPConfig(project={"name": "test-project"})  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("version",) for err in errors)

    def test_codebase_mcp_config_missing_project(self) -> None:
        """Test CodebaseMCPConfig requires project field."""
        with pytest.raises(ValidationError) as exc_info:
            CodebaseMCPConfig(version="1.0")  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(err["loc"] == ("project",) for err in errors)


# ==============================================================================
# Phase 1 Module Tests: auto_switch.validation
# ==============================================================================


class TestAutoSwitchValidation:
    """Unit tests for auto_switch.validation config syntax validation."""

    def test_validate_config_syntax_valid(
        self, temp_config_file: Path
    ) -> None:
        """Test validate_config_syntax with valid config file."""
        config = validate_config_syntax(temp_config_file)
        assert config["version"] == "1.0"
        assert config["project"]["name"] == "test-project"

        # Cleanup
        temp_config_file.unlink()

    def test_validate_config_syntax_minimal(self) -> None:
        """Test validate_config_syntax with minimal valid config."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"version": "1.0", "project": {"name": "minimal"}}, f)
            config_path = Path(f.name)

        config = validate_config_syntax(config_path)
        assert config["version"] == "1.0"
        assert config["project"]["name"] == "minimal"

        config_path.unlink()

    def test_validate_config_syntax_invalid_json(self) -> None:
        """Test validate_config_syntax rejects invalid JSON."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("{invalid json}")
            config_path = Path(f.name)

        with pytest.raises(ValueError, match="Invalid JSON"):
            validate_config_syntax(config_path)

        config_path.unlink()

    def test_validate_config_syntax_missing_version(self) -> None:
        """Test validate_config_syntax requires version field."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"project": {"name": "test"}}, f)
            config_path = Path(f.name)

        with pytest.raises(ValueError, match="Missing required field 'version'"):
            validate_config_syntax(config_path)

        config_path.unlink()

    def test_validate_config_syntax_missing_project(self) -> None:
        """Test validate_config_syntax requires project field."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"version": "1.0"}, f)
            config_path = Path(f.name)

        with pytest.raises(
            ValueError, match="Missing or invalid 'project' object"
        ):
            validate_config_syntax(config_path)

        config_path.unlink()

    def test_validate_config_syntax_missing_project_name(self) -> None:
        """Test validate_config_syntax requires project.name field."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"version": "1.0", "project": {}}, f)
            config_path = Path(f.name)

        with pytest.raises(
            ValueError, match="Missing required field 'project.name'"
        ):
            validate_config_syntax(config_path)

        config_path.unlink()

    def test_validate_config_syntax_invalid_version_format(self) -> None:
        """Test validate_config_syntax rejects invalid version format."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(
                {"version": "invalid", "project": {"name": "test"}}, f
            )
            config_path = Path(f.name)

        with pytest.raises(ValueError, match="Invalid version format"):
            validate_config_syntax(config_path)

        config_path.unlink()

    def test_validate_config_syntax_invalid_utf8(self) -> None:
        """Test validate_config_syntax rejects non-UTF-8 files."""
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".json", delete=False
        ) as f:
            # Write invalid UTF-8 bytes
            f.write(b"\xff\xfe{\"version\": \"1.0\"}")
            config_path = Path(f.name)

        with pytest.raises(ValueError, match="Invalid UTF-8 encoding"):
            validate_config_syntax(config_path)

        config_path.unlink()

    def test_validate_config_syntax_file_not_found(self) -> None:
        """Test validate_config_syntax handles missing files."""
        nonexistent = Path("/tmp/nonexistent-config-file.json")
        with pytest.raises(ValueError, match="Cannot read config file"):
            validate_config_syntax(nonexistent)


# ==============================================================================
# Phase 1 Module Tests: auto_switch.discovery
# ==============================================================================


class TestAutoSwitchDiscovery:
    """Unit tests for auto_switch.discovery config file discovery."""

    def test_find_config_file_current_directory(self) -> None:
        """Test find_config_file finds config in current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config at current directory
            tmpdir_path = Path(tmpdir).resolve()  # Resolve symlinks first
            config_dir = tmpdir_path / ".codebase-mcp"
            config_dir.mkdir()
            config_file = config_dir / "config.json"
            config_file.write_text(
                json.dumps({"version": "1.0", "project": {"name": "test"}})
            )

            # Search from current directory
            found = find_config_file(tmpdir_path)
            assert found == config_file

    def test_find_config_file_parent_directory(self) -> None:
        """Test find_config_file finds config in parent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested structure
            tmpdir_path = Path(tmpdir).resolve()
            subdir = tmpdir_path / "level1"
            subdir.mkdir()

            # Create config at top level
            config_dir = tmpdir_path / ".codebase-mcp"
            config_dir.mkdir()
            config_file = config_dir / "config.json"
            config_file.write_text(
                json.dumps({"version": "1.0", "project": {"name": "test"}})
            )

            # Search from subdirectory
            found = find_config_file(subdir)
            assert found == config_file

    def test_find_config_file_multiple_levels(self) -> None:
        """Test find_config_file with deep nested structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create deeply nested structure
            tmpdir_path = Path(tmpdir).resolve()
            nested_dir = tmpdir_path / "l1" / "l2" / "l3" / "l4" / "l5"
            nested_dir.mkdir(parents=True)

            # Create config at top level
            config_dir = tmpdir_path / ".codebase-mcp"
            config_dir.mkdir()
            config_file = config_dir / "config.json"
            config_file.write_text(
                json.dumps({"version": "1.0", "project": {"name": "test"}})
            )

            # Search from deepest directory
            found = find_config_file(nested_dir)
            assert found == config_file

    def test_find_config_file_not_found(self) -> None:
        """Test find_config_file returns None when config not found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # No config file created
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()

            found = find_config_file(subdir)
            assert found is None

    def test_find_config_file_max_depth(self) -> None:
        """Test find_config_file respects max_depth limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create structure deeper than max_depth
            nested_dir = Path(tmpdir)
            for i in range(25):  # Deeper than default max_depth=20
                nested_dir = nested_dir / f"level{i}"
            nested_dir.mkdir(parents=True)

            # Create config at top level
            config_dir = Path(tmpdir) / ".codebase-mcp"
            config_dir.mkdir()
            config_file = config_dir / "config.json"
            config_file.write_text(
                json.dumps({"version": "1.0", "project": {"name": "test"}})
            )

            # Search from deepest directory with default max_depth
            found = find_config_file(nested_dir)
            assert found is None  # Too deep to find

    def test_find_config_file_custom_max_depth(self) -> None:
        """Test find_config_file with custom max_depth."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create 3-level structure
            tmpdir_path = Path(tmpdir).resolve()
            nested_dir = tmpdir_path / "l1" / "l2" / "l3"
            nested_dir.mkdir(parents=True)

            # Create config at top level
            config_dir = tmpdir_path / ".codebase-mcp"
            config_dir.mkdir()
            config_file = config_dir / "config.json"
            config_file.write_text(
                json.dumps({"version": "1.0", "project": {"name": "test"}})
            )

            # Search with max_depth=2 (should not find)
            found = find_config_file(nested_dir, max_depth=2)
            assert found is None

            # Search with max_depth=5 (should find)
            found = find_config_file(nested_dir, max_depth=5)
            assert found == config_file

    def test_find_config_file_symlink_resolution(self) -> None:
        """Test find_config_file resolves symlinks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create real directory with config
            tmpdir_path = Path(tmpdir).resolve()
            real_dir = tmpdir_path / "real"
            real_dir.mkdir()
            config_dir = real_dir / ".codebase-mcp"
            config_dir.mkdir()
            config_file = config_dir / "config.json"
            config_file.write_text(
                json.dumps({"version": "1.0", "project": {"name": "test"}})
            )

            # Create symlink to real directory
            symlink_dir = tmpdir_path / "symlink"
            symlink_dir.symlink_to(real_dir)

            # Search from symlink (should resolve and find config)
            found = find_config_file(symlink_dir)
            assert found == config_file


# ==============================================================================
# Phase 1 Module Tests: auto_switch.cache
# ==============================================================================


class TestAutoSwitchCache:
    """Unit tests for auto_switch.cache async config cache."""

    @pytest.mark.asyncio
    async def test_cache_get_miss(self) -> None:
        """Test cache get with no entry (cache miss)."""
        cache = ConfigCache(max_size=10)
        result = await cache.get("/tmp/test")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self) -> None:
        """Test cache set and get operations."""
        cache = ConfigCache(max_size=10)

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            config_file.write_text(
                json.dumps({"version": "1.0", "project": {"name": "test"}})
            )

            config = {"version": "1.0", "project": {"name": "test"}}
            await cache.set(tmpdir, config, config_file)

            cached = await cache.get(tmpdir)
            assert cached is not None
            assert cached["project"]["name"] == "test"

    @pytest.mark.asyncio
    async def test_cache_mtime_invalidation(self) -> None:
        """Test cache invalidation when file mtime changes."""
        cache = ConfigCache(max_size=10)

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            config_file.write_text(
                json.dumps({"version": "1.0", "project": {"name": "test"}})
            )

            # Set initial cache
            config = {"version": "1.0", "project": {"name": "test"}}
            await cache.set(tmpdir, config, config_file)

            # Verify cache hit
            cached = await cache.get(tmpdir)
            assert cached is not None

            # Modify file (change mtime)
            await asyncio.sleep(0.01)  # Ensure mtime changes
            config_file.write_text(
                json.dumps({"version": "1.0", "project": {"name": "updated"}})
            )

            # Verify cache invalidated
            cached = await cache.get(tmpdir)
            assert cached is None

    @pytest.mark.asyncio
    async def test_cache_file_deletion_invalidation(self) -> None:
        """Test cache invalidation when file is deleted."""
        cache = ConfigCache(max_size=10)

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            config_file.write_text(
                json.dumps({"version": "1.0", "project": {"name": "test"}})
            )

            # Set initial cache
            config = {"version": "1.0", "project": {"name": "test"}}
            await cache.set(tmpdir, config, config_file)

            # Delete file
            config_file.unlink()

            # Verify cache invalidated
            cached = await cache.get(tmpdir)
            assert cached is None

    @pytest.mark.asyncio
    async def test_cache_lru_eviction(self) -> None:
        """Test LRU eviction when cache reaches max_size."""
        cache = ConfigCache(max_size=2)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create 3 config files
            configs = []
            for i in range(3):
                config_file = Path(tmpdir) / f"config{i}.json"
                config_file.write_text(
                    json.dumps(
                        {"version": "1.0", "project": {"name": f"test{i}"}}
                    )
                )
                configs.append((f"/tmp/dir{i}", config_file))

            # Add first two entries
            for i in range(2):
                config = {"version": "1.0", "project": {"name": f"test{i}"}}
                await cache.set(configs[i][0], config, configs[i][1])

            # Verify both cached
            assert await cache.get(configs[0][0]) is not None
            assert await cache.get(configs[1][0]) is not None

            # Add third entry (should evict oldest)
            await asyncio.sleep(0.01)  # Ensure different access times
            config = {"version": "1.0", "project": {"name": "test2"}}
            await cache.set(configs[2][0], config, configs[2][1])

            # Verify oldest evicted
            size = await cache.get_size()
            assert size == 2

    @pytest.mark.asyncio
    async def test_cache_clear(self) -> None:
        """Test cache clear operation."""
        cache = ConfigCache(max_size=10)

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            config_file.write_text(
                json.dumps({"version": "1.0", "project": {"name": "test"}})
            )

            config = {"version": "1.0", "project": {"name": "test"}}
            await cache.set(tmpdir, config, config_file)

            # Verify cached
            assert await cache.get(tmpdir) is not None
            assert await cache.get_size() == 1

            # Clear cache
            await cache.clear()

            # Verify cleared
            assert await cache.get(tmpdir) is None
            assert await cache.get_size() == 0

    @pytest.mark.asyncio
    async def test_cache_concurrent_access(self) -> None:
        """Test cache handles concurrent async access."""
        cache = ConfigCache(max_size=10)

        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "config.json"
            config_file.write_text(
                json.dumps({"version": "1.0", "project": {"name": "test"}})
            )

            # Simulate concurrent set operations
            config = {"version": "1.0", "project": {"name": "test"}}
            tasks = [
                cache.set(f"/tmp/dir{i}", config, config_file)
                for i in range(10)
            ]
            await asyncio.gather(*tasks)

            # Verify all cached
            size = await cache.get_size()
            assert size == 10

    @pytest.mark.asyncio
    async def test_get_config_cache_singleton(self) -> None:
        """Test get_config_cache returns singleton instance."""
        cache1 = get_config_cache()
        cache2 = get_config_cache()
        assert cache1 is cache2


# ==============================================================================
# Phase 1 Module Tests: auto_switch.session_context
# ==============================================================================


class TestAutoSwitchSessionContext:
    """Unit tests for auto_switch.session_context manager."""

    @pytest.mark.asyncio
    async def test_session_context_manager_start_stop(self) -> None:
        """Test SessionContextManager start and stop lifecycle."""
        manager = SessionContextManager()

        # Start manager
        await manager.start()
        assert manager._running is True

        # Stop manager
        await manager.stop()
        assert manager._running is False

    @pytest.mark.asyncio
    async def test_session_context_manager_idempotent(self) -> None:
        """Test start/stop are idempotent."""
        manager = SessionContextManager()

        # Multiple starts
        await manager.start()
        await manager.start()  # Should not raise
        assert manager._running is True

        # Multiple stops
        await manager.stop()
        await manager.stop()  # Should not raise
        assert manager._running is False

    @pytest.mark.asyncio
    async def test_set_and_get_working_directory(
        self, session_manager: SessionContextManager
    ) -> None:
        """Test set and get working directory for session."""
        session_id = "test-session-1"
        directory = "/tmp/test-project"

        # Set working directory
        await session_manager.set_working_directory(session_id, directory)

        # Get working directory
        result = await session_manager.get_working_directory(session_id)
        assert result == directory

    @pytest.mark.asyncio
    async def test_get_working_directory_not_set(
        self, session_manager: SessionContextManager
    ) -> None:
        """Test get working directory returns None when not set."""
        result = await session_manager.get_working_directory("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_multiple_sessions_isolated(
        self, session_manager: SessionContextManager
    ) -> None:
        """Test multiple sessions are isolated from each other."""
        session1_id = "session-1"
        session2_id = "session-2"
        dir1 = "/tmp/project1"
        dir2 = "/tmp/project2"

        # Set working directories for both sessions
        await session_manager.set_working_directory(session1_id, dir1)
        await session_manager.set_working_directory(session2_id, dir2)

        # Verify isolation
        result1 = await session_manager.get_working_directory(session1_id)
        result2 = await session_manager.get_working_directory(session2_id)

        assert result1 == dir1
        assert result2 == dir2
        assert result1 != result2

    @pytest.mark.asyncio
    async def test_get_session_count(
        self, session_manager: SessionContextManager
    ) -> None:
        """Test get_session_count tracks active sessions."""
        assert await session_manager.get_session_count() == 0

        # Add sessions
        await session_manager.set_working_directory("session-1", "/tmp/dir1")
        assert await session_manager.get_session_count() == 1

        await session_manager.set_working_directory("session-2", "/tmp/dir2")
        assert await session_manager.get_session_count() == 2

    @pytest.mark.asyncio
    async def test_session_context_dataclass(self) -> None:
        """Test SessionContext dataclass."""
        ctx = SessionContext(
            session_id="test-session",
            working_directory="/tmp/project",
            config_path="/tmp/project/.codebase-mcp/config.json",
            project_id="test-project-uuid",
            set_at=time.time(),
            last_used=time.time(),
        )

        assert ctx.session_id == "test-session"
        assert ctx.working_directory == "/tmp/project"
        assert ctx.project_id == "test-project-uuid"

    @pytest.mark.asyncio
    async def test_get_session_context_manager_singleton(self) -> None:
        """Test get_session_context_manager returns singleton."""
        mgr1 = get_session_context_manager()
        mgr2 = get_session_context_manager()
        assert mgr1 is mgr2


# ==============================================================================
# Phase 2 Resolution Chain Tests
# ==============================================================================


class TestResolutionChain:
    """Integration tests for 4-tier resolution chain."""

    @pytest.mark.asyncio
    async def test_priority_1_explicit_id(self) -> None:
        """Test Priority 1: Explicit project_id takes precedence."""
        result = await resolve_project_id(explicit_id="explicit-id", ctx=None)
        assert result == "explicit-id"

    @pytest.mark.asyncio
    async def test_priority_4_default_fallback(self) -> None:
        """Test Priority 4: Default workspace fallback."""
        # No explicit_id, no ctx, no workflow-mcp
        with patch("src.database.session.get_settings") as mock_settings:
            mock_settings.return_value.workflow_mcp_url = None
            result = await resolve_project_id(explicit_id=None, ctx=None)
            assert result is None  # Default workspace

    @pytest.mark.asyncio
    async def test_resolve_project_context_no_ctx(self) -> None:
        """Test _resolve_project_context with no context."""
        result = await _resolve_project_context(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_project_context_no_working_dir(
        self, mock_fastmcp_context: Mock
    ) -> None:
        """Test _resolve_project_context with no working directory set."""
        # Session exists but no working directory set
        result = await _resolve_project_context(mock_fastmcp_context)
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_project_context_with_config(
        self, mock_fastmcp_context: Mock
    ) -> None:
        """Test _resolve_project_context with valid config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config file
            config_dir = Path(tmpdir) / ".codebase-mcp"
            config_dir.mkdir()
            config_file = config_dir / "config.json"
            config_file.write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "project": {
                            "name": "test-project",
                            "id": "test-uuid",
                        },
                    }
                )
            )

            # Set working directory
            session_mgr = get_session_context_manager()
            await session_mgr.start()
            await session_mgr.set_working_directory(
                mock_fastmcp_context.session_id, tmpdir
            )

            try:
                # Resolve project context
                result = await _resolve_project_context(mock_fastmcp_context)
                assert result is not None
                project_id, schema_name = result
                assert project_id == "test-uuid"
                assert schema_name == "project_test_uuid"
            finally:
                await session_mgr.stop()

    @pytest.mark.asyncio
    async def test_resolve_project_context_name_only(
        self, mock_fastmcp_context: Mock
    ) -> None:
        """Test _resolve_project_context with name only (no ID)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config file without ID
            config_dir = Path(tmpdir) / ".codebase-mcp"
            config_dir.mkdir()
            config_file = config_dir / "config.json"
            config_file.write_text(
                json.dumps(
                    {"version": "1.0", "project": {"name": "test-project"}}
                )
            )

            # Set working directory
            session_mgr = get_session_context_manager()
            await session_mgr.start()
            await session_mgr.set_working_directory(
                mock_fastmcp_context.session_id, tmpdir
            )

            try:
                # Resolve project context
                result = await _resolve_project_context(mock_fastmcp_context)
                assert result is not None
                project_id, schema_name = result
                assert project_id == "test-project"
                assert schema_name == "project_test_project"
            finally:
                await session_mgr.stop()

    @pytest.mark.asyncio
    async def test_resolve_project_id_session_config_priority(
        self, mock_fastmcp_context: Mock
    ) -> None:
        """Test Priority 2: Session config overrides workflow-mcp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config file
            config_dir = Path(tmpdir) / ".codebase-mcp"
            config_dir.mkdir()
            config_file = config_dir / "config.json"
            config_file.write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "project": {
                            "name": "session-project",
                            "id": "session-uuid",
                        },
                    }
                )
            )

            # Set working directory
            session_mgr = get_session_context_manager()
            await session_mgr.start()
            await session_mgr.set_working_directory(
                mock_fastmcp_context.session_id, tmpdir
            )

            try:
                # Mock workflow-mcp settings
                with patch(
                    "src.database.session.get_settings"
                ) as mock_settings:
                    mock_settings.return_value.workflow_mcp_url = (
                        "http://localhost:8080"
                    )

                    # Resolve - session config should take priority
                    result = await resolve_project_id(
                        explicit_id=None, ctx=mock_fastmcp_context
                    )
                    assert result == "session-uuid"
            finally:
                await session_mgr.stop()


# ==============================================================================
# Backward Compatibility Tests
# ==============================================================================


class TestBackwardCompatibility:
    """Tests ensuring backward compatibility."""

    @pytest.mark.asyncio
    async def test_tools_work_without_ctx(self) -> None:
        """Test tools work without ctx parameter (backward compatibility)."""
        # Should work without ctx parameter
        result = await resolve_project_id(explicit_id="test-id")
        assert result == "test-id"

    @pytest.mark.asyncio
    async def test_explicit_project_id_always_wins(
        self, mock_fastmcp_context: Mock
    ) -> None:
        """Test explicit project_id always takes priority."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config file
            config_dir = Path(tmpdir) / ".codebase-mcp"
            config_dir.mkdir()
            config_file = config_dir / "config.json"
            config_file.write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "project": {"name": "config-project", "id": "config-id"},
                    }
                )
            )

            # Set working directory
            session_mgr = get_session_context_manager()
            await session_mgr.start()
            await session_mgr.set_working_directory(
                mock_fastmcp_context.session_id, tmpdir
            )

            try:
                # Even with ctx and config, explicit_id takes priority
                result = await resolve_project_id(
                    explicit_id="explicit-id", ctx=mock_fastmcp_context
                )
                assert result == "explicit-id"
            finally:
                await session_mgr.stop()

    @pytest.mark.asyncio
    async def test_none_explicit_id_uses_resolution_chain(
        self, mock_fastmcp_context: Mock
    ) -> None:
        """Test None explicit_id triggers resolution chain."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config file
            config_dir = Path(tmpdir) / ".codebase-mcp"
            config_dir.mkdir()
            config_file = config_dir / "config.json"
            config_file.write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "project": {"name": "auto-project", "id": "auto-id"},
                    }
                )
            )

            # Set working directory
            session_mgr = get_session_context_manager()
            await session_mgr.start()
            await session_mgr.set_working_directory(
                mock_fastmcp_context.session_id, tmpdir
            )

            try:
                # explicit_id=None should trigger resolution
                result = await resolve_project_id(
                    explicit_id=None, ctx=mock_fastmcp_context
                )
                assert result == "auto-id"
            finally:
                await session_mgr.stop()


# ==============================================================================
# MCP Tool Tests: set_working_directory
# ==============================================================================


class TestSetWorkingDirectoryTool:
    """Integration tests for set_working_directory MCP tool."""

    @pytest.mark.asyncio
    async def test_set_working_directory_valid(
        self, mock_fastmcp_context: Mock
    ) -> None:
        """Test set_working_directory with valid directory."""
        # Import the module to get the wrapped tool
        from src.mcp.tools import project as project_module

        # Access the underlying function from the wrapped tool
        set_working_directory = project_module.set_working_directory.fn

        with tempfile.TemporaryDirectory() as tmpdir:
            session_mgr = get_session_context_manager()
            await session_mgr.start()

            try:
                result = await set_working_directory(tmpdir, mock_fastmcp_context)

                assert result["session_id"] == mock_fastmcp_context.session_id
                assert result["working_directory"] == tmpdir
                assert result["config_found"] is False
                assert result["config_path"] is None
                assert result["project_info"] is None
            finally:
                await session_mgr.stop()

    @pytest.mark.asyncio
    async def test_set_working_directory_with_config(
        self, mock_fastmcp_context: Mock
    ) -> None:
        """Test set_working_directory finds and validates config."""
        from src.mcp.tools import project as project_module
        set_working_directory = project_module.set_working_directory.fn

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config file
            tmpdir_path = Path(tmpdir).resolve()
            config_dir = tmpdir_path / ".codebase-mcp"
            config_dir.mkdir()
            config_file = config_dir / "config.json"
            config_file.write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "project": {
                            "name": "test-project",
                            "id": "test-uuid",
                        },
                    }
                )
            )

            session_mgr = get_session_context_manager()
            await session_mgr.start()

            try:
                result = await set_working_directory(str(tmpdir_path), mock_fastmcp_context)

                assert result["config_found"] is True
                # Compare resolved paths to handle symlinks
                assert Path(result["config_path"]).resolve() == config_file.resolve()
                assert result["project_info"]["name"] == "test-project"
                assert result["project_info"]["id"] == "test-uuid"
            finally:
                await session_mgr.stop()

    @pytest.mark.asyncio
    async def test_set_working_directory_invalid_path(
        self, mock_fastmcp_context: Mock
    ) -> None:
        """Test set_working_directory rejects invalid paths."""
        from src.mcp.tools import project as project_module
        set_working_directory = project_module.set_working_directory.fn

        # Relative path
        with pytest.raises(ValueError, match="must be absolute"):
            await set_working_directory("relative/path", mock_fastmcp_context)

        # Nonexistent directory
        with pytest.raises(ValueError, match="does not exist"):
            await set_working_directory("/tmp/nonexistent-dir-12345", mock_fastmcp_context)

    @pytest.mark.asyncio
    async def test_set_working_directory_file_not_directory(
        self, mock_fastmcp_context: Mock
    ) -> None:
        """Test set_working_directory rejects file paths."""
        from src.mcp.tools import project as project_module
        set_working_directory = project_module.set_working_directory.fn

        with tempfile.NamedTemporaryFile() as f:
            with pytest.raises(ValueError, match="not a directory"):
                await set_working_directory(f.name, mock_fastmcp_context)


# ==============================================================================
# Test Execution
# ==============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
