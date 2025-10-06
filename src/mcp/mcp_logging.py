"""
Structured logging module for Codebase MCP Server.

Constitutional Compliance:
- Principle III: Protocol Compliance - No stdout/stderr pollution
- Principle V: Production Quality - Structured, rotatable, comprehensive error handling
- Principle VIII: Type Safety - Full mypy --strict compliance

Features:
- JSON structured logging for easy parsing
- File-only output to /tmp/codebase-mcp.log
- Automatic log rotation (100MB per file, 5 backup files)
- Contextual logging with request IDs and operation metadata
- Full type safety with mypy --strict compliance
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final, Mapping, TypedDict, cast

from pydantic import BaseModel, ConfigDict, Field

# ==============================================================================
# Constants
# ==============================================================================

LOG_FILE_PATH: Final[Path] = Path("/tmp/codebase-mcp.log")
LOG_MAX_BYTES: Final[int] = 100 * 1024 * 1024  # 100MB
LOG_BACKUP_COUNT: Final[int] = 5
LOG_FORMAT_VERSION: Final[str] = "1.0"

# ==============================================================================
# Type Definitions
# ==============================================================================


class LogContext(TypedDict, total=False):
    """Type-safe structure for logging context metadata."""

    # Request/Operation Context
    request_id: str
    operation: str
    repository_id: str
    repository_path: str

    # Performance Metrics
    duration_ms: float
    latency_ms: float

    # Error Context
    error: str
    error_type: str
    traceback: str

    # Additional Context
    files_processed: int
    embeddings_count: int
    custom: dict[str, Any]


class StructuredLogRecord(BaseModel):
    """
    Pydantic model for structured log records.

    Ensures type safety and validation of log output format.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: str = Field(
        ...,
        description="ISO 8601 timestamp with timezone",
    )
    level: str = Field(
        ...,
        description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )
    logger: str = Field(
        ...,
        description="Logger name (typically module name)",
    )
    module: str = Field(
        ...,
        description="Python module where log was generated",
    )
    function: str = Field(
        ...,
        description="Function name where log was generated",
    )
    line: int = Field(
        ...,
        description="Line number where log was generated",
    )
    message: str = Field(
        ...,
        description="Human-readable log message",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional structured context data",
    )
    format_version: str = Field(
        default=LOG_FORMAT_VERSION,
        description="Log format version for backward compatibility",
    )


# ==============================================================================
# JSON Formatter
# ==============================================================================


class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging.

    Outputs log records as JSON lines with full type safety.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON string.

        Args:
            record: Python logging.LogRecord to format

        Returns:
            JSON string representation of the log record
        """
        # Extract base log information
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()

        # Extract context from the 'extra' attribute if present
        context: dict[str, Any] = {}
        if hasattr(record, "context") and isinstance(record.context, dict):
            context = cast(dict[str, Any], record.context)

        # Add exception information if present
        if record.exc_info:
            context["error_type"] = record.exc_info[0].__name__ if record.exc_info[0] else "Unknown"
            context["error"] = str(record.exc_info[1]) if record.exc_info[1] else ""
            context["traceback"] = "".join(
                traceback.format_exception(*record.exc_info)
            ).strip()

        # Create structured log record
        log_entry = StructuredLogRecord(
            timestamp=timestamp,
            level=record.levelname,
            logger=record.name,
            module=record.module,
            function=record.funcName,
            line=record.lineno,
            message=record.getMessage(),
            context=context,
        )

        # Convert to JSON
        return log_entry.model_dump_json(exclude_none=True)


# ==============================================================================
# Logger Configuration
# ==============================================================================


class LoggerManager:
    """
    Singleton logger manager for the MCP server.

    Ensures all loggers use structured JSON format and file-only output.
    """

    _instance: LoggerManager | None = None
    _configured: bool = False

    def __new__(cls) -> LoggerManager:
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def configure_logging(
        self,
        *,
        log_file: Path = LOG_FILE_PATH,
        max_bytes: int = LOG_MAX_BYTES,
        backup_count: int = LOG_BACKUP_COUNT,
        level: int = logging.INFO,
    ) -> None:
        """
        Configure the root logger with structured JSON file logging.

        Args:
            log_file: Path to log file (default: /tmp/codebase-mcp.log)
            max_bytes: Maximum size per log file before rotation (default: 100MB)
            backup_count: Number of backup files to keep (default: 5)
            level: Minimum log level (default: logging.INFO)

        Note:
            This method is idempotent - calling it multiple times has no effect
            after the first call.
        """
        if self._configured:
            return

        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_file),
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )

        # Set JSON formatter
        json_formatter = JSONFormatter()
        file_handler.setFormatter(json_formatter)

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        root_logger.addHandler(file_handler)

        # CRITICAL: Remove any default console handlers to prevent stdout/stderr pollution
        # This ensures Principle III (Protocol Compliance) - MCP protocol requires
        # clean stdout/stderr for SSE communication
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.StreamHandler) and handler.stream in (
                sys.stdout,
                sys.stderr,
            ):
                root_logger.removeHandler(handler)

        self._configured = True

        # Log configuration success
        config_logger = logging.getLogger(__name__)
        config_logger.info(
            "Structured logging configured",
            extra={
                "context": {
                    "log_file": str(log_file),
                    "max_bytes": max_bytes,
                    "backup_count": backup_count,
                    "level": logging.getLevelName(level),
                }
            },
        )

    def is_configured(self) -> bool:
        """Check if logging is configured."""
        return self._configured


# ==============================================================================
# Public API
# ==============================================================================


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.

    Args:
        name: Logger name (typically __name__ from calling module)

    Returns:
        Configured logger instance with structured JSON output

    Example:
        >>> from src.mcp.mcp_logging import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Repository indexed", extra={"context": {"repo_id": "123"}})
    """
    # Ensure logging is configured (idempotent)
    manager = LoggerManager()
    if not manager.is_configured():
        manager.configure_logging()

    return logging.getLogger(name)


