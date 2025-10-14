"""Test repository generation fixtures for performance validation.

This module generates synthetic code repositories using tree-sitter for
parseable code generation. Fixtures create realistic file structures with
proper Python and JavaScript syntax suitable for performance benchmarking.

Constitutional Compliance:
- Principle VIII: Type Safety (mypy --strict compliance, complete annotations)
- Principle V: Production Quality (comprehensive error handling)
- Principle IV: Performance (bulk generation for 10,000-file repositories)

Requirements Addressed:
- FR-024: Realistic test fixtures with file size distribution, directory depth,
         language mix, and code complexity (functions, classes, imports)

Usage:
    from tests.fixtures.test_repository import generate_test_repository

    # Generate 10,000-file repository for benchmarking
    repo_path = generate_test_repository(
        base_path=tmp_path,
        total_files=10_000,
        language_mix={"python": 0.6, "javascript": 0.4}
    )
"""

from __future__ import annotations

import random
import string
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

import tree_sitter_javascript as tsjs
import tree_sitter_python as tspy
from tree_sitter import Language, Parser


# ==============================================================================
# Type Definitions
# ==============================================================================

LanguageType = Literal["python", "javascript"]


@dataclass(frozen=True)
class FileGenerationSpec:
    """Specification for generating a single code file.

    Attributes:
        relative_path: Path relative to repository root
        language: Programming language (python or javascript)
        size_bytes: Target file size in bytes (100-50000)
        directory_depth: Nesting level in directory tree (0-5)
        complexity_level: Code complexity (simple/medium/complex)
    """

    relative_path: Path
    language: LanguageType
    size_bytes: int
    directory_depth: int
    complexity_level: Literal["simple", "medium", "complex"]


@dataclass(frozen=True)
class RepositorySpec:
    """Specification for generating a test repository.

    Attributes:
        total_files: Total number of files to generate (10,000 typical)
        language_mix: Language distribution (e.g., {"python": 0.6, "javascript": 0.4})
        max_directory_depth: Maximum nesting level (5 per FR-024)
        min_file_size: Minimum file size in bytes (100 per FR-024)
        max_file_size: Maximum file size in bytes (50,000 per FR-024)
    """

    total_files: int
    language_mix: dict[str, float]
    max_directory_depth: int
    min_file_size: int
    max_file_size: int


class CodeGenerator(Protocol):
    """Protocol for language-specific code generators."""

    def generate_imports(self, count: int) -> str:
        """Generate import statements."""
        ...

    def generate_function(self, name: str, complexity: str) -> str:
        """Generate function definition."""
        ...

    def generate_class(self, name: str, complexity: str) -> str:
        """Generate class definition."""
        ...

    def validate_syntax(self, code: str) -> bool:
        """Validate code syntax using tree-sitter."""
        ...


# ==============================================================================
# Python Code Generator
# ==============================================================================


