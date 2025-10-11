# Phase 0: Foundation Setup

## Overview

**Purpose:** Establish complete infrastructure foundation for both MCPs before feature implementation begins.

**Duration:** 1 week (40 hours total, can be parallelized)

**Why Phase 0 Matters:**
- workflow-mcp is brand new (needs everything from scratch)
- codebase-mcp needs baseline and refactor preparation
- TDD requires test framework before implementation
- FastMCP patterns need boilerplate server setup
- Database permissions need validation (CREATEDB)
- CI/CD needs skeleton before first commit

**Without Phase 0:** Risk of discovering infrastructure issues mid-implementation, causing rework and delays.

---

## Phase 0A: workflow-mcp Foundation (Brand New Repository)

**Duration:** 1 week (40 hours)

### Deliverables Checklist

#### 1. Repository Initialization (2 hours)

```bash
# Create repository
mkdir -p /Users/cliffclarke/Claude_Code/workflow-mcp
cd /Users/cliffclarke/Claude_Code/workflow-mcp
git init
git checkout -b main

# Create initial structure
mkdir -p {src/workflow_mcp,tests/{unit,integration,performance},docs,.github/workflows}
```

**Files to create:**
- [ ] `README.md` - Project overview, installation, usage
- [ ] `.gitignore` - Python, IDE, env files
- [ ] `LICENSE` - MIT or Apache 2.0
- [ ] `.python-version` - `3.11.9`

**Git commits:**
```bash
git add .
git commit -m "chore: initialize workflow-mcp repository"
```

---

#### 2. Project Configuration (3 hours)

**Create `pyproject.toml`:**
```toml
[project]
name = "workflow-mcp"
version = "0.1.0"
description = "AI project management MCP with multi-project support"
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=0.2.0",
    "mcp>=0.9.0",
    "asyncpg>=0.29.0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "pytest-benchmark>=4.0.0",
    "mypy>=1.7.0",
    "ruff>=0.1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.coverage.run]
source = ["src"]
omit = ["tests/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
```

**Create `.env.template`:**
```bash
# PostgreSQL Connection
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=mcp_user
POSTGRES_PASSWORD=your_password_here
POSTGRES_DB=project_registry

# MCP Server Configuration
MCP_SERVER_PORT=8002
MCP_LOG_LEVEL=INFO
MCP_LOG_FILE=/tmp/workflow-mcp.log

# Project Configuration
MAX_ACTIVE_PROJECTS=50
DEFAULT_TOKEN_BUDGET=200000
```

**Git commits:**
```bash
git add pyproject.toml .env.template
git commit -m "chore: add project configuration and dependencies"
```

---

#### 3. Base Directory Structure (2 hours)

**Create source structure:**
```bash
# Source code
mkdir -p src/workflow_mcp/{models,services,tools,utils}
touch src/workflow_mcp/__init__.py
touch src/workflow_mcp/{models,services,tools,utils}/__init__.py

# Tests
mkdir -p tests/{unit,integration,performance,fixtures}
touch tests/__init__.py
touch tests/conftest.py
```

**Create `src/workflow_mcp/__init__.py`:**
```python
"""workflow-mcp: AI project management MCP with multi-project support."""

__version__ = "0.1.0"
```

**Create `tests/conftest.py`:**
```python
"""Pytest configuration and shared fixtures."""
import pytest
import asyncpg
from typing import AsyncGenerator

@pytest.fixture
async def test_db_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """Create test database connection pool."""
    pool = await asyncpg.create_pool(
        host="localhost",
        port=5432,
        user="mcp_user",
        password="test_password",
        database="test_workflow_mcp",
        min_size=2,
        max_size=5,
    )

    try:
        yield pool
    finally:
        await pool.close()

@pytest.fixture
async def clean_db(test_db_pool: asyncpg.Pool) -> None:
    """Clean test database before each test."""
    async with test_db_pool.acquire() as conn:
        # Drop all test tables
        await conn.execute("""
            DROP SCHEMA IF EXISTS workflow CASCADE;
            CREATE SCHEMA workflow;
        """)
```

