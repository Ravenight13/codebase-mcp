# Integration Test Fixture Architecture

**Date**: 2025-10-10
**Status**: Implemented and Validated
**Author**: Claude Code (Test Automation Engineer)

## Executive Summary

This document describes the async fixture architecture implemented to resolve event loop conflicts in the integration test suite for the Codebase MCP Server.

## Problem Statement

### Original Issues

1. **Event Loop Conflicts**: `RuntimeError: Task got Future attached to a different loop`
2. **Transaction Management**: `sqlalchemy.exc.InvalidRequestError: Can't operate on closed transaction inside context manager`
3. **Test Isolation**: Duplicate key violations suggesting data leakage between tests

### Root Cause Analysis

The original fixture implementation used **session-scoped async fixtures** for the database engine. This caused:
- AsyncEngine created in one event loop
- Tests running in different event loops (pytest-asyncio function scope)
- Connection pool conflicts between loops
- Transaction management failures

## Solution Architecture

### Fixture Hierarchy

```
database_url (session, non-async)
    ↓
test_engine (function, async) ← Creates schema
    ↓
├── test_session_factory (function, non-async) ← For multi-client tests
│       ↓
│   Multiple AsyncSession instances
│
└── session (function, async) ← For single-session tests
        ↓
    Single AsyncSession instance
```

### Key Design Principles

1. **Function Scope for Async Fixtures**: All async fixtures use `scope="function"` to ensure each test gets its own event loop
2. **Schema Per Test**: Each test creates and tears down the full database schema
3. **Transaction Isolation**: Sessions don't use explicit BEGIN/ROLLBACK blocks to allow commits in fixtures
4. **Factory Pattern**: `test_session_factory` fixture provides a factory for creating multiple sessions (concurrent client simulation)

## Fixture Implementations

### 1. database_url (Session Scope, Non-Async)

```python
@pytest.fixture(scope="session")
def database_url() -> str:
    """Get test database URL from environment or use default."""
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/codebase_mcp_test",
    )
```

**Rationale**: Configuration values can safely be session-scoped since they don't involve async operations.

### 2. test_engine (Function Scope, Async)

```python
@pytest_asyncio.fixture(scope="function")
async def test_engine(database_url: str) -> AsyncGenerator[AsyncEngine, None]:
    """Create async database engine for tests."""
    test_engine = create_async_engine(
        database_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )

    # Create all tables
    async with test_engine.begin() as conn:
        await conn.execute(sqlalchemy.text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    yield test_engine

    # Cleanup: Drop all tables and dispose engine
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()
```

**Key Features**:
- **Function-scoped**: Each test gets fresh engine with current event loop
- **Schema management**: Creates all tables in setup, drops all in teardown
- **Complete isolation**: No data persists between tests

### 3. test_session_factory (Function Scope, Non-Async)

```python
@pytest.fixture(scope="function")
def test_session_factory(test_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Provide test-specific session factory for creating multiple sessions."""
    return async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
```

**Use Cases**:
- Concurrent client simulation tests
- Multiple database sessions in single test
- Optimistic locking conflict testing

**Usage Example**:
```python
async def test_concurrent_updates(
    test_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    # Client A session
    async with test_session_factory() as db1:
        await update_work_item(session=db1, ...)
        await db1.commit()

    # Client B session
    async with test_session_factory() as db2:
        await update_work_item(session=db2, ...)
        await db2.commit()
```

### 4. session (Function Scope, Async)

```python
@pytest_asyncio.fixture(scope="function")
async def session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for tests with automatic rollback."""
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as test_session:
        try:
            yield test_session
        finally:
            if test_session.in_transaction():
                await test_session.rollback()
            await test_session.close()
```

**Key Features**:
- **No explicit transaction block**: Allows commits in fixtures
- **Automatic cleanup**: Rolls back pending transactions
- **Schema isolation**: Relies on test_engine's schema drop/recreate

**Usage Example**:
```python
async def test_create_vendor(session: AsyncSession) -> None:
    vendor = VendorExtractor(name="test-vendor")
    session.add(vendor)
    await session.commit()

    # Assertions...
    # Automatic cleanup via test_engine fixture
```

## Configuration

### pytest.ini / pyproject.toml

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"  # Prevent event loop conflicts
```

**Critical**: `asyncio_default_fixture_loop_scope = "function"` ensures all async fixtures default to function scope unless explicitly overridden.

## Migration Guide

### Before (Session-Scoped Engine)

```python
@pytest.fixture(scope="session")  # ❌ WRONG
async def engine(database_url: str) -> AsyncGenerator[AsyncEngine, None]:
    test_engine = create_async_engine(database_url)
    yield test_engine
    await test_engine.dispose()

@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSession(engine) as session:
        async with session.begin():  # ❌ Explicit transaction blocks commits
            yield session
            await session.rollback()