class PythonCodeGenerator:
    """Generates syntactically valid Python code using tree-sitter."""

    def __init__(self) -> None:
        """Initialize Python parser."""
        self.language: Language = Language(tspy.language())
        self.parser: Parser = Parser(self.language)

    def generate_imports(self, count: int) -> str:
        """Generate Python import statements.

        Args:
            count: Number of imports to generate (1-10)

        Returns:
            Multi-line string of import statements
        """
        standard_libs = [
            "asyncio",
            "json",
            "os",
            "sys",
            "pathlib",
            "datetime",
            "typing",
            "uuid",
            "logging",
            "re",
        ]
        selected = random.sample(standard_libs, min(count, len(standard_libs)))
        imports = [f"import {lib}" for lib in selected]
        imports.append("from typing import Any, Optional")
        return "\n".join(imports)

    def generate_function(self, name: str, complexity: str) -> str:
        """Generate Python function definition.

        Args:
            name: Function name (valid Python identifier)
            complexity: Complexity level (simple/medium/complex)

        Returns:
            Python function definition with type annotations
        """
        if complexity == "simple":
            return f'''def {name}(value: str) -> str:
    """Simple function that returns input."""
    return value
'''
        elif complexity == "medium":
            return f'''async def {name}(data: dict[str, Any]) -> dict[str, Any]:
    """Process data and return result."""
    result = {{"status": "success", "data": data}}
    await asyncio.sleep(0.1)
    return result
'''
        else:  # complex
            return f'''async def {name}(
    session: Any,
    filters: dict[str, Any],
    limit: int = 100
) -> list[dict[str, Any]]:
    """Fetch records with complex filtering logic."""
    results: list[dict[str, Any]] = []
    for key, value in filters.items():
        if isinstance(value, (str, int)):
            results.append({{"key": key, "value": value}})
    return results[:limit]
'''

    def generate_class(self, name: str, complexity: str) -> str:
        """Generate Python class definition.

        Args:
            name: Class name (valid Python identifier)
            complexity: Complexity level (simple/medium/complex)

        Returns:
            Python class definition with methods
        """
        if complexity == "simple":
            return f'''class {name}:
    """Simple data class."""

    def __init__(self, value: str) -> None:
        self.value = value

    def get_value(self) -> str:
        """Return stored value."""
        return self.value
'''
        elif complexity == "medium":
            return f'''class {name}:
    """Data processor with state management."""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.initialized = False
        self.logger = logging.getLogger(__name__)

    async def initialize(self) -> None:
        """Initialize processor."""
        self.initialized = True
        self.logger.info("Processor initialized")

    async def process(self, data: Any) -> dict[str, Any]:
        """Process data."""
        if not self.initialized:
            await self.initialize()
        return {{"status": "processed", "data": data}}
'''
        else:  # complex
            return f'''class {name}:
    """Complex service with lifecycle management."""

    def __init__(
        self,
        config: dict[str, Any],
        dependencies: Optional[dict[str, Any]] = None
    ) -> None:
        self.config = config
        self.dependencies = dependencies or {{}}
        self.state: dict[str, Any] = {{}}
        self.logger = logging.getLogger(__name__)

    async def start(self) -> None:
        """Start service."""
        self.logger.info("Starting service")
        await self._initialize_dependencies()
        self.state["running"] = True

    async def _initialize_dependencies(self) -> None:
        """Initialize all dependencies."""
        for name, dep in self.dependencies.items():
            self.logger.debug(f"Initializing dependency: {{name}}")
            await asyncio.sleep(0.01)

    async def stop(self) -> None:
        """Stop service."""
        self.state["running"] = False
        self.logger.info("Service stopped")

    async def health_check(self) -> dict[str, Any]:
        """Return service health status."""
        return {{
            "status": "healthy" if self.state.get("running") else "stopped",
            "dependencies": len(self.dependencies)
        }}
'''

    def validate_syntax(self, code: str) -> bool:
        """Validate Python syntax using tree-sitter.

        Args:
            code: Python source code

        Returns:
            True if code parses without errors
        """
        tree = self.parser.parse(bytes(code, "utf-8"))
        return not tree.root_node.has_error


# ==============================================================================
# JavaScript Code Generator
# ==============================================================================


