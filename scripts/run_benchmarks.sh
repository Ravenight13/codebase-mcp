#!/usr/bin/env bash
# scripts/run_benchmarks.sh
#
# T017: Pytest benchmark runner script for Phase 3 User Story 1
#
# Purpose: Orchestrates execution of all performance benchmarks (T013-T016)
#          and saves results to performance_baselines/ directory
#
# Constitutional Compliance:
#   - Principle IV: Validates performance targets (<60s, <500ms, <50ms, <100ms)
#   - Principle VII: TDD - benchmarks serve as regression tests
#   - SC-005: Validates performance variance within 10% of baseline
#
# Usage:
#   ./scripts/run_benchmarks.sh [options]
#
# Options:
#   --output-dir DIR    Output directory for benchmark results (default: performance_baselines/)
#   --baseline NAME     Baseline name for comparison (default: none)
#   --compare           Compare against existing baseline and fail if >10% slower
#   --json-output       Generate JSON output files
#   --html-report       Generate HTML performance report
#   --help              Show this help message
#
# Requirements:
#   - PostgreSQL database running (for codebase-mcp and workflow-mcp)
#   - Ollama running with nomic-embed-text model (for embeddings)
#   - pytest-benchmark installed
#   - Test fixtures available
#
# Output:
#   - performance_baselines/indexing_benchmark_<timestamp>.json
#   - performance_baselines/search_benchmark_<timestamp>.json
#   - performance_baselines/workflow_benchmark_<timestamp>.json
#   - performance_baselines/combined_report_<timestamp>.json

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
OUTPUT_DIR="${REPO_ROOT}/performance_baselines"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BASELINE_NAME=""
COMPARE_MODE=false
JSON_OUTPUT=true
HTML_REPORT=false
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --baseline)
            BASELINE_NAME="$2"
            shift 2
            ;;
        --compare)
            COMPARE_MODE=true
            shift
            ;;
        --json-output)
            JSON_OUTPUT=true
            shift
            ;;
        --html-report)
            HTML_REPORT=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            grep '^#' "$0" | grep -v '#!/usr/bin/env' | sed 's/^# *//'
            exit 0
            ;;
        *)
            echo -e "${RED}ERROR: Unknown option: $1${NC}" >&2
            echo "Run with --help for usage information" >&2
            exit 1
            ;;
    esac
done

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

# Banner
echo "================================================================================"
echo "  Performance Benchmark Runner (T017)"
echo "  Phase 3: User Story 1 - Performance Baseline Validation"
echo "================================================================================"
echo ""

# Create output directory
log_info "Creating output directory: ${OUTPUT_DIR}"
mkdir -p "${OUTPUT_DIR}"

# Verify prerequisites
log_info "Verifying prerequisites..."

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    log_error "pytest not found. Install with: pip install pytest pytest-benchmark"
    exit 1
fi

# Check if pytest-benchmark is installed
if ! python -c "import pytest_benchmark" 2>/dev/null; then
    log_error "pytest-benchmark not installed. Install with: pip install pytest-benchmark"
    exit 1
fi

# Check if benchmark test files exist
BENCHMARK_FILES=(
    "${REPO_ROOT}/tests/benchmarks/test_indexing_perf.py"
    "${REPO_ROOT}/tests/benchmarks/test_search_perf.py"
    "${REPO_ROOT}/tests/benchmarks/test_workflow_perf.py"
)

for file in "${BENCHMARK_FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
        log_error "Benchmark test file not found: $file"
        exit 1
    fi
done

log_success "All prerequisites verified"
echo ""

# Build pytest command base
PYTEST_BASE_CMD="pytest --benchmark-only --benchmark-warmup=on"

if [[ "$VERBOSE" == true ]]; then
    PYTEST_BASE_CMD="$PYTEST_BASE_CMD -v"
fi

if [[ "$JSON_OUTPUT" == true ]]; then
    PYTEST_BASE_CMD="$PYTEST_BASE_CMD --benchmark-json"
fi

if [[ -n "$BASELINE_NAME" ]] && [[ "$COMPARE_MODE" == true ]]; then
    BASELINE_FILE="${OUTPUT_DIR}/${BASELINE_NAME}.json"
    if [[ -f "$BASELINE_FILE" ]]; then
        log_info "Comparison mode enabled with baseline: ${BASELINE_NAME}"
        PYTEST_BASE_CMD="$PYTEST_BASE_CMD --benchmark-compare=${BASELINE_FILE} --benchmark-compare-fail=mean:10%"
    else
        log_warning "Baseline file not found: ${BASELINE_FILE}"
        log_warning "Skipping comparison mode"
    fi
fi

# Function to run benchmark
run_benchmark() {
    local test_file="$1"
    local output_name="$2"
    local description="$3"

    echo "================================================================================"
    log_info "Running: ${description}"
    echo "================================================================================"

    local output_file="${OUTPUT_DIR}/${output_name}_${TIMESTAMP}.json"
    local cmd="${PYTEST_BASE_CMD} ${test_file}"

    if [[ "$JSON_OUTPUT" == true ]]; then
        cmd="${cmd}=${output_file}"
    fi

    log_info "Command: ${cmd}"
    echo ""

    # Run benchmark
    if eval "$cmd"; then
        log_success "Benchmark completed: ${description}"
        if [[ "$JSON_OUTPUT" == true ]]; then
            log_info "Results saved to: ${output_file}"
        fi
        return 0
    else
        log_error "Benchmark failed: ${description}"
        return 1
    fi
}

