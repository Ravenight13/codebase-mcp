# Codebase MCP Server - Setup Guide

Complete installation and configuration guide for the Codebase MCP Server - a production-grade MCP server that indexes code repositories into PostgreSQL with pgvector for semantic search.

## Prerequisites

### Required Software

#### 1. PostgreSQL (via Postgres.app)
- **Download**: https://postgresapp.com/
- **Version**: PostgreSQL 14+ with pgvector extension
- **Purpose**: Vector database for semantic code embeddings

After installation:
1. Open Postgres.app
2. Click "Initialize" to start the server
3. Server will run on `localhost:5432`

#### 2. Python 3.13+
- **Version**: Python 3.13 or higher
- **Package Manager**: `uv` (modern Python package manager)

Install `uv`:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify installation:
```bash
uv --version
python3 --version  # Should show 3.13 or higher
```

#### 3. Ollama (for embeddings)
- **Download**: https://ollama.com/
- **Purpose**: Local embedding generation (no cloud dependencies)

Install and setup:
```bash
# Download from https://ollama.com/ and install

# Start Ollama service
ollama serve

# Pull the embedding model (in a new terminal)
ollama pull nomic-embed-text
```

Verify:
```bash
ollama list
# Should show: nomic-embed-text
```

#### 4. Claude Desktop
- **Download**: https://claude.ai/download
- **Version**: Latest stable release
- **Purpose**: AI assistant interface for MCP tools

---

## Database Setup

### Step 1: Create Database

Using Postgres.app GUI:
1. Open Postgres.app
2. Double-click your server to open `psql`
3. Run:
```sql
CREATE DATABASE codebase_mcp;
\q
```

Or using command line:
```bash
createdb codebase_mcp
```

Verify:
```bash
psql -l | grep codebase_mcp
# Should show: codebase_mcp database
```

### Step 2: Initialize Schema

```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp
psql -d codebase_mcp -f init_tables.sql
```

Expected output:
```
CREATE EXTENSION
CREATE TABLE
CREATE TABLE
CREATE TABLE
...
CREATE INDEX
CREATE INDEX
```

This creates 11 tables:

**Repository & Code Tables:**
- `repositories` - Tracked repositories
- `code_files` - File metadata and change tracking
- `code_chunks` - Semantic code chunks with embeddings

**Task Management Tables:**
- `tasks` - Task definitions and state
- `task_planning_references` - Links to specification artifacts
- `task_branch_links` - Git branch associations
- `task_commit_links` - Git commit tracking
- `task_status_history` - Task state transitions

**Metadata Tables:**
- `change_events` - File change tracking
- `embedding_metadata` - Embedding model tracking
- `file_metadata` - File type and language detection

### Step 3: Verify pgvector Extension

```bash
psql -d codebase_mcp -c "SELECT * FROM pg_extension WHERE extname = 'vector';"
```

Expected output:
```
 oid  | extname | ...
------+---------+-----
 xxxxx | vector  | ...
```

If pgvector is not installed:
```bash
# In Postgres.app, it should be included by default
# If missing, you may need to install manually:
# brew install pgvector (requires Homebrew)
```

---

## Project Configuration

### Step 1: Environment Variables

Create `.env` file in the project root:

```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp
cat > .env << 'EOF'
# Database Configuration
DATABASE_URL=postgresql+asyncpg://cliffclarke@localhost:5432/codebase_mcp

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Database Pool Configuration
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# Logging
LOG_LEVEL=INFO
EOF
```

**Important Configuration Notes:**
- Replace `cliffclarke` with your macOS username (or PostgreSQL username)
- Use `postgresql+asyncpg://` scheme (NOT `postgresql://`)
- Ensure `OLLAMA_BASE_URL` matches your Ollama server port (default: 11434)
- Pool sizes are tuned for concurrent MCP operations

Verify your username:
```bash
whoami
# Use this value in DATABASE_URL
```

### Step 2: Claude Desktop Configuration

Edit Claude Desktop's MCP configuration:

