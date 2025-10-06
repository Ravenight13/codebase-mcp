"""SQLAlchemy models and Pydantic schemas for the MCP server.

This module exports all database models and their corresponding Pydantic schemas
for use throughout the application.

Model Organization:
- database: Core database infrastructure (Base, engine, sessions)
- repository: Repository entity and schemas
- code_file: CodeFile entity and schemas
- code_chunk: CodeChunk entity with pgvector embeddings and schemas
- task: Task entity and schemas
- task_relations: Task relationship entities (planning, branches, commits, history)
- tracking: Operational tracking entities (changes, embeddings, search analytics)

Constitutional Compliance:
- Principle VIII: Type safety (all models fully typed with mypy --strict)
- Principle V: Production quality (proper indexes, constraints, relationships)
- Principle IV: Performance (HNSW indexes, connection pooling, async operations)
"""

# Database infrastructure
from .database import (
    Base,
    create_engine,
    create_session_factory,
    drop_database,
    get_session,
    init_database,
)

# Repository models and schemas
from .repository import Repository, RepositoryCreate, RepositoryResponse

# CodeFile models and schemas
from .code_file import CodeFile, CodeFileResponse

# CodeChunk models and schemas with pgvector
from .code_chunk import CodeChunk, CodeChunkCreate, CodeChunkResponse

# Task models and schemas
from .task import Task, TaskCreate, TaskResponse, TaskUpdate

# Task relationship models
from .task_relations import (
    TaskBranchLink,
    TaskCommitLink,
    TaskPlanningReference,
    TaskStatusHistory,
)

# Tracking and analytics models
from .tracking import ChangeEvent, EmbeddingMetadata, SearchQuery

# Export all models and schemas
__all__ = [
    # Database infrastructure
    "Base",
    "create_engine",
    "create_session_factory",
    "get_session",
    "init_database",
    "drop_database",
    # Repository
    "Repository",
    "RepositoryCreate",
    "RepositoryResponse",
    # CodeFile
    "CodeFile",
    "CodeFileResponse",
    # CodeChunk
    "CodeChunk",
    "CodeChunkCreate",
    "CodeChunkResponse",
    # Task
    "Task",
    "TaskCreate",
    "TaskUpdate",
    "TaskResponse",
    # Task relationships
    "TaskPlanningReference",
    "TaskBranchLink",
    "TaskCommitLink",
    "TaskStatusHistory",
    # Tracking and analytics
    "ChangeEvent",
    "EmbeddingMetadata",
    "SearchQuery",
]
