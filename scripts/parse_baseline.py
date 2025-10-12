#!/usr/bin/env python3
"""Parse pytest-benchmark baseline results for performance analysis.

Extracts key metrics from pytest-benchmark JSON output and displays them
in a human-readable format with target comparisons.

Usage:
    python scripts/parse_baseline.py baseline-results.json

Constitutional Compliance:
- Principle VIII: Type Safety (mypy --strict compliance, Pydantic models)
- Principle V: Production Quality (comprehensive error handling)
"""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any, Final

from pydantic import BaseModel, Field, ValidationError

# ==============================================================================
# Constants
# ==============================================================================

# Performance targets from constitutional principles
INDEXING_TARGET_SECONDS: Final[Decimal] = Decimal("60.0")
SEARCH_P50_TARGET_MS: Final[Decimal] = Decimal("250.0")
SEARCH_P95_TARGET_MS: Final[Decimal] = Decimal("500.0")
SEARCH_P99_TARGET_MS: Final[Decimal] = Decimal("750.0")

# ==============================================================================
# Pydantic Models for JSON Parsing
# ==============================================================================


class BenchmarkStats(BaseModel):
    """Statistics from a pytest-benchmark run.

    Fields match pytest-benchmark JSON output structure.
    """

    min: float = Field(description="Minimum execution time in seconds")
    max: float = Field(description="Maximum execution time in seconds")
    mean: float = Field(description="Mean execution time in seconds")
    median: float = Field(description="Median execution time in seconds")
    stddev: float = Field(description="Standard deviation in seconds")
    q1: float = Field(description="First quartile (25th percentile) in seconds")
    q3: float = Field(description="Third quartile (75th percentile) in seconds")
    iqr: float = Field(description="Interquartile range in seconds")

    # Percentiles (may be missing in some output formats)
    p50: float | None = Field(None, description="50th percentile (median) in seconds")
    p95: float | None = Field(None, description="95th percentile in seconds")
    p99: float | None = Field(None, description="99th percentile in seconds")


class BenchmarkResult(BaseModel):
    """Individual benchmark test result.

    Represents a single benchmark from pytest-benchmark output.
    """

    name: str = Field(description="Test name (e.g., test_indexing_baseline)")
    fullname: str = Field(description="Full test path")
    stats: BenchmarkStats = Field(description="Statistical measurements")
    rounds: int = Field(description="Number of benchmark rounds executed")


class BenchmarkMachineInfo(BaseModel):
    """Machine information from benchmark run.

    Captures environment context for reproducibility.
    """

    node: str = Field(description="Machine hostname")
    processor: str = Field(description="CPU model")
    python_version: str = Field(description="Python version string")


class BenchmarkReport(BaseModel):
    """Complete pytest-benchmark JSON report.

    Top-level structure of benchmark output file.
    """

    machine_info: BenchmarkMachineInfo = Field(description="Environment information")
    benchmarks: list[BenchmarkResult] = Field(description="List of benchmark results")


# ==============================================================================
# Metric Extraction
# ==============================================================================


def extract_indexing_metrics(report: BenchmarkReport) -> BenchmarkResult | None:
    """Extract indexing benchmark metrics.

    Args:
        report: Parsed benchmark report

    Returns:
        Indexing benchmark result, or None if not found
    """
    for benchmark in report.benchmarks:
        if "indexing" in benchmark.name.lower():
            return benchmark
    return None


def extract_search_metrics(report: BenchmarkReport) -> BenchmarkResult | None:
    """Extract search benchmark metrics.

    Args:
        report: Parsed benchmark report

    Returns:
        Search benchmark result, or None if not found
    """
    for benchmark in report.benchmarks:
        if "search" in benchmark.name.lower():
            return benchmark
    return None


# ==============================================================================
# Display Functions
# ==============================================================================


def format_seconds(seconds: float) -> str:
    """Format seconds with appropriate precision.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted string with units
    """
    if seconds < 1.0:
        return f"{seconds * 1000:.2f}ms"
    return f"{seconds:.2f}s"


def format_comparison(actual: Decimal, target: Decimal) -> str:
    """Format performance comparison with target.

    Args:
        actual: Actual measured value
        target: Target performance value

    Returns:
        Comparison string with pass/fail indicator
    """
    if actual <= target:
        percentage = (actual / target) * 100
        return f"✓ PASS ({percentage:.1f}% of target)"
    else:
        percentage = (actual / target) * 100
        return f"✗ FAIL ({percentage:.1f}% of target)"


