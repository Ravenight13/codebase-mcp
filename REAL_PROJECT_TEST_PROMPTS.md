# Real Project Testing Prompts

## Prompt 1: Commission Processing Vendor Extractors

```
Test config-based project tracking with the commission-processing-vendor-extractors project. Execute these commands:

1. Navigate to the codebase-mcp project:
   cd /Users/cliffclarke/Claude_Code/codebase-mcp

2. Create config file for commission-processing project:
   cat > /Users/cliffclarke/Claude_Code/commission-processing-vendor-extractors/.codebase-mcp/config.json <<'EOF'
   {
     "version": "1.0",
     "project": {
       "name": "commission-processing-vendor-extractors",
       "id": "commission-vendor-extractors"
     },
     "auto_switch": true,
     "description": "Commission processing vendor file extraction system"
   }
   EOF

3. Verify the config file was created and is valid:
   uv run python -c "
   from src.auto_switch.validation import validate_config_syntax
   from pathlib import Path
   config = validate_config_syntax(Path('/Users/cliffclarke/Claude_Code/commission-processing-vendor-extractors/.codebase-mcp/config.json'))
   print(f'✓ Config valid')
   print(f'  Project name: {config[\"project\"][\"name\"]}')
   print(f'  Project ID: {config[\"project\"][\"id\"]}')
   "

4. Test the complete workflow - set working directory and resolve project:
   uv run python -c "
   import asyncio
   from unittest.mock import Mock
   from src.database.session import resolve_project_id
   from src.auto_switch.session_context import get_session_context_manager
   from src.mcp.tools.project import set_working_directory

   async def test():
       # Start session manager
       mgr = get_session_context_manager()
       await mgr.start()

       # Create mock context for session
       ctx = Mock()
       ctx.session_id = 'commission-processing-session'

       # Call set_working_directory tool
       result = await set_working_directory.fn(
           directory='/Users/cliffclarke/Claude_Code/commission-processing-vendor-extractors',
           ctx=ctx
       )

       print(f'✓ set_working_directory tool response:')
       print(f'  Session ID: {result[\"session_id\"]}')
       print(f'  Config found: {result[\"config_found\"]}')
       print(f'  Project name: {result[\"project_info\"][\"name\"]}')
       print(f'  Project ID: {result[\"project_info\"][\"id\"]}')

       # Test that resolve_project_id uses the config
       resolved = await resolve_project_id(explicit_id=None, ctx=ctx)
       print(f'\\n✓ Project resolution:')
       print(f'  Resolved to: {resolved}')
       assert resolved == 'commission-vendor-extractors'

       await mgr.stop()
       print('\\n✓ Commission processing project configured successfully!')

   asyncio.run(test())
   "

5. Now test indexing the repository (this will actually index the codebase):
   uv run python -c "
   import asyncio
   from unittest.mock import Mock
   from src.mcp.tools.indexing import index_repository
   from src.auto_switch.session_context import get_session_context_manager

   async def test_indexing():
       mgr = get_session_context_manager()
       await mgr.start()

       ctx = Mock()
       ctx.session_id = 'commission-processing-session'
       ctx.info = Mock(return_value=asyncio.coroutine(lambda x: None)())

       # Set working directory first
       await mgr.set_working_directory(
           ctx.session_id,
           '/Users/cliffclarke/Claude_Code/commission-processing-vendor-extractors'
       )

       print('Indexing commission-processing-vendor-extractors...')
       print('(This may take 30-60 seconds depending on codebase size)')

       # Index WITHOUT explicit project_id - should use config automatically
       result = await index_repository.fn(
           repo_path='/Users/cliffclarke/Claude_Code/commission-processing-vendor-extractors',
           project_id=None,  # Let it resolve from config
           force_reindex=False,
           ctx=ctx
       )

       print(f'\\n✓ Indexing complete:')
       print(f'  Repository ID: {result[\"repository_id\"]}')
       print(f'  Files indexed: {result[\"files_indexed\"]}')
       print(f'  Chunks created: {result[\"chunks_created\"]}')
       print(f'  Duration: {result[\"duration_seconds\"]:.2f}s')
       print(f'  Project ID: {result[\"project_id\"]}')
       print(f'  Schema: {result[\"schema_name\"]}')

       assert result['project_id'] == 'commission-vendor-extractors'
       assert result['schema_name'] == 'project_commission_vendor_extractors'

       await mgr.stop()
       print('\\n✓ Commission processing codebase indexed with auto-switch!')

   asyncio.run(test_indexing())
   "

Report the results. The indexing should use project_id "commission-vendor-extractors" without explicitly passing it.
```

---

## Prompt 2: Workflow MCP Project

