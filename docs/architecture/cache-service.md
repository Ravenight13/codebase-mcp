# SQLite Cache Service

## Overview

The SQLite cache service provides persistent, file-based caching with automatic TTL (Time-To-Live) management for offline fallback when PostgreSQL is unavailable.

**Location**: `src/services/cache.py`

## Key Features

- **30-minute TTL**: All cached entries automatically expire after 30 minutes
- **Async Context Manager**: Automatic connection lifecycle management
- **Schema Mirroring**: Matches PostgreSQL table structure for transparent fallback
- **Type Safety**: Full mypy --strict compliance with comprehensive type annotations
- **Performance**: <1ms cache lookups via indexed primary keys
- **File-based Persistence**: Survives process restarts (default: `cache/project_status.db`)

## Constitutional Compliance

- **Principle II**: Local-first (no external dependencies)
- **Principle III**: Protocol compliance (async operations matching AsyncPG)
- **Principle IV**: Performance (<1ms lookups, <100ms bulk operations)
- **Principle V**: Production quality (comprehensive error handling)
- **Principle VIII**: Type safety (mypy --strict compliance)

## Usage

### Basic Operations

```python
from src.services.cache import SQLiteCache
from uuid import uuid4

# Initialize cache with async context manager
async with SQLiteCache() as cache:
    # Cache vendor extractor
    vendor_data = {
        "id": str(uuid4()),
        "name": "vendor_abc",
        "status": "operational",
        "version": 1,
        "extractor_version": "2.3.1",
        "metadata_": {...},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "created_by": "mcp-client"
    }
    await cache.set_vendor("vendor_abc", vendor_data)
    
    # Retrieve cached vendor
    cached = await cache.get_vendor("vendor_abc")
    if cached:
        print(f"Found vendor: {cached['name']}")
    
    # Cache work item
    item_id = uuid4()
    work_item_data = {...}
    await cache.set_work_item(item_id, work_item_data)
    
    # Check staleness
    is_stale = await cache.is_stale(f"vendor:{vendor_name}")
    if is_stale:
        print("Entry expired, needs refresh")
    
    # Clear stale entries
    removed_count = await cache.clear_stale()
    print(f"Removed {removed_count} stale entries")
```

### Advanced Operations

```python
# Get cache statistics
stats = await cache.get_stats()
print(f"Total entries: {stats.total_entries}")
print(f"Stale entries: {stats.stale_entries}")

# Clear all cache entries
cleared = await cache.clear_all()
print(f"Cleared {cleared} entries")

# Custom cache path
cache = SQLiteCache(db_path=Path("custom/path/cache.db"))
async with cache:
    # Operations...
```

## API Reference

### SQLiteCache Class

**Constructor**:
- `db_path: Path` - Database file path (default: `cache/project_status.db`)

**Vendor Operations**:
- `async get_vendor(name: str) -> dict | None` - Retrieve cached vendor by name
- `async set_vendor(name: str, data: dict) -> None` - Cache vendor data

**Work Item Operations**:
- `async get_work_item(item_id: UUID) -> dict | None` - Retrieve cached work item
- `async set_work_item(item_id: UUID, data: dict) -> None` - Cache work item data

**TTL Operations**:
- `async is_stale(cache_key: str) -> bool` - Check if entry exceeds TTL
- `async clear_stale() -> int` - Remove all expired entries

**Statistics**:
- `async get_stats() -> CacheStats` - Calculate cache metrics

**Maintenance**:
- `async clear_all() -> int` - Clear all cache entries

### CacheStats Model

```python
class CacheStats(BaseModel):
    total_entries: int           # Total cached entries
    stale_entries: int           # Entries exceeding TTL
    vendors_cached: int          # Vendor extractor count
    work_items_cached: int       # Work item count
    oldest_entry_age_seconds: float  # Age of oldest entry
```

## Schema

### cached_vendors Table

```sql
CREATE TABLE cached_vendors (
    name TEXT PRIMARY KEY,
    data TEXT NOT NULL,  -- JSON serialized vendor
    cached_at REAL NOT NULL  -- Unix timestamp
);

CREATE INDEX idx_vendors_cached_at ON cached_vendors (cached_at);
```

### cached_work_items Table

```sql
CREATE TABLE cached_work_items (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,  -- JSON serialized work item
    cached_at REAL NOT NULL  -- Unix timestamp
);

CREATE INDEX idx_work_items_cached_at ON cached_work_items (cached_at);
```

### cache_metadata Table

```sql
CREATE TABLE cache_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at REAL NOT NULL
);
```

## Performance Targets

- **Cache Lookup**: <1ms (indexed primary keys)
- **Bulk Cleanup**: <100ms (50 entries)
- **TTL**: 30 minutes (1800 seconds)

## Error Handling

All cache operations are designed for graceful degradation:

```python
# RuntimeError raised if cache not initialized
try:
    await cache.get_vendor("test")
except RuntimeError as e:
    print(f"Cache error: {e}")

# ValueError raised for invalid cache keys
try:
    await cache.is_stale("invalid_key")
except ValueError as e:
    print(f"Invalid key format: {e}")

# None returned for cache misses
vendor = await cache.get_vendor("nonexistent")
if vendor is None:
    print("Cache miss - fetch from PostgreSQL")
```

## Testing

Run the comprehensive test suite:

```bash
pytest tests/test_cache.py -v --cov=src/services/cache
```

**Coverage**: 83% (25 tests, all passing)

Run the usage example:

```bash
python examples/cache_usage.py
```

## Integration with PostgreSQL Fallback

The cache is designed to work alongside PostgreSQL:

```python
# Try PostgreSQL first
try:
    vendor = await postgres_session.query(VendorExtractor).filter_by(name="vendor_abc").first()
except DatabaseError:
    # PostgreSQL unavailable - use cache
    vendor_data = await cache.get_vendor("vendor_abc")
    if vendor_data is None:
        raise RuntimeError("Vendor not found in cache")
```

## Dependencies

- **aiosqlite** >=0.19.0 - Async SQLite interface
- **pydantic** >=2.5.0 - Data validation

Added to `requirements.txt`:

```
aiosqlite>=0.19.0
```

## Future Enhancements

- [ ] Automatic background cleanup task for stale entries
- [ ] Configurable TTL per entry type
- [ ] Cache warming strategy on PostgreSQL reconnect
- [ ] Compression for large cached entries
- [ ] Cache hit/miss metrics tracking

## See Also

- [SQLite Cache Implementation](../src/services/cache.py)
- [Cache Tests](../tests/test_cache.py)
- [Usage Example](../examples/cache_usage.py)
- [Research: SQLite Cache Decision](../specs/003-database-backed-project/research.md)
