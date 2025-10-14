"""Workflow-mcp test data fixtures for performance validation.

This module provides fixture generation functions for workflow-mcp performance testing,
specifically designed to validate FR-004 requirements: 1000 entities distributed across
5 projects with 10-20 work items per project.

Constitutional Compliance:
- Principle VIII: Type safety (mypy --strict compliance, complete type annotations)
- Principle V: Production quality (realistic test data, proper validation)
- Principle IV: Performance (bulk insert patterns for large datasets)

Requirements:
- FR-004: 1000 entities distributed across 5 projects
- 10-20 work items per project (minimum 10, maximum 20)
- Realistic test data (not placeholder strings)
- Type-safe implementation (mypy --strict compliance)

Usage:
    from tests.fixtures.workflow_fixtures import (
        generate_test_projects,
        generate_test_entities,
        generate_test_work_items
    )

    # Generate 5 projects
    projects = generate_test_projects(count=5)

    # Generate 1000 entities across 5 projects
    entities = generate_test_entities(project_count=5, entities_per_project=200)

    # Generate 10-20 work items per project with entity references
    entity_ids = [entity["id"] for entity in entities]
    work_items = generate_test_work_items(entity_refs=entity_ids, items_per_project=15)
"""

from __future__ import annotations

import random
from datetime import UTC, datetime
from typing import Any, List, Dict
from uuid import UUID, uuid4


# ==============================================================================
# Test Data Templates
# ==============================================================================

# Realistic project names for workflow-mcp testing
PROJECT_NAMES: List[str] = [
    "commission-processing",
    "vendor-integration",
    "financial-reporting",
    "audit-compliance",
    "data-migration"
]

PROJECT_DESCRIPTIONS: List[str] = [
    "Commission statement processing and reconciliation system",
    "Multi-vendor file format integration and extraction pipeline",
    "Automated financial report generation and distribution",
    "SOX compliance validation and audit trail management",
    "Legacy data migration to new database schema"
]

# Entity type definitions (realistic for workflow-mcp)
ENTITY_TYPE_NAME: str = "vendor"

# Realistic vendor names for entity test data
VENDOR_NAMES: List[str] = [
    "EPSON", "CANON", "HP", "XEROX", "RICOH", "BROTHER", "KYOCERA", "SHARP",
    "KONICA_MINOLTA", "DELL", "LENOVO", "TOSHIBA", "SAMSUNG", "PANASONIC", "FUJITSU",
    "OKI", "ZEBRA", "LEXMARK", "PITNEY_BOWES", "KODAK", "NEOPOST", "HASLER", "QUADIENT",
    "FP_MAILING", "SECAP", "FRANCOTYP_POSTALIA", "MAILMARK", "STREAMLINE", "DATA_PAC",
    "COMPULINK", "PITNEYBOWES_SOFTWARE", "BELL_HOWELL", "OPEX", "BOWE_BELL_HOWELL",
    "FORMAX", "MBM", "MARTIN_YALE", "INTIMUS", "IDEAL", "FELLOWES", "GBC", "SWINGLINE",
    "STAPLES", "REXEL", "DAHLE", "KOBRA", "HSM", "DESTROYIT"
]

# Vendor status values (realistic for commission processing)
VENDOR_STATUSES: List[str] = ["operational", "broken", "deprecated", "testing"]

# Work item types (from workflow-mcp hierarchy)
WORK_ITEM_TYPES: List[str] = ["project", "session", "task", "research", "subtask"]

# Work item statuses (from workflow-mcp spec)
WORK_ITEM_STATUSES: List[str] = ["planned", "active", "completed", "blocked"]