def display_indexing_metrics(benchmark: BenchmarkResult) -> None:
    """Display indexing performance metrics.

    Args:
        benchmark: Indexing benchmark result
    """
    print("\n" + "=" * 70)
    print("INDEXING PERFORMANCE BASELINE")
    print("=" * 70)

    mean_seconds = Decimal(str(benchmark.stats.mean))
    median_seconds = Decimal(str(benchmark.stats.median))

    print(f"\nTest: {benchmark.name}")
    print(f"Rounds: {benchmark.rounds}")
    print(f"\nTiming Statistics:")
    print(f"  Mean:   {format_seconds(float(mean_seconds))}")
    print(f"  Median: {format_seconds(float(median_seconds))}")
    print(f"  Min:    {format_seconds(benchmark.stats.min)}")
    print(f"  Max:    {format_seconds(benchmark.stats.max)}")
    print(f"  StdDev: {format_seconds(benchmark.stats.stddev)}")

    print(f"\nTarget Comparison:")
    print(f"  Target:  {format_seconds(float(INDEXING_TARGET_SECONDS))}")
    print(f"  Result:  {format_comparison(mean_seconds, INDEXING_TARGET_SECONDS)}")


def display_search_metrics(benchmark: BenchmarkResult) -> None:
    """Display search performance metrics.

    Args:
        benchmark: Search benchmark result
    """
    print("\n" + "=" * 70)
    print("SEARCH PERFORMANCE BASELINE")
    print("=" * 70)

    mean_ms = Decimal(str(benchmark.stats.mean * 1000))
    p50_ms = (
        Decimal(str(benchmark.stats.p50 * 1000))
        if benchmark.stats.p50
        else Decimal(str(benchmark.stats.median * 1000))
    )
    p95_ms = Decimal(str(benchmark.stats.q3 * 1000)) if not benchmark.stats.p95 else Decimal(str(benchmark.stats.p95 * 1000))
    p99_ms = Decimal(str(benchmark.stats.max * 1000)) if not benchmark.stats.p99 else Decimal(str(benchmark.stats.p99 * 1000))

    print(f"\nTest: {benchmark.name}")
    print(f"Rounds: {benchmark.rounds}")
    print(f"\nLatency Statistics:")
    print(f"  Mean:   {format_seconds(benchmark.stats.mean)}")
    print(f"  Median: {format_seconds(benchmark.stats.median)}")
    print(f"  Min:    {format_seconds(benchmark.stats.min)}")
    print(f"  Max:    {format_seconds(benchmark.stats.max)}")

    print(f"\nPercentile Analysis:")
    print(f"  P50: {float(p50_ms):.2f}ms")
    print(f"  P95: {float(p95_ms):.2f}ms")
    print(f"  P99: {float(p99_ms):.2f}ms")

    print(f"\nTarget Comparisons:")
    print(f"  P50 Target: {float(SEARCH_P50_TARGET_MS):.2f}ms")
    print(f"      Result: {format_comparison(p50_ms, SEARCH_P50_TARGET_MS)}")
    print(f"  P95 Target: {float(SEARCH_P95_TARGET_MS):.2f}ms")
    print(f"      Result: {format_comparison(p95_ms, SEARCH_P95_TARGET_MS)}")


def display_environment(machine_info: BenchmarkMachineInfo) -> None:
    """Display benchmark environment information.

    Args:
        machine_info: Machine information from benchmark run
    """
    print("\n" + "=" * 70)
    print("ENVIRONMENT INFORMATION")
    print("=" * 70)
    print(f"\nMachine:  {machine_info.node}")
    print(f"CPU:      {machine_info.processor}")
    print(f"Python:   {machine_info.python_version}")


# ==============================================================================
# Main Entry Point
# ==============================================================================


def parse_baseline_file(file_path: Path) -> int:
    """Parse and display baseline results from JSON file.

    Args:
        file_path: Path to pytest-benchmark JSON output

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Read and parse JSON
        json_data: dict[str, Any] = json.loads(file_path.read_text(encoding="utf-8"))
        report = BenchmarkReport.model_validate(json_data)

        # Display environment info
        display_environment(report.machine_info)

        # Extract and display indexing metrics
        indexing = extract_indexing_metrics(report)
        if indexing:
            display_indexing_metrics(indexing)
        else:
            print("\nWarning: No indexing benchmark found in results", file=sys.stderr)

        # Extract and display search metrics
        search = extract_search_metrics(report)
        if search:
            display_search_metrics(search)
        else:
            print("\nWarning: No search benchmark found in results", file=sys.stderr)

        print("\n" + "=" * 70)
        print()

        return 0

    except FileNotFoundError:
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON: {e}", file=sys.stderr)
        return 1
    except ValidationError as e:
        print(f"Error: Invalid benchmark format: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    if len(sys.argv) != 2:
        print("Usage: python scripts/parse_baseline.py <baseline-results.json>", file=sys.stderr)
        print("\nParses pytest-benchmark JSON output and displays performance metrics.", file=sys.stderr)
        return 1

    file_path = Path(sys.argv[1])
    return parse_baseline_file(file_path)


if __name__ == "__main__":
    sys.exit(main())
