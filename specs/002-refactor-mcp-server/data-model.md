# Data Model: FastMCP Tool Handler Signatures

This document defines the FastMCP tool handler signatures for all 6 MCP tools in the Codebase MCP Server. Each tool uses FastMCP's `@mcp.tool()` decorator with automatic schema generation from type hints and Pydantic models.

## Design Principles

1. **Automatic Schema Generation**: FastMCP infers MCP schemas from function signatures and Pydantic models
2. **Type Safety**: Full type hints for mypy --strict compliance
3. **Context Injection**: FastMCP's `Context` object provides logging, sampling, and resource access
4. **Pydantic Validation**: Input/output models provide field-level validation
5. **Async Support**: All handlers use async def for database and embedding operations
6. **Dual Logging**: Context logging for MCP clients + Python logging for file persistence

## Tool Signatures

### 1. search_code

**Purpose**: Semantic code search using pgvector similarity matching

**Function Signature**:
```python
from fastmcp import FastMCP
from fastmcp.context import Context
from pydantic import BaseModel, Field
from typing import Literal

mcp = FastMCP("codebase-mcp")

# Input Model
class SearchCodeRequest(BaseModel):
    """Search code using semantic similarity."""
    query: str = Field(..., min_length=1, max_length=500, description="Natural language search query")
    repository_id: str | None = Field(None, description="Optional UUID string to filter by repository")
    file_type: str | None = Field(None, description="Optional file extension filter (e.g., 'py', 'js')")
    directory: str | None = Field(None, description="Optional directory path filter (supports wildcards)")
    limit: int = Field(10, ge=1, le=50, description="Maximum number of results")

# Output Model
class SearchResultItem(BaseModel):
    """Single search result item."""
    chunk_id: str = Field(..., description="UUID of the code chunk")
    file_path: str = Field(..., description="Relative path to the file")
    content: str = Field(..., description="Code snippet content")
    start_line: int = Field(..., ge=1, description="Starting line number")
    end_line: int = Field(..., ge=1, description="Ending line number")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score (0.0-1.0)")
    context_before: str = Field("", description="Lines before the chunk")
    context_after: str = Field("", description="Lines after the chunk")

class SearchCodeResponse(BaseModel):
    """Search results with metadata."""
    results: list[SearchResultItem] = Field(default_factory=list, description="Search results")
    total_count: int = Field(..., ge=0, description="Total number of results")
    latency_ms: int = Field(..., ge=0, description="Search latency in milliseconds")

# Tool Handler
@mcp.tool
async def search_code(request: SearchCodeRequest, ctx: Context) -> SearchCodeResponse:
    """Search codebase using semantic similarity.

    Performs semantic code search across indexed repositories using embeddings
    and pgvector similarity matching. Supports filtering by repository, file type,
    and directory.

    Performance target: <500ms p95 latency
    """
    import logging
    from uuid import UUID
    from sqlalchemy.ext.asyncio import AsyncSession

    logger = logging.getLogger(__name__)

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
        except ValueError as e:
            raise ValueError(f"Invalid repository_id format: {request.repository_id}")

    # Get database session (from dependency injection)
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
            latency_ms=calculate_latency()
        )
```

**Context Injection Pattern**:
- `ctx: Context` parameter provides MCP client logging
- `await ctx.info()`, `await ctx.error()` send logs to client
- Separate Python `logging` module for file persistence

**Pydantic Validation**:
- `query`: 1-500 characters
- `limit`: 1-50 range
- `repository_id`: Optional UUID string
- `file_type`: No leading dot validation

---

### 2. index_repository

**Purpose**: Index a code repository for semantic search

**Function Signature**:
```python
# Input Model
class IndexRepositoryRequest(BaseModel):
    """Index a code repository."""
    repo_path: str = Field(..., description="Absolute path to repository directory")
    force_reindex: bool = Field(False, description="Force full re-index even if already indexed")

# Output Model
class IndexRepositoryResponse(BaseModel):
    """Indexing results with metadata."""
    repository_id: str = Field(..., description="UUID of the indexed repository")
    files_indexed: int = Field(..., ge=0, description="Number of files indexed")
    chunks_created: int = Field(..., ge=0, description="Number of code chunks created")
    duration_seconds: float = Field(..., ge=0, description="Indexing duration in seconds")
    status: Literal["success", "partial", "failed"] = Field(..., description="Indexing status")
    errors: list[str] = Field(default_factory=list, description="Error messages if any")

# Tool Handler
@mcp.tool
async def index_repository(request: IndexRepositoryRequest, ctx: Context) -> IndexRepositoryResponse:
    """Index a code repository for semantic search.

    Orchestrates the complete repository indexing workflow: scanning,
    chunking, embedding generation, and storage in PostgreSQL with pgvector.

    Performance target: <60 seconds for 10,000 files
    """
    import logging
    from pathlib import Path

    logger = logging.getLogger(__name__)

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
            progress_callback=lambda msg: ctx.info(msg)  # Real-time progress updates
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
```

