#!/usr/bin/env python3
"""
Example demonstrating Pydantic settings configuration usage.

This example shows:
- Loading settings from environment variables
- Accessing configuration values
- Type-safe configuration usage
- Error handling for invalid configuration

Usage:
    # Set environment variables first
    export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/codebase_mcp"
    export LOG_LEVEL="DEBUG"

    # Run the example
    python examples/settings_example.py
"""

from __future__ import annotations

from src.config import settings


def demonstrate_settings_usage() -> None:
    """Demonstrate accessing and using settings configuration."""
    print("=== Codebase MCP Server Settings ===\n")

    # Database Configuration
    print("Database Configuration:")
    print(f"  URL: {settings.database_url}")
    print(f"  Pool Size: {settings.db_pool_size}")
    print(f"  Max Overflow: {settings.db_max_overflow}")
    print()

    # Ollama Configuration
    print("Ollama Configuration:")
    print(f"  Base URL: {settings.ollama_base_url}")
    print(f"  Embedding Model: {settings.ollama_embedding_model}")
    print()

    # Performance Tuning
    print("Performance Tuning:")
    print(f"  Embedding Batch Size: {settings.embedding_batch_size}")
    print(f"  Max Concurrent Requests: {settings.max_concurrent_requests}")
    print()

    # Logging Configuration
    print("Logging Configuration:")
    print(f"  Log Level: {settings.log_level.value}")
    print(f"  Log File: {settings.log_file}")
    print()

    # Type-safe usage examples
    print("Type-Safe Usage Examples:")
    print(f"  Database pool size is int: {isinstance(settings.db_pool_size, int)}")
    print(
        f"  Embedding batch size is int: {isinstance(settings.embedding_batch_size, int)}"
    )
    print(f"  Log level is enum: {type(settings.log_level).__name__}")
    print()

    # Configuration validation
    print("Configuration Validation:")
    print(
        f"  ✓ Database URL uses asyncpg driver: "
        f"{str(settings.database_url).startswith('postgresql+asyncpg://')}"
    )
    print(
        f"  ✓ Embedding batch size in range [1-1000]: "
        f"{1 <= settings.embedding_batch_size <= 1000}"
    )
    print(
        f"  ✓ Pool size in range [5-50]: " f"{5 <= settings.db_pool_size <= 50}"
    )
    print()


if __name__ == "__main__":
    try:
        demonstrate_settings_usage()
    except Exception as e:
        print(f"ERROR: Failed to load settings: {e}")
        print("\nPlease ensure required environment variables are set:")
        print("  DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/codebase_mcp")
        print("\nOr create a .env file in the project root with:")
        print("  DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/codebase_mcp")
        print("  LOG_LEVEL=INFO")
