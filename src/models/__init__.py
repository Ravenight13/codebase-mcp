"""SQLAlchemy models and Pydantic schemas for the MCP server.

This module exports all database models and their corresponding Pydantic schemas
for use throughout the application.

Model Organization:
- database: Core database infrastructure (Base, engine, sessions)
- repository: Repository entity and schemas
- code_file: CodeFile entity and schemas
- code_chunk: CodeChunk entity with pgvector embeddings and schemas
- project_identifier: Validated project identifier for multi-workspace support
- workflow_context: WorkflowIntegrationContext for workflow-mcp integration
- health: Health check response and connection pool statistics models
- metrics: Prometheus-compatible metrics models (counters, histograms)
- performance: Performance benchmark result models
- load_testing: Load test results with error breakdown and resource usage models

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

# Analytics models (non-essential tracking)
from .analytics import ChangeEvent, EmbeddingMetadata

# Project workspace models
from .project_identifier import ProjectIdentifier
from .workspace_config import WorkspaceConfig
from .workflow_context import WorkflowIntegrationContext

# Health check models
from .health import ConnectionPoolStats, HealthCheckResponse

# Metrics models
from .metrics import LatencyHistogram, MetricCounter, MetricHistogram, MetricsResponse

# Performance models
from .performance import PerformanceBenchmarkResult

# Load testing models
from .load_testing import ErrorBreakdown, LoadTestResult, ResourceUsageStats

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
    # Analytics
    "ChangeEvent",
    "EmbeddingMetadata",
    # Project workspace
    "ProjectIdentifier",
    "WorkspaceConfig",
    "WorkflowIntegrationContext",
    # Health check
    "ConnectionPoolStats",
    "HealthCheckResponse",
    # Metrics
    "LatencyHistogram",
    "MetricCounter",
    "MetricHistogram",
    "MetricsResponse",
    # Performance
    "PerformanceBenchmarkResult",
    # Load testing
    "ErrorBreakdown",
    "LoadTestResult",
    "ResourceUsageStats",
]
