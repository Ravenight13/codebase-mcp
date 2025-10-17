#!/usr/bin/env python3
"""Setup script to create codebase-mcp project in registry.

This script:
1. Creates the codebase-mcp project in the registry
2. Provisions the project database (cb_proj_codebase_mcp_*)
3. Updates .codebase-mcp/config.json with project info

Run once to initialize the codebase-mcp project itself.
"""

import asyncio
import json
import uuid
from pathlib import Path

import asyncpg


async def main() -> None:
    """Create codebase-mcp project and provision database."""

    # Generate project UUID
    project_uuid = str(uuid.uuid4())
    project_id_short = project_uuid.replace("-", "")[:8]

    # Project details
    project_name = "codebase-mcp"
    project_description = "Codebase MCP Server - Semantic code search for AI assistants"
    database_name = f"cb_proj_codebase_mcp_{project_id_short}"

    print(f"Creating project: {project_name}")
    print(f"UUID: {project_uuid}")
    print(f"Database: {database_name}")
    print()

    # 1. Insert into registry
    print("1. Registering project in registry database...")
    registry_conn = await asyncpg.connect(
        host="localhost",
        database="codebase_mcp_registry",
        user="cliffclarke",
    )

    try:
        await registry_conn.execute(
            """
            INSERT INTO projects (id, name, description, database_name, metadata)
            VALUES ($1, $2, $3, $4, $5::jsonb)
            ON CONFLICT (name) DO UPDATE
            SET description = EXCLUDED.description,
                database_name = EXCLUDED.database_name,
                metadata = EXCLUDED.metadata
            """,
            project_uuid,
            project_name,
            project_description,
            database_name,
            json.dumps({"environment": "development", "owner": "cliffclarke"})
        )
        print("   ✓ Project registered")
    finally:
        await registry_conn.close()

    # 2. Create database
    print("2. Creating project database...")
    postgres_conn = await asyncpg.connect(
        host="localhost",
        database="postgres",
        user="cliffclarke",
    )

    try:
        await postgres_conn.execute(f'CREATE DATABASE "{database_name}"')
        print(f"   ✓ Database created: {database_name}")
    except asyncpg.DuplicateDatabaseError:
        print(f"   ℹ Database already exists: {database_name}")
    finally:
        await postgres_conn.close()

    # 3. Initialize schema
    print("3. Initializing project database schema...")
    project_conn = await asyncpg.connect(
        host="localhost",
        database=database_name,
        user="cliffclarke",
    )

    try:
        # Read and execute schema SQL
        schema_file = Path(__file__).parent / "init_project_schema.sql"
        with open(schema_file) as f:
            sql = f.read()

        await project_conn.execute(sql)
        print("   ✓ Schema initialized (repositories, code_files, code_chunks)")
    finally:
        await project_conn.close()

    # 4. Update config file
    print("4. Updating .codebase-mcp/config.json...")
    config_dir = Path("/Users/cliffclarke/Claude_Code/codebase-mcp/.codebase-mcp")
    config_dir.mkdir(exist_ok=True)

    config_path = config_dir / "config.json"
    config = {
        "version": "1.0",
        "project": {
            "name": project_name,
            "id": project_uuid
        },
        "auto_switch": True,
        "strict_mode": False,
        "description": project_description
    }

    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"   ✓ Config file updated: {config_path}")

    print()
    print("=" * 60)
    print("✅ Setup Complete!")
    print("=" * 60)
    print(f"Project: {project_name}")
    print(f"Database: {database_name}")
    print(f"Config: {config_path}")
    print()
    print("Next steps:")
    print("1. Restart MCP server (if running)")
    print("2. Call set_working_directory() to activate this project")
    print("3. Use index_repository() to index code")


if __name__ == "__main__":
    asyncio.run(main())
