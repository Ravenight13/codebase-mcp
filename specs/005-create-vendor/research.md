# Research: Create Vendor MCP Function

**Feature**: 005-create-vendor
**Date**: 2025-10-11
**Status**: Complete

## Database Schema Research

### Existing Vendor Table Structure
**Table**: `vendor_extractors`

**Columns**:
- `id` (UUID, primary key): Unique vendor identifier
- `version` (INTEGER, NOT NULL, default=1): Optimistic locking version
- `name` (VARCHAR(100), UNIQUE, NOT NULL, indexed): Vendor name (unique lookup key)
- `status` (VARCHAR(20), NOT NULL): Operational status ("operational" | "broken")
- `extractor_version` (VARCHAR(50), NOT NULL): Extractor semantic version
- `metadata_` (JSONB, NOT NULL): Pydantic-validated metadata
- `created_at` (TIMESTAMP WITH TIMEZONE, NOT NULL): Creation timestamp
- `updated_at` (TIMESTAMP WITH TIMEZONE, NOT NULL): Last update timestamp
- `created_by` (VARCHAR(100), NOT NULL): AI client identifier

**Indexes**:
- `idx_vendor_name`: UNIQUE B-tree index on `name` column (<1ms queries)
- `idx_vendor_status`: B-tree index on `status` column (filter operational/broken)

**Constraints**:
- `ck_vendor_status`: CHECK (status IN ('operational', 'broken'))
- `unique_name`: UNIQUE constraint on `name` column

**Optimistic Locking**:
- SQLAlchemy configured with `__mapper_args__ = {"version_id_col": version}`
- Version auto-incremented on UPDATE
- Used by `update_vendor_status()` service

**Decision**: The existing schema fully supports create_vendor() operation. UNIQUE constraint on `name` provides case-sensitive uniqueness. For case-insensitive uniqueness (per FR-012), we need application-level validation before INSERT.

**Rationale**: Database UNIQUE constraint is case-sensitive. PostgreSQL supports case-insensitive uniqueness via functional indexes (LOWER(name)), but adding this requires migration. For Feature 005, we'll implement application-level case-insensitive validation to avoid schema changes.

**Alternatives Considered**:
- Database migration to add functional unique index on LOWER(name): Rejected - unnecessary complexity for Feature 005, can be deferred to future optimization
- Case-sensitive uniqueness only: Rejected - violates FR-012 clarification

## Existing Tool Implementation Patterns

### FastMCP Decorator Pattern
From `src/mcp/tools/tracking.py`:
```python
@mcp.tool()
async def query_vendor_status(
    name: str,
    ctx: Context | None = None,
) -> dict[str, Any]:
```

**Key Patterns**:
- Use `@mcp.tool()` decorator from FastMCP
- Async function signature with `async def`
- Context injection via `ctx: Context | None = None` parameter
- Return type: `dict[str, Any]` (MCP contract format)
- Dual logging pattern: `ctx.info()` for MCP client + `logger.info()` for file logs

**Decision**: Follow identical pattern for `create_vendor()` tool function.

**Rationale**: Consistency with existing vendor tools enables code reuse and maintainability.

### Error Handling Pattern
From `src/mcp/tools/tracking.py`:
```python
try:
    async with get_session_factory()() as db:
        vendor = await get_vendor_by_name(name, db)
        await db.commit()
except VendorNotFoundError as e:
    error_msg = f"Vendor not found: {name}"
    if ctx:
        await ctx.error(error_msg)
    logger.warning("Vendor not found", extra={"vendor_name": name})
    raise ValueError(error_msg) from e
```

**Key Patterns**:
- Try-except blocks wrapping service calls
- Convert service exceptions (VendorNotFoundError) to ValueError for MCP client
- Dual error logging: `ctx.error()` + `logger.error()/warning()`
- Structured logging with `extra={}` parameter
- Re-raise as ValueError (MCP-compatible exception)

**Decision**: Use identical error handling pattern for `create_vendor()`.

**Rationale**: MCP clients expect ValueError exceptions. Service-layer exceptions need translation.

### Input Validation Pattern
From `src/mcp/tools/tracking.py` (`update_vendor_status`):
```python
# Validate vendor name
if not name or not name.strip():
    error_msg = "Vendor name cannot be empty"
    if ctx:
        await ctx.error(error_msg)
    raise ValueError(error_msg)

# Validate status if provided
valid_statuses = {"operational", "broken"}
if status is not None and status not in valid_statuses:
    error_msg = f"Invalid status: {status}. Valid values: {valid_statuses}"
    if ctx:
        await ctx.error(error_msg)
    raise ValueError(error_msg)
```

