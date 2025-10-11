# Quickstart: Create Vendor MCP Function

**Feature**: 005-create-vendor
**Date**: 2025-10-11
**Purpose**: Integration test scenarios validating create_vendor() MCP tool functionality

## Prerequisites

### Database Setup
```bash
# Ensure PostgreSQL running with test database
psql -U postgres -c "CREATE DATABASE codebase_mcp_test;"

# Run migrations
alembic upgrade head
```

### Test Environment
```bash
# Activate virtual environment
source .venv/bin/activate

# Install test dependencies
pip install -r requirements-dev.txt
```

## Test Scenarios

### Scenario 1: Create Vendor with Full Metadata

**Objective**: Validate vendor creation with all metadata fields

**Given**:
- No vendor named "NewCorp" exists in database
- AI assistant has scaffolded vendor code skeleton

**When**:
```python
response = await create_vendor(
    name="NewCorp",
    initial_metadata={
        "scaffolder_version": "1.0",
        "created_at": "2025-10-11T10:00:00Z",
        "custom_field": "custom_value"
    },
    created_by="claude-code"
)
```

**Then**:
- Response status: SUCCESS
- Response contains:
  - `id`: Valid UUID string
  - `name`: "NewCorp"
  - `status`: "broken"
  - `extractor_version`: "0.0.0"
  - `metadata`: {"scaffolder_version": "1.0", "created_at": "2025-10-11T10:00:00Z", "custom_field": "custom_value"}
  - `version`: 1
  - `created_at`: ISO 8601 timestamp (within 1 second of call)
  - `updated_at`: ISO 8601 timestamp (same as created_at)
  - `created_by`: "claude-code"
- Database record created in vendor_extractors table
- Record queryable via query_vendor_status("NewCorp")

**Validation**:
```python
# Verify database record
vendor = await query_vendor_status(name="NewCorp")
assert vendor["name"] == "NewCorp"
assert vendor["status"] == "broken"
assert vendor["version"] == 1
assert vendor["metadata"]["scaffolder_version"] == "1.0"
assert vendor["metadata"]["custom_field"] == "custom_value"
```

**Performance**:
- Latency: <100ms p95

---

### Scenario 2: Create Vendor with Partial Metadata

**Objective**: Validate vendor creation with only scaffolder_version

**Given**:
- No vendor named "AcmeInc" exists in database

**When**:
```python
response = await create_vendor(
    name="AcmeInc",
    initial_metadata={
        "scaffolder_version": "1.0"
    }
)
```

**Then**:
- Response status: SUCCESS
- `name`: "AcmeInc"
- `status`: "broken"
- `metadata`: {"scaffolder_version": "1.0"}
- `version`: 1
- `created_by`: "claude-code" (default)

**Validation**:
```python
vendor = await query_vendor_status(name="AcmeInc")
assert vendor["metadata"]["scaffolder_version"] == "1.0"
assert "created_at" not in vendor["metadata"]  # Optional field not provided
assert "custom_field" not in vendor["metadata"]
```

---

### Scenario 3: Create Vendor with No Metadata

**Objective**: Validate vendor creation with empty metadata

**Given**:
- No vendor named "TechCo" exists in database

**When**:
```python
response = await create_vendor(
    name="TechCo"
)
```

**Then**:
- Response status: SUCCESS
- `name`: "TechCo"
- `metadata`: {} (empty dict)
- All other fields present with default values

**Validation**:
```python
vendor = await query_vendor_status(name="TechCo")
assert vendor["metadata"] == {}
```

---

### Scenario 4: Duplicate Vendor Error (Exact Match)

**Objective**: Validate duplicate detection for exact name match

**Given**:
- Vendor "ExistingVendor" already exists in database

**When**:
```python
response = await create_vendor(
    name="ExistingVendor",
    initial_metadata={}
)
```

**Then**:
- Response status: ERROR
- Error type: "VendorAlreadyExistsError"
- Error message: "Vendor already exists: ExistingVendor"
- No new database record created
- Existing vendor record unchanged

**Validation**:
```python
try:
    await create_vendor(name="ExistingVendor")
    assert False, "Expected VendorAlreadyExistsError"
except ValueError as e:
    assert "already exists" in str(e).lower()

# Verify existing vendor unchanged
vendor = await query_vendor_status(name="ExistingVendor")
assert vendor["version"] == 1  # Original version unchanged
```

---

### Scenario 5: Duplicate Vendor Error (Case-Insensitive)

**Objective**: Validate case-insensitive duplicate detection

**Given**:
- Vendor "NewCorp" exists in database (from Scenario 1)

**When**:
```python
response = await create_vendor(
    name="newcorp"  # Different case
)
```

**Then**:
- Response status: ERROR
- Error type: "VendorAlreadyExistsError"
- Error message: "Vendor already exists: newcorp (conflicts with existing 'NewCorp')"
- No new database record created

