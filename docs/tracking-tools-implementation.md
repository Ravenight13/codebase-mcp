# Tracking Tools Implementation (T033-T035)

## Overview

This document describes the implementation of three MCP tools for vendor tracking and deployment recording in the Codebase MCP Server.

**Tasks Completed:**
- T033: `record_deployment` - Record deployment events with vendor/work item relationships
- T034: `query_vendor_status` - Query vendor operational status (<1ms target)
- T035: `update_vendor_status` - Update vendor status with optimistic locking

**Location:** `/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/tools/tracking.py`

## Architecture

### MCP Tool Pattern

All three tools follow the standard FastMCP pattern:

```python
@mcp.tool()
async def tool_name(
    param1: Type1,
    param2: Type2 | None = None,
    ctx: Context | None = None,
) -> dict[str, Any]:
    """Tool description.

    Args:
        param1: Description
        param2: Optional description
        ctx: FastMCP context for logging (injected)

    Returns:
        Dictionary matching MCP contract

    Raises:
        ValueError: Description
        RuntimeError: Description

    Performance:
        Target: <Xms p95 latency

    Requirements:
        FR-XXX (requirement description)
    """
```

### Type Safety Features

1. **Complete Type Annotations**: All parameters and return types explicitly typed
2. **Pydantic Validation**: Input metadata validated via Pydantic models from contracts
3. **UUID Conversion**: String UUIDs converted to UUID objects with error handling
4. **Commit Hash Validation**: Regex pattern validation for 40-char lowercase hex
5. **Status Validation**: Enum-based validation for vendor status values

### Error Handling Strategy

```python
# Service Layer Exceptions -> MCP Tool Exceptions
VendorNotFoundError -> ValueError (404)
OptimisticLockError -> RuntimeError (409)
ValidationError -> ValueError (400)
InvalidDeploymentDataError -> ValueError (400)
```

### Dual Logging Pattern

Each tool uses two logging mechanisms:

1. **FastMCP Context Logging** (`ctx.info()`, `ctx.error()`):
   - Sent to MCP client (Claude Desktop)
   - Real-time feedback during tool execution
   - User-friendly messages

2. **Python File Logging** (`logger.info()`, `logger.error()`):
   - Written to `/tmp/codebase-mcp.log`
   - Detailed diagnostic information
   - Structured extra fields for debugging

Example:
```python
if ctx:
    await ctx.info(f"Querying vendor status: {name}")

logger.info(
    "query_vendor_status called",
    extra={"vendor_name": name},
)
```

## Tool Implementations

### T033: record_deployment

**Purpose:** Record deployment events with PR details, test results, and relationships

**Performance Target:** <200ms p95 latency

**Key Features:**
- Validates deployment metadata using `DeploymentMetadata` Pydantic model
- Validates commit hash format (40 lowercase hex characters)
- Creates many-to-many links to vendors and work items
- Returns complete deployment event with relationship IDs

**Parameters:**
```python
deployed_at: datetime        # Deployment timestamp (UTC)
metadata: dict[str, Any]     # DeploymentMetadata structure
vendor_ids: list[str] | None # Vendor UUIDs (optional)
work_item_ids: list[str] | None  # Work item UUIDs (optional)
created_by: str = "claude-code"  # AI client identifier
ctx: Context | None = None   # FastMCP context
```

**Response Structure:**
```python
{
    "id": "uuid-string",
    "deployed_at": "2025-10-10T18:00:00Z",
    "commit_hash": "84b04732a1f5e9c8d3b2a0e6f7c8d9e0a1b2c3d4",
    "metadata": {
        "pr_number": 42,
        "pr_title": "feat: add feature",
        "commit_hash": "...",
        "test_summary": {"unit": 150, "integration": 30},
        "constitutional_compliance": true
    },
    "vendor_ids": ["uuid1", "uuid2"],
    "work_item_ids": ["uuid3", "uuid4"],
    "created_at": "2025-10-10T18:00:00Z",
    "created_by": "claude-code"
}
```

**Error Cases:**
- Invalid metadata structure → `ValueError`
- Invalid commit hash format → `ValueError`
- Invalid UUID format → `ValueError`
- Duplicate vendor/work item IDs → `ValueError`
- Referenced entity not found → `ValueError`

### T034: query_vendor_status

**Purpose:** Query vendor operational status with <1ms response time

**Performance Target:** <1ms p95 latency (single vendor query)

**Key Features:**
- Optimized query using unique index on `vendor_extractors.name`
- Returns complete vendor metadata including test results
- Minimal latency for real-time status checks

**Parameters:**
```python
name: str                    # Unique vendor name
ctx: Context | None = None   # FastMCP context
```

**Response Structure:**
```python
{
    "id": "uuid-string",
    "version": 5,
    "name": "ADP Vendor",
    "status": "operational",
    "extractor_version": "2.3.1",
    "metadata": {
        "format_support": {
            "excel": true,
            "csv": true,
            "pdf": false,
            "ocr": false
        },
        "test_results": {
            "passing": 42,
            "total": 45,
            "skipped": 2
        },
        "extractor_version": "2.3.1",
        "manifest_compliant": true
    },
    "created_at": "2025-01-15T10:00:00Z",
    "updated_at": "2025-10-10T12:30:00Z",
    "created_by": "claude-code"
}
```

