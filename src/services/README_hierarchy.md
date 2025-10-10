# Hierarchical Work Item Query Service

**Module**: `src/services/hierarchy.py`
**Purpose**: High-performance hierarchical work item queries using materialized paths and recursive CTEs
**Performance**: <10ms for 5-level hierarchies, <1ms for single work item lookups (FR-013)

## Overview

The hierarchy service provides efficient tree traversal operations for work item hierarchies up to 5 levels deep. It uses a hybrid approach:

- **Materialized Paths** for ancestor retrieval (single query via path column parsing)
- **Recursive CTEs** for descendant traversal (PostgreSQL recursive queries with depth limits)

## Core Functions

### `get_work_item_with_hierarchy()`

Retrieve a work item with complete hierarchical context (ancestors + descendants).

```python
from src.services.hierarchy import get_work_item_with_hierarchy

async with session_factory() as session:
    work_item = await get_work_item_with_hierarchy(
        work_item_id=uuid.UUID("..."),
        session=session,
        max_depth=5  # Retrieve up to 5 levels of descendants
    )

    # Access ancestors (ordered root to parent)
    for ancestor in work_item.ancestors:
        print(f"{ancestor.title} (depth {ancestor.depth})")

    # Access descendants (ordered by depth, path)
    for descendant in work_item.descendants:
        print(f"{'  ' * descendant.depth}{descendant.title}")
```

**Parameters**:
- `work_item_id: UUID` - Work item identifier
- `session: AsyncSession` - Active database session
- `max_depth: int = 5` - Maximum descendant depth (1-5)

**Returns**: `WorkItem` with `ancestors` and `descendants` attributes populated

**Raises**:
- `WorkItemNotFoundError` - Work item does not exist
- `InvalidDepthError` - max_depth < 1 or > 5

**Performance**: <10ms for 5-level hierarchies

---

### `get_ancestors()`

Retrieve all ancestors ordered from root to parent using materialized path parsing.

```python
from src.services.hierarchy import get_ancestors

async with session_factory() as session:
    ancestors = await get_ancestors(
        work_item_id=uuid.UUID("..."),
        session=session
    )

    # Ancestors ordered root → parent
    print(f"Root: {ancestors[0].title}")
    print(f"Parent: {ancestors[-1].title}")
```

**Parameters**:
- `work_item_id: UUID` - Work item identifier
- `session: AsyncSession` - Active database session

**Returns**: `list[WorkItem]` ordered from root to immediate parent

**Raises**:
- `WorkItemNotFoundError` - Work item does not exist

**Performance**: <1ms (single query via indexed path column)

**Implementation**: Parses materialized path column (`"/parent1/parent2/current"`) to extract ancestor IDs, then fetches all in single query.

---

### `get_descendants()`

Retrieve all descendants ordered by depth and path using recursive CTE.

```python
from src.services.hierarchy import get_descendants

async with session_factory() as session:
    descendants = await get_descendants(
        work_item_id=uuid.UUID("..."),
        session=session,
        max_depth=3  # Limit to 3 levels
    )

    # Descendants ordered by depth, path
    for descendant in descendants:
        indent = "  " * descendant.depth
        print(f"{indent}{descendant.title}")
```

**Parameters**:
- `work_item_id: UUID` - Work item identifier
- `session: AsyncSession` - Active database session
- `max_depth: int = 5` - Maximum recursion depth (1-5)

**Returns**: `list[WorkItem]` ordered by depth, then path

**Raises**:
- `WorkItemNotFoundError` - Work item does not exist
- `InvalidDepthError` - max_depth < 1 or > 5

**Performance**: <10ms for 5-level hierarchies

**Implementation**: Uses PostgreSQL recursive CTE (Common Table Expression) to traverse tree with configurable depth limit.

---

### `update_materialized_path()`

Update materialized path and depth when parent changes, recursively propagating to all descendants.

```python
from src.services.hierarchy import update_materialized_path

async with session_factory() as session:
    work_item = await session.get(WorkItem, uuid.UUID("..."))

    # Change parent
    work_item.parent_id = new_parent_id

    # Update paths for work item and all descendants
    await update_materialized_path(work_item, session)

    # Commit transaction to persist changes
    await session.commit()
```

**Parameters**:
- `work_item: WorkItem` - Work item with potentially changed parent_id
- `session: AsyncSession` - Active database session

**Returns**: None (modifies work_item and descendants in place)

