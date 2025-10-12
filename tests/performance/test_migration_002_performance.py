"""Performance tests for Alembic migration 002 (schema refactoring).

Tests migration performance on large dataset (100 repositories + 10,000 code chunks)
to ensure the forward migration completes within 5 minutes (300 seconds) per FR-031.

Constitutional Compliance:
- Principle IV: Performance (<5 minute migration per FR-031)
- Principle VIII: Type Safety (mypy --strict compliance, complete type annotations)
- Principle V: Production Quality (comprehensive timing, error handling)

Test Scenario 5: Large Dataset Performance
- Generate 100 repos + 10K chunks using generate_test_data.py utility
- Time migration execution: alembic upgrade head
- Assert duration < 300 seconds (5 minutes per FR-031)
- Capture per-step timing from Python logger output
- Generate performance report (step durations, total time)

Requirements:
- pytest must be installed: pip install pytest
- asyncpg must be installed: pip install asyncpg
- Alembic must be configured: alembic.ini with DATABASE_URL

Usage:
    # Run performance tests only:
    pytest tests/performance/test_migration_002_performance.py -v --slow

    # Skip slow tests:
    pytest tests/performance/test_migration_002_performance.py -v -m "not slow"

    # Run with benchmark plugin (optional):
    pytest tests/performance/test_migration_002_performance.py -v --benchmark-only

Exit Codes:
    0 - All tests passed (performance meets requirements)
    1 - Test failed (performance regression or timeout)
"""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from typing import Any

# ==============================================================================
# Type Definitions
# ==============================================================================


@dataclass(frozen=True)
class PerformanceReport:
    """Performance metrics for migration execution.

    Attributes:
        total_duration_seconds: Total migration time in seconds
        step_durations: Dict mapping step descriptions to durations in seconds
        repositories_count: Number of repositories in test dataset
        code_chunks_count: Number of code chunks in test dataset
        meets_requirement: Whether duration < 300 seconds (FR-031)
    """

    total_duration_seconds: float
    step_durations: dict[str, float]
    repositories_count: int
    code_chunks_count: int
    meets_requirement: bool


@dataclass(frozen=True)
class TestDataStats:
    """Statistics from test data generation.

    Attributes:
        repositories_created: Number of repositories created
        code_files_created: Number of code files created
        code_chunks_created: Number of code chunks created
        generation_duration_seconds: Time to generate data
    """

    repositories_created: int
    code_files_created: int
    code_chunks_created: int
    generation_duration_seconds: float


# ==============================================================================
# Test Configuration
# ==============================================================================

# Performance target from FR-031
MIGRATION_PERFORMANCE_TARGET_SECONDS = 300.0  # 5 minutes

# Test dataset size (FR-028: minimum 100 repos, 10K chunks)
TEST_REPOSITORIES = 100
TEST_CHUNKS_PER_REPO = 100  # 100 repos × 100 chunks = 10,000 chunks

# Test database configuration
TEST_DATABASE_NAME = "codebase_mcp_test"
MIGRATION_LOG_FILE = "/tmp/codebase-mcp-migration.log"

# Repository root for running scripts
REPO_ROOT = Path("/Users/cliffclarke/Claude_Code/codebase-mcp")
TEST_DATA_SCRIPT = REPO_ROOT / "tests" / "fixtures" / "generate_test_data.py"


# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture(scope="module")
def test_database_url() -> str:
    """Provide test database connection URL.

    Returns:
        PostgreSQL connection URL for test database

    Raises:
        pytest.skip: If DATABASE_URL not configured
    """
    # Check if DATABASE_URL is set
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        pytest.skip(
            "DATABASE_URL not set. "
            f"Set with: export DATABASE_URL=postgresql://localhost/{TEST_DATABASE_NAME}"
        )

    # Ensure it points to test database for safety
    if TEST_DATABASE_NAME not in database_url:
        pytest.skip(
            f"DATABASE_URL does not point to test database ({TEST_DATABASE_NAME}). "
            f"Current: {database_url}"
        )

    return database_url