**Error Cases:**
- Empty vendor name → `ValueError`
- Vendor not found → `ValueError`

### T035: update_vendor_status

**Purpose:** Update vendor status with optimistic locking to prevent conflicts

**Performance Target:** <100ms p95 latency

**Key Features:**
- Optimistic locking via version checking
- Partial updates (only provided fields modified)
- Metadata validation via Pydantic
- Merge updates with existing metadata

**Parameters:**
```python
name: str                    # Unique vendor name
version: int                 # Expected version for locking
status: str | None = None    # New status (optional)
metadata: dict[str, Any] | None = None  # Updated metadata (optional)
updated_by: str = "claude-code"  # AI client identifier
ctx: Context | None = None   # FastMCP context
```

**Response Structure:**
Same as `query_vendor_status` with incremented `version` field

**Error Cases:**
- Invalid version (<1) → `ValueError`
- Invalid status → `ValueError`
- No updates provided → `ValueError`
- Vendor not found → `ValueError`
- Version mismatch → `RuntimeError` (optimistic lock conflict)
- Invalid metadata → `ValueError`

## Helper Functions

### _vendor_to_dict

Converts SQLAlchemy `VendorExtractor` model to MCP contract dictionary.

**Implementation:**
```python
def _vendor_to_dict(vendor: Any) -> dict[str, Any]:
    return {
        "id": str(vendor.id),
        "version": vendor.version,
        "name": vendor.name,
        "status": vendor.status,
        "extractor_version": vendor.extractor_version,
        "metadata": vendor.metadata_,
        "created_at": vendor.created_at.isoformat(),
        "updated_at": vendor.updated_at.isoformat(),
        "created_by": vendor.created_by,
    }
```

### _deployment_to_dict

Converts SQLAlchemy `DeploymentEvent` model to MCP contract dictionary.

**Implementation:**
```python
def _deployment_to_dict(
    deployment: Any,
    vendor_ids: list[UUID],
    work_item_ids: list[UUID]
) -> dict[str, Any]:
    return {
        "id": str(deployment.id),
        "deployed_at": deployment.deployed_at.isoformat(),
        "commit_hash": deployment.commit_hash,
        "metadata": deployment.metadata_,
        "vendor_ids": [str(vid) for vid in vendor_ids],
        "work_item_ids": [str(wid) for wid in work_item_ids],
        "created_at": deployment.created_at.isoformat(),
        "created_by": deployment.created_by,
    }
```

### _validate_commit_hash

Validates git commit hash format (40 lowercase hex characters).

**Implementation:**
```python
COMMIT_HASH_PATTERN = re.compile(r"^[a-f0-9]{40}$")

def _validate_commit_hash(commit_hash: str) -> None:
    if not COMMIT_HASH_PATTERN.match(commit_hash):
        raise ValueError(
            f"Invalid commit hash format: {commit_hash}. "
            "Must be 40 lowercase hexadecimal characters."
        )
```

## Integration Points

### Database Session Management

All tools use `get_session_factory()()` context manager:

```python
async with get_session_factory()() as db:
    result = await service_function(param, db)
    await db.commit()
```

**Key Points:**
- Automatic transaction management (commit on success, rollback on error)
- Connection pooling for performance
- Proper cleanup via context manager

### Service Layer Integration

Tools delegate business logic to service functions:

| Tool | Service Function | Module |
|------|-----------------|---------|
| `record_deployment` | `create_deployment()` | `src.services.deployment` |
| `query_vendor_status` | `get_vendor_by_name()` | `src.services.vendor` |
| `update_vendor_status` | `update_vendor_status()` | `src.services.vendor` |

**Note:** The MCP tool `update_vendor_status` imports the service function with an alias to avoid naming conflict:

```python
from src.services.vendor import (
    update_vendor_status as update_vendor_service,
)
```

### Pydantic Schema Integration

Tools import Pydantic models from contracts:

```python
from pydantic_schemas import (
    DeploymentMetadata,
    VendorMetadata,
    VendorStatus,
)
```

**Path Configuration:**
```python
specs_contracts_path = (
    Path(__file__).parent.parent.parent.parent
    / "specs"
    / "003-database-backed-project"
    / "contracts"
)
sys.path.insert(0, str(specs_contracts_path))
```

**Note:** A symlink was created to resolve the hyphen-in-filename issue:
```bash
specs/003-database-backed-project/contracts/pydantic_schemas.py -> pydantic-schemas.py
```

## Server Registration

The tools are registered with FastMCP server in `src/mcp/server_fastmcp.py`:

