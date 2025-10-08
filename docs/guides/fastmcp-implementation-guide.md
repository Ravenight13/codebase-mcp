# FastMCP Implementation Guide

**A Comprehensive Guide to Building Production-Grade MCP Servers with FastMCP**

> Based on lessons learned from the Codebase MCP Server project - a production-grade MCP server implementation that indexes code repositories for semantic search using PostgreSQL with pgvector.

**Version**: 1.0
**Last Updated**: 2025-10-08
**Reference Implementation**: `/Users/cliffclarke/Claude_Code/codebase-mcp`

---

## Table of Contents

1. [Introduction](#introduction)
2. [Project Setup](#project-setup)
3. [FastMCP Core Setup](#fastmcp-core-setup)
4. [Database Integration (PostgreSQL + pgvector)](#database-integration)
5. [Implementing MCP Resources](#implementing-mcp-resources)
6. [Implementing MCP Tools](#implementing-mcp-tools)
7. [Error Handling & Logging](#error-handling--logging)
8. [Testing Strategy](#testing-strategy)
9. [Common Pitfalls & Solutions](#common-pitfalls--solutions)
10. [Deployment](#deployment)
11. [MCP Client Integration](#mcp-client-integration)
12. [Reference Implementation](#reference-implementation)

---

## Introduction

### What is FastMCP?

FastMCP is a modern Python framework for building Model Context Protocol (MCP) servers. It simplifies MCP server development with decorator-based tool registration, automatic JSON schema generation, and built-in transport handling.

**Key Features**:
- **Decorator-based API**: Use `@mcp.tool()` to register tools
- **Automatic schema generation**: Type hints → JSON schemas
- **Stdio & SSE transports**: Built-in protocol handling
- **Context injection**: Optional client communication channel
- **Lifespan management**: AsyncContextManager for startup/shutdown

### When to Use This Guide

This guide is for you if:
- You're building an MCP server with Python
- You need database integration (PostgreSQL, etc.)
- You want production-quality code with tests
- You've hit confusing FastMCP issues

### Common Pitfalls This Guide Prevents

This guide documents solutions to critical issues encountered during development:

1. **Double-Import Problem**: Tools registered but invisible to MCP protocol
2. **Stdout/Stderr Pollution**: Breaking MCP protocol with console logs
3. **Event Loop Conflicts**: Async initialization timing issues
4. **Session Management**: Import binding issues with database sessions
5. **Type Safety**: mypy --strict compliance patterns

**Estimated Time Savings**: 8-20 hours of debugging these issues.

---

## Project Setup

### Directory Structure

```
your-mcp-server/
├── src/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py              # Pydantic settings
│   ├── database.py                  # Database connection management
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py              # SQLAlchemy Base
│   │   └── your_model.py            # Your models
│   ├── services/
│   │   ├── __init__.py
│   │   └── your_service.py          # Business logic
│   └── mcp/
│       ├── __init__.py
│       ├── server_fastmcp.py        # FastMCP server
│       ├── errors.py                # Custom error classes
│       ├── mcp_logging.py           # File-only logging
│       └── tools/
│           ├── __init__.py
│           ├── tool1.py
│           └── tool2.py
├── run_server.py                    # Wrapper script (CRITICAL!)
├── tests/
│   ├── contract/                    # MCP protocol compliance
│   ├── integration/                 # End-to-end tests
│   └── unit/                        # Isolated component tests
├── migrations/                      # Alembic database migrations
├── scripts/                         # Utility scripts
├── .env.example                     # Environment template
├── pyproject.toml                   # Dependencies & tool config
├── requirements.txt                 # Production dependencies
└── requirements-dev.txt             # Dev dependencies
```

### pyproject.toml Configuration

```toml
[project]
name = "your-mcp-server"
version = "0.1.0"
description = "Your MCP server description"
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=0.1.0",           # FastMCP framework
    "mcp>=0.9.0",               # MCP Python SDK
    "pydantic>=2.5.0",          # Data validation
    "pydantic-settings>=2.1.0", # Environment config
    "sqlalchemy[asyncpg]>=2.0.25",  # Database ORM (if needed)
    "httpx>=0.26.0",            # Async HTTP client
    "python-dotenv>=1.0.0",     # .env file support
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "mypy>=1.8.0",
    "ruff>=0.1.11",
]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[tool.mypy]
strict = true
python_version = "3.11"

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "ANN", "ASYNC", "S", "B"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = [
    "--cov=src",
    "--cov-fail-under=95",
    "-vv",
]
```

### Dependency Management

**Option 1: UV (Recommended)**
```bash
# Install dependencies
uv sync

# Run server
uv run python run_server.py
```

**Option 2: Pip (Traditional)**
```bash
# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements-dev.txt
pip install -e .
```

### Python Version

**Requirement**: Python 3.11+

**Why 3.11+**:
- Modern type hints (`X | None` syntax)
- AsyncIO improvements
- Performance enhancements
- Match/case statements (useful for error handling)

---

## FastMCP Core Setup

### Server Initialization Pattern

**File**: `src/mcp/server_fastmcp.py`

```python
from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastmcp import FastMCP

# Configure file-only logging (CRITICAL - no stdout/stderr!)
LOG_FILE = Path("/tmp/your-mcp-server.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        ),
    ],
)

logger = logging.getLogger(__name__)

# Suppress external library logs
logging.getLogger("fastmcp").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastMCP) -> AsyncGenerator[None, None]:
    """
    Lifespan context manager for startup/shutdown.

    BLOCKING PATTERN: Wait for initialization to complete before
    accepting connections. This ensures tools can access resources
    immediately when called.
    """
    # Startup: Initialize resources (database, etc.)
    try:
        logger.info("Initializing server resources...")
        sys.stderr.write("INFO: Initializing resources...\n")

        # Initialize database, connections, etc. (BLOCKING)
        await init_db_connection()

        logger.info("✓ Server initialized successfully")
        sys.stderr.write("INFO: Server ready for connections\n")
    except Exception as e:
        logger.critical(f"Initialization failed: {e}", exc_info=True)
        sys.stderr.write(f"FATAL: Initialization failed: {e}\n")
        raise RuntimeError(f"Server initialization failed: {e}") from e

    # Yield control to FastMCP (server starts)
    yield

    # Shutdown: Clean up resources
    try:
        logger.info("Shutting down server...")
        await close_db_connection()
        logger.info("✓ Shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)


# Initialize FastMCP instance
mcp = FastMCP(
    "your-mcp-server",
    version="0.1.0",
    lifespan=lifespan,
)

# Export for tool imports
__all__ = ["mcp"]


def main() -> None:
    """
    Main entry point.

    CRITICAL: Import tools INSIDE main() to avoid double-import issue.
    """
    try:
        # Import tool modules (triggers @mcp.tool() registration)
        logger.info("Importing tool modules...")
        import src.mcp.tools.tool1  # noqa: F401
        import src.mcp.tools.tool2  # noqa: F401
        logger.info("✓ Tool modules imported successfully")
    except ImportError as e:
        logger.critical(f"FATAL: Failed to import tool modules: {e}")
        sys.stderr.write(f"FATAL: Tool import failed: {e}\n")
        sys.exit(1)

    # Start server (FastMCP handles stdio protocol)
    try:
        logger.info("Starting FastMCP server...")
        mcp.run()
    except Exception as e:
        logger.critical(f"Server startup failed: {e}", exc_info=True)
        sys.stderr.write(f"FATAL: Server startup failed: {e}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Wrapper Script (CRITICAL!)

**File**: `run_server.py` (root directory)

```python
#!/usr/bin/env python3
"""
Wrapper script to prevent double-import issue.

CRITICAL: This wrapper ensures the server module loads exactly once,
preventing the double-import problem where tools register on one
mcp instance but the protocol queries a different instance.

Without this wrapper:
- Running `python -m src.mcp.server_fastmcp` loads module twice
- Once as __main__ (entry point)
- Once as src.mcp.server_fastmcp (when tools import it)
- Result: Tools register on __main__.mcp but protocol queries
  src.mcp.server_fastmcp.mcp → zero tools visible

With this wrapper:
- Runs as __main__ but imports server module by full path
- Single module instance throughout execution
- All tools properly registered and visible
"""

import sys
from pathlib import Path

# Ensure project root is in path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import and run - ensures single module load
from src.mcp.server_fastmcp import main

if __name__ == "__main__":
    main()
```

**Make it executable**:
```bash
chmod +x run_server.py
```

### Why the Wrapper Script is Critical

**The Double-Import Problem**:

When you run `python -m src.mcp.server_fastmcp`:
1. Python loads the module as `__main__` (the entry point)
2. Tools import `from src.mcp.server_fastmcp import mcp`
3. Python loads the module AGAIN as `src.mcp.server_fastmcp`
4. Now there are TWO `mcp` instances:
   - `__main__.mcp` (where tools registered)
   - `src.mcp.server_fastmcp.mcp` (where protocol queries)
5. Result: MCP client sees zero tools despite successful registration

**The Wrapper Solution**:
- Wrapper runs as `__main__`
- Imports server module by full path
- Single module instance = single `mcp` instance
- Tools and protocol use same instance ✅

### Transport Configuration

FastMCP automatically handles transport based on how you run it:

**Stdio Transport** (for Claude Desktop):
```python
# No special configuration needed!
mcp.run()  # Automatically uses stdio
```

**Configuration for Claude Desktop**:
```json
{
  "mcpServers": {
    "your-server": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/run_server.py"],
      "env": {
        "DATABASE_URL": "postgresql+asyncpg://...",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**CRITICAL Requirements**:
- Use absolute paths (no `~` or relative paths)
- Use wrapper script (`run_server.py`)
- All logs must go to file (NO stdout/stderr)
- Environment variables in config (not inherited)

---

## Database Integration

### PostgreSQL + pgvector Setup

**Dependencies**:
```toml
dependencies = [
    "sqlalchemy[asyncpg]>=2.0.25",
    "alembic>=1.13.0",
    "pgvector>=0.2.4",  # Vector similarity search
]
```

### Database Configuration

**File**: `src/config/settings.py`

```python
from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Annotated


class Settings(BaseSettings):
    """Type-safe environment configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",  # Fail on typos in env var names
    )

    # Database
    database_url: Annotated[
        PostgresDsn,
        Field(description="PostgreSQL connection URL with asyncpg driver"),
    ]

    db_pool_size: Annotated[
        int,
        Field(default=20, ge=5, le=50, description="Connection pool size"),
    ] = 20

    db_max_overflow: Annotated[
        int,
        Field(default=10, ge=0, le=20, description="Overflow connections"),
    ] = 10

    @field_validator("database_url")
    @classmethod
    def validate_asyncpg_driver(cls, v: PostgresDsn) -> PostgresDsn:
        """Ensure async driver is used."""
        if v.scheme != "postgresql+asyncpg":
            raise ValueError(
                "DATABASE_URL must use asyncpg driver.\n"
                f"Found: {v.scheme}\n"
                "Expected: postgresql+asyncpg\n\n"
                "Fix: Update .env file:\n"
                "  DATABASE_URL=postgresql+asyncpg://user:password@host/db"
            )
        return v


# Singleton instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get cached settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
```

**Environment file** (`.env.example`):
```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/your_db
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
LOG_LEVEL=INFO
LOG_FILE=/tmp/your-mcp-server.log
```

### Connection Management

**File**: `src/database.py`

```python
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

# Global session factory (initialized at startup)
_session_factory: async_sessionmaker[AsyncSession] | None = None
_engine: AsyncEngine | None = None


async def init_db_connection() -> None:
    """
    Initialize database connection pool.

    Called during FastMCP lifespan startup.
    BLOCKING: Waits for database to be ready.
    """
    global _session_factory, _engine

    settings = get_settings()

    # Create async engine with connection pooling
    _engine = create_async_engine(
        str(settings.database_url),
        echo=False,  # Set True for SQL debugging
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,    # Health check before use
        pool_recycle=3600,     # Recycle connections after 1 hour
    )

    # Create session factory
    _session_factory = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    logger.info("Database connection pool initialized")


async def close_db_connection() -> None:
    """Close database connection pool."""
    global _engine

    if _engine is not None:
        await _engine.dispose()
        logger.info("Database connection pool closed")


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get the session factory.

    CRITICAL: This function returns the factory at runtime, avoiding
    import binding issues where tools import SessionLocal=None at
    module load time before it's initialized.

    Returns:
        Session factory for creating database sessions

    Raises:
        RuntimeError: If database not initialized
    """
    if _session_factory is None:
        error_msg = (
            "Database not initialized. "
            "Call init_db_connection() during startup."
        )
        logger.error("Session factory requested before initialization")
        raise RuntimeError(error_msg)

    return _session_factory


# Exported API
__all__ = [
    "init_db_connection",
    "close_db_connection",
    "get_session_factory",
]
```

### SQLAlchemy Models with pgvector

**File**: `src/models/database.py`

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass
```

**File**: `src/models/your_model.py`

```python
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.database import Base


class CodeChunk(Base):
    """Example model with vector embeddings."""

    __tablename__ = "code_chunks"

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Content
    content: Mapped[str] = mapped_column(String, nullable=False)

    # Vector embedding (768 dimensions for nomic-embed-text)
    embedding: Mapped[Vector | None] = mapped_column(
        Vector(768),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # Indexes
    __table_args__ = (
        # HNSW index for fast vector similarity search
        Index(
            "ix_chunks_embedding_cosine",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
```

### Session Usage in Tools

**Pattern**: Use async context manager with explicit commit

```python
from src.database import get_session_factory

@mcp.tool()
async def your_tool(param: str, ctx: Context | None = None) -> dict[str, Any]:
    """Your tool implementation."""

    # Get session factory and create session
    async with get_session_factory()() as db:
        # Perform database operations
        result = await your_service_function(db, param)

        # CRITICAL: Commit before exiting context
        await db.commit()

    # Session automatically closed here
    return {"result": result}
```

**Why `get_session_factory()()`?**

The double parentheses are intentional:
1. `get_session_factory()` → returns the session maker
2. `()` → calls the session maker to create a session
3. `async with` → uses the session as a context manager

---

## Implementing MCP Resources

MCP Resources provide read-only data that MCP clients can access. FastMCP makes this simple with decorators.

### Basic Resource Pattern

```python
from fastmcp import Context

@mcp.resource("resource://your-server/config")
async def get_config(ctx: Context | None = None) -> str:
    """
    Provide server configuration to MCP clients.

    Returns:
        Configuration as string (JSON, YAML, or plain text)
    """
    config = {
        "version": "0.1.0",
        "features": ["feature1", "feature2"],
        "status": "ready",
    }

    return json.dumps(config, indent=2)
```

### Dynamic Resources

```python
@mcp.resource("resource://your-server/data/{item_id}")
async def get_item(item_id: str, ctx: Context | None = None) -> str:
    """
    Provide dynamic resource based on URI parameter.

    Args:
        item_id: Extracted from URI path
        ctx: FastMCP context
    """
    async with get_session_factory()() as db:
        item = await get_item_from_db(db, item_id)
        await db.commit()

    return json.dumps(item.to_dict())
```

### Resource Listing

```python
@mcp.list_resources()
async def list_resources(ctx: Context | None = None) -> list[dict[str, Any]]:
    """
    List all available resources.

    Returns:
        List of resource descriptors
    """
    return [
        {
            "uri": "resource://your-server/config",
            "name": "Server Configuration",
            "description": "Current server configuration and status",
            "mimeType": "application/json",
        },
        {
            "uri": "resource://your-server/data/{item_id}",
            "name": "Item Data",
            "description": "Get specific item by ID",
            "mimeType": "application/json",
        },
    ]
```

---

## Implementing MCP Tools

MCP Tools are functions that MCP clients can invoke. This is where most of your server logic lives.

### Basic Tool Pattern

**File**: `src/mcp/tools/your_tool.py`

```python
from __future__ import annotations

import logging
import time
from typing import Any

from fastmcp import Context

from src.database import get_session_factory
from src.mcp.server_fastmcp import mcp
from src.services.your_service import your_service_function

logger = logging.getLogger(__name__)


@mcp.tool()
async def your_tool(
    required_param: str,
    optional_param: int = 10,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """
    One-line summary of what this tool does.

    Longer description explaining the tool's purpose, behavior,
    and any important details about how it works.

    Args:
        required_param: Description of required parameter
        optional_param: Description of optional parameter (default: 10)
        ctx: FastMCP context for client logging (injected automatically)

    Returns:
        Dictionary with results:
        {
            "result": "description",
            "count": 42,
            "latency_ms": 123
        }

    Raises:
        ValueError: If input validation fails
        RuntimeError: If operation fails

    Performance:
        Target: <500ms p95 latency
    """
    start_time = time.perf_counter()

    # Dual logging: Context (client) + File (server)
    if ctx:
        await ctx.info(f"Processing: {required_param}")

    logger.info(
        "your_tool called",
        extra={"context": {"required_param": required_param}},
    )

    # Input validation
    try:
        if not required_param or not required_param.strip():
            raise ValueError("required_param cannot be empty")

        if optional_param < 1 or optional_param > 100:
            raise ValueError("optional_param must be between 1 and 100")

    except ValueError:
        raise  # Re-raise validation errors
    except Exception as e:
        logger.error(f"Validation error: {e}")
        raise ValueError(f"Input validation failed: {e}") from e

    # Execute operation with database
    try:
        async with get_session_factory()() as db:
            result = await your_service_function(
                db,
                required_param,
                optional_param,
            )
            await db.commit()

    except Exception as e:
        logger.error(f"Operation failed: {e}", exc_info=True)
        if ctx:
            await ctx.error(f"Operation failed: {str(e)[:100]}")
        raise

    # Calculate latency
    latency_ms = int((time.perf_counter() - start_time) * 1000)

    # Format response
    response: dict[str, Any] = {
        "result": result,
        "count": len(result),
        "latency_ms": latency_ms,
    }

    # Log success
    logger.info(
        "your_tool completed",
        extra={"context": {"latency_ms": latency_ms}},
    )

    if ctx:
        await ctx.info(f"Completed in {latency_ms}ms")

    return response


__all__ = ["your_tool"]
```

### Parameter Validation with Pydantic

For complex validation, use Pydantic models:

```python
from pydantic import BaseModel, Field, field_validator
from pydantic import ValidationError as PydanticValidationError


class ToolInput(BaseModel):
    """Input validation schema."""

    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=100)

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Ensure query doesn't contain invalid characters."""
        if any(char in v for char in ["<", ">", ";"]):
            raise ValueError("Query contains invalid characters")
        return v.strip()


@mcp.tool()
async def validated_tool(
    query: str,
    limit: int = 10,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Tool with Pydantic validation."""

    # Validate with Pydantic
    try:
        validated = ToolInput(query=query, limit=limit)
    except PydanticValidationError as e:
        raise ValueError(f"Invalid input: {e}") from e

    # Use validated data
    async with get_session_factory()() as db:
        result = await search(db, validated.query, validated.limit)
        await db.commit()

    return {"results": result}
```

### Error Handling

**File**: `src/mcp/errors.py`

```python
from typing import Any


class MCPError(Exception):
    """Base exception for MCP-related errors."""

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """Convert error to MCP-compliant error response."""
        error_dict = {"message": self.message}
        if self.code:
            error_dict["code"] = self.code
        if self.details:
            error_dict["details"] = self.details
        return error_dict


class ValidationError(MCPError):
    """Input validation failed."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code="VALIDATION_ERROR", details=details)


class NotFoundError(MCPError):
    """Requested resource not found."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code="NOT_FOUND", details=details)


class OperationError(MCPError):
    """Operation failed."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message, code="OPERATION_ERROR", details=details)
```

**Usage in tools**:

```python
@mcp.tool()
async def get_item(item_id: str, ctx: Context | None = None) -> dict[str, Any]:
    """Get item by ID."""

    try:
        async with get_session_factory()() as db:
            item = await get_item_service(db, item_id)
            await db.commit()
    except ItemNotFoundError as e:
        # Service error → ValueError for MCP
        raise ValueError(f"Item not found: {item_id}") from e
    except Exception as e:
        logger.error(f"Failed to get item: {e}")
        raise

    return item.to_dict()
```

---

## Error Handling & Logging

### Dual Logging Pattern

**CRITICAL**: MCP protocol requires clean stdout/stderr for JSON-RPC communication. All application logs MUST go to file.

**Pattern**:
1. **File Logging** (server diagnostics) → `/tmp/your-server.log`
2. **Context Logging** (client communication) → `ctx.info()`

### File Logging Setup

**File**: `src/mcp/mcp_logging.py`

```python
import logging
import logging.handlers
import sys
from pathlib import Path


def configure_logging(log_file: Path, level: int = logging.INFO) -> None:
    """
    Configure file-only logging.

    CRITICAL: Removes all console handlers to prevent stdout/stderr
    pollution which breaks MCP protocol.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove any existing console handlers
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler):
            if handler.stream in (sys.stdout, sys.stderr):
                root_logger.removeHandler(handler)

    # Add rotating file handler
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=5,
        encoding="utf-8",
    )

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)

    # Suppress external library logs
    logging.getLogger("fastmcp").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get logger for module."""
    return logging.getLogger(name)
```

### Context Logging (Client Communication)

```python
from fastmcp import Context

@mcp.tool()
async def your_tool(param: str, ctx: Context | None = None) -> dict[str, Any]:
    """Tool with client communication."""

    # Progress updates to client
    if ctx:
        await ctx.info("Starting operation...")

    # ... processing ...

    if ctx:
        await ctx.info(f"Processing step 1/3")

    # ... more processing ...

    # Error notification
    if ctx and error_occurred:
        await ctx.error(f"Operation failed: {error_message}")

    # Success notification
    if ctx:
        await ctx.info("Operation completed successfully")

    return result
```

**Context Methods**:
- `await ctx.info(message)` - Info messages to client
- `await ctx.error(message)` - Error messages to client
- `await ctx.warn(message)` - Warning messages to client
- `await ctx.debug(message)` - Debug messages to client

### Structured Logging (Optional)

For production systems, consider JSON structured logging:

```python
import json
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Format log records as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add context if available
        if hasattr(record, "context"):
            log_entry["context"] = record.context

        return json.dumps(log_entry)
```

---

## Testing Strategy

### Test Organization

```
tests/
├── contract/           # MCP protocol compliance
│   ├── test_tool1_contract.py
│   └── test_tool2_contract.py
├── integration/        # End-to-end workflows
│   ├── test_workflow1.py
│   └── test_workflow2.py
└── unit/              # Isolated components
    ├── test_settings.py
    └── test_service.py
```

### Contract Tests (Schema Validation)

Contract tests validate Pydantic schemas BEFORE implementation:

```python
"""Contract tests for your_tool."""

import pytest
from pydantic import BaseModel, Field, ValidationError


class YourToolInput(BaseModel):
    """Input schema for your_tool."""

    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=100)


class YourToolOutput(BaseModel):
    """Output schema for your_tool."""

    results: list[dict[str, str]]
    total_count: int = Field(..., ge=0)
    latency_ms: int = Field(..., ge=0)


@pytest.mark.contract
def test_input_valid_minimal() -> None:
    """Test input schema with minimal required fields."""
    valid_input = YourToolInput(query="test")

    assert valid_input.query == "test"
    assert valid_input.limit == 10  # Default


@pytest.mark.contract
def test_input_empty_query() -> None:
    """Test input validation fails for empty query."""
    with pytest.raises(ValidationError) as exc_info:
        YourToolInput(query="")

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("query",) for error in errors)


@pytest.mark.contract
def test_output_valid() -> None:
    """Test output schema validation."""
    valid_output = YourToolOutput(
        results=[{"key": "value"}],
        total_count=1,
        latency_ms=123,
    )

    assert len(valid_output.results) == 1
    assert valid_output.total_count == 1
```

### Integration Tests

```python
"""Integration tests for your_tool."""

import pytest
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def test_data(tmp_path: Path) -> Path:
    """Create test data."""
    data_file = tmp_path / "test.txt"
    data_file.write_text("test content")
    return data_file


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tool_workflow(
    test_data: Path,
    db_session: AsyncSession,
) -> None:
    """Test complete tool workflow."""
    from src.services.your_service import your_service_function

    # Call service
    result = await your_service_function(
        db_session,
        param="test",
    )

    # Verify results
    assert result is not None
    assert len(result) > 0
```

### Unit Tests

```python
"""Unit tests for settings."""

import pytest
from pydantic import ValidationError
from src.config.settings import Settings


def test_settings_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test settings load with valid configuration."""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://user:pass@localhost:5432/db",
    )

    settings = Settings()

    assert str(settings.database_url).startswith("postgresql+asyncpg://")
    assert settings.db_pool_size == 20


def test_settings_missing_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test validation fails when DATABASE_URL is missing."""
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert "database_url" in str(exc_info.value).lower()
```

### Test Fixtures

```python
"""Shared test fixtures."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
async def db_session() -> AsyncSession:
    """Create test database session."""
    engine = create_async_engine(
        "postgresql+asyncpg://localhost/test_db",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session

    await engine.dispose()
```

### Pytest Configuration

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
asyncio_mode = "auto"

addopts = [
    "--strict-markers",
    "--cov=src",
    "--cov-fail-under=95",
    "-vv",
]

markers = [
    "unit: Unit tests (fast, isolated)",
    "integration: Integration tests (database, services)",
    "contract: Contract/API tests (schema validation)",
    "slow: Slow-running tests (performance benchmarks)",
]
```

### Running Tests

```bash
# All tests
pytest

# Specific category
pytest -m unit
pytest -m integration
pytest -m contract

# Specific file
pytest tests/unit/test_settings.py -v

# With coverage report
pytest --cov-report=html
open htmlcov/index.html
```

---

## Common Pitfalls & Solutions

### 1. Double-Import Problem ⚠️ CRITICAL

**Problem**: Tools registered but MCP client sees zero tools.

**Cause**: Running as `python -m src.mcp.server` loads module twice.

**Solution**: Use wrapper script (`run_server.py`)

```python
# ❌ WRONG - causes double import
python -m src.mcp.server_fastmcp

# ✅ RIGHT - use wrapper
python run_server.py
```

**Detection**:
```bash
# Check Claude Desktop logs
tail -f ~/Library/Logs/Claude/mcp*.log

# Should see tool count > 0
"tools": [...],  # Should have your tools
```

### 2. Stdout/Stderr Pollution ⚠️ CRITICAL

**Problem**: MCP protocol breaks with "Invalid JSON" errors.

**Cause**: `print()` statements or logging to console.

**Solution**: File-only logging

```python
# ❌ WRONG - breaks MCP protocol
print("Debug message")
logging.basicConfig()  # Logs to stderr by default

# ✅ RIGHT - file logging only
logger = logging.getLogger(__name__)
logger.info("Debug message")  # Goes to /tmp/server.log
```

**Detection**:
Check Claude Desktop logs for JSON parsing errors.

### 3. Forgetting to Commit Database Sessions

**Problem**: Changes not persisted to database.

**Cause**: Missing `await db.commit()`.

**Solution**: Always commit before exiting context

```python
# ❌ WRONG - changes rolled back
async with get_session_factory()() as db:
    result = await service_function(db, param)
    # Session closes, rollback happens

# ✅ RIGHT - changes persisted
async with get_session_factory()() as db:
    result = await service_function(db, param)
    await db.commit()  # Persist changes
```

### 4. Not Converting UUIDs to Strings

**Problem**: `Object of type UUID is not JSON serializable`

**Cause**: Returning UUID objects in response.

**Solution**: Convert UUIDs to strings

```python
# ❌ WRONG - UUID not JSON serializable
return {"id": task.id}  # UUID object

# ✅ RIGHT - convert to string
return {"id": str(task.id)}  # String
```

### 5. Missing Context Null Checks

**Problem**: `NoneType has no attribute 'info'`

**Cause**: Calling context methods without checking if None.

**Solution**: Always check before using context

```python
# ❌ WRONG - crashes if ctx is None
await ctx.info("Message")

# ✅ RIGHT - check first
if ctx:
    await ctx.info("Message")
```

### 6. Wrong Exception Types

**Problem**: FastMCP doesn't convert error to MCP format.

**Cause**: Raising custom exceptions.

**Solution**: Raise `ValueError` for user-facing errors

```python
# ❌ WRONG - FastMCP doesn't recognize custom errors
raise CustomNotFoundError(f"Item not found: {id}")

# ✅ RIGHT - convert to ValueError
try:
    result = await get_item(db, id)
except ItemNotFoundError as e:
    raise ValueError(f"Item not found: {id}") from e
```

### 7. Tool Imports at Module Level

**Problem**: Tools not visible to protocol.

**Cause**: Importing tools at top of server file.

**Solution**: Import inside `main()` function

```python
# ❌ WRONG - module-level import
import src.mcp.tools.tool1

def main():
    mcp.run()

# ✅ RIGHT - import inside main()
def main():
    import src.mcp.tools.tool1  # noqa: F401
    mcp.run()
```

### 8. Async Event Loop Conflicts

**Problem**: `RuntimeError: no running event loop`

**Cause**: Running async code before FastMCP starts event loop.

**Solution**: Move async operations to lifespan

```python
# ❌ WRONG - async before event loop
def main():
    asyncio.run(validate_database())  # Creates separate loop
    mcp.run()

# ✅ RIGHT - async in lifespan
@asynccontextmanager
async def lifespan(app: FastMCP):
    await validate_database()  # In FastMCP's event loop
    yield

mcp = FastMCP("server", lifespan=lifespan)
```

### 9. Relative Paths in Claude Config

**Problem**: Server won't start from Claude Desktop.

**Cause**: Using relative or `~` paths in config.

**Solution**: Use absolute paths

```json
{
  "mcpServers": {
    "your-server": {
      "command": "~/.venv/bin/python",  // ❌ WRONG
      "command": "/Users/you/.venv/bin/python",  // ✅ RIGHT
    }
  }
}
```

### 10. Missing Type Annotations

**Problem**: mypy errors, poor IDE support.

**Cause**: Incomplete type hints.

**Solution**: Full type annotations

```python
# ❌ WRONG - missing types
async def tool(param):
    result = {}
    return result

# ✅ RIGHT - complete types
async def tool(
    param: str,
    ctx: Context | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    return result
```

---

## Deployment

### Production Checklist

- [ ] **Environment Variables**: Use `.env` file (not hardcoded)
- [ ] **Database Pooling**: Configure `DB_POOL_SIZE` for expected load
- [ ] **Log Level**: Set to `INFO` (not `DEBUG`)
- [ ] **Log Rotation**: Enabled (100MB, 5 backups)
- [ ] **Error Handling**: Comprehensive try/except blocks
- [ ] **Type Safety**: Pass `mypy --strict`
- [ ] **Tests**: 95% code coverage
- [ ] **Performance**: Meet latency targets

### Environment Setup

```bash
# Production .env
DATABASE_URL=postgresql+asyncpg://user:secure_pass@prod_host:5432/db
DB_POOL_SIZE=50              # Higher for production
DB_MAX_OVERFLOW=20
LOG_LEVEL=INFO               # Not DEBUG
LOG_FILE=/var/log/your-server.log
```

### Process Management

**Option 1: Systemd Service**

```ini
# /etc/systemd/system/your-mcp-server.service
[Unit]
Description=Your MCP Server
After=network.target postgresql.service

[Service]
Type=simple
User=mcp
WorkingDirectory=/opt/your-mcp-server
Environment="PATH=/opt/your-mcp-server/.venv/bin"
ExecStart=/opt/your-mcp-server/.venv/bin/python run_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable your-mcp-server
sudo systemctl start your-mcp-server

# Check status
sudo systemctl status your-mcp-server

# View logs
sudo journalctl -u your-mcp-server -f
```

**Option 2: Docker**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ src/
COPY run_server.py .
COPY .env .

# Run server
CMD ["python", "run_server.py"]
```

```bash
# Build and run
docker build -t your-mcp-server .
docker run -d --name mcp-server \
  -v $(pwd)/.env:/app/.env:ro \
  your-mcp-server
```

### Monitoring

**Health Check**:

```python
# src/health.py
from sqlalchemy import text

async def check_health() -> dict[str, Any]:
    """Health check endpoint."""
    checks = {}

    # Database check
    try:
        async with get_session_factory()() as db:
            await db.execute(text("SELECT 1"))
            checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {e}"

    # Overall status
    checks["status"] = "healthy" if all(
        v == "healthy" for v in checks.values()
    ) else "unhealthy"

    return checks
```

**Log Monitoring**:

```bash
# Monitor errors
tail -f /var/log/your-server.log | grep ERROR

# Monitor specific operations
tail -f /var/log/your-server.log | grep "your_tool"

# Performance metrics (if using JSON logging)
tail -f /var/log/your-server.log | jq 'select(.latency_ms > 500)'
```

---

## MCP Client Integration

### Claude Desktop Configuration

**Config File Location**:
```
~/Library/Application Support/Claude/claude_desktop_config.json
```

**Configuration Example**:

```json
{
  "mcpServers": {
    "your-server": {
      "command": "/path/to/your-project/.venv/bin/python",
      "args": [
        "/path/to/your-project/run_server.py"
      ],
      "cwd": "/path/to/your-project",
      "env": {
        "DATABASE_URL": "postgresql+asyncpg://user:password@localhost:5432/db",
        "LOG_LEVEL": "INFO",
        "LOG_FILE": "/tmp/your-server.log"
      }
    }
  }
}
```

**CRITICAL Requirements**:

1. **Use absolute paths** (no `~`, no relative paths)
2. **Use wrapper script** (`run_server.py`)
3. **Specify all env vars** (not inherited from shell)
4. **Set working directory** (`cwd`)

### Verification

**1. Restart Claude Desktop**:
```bash
killall Claude
open -a Claude
```

**2. Check Tools Menu**:
- Look for tools menu (🔨 icon)
- Should see "your-server" with your tools listed

**3. Check Logs**:
```bash
# Server logs
tail -f /tmp/your-server.log

# Claude Desktop logs
tail -f ~/Library/Logs/Claude/mcp*.log
```

**Expected server log output**:
```
INFO: Starting FastMCP server...
INFO: 3 tools registered:
  - tool1
  - tool2
  - tool3
INFO: Server ready for connections
```

### Troubleshooting

**Issue**: Server won't start

**Check**:
1. Paths are absolute
2. Python executable exists
3. Dependencies installed
4. Database accessible

**Issue**: No tools visible

**Check**:
1. Using wrapper script (`run_server.py`)
2. Tools imported in `main()`
3. Check Claude Desktop logs for errors
4. Check server logs for import errors

**Issue**: "Invalid JSON" errors

**Check**:
1. No `print()` statements in code
2. Logging configured for file-only
3. No console handlers in logging config

---

## Reference Implementation

### Project: Codebase MCP Server

**Location**: `/Users/cliffclarke/Claude_Code/codebase-mcp`

**Description**: Production-grade MCP server that indexes code repositories into PostgreSQL with pgvector for semantic search.

### Key Files to Review

**Server Setup**:
- `run_server.py` - Wrapper script (critical for avoiding double-import)
- `src/mcp/server_fastmcp.py` - FastMCP server initialization
- `src/database.py` - Database connection management with session factory

**Tool Implementations**:
- `src/mcp/tools/indexing.py` - Repository indexing (long-running operation)
- `src/mcp/tools/search.py` - Semantic search (performance-critical)
- `src/mcp/tools/tasks.py` - CRUD operations

**Database Models**:
- `src/models/code_chunk.py` - Model with pgvector embeddings
- `src/models/repository.py` - Repository model
- `src/models/task.py` - Task model

**Configuration**:
- `src/config/settings.py` - Pydantic Settings with validation
- `.env.example` - Environment variable template
- `pyproject.toml` - Dependencies and tool configuration

**Testing**:
- `tests/contract/` - MCP protocol compliance tests
- `tests/integration/` - End-to-end workflow tests
- `tests/unit/` - Isolated component tests

### Architecture Decisions

**Why FastMCP over MCP SDK directly?**
- Decorator-based API is cleaner
- Automatic schema generation from type hints
- Built-in transport handling
- Better developer experience

**Why wrapper script?**
- Solves double-import problem
- Single module instance guaranteed
- Tools properly registered and visible

**Why file-only logging?**
- MCP protocol requires clean stdout/stderr
- Dual logging provides best debugging experience
- Context logging for client communication

**Why async throughout?**
- Database operations are async (asyncpg)
- MCP tools must be async
- Better performance under load

**Why Pydantic for config?**
- Type-safe configuration
- Automatic validation
- Great error messages
- Environment variable support

### Performance Characteristics

**From the reference implementation**:

- **Repository Indexing**: <60 seconds for 10,000 files
- **Semantic Search**: <500ms p95 latency
- **Task Operations**: <200ms p95 latency
- **Database Pool**: 20 connections + 10 overflow
- **Connection Lifecycle**: 1 hour recycle

### Constitutional Principles

The reference implementation follows strict principles:

1. **Simplicity**: Focus on core functionality
2. **Protocol Compliance**: Clean stdio, no pollution
3. **Performance**: Meet latency targets
4. **Production Quality**: Comprehensive error handling
5. **Type Safety**: mypy --strict compliance
6. **TDD**: Tests before code
7. **FastMCP Foundation**: Use FastMCP for all MCP

### Git History Reference

**Critical Bug Fixes** (commits to review):

- `8f3161a` - Wrapper script to fix double-import
- `4c167f0` - Session factory to fix import binding
- `6ef7dd0` - Remove async pre-flight validation
- `888f290` - Archive session artifacts

### Contact & Support

**Reference Implementation**:
- Repository: `/Users/cliffclarke/Claude_Code/codebase-mcp`
- Documentation: `docs/ARCHITECTURE.md`, `docs/troubleshooting.md`

**FastMCP Resources**:
- GitHub: https://github.com/jlowin/fastmcp
- MCP Specification: https://modelcontextprotocol.io/

---

## Summary

### Quick Start Checklist

- [ ] Set up project structure
- [ ] Create `pyproject.toml` with dependencies
- [ ] Implement `src/mcp/server_fastmcp.py`
- [ ] Create `run_server.py` wrapper (CRITICAL!)
- [ ] Configure file-only logging
- [ ] Implement your first tool
- [ ] Write contract tests
- [ ] Configure Claude Desktop
- [ ] Test end-to-end

### Key Takeaways

1. **Use wrapper script** to avoid double-import
2. **File-only logging** to preserve MCP protocol
3. **Lifespan pattern** for initialization
4. **Session factory** for database access
5. **Dual logging** for debugging
6. **Contract tests** before implementation
7. **Type safety** with mypy --strict
8. **Absolute paths** in Claude Desktop config

### Common Commands

```bash
# Development
python run_server.py              # Run server
pytest                            # Run tests
mypy src                          # Type check
ruff check --fix src             # Lint and fix

# Production
python run_server.py              # Run server
tail -f /tmp/server.log          # Monitor logs

# Claude Desktop
killall Claude && open -a Claude  # Restart
tail -f ~/Library/Logs/Claude/mcp*.log  # Check logs
```

### When You Get Stuck

1. **Check logs**: Server log + Claude Desktop log
2. **Review this guide**: Common pitfalls section
3. **Check reference implementation**: See how it's done
4. **Test incrementally**: Add one feature at a time
5. **Use type checker**: mypy catches many issues early

---

**Guide Version**: 1.0
**Last Updated**: 2025-10-08
**Based On**: Codebase MCP Server (production implementation)

**This guide saves you 8-20 hours** of debugging FastMCP issues. Follow the patterns, avoid the pitfalls, and build production-grade MCP servers with confidence.