**Validation**:
```python
try:
    await create_vendor(name="newcorp")
    assert False, "Expected VendorAlreadyExistsError for case-insensitive duplicate"
except ValueError as e:
    assert "already exists" in str(e).lower()

# Verify only one "NewCorp" record exists
count = await session.execute(
    select(func.count()).select_from(VendorExtractor)
    .where(func.lower(VendorExtractor.name) == "newcorp")
)
assert count.scalar() == 1
```

---

### Scenario 6: Immediate Query After Creation

**Objective**: Validate newly created vendor is immediately queryable

**Given**:
- No vendor named "QueryTest" exists

**When**:
```python
create_response = await create_vendor(
    name="QueryTest",
    initial_metadata={"scaffolder_version": "1.0"}
)

# Immediately query without delay
query_response = await query_vendor_status(name="QueryTest")
```

**Then**:
- Both operations succeed
- `create_response["id"]` == `query_response["id"]`
- `query_response["status"]` == "broken"
- `query_response["version"]` == 1
- `query_response["metadata"]` matches `create_response["metadata"]`

**Validation**:
```python
assert create_response["name"] == query_response["name"]
assert create_response["version"] == query_response["version"]
assert create_response["metadata"] == query_response["metadata"]
```

---

### Scenario 7: Invalid Name Validation (Empty)

**Objective**: Validate empty name rejection

**Given**:
- Attempting to create vendor with empty name

**When**:
```python
response = await create_vendor(name="")
```

**Then**:
- Response status: ERROR
- Error type: "ValidationError"
- Error message: "Vendor name cannot be empty"
- HTTP status: 400 (Bad Request)

**Validation**:
```python
try:
    await create_vendor(name="")
    assert False, "Expected ValidationError"
except ValueError as e:
    assert "cannot be empty" in str(e).lower()
```

---

### Scenario 8: Invalid Name Validation (Too Long)

**Objective**: Validate length constraint (max 100 characters)

**Given**:
- Attempting to create vendor with 101-character name

**When**:
```python
response = await create_vendor(name="A" * 101)
```

**Then**:
- Response status: ERROR
- Error type: "ValidationError"
- Error message: "Vendor name must be 1-100 characters, got 101"

**Validation**:
```python
try:
    await create_vendor(name="A" * 101)
    assert False, "Expected ValidationError"
except ValueError as e:
    assert "1-100 characters" in str(e).lower()
```

---

### Scenario 9: Invalid Name Validation (Invalid Characters)

**Objective**: Validate character constraint (alphanumeric + spaces/hyphens/underscores)

**Given**:
- Attempting to create vendor with special characters

**When**:
```python
response = await create_vendor(name="Test@Vendor!")
```

**Then**:
- Response status: ERROR
- Error type: "ValidationError"
- Error message: "Vendor name must contain only alphanumeric characters, spaces, hyphens, and underscores"

**Validation**:
```python
invalid_names = [
    "Test@Vendor",
    "Vendor!",
    "Test#123",
    "Vendor$Corp",
    "Test%Value"
]

for name in invalid_names:
    try:
        await create_vendor(name=name)
        assert False, f"Expected ValidationError for name: {name}"
    except ValueError as e:
        assert "alphanumeric" in str(e).lower()
```

---

### Scenario 10: Invalid Metadata Type (scaffolder_version)

**Objective**: Validate scaffolder_version type constraint

**Given**:
- Attempting to create vendor with non-string scaffolder_version

**When**:
```python
response = await create_vendor(
    name="TestVendor",
    initial_metadata={"scaffolder_version": 123}  # Integer instead of string
)
```

**Then**:
- Response status: ERROR
- Error type: "ValidationError"
- Error message: "scaffolder_version must be string"

**Validation**:
```python
try:
    await create_vendor(
        name="TestVendor",
        initial_metadata={"scaffolder_version": 123}
    )
    assert False, "Expected ValidationError"
except ValueError as e:
    assert "scaffolder_version" in str(e).lower()
    assert "string" in str(e).lower()
```

---

### Scenario 11: Invalid Metadata Format (created_at)

**Objective**: Validate created_at ISO 8601 format constraint

**Given**:
- Attempting to create vendor with invalid created_at format

**When**:
```python
response = await create_vendor(
    name="TestVendor2",
    initial_metadata={"created_at": "invalid-date"}
)
```

**Then**:
- Response status: ERROR
- Error type: "ValidationError"
- Error message: "created_at must be valid ISO 8601 format"

**Validation**:
```python
invalid_dates = [
    "invalid-date",
    "2025-13-01",  # Invalid month
    "2025-10-32",  # Invalid day
    "not-a-date"
]

for date in invalid_dates:
    try:
        await create_vendor(
            name=f"TestVendor_{date}",
            initial_metadata={"created_at": date}
        )
        assert False, f"Expected ValidationError for date: {date}"
    except ValueError as e:
        assert "created_at" in str(e).lower() or "iso 8601" in str(e).lower()
```

---

### Scenario 12: Concurrent Creation Attempts

**Objective**: Validate concurrent creation safety

**Given**:
- Two AI assistants attempt to create same vendor simultaneously