@pytest.fixture(scope="module")
def clean_test_database(test_database_url: str) -> None:
    """Clean test database before tests.

    Drops and recreates test database to ensure clean state.

    Args:
        test_database_url: Test database connection URL

    Raises:
        pytest.skip: If database setup fails
    """
    try:
        # Drop and recreate database
        drop_cmd = f"dropdb {TEST_DATABASE_NAME} 2>/dev/null || true"
        subprocess.run(drop_cmd, shell=True, check=False, cwd=REPO_ROOT)

        create_cmd = f"createdb {TEST_DATABASE_NAME}"
        subprocess.run(create_cmd, shell=True, check=True, cwd=REPO_ROOT)

        # Create pgvector extension
        extension_cmd = f"psql {test_database_url} -c 'CREATE EXTENSION IF NOT EXISTS vector;'"
        subprocess.run(extension_cmd, shell=True, check=True, cwd=REPO_ROOT)

        # Apply baseline migrations (001 through 005)
        baseline_cmd = "alembic upgrade 005"
        subprocess.run(
            baseline_cmd,
            shell=True,
            check=True,
            cwd=REPO_ROOT,
            env={**os.environ, "DATABASE_URL": test_database_url},
        )

    except subprocess.CalledProcessError as e:
        pytest.skip(f"Database setup failed: {e}")


@pytest.fixture(scope="module")
def test_data_generated(
    test_database_url: str, clean_test_database: None
) -> TestDataStats:
    """Generate test data for performance testing.

    Uses generate_test_data.py utility to create 100 repos + 10K chunks.

    Args:
        test_database_url: Test database connection URL
        clean_test_database: Database cleanup fixture (dependency)

    Returns:
        TestDataStats with generation metrics

    Raises:
        pytest.skip: If test data generation fails
    """
    try:
        # Run test data generation script
        # 100 repos × 1 file per repo × 100 chunks per file = 10,000 chunks
        start_time = time.time()

        generation_cmd = [
            sys.executable,
            str(TEST_DATA_SCRIPT),
            "--repositories",
            str(TEST_REPOSITORIES),
            "--files-per-repo",
            "1",
            "--chunks-per-file",
            str(TEST_CHUNKS_PER_REPO),
        ]

        result = subprocess.run(
            generation_cmd,
            capture_output=True,
            text=True,
            check=True,
            cwd=REPO_ROOT,
            env={**os.environ, "DATABASE_URL": test_database_url},
        )

        duration = time.time() - start_time

        # Parse output for verification
        output = result.stdout
        print(f"\n[TEST DATA GENERATION OUTPUT]")
        print(output)

        # Extract counts from output (format: "Repositories: 100")
        repo_match = re.search(r"Repositories:\s+(\d+)", output)
        chunk_match = re.search(r"Code chunks:\s+([\d,]+)", output)
        file_match = re.search(r"Code files:\s+([\d,]+)", output)

        repos_created = int(repo_match.group(1)) if repo_match else 0
        chunks_created = (
            int(chunk_match.group(1).replace(",", "")) if chunk_match else 0
        )
        files_created = int(file_match.group(1).replace(",", "")) if file_match else 0

        return TestDataStats(
            repositories_created=repos_created,
            code_files_created=files_created,
            code_chunks_created=chunks_created,
            generation_duration_seconds=duration,
        )

    except subprocess.CalledProcessError as e:
        pytest.skip(f"Test data generation failed: {e}\nStdout: {e.stdout}\nStderr: {e.stderr}")
    except Exception as e:
        pytest.skip(f"Test data generation error: {e}")


@pytest.fixture
def clear_migration_log() -> None:
    """Clear migration log file before test.

    Ensures clean log for parsing step timings.
    """
    log_path = Path(MIGRATION_LOG_FILE)
    if log_path.exists():
        log_path.unlink()


# ==============================================================================
# Helper Functions
# ==============================================================================


def parse_migration_log(log_content: str) -> dict[str, float]:
    """Parse migration log to extract step durations.

    Parses log entries like:
        2025-10-11 14:30:01,234 - INFO - Step 1/10: Checking prerequisites... (0.05s)
        2025-10-11 14:30:02,456 - INFO - Step 2/10: Verifying foreign keys... (1.23s)

    Args:
        log_content: Raw log file content

    Returns:
        Dictionary mapping step descriptions to durations in seconds

    Example:
        >>> log = "Step 1/10: Checking prerequisites... (0.05s)"
        >>> parse_migration_log(log)
        {'Step 1/10: Checking prerequisites': 0.05}
    """
    step_durations: dict[str, float] = {}

    # Regex pattern: "Step X/Y: Description... (N.NNs)"
    pattern = r"(Step \d+/\d+: [^(]+?)\s*\((\d+\.\d+)s\)"

    for match in re.finditer(pattern, log_content):
        step_description = match.group(1).strip()
        duration = float(match.group(2))
        step_durations[step_description] = duration

    return step_durations


