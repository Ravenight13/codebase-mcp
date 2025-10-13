#!/usr/bin/env bash
#
# Connection Pool Performance Baseline Collection Script
#
# This script runs pytest-benchmark tests for connection pool operations and
# generates a baseline JSON file for performance regression testing.
#
# **Performance Targets** (from specs/009-v2-connection-mgmt/spec.md):
# - Pool initialization: <2s for 10 connections
# - Connection acquisition: <10ms p95 latency
# - Health check: <10ms p99 latency
# - Graceful shutdown: <30s
#
# **Usage**:
#   # Collect baseline (run from repo root)
#   ./scripts/collect_connection_pool_baseline.sh
#
#   # Run with custom database URL
#   TEST_DATABASE_URL=postgresql+asyncpg://localhost/test_db \
#       ./scripts/collect_connection_pool_baseline.sh
#
# **Outputs**:
#   performance_baselines/connection_pool_baseline.json
#   performance_baselines/connection_pool_benchmark_raw.json (full pytest-benchmark output)
#
# **Performance Regression Testing**:
#   # Run benchmarks and compare against baseline
#   pytest tests/benchmarks/test_connection_pool_benchmarks.py --benchmark-only \
#       --benchmark-compare=performance_baselines/connection_pool_baseline.json \
#       --benchmark-compare-fail=mean:10%
#
#   # Fail CI if performance degrades >10% from baseline (mean)
#   # Fail CI if performance degrades >15% from baseline (p95)
#
# **Constitutional Compliance**:
# - Principle IV (Performance): Validates performance targets
# - Principle V (Production Quality): Comprehensive error handling
# - Principle X (Git Micro-Commit): Baseline file should be committed
#
# **Exit Codes**:
#   0 - Success: Baseline collected and validated
#   1 - Error: Missing dependencies (pytest, pytest-benchmark)
#   2 - Error: Database connection failure
#   3 - Error: Benchmark execution failure
#   4 - Error: Performance target violation (initialization >2s, acquisition >10ms, etc.)

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BASELINE_DIR="${REPO_ROOT}/performance_baselines"
BASELINE_FILE="${BASELINE_DIR}/connection_pool_baseline.json"
RAW_OUTPUT_FILE="${BASELINE_DIR}/connection_pool_benchmark_raw.json"
TEMP_OUTPUT_FILE="${BASELINE_DIR}/connection_pool_benchmark_temp.json"

# Color output for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

# Print header
print_header() {
    echo ""
    echo "================================================================"
    echo " Connection Pool Performance Baseline Collection"
    echo "================================================================"
    echo ""
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if pytest is installed
    if ! command -v pytest &> /dev/null; then
        log_error "pytest is not installed."
        log_error "Install with: pip install -e '.[dev]'"
        exit 1
    fi

    # Check if pytest-benchmark is installed
    if ! python -c "import pytest_benchmark" 2>/dev/null; then
        log_error "pytest-benchmark is not installed."
        log_error "Install with: pip install pytest-benchmark>=4.0.0"
        exit 1
    fi

    # Check if test database URL is set
    if [[ -z "${TEST_DATABASE_URL:-}" ]]; then
        TEST_DATABASE_URL="postgresql+asyncpg://localhost:5432/codebase_mcp_test"
        log_warning "TEST_DATABASE_URL not set, using default: ${TEST_DATABASE_URL}"
    fi

    # Test database connectivity
    log_info "Testing database connectivity: ${TEST_DATABASE_URL}"
    if ! python -c "
import asyncio
import asyncpg
import sys
from urllib.parse import urlparse

url = '${TEST_DATABASE_URL}'.replace('postgresql+asyncpg://', 'postgresql://')
parsed = urlparse(url)

async def test_connection():
    try:
        conn = await asyncpg.connect(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path.lstrip('/') if parsed.path else 'postgres'
        )
        await conn.close()
        return True
    except Exception as e:
        print(f'Connection failed: {e}', file=sys.stderr)
        return False

result = asyncio.run(test_connection())
sys.exit(0 if result else 1)
" 2>/dev/null; then
        log_error "Database connection failed: ${TEST_DATABASE_URL}"
        log_error "Ensure PostgreSQL is running and database exists."
        log_error "Create test database: createdb codebase_mcp_test"
        exit 2
    fi

    log_success "Prerequisites check passed"
}