```python
def main() -> None:
    try:
        logger.info("Importing tool modules...")
        import src.mcp.tools.configuration  # noqa: F401
        import src.mcp.tools.indexing  # noqa: F401
        import src.mcp.tools.search  # noqa: F401
        import src.mcp.tools.tasks  # noqa: F401
        import src.mcp.tools.tracking  # noqa: F401  # NEW
        logger.info("✓ Tool modules imported successfully")
```

Expected tools list updated to include:
- `query_vendor_status`
- `record_deployment`
- `update_vendor_status`

## Testing

### Import Validation

```bash
python3 -c "from src.mcp.tools.tracking import record_deployment, query_vendor_status, update_vendor_status"
```

### Type Safety Validation

```bash
python -m mypy src/mcp/tools/tracking.py --strict
```

**Status:** ✓ All type checks pass

### Commit Hash Validation Tests

```python
# Valid: 40 lowercase hex
_validate_commit_hash('84b04732a1f5e9c8d3b2a0e6f7c8d9e0a1b2c3d4')  # ✓

# Invalid: too short
_validate_commit_hash('invalid')  # → ValueError

# Invalid: uppercase
_validate_commit_hash('84B04732A1F5E9C8D3B2A0E6F7C8D9E0A1B2C3D4')  # → ValueError
```

## Performance Characteristics

### query_vendor_status

**Target:** <1ms p95 latency

**Optimization Strategies:**
- Unique index on `vendor_extractors.name`
- Single-row query (no joins)
- Minimal data marshalling

**Measured Latency:** Tracked via `time.perf_counter()` and logged

### update_vendor_status

**Target:** <100ms p95 latency

**Optimization Strategies:**
- Optimistic locking (no row-level locks)
- Partial updates (only modified fields)
- Single database transaction

### record_deployment

**Target:** <200ms p95 latency

**Optimization Strategies:**
- Batch junction table inserts
- Single transaction for deployment + links
- Efficient UUID validation

## Constitutional Compliance

### Principle III: Protocol Compliance
- MCP-compliant responses (JSON dictionaries)
- FastMCP decorators for tool registration
- No stdout/stderr pollution (dual logging pattern)

### Principle IV: Performance
- <1ms vendor queries (unique index optimization)
- <200ms deployment recording (batch inserts)
- <100ms vendor updates (optimistic locking)

### Principle V: Production Quality
- Comprehensive error handling
- Detailed error messages
- Graceful degradation
- Structured logging with context

### Principle VIII: Type Safety
- 100% type annotations
- mypy --strict compliance
- Pydantic validation for all inputs
- UUID type conversion with error handling

### Principle X: Git Micro-Commits
- Deployment audit trail with commit hashes
- Commit hash validation
- Traceability through relationships

### Principle XI: FastMCP Foundation
- FastMCP decorators (`@mcp.tool()`)
- Context injection for logging
- Automatic schema generation

## Known Issues and Limitations

### 1. Pydantic Schema Import

**Issue:** The contracts file is named `pydantic-schemas.py` with a hyphen, which Python cannot import directly.

**Solution:** Created a symlink `pydantic_schemas.py -> pydantic-schemas.py` in the contracts directory.

**Impact:** All service modules and MCP tools can now import using `from pydantic_schemas import ...`

### 2. Function Naming Conflict

**Issue:** The MCP tool `update_vendor_status` has the same name as the service function `update_vendor_status`.

**Solution:** Import service function with alias:
```python
from src.services.vendor import update_vendor_status as update_vendor_service
```

**Impact:** No conflicts, clear distinction between tool and service layers.

### 3. mypy Errors in server_fastmcp.py

**Issue:** mypy reports errors for `init_db_connection` and `close_db_connection` imports in `server_fastmcp.py`.

**Status:** Pre-existing issue, unrelated to tracking tools implementation.

**Impact:** None on tracking tools functionality.

## File Locations

- **Implementation:** `/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/tools/tracking.py`
- **Server Integration:** `/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/server_fastmcp.py`
- **Contracts:** `/Users/cliffclarke/Claude_Code/codebase-mcp/specs/003-database-backed-project/contracts/mcp-tools.yaml`
- **Pydantic Schemas:** `/Users/cliffclarke/Claude_Code/codebase-mcp/specs/003-database-backed-project/contracts/pydantic-schemas.py`
- **Services Used:**
  - `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/vendor.py`
  - `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/deployment.py`
  - `/Users/cliffclarke/Claude_Code/codebase-mcp/src/services/validation.py`

## Summary

Successfully implemented three production-ready MCP tools for vendor tracking and deployment recording:

1. **record_deployment** - Complete deployment event recording with relationships
2. **query_vendor_status** - High-performance vendor status queries (<1ms)
3. **update_vendor_status** - Safe concurrent updates with optimistic locking

All tools follow FastMCP conventions, include comprehensive error handling, maintain type safety with mypy --strict compliance, and adhere to constitutional principles.

**Status:** ✓ Implementation Complete
**Type Safety:** ✓ mypy --strict passes
**Integration:** ✓ Server registration complete
**Testing:** ✓ Import and validation tests pass
