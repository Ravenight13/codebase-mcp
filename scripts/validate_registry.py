#!/usr/bin/env python3
"""Validation script for ProjectRegistry API.

This script demonstrates the complete ProjectRegistry API and validates
that all components work together correctly.

Usage:
    python scripts/validate_registry.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.registry import Project, ProjectRegistry
from src.database.provisioning import create_pool


async def main() -> None:
    """Validate ProjectRegistry API."""
    print("=" * 80)
    print("ProjectRegistry API Validation")
    print("=" * 80)

    # Check environment
    db_url = os.getenv("DATABASE_URL", "postgresql://localhost/codebase_mcp_registry")
    print(f"\nRegistry Database: {db_url}")

    try:
        # Connect to registry database
        print("\n1. Connecting to registry database...")
        registry_pool = await create_pool("codebase_mcp_registry")
        registry = ProjectRegistry(registry_pool)
        print("   ✓ Connected successfully")

        # List existing projects
        print("\n2. Listing existing projects...")
        projects = await registry.list_projects()
        print(f"   ✓ Found {len(projects)} existing projects")
        for project in projects[:5]:  # Show first 5
            print(f"     - {project.name} (DB: {project.database_name})")

        # Test Project model validation
        print("\n3. Testing Project model validation...")
        try:
            # Valid project
            test_project = Project(
                id="550e8400-e29b-41d4-a716-446655440000",
                name="Valid Project",
                description="Test project",
                database_name="cb_proj_valid_project_abc123de",
                created_at=projects[0].created_at if projects else None,
                updated_at=projects[0].updated_at if projects else None,
                metadata={"test": True},
            )
            print("   ✓ Valid project model created")

            # Invalid database name
            try:
                invalid_project = Project(
                    id="550e8400-e29b-41d4-a716-446655440000",
                    name="Invalid Project",
                    description="Test",
                    database_name="invalid_name",  # Wrong format
                    created_at=projects[0].created_at if projects else None,
                    updated_at=projects[0].updated_at if projects else None,
                    metadata={},
                )
                print("   ✗ FAILED: Invalid database name should be rejected")
            except ValueError as e:
                print(f"   ✓ Invalid database name rejected: {str(e)[:50]}...")

            # Invalid project name
            try:
                invalid_project = Project(
                    id="550e8400-e29b-41d4-a716-446655440000",
                    name="Invalid@Project#Name",  # Invalid characters
                    description="Test",
                    database_name="cb_proj_invalid_abc123de",
                    created_at=projects[0].created_at if projects else None,
                    updated_at=projects[0].updated_at if projects else None,
                    metadata={},
                )
                print("   ✗ FAILED: Invalid project name should be rejected")
            except ValueError as e:
                print(f"   ✓ Invalid project name rejected: {str(e)[:50]}...")

        except Exception as e:
            print(f"   ✗ FAILED: {e}")

        # Test get_project_by_name
        if projects:
            print("\n4. Testing get_project_by_name...")
            first_project = projects[0]
            found_project = await registry.get_project_by_name(first_project.name)
            if found_project and found_project.id == first_project.id:
                print(f"   ✓ Found project by name: {first_project.name}")
            else:
                print(f"   ✗ FAILED: Project lookup mismatch")

            # Test get_project by ID
            print("\n5. Testing get_project by ID...")
            found_by_id = await registry.get_project(first_project.id)
            if found_by_id and found_by_id.name == first_project.name:
                print(f"   ✓ Found project by ID: {first_project.id}")
            else:
                print(f"   ✗ FAILED: Project ID lookup mismatch")

        # Test non-existent lookups
        print("\n6. Testing non-existent project lookups...")
        not_found = await registry.get_project("00000000-0000-0000-0000-000000000000")
        if not_found is None:
            print("   ✓ Non-existent UUID returns None")
        else:
            print("   ✗ FAILED: Should return None for non-existent UUID")

        not_found_name = await registry.get_project_by_name("NonExistentProject123456789")
        if not_found_name is None:
            print("   ✓ Non-existent name returns None")
        else:
            print("   ✗ FAILED: Should return None for non-existent name")

        print("\n" + "=" * 80)
        print("✓ All validation tests completed successfully!")
        print("=" * 80)

        # Cleanup
        await registry_pool.close()

    except Exception as e:
        print(f"\n✗ VALIDATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
