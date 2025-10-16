# Testing Prompts for Config-Based Project Tracking

## Main Testing Prompt (New Chat Window)

```
Run the test suite for spec 013 config-based project tracking. This code is already implemented - just validate it works.

Execute these commands and report results:

1. Run pytest:
   pytest tests/test_013_config_based_tracking.py -v

2. Validate the config file exists and works:
   uv run python -c "
   from src.auto_switch.validation import validate_config_syntax
   from pathlib import Path
   config = validate_config_syntax(Path('.codebase-mcp/config.json'))
   print(f'Config valid: {config[\"project\"][\"name\"]}')
   "

3. Test the resolution chain:
   uv run python -c "
   import asyncio
   from unittest.mock import Mock
   from src.database.session import resolve_project_id
   from src.auto_switch.session_context import get_session_context_manager

   async def test():
       mgr = get_session_context_manager()
       await mgr.start()
       ctx = Mock()
       ctx.session_id = 'test'
       await mgr.set_working_directory('test', '/Users/cliffclarke/Claude_Code/codebase-mcp')
       result = await resolve_project_id(explicit_id=None, ctx=ctx)
       print(f'Resolved: {result}')
       await mgr.stop()

   asyncio.run(test())
   "

Report which tests pass/fail and any errors.
```

---

## Project A Testing Prompt

```
Test config-based project tracking with Project A. Execute these commands:

1. Create the test project structure:
   mkdir -p /Users/cliffclarke/Claude_Code/project-a/.codebase-mcp
   mkdir -p /Users/cliffclarke/Claude_Code/project-a/src/components

2. Create config file:
   cat > /Users/cliffclarke/Claude_Code/project-a/.codebase-mcp/config.json <<'EOF'
   {
     "version": "1.0",
     "project": {
       "name": "project-a",
       "id": "proj-a-frontend-2025"
     },
     "auto_switch": true,
     "description": "Project A - Frontend application"
   }
   EOF

3. Test config discovery from subdirectory:
   cd /Users/cliffclarke/Claude_Code/codebase-mcp
   uv run python -c "
   from pathlib import Path
   from src.auto_switch.discovery import find_config_file
   found = find_config_file(Path('/Users/cliffclarke/Claude_Code/project-a/src/components'))
   print(f'Found config: {found}')
   assert 'project-a' in str(found)
   "

4. Test resolution returns correct project ID:
   uv run python -c "
   import asyncio
   from unittest.mock import Mock
   from src.database.session import resolve_project_id
   from src.auto_switch.session_context import get_session_context_manager

   async def test():
       mgr = get_session_context_manager()
       await mgr.start()
       ctx = Mock()
       ctx.session_id = 'proj-a-session'
       await mgr.set_working_directory('proj-a-session', '/Users/cliffclarke/Claude_Code/project-a')
       result = await resolve_project_id(explicit_id=None, ctx=ctx)
       print(f'Resolved to: {result}')
       assert result == 'proj-a-frontend-2025'
       await mgr.stop()

   asyncio.run(test())
   "

Report success/failure and any errors.
```

---

## Project B Testing Prompt

```
Test multi-session isolation with Project B. This tests that sessions stay independent. Execute:

1. Create Project B with name-only config (no ID):
   mkdir -p /Users/cliffclarke/Claude_Code/project-b/src/api/v1/endpoints
   cat > /Users/cliffclarke/Claude_Code/project-b/.codebase-mcp/config.json <<'EOF'
   {
     "version": "1.0",
     "project": {
       "name": "project-b"
     },
     "auto_switch": true,
     "description": "Project B - Backend API"
   }
   EOF

2. Test multi-session isolation (Project A must exist from previous prompt):
   cd /Users/cliffclarke/Claude_Code/codebase-mcp
   uv run python -c "
   import asyncio
   from unittest.mock import Mock
   from src.database.session import resolve_project_id
   from src.auto_switch.session_context import get_session_context_manager

   async def test():
       mgr = get_session_context_manager()
       await mgr.start()

       # Session A with Project A
       ctx_a = Mock()
       ctx_a.session_id = 'session-a'
       await mgr.set_working_directory('session-a', '/Users/cliffclarke/Claude_Code/project-a')

       # Session B with Project B
       ctx_b = Mock()
       ctx_b.session_id = 'session-b'
       await mgr.set_working_directory('session-b', '/Users/cliffclarke/Claude_Code/project-b')

       # Resolve both
       result_a = await resolve_project_id(explicit_id=None, ctx=ctx_a)
       result_b = await resolve_project_id(explicit_id=None, ctx=ctx_b)

       print(f'Session A resolved to: {result_a}')
       print(f'Session B resolved to: {result_b}')

       # Verify isolation
       assert result_a == 'proj-a-frontend-2025', f'Expected proj-a-frontend-2025, got {result_a}'
       assert result_b == 'project-b', f'Expected project-b, got {result_b}'

       print('✓ Session isolation working!')
       await mgr.stop()

   asyncio.run(test())
   "

3. Test nested directory discovery (4 levels deep):
   uv run python -c "
   from pathlib import Path
   from src.auto_switch.discovery import find_config_file
   found = find_config_file(Path('/Users/cliffclarke/Claude_Code/project-b/src/api/v1/endpoints'))
   print(f'Found from 4 levels deep: {found}')
   assert 'project-b' in str(found)
   "

Report results. Both sessions should resolve to different projects independently.
```

---

## Quick Validation Script

To quickly validate both projects are set up correctly, run this:

```python
import asyncio
from pathlib import Path
from unittest.mock import Mock
from src.database.session import resolve_project_id
from src.auto_switch.session_context import get_session_context_manager

async def test_multi_project():
    session_mgr = get_session_context_manager()
    await session_mgr.start()

    # Test Project A
    ctx_a = Mock()
    ctx_a.session_id = "project-a-session"
    await session_mgr.set_working_directory(ctx_a.session_id, "/Users/cliffclarke/Claude_Code/project-a")
    project_a = await resolve_project_id(explicit_id=None, ctx=ctx_a)
    print(f"Project A resolved to: {project_a}")

    # Test Project B
    ctx_b = Mock()
    ctx_b.session_id = "project-b-session"
    await session_mgr.set_working_directory(ctx_b.session_id, "/Users/cliffclarke/Claude_Code/project-b")
    project_b = await resolve_project_id(explicit_id=None, ctx=ctx_b)
    print(f"Project B resolved to: {project_b}")

    # Verify isolation
    project_a_check = await resolve_project_id(explicit_id=None, ctx=ctx_a)
    print(f"Project A still resolves to: {project_a_check}")

    await session_mgr.stop()

    assert project_a == "proj-a-frontend-2025"
    assert project_b == "project-b"
    assert project_a_check == "proj-a-frontend-2025"
    print("✓ Multi-project isolation working correctly!")

asyncio.run(test_multi_project())
```

---

## Expected Results

### All Tests Should Show:

1. **Config Discovery**: <50ms for first lookup, <5ms for cached
2. **Session Isolation**: Projects A and B completely independent
3. **Priority System**: Explicit ID always overrides config
4. **Backward Compatibility**: Tools work with and without project_id
5. **Cache Invalidation**: Automatic on file modification
6. **Upward Traversal**: Finds config up to 20 levels up

### Performance Benchmarks:

- Config validation: <10ms
- Config discovery (first): <50ms
- Config discovery (cached): <5ms
- Session lookup: <1ms
- Full resolution chain: <100ms

If any test fails or performance is significantly worse, investigate and report.
