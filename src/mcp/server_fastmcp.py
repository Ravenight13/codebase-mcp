"""FastMCP server implementation for Codebase MCP Server.

This module implements the MCP server using the FastMCP framework,
replacing the custom protocol implementation with a standardized approach.

Features:
- FastMCP framework initialization
- Stdio transport for Claude Desktop integration
- Tool registration via decorators
- Automatic schema generation from Pydantic models
- Dual logging pattern (Context for client, file for server)
- Context injection for logging

Constitutional Compliance:
- Principle III: Protocol Compliance (stdio transport, no stdout/stderr pollution)
- Principle V: Production Quality (startup validation, error handling)
- Principle VIII: Type Safety (full type hints, mypy --strict)
- Principle XI: FastMCP Foundation (FastMCP as standard MCP interface)
"""

from __future__ import annotations

import asyncio
import logging
import logging.handlers
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncGenerator

from fastmcp import FastMCP

if TYPE_CHECKING:
    from src.connection_pool.manager import ConnectionPoolManager

# ==============================================================================
# Configure File Logging (separate from MCP protocol)
# ==============================================================================

# Dual Logging Pattern:
# 1. Context logging (ctx.info()) -> MCP client (Claude Desktop)
# 2. Python logging -> /tmp/codebase-mcp.log (server persistence)

LOG_FILE = Path("/tmp/codebase-mcp.log")

# Create logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        # File handler for persistent logs
        logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        ),
    ],
)

# Get logger for this module
logger = logging.getLogger(__name__)

# Suppress external library logs from polluting our log file
logging.getLogger("fastmcp").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("asyncpg").setLevel(logging.WARNING)

logger.info("=" * 80)
logger.info("FastMCP Server Initialization")
logger.info(f"Log file: {LOG_FILE}")
logger.info("=" * 80)

# ==============================================================================
# Module-Level Pool Manager and Services (for tool/resource access)
# ==============================================================================

# Global pool manager instance (initialized by lifespan)
_pool_manager: ConnectionPoolManager | None = None

# Global service instances (initialized by lifespan)
_health_service: Any = None  # HealthService (avoid circular import)
_metrics_service: Any = None  # MetricsService


def get_pool_manager() -> ConnectionPoolManager:
    """Get the initialized connection pool manager.

    This function provides access to the global pool manager instance for
    MCP tools to acquire database connections.

    Returns:
        ConnectionPoolManager: Initialized pool manager instance

    Raises:
        RuntimeError: If pool manager not initialized (call initialize() during startup)

    Example:
        >>> # In MCP tool:
        >>> from src.mcp.server_fastmcp import get_pool_manager
        >>> pool_manager = get_pool_manager()
        >>> async with pool_manager.acquire() as conn:
        ...     result = await conn.fetchval("SELECT 1")
    """
    if _pool_manager is None:
        raise RuntimeError(
            "Connection pool manager not initialized. "
            "This is a server lifecycle issue - the pool should be initialized in lifespan."
        )
    return _pool_manager


def get_health_service() -> Any:  # Returns HealthService
    """Get the initialized health service.

    This function provides access to the global health service instance for
    MCP resources to perform health checks.

    Returns:
        HealthService: Initialized health service instance

    Raises:
        RuntimeError: If health service not initialized

    Example:
        >>> from src.mcp.server_fastmcp import get_health_service
        >>> health_service = get_health_service()
        >>> response = await health_service.check_health()
    """
    if _health_service is None:
        raise RuntimeError(
            "Health service not initialized. "
            "This is a server lifecycle issue - the service should be initialized in lifespan."
        )
    return _health_service


def get_metrics_service() -> Any:  # Returns MetricsService
    """Get the initialized metrics service.

    This function provides access to the global metrics service instance for
    MCP resources to collect and export metrics.

    Returns:
        MetricsService: Initialized metrics service instance

    Raises:
        RuntimeError: If metrics service not initialized

    Example:
        >>> from src.mcp.server_fastmcp import get_metrics_service
        >>> metrics_service = get_metrics_service()
        >>> metrics_service.increment_counter("requests_total", "Total requests")
    """
    if _metrics_service is None:
        raise RuntimeError(
            "Metrics service not initialized. "
            "This is a server lifecycle issue - the service should be initialized in lifespan."
        )
    return _metrics_service