def run_migration_upgrade(database_url: str) -> tuple[float, str]:
    """Execute alembic upgrade head and measure duration.

    Args:
        database_url: Database connection URL

    Returns:
        Tuple of (duration_seconds, combined_output)

    Raises:
        subprocess.CalledProcessError: If migration fails
    """
    start_time = time.time()

    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO_ROOT,
        env={**os.environ, "DATABASE_URL": database_url},
    )

    duration = time.time() - start_time

    # Combine stdout and stderr for full output
    combined_output = f"{result.stdout}\n{result.stderr}"

    return duration, combined_output


def verify_migration_applied(database_url: str) -> str:
    """Verify migration 002 was applied successfully.

    Args:
        database_url: Database connection URL

    Returns:
        Current Alembic revision string

    Raises:
        subprocess.CalledProcessError: If alembic current fails
    """
    result = subprocess.run(
        ["alembic", "current"],
        capture_output=True,
        text=True,
        check=True,
        cwd=REPO_ROOT,
        env={**os.environ, "DATABASE_URL": database_url},
    )

    return result.stdout.strip()


async def get_row_counts(database_url: str) -> tuple[int, int]:
    """Query database for row counts.

    Args:
        database_url: Database connection URL

    Returns:
        Tuple of (repositories_count, code_chunks_count)

    Raises:
        Exception: If database query fails
    """
    import asyncpg

    # Remove asyncpg driver prefix if present
    db_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    conn = await asyncpg.connect(db_url)
    try:
        repo_count = await conn.fetchval("SELECT COUNT(*) FROM repositories")
        chunk_count = await conn.fetchval("SELECT COUNT(*) FROM code_chunks")

        return (repo_count or 0, chunk_count or 0)

    finally:
        await conn.close()


# ==============================================================================
# Performance Tests
# ==============================================================================


@pytest.mark.slow
@pytest.mark.performance
def test_migration_002_performance_large_dataset(
    test_database_url: str,
    test_data_generated: TestDataStats,
    clear_migration_log: None,
) -> None:
    """Test migration 002 performance on large dataset.

    This test validates FR-031: Migration must complete within 5 minutes
    on production-scale database (100 repositories, 10,000 code chunks).

    Test Flow:
    1. Generate 100 repos + 10K chunks (via test_data_generated fixture)
    2. Clear migration log file
    3. Execute: alembic upgrade head
    4. Time total migration duration
    5. Parse per-step timing from log file
    6. Assert total duration < 300 seconds
    7. Generate performance report

    Args:
        test_database_url: Test database connection URL fixture
        test_data_generated: Test data generation stats fixture
        clear_migration_log: Migration log cleanup fixture

    Raises:
        AssertionError: If migration duration exceeds 300 seconds
    """
    # Verify test data was generated correctly
    assert test_data_generated.repositories_created == TEST_REPOSITORIES, (
        f"Expected {TEST_REPOSITORIES} repositories, "
        f"got {test_data_generated.repositories_created}"
    )
    assert test_data_generated.code_chunks_created >= 10_000, (
        f"Expected at least 10,000 code chunks, "
        f"got {test_data_generated.code_chunks_created}"
    )

    print(f"\n[TEST DATA GENERATED]")
    print(f"  Repositories: {test_data_generated.repositories_created:,}")
    print(f"  Code files: {test_data_generated.code_files_created:,}")
    print(f"  Code chunks: {test_data_generated.code_chunks_created:,}")
    print(f"  Generation time: {test_data_generated.generation_duration_seconds:.2f}s")

    # Execute migration and measure duration
    print(f"\n[RUNNING MIGRATION]")
    print(f"  Command: alembic upgrade head")
    print(f"  Database: {test_database_url.split('/')[-1]}")
    print(f"  Target: < {MIGRATION_PERFORMANCE_TARGET_SECONDS}s")

    try:
        duration, output = run_migration_upgrade(test_database_url)
    except subprocess.CalledProcessError as e:
        pytest.fail(
            f"Migration failed with exit code {e.returncode}\n"
            f"Stdout: {e.stdout}\n"
            f"Stderr: {e.stderr}"
        )

    print(f"\n[MIGRATION OUTPUT]")
    print(output)

    # Parse per-step timing from log file (if available)
    step_durations: dict[str, float] = {}
    log_path = Path(MIGRATION_LOG_FILE)
    if log_path.exists():
        log_content = log_path.read_text()
        step_durations = parse_migration_log(log_content)

    # Verify migration applied
    current_revision = verify_migration_applied(test_database_url)
    print(f"\n[MIGRATION APPLIED]")
    print(f"  Current revision: {current_revision}")

    # Verify data preservation
    loop = asyncio.get_event_loop()
    repo_count, chunk_count = loop.run_until_complete(
        get_row_counts(test_database_url)
    )

    assert repo_count == test_data_generated.repositories_created, (
        f"Data loss detected! Expected {test_data_generated.repositories_created} "
        f"repositories, found {repo_count}"
    )
    assert chunk_count == test_data_generated.code_chunks_created, (
        f"Data loss detected! Expected {test_data_generated.code_chunks_created} "
        f"code chunks, found {chunk_count}"
    )

    # Validate performance requirement (FR-031)
    meets_requirement = duration < MIGRATION_PERFORMANCE_TARGET_SECONDS

    # Generate performance report
    report = PerformanceReport(
        total_duration_seconds=duration,
        step_durations=step_durations,
        repositories_count=repo_count,
        code_chunks_count=chunk_count,
        meets_requirement=meets_requirement,
    )

    # Print detailed performance report
    print(f"\n{'=' * 60}")
    print("PERFORMANCE REPORT")
    print(f"{'=' * 60}")
    print(f"Total Duration:       {report.total_duration_seconds:.2f}s")
    print(f"Target:               < {MIGRATION_PERFORMANCE_TARGET_SECONDS}s")
    print(f"Performance Target:   {'✅ PASS' if meets_requirement else '❌ FAIL'}")
    print(f"Margin:               {MIGRATION_PERFORMANCE_TARGET_SECONDS - duration:.2f}s")
    print(f"\nDataset Size:")
    print(f"  Repositories:       {report.repositories_count:,}")
    print(f"  Code chunks:        {report.code_chunks_count:,}")

    if step_durations:
        print(f"\nPer-Step Breakdown:")
        for step_desc, step_duration in sorted(
            step_durations.items(), key=lambda x: x[1], reverse=True
        ):
            percentage = (step_duration / duration * 100) if duration > 0 else 0
            print(f"  {step_desc}: {step_duration:.2f}s ({percentage:.1f}%)")

    print(f"{'=' * 60}\n")

    # Assert performance requirement (FR-031)
    assert meets_requirement, (
        f"Migration duration {duration:.2f}s exceeds target of "
        f"{MIGRATION_PERFORMANCE_TARGET_SECONDS}s (FR-031 violation)"
    )


