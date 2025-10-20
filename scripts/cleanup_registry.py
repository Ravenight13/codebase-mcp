#!/usr/bin/env python3
"""Clean up orphaned entries in the codebase_mcp_registry database.

This script identifies and optionally removes registry entries that point to
non-existent project databases.

Usage:
    # Dry run (shows what would be deleted)
    python scripts/cleanup_registry.py

    # Actually delete orphaned entries
    python scripts/cleanup_registry.py --delete

    # Export orphaned entries before deletion
    python scripts/cleanup_registry.py --delete --export orphaned_projects.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.provisioning import create_pool
from src.database.registry import Project, ProjectRegistry


async def get_existing_databases(pool: Any) -> set[str]:
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


async def find_orphaned_projects(
    registry: ProjectRegistry, existing_dbs: set[str]
) -> list[Project]:
    """
    Find registry entries that point to non-existent databases.

    Args:
        registry: ProjectRegistry instance
        existing_dbs: Set of database names that exist

    Returns:
        List of orphaned Project objects
    """
    all_projects = await registry.list_projects()
    orphaned = [
        project
        for project in all_projects
        if project.database_name not in existing_dbs
    ]
    return orphaned


async def delete_orphaned_entries(
    registry: ProjectRegistry, orphaned_projects: list[Project]
) -> int:
    """
    Delete orphaned entries from the registry.

    Args:
        registry: ProjectRegistry instance
        orphaned_projects: List of orphaned projects to delete

    Returns:
        Number of entries deleted
    """
    deleted_count = 0
    for project in orphaned_projects:
        try:
            # Delete using raw SQL since we don't have a delete method in ProjectRegistry
            async with registry._pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM projects WHERE id = $1", project.id
                )
            deleted_count += 1
            print(f"  ✓ Deleted: {project.name} ({project.database_name})")
        except Exception as e:
            print(f"  ✗ Failed to delete {project.name}: {e}")

    return deleted_count


def export_orphaned_projects(orphaned: list[Project], filepath: str) -> None:
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
                "id": str(project.id),
                "name": project.name,
                "description": project.description,
                "database_name": project.database_name,
                "created_at": project.created_at.isoformat() if project.created_at else None,
                "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                "metadata": project.metadata,
            }
            for project in orphaned
        ],
    }

    with open(filepath, "w") as f:
        json.dump(export_data, f, indent=2)

    print(f"\n✓ Exported {len(orphaned)} orphaned entries to: {filepath}")


async def main() -> None:
    """Main cleanup workflow."""
    parser = argparse.ArgumentParser(
        description="Clean up orphaned entries in codebase_mcp_registry"
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
    print("Registry Cleanup Utility")
    print("=" * 80)

    try:
        # Connect to registry
        print("\n1. Connecting to registry database...")
        registry_pool = await create_pool("codebase_mcp_registry")
        registry = ProjectRegistry(registry_pool)
        print("   ✓ Connected to codebase_mcp_registry")

        # Get list of existing databases
        print("\n2. Querying PostgreSQL for existing databases...")
        existing_dbs = await get_existing_databases(registry_pool)
        print(f"   ✓ Found {len(existing_dbs)} databases in PostgreSQL")

        # Find orphaned entries
        print("\n3. Checking registry for orphaned entries...")
        orphaned_projects = await find_orphaned_projects(registry, existing_dbs)

        if not orphaned_projects:
            print("   ✓ No orphaned entries found! Registry is clean.")
            await registry_pool.close()
            return

        print(f"   ⚠ Found {len(orphaned_projects)} orphaned entries:")
        print()
        for project in orphaned_projects:
            print(f"   • {project.name}")
            print(f"     Database: {project.database_name} (DOES NOT EXIST)")
            print(f"     ID: {project.id}")
            print(f"     Created: {project.created_at}")
            print()

        # Export if requested
        if args.export:
            export_orphaned_projects(orphaned_projects, args.export)

        # Delete if requested
        if args.delete:
            print("\n4. Deleting orphaned entries...")
            print("   ⚠ WARNING: This will permanently remove these entries from the registry!")

            # Confirmation prompt
            response = input("\n   Continue? [y/N]: ").strip().lower()
            if response != "y":
                print("   ✗ Deletion cancelled by user")
                await registry_pool.close()
                return

            deleted_count = await delete_orphaned_entries(registry, orphaned_projects)
            print(f"\n   ✓ Deleted {deleted_count} orphaned entries")
        else:
            print("\n4. Dry run mode (no changes made)")
            print("   Run with --delete to actually remove these entries")
            print("   Run with --export FILE to backup before deletion")

        print("\n" + "=" * 80)
        print("Cleanup completed successfully!")
        print("=" * 80)

        # Cleanup
        await registry_pool.close()

    except Exception as e:
        print(f"\n✗ CLEANUP FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
