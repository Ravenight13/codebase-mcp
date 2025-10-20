#!/usr/bin/env python3
"""Find databases that exist but are not tracked in any registry.

This script identifies databases that exist in PostgreSQL but are not
registered in any of the three registry databases:
- codebase_mcp_registry
- workflow_mcp_registry
- workflow_registry

Usage:
    python scripts/find_untracked_databases.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import asyncpg

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


async def create_simple_pool(database_name: str) -> asyncpg.Pool:
    """
    Create a simple connection pool for a database.

    Args:
        database_name: Name of the database to connect to

    Returns:
        AsyncPG connection pool
    """
    return await asyncpg.create_pool(
        host="localhost",
        database=database_name,
        min_size=1,
        max_size=3,
    )


async def get_all_databases(pool: asyncpg.Pool) -> set[str]:
    """
    Query PostgreSQL to get list of all existing databases.

    Args:
        pool: AsyncPG connection pool

    Returns:
        Set of database names that exist in PostgreSQL
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT datname FROM pg_database WHERE datistemplate = false"
        )
        return {row["datname"] for row in rows}


async def get_tracked_databases_from_registry(
    pool: asyncpg.Pool, registry_name: str
) -> set[str]:
    """
    Get all database names tracked in a registry.

    Args:
        pool: AsyncPG connection pool for registry
        registry_name: Name of the registry for display

    Returns:
        Set of database names tracked in this registry
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT database_name FROM projects")
        databases = {row["database_name"] for row in rows}
        print(f"   • {registry_name}: {len(databases)} databases tracked")
        return databases


async def main() -> None:
    """Main analysis workflow."""
    print("=" * 80)
    print("Untracked Database Finder")
    print("=" * 80)

    try:
        # Get all databases
        print("\n1. Querying PostgreSQL for all databases...")
        postgres_pool = await create_simple_pool("postgres")
        all_databases = await get_all_databases(postgres_pool)
        await postgres_pool.close()
        print(f"   ✓ Found {len(all_databases)} total databases")

        # System/template databases to exclude
        system_databases = {
            "postgres",
            "template0",
            "template1",
        }

        # Registry databases themselves
        registry_databases = {
            "codebase_mcp_registry",
            "workflow_mcp_registry",
            "workflow_registry",
        }

        print("\n2. Fetching tracked databases from registries...")
        tracked_databases: set[str] = set()

        # Get tracked databases from codebase_mcp_registry
        try:
            pool = await create_simple_pool("codebase_mcp_registry")
            tracked = await get_tracked_databases_from_registry(
                pool, "codebase_mcp_registry"
            )
            tracked_databases.update(tracked)
            await pool.close()
        except Exception as e:
            print(f"   ✗ Failed to query codebase_mcp_registry: {e}")

        # Get tracked databases from workflow_mcp_registry
        try:
            pool = await create_simple_pool("workflow_mcp_registry")
            tracked = await get_tracked_databases_from_registry(
                pool, "workflow_mcp_registry"
            )
            tracked_databases.update(tracked)
            await pool.close()
        except Exception as e:
            print(f"   ✗ Failed to query workflow_mcp_registry: {e}")

        # Get tracked databases from workflow_registry
        try:
            pool = await create_simple_pool("workflow_registry")
            tracked = await get_tracked_databases_from_registry(
                pool, "workflow_registry"
            )
            tracked_databases.update(tracked)
            await pool.close()
        except Exception as e:
            print(f"   ✗ Failed to query workflow_registry: {e}")

        print(f"\n   ✓ Total tracked databases across all registries: {len(tracked_databases)}")

        # Find untracked databases
        print("\n3. Identifying untracked databases...")

        # Exclude system databases and registries themselves
        exclude_databases = system_databases | registry_databases

        # Find databases that exist but aren't tracked and aren't system/registry databases
        untracked_databases = all_databases - tracked_databases - exclude_databases

        if not untracked_databases:
            print("   ✓ No untracked databases found! All databases are properly registered.")
        else:
            print(f"   ⚠ Found {len(untracked_databases)} untracked databases:")
            print()

            # Sort databases by prefix for better organization
            sorted_databases = sorted(untracked_databases)

            # Group by prefix
            cb_proj = [db for db in sorted_databases if db.startswith("cb_proj_")]
            wf_proj = [db for db in sorted_databases if db.startswith("wf_proj_")]
            other = [db for db in sorted_databases if not db.startswith(("cb_proj_", "wf_proj_"))]

            if cb_proj:
                print(f"   Codebase-MCP project databases (cb_proj_*): {len(cb_proj)}")
                for db in cb_proj[:10]:
                    print(f"     • {db}")
                if len(cb_proj) > 10:
                    print(f"     ... and {len(cb_proj) - 10} more")
                print()

            if wf_proj:
                print(f"   Workflow-MCP project databases (wf_proj_*): {len(wf_proj)}")
                for db in wf_proj[:10]:
                    print(f"     • {db}")
                if len(wf_proj) > 10:
                    print(f"     ... and {len(wf_proj) - 10} more")
                print()

            if other:
                print(f"   Other databases: {len(other)}")
                for db in other:
                    print(f"     • {db}")
                print()

        # Summary
        print("=" * 80)
        print("Summary")
        print("=" * 80)
        print(f"Total databases: {len(all_databases)}")
        print(f"System databases: {len(system_databases)}")
        print(f"Registry databases: {len(registry_databases)}")
        print(f"Tracked databases: {len(tracked_databases)}")
        print(f"Untracked databases: {len(untracked_databases)}")
        print("=" * 80)

        # Detailed breakdown
        if untracked_databases:
            print("\nDetailed List of Untracked Databases:")
            print("-" * 80)
            for db in sorted(untracked_databases):
                print(db)
            print("-" * 80)

    except Exception as e:
        print(f"\n✗ ANALYSIS FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