class JavaScriptCodeGenerator:
    """Generates syntactically valid JavaScript code using tree-sitter."""

    def __init__(self) -> None:
        """Initialize JavaScript parser."""
        self.language: Language = Language(tsjs.language())
        self.parser: Parser = Parser(self.language)

    def generate_imports(self, count: int) -> str:
        """Generate ES6 import statements.

        Args:
            count: Number of imports to generate (1-10)

        Returns:
            Multi-line string of import statements
        """
        modules = ["fs", "path", "util", "stream", "events", "crypto", "os"]
        selected = random.sample(modules, min(count, len(modules)))
        imports = [f"const {mod} = require('{mod}');" for mod in selected]
        return "\n".join(imports)

    def generate_function(self, name: str, complexity: str) -> str:
        """Generate JavaScript function definition.

        Args:
            name: Function name (valid JS identifier)
            complexity: Complexity level (simple/medium/complex)

        Returns:
            JavaScript function definition
        """
        if complexity == "simple":
            return f'''function {name}(value) {{
  return value;
}}
'''
        elif complexity == "medium":
            return f'''async function {name}(data) {{
  const result = {{ status: 'success', data: data }};
  await new Promise(resolve => setTimeout(resolve, 100));
  return result;
}}
'''
        else:  # complex
            return f'''async function {name}(session, filters, limit = 100) {{
  const results = [];
  for (const [key, value] of Object.entries(filters)) {{
    if (typeof value === 'string' || typeof value === 'number') {{
      results.push({{ key, value }});
    }}
  }}
  return results.slice(0, limit);
}}
'''

    def generate_class(self, name: str, complexity: str) -> str:
        """Generate JavaScript class definition.

        Args:
            name: Class name (valid JS identifier)
            complexity: Complexity level (simple/medium/complex)

        Returns:
            JavaScript class definition
        """
        if complexity == "simple":
            return f'''class {name} {{
  constructor(value) {{
    this.value = value;
  }}

  getValue() {{
    return this.value;
  }}
}}
'''
        elif complexity == "medium":
            return f'''class {name} {{
  constructor(config) {{
    this.config = config;
    this.initialized = false;
  }}

  async initialize() {{
    this.initialized = true;
    console.log('Processor initialized');
  }}

  async process(data) {{
    if (!this.initialized) {{
      await this.initialize();
    }}
    return {{ status: 'processed', data }};
  }}
}}
'''
        else:  # complex
            return f'''class {name} {{
  constructor(config, dependencies = {{}}) {{
    this.config = config;
    this.dependencies = dependencies;
    this.state = {{}};
  }}

  async start() {{
    console.log('Starting service');
    await this._initializeDependencies();
    this.state.running = true;
  }}

  async _initializeDependencies() {{
    for (const [name, dep] of Object.entries(this.dependencies)) {{
      console.log(`Initializing dependency: ${{name}}`);
      await new Promise(resolve => setTimeout(resolve, 10));
    }}
  }}

  async stop() {{
    this.state.running = false;
    console.log('Service stopped');
  }}

  async healthCheck() {{
    return {{
      status: this.state.running ? 'healthy' : 'stopped',
      dependencies: Object.keys(this.dependencies).length
    }};
  }}
}}
'''

    def validate_syntax(self, code: str) -> bool:
        """Validate JavaScript syntax using tree-sitter.

        Args:
            code: JavaScript source code

        Returns:
            True if code parses without errors
        """
        tree = self.parser.parse(bytes(code, "utf-8"))
        return not tree.root_node.has_error


# ==============================================================================
# Repository Generation Functions
# ==============================================================================


def _random_identifier(prefix: str = "") -> str:
    """Generate random valid identifier.

    Args:
        prefix: Optional prefix (e.g., 'func_', 'class_')

    Returns:
        Valid Python/JavaScript identifier
    """
    suffix = "".join(random.choices(string.ascii_lowercase, k=8))
    return f"{prefix}{suffix}" if prefix else suffix