# Run pytest-benchmark
run_benchmarks() {
    log_info "Running connection pool benchmarks..."
    log_info "Output: ${RAW_OUTPUT_FILE}"

    # Run pytest with benchmark collection
    cd "${REPO_ROOT}"

    if ! TEST_DATABASE_URL="${TEST_DATABASE_URL}" \
        pytest tests/benchmarks/test_connection_pool_benchmarks.py \
        --benchmark-only \
        --benchmark-json="${TEMP_OUTPUT_FILE}" \
        --benchmark-warmup=on \
        --benchmark-disable-gc \
        --benchmark-min-rounds=5 \
        -v; then
        log_error "Benchmark execution failed"
        exit 3
    fi

    # Move temp file to final location
    mv "${TEMP_OUTPUT_FILE}" "${RAW_OUTPUT_FILE}"

    log_success "Benchmarks completed successfully"
}

# Extract baseline metrics
extract_baseline() {
    log_info "Extracting baseline metrics..."

    # Parse pytest-benchmark JSON output and create simplified baseline
    python3 << 'EOF'
import json
import sys
from pathlib import Path

# Read raw benchmark output
raw_file = Path("performance_baselines/connection_pool_benchmark_raw.json")
if not raw_file.exists():
    print("ERROR: Raw benchmark file not found", file=sys.stderr)
    sys.exit(3)

with open(raw_file) as f:
    raw_data = json.load(f)

# Extract baseline metrics
baseline = {
    "collection_date": raw_data.get("datetime", "unknown"),
    "machine_info": {
        "node": raw_data.get("machine_info", {}).get("node", "unknown"),
        "processor": raw_data.get("machine_info", {}).get("processor", "unknown"),
        "python_version": raw_data.get("machine_info", {}).get("python_version", "unknown"),
    },
    "benchmarks": {}
}

for bench in raw_data.get("benchmarks", []):
    name = bench["name"]
    stats = bench["stats"]

    baseline["benchmarks"][name] = {
        "description": bench.get("fullname", name),
        "mean_ms": stats["mean"] * 1000,      # Convert to milliseconds
        "stddev_ms": stats["stddev"] * 1000,
        "median_ms": stats["median"] * 1000,   # p50
        "min_ms": stats["min"] * 1000,
        "max_ms": stats["max"] * 1000,
        "iterations": stats.get("iterations", stats.get("rounds", 0)),
        # Percentiles (if available in stats, otherwise approximate)
        "p50_ms": stats.get("median", stats["median"]) * 1000,
        "p95_ms": stats.get("q_95", stats["max"] * 0.95) * 1000,
        "p99_ms": stats.get("q_99", stats["max"] * 0.99) * 1000,
    }

# Write baseline file
baseline_file = Path("performance_baselines/connection_pool_baseline.json")
with open(baseline_file, "w") as f:
    json.dump(baseline, f, indent=2)

print(f"Baseline saved to: {baseline_file}")

# Print summary
print("\n" + "="*60)
print("Performance Baseline Summary")
print("="*60)
for name, metrics in baseline["benchmarks"].items():
    print(f"\n{name}:")
    print(f"  Mean:   {metrics['mean_ms']:.2f} ms")
    print(f"  Median: {metrics['median_ms']:.2f} ms (p50)")
    print(f"  p95:    {metrics['p95_ms']:.2f} ms")
    print(f"  p99:    {metrics['p99_ms']:.2f} ms")
    print(f"  Min:    {metrics['min_ms']:.2f} ms")
    print(f"  Max:    {metrics['max_ms']:.2f} ms")
print("="*60)
EOF

    if [[ $? -ne 0 ]]; then
        log_error "Failed to extract baseline metrics"
        exit 3
    fi

    log_success "Baseline metrics extracted to: ${BASELINE_FILE}"
}

