#!/usr/bin/env python3
"""Clean up orphaned entries in workflow-mcp registry databases.

This script identifies and optionally removes registry entries that point to
non-existent project databases in both workflow_mcp_registry and workflow_registry.

Usage:
    # Dry run (shows what would be deleted)
    python scripts/cleanup_workflow_registries.py

    # Clean up a specific registry
    python scripts/cleanup_workflow_registries.py --registry workflow_mcp_registry

    # Clean up both registries
    python scripts/cleanup_workflow_registries.py --registry all

    # Actually delete orphaned entries
    python scripts/cleanup_workflow_registries.py --registry all --delete

    # Export orphaned entries before deletion
    python scripts/cleanup_workflow_registries.py --registry all --delete --export orphaned_workflow.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

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


async def get_existing_databases(pool: asyncpg.Pool) -> set[str]:
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


async def get_projects_from_registry(pool: asyncpg.Pool) -> list[dict[str, Any]]:
    """
    Get all projects from a registry database.

    Args:
        pool: AsyncPG connection pool for registry

    Returns:
        List of project dictionaries with id, name, and database_name
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, name, description, database_name, created_at, updated_at, metadata
            FROM projects
            ORDER BY created_at DESC
            """
        )
        return [
            {
                "id": str(row["id"]),
                "name": row["name"],
                "description": row["description"],
                "database_name": row["database_name"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "metadata": row["metadata"] if row["metadata"] else {},
            }
            for row in rows
        ]


async def find_orphaned_projects(
    projects: list[dict[str, Any]], existing_dbs: set[str]
) -> list[dict[str, Any]]:
    """
    Find registry entries that point to non-existent databases.

    Args:
        projects: List of project dictionaries from registry
        existing_dbs: Set of database names that exist

    Returns:
        List of orphaned project dictionaries
    """
    return [
        project
        for project in projects
        if project["database_name"] not in existing_dbs
    ]


async def delete_orphaned_entries(
    pool: asyncpg.Pool, orphaned_projects: list[dict[str, Any]]
) -> int:
    """
    Delete orphaned entries from the registry.

    Args:
        pool: AsyncPG connection pool for registry
        orphaned_projects: List of orphaned projects to delete

    Returns:
        Number of entries deleted
    """
    deleted_count = 0
    for project in orphaned_projects:
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM projects WHERE id = $1", project["id"]
                )
            deleted_count += 1
            print(f"  ✓ Deleted: {project['name']} ({project['database_name']})")
        except Exception as e:
            print(f"  ✗ Failed to delete {project['name']}: {e}")

    return deleted_count


def export_orphaned_projects(orphaned: list[dict[str, Any]], filepath: str) -> None:
    """
    Export orphaned projects to JSON file for backup.

    Args:
        orphaned: List of orphaned projects
        filepath: Path to export JSON file
    """
    export_data = {
        "exported_at": datetime.now().isoformat(),
        "count": len(orphaned),
        "projects": [
            {
                "id": project["id"],
                "name": project["name"],
                "description": project["description"],
                "database_name": project["database_name"],
                "created_at": project["created_at"].isoformat() if project["created_at"] else None,
                "updated_at": project["updated_at"].isoformat() if project["updated_at"] else None,
                "metadata": project["metadata"],
            }
            for project in orphaned
        ],
    }

    with open(filepath, "w") as f:
        json.dump(export_data, f, indent=2)

    print(f"\n✓ Exported {len(orphaned)} orphaned entries to: {filepath}")


async def cleanup_registry(
    registry_name: str,
    existing_dbs: set[str],
    delete: bool,
    export_file: str | None,
) -> tuple[int, int]:
    """
    Clean up a single registry database.

    Args:
        registry_name: Name of the registry database
        existing_dbs: Set of existing database names
        delete: Whether to actually delete orphaned entries
        export_file: Optional path to export orphaned entries

    Returns:
        Tuple of (total_projects, orphaned_count)
    """
    print(f"\n{'=' * 80}")
    print(f"Cleaning up: {registry_name}")
    print(f"{'=' * 80}")

    try:
        # Connect to registry
        print("\n1. Connecting to registry database...")
        pool = await create_simple_pool(registry_name)
        print(f"   ✓ Connected to {registry_name}")

        # Get all projects
        print("\n2. Fetching projects from registry...")
        projects = await get_projects_from_registry(pool)
        print(f"   ✓ Found {len(projects)} total projects")

        # Find orphaned entries
        print("\n3. Checking for orphaned entries...")
        orphaned_projects = await find_orphaned_projects(projects, existing_dbs)

        if not orphaned_projects:
            print("   ✓ No orphaned entries found! Registry is clean.")
            await pool.close()
            return len(projects), 0

        print(f"   ⚠ Found {len(orphaned_projects)} orphaned entries:")
        print()
        for project in orphaned_projects[:10]:  # Show first 10
            print(f"   • {project['name']}")
            print(f"     Database: {project['database_name']} (DOES NOT EXIST)")
            print(f"     ID: {project['id']}")
            print(f"     Created: {project['created_at']}")
            print()

        if len(orphaned_projects) > 10:
            print(f"   ... and {len(orphaned_projects) - 10} more")
            print()

        # Export if requested
        if export_file:
            export_path = f"{registry_name}_{export_file}"
            export_orphaned_projects(orphaned_projects, export_path)

        # Delete if requested
        if delete:
            print("\n4. Deleting orphaned entries...")
            print("   ⚠ WARNING: This will permanently remove these entries from the registry!")

            deleted_count = await delete_orphaned_entries(pool, orphaned_projects)
            print(f"\n   ✓ Deleted {deleted_count} orphaned entries from {registry_name}")
        else:
            print("\n4. Dry run mode (no changes made)")
            print("   Run with --delete to actually remove these entries")

        # Cleanup
        await pool.close()
        return len(projects), len(orphaned_projects)

    except Exception as e:
        print(f"\n✗ CLEANUP FAILED for {registry_name}: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0


async def main() -> None:
    """Main cleanup workflow."""
    parser = argparse.ArgumentParser(
        description="Clean up orphaned entries in workflow-mcp registry databases"
    )
    parser.add_argument(
        "--registry",
        type=str,
        choices=["workflow_mcp_registry", "workflow_registry", "all"],
        default="all",
        help="Which registry database to clean (default: all)",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete orphaned entries (default: dry run)",
    )
    parser.add_argument(
        "--export",
        type=str,
        metavar="FILE",
        help="Export orphaned entries to JSON file before deletion",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("Workflow Registry Cleanup Utility")
    print("=" * 80)

    try:
        # Get list of existing databases (shared across both registries)
        print("\n1. Querying PostgreSQL for existing databases...")
        temp_pool = await create_simple_pool("postgres")
        existing_dbs = await get_existing_databases(temp_pool)
        await temp_pool.close()
        print(f"   ✓ Found {len(existing_dbs)} databases in PostgreSQL")

        # Determine which registries to clean
        registries_to_clean = []
        if args.registry == "all":
            registries_to_clean = ["workflow_mcp_registry", "workflow_registry"]
        else:
            registries_to_clean = [args.registry]

        # Track totals
        total_projects = 0
        total_orphaned = 0

        # Clean each registry
        for registry_name in registries_to_clean:
            projects_count, orphaned_count = await cleanup_registry(
                registry_name=registry_name,
                existing_dbs=existing_dbs,
                delete=args.delete,
                export_file=args.export,
            )
            total_projects += projects_count
            total_orphaned += orphaned_count

        # Summary
        print("\n" + "=" * 80)
        print("Cleanup Summary")
        print("=" * 80)
        print(f"Registries cleaned: {len(registries_to_clean)}")
        print(f"Total projects: {total_projects}")
        print(f"Orphaned entries: {total_orphaned}")
        if args.delete:
            print(f"Entries deleted: {total_orphaned}")
        else:
            print("Mode: DRY RUN (no changes made)")
            print("\nRun with --delete to actually remove orphaned entries")
            if args.export:
                print("Run with --export FILE to backup before deletion")
        print("=" * 80)

    except Exception as e:
        print(f"\n✗ CLEANUP FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