def _generate_directory_structure(
    total_files: int, max_depth: int
) -> list[Path]:
    """Generate realistic directory structure.

    Args:
        total_files: Total number of files to distribute
        max_depth: Maximum directory nesting level (0-5)

    Returns:
        List of relative paths with appropriate directory nesting
    """
    paths: list[Path] = []

    # Distribution: 30% root, 40% depth 1-2, 30% depth 3-5
    root_files = int(total_files * 0.3)
    shallow_files = int(total_files * 0.4)
    deep_files = total_files - root_files - shallow_files

    # Common directory names for realistic structure
    top_dirs = ["src", "lib", "tests", "utils", "core", "api", "services"]
    mid_dirs = ["handlers", "models", "schemas", "processors", "validators"]

    # Root level files
    for i in range(root_files):
        paths.append(Path(f"module_{i:04d}.py"))

    # Shallow depth (1-2 levels)
    for i in range(shallow_files):
        top = random.choice(top_dirs)
        if random.random() < 0.5:
            paths.append(Path(top) / f"file_{i:04d}.py")
        else:
            mid = random.choice(mid_dirs)
            paths.append(Path(top) / mid / f"file_{i:04d}.py")

    # Deep depth (3-5 levels)
    for i in range(deep_files):
        depth = random.randint(3, max_depth)
        components = [random.choice(top_dirs)]
        for _ in range(depth - 1):
            components.append(random.choice(mid_dirs))
        components.append(f"file_{i:04d}.py")
        paths.append(Path(*components))

    return paths


def _generate_file_specs(
    repo_spec: RepositorySpec,
) -> list[FileGenerationSpec]:
    """Generate file generation specifications.

    Args:
        repo_spec: Repository specification parameters

    Returns:
        List of file specifications with language, size, and complexity
    """
    specs: list[FileGenerationSpec] = []

    # Generate directory structure
    dir_paths = _generate_directory_structure(
        repo_spec.total_files, repo_spec.max_directory_depth
    )

    # Calculate language distribution
    python_count = int(repo_spec.total_files * repo_spec.language_mix.get("python", 0.6))
    # Build language list with explicit typing
    python_list: list[LanguageType] = ["python"] * python_count
    js_list: list[LanguageType] = ["javascript"] * (repo_spec.total_files - python_count)
    languages: list[LanguageType] = python_list + js_list
    random.shuffle(languages)

    # Generate specs for each file
    for path, language in zip(dir_paths, languages):
        # Update extension based on language
        if language == "javascript":
            path = path.with_suffix(".js")

        # Random file size within bounds
        size_bytes = random.randint(repo_spec.min_file_size, repo_spec.max_file_size)

        # Complexity distribution: 40% simple, 40% medium, 20% complex
        complexity_choice = random.random()
        if complexity_choice < 0.4:
            complexity: Literal["simple", "medium", "complex"] = "simple"
        elif complexity_choice < 0.8:
            complexity = "medium"
        else:
            complexity = "complex"

        specs.append(
            FileGenerationSpec(
                relative_path=path,
                language=language,
                size_bytes=size_bytes,
                directory_depth=len(path.parents) - 1,
                complexity_level=complexity,
            )
        )

    return specs


def _generate_file_content(
    spec: FileGenerationSpec, generator: CodeGenerator
) -> str:
    """Generate file content based on specification.

    Args:
        spec: File generation specification
        generator: Language-specific code generator

    Returns:
        Generated source code content
    """
    lines: list[str] = []

    # Add imports (2-5 imports)
    import_count = random.randint(2, 5)
    lines.append(generator.generate_imports(import_count))
    lines.append("")

    # Calculate content to generate based on target size
    current_size = len("\n".join(lines).encode("utf-8"))
    target_size = spec.size_bytes

    # Generate functions and classes until target size reached
    item_count = 0
    while current_size < target_size and item_count < 20:  # Max 20 items per file
        if random.random() < 0.6:  # 60% functions, 40% classes
            name = _random_identifier("func_")
            lines.append(generator.generate_function(name, spec.complexity_level))
        else:
            name = _random_identifier("Class")
            lines.append(generator.generate_class(name, spec.complexity_level))

        lines.append("")
        current_size = len("\n".join(lines).encode("utf-8"))
        item_count += 1

    content = "\n".join(lines)

    # Validate syntax
    if not generator.validate_syntax(content):
        raise ValueError(f"Generated invalid syntax for {spec.relative_path}")

    return content