```bash
# Open configuration file
open ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

Replace contents with:

```json
{
  "mcpServers": {
    "codebase-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "anthropic-mcp",
        "python",
        "/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/mcp_stdio_server_v3.py"
      ]
    }
  }
}
```

**Critical Configuration Rules:**
- ✅ Use **absolute paths** (e.g., `/Users/cliffclarke/...`)
- ❌ Do NOT use relative paths (e.g., `~/...` or `./...`)
- ✅ Ensure `uv` is in your PATH
- ✅ Point to `mcp_stdio_server_v3.py` (latest version)

Verify `uv` is accessible:
```bash
which uv
# Should show: /Users/cliffclarke/.local/bin/uv (or similar)
```

---

## Installation

### Install Python Dependencies

```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp
uv sync
```

Expected output:
```
Resolved X packages in X.XXs
Installed X packages in X.XXs
  + anthropic-mcp
  + asyncpg
  + fastapi
  + pydantic
  + sqlalchemy
  + pgvector
  ...
```

This installs all dependencies from `pyproject.toml`:
- **Database**: SQLAlchemy 2.0+, asyncpg, pgvector
- **MCP Framework**: anthropic-mcp SDK
- **API Framework**: FastAPI, Pydantic V2
- **Utilities**: httpx, python-dotenv, tree-sitter

---

## Verification

### Test 1: Database Connection

Create test script:
```bash
cat > test_db_connection.py << 'EOF'
import asyncio
from src.database import get_db_session

async def test_connection():
    async for session in get_db_session():
        print("✅ Database connected successfully")
        return

if __name__ == "__main__":
    asyncio.run(test_connection())
EOF

uv run python test_db_connection.py
```

Expected output:
```
✅ Database connected successfully
```

### Test 2: Task Management

Test the task tools:
```bash
uv run python test_tool_handlers.py
```

Expected output:
```
✅ Database connected
✅ Task created: 123e4567-e89b-12d3-a456-426614174000
✅ Task retrieved: Test Task - Parameter Passing Fix
✅ ALL TESTS PASSED
```

This verifies:
- Database connectivity
- Async session management
- Task CRUD operations
- UUID handling

### Test 3: Repository Indexing & Embeddings

Test the indexing pipeline:
```bash
uv run python test_embeddings.py
```

Expected output:
```
Files indexed: 2
Chunks created: 6
✅ All 6 chunks have embeddings!
Embedding dimensions: 768
Sample chunk: def example_function():
    """Sample function for testing"""
    return "Hello, World!"
```

This verifies:
- File scanning
- Code chunking
- Ollama embedding generation
- Vector storage in PostgreSQL

### Test 4: MCP Server Integration (Claude Desktop)

1. **Restart Claude Desktop** (completely quit and reopen)

2. **Check MCP Server Logs**:
```bash
tail -f ~/Library/Logs/Claude/mcp*.log
```

Look for:
```
[codebase-mcp] Server started
[codebase-mcp] Tools registered: 12
```

3. **Test in Claude Desktop**:

Open Claude Desktop and try these commands:

```
Create a task called "Test MCP Integration" with description "Verify MCP server is working correctly"
```

Expected response:
```
✅ Task created successfully!
- ID: 123e4567-e89b-12d3-a456-426614174000
- Title: Test MCP Integration
- Status: pending
```

```
List all my tasks
```

Expected response:
```
Current tasks:
1. Test MCP Integration (pending)
   Description: Verify MCP server is working correctly
```

4. **Check Developer Tools** (Optional):
```
Cmd + Option + I (macOS)
```

Look in Console for MCP-related messages (should have no errors).

---

## Troubleshooting

### Database Issues

#### "Database connection failed"

**Symptoms:**
```
asyncpg.exceptions.InvalidCatalogNameError: database "codebase_mcp" does not exist
```

**Solutions:**
1. Check Postgres.app is running:
```bash
psql -l
# Should list databases
```

2. Verify database exists:
```bash
psql -l | grep codebase_mcp
# Should show: codebase_mcp
```

3. Create database if missing:
```bash
createdb codebase_mcp
psql -d codebase_mcp -f init_tables.sql
```

4. Check DATABASE_URL in `.env`:
```bash
cat .env | grep DATABASE_URL
# Should match: postgresql+asyncpg://YOUR_USERNAME@localhost:5432/codebase_mcp
```

#### "Timezone warning"

**Symptoms:**
```
SAWarning: Dialect postgresql+asyncpg does *not* support timezone-aware datetimes
```

**Solution:**
This has been fixed in the latest code by using timezone-naive `datetime.now()` instead of `datetime.utcnow()`. Ensure you're using the latest code:

```bash
git pull origin 001-build-a-production
```

If still seeing warnings, re-initialize database:
```bash
psql -d codebase_mcp -f init_tables.sql
```

### Python/Module Issues

#### "No module named 'src'"

**Symptoms:**
```
ModuleNotFoundError: No module named 'src'
```

**Solutions:**
1. Run from project root:
```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp
pwd  # Verify you're in the right directory
```

2. Don't use relative paths in Claude Desktop config:
```json
// ❌ WRONG:
"args": ["run", "python", "~/codebase-mcp/src/mcp/server.py"]