# Validate performance targets
validate_targets() {
    log_info "Validating performance targets..."

    python3 << 'EOF'
import json
import sys
from pathlib import Path

# Read baseline file
baseline_file = Path("performance_baselines/connection_pool_baseline.json")
with open(baseline_file) as f:
    baseline = json.load(f)

# Performance targets (from spec)
targets = {
    "test_benchmark_pool_initialization": {
        "mean_ms": 2000,  # <2s
        "description": "Pool initialization"
    },
    "test_benchmark_connection_acquisition_single": {
        "p95_ms": 10,  # <10ms p95
        "description": "Single connection acquisition"
    },
    "test_benchmark_connection_acquisition_concurrent": {
        "p95_ms": 10,  # <10ms p95
        "description": "Concurrent connection acquisition"
    },
    "test_benchmark_health_check": {
        "p99_ms": 10,  # <10ms p99
        "description": "Health check query"
    },
    "test_benchmark_graceful_shutdown": {
        "mean_ms": 30000,  # <30s
        "description": "Graceful shutdown"
    }
}

violations = []

for bench_name, bench_data in baseline["benchmarks"].items():
    if bench_name not in targets:
        continue

    target = targets[bench_name]

    for metric, threshold in target.items():
        if metric == "description":
            continue

        actual = bench_data.get(metric, float('inf'))

        if actual > threshold:
            violations.append({
                "benchmark": target["description"],
                "metric": metric,
                "threshold": threshold,
                "actual": actual,
                "exceeded_by": actual - threshold
            })

if violations:
    print("\nERROR: Performance target violations detected:\n")
    for v in violations:
        print(f"  {v['benchmark']} ({v['metric']}):")
        print(f"    Target:   {v['threshold']:.2f} ms")
        print(f"    Actual:   {v['actual']:.2f} ms")
        print(f"    Exceeded: +{v['exceeded_by']:.2f} ms\n")
    sys.exit(4)
else:
    print("\nAll performance targets met!")
    sys.exit(0)
EOF

    local exit_code=$?

    if [[ $exit_code -eq 4 ]]; then
        log_error "Performance targets not met"
        log_warning "Consider optimizing code or adjusting targets"
        exit 4
    elif [[ $exit_code -ne 0 ]]; then
        log_error "Target validation failed"
        exit 3
    fi

    log_success "All performance targets validated"
}

# Print usage instructions
print_usage() {
    echo ""
    echo "================================================================"
    echo " Baseline Collection Complete!"
    echo "================================================================"
    echo ""
    echo "Baseline file: ${BASELINE_FILE}"
    echo ""
    echo "Next Steps:"
    echo ""
    echo "1. Commit baseline to repository:"
    echo "   git add ${BASELINE_FILE}"
    echo "   git commit -m \"chore(benchmarks): add connection pool performance baseline\""
    echo ""
    echo "2. Run performance regression tests:"
    echo "   pytest tests/benchmarks/test_connection_pool_benchmarks.py --benchmark-only \\"
    echo "       --benchmark-compare=${BASELINE_FILE} \\"
    echo "       --benchmark-compare-fail=mean:10%"
    echo ""
    echo "3. Add to CI/CD pipeline:"
    echo "   - Run benchmarks on pull requests"
    echo "   - Fail if performance degrades >10% from baseline"
    echo "   - Update baseline when intentional changes are made"
    echo ""
    echo "4. Monitor performance trends:"
    echo "   - Track mean/p95/p99 latencies over time"
    echo "   - Alert on significant deviations"
    echo "   - Update baseline after optimization work"
    echo ""
    echo "================================================================"
    echo ""
}

# Main execution
main() {
    print_header
    check_prerequisites
    run_benchmarks
    extract_baseline
    validate_targets
    print_usage

    log_success "Baseline collection complete!"
}

# Execute main function
main "$@"
