#!/usr/bin/env python3
"""Validate Pydantic models for config-based project tracking."""

import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from src.auto_switch.models import CodebaseMCPConfig, ProjectConfig

def test_basic_config():
    """Test basic configuration creation."""
    config = CodebaseMCPConfig(version="1.0", project={"name": "test"})
    assert config.project.name == "test"
    assert config.version == "1.0"
    assert config.auto_switch is True  # Default value
    assert config.strict_mode is False  # Default value
    assert config.dry_run is False  # Default value
    print("✓ Basic config validation passed")

def test_full_config():
    """Test full configuration with all fields."""
    config = CodebaseMCPConfig(
        version="1.0",
        project=ProjectConfig(name="test-project", id="550e8400-e29b-41d4-a716-446655440000"),
        auto_switch=False,
        strict_mode=True,
        dry_run=True,
        description="Test configuration"
    )
    assert config.project.name == "test-project"
    assert config.project.id == "550e8400-e29b-41d4-a716-446655440000"
    assert config.auto_switch is False
    assert config.strict_mode is True
    assert config.dry_run is True
    assert config.description == "Test configuration"
    print("✓ Full config validation passed")

def test_version_pattern():
    """Test version pattern validation."""
    try:
        CodebaseMCPConfig(version="invalid", project={"name": "test"})
        assert False, "Should have raised validation error"
    except Exception as e:
        assert "pattern" in str(e).lower()
        print("✓ Version pattern validation passed")

def test_project_name_required():
    """Test that project name is required."""
    try:
        CodebaseMCPConfig(version="1.0", project={})
        assert False, "Should have raised validation error"
    except Exception as e:
        assert "name" in str(e).lower()
        print("✓ Project name required validation passed")

if __name__ == "__main__":
    print("Running Pydantic model validation tests...\n")
    test_basic_config()
    test_full_config()
    test_version_pattern()
    test_project_name_required()
    print("\n✅ All model validation tests passed!")
