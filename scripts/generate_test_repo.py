#!/usr/bin/env python3
"""Generate deterministic test repository for baseline performance testing.

Creates a test repository with N Python files containing realistic code patterns
for benchmarking the MCP server's indexing and search performance.

Usage:
    python scripts/generate_test_repo.py --files 100 --output test_repos/baseline_repo

Constitutional Compliance:
- Principle VIII: Type Safety (mypy --strict compliance)
- Principle V: Production Quality (comprehensive error handling)
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Final

# ==============================================================================
# Constants
# ==============================================================================

SEED: Final[int] = 42
MIN_LINES_PER_FILE: Final[int] = 50
MAX_LINES_PER_FILE: Final[int] = 100

# Sample code templates for deterministic generation
CLASS_NAMES: Final[list[str]] = [
    "DataProcessor",
    "FileHandler",
    "ConfigManager",
    "APIClient",
    "CacheManager",
    "LoggerFactory",
    "ValidationEngine",
    "SerializerBase",
    "ConnectionPool",
    "TaskExecutor",
]

FUNCTION_NAMES: Final[list[str]] = [
    "process_data",
    "validate_input",
    "transform_output",
    "fetch_resource",
    "parse_config",
    "serialize_object",
    "deserialize_json",
    "calculate_metrics",
    "cleanup_resources",
    "initialize_service",
]

METHOD_NAMES: Final[list[str]] = [
    "setup",
    "teardown",
    "validate",
    "execute",
    "process",
    "transform",
    "serialize",
    "deserialize",
    "connect",
    "disconnect",
]

PARAM_NAMES: Final[list[str]] = [
    "data",
    "config",
    "options",
    "context",
    "payload",
    "metadata",
    "parameters",
    "settings",
    "attributes",
    "properties",
]

TYPE_HINTS: Final[list[str]] = [
    "str",
    "int",
    "bool",
    "dict[str, Any]",
    "list[str]",
    "Path",
    "datetime",
    "UUID",
]

# ==============================================================================
# Code Generation Functions
# ==============================================================================


def generate_module_docstring(module_num: int) -> str:
    """Generate a module-level docstring.

    Args:
        module_num: Module number for deterministic content

    Returns:
        Module docstring with description
    """
    return f'''"""Module {module_num:04d} - Synthetic test module.

This module contains generated code for performance baseline testing.
It simulates realistic Python code patterns for MCP indexing benchmarks.
"""
'''


def generate_function(func_idx: int, rng: random.Random) -> str:
    """Generate a standalone function with type hints.

    Args:
        func_idx: Function index for deterministic naming
        rng: Random number generator for deterministic choices

    Returns:
        Complete function definition as string
    """
    func_name = rng.choice(FUNCTION_NAMES)
    param1 = rng.choice(PARAM_NAMES)
    param2 = rng.choice(PARAM_NAMES)
    type1 = rng.choice(TYPE_HINTS)
    type2 = rng.choice(TYPE_HINTS)
    return_type = rng.choice(TYPE_HINTS)

    return f'''
def {func_name}_{func_idx}({param1}: {type1}, {param2}: {type2}) -> {return_type}:
    """Process {param1} and {param2} to produce result.

    Args:
        {param1}: Input {type1} value
        {param2}: Additional {type2} parameter

    Returns:
        Processed {return_type} result
    """
    result = f"{{{param1}}} - {{{param2}}}"
    return result  # type: ignore[return-value]
'''


def generate_class(class_idx: int, rng: random.Random) -> str:
    """Generate a class with methods and type hints.

    Args:
        class_idx: Class index for deterministic naming
        rng: Random number generator for deterministic choices

    Returns:
        Complete class definition as string
    """
    class_name = rng.choice(CLASS_NAMES)
    method1 = rng.choice(METHOD_NAMES)
    method2 = rng.choice(METHOD_NAMES)
    param1 = rng.choice(PARAM_NAMES)
    param2 = rng.choice(PARAM_NAMES)
    type1 = rng.choice(TYPE_HINTS)
    type2 = rng.choice(TYPE_HINTS)

    return f'''
class {class_name}{class_idx}:
    """Generated class for testing purposes.

    This class demonstrates typical Python class patterns
    used in real-world codebases.
    """

    def __init__(self, {param1}: {type1}) -> None:
        """Initialize {class_name}{class_idx}.

        Args:
            {param1}: Configuration {type1}
        """
        self.{param1} = {param1}

    def {method1}(self, {param2}: {type2}) -> bool:
        """Perform {method1} operation.

        Args:
            {param2}: Input {type2} parameter

        Returns:
            Operation success status
        """
        return True

    def {method2}(self) -> str:
        """Perform {method2} operation.

        Returns:
            Operation result string
        """
        return f"{{self.{param1}}}"
'''


def generate_python_file(file_num: int, target_lines: int) -> str:
    """Generate a complete Python file with specified line count.

    Args:
        file_num: File number for deterministic content
        target_lines: Target number of lines (approximate)

    Returns:
        Complete Python file content
    """
    # Use seeded random for determinism
    rng = random.Random(SEED + file_num)

    lines: list[str] = []

    # Add imports
    lines.append("from __future__ import annotations\n")
    lines.append("")
    lines.append("import random")
    lines.append("from pathlib import Path")
    lines.append("from typing import Any")
    lines.append("from datetime import datetime")
    lines.append("from uuid import UUID")
    lines.append("")

    # Add module docstring
    lines.append(generate_module_docstring(file_num))
    lines.append("")

    current_lines = len(lines)

    # Generate functions and classes to reach target line count
    func_idx = 0
    class_idx = 0

    while current_lines < target_lines:
        if rng.random() < 0.5:
            # Generate function
            func_code = generate_function(func_idx, rng)
            lines.append(func_code)
            func_idx += 1
            current_lines += func_code.count("\n")
        else:
            # Generate class
            class_code = generate_class(class_idx, rng)
            lines.append(class_code)
            class_idx += 1
            current_lines += class_code.count("\n")

    return "".join(lines)


def create_test_repository(output_dir: Path, num_files: int) -> None:
    """Create test repository with specified number of files.

    Args:
        output_dir: Output directory path
        num_files: Number of Python files to generate

    Raises:
        OSError: If directory creation or file writing fails
    """
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Use seeded random for line counts
    rng = random.Random(SEED)

    print(f"Generating {num_files} Python files in {output_dir}...")

    for i in range(num_files):
        # Deterministic line count between MIN_LINES and MAX_LINES
        target_lines = rng.randint(MIN_LINES_PER_FILE, MAX_LINES_PER_FILE)

        # Generate file content
        content = generate_python_file(i, target_lines)

        # Write file
        file_path = output_dir / f"module_{i:04d}.py"
        file_path.write_text(content, encoding="utf-8")

        # Progress indicator every 10 files
        if (i + 1) % 10 == 0:
            print(f"  Generated {i + 1}/{num_files} files...")

    print(f"\nCompleted! Generated {num_files} files in {output_dir}")
    print(f"Total size: {sum(f.stat().st_size for f in output_dir.glob('*.py')) / 1024:.1f} KB")


# ==============================================================================
# CLI Entry Point
# ==============================================================================


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Generate deterministic test repository for performance baselines",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--files",
        type=int,
        default=100,
        help="Number of Python files to generate",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("test_repos/baseline_repo"),
        help="Output directory path",
    )
    return parser.parse_args()


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        args = parse_args()

        # Validate arguments
        if args.files <= 0:
            print("Error: --files must be positive", file=sys.stderr)
            return 1

        # Create test repository
        create_test_repository(args.output, args.files)

        return 0

    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
