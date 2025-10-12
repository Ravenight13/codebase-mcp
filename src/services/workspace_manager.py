"""Project workspace provisioning and validation service.

Manages the lifecycle of project workspaces, including:
- Automatic schema provisioning on first use
- Schema existence validation with in-memory caching
- Table structure creation using SQLAlchemy metadata
- Workspace registration in global registry

Constitutional Compliance:
- Principle V: Production quality (comprehensive error handling, caching optimization)
- Principle VIII: Pydantic-based type safety (mypy --strict compliance)
- Principle IV: Performance guarantees (schema existence caching, efficient queries)
- Principle XVI: Security-first design (validated identifiers, parameterized queries)

Functional Requirements:
- FR-009: System MUST provision isolated PostgreSQL schemas per project
- FR-010: System MUST auto-provision workspace on first project use
- FR-011: System MUST track workspace creation timestamps

Key Features:
- Auto-provisioning: Creates schema + tables on first use
- Caching: In-memory schema existence cache for performance
- Idempotent: Safe to call ensure_workspace_exists multiple times
- Security: Validates project identifiers before any database operations
- Error handling: Clear permission errors with actionable suggestions
"""

from __future__ import annotations

import logging
from typing import Final

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from src.models.database import Base
from src.models.project_identifier import ProjectIdentifier

logger: Final[logging.Logger] = logging.getLogger(__name__)


