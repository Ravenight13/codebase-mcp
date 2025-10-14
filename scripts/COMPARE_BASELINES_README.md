# Baseline Comparison Script - Hybrid Regression Detection

## Overview

`compare_baselines.py` implements hybrid regression detection for performance validation as specified in feature 011 research.md lines 268-305. The script compares two baseline JSON files (pre-split and post-split) to detect performance regressions using a dual-threshold approach.

## Hybrid Regression Logic

The script flags a performance regression **ONLY** if **BOTH** conditions are met:

1. **Degradation Check**: Current metric exceeds baseline by >10%
2. **Constitutional Check**: Current metric exceeds constitutional target

This approach allows minor degradation within constitutional targets while preventing significant regressions that violate performance guarantees.

## Constitutional Performance Targets

From `.specify/memory/constitution.md` and `spec.md`:

| Operation Type | Constitutional Target (p95) |
|----------------|----------------------------|
| `index` | <60 seconds (60,000ms) |
| `search` | <500 milliseconds |
| `project_switch` | <50 milliseconds |
| `entity_query` | <100 milliseconds |

## Usage

### Basic Comparison

```bash
python scripts/compare_baselines.py pre-split.json post-split.json
```

### Verbose Mode (Show Detailed Metrics)

```bash
python scripts/compare_baselines.py pre-split.json post-split.json --verbose
```

### Save JSON Report

```bash
python scripts/compare_baselines.py pre-split.json post-split.json --output report.json
```

### Combined Options

```bash
python scripts/compare_baselines.py pre-split.json post-split.json --verbose --output report.json
```

## Exit Codes

- **0**: All metrics pass (no regressions detected)
- **1**: One or more metrics failed regression checks

## Output Interpretation

### PASS (✓)

```
✓ PASS: Within baseline (8.5% change) and constitutional target (430.00ms < 500.00ms)
```

Both conditions satisfied:
- Metric is within 10% of baseline
- Metric is below constitutional target

**Action**: None required. Performance is acceptable.

---

### WARNING (⚠) - Scenario 1: Baseline Exceeded, Target Met

```
⚠ WARNING: Exceeds baseline by 14.6% but within constitutional target (55000.00ms < 60000.00ms). Acceptable degradation.
```

Conditions:
- Metric exceeds baseline by >10%
- Metric is still below constitutional target

**Action**: Review performance, but deployment not blocked. This is acceptable degradation per FR-018.

---

### WARNING (⚠) - Scenario 2: Target Exceeded, Baseline Met

```
⚠ WARNING: Exceeds constitutional target (520.00ms > 500.00ms) but within baseline variance (8.2% change). Baseline may need adjustment.
```

Conditions:
- Metric is within 10% of baseline
- Metric exceeds constitutional target

**Action**: Review baseline accuracy. Target violation without significant degradation suggests baseline was already non-compliant.

---

### FAIL (✗) - Regression Detected

```
✗ FAIL: REGRESSION DETECTED. Exceeds baseline by 41.7% AND exceeds constitutional target (68000.00ms > 60000.00ms). This violates performance guarantees.
```

Both conditions met:
- Metric exceeds baseline by >10%
- Metric exceeds constitutional target

**Action**: BLOCK deployment. Investigate and resolve performance regression before proceeding.

## Baseline JSON Format

Baselines use `PerformanceBenchmarkResult` model from `src/models/performance.py`:

```json
{
  "version": "1.0",
  "timestamp": "2025-10-13T10:00:00Z",
  "benchmarks": [
    {
      "benchmark_id": "550e8400-e29b-41d4-a716-446655440000",
      "server_id": "codebase-mcp",
      "operation_type": "index",
      "timestamp": "2025-10-13T10:00:00Z",
      "latency_p50_ms": 45000.00,
      "latency_p95_ms": 48000.00,
      "latency_p99_ms": 52000.00,
      "latency_mean_ms": 46000.00,
      "latency_min_ms": 42000.00,
      "latency_max_ms": 55000.00,
      "sample_size": 5,
      "test_parameters": {
        "file_count": 10000,
        "repository": "test-repo"
      },
      "pass_status": "pass",
      "target_threshold_ms": 60000.0
    }
  ]
}
```

### Required Fields

- `version`: Baseline format version (string)
- `timestamp`: When baseline was created (ISO 8601 string)
- `benchmarks`: Array of benchmark results (array)

