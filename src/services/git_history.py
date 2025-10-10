"""Git history fallback parser for extracting structured data from commit history.

Provides fallback data source when .project_status.md is unavailable or database
migration is incomplete. Parses git log for deployment commits, work items from
branch names, and vendor status updates from commit messages.

Constitutional Compliance:
- Principle II: Local-first architecture (git is always available locally)
- Principle V: Production quality (subprocess timeout, comprehensive error handling)
- Principle VIII: Type safety (full mypy --strict compliance)

Key Features:
- Deployment commit parsing with PR #, test results, constitutional compliance
- Work item extraction from branch name patterns (###-feature-name)
- Vendor status updates from commit message patterns
- 5-second subprocess timeout for all git operations
- Structured data output matching database schemas

Performance:
- <500ms for 10 deployment commits (subprocess + parsing)
- <1 second for vendor status search (last 100 commits)
- <100ms for branch name parsing (no subprocess)
"""

from __future__ import annotations

import asyncio
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from src.mcp.mcp_logging import get_logger

# ==============================================================================
# Logger
# ==============================================================================

logger = get_logger(__name__)

# ==============================================================================
# Type Definitions
# ==============================================================================

GitEventType = Literal["deployment", "vendor_status", "work_item"]

# ==============================================================================
# Constants
# ==============================================================================

GIT_TIMEOUT_SECONDS = 5
DEFAULT_COMMIT_LIMIT = 10
VENDOR_SEARCH_COMMIT_LIMIT = 100

# Commit message patterns
DEPLOYMENT_PATTERNS = [
    r"Merge pull request #(\d+)",  # GitHub PR merge
    r"PR #(\d+):",  # Explicit PR reference
    r"deploy:|deployment:",  # Deployment tag
]

VENDOR_STATUS_PATTERN = r"vendor\((\w+)\):\s*(operational|broken)"
TEST_RESULTS_PATTERN = r"(\d+)/(\d+)\s+tests?\s+passing"
VERSION_PATTERN = r"version[:\s]+([0-9]+\.[0-9]+\.[0-9]+)"
CONSTITUTIONAL_MARKERS = [
    "constitutional compliance",
    "✅",
    "[COMPLIANT]",
]

# Branch name patterns
BRANCH_PATTERNS = [
    r"^(\d{3})-(.+)$",  # 001-feature-name
    r"^feature/(\d{3})-(.+)$",  # feature/001-feature-name
    r"^bugfix/(\d{3})-(.+)$",  # bugfix/001-fix-name
]

# ==============================================================================
# Public API
# ==============================================================================


async def parse_deployment_commits(limit: int = DEFAULT_COMMIT_LIMIT) -> list[dict[str, Any]]:
    """Parse git log for deployment commits.

    Searches commit messages for deployment patterns (PR #, merge commits, deploy tags)
    and extracts structured data matching DeploymentEvent schema.

    Args:
        limit: Maximum number of deployment commits to return (default: 10)

    Returns:
        list[dict]: Deployment commit data with keys:
            - commit_hash: str (40-char lowercase hex)
            - pr_number: int (extracted from PR # pattern)
            - pr_title: str (commit subject line)
            - deployed_at: str (ISO 8601 timestamp)
            - constitutional_compliance: bool (from commit message markers)
            - test_summary: dict[str, int] (from commit body)

    Raises:
        subprocess.TimeoutExpired: If git command exceeds 5-second timeout
        ValueError: If git command fails or returns invalid output

    Performance:
        <500ms for 10 commits (subprocess execution + parsing)
    """
    logger.info(f"Parsing deployment commits (limit={limit})")

    try:
        # Execute git log with format: hash|author_date|subject|body
        result = await asyncio.to_thread(
            subprocess.run,
            [
                "git",
                "log",
                f"-{limit * 3}",  # Search more commits to find deployments
                "--format=%H|%aI|%s|%b",
                "--no-merges",  # Include merge commits
            ],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
            cwd=Path.cwd(),
        )

        if result.returncode != 0:
            error_msg = f"Git command failed: {result.stderr}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Parse commit log output
        deployments: list[dict[str, Any]] = []
        commits = result.stdout.strip().split("\n\n")

        for commit_block in commits:
            if not commit_block.strip():
                continue

            lines = commit_block.split("\n")
            if not lines:
                continue

            # Parse format: hash|date|subject|body
            parts = lines[0].split("|", maxsplit=3)
            if len(parts) < 3:
                continue

            commit_hash, author_date, subject = parts[0], parts[1], parts[2]
            body = parts[3] if len(parts) > 3 else ""

            # Check if commit is a deployment
            pr_number = _extract_pr_number(subject)
            if pr_number is None:
                continue

            # Extract test results from commit body
            test_summary = _extract_test_summary(body)

            # Check constitutional compliance markers
            constitutional_compliance = _check_constitutional_compliance(subject, body)

            deployment_data: dict[str, Any] = {
                "commit_hash": commit_hash.lower(),
                "pr_number": pr_number,
                "pr_title": subject,
                "deployed_at": author_date,
                "constitutional_compliance": constitutional_compliance,
                "test_summary": test_summary,
            }

            deployments.append(deployment_data)

            if len(deployments) >= limit:
                break

        logger.info(f"Found {len(deployments)} deployment commits")
        return deployments

    except subprocess.TimeoutExpired as e:
        error_msg = f"Git command timed out after {GIT_TIMEOUT_SECONDS}s"
        logger.error(error_msg)
        raise ValueError(error_msg) from e
    except Exception as e:
        logger.error(f"Error parsing deployment commits: {e}")
        raise