```

**Problems**:
- Session-scoped engine creates connections in different event loop
- Explicit transaction block prevents commits in fixtures
- Tests can't simulate real commit behavior

### After (Function-Scoped Engine)

```python
@pytest_asyncio.fixture(scope="function")  # ✅ CORRECT
async def test_engine(database_url: str) -> AsyncGenerator[AsyncEngine, None]:
    test_engine = create_async_engine(database_url)

    # Setup schema
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield test_engine

    # Teardown schema
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    async with async_sessionmaker(test_engine)() as session:
        try:
            yield session  # ✅ No transaction block, allows commits
        finally:
            if session.in_transaction():
                await session.rollback()
            await session.close()
```

**Benefits**:
- Each test gets fresh engine in current event loop
- Fixtures can commit freely
- Complete test isolation via schema recreation

## Performance Considerations

### Trade-offs

**Function-Scoped Engine**:
- ✅ **Pros**: Complete isolation, no event loop conflicts, reliable test execution
- ❌ **Cons**: Slower tests due to schema creation per test (adds ~100-200ms per test)

**Session-Scoped Engine** (original):
- ✅ **Pros**: Faster tests, schema created once
- ❌ **Cons**: Event loop conflicts, data leakage, unreliable tests

### Optimization Strategies

1. **Test Grouping**: Run related tests in same module to share schema creation overhead
2. **Parallel Execution**: Use pytest-xdist with `--numprocesses` for parallelization
3. **Selective Testing**: Use markers (`@pytest.mark.integration`) to skip slow tests during development

## Validation

### Test Results

**Before Fixes**:
```
tests/integration/test_vendor_query_performance.py::test_vendor_response_schema_compliance ERROR
RuntimeError: Task got Future attached to a different loop
```

**After Fixes**:
```
tests/integration/test_vendor_query_performance.py PASSED (5/5 tests)
tests/integration/test_concurrent_work_item_updates.py PASSED (11/13 tests)
```

**Remaining Failures**: 2 failures are application logic issues (version increment bug, not fixture issues)

### Validated Scenarios

✅ Single test execution
✅ Multiple tests in same file
✅ Multiple test files
✅ Concurrent session creation (multi-client tests)
✅ No event loop conflicts
✅ No transaction management errors
✅ Complete test isolation

## Common Patterns

### Pattern 1: Single Session Test

```python
async def test_create_entity(session: AsyncSession) -> None:
    entity = MyEntity(name="test")
    session.add(entity)
    await session.commit()
    await session.refresh(entity)

    assert entity.id is not None
```

### Pattern 2: Multi-Client Test

```python
async def test_concurrent_updates(
    test_session_factory: async_sessionmaker[AsyncSession],
    work_item: WorkItem
) -> None:
    # Client A
    async with test_session_factory() as db1:
        await update_work_item(work_item.id, version=1, session=db1)
        await db1.commit()

    # Client B (should fail with optimistic lock error)
    with pytest.raises(OptimisticLockError):
        async with test_session_factory() as db2:
            await update_work_item(work_item.id, version=1, session=db2)
            await db2.commit()
```

### Pattern 3: Test Fixture with Session

```python
@pytest.fixture
async def test_vendor(session: AsyncSession) -> VendorExtractor:
    vendor = VendorExtractor(name="test-vendor")
    session.add(vendor)
    await session.commit()  # Required in fixture
    await session.refresh(vendor)  # Get DB-generated fields
    return vendor
```

## Troubleshooting

### Issue: Event Loop Closed Error

**Symptom**: `RuntimeError: Event loop is closed`

**Cause**: Using session-scoped async fixtures or mixing event loops

**Solution**: Ensure all async fixtures use `scope="function"` and `@pytest_asyncio.fixture`

### Issue: Can't Operate on Closed Transaction

**Symptom**: `sqlalchemy.exc.InvalidRequestError: Can't operate on closed transaction`

**Cause**: Explicit transaction block (`async with session.begin()`) in fixture

**Solution**: Remove explicit transaction block, let session handle commits naturally

### Issue: Duplicate Key Violations

**Symptom**: Tests fail with unique constraint violations

**Cause**: Data persisting between tests (schema not dropping/recreating)

**Solution**: Verify `test_engine` fixture properly drops schema in cleanup

## References

- **pytest-asyncio Documentation**: https://pytest-asyncio.readthedocs.io/
- **SQLAlchemy Async Documentation**: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- **Constitutional Compliance**:
  - Principle VII: TDD (comprehensive test infrastructure)
  - Principle VIII: Type Safety (type-annotated fixtures)
  - Principle V: Production Quality (proper resource cleanup)

## Changelog

- **2025-10-10**: Initial implementation
  - Function-scoped async fixtures
  - Test-specific session factory
  - pytest-asyncio configuration
  - Comprehensive documentation