### Benchmark Result Fields

- `benchmark_id`: Unique identifier (UUID string)
- `server_id`: Either "codebase-mcp" or "workflow-mcp"
- `operation_type`: One of "index", "search", "project_switch", "entity_query"
- `timestamp`: When benchmark was executed (ISO 8601 string)
- `latency_p50_ms`: 50th percentile latency (Decimal)
- `latency_p95_ms`: 95th percentile latency (Decimal) - **PRIMARY COMPARISON METRIC**
- `latency_p99_ms`: 99th percentile latency (Decimal)
- `latency_mean_ms`: Mean latency (Decimal)
- `latency_min_ms`: Minimum latency (Decimal)
- `latency_max_ms`: Maximum latency (Decimal)
- `sample_size`: Number of iterations (integer)
- `test_parameters`: Test-specific parameters (object)
- `pass_status`: "pass", "fail", or "warning"
- `target_threshold_ms`: Constitutional target for this operation (Decimal, optional)

## Example Scenarios

### Scenario 1: All Metrics Pass

**Pre-split**: Indexing p95 = 48,000ms
**Post-split**: Indexing p95 = 50,000ms
**Target**: 60,000ms

**Result**: PASS (4.2% degradation, within target)

### Scenario 2: Acceptable Degradation

**Pre-split**: Search p95 = 380ms
**Post-split**: Search p95 = 430ms
**Target**: 500ms

**Result**: WARNING (13.2% degradation, but within target)
**Exit Code**: 0 (Success)

### Scenario 3: Regression Detected

**Pre-split**: Indexing p95 = 48,000ms
**Post-split**: Indexing p95 = 68,000ms
**Target**: 60,000ms

**Result**: FAIL (41.7% degradation AND exceeds target)
**Exit Code**: 1 (Failure)

## Integration with CI/CD

### Example GitHub Actions Workflow

```yaml
- name: Compare Performance Baselines
  run: |
    python scripts/compare_baselines.py \
      docs/performance/baseline-pre-split.json \
      docs/performance/baseline-post-split.json \
      --output performance-report.json

- name: Upload Performance Report
  if: always()
  uses: actions/upload-artifact@v3
  with:
    name: performance-report
    path: performance-report.json

- name: Fail on Regression
  if: failure()
  run: |
    echo "Performance regression detected!"
    cat performance-report.json
    exit 1
```

## Type Safety

The script is fully type-safe and passes `mypy --strict` validation:

```bash
mypy --strict scripts/compare_baselines.py
# Success: no issues found in 1 source file
```

## Constitutional Compliance

This script implements:

- **Principle IV**: Performance Guarantees (constitutional targets enforcement)
- **Principle VIII**: Pydantic-Based Type Safety (mypy --strict compliance)
- **Principle V**: Production Quality (comprehensive error handling)
- **FR-018**: Hybrid approach for regression detection (spec.md)

## Troubleshooting

### Error: File not found

```
Error: Baseline file not found: pre-split.json
```

**Solution**: Verify file paths are correct and files exist.

### Error: Invalid JSON

```
Error: Invalid JSON: Expecting value: line 1 column 1 (char 0)
```

**Solution**: Validate JSON syntax. Use `jq` to check:

```bash
jq . baseline.json
```

### Error: Invalid baseline format

```
Error: Invalid baseline format: 1 validation error for BaselineFile
```

**Solution**: Verify baseline matches expected schema. Check:
- All required fields present
- Field types match specification
- `operation_type` is one of valid values

## Related Files

- `/Users/cliffclarke/Claude_Code/codebase-mcp/src/models/performance.py` - Performance model definitions
- `/Users/cliffclarke/Claude_Code/codebase-mcp/specs/011-performance-validation-multi/research.md` - Hybrid regression logic research (lines 268-305)
- `/Users/cliffclarke/Claude_Code/codebase-mcp/specs/011-performance-validation-multi/spec.md` - Feature specification (FR-018)

## Testing

Run the script with sample baselines to verify functionality:

```bash
# Create test baselines
python scripts/generate_test_baselines.py

# Run comparison
python scripts/compare_baselines.py \
  /tmp/test_pre_split_baseline.json \
  /tmp/test_post_split_baseline.json \
  --verbose
```
