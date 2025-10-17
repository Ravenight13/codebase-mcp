"""Unit tests for IndexingJob models and schemas.

Tests Pydantic validation for IndexingJobCreate and IndexingJobResponse models,
focusing on path security validation and model serialization.

Constitutional Compliance:
- Principle VII: Test-Driven Development (tests validate security)
- Principle VIII: Type Safety (validates Pydantic models)
- Principle V: Production Quality (security validation)

Test Coverage:
- Path validation: absolute paths, relative path rejection
- Security: path traversal detection and prevention
- Model serialization: Create and Response models
- Field validation: empty field rejection
- ORM integration: SQLAlchemy to Pydantic conversion

Security Validation:
- Prevents relative path attacks (must be absolute)
- Prevents path traversal attacks (no ../ sequences)
- Validates all path components for suspicious patterns

Performance Target:
- <1 second for complete test suite
- <50ms per individual test
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from src.models.indexing_job import (
    IndexingJob,
    IndexingJobCreate,
    IndexingJobResponse,
)


# ==============================================================================
# Valid Path Tests
# ==============================================================================


class TestValidPathAcceptance:
    """Test that valid absolute paths are accepted."""

    def test_valid_absolute_path_unix(self) -> None:
        """Test Unix-style absolute paths are accepted."""
        job = IndexingJobCreate(
            repo_path="/tmp/test-repo",
            project_id="test-project",
        )
        assert job.repo_path == "/tmp/test-repo"
        assert job.project_id == "test-project"

    def test_valid_absolute_path_nested(self) -> None:
        """Test deeply nested absolute paths are accepted."""
        job = IndexingJobCreate(
            repo_path="/var/lib/projects/client-a/repo",
            project_id="client-a",
        )
        assert job.repo_path == "/var/lib/projects/client-a/repo"
        assert job.project_id == "client-a"

    def test_valid_absolute_path_home_directory(self) -> None:
        """Test home directory paths are accepted."""
        job = IndexingJobCreate(
            repo_path="/Users/alice/projects/my-repo",
            project_id="my-project",
        )
        assert job.repo_path == "/Users/alice/projects/my-repo"
        assert job.project_id == "my-project"

    def test_valid_absolute_path_with_hyphens(self) -> None:
        """Test paths with hyphens and underscores are accepted."""
        job = IndexingJobCreate(
            repo_path="/opt/my-awesome_project/repo-v2",
            project_id="test-project",
        )
        assert job.repo_path == "/opt/my-awesome_project/repo-v2"


# ==============================================================================
# Relative Path Rejection Tests
# ==============================================================================


class TestRelativePathRejection:
    """Test that relative paths are rejected."""

    def test_relative_path_dot_slash(self) -> None:
        """Test relative paths with ./ prefix are rejected."""
        with pytest.raises(ValueError, match="must be absolute"):
            IndexingJobCreate(
                repo_path="./relative/path",
                project_id="test",
            )

    def test_relative_path_no_leading_slash(self) -> None:
        """Test paths without leading slash are rejected."""
        with pytest.raises(ValueError, match="must be absolute"):
            IndexingJobCreate(
                repo_path="relative/path",
                project_id="test",
            )

    def test_relative_path_single_directory(self) -> None:
        """Test single directory relative path is rejected."""
        with pytest.raises(ValueError, match="must be absolute"):
            IndexingJobCreate(
                repo_path="repo",
                project_id="test",
            )

    def test_relative_path_parent_directory(self) -> None:
        """Test parent directory relative path is rejected."""
        with pytest.raises(ValueError, match="must be absolute"):
            IndexingJobCreate(
                repo_path="../parent",
                project_id="test",
            )


# ==============================================================================
# Path Traversal Detection Tests
# ==============================================================================


class TestPathTraversalDetection:
    """Test that path traversal patterns are detected and rejected."""

    @pytest.mark.parametrize(
        "malicious_path",
        [
            "/var/data/../../etc/passwd",
            "/tmp/../../../etc/shadow",
            "/Users/test/../../../etc/hosts",
            "/home/user/repo/../../../../../../etc/passwd",
            "/opt/app/../../../sensitive/data",
            "/var/www/html/../../../../../../root/.ssh/id_rsa",
        ],
    )
    def test_path_traversal_rejected(self, malicious_path: str) -> None:
        """Test path traversal patterns are rejected.

        Args:
            malicious_path: Path containing traversal sequences
        """
        with pytest.raises(ValueError, match="Path traversal detected"):
            IndexingJobCreate(
                repo_path=malicious_path,
                project_id="test",
            )

    def test_path_traversal_double_dot_in_middle(self) -> None:
        """Test path with .. in middle is rejected."""
        with pytest.raises(ValueError, match="Path traversal detected"):
            IndexingJobCreate(
                repo_path="/var/data/../sensitive",
                project_id="test",
            )

    def test_path_traversal_multiple_sequences(self) -> None:
        """Test path with multiple .. sequences is rejected."""
        with pytest.raises(ValueError, match="Path traversal detected"):
            IndexingJobCreate(
                repo_path="/a/b/../c/../d",
                project_id="test",
            )

    def test_path_traversal_at_start(self) -> None:
        """Test path starting with .. is rejected."""
        # This is also a relative path, caught by absolute check
        with pytest.raises(ValueError, match="must be absolute"):
            IndexingJobCreate(
                repo_path="../etc/passwd",
                project_id="test",
            )


# ==============================================================================
# Model Serialization Tests
# ==============================================================================


class TestModelSerialization:
    """Test Pydantic model serialization and deserialization."""

    def test_indexing_job_create_serialization(self) -> None:
        """Test IndexingJobCreate serializes correctly to dict."""
        job = IndexingJobCreate(
            repo_path="/tmp/test-repo",
            project_id="test-project",
        )

        # Should serialize to dict
        data = job.model_dump()
        assert data["repo_path"] == "/tmp/test-repo"
        assert data["project_id"] == "test-project"
        assert len(data) == 2  # Only two fields

    def test_indexing_job_create_json_serialization(self) -> None:
        """Test IndexingJobCreate serializes to JSON."""
        job = IndexingJobCreate(
            repo_path="/tmp/test-repo",
            project_id="test-project",
        )

        # Should serialize to JSON string
        json_str = job.model_dump_json()
        assert "/tmp/test-repo" in json_str
        assert "test-project" in json_str

    def test_indexing_job_response_from_orm(self) -> None:
        """Test IndexingJobResponse can serialize from SQLAlchemy model."""
        # Create mock SQLAlchemy object
        job = IndexingJob(
            id=uuid.uuid4(),
            repo_path="/tmp/test",
            project_id="test",
            status="pending",
            files_indexed=0,
            chunks_created=0,
            created_at=datetime.utcnow(),
        )

        # Should convert to response model
        response = IndexingJobResponse.model_validate(job)
        assert response.job_id == job.id
        assert response.status == "pending"
        assert response.repo_path == "/tmp/test"
        assert response.project_id == "test"
        assert response.files_indexed == 0
        assert response.chunks_created == 0

    def test_indexing_job_response_with_all_fields(self) -> None:
        """Test IndexingJobResponse with all optional fields populated."""
        now = datetime.utcnow()
        job = IndexingJob(
            id=uuid.uuid4(),
            repo_path="/tmp/test",
            project_id="test",
            status="completed",
            error_message=None,
            files_indexed=150,
            chunks_created=450,
            started_at=now,
            completed_at=now,
            created_at=now,
        )

        response = IndexingJobResponse.model_validate(job)
        assert response.status == "completed"
        assert response.error_message is None
        assert response.files_indexed == 150
        assert response.chunks_created == 450
        assert response.started_at == now
        assert response.completed_at == now

    def test_indexing_job_response_with_error(self) -> None:
        """Test IndexingJobResponse with error message."""
        job = IndexingJob(
            id=uuid.uuid4(),
            repo_path="/tmp/test",
            project_id="test",
            status="failed",
            error_message="Repository not found",
            files_indexed=25,
            chunks_created=0,
            created_at=datetime.utcnow(),
        )

        response = IndexingJobResponse.model_validate(job)
        assert response.status == "failed"
        assert response.error_message == "Repository not found"
        assert response.files_indexed == 25


# ==============================================================================
# Empty Field Validation Tests
# ==============================================================================


class TestEmptyFieldValidation:
    """Test that empty or invalid field values are rejected."""

    def test_empty_repo_path_rejected(self) -> None:
        """Test empty repo_path is rejected by Pydantic min_length."""
        with pytest.raises(ValidationError) as exc_info:
            IndexingJobCreate(
                repo_path="",
                project_id="test",
            )

        # Should fail on min_length constraint
        errors = exc_info.value.errors()
        assert any(
            error["type"] == "string_too_short" and error["loc"] == ("repo_path",)
            for error in errors
        )

    def test_empty_project_id_rejected(self) -> None:
        """Test empty project_id is rejected by Pydantic min_length."""
        with pytest.raises(ValidationError) as exc_info:
            IndexingJobCreate(
                repo_path="/tmp/test",
                project_id="",
            )

        # Should fail on min_length constraint
        errors = exc_info.value.errors()
        assert any(
            error["type"] == "string_too_short" and error["loc"] == ("project_id",)
            for error in errors
        )

    def test_whitespace_only_repo_path_accepted_but_fails_absolute_check(self) -> None:
        """Test whitespace-only repo_path fails absolute path check."""
        with pytest.raises(ValueError, match="must be absolute"):
            IndexingJobCreate(
                repo_path="   ",
                project_id="test",
            )

    def test_missing_repo_path_rejected(self) -> None:
        """Test missing repo_path field is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            # Type ignore because we're intentionally passing invalid data
            IndexingJobCreate(project_id="test")  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(
            error["type"] == "missing" and error["loc"] == ("repo_path",)
            for error in errors
        )

    def test_missing_project_id_rejected(self) -> None:
        """Test missing project_id field is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            # Type ignore because we're intentionally passing invalid data
            IndexingJobCreate(repo_path="/tmp/test")  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(
            error["type"] == "missing" and error["loc"] == ("project_id",)
            for error in errors
        )


# ==============================================================================
# Field Alias Tests (IndexingJobResponse)
# ==============================================================================


class TestResponseFieldAliases:
    """Test field alias functionality in IndexingJobResponse."""

    def test_response_uses_job_id_alias(self) -> None:
        """Test that 'id' field is aliased to 'job_id' in response."""
        job = IndexingJob(
            id=uuid.uuid4(),
            repo_path="/tmp/test",
            project_id="test",
            status="pending",
            files_indexed=0,
            chunks_created=0,
            created_at=datetime.utcnow(),
        )

        response = IndexingJobResponse.model_validate(job)

        # Should have job_id attribute (aliased from id)
        assert hasattr(response, "job_id")
        assert response.job_id == job.id

        # Serialization should use alias
        data = response.model_dump()
        assert "job_id" in data
        assert data["job_id"] == job.id

    def test_response_json_uses_id_field(self) -> None:
        """Test that JSON serialization uses 'id' not 'job_id' when populate_by_name is True."""
        job = IndexingJob(
            id=uuid.uuid4(),
            repo_path="/tmp/test",
            project_id="test",
            status="pending",
            files_indexed=0,
            chunks_created=0,
            created_at=datetime.utcnow(),
        )

        response = IndexingJobResponse.model_validate(job)
        data = response.model_dump(by_alias=True)

        # With by_alias=True, should use 'id' (the alias)
        assert "id" in data


# ==============================================================================
# Edge Case Tests
# ==============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_long_path_accepted(self) -> None:
        """Test very long absolute paths are accepted."""
        long_path = "/very/" + "long/" * 50 + "path"
        job = IndexingJobCreate(
            repo_path=long_path,
            project_id="test",
        )
        assert job.repo_path == long_path

    def test_path_with_special_characters_accepted(self) -> None:
        """Test paths with special characters (except ..) are accepted."""
        job = IndexingJobCreate(
            repo_path="/tmp/test-repo@v1.0_final",
            project_id="test",
        )
        assert job.repo_path == "/tmp/test-repo@v1.0_final"

    def test_project_id_with_valid_characters(self) -> None:
        """Test project_id with various valid characters."""
        job = IndexingJobCreate(
            repo_path="/tmp/test",
            project_id="my-project-123",
        )
        assert job.project_id == "my-project-123"

    def test_from_attributes_config(self) -> None:
        """Test that from_attributes config is properly set."""
        # IndexingJobCreate should have from_attributes=True
        assert IndexingJobCreate.model_config.get("from_attributes") is True

        # IndexingJobResponse should have from_attributes=True
        assert IndexingJobResponse.model_config.get("from_attributes") is True
