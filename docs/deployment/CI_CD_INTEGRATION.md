# CI/CD Integration Guide

## Overview

Integrate Codebase MCP Server Docker build and test into CI/CD pipelines.

## GitHub Actions Example

```yaml
name: Docker Build and Test

on: [push, pull_request]

jobs:
  build-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker image
        run: docker build -t codebase-mcp:${{ github.sha }} .
      
      - name: Start services
        run: docker-compose -f docker-compose.test.yml up -d
      
      - name: Run tests
        run: docker-compose -f docker-compose.test.yml exec -T codebase-mcp pytest -v
      
      - name: Cleanup
        if: always()
        run: docker-compose -f docker-compose.test.yml down -v
```

## Layer Caching

Docker layer caching improves build speed:

**First build** (dependencies): ~2-3 minutes
**Code-only changes**: <30 seconds

**Ensure efficient caching**:
```dockerfile
# ✅ GOOD: Dependencies installed before code copied
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src/ /app/src/  # Code changes don't invalidate dependency cache

# ❌ BAD: Code mixed with dependencies
COPY . /app
RUN pip install -r requirements.txt
```

## Test Execution

```bash
# Run full test suite
docker-compose -f docker-compose.test.yml exec codebase-mcp pytest -v

# Run with coverage
docker-compose -f docker-compose.test.yml exec codebase-mcp pytest --cov=src -v

# Run specific tests
docker-compose -f docker-compose.test.yml exec codebase-mcp pytest tests/integration/ -v
```

## Artifact Collection

```bash
# Extract coverage report
docker-compose -f docker-compose.test.yml exec codebase-mcp cat coverage.xml > coverage.xml

# Upload to Codecov
curl -s https://codecov.io/bash | bash -s -- -f coverage.xml
```

## Performance Targets

- **Build**: <2 minutes (with cache), <30s (code-only)
- **Tests**: <5 minutes total
- **Image size**: <500 MB
- **Startup**: <120 seconds

