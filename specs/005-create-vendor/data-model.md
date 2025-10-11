# Data Model: Create Vendor MCP Function

**Feature**: 005-create-vendor
**Date**: 2025-10-11
**Status**: Complete

## Entities

### VendorExtractor (Existing Database Table)

**Table**: `vendor_extractors`

**Purpose**: Tracks operational status, test results, and capabilities for 45+ commission vendor extractors

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PRIMARY KEY | Unique vendor identifier |
| version | INTEGER | NOT NULL, DEFAULT 1 | Optimistic locking version (auto-increment on UPDATE) |
| name | VARCHAR(100) | UNIQUE, NOT NULL, INDEXED | Vendor name (primary lookup key) |
| status | VARCHAR(20) | NOT NULL, CHECK IN ('operational', 'broken') | Operational status |
| extractor_version | VARCHAR(50) | NOT NULL | Extractor semantic version |
| metadata_ | JSONB | NOT NULL | Pydantic-validated metadata (flexible schema) |
| created_at | TIMESTAMP WITH TIMEZONE | NOT NULL | Creation timestamp (UTC) |
| updated_at | TIMESTAMP WITH TIMEZONE | NOT NULL | Last update timestamp (UTC, auto-updated) |
| created_by | VARCHAR(100) | NOT NULL | AI client identifier (e.g., "claude-code") |

**Indexes**:
- `idx_vendor_name`: UNIQUE B-tree index on `name` column (enables <1ms lookups)
- `idx_vendor_status`: B-tree index on `status` column (enables fast operational/broken filtering)

**Relationships**:
- One-to-many with VendorDeploymentLink (many-to-many with DeploymentEvent)

**Initial Values for New Vendors**:
- `status`: "broken" (per FR-002)
- `version`: 1 (first version)
- `extractor_version`: "0.0.0" (initial version, updated later)
- `metadata_`: {} or user-provided initial_metadata after validation
- `created_at`: NOW() (UTC)
- `updated_at`: NOW() (UTC)
- `created_by`: From request parameter (default: "claude-code")

## Pydantic Request/Response Models

### CreateVendorRequest

**Purpose**: Validate create_vendor() tool input parameters

**Fields**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| name | str | REQUIRED, 1-100 chars, regex `^[a-zA-Z0-9 \-_]+$` | Vendor name (alphanumeric + spaces/hyphens/underscores) |
| initial_metadata | Optional[Dict[str, Any]] | OPTIONAL, flexible schema | Initial metadata with optional known fields |
| created_by | str | OPTIONAL, default="claude-code" | AI client identifier |

**Validation Rules**:
- `name`:
  - Cannot be empty or whitespace-only
  - Length: 1-100 characters
  - Pattern: `^[a-zA-Z0-9 \-_]+$` (alphanumeric, spaces, hyphens, underscores)
  - Case-insensitive uniqueness check (application-level)
- `initial_metadata` (if provided):
  - Known fields validated if present:
    - `scaffolder_version`: Must be string
    - `created_at`: Must be string in ISO 8601 format (e.g., "2025-10-11T10:00:00Z")
  - Unknown fields: Allowed without validation (flexible schema per clarifications)

**Example Valid Requests**:
```python
# Full metadata
{
    "name": "NewCorp",
    "initial_metadata": {
        "scaffolder_version": "1.0",
        "created_at": "2025-10-11T10:00:00Z",
        "custom_field": "custom_value"
    },
    "created_by": "claude-code"
}

# Partial metadata
{
    "name": "AcmeInc",
    "initial_metadata": {
        "scaffolder_version": "1.0"
    }
}

# No metadata
{
    "name": "TechCo"
}
```

**Example Invalid Requests**:
```python
# Empty name
{"name": ""}  # ValidationError: "Vendor name cannot be empty"

# Name too long
{"name": "A" * 101}  # ValidationError: "Vendor name must be 1-100 characters"

# Invalid characters
{"name": "Test@Vendor!"}  # ValidationError: "Vendor name must contain only alphanumeric characters, spaces, hyphens, and underscores"

# Invalid metadata types
{
    "name": "TestVendor",
    "initial_metadata": {
        "scaffolder_version": 123,  # ValidationError: "scaffolder_version must be string"
        "created_at": "invalid-date"  # ValidationError: "created_at must be ISO 8601 format"
    }
}
```