**Git commits:**
```bash
git add src/ tests/
git commit -m "chore: create base directory structure"
```

---

#### 4. FastMCP Server Boilerplate (4 hours)

**Create `src/workflow_mcp/server.py`:**
```python
"""FastMCP server for workflow-mcp."""
import os
import logging
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from pydantic import BaseModel

# Configure logging
LOG_FILE = Path(os.getenv("MCP_LOG_FILE", "/tmp/workflow-mcp.log"))
LOG_LEVEL = os.getenv("MCP_LOG_LEVEL", "INFO")

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
    ],
)

logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("workflow-mcp")


# Health check tool (for testing infrastructure)
class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    database_connected: bool


@mcp.tool()
async def health_check() -> HealthResponse:
    """
    Health check endpoint to verify server is operational.

    Returns:
        HealthResponse with server status and version
    """
    # TODO: Add actual database connection check in Phase 1
    return HealthResponse(
        status="healthy",
        version="0.1.0",
        database_connected=False,  # Will be True after Phase 1
    )


def main() -> None:
    """Run the MCP server."""
    port = int(os.getenv("MCP_SERVER_PORT", "8002"))
    logger.info(f"Starting workflow-mcp server on port {port}")
    mcp.run(transport="sse", port=port)


if __name__ == "__main__":
    main()
```

**Create `src/workflow_mcp/config.py`:**
```python
"""Configuration management for workflow-mcp."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "mcp_user"
    postgres_password: str
    postgres_db: str = "project_registry"

    # MCP Server
    mcp_server_port: int = 8002
    mcp_log_level: str = "INFO"
    mcp_log_file: str = "/tmp/workflow-mcp.log"

    # Project Configuration
    max_active_projects: int = 50
    default_token_budget: int = 200000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Global settings instance
settings = Settings()
```

**Create `tests/unit/test_server.py`:**
```python
"""Test FastMCP server initialization."""
import pytest
from workflow_mcp.server import health_check


@pytest.mark.asyncio
async def test_health_check() -> None:
    """Test health check endpoint returns expected response."""
    response = await health_check()

    assert response.status == "healthy"
    assert response.version == "0.1.0"
    assert isinstance(response.database_connected, bool)
```

**Git commits:**
```bash
git add src/workflow_mcp/server.py src/workflow_mcp/config.py
git commit -m "feat(server): add FastMCP server boilerplate"

git add tests/unit/test_server.py
git commit -m "test(server): add health check test"
```

---

#### 5. Database Setup Scripts (4 hours)

**Create `scripts/setup_database.sh`:**
```bash
#!/bin/bash
set -e

echo "🗄️  Setting up PostgreSQL for workflow-mcp..."

# Check PostgreSQL is running
if ! pg_isready -h localhost -p 5432 > /dev/null 2>&1; then
    echo "❌ PostgreSQL is not running on localhost:5432"
    echo "   Start PostgreSQL first: brew services start postgresql@14"
    exit 1
fi

# Create database user (if doesn't exist)
psql -h localhost -U postgres -c "
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mcp_user') THEN
            CREATE ROLE mcp_user WITH LOGIN PASSWORD 'your_password_here';
        END IF;
    END
    \$\$;
" 2>/dev/null || echo "User mcp_user already exists"

# Grant CREATEDB permission
psql -h localhost -U postgres -c "ALTER ROLE mcp_user CREATEDB;" 2>/dev/null

# Create registry database
psql -h localhost -U postgres -c "DROP DATABASE IF EXISTS project_registry;" 2>/dev/null || true
psql -h localhost -U postgres -c "CREATE DATABASE project_registry OWNER mcp_user;"

# Create test database
psql -h localhost -U postgres -c "DROP DATABASE IF EXISTS test_workflow_mcp;" 2>/dev/null || true
psql -h localhost -U postgres -c "CREATE DATABASE test_workflow_mcp OWNER mcp_user;"

echo "✅ Database setup complete!"
echo ""
echo "Databases created:"
echo "  - project_registry (production)"
echo "  - test_workflow_mcp (testing)"
echo ""
echo "User created:"
echo "  - mcp_user (with CREATEDB permission)"
echo ""
echo "Next: Update .env file with database credentials"
```

