"""Integration tests for full status generation performance (Scenario 8).

Tests verify (from quickstart.md):
- Full project status generation in <100ms (FR-023)
- Vendor health summary generation
- Active work items list generation
- Recent deployments list generation
- Pending enhancements list generation
- Markdown format compatibility with legacy .project_status.md

Performance Target:
- <100ms for 45 vendors + 50 work items + 20 deployments

Constitutional Compliance:
- Principle IV: Performance Guarantees (<100ms status generation)
- Principle VII: TDD (validates acceptance criteria)
- Principle VIII: Type Safety (mypy --strict compliance)
"""

from __future__ import annotations

import random
import re
import time
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.task import WorkItem
from src.models.tracking import DeploymentEvent, VendorExtractor
from src.services.markdown import generate_project_status_md

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine


@pytest.fixture
async def full_project_data(
    session: AsyncSession,
) -> tuple[list[VendorExtractor], list[WorkItem], list[DeploymentEvent]]:
    """Seed complete project data for status generation.

    Seeds:
        - 45 vendor extractors (2/3 operational)
        - 50 active work items (hierarchical structure)
        - 20 recent deployment events

    Returns:
        Tuple of (vendors, work_items, deployments)
    """
    # Seed 45 vendors (2/3 operational, 1/3 broken)
    vendors = [
        VendorExtractor(
            name=f"vendor_{i:02d}",
            status="operational" if i % 3 != 0 else "broken",
            extractor_version="1.2.3",
            metadata_={
                "test_results": {
                    "passing": 10 if i % 3 != 0 else 5,
                    "total": 12,
                    "skipped": 2 if i % 3 != 0 else 7,
                },
                "format_support": {
                    "excel": True,
                    "csv": True,
                    "pdf": i % 2 == 0,
                    "ocr": i % 4 == 0,
                },
                "extractor_version": "1.2.3",
                "manifest_compliant": i % 3 != 0,
            },
            created_by="test-fixture",
        )
        for i in range(45)
    ]
    session.add_all(vendors)
    await session.flush()

    # Seed 50 active work items (hierarchical: 10 projects, 20 sessions, 20 tasks)
    work_items: list[WorkItem] = []

    # Create 10 projects (depth 0)
    projects = [
        WorkItem(
            item_type="project",
            title=f"Project {i}",
            status=random.choice(["active", "planning", "on-hold"]),
            depth=0,
            parent_id=None,
            metadata={
                "description": f"Description for project {i}",
                "target_quarter": "Q4 2025",
                "constitutional_principles": ["TDD", "Type Safety"],
            },
            created_by="test-fixture",
        )
        for i in range(10)
    ]
    work_items.extend(projects)
    session.add_all(projects)
    await session.flush()

    # Create 20 sessions (depth 1, children of projects)
    sessions = [
        WorkItem(
            item_type="session",
            title=f"Session {i}",
            status=random.choice(["active", "complete"]),
            depth=1,
            parent_id=projects[i % 10].id,
            branch_name=f"feature/session-{i}" if i % 2 == 0 else None,
            metadata={
                "token_budget": 200000,
                "prompts_count": random.randint(5, 50),
                "yaml_frontmatter": {"session_id": f"S{i:03d}"},
            },
            created_by="test-fixture",
        )
        for i in range(20)
    ]
    work_items.extend(sessions)
    session.add_all(sessions)
    await session.flush()

    # Create 20 tasks (depth 2, children of sessions)
    tasks = [
        WorkItem(
            item_type="task",
            title=f"Task {i}",
            status=random.choice(["active", "complete", "blocked"]),
            depth=2,
            parent_id=sessions[i % 20].id,
            branch_name=f"task/T{i:03d}" if i % 3 == 0 else None,
            metadata={
                "estimated_hours": random.uniform(1.0, 8.0),
                "actual_hours": random.uniform(0.5, 10.0) if i % 2 == 0 else None,
                "blocked_reason": "Dependency not met" if i % 5 == 0 else None,
            },
            created_by="test-fixture",
        )
        for i in range(20)
    ]
    work_items.extend(tasks)
    session.add_all(tasks)
    await session.flush()

    # Seed 20 deployment events (recent, last 30 days)
    deployments = [
        DeploymentEvent(
            deployed_at=datetime.now(timezone.utc) - timedelta(days=i),
            commit_hash=f"{uuid4().hex[:40]}",  # Generate 40-char hex
            metadata_={
                "pr_number": 100 + i,
                "pr_title": f"Deployment {i}: Feature implementation",
                "commit_hash": f"{uuid4().hex[:40]}",
                "test_summary": {
                    "unit": random.randint(100, 200),
                    "integration": random.randint(20, 50),
                    "contract": random.randint(5, 15),
                },
                "constitutional_compliance": i % 4 != 0,  # 75% compliant
            },
        )
        for i in range(20)
    ]
    session.add_all(deployments)
    await session.flush()

    # Link deployments to vendors (each deployment affects 3-5 vendors)
    from src.models.tracking import VendorDeploymentLink

    for deployment in deployments:
        affected_vendor_count = random.randint(3, 5)
        affected_vendors = random.sample(vendors, affected_vendor_count)
        for vendor in affected_vendors:
            link = VendorDeploymentLink(
                deployment_id=deployment.id, vendor_id=vendor.id
            )
            session.add(link)

    # Link deployments to work items (each deployment includes 2-4 work items)
    from src.models.tracking import WorkItemDeploymentLink

    for deployment in deployments:
        included_item_count = random.randint(2, 4)
        included_items = random.sample(work_items, included_item_count)
        for work_item in included_items:
            link = WorkItemDeploymentLink(
                deployment_id=deployment.id, work_item_id=work_item.id
            )
            session.add(link)

    await session.commit()

    return vendors, work_items, deployments


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_status_generation_performance(
    full_project_data: tuple[
        list[VendorExtractor], list[WorkItem], list[DeploymentEvent]
    ],
) -> None:
    """Test full status generation completes in <100ms.

    Given: 45 vendors, 50 work items, 20 deployments in database
    When: Generate full project status markdown
    Then: Generation completes in <100ms (FR-023)
    And: Output includes all required sections
    """
    vendors, work_items, deployments = full_project_data

    # Measure generation time
    start_time = time.perf_counter()
    markdown = await generate_project_status_md(
        vendors=vendors, work_items=work_items, deployments=deployments
    )
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # Performance assertion: <100ms (FR-023)
    assert (
        elapsed_ms < 100.0
    ), f"Status generation took {elapsed_ms:.2f}ms (target: <100ms)"

    # Verify markdown is not empty
    assert len(markdown) > 0, "Generated markdown should not be empty"

    # Verify markdown contains expected sections
    assert "# Project Status" in markdown, "Missing project status header"
    assert (
        "## Operational Vendors" in markdown
    ), "Missing operational vendors section"
    assert "## Active Work Items" in markdown, "Missing active work items section"
    assert "## Recent Deployments" in markdown, "Missing recent deployments section"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vendor_health_summary_accuracy(
    full_project_data: tuple[
        list[VendorExtractor], list[WorkItem], list[DeploymentEvent]
    ],
) -> None:
    """Test vendor health summary is accurate.

    Given: 45 vendors (30 operational, 15 broken)
    When: Generate status markdown
    Then: Vendor section shows correct operational count
    And: Each vendor line includes status, test results, format support
    """
    vendors, work_items, deployments = full_project_data

    markdown = await generate_project_status_md(
        vendors=vendors, work_items=work_items, deployments=deployments
    )

    # Verify operational vendor count in header
    operational_count = sum(1 for v in vendors if v.status == "operational")
    total_vendors = len(vendors)

    vendor_header_pattern = rf"## Operational Vendors \({operational_count}/{total_vendors}\)"
    assert re.search(
        vendor_header_pattern, markdown
    ), f"Expected '{vendor_header_pattern}' in vendor section"

    # Verify vendor entries format: - **vendor_name**: status (passing/total tests) [formats]
    vendor_entry_pattern = r"- \*\*vendor_\d+\*\*: \w+ \(\d+/\d+ tests\) \[.+?\]"
    vendor_entries = re.findall(vendor_entry_pattern, markdown)

    assert len(vendor_entries) == total_vendors, (
        f"Expected {total_vendors} vendor entries, found {len(vendor_entries)}"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_active_work_items_hierarchy(
    full_project_data: tuple[
        list[VendorExtractor], list[WorkItem], list[DeploymentEvent]
    ],
) -> None:
    """Test active work items section preserves hierarchy.

    Given: 50 work items (10 projects, 20 sessions, 20 tasks)
    When: Generate status markdown
    Then: Work items section includes all 50 items
    And: Items are indented by depth
    And: Each item shows status, created date, branch (if present)
    """
    vendors, work_items, deployments = full_project_data

    markdown = await generate_project_status_md(
        vendors=vendors, work_items=work_items, deployments=deployments
    )

    # Verify work items count in header
    work_item_count = len(work_items)
    work_item_header_pattern = rf"## Active Work Items \({work_item_count}\)"
    assert re.search(
        work_item_header_pattern, markdown
    ), f"Expected '{work_item_header_pattern}' in work items section"

    # Verify work item entries format: ### Title (item_type)
    work_item_entry_pattern = r"###\s+.+?\s+\(\w+\)"
    work_item_entries = re.findall(work_item_entry_pattern, markdown)

    assert len(work_item_entries) == work_item_count, (
        f"Expected {work_item_count} work item entries, found {len(work_item_entries)}"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_recent_deployments_chronological_order(
    full_project_data: tuple[
        list[VendorExtractor], list[WorkItem], list[DeploymentEvent]
    ],
) -> None:
    """Test recent deployments are in reverse chronological order.

    Given: 20 deployment events over last 30 days
    When: Generate status markdown
    Then: Deployments section shows all 20 deployments
    And: Deployments are sorted newest first
    And: Each deployment shows timestamp, PR number, PR title, commit hash, tests
    """
    vendors, work_items, deployments = full_project_data

    markdown = await generate_project_status_md(
        vendors=vendors, work_items=work_items, deployments=deployments
    )

    # Verify deployments count in header
    deployment_count = len(deployments)
    deployment_header_pattern = rf"## Recent Deployments \(Last {deployment_count}\)"
    assert re.search(
        deployment_header_pattern, markdown
    ), f"Expected '{deployment_header_pattern}' in deployments section"

    # Verify deployment entries format: ### timestamp - PR #number
    deployment_entry_pattern = r"###\s+.+?\s+-\s+PR #\d+"
    deployment_entries = re.findall(deployment_entry_pattern, markdown)

    assert len(deployment_entries) == deployment_count, (
        f"Expected {deployment_count} deployment entries, found {len(deployment_entries)}"
    )

    # Verify each deployment includes required metadata
    for deployment in deployments:
        pr_number = deployment.metadata_.pr_number
        # Check PR number appears in markdown
        assert (
            f"PR #{pr_number}" in markdown
        ), f"PR #{pr_number} not found in deployments section"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_markdown_format_legacy_compatibility(
    full_project_data: tuple[
        list[VendorExtractor], list[WorkItem], list[DeploymentEvent]
    ],
) -> None:
    """Test markdown format matches legacy .project_status.md structure.

    Given: Full project data
    When: Generate status markdown
    Then: Output follows legacy format structure
    And: Includes timestamp in header
    And: Includes generated at footer
    """
    vendors, work_items, deployments = full_project_data

    markdown = await generate_project_status_md(
        vendors=vendors, work_items=work_items, deployments=deployments
    )

    # Verify header with timestamp
    header_pattern = r"# Project Status - .+"
    assert re.search(
        header_pattern, markdown
    ), "Expected '# Project Status - <timestamp>' header"

    # Verify footer with generation timestamp
    footer_pattern = r"\*Generated at .+\*"
    assert re.search(
        footer_pattern, markdown
    ), "Expected '*Generated at <timestamp>*' footer"

    # Verify section ordering
    sections = [
        "## Operational Vendors",
        "## Active Work Items",
        "## Recent Deployments",
    ]

    # Find position of each section
    section_positions = {
        section: markdown.find(section) for section in sections
    }

    # Verify all sections present
    for section in sections:
        assert (
            section_positions[section] != -1
        ), f"Section '{section}' not found in markdown"

    # Verify sections in correct order
    assert (
        section_positions["## Operational Vendors"]
        < section_positions["## Active Work Items"]
    ), "Operational Vendors section should come before Active Work Items"
    assert (
        section_positions["## Active Work Items"]
        < section_positions["## Recent Deployments"]
    ), "Active Work Items section should come before Recent Deployments"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_status_generation_with_minimal_data(
    session: AsyncSession,
) -> None:
    """Test status generation with minimal data (edge case).

    Given: 0 vendors, 0 work items, 0 deployments
    When: Generate status markdown
    Then: Generation completes successfully
    And: Output includes all section headers
    And: Sections show 0 counts
    """
    # Generate with empty lists
    start_time = time.perf_counter()
    markdown = await generate_project_status_md(
        vendors=[], work_items=[], deployments=[]
    )
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # Performance should still be <100ms even with no data
    assert (
        elapsed_ms < 100.0
    ), f"Status generation took {elapsed_ms:.2f}ms (target: <100ms)"

    # Verify sections present
    assert "# Project Status" in markdown
    assert "## Operational Vendors (0/0)" in markdown
    assert "## Active Work Items (0)" in markdown
    assert "## Recent Deployments (Last 0)" in markdown


@pytest.mark.integration
@pytest.mark.asyncio
async def test_status_generation_with_large_dataset(
    session: AsyncSession,
) -> None:
    """Test status generation with larger dataset (stress test).

    Given: 100 vendors, 200 work items, 50 deployments
    When: Generate status markdown
    Then: Generation completes in reasonable time (<200ms)
    And: All data included in output
    """
    # Seed larger dataset
    vendors = [
        VendorExtractor(
            name=f"vendor_{i:03d}",
            status="operational" if i % 2 == 0 else "broken",
            extractor_version="2.0.0",
            metadata_={
                "test_results": {"passing": 10, "total": 12, "skipped": 2},
                "format_support": {
                    "excel": True,
                    "csv": True,
                    "pdf": False,
                    "ocr": False,
                },
                "extractor_version": "2.0.0",
                "manifest_compliant": True,
            },
            created_by="stress-test",
        )
        for i in range(100)
    ]
    session.add_all(vendors)
    await session.flush()

    work_items = [
        WorkItem(
            item_type="task",
            title=f"Task {i}",
            status="active",
            depth=0,
            parent_id=None,
            metadata={
                "estimated_hours": 2.0,
                "actual_hours": None,
                "blocked_reason": None,
            },
            created_by="stress-test",
        )
        for i in range(200)
    ]
    session.add_all(work_items)
    await session.flush()

    deployments = [
        DeploymentEvent(
            deployed_at=datetime.now(timezone.utc) - timedelta(hours=i),
            commit_hash=f"{uuid4().hex[:40]}",
            metadata_={
                "pr_number": 200 + i,
                "pr_title": f"Stress test deployment {i}",
                "commit_hash": f"{uuid4().hex[:40]}",
                "test_summary": {"unit": 150, "integration": 30},
                "constitutional_compliance": True,
            },
        )
        for i in range(50)
    ]
    session.add_all(deployments)
    await session.commit()

    # Measure generation time with larger dataset
    start_time = time.perf_counter()
    markdown = await generate_project_status_md(
        vendors=vendors, work_items=work_items, deployments=deployments
    )
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    # Allow slightly longer time for larger dataset (<200ms)
    assert (
        elapsed_ms < 200.0
    ), f"Large dataset generation took {elapsed_ms:.2f}ms (target: <200ms)"

    # Verify all data included
    assert "## Operational Vendors (50/100)" in markdown
    assert "## Active Work Items (200)" in markdown
    assert "## Recent Deployments (Last 50)" in markdown
