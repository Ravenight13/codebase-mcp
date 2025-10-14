#!/usr/bin/env bash
# scripts/validate_performance.sh
# Performance validation automation script
# Orchestrates benchmarks, baseline comparison, and reporting
#
# Usage:
#   ./scripts/validate_performance.sh [OPTIONS]
#
# Options:
#   --dry-run         Show what would be executed without running benchmarks
#   --baseline FILE   Specify custom baseline file (default: performance_baselines/baseline.json)
#   --skip-benchmarks Skip benchmark execution, only compare existing results
#   --verbose         Enable verbose output
#   --help            Show this help message
#
# Exit codes:
#   0 - All benchmarks passed and within performance thresholds
#   1 - Performance regression detected or benchmarks failed
#   2 - Invalid arguments or missing dependencies
#
# Examples:
#   # Run full validation with default baseline
#   ./scripts/validate_performance.sh
#
#   # Dry run to see what would be executed
#   ./scripts/validate_performance.sh --dry-run
#
#   # Compare against custom baseline
#   ./scripts/validate_performance.sh --baseline performance_baselines/v1.0-baseline.json
#
#   # Compare existing results without re-running benchmarks
#   ./scripts/validate_performance.sh --skip-benchmarks
#

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

BASELINE_DIR="performance_baselines"
REPORTS_DIR="docs/performance"
CURRENT_RESULTS="${BASELINE_DIR}/current.json"
BASELINE_FILE="${BASELINE_DIR}/baseline.json"
VALIDATION_REPORT="${REPORTS_DIR}/validation-report.json"
COMPARISON_SCRIPT="scripts/compare_baselines.py"

# Default options
DRY_RUN=false
SKIP_BENCHMARKS=false
VERBOSE=false
CUSTOM_BASELINE=""

# ============================================================================
# Colors for output
# ============================================================================

