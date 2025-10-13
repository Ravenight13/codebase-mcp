"""WorkflowIntegrationContext model for workflow-mcp integration.

This module provides the WorkflowIntegrationContext Pydantic model for handling
optional workflow-mcp server integration with TTL-based caching for automatic
project context detection.

Entity Responsibilities:
- Store active project ID from workflow-mcp server
- Track integration status for error handling
- Implement TTL-based caching with expiration checking
- Support optional/graceful workflow-mcp integration

Constitutional Compliance:
- Principle VIII: Pydantic-based type safety (mypy --strict compatible)
- Principle V: Production quality (comprehensive docstrings, error handling)
- Principle XI: FastMCP foundation (integration model for MCP ecosystem)

Functional Requirements:
- FR-012: Detect workflow-mcp active project with caching
- FR-013: Handle workflow-mcp unavailability gracefully
- FR-014: TTL-based cache invalidation (60s default)
- FR-015: Status tracking for integration failures
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class WorkflowIntegrationContext(BaseModel):
    """Context from workflow-mcp server with caching metadata.

    This model stores the active project ID retrieved from an optional
    workflow-mcp MCP server integration, along with caching metadata
    to avoid excessive inter-MCP communication.

    Attributes:
        active_project_id: UUID of active project from workflow-mcp server.
            None indicates workflow-mcp is unavailable, timed out, or no
            project is active.
        status: Integration status for error handling:
            - "success": Project ID retrieved successfully
            - "timeout": workflow-mcp request exceeded timeout threshold
            - "unavailable": workflow-mcp server not running/reachable
            - "invalid_response": workflow-mcp returned malformed data
        retrieved_at: UTC timestamp when context was cached.
            Used for TTL expiration calculation.
        cache_ttl_seconds: Time-to-live in seconds for cached context.
            Default: 60 seconds (1 minute). After TTL expiration,
            codebase-mcp will re-query workflow-mcp for fresh context.

    Example:
        >>> context = WorkflowIntegrationContext(
        ...     active_project_id="550e8400-e29b-41d4-a716-446655440000",
        ...     status="success",
        ... )
        >>> context.is_expired()
        False

        >>> unavailable_context = WorkflowIntegrationContext(
        ...     active_project_id=None,
        ...     status="unavailable",
        ... )
        >>> unavailable_context.is_expired()
        False

    Constitutional Compliance:
        - Principle VIII: Full type safety with Pydantic validation
        - Principle V: Production quality with clear documentation
        - Principle XI: FastMCP ecosystem integration pattern
    """

    active_project_id: str | None = Field(
        None,
        description="Active project UUID from workflow-mcp (None if unavailable)",
    )

    status: Literal["success", "timeout", "unavailable", "invalid_response"] = Field(
        ...,
        description="Integration status for error handling and diagnostics",
    )

    retrieved_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when context was cached for TTL calculation",
    )

    cache_ttl_seconds: int = Field(
        default=60,
        description="Time-to-live in seconds for cached context (default: 60s)",
    )

    def is_expired(self) -> bool:
        """Check if cached context has exceeded TTL.

        Calculates the age of the cached context by comparing current UTC
        time with the retrieved_at timestamp. Returns True if the cache
        age exceeds cache_ttl_seconds.

        Returns:
            bool: True if cache is expired and should be refreshed,
                False if cache is still valid.

        Example:
            >>> context = WorkflowIntegrationContext(
            ...     active_project_id="550e8400-e29b-41d4-a716-446655440000",
            ...     status="success",
            ...     cache_ttl_seconds=60,
            ... )
            >>> context.is_expired()  # Immediately after creation
            False

            >>> # After 61 seconds...
            >>> context.is_expired()
            True

        Note:
            Uses datetime.utcnow() for current time calculation to match
            retrieved_at timestamp (also uses utcnow). Both timestamps
            must use the same clock for accurate TTL calculation.
        """
        age_seconds = (datetime.utcnow() - self.retrieved_at).total_seconds()
        return age_seconds > self.cache_ttl_seconds

    model_config = {"frozen": False}  # Allow mutable cache metadata updates
