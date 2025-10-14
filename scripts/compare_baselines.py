#!/usr/bin/env python3
"""Compare baseline performance measurements with hybrid regression detection.

Implements hybrid regression logic from research.md lines 268-305:
- Flag violation if BOTH conditions met:
  1. Metric exceeds baseline by >10% (degradation check)
  2. AND metric exceeds constitutional target (performance guarantee)

Usage:
    python scripts/compare_baselines.py pre-split.json post-split.json

Exit Codes:
    0: All metrics pass (no regressions)
    1: One or more metrics failed regression checks

Constitutional Compliance:
- Principle VIII: Type Safety (mypy --strict compliance, Pydantic models)
- Principle IV: Performance Guarantees (constitutional targets enforcement)
- Principle V: Production Quality (comprehensive error handling)
"""

from __future__ import annotations

import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, Field, ValidationError

# ==============================================================================
# Constitutional Performance Targets
# ==============================================================================

CONSTITUTIONAL_TARGETS: Final[dict[str, Decimal]] = {
    "index": Decimal("60000.0"),  # Indexing: <60s p95 (in milliseconds)
    "search": Decimal("500.0"),  # Search: <500ms p95
    "project_switch": Decimal("50.0"),  # Project switching: <50ms p95
    "entity_query": Decimal("100.0"),  # Entity queries: <100ms p95
}

DEGRADATION_THRESHOLD_PERCENT: Final[Decimal] = Decimal("10.0")

# ==============================================================================
# Pydantic Models
# ==============================================================================


class PerformanceBenchmarkResult(BaseModel):
    """
    Performance benchmark result for regression detection.

    Matches src/models/performance.py structure.
    """

    # Identification
    benchmark_id: str = Field(description="Unique identifier for this benchmark run (UUID)")
    server_id: Literal["codebase-mcp", "workflow-mcp"] = Field(description="Server identifier")
    operation_type: Literal["index", "search", "project_switch", "entity_query"] = Field(
        description="Operation being benchmarked"
    )

    # Timing
    timestamp: str = Field(description="Benchmark execution timestamp (ISO 8601)")

    # Latency Metrics (in milliseconds)
    latency_p50_ms: Decimal = Field(ge=0, description="50th percentile latency in milliseconds")
    latency_p95_ms: Decimal = Field(ge=0, description="95th percentile latency in milliseconds")
    latency_p99_ms: Decimal = Field(ge=0, description="99th percentile latency in milliseconds")
    latency_mean_ms: Decimal = Field(ge=0, description="Mean latency in milliseconds")
    latency_min_ms: Decimal = Field(ge=0, description="Minimum latency in milliseconds")
    latency_max_ms: Decimal = Field(ge=0, description="Maximum latency in milliseconds")

    # Test Parameters
    sample_size: int = Field(ge=1, description="Number of iterations in the benchmark")
    test_parameters: dict[str, str | int | float] = Field(
        default_factory=dict, description="Test-specific parameters"
    )

    # Validation
    pass_status: Literal["pass", "fail", "warning"] = Field(
        description="Pass/fail status against target thresholds"
    )
    target_threshold_ms: Decimal | None = Field(
        default=None, description="Target threshold for this operation (from constitution)"
    )


class BaselineFile(BaseModel):
    """Container for baseline benchmark results."""

    version: str = Field(description="Baseline format version")
    timestamp: str = Field(description="When baseline was created")
    benchmarks: list[PerformanceBenchmarkResult] = Field(description="List of benchmark results")


