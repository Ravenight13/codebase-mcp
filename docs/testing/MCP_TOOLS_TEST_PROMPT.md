# MCP Tools Test Prompt

Copy this prompt into a new chat window to test config-based project tracking using ONLY MCP tools:

---

## Test Prompt

```
Test the config-based project tracking feature using MCP tools. Both projects have config files already created at:
- /Users/cliffclarke/Claude_Code/commission-processing-vendor-extractors/.codebase-mcp/config.json (project ID: commission-vendor-extractors)
- /Users/cliffclarke/Claude_Code/workflow-mcp/.codebase-mcp/config.json (project ID: workflow-mcp-server)

Execute these MCP tool calls in order:

1. Set working directory for commission-processing project:
   Call the set_working_directory tool with:
   - directory: /Users/cliffclarke/Claude_Code/commission-processing-vendor-extractors

   Verify the response shows:
   - config_found: true
   - project_info.id: commission-vendor-extractors

2. Index the commission-processing repository WITHOUT specifying project_id:
   Call the index_repository tool with:
   - repo_path: /Users/cliffclarke/Claude_Code/commission-processing-vendor-extractors
   - project_id: (do NOT provide this - let it auto-resolve)

   Verify the response shows:
   - project_id: commission-vendor-extractors
   - schema_name: project_commission_vendor_extractors

3. Set working directory for workflow-mcp project:
   Call the set_working_directory tool with:
   - directory: /Users/cliffclarke/Claude_Code/workflow-mcp

   Verify the response shows:
   - config_found: true
   - project_info.id: workflow-mcp-server

4. Index the workflow-mcp repository WITHOUT specifying project_id:
   Call the index_repository tool with:
   - repo_path: /Users/cliffclarke/Claude_Code/workflow-mcp
   - project_id: (do NOT provide this - let it auto-resolve)

   Verify the response shows:
   - project_id: workflow-mcp-server
   - schema_name: project_workflow_mcp_server

5. Test search isolation - search in commission-processing context:
   Call the search_code tool with:
   - query: vendor extractor
   - project_id: (do NOT provide this - let it auto-resolve)

   This should search in the commission-processing codebase.

6. Test search isolation - search in workflow-mcp context:
   Call the search_code tool with:
   - query: work item
   - project_id: (do NOT provide this - let it auto-resolve)

   This should search in the workflow-mcp codebase.

Report:
- Did set_working_directory find the config files?
- Did index_repository auto-resolve to the correct project IDs?
- Are the two projects in separate schemas (project_commission_vendor_extractors vs project_workflow_mcp_server)?
- Did searches stay isolated to their respective projects?

This demonstrates that projects auto-switch based on the working directory without needing explicit project_id parameters.
```