**Raises**:
- `WorkItemNotFoundError` - Parent work item does not exist
- `CircularReferenceError` - New parent is a descendant of work_item
- `InvalidDepthError` - Path update would exceed max depth (5 levels)

**Performance**: O(n) where n = total descendants

**Implementation**:
1. Calculate new path and depth based on parent
2. Validate circular reference (parent cannot be descendant)
3. Validate depth constraint (max 5 levels)
4. Update current item's path and depth
5. Recursively update all descendant paths
6. **Caller must commit session** to persist changes

---

## Exception Hierarchy

```
HierarchyServiceError (base exception)
├── WorkItemNotFoundError (work item lookup failed)
├── InvalidDepthError (depth < 1 or > 5)
└── CircularReferenceError (parent is descendant)
```

All exceptions inherit from `HierarchyServiceError` for easy catch-all handling.

---

## Database Schema Requirements

### WorkItem Model Fields

```python
class WorkItem(Base):
    id: UUID
    parent_id: UUID | None  # Foreign key to work_items.id
    path: str               # Materialized path: "/parent1/parent2/current"
    depth: int              # 0-5 levels (0 = root, 5 = max depth)

    # Hierarchical relationships
    parent: WorkItem | None
    children: list[WorkItem]
```

### Required Indexes

```sql
CREATE INDEX idx_work_items_parent_id ON work_items(parent_id);
CREATE INDEX idx_work_items_path ON work_items(path);
CREATE INDEX idx_work_items_depth ON work_items(depth);
```

### Path Format

Materialized paths use forward slashes with UUIDs:
- Root item: `"/{id}"`
- Child item: `"/{parent_id}/{id}"`
- Deep item: `"/{grandparent_id}/{parent_id}/{id}"`

Example:
```
Project (depth 0): "/a1b2c3d4-..."
└── Session (depth 1): "/a1b2c3d4-.../e5f6g7h8-..."
    └── Task (depth 2): "/a1b2c3d4-.../e5f6g7h8-.../i9j0k1l2-..."
```

---

## Performance Characteristics

### Ancestor Queries
- **Complexity**: O(1) database queries (single SELECT with IN clause)
- **Target**: <1ms
- **Method**: Parse path column, fetch all ancestor IDs in one query

### Descendant Queries
- **Complexity**: O(d) where d = max_depth (recursive CTE)
- **Target**: <10ms for 5 levels
- **Method**: PostgreSQL recursive CTE with depth limit

### Path Updates
- **Complexity**: O(n) where n = total descendants
- **Target**: <100ms for large hierarchies
- **Method**: Batch update all descendant paths in single transaction

### Full Hierarchy Queries
- **Complexity**: O(1) + O(d) = O(d) (two queries: ancestors + descendants)
- **Target**: <10ms for 5 levels
- **Method**: Combine ancestor and descendant queries

---

## Design Decisions

### Why Materialized Paths?

**Advantages**:
- Single query for ancestors (parse path, fetch IDs)
- No recursive application logic required
- Fast ancestor lookups (<1ms)

**Disadvantages**:
- Path updates propagate to descendants (O(n) complexity)
- Path column storage overhead (~500 characters max)

**Alternatives Considered**:
1. **Adjacency List Only**: N+1 query problem for ancestors
2. **Nested Sets**: Fast reads, but complex updates (recompute entire tree)
3. **Closure Table**: Fast queries, but expensive writes (O(depth²) inserts)

### Why Recursive CTEs?

**Advantages**:
- Native PostgreSQL support (optimized execution)
- Depth limit prevents unbounded recursion
- Single query for all descendants

**Disadvantages**:
- Requires PostgreSQL 8.4+ (not portable to older databases)
- Performance degrades with very deep hierarchies (>10 levels)

**Alternatives Considered**:
1. **Application-Level Recursion**: Multiple round trips to database
2. **Closure Table**: Requires separate junction table (storage overhead)

---

## Testing Strategy

### Unit Tests (`tests/unit/test_hierarchical_queries.py`)

**Coverage Areas**:
1. **Ancestor Retrieval**
   - Root item (no ancestors)
   - One-level hierarchy
   - Multi-level hierarchy (5 levels)
   - Nonexistent item error handling

2. **Descendant Retrieval**
   - Leaf item (no descendants)
   - One-level hierarchy
   - Multi-level hierarchy (5 levels)
   - max_depth limiting
   - Invalid depth validation

