# Codebase MCP Performance Benchmarks

This directory contains performance benchmarks for validating constitutional performance targets for the codebase-mcp server.

## Overview

Performance benchmarks use `pytest-benchmark` to measure and validate system performance against constitutional guarantees defined in `.specify/memory/constitution.md`.

## Benchmark Categories

### 1. Indexing Performance (`test_indexing_perf.py`)
- **Target**: Index 10,000 files in <60s (p95) - Constitutional Principle IV
- **Iterations**: 5 benchmark runs with 1 warmup round
- **Validates**: FR-001 from specs/011-performance-validation-multi/spec.md

### 2. Search Performance (`test_search_perf.py`)
- **Target**: Search latency <500ms (p95) - Constitutional Principle IV
- **Validates**: FR-002 from specs/011-performance-validation-multi/spec.md

### 3. Workflow MCP Performance (`test_workflow_perf.py`)
- **Target**: Project switching <50ms (p95) - Constitutional Principle IV
- **Validates**: FR-003, FR-004 from specs/011-performance-validation-multi/spec.md

## Running Benchmarks

### Run All Benchmarks
```bash
# Run all benchmarks with statistics
pytest tests/benchmarks/ --benchmark-only -v

# Save results to JSON baseline
pytest tests/benchmarks/ --benchmark-only \
    --benchmark-json=performance_baselines/benchmark_results.json
```

### Run Specific Benchmark Suite
```bash
# Indexing benchmarks only
pytest tests/benchmarks/test_indexing_perf.py --benchmark-only -v

# Search benchmarks only
pytest tests/benchmarks/test_search_perf.py --benchmark-only -v

# Workflow benchmarks only
pytest tests/benchmarks/test_workflow_perf.py --benchmark-only -v
```

### Compare Against Baseline
```bash
# Compare current run against saved baseline
pytest tests/benchmarks/test_indexing_perf.py --benchmark-only \
    --benchmark-compare=performance_baselines/indexing_baseline.json \
    --benchmark-compare-fail=mean:10%
```

### Generate Performance Report
```bash
# Run with histogram visualization
pytest tests/benchmarks/ --benchmark-only \
    --benchmark-histogram=performance_reports/histogram

# Run with table output
pytest tests/benchmarks/ --benchmark-only \
    --benchmark-columns=min,max,mean,stddev,median,ops,rounds
```

## Benchmark Architecture

### Test Fixtures (`conftest.py`)
- `test_engine`: Function-scoped async database engine
- `session`: Function-scoped async database session with automatic rollback
- `benchmark_repository`: Generated 10,000-file test repository

### Test Repository Generation
Benchmarks use synthetic repositories generated via `tests/fixtures/test_repository.py`:
- **File count**: 10,000 files (60% Python, 40% JavaScript)
- **File sizes**: 100 bytes to 50KB (realistic distribution)
- **Directory depth**: Up to 5 levels (matches production codebases)
- **Code complexity**: Functions, classes, imports (tree-sitter validated syntax)

### Performance Validation Model
All benchmarks create `PerformanceBenchmarkResult` instances (from `src/models/performance.py`) to:
- Store benchmark results with Decimal precision
- Validate percentile ordering (p50 ≤ p95 ≤ p99)
- Determine pass/fail status against constitutional targets
- Enable regression detection across benchmark runs

## Constitutional Compliance

Benchmarks validate these constitutional principles:

- **Principle IV**: Performance Guarantees
  - Indexing: <60s (p95) for 10,000 files
  - Search: <500ms (p95)
  - Project switching: <50ms (p95)
  - Entity queries: <100ms (p95)

- **Principle VII**: TDD (Test-Driven Development)
  - Benchmarks serve as performance regression tests
  - Fail fast when performance degrades

- **Principle VIII**: Type Safety
  - Full mypy --strict compliance
  - Pydantic models for benchmark results

## Benchmark Results Format

Each benchmark generates a `PerformanceBenchmarkResult` with:

```python
{
    "benchmark_id": "uuid",
    "server_id": "codebase-mcp" | "workflow-mcp",
    "operation_type": "index" | "search" | "project_switch" | "entity_query",
    "timestamp": "2025-10-13T10:30:00Z",
    "latency_p50_ms": Decimal("245.32"),
    "latency_p95_ms": Decimal("478.91"),
    "latency_p99_ms": Decimal("512.45"),
    "latency_mean_ms": Decimal("268.77"),
    "latency_min_ms": Decimal("198.12"),
    "latency_max_ms": Decimal("543.88"),
    "sample_size": 5,
    "test_parameters": {
        "file_count": 10000,
        "iterations": 5
    },
    "pass_status": "pass" | "warning" | "fail",
    "target_threshold_ms": Decimal("60000.0")
}
```

## Interpreting Results

### Pass/Fail Status
- **pass**: p95 latency < constitutional target
- **warning**: p95 latency < target * 1.1 (within 10% threshold)
- **fail**: p95 latency > target * 1.1 (exceeds acceptable range)

### Variance Validation
Indexing and search benchmarks also validate variance (coefficient of variation):
- **Target**: CV < 5% (consistent performance)
- **Formula**: CV = (stddev / mean) × 100%

## CI/CD Integration

Benchmarks are designed for CI/CD pipeline integration:

```yaml
# .github/workflows/performance.yml
- name: Run Performance Benchmarks
  run: |
    pytest tests/benchmarks/ --benchmark-only \
      --benchmark-json=results.json \
      --benchmark-compare=baselines/baseline.json \
      --benchmark-compare-fail=mean:10%
```

## Troubleshooting

### Slow Benchmark Execution
- Each indexing benchmark takes ~30-60s (by design, testing 10K files)
- Use `--benchmark-only` to skip regular tests
- Consider `--benchmark-skip` when running unit tests

### Database Connection Issues
- Ensure PostgreSQL is running: `pg_isready`
- Check `TEST_DATABASE_URL` environment variable
- Verify database exists: `createdb codebase_mcp_test`

### Event Loop Conflicts
- All async fixtures use function scope (see conftest.py)
- Each benchmark gets fresh engine + session
- No session/module scope async fixtures (prevents loop conflicts)

## References

- **Specification**: `specs/011-performance-validation-multi/spec.md`
- **Quickstart**: `specs/011-performance-validation-multi/quickstart.md`
- **Data Model**: `specs/011-performance-validation-multi/data-model.md`
- **Constitution**: `.specify/memory/constitution.md` (Principle IV)