**Create `scripts/init_registry_schema.sql`:**
```sql
-- Registry database schema for project tracking
-- This will be populated in Phase 1

CREATE SCHEMA IF NOT EXISTS registry;

-- Placeholder table for Phase 0 verification
CREATE TABLE registry.system_info (
    id SERIAL PRIMARY KEY,
    version VARCHAR(10) NOT NULL,
    initialized_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO registry.system_info (version) VALUES ('0.1.0');
```

**Make scripts executable:**
```bash
chmod +x scripts/setup_database.sh
```

**Create verification script `scripts/verify_database.sh`:**
```bash
#!/bin/bash
set -e

echo "🔍 Verifying database setup..."

# Check project_registry exists
if psql -h localhost -U mcp_user -lqt | cut -d \| -f 1 | grep -qw project_registry; then
    echo "✅ project_registry database exists"
else
    echo "❌ project_registry database NOT found"
    exit 1
fi

# Check CREATEDB permission
if psql -h localhost -U mcp_user -d postgres -c "CREATE DATABASE temp_test_db;" 2>/dev/null; then
    psql -h localhost -U mcp_user -d postgres -c "DROP DATABASE temp_test_db;"
    echo "✅ mcp_user has CREATEDB permission"
else
    echo "❌ mcp_user does NOT have CREATEDB permission"
    exit 1
fi

# Check registry schema
if psql -h localhost -U mcp_user -d project_registry -c "\dn" | grep -qw registry; then
    echo "✅ registry schema exists"
else
    echo "❌ registry schema NOT found"
    exit 1
fi

echo ""
echo "🎉 Database verification complete!"
```

**Git commits:**
```bash
git add scripts/
git commit -m "chore(db): add database setup and verification scripts"
```

---

#### 6. CI/CD Pipeline Skeleton (3 hours)

**Create `.github/workflows/ci.yml`:**
```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install ruff mypy
          pip install -e ".[dev]"

      - name: Run ruff
        run: ruff check src/ tests/

      - name: Run mypy
        run: mypy src/

  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e ".[dev]"

      - name: Setup test database
        env:
          POSTGRES_PASSWORD: postgres
        run: |
          psql -h localhost -U postgres -c "CREATE ROLE mcp_user WITH LOGIN PASSWORD 'test_password' CREATEDB;"
          psql -h localhost -U postgres -c "CREATE DATABASE test_workflow_mcp OWNER mcp_user;"

      - name: Run tests
        env:
          POSTGRES_PASSWORD: test_password
        run: |
          pytest tests/ -v --cov=src --cov-report=xml --cov-report=term

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

**Create `.github/workflows/performance.yml`:**
```yaml
name: Performance

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday

jobs:
  benchmark:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Run performance tests
        run: pytest tests/performance -v --benchmark-only

      - name: Store benchmark results
        uses: benchmark-action/github-action-benchmark@v1
        with:
          tool: 'pytest'
          output-file-path: benchmark-results.json
```

**Git commits:**
```bash
git add .github/
git commit -m "ci: add GitHub Actions workflows for testing and benchmarking"
```

---

#### 7. Development Tools Configuration (2 hours)

**Create `.vscode/settings.json`:**
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.unittestEnabled": false,
  "python.testing.pytestArgs": ["tests"],
  "python.linting.enabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.rulers": [100],
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff"
  }
}
```

**Create `Makefile`:**
```makefile
.PHONY: install test lint format clean run

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

lint:
	ruff check src/ tests/
	mypy src/

format:
	ruff check --fix src/ tests/

clean:
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

run:
	python -m workflow_mcp.server

db-setup:
	./scripts/setup_database.sh

db-verify:
	./scripts/verify_database.sh
```

