"""Connection pool configuration with environment variable support.

This module defines the PoolConfig model for configuring PostgreSQL connection pools
with Pydantic validation and environment variable overrides.

Constitutional Compliance:
- Principle VIII: Pydantic-based type safety with complete validation
- Principle V: Production-quality error messages with actionable suggestions
- Principle III: JSON-serializable for MCP protocol transport
"""

from __future__ import annotations

from pydantic import Field, ValidationInfo, field_validator
from pydantic_settings import BaseSettings


class PoolConfig(BaseSettings):
    """Connection pool configuration with environment variable overrides.

    This configuration model provides comprehensive connection pool tuning with
    runtime validation, environment variable support, and immutability guarantees.

    Environment Variables:
        POOL_MIN_SIZE: Minimum pool size (default: 2)
        POOL_MAX_SIZE: Maximum pool size (default: 10)
        POOL_MAX_QUERIES: Queries before recycling (default: 50000)
        POOL_MAX_IDLE_TIME: Idle timeout in seconds (default: 60.0)
        POOL_TIMEOUT: Acquisition timeout (default: 30.0)
        POOL_COMMAND_TIMEOUT: Query timeout (default: 60.0)
        POOL_MAX_CONNECTION_LIFETIME: Connection max age (default: 3600.0)
        POOL_LEAK_DETECTION_TIMEOUT: Leak warning threshold (default: 30.0)
        POOL_ENABLE_LEAK_DETECTION: Enable leak detection (default: true)
        POOL_DATABASE_URL or DATABASE_URL: PostgreSQL connection string (required)

    Example:
        >>> config = PoolConfig(
        ...     min_size=2,
        ...     max_size=10,
        ...     timeout=30.0,
        ...     database_url="postgresql+asyncpg://localhost/codebase_mcp"
        ... )
        >>> config.min_size
        2

    Validation Rules:
        - min_size: 1 <= value <= 100
        - max_size: 1 <= value <= 100, must be >= min_size
        - max_queries: >= 1000
        - max_idle_time: >= 10.0 seconds
        - timeout: 0 < value < 300 seconds
        - command_timeout: > 0 seconds
        - max_connection_lifetime: >= 60 seconds
        - leak_detection_timeout: >= 0 (0 = disabled)
        - database_url: Required, must be valid PostgreSQL connection string
    """

    min_size: int = Field(
        default=2,
        ge=1,
        le=100,
        description="Minimum number of connections to maintain in the pool. "
        "The pool will always keep at least this many connections alive, "
        "even during idle periods. Range: 1-100."
    )

    max_size: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of connections allowed in the pool. "
        "The pool will never exceed this limit. When all connections are in use, "
        "new requests will wait (up to timeout) for a connection to become available. "
        "Must be >= min_size. Range: 1-100."
    )

    max_queries: int = Field(
        default=50000,
        ge=1000,
        description="Maximum number of queries a connection can execute before recycling. "
        "After reaching this limit, the connection is closed and replaced with a new one. "
        "Prevents memory leaks from long-lived connections. Minimum: 1000."
    )

    max_idle_time: float = Field(
        default=60.0,
        ge=10.0,
        description="Maximum time in seconds a connection can remain idle before being closed. "
        "Idle connections exceeding this duration are automatically removed from the pool "
        "to free resources. The pool will maintain at least min_size connections. Minimum: 10.0s."
    )

    timeout: float = Field(
        default=30.0,
        gt=0.0,
        lt=300.0,
        description="Maximum time in seconds to wait for connection acquisition. "
        "If no connection becomes available within this timeout, a PoolTimeoutError is raised. "
        "Range: 0-300 seconds (5 minutes max)."
    )

    command_timeout: float = Field(
        default=60.0,
        gt=0.0,
        description="Maximum time in seconds for query execution. "
        "Queries exceeding this timeout will be cancelled. "
        "Set higher for long-running analytical queries. Must be > 0."
    )

    max_connection_lifetime: float = Field(
        default=3600.0,
        ge=60.0,
        description="Maximum age of a connection in seconds. "
        "Connections older than this value are closed and replaced, "
        "even if they haven't reached max_queries. Prevents connection staleness. "
        "Minimum: 60 seconds (1 minute)."
    )

    leak_detection_timeout: float = Field(
        default=30.0,
        ge=0.0,
        description="Time in seconds before issuing connection leak warning. "
        "If a connection is held longer than this threshold, a warning is logged "
        "with the acquisition stack trace. Set to 0 to disable leak detection. "
        "Minimum: 0 (disabled)."
    )

    enable_leak_detection: bool = Field(
        default=True,
        description="Toggle connection leak detection. "
        "When enabled, tracks connection acquisition times and stack traces "
        "to detect potential leaks. Recommended for development and staging. "
        "Can be disabled in production for performance."
    )

    database_url: str = Field(
        ...,
        description="PostgreSQL connection string. "
        "Must use asyncpg driver format: postgresql+asyncpg://user:pass@host:port/database. "
        "This field is required and has no default value. "
        "Supports both POOL_DATABASE_URL and DATABASE_URL environment variables."
    )

    @field_validator("max_size")
    @classmethod
    def validate_max_size_greater_than_min(cls, v: int, info: ValidationInfo) -> int:
        """Ensure max_size >= min_size.

        This validator enforces that the maximum pool size is at least as large
        as the minimum pool size to prevent invalid configurations.

        Args:
            v: The max_size value to validate
            info: Validation context containing other field values

        Returns:
            The validated max_size value

        Raises:
            ValueError: If max_size < min_size with actionable error message

        Example:
            >>> # Valid configuration
            >>> config = PoolConfig(min_size=2, max_size=10, database_url="...")
            >>> # Invalid configuration
            >>> config = PoolConfig(min_size=15, max_size=10, database_url="...")
            ValidationError: max_size (10) must be >= min_size (15).
            Suggestion: Increase POOL_MAX_SIZE to 15 or reduce POOL_MIN_SIZE to 10
        """
        if "min_size" in info.data and v < info.data["min_size"]:
            raise ValueError(
                f"max_size ({v}) must be >= min_size ({info.data['min_size']}). "
                f"Suggestion: Increase POOL_MAX_SIZE to {info.data['min_size']} or reduce POOL_MIN_SIZE to {v}"
            )
        return v

    model_config = {
        "env_prefix": "POOL_",  # POOL_MIN_SIZE, POOL_MAX_SIZE, etc.
        "env_file": ".env",  # Load from .env file if present
        "frozen": True,  # Immutable after initialization
        "extra": "ignore",  # Ignore extra environment variables
    }
