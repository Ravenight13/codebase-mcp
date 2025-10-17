"""Project management tools for session-based workspace switching."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastmcp import Context

from src.auto_switch.discovery import find_config_file
from src.auto_switch.session_context import get_session_context_manager
from src.auto_switch.validation import validate_config_syntax
from src.mcp.mcp_logging import get_logger
from src.mcp.server_fastmcp import mcp

logger = get_logger(__name__)


@mcp.tool()
async def set_working_directory(
    directory: str,
    ctx: Context,
) -> dict[str, Any]:
    """Set working directory for session-based project auto-switching.

    Enables automatic project resolution by storing the working directory
    for this MCP session. Subsequent operations will use the project
    configuration found in .codebase-mcp/config.json (searches up to 20 levels).

    Args:
        directory: Absolute path to working directory
        ctx: FastMCP context (provides session_id)

    Returns:
        Dictionary with session info:
        {
            "session_id": str,
            "working_directory": str,
            "config_found": bool,
            "config_path": str | None,
            "project_info": {
                "name": str,
                "id": str | None
            } | None
        }

    Raises:
        ValueError: If directory path is invalid

    Example:
        >>> result = await set_working_directory(
        ...     directory="/Users/alice/projects/my-app",
        ...     ctx=ctx
        ... )
        >>> print(result["config_found"])  # True
        >>> print(result["project_info"]["name"])  # "my-app"
    """
    # Validate directory path
    directory_path = Path(directory)

    if not directory_path.is_absolute():
        raise ValueError(f"Directory path must be absolute: {directory}")

    if not directory_path.exists():
        raise ValueError(f"Directory does not exist: {directory}")

    if not directory_path.is_dir():
        raise ValueError(f"Path is not a directory: {directory}")

    # Get session ID from FastMCP Context
    session_id = ctx.session_id

    # Store working directory for this session
    session_mgr = get_session_context_manager()
    await session_mgr.set_working_directory(session_id, str(directory_path))

    logger.info(
        f"Set working directory for session {session_id}: {directory_path}",
        extra={
            "context": {
                "operation": "set_working_directory",
                "session_id": session_id,
                "directory": str(directory_path),
            }
        },
    )

    # Try to find config file (optional - for immediate feedback)
    config_found = False
    config_path_str = None
    project_info = None

    try:
        config_path = find_config_file(directory_path)
        if config_path:
            config_found = True
            config_path_str = str(config_path)

            # Validate config (optional - for immediate feedback)
            try:
                config = validate_config_syntax(config_path)
                project_info = {
                    "name": config["project"]["name"],
                    "id": config["project"].get("id"),
                }
                logger.info(
                    f"Found valid config for session {session_id}: {project_info}",
                    extra={
                        "context": {
                            "operation": "set_working_directory",
                            "session_id": session_id,
                            "config_path": config_path_str,
                            "project_name": project_info["name"],
                        }
                    },
                )
            except Exception as e:
                logger.warning(
                    f"Config file found but invalid: {e}",
                    extra={
                        "context": {
                            "operation": "set_working_directory",
                            "session_id": session_id,
                            "config_path": config_path_str,
                            "error": str(e),
                        }
                    },
                )
        else:
            logger.info(
                f"No config file found for session {session_id} (searched 20 levels)",
                extra={
                    "context": {
                        "operation": "set_working_directory",
                        "session_id": session_id,
                        "directory": str(directory_path),
                    }
                },
            )
    except Exception as e:
        logger.debug(
            f"Error searching for config: {e}",
            extra={
                "context": {
                    "operation": "set_working_directory",
                    "session_id": session_id,
                    "error": str(e),
                }
            },
        )

    return {
        "session_id": session_id,
        "working_directory": str(directory_path),
        "config_found": config_found,
        "config_path": config_path_str,
        "project_info": project_info,
    }