# ==============================================================================
# FastMCP Lifespan (Connection Pool Initialization)
# ==============================================================================


@asynccontextmanager
async def lifespan(app: FastMCP) -> AsyncGenerator[None, None]:
    """Lifespan context manager for FastMCP server.

    Manages server startup and shutdown lifecycle:
    - Startup: Initialize session manager, connection pool (blocking to ensure ready)
    - Shutdown: Close connection pool, stop session manager gracefully

    Blocking Pattern:
    - Wait for pool to be ready before accepting connections from Claude Desktop
    - Ensures tools can access DB immediately when called
    - Prevents race conditions with early tool invocations

    Constitutional Compliance:
    - Principle V: Production Quality (proper initialization order, error handling)
    - Principle VIII: Type Safety (full type hints, mypy --strict)
    - Principle IV: Performance (<2s initialization, <10ms health checks)

    Args:
        app: FastMCP server instance

    Yields:
        None (context manager pattern)

    Raises:
        RuntimeError: If connection pool or session manager initialization fails
    """
    global _pool_manager, _health_service, _metrics_service

    # Import connection pool management, services, and session manager
    from src.auto_switch.session_context import get_session_context_manager
    from src.config.settings import get_settings
    from src.connection_pool.config import PoolConfig
    from src.connection_pool.manager import ConnectionPoolManager
    from src.services.health_service import HealthService
    from src.services.metrics_service import MetricsService

    # Create connection pool manager instance
    pool_manager = ConnectionPoolManager()

    # Get session context manager instance
    session_mgr = get_session_context_manager()

    # Startup: Initialize session manager and connection pool
    # (blocking to ensure ready before serving)
    try:
        logger.info("Starting codebase-mcp server...")
        sys.stderr.write("INFO: Starting codebase-mcp server...\n")

        # Start session manager first (enables per-session isolation)
        await session_mgr.start()
        logger.info("Session manager started")
        sys.stderr.write("INFO: Session manager started\n")

        # Initialize connection pool
        logger.info("Initializing connection pool...")
        sys.stderr.write("INFO: Initializing connection pool...\n")

        # Load settings and create pool configuration
        settings = get_settings()
        pool_config = PoolConfig(
            min_size=settings.db_pool_size,
            max_size=settings.db_pool_size + settings.db_max_overflow,
            timeout=30.0,
            command_timeout=60.0,
            max_queries=50000,
            max_idle_time=300.0,  # 5 minutes
            max_connection_lifetime=3600.0,  # 1 hour
            leak_detection_timeout=30.0,
            enable_leak_detection=True,
            database_url=str(settings.database_url),
        )

        # Initialize pool (BLOCKING - wait for completion)
        await pool_manager.initialize(pool_config)

        # Store pool_manager in module-level variable for tool access
        _pool_manager = pool_manager

        # Initialize health service
        logger.info("Initializing health service...")
        _health_service = HealthService(pool_manager)
        logger.info("✓ Health service initialized successfully")

        # Initialize metrics service
        logger.info("Initializing metrics service...")
        _metrics_service = MetricsService()
        logger.info("✓ Metrics service initialized successfully")

        logger.info("✓ All services initialized successfully")
        logger.info("Server startup complete")
        sys.stderr.write("INFO: All services initialized successfully\n")
        sys.stderr.write("INFO: Server startup complete\n")

    except Exception as e:
        logger.critical(
            f"Failed to initialize server: {e}",
            exc_info=True,
        )
        sys.stderr.write(f"FATAL: Server initialization failed: {e}\n")
        sys.stderr.write("FIX: Check PostgreSQL is running and DATABASE_URL is correct\n")
        raise RuntimeError(f"Server initialization failed: {e}") from e

    # Yield control to FastMCP server (tools are visible NOW)
    yield

    # Shutdown: Close connection pool and stop session manager gracefully
    try:
        logger.info("Shutting down codebase-mcp server...")
        sys.stderr.write("INFO: Shutting down codebase-mcp server...\n")

        # Close connection pool first
        logger.info("Closing connection pool gracefully...")
        await pool_manager.shutdown(timeout=30.0)
        logger.info("Connection pool closed successfully")

        # Stop session manager
        await session_mgr.stop()
        logger.info("Session manager stopped")
        sys.stderr.write("INFO: Session manager stopped\n")

        logger.info("Server shutdown complete")
        sys.stderr.write("INFO: Server shutdown complete\n")

    except Exception as e:
        logger.error(
            f"Error during shutdown: {e}",
            exc_info=True,
        )