**Key Patterns**:
- Validate inputs before database operations
- Raise ValueError with descriptive error messages
- Log validation failures via ctx and file logger

**Decision**: Implement vendor name validation before INSERT operation:
- Check empty/whitespace
- Regex validation: `^[a-zA-Z0-9 \-_]+$`
- Length validation: 1-100 characters
- Case-insensitive duplicate check (application-level query)

**Rationale**: Fail-fast validation prevents invalid database operations and improves error messages.

## Vendor Service Layer Patterns

### Service Function Signature
From `src/services/vendor.py`:
```python
async def update_vendor_status(
    name: str,
    version: int,
    updates: dict[str, Any],
    session: AsyncSession,
) -> VendorExtractor:
```

**Key Patterns**:
- Async function with `AsyncSession` parameter
- Return type: SQLAlchemy model (VendorExtractor)
- Parameters: entity identifiers + updates dict + session

**Decision**: New service function signature:
```python
async def create_vendor(
    name: str,
    initial_metadata: dict[str, Any] | None,
    created_by: str,
    session: AsyncSession,
) -> VendorExtractor:
```

**Rationale**: Follows existing service pattern. Returns model instance for tool layer conversion.

### Exception Classes
From `src/services/vendor.py`:
```python
class VendorNotFoundError(Exception):
    def __init__(self, *, vendor_name: str | None = None, vendor_id: UUID | None = None) -> None:
        # ...
    def to_dict(self) -> dict[str, Any]:
        # ...
```

**Decision**: Create new exception class for duplicate vendor errors:
```python
class VendorAlreadyExistsError(Exception):
    def __init__(self, vendor_name: str) -> None:
        self.vendor_name = vendor_name
        super().__init__(f"Vendor already exists: {vendor_name}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": "VendorAlreadyExistsError",
            "vendor_name": self.vendor_name,
            "http_status": 409,
        }
```

**Rationale**: Consistent with existing exception patterns. HTTP 409 Conflict is standard for duplicate resource creation.

## Pydantic Metadata Validation

### Existing Metadata Schema
From `specs/003-database-backed-project/contracts/pydantic_schemas.py`:
```python
from pydantic_schemas import VendorMetadata, VendorStatus
```

**Investigation**: The contracts use Pydantic models for metadata validation. Need to review schema structure for flexible validation.

**Decision**: Use flexible validation approach:
- Known fields: `scaffolder_version` (Optional[str]), `created_at` (Optional[str] with ISO 8601 validation)
- Unknown fields: Pass through without validation
- Service layer validates known fields, stores full dict in metadata_ column

**Rationale**: Per clarification session, metadata schema should be flexible (validate known fields, allow additional custom fields).

### Metadata Validation Implementation
From `src/services/vendor.py`:
```python
from src.services.validation import ValidationError, validate_vendor_metadata
```

**Decision**: Create new validation function for flexible metadata:
```python
def validate_create_vendor_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Validate vendor creation metadata with flexible schema.

    Known fields (validated if present):
    - scaffolder_version: str
    - created_at: str (ISO 8601 format)

    Unknown fields: allowed without validation
    """
    if metadata is None:
        return {}

    validated = {}

    # Validate scaffolder_version if present
    if "scaffolder_version" in metadata:
        if not isinstance(metadata["scaffolder_version"], str):
            raise ValidationError({"scaffolder_version": "Must be string"})
        validated["scaffolder_version"] = metadata["scaffolder_version"]

    # Validate created_at if present (ISO 8601 format)
    if "created_at" in metadata:
        if not isinstance(metadata["created_at"], str):
            raise ValidationError({"created_at": "Must be ISO 8601 string"})
        try:
            datetime.fromisoformat(metadata["created_at"])
        except ValueError:
            raise ValidationError({"created_at": "Invalid ISO 8601 format"})
        validated["created_at"] = metadata["created_at"]

    # Copy unknown fields without validation
    for key, value in metadata.items():
        if key not in validated:
            validated[key] = value

    return validated
```

**Rationale**: Flexible validation per clarification session. Fails fast on known field errors, allows extensibility.

## Database Constraint Strategy

### Case-Insensitive Uniqueness
**Requirement**: FR-012 specifies case-insensitive uniqueness

