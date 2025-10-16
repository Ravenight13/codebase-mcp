#!/usr/bin/env python3
"""Validation test for config file discovery logic.

This script tests the find_config_file() function with various scenarios:
1. Config found in working directory
2. Config found in parent directory (upward traversal)
3. Config not found (returns None)
4. Filesystem root detection
5. Max depth limit enforcement
"""

from pathlib import Path
import tempfile
import json
import sys
import logging

# Add src to path for import
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.auto_switch.discovery import find_config_file

# Configure logging to see debug output
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_config_in_working_directory():
    """Test 1: Config found in working directory."""
    print("\n=== Test 1: Config in working directory ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir) / ".codebase-mcp"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({"version": "1.0", "project": {"name": "test"}}))

        found = find_config_file(Path(tmpdir))
        # Resolve both paths for comparison (macOS /var -> /private/var symlink)
        assert found.resolve() == config_file.resolve(), f"Expected {config_file.resolve()}, got {found.resolve()}"
        print(f"✓ Found config at: {found}")
        print("✓ Test 1 PASSED")

def test_config_in_parent_directory():
    """Test 2: Config found in parent directory (upward traversal)."""
    print("\n=== Test 2: Config in parent directory ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create config at root level
        config_dir = Path(tmpdir) / ".codebase-mcp"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({"version": "1.0", "project": {"name": "parent-test"}}))

        # Create nested subdirectory
        subdir = Path(tmpdir) / "level1" / "level2" / "level3"
        subdir.mkdir(parents=True)

        # Search from nested directory
        found = find_config_file(subdir)
        # Resolve both paths for comparison
        assert found.resolve() == config_file.resolve(), f"Expected {config_file.resolve()}, got {found.resolve()}"
        print(f"✓ Found config at: {found}")
        print(f"✓ Traversed from {subdir} to {config_file.parent}")
        print("✓ Test 2 PASSED")

def test_config_not_found():
    """Test 3: Config not found (returns None)."""
    print("\n=== Test 3: Config not found ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        # No config file created
        subdir = Path(tmpdir) / "no-config"
        subdir.mkdir()

        found = find_config_file(subdir)
        assert found is None, f"Expected None, got {found}"
        print("✓ Correctly returned None when config not found")
        print("✓ Test 3 PASSED")

def test_max_depth_limit():
    """Test 4: Max depth limit enforcement."""
    print("\n=== Test 4: Max depth limit ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create config at root
        config_dir = Path(tmpdir) / ".codebase-mcp"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({"version": "1.0", "project": {"name": "depth-test"}}))

        # Create deep nested directory (5 levels)
        deep_dir = Path(tmpdir) / "l1" / "l2" / "l3" / "l4" / "l5"
        deep_dir.mkdir(parents=True)

        # Search with max_depth=3 (should NOT find config)
        found = find_config_file(deep_dir, max_depth=3)
        assert found is None, f"Expected None with max_depth=3, got {found}"
        print("✓ Max depth limit enforced (max_depth=3, config at level 5)")

        # Search with max_depth=10 (should find config)
        found = find_config_file(deep_dir, max_depth=10)
        # Resolve both paths for comparison
        assert found.resolve() == config_file.resolve(), f"Expected {config_file.resolve()}, got {found.resolve()}"
        print("✓ Config found with max_depth=10")
        print("✓ Test 4 PASSED")

def test_symlink_resolution():
    """Test 5: Symlink resolution."""
    print("\n=== Test 5: Symlink resolution ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create config in real directory
        real_dir = Path(tmpdir) / "real-project"
        real_dir.mkdir()
        config_dir = real_dir / ".codebase-mcp"
        config_dir.mkdir()
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps({"version": "1.0", "project": {"name": "symlink-test"}}))

        # Create symlink to real directory
        symlink_dir = Path(tmpdir) / "symlink-project"
        try:
            symlink_dir.symlink_to(real_dir)

            # Search from symlink (should resolve to real path)
            found = find_config_file(symlink_dir)
            # Resolve both paths for comparison
            assert found.resolve() == config_file.resolve(), f"Expected {config_file.resolve()}, got {found.resolve()}"
            print(f"✓ Resolved symlink {symlink_dir} -> {real_dir}")
            print(f"✓ Found config at: {found}")
            print("✓ Test 5 PASSED")
        except OSError as e:
            print(f"⚠ Symlink test skipped (OS limitation): {e}")

def main():
    """Run all validation tests."""
    print("=" * 60)
    print("Config Discovery Validation Tests")
    print("=" * 60)

    try:
        test_config_in_working_directory()
        test_config_in_parent_directory()
        test_config_not_found()
        test_max_depth_limit()
        test_symlink_resolution()

        print("\n" + "=" * 60)
        print("✓ ALL VALIDATION TESTS PASSED")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