class ProjectWorkspaceManager:
    """Manage project workspace provisioning and validation.

    This service handles the complete workspace lifecycle:
    1. Validate project identifier format (prevents SQL injection)
    2. Check if PostgreSQL schema exists (cached for performance)
    3. Create schema + table structure if needed (one-time operation)
    4. Register workspace in global registry (project_registry.workspace_config)

    Thread Safety:
        This class is thread-safe. The schema existence cache is a set that
        can be safely modified by multiple async tasks (GIL protection).

    Example Usage:
        >>> engine = create_engine("postgresql+asyncpg://localhost/codebase_mcp")
        >>> manager = ProjectWorkspaceManager(engine)
        >>> schema_name = await manager.ensure_workspace_exists("client-a")
        >>> print(schema_name)
        'project_client_a'

        >>> # Second call uses cache (no database query)
        >>> schema_name = await manager.ensure_workspace_exists("client-a")

    Attributes:
        engine: SQLAlchemy async engine for database operations
        _schema_cache: In-memory set of known schema names (performance optimization)
    """

    def __init__(self, engine: AsyncEngine) -> None:
        """Initialize workspace manager with database engine.

        Args:
            engine: Configured AsyncEngine instance for PostgreSQL operations
        """
        self.engine: AsyncEngine = engine
        self._schema_cache: set[str] = set()

    async def ensure_workspace_exists(self, project_id: str) -> str:
        """Ensure project workspace exists, creating if necessary.

        This is the main entry point for workspace provisioning. It performs:
        1. Project identifier validation (raises ValueError if invalid)
        2. Schema existence check (cached for performance)
        3. Schema + table creation if needed (idempotent)
        4. Workspace registration in global registry

        Args:
            project_id: Project identifier string (will be validated)
                       Format: lowercase alphanumeric with hyphens
                       Examples: "client-a", "frontend-app", "my-project-123"

        Returns:
            PostgreSQL schema name (e.g., "project_client_a")

        Raises:
            ValueError: If project_id format is invalid (from ProjectIdentifier)
            PermissionError: If database user lacks CREATE SCHEMA permission
                            Includes actionable GRANT command in error message
            Exception: For other database errors (connection failures, etc.)

        Example:
            >>> manager = ProjectWorkspaceManager(engine)
            >>> # First call: validates, creates schema, registers workspace
            >>> schema = await manager.ensure_workspace_exists("client-a")
            >>> # Second call: validates, returns cached schema name
            >>> schema = await manager.ensure_workspace_exists("client-a")

        Performance:
            - First call: ~50-100ms (schema creation + table creation)
            - Subsequent calls: <1ms (cache hit, no database query)
        """
        # Validate identifier (raises ValueError if invalid format)
        # This is SECURITY-CRITICAL: prevents SQL injection attacks
        identifier = ProjectIdentifier(value=project_id)
        schema_name = identifier.to_schema_name()

        # Check if schema exists (cached for performance)
        if await self._schema_exists(schema_name):
            logger.debug(f"Workspace exists (cached): {schema_name}")
            return schema_name

        # Create schema + tables (one-time operation)
        try:
            await self._create_schema(schema_name)
            await self._register_workspace(project_id, schema_name)
            self._schema_cache.add(schema_name)
            logger.info(
                f"Provisioned new workspace: {schema_name} for project: {project_id}"
            )
        except Exception as e:
            # Handle permission errors with actionable guidance
            error_msg_lower = str(e).lower()
            if "permission denied" in error_msg_lower or "must be owner" in error_msg_lower:
                raise PermissionError(
                    f"Failed to create schema '{schema_name}'. "
                    f"Database user lacks CREATE SCHEMA permission.\n\n"
                    f"Suggested action:\n"
                    f"  GRANT CREATE ON DATABASE codebase_mcp TO <current_user>;\n\n"
                    f"Original error: {e}"
                ) from e
            raise

        return schema_name

    async def _schema_exists(self, schema_name: str) -> bool:
        """Check if PostgreSQL schema exists (with caching).

        This method uses a two-tier strategy:
        1. Check in-memory cache first (instant, no database query)
        2. Query information_schema.schemata if not cached

        Args:
            schema_name: PostgreSQL schema name (e.g., "project_client_a")

        Returns:
            True if schema exists, False otherwise

        Performance:
            - Cache hit: <1ms (no database query)
            - Cache miss: ~5-10ms (single SELECT query)

        Thread Safety:
            This method is thread-safe. Cache reads/writes are atomic operations
            protected by the GIL in CPython.
        """
        # Check cache first (performance optimization)
        if schema_name in self._schema_cache:
            return True

        # Query information_schema if not cached
        async with self.engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT 1 FROM information_schema.schemata "
                    "WHERE schema_name = :schema_name"
                ),
                {"schema_name": schema_name},
            )

            exists = result.scalar() is not None
            if exists:
                # Add to cache for future calls
                self._schema_cache.add(schema_name)
                logger.debug(f"Schema exists (database query): {schema_name}")

            return exists

    async def _create_schema(self, schema_name: str) -> None:
        """Create PostgreSQL schema with table structure.

        This method performs:
        1. Enable pgvector extension (required for embeddings)
        2. CREATE SCHEMA IF NOT EXISTS (idempotent)
        3. SET search_path (ensures tables created in correct schema)
        4. Create all tables using SQLAlchemy metadata (Base.metadata.create_all)

        Args:
            schema_name: PostgreSQL schema name (e.g., "project_client_a")

        Raises:
            PermissionError: If user lacks CREATE SCHEMA permission
            Exception: For other database errors

        Security:
            This method uses validated schema names only (from ProjectIdentifier).
            Schema names are constructed from validated project identifiers and
            cannot contain SQL injection characters.

        Performance:
            - pgvector extension: ~5-10ms (cached if already exists)
            - Schema creation: ~10-20ms
            - Table creation: ~30-50ms (depends on number of tables)
            - Total: ~50-100ms
        """
        async with self.engine.begin() as conn:
            # Enable pgvector extension globally (required for embedding VECTOR type)
            # Must be done before changing search_path
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public"))
            logger.debug("Ensured pgvector extension exists in public schema")

            # Create schema (idempotent)
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
            logger.debug(f"Created schema: {schema_name}")

            # Set search_path for table creation
            # Include public schema for pgvector types
            await conn.execute(text(f"SET search_path TO {schema_name}, public"))

            # Create all tables using SQLAlchemy metadata
            # Base.metadata contains all table definitions from models
            await conn.run_sync(Base.metadata.create_all)
            logger.debug(f"Created tables in schema: {schema_name}")

    async def _register_workspace(self, project_id: str, schema_name: str) -> None:
        """Register workspace in global registry (project_registry.workspace_config).

        This method inserts the workspace configuration into the global registry
        table, allowing other services to discover the workspace schema name
        from the project identifier.

        Args:
            project_id: Validated project identifier (e.g., "client-a")
            schema_name: PostgreSQL schema name (e.g., "project_client_a")

        Notes:
            - Uses ON CONFLICT DO NOTHING (idempotent)
            - created_at timestamp is auto-generated by PostgreSQL DEFAULT NOW()
            - metadata field defaults to empty JSON object '{}'::jsonb

        Performance:
            - INSERT operation: ~5-10ms
            - Conflict detection: ~1-2ms (if duplicate)
        """
        async with self.engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO project_registry.workspace_config "
                    "(project_id, schema_name, created_at, metadata) "
                    "VALUES (:project_id, :schema_name, NOW(), '{}'::jsonb) "
                    "ON CONFLICT (project_id) DO NOTHING"
                ),
                {"project_id": project_id, "schema_name": schema_name},
            )
            logger.debug(
                f"Registered workspace: project_id={project_id}, schema_name={schema_name}"
            )
