"""
Example usage of the structured logging module.

This file demonstrates proper usage patterns for the logging module
with constitutional compliance.
"""

from __future__ import annotations

from pathlib import Path

from src.mcp.mcp_logging import get_logger, get_structured_logger


def example_basic_logging() -> None:
    """Example: Basic logging with standard logger."""
    logger = get_logger(__name__)

    logger.info("Service started")
    logger.debug("Processing request")
    logger.warning("Slow operation detected")


def example_structured_logging() -> None:
    """Example: Structured logging with context."""
    logger = get_structured_logger(__name__)

    # Log with context
    logger.info(
        "Repository indexed successfully",
        context={
            "repository_id": "repo-12345",
            "repository_path": "/path/to/repo",
            "files_processed": 1000,
            "duration_ms": 1234.56,
        },
    )


def example_error_logging() -> None:
    """Example: Error logging with exception context."""
    logger = get_structured_logger(__name__)

    try:
        # Simulate error
        msg = "Database connection failed"
        raise ConnectionError(msg)
    except ConnectionError:
        logger.error(
            "Failed to connect to database",
            context={
                "operation": "index_repository",
                "repository_id": "repo-67890",
            },
        )


def example_performance_logging() -> None:
    """Example: Performance metrics logging."""
    logger = get_structured_logger(__name__)

    start_time = 0.0  # In real code: time.perf_counter()
    # ... do work ...
    duration_ms = 1500.0  # In real code: (time.perf_counter() - start_time) * 1000

    logger.info(
        "Repository indexing completed",
        context={
            "repository_id": "repo-11111",
            "duration_ms": duration_ms,
            "files_processed": 2500,
            "embeddings_count": 15000,
        },
    )


def example_custom_configuration() -> None:
    """Example: Custom logging configuration."""
    from src.mcp.mcp_logging import configure_logging
    import logging

    # Configure with custom settings
    configure_logging(
        log_file=Path("/var/log/mcp-server.log"),
        max_bytes=50 * 1024 * 1024,  # 50MB
        backup_count=10,
        level=logging.DEBUG,
    )

    logger = get_structured_logger(__name__)
    logger.debug("Custom configuration loaded")


if __name__ == "__main__":
    # These examples demonstrate usage patterns
    # The actual log output goes to /tmp/codebase-mcp.log
    example_basic_logging()
    example_structured_logging()
    example_error_logging()
    example_performance_logging()