**Current State**: PostgreSQL UNIQUE constraint is case-sensitive

**Options**:
1. **Application-level check**: Query `SELECT * FROM vendor_extractors WHERE LOWER(name) = LOWER(:name)` before INSERT
2. **Functional unique index**: `CREATE UNIQUE INDEX idx_vendor_name_lower ON vendor_extractors (LOWER(name))`
3. **CITEXT column type**: Change name column to CITEXT type

**Decision**: Functional unique index (Option 2) - **Database-level enforcement**

**Rationale**:
- Robust concurrent handling - database enforces uniqueness atomically
- Eliminates race condition window between check and INSERT
- Better performance for duplicate checking (indexed LOWER() function)
- Aligns with production quality standards (Principle V)
- Requires database migration but provides bulletproof guarantees

**Migration Required**:
```sql
-- Drop existing case-sensitive unique constraint
ALTER TABLE vendor_extractors DROP CONSTRAINT IF EXISTS vendor_extractors_name_key;

-- Create case-insensitive functional unique index
CREATE UNIQUE INDEX idx_vendor_name_lower ON vendor_extractors (LOWER(name));
```

**Implementation**:
```python
# No application-level duplicate check needed
# Database enforces uniqueness via functional index
try:
    session.add(vendor)
    await session.flush()  # Trigger UNIQUE index check
except IntegrityError as e:
    if "idx_vendor_name_lower" in str(e).lower():
        # Extract existing vendor name from database for error message
        existing = await session.execute(
            select(VendorExtractor).where(
                func.lower(VendorExtractor.name) == func.lower(name)
            )
        )
        existing_vendor = existing.scalar_one_or_none()
        existing_name = existing_vendor.name if existing_vendor else name
        raise VendorAlreadyExistsError(
            vendor_name=name,
            existing_name=existing_name  # Show actual casing
        )
    raise
```

### Duplicate Handling
**Requirement**: FR-007 and FR-013 - prevent duplicates, handle concurrent attempts

**Strategy**: Functional unique index + IntegrityError catch with enhanced error message

**Error Message Format**:
- Show both the attempted name and the conflicting existing name with actual casing
- Example: "Vendor already exists: newcorp (conflicts with existing 'NewCorp')"

**Enhanced Exception Class**:
```python
class VendorAlreadyExistsError(Exception):
    def __init__(self, vendor_name: str, existing_name: str | None = None) -> None:
        self.vendor_name = vendor_name
        self.existing_name = existing_name or vendor_name

        if existing_name and existing_name != vendor_name:
            message = f"Vendor already exists: {vendor_name} (conflicts with existing '{existing_name}')"
        else:
            message = f"Vendor already exists: {vendor_name}"

        super().__init__(message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_type": "VendorAlreadyExistsError",
            "vendor_name": self.vendor_name,
            "existing_name": self.existing_name,
            "http_status": 409,
        }
```

**Rationale**: Database-level enforcement provides atomic uniqueness checking, eliminating race conditions. Enhanced error messages help users understand case-insensitive conflicts.

**Alternatives Considered**:
- Application-level check: Rejected - race condition window between check and INSERT
- CITEXT column type: Rejected - more invasive schema change, functional index is sufficient
- SELECT FOR UPDATE lock: Rejected - unnecessary complexity with functional unique index

## Vendor Name Validation

### Validation Rules (FR-012)
- Length: 1-100 characters
- Allowed characters: alphanumeric + spaces + hyphens + underscores
- Case-insensitive uniqueness

**Regex Pattern**: `^[a-zA-Z0-9 \-_]+$`

**Implementation**:
```python
import re

VENDOR_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9 \-_]+$')

def validate_vendor_name(name: str) -> None:
    """Validate vendor name per FR-012 requirements."""
    if not name or not name.strip():
        raise ValueError("Vendor name cannot be empty")

    if len(name) < 1 or len(name) > 100:
        raise ValueError(f"Vendor name must be 1-100 characters, got {len(name)}")

    if not VENDOR_NAME_PATTERN.match(name):
        raise ValueError(
            "Vendor name must contain only alphanumeric characters, "
            "spaces, hyphens, and underscores"
        )
```

**Rationale**: Validates per clarification session requirements. Regex is efficient for <100ms target.

## Performance Considerations

### Performance Target
**Requirement**: FR-015 - <100ms p95 latency

