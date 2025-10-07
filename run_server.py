#!/usr/bin/env python3
"""Wrapper script to prevent dual module loading.

This wrapper solves the double-import issue that occurs when running
`python -m src.mcp.server_fastmcp`:

Problem:
--------
When running `python -m src.mcp.server_fastmcp`, Python loads the module twice:
1. Once as `__main__` (the entry point that runs)
2. Once as `src.mcp.server_fastmcp` (when tools import it)

This creates two separate `mcp` FastMCP instances:
- Tools register on the `__main__.mcp` instance
- Protocol handlers query the `src.mcp.server_fastmcp.mcp` instance
- Result: Claude Desktop sees zero tools despite successful registration

Solution:
---------
This wrapper script loads as `__main__` but imports and runs the server module
by its full path, ensuring only ONE module instance exists:
1. Wrapper runs as `__main__`
2. Imports `src.mcp.server_fastmcp` module (single load)
3. Tools import from the same module instance
4. Single `mcp` instance throughout execution

Usage:
------
Configure Claude Desktop to run this wrapper:
{
  "codebase-mcp": {
    "command": "/path/to/.venv/bin/python",
    "args": ["/path/to/run_server.py"]
  }
}

Constitutional Compliance:
--------------------------
- Principle V: Production Quality (proper module isolation)
- Principle VIII: Type Safety (maintains type safety from main module)
"""

import sys
from pathlib import Path

# Ensure project root is in path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import and run - this ensures single module load as src.mcp.server_fastmcp
from src.mcp.server_fastmcp import main

if __name__ == "__main__":
    main()
