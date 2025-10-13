"""Performance benchmarks for connection pool and critical operations.

This package contains pytest-benchmark tests for establishing performance
baselines and detecting regressions in critical system components.

**Benchmark Categories**:
- Connection Pool: Initialization, acquisition, health checks, shutdown
- Database Operations: Query execution, transaction handling (future)
- MCP Protocol: Request/response latency (future)

**Constitutional Compliance**:
- Principle IV (Performance): Validates performance targets in CI/CD
- Principle VII (TDD): Benchmarks as performance regression tests
- Principle VIII (Type Safety): Full mypy --strict compliance
"""