# Realistic work item titles for commission processing domain
WORK_ITEM_TITLES: List[str] = [
    "Fix EPSON PDF extractor pattern recognition",
    "Add support for Canon new statement format",
    "Reconcile HP commission discrepancies Q3",
    "Update Xerox line item parsing logic",
    "Implement Ricoh dealer name fallback",
    "Validate Brother commission rate calculations",
    "Debug Kyocera split commission handling",
    "Optimize Sharp multi-page statement processing",
    "Add Konica Minolta unknown entry detection",
    "Refactor Dell extractor for v2.0 schema",
    "Test Lenovo vendor integration pipeline",
    "Document Toshiba statement format variations",
    "Investigate Samsung reconciliation failures",
    "Enhance Panasonic unit price calculation accuracy",
    "Research Fujitsu alternative parsing strategies",
    "Deploy OKI extractor to production environment",
    "Monitor Zebra commission processing performance",
    "Review Lexmark audit trail compliance",
    "Analyze Pitney Bowes data quality issues",
    "Validate Kodak financial precision requirements"
]


# ==============================================================================
# Project Fixture Generation
# ==============================================================================


def generate_test_projects(count: int = 5) -> List[Dict[str, Any]]:
    """Generate test projects for workflow-mcp.

    Creates realistic project records with unique names and descriptions.
    Designed for performance testing of workflow-mcp project operations.

    Args:
        count: Number of projects to generate (default: 5)

    Returns:
        List of project dictionaries with fields:
            - id: UUID primary key
            - name: Unique project name (kebab-case)
            - description: Detailed project description
            - database_name: Generated database name for project isolation
            - created_at: Creation timestamp (ISO 8601 string)
            - updated_at: Update timestamp (ISO 8601 string)
            - metadata: Empty dict (reserved for future use)

    Raises:
        ValueError: If count < 1 or count > len(PROJECT_NAMES)

    Example:
        >>> projects = generate_test_projects(count=5)
        >>> len(projects)
        5
        >>> projects[0]["name"]
        'commission-processing'
        >>> "id" in projects[0]
        True
    """
    if count < 1:
        raise ValueError(f"count must be >= 1, got: {count}")

    if count > len(PROJECT_NAMES):
        raise ValueError(
            f"count exceeds available project templates: {count} > {len(PROJECT_NAMES)}"
        )

    projects: List[Dict[str, Any]] = []
    now = datetime.now(UTC).isoformat()

    for i in range(count):
        project_id = uuid4()
        project_name = PROJECT_NAMES[i]
        project_description = PROJECT_DESCRIPTIONS[i]

        # Generate database name (workflow_project_{uuid_prefix})
        database_name = f"workflow_project_{str(project_id).replace('-', '')[:16]}"

        project: Dict[str, Any] = {
            "id": project_id,
            "name": project_name,
            "description": project_description,
            "database_name": database_name,
            "created_at": now,
            "updated_at": now,
            "metadata": {}
        }
        projects.append(project)

    return projects


# ==============================================================================
# Entity Fixture Generation
# ==============================================================================


