"""Config-based project tracking with session isolation.

This module implements automatic project switching based on .codebase-mcp/config.json
files discovered in the working directory tree. It provides:

- Session-based isolation for multi-client support
- LRU cache with mtime-based invalidation
- Async-safe concurrency primitives
- Background cleanup of stale sessions
"""

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
