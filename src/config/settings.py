"""
Production-grade settings configuration for Codebase MCP Server.

Constitutional Compliance:
- Principle V: Production quality with fail-fast validation
- Principle VIII: Type safety with Pydantic 2.0+, mypy --strict compliance

All configuration values are loaded from environment variables with .env support.
Validation errors halt server startup with actionable error messages.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated
import warnings

from pydantic import (
    Field,
    HttpUrl,
    PostgresDsn,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

# Import PoolConfig for connection pool management
from src.connection_pool.config import PoolConfig

# ============================================================================
# Constants
# ============================================================================

# Performance warning threshold for embedding batch size
MIN_RECOMMENDED_BATCH_SIZE = 10


class LogLevel(str, Enum):
    """Valid log levels for structured logging."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """
    Application settings with environment variable parsing and validation.

    All settings are loaded from environment variables with .env file support.
    Required fields must be set or server startup will fail.

    Connection Pool Integration:
        The Settings class automatically initializes a PoolConfig instance from
        DATABASE_URL and POOL_* environment variables. This ensures fail-fast
        behavior: invalid configuration will halt server startup with clear
        error messages.

        The pool_config field is automatically populated during validation and
        provides access to advanced connection pool settings. If no POOL_*
        environment variables are set, default values from PoolConfig are used.

    Example .env:
        # Required: Database connection
        DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/codebase_mcp

        # Ollama Configuration
        OLLAMA_BASE_URL=http://localhost:11434
        OLLAMA_EMBEDDING_MODEL=nomic-embed-text

        # Performance Tuning
        EMBEDDING_BATCH_SIZE=50
        MAX_CONCURRENT_REQUESTS=10

        # Legacy Pool Configuration (Deprecated - use POOL_* variables instead)
        DB_POOL_SIZE=20
        DB_MAX_OVERFLOW=10

        # Logging
        LOG_LEVEL=INFO
        LOG_FILE=/tmp/codebase-mcp.log

        # Advanced Connection Pool Configuration (Optional - uses defaults if not set)
        # All POOL_* variables are optional. Defaults are production-ready.
        POOL_MIN_SIZE=2              # Min connections (default: 2)
        POOL_MAX_SIZE=10             # Max connections (default: 10)
        POOL_TIMEOUT=30.0            # Connection acquisition timeout (default: 30.0s)
        POOL_COMMAND_TIMEOUT=60.0    # Query execution timeout (default: 60.0s)
        POOL_MAX_IDLE_TIME=60.0      # Idle connection timeout (default: 60.0s)
        POOL_MAX_QUERIES=50000       # Queries before connection recycling (default: 50000)
        POOL_MAX_CONNECTION_LIFETIME=3600.0  # Max connection age (default: 3600.0s)
        POOL_LEAK_DETECTION_TIMEOUT=30.0     # Leak warning threshold (default: 30.0s)
        POOL_ENABLE_LEAK_DETECTION=true      # Enable leak detection (default: true)

    Validation Rules:
        - DATABASE_URL must use postgresql+asyncpg:// scheme
        - POOL_MAX_SIZE must be >= POOL_MIN_SIZE
        - All timeout values must be positive
        - Configuration errors fail fast at startup with actionable messages

    Usage Example:
        >>> from src.config.settings import get_settings
        >>> settings = get_settings()
        >>> # Access database URL
        >>> db_url = settings.database_url
        >>> # Access pool configuration
        >>> pool_config = settings.pool_config
        >>> print(f"Pool size: {pool_config.min_size}-{pool_config.max_size}")
        Pool size: 2-10
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",  # Fail on unknown env vars to catch typos
    )

    # ============================================================================
    # Database Configuration
    # ============================================================================

    database_url: Annotated[
        PostgresDsn,
        Field(
            description=(
                "PostgreSQL connection URL with asyncpg driver. "
                "Format: postgresql+asyncpg://user:password@host:port/database"
            ),
        ),
    ]

    db_pool_size: Annotated[
        int,
        Field(
            default=20,
            ge=5,
            le=50,
            description=(
                "SQLAlchemy connection pool size. "
                "Should accommodate max concurrent AI assistants. "
                "Range: 5-50"
            ),
        ),
    ]

    db_max_overflow: Annotated[
        int,
        Field(
            default=10,
            ge=0,
            le=20,
            description=(
                "Maximum overflow connections beyond pool_size. "
                "Handles traffic spikes. "
                "Range: 0-20"
            ),
        ),
    ]

    # ============================================================================
    # Ollama Configuration
    # ============================================================================

    ollama_base_url: Annotated[
        HttpUrl,
        Field(
            default="http://localhost:11434",
            description=(
                "Ollama API base URL for embedding generation. "
                "Must be accessible from the server."
            ),
        ),
    ]

    ollama_embedding_model: Annotated[
        str,
        Field(
            default="nomic-embed-text",
            min_length=1,
            description=(
                "Ollama embedding model name. "
                "Must be pulled locally: ollama pull nomic-embed-text"
            ),
        ),
    ]

    # ============================================================================
    # Performance Tuning
    # ============================================================================

    embedding_batch_size: Annotated[
        int,
        Field(
            default=50,
            ge=1,
            le=1000,
            description=(
                "Number of text chunks to embed per Ollama API request. "
                "Larger batches improve throughput but increase latency. "
                "Range: 1-1000"
            ),
        ),
    ]

    max_concurrent_requests: Annotated[
        int,
        Field(
            default=10,
            ge=1,
            le=100,
            description=(
                "Maximum concurrent AI assistant connections. "
                "Limits resource usage under load. "
                "Range: 1-100"
            ),
        ),
    ]

    # ============================================================================
    # Logging Configuration
    # ============================================================================

    log_level: Annotated[
        LogLevel,
        Field(
            default=LogLevel.INFO,
            description=(
                "Logging verbosity level. "
                "Valid values: DEBUG, INFO, WARNING, ERROR, CRITICAL"
            ),
        ),
    ]

    log_file: Annotated[
        str,
        Field(
            default="/tmp/codebase-mcp.log",  # noqa: S108 - temporary log file is acceptable for MCP server
            min_length=1,
            description=(
                "File path for structured JSON logs. "
                "CRITICAL: Never log to stdout/stderr (MCP protocol violation)"
            ),
        ),
    ]

    # ============================================================================
    # Multi-project Workspace Integration (Optional)
    # ============================================================================

    workflow_mcp_url: Annotated[
        HttpUrl | None,
        Field(
            default=None,
            description=(
                "Optional workflow-mcp server URL for automatic project detection. "
                "If not set, multi-project workspace features are disabled."
            ),
        ),
    ] = None

    workflow_mcp_timeout: Annotated[
        float,
        Field(
            default=1.0,
            ge=0.1,
            le=5.0,
            description=(
                "Timeout for workflow-mcp queries (seconds). "
                "Should be low to avoid blocking indexing operations. "
                "Range: 0.1-5.0"
            ),
        ),
    ] = 1.0

    workflow_mcp_cache_ttl: Annotated[
        int,
        Field(
            default=60,
            ge=10,
            le=300,
            description=(
                "Cache TTL for workflow-mcp responses (seconds). "
                "Reduces query overhead for repeated repository checks. "
                "Range: 10-300"
            ),
        ),
    ] = 60

    # ============================================================================
    # Connection Pool Configuration
    # ============================================================================

    pool_config: Annotated[
        PoolConfig | None,
        Field(
            default=None,
            description=(
                "Advanced connection pool configuration. "
                "This field is automatically populated from DATABASE_URL and POOL_* environment variables. "
                "If not explicitly set, a PoolConfig instance will be created with DATABASE_URL "
                "and default pool settings during validation."
            ),
        ),
    ] = None

    # ============================================================================
    # Validators
    # ============================================================================

    @field_validator("database_url")
    @classmethod
    def validate_asyncpg_driver(cls, v: PostgresDsn) -> PostgresDsn:
        """
        Ensure DATABASE_URL uses asyncpg driver for async SQLAlchemy.

        Args:
            v: PostgreSQL DSN to validate

        Returns:
            Validated PostgreSQL DSN

        Raises:
            ValueError: If scheme is not postgresql+asyncpg
        """
        if v.scheme != "postgresql+asyncpg":
            error_msg = (
                "DATABASE_URL must use asyncpg driver for async operations.\n"
                f"Found: {v.scheme}\n"
                "Expected: postgresql+asyncpg\n\n"
                "Fix: Update .env file:\n"
                "  DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/codebase_mcp"
            )
            raise ValueError(error_msg)
        return v

    @field_validator("ollama_base_url")
    @classmethod
    def validate_ollama_url(cls, v: HttpUrl) -> HttpUrl:
        """
        Ensure Ollama URL is well-formed and uses HTTP/HTTPS.

        Args:
            v: Ollama base URL to validate

        Returns:
            Validated Ollama URL

        Raises:
            ValueError: If URL is malformed
        """
        # Pydantic HttpUrl already validates format
        # Additional checks can be added here if needed
        return v

    @field_validator("db_pool_size", "db_max_overflow")
    @classmethod
    def validate_pool_configuration(cls, v: int) -> int:
        """
        Validate database pool size configuration is reasonable.

        Args:
            v: Pool size value to validate

        Returns:
            Validated pool size

        Raises:
            ValueError: If pool configuration is invalid
        """
        # Validation handled by Field constraints (ge/le)
        # This validator can add cross-field validation if needed
        return v

    @field_validator("embedding_batch_size")
    @classmethod
    def validate_batch_size(cls, v: int) -> int:
        """
        Validate embedding batch size is optimized for performance.

        Args:
            v: Batch size to validate

        Returns:
            Validated batch size

        Raises:
            ValueError: If batch size is suboptimal
        """
        # Warn about very small batch sizes (performance impact)
        if v < MIN_RECOMMENDED_BATCH_SIZE:
            warnings.warn(
                f"EMBEDDING_BATCH_SIZE={v} is very small and may impact indexing performance. "
                "Recommended: 50-100 for optimal throughput.",
                stacklevel=2,
            )
        return v

    @model_validator(mode="after")
    def initialize_pool_config(self) -> "Settings":
        """
        Initialize pool_config from DATABASE_URL and environment variables.

        This validator automatically creates a PoolConfig instance if one wasn't
        explicitly provided. It uses the DATABASE_URL from Settings and reads
        POOL_* environment variables for pool-specific configuration.

        This ensures fail-fast behavior: if DATABASE_URL is invalid or missing,
        server startup will fail with a clear error message.

        Returns:
            Settings instance with initialized pool_config

        Raises:
            ValueError: If PoolConfig creation fails due to invalid configuration

        Example:
            >>> # With only DATABASE_URL set
            >>> settings = Settings(database_url="postgresql+asyncpg://localhost/db")
            >>> settings.pool_config.min_size  # Uses default: 2
            2
            >>> settings.pool_config.database_url
            'postgresql+asyncpg://localhost/db'

            >>> # With POOL_* environment variables
            >>> # POOL_MIN_SIZE=5, POOL_MAX_SIZE=20
            >>> settings = Settings(database_url="postgresql+asyncpg://localhost/db")
            >>> settings.pool_config.min_size
            5
        """
        if self.pool_config is None:
            # Convert PostgresDsn to string for PoolConfig
            database_url_str = str(self.database_url)

            try:
                # Create PoolConfig with DATABASE_URL
                # PoolConfig will automatically read POOL_* environment variables
                self.pool_config = PoolConfig(database_url=database_url_str)
            except Exception as e:
                # Re-raise with context about where the error occurred
                error_msg = (
                    "Failed to initialize connection pool configuration.\n"
                    f"Error: {e}\n\n"
                    "This typically indicates:\n"
                    "  1. Invalid POOL_* environment variable values\n"
                    "  2. Conflicting pool size configuration (max_size < min_size)\n"
                    "  3. Out-of-range timeout values\n\n"
                    "Check your .env file and ensure POOL_* variables follow PoolConfig validation rules.\n"
                    "See PoolConfig documentation for valid ranges and constraints."
                )
                raise ValueError(error_msg) from e

        return self


# ============================================================================
# Singleton Instance
# ============================================================================

# Lazy-loaded singleton for testing flexibility
_settings_instance: Settings | None = None


def get_settings() -> Settings:
    """
    Get singleton settings instance with lazy initialization.

    Returns:
        Singleton Settings instance

    Raises:
        ValidationError: If environment variables are invalid or missing

    Example:
        >>> settings = get_settings()
        >>> db_url = settings.database_url
        >>> batch_size = settings.embedding_batch_size
    """
    global _settings_instance  # noqa: PLW0603 - singleton pattern requires global state
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


# ============================================================================
# Convenience Export
# ============================================================================

# Primary export for application code
# Note: This will fail if DATABASE_URL is not set. In that case, use get_settings()
# or import Settings directly for testing/validation purposes.
try:
    settings = get_settings()
except Exception:
    # Allow module import even if settings validation fails
    # This enables testing and validation without requiring full config
    settings = None  # type: ignore[assignment]


# ============================================================================
# Type Exports for External Use
# ============================================================================

__all__ = [
    "LogLevel",
    "PoolConfig",
    "Settings",
    "get_settings",
    "settings",
]