# Initialize results tracking
RESULTS_FILE="${OUTPUT_DIR}/benchmark_summary_${TIMESTAMP}.txt"
touch "$RESULTS_FILE"

echo "Benchmark Execution Summary" >> "$RESULTS_FILE"
echo "Generated: $(date)" >> "$RESULTS_FILE"
echo "Output Directory: ${OUTPUT_DIR}" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

# Track benchmark results
declare -A BENCHMARK_RESULTS

# Run T013: Indexing Performance Benchmark
echo ""
if run_benchmark \
    "${REPO_ROOT}/tests/benchmarks/test_indexing_perf.py" \
    "indexing_benchmark" \
    "T013 - Indexing Performance (<60s p95 target)"; then
    BENCHMARK_RESULTS["T013"]="PASS"
    echo "T013 - Indexing Performance: PASS" >> "$RESULTS_FILE"
else
    BENCHMARK_RESULTS["T013"]="FAIL"
    echo "T013 - Indexing Performance: FAIL" >> "$RESULTS_FILE"
fi
echo ""

# Run T014: Search Performance Benchmark
if run_benchmark \
    "${REPO_ROOT}/tests/benchmarks/test_search_perf.py" \
    "search_benchmark" \
    "T014 - Search Performance (<500ms p95 target, 10 concurrent clients)"; then
    BENCHMARK_RESULTS["T014"]="PASS"
    echo "T014 - Search Performance: PASS" >> "$RESULTS_FILE"
else
    BENCHMARK_RESULTS["T014"]="FAIL"
    echo "T014 - Search Performance: FAIL" >> "$RESULTS_FILE"
fi
echo ""

# Run T015 & T016: Workflow Performance Benchmarks
if run_benchmark \
    "${REPO_ROOT}/tests/benchmarks/test_workflow_perf.py" \
    "workflow_benchmark" \
    "T015/T016 - Workflow Performance (<50ms project switch, <100ms entity query)"; then
    BENCHMARK_RESULTS["T015_T016"]="PASS"
    echo "T015/T016 - Workflow Performance: PASS" >> "$RESULTS_FILE"
else
    BENCHMARK_RESULTS["T015_T016"]="FAIL"
    echo "T015/T016 - Workflow Performance: FAIL" >> "$RESULTS_FILE"
fi
echo ""

# Generate summary report
echo "================================================================================"
echo "  Benchmark Execution Summary"
echo "================================================================================"
echo ""

TOTAL_BENCHMARKS=3
PASSED_BENCHMARKS=0

for task in "${!BENCHMARK_RESULTS[@]}"; do
    result="${BENCHMARK_RESULTS[$task]}"
    if [[ "$result" == "PASS" ]]; then
        log_success "${task}: PASS"
        ((PASSED_BENCHMARKS++))
    else
        log_error "${task}: FAIL"
    fi
done

echo ""
echo "Results: ${PASSED_BENCHMARKS}/${TOTAL_BENCHMARKS} benchmarks passed"
echo ""
log_info "Summary saved to: ${RESULTS_FILE}"
log_info "Benchmark results saved to: ${OUTPUT_DIR}/"
echo ""

# Generate HTML report if requested
if [[ "$HTML_REPORT" == true ]]; then
    log_info "Generating HTML performance report..."
    HTML_FILE="${OUTPUT_DIR}/performance_report_${TIMESTAMP}.html"

    cat > "$HTML_FILE" <<EOF
<!DOCTYPE html>
<html>
<head>
    <title>Performance Benchmark Report - ${TIMESTAMP}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        .pass { color: green; font-weight: bold; }
        .fail { color: red; font-weight: bold; }
    </style>
</head>
<body>
    <h1>Performance Benchmark Report</h1>
    <p><strong>Generated:</strong> $(date)</p>
    <p><strong>Output Directory:</strong> ${OUTPUT_DIR}</p>

    <h2>Benchmark Results</h2>
    <table>
        <tr>
            <th>Task</th>
            <th>Description</th>
            <th>Target</th>
            <th>Status</th>
        </tr>
        <tr>
            <td>T013</td>
            <td>Indexing Performance</td>
            <td>&lt;60s p95</td>
            <td class="${BENCHMARK_RESULTS[T013],,}">${BENCHMARK_RESULTS[T013]}</td>
        </tr>
        <tr>
            <td>T014</td>
            <td>Search Performance</td>
            <td>&lt;500ms p95 (10 concurrent clients)</td>
            <td class="${BENCHMARK_RESULTS[T014],,}">${BENCHMARK_RESULTS[T014]}</td>
        </tr>
        <tr>
            <td>T015/T016</td>
            <td>Workflow Performance</td>
            <td>&lt;50ms project switch, &lt;100ms entity query</td>
            <td class="${BENCHMARK_RESULTS[T015_T016],,}">${BENCHMARK_RESULTS[T015_T016]}</td>
        </tr>
    </table>

    <h2>Summary</h2>
    <p><strong>Results:</strong> ${PASSED_BENCHMARKS}/${TOTAL_BENCHMARKS} benchmarks passed</p>
</body>
</html>
EOF

    log_success "HTML report generated: ${HTML_FILE}"
fi

# Exit with appropriate code
if [[ "$PASSED_BENCHMARKS" -eq "$TOTAL_BENCHMARKS" ]]; then
    echo ""
    log_success "All benchmarks passed! ✨"
    echo ""
    exit 0
else
    echo ""
    log_error "Some benchmarks failed. See results above."
    echo ""
    exit 1
fi