**Git commits:**
```bash
git add .vscode/ Makefile
git commit -m "chore: add development tools configuration"
```

---

#### 8. Documentation (3 hours)

**Update `README.md`:**
```markdown
# workflow-mcp

AI project management MCP with multi-project workspace support.

## Features

- Multi-project workspace management
- Generic entity system (vendors, game mechanics, any domain)
- Work item hierarchy (projects, sessions, tasks, research)
- Task management with status tracking
- Deployment history with relationships

## Prerequisites

- Python 3.11+
- PostgreSQL 14+ with CREATEDB permission
- uv or pip for package management

## Installation

```bash
# Clone repository
git clone <repo-url>
cd workflow-mcp

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or: .venv\Scripts\activate on Windows

# Install dependencies
make install

# Setup database
make db-setup

# Verify database
make db-verify
```

## Configuration

Copy `.env.template` to `.env` and update with your settings:

```bash
cp .env.template .env
# Edit .env with your database credentials
```

## Development

```bash
# Run tests
make test

# Run tests with coverage
make test-cov

# Run linting
make lint

# Format code
make format

# Run server
make run
```

## Project Status

**Phase 0: Foundation** ✅ (Complete)
- Repository initialization
- FastMCP server boilerplate
- Database setup scripts
- CI/CD pipeline
- Development tools

**Phase 1: Core** 🚧 (In Progress)
- Project management (create/switch/list)
- Minimal entity system
- Connection pooling with LRU eviction

**Phase 3: Complete** 📋 (Planned)
- Work item hierarchy
- Task management
- Deployment tracking
- Entity enhancements

## Architecture

See `docs/mcp-split-plan/00-architecture/` for detailed architecture documentation.

## License

MIT
```

**Create `CONTRIBUTING.md`:**
```markdown
# Contributing to workflow-mcp

## Development Workflow

1. **Create feature branch:**
   ```bash
   git checkout -b 001-feature-name
   ```

2. **Follow TDD approach:**
   - Write test first (RED)
   - Implement feature (GREEN)
   - Refactor (REFACTOR)

3. **Commit with Conventional Commits:**
   ```bash
   git commit -m "feat(scope): description"
   git commit -m "test(scope): description"
   ```

4. **Run tests and linting:**
   ```bash
   make test
   make lint
   ```

5. **Create pull request**

## Commit Message Format

- `feat(scope):` - New feature
- `fix(scope):` - Bug fix
- `refactor(scope):` - Code restructuring
- `test(scope):` - Test addition/modification
- `docs(scope):` - Documentation
- `chore(scope):` - Maintenance

## Code Standards

- **Type hints:** All functions must have type hints
- **Docstrings:** Public functions must have docstrings
- **Test coverage:** Maintain >80% coverage
- **mypy:** Code must pass `mypy --strict`
- **Line length:** Max 100 characters
```

**Git commits:**
```bash
git add README.md CONTRIBUTING.md
git commit -m "docs: add README and contributing guide"
```

---

#### 9. Installation and Verification (2 hours)

**Install and test:**
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install package
pip install -e ".[dev]"

# Run database setup
make db-setup

# Verify database
make db-verify

# Run tests
make test

# Run linting
make lint

