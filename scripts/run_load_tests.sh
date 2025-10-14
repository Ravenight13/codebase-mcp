#!/bin/bash
#
# Load Test Orchestration Script
#
# Purpose: Execute k6 load tests for both codebase-mcp and workflow-mcp servers,
#          collect results, validate thresholds, and generate summary report.
#
# Constitutional Compliance:
# - SC-006: Validate 50 concurrent clients handled without crash
# - SC-007: Validate 99.9% uptime during extended load testing
# - Principle IV: Performance guarantees under load
#
# Usage:
#   ./scripts/run_load_tests.sh [OPTIONS]
#
# Options:
#   --codebase-only    Run only codebase-mcp load test
#   --workflow-only    Run only workflow-mcp load test
#   --skip-health      Skip pre-flight health checks
#   --no-report        Skip summary report generation
#   --help             Display this help message
#
# Requirements:
# - k6 version 0.45+ installed
# - codebase-mcp server running on http://localhost:8020
# - workflow-mcp server running on http://localhost:8010
# - tests/load/ directory with k6 test scripts
#
# Exit Codes:
#   0 - All tests passed
#   1 - Health check failed (servers not running)
#   2 - k6 not installed
#   3 - Load test failed (thresholds violated)
#   4 - Report generation failed
#

set -euo pipefail

# Script directory and repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Test configuration
RESULTS_DIR="$REPO_ROOT/tests/load/results"
K6_CODEBASE_SCRIPT="$REPO_ROOT/tests/load/k6_codebase_load.js"
K6_WORKFLOW_SCRIPT="$REPO_ROOT/tests/load/k6_workflow_load.js"
SUMMARY_REPORT="$RESULTS_DIR/load_test_summary_$(date +%Y%m%d_%H%M%S).md"

# Server URLs
CODEBASE_URL="http://localhost:8020"
WORKFLOW_URL="http://localhost:8010"

# Default options
RUN_CODEBASE=true
RUN_WORKFLOW=true
SKIP_HEALTH=false
SKIP_REPORT=false

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Help message
show_help() {
    cat << EOF
Load Test Orchestration Script

USAGE:
    ./scripts/run_load_tests.sh [OPTIONS]

OPTIONS:
    --codebase-only    Run only codebase-mcp load test
    --workflow-only    Run only workflow-mcp load test
    --skip-health      Skip pre-flight health checks
    --no-report        Skip summary report generation
    --help             Display this help message

DESCRIPTION:
    Executes k6 load tests for both MCP servers, validates performance
    thresholds, and generates comprehensive summary reports.

    Load Test Scenarios:
    - Codebase-MCP: 50 concurrent users, 10min sustained load, p95<2000ms
    - Workflow-MCP: 50 concurrent users, 10min sustained load, error rate <1%

    Total Duration: ~38 minutes (19 minutes per server)

REQUIREMENTS:
    - k6 version 0.45+ installed
    - Both servers running and healthy
    - Sufficient system resources (CPU, memory)

EXIT CODES:
    0 - All tests passed
    1 - Health check failed
    2 - k6 not installed
    3 - Load test failed
    4 - Report generation failed

EXAMPLES:
    # Run full load test suite
    ./scripts/run_load_tests.sh

    # Run only codebase-mcp load test
    ./scripts/run_load_tests.sh --codebase-only

    # Run without generating summary report
    ./scripts/run_load_tests.sh --no-report

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --codebase-only)
                RUN_WORKFLOW=false
                shift
                ;;
            --workflow-only)
                RUN_CODEBASE=false
                shift
                ;;
            --skip-health)
                SKIP_HEALTH=true
                shift
                ;;
            --no-report)
                SKIP_REPORT=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Check if k6 is installed