if [[ -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    BOLD='\033[1m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    BOLD=''
    NC=''
fi

# ============================================================================
# Helper Functions
# ============================================================================

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

log_section() {
    echo ""
    echo -e "${BOLD}===========================================================${NC}"
    echo -e "${BOLD}$*${NC}"
    echo -e "${BOLD}===========================================================${NC}"
}

show_help() {
    sed -n '/^# Usage:/,/^$/p' "$0" | sed 's/^# \?//'
}

# ============================================================================
# Validation Functions
# ============================================================================

validate_dependencies() {
    log_section "Validating Dependencies"

    local missing=0

    # Check for pytest
    if ! command -v pytest &> /dev/null; then
        log_error "pytest not found. Install with: pip install pytest"
        missing=$((missing + 1))
    else
        log_info "✓ pytest found: $(pytest --version | head -1)"
    fi

    # Check for pytest-benchmark
    if ! python -c "import pytest_benchmark" 2>/dev/null; then
        log_error "pytest-benchmark not found. Install with: pip install pytest-benchmark"
        missing=$((missing + 1))
    else
        log_info "✓ pytest-benchmark found"
    fi

    # Check for comparison script
    if [[ ! -f "$COMPARISON_SCRIPT" ]]; then
        log_error "Comparison script not found: $COMPARISON_SCRIPT"
        log_error "This script requires compare_baselines.py to be implemented (Task T011)"
        missing=$((missing + 1))
    else
        log_info "✓ Comparison script found: $COMPARISON_SCRIPT"
    fi

    # Check for baseline file (unless skip-benchmarks)
    if [[ -z "$CUSTOM_BASELINE" ]]; then
        if [[ ! -f "$BASELINE_FILE" ]]; then
            log_warning "Baseline file not found: $BASELINE_FILE"
            log_warning "This appears to be the first run - current results will become the baseline"
        else
            log_info "✓ Baseline file found: $BASELINE_FILE"
        fi
    fi

    if [[ $missing -gt 0 ]]; then
        log_error "Missing $missing critical dependencies"
        return 2
    fi

    log_success "All dependencies validated"
    return 0
}

validate_directories() {
    log_section "Validating Directory Structure"

    # Create directories if they don't exist
    if [[ ! -d "$BASELINE_DIR" ]]; then
        log_warning "Creating missing directory: $BASELINE_DIR"
        mkdir -p "$BASELINE_DIR"
    else
        log_info "✓ $BASELINE_DIR exists"
    fi

    if [[ ! -d "$REPORTS_DIR" ]]; then
        log_warning "Creating missing directory: $REPORTS_DIR"
        mkdir -p "$REPORTS_DIR"
    else
        log_info "✓ $REPORTS_DIR exists"
    fi

    if [[ ! -d "tests/benchmarks" ]]; then
        log_error "Benchmark tests directory not found: tests/benchmarks"
        log_error "Cannot run benchmarks without test files"
        return 2
    else
        log_info "✓ tests/benchmarks/ exists"
    fi

    log_success "Directory structure validated"
    return 0
}

# ============================================================================
# Main Functions
# ============================================================================

run_benchmarks() {
    log_section "Running Performance Benchmarks"

    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would execute:"
        log_info "  pytest tests/benchmarks/ --benchmark-only --benchmark-json=\"$CURRENT_RESULTS\""
        return 0
    fi

    log_info "Executing benchmark suite..."
    log_info "Output will be saved to: $CURRENT_RESULTS"

    if [[ "$VERBOSE" == true ]]; then
        pytest tests/benchmarks/ \
            --benchmark-only \
            --benchmark-json="$CURRENT_RESULTS" \
            -v
    else
        pytest tests/benchmarks/ \
            --benchmark-only \
            --benchmark-json="$CURRENT_RESULTS"
    fi

    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        log_success "Benchmarks completed successfully"
        log_info "Results saved to: $CURRENT_RESULTS"
    else
        log_error "Benchmarks failed with exit code: $exit_code"
        return 1
    fi

    return 0
}

compare_with_baseline() {
    log_section "Comparing with Baseline"

    # Determine which baseline to use
    local baseline_to_use="$BASELINE_FILE"
    if [[ -n "$CUSTOM_BASELINE" ]]; then
        baseline_to_use="$CUSTOM_BASELINE"
        log_info "Using custom baseline: $baseline_to_use"
    fi

    # Check if this is the first run
    if [[ ! -f "$baseline_to_use" ]]; then
        log_warning "No baseline file found - this appears to be the first run"
        log_info "Copying current results to baseline: $BASELINE_FILE"

        if [[ "$DRY_RUN" == true ]]; then
            log_info "[DRY RUN] Would copy $CURRENT_RESULTS to $BASELINE_FILE"
        else
            cp "$CURRENT_RESULTS" "$BASELINE_FILE"
            log_success "Baseline created from current results"
        fi

        log_info "Skipping comparison - no baseline to compare against"
        return 0
    fi

    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would execute:"
        log_info "  python $COMPARISON_SCRIPT \\"
        log_info "    \"$baseline_to_use\" \\"
        log_info "    \"$CURRENT_RESULTS\" \\"
        log_info "    --output \"$VALIDATION_REPORT\""
        return 0
    fi

    log_info "Comparing current results with baseline..."
    log_info "Baseline: $baseline_to_use"
    log_info "Current:  $CURRENT_RESULTS"
    log_info "Output:   $VALIDATION_REPORT"

    if [[ "$VERBOSE" == true ]]; then
        python "$COMPARISON_SCRIPT" \
            "$baseline_to_use" \
            "$CURRENT_RESULTS" \
            --output "$VALIDATION_REPORT" \
            --verbose
    else
        python "$COMPARISON_SCRIPT" \
            "$baseline_to_use" \
            "$CURRENT_RESULTS" \
            --output "$VALIDATION_REPORT"
    fi

    local exit_code=$?

    if [[ $exit_code -eq 0 ]]; then
        log_success "Performance comparison passed - no regressions detected"
        return 0
    else
        log_error "Performance comparison failed - regressions detected"
        log_error "See report for details: $VALIDATION_REPORT"
        return 1
    fi
}

generate_summary() {
    log_section "Validation Summary"

    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY RUN] Would generate summary report"
        return 0
    fi

    log_info "Results location:"
    log_info "  Current results:    $CURRENT_RESULTS"
    log_info "  Baseline file:      ${CUSTOM_BASELINE:-$BASELINE_FILE}"
    log_info "  Validation report:  $VALIDATION_REPORT"

    if [[ -f "$VALIDATION_REPORT" ]]; then
        # Try to extract summary from JSON report if jq is available
        if command -v jq &> /dev/null && [[ -f "$VALIDATION_REPORT" ]]; then
            log_info ""
            log_info "Quick summary:"
            jq -r '
                if .status then
                    "  Status: " + .status + "\n" +
                    "  Total benchmarks: " + (.total_benchmarks // 0 | tostring) + "\n" +
                    "  Regressions: " + (.regressions // 0 | tostring) + "\n" +
                    "  Improvements: " + (.improvements // 0 | tostring)
                else
                    "  (JSON structure varies - see full report)"
                end
            ' "$VALIDATION_REPORT" 2>/dev/null || log_info "  See full report for details"
        fi
    fi
}

# ============================================================================
# Argument Parsing
# ============================================================================

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --baseline)
                if [[ -z "${2:-}" ]]; then
                    log_error "--baseline requires a file path argument"
                    return 2
                fi
                CUSTOM_BASELINE="$2"
                shift 2
                ;;
            --skip-benchmarks)
                SKIP_BENCHMARKS=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                echo ""
                show_help
                return 2
                ;;
        esac
    done

    # Validate custom baseline exists
    if [[ -n "$CUSTOM_BASELINE" && ! -f "$CUSTOM_BASELINE" ]]; then
        log_error "Custom baseline file not found: $CUSTOM_BASELINE"
        return 2
    fi

    return 0
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    log_section "Performance Validation Automation"

    # Parse arguments
    if ! parse_arguments "$@"; then
        return 2
    fi

    if [[ "$DRY_RUN" == true ]]; then
        log_warning "DRY RUN MODE - No changes will be made"
    fi

    # Validate environment
    if ! validate_dependencies; then
        log_error "Dependency validation failed"
        return 2
    fi

    if ! validate_directories; then
        log_error "Directory validation failed"
        return 2
    fi

    # Run benchmarks (unless skipped)
    if [[ "$SKIP_BENCHMARKS" == false ]]; then
        if ! run_benchmarks; then
            log_error "Benchmark execution failed"
            return 1
        fi
    else
        log_section "Skipping Benchmarks"
        log_info "Using existing results: $CURRENT_RESULTS"

        if [[ ! -f "$CURRENT_RESULTS" ]]; then
            log_error "Current results file not found: $CURRENT_RESULTS"
            log_error "Cannot skip benchmarks without existing results"
            return 2
        fi
    fi

    # Compare with baseline
    if ! compare_with_baseline; then
        log_error "Performance validation failed"
        generate_summary
        return 1
    fi

    # Generate summary
    generate_summary

    log_section "Performance Validation Complete"
    log_success "All performance targets met - no regressions detected"

    return 0
}

# Run main function with all arguments
main "$@"
exit $?
