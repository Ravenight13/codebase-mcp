"""
Configuration module for Codebase MCP Server.

Exports:
    - Settings: Pydantic settings class
    - LogLevel: Logging level enum
    - get_settings: Function to get singleton settings instance
    - settings: Module-level singleton settings instance
"""

from src.config.settings import LogLevel, Settings, get_settings, settings

__all__ = [
    "Settings",
    "LogLevel",
    "get_settings",
    "settings",
]