# Start server (manual test)
make run
# In another terminal, test health check:
# curl http://localhost:8002/health
```

**Git commits:**
```bash
git add .
git commit -m "chore: complete Phase 0 setup and verification"
git tag v0.1.0-phase0
```

---

### Phase 0A Summary

**Total Time:** ~25 hours

**Deliverables:**
- ✅ Repository initialized with proper structure
- ✅ FastMCP server boilerplate with health check
- ✅ Database setup scripts with verification
- ✅ CI/CD pipeline configured
- ✅ Development tools (Makefile, VSCode, linting)
- ✅ Comprehensive documentation
- ✅ All tests passing (1 test: health_check)
- ✅ Ready for Phase 1 implementation

**Git History:**
```
v0.1.0-phase0 - chore: complete Phase 0 setup and verification
├── docs: add README and contributing guide
├── chore: add development tools configuration
├── ci: add GitHub Actions workflows
├── chore(db): add database setup scripts
├── test(server): add health check test
├── feat(server): add FastMCP server boilerplate
├── chore: create base directory structure
├── chore: add project configuration
└── chore: initialize workflow-mcp repository
```

---

## Phase 0B: codebase-mcp Preparation (Existing Repository)

**Duration:** Parallel with Phase 0A (15 hours)

### Deliverables Checklist

#### 1. Performance Baseline Collection (3 hours)

**Create `scripts/collect_baseline.sh`:**
```bash
#!/bin/bash
set -e

echo "📊 Collecting performance baseline for codebase-mcp..."

# Ensure test repository exists
if [ ! -d "test_repos/baseline_repo" ]; then
    echo "Creating baseline test repository (10,000 files)..."
    python scripts/generate_test_repo.py --files 10000 --output test_repos/baseline_repo
fi

# Run baseline benchmarks
pytest tests/performance/test_baseline.py \
    --benchmark-only \
    --benchmark-json=baseline-results.json \
    -v

echo "✅ Baseline collected: baseline-results.json"
echo ""
echo "Key metrics:"
python scripts/parse_baseline.py baseline-results.json
```

**Create `scripts/generate_test_repo.py`:**
```python
"""Generate deterministic test repository for benchmarking."""
import argparse
from pathlib import Path


