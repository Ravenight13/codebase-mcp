# Performance Testing Dependencies

This document outlines all dependencies required for performance testing and validation in the codebase-mcp project.

## Python Dependencies (Already Installed)

The following Python packages are **already available** in `pyproject.toml` under `[project.optional-dependencies.dev]`:

### pytest-benchmark (>=4.0.0)
- **Status**: ✓ Already installed (line 66 in pyproject.toml)
- **Purpose**: Performance baseline testing for Python code
- **Usage**:
  ```bash
  pytest tests/benchmarks/ --benchmark-only
  pytest tests/benchmarks/ --benchmark-compare=performance_baselines/baseline.json
  ```

### pytest-asyncio (>=0.23.0)
- **Status**: ✓ Already installed (line 62 in pyproject.toml)
- **Purpose**: Async test support (required for async benchmark tests)
- **Usage**: Automatically enabled in pytest.ini via `asyncio_mode = "auto"`

### httpx (>=0.26.0)
- **Status**: ✓ Already installed (line 49 in pyproject.toml, production dependency)
- **Purpose**: HTTP client for MCP protocol testing and load test clients
- **Usage**: Used in contract tests and will be used in load test scenarios

## External Dependencies (Not Python Packages)

### k6 (>=0.45.0)
- **Status**: ⚠️ **Requires separate installation** (not a Python package)
- **Purpose**: Load testing and stress testing for MCP server endpoints
- **Installation**:

  **macOS (Homebrew)**:
  ```bash
  brew install k6
  ```

  **Linux (Debian/Ubuntu)**:
  ```bash
  sudo gpg -k
  sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
  echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
  sudo apt-get update
  sudo apt-get install k6
  ```

  **Linux (Fedora/CentOS)**:
  ```bash
  sudo dnf install https://dl.k6.io/rpm/repo.rpm
  sudo dnf install k6
  ```

  **Windows (Chocolatey)**:
  ```bash
  choco install k6
  ```

  **Docker** (alternative):
  ```bash
  docker pull grafana/k6:latest
  ```

- **Verification**:
  ```bash
  k6 version
  # Expected output: k6 v0.45.0 or higher
  ```

- **Usage**:
  ```bash
  # Run load test
  k6 run tests/load/mcp_load_test.js

  # Run with Docker
  docker run --rm -v $(pwd):/workspace grafana/k6 run /workspace/tests/load/mcp_load_test.js
  ```

## Optional Dependencies

### py-spy (>=0.3.14)
- **Status**: ✓ Already installed (line 77 in pyproject.toml)
- **Purpose**: Performance profiling for investigating bottlenecks
- **Usage**:
  ```bash
  py-spy record -o profile.svg -- python run_server.py
  ```

### tiktoken (>=0.5.0)
- **Status**: ✓ Already installed (line 67 in pyproject.toml)
- **Purpose**: Token counting for MCP efficiency tests
- **Usage**: Used in contract tests to validate response sizes

## Installation Quick Start

### For Development (Python dependencies only)
```bash
# Install all dev dependencies including performance testing tools
pip install -e '.[dev]'

# OR with uv (recommended)
uv pip install -e '.[dev]'
```

### For Full Performance Testing (Python + k6)
```bash
# 1. Install Python dependencies
pip install -e '.[dev]'

# 2. Install k6 (macOS example)
brew install k6

# 3. Verify installation
pytest --version          # Should show pytest with benchmark plugin
k6 version               # Should show k6 v0.45.0+
```

## Dependency Verification

Run this script to verify all dependencies are available:

```bash
#!/bin/bash
# scripts/verify_performance_deps.sh

echo "Checking Python dependencies..."
python -c "import pytest_benchmark; print(f'✓ pytest-benchmark {pytest_benchmark.__version__}')" || echo "✗ pytest-benchmark missing"
python -c "import pytest_asyncio; print(f'✓ pytest-asyncio {pytest_asyncio.__version__}')" || echo "✗ pytest-asyncio missing"
python -c "import httpx; print(f'✓ httpx {httpx.__version__}')" || echo "✗ httpx missing"

echo ""
echo "Checking external dependencies..."
if command -v k6 &> /dev/null; then
    echo "✓ k6 $(k6 version --quiet 2>&1 | head -1)"
else
    echo "✗ k6 not installed (install via: brew install k6)"
fi
```

## CI/CD Configuration

For GitHub Actions (`.github/workflows/performance.yml`):

```yaml
- name: Install k6
  run: |
    curl https://github.com/grafana/k6/releases/download/v0.45.0/k6-v0.45.0-linux-amd64.tar.gz -L | tar xvz --strip-components 1

- name: Install Python dependencies
  run: pip install -e '.[dev]'
```

## Troubleshooting

### pytest-benchmark not found
```bash
# Reinstall dev dependencies
pip install -e '.[dev]' --force-reinstall
```

### k6 not in PATH
```bash
# Add to PATH (adjust path as needed)
export PATH="/usr/local/bin:$PATH"

# Or install via Homebrew (macOS)
brew link k6
```

### httpx version conflicts
```bash
# The project requires httpx>=0.26.0
# If you see version conflicts, update:
pip install --upgrade httpx
```

## Related Documentation

- **Baseline Collection**: `performance_baselines/README.md`
- **Load Testing Guide**: `docs/performance/LOAD_TESTING.md` (to be created in T006)
- **Benchmark Tests**: `tests/benchmarks/` directory
- **Load Tests**: `tests/load/` directory

## Constitutional Compliance

This dependency setup aligns with:
- **Principle IV (Performance)**: Tools for measuring <500ms search, <60s indexing
- **Principle VII (TDD)**: Performance tests as regression protection
- **Principle XI (FastMCP Foundation)**: httpx for MCP protocol testing