```
Test config-based project tracking with the workflow-mcp project. This tests multi-project isolation. Execute these commands:

1. Navigate to the codebase-mcp project:
   cd /Users/cliffclarke/Claude_Code/codebase-mcp

2. Create config file for workflow-mcp project:
   cat > /Users/cliffclarke/Claude_Code/workflow-mcp/.codebase-mcp/config.json <<'EOF'
   {
     "version": "1.0",
     "project": {
       "name": "workflow-mcp",
       "id": "workflow-mcp-server"
     },
     "auto_switch": true,
     "description": "Workflow MCP server for project tracking and work item management"
   }
   EOF

3. Verify the config file was created and is valid:
   uv run python -c "
   from src.auto_switch.validation import validate_config_syntax
   from pathlib import Path
   config = validate_config_syntax(Path('/Users/cliffclarke/Claude_Code/workflow-mcp/.codebase-mcp/config.json'))
   print(f'✓ Config valid')
   print(f'  Project name: {config[\"project\"][\"name\"]}')
   print(f'  Project ID: {config[\"project\"][\"id\"]}')
   "

4. Test multi-session isolation with both projects:
   uv run python -c "
   import asyncio
   from unittest.mock import Mock
   from src.database.session import resolve_project_id
   from src.auto_switch.session_context import get_session_context_manager

   async def test():
       mgr = get_session_context_manager()
       await mgr.start()

       # Session 1: Commission processing
       ctx1 = Mock()
       ctx1.session_id = 'commission-session'
       await mgr.set_working_directory(
           'commission-session',
           '/Users/cliffclarke/Claude_Code/commission-processing-vendor-extractors'
       )

       # Session 2: Workflow MCP
       ctx2 = Mock()
       ctx2.session_id = 'workflow-session'
       await mgr.set_working_directory(
           'workflow-session',
           '/Users/cliffclarke/Claude_Code/workflow-mcp'
       )

       # Resolve both sessions
       result1 = await resolve_project_id(explicit_id=None, ctx=ctx1)
       result2 = await resolve_project_id(explicit_id=None, ctx=ctx2)

       print(f'✓ Multi-session isolation test:')
       print(f'  Session 1 resolved to: {result1}')
       print(f'  Session 2 resolved to: {result2}')

       # Verify they're different
       assert result1 == 'commission-vendor-extractors', f'Expected commission-vendor-extractors, got {result1}'
       assert result2 == 'workflow-mcp-server', f'Expected workflow-mcp-server, got {result2}'

       # Verify session 1 still resolves correctly after session 2 was added
       result1_check = await resolve_project_id(explicit_id=None, ctx=ctx1)
       assert result1_check == 'commission-vendor-extractors'

       print(f'\\n✓ Sessions are completely isolated!')
       await mgr.stop()

   asyncio.run(test())
   "

5. Index the workflow-mcp repository:
   uv run python -c "
   import asyncio
   from unittest.mock import Mock
   from src.mcp.tools.indexing import index_repository
   from src.auto_switch.session_context import get_session_context_manager

   async def test_indexing():
       mgr = get_session_context_manager()
       await mgr.start()

       ctx = Mock()
       ctx.session_id = 'workflow-session'
       ctx.info = Mock(return_value=asyncio.coroutine(lambda x: None)())

       # Set working directory for workflow-mcp
       await mgr.set_working_directory(
           ctx.session_id,
           '/Users/cliffclarke/Claude_Code/workflow-mcp'
       )

       print('Indexing workflow-mcp...')
       print('(This may take 30-60 seconds depending on codebase size)')

       # Index WITHOUT explicit project_id - should use config automatically
       result = await index_repository.fn(
           repo_path='/Users/cliffclarke/Claude_Code/workflow-mcp',
           project_id=None,  # Let it resolve from config
           force_reindex=False,
           ctx=ctx
       )

       print(f'\\n✓ Indexing complete:')
       print(f'  Repository ID: {result[\"repository_id\"]}')
       print(f'  Files indexed: {result[\"files_indexed\"]}')
       print(f'  Chunks created: {result[\"chunks_created\"]}')
       print(f'  Duration: {result[\"duration_seconds\"]:.2f}s')
       print(f'  Project ID: {result[\"project_id\"]}')
       print(f'  Schema: {result[\"schema_name\"]}')

       assert result['project_id'] == 'workflow-mcp-server'
       assert result['schema_name'] == 'project_workflow_mcp_server'

       await mgr.stop()
       print('\\n✓ Workflow-mcp codebase indexed with auto-switch!')

   asyncio.run(test_indexing())
   "

6. Verify both projects are indexed in separate schemas:
   uv run python -c "
   import asyncio
   from src.database.session import get_session

   async def verify():
       # Check commission-processing schema
       async with get_session(project_id='commission-vendor-extractors') as db:
           result = await db.execute('SELECT COUNT(*) FROM repositories')
           count1 = result.scalar()
           print(f'Commission processing schema has {count1} repository')

       # Check workflow-mcp schema
       async with get_session(project_id='workflow-mcp-server') as db:
           result = await db.execute('SELECT COUNT(*) FROM repositories')
           count2 = result.scalar()
           print(f'Workflow MCP schema has {count2} repository')

       print(f'\\n✓ Both projects indexed in separate schemas!')

   asyncio.run(verify())
   "

Report the results. Both projects should be indexed in completely separate database schemas with full isolation.
```

---

## Expected Results

After running both prompts, you should see:

### Commission Processing Project:
- Config file created at `/Users/cliffclarke/Claude_Code/commission-processing-vendor-extractors/.codebase-mcp/config.json`
- Project ID resolves to: `commission-vendor-extractors`
- Schema name: `project_commission_vendor_extractors`
- Repository indexed with X files and Y chunks

### Workflow MCP Project:
- Config file created at `/Users/cliffclarke/Claude_Code/workflow-mcp/.codebase-mcp/config.json`
- Project ID resolves to: `workflow-mcp-server`
- Schema name: `project_workflow_mcp_server`
- Repository indexed with X files and Y chunks

### Session Isolation:
- Two concurrent sessions maintain separate project contexts
- No cross-contamination between projects
- Each session correctly resolves to its own project ID

### Performance:
- Config discovery: <50ms
- Indexing: 30-120 seconds depending on codebase size
- Session resolution: <1ms

Both codebases will be indexed in completely separate PostgreSQL schemas, demonstrating full multi-project isolation!
