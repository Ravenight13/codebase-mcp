"""MCP-compliant error classes for the Codebase MCP Server.

This module defines the error hierarchy for MCP protocol operations:
- MCPError: Base exception for all MCP-related errors
- ValidationError: Input validation failures (400)
- NotFoundError: Resource not found (404)
- OperationError: Operation execution failures (500)

Constitutional Compliance:
- Principle III: Protocol Compliance (MCP error format)
- Principle V: Production Quality (comprehensive error handling)
- Principle VIII: Type Safety (mypy --strict compliance)

Usage:
    >>> from src.mcp.errors import ValidationError, NotFoundError
    >>>
    >>> # Raise validation error
    >>> raise ValidationError(
    ...     "Invalid query parameter",
    ...     details={"parameter": "query", "value": ""}
    ... )
    >>>
    >>> # Raise not found error
    >>> raise NotFoundError(
    ...     "Repository not found",
    ...     details={"repository_id": "abc-123"}
    ... )
"""

from __future__ import annotations

from typing import Any

# ==============================================================================
# MCP Error Classes
# ==============================================================================


class MCPError(Exception):
    """Base exception for MCP-related errors.

    All MCP errors extend this base class and provide MCP-compliant
    error responses via the to_dict() method.

    Attributes:
        message: Human-readable error message
        code: MCP error code (e.g., "VALIDATION_ERROR", "NOT_FOUND")
        details: Additional error context as dictionary

    Example:
        >>> error = MCPError("Something went wrong", code="GENERIC_ERROR")
        >>> error.to_dict()
        {'message': 'Something went wrong', 'code': 'GENERIC_ERROR', 'details': {}}
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

        Example:
            >>> error = ValidationError("Invalid input", details={"field": "query"})
            >>> error.to_dict()
            {
                'message': 'Invalid input',
                'code': 'VALIDATION_ERROR',
                'details': {'field': 'query'}
            }
        """
        error_dict: dict[str, Any] = {"message": self.message}
        if self.code:
            error_dict["code"] = self.code
        if self.details:
            error_dict["details"] = self.details
        return error_dict


class ValidationError(MCPError):
    """Error raised when input validation fails.

    Used for:
    - Missing required parameters
    - Invalid parameter types
    - Out-of-range values
    - Schema validation failures

    HTTP Status: 400 Bad Request

    Example:
        >>> raise ValidationError(
        ...     "Query parameter is required",
        ...     details={"parameter": "query"}
        ... )
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """Initialize validation error.

        Args:
            message: Human-readable error message
            details: Additional validation error context
        """
        super().__init__(message, code="VALIDATION_ERROR", details=details)


class NotFoundError(MCPError):
    """Error raised when a requested resource is not found.

    Used for:
    - Repository not found
    - Task not found
    - File not found
    - Chunk not found

    HTTP Status: 404 Not Found

    Example:
        >>> raise NotFoundError(
        ...     "Repository not found",
        ...     details={"repository_id": "abc-123"}
        ... )
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """Initialize not found error.

        Args:
            message: Human-readable error message
            details: Additional context about the missing resource
        """
        super().__init__(message, code="NOT_FOUND", details=details)


class OperationError(MCPError):
    """Error raised when an operation fails.

    Used for:
    - Database operation failures
    - File system errors
    - External service failures (Ollama)
    - Indexing failures
    - Search failures

    HTTP Status: 500 Internal Server Error

    Example:
        >>> raise OperationError(
        ...     "Failed to generate embeddings",
        ...     details={"model": "nomic-embed-text", "error": "Connection timeout"}
        ... )
    """

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
    "MCPError",
    "ValidationError",
    "NotFoundError",
    "OperationError",
]
