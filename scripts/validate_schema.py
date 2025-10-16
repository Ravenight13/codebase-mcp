#!/usr/bin/env python3
"""Validate JSON schema structure."""

import sys
import json
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from src.auto_switch.models import CONFIG_SCHEMA

def test_schema_structure():
    """Test that schema is valid JSON Schema."""
    # Verify required top-level keys
    assert "type" in CONFIG_SCHEMA
    assert CONFIG_SCHEMA["type"] == "object"
    assert "required" in CONFIG_SCHEMA
    assert "properties" in CONFIG_SCHEMA

    # Verify required fields
    assert "version" in CONFIG_SCHEMA["required"]
    assert "project" in CONFIG_SCHEMA["required"]

    # Verify project structure
    project_schema = CONFIG_SCHEMA["properties"]["project"]
    assert project_schema["type"] == "object"
    assert "name" in project_schema["required"]

    print("✓ Schema structure validation passed")

    # Pretty print schema
    print("\nJSON Schema structure:")
    print(json.dumps(CONFIG_SCHEMA, indent=2))

if __name__ == "__main__":
    print("Validating JSON Schema structure...\n")
    test_schema_structure()
    print("\n✅ Schema validation complete!")
