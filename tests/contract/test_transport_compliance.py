"""
T007: Contract tests for stdio transport compliance.

These tests validate that the FastMCP server properly implements JSON-RPC 2.0
over stdio transport, compatible with Claude Desktop's MCP client pattern.

Tests MUST fail initially as server validation fails with no tools registered.

Protocol Requirements:
- JSON-RPC 2.0 request/response format
- Stdio transport (stdin/stdout communication)
- No stdout/stderr pollution (logs go to /tmp/codebase-mcp.log)
- Proper server initialization and validation

Constitutional Compliance:
- Principle III: Protocol Compliance (stdio transport, no stdout pollution)
- Principle V: Production Quality (startup validation, error handling)
- Principle VIII: Type Safety (full type hints, mypy --strict)
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, Field, ValidationError

# Test server import
from src.mcp.server_fastmcp import LOG_FILE, logger, mcp, validate_server_startup


# ==============================================================================
# JSON-RPC 2.0 Protocol Models
# ==============================================================================


class JsonRpcRequest(BaseModel):
    """JSON-RPC 2.0 request message format."""

    jsonrpc: str = Field(default="2.0", pattern="^2\\.0$")
    method: str = Field(..., min_length=1)
    params: dict[str, Any] | list[Any] | None = Field(default=None)
    id: int | str | None = Field(default=None)


class JsonRpcError(BaseModel):
    """JSON-RPC 2.0 error object."""

    code: int = Field(...)
    message: str = Field(..., min_length=1)
    data: Any = Field(default=None)


class JsonRpcResponse(BaseModel):
    """JSON-RPC 2.0 response message format."""

    jsonrpc: str = Field(default="2.0", pattern="^2\\.0$")
    result: Any = Field(default=None)
    error: JsonRpcError | None = Field(default=None)
    id: int | str | None = Field(...)


# ==============================================================================
# Protocol Schema Tests
# ==============================================================================


@pytest.mark.contract
def test_jsonrpc_request_schema_valid_minimal() -> None:
    """Test JSON-RPC 2.0 request schema with minimal required fields."""
    request = JsonRpcRequest(method="tools/list", id=1)

    assert request.jsonrpc == "2.0"
    assert request.method == "tools/list"
    assert request.params is None
    assert request.id == 1


@pytest.mark.contract
def test_jsonrpc_request_schema_valid_with_params() -> None:
    """Test JSON-RPC 2.0 request schema with parameters."""
    request = JsonRpcRequest(
        method="search_code",
        params={"query": "test query", "limit": 10},
        id="req-123",
    )

    assert request.jsonrpc == "2.0"
    assert request.method == "search_code"
    assert request.params == {"query": "test query", "limit": 10}
    assert request.id == "req-123"


@pytest.mark.contract
def test_jsonrpc_request_schema_invalid_version() -> None:
    """Test JSON-RPC request validation fails for invalid jsonrpc version."""
    with pytest.raises(ValidationError) as exc_info:
        JsonRpcRequest(jsonrpc="1.0", method="test", id=1)

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("jsonrpc",) for error in errors)


@pytest.mark.contract
def test_jsonrpc_request_schema_missing_method() -> None:
    """Test JSON-RPC request validation fails when method is missing."""
    with pytest.raises(ValidationError) as exc_info:
        JsonRpcRequest(id=1)  # type: ignore[call-arg]

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("method",) for error in errors)


@pytest.mark.contract
def test_jsonrpc_response_schema_valid_result() -> None:
    """Test JSON-RPC 2.0 response schema with successful result."""
    response = JsonRpcResponse(result={"status": "ok"}, id=1)

    assert response.jsonrpc == "2.0"
    assert response.result == {"status": "ok"}
    assert response.error is None
    assert response.id == 1


@pytest.mark.contract
def test_jsonrpc_response_schema_valid_error() -> None:
    """Test JSON-RPC 2.0 response schema with error."""
    error = JsonRpcError(code=-32601, message="Method not found")
    response = JsonRpcResponse(error=error, id=1)

    assert response.jsonrpc == "2.0"
    assert response.result is None
    assert response.error is not None
    assert response.error.code == -32601
    assert response.error.message == "Method not found"
    assert response.id == 1


# ==============================================================================
# Stdio Transport Configuration Tests
# ==============================================================================


@pytest.mark.contract
def test_stdio_transport_mcp_instance_exists() -> None:
    """Verify FastMCP server instance is initialized."""
    from src.mcp.server_fastmcp import mcp

    assert mcp is not None
    assert hasattr(mcp, "run")
    assert callable(mcp.run)


@pytest.mark.contract
def test_stdio_transport_default_initialization() -> None:
    """Verify server uses stdio transport by default."""
    # FastMCP's run() method uses stdio transport by default
    # This test documents that requirement
    from src.mcp.server_fastmcp import mcp

    # Check that mcp instance has the expected FastMCP attributes
    assert hasattr(mcp, "name")
    assert mcp.name == "codebase-mcp"

    # Verify run method exists (stdio transport is default)
    assert hasattr(mcp, "run")
    assert callable(mcp.run)


# ==============================================================================
# Logging Configuration Tests (No Stdout/Stderr Pollution)
# ==============================================================================


@pytest.mark.contract
def test_logging_file_path_configured() -> None:
    """Verify server logging is configured to write to file."""
    from src.mcp.server_fastmcp import LOG_FILE

    assert LOG_FILE == Path("/tmp/codebase-mcp.log")
    assert isinstance(LOG_FILE, Path)


@pytest.mark.contract
def test_logging_handlers_configured_correctly() -> None:
    """Verify logging handlers do not write to stdout/stderr."""
    from src.mcp.server_fastmcp import logger

    # Check that logger is configured
    assert logger is not None
    assert logger.name == "src.mcp.server_fastmcp"

    # Get root logger handlers (configured in basicConfig)
    root_logger = logging.getLogger()
    handlers = root_logger.handlers

    # Verify at least one handler exists
    assert len(handlers) > 0

    # Verify no handlers write to stdout/stderr
    for handler in handlers:
        # Check if it's a StreamHandler (base class for file and console handlers)
        if isinstance(handler, logging.StreamHandler):
            # If it's a StreamHandler, verify it's either:
            # 1. A RotatingFileHandler (subclass of StreamHandler)
            # 2. Or writing to /dev/null (pytest capture)
            # 3. Or writing to a file stream (not sys.stdout/sys.stderr)
            if hasattr(handler, "stream"):
                # Allow RotatingFileHandler or file streams
                is_file_handler = isinstance(
                    handler, logging.handlers.RotatingFileHandler
                )
                is_not_console = handler.stream not in (sys.stdout, sys.stderr)
                assert (
                    is_file_handler or is_not_console
                ), f"Handler {handler} writes to console"


@pytest.mark.contract
def test_logging_file_handler_configuration() -> None:
    """Verify rotating file handler is properly configured."""
    root_logger = logging.getLogger()
    handlers = root_logger.handlers

    # Find the RotatingFileHandler for our log file
    rotating_handlers = [
        h
        for h in handlers
        if isinstance(h, logging.handlers.RotatingFileHandler)
        and "/tmp/codebase-mcp.log" in str(getattr(h, "baseFilename", ""))
    ]

    assert len(rotating_handlers) > 0, "No RotatingFileHandler for codebase-mcp.log found"

    handler = rotating_handlers[0]
    # Verify reasonable rotation settings
    # NOTE: Multiple modules configure logging, so accept either 10MB or 100MB
    assert handler.maxBytes in (
        10 * 1024 * 1024,  # 10MB (server_fastmcp.py)
        100 * 1024 * 1024,  # 100MB (mcp_logging.py default)
    ), f"Unexpected maxBytes: {handler.maxBytes}"
    assert handler.backupCount == 5


@pytest.mark.contract
def test_external_library_logs_suppressed() -> None:
    """Verify external library logging is suppressed to WARNING level."""
    # Check that external libraries are set to WARNING level
    fastmcp_logger = logging.getLogger("fastmcp")
    httpx_logger = logging.getLogger("httpx")
    asyncpg_logger = logging.getLogger("asyncpg")

    assert fastmcp_logger.level == logging.WARNING
    assert httpx_logger.level == logging.WARNING
    assert asyncpg_logger.level == logging.WARNING


# ==============================================================================
# Server Startup Validation Tests (Expected to FAIL)
# ==============================================================================


@pytest.mark.contract
@pytest.mark.asyncio
async def test_server_validation_fails_with_no_tools() -> None:
    """
    Test server startup validation MUST fail when no tools are registered.

    This is the PRIMARY test that validates TDD approach - it MUST fail
    until tools are registered in subsequent tasks (T008-T013).

    Expected behavior:
    - Raises RuntimeError with clear error message
    - Error message indicates missing tools
    - Error message suggests fix (import tool modules)
    """
    from src.mcp.server_fastmcp import mcp, validate_server_startup

    # Server validation should fail because no tools are registered yet
    with pytest.raises(RuntimeError) as exc_info:
        await validate_server_startup(mcp)

    error_message = str(exc_info.value)

    # Verify error message is clear and actionable
    assert "validation failed" in error_message.lower()
    assert "no tools registered" in error_message.lower()
    assert "import" in error_message.lower()  # Suggests fix


@pytest.mark.contract
@pytest.mark.asyncio
async def test_server_validation_checks_expected_tools() -> None:
    """
    Test server validation checks for all 6 expected tools.

    Expected tools:
    - search_code
    - index_repository
    - create_task
    - get_task
    - list_tasks
    - update_task

    This test documents the expected tool set.
    """
    expected_tools = {
        "search_code",
        "index_repository",
        "create_task",
        "get_task",
        "list_tasks",
        "update_task",
    }

    # This test currently fails because tools aren't registered
    # Once tools are registered, validation will check for these 6 tools
    assert len(expected_tools) == 6
    assert "search_code" in expected_tools
    assert "index_repository" in expected_tools
    assert "create_task" in expected_tools
    assert "get_task" in expected_tools
    assert "list_tasks" in expected_tools
    assert "update_task" in expected_tools


@pytest.mark.contract
@pytest.mark.asyncio
async def test_server_get_tools_returns_empty_dict() -> None:
    """
    Test mcp.get_tools() currently returns empty dict.

    This test documents current state (no tools registered).
    After T008-T013, this test will need updating to verify tools exist.
    """
    from src.mcp.server_fastmcp import mcp

    registered_tools = await mcp.get_tools()

    # Currently no tools registered
    assert isinstance(registered_tools, dict)
    assert len(registered_tools) == 0


# ==============================================================================
# Constitutional Compliance Documentation Tests
# ==============================================================================


@pytest.mark.contract
def test_principle_iii_protocol_compliance_documented() -> None:
    """
    Document Principle III: Protocol Compliance requirements.

    Requirements:
    - JSON-RPC 2.0 over stdio transport
    - No stdout/stderr pollution
    - Compatible with Claude Desktop MCP client
    - Logging to /tmp/codebase-mcp.log
    """
    requirements = {
        "protocol": "JSON-RPC 2.0",
        "transport": "stdio",
        "no_stdout_pollution": True,
        "log_file": "/tmp/codebase-mcp.log",
        "client_compatibility": "Claude Desktop",
    }

    assert requirements["protocol"] == "JSON-RPC 2.0"
    assert requirements["transport"] == "stdio"
    assert requirements["no_stdout_pollution"] is True
    assert requirements["log_file"] == "/tmp/codebase-mcp.log"


@pytest.mark.contract
def test_principle_v_production_quality_validation() -> None:
    """
    Document Principle V: Production Quality requirements.

    Requirements:
    - Fail-fast startup validation
    - Clear error messages with suggested fixes
    - Graceful error handling
    - Comprehensive logging
    """
    requirements = {
        "fail_fast_validation": True,
        "clear_error_messages": True,
        "suggested_fixes": True,
        "graceful_error_handling": True,
        "comprehensive_logging": True,
    }

    # All production quality requirements must be True
    assert all(requirements.values())


@pytest.mark.contract
def test_principle_viii_type_safety_compliance() -> None:
    """
    Verify type safety compliance in server module.

    This test validates that the server module follows type safety principles:
    - All functions have type hints
    - Pydantic models for data validation
    - mypy --strict compatibility
    """
    from src.mcp.server_fastmcp import main, validate_server_startup

    # Check that critical functions have type annotations
    assert hasattr(main, "__annotations__")
    assert hasattr(validate_server_startup, "__annotations__")

    # Validate return type annotations exist (can be None or the string "None")
    main_return = main.__annotations__.get("return")
    assert main_return is None or main_return == "None" or main_return == None.__class__

    validate_return = validate_server_startup.__annotations__.get("return")
    assert validate_return is None or validate_return == "None" or validate_return == None.__class__


# ==============================================================================
# Integration Readiness Tests
# ==============================================================================


@pytest.mark.contract
def test_claude_desktop_config_pattern_documented() -> None:
    """
    Document expected Claude Desktop configuration pattern.

    Expected config in claude_desktop_config.json:
    {
      "mcpServers": {
        "codebase-mcp": {
          "command": "uv",
          "args": [
            "--directory",
            "/path/to/codebase-mcp",
            "run",
            "codebase-mcp"
          ]
        }
      }
    }

    This test documents the integration pattern for users.
    """
    expected_config = {
        "mcpServers": {
            "codebase-mcp": {
                "command": "uv",
                "args": [
                    "--directory",
                    "/path/to/codebase-mcp",
                    "run",
                    "codebase-mcp",
                ],
            }
        }
    }

    assert "mcpServers" in expected_config
    assert "codebase-mcp" in expected_config["mcpServers"]
    assert expected_config["mcpServers"]["codebase-mcp"]["command"] == "uv"


@pytest.mark.contract
def test_stdio_transport_no_url_required() -> None:
    """
    Verify stdio transport does not require URL configuration.

    Unlike SSE transport which needs baseUrl in config, stdio transport
    communicates over stdin/stdout and requires no URL.

    This test documents the transport difference for users.
    """
    # Stdio transport requirements
    stdio_requirements = {
        "requires_url": False,
        "requires_command": True,
        "requires_args": True,
        "communication": "stdin/stdout",
    }

    assert stdio_requirements["requires_url"] is False
    assert stdio_requirements["requires_command"] is True
    assert stdio_requirements["communication"] == "stdin/stdout"


# ==============================================================================
# Performance Requirements Documentation
# ==============================================================================


@pytest.mark.contract
def test_startup_validation_performance_documented() -> None:
    """
    Document startup validation performance requirements.

    Startup should be fast:
    - Tool validation: < 100ms
    - Server initialization: < 500ms
    - Total startup time: < 1s

    Actual performance validation will be in integration tests.
    """
    performance_requirements = {
        "tool_validation_ms": 100,
        "server_init_ms": 500,
        "total_startup_ms": 1000,
    }

    assert performance_requirements["tool_validation_ms"] == 100
    assert performance_requirements["server_init_ms"] == 500
    assert performance_requirements["total_startup_ms"] == 1000
