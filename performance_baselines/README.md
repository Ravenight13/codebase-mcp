# Performance Baselines

This directory contains performance baseline measurements for critical system operations.

## Connection Pool Baseline

**File**: `connection_pool_baseline.json`

Contains performance metrics for connection pool operations, used for regression testing.

### Baseline Structure

```json
{
  "collection_date": "2025-10-13T14:30:00Z",
  "machine_info": {
    "node": "hostname",
    "processor": "Apple M1",
    "python_version": "3.11.0"
  },
  "benchmarks": {
    "test_benchmark_pool_initialization": {
      "description": "Pool initialization time",
      "mean_ms": 125.5,
      "stddev_ms": 12.3,
      "median_ms": 123.0,
      "p50_ms": 123.0,
      "p95_ms": 145.2,
      "p99_ms": 158.7,
      "min_ms": 110.2,
      "max_ms": 162.4,
      "iterations": 10
    },
    ...
  }
}
```

### Performance Targets

From `specs/009-v2-connection-mgmt/spec.md`:

- **Pool initialization**: <2s (2000ms)
- **Connection acquisition (single)**: <10ms p95
- **Connection acquisition (concurrent)**: <10ms p95
- **Health check**: <10ms p99
- **Graceful shutdown**: <30s (30000ms)

### Collecting Baseline

Run from repository root:

```bash
./scripts/collect_connection_pool_baseline.sh
```

This will:
1. Run all connection pool benchmarks
2. Generate `connection_pool_baseline.json`
3. Validate against performance targets
4. Display summary report

### Regression Testing

Compare current performance against baseline:

```bash
# Run benchmarks and compare (warning only)
pytest tests/benchmarks/test_connection_pool_benchmarks.py --benchmark-only \
    --benchmark-compare=performance_baselines/connection_pool_baseline.json

# Fail if performance degrades >10% from baseline
pytest tests/benchmarks/test_connection_pool_benchmarks.py --benchmark-only \
    --benchmark-compare=performance_baselines/connection_pool_baseline.json \
    --benchmark-compare-fail=mean:10%

# Fail if p95 latency degrades >15%
pytest tests/benchmarks/test_connection_pool_benchmarks.py --benchmark-only \
    --benchmark-compare=performance_baselines/connection_pool_baseline.json \
    --benchmark-compare-fail=mean:10%,p95:15%
```

### CI/CD Integration

Add to `.github/workflows/performance.yml`:

```yaml
name: Performance Benchmarks

on:
  pull_request:
    branches: [main, master]

jobs:
  benchmarks:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: codebase_mcp_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -e '.[dev]'

      - name: Run benchmarks
        env:
          TEST_DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost/codebase_mcp_test
        run: |
          pytest tests/benchmarks/test_connection_pool_benchmarks.py --benchmark-only \
            --benchmark-compare=performance_baselines/connection_pool_baseline.json \
            --benchmark-compare-fail=mean:10%
```

### Updating Baseline

When intentional performance changes are made (optimizations, feature additions):

1. Collect new baseline: `./scripts/collect_connection_pool_baseline.sh`
2. Review changes: `git diff performance_baselines/connection_pool_baseline.json`
3. Commit updated baseline: `git add performance_baselines/connection_pool_baseline.json`
4. Document reason in commit message

### Interpreting Results

#### Metrics Explanation

- **mean_ms**: Average latency across all iterations
- **median_ms** (p50): 50th percentile (middle value)
- **p95_ms**: 95th percentile (95% of requests faster than this)
- **p99_ms**: 99th percentile (99% of requests faster than this)
- **stddev_ms**: Standard deviation (variability)
- **min/max_ms**: Fastest/slowest measurements

#### Performance Degradation

If benchmarks fail:

1. **Investigate**: Check recent code changes that might impact performance
2. **Profile**: Use `py-spy` to identify bottlenecks
3. **Optimize**: Apply targeted optimizations
4. **Re-baseline**: If changes are intentional, update baseline

#### Example Output

```
test_benchmark_connection_acquisition_single
  Mean:   2.35 ms
  Median: 2.20 ms (p50)
  p95:    3.45 ms  ✓ (target: <10ms)
  p99:    4.12 ms
  Min:    1.89 ms
  Max:    5.67 ms
```

### Machine-Specific Considerations

Baselines are machine-specific (CPU, memory, disk speed). For CI/CD:

- Use consistent runner hardware
- Store baseline per runner type
- Allow tolerances (±10-20%) for variance

### Constitutional Compliance

- **Principle IV (Performance)**: Validates performance guarantees
- **Principle VII (TDD)**: Benchmarks as regression tests
- **Principle X (Git Micro-Commit)**: Baseline committed to repository
