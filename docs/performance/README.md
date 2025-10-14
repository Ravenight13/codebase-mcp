# Performance Documentation

This directory contains performance testing documentation, reports, and analysis for the codebase-mcp project.

## Directory Structure

```
docs/performance/
├── README.md           # This file
├── DEPENDENCIES.md     # Required dependencies for performance testing
├── *.html              # Generated performance reports (gitignored)
└── *.json              # Generated performance data (gitignored)
```

## Purpose

This directory houses:
1. **Documentation**: Guides for running performance tests
2. **Reports**: Generated HTML/JSON reports from load tests (temporary, not committed)
3. **Analysis**: Performance analysis and findings

## Performance Baselines vs Reports

- **Baselines** (`performance_baselines/`): Committed baseline measurements for regression testing
- **Reports** (`docs/performance/`): Temporary test reports and analysis (gitignored)

## Available Documentation

### DEPENDENCIES.md
Complete guide to all performance testing dependencies:
- Python packages (pytest-benchmark, pytest-asyncio, httpx)
- External tools (k6 for load testing)
- Installation instructions
- Verification steps

### Coming Soon
- `LOAD_TESTING.md` - Load testing guide (Task T006)
- `BENCHMARKING.md` - Benchmark testing guide (Task T007)
- Performance analysis reports

## Quick Start

1. **Install dependencies**:
   ```bash
   # Python dependencies
   pip install -e '.[dev]'

   # k6 (macOS)
   brew install k6
   ```

2. **Run performance tests**:
   ```bash
   # Benchmark tests
   pytest tests/benchmarks/ --benchmark-only

   # Load tests (when implemented)
   k6 run tests/load/mcp_load_test.js
   ```

3. **View reports**:
   Reports will be generated in this directory as HTML/JSON files.

## Performance Targets

From Constitutional Principle IV:
- **Indexing**: <60 seconds for 10,000 files
- **Search**: <500ms p95 latency
- **Connection pool**: <2s initialization, <10ms acquisition

See `specs/011-performance-validation-multi/spec.md` for detailed requirements.

## Related Documentation

- **Baselines**: `performance_baselines/README.md`
- **Feature Spec**: `specs/011-performance-validation-multi/spec.md`
- **Test Code**: `tests/benchmarks/` and `tests/load/`

## Constitutional Compliance

- **Principle IV**: Performance Guarantees (60s indexing, 500ms search)
- **Principle VII**: Test-Driven Development (performance regression tests)