def configure_logging(
    *,
    log_file: Path = LOG_FILE_PATH,
    max_bytes: int = LOG_MAX_BYTES,
    backup_count: int = LOG_BACKUP_COUNT,
    level: int = logging.INFO,
) -> None:
    """
    Manually configure logging with custom settings.

    Args:
        log_file: Path to log file (default: /tmp/codebase-mcp.log)
        max_bytes: Maximum size per log file before rotation (default: 100MB)
        backup_count: Number of backup files to keep (default: 5)
        level: Minimum log level (default: logging.INFO)

    Example:
        >>> from pathlib import Path
        >>> configure_logging(log_file=Path("/var/log/mcp.log"), level=logging.DEBUG)
    """
    manager = LoggerManager()
    manager.configure_logging(
        log_file=log_file,
        max_bytes=max_bytes,
        backup_count=backup_count,
        level=level,
    )


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    context: LogContext | None = None,
    exc_info: bool = False,
) -> None:
    """
    Log a message with structured context.

    Args:
        logger: Logger instance
        level: Log level (logging.INFO, logging.ERROR, etc.)
        message: Human-readable log message
        context: Structured context data
        exc_info: Whether to include exception information

    Example:
        >>> logger = get_logger(__name__)
        >>> log_with_context(
        ...     logger,
        ...     logging.INFO,
        ...     "Repository indexed",
        ...     context={"repository_id": "123", "files_processed": 1000}
        ... )
    """
    extra: dict[str, Any] = {}
    if context:
        extra["context"] = dict(context)

    logger.log(level, message, extra=extra, exc_info=exc_info)


# ==============================================================================
# Convenience Logging Methods
# ==============================================================================


class StructuredLogger:
    """
    Convenience wrapper around logging.Logger with structured context support.

    Provides type-safe methods for common logging operations with context.
    """

    def __init__(self, logger: logging.Logger) -> None:
        """Initialize with a logger instance."""
        self._logger = logger

    def debug(
        self,
        message: str,
        context: LogContext | None = None,
        exc_info: bool = False,
    ) -> None:
        """Log debug message with context."""
        log_with_context(self._logger, logging.DEBUG, message, context, exc_info)

    def info(
        self,
        message: str,
        context: LogContext | None = None,
        exc_info: bool = False,
    ) -> None:
        """Log info message with context."""
        log_with_context(self._logger, logging.INFO, message, context, exc_info)

    def warning(
        self,
        message: str,
        context: LogContext | None = None,
        exc_info: bool = False,
    ) -> None:
        """Log warning message with context."""
        log_with_context(self._logger, logging.WARNING, message, context, exc_info)

    def error(
        self,
        message: str,
        context: LogContext | None = None,
        exc_info: bool = True,
    ) -> None:
        """Log error message with context (includes exception info by default)."""
        log_with_context(self._logger, logging.ERROR, message, context, exc_info)

    def critical(
        self,
        message: str,
        context: LogContext | None = None,
        exc_info: bool = True,
    ) -> None:
        """Log critical message with context (includes exception info by default)."""
        log_with_context(self._logger, logging.CRITICAL, message, context, exc_info)


def get_structured_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger with convenience methods.

    Args:
        name: Logger name (typically __name__ from calling module)

    Returns:
        StructuredLogger instance with type-safe context support

    Example:
        >>> logger = get_structured_logger(__name__)
        >>> logger.info("Repository indexed", context={"repository_id": "123"})
    """
    return StructuredLogger(get_logger(name))


# ==============================================================================
# Module Initialization
# ==============================================================================

# Auto-configure logging when module is imported
_manager = LoggerManager()
if not _manager.is_configured():
    _manager.configure_logging()

__all__ = [
    "LogContext",
    "StructuredLogger",
    "configure_logging",
    "get_logger",
    "get_structured_logger",
    "log_with_context",
]