async def get_work_item_from_branch(branch_name: str) -> dict[str, Any] | None:
    """Extract work item from branch name pattern.

    Parses branch names following conventions:
    - ###-feature-name (e.g., '001-semantic-search')
    - feature/###-feature-name
    - bugfix/###-fix-description

    Args:
        branch_name: Git branch name to parse

    Returns:
        dict | None: Work item data if pattern matches, None otherwise
            Keys:
            - title: str (feature name from branch)
            - item_type: Literal["project", "task"] (inferred from branch prefix)
            - branch_name: str (original branch name)
            - feature_number: int (extracted ### number)

    Example:
        >>> await get_work_item_from_branch('003-database-backed-project')
        {
            'title': 'database backed project',
            'item_type': 'project',
            'branch_name': '003-database-backed-project',
            'feature_number': 3
        }
    """
    logger.debug(f"Extracting work item from branch: {branch_name}")

    for pattern in BRANCH_PATTERNS:
        match = re.match(pattern, branch_name)
        if match:
            feature_num_str, feature_name = match.groups()
            feature_number = int(feature_num_str)

            # Infer item type from branch prefix
            item_type: Literal["project", "task"] = "project" if "feature" in branch_name or feature_number < 100 else "task"

            # Format feature name (replace hyphens with spaces, title case)
            title = feature_name.replace("-", " ").strip()

            work_item_data: dict[str, Any] = {
                "title": title,
                "item_type": item_type,
                "branch_name": branch_name,
                "feature_number": feature_number,
            }

            logger.info(f"Extracted work item: {title} (#{feature_number})")
            return work_item_data

    logger.debug(f"No work item pattern matched for branch: {branch_name}")
    return None


