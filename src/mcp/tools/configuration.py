"""MCP tool handlers for singleton project configuration management.

Provides get_project_configuration and update_project_configuration tools for
MCP clients to query and update the singleton project configuration.

Constitutional Compliance:
- Principle III: Protocol Compliance (MCP-compliant responses)
- Principle IV: Performance (<50ms p95 latency target)
- Principle V: Production Quality (comprehensive validation, error handling)
- Principle VIII: Type Safety (mypy --strict compliance)
- Principle XI: FastMCP Foundation (FastMCP decorator-based tools)
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastmcp import Context
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, NoResultFound

from src.database.session import check_database_health, get_session
from src.mcp.mcp_logging import get_logger
from src.mcp.server_fastmcp import mcp
from src.models.tracking import ProjectConfiguration

# ==============================================================================
# Constants
# ==============================================================================

logger = get_logger(__name__)

# Singleton configuration ID (always 1)
SINGLETON_CONFIG_ID = 1

# ==============================================================================
# Tool Implementations
# ==============================================================================


@mcp.tool()
async def get_project_configuration(
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Get singleton project configuration.

    Retrieves the singleton project configuration including active context type,
    token budgets, current session reference, git state, and health check status.
    Always returns single row (id=1).

    Performance target: <50ms p95 latency

    Args:
        ctx: FastMCP context for client logging (injected automatically)

    Returns:
        Dictionary with project configuration matching MCP contract:
        {
            "id": 1,
            "active_context_type": "feature",
            "current_session_id": "uuid" | null,
            "git_branch": "003-database-backed-project" | null,
            "git_head_commit": "a1b2c3d4..." | null,
            "default_token_budget": 200000,
            "database_healthy": true,
            "last_health_check_at": "2025-10-10T14:00:00Z" | null,
            "updated_at": "2025-10-10T14:30:00Z",
            "updated_by": "claude-code"
        }

    Raises:
        ValueError: If configuration not initialized (should never happen)
        Exception: If database query fails

    Constitutional Compliance:
        - Principle IV: Performance (<50ms p95 latency)
        - Principle V: Production Quality (proper error handling)
    """
    start_time = time.perf_counter()

    # Dual logging: Context logging for MCP client + file logging for server
    if ctx:
        await ctx.info("Retrieving singleton project configuration")

    logger.info(
        "get_project_configuration called",
        extra={"context": {"operation": "get_project_configuration"}},
    )

    # Query singleton configuration
    try:
        async with get_session() as session:
            # Query WHERE id = 1 (singleton pattern)
            result = await session.execute(
                select(ProjectConfiguration).where(
                    ProjectConfiguration.id == SINGLETON_CONFIG_ID
                )
            )
            config = result.scalar_one_or_none()

            if config is None:
                # Configuration should always exist (created by migration)
                logger.error(
                    "Singleton project configuration not found (database not initialized)",
                    extra={
                        "context": {
                            "operation": "get_project_configuration",
                            "singleton_id": SINGLETON_CONFIG_ID,
                        }
                    },
                )
                if ctx:
                    await ctx.error("Project configuration not initialized")
                raise ValueError(
                    f"Singleton project configuration not found (id={SINGLETON_CONFIG_ID}). "
                    "Run database migrations to initialize."
                )

    except ValueError:
        # Re-raise validation errors (FastMCP handles them automatically)
        raise
    except Exception as e:
        logger.error(
            "Failed to retrieve project configuration",
            extra={
                "context": {
                    "operation": "get_project_configuration",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            },
            exc_info=True,
        )
        if ctx:
            await ctx.error(f"Database query failed: {str(e)[:100]}")
        raise  # Let FastMCP handle the error response

    # Calculate latency
    latency_ms = int((time.perf_counter() - start_time) * 1000)

    # Format response according to MCP contract
    response: dict[str, Any] = {
        "id": config.id,
        "active_context_type": config.active_context_type,
        "current_session_id": (
            str(config.current_session_id) if config.current_session_id else None
        ),
        "git_branch": config.git_branch,
        "git_head_commit": config.git_head_commit,
        "default_token_budget": config.default_token_budget,
        "database_healthy": config.database_healthy,
        "last_health_check_at": (
            config.last_health_check_at.isoformat()
            if config.last_health_check_at
            else None
        ),
        "updated_at": config.updated_at.isoformat(),
        "updated_by": config.updated_by,
    }

    logger.info(
        "get_project_configuration completed successfully",
        extra={
            "context": {
                "operation": "get_project_configuration",
                "latency_ms": latency_ms,
                "active_context_type": config.active_context_type,
                "git_branch": config.git_branch,
            }
        },
    )

    # Performance warning if exceeds target
    if latency_ms > 50:
        logger.warning(
            "get_project_configuration latency exceeded p95 target",
            extra={
                "context": {
                    "latency_ms": latency_ms,
                    "target_ms": 50,
                }
            },
        )

    if ctx:
        await ctx.info(
            f"Retrieved configuration (context: {config.active_context_type}, "
            f"branch: {config.git_branch or 'none'}) in {latency_ms}ms"
        )

    return response


@mcp.tool()
async def update_project_configuration(
    active_context_type: str | None = None,
    current_session_id: str | None = None,
    git_branch: str | None = None,
    git_head_commit: str | None = None,
    default_token_budget: int | None = None,
    updated_by: str = "claude-code",
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Update singleton project configuration.

    Updates the singleton project configuration with provided values. Uses
    upsert pattern (INSERT ... ON CONFLICT DO UPDATE) to handle initialization.
    Performs database health check and updates health status automatically.

    Performance target: <100ms p95 latency

    Args:
        active_context_type: New context type ("feature"|"maintenance"|"research")
        current_session_id: UUID string of current session work item
        git_branch: Current git branch name
        git_head_commit: Current git HEAD commit hash (40-char hex)
        default_token_budget: Default token budget for new sessions (1000-1000000)
        updated_by: AI client identifier (default: "claude-code")
        ctx: FastMCP context for client logging (injected automatically)

    Returns:
        Dictionary with updated project configuration (same format as get_project_configuration)

    Raises:
        ValueError: If validation fails (invalid context type, UUID format, commit hash, etc.)
        Exception: If database update fails

    Constitutional Compliance:
        - Principle IV: Performance (<100ms p95 latency)
        - Principle V: Production Quality (comprehensive validation, health check)
    """
    start_time = time.perf_counter()

    # Dual logging: Context logging for MCP client + file logging for server
    if ctx:
        await ctx.info("Updating singleton project configuration")

    logger.info(
        "update_project_configuration called",
        extra={
            "context": {
                "operation": "update_project_configuration",
                "active_context_type": active_context_type,
                "git_branch": git_branch,
                "updated_by": updated_by,
            }
        },
    )

    # Validate input parameters
    try:
        # Validate active_context_type
        if active_context_type is not None:
            valid_context_types = ["feature", "maintenance", "research"]
            if active_context_type not in valid_context_types:
                raise ValueError(
                    f"Invalid active_context_type: {active_context_type}. "
                    f"Must be one of: {', '.join(valid_context_types)}"
                )

        # Validate current_session_id format (UUID)
        session_uuid: UUID | None = None
        if current_session_id is not None:
            try:
                session_uuid = UUID(current_session_id)
            except (ValueError, AttributeError) as e:
                raise ValueError(
                    f"Invalid current_session_id format: {current_session_id}"
                ) from e

        # Validate git_head_commit format (40 lowercase hex characters)
        if git_head_commit is not None:
            if not (
                isinstance(git_head_commit, str)
                and len(git_head_commit) == 40
                and all(c in "0123456789abcdef" for c in git_head_commit)
            ):
                raise ValueError(
                    f"Invalid git_head_commit format: {git_head_commit}. "
                    "Must be 40 lowercase hex characters."
                )

        # Validate default_token_budget range
        if default_token_budget is not None:
            if not (1000 <= default_token_budget <= 1000000):
                raise ValueError(
                    f"Invalid default_token_budget: {default_token_budget}. "
                    "Must be between 1000 and 1000000."
                )

        # Validate git_branch length
        if git_branch is not None and len(git_branch) > 100:
            raise ValueError(
                f"git_branch too long: {len(git_branch)} chars (max 100)"
            )

        # Validate updated_by length
        if len(updated_by) > 100:
            raise ValueError(f"updated_by too long: {len(updated_by)} chars (max 100)")

    except ValueError:
        # Re-raise validation errors (FastMCP handles them automatically)
        raise
    except Exception as e:
        # Wrap unexpected validation errors
        logger.error(
            "Unexpected error during input validation",
            extra={
                "context": {
                    "operation": "update_project_configuration",
                    "error": str(e),
                }
            },
        )
        raise ValueError(f"Input validation failed: {e}") from e

    # Perform database health check
    database_healthy = await check_database_health()
    health_check_timestamp = datetime.now(timezone.utc)

    # Update singleton configuration
    try:
        async with get_session() as session:
            # Query existing configuration
            result = await session.execute(
                select(ProjectConfiguration).where(
                    ProjectConfiguration.id == SINGLETON_CONFIG_ID
                )
            )
            config = result.scalar_one_or_none()

            if config is None:
                # Create new configuration (upsert pattern)
                logger.info(
                    "Creating new singleton project configuration",
                    extra={
                        "context": {
                            "operation": "update_project_configuration",
                            "singleton_id": SINGLETON_CONFIG_ID,
                        }
                    },
                )

                config = ProjectConfiguration(
                    id=SINGLETON_CONFIG_ID,
                    active_context_type=active_context_type or "feature",
                    current_session_id=session_uuid,
                    git_branch=git_branch,
                    git_head_commit=git_head_commit,
                    default_token_budget=default_token_budget or 200000,
                    database_healthy=database_healthy,
                    last_health_check_at=health_check_timestamp,
                    updated_by=updated_by,
                )
                session.add(config)
            else:
                # Update existing configuration (partial update)
                if active_context_type is not None:
                    config.active_context_type = active_context_type
                if current_session_id is not None:
                    config.current_session_id = session_uuid
                if git_branch is not None:
                    config.git_branch = git_branch
                if git_head_commit is not None:
                    config.git_head_commit = git_head_commit
                if default_token_budget is not None:
                    config.default_token_budget = default_token_budget

                # Always update health check status
                config.database_healthy = database_healthy
                config.last_health_check_at = health_check_timestamp
                config.updated_by = updated_by

            # Commit transaction (handled by get_session context manager)
            await session.flush()  # Ensure DB assigns values before returning

    except IntegrityError as e:
        logger.error(
            "Integrity constraint violation during configuration update",
            extra={
                "context": {
                    "operation": "update_project_configuration",
                    "error": str(e),
                }
            },
            exc_info=True,
        )
        if ctx:
            await ctx.error(f"Database integrity error: {str(e)[:100]}")
        raise ValueError(f"Database integrity constraint violated: {e}") from e
    except Exception as e:
        logger.error(
            "Failed to update project configuration",
            extra={
                "context": {
                    "operation": "update_project_configuration",
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            },
            exc_info=True,
        )
        if ctx:
            await ctx.error(f"Database update failed: {str(e)[:100]}")
        raise  # Let FastMCP handle the error response

    # Calculate latency
    latency_ms = int((time.perf_counter() - start_time) * 1000)

    # Format response according to MCP contract
    response: dict[str, Any] = {
        "id": config.id,
        "active_context_type": config.active_context_type,
        "current_session_id": (
            str(config.current_session_id) if config.current_session_id else None
        ),
        "git_branch": config.git_branch,
        "git_head_commit": config.git_head_commit,
        "default_token_budget": config.default_token_budget,
        "database_healthy": config.database_healthy,
        "last_health_check_at": (
            config.last_health_check_at.isoformat()
            if config.last_health_check_at
            else None
        ),
        "updated_at": config.updated_at.isoformat(),
        "updated_by": config.updated_by,
    }

    logger.info(
        "update_project_configuration completed successfully",
        extra={
            "context": {
                "operation": "update_project_configuration",
                "latency_ms": latency_ms,
                "active_context_type": config.active_context_type,
                "git_branch": config.git_branch,
                "database_healthy": database_healthy,
            }
        },
    )

    # Performance warning if exceeds target
    if latency_ms > 100:
        logger.warning(
            "update_project_configuration latency exceeded p95 target",
            extra={
                "context": {
                    "latency_ms": latency_ms,
                    "target_ms": 100,
                }
            },
        )

    if ctx:
        await ctx.info(
            f"Updated configuration (context: {config.active_context_type}, "
            f"branch: {config.git_branch or 'none'}, healthy: {database_healthy}) "
            f"in {latency_ms}ms"
        )

    return response


# ==============================================================================
# Module Exports
# ==============================================================================

__all__ = ["get_project_configuration", "update_project_configuration"]