def generate_test_entities(
    project_count: int = 5,
    entities_per_project: int = 200
) -> List[Dict[str, Any]]:
    """Generate 1000 entities distributed across projects.

    Creates realistic entity records representing vendors in a commission processing
    system. Entities are evenly distributed across projects with realistic vendor
    names, statuses, and version strings.

    Args:
        project_count: Number of projects to distribute entities across (default: 5)
        entities_per_project: Number of entities per project (default: 200)

    Returns:
        List of entity dictionaries with fields:
            - id: UUID primary key
            - entity_type: Always "vendor" (matches commission processing domain)
            - name: Unique vendor name (uppercase with underscores)
            - data: JSONB data with vendor-specific fields:
                - status: Vendor status (operational/broken/deprecated/testing)
                - version: Vendor version string (semver format)
                - priority: Vendor priority (high/medium/low)
            - tags: List of tags for categorization (e.g., ["pdf-extractor", "high-priority"])
            - version: Entity version (starts at 1)
            - created_at: Creation timestamp (ISO 8601 string)
            - updated_at: Update timestamp (ISO 8601 string)
            - deleted_at: Always None (no soft deletes in test data)
            - metadata: Empty dict (reserved for future use)
            - project_id: UUID of owning project

    Raises:
        ValueError: If project_count < 1 or entities_per_project < 1

    Example:
        >>> entities = generate_test_entities(project_count=5, entities_per_project=200)
        >>> len(entities)
        1000
        >>> entities[0]["entity_type"]
        'vendor'
        >>> entities[0]["data"]["status"] in ["operational", "broken", "deprecated", "testing"]
        True
    """
    if project_count < 1:
        raise ValueError(f"project_count must be >= 1, got: {project_count}")

    if entities_per_project < 1:
        raise ValueError(f"entities_per_project must be >= 1, got: {entities_per_project}")

    entities: List[Dict[str, Any]] = []
    now = datetime.now(UTC).isoformat()

    # Generate projects to get project IDs for distribution
    projects = generate_test_projects(count=project_count)
    project_ids = [project["id"] for project in projects]

    # Generate entities distributed across projects
    for project_idx in range(project_count):
        project_id = project_ids[project_idx]

        for entity_idx in range(entities_per_project):
            entity_id = uuid4()

            # Select vendor name (cycle through if more entities than names)
            vendor_name = VENDOR_NAMES[entity_idx % len(VENDOR_NAMES)]

            # Make entity name unique by appending project suffix
            entity_name = f"{vendor_name}_P{project_idx:02d}_{entity_idx:03d}"

            # Generate realistic vendor data
            status = random.choice(VENDOR_STATUSES)
            version = f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}"
            priority = random.choice(["high", "medium", "low"])

            # Generate tags based on status and priority
            tags: List[str] = []
            if status == "broken":
                tags.append("needs-repair")
            if priority == "high":
                tags.append("high-priority")
            tags.append("pdf-extractor")

            entity: Dict[str, Any] = {
                "id": entity_id,
                "entity_type": ENTITY_TYPE_NAME,
                "name": entity_name,
                "data": {
                    "status": status,
                    "version": version,
                    "priority": priority
                },
                "tags": tags,
                "version": 1,
                "created_at": now,
                "updated_at": now,
                "deleted_at": None,
                "metadata": {},
                "project_id": project_id
            }
            entities.append(entity)

    return entities


# ==============================================================================
# Work Item Fixture Generation
# ==============================================================================


