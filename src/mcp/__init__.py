"""MCP (Model Context Protocol) server implementation.

This package provides MCP server implementation with multiple transports:
- SSE (Server-Sent Events) transport for web-based clients
- stdio (JSON-RPC over stdin/stdout) transport for CLI clients

Constitutional Compliance:
- Principle III: Protocol Compliance (MCP via SSE and stdio)
- Principle V: Production Quality (comprehensive error handling)
- Principle VIII: Type Safety (mypy --strict compliance)
"""

from .logging import get_logger, get_structured_logger
from .server import (
    MCPError,
    NotFoundError,
    OperationError,
    ValidationError,
    create_mcp_server,
    get_sse_transport,
)
from .stdio_server import main as stdio_main

__all__ = [
    # Logging
    "get_logger",
    "get_structured_logger",
    # SSE Server
    "create_mcp_server",
    "get_sse_transport",
    # stdio Server
    "stdio_main",
    # Errors
    "MCPError",
    "ValidationError",
    "NotFoundError",
    "OperationError",
]
