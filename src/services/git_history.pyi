"""Type stubs for git_history service.

Fallback data source parser for extracting structured data from git history.
Provides deployment commits, work item extraction from branch names, and vendor
status parsing from commit messages.

Constitutional Compliance:
- Principle V: Production quality (subprocess timeout, error handling)
- Principle VIII: Type safety (full mypy --strict compliance)
"""

from __future__ import annotations

from typing import Any, Literal

# ==============================================================================
# Type Definitions
# ==============================================================================

GitEventType = Literal["deployment", "vendor_status", "work_item"]

# ==============================================================================
# Public API
# ==============================================================================

async def parse_deployment_commits(limit: int = 10) -> list[dict[str, Any]]:
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

    Example:
        >>> commits = await parse_deployment_commits(limit=5)
        >>> commits[0]
        {
            'commit_hash': 'a1b2c3d4e5f6...40chars',
            'pr_number': 123,
            'pr_title': 'feat(vendor): add ABC extractor',
            'deployed_at': '2025-10-10T14:30:00Z',
            'constitutional_compliance': True,
            'test_summary': {'unit': 150, 'integration': 30}
        }
    """
    ...

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

        >>> await get_work_item_from_branch('invalid-branch')
        None
    """
    ...

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

    Example:
        >>> await get_vendor_status_from_commits('abc')
        {
            'name': 'vendor_abc',
            'status': 'operational',
            'extractor_version': '2.3.1',
            'test_results': {'passing': 45, 'total': 50, 'skipped': 5},
            'last_updated': '2025-10-10T14:30:00Z'
        }
    """
    ...