### CreateVendorResponse

**Purpose**: Return created vendor details matching MCP contract

**Fields**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | str | UUID string | Vendor unique identifier |
| name | str | 1-100 chars | Vendor name (as provided) |
| status | str | Always "broken" | Initial operational status |
| extractor_version | str | Always "0.0.0" | Initial extractor version (updated later) |
| metadata | Dict[str, Any] | Flexible schema | Stored metadata (merged with defaults) |
| version | int | Always 1 | Optimistic locking version |
| created_at | str | ISO 8601 format | Creation timestamp |
| updated_at | str | ISO 8601 format | Last update timestamp (same as created_at initially) |
| created_by | str | 1-100 chars | AI client identifier |

**Example Response**:
```python
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "NewCorp",
    "status": "broken",
    "extractor_version": "0.0.0",
    "metadata": {
        "scaffolder_version": "1.0",
        "created_at": "2025-10-11T10:00:00Z",
        "custom_field": "custom_value"
    },
    "version": 1,
    "created_at": "2025-10-11T10:15:30.123456+00:00",
    "updated_at": "2025-10-11T10:15:30.123456+00:00",
    "created_by": "claude-code"
}
```

## Validation Logic

### Name Validation

**Function**: `validate_vendor_name(name: str) -> None`

**Rules**:
1. Not empty or whitespace-only
2. Length: 1-100 characters
3. Pattern: `^[a-zA-Z0-9 \-_]+$`

**Implementation**:
```python
import re

VENDOR_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9 \-_]+$')

def validate_vendor_name(name: str) -> None:
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

### Case-Insensitive Duplicate Check

**Purpose**: Check if vendor name exists (case-insensitive) before INSERT

**Implementation**: Enforced by database functional unique index `idx_vendor_name_lower` on `LOWER(name)` column. Application-level duplicate check not required - database will reject duplicate inserts with IntegrityError, which service layer catches and translates to VendorAlreadyExistsError.

**Performance**: <1ms (database enforces uniqueness via functional index on LOWER(name))

### Metadata Validation

**Function**: `validate_create_vendor_metadata(metadata: Dict[str, Any] | None) -> Dict[str, Any]`

**Purpose**: Validate known metadata fields, allow unknown fields (flexible schema)

**Known Fields**:
- `scaffolder_version`: Optional[str] - Scaffolder version identifier
- `created_at`: Optional[str] - ISO 8601 timestamp when vendor was created

**Implementation**:
```python
from datetime import datetime

def validate_create_vendor_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if metadata is None:
        return {}

    validated = {}

    # Validate scaffolder_version if present
    if "scaffolder_version" in metadata:
        if not isinstance(metadata["scaffolder_version"], str):
            raise ValueError("scaffolder_version must be string")
        validated["scaffolder_version"] = metadata["scaffolder_version"]

    # Validate created_at if present (ISO 8601 format)
    if "created_at" in metadata:
        if not isinstance(metadata["created_at"], str):
            raise ValueError("created_at must be ISO 8601 string")
        try:
            datetime.fromisoformat(metadata["created_at"])
        except ValueError:
            raise ValueError("created_at must be valid ISO 8601 format")
        validated["created_at"] = metadata["created_at"]

    # Copy unknown fields without validation (flexible schema)
    for key, value in metadata.items():
        if key not in validated:
            validated[key] = value

    return validated
