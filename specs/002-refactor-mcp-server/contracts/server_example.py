"""Complete FastMCP server initialization example.

This example demonstrates how to register all 6 MCP tools using FastMCP decorators
with the stdio transport for Claude Desktop integration.

Features:
- FastMCP framework initialization
- All 6 tools registered with @mcp.tool decorator
- Automatic schema generation from Pydantic models
- Context injection for logging
- Dual logging pattern (Context + file)
- Stdio transport (default)
- Startup validation

Constitutional Compliance:
- Principle III: Protocol Compliance (stdio transport, no stdout/stderr pollution)
- Principle V: Production Quality (startup validation, error handling)
- Principle VIII: Type Safety (full type hints, mypy --strict)
"""

import logging
import sys
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastmcp import FastMCP
from fastmcp.context import Context
from fastmcp.exceptions import FastMCPError, ValidationError
from pydantic import BaseModel, Field

# ==============================================================================
# Configure File Logging (separate from MCP protocol)
# ==============================================================================

logging.basicConfig(
    filename='/tmp/codebase-mcp.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==============================================================================
# Initialize FastMCP Server
# ==============================================================================

mcp = FastMCP("codebase-mcp")

# ==============================================================================
# Pydantic Models
# ==============================================================================

# Search Tool Models
class SearchCodeRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Natural language search query")
    repository_id: str | None = Field(None, description="Optional UUID string to filter by repository")
    file_type: str | None = Field(None, description="Optional file extension filter (e.g., 'py', 'js')")
    directory: str | None = Field(None, description="Optional directory path filter (supports wildcards)")
    limit: int = Field(10, ge=1, le=50, description="Maximum number of results")

class SearchResultItem(BaseModel):
    chunk_id: str
    file_path: str
    content: str
    start_line: int = Field(..., ge=1)
    end_line: int = Field(..., ge=1)
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    context_before: str = ""
    context_after: str = ""

class SearchCodeResponse(BaseModel):
    results: list[SearchResultItem] = Field(default_factory=list)
    total_count: int = Field(..., ge=0)
    latency_ms: int = Field(..., ge=0)

# Indexing Tool Models
class IndexRepositoryRequest(BaseModel):
    repo_path: str = Field(..., description="Absolute path to repository directory")
    force_reindex: bool = Field(False, description="Force full re-index even if already indexed")

class IndexRepositoryResponse(BaseModel):
    repository_id: str
    files_indexed: int = Field(..., ge=0)
    chunks_created: int = Field(..., ge=0)
    duration_seconds: float = Field(..., ge=0)
    status: Literal["success", "partial", "failed"]
    errors: list[str] = Field(default_factory=list)

# Task Tool Models
class CreateTaskRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    notes: str | None = None
    planning_references: list[str] = Field(default_factory=list)

class GetTaskRequest(BaseModel):
    task_id: str = Field(..., description="UUID string of the task")

class ListTasksRequest(BaseModel):
    status: Literal["need to be done", "in-progress", "complete"] | None = None
    branch: str | None = None
    limit: int = Field(20, ge=1, le=100)

class UpdateTaskRequest(BaseModel):
    task_id: str
    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    notes: str | None = None
    status: Literal["need to be done", "in-progress", "complete"] | None = None
    branch: str | None = None
    commit: str | None = Field(None, pattern="^[a-f0-9]{40}$")

class TaskResponse(BaseModel):
    id: str
    title: str
    description: str | None
    notes: str | None
    status: Literal["need to be done", "in-progress", "complete"]
    created_at: str
    updated_at: str
    planning_references: list[str] = Field(default_factory=list)
    branches: list[str] = Field(default_factory=list)
    commits: list[str] = Field(default_factory=list)

class ListTasksResponse(BaseModel):
    tasks: list[TaskResponse] = Field(default_factory=list)
    total_count: int = Field(..., ge=0)

# ==============================================================================
# Database Session (Placeholder - replace with actual implementation)
# ==============================================================================

async def get_db_session():
    """Get async database session (placeholder)."""
    # TODO: Replace with actual AsyncSession from SQLAlchemy
    class MockSession:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    return MockSession()

# ==============================================================================
# Service Functions (Placeholders - replace with actual implementations)
# ==============================================================================

async def search_code_service(query: str, db, repository_id, file_type, directory, limit):
    """Placeholder for search service."""
    return []

async def index_repository_service(repo_path, name, db, force_reindex, progress_callback):
    """Placeholder for indexing service."""
    class MockResult:
        repository_id = UUID("123e4567-e89b-12d3-a456-426614174000")
        files_indexed = 0
        chunks_created = 0
        duration_seconds = 0.0
        status = "success"
        errors = []
    return MockResult()

async def create_task_service(db, request):
    """Placeholder for create task service."""
    class MockTask:
        id = UUID("550e8400-e29b-41d4-a716-446655440000")
        title = request.title
        description = request.description
        notes = request.notes
        status = "need to be done"
        created_at = None  # Should be datetime
        updated_at = None  # Should be datetime
        planning_references = []
        branch_links = []
        commit_links = []
    return MockTask()

async def get_task_service(db, task_id):
    """Placeholder for get task service."""
    return None  # TODO: Implement

async def list_tasks_service(db, status, branch, limit):
    """Placeholder for list tasks service."""
    return []

async def update_task_service(db, task_id, title, description, notes, status, branch, commit):
    """Placeholder for update task service."""
    return None  # TODO: Implement

# ==============================================================================
# Tool Handlers
# ==============================================================================

@mcp.tool
async def search_code(request: SearchCodeRequest, ctx: Context) -> SearchCodeResponse:
    """Search codebase using semantic similarity.

    Performs semantic code search across indexed repositories using embeddings
    and pgvector similarity matching. Supports filtering by repository, file type,
    and directory.

    Performance target: <500ms p95 latency
    """
    # Context logging (to MCP client)
    await ctx.info(f"Searching for: {request.query[:100]}")

    # File logging (to /tmp/codebase-mcp.log)
    logger.info(f"search_code called", extra={
        "query": request.query[:100],
        "repository_id": request.repository_id,
        "limit": request.limit
    })

    # Validate repository_id format if provided
    repo_uuid: UUID | None = None
    if request.repository_id:
        try:
            repo_uuid = UUID(request.repository_id)
        except ValueError:
            raise ValueError(f"Invalid repository_id format: {request.repository_id}")

    # Get database session
    async with get_db_session() as db:
        # Perform search
        results = await search_code_service(
            query=request.query,
            db=db,
            repository_id=repo_uuid,
            file_type=request.file_type,
            directory=request.directory,
            limit=request.limit
        )

        # Format response
        return SearchCodeResponse(
            results=[
                SearchResultItem(
                    chunk_id=str(r.chunk_id),
                    file_path=r.file_path,
                    content=r.content,
                    start_line=r.start_line,
                    end_line=r.end_line,
                    similarity_score=r.similarity_score,
                    context_before=r.context_before or "",
                    context_after=r.context_after or ""
                )
                for r in results
            ],
            total_count=len(results),
            latency_ms=0  # TODO: Calculate actual latency
        )


@mcp.tool
async def index_repository(request: IndexRepositoryRequest, ctx: Context) -> IndexRepositoryResponse:
    """Index a code repository for semantic search.

    Orchestrates the complete repository indexing workflow: scanning,
    chunking, embedding generation, and storage in PostgreSQL with pgvector.

    Performance target: <60 seconds for 10,000 files
    """
    # Context logging
    await ctx.info(f"Indexing repository: {request.repo_path}")

    # File logging
    logger.info(f"index_repository called", extra={
        "repo_path": request.repo_path,
        "force_reindex": request.force_reindex
    })

    # Validate path
    path_obj = Path(request.repo_path)
    if not path_obj.is_absolute():
        raise ValueError(f"Repository path must be absolute: {request.repo_path}")
    if not path_obj.exists():
        raise ValueError(f"Repository path does not exist: {request.repo_path}")
    if not path_obj.is_dir():
        raise ValueError(f"Repository path must be a directory: {request.repo_path}")

    # Get database session
    async with get_db_session() as db:
        # Perform indexing
        result = await index_repository_service(
            repo_path=path_obj,
            name=path_obj.name,
            db=db,
            force_reindex=request.force_reindex,
            progress_callback=lambda msg: ctx.info(msg)
        )

        # Format response
        return IndexRepositoryResponse(
            repository_id=str(result.repository_id),
            files_indexed=result.files_indexed,
            chunks_created=result.chunks_created,
            duration_seconds=result.duration_seconds,
            status=result.status,
            errors=result.errors
        )


@mcp.tool
async def create_task(request: CreateTaskRequest, ctx: Context) -> TaskResponse:
    """Create a new development task.

    Creates a task with 'need to be done' status and optional planning
    references. Supports git integration for tracking implementation
    progress across branches and commits.

    Performance target: <150ms p95 latency
    """
    # Context logging
    await ctx.info(f"Creating task: {request.title[:50]}")

    # File logging
    logger.info(f"create_task called", extra={
        "title": request.title[:100],
        "planning_refs": len(request.planning_references)
    })

    # Get database session
    async with get_db_session() as db:
        # Create task
        task = await create_task_service(db, request)

        # Format response
        return TaskResponse(
            id=str(task.id),
            title=task.title,
            description=task.description,
            notes=task.notes,
            status=task.status,
            created_at="2025-10-06T10:30:00Z",  # TODO: Use actual timestamp
            updated_at="2025-10-06T10:30:00Z",  # TODO: Use actual timestamp
            planning_references=request.planning_references,
            branches=[],
            commits=[]
        )


@mcp.tool
async def get_task(request: GetTaskRequest, ctx: Context) -> TaskResponse:
    """Retrieve a development task by ID.

    Fetches task data including all associated planning references,
    git branches, and commits.

    Performance target: <100ms p95 latency
    """
    # Context logging
    await ctx.info(f"Fetching task: {request.task_id}")

    # File logging
    logger.info(f"get_task called", extra={"task_id": request.task_id})

    # Validate UUID format
    try:
        task_uuid = UUID(request.task_id)
    except ValueError:
        raise ValueError(f"Invalid task_id format: {request.task_id}")

    # Get database session
    async with get_db_session() as db:
        # Retrieve task
        task = await get_task_service(db, task_uuid)

        if not task:
            raise ValueError(f"Task not found: {request.task_id}")

        # Format response
        return TaskResponse(
            id=str(task.id),
            title=task.title,
            description=task.description,
            notes=task.notes,
            status=task.status,
            created_at="2025-10-06T10:30:00Z",  # TODO: Use actual timestamp
            updated_at="2025-10-06T10:30:00Z",  # TODO: Use actual timestamp
            planning_references=[ref.file_path for ref in task.planning_references],
            branches=[link.branch_name for link in task.branch_links],
            commits=[link.commit_hash for link in task.commit_links]
        )


@mcp.tool
async def list_tasks(request: ListTasksRequest, ctx: Context) -> ListTasksResponse:
    """List development tasks with optional filters.

    Supports filtering by status (need to be done, in-progress, complete)
    and git branch name. Results are ordered by updated_at descending.

    Performance target: <200ms p95 latency
    """
    # Context logging
    await ctx.info(f"Listing tasks (status={request.status}, branch={request.branch})")

    # File logging
    logger.info(f"list_tasks called", extra={
        "status": request.status,
        "branch": request.branch,
        "limit": request.limit
    })

    # Get database session
    async with get_db_session() as db:
        # List tasks
        tasks = await list_tasks_service(
            db=db,
            status=request.status,
            branch=request.branch,
            limit=request.limit
        )

        # Format response
        return ListTasksResponse(
            tasks=[
                TaskResponse(
                    id=str(task.id),
                    title=task.title,
                    description=task.description,
                    notes=task.notes,
                    status=task.status,
                    created_at="2025-10-06T10:30:00Z",  # TODO: Use actual timestamp
                    updated_at="2025-10-06T10:30:00Z",  # TODO: Use actual timestamp
                    planning_references=[ref.file_path for ref in task.planning_references],
                    branches=[link.branch_name for link in task.branch_links],
                    commits=[link.commit_hash for link in task.commit_links]
                )
                for task in tasks
            ],
            total_count=len(tasks)
        )


@mcp.tool
async def update_task(request: UpdateTaskRequest, ctx: Context) -> TaskResponse:
    """Update an existing development task.

    Supports partial updates (only provided fields are updated).
    Can associate tasks with git branches and commits for traceability.

    Performance target: <150ms p95 latency
    """
    # Context logging
    await ctx.info(f"Updating task: {request.task_id}")

    # File logging
    logger.info(f"update_task called", extra={
        "task_id": request.task_id,
        "status": request.status,
        "branch": request.branch,
        "commit": request.commit
    })

    # Validate UUID format
    try:
        task_uuid = UUID(request.task_id)
    except ValueError:
        raise ValueError(f"Invalid task_id format: {request.task_id}")

    # Get database session
    async with get_db_session() as db:
        # Update task
        task = await update_task_service(
            db=db,
            task_id=task_uuid,
            title=request.title,
            description=request.description,
            notes=request.notes,
            status=request.status,
            branch=request.branch,
            commit=request.commit
        )

        if not task:
            raise ValueError(f"Task not found: {request.task_id}")

        # Format response
        return TaskResponse(
            id=str(task.id),
            title=task.title,
            description=task.description,
            notes=task.notes,
            status=task.status,
            created_at="2025-10-06T10:30:00Z",  # TODO: Use actual timestamp
            updated_at="2025-10-06T10:30:00Z",  # TODO: Use actual timestamp
            planning_references=[ref.file_path for ref in task.planning_references],
            branches=[link.branch_name for link in task.branch_links],
            commits=[link.commit_hash for link in task.commit_links]
        )


# ==============================================================================
# Startup Validation
# ==============================================================================

def validate_server_startup(mcp_server: FastMCP) -> None:
    """Validate all registered components before starting server.

    Constitutional Compliance:
    - Principle V: Production Quality (fail-fast validation)

    Raises:
        ValidationError: If any tools/resources fail validation
    """
    # Check all tools are registered
    tools = mcp_server.list_tools()
    if not tools:
        raise ValidationError("No tools registered")

    expected_tools = {
        "search_code",
        "index_repository",
        "create_task",
        "get_task",
        "list_tasks",
        "update_task"
    }
    registered_tools = {tool.name for tool in tools}

    if registered_tools != expected_tools:
        missing = expected_tools - registered_tools
        extra = registered_tools - expected_tools
        raise ValidationError(
            f"Tool registration mismatch. Missing: {missing}, Extra: {extra}"
        )

    # Validate tool schemas
    for tool in tools:
        if not tool.input_schema:
            raise ValidationError(f"Tool {tool.name} missing input schema")

    logger.info(f"Server startup validation passed: {len(tools)} tools registered")


# ==============================================================================
# Main Entry Point
# ==============================================================================

if __name__ == "__main__":
    try:
        # Validate server configuration before starting
        validate_server_startup(mcp)

        logger.info("Starting FastMCP server with stdio transport")

        # Start server with stdio transport (default)
        # This is compatible with Claude Desktop out-of-the-box
        mcp.run()

    except FastMCPError as e:
        logger.critical(f"Server startup failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Unexpected error during startup: {e}", exc_info=True)
        sys.exit(1)