class MetricComparison(BaseModel):
    """Comparison of a single metric between baselines."""

    operation_type: str = Field(description="Operation being compared")
    server_id: str = Field(description="Server being benchmarked")
    baseline_p95_ms: Decimal = Field(description="Baseline p95 latency in milliseconds")
    current_p95_ms: Decimal = Field(description="Current p95 latency in milliseconds")
    constitutional_target_ms: Decimal = Field(description="Constitutional target for this operation")
    degradation_percent: Decimal = Field(description="Percentage degradation from baseline")
    exceeds_baseline: bool = Field(description="Whether degradation >10% from baseline")
    exceeds_target: bool = Field(description="Whether current exceeds constitutional target")
    regression: bool = Field(description="Whether BOTH baseline and target exceeded (hybrid logic)")
    status: Literal["pass", "fail", "warning"] = Field(description="Overall comparison status")
    explanation: str = Field(description="Human-readable explanation of result")


class ComparisonReport(BaseModel):
    """Complete comparison report with all metrics."""

    pre_split_file: str = Field(description="Path to pre-split baseline file")
    post_split_file: str = Field(description="Path to post-split baseline file")
    timestamp: str = Field(description="When comparison was generated")
    comparisons: list[MetricComparison] = Field(description="Individual metric comparisons")
    overall_status: Literal["pass", "fail", "warning"] = Field(
        description="Overall pass/fail/warning status"
    )
    summary: str = Field(description="Summary of comparison results")


# ==============================================================================
# Hybrid Regression Detection Logic
# ==============================================================================


def check_regression(
    current: Decimal, baseline: Decimal, target: Decimal, operation_type: str
) -> tuple[bool, bool, bool, Decimal, str]:
    """
    Flag regression if BOTH conditions met:
    1. Current exceeds baseline by >10%
    2. Current exceeds constitutional target

    Args:
        current: Current measured value (p95 latency in ms)
        baseline: Baseline value for comparison (p95 latency in ms)
        target: Constitutional target value (p95 latency in ms)
        operation_type: Operation being tested (for explanation)

    Returns:
        Tuple of (exceeds_baseline, exceeds_target, regression, degradation_percent, explanation)
    """
    # Calculate degradation percentage
    degradation_percent = ((current - baseline) / baseline) * Decimal("100.0")

    # Check conditions
    exceeds_baseline = degradation_percent > DEGRADATION_THRESHOLD_PERCENT
    exceeds_target = current > target

    # Hybrid logic: BOTH must be true for regression
    regression = exceeds_baseline and exceeds_target

    # Generate explanation
    if not exceeds_baseline and not exceeds_target:
        explanation = (
            f"✓ PASS: Within baseline ({degradation_percent:.1f}% change) "
            f"and constitutional target ({current:.2f}ms < {target:.2f}ms)"
        )
    elif exceeds_baseline and not exceeds_target:
        explanation = (
            f"⚠ WARNING: Exceeds baseline by {degradation_percent:.1f}% "
            f"but within constitutional target ({current:.2f}ms < {target:.2f}ms). "
            f"Acceptable degradation."
        )
    elif not exceeds_baseline and exceeds_target:
        explanation = (
            f"⚠ WARNING: Exceeds constitutional target ({current:.2f}ms > {target:.2f}ms) "
            f"but within baseline variance ({degradation_percent:.1f}% change). "
            f"Baseline may need adjustment."
        )
    else:  # Both conditions met - regression
        explanation = (
            f"✗ FAIL: REGRESSION DETECTED. Exceeds baseline by {degradation_percent:.1f}% "
            f"AND exceeds constitutional target ({current:.2f}ms > {target:.2f}ms). "
            f"This violates performance guarantees."
        )

    return exceeds_baseline, exceeds_target, regression, degradation_percent, explanation


# ==============================================================================
# Baseline Loading and Comparison
# ==============================================================================