check_k6_installed() {
    log_info "Checking k6 installation..."
    if ! command -v k6 &> /dev/null; then
        log_error "k6 is not installed"
        echo ""
        echo "Install k6:"
        echo "  macOS:   brew install k6"
        echo "  Linux:   sudo apt-get install k6  # or snap install k6"
        echo "  Windows: choco install k6"
        echo ""
        echo "See: https://k6.io/docs/getting-started/installation/"
        exit 2
    fi

    k6_version=$(k6 version 2>&1 | grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' | head -1 || echo "unknown")
    log_success "k6 installed: $k6_version"
}

# Check server health
check_server_health() {
    local server_name=$1
    local server_url=$2

    log_info "Checking $server_name health at $server_url/health..."

    if ! curl -sf "$server_url/health" > /dev/null 2>&1; then
        log_error "$server_name is not responding at $server_url"
        echo ""
        echo "Ensure $server_name is running:"
        echo "  Expected URL: $server_url/health"
        echo ""
        return 1
    fi

    log_success "$server_name is healthy"
    return 0
}

# Run pre-flight health checks
preflight_checks() {
    if [ "$SKIP_HEALTH" = true ]; then
        log_warning "Skipping health checks (--skip-health flag)"
        return 0
    fi

    log_info "Running pre-flight health checks..."

    local all_healthy=true

    if [ "$RUN_CODEBASE" = true ]; then
        if ! check_server_health "codebase-mcp" "$CODEBASE_URL"; then
            all_healthy=false
        fi
    fi

    if [ "$RUN_WORKFLOW" = true ]; then
        if ! check_server_health "workflow-mcp" "$WORKFLOW_URL"; then
            all_healthy=false
        fi
    fi

    if [ "$all_healthy" = false ]; then
        log_error "Pre-flight health checks failed"
        exit 1
    fi

    log_success "All pre-flight health checks passed"
}

# Create results directory
setup_results_dir() {
    log_info "Setting up results directory..."
    mkdir -p "$RESULTS_DIR"
    log_success "Results directory ready: $RESULTS_DIR"
}

# Run k6 load test
run_k6_test() {
    local test_name=$1
    local script_path=$2
    local server_url=$3

    log_info "Starting $test_name load test..."
    echo ""
    echo "Test Parameters:"
    echo "  Script: $script_path"
    echo "  Target: $server_url"
    echo "  Duration: ~19 minutes (2min ramp-up, 10min sustained, 2min ramp-down)"
    echo "  Concurrent Users: 50 (peak)"
    echo ""

    if [ ! -f "$script_path" ]; then
        log_error "Test script not found: $script_path"
        return 1
    fi

    # Run k6 with JSON output for result collection
    local test_start=$(date +%s)
    if k6 run "$script_path" --quiet; then
        local test_end=$(date +%s)
        local duration=$((test_end - test_start))
        log_success "$test_name load test completed in ${duration}s"
        return 0
    else
        local test_end=$(date +%s)
        local duration=$((test_end - test_start))
        log_error "$test_name load test failed after ${duration}s"
        return 1
    fi
}

# Validate test results
validate_results() {
    local results_file=$1

    if [ ! -f "$results_file" ]; then
        log_warning "Results file not found: $results_file"
        return 1
    fi

    log_info "Validating test results from $results_file..."

    # Extract key metrics using jq (if available)
    if command -v jq &> /dev/null; then
        local error_rate=$(jq -r '.metrics.error_rate_percent // 0' "$results_file")
        local p95_latency=$(jq -r '.metrics.latency.p95 // 0' "$results_file")
        local thresholds_passed=$(jq -r '.thresholds_passed // false' "$results_file")

        echo "  Error Rate: ${error_rate}%"
        echo "  p95 Latency: ${p95_latency}ms"
        echo "  Thresholds: $thresholds_passed"

        if [ "$thresholds_passed" = "true" ]; then
            log_success "All thresholds passed"
            return 0
        else
            log_error "Some thresholds failed"
            return 1
        fi
    else
        log_warning "jq not installed, skipping detailed validation"
        log_info "Install jq for detailed result validation: brew install jq"
        return 0
    fi
}

# Generate summary report
generate_summary_report() {
    log_info "Generating summary report..."

    # Find most recent result files
    local codebase_result=$(find "$RESULTS_DIR" -name "codebase_load_results_*.json" -type f | sort -r | head -1)
    local workflow_result=$(find "$RESULTS_DIR" -name "workflow_load_results_*.json" -type f | sort -r | head -1)

    cat > "$SUMMARY_REPORT" << 'EOF_HEADER'
# Load Testing Summary Report

**Generated**: $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Test Suite**: Phase 06 User Story 3 - Load and Stress Testing

## Executive Summary

This report summarizes the results of load testing for both codebase-mcp and workflow-mcp servers.

### Test Configuration

- **Concurrent Users**: 50 (peak load)
- **Test Duration**: ~19 minutes per server
  - Ramp-up: 2 minutes (0 → 10 users) + 5 minutes (10 → 50 users)
  - Sustained Load: 10 minutes at 50 users
  - Ramp-down: 2 minutes (50 → 0 users)

### Success Criteria

- **SC-006**: Both servers handle 50 concurrent clients without crashing
- **SC-007**: System maintains 99.9% uptime during load testing
- **Performance**: p95 latency < 2000ms (codebase), error rate < 1% (both)

---

EOF_HEADER

    # Add codebase-mcp results
    if [ "$RUN_CODEBASE" = true ] && [ -n "$codebase_result" ]; then
        cat >> "$SUMMARY_REPORT" << 'EOF_CODEBASE'
## Codebase-MCP Results

EOF_CODEBASE

        if command -v jq &> /dev/null; then
            {
                echo "### Metrics"
                echo ""
                echo "| Metric | Value |"
                echo "|--------|-------|"
                echo "| Total Requests | $(jq -r '.metrics.requests_total' "$codebase_result") |"
                echo "| Requests/sec | $(jq -r '.metrics.requests_per_second' "$codebase_result" | xargs printf '%.2f') |"
                echo "| Error Rate | $(jq -r '.metrics.error_rate_percent' "$codebase_result" | xargs printf '%.2f')% |"
                echo "| p50 Latency | $(jq -r '.metrics.latency.p50' "$codebase_result" | xargs printf '%.2f')ms |"
                echo "| p95 Latency | $(jq -r '.metrics.latency.p95' "$codebase_result" | xargs printf '%.2f')ms |"
                echo "| p99 Latency | $(jq -r '.metrics.latency.p99' "$codebase_result" | xargs printf '%.2f')ms |"
                echo ""
                echo "### Success Criteria"
                echo ""
                jq -r '.success_criteria | to_entries[] | "- **\(.key)**: \(.value)"' "$codebase_result"
                echo ""
            } >> "$SUMMARY_REPORT"
        else
            echo "_(jq not available for detailed metrics)_" >> "$SUMMARY_REPORT"
            echo "" >> "$SUMMARY_REPORT"
        fi
    fi

    # Add workflow-mcp results
    if [ "$RUN_WORKFLOW" = true ] && [ -n "$workflow_result" ]; then
        cat >> "$SUMMARY_REPORT" << 'EOF_WORKFLOW'
## Workflow-MCP Results

EOF_WORKFLOW

        if command -v jq &> /dev/null; then
            {
                echo "### Metrics"
                echo ""
                echo "| Metric | Value |"
                echo "|--------|-------|"
                echo "| Total Requests | $(jq -r '.metrics.requests_total' "$workflow_result") |"
                echo "| Requests/sec | $(jq -r '.metrics.requests_per_second' "$workflow_result" | xargs printf '%.2f') |"
                echo "| Error Rate | $(jq -r '.metrics.error_rate_percent' "$workflow_result" | xargs printf '%.2f')% |"
                echo "| p50 Latency | $(jq -r '.metrics.latency.p50' "$workflow_result" | xargs printf '%.2f')ms |"
                echo "| p95 Latency | $(jq -r '.metrics.latency.p95' "$workflow_result" | xargs printf '%.2f')ms |"
                echo "| p99 Latency | $(jq -r '.metrics.latency.p99' "$workflow_result" | xargs printf '%.2f')ms |"
                echo ""
                echo "### Operation-Specific Metrics"
                echo ""
                echo "| Operation | p95 Latency |"
                echo "|-----------|-------------|"
                echo "| Project Switch | $(jq -r '.metrics.custom_metrics.project_switch_p95 // "N/A"' "$workflow_result" | xargs printf '%.2f')ms |"
                echo "| Entity Query | $(jq -r '.metrics.custom_metrics.entity_query_p95 // "N/A"' "$workflow_result" | xargs printf '%.2f')ms |"
                echo "| Work Item Query | $(jq -r '.metrics.custom_metrics.work_item_query_p95 // "N/A"' "$workflow_result" | xargs printf '%.2f')ms |"
                echo ""
                echo "### Success Criteria"
                echo ""
                jq -r '.success_criteria | to_entries[] | "- **\(.key)**: \(.value)"' "$workflow_result"
                echo ""
            } >> "$SUMMARY_REPORT"
        else
            echo "_(jq not available for detailed metrics)_" >> "$SUMMARY_REPORT"
            echo "" >> "$SUMMARY_REPORT"
        fi
    fi

    # Add conclusion
    cat >> "$SUMMARY_REPORT" << 'EOF_CONCLUSION'
## Conclusion

Load testing validates that both servers can handle 50 concurrent clients
under sustained load while maintaining acceptable performance and uptime.

### Next Steps

1. Review detailed results in `tests/load/results/`
2. If thresholds failed, investigate specific failure patterns
3. Document any performance degradation under load
4. Proceed to Phase 07 resilience testing or address failures

---

**Files Referenced**:
- Codebase Results: $(basename "$codebase_result" 2>/dev/null || echo "N/A")
- Workflow Results: $(basename "$workflow_result" 2>/dev/null || echo "N/A")

EOF_CONCLUSION

    # Expand variables in the report
    eval "cat > \"$SUMMARY_REPORT.tmp\" << 'EOF_EVAL'
$(cat "$SUMMARY_REPORT")
EOF_EVAL"
    mv "$SUMMARY_REPORT.tmp" "$SUMMARY_REPORT"

    log_success "Summary report generated: $SUMMARY_REPORT"
}

# Main execution
main() {
    log_info "Load Test Orchestration Script"
    echo "========================================"
    echo ""

    parse_args "$@"
    check_k6_installed
    setup_results_dir
    preflight_checks

    local all_tests_passed=true

    # Run codebase-mcp load test
    if [ "$RUN_CODEBASE" = true ]; then
        if ! run_k6_test "codebase-mcp" "$K6_CODEBASE_SCRIPT" "$CODEBASE_URL"; then
            all_tests_passed=false
        fi
        echo ""
    fi

    # Run workflow-mcp load test
    if [ "$RUN_WORKFLOW" = true ]; then
        if ! run_k6_test "workflow-mcp" "$K6_WORKFLOW_SCRIPT" "$WORKFLOW_URL"; then
            all_tests_passed=false
        fi
        echo ""
    fi

    # Generate summary report
    if [ "$SKIP_REPORT" = false ]; then
        if ! generate_summary_report; then
            log_error "Failed to generate summary report"
            exit 4
        fi
    fi

    # Final status
    echo "========================================"
    if [ "$all_tests_passed" = true ]; then
        log_success "All load tests completed successfully"
        echo ""
        echo "Results available in: $RESULTS_DIR"
        if [ "$SKIP_REPORT" = false ]; then
            echo "Summary report: $SUMMARY_REPORT"
        fi
        exit 0
    else
        log_error "Some load tests failed"
        echo ""
        echo "Check detailed results in: $RESULTS_DIR"
        exit 3
    fi
}

# Execute main function
main "$@"