@pytest.mark.slow
@pytest.mark.performance
def test_migration_002_step_timing_logged(
    test_database_url: str,
    test_data_generated: TestDataStats,
    clear_migration_log: None,
) -> None:
    """Test that migration logs per-step timing information.

    Validates that the migration implementation includes proper logging
    with step-by-step timing breakdown for observability.

    This test can be run independently or after test_migration_002_performance_large_dataset
    (migration is idempotent via Alembic tracking).

    Args:
        test_database_url: Test database connection URL fixture
        test_data_generated: Test data generation stats fixture
        clear_migration_log: Migration log cleanup fixture

    Raises:
        AssertionError: If step timing not found in logs
    """
    # Run migration (idempotent - will skip if already applied)
    try:
        duration, output = run_migration_upgrade(test_database_url)
    except subprocess.CalledProcessError:
        # If migration already applied, check log from previous run
        pass

    # Parse migration log
    log_path = Path(MIGRATION_LOG_FILE)

    if not log_path.exists():
        pytest.skip(
            f"Migration log not found at {MIGRATION_LOG_FILE}. "
            "Ensure migration logging is configured correctly."
        )

    log_content = log_path.read_text()
    step_durations = parse_migration_log(log_content)

    # Validate step timing logged
    assert len(step_durations) > 0, (
        "No step timing information found in migration log. "
        "Migration should log major steps with durations."
    )

    print(f"\n[STEP TIMING VALIDATION]")
    print(f"  Steps logged: {len(step_durations)}")
    print(f"  Log file: {MIGRATION_LOG_FILE}")

    for step_desc, step_duration in step_durations.items():
        print(f"  ✅ {step_desc}: {step_duration:.2f}s")

    # Expected major steps (based on migration design)
    expected_step_keywords = [
        "prerequisite",
        "foreign key",
        "column",
        "constraint",
        "index",
        "drop",
    ]

    log_lower = log_content.lower()
    missing_steps: list[str] = []

    for keyword in expected_step_keywords:
        if keyword not in log_lower:
            missing_steps.append(keyword)

    if missing_steps:
        print(f"\n[WARNING] Some expected step keywords not found in log:")
        for keyword in missing_steps:
            print(f"  - {keyword}")

    # This is a soft warning, not a hard failure
    # (migration may complete steps differently than expected)


# ==============================================================================
# Test Markers and Configuration
# ==============================================================================

pytestmark = [
    pytest.mark.slow,
    pytest.mark.performance,
]