def load_baseline_file(file_path: Path) -> BaselineFile:
    """Load and validate baseline JSON file.

    Args:
        file_path: Path to baseline JSON file

    Returns:
        Validated BaselineFile object

    Raises:
        FileNotFoundError: If file doesn't exist
        ValidationError: If file format is invalid
        json.JSONDecodeError: If JSON is malformed
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Baseline file not found: {file_path}")

    json_data = json.loads(file_path.read_text(encoding="utf-8"))
    return BaselineFile.model_validate(json_data)


def find_matching_benchmark(
    benchmarks: list[PerformanceBenchmarkResult], server_id: str, operation_type: str
) -> PerformanceBenchmarkResult | None:
    """Find benchmark matching server and operation type.

    Args:
        benchmarks: List of benchmarks to search
        server_id: Server identifier to match
        operation_type: Operation type to match

    Returns:
        Matching benchmark or None if not found
    """
    for benchmark in benchmarks:
        if benchmark.server_id == server_id and benchmark.operation_type == operation_type:
            return benchmark
    return None


def compare_baselines(pre_split: BaselineFile, post_split: BaselineFile) -> ComparisonReport:
    """Compare two baseline files using hybrid regression detection.

    Args:
        pre_split: Pre-split baseline measurements
        post_split: Post-split baseline measurements

    Returns:
        ComparisonReport with detailed analysis
    """
    from datetime import datetime, timezone

    comparisons: list[MetricComparison] = []
    has_failures = False
    has_warnings = False

    # Compare each post-split benchmark against pre-split
    for post_benchmark in post_split.benchmarks:
        # Find matching pre-split benchmark
        pre_benchmark = find_matching_benchmark(
            pre_split.benchmarks, post_benchmark.server_id, post_benchmark.operation_type
        )

        if pre_benchmark is None:
            # No baseline found - can't compare
            comparisons.append(
                MetricComparison(
                    operation_type=post_benchmark.operation_type,
                    server_id=post_benchmark.server_id,
                    baseline_p95_ms=Decimal("0.0"),
                    current_p95_ms=post_benchmark.latency_p95_ms,
                    constitutional_target_ms=CONSTITUTIONAL_TARGETS.get(
                        post_benchmark.operation_type, Decimal("0.0")
                    ),
                    degradation_percent=Decimal("0.0"),
                    exceeds_baseline=False,
                    exceeds_target=False,
                    regression=False,
                    status="warning",
                    explanation=f"⚠ WARNING: No baseline found for {post_benchmark.operation_type} on {post_benchmark.server_id}. Cannot compare.",
                )
            )
            has_warnings = True
            continue

        # Get constitutional target
        target = CONSTITUTIONAL_TARGETS.get(post_benchmark.operation_type, Decimal("0.0"))

        # Run hybrid regression check
        exceeds_baseline, exceeds_target, regression, degradation_percent, explanation = (
            check_regression(
                post_benchmark.latency_p95_ms,
                pre_benchmark.latency_p95_ms,
                target,
                post_benchmark.operation_type,
            )
        )

        # Determine status
        if regression:
            status: Literal["pass", "fail", "warning"] = "fail"
            has_failures = True
        elif exceeds_baseline or exceeds_target:
            status = "warning"
            has_warnings = True
        else:
            status = "pass"

        comparisons.append(
            MetricComparison(
                operation_type=post_benchmark.operation_type,
                server_id=post_benchmark.server_id,
                baseline_p95_ms=pre_benchmark.latency_p95_ms,
                current_p95_ms=post_benchmark.latency_p95_ms,
                constitutional_target_ms=target,
                degradation_percent=degradation_percent,
                exceeds_baseline=exceeds_baseline,
                exceeds_target=exceeds_target,
                regression=regression,
                status=status,
                explanation=explanation,
            )
        )

    # Determine overall status
    if has_failures:
        overall_status: Literal["pass", "fail", "warning"] = "fail"
        summary = "FAILED: One or more metrics show performance regression (exceed baseline by >10% AND exceed constitutional targets)"
    elif has_warnings:
        overall_status = "warning"
        summary = "WARNING: Some metrics exceed baseline or targets individually, but no hybrid regressions detected"
    else:
        overall_status = "pass"
        summary = "PASSED: All metrics within acceptable ranges"

    return ComparisonReport(
        pre_split_file="pre-split baseline",
        post_split_file="post-split baseline",
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        comparisons=comparisons,
        overall_status=overall_status,
        summary=summary,
    )


# ==============================================================================
# Display Functions
# ==============================================================================


def display_comparison_report(report: ComparisonReport, verbose: bool = False) -> None:
    """Display comparison report in human-readable format.

    Args:
        report: Comparison report to display
        verbose: Whether to show detailed metric information
    """
    print("\n" + "=" * 80)
    print("BASELINE COMPARISON REPORT - HYBRID REGRESSION DETECTION")
    print("=" * 80)
    print(f"\nTimestamp: {report.timestamp}")
    print(f"Overall Status: {report.overall_status.upper()}")
    print(f"Summary: {report.summary}")

    print("\n" + "-" * 80)
    print("INDIVIDUAL METRIC COMPARISONS")
    print("-" * 80)

    for comparison in report.comparisons:
        print(f"\n{comparison.server_id} - {comparison.operation_type}")
        if verbose:
            print(f"  Baseline p95:      {comparison.baseline_p95_ms:.2f}ms")
            print(f"  Current p95:       {comparison.current_p95_ms:.2f}ms")
            print(f"  Constitutional:    {comparison.constitutional_target_ms:.2f}ms")
            print(f"  Degradation:       {comparison.degradation_percent:.1f}%")
            print(f"  Exceeds Baseline:  {comparison.exceeds_baseline}")
            print(f"  Exceeds Target:    {comparison.exceeds_target}")
            print(f"  Regression:        {comparison.regression}")
        print(f"  {comparison.explanation}")

    print("\n" + "=" * 80)


def output_json_report(report: ComparisonReport, output_path: Path) -> None:
    """Write comparison report to JSON file.

    Args:
        report: Comparison report to write
        output_path: Path to output JSON file
    """
    output_path.write_text(
        report.model_dump_json(indent=2, exclude_none=True), encoding="utf-8"
    )
    print(f"\nJSON report written to: {output_path}")


# ==============================================================================
# Main Entry Point
# ==============================================================================


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for pass, 1 for fail)
    """
    parser = argparse.ArgumentParser(
        description="Compare baseline performance measurements with hybrid regression detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare two baselines (console output)
  python scripts/compare_baselines.py pre-split.json post-split.json

  # Compare with verbose output
  python scripts/compare_baselines.py pre-split.json post-split.json --verbose

  # Save JSON report
  python scripts/compare_baselines.py pre-split.json post-split.json --output report.json

Hybrid Regression Logic:
  Flags regression if BOTH conditions met:
  1. Metric exceeds baseline by >10%
  2. AND metric exceeds constitutional target

  This allows minor degradation within constitutional targets while
  preventing significant regressions that violate performance guarantees.
        """,
    )

    parser.add_argument(
        "pre_split", type=Path, help="Path to pre-split baseline JSON file"
    )
    parser.add_argument(
        "post_split", type=Path, help="Path to post-split baseline JSON file"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Path to output JSON report (optional)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed metric information",
    )

    args = parser.parse_args()

    try:
        # Load baseline files
        print(f"Loading pre-split baseline: {args.pre_split}")
        pre_split = load_baseline_file(args.pre_split)
        print(f"  Found {len(pre_split.benchmarks)} benchmarks")

        print(f"\nLoading post-split baseline: {args.post_split}")
        post_split = load_baseline_file(args.post_split)
        print(f"  Found {len(post_split.benchmarks)} benchmarks")

        # Compare baselines
        print("\nRunning hybrid regression detection...")
        report = compare_baselines(pre_split, post_split)

        # Display results
        display_comparison_report(report, verbose=args.verbose)

        # Write JSON report if requested
        if args.output:
            output_json_report(report, args.output)

        # Return exit code based on overall status
        if report.overall_status == "fail":
            print("\nEXIT CODE: 1 (FAILURE - regressions detected)")
            return 1
        else:
            print("\nEXIT CODE: 0 (SUCCESS)")
            return 0

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        return 1
    except ValidationError as e:
        print(f"Error: Invalid baseline format: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
