"""Config validation for .codebase-mcp/config.json files.

Validates:
- UTF-8 encoding
- JSON parsing
- Required fields (version, project.name)
- Type constraints
- Version format (major.minor)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def validate_config_syntax(config_path: Path) -> dict[str, Any]:
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
    except (OSError, FileNotFoundError) as e:
        raise ValueError(f"Cannot read config file {config_path}: {e}")

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
        raise ValueError(
            f"Invalid version format '{config['version']}' in {config_path}, "
            f"expected 'major.minor' (e.g., '1.0')"
        )

    return config