**Context Injection Pattern**:
- Progress updates via `ctx.info()` during indexing
- Real-time feedback to MCP client
- File logging for debugging and auditing

**Pydantic Validation**:
- `repo_path`: Absolute path validation
- `force_reindex`: Boolean flag
- Path existence checks in handler logic

---

### 3. create_task

**Purpose**: Create a new development task

**Function Signature**:
```python
# Input Model
class CreateTaskRequest(BaseModel):
    """Create a new development task."""
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: str | None = Field(None, description="Detailed task description")
    notes: str | None = Field(None, description="Additional notes or context")
    planning_references: list[str] = Field(
        default_factory=list,
        description="Relative paths to planning documents"
    )

# Output Model (shared with get_task and update_task)
class TaskResponse(BaseModel):
    """Task data with metadata."""
    id: str = Field(..., description="UUID of the task")
    title: str = Field(..., description="Task title")
    description: str | None = Field(None, description="Task description")
    notes: str | None = Field(None, description="Task notes")
    status: Literal["need to be done", "in-progress", "complete"] = Field(
        ..., description="Task status"
    )
    created_at: str = Field(..., description="ISO 8601 timestamp")
    updated_at: str = Field(..., description="ISO 8601 timestamp")
    planning_references: list[str] = Field(
        default_factory=list,
        description="Planning document file paths"
    )
    branches: list[str] = Field(
        default_factory=list,
        description="Associated git branches"
    )
    commits: list[str] = Field(
        default_factory=list,
        description="Associated git commit hashes"
    )

# Tool Handler
@mcp.tool
async def create_task(request: CreateTaskRequest, ctx: Context) -> TaskResponse:
    """Create a new development task.

    Creates a task with 'need to be done' status and optional planning
    references. Supports git integration for tracking implementation
    progress across branches and commits.

    Performance target: <150ms p95 latency
    """
    import logging

    logger = logging.getLogger(__name__)

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
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
            planning_references=request.planning_references,
            branches=[],
            commits=[]
        )
```

**Context Injection Pattern**:
- Task creation notifications to client
- File logging for audit trail

**Pydantic Validation**:
- `title`: 1-200 characters (required)
- `description`, `notes`: Optional text fields
- `planning_references`: List of file paths

---

### 4. get_task

**Purpose**: Retrieve a task by ID

**Function Signature**:
```python
# Input Model
class GetTaskRequest(BaseModel):
    """Retrieve a task by ID."""
    task_id: str = Field(..., description="UUID string of the task")

# Tool Handler
@mcp.tool
async def get_task(request: GetTaskRequest, ctx: Context) -> TaskResponse:
    """Retrieve a development task by ID.

    Fetches task data including all associated planning references,
    git branches, and commits.

    Performance target: <100ms p95 latency
    """
    import logging
    from uuid import UUID

    logger = logging.getLogger(__name__)

    # Context logging
    await ctx.info(f"Fetching task: {request.task_id}")

    # File logging
    logger.info(f"get_task called", extra={"task_id": request.task_id})

    # Validate UUID format
    try:
        task_uuid = UUID(request.task_id)
    except ValueError as e:
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
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
            planning_references=[ref.file_path for ref in task.planning_references],
            branches=[link.branch_name for link in task.branch_links],
            commits=[link.commit_hash for link in task.commit_links]
        )
```

**Context Injection Pattern**:
- Fetch notifications to client
- Error reporting via `ctx.error()`

**Pydantic Validation**:
- `task_id`: UUID string format
- Runtime validation for existence

---

### 5. list_tasks

**Purpose**: List tasks with optional filters

**Function Signature**:
```python
# Input Model
class ListTasksRequest(BaseModel):
    """List tasks with filters."""
    status: Literal["need to be done", "in-progress", "complete"] | None = Field(
        None,
        description="Filter by task status"
    )
    branch: str | None = Field(None, description="Filter by git branch name")
    limit: int = Field(20, ge=1, le=100, description="Maximum number of results")

# Output Model
class ListTasksResponse(BaseModel):
    """List of tasks with metadata."""
    tasks: list[TaskResponse] = Field(default_factory=list, description="Task list")
    total_count: int = Field(..., ge=0, description="Total number of tasks")

# Tool Handler
@mcp.tool
async def list_tasks(request: ListTasksRequest, ctx: Context) -> ListTasksResponse:
    """List development tasks with optional filters.

    Supports filtering by status (need to be done, in-progress, complete)
    and git branch name. Results are ordered by updated_at descending.

    Performance target: <200ms p95 latency
    """
    import logging

    logger = logging.getLogger(__name__)

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
                    created_at=task.created_at.isoformat(),
                    updated_at=task.updated_at.isoformat(),
                    planning_references=[ref.file_path for ref in task.planning_references],
                    branches=[link.branch_name for link in task.branch_links],
                    commits=[link.commit_hash for link in task.commit_links]
                )
                for task in tasks
            ],
            total_count=len(tasks)
        )
```

