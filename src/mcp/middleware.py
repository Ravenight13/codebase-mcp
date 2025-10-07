"""Error handling and logging middleware for FastAPI MCP Server.

This module provides production-grade middleware for the Codebase MCP Server:
- Request/response logging with correlation IDs
- Performance timing for all requests
- Error handling with MCP-compliant responses
- No stdout/stderr pollution (file logging only)

Constitutional Compliance:
- Principle III: Protocol Compliance (no stdout/stderr, MCP error format)
- Principle IV: Performance (request timing, performance monitoring)
- Principle V: Production quality (comprehensive error handling, correlation IDs)
- Principle VIII: Type safety (mypy --strict compliance)

Usage:
    >>> from fastapi import FastAPI
    >>> from src.mcp.middleware import LoggingMiddleware, ErrorHandlingMiddleware
    >>>
    >>> app = FastAPI()
    >>> app.add_middleware(ErrorHandlingMiddleware)
    >>> app.add_middleware(LoggingMiddleware)
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from starlette.middleware.base import BaseHTTPMiddleware

from src.mcp.errors import MCPError, NotFoundError, OperationError, ValidationError
from src.mcp.mcp_logging import get_logger

# ==============================================================================
# Module Constants
# ==============================================================================

logger = get_logger(__name__)

# Correlation ID header name
CORRELATION_ID_HEADER = "X-Correlation-ID"

# Performance warning threshold (milliseconds)
SLOW_REQUEST_THRESHOLD_MS = 1000.0


# ==============================================================================
# Logging Middleware
# ==============================================================================


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging with correlation IDs.

    Features:
    - Generates unique correlation ID for each request
    - Logs request start with method, path, and correlation ID
    - Logs response completion with status code and duration
    - Tracks performance metrics for slow request detection
    - Adds correlation ID to response headers for tracing

    Constitutional Compliance:
    - Principle III: All logging to file (no stdout/stderr pollution)
    - Principle V: Production quality (correlation IDs, performance tracking)

    Example:
        >>> app = FastAPI()
        >>> app.add_middleware(LoggingMiddleware)
        >>> # All requests now have correlation IDs and are logged

    Note:
        This middleware should be added BEFORE ErrorHandlingMiddleware to
        ensure errors are also logged with correlation IDs.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request with logging and correlation ID tracking.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response with correlation ID header

        Side Effects:
            - Logs request start
            - Logs response completion
            - Adds correlation ID to request state
            - Adds correlation ID to response headers
        """
        # Generate unique correlation ID for this request
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        # Log request start
        start_time = time.perf_counter()

        logger.info(
            "Request started",
            extra={
                "context": {
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": str(request.url.path),
                    "query_params": dict(request.query_params),
                    "client_host": request.client.host if request.client else None,
                }
            },
        )

        try:
            # Process request through middleware chain
            response = await call_next(request)

            # Calculate request duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log response completion
            logger.info(
                "Request completed",
                extra={
                    "context": {
                        "correlation_id": correlation_id,
                        "method": request.method,
                        "path": str(request.url.path),
                        "status_code": response.status_code,
                        "duration_ms": round(duration_ms, 2),
                    }
                },
            )

            # Warn on slow requests
            if duration_ms > SLOW_REQUEST_THRESHOLD_MS:
                logger.warning(
                    "Slow request detected",
                    extra={
                        "context": {
                            "correlation_id": correlation_id,
                            "method": request.method,
                            "path": str(request.url.path),
                            "duration_ms": round(duration_ms, 2),
                            "threshold_ms": SLOW_REQUEST_THRESHOLD_MS,
                        }
                    },
                )

            # Add correlation ID to response headers
            response.headers[CORRELATION_ID_HEADER] = correlation_id

            return response

        except Exception as e:
            # Calculate duration even on error
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log error with context
            logger.error(
                "Request failed with exception",
                extra={
                    "context": {
                        "correlation_id": correlation_id,
                        "method": request.method,
                        "path": str(request.url.path),
                        "duration_ms": round(duration_ms, 2),
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                },
                exc_info=True,
            )

            # Re-raise to be handled by ErrorHandlingMiddleware
            raise


# ==============================================================================
# Error Handling Middleware
# ==============================================================================


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for error handling and MCP-compliant error responses.

    Features:
    - Catches all unhandled exceptions
    - Formats errors as MCP-compliant JSON responses
    - Logs errors with full context and stack traces
    - Returns appropriate HTTP status codes
    - Preserves correlation IDs from LoggingMiddleware

    Error Types Handled:
    - ValidationError (400): Input validation failures
    - NotFoundError (404): Resource not found
    - OperationError (500): Operation failures
    - PydanticValidationError (422): Schema validation failures
    - Exception (500): Unexpected errors

    Constitutional Compliance:
    - Principle III: MCP-compliant error format
    - Principle V: Comprehensive error handling
    - Principle VIII: Type safety with proper error types

    Example:
        >>> app = FastAPI()
        >>> app.add_middleware(ErrorHandlingMiddleware)
        >>> # All exceptions are now caught and formatted as MCP errors

    Note:
        This middleware should be added AFTER LoggingMiddleware to ensure
        errors include correlation IDs in logs.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process request with error handling.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            HTTP response (success or error)

        Side Effects:
            - Logs all errors with full context
            - Formats errors as JSON responses
        """
        try:
            # Process request through middleware chain
            response = await call_next(request)
            return response

        except ValidationError as e:
            # MCP validation error (400)
            return await self._handle_validation_error(request, e)

        except NotFoundError as e:
            # MCP not found error (404)
            return await self._handle_not_found_error(request, e)

        except OperationError as e:
            # MCP operation error (500)
            return await self._handle_operation_error(request, e)

        except PydanticValidationError as e:
            # Pydantic validation error (422)
            return await self._handle_pydantic_validation_error(request, e)

        except Exception as e:
            # Unexpected error (500)
            return await self._handle_unexpected_error(request, e)

    async def _handle_validation_error(
        self, request: Request, error: ValidationError
    ) -> JSONResponse:
        """Handle MCP validation errors.

        Args:
            request: HTTP request
            error: ValidationError instance

        Returns:
            JSON response with 400 status code
        """
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        logger.warning(
            "Validation error",
            extra={
                "context": {
                    "correlation_id": correlation_id,
                    "error_type": "ValidationError",
                    "error": error.message,
                    "details": error.details,
                }
            },
        )

        return JSONResponse(
            status_code=400,
            content={
                "error": "ValidationError",
                "message": error.message,
                "details": error.details or {},
                "correlation_id": correlation_id,
            },
            headers={CORRELATION_ID_HEADER: correlation_id},
        )

    async def _handle_not_found_error(
        self, request: Request, error: NotFoundError
    ) -> JSONResponse:
        """Handle MCP not found errors.

        Args:
            request: HTTP request
            error: NotFoundError instance

        Returns:
            JSON response with 404 status code
        """
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        logger.warning(
            "Resource not found",
            extra={
                "context": {
                    "correlation_id": correlation_id,
                    "error_type": "NotFoundError",
                    "error": error.message,
                    "details": error.details,
                }
            },
        )

        return JSONResponse(
            status_code=404,
            content={
                "error": "NotFoundError",
                "message": error.message,
                "details": error.details or {},
                "correlation_id": correlation_id,
            },
            headers={CORRELATION_ID_HEADER: correlation_id},
        )

    async def _handle_operation_error(
        self, request: Request, error: OperationError
    ) -> JSONResponse:
        """Handle MCP operation errors.

        Args:
            request: HTTP request
            error: OperationError instance

        Returns:
            JSON response with 500 status code
        """
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        logger.error(
            "Operation error",
            extra={
                "context": {
                    "correlation_id": correlation_id,
                    "error_type": "OperationError",
                    "error": error.message,
                    "details": error.details,
                }
            },
            exc_info=True,
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": "OperationError",
                "message": error.message,
                "details": error.details or {},
                "correlation_id": correlation_id,
            },
            headers={CORRELATION_ID_HEADER: correlation_id},
        )

    async def _handle_pydantic_validation_error(
        self, request: Request, error: PydanticValidationError
    ) -> JSONResponse:
        """Handle Pydantic validation errors.

        Args:
            request: HTTP request
            error: PydanticValidationError instance

        Returns:
            JSON response with 422 status code
        """
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        logger.warning(
            "Schema validation error",
            extra={
                "context": {
                    "correlation_id": correlation_id,
                    "error_type": "PydanticValidationError",
                    "errors": error.errors(),
                }
            },
        )

        return JSONResponse(
            status_code=422,
            content={
                "error": "ValidationError",
                "message": "Input validation failed",
                "details": {"validation_errors": error.errors()},
                "correlation_id": correlation_id,
            },
            headers={CORRELATION_ID_HEADER: correlation_id},
        )

    async def _handle_unexpected_error(
        self, request: Request, error: Exception
    ) -> JSONResponse:
        """Handle unexpected errors.

        Args:
            request: HTTP request
            error: Exception instance

        Returns:
            JSON response with 500 status code
        """
        correlation_id = getattr(request.state, "correlation_id", "unknown")

        logger.error(
            "Unexpected error",
            extra={
                "context": {
                    "correlation_id": correlation_id,
                    "error_type": type(error).__name__,
                    "error": str(error),
                }
            },
            exc_info=True,
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred",
                "details": {
                    "error_type": type(error).__name__,
                },
                "correlation_id": correlation_id,
            },
            headers={CORRELATION_ID_HEADER: correlation_id},
        )


# ==============================================================================
# Public API
# ==============================================================================

__all__ = [
    "LoggingMiddleware",
    "ErrorHandlingMiddleware",
    "CORRELATION_ID_HEADER",
]