// ✅ CORRECT:
"args": ["run", "python", "/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/mcp_stdio_server_v3.py"]
```

3. Verify Python path:
```bash
uv run python -c "import sys; print('\n'.join(sys.path))"
# Should include current directory
```

### Ollama Issues

#### "Ollama connection refused"

**Symptoms:**
```
httpx.ConnectError: [Errno 61] Connection refused
```

**Solutions:**
1. Start Ollama service:
```bash
ollama serve
# Leave this terminal open
```

2. Verify Ollama is running (in new terminal):
```bash
curl http://localhost:11434/api/tags
# Should return JSON with models
```

3. Check model is installed:
```bash
ollama list
# Should show: nomic-embed-text
```

4. Pull model if missing:
```bash
ollama pull nomic-embed-text
```

5. Verify port in `.env`:
```bash
cat .env | grep OLLAMA_BASE_URL
# Should be: http://localhost:11434
```

### Claude Desktop Issues

#### "MCP server not showing in Claude Desktop"

**Symptoms:**
- No MCP tools available in Claude
- Commands like "Create a task" don't work

**Solutions:**

1. **Check JSON syntax**:
```bash
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json | python -m json.tool
# Should output valid JSON without errors
```

2. **Use absolute paths**:
```json
// ❌ WRONG:
"args": ["run", "python", "~/codebase-mcp/src/mcp/server.py"]

// ✅ CORRECT:
"args": ["run", "python", "/Users/cliffclarke/Claude_Code/codebase-mcp/src/mcp/mcp_stdio_server_v3.py"]
```

3. **Restart Claude Desktop completely**:
```bash
# Quit Claude Desktop
killall Claude

# Wait 3 seconds, then reopen
open /Applications/Claude.app
```

4. **Check MCP logs**:
```bash
tail -f ~/Library/Logs/Claude/mcp*.log
# Look for startup messages or errors
```

5. **Verify uv is in PATH**:
```bash
which uv
# Should show path to uv binary
```

If `uv` not found:
```bash
export PATH="$HOME/.local/bin:$PATH"
# Add to ~/.zshrc or ~/.bash_profile
```

#### "MCP server crashes on startup"

**Symptoms:**
```
[codebase-mcp] Server exited with code 1
```

**Solutions:**

1. Test server manually:
```bash
cd /Users/cliffclarke/Claude_Code/codebase-mcp
uv run python src/mcp/mcp_stdio_server_v3.py
# Should start without errors
```

2. Check for import errors:
```bash
uv run python -c "from src.mcp.mcp_stdio_server_v3 import main"
# Should succeed silently
```

3. Verify dependencies:
```bash
uv sync
```

4. Check database connectivity:
```bash
uv run python test_db_connection.py
```

---

## What's Working

### ✅ Implemented Features

**Task Management:**
- Create tasks with title, description, status
- Read task details by ID
- Update task status (pending → in_progress → completed)
- List all tasks with filtering

**Repository Indexing:**
- Recursive directory scanning
- Binary file filtering (images, archives, executables)
- File content chunking (semantic boundaries)
- Ollama embedding generation (768 dimensions)
- PostgreSQL vector storage with pgvector

**Database Operations:**
- Async connection pooling (20 connections)
- SQLAlchemy 2.0+ with asyncpg driver
- Timezone-aware timestamps
- UUID primary keys
- Full-text search indexes

**MCP Integration:**
- STDIO transport for Claude Desktop
- 12 registered tools
- Request/response logging
- Error handling and validation

### 🚧 Known Limitations

**Not Yet Implemented:**
- Semantic code search (embeddings stored, search API pending)
- Git integration (branch/commit tracking tables ready)
- Task-to-spec linking (schema exists, implementation pending)
- Multi-repository support (single repo tested)
- Search performance tuning (basic indexing works)

---

## Next Steps

After successful setup, try these workflows:

### 1. Test Task Management
```
# In Claude Desktop:
Create a task "Implement semantic search API" with description "Build FastAPI endpoint for vector similarity search"