**Context Injection Pattern**:
- List operation notifications
- Filter logging for debugging

**Pydantic Validation**:
- `status`: Literal type for valid statuses
- `limit`: 1-100 range
- `branch`: Optional string

---

### 6. update_task

**Purpose**: Update an existing task

**Function Signature**:
```python
# Input Model
class UpdateTaskRequest(BaseModel):
    """Update an existing task."""
    task_id: str = Field(..., description="UUID string of the task")
    title: str | None = Field(None, min_length=1, max_length=200, description="New title")
    description: str | None = Field(None, description="New description")
    notes: str | None = Field(None, description="New notes")
    status: Literal["need to be done", "in-progress", "complete"] | None = Field(
        None,
        description="New status"
    )
    branch: str | None = Field(None, description="Git branch name to associate")
    commit: str | None = Field(
        None,
        pattern="^[a-f0-9]{40}$",
        description="Git commit hash (40-char hex)"
    )

# Tool Handler
@mcp.tool
async def update_task(request: UpdateTaskRequest, ctx: Context) -> TaskResponse:
    """Update an existing development task.

    Supports partial updates (only provided fields are updated).
    Can associate tasks with git branches and commits for traceability.

    Performance target: <150ms p95 latency
    """
    import logging
    from uuid import UUID

    logger = logging.getLogger(__name__)

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
    except ValueError as e:
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
            created_at=task.created_at.isoformat(),
            updated_at=task.updated_at.isoformat(),
            planning_references=[ref.file_path for ref in task.planning_references],
            branches=[link.branch_name for link in task.branch_links],
            commits=[link.commit_hash for link in task.commit_links]
        )
```

**Context Injection Pattern**:
- Update notifications with field details
- Error reporting for validation failures

**Pydantic Validation**:
- `task_id`: UUID string format
- `title`: 1-200 characters if provided
- `status`: Literal type validation
- `commit`: 40-character hex pattern

---

## Shared Patterns

### Context Injection

All tools follow this pattern:
```python
@mcp.tool
async def tool_name(request: RequestModel, ctx: Context) -> ResponseModel:
    # Context logging (to MCP client)
    await ctx.info("Operation started")
    await ctx.error("Error occurred") if error

    # File logging (to /tmp/codebase-mcp.log)
    logger.info("Operation details", extra={...})
    logger.error("Error details", extra={...})
```

### Database Session Management

All tools use async context manager:
```python
async with get_db_session() as db:
    # Perform database operations
    result = await service_function(db, ...)
```

### Error Handling

FastMCP automatically handles:
- `ValueError`: Converted to MCP validation errors
- `ValidationError` (Pydantic): Field-level error messages
- `Exception`: Generic error responses

Custom errors:
```python
# Validation errors
raise ValueError(f"Invalid parameter: {details}")

# Not found errors
if not entity:
    raise ValueError(f"Entity not found: {id}")
```

### Type Hints

All functions use full type hints for mypy --strict:
```python
async def tool_name(
    request: RequestModel,  # Pydantic model
    ctx: Context           # FastMCP context
) -> ResponseModel:        # Pydantic model
    ...
```

### Docstrings

FastMCP uses docstrings for automatic schema descriptions:
```python
@mcp.tool
async def search_code(...) -> ...:
    """Search codebase using semantic similarity.

    Performs semantic code search across indexed repositories using embeddings
    and pgvector similarity matching. Supports filtering by repository, file type,
    and directory.

    Performance target: <500ms p95 latency
    """
```

## Pydantic Model Compatibility

All existing Pydantic models are compatible with FastMCP:
- `TaskResponse` (from `/Users/cliffclarke/Claude_Code/codebase-mcp/src/models/task.py`)
- `CodeChunkResponse` (from `/Users/cliffclarke/Claude_Code/codebase-mcp/src/models/code_chunk.py`)
- `RepositoryResponse` (from `/Users/cliffclarke/Claude_Code/codebase-mcp/src/models/repository.py`)

No changes needed - FastMCP automatically generates MCP schemas from these models.

## Constitutional Compliance

- **Principle III (Protocol Compliance)**: Context logging uses MCP protocol, no stdout/stderr pollution
- **Principle IV (Performance)**: All handlers maintain performance targets (60s indexing, 500ms search)
- **Principle V (Production Quality)**: Comprehensive validation, error handling, logging
- **Principle VIII (Type Safety)**: Full type hints for mypy --strict compliance
- **Principle X (Git Micro-Commits)**: Task tools support branch/commit tracking