def generate_test_repository(
    base_path: Path,
    total_files: int = 10_000,
    language_mix: dict[str, float] | None = None,
    max_directory_depth: int = 5,
    min_file_size: int = 100,
    max_file_size: int = 50_000,
) -> Path:
    """Generate synthetic test repository with tree-sitter validated code.

    Args:
        base_path: Base directory for repository (must exist)
        total_files: Total number of files to generate (default: 10,000)
        language_mix: Language distribution (default: {"python": 0.6, "javascript": 0.4})
        max_directory_depth: Maximum nesting level (default: 5, per FR-024)
        min_file_size: Minimum file size in bytes (default: 100, per FR-024)
        max_file_size: Maximum file size in bytes (default: 50,000, per FR-024)

    Returns:
        Path to generated repository root

    Raises:
        ValueError: If parameters are invalid
        OSError: If file system operations fail

    Example:
        >>> from pathlib import Path
        >>> repo_path = generate_test_repository(
        ...     base_path=Path("/tmp"),
        ...     total_files=10_000,
        ...     language_mix={"python": 0.6, "javascript": 0.4}
        ... )
        >>> files = list(repo_path.rglob("*.py"))
        >>> len(files) >= 5000  # At least 60% Python files
        True
    """
    if not base_path.exists():
        raise ValueError(f"Base path does not exist: {base_path}")

    if total_files < 1:
        raise ValueError(f"total_files must be >= 1, got {total_files}")

    if language_mix is None:
        language_mix = {"python": 0.6, "javascript": 0.4}

    # Validate language mix sums to 1.0 (within floating point tolerance)
    total_proportion = sum(language_mix.values())
    if not 0.99 <= total_proportion <= 1.01:
        raise ValueError(f"Language mix must sum to 1.0, got {total_proportion}")

    # Create repository root
    repo_path = base_path / "test_repository"
    repo_path.mkdir(exist_ok=True)

    # Generate repository specification
    repo_spec = RepositorySpec(
        total_files=total_files,
        language_mix=language_mix,
        max_directory_depth=max_directory_depth,
        min_file_size=min_file_size,
        max_file_size=max_file_size,
    )

    # Generate file specifications
    file_specs = _generate_file_specs(repo_spec)

    # Initialize code generators
    python_gen = PythonCodeGenerator()
    js_gen = JavaScriptCodeGenerator()

    # Generate files
    for i, spec in enumerate(file_specs):
        # Show progress every 1000 files
        if i > 0 and i % 1000 == 0:
            print(f"Generated {i:,} / {total_files:,} files...")

        # Create directory structure
        file_path = repo_path / spec.relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Select appropriate generator
        generator = python_gen if spec.language == "python" else js_gen

        # Generate and write content
        content = _generate_file_content(spec, generator)
        file_path.write_text(content, encoding="utf-8")

    print(f"Generated {total_files:,} files in {repo_path}")
    return repo_path


# ==============================================================================
# Convenience Functions for Testing
# ==============================================================================


def generate_small_test_repository(base_path: Path) -> Path:
    """Generate small test repository for quick validation (100 files).

    Args:
        base_path: Base directory for repository

    Returns:
        Path to generated repository root
    """
    return generate_test_repository(
        base_path=base_path,
        total_files=100,
        language_mix={"python": 0.6, "javascript": 0.4},
        max_directory_depth=3,
        min_file_size=100,
        max_file_size=5_000,
    )


def generate_benchmark_repository(base_path: Path) -> Path:
    """Generate standard benchmark repository (10,000 files per FR-001).

    Args:
        base_path: Base directory for repository

    Returns:
        Path to generated repository root
    """
    return generate_test_repository(
        base_path=base_path,
        total_files=10_000,
        language_mix={"python": 0.6, "javascript": 0.4},
        max_directory_depth=5,
        min_file_size=100,
        max_file_size=50_000,
    )