**When**:
```python
import asyncio

# Simulate concurrent calls
task1 = create_vendor(name="ConcurrentVendor", initial_metadata={"source": "assistant1"})
task2 = create_vendor(name="ConcurrentVendor", initial_metadata={"source": "assistant2"})

results = await asyncio.gather(task1, task2, return_exceptions=True)
```

**Then**:
- One call succeeds (creates vendor)
- Other call fails with VendorAlreadyExistsError
- Exactly one vendor record exists in database
- Successful vendor has one of the two metadata values

**Validation**:
```python
successes = [r for r in results if not isinstance(r, Exception)]
failures = [r for r in results if isinstance(r, Exception)]

assert len(successes) == 1, "Exactly one concurrent creation should succeed"
assert len(failures) == 1, "Exactly one concurrent creation should fail"
assert isinstance(failures[0], ValueError), "Failure should be VendorAlreadyExistsError translated to ValueError"

# Verify single record
vendor = await query_vendor_status(name="ConcurrentVendor")
assert vendor["metadata"]["source"] in ["assistant1", "assistant2"]
```

---

## Performance Validation

### Latency Test

**Objective**: Validate <100ms p95 latency requirement (FR-015)

**Setup**:
```python
import time
import statistics

latencies = []
for i in range(100):
    start = time.perf_counter()
    await create_vendor(
        name=f"PerfTest_{i}",
        initial_metadata={"iteration": i}
    )
    latency_ms = (time.perf_counter() - start) * 1000
    latencies.append(latency_ms)
```

**Validation**:
```python
p50 = statistics.quantiles(latencies, n=100)[49]
p95 = statistics.quantiles(latencies, n=100)[94]
p99 = statistics.quantiles(latencies, n=100)[98]

print(f"Latency p50: {p50:.2f}ms")
print(f"Latency p95: {p95:.2f}ms")
print(f"Latency p99: {p99:.2f}ms")

assert p95 < 100, f"p95 latency {p95:.2f}ms exceeds 100ms target"
```

**Expected Results**:
- p50: <10ms
- p95: <50ms (well under 100ms target)
- p99: <100ms

---

## Cleanup

```python
# Clean up test vendors
test_vendors = [
    "NewCorp", "AcmeInc", "TechCo", "ExistingVendor",
    "QueryTest", "TestVendor", "TestVendor2", "ConcurrentVendor"
] + [f"PerfTest_{i}" for i in range(100)]

for name in test_vendors:
    try:
        await session.execute(
            delete(VendorExtractor).where(VendorExtractor.name == name)
        )
    except Exception:
        pass  # Vendor may not exist

await session.commit()
```

---

## Integration with Vendor Workflow

### End-to-End Vendor Onboarding Test

**Objective**: Validate complete vendor lifecycle from scaffolding to operational

**Steps**:

1. **Scaffold vendor code** (simulated):
   ```bash
   # scripts/new_vendor.sh creates files
   # - src/extractors/new_vendor.py
   # - tests/test_new_vendor.py
   # - fixtures/new_vendor_samples/
   ```

2. **Create vendor record**:
   ```python
   vendor = await create_vendor(
       name="FullWorkflowVendor",
       initial_metadata={
           "scaffolder_version": "1.0",
           "created_at": datetime.now(timezone.utc).isoformat()
       },
       created_by="claude-code"
   )
   assert vendor["status"] == "broken"
   assert vendor["version"] == 1
   ```

3. **Verify immediate queryability**:
   ```python
   queried = await query_vendor_status(name="FullWorkflowVendor")
   assert queried["id"] == vendor["id"]
   assert queried["status"] == "broken"
   ```

4. **Implement extractor** (simulated):
   ```python
   # Developer writes extractor code
   # Tests pass
   # Ready to mark operational
   ```

5. **Update to operational**:
   ```python
   updated = await update_vendor_status(
       name="FullWorkflowVendor",
       version=1,
       status="operational",
       metadata={
           "test_results": {"passing": 50, "total": 50, "skipped": 0},
           "format_support": {"excel": True, "csv": True, "pdf": False, "ocr": False},
           "extractor_version": "1.0.0",
           "manifest_compliant": True
       }
   )
   assert updated["status"] == "operational"
   assert updated["version"] == 2  # Version incremented
   ```

6. **Final verification**:
   ```python
   final = await query_vendor_status(name="FullWorkflowVendor")
   assert final["status"] == "operational"
   assert final["version"] == 2
   assert final["metadata"]["test_results"]["passing"] == 50
   ```

**Expected Duration**: <5 seconds for complete workflow
**Expected Outcome**: Vendor successfully transitions from creation to operational status

---

## Test Execution

```bash
# Run all integration tests
pytest tests/integration/test_create_vendor_integration.py -v

# Run with coverage
pytest tests/integration/test_create_vendor_integration.py --cov=src.mcp.tools.tracking --cov=src.services.vendor

# Run performance tests
pytest tests/integration/test_create_vendor_integration.py::test_create_vendor_latency -v
```

**Success Criteria**:
- All scenarios pass
- p95 latency <100ms
- No database constraint violations
- Proper error handling for all edge cases