# ==============================================================================
# Initialize FastMCP Server
# ==============================================================================

mcp = FastMCP("codebase-mcp", version="0.1.0", lifespan=lifespan)

# Export for tool and resource access
__all__ = ["mcp", "get_pool_manager", "get_health_service", "get_metrics_service"]

# ==============================================================================
# Main Entry Point
# ==============================================================================

def main() -> None:
    """Main entry point for FastMCP server.

    Runs the server with stdio transport for Claude Desktop compatibility.

    Startup sequence:
    1. Import tool modules FIRST (inside main()) to register with correct mcp instance
    2. Pre-flight validation: verify tools are registered
    3. Log diagnostic information to file and stderr
    4. Start FastMCP server with stdio transport
    5. Handle graceful shutdown on errors

    CRITICAL: Tool imports MUST happen inside main() to avoid double-import issue:
    - When run as `python -m src.mcp.server_fastmcp`, module loads as `__main__`
    - Module-level imports create tools on `__main__.mcp` instance
    - But FastMCP protocol handlers look at `src.mcp.server_fastmcp.mcp` instance
    - Result: Tools registered but protocol returns empty tools list
    - Solution: Import tools inside main() so they register with the active mcp instance

    Logging behavior:
    - File logging: All server events -> /tmp/codebase-mcp.log
    - Stderr logging: Startup status -> Claude Desktop debugging
    - Context logging: Tool execution events -> MCP client (via ctx.info())
    """
    # CRITICAL: Import tools FIRST, inside main(), so they register with the
    # correct mcp instance (the one that will be used by the protocol handlers)
    try:
        logger.info("Importing tool modules...")
        import src.mcp.tools.background_indexing  # noqa: F401
        import src.mcp.tools.project  # noqa: F401
        import src.mcp.tools.search  # noqa: F401
        logger.info("✓ Tool modules imported successfully")

        logger.info("Importing resource modules...")
        import src.mcp.health  # noqa: F401
        import src.mcp.resources.health_endpoint  # noqa: F401
        import src.mcp.resources.metrics_endpoint  # noqa: F401
        logger.info("✓ Resource modules imported successfully")
    except ImportError as e:
        logger.critical(f"FATAL: Failed to import tool modules: {e}", exc_info=True)
        sys.stderr.write(f"FATAL: Failed to import tool modules: {e}\n")
        sys.stderr.write("FIX: Check that all dependencies are installed (uv sync)\n")
        sys.stderr.write("LOG: See /tmp/codebase-mcp.log for details\n")
        sys.exit(1)

    try:
        logger.info("=" * 80)
        logger.info("FastMCP Server Startup")
        logger.info("=" * 80)

        # List expected tools and resources for diagnostics
        expected_tools = [
            "get_indexing_status",
            "index_repository",
            "search_code",
            "start_indexing_background",
        ]
        expected_resources = [
            "health://connection-pool",
            "health://status",
            "metrics://prometheus",
        ]

        logger.info(f"✓ Tool modules imported successfully")
        logger.info(f"  Expected tools: {', '.join(expected_tools)}")
        logger.info(f"  Expected resources: {', '.join(expected_resources)}")
        logger.info("Starting FastMCP server with stdio transport...")

        sys.stderr.write("INFO: Starting FastMCP server...\n")
        sys.stderr.write(f"INFO: {len(expected_tools)} tools registered:\n")
        for name in expected_tools:
            sys.stderr.write(f"  - {name}\n")
        sys.stderr.write(f"INFO: {len(expected_resources)} resources registered:\n")
        for uri in expected_resources:
            sys.stderr.write(f"  - {uri}\n")
        sys.stderr.write("INFO: Server ready for connections\n")

        # Start server - FastMCP handles protocol internally
        mcp.run()

    except Exception as e:
        # Unexpected errors during startup
        logger.critical(f"Server startup failed: {e}", exc_info=True)
        sys.stderr.write(f"FATAL: Server startup failed: {e}\n")
        sys.stderr.write(f"LOG: See /tmp/codebase-mcp.log for details\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