def generate_test_repo(num_files: int, output_dir: Path) -> None:
    """Generate test repository with specified number of Python files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for i in range(num_files):
        file_path = output_dir / f"module_{i:05d}.py"
        content = f'''"""Test module {i}."""

def function_{i}(x: int, y: int) -> int:
    """Calculate something for testing."""
    return x + y + {i}


class Class{i}:
    """Test class {i}."""

    def __init__(self, value: int) -> None:
        self.value = value

    def method(self) -> int:
        """Return value."""
        return self.value + {i}
'''
        file_path.write_text(content)

    print(f"Generated {num_files} files in {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    generate_test_repo(args.files, args.output)
```

**Create `tests/performance/test_baseline.py`:**
```python
"""Baseline performance tests before refactoring."""
import pytest
from pathlib import Path


@pytest.mark.benchmark
def test_indexing_baseline(benchmark):
    """Measure current indexing performance."""
    test_repo = Path("test_repos/baseline_repo")

    def index_repo():
        # TODO: Call current index_repository implementation
        pass

    result = benchmark(index_repo)
    # Target: <60s for 10k files
    assert result < 60.0, f"Indexing took {result}s (target: <60s)"


@pytest.mark.benchmark
def test_search_baseline(benchmark):
    """Measure current search performance."""

    def search():
        # TODO: Call current search_code implementation
        pass

    result = benchmark(search)
    # Target: <500ms p95
    assert result < 0.5, f"Search took {result}s (target: <0.5s)"
```

**Git commits:**
```bash
git add scripts/collect_baseline.sh scripts/generate_test_repo.py
git commit -m "chore(perf): add baseline collection scripts"

git add tests/performance/test_baseline.py
git commit -m "test(perf): add baseline performance tests"
```

---

#### 2. Refactor Branch Preparation (2 hours)

**Create refactor branch:**
```bash
# Ensure main is clean
git checkout main
git status

# Create refactor branch
git checkout -b 004-multi-project-refactor

# Create rollback tag
git tag backup-before-refactor
git push origin backup-before-refactor
```

**Create `scripts/emergency_rollback.sh`:**
```bash
#!/bin/bash
set -e

echo "⚠️  EMERGENCY ROLLBACK"
echo "This will revert codebase-mcp to pre-refactor state."
echo ""
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Rollback cancelled."
    exit 0
fi

# Stash any uncommitted changes
git stash

# Return to main
git checkout main

# Reset to backup tag
git reset --hard backup-before-refactor

echo "✅ Rollback complete"
echo "Repository restored to: $(git log -1 --oneline)"
```

**Git commits:**
```bash
git add scripts/emergency_rollback.sh
git commit -m "chore: add emergency rollback script"
```

---

#### 3. Database Validation (2 hours)

**Create `scripts/validate_db_permissions.sh`:**
```bash
#!/bin/bash
set -e

echo "🔍 Validating PostgreSQL setup for multi-project..."

# Check PostgreSQL version
PG_VERSION=$(psql --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
MAJOR_VERSION=$(echo $PG_VERSION | cut -d. -f1)

if [ "$MAJOR_VERSION" -lt 14 ]; then
    echo "❌ PostgreSQL version $PG_VERSION is too old (need 14+)"
    exit 1
fi
echo "✅ PostgreSQL version $PG_VERSION"

# Check pgvector extension
if psql -U mcp_user -d postgres -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null; then
    echo "✅ pgvector extension available"
else
    echo "❌ pgvector extension NOT available"
    echo "   Install: brew install pgvector"
    exit 1
fi

# Check CREATEDB permission
if psql -U mcp_user -d postgres -c "CREATE DATABASE temp_test_db;" 2>/dev/null; then
    psql -U mcp_user -d postgres -c "DROP DATABASE temp_test_db;"
    echo "✅ mcp_user has CREATEDB permission"
else
    echo "❌ mcp_user does NOT have CREATEDB permission"
    echo "   Fix: psql -U postgres -c \"ALTER ROLE mcp_user CREATEDB;\""
    exit 1
fi

# Test dynamic database creation
TEST_DB="test_multiproject_$(date +%s)"
psql -U mcp_user -d postgres -c "CREATE DATABASE $TEST_DB;"
psql -U mcp_user -d $TEST_DB -c "CREATE SCHEMA codebase;"
psql -U mcp_user -d $TEST_DB -c "CREATE TABLE codebase.test (id SERIAL);"
psql -U mcp_user -d postgres -c "DROP DATABASE $TEST_DB;"
echo "✅ Dynamic database creation works"

echo ""
echo "🎉 Database validation complete!"
```

**Git commits:**
```bash
git add scripts/validate_db_permissions.sh
git commit -m "chore(db): add database permission validation"
```

---

#### 4. Documentation Updates (3 hours)

**Create `docs/REFACTORING-JOURNAL.md`:**
```markdown
# Refactoring Journal

## Phase 0: Preparation (2025-10-11)

### Goals
- Collect performance baseline
- Validate database permissions
- Create rollback procedures
- Document pre-refactor state

### Baseline Metrics
- Indexing: [TBD after collection]
- Search latency: [TBD after collection]
- Tool count: 16 tools
- Lines of code: ~4,500

### Pre-Refactor State
- Branch: 004-multi-project-refactor
- Backup tag: backup-before-refactor
- Database: Single monolithic database

---

## Phase 1-12: [To be filled during implementation]
```

**Update `README.md`:**
```markdown
# codebase-mcp

> **⚠️ REFACTORING IN PROGRESS**
> This MCP is being refactored to focus exclusively on semantic code search
> with multi-project support. See `docs/REFACTORING-JOURNAL.md` for status.

## Current Status

**Phase 0: Preparation** ✅ (Complete)
- Performance baseline collected
- Database permissions validated
- Rollback procedures ready

**Phase 1-12: Refactoring** 🚧 (In Progress)
- Removing non-search features
- Adding multi-project support
- Target: 16 → 2 tools, 4500 → 1800 LOC

## Rollback

If issues occur during refactoring:

```bash
./scripts/emergency_rollback.sh
```

This restores to tag: `backup-before-refactor`
```

**Git commits:**
```bash
git add docs/REFACTORING-JOURNAL.md README.md
git commit -m "docs: add refactoring journal and update README"
```

---

#### 5. Dependencies Update (2 hours)

**Update `pyproject.toml` to add Phase 0 tools:**
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "pytest-benchmark>=4.0.0",  # Added for performance testing
    "mypy>=1.7.0",
    "ruff>=0.1.0",
]
```

**Reinstall with new dependencies:**
```bash
pip install -e ".[dev]"
```

**Git commits:**
```bash
git add pyproject.toml
git commit -m "chore: add pytest-benchmark for performance testing"
```

---

#### 6. Phase 0 Execution and Verification (3 hours)

**Run all Phase 0 scripts:**
```bash
# Validate database
./scripts/validate_db_permissions.sh

# Generate test repository
python scripts/generate_test_repo.py --files 10000 --output test_repos/baseline_repo

# Collect baseline
./scripts/collect_baseline.sh

# Verify baseline results
ls -lh baseline-results.json
```

**Create Phase 0 completion checklist:**
```bash
cat > PHASE-0-CHECKLIST.md << 'EOF'
# Phase 0 Completion Checklist

## codebase-mcp Preparation

- [ ] Performance baseline collected
- [ ] Test repository generated (10,000 files)
- [ ] Database permissions validated (CREATEDB)
- [ ] pgvector extension available
- [ ] Refactor branch created (004-multi-project-refactor)
- [ ] Rollback tag created (backup-before-refactor)
- [ ] Emergency rollback script tested
- [ ] Documentation updated
- [ ] Dependencies installed
- [ ] All Phase 0 scripts executable

## Sign-Off

Baseline metrics recorded:
- Indexing time: ________ seconds (target: <60s)
- Search p95: ________ ms (target: <500ms)
- Tool count: 16 (target after refactor: 2)
- LOC: ~4,500 (target after refactor: ~1,800)

Ready for Phase 1: [ ] YES / [ ] NO

Notes:
_______________________________________________
_______________________________________________
EOF
```

**Git commits:**
```bash
git add PHASE-0-CHECKLIST.md
git commit -m "chore: add Phase 0 completion checklist"
git tag v2.0.0-phase0-prep
```

---

### Phase 0B Summary

**Total Time:** ~15 hours (parallel with Phase 0A)

**Deliverables:**
- ✅ Performance baseline collected
- ✅ Test repository generated (10,000 files)
- ✅ Database permissions validated
- ✅ Refactor branch created with rollback protection
- ✅ Emergency rollback procedures
- ✅ Documentation updated
- ✅ Ready for Phase 1 refactoring

**Git History:**
```
v2.0.0-phase0-prep - chore: add Phase 0 completion checklist
├── chore: add pytest-benchmark
├── docs: add refactoring journal
├── chore(db): add database validation
├── chore: add emergency rollback script
├── test(perf): add baseline tests
└── chore(perf): add baseline collection scripts
```

---

## Phase 0 Combined Timeline

### Week 0: Foundation Setup

| Day | workflow-mcp (New) | codebase-mcp (Prep) | Hours |
|-----|-------------------|---------------------|-------|
| Mon | Repo init + config | Baseline scripts | 8h |
| Tue | FastMCP boilerplate | Baseline collection | 8h |
| Wed | Database setup | DB validation | 8h |
| Thu | CI/CD pipeline | Branch prep + docs | 8h |
| Fri | Docs + verification | Verification + sign-off | 8h |

**Total:** 40 hours (5 days × 8 hours)

---

## Success Criteria for Phase 0

### workflow-mcp
- ✅ Repository initialized with complete structure
- ✅ FastMCP server starts successfully
- ✅ Health check endpoint returns 200 OK
- ✅ Database setup scripts execute without errors
- ✅ CREATEDB permission verified
- ✅ CI/CD pipeline runs and passes
- ✅ All tests passing (1 test)
- ✅ Documentation complete

### codebase-mcp
- ✅ Performance baseline collected and stored
- ✅ Baseline meets current targets (<60s indexing, <500ms search)
- ✅ Database permissions validated (CREATEDB, pgvector)
- ✅ Refactor branch created from main
- ✅ Rollback tag created and pushed
- ✅ Emergency rollback script tested
- ✅ Documentation updated with refactor status

---

## Phase 0 Outputs

### workflow-mcp Outputs
```
workflow-mcp/
├── .github/workflows/           # CI/CD pipelines
├── .vscode/                     # VSCode settings
├── docs/                        # Documentation
├── scripts/                     # Setup scripts
│   ├── setup_database.sh
│   └── verify_database.sh
├── src/workflow_mcp/           # Source code
│   ├── __init__.py
│   ├── server.py               # FastMCP server
│   ├── config.py               # Settings
│   ├── models/
│   ├── services/
│   ├── tools/
│   └── utils/
├── tests/                      # Test suite
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── performance/
├── .env.template               # Config template
├── .gitignore
├── .python-version
├── CONTRIBUTING.md
├── LICENSE
├── Makefile
├── pyproject.toml
└── README.md
```

### codebase-mcp Outputs
```
codebase-mcp/
├── baseline-results.json       # Performance baseline
├── test_repos/baseline_repo/   # 10,000 test files
├── scripts/
│   ├── collect_baseline.sh
│   ├── generate_test_repo.py
│   ├── emergency_rollback.sh
│   └── validate_db_permissions.sh
├── docs/
│   └── REFACTORING-JOURNAL.md
├── PHASE-0-CHECKLIST.md
└── [existing structure]
```

---

## Next Steps After Phase 0

### 1. Review Phase 0 Outputs
- [ ] Verify workflow-mcp health check works
- [ ] Review codebase-mcp baseline metrics
- [ ] Confirm database permissions
- [ ] Test rollback procedures

### 2. Begin Phase 1: workflow-mcp Core
```bash
cd workflow-mcp
git checkout -b 001-project-management-core

# Use /specify with prepared prompt
cat ../codebase-mcp/docs/mcp-split-plan/02-workflow-mcp/specify-prompt.txt
/specify [paste content]
```

### 3. Parallel Work (Optional)
If confident, can start codebase-mcp Phase 1 while workflow-mcp Phase 1 develops:
```bash
cd codebase-mcp
# Already on branch: 004-multi-project-refactor

# Begin removing features (Phase 1-2)
```

---

## Rollback Procedures

### workflow-mcp Rollback
```bash
cd workflow-mcp
git reset --hard HEAD    # Discard all changes
# Or delete repository and re-run Phase 0
```

### codebase-mcp Rollback
```bash
cd codebase-mcp
./scripts/emergency_rollback.sh
# Or manually:
git checkout main
git reset --hard backup-before-refactor
```

---

## Phase 0 Risk Mitigation

| Risk | Mitigation | Status |
|------|-----------|--------|
| CREATEDB permission denied | Validate early in Phase 0 | ✅ Scripted |
| pgvector not installed | Check during DB validation | ✅ Scripted |
| Baseline collection fails | Use generated test repo | ✅ Deterministic |
| CI/CD pipeline errors | Test with simple health check | ✅ Minimal |
| Rollback fails | Multiple rollback methods | ✅ Documented |

---

## Conclusion

Phase 0 establishes a **solid foundation** for both MCPs:

- **workflow-mcp** gets complete infrastructure (repo, server, CI/CD, docs)
- **codebase-mcp** gets preparation and protection (baseline, rollback, validation)

**After Phase 0:**
- ✅ Can confidently begin Phase 1 implementation
- ✅ Have rollback procedures if issues occur
- ✅ Have baseline to detect performance regressions
- ✅ Have CI/CD to catch issues early

**Time Investment:** 1 week (40 hours)
**Risk Reduction:** High (catches infrastructure issues before implementation)
**Recommendation:** **STRONGLY RECOMMENDED** before Phase 1

---

**Status:** Ready for approval and execution
**Last Updated:** 2025-10-11
**Version:** 1.0.0
