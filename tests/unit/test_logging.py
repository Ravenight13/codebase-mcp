"""
Unit tests for structured logging module.

Tests verify:
- JSON structured output format
- File-only logging (no stdout/stderr pollution)
- Log rotation functionality
- Type safety compliance
- Context logging capabilities
- Exception logging with tracebacks
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

import pytest

from src.mcp.mcp_logging import (
    JSONFormatter,
    LoggerManager,
    StructuredLogger,
    configure_logging,
    get_logger,
    get_structured_logger,
)


@pytest.fixture
def temp_log_file(tmp_path: Path) -> Path:
    """Create temporary log file path."""
    return tmp_path / "test-mcp.log"


@pytest.fixture
def clean_logger_manager() -> Any:
    """Reset logger manager singleton state before each test."""
    # Reset singleton state
    LoggerManager._instance = None
    LoggerManager._configured = False

    # Clear all handlers from root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    yield

    # Cleanup after test
    LoggerManager._instance = None
    LoggerManager._configured = False
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)


class TestJSONFormatter:
    """Test JSON log formatter."""

    def test_basic_formatting(self) -> None:
        """Test basic log record formatting to JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test"
        record.funcName = "test_function"

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test.module"
        assert log_data["module"] == "test"
        assert log_data["function"] == "test_function"
        assert log_data["line"] == 42
        assert log_data["message"] == "Test message"
        assert "timestamp" in log_data
        assert "format_version" in log_data

    def test_formatting_with_context(self) -> None:
        """Test log formatting with additional context."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.module",
            level=logging.INFO,
            pathname="/path/to/test.py",
            lineno=42,
            msg="Repository indexed",
            args=(),
            exc_info=None,
        )
        record.module = "test"
        record.funcName = "test_function"
        record.context = {"repository_id": "test-repo-123", "files_processed": 1000}

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["message"] == "Repository indexed"
        assert log_data["context"]["repository_id"] == "test-repo-123"
        assert log_data["context"]["files_processed"] == 1000

    def test_formatting_with_exception(self) -> None:
        """Test log formatting with exception information."""
        formatter = JSONFormatter()

        try:
            msg = "Test exception"
            raise ValueError(msg)
        except ValueError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test.module",
            level=logging.ERROR,
            pathname="/path/to/test.py",
            lineno=42,
            msg="An error occurred",
            args=(),
            exc_info=exc_info,
        )
        record.module = "test"
        record.funcName = "test_function"

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["level"] == "ERROR"
        assert log_data["message"] == "An error occurred"
        assert log_data["context"]["error_type"] == "ValueError"
        assert "Test exception" in log_data["context"]["error"]
        assert "traceback" in log_data["context"]
        assert "ValueError" in log_data["context"]["traceback"]


class TestLoggerManager:
    """Test logger manager singleton."""

    def test_singleton_instance(self, clean_logger_manager: None) -> None:
        """Test that LoggerManager is a singleton."""
        manager1 = LoggerManager()
        manager2 = LoggerManager()
        assert manager1 is manager2

    def test_configuration_idempotency(
        self,
        clean_logger_manager: None,
        temp_log_file: Path,
    ) -> None:
        """Test that configure_logging can be called multiple times safely."""
        manager = LoggerManager()
        manager.configure_logging(log_file=temp_log_file)
        assert manager.is_configured()

        # Second call should be no-op
        manager.configure_logging(log_file=temp_log_file)
        assert manager.is_configured()

    def test_no_console_handlers(
        self,
        clean_logger_manager: None,
        temp_log_file: Path,
    ) -> None:
        """Test that console handlers are removed (no stdout/stderr pollution)."""
        manager = LoggerManager()
        manager.configure_logging(log_file=temp_log_file)

        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler):
                assert handler.stream not in (sys.stdout, sys.stderr), (
                    "Console handlers detected - violates Principle III "
                    "(Protocol Compliance)"
                )

    def test_log_file_creation(
        self,
        clean_logger_manager: None,
        temp_log_file: Path,
    ) -> None:
        """Test that log file is created."""
        manager = LoggerManager()
        manager.configure_logging(log_file=temp_log_file)

        # Write a log message
        logger = logging.getLogger("test")
        logger.info("Test message")

        # Verify file exists and contains data
        assert temp_log_file.exists()
        content = temp_log_file.read_text()
        assert len(content) > 0

        # Verify it's valid JSON (multiple lines)
        log_lines = content.strip().split("\n")
        assert len(log_lines) >= 1

        # Find the test message log entry
        test_log_entry = None
        for line in log_lines:
            log_data = json.loads(line)
            if log_data["message"] == "Test message":
                test_log_entry = log_data
                break

        assert test_log_entry is not None
        assert test_log_entry["message"] == "Test message"


class TestPublicAPI:
    """Test public API functions."""

    def test_get_logger(self, clean_logger_manager: None, temp_log_file: Path) -> None:
        """Test get_logger function."""
        configure_logging(log_file=temp_log_file)
        logger = get_logger("test.module")

        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_get_structured_logger(
        self,
        clean_logger_manager: None,
        temp_log_file: Path,
    ) -> None:
        """Test get_structured_logger function."""
        configure_logging(log_file=temp_log_file)
        logger = get_structured_logger("test.module")

        assert isinstance(logger, StructuredLogger)

    def test_configure_logging_custom_parameters(
        self,
        clean_logger_manager: None,
        temp_log_file: Path,
    ) -> None:
        """Test configure_logging with custom parameters."""
        configure_logging(
            log_file=temp_log_file,
            max_bytes=50 * 1024 * 1024,  # 50MB
            backup_count=3,
            level=logging.DEBUG,
        )

        manager = LoggerManager()
        assert manager.is_configured()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG


class TestStructuredLogger:
    """Test StructuredLogger convenience wrapper."""

    def test_info_logging(
        self,
        clean_logger_manager: None,
        temp_log_file: Path,
    ) -> None:
        """Test info level logging with context."""
        configure_logging(log_file=temp_log_file)
        logger = get_structured_logger("test.module")

        logger.info(
            "Repository indexed",
            context={"repository_id": "test-123", "files_processed": 500},
        )

        content = temp_log_file.read_text()
        log_data = json.loads(content.strip().split("\n")[-1])

        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Repository indexed"
        assert log_data["context"]["repository_id"] == "test-123"
        assert log_data["context"]["files_processed"] == 500

    def test_error_logging_with_exception(
        self,
        clean_logger_manager: None,
        temp_log_file: Path,
    ) -> None:
        """Test error logging with exception context."""
        configure_logging(log_file=temp_log_file)
        logger = get_structured_logger("test.module")

        try:
            msg = "Database connection failed"
            raise ConnectionError(msg)
        except ConnectionError:
            logger.error(
                "Failed to index repository",
                context={"repository_id": "test-456"},
            )

        content = temp_log_file.read_text()
        log_data = json.loads(content.strip().split("\n")[-1])

        assert log_data["level"] == "ERROR"
        assert log_data["message"] == "Failed to index repository"
        assert log_data["context"]["repository_id"] == "test-456"
        assert log_data["context"]["error_type"] == "ConnectionError"
        assert "Database connection failed" in log_data["context"]["error"]
        assert "traceback" in log_data["context"]

    def test_debug_logging(
        self,
        clean_logger_manager: None,
        temp_log_file: Path,
    ) -> None:
        """Test debug level logging."""
        configure_logging(log_file=temp_log_file, level=logging.DEBUG)
        logger = get_structured_logger("test.module")

        # Type-safe context using custom dict
        context: dict[str, Any] = {"filename": "test.py"}
        logger.debug("Processing file", context=context)  # type: ignore[arg-type]

        content = temp_log_file.read_text()
        log_data = json.loads(content.strip().split("\n")[-1])

        assert log_data["level"] == "DEBUG"
        assert log_data["message"] == "Processing file"
        assert log_data["context"]["filename"] == "test.py"

    def test_warning_logging(
        self,
        clean_logger_manager: None,
        temp_log_file: Path,
    ) -> None:
        """Test warning level logging."""
        configure_logging(log_file=temp_log_file)
        logger = get_structured_logger("test.module")

        logger.warning("Slow operation detected", context={"duration_ms": 5000.0})

        content = temp_log_file.read_text()
        log_data = json.loads(content.strip().split("\n")[-1])

        assert log_data["level"] == "WARNING"
        assert log_data["message"] == "Slow operation detected"
        assert log_data["context"]["duration_ms"] == 5000.0

    def test_critical_logging(
        self,
        clean_logger_manager: None,
        temp_log_file: Path,
    ) -> None:
        """Test critical level logging."""
        configure_logging(log_file=temp_log_file)
        logger = get_structured_logger("test.module")

        try:
            msg = "Database unavailable"
            raise RuntimeError(msg)
        except RuntimeError:
            context: dict[str, Any] = {"subsystem": "database"}
            logger.critical(
                "System failure",
                context=context,  # type: ignore[arg-type]
            )

        content = temp_log_file.read_text()
        log_data = json.loads(content.strip().split("\n")[-1])

        assert log_data["level"] == "CRITICAL"
        assert log_data["message"] == "System failure"
        assert log_data["context"]["subsystem"] == "database"
        assert "error_type" in log_data["context"]


class TestLogRotation:
    """Test log rotation functionality."""

    def test_log_rotation_on_size(
        self,
        clean_logger_manager: None,
        temp_log_file: Path,
    ) -> None:
        """Test that logs rotate when size limit is reached."""
        # Configure with very small max_bytes for testing
        small_max_bytes = 1024  # 1KB
        configure_logging(
            log_file=temp_log_file,
            max_bytes=small_max_bytes,
            backup_count=2,
        )

        logger = get_structured_logger("test.module")

        # Write enough logs to trigger rotation
        for i in range(100):
            context: dict[str, Any] = {"iteration": i}
            logger.info(
                "Test log message " * 10,  # Make message long enough
                context=context,  # type: ignore[arg-type]
            )

        # Check that rotation occurred
        rotated_files = list(temp_log_file.parent.glob(f"{temp_log_file.name}.*"))
        assert len(rotated_files) > 0, "Log rotation should have created backup files"


class TestConstitutionalCompliance:
    """Test constitutional principle compliance."""

    def test_no_stdout_stderr_pollution(
        self,
        clean_logger_manager: None,
        temp_log_file: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """
        Test Principle III: Protocol Compliance - No stdout/stderr pollution.

        MCP protocol requires clean stdout/stderr for SSE communication.
        """
        configure_logging(log_file=temp_log_file, level=logging.DEBUG)
        logger = get_structured_logger("test.module")

        # Log various levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")

        try:
            msg = "Test error"
            raise ValueError(msg)
        except ValueError:
            logger.error("Error message")

        # Verify no output to stdout/stderr
        captured = capsys.readouterr()
        assert captured.out == "", "stdout should be empty (Principle III violation)"
        assert captured.err == "", "stderr should be empty (Principle III violation)"

        # Verify logs were written to file
        assert temp_log_file.exists()
        content = temp_log_file.read_text()

        # Parse each log line and check for messages
        log_lines = content.strip().split("\n")
        messages = []
        for line in log_lines:
            log_data = json.loads(line)
            messages.append(log_data["message"])

        assert "Debug message" in messages
        assert "Info message" in messages
        assert "Warning message" in messages
        assert "Error message" in messages

    def test_structured_format_for_production(
        self,
        clean_logger_manager: None,
        temp_log_file: Path,
    ) -> None:
        """
        Test Principle V: Production Quality - Structured logging.

        Logs must be machine-parseable for production monitoring.
        """
        configure_logging(log_file=temp_log_file)
        logger = get_structured_logger("test.module")

        logger.info(
            "Repository indexed",
            context={
                "repository_id": "prod-repo-789",
                "files_processed": 2500,
                "duration_ms": 1234.56,
            },
        )

        content = temp_log_file.read_text()

        # Find the repository indexed log entry
        log_lines = content.strip().split("\n")
        log_data = None
        for line in log_lines:
            entry = json.loads(line)
            if entry["message"] == "Repository indexed":
                log_data = entry
                break

        assert log_data is not None, "Could not find 'Repository indexed' log entry"

        # Verify all required fields are present
        required_fields = [
            "timestamp",
            "level",
            "logger",
            "module",
            "function",
            "line",
            "message",
            "context",
        ]
        for field in required_fields:
            assert field in log_data, f"Missing required field: {field}"

        # Verify ISO 8601 timestamp format
        assert "T" in log_data["timestamp"]
        assert "Z" in log_data["timestamp"] or "+" in log_data["timestamp"]

    def test_type_safety_compliance(
        self,
        clean_logger_manager: None,
        temp_log_file: Path,
    ) -> None:
        """
        Test Principle VIII: Type Safety - Pydantic validation.

        Log records must be type-safe and validated.
        """
        configure_logging(log_file=temp_log_file)
        logger = get_structured_logger("test.module")

        # Log with typed context
        logger.info(
            "Operation completed",
            context={
                "operation": "index_repository",
                "duration_ms": 123.45,
                "files_processed": 100,
            },
        )

        content = temp_log_file.read_text()

        # Find the operation completed log entry
        log_lines = content.strip().split("\n")
        log_data = None
        for line in log_lines:
            entry = json.loads(line)
            if entry["message"] == "Operation completed":
                log_data = entry
                break

        assert log_data is not None, "Could not find 'Operation completed' log entry"

        # Verify type preservation
        assert isinstance(log_data["context"]["duration_ms"], float)
        assert isinstance(log_data["context"]["files_processed"], int)
        assert isinstance(log_data["context"]["operation"], str)