def generate_test_work_items(
    entity_refs: List[UUID],
    items_per_project: int = 15
) -> List[Dict[str, Any]]:
    """Generate work items with entity references.

    Creates realistic work item records representing tasks in a commission processing
    workflow. Each work item references entities (vendors) and follows the workflow-mcp
    hierarchy (project, session, task, research, subtask).

    Args:
        entity_refs: List of entity UUIDs to reference from work items
        items_per_project: Number of work items per project (default: 15)
                          Must be between 10 and 20 per FR-004

    Returns:
        List of work item dictionaries with fields:
            - id: UUID primary key
            - item_type: Work item type (project/session/task/research/subtask)
            - title: Descriptive work item title (realistic for commission processing)
            - description: Detailed work item description
            - status: Work item status (planned/active/completed/blocked)
            - parent_id: Parent work item UUID (None for root projects)
            - materialized_path: Hierarchical path for ancestor queries
            - hierarchy_level: Depth in hierarchy (1-5)
            - created_at: Creation timestamp (ISO 8601 string)
            - updated_at: Update timestamp (ISO 8601 string)
            - completed_at: Completion timestamp (None if not completed)
            - deleted_at: Soft delete timestamp (always None in test data)
            - metadata: Dict containing entity_refs for cross-server integration
            - git_branch: Git branch name (None in test data)
            - git_commits: List of commit SHAs (empty in test data)

    Raises:
        ValueError: If items_per_project < 10 or items_per_project > 20
        ValueError: If entity_refs is empty

    Example:
        >>> entities = generate_test_entities(project_count=5, entities_per_project=200)
        >>> entity_ids = [entity["id"] for entity in entities]
        >>> work_items = generate_test_work_items(entity_refs=entity_ids, items_per_project=15)
        >>> len(work_items)
        75
        >>> work_items[0]["item_type"]
        'project'
        >>> len(work_items[0]["metadata"]["entity_refs"]) >= 1
        True
    """
    if items_per_project < 10:
        raise ValueError(
            f"items_per_project must be >= 10 per FR-004, got: {items_per_project}"
        )

    if items_per_project > 20:
        raise ValueError(
            f"items_per_project must be <= 20 per FR-004, got: {items_per_project}"
        )

    if not entity_refs:
        raise ValueError("entity_refs cannot be empty")

    work_items: List[Dict[str, Any]] = []
    now = datetime.now(UTC).isoformat()

    # Calculate project count from entity distribution
    # FR-004: 1000 entities across 5 projects = 200 entities per project
    project_count = 5

    # Generate work items for each project
    for project_idx in range(project_count):
        # Create root project work item
        project_id = uuid4()
        project_path = f"/proj-{str(project_id)[:8]}"

        # Select random title for project
        project_title = f"Project: {PROJECT_NAMES[project_idx % len(PROJECT_NAMES)]}"

        # Select entity references for this project (random sample)
        num_entity_refs = random.randint(2, 5)
        project_entity_refs = random.sample(entity_refs, num_entity_refs)

        project_work_item: Dict[str, Any] = {
            "id": project_id,
            "item_type": "project",
            "title": project_title,
            "description": f"Root project work item for {project_title}",
            "status": random.choice(WORK_ITEM_STATUSES),
            "parent_id": None,
            "materialized_path": project_path,
            "hierarchy_level": 1,
            "created_at": now,
            "updated_at": now,
            "completed_at": None,
            "deleted_at": None,
            "metadata": {
                "entity_refs": [str(ref) for ref in project_entity_refs]
            },
            "git_branch": None,
            "git_commits": []
        }
        work_items.append(project_work_item)

        # Generate child work items (items_per_project - 1, since project is already created)
        remaining_items = items_per_project - 1

        for item_idx in range(remaining_items):
            item_id = uuid4()

            # Determine item type (favor tasks over other types)
            if item_idx % 3 == 0:
                item_type = "session"
                hierarchy_level = 2
                parent_id = project_id
                item_path = f"{project_path}/sess-{str(item_id)[:8]}"
            elif item_idx % 3 == 1:
                item_type = "task"
                hierarchy_level = 2
                parent_id = project_id
                item_path = f"{project_path}/task-{str(item_id)[:8]}"
            else:
                item_type = "research"
                hierarchy_level = 2
                parent_id = project_id
                item_path = f"{project_path}/research-{str(item_id)[:8]}"

            # Select realistic work item title
            item_title = WORK_ITEM_TITLES[item_idx % len(WORK_ITEM_TITLES)]

            # Select entity references for this work item (1-3 entities)
            num_entity_refs = random.randint(1, 3)
            item_entity_refs = random.sample(entity_refs, num_entity_refs)

            # Determine status (favor active/completed for realistic distribution)
            if item_idx < remaining_items // 2:
                status = "completed"
                completed_at = now
            elif item_idx < (remaining_items * 3) // 4:
                status = "active"
                completed_at = None
            else:
                status = random.choice(["planned", "blocked"])
                completed_at = None

            work_item: Dict[str, Any] = {
                "id": item_id,
                "item_type": item_type,
                "title": item_title,
                "description": f"Work item for {item_title}",
                "status": status,
                "parent_id": parent_id,
                "materialized_path": item_path,
                "hierarchy_level": hierarchy_level,
                "created_at": now,
                "updated_at": now,
                "completed_at": completed_at,
                "deleted_at": None,
                "metadata": {
                    "entity_refs": [str(ref) for ref in item_entity_refs]
                },
                "git_branch": None,
                "git_commits": []
            }
            work_items.append(work_item)

    return work_items