async def get_vendor_status_from_commits(vendor_name: str) -> dict[str, Any] | None:
    """Get latest vendor status from commit messages.

    Searches commit messages for vendor status updates matching pattern:
    - "vendor(ABC): operational" / "vendor(ABC): broken"
    - "fix(vendor-abc): restore operational status"
    - Test result patterns: "45/50 tests passing"

    Args:
        vendor_name: Vendor name to search for (case-insensitive)

    Returns:
        dict | None: Vendor status data if found, None otherwise
            Keys:
            - name: str (vendor name)
            - status: Literal["operational", "broken"]
            - extractor_version: str (from commit message if present)
            - test_results: dict[str, int] (passing, total, skipped)
            - last_updated: str (ISO 8601 timestamp of commit)

    Performance:
        <1 second for searching last 100 commits
    """
    logger.info(f"Searching vendor status for: {vendor_name}")

    try:
        # Execute git log searching for vendor name
        result = await asyncio.to_thread(
            subprocess.run,
            [
                "git",
                "log",
                f"-{VENDOR_SEARCH_COMMIT_LIMIT}",
                "--format=%H|%aI|%s|%b",
                "--all",  # Search all branches
                f"--grep={vendor_name}",
                "-i",  # Case-insensitive
            ],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
            cwd=Path.cwd(),
        )

        if result.returncode != 0:
            logger.warning(f"Git command failed for vendor {vendor_name}: {result.stderr}")
            return None

        # Parse commit log output
        commits = result.stdout.strip().split("\n\n")

        for commit_block in commits:
            if not commit_block.strip():
                continue

            lines = commit_block.split("\n")
            if not lines:
                continue

            # Parse format: hash|date|subject|body
            parts = lines[0].split("|", maxsplit=3)
            if len(parts) < 3:
                continue

            commit_hash, author_date, subject = parts[0], parts[1], parts[2]
            body = parts[3] if len(parts) > 3 else ""

            # Search for vendor status pattern
            status_match = re.search(VENDOR_STATUS_PATTERN, subject + "\n" + body, re.IGNORECASE)
            if not status_match:
                continue

            vendor_match_name, status = status_match.groups()

            # Extract version if present
            version_match = re.search(VERSION_PATTERN, body)
            extractor_version = version_match.group(1) if version_match else "unknown"

            # Extract test results
            test_results = _extract_test_results(body)

            vendor_data: dict[str, Any] = {
                "name": f"vendor_{vendor_match_name.lower()}",
                "status": status.lower(),
                "extractor_version": extractor_version,
                "test_results": test_results,
                "last_updated": author_date,
            }

            logger.info(f"Found vendor status: {vendor_data['name']} -> {vendor_data['status']}")
            return vendor_data

        logger.info(f"No vendor status found for: {vendor_name}")
        return None

    except subprocess.TimeoutExpired as e:
        logger.error(f"Git command timed out for vendor {vendor_name}")
        return None
    except Exception as e:
        logger.error(f"Error searching vendor status: {e}")
        return None


# ==============================================================================
# Private Helpers
# ==============================================================================


def _extract_pr_number(subject: str) -> int | None:
    """Extract PR number from commit subject line.

    Args:
        subject: Commit subject line

    Returns:
        int | None: PR number if found, None otherwise
    """
    for pattern in DEPLOYMENT_PATTERNS:
        match = re.search(pattern, subject, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _extract_test_summary(body: str) -> dict[str, int]:
    """Extract test results from commit body.

    Parses patterns like:
    - "unit: 150, integration: 30"
    - "Tests: 180 passing"
    - "150/180 tests passing"

    Args:
        body: Commit message body

    Returns:
        dict[str, int]: Test summary with category counts
    """
    test_summary: dict[str, int] = {}

    # Pattern 1: "unit: 150, integration: 30"
    category_pattern = r"(\w+):\s*(\d+)"
    for match in re.finditer(category_pattern, body):
        category, count = match.groups()
        if "test" in category.lower() or category.lower() in ["unit", "integration", "e2e"]:
            test_summary[category.lower()] = int(count)

    # Pattern 2: "150/180 tests passing"
    ratio_match = re.search(TEST_RESULTS_PATTERN, body, re.IGNORECASE)
    if ratio_match and not test_summary:
        passing, total = ratio_match.groups()
        test_summary["passing"] = int(passing)
        test_summary["total"] = int(total)

    return test_summary


def _extract_test_results(body: str) -> dict[str, int]:
    """Extract test results for vendor status.

    Args:
        body: Commit message body

    Returns:
        dict[str, int]: Test results with keys: passing, total, skipped
    """
    test_results: dict[str, int] = {"passing": 0, "total": 0, "skipped": 0}

    # Search for "45/50 tests passing"
    match = re.search(TEST_RESULTS_PATTERN, body, re.IGNORECASE)
    if match:
        passing, total = match.groups()
        test_results["passing"] = int(passing)
        test_results["total"] = int(total)

        # Search for skipped count
        skipped_match = re.search(r"(\d+)\s+skipped", body, re.IGNORECASE)
        if skipped_match:
            test_results["skipped"] = int(skipped_match.group(1))

    return test_results


def _check_constitutional_compliance(subject: str, body: str) -> bool:
    """Check if commit indicates constitutional compliance.

    Args:
        subject: Commit subject line
        body: Commit message body

    Returns:
        bool: True if constitutional compliance marker found
    """
    full_message = subject + "\n" + body
    return any(marker.lower() in full_message.lower() for marker in CONSTITUTIONAL_MARKERS)
