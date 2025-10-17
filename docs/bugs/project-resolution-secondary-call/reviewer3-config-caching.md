# Config Caching Analysis - Critical Bug Found

## Executive Summary

**Bug Found:** Cache returns config but not config_path, causing redundant filesystem search on cache hits that can fail or find wrong path.

**Confidence Level:** 95% - Clear implementation gap between cache storage and retrieval

## The Problem Flow

### Cache Miss (First Call - Works)
```python
# session.py lines 351-381
if config is None:  # Cache miss
    config_path = find_config_file(Path(working_dir))  # ✅ Gets path
    config = validate_config_syntax(config_path)        # ✅ Reads config
    await cache.set(working_dir, config, config_path)   # ✅ Stores BOTH

# Lines 383-395 - config_path already set, skips this block

# Line 401 - Calls with correct config_path
get_or_create_project_from_config(config_path)  # ✅ Works
```

### Cache Hit (Second Call - FAILS)
```python
# session.py lines 344-348
config = await cache.get(working_dir)  # Returns ONLY config dict
# config_path remains None! ❌

# Lines 383-395 - PROBLEM AREA
if config_path is None:  # True on cache hit!
    config_path = find_config_file(Path(working_dir))  # Redundant search!
    # This can fail or return different path
```

## Root Cause Analysis

### 1. Cache Storage vs Retrieval Mismatch

**Cache stores** (cache.py line 150-155):
```python
self._cache[working_directory] = CacheEntry(
    config=config,
    config_path=config_path,  # ✅ Path stored
    mtime_ns=mtime_ns,
    access_time=time.time(),
)
```

**Cache returns** (cache.py line 114):
```python
return entry.config  # ❌ Only config, not path!
```

### 2. Redundant Filesystem Search

When cache hit occurs:
1. `config` is retrieved from cache
2. `config_path` remains `None`
3. Lines 383-395 trigger redundant `find_config_file()` search
4. This search can:
   - Fail (permissions, symlinks, etc.)
   - Find a different config file (if multiple exist in hierarchy)
   - Succeed but waste time

### 3. Why Second Call Fails

The second call fails because:
1. First call updates config with project.id and writes to disk
2. Second call gets cached config (with project.id)
3. But needs to re-find config_path (redundant search)
4. If find_config_file() fails, entire resolution fails
5. Even if it succeeds, `get_or_create_project_from_config()` re-reads from disk (line 265)

## Specific Code Issues

### Issue 1: Cache Interface Design Flaw
```python
# Current implementation (cache.py line 72)
async def get(self, working_directory: str) -> Optional[Dict[str, Any]]:
    # Returns only config dict

# Should be:
async def get(self, working_directory: str) -> Optional[Tuple[Dict[str, Any], Path]]:
    # Returns (config, config_path) tuple
```

### Issue 2: Session.py Cache Handling
```python
# Current (lines 344-348, 383-395)
config = await cache.get(working_dir)  # Only gets config
# ...
if config_path is None:  # Always true on cache hit!
    config_path = find_config_file(...)  # Redundant!

# Should be:
cache_result = await cache.get(working_dir)
if cache_result:
    config, config_path = cache_result  # Get both!
```

### Issue 3: Double Config Reading
Even after fixing cache, `get_or_create_project_from_config()` at line 265 still re-reads from disk:
```python
config = read_config(config_path)  # Re-reads even if we have cached config!
```

## Proposed Fix

### Option 1: Fix Cache Interface (Recommended)

**1. Update cache.py get() method:**
```python
async def get(self, working_directory: str) -> Optional[Tuple[Dict[str, Any], Path]]:
    async with self._lock:
        entry = self._cache.get(working_directory)
        if entry is None:
            return None

        # Validate mtime...

        entry.access_time = time.time()
        return (entry.config, entry.config_path)  # Return BOTH
```

**2. Update session.py cache handling:**
```python
# Line 344
cache_result = await cache.get(working_dir)

if cache_result is None:
    # Cache miss path...
    config_path = find_config_file(...)
    config = validate_config_syntax(config_path)
    await cache.set(working_dir, config, config_path)
else:
    # Cache hit - we have both!
    config, config_path = cache_result

# No need for lines 383-395 anymore!
```

### Option 2: Pass Config to get_or_create_project_from_config()

Modify `get_or_create_project_from_config()` to optionally accept pre-loaded config:
```python
async def get_or_create_project_from_config(
    config_path: Path,
    registry: ProjectRegistry | None = None,
    config: dict[str, any] | None = None,  # Add this
) -> Project:
    if config is None:
        config = read_config(config_path)  # Only read if not provided
    # Rest of logic...
```

## Impact Analysis

### Current Impact
- Every cache hit triggers redundant filesystem traversal
- Potential for finding wrong config file
- Unnecessary disk I/O on every cached resolution
- Can fail even when cache has valid data

### After Fix
- Cache hits avoid ALL filesystem operations
- Consistent config path between calls
- True <1ms cache performance
- No risk of path mismatch

## Validation

Test scenario to verify fix:
```python
# Setup
ctx = mock_context()
await set_working_directory("/test/dir", ctx)

# First call - cache miss
project1 = await resolve_project_id(None, None, ctx)
# Should: find config, create project, cache (config, path)

# Second call - cache hit
project2 = await resolve_project_id(project1[0], None, ctx)
# Should: get (config, path) from cache, no filesystem ops

# Verify no find_config_file() on second call
assert mock_find_config_file.call_count == 1  # Only first call
```

## Conclusion

The bug is a clear cache interface design flaw where the cache stores both config and path but only returns config. This forces redundant filesystem operations on every cache hit, defeating the purpose of caching and introducing failure points.

**Recommendation:** Implement Option 1 - fix the cache interface to return both config and config_path. This is the cleanest solution and maintains proper separation of concerns.

**Confidence:** 95% - The code clearly shows the mismatch between what's stored and what's returned from cache.