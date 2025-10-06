"""MCP Server initialization with SSE transport and tool registration.

This module provides the core MCP server setup using the official MCP SDK
for Python with Server-Sent Events (SSE) transport.

Constitutional Compliance:
- Principle III: Protocol Compliance (MCP via SSE, no stdout/stderr pollution)
- Principle V: Production Quality (error handling, validation, logging)
- Principle VIII: Type Safety (mypy --strict compliance)

Key Features:
- MCP SDK-based server with SSE transport
- Tool registration framework with automatic schema generation
- MCP-compliant error responses
- Structured logging (file-only, no stdout/stderr)
- Type-safe tool handlers
"""

from __future__ import annotations

from typing import Any, Callable, TypeVar

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool

from src.mcp.mcp_logging import get_logger

# ==============================================================================
# Constants
# ==============================================================================

logger = get_logger(__name__)

# Type variable for tool handler functions
F = TypeVar("F", bound=Callable[..., Any])

# ==============================================================================
# Server Creation
# ==============================================================================


def create_mcp_server() -> Server:
    """Create and configure MCP server instance.

    Returns:
        Configured MCP Server with SSE transport ready for tool registration

    Example:
        >>> server = create_mcp_server()
        >>> @server.tool()
        ... async def search_code(query: str) -> dict:
        ...     # Tool implementation
        ...     pass
        >>> # Server is now ready to handle tool calls

    Note:
        Tools must be registered using the @server.tool() decorator after
        calling this function. The server will not be started until
        get_sse_transport() is called and the transport is connected.
    """
    logger.info("Creating MCP server instance")

    # Create server with name and version
    server = Server("codebase-mcp")

    logger.info(
        "MCP server created successfully",
        extra={
            "context": {
                "server_name": "codebase-mcp",
                "protocol": "MCP via SSE",
            }
        },
    )

    return server


def get_sse_transport() -> SseServerTransport:
    """Get SSE transport for streaming responses.

    Returns:
        Configured SSE server transport for MCP communication

    Example:
        >>> server = create_mcp_server()
        >>> transport = get_sse_transport()
        >>> # Connect transport to FastAPI endpoint for SSE streaming

    Note:
        The transport should be connected to a FastAPI endpoint that handles
        the SSE streaming protocol. The endpoint should accept POST requests
        with JSON payloads and return Server-Sent Events.
    """
    logger.info("Creating SSE transport for MCP server")

    # Create SSE transport
    transport = SseServerTransport("/messages")

    logger.info(
        "SSE transport created successfully",
        extra={
            "context": {
                "endpoint": "/messages",
                "protocol": "Server-Sent Events (SSE)",
            }
        },
    )

    return transport


# ==============================================================================
# Error Handling
# ==============================================================================


class MCPError(Exception):
    """Base exception for MCP-related errors.

    Attributes:
        message: Human-readable error message
        code: MCP error code (optional)
        details: Additional error context (optional)
    """

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initialize MCP error.

        Args:
            message: Human-readable error message
            code: MCP error code (optional)
            details: Additional error context (optional)
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert error to MCP-compliant error response.

        Returns:
            Dictionary with error information suitable for MCP response
        """
        error_dict: dict[str, Any] = {"message": self.message}
        if self.code:
            error_dict["code"] = self.code
        if self.details:
            error_dict["details"] = self.details
        return error_dict


class ValidationError(MCPError):
    """Error raised when input validation fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """Initialize validation error.

        Args:
            message: Human-readable error message
            details: Additional validation error context
        """
        super().__init__(message, code="VALIDATION_ERROR", details=details)


class NotFoundError(MCPError):
    """Error raised when a requested resource is not found."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """Initialize not found error.

        Args:
            message: Human-readable error message
            details: Additional context about the missing resource
        """
        super().__init__(message, code="NOT_FOUND", details=details)


class OperationError(MCPError):
    """Error raised when an operation fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """Initialize operation error.

        Args:
            message: Human-readable error message
            details: Additional context about the failure
        """
        super().__init__(message, code="OPERATION_ERROR", details=details)


# ==============================================================================
# Module Exports
# ==============================================================================

__all__ = [
    "Server",
    "SseServerTransport",
    "Tool",
    "create_mcp_server",
    "get_sse_transport",
    "MCPError",
    "ValidationError",
    "NotFoundError",
    "OperationError",
]