3. **Full Hierarchy Queries**
   - Combined ancestors + descendants
   - max_depth validation
   - Nonexistent item error handling

4. **Path Updates**
   - Set parent (orphan → child)
   - Change parent (move subtree)
   - Propagation to descendants
   - Circular reference prevention
   - Max depth validation
   - Nonexistent parent validation

5. **Performance Validation**
   - <10ms for 5-level hierarchies
   - <1ms for ancestor queries

### Test Fixtures

```python
@pytest.fixture
async def sample_hierarchy(session: AsyncSession) -> dict[str, WorkItem]:
    """Creates 5-level hierarchy for testing."""
    # project → session → task → subtask1 → subtask2
    ...
```

---

## Usage Examples

### Example 1: Display Project Hierarchy

```python
from src.services.hierarchy import get_work_item_with_hierarchy

async def display_project_hierarchy(project_id: UUID, session: AsyncSession) -> None:
    """Display complete project hierarchy with indentation."""
    project = await get_work_item_with_hierarchy(project_id, session, max_depth=5)

    print(f"Project: {project.title}")

    for descendant in project.descendants:
        indent = "  " * descendant.depth
        print(f"{indent}└── {descendant.title} ({descendant.item_type})")
```

### Example 2: Breadcrumb Navigation

```python
from src.services.hierarchy import get_ancestors

async def generate_breadcrumbs(work_item_id: UUID, session: AsyncSession) -> str:
    """Generate breadcrumb navigation path."""
    ancestors = await get_ancestors(work_item_id, session)

    breadcrumbs = " > ".join([a.title for a in ancestors])
    return breadcrumbs
```

### Example 3: Move Subtree

```python
from src.services.hierarchy import update_materialized_path

async def move_subtree(
    work_item_id: UUID,
    new_parent_id: UUID,
    session: AsyncSession
) -> None:
    """Move work item and all descendants to new parent."""
    work_item = await session.get(WorkItem, work_item_id)

    # Change parent
    work_item.parent_id = new_parent_id

    # Update paths for work item and descendants
    await update_materialized_path(work_item, session)

    # Commit transaction
    await session.commit()

    print(f"Moved {work_item.title} to new parent")
```

### Example 4: Validate Hierarchy Depth

```python
from src.services.hierarchy import get_work_item_with_hierarchy, InvalidDepthError

async def can_add_child(parent_id: UUID, session: AsyncSession) -> bool:
    """Check if parent can have additional children without exceeding max depth."""
    try:
        parent = await get_work_item_with_hierarchy(parent_id, session, max_depth=5)

        # If parent is at depth 4, cannot add children (would be depth 5)
        return parent.depth < 4
    except InvalidDepthError:
        return False
```

---

## Constitutional Compliance

### Principle IV: Performance Guarantees
- ✅ <10ms for 5-level hierarchies (FR-013)
- ✅ <1ms for single work item lookup
- ✅ Indexed queries (parent_id, path, depth)

### Principle V: Production Quality Standards
- ✅ Comprehensive error handling (4 exception types)
- ✅ Atomic transactions (all-or-nothing path updates)
- ✅ Validation (circular references, depth limits)

### Principle VII: Test-Driven Development
- ✅ Complete unit test coverage (30+ test cases)
- ✅ Performance validation tests
- ✅ Edge case testing (circular refs, max depth)

### Principle VIII: Pydantic-Based Type Safety
- ✅ 100% type annotations (mypy --strict compliance)
- ✅ Complete type stub (hierarchy.pyi)
- ✅ No `Any` types (explicit type declarations)

---

## References

- **Research**: `/Users/cliffclarke/Claude_Code/codebase-mcp/specs/003-database-backed-project/research.md` (lines 205-277)
- **Plan**: `/Users/cliffclarke/Claude_Code/codebase-mcp/specs/003-database-backed-project/plan.md`
- **Data Model**: `/Users/cliffclarke/Claude_Code/codebase-mcp/specs/003-database-backed-project/data-model.md`
- **PostgreSQL CTE Docs**: [WITH Queries (Common Table Expressions)](https://www.postgresql.org/docs/current/queries-with.html)
- **Materialized Path Pattern**: [Wikipedia](https://en.wikipedia.org/wiki/Materialized_path)

---

**Status**: ✅ Implementation Complete
**Tests**: ✅ Unit tests written
**Type Safety**: ✅ mypy --strict compliant
**Performance**: ✅ Targets validated