```

## Service Layer Interface

### create_vendor() Service Function

**Signature**:
```python
async def create_vendor(
    name: str,
    initial_metadata: dict[str, Any] | None,
    created_by: str,
    session: AsyncSession,
) -> VendorExtractor
```

**Parameters**:
- `name`: Vendor name (pre-validated by tool layer)
- `initial_metadata`: Optional metadata dict (pre-validated by tool layer)
- `created_by`: AI client identifier
- `session`: Active async database session

**Returns**: VendorExtractor SQLAlchemy model instance

**Raises**:
- `VendorAlreadyExistsError`: Vendor with name already exists (case-insensitive)
- `ValueError`: Invalid input parameters
- `IntegrityError`: Database constraint violation (UNIQUE constraint)

**Logic Flow**:
1. Create VendorExtractor instance with initial values
2. Add to session
3. Flush to trigger UNIQUE constraint check on LOWER(name)
4. Catch IntegrityError → Query existing vendor name → Raise VendorAlreadyExistsError with existing_name
5. Return created instance

## Error Handling

### VendorAlreadyExistsError

**Purpose**: Raised when attempting to create vendor with duplicate name (case-insensitive)

**Definition**:
```python
class VendorAlreadyExistsError(Exception):
    def __init__(self, vendor_name: str, existing_name: str | None = None) -> None:
        self.vendor_name = vendor_name
        self.existing_name = existing_name
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
            "http_status": 409,  # Conflict
        }
```

**HTTP Mapping**: 409 Conflict (standard for duplicate resource creation)

**MCP Translation**: Converted to ValueError in tool layer for MCP protocol compliance

**Example Error Messages**:
- Same case: `"Vendor already exists: NewCorp"`
- Different case: `"Vendor already exists: newcorp (conflicts with existing 'NewCorp')"`

## State Transitions

### New Vendor Lifecycle

```
[Not Exists]
     |
     | create_vendor()
     v
[Created: status="broken", version=1]
     |
     | update_vendor_status(status="operational")
     v
[Operational: status="operational", version=2]
```

**Initial State** (after create_vendor):
- status: "broken"
- version: 1
- extractor_version: "0.0.0" (initial version)
- metadata: initial_metadata or {}
- All format support flags: false (implied by initial 0.0.0 version)

**Note**: No format support flags in VendorExtractor table. Format support stored in metadata_ JSONB field.

## Performance Characteristics

### Latency Budget

**Target**: <100ms p95 (per FR-015)

**Operation Breakdown**:
1. Name validation (regex): ~0.1ms
2. Metadata validation (Python): ~0.5ms
3. INSERT operation: <5ms (single row with 2 indexes, functional unique index checks LOWER(name))
4. Response serialization: ~1ms
5. **Total**: ~7ms (93ms under budget)

### Concurrency

**Scenario**: Multiple AI assistants create same vendor simultaneously

**Handling**:
1. Both attempts INSERT with different case (e.g., "NewCorp" and "newcorp")
2. Database functional unique index on LOWER(name) rejects duplicate INSERT
3. Second INSERT gets IntegrityError
4. Service layer catches IntegrityError → Queries existing vendor name → Raises VendorAlreadyExistsError with existing_name (e.g., "newcorp (conflicts with existing 'NewCorp')")
5. Tool layer translates to ValueError for MCP client

**Result**: One succeeds, others get clear error message showing the conflicting name

## Testing Scenarios

### Valid Creation Scenarios
1. Create with full metadata (scaffolder_version, created_at, custom fields)
2. Create with partial metadata (scaffolder_version only)
3. Create with no metadata (empty dict)
4. Create with only custom fields (no known fields)

### Validation Error Scenarios
1. Empty vendor name → ValueError
2. Name too long (>100 chars) → ValueError
3. Name with invalid characters → ValueError
4. Invalid scaffolder_version type (int instead of str) → ValueError
5. Invalid created_at format (not ISO 8601) → ValueError

### Duplicate Detection Scenarios
1. Exact name match → VendorAlreadyExistsError: "Vendor already exists: NewCorp"
2. Case-insensitive match ("NewCorp" vs "newcorp") → VendorAlreadyExistsError: "Vendor already exists: newcorp (conflicts with existing 'NewCorp')"
3. Concurrent creation attempts → One succeeds, others get VendorAlreadyExistsError with existing_name showing the case that was created first

### Integration Scenarios
1. Create vendor + immediately query → Returns created vendor
2. Create vendor + update status → Status changes, version increments
3. Create vendor + create deployment → Links vendor to deployment