**Operations**:
1. Name validation: ~0.1ms (regex match)
2. Case-insensitive duplicate check: <1ms (indexed SELECT with LOWER())
3. Metadata validation: ~0.5ms (Python validation)
4. INSERT operation: <5ms (single row with indexes)
5. Response serialization: ~1ms (model to dict conversion)

**Total Estimated**: ~7ms (well under 100ms target)

**Optimization Notes**:
- UNIQUE constraint provides O(log n) duplicate detection
- No need for batching (single INSERT)
- Async operations prevent blocking

**Decision**: Current design meets performance requirements. No special optimizations needed.

**Alternatives Considered**:
- Batch insert: Rejected - single vendor creation use case
- Caching: Rejected - not needed for <100ms target

## Contract Test Strategy

### Existing Contract Test Pattern
From `tests/contract/test_vendor_tracking_contract.py`:
```python
import pytest
from pydantic import ValidationError
from pydantic_schemas import VendorStatus, VendorMetadata

def test_vendor_status_creation():
    """Test VendorStatus Pydantic model validation."""
    status = VendorStatus.OPERATIONAL
    assert status == "operational"

def test_vendor_metadata_validation():
    """Test VendorMetadata Pydantic validation."""
    metadata = VendorMetadata(
        format_support={"excel": True, "csv": False},
        test_results={"passing": 40, "total": 50, "skipped": 10},
        extractor_version="1.0.0",
        manifest_compliant=True
    )
    assert metadata.format_support["excel"] is True
```

**Decision**: Create contract tests for CreateVendorRequest and CreateVendorResponse Pydantic models

**Test Structure**:
```python
def test_create_vendor_request_validation():
    """Test CreateVendorRequest Pydantic validation."""
    # Valid request
    # Invalid name (too long, invalid chars)
    # Invalid metadata (wrong types for known fields)

def test_create_vendor_response_schema():
    """Test CreateVendorResponse Pydantic schema."""
    # Validate required fields
    # Validate types
    # Validate status always "broken"
    # Validate version always 1
```

**Rationale**: Follows existing contract test patterns. Tests Pydantic models before implementation.

## Integration Test Scenarios

### Test Data Setup
Based on acceptance scenarios from spec.md:

**Test Vendors**:
- "NewCorp": Full metadata test
- "AcmeInc": Partial metadata test
- "ExistingVendor": Duplicate detection test
- "TechCo": Immediate query test
- "newcorp": Case-insensitive duplicate test (vs "NewCorp")

**Test Metadata**:
```python
FULL_METADATA = {
    "scaffolder_version": "1.0",
    "created_at": "2025-10-11T10:00:00Z",
    "custom_field": "custom_value"
}

PARTIAL_METADATA = {
    "scaffolder_version": "1.0"
}

EMPTY_METADATA = {}

INVALID_METADATA = {
    "scaffolder_version": 123,  # Should be string
    "created_at": "invalid-date"  # Should be ISO 8601
}
```

**Decision**: Use pytest fixtures for test database setup and teardown

**Rationale**: Isolated test environment per existing integration test patterns.

## Summary of Technical Decisions

| Decision Area | Chosen Approach | Rationale |
|---------------|-----------------|-----------|
| **Database Schema** | Add functional unique index (migration required) | Database-level enforcement, no race conditions |
| **Uniqueness Strategy** | Functional unique index on LOWER(name) | Atomic enforcement, eliminates race conditions |
| **Duplicate Handling** | Functional index + IntegrityError with enhanced error message | Shows conflicting existing vendor with actual casing |
| **Metadata Validation** | Flexible schema (validate known fields) | Per clarification requirements |
| **Name Validation** | Regex + length check | Meets FR-012 requirements |
| **Service Exception** | VendorAlreadyExistsError with existing_name field | HTTP 409 Conflict with helpful error details |
| **Tool Pattern** | FastMCP @mcp.tool() decorator | Consistency with existing tools |
| **Error Handling** | Dual logging + ValueError translation | MCP protocol compliance |
| **Performance** | Single INSERT with indexed uniqueness check | Meets <100ms p95 target |
| **Testing** | Contract + integration + unit tests + migration test | TDD approach per constitution |
| **Initial extractor_version** | "0.0.0" semantic version | Indicates "not yet implemented" state |
| **scripts/new_vendor.sh** | Create as part of Feature 005 | Does not exist, needed for atomic onboarding |

## Implementation Readiness

All technical decisions documented. No remaining unknowns. Ready to proceed to Phase 1 (Design & Contracts).
