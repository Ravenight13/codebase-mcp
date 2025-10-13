"""WorkflowIntegrationClient for workflow-mcp HTTP integration.

This module provides an HTTP client for optional workflow-mcp server integration
with timeout handling, connection error recovery, and TTL-based caching.

Service Responsibilities:
- Query workflow-mcp /api/v1/projects/active endpoint with timeout
- Cache active project ID to minimize inter-MCP communication
- Handle timeout, connection, and invalid response errors gracefully
- Return None on errors to enable default workspace fallback

Constitutional Compliance:
- Principle II: Local-first architecture (graceful degradation when unavailable)
- Principle V: Production quality (comprehensive error handling)
- Principle VIII: Pydantic-based type safety (mypy --strict compatible)
- Principle X: Git micro-commit strategy

Functional Requirements:
- FR-012: Detect workflow-mcp active project with caching
- FR-013: Handle workflow-mcp unavailability gracefully
- FR-014: TTL-based cache invalidation (60s default)
- FR-015: Status tracking for integration failures
"""

from __future__ import annotations

import logging
from typing import Dict

import httpx

from src.models.workflow_context import WorkflowIntegrationContext

logger = logging.getLogger(__name__)


class WorkflowIntegrationClient:
    """Optional HTTP client for workflow-mcp integration.

    This client queries an external workflow-mcp MCP server to detect the
    active project context. It implements timeout protection, connection
    error handling, and TTL-based caching to minimize network overhead.

    All errors are handled gracefully by returning None, allowing codebase-mcp
    to fall back to the default workspace when workflow-mcp is unavailable.

    Attributes:
        base_url: Base URL of workflow-mcp server (default: http://localhost:8000)
        timeout: HTTP timeout in seconds (default: 1.0s)
        cache_ttl: Cache time-to-live in seconds (default: 60s)
        client: httpx.AsyncClient for HTTP requests
        _cache: In-memory cache for WorkflowIntegrationContext

    Example:
        >>> client = WorkflowIntegrationClient(
        ...     base_url="http://localhost:8000",
        ...     timeout=1.0,
        ...     cache_ttl=60
        ... )
        >>> project_id = await client.get_active_project()
        >>> if project_id:
        ...     print(f"Active project: {project_id}")
        ... else:
        ...     print("Using default workspace")
        >>> await client.close()

    Constitutional Compliance:
        - Principle II: Graceful degradation when workflow-mcp unavailable
        - Principle V: Comprehensive error handling with detailed logging
        - Principle VIII: Full type safety with mypy --strict compliance
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        timeout: float = 1.0,
        cache_ttl: int = 60,
    ) -> None:
        """Initialize WorkflowIntegrationClient with HTTP settings.

        Args:
            base_url: Base URL of workflow-mcp server (default: http://localhost:8000)
            timeout: HTTP timeout in seconds (default: 1.0s)
            cache_ttl: Cache time-to-live in seconds (default: 60s)
        """
        self.base_url = base_url
        self.timeout = httpx.Timeout(timeout)
        self.cache_ttl = cache_ttl
        self.client = httpx.AsyncClient(timeout=self.timeout)
        self._cache: Dict[str, WorkflowIntegrationContext] = {}

    async def get_active_project(self) -> str | None:
        """Query workflow-mcp for active project with caching.

        Queries the workflow-mcp /api/v1/projects/active endpoint to detect
        the active project context. Implements TTL-based caching to minimize
        network overhead and inter-MCP communication.

        Returns:
            Active project UUID string if workflow-mcp is available and a
            project is active, None otherwise (timeout, unavailable, or no
            active project).

        Error Handling:
            - Timeout: Returns None, logs warning at WARNING level
            - Connection refused: Returns None, logs info at INFO level
            - Invalid response: Returns None, logs error at ERROR level

        Example:
            >>> client = WorkflowIntegrationClient()
            >>> project_id = await client.get_active_project()
            >>> if project_id:
            ...     print(f"Using workflow-mcp project: {project_id}")
            ... else:
            ...     print("Falling back to default workspace")

        Constitutional Compliance:
            - Principle II: Local-first (graceful degradation)
            - Principle V: Production quality (comprehensive error handling)
        """
        # Check cache for unexpired context
        cached = self._cache.get("active_project")
        if cached and not cached.is_expired():
            logger.debug(f"Using cached workflow context: {cached.status}")
            return cached.active_project_id

        # Query workflow-mcp for fresh context
        try:
            response = await self.client.get(f"{self.base_url}/api/v1/projects/active")
            response.raise_for_status()

            data = response.json()
            context = WorkflowIntegrationContext(
                active_project_id=data.get("project_id"),
                status="success",
                cache_ttl_seconds=self.cache_ttl,
            )
            logger.info(f"Workflow-mcp active project: {context.active_project_id}")

        except httpx.TimeoutException as e:
            context = self._handle_timeout(e)

        except httpx.ConnectError as e:
            context = self._handle_connection_error(e)

        except Exception as e:
            context = self._handle_invalid_response(e)

        # Update cache with fresh context
        self._cache["active_project"] = context
        return context.active_project_id

    def _handle_timeout(self, error: httpx.TimeoutException) -> WorkflowIntegrationContext:
        """Handle workflow-mcp timeout error.

        Logs a warning message indicating the timeout threshold was exceeded
        and returns a context with status="timeout" for fallback handling.

        Args:
            error: httpx.TimeoutException raised by HTTP client

        Returns:
            WorkflowIntegrationContext with status="timeout" and None project ID

        Constitutional Compliance:
            - Principle II: Graceful degradation (returns usable context)
            - Principle V: Production quality (detailed logging)
        """
        logger.warning(
            f"workflow-mcp timeout ({self.timeout.connect}s), using default workspace"
        )
        return WorkflowIntegrationContext(
            active_project_id=None,
            status="timeout",
            cache_ttl_seconds=self.cache_ttl,
        )

    def _handle_connection_error(self, error: httpx.ConnectError) -> WorkflowIntegrationContext:
        """Handle workflow-mcp connection error.

        Logs an info message indicating workflow-mcp is unavailable (not running
        or unreachable) and returns a context with status="unavailable" for
        fallback handling.

        Args:
            error: httpx.ConnectError raised by HTTP client

        Returns:
            WorkflowIntegrationContext with status="unavailable" and None project ID

        Constitutional Compliance:
            - Principle II: Graceful degradation (returns usable context)
            - Principle V: Production quality (appropriate log levels)
        """
        logger.info("workflow-mcp unavailable, using default workspace")
        return WorkflowIntegrationContext(
            active_project_id=None,
            status="unavailable",
            cache_ttl_seconds=self.cache_ttl,
        )

    def _handle_invalid_response(self, error: Exception) -> WorkflowIntegrationContext:
        """Handle workflow-mcp invalid response error.

        Logs an error message indicating workflow-mcp returned malformed data
        or an unexpected error occurred, and returns a context with
        status="invalid_response" for fallback handling.

        Args:
            error: Exception raised during response processing

        Returns:
            WorkflowIntegrationContext with status="invalid_response" and None project ID

        Constitutional Compliance:
            - Principle II: Graceful degradation (returns usable context)
            - Principle V: Production quality (error details logged)
        """
        logger.error(f"workflow-mcp error: {error}, using default workspace")
        return WorkflowIntegrationContext(
            active_project_id=None,
            status="invalid_response",
            cache_ttl_seconds=self.cache_ttl,
        )

    async def close(self) -> None:
        """Close HTTP client connection.

        Releases the underlying HTTP connection pool resources. Should be
        called when the client is no longer needed to prevent resource leaks.

        Example:
            >>> client = WorkflowIntegrationClient()
            >>> try:
            ...     project_id = await client.get_active_project()
            ... finally:
            ...     await client.close()

        Constitutional Compliance:
            - Principle V: Production quality (proper resource cleanup)
        """
        await self.client.aclose()
