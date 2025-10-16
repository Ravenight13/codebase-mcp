"""Config file discovery with upward directory traversal.

This module implements the config discovery algorithm for automatic project
switching. It searches for .codebase-mcp/config.json starting from a working
directory and traversing upward through parent directories until found or
reaching filesystem root/max depth.

Constitutional Compliance:
- Principle 2 (Local-First): No network calls, filesystem-only operations
- Principle 5 (Production Quality): Comprehensive error handling for symlinks,
  permissions, and filesystem boundaries
"""

from __future__ import annotations

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
    1. Start from working_directory (with symlink resolution)
    2. Check for .codebase-mcp/config.json in current directory
    3. Move to parent directory if not found
    4. Stop at: config found, filesystem root, or max_depth

    Args:
        working_directory: Absolute path to start search
        max_depth: Maximum levels to search upward (default: 20)

    Returns:
        Path to config.json if found, None otherwise

    Examples:
        >>> config = find_config_file(Path("/home/user/project/subdir"))
        >>> # Returns: Path("/home/user/project/.codebase-mcp/config.json")

        >>> config = find_config_file(Path("/tmp/no-config"))
        >>> # Returns: None
    """
    # Resolve symlinks with error handling
    try:
        current = working_directory.resolve()
    except (OSError, RuntimeError) as e:
        logger.warning(
            f"Failed to resolve symlinks in {working_directory}: {e}. "
            f"Using path as-is."
        )
        current = working_directory

    for level in range(max_depth):
        config_path = current / ".codebase-mcp" / "config.json"

        try:
            if config_path.exists() and config_path.is_file():
                logger.info(f"Found config at {config_path} (level {level})")
                return config_path
        except (OSError, PermissionError) as e:
            logger.warning(f"Cannot access {config_path}: {e}")
            # Continue search in parent directories

        # Check if we've reached filesystem root
        parent = current.parent
        if parent == current:
            logger.debug(f"Reached filesystem root without finding config")
            return None

        current = parent

    logger.debug(f"Max depth {max_depth} reached without finding config")
    return None
