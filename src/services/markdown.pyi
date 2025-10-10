"""Type stubs for markdown service.

Markdown status file generation and legacy format parsing.
Provides Jinja2-based template rendering with <100ms performance target.

Constitutional Compliance:
- Principle IV: Performance (<100ms full status generation, FR-023)
- Principle V: Production quality (backward compatibility, error handling)
- Principle VIII: Type safety (full mypy --strict compliance)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.models.task import WorkItem
from src.models.tracking import DeploymentEvent, VendorExtractor

# ==============================================================================
# Public API
# ==============================================================================

async def generate_project_status_md(
    vendors: list[VendorExtractor],
    work_items: list[WorkItem],
    deployments: list[DeploymentEvent],
) -> str:
    """Generate project status markdown from database entities.

    Uses Jinja2 templates for consistent formatting matching legacy .project_status.md
    structure. Renders operational vendor counts, active work items, and recent
    deployment history.

    Args:
        vendors: List of VendorExtractor entities
        work_items: List of WorkItem entities (active only, deleted_at IS NULL)
        deployments: List of DeploymentEvent entities (sorted by deployed_at DESC)

    Returns:
        str: Rendered markdown content ready to write to file

    Performance:
        <100ms for 45 vendors + 1,200 work items + 50 deployments (FR-023)

    Template Structure:
        - Header with timestamp
        - Operational Vendors section (count/total with test results)
        - Active Work Items section (hierarchical display)
        - Recent Deployments section (last 10 with PR links)

    Example:
        >>> markdown = await generate_project_status_md(
        ...     vendors=await get_all_vendors(),
        ...     work_items=await get_active_work_items(),
        ...     deployments=await get_recent_deployments(limit=10)
        ... )
        >>> print(markdown[:100])
        '# Project Status - 2025-10-10T14:30:00Z\\n\\n## Operational Vendors (42/45)\\n\\n- **vendor_abc**: o...'
    """
    ...

async def parse_legacy_markdown(file_path: Path) -> dict[str, Any]:
    """Parse legacy .project_status.md format to extract structured data.

    Parses markdown sections (vendors, work items, deployments, enhancements)
    and extracts structured data for migration to database.

    Args:
        file_path: Path to .project_status.md file

    Returns:
        dict: Structured data with keys:
            - vendors: list[dict] (VendorExtractor data)
            - work_items: list[dict] (WorkItem data)
            - deployments: list[dict] (DeploymentEvent data)
            - enhancements: list[dict] (FutureEnhancement data)
            - metadata: dict (file version, last updated timestamp)

    Raises:
        FileNotFoundError: If file_path does not exist
        ValueError: If markdown structure is invalid or cannot be parsed

    Performance:
        <200ms for typical .project_status.md (45 vendors, 100 items, 50 deployments)

    Example:
        >>> data = await parse_legacy_markdown(Path('.project_status.md'))
        >>> data['vendors'][0]
        {
            'name': 'vendor_abc',
            'status': 'operational',
            'test_results': {'passing': 45, 'total': 50, 'skipped': 5}
        }
    """
    ...

async def append_fallback_write(file_path: Path, data: dict[str, Any]) -> None:
    """Append fallback write markers to markdown file.

    Used when database is unavailable to record state changes in markdown format.
    Appends timestamped entries with fallback markers for later reconciliation.

    Args:
        file_path: Path to markdown file (will be created if missing)
        data: Structured data to append (vendor updates, work item changes, etc.)

    Raises:
        OSError: If file cannot be opened for writing
        ValueError: If data structure is invalid

    Side Effects:
        - Appends to existing file or creates new file
        - Adds "<!-- FALLBACK WRITE: timestamp -->" markers
        - Preserves existing content

    Example:
        >>> await append_fallback_write(
        ...     Path('.project_status.md'),
        ...     {'vendor': 'abc', 'status': 'operational', 'updated_at': '2025-10-10T14:30:00Z'}
        ... )
        # File now contains:
        # <!-- FALLBACK WRITE: 2025-10-10T14:30:00Z -->
        # - **vendor_abc**: operational
    """
    ...