Update task <uuid> to status "in_progress"

List all tasks
```

### 2. Index a Small Repository
```python
# Create test script
cat > index_repo.py << 'EOF'
import asyncio
from pathlib import Path
from src.services.indexer import CodebaseIndexer

async def index_test_repo():
    indexer = CodebaseIndexer()
    repo_path = Path("/Users/cliffclarke/Claude_Code/codebase-mcp")

    result = await indexer.index_repository(str(repo_path))
    print(f"✅ Indexed {result['files_indexed']} files")
    print(f"✅ Created {result['chunks_created']} chunks")

if __name__ == "__main__":
    asyncio.run(index_test_repo())
EOF

uv run python index_repo.py
```

### 3. Test Semantic Search (when implemented)
```python
# Future workflow (not yet implemented)
async def search_code(query: str):
    searcher = CodeSearcher()
    results = await searcher.search(query, limit=5)

    for result in results:
        print(f"File: {result.file_path}")
        print(f"Similarity: {result.score:.3f}")
        print(f"Chunk:\n{result.content}\n")
```

### 4. Explore Database
```bash
psql -d codebase_mcp

-- View indexed files
SELECT file_path, language, indexed_at FROM code_files LIMIT 10;

-- View chunks
SELECT file_id, chunk_index, LENGTH(content) as size
FROM code_chunks LIMIT 10;

-- View tasks
SELECT task_id, title, status, created_at FROM tasks;

-- Check embedding dimensions
SELECT COUNT(*), vector_dims(embedding)
FROM code_chunks
WHERE embedding IS NOT NULL
GROUP BY vector_dims(embedding);
```

---

## Development Workflow

If you're contributing or extending the server:

### 1. Run Tests
```bash
# Database connectivity
uv run python test_db_connection.py

# Task operations
uv run python test_tool_handlers.py

# Embeddings pipeline
uv run python test_embeddings.py

# Full test suite (when available)
uv run pytest tests/
```

### 2. Code Quality
```bash
# Type checking
uv run mypy src/ --strict

# Linting
uv run ruff check src/

# Formatting
uv run ruff format src/
```

### 3. Database Migrations
```bash
# Reset database (WARNING: deletes all data)
psql -d codebase_mcp -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
psql -d codebase_mcp -f init_tables.sql
```

### 4. Debug Logging
```bash
# Enable verbose logging in .env
LOG_LEVEL=DEBUG

# View logs in real-time
tail -f logs/codebase_mcp.log
```

---

## Support & Resources

**Documentation:**
- Project README: `/Users/cliffclarke/Claude_Code/codebase-mcp/README.md`
- MCP Protocol: https://spec.modelcontextprotocol.io/
- Postgres.app Docs: https://postgresapp.com/documentation/
- Ollama Docs: https://github.com/ollama/ollama/tree/main/docs

**Troubleshooting:**
- Check logs: `~/Library/Logs/Claude/mcp*.log`
- Check database: `psql -d codebase_mcp`
- Check Ollama: `ollama list`

**Common Commands:**
```bash
# Check services
psql -l                          # PostgreSQL databases
ollama list                      # Ollama models
uv run python test_db_connection.py  # Test DB

# Restart services
killall Claude                   # Restart Claude Desktop
ollama serve                     # Start Ollama

# View logs
tail -f ~/Library/Logs/Claude/mcp*.log
```

---

## Quick Reference

### File Locations
```
Project Root:     /Users/cliffclarke/Claude_Code/codebase-mcp/
Database Schema:  init_tables.sql
MCP Server:       src/mcp/mcp_stdio_server_v3.py
Configuration:    .env
Claude Config:    ~/Library/Application Support/Claude/claude_desktop_config.json
Logs:             ~/Library/Logs/Claude/mcp*.log
```

### Service URLs
```
PostgreSQL:  localhost:5432
Ollama:      http://localhost:11434
Database:    codebase_mcp
```

### Key Commands
```bash
# Start services
ollama serve
open /Applications/Postgres.app

# Test server
uv run python test_tool_handlers.py

# Restart Claude
killall Claude && open /Applications/Claude.app

# View logs
tail -f ~/Library/Logs/Claude/mcp*.log
```

---

**Setup Complete!** 🎉

Your Codebase MCP Server is now configured and ready for use. Start with task management in Claude Desktop, then explore repository indexing and semantic search features.
