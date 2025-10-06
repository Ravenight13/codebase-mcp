"""
Unit tests for settings configuration module.

Tests cover:
- Valid configuration loading from environment variables
- Required field validation
- Field type coercion and constraints
- Database URL asyncpg driver validation
- Custom validators for URLs and ranges
- Singleton pattern behavior
- Error messages for common misconfigurations

Constitutional Compliance:
- Principle V: Production quality with comprehensive test coverage
- Principle VIII: Type safety validation (mypy --strict)
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from pydantic import ValidationError

from src.config.settings import LogLevel, Settings, get_settings


class TestSettingsValidation:
    """Test settings validation and field constraints."""

    def test_valid_minimal_configuration(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test settings load with minimal valid configuration."""
        # Set required environment variable
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql+asyncpg://user:password@localhost:5432/test_db",
        )

        settings = Settings()

        # Required field should be set
        assert str(settings.database_url).startswith("postgresql+asyncpg://")

        # Optional fields should have defaults
        assert settings.ollama_base_url == "http://localhost:11434"
        assert settings.ollama_embedding_model == "nomic-embed-text"
        assert settings.embedding_batch_size == 50
        assert settings.max_concurrent_requests == 10
        assert settings.db_pool_size == 20
        assert settings.db_max_overflow == 10
        assert settings.log_level == LogLevel.INFO
        assert settings.log_file == "/tmp/codebase-mcp.log"

    def test_valid_full_configuration(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test settings load with all fields customized."""
        # Set all environment variables
        env_vars = {
            "DATABASE_URL": "postgresql+asyncpg://custom:pass@db.example.com:5432/prod_db",
            "OLLAMA_BASE_URL": "http://ollama.example.com:11434",
            "OLLAMA_EMBEDDING_MODEL": "custom-model",
            "EMBEDDING_BATCH_SIZE": "100",
            "MAX_CONCURRENT_REQUESTS": "50",
            "DB_POOL_SIZE": "30",
            "DB_MAX_OVERFLOW": "15",
            "LOG_LEVEL": "DEBUG",
            "LOG_FILE": "/var/log/codebase-mcp.log",
        }
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)

        settings = Settings()

        # Verify all values loaded correctly
        assert "postgresql+asyncpg://custom:pass@db.example.com" in str(
            settings.database_url
        )
        assert str(settings.ollama_base_url) == "http://ollama.example.com:11434/"
        assert settings.ollama_embedding_model == "custom-model"
        assert settings.embedding_batch_size == 100
        assert settings.max_concurrent_requests == 50
        assert settings.db_pool_size == 30
        assert settings.db_max_overflow == 15
        assert settings.log_level == LogLevel.DEBUG
        assert settings.log_file == "/var/log/codebase-mcp.log"

    def test_missing_required_database_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test validation fails when required DATABASE_URL is missing."""
        # Ensure DATABASE_URL is not set
        monkeypatch.delenv("DATABASE_URL", raising=False)

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        # Verify error message mentions the required field
        error = exc_info.value
        assert "database_url" in str(error).lower()
        assert "field required" in str(error).lower()

    def test_invalid_database_url_driver(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test validation fails when DATABASE_URL uses wrong driver."""
        # Use psycopg2 instead of asyncpg
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql+psycopg2://user:password@localhost:5432/test_db",
        )

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        # Verify error message explains asyncpg requirement
        error_msg = str(exc_info.value)
        assert "asyncpg" in error_msg.lower()
        assert "driver" in error_msg.lower()

    def test_invalid_database_url_sync_driver(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test validation fails when DATABASE_URL uses sync PostgreSQL driver."""
        # Use standard postgresql:// scheme (sync driver)
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql://user:password@localhost:5432/test_db",
        )

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        # Verify error message explains asyncpg requirement
        error_msg = str(exc_info.value)
        assert "asyncpg" in error_msg.lower()

    def test_invalid_ollama_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test validation fails for malformed Ollama URL."""
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql+asyncpg://user:password@localhost:5432/test_db",
        )
        monkeypatch.setenv("OLLAMA_BASE_URL", "not-a-valid-url")

        with pytest.raises(ValidationError) as exc_info:
            Settings()

        # Verify error mentions URL validation
        error_msg = str(exc_info.value)
        assert "ollama_base_url" in error_msg.lower()

    def test_embedding_batch_size_constraints(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test embedding_batch_size respects min/max constraints."""
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql+asyncpg://user:password@localhost:5432/test_db",
        )

        # Test minimum boundary (below range)
        monkeypatch.setenv("EMBEDDING_BATCH_SIZE", "0")
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        assert "embedding_batch_size" in str(exc_info.value).lower()

        # Test maximum boundary (above range)
        monkeypatch.setenv("EMBEDDING_BATCH_SIZE", "1001")
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        assert "embedding_batch_size" in str(exc_info.value).lower()

        # Test valid boundary values
        monkeypatch.setenv("EMBEDDING_BATCH_SIZE", "1")
        settings_min = Settings()
        assert settings_min.embedding_batch_size == 1

        monkeypatch.setenv("EMBEDDING_BATCH_SIZE", "1000")
        settings_max = Settings()
        assert settings_max.embedding_batch_size == 1000

    def test_max_concurrent_requests_constraints(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test max_concurrent_requests respects min/max constraints."""
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql+asyncpg://user:password@localhost:5432/test_db",
        )

        # Test below minimum
        monkeypatch.setenv("MAX_CONCURRENT_REQUESTS", "0")
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        assert "max_concurrent_requests" in str(exc_info.value).lower()

        # Test above maximum
        monkeypatch.setenv("MAX_CONCURRENT_REQUESTS", "101")
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        assert "max_concurrent_requests" in str(exc_info.value).lower()

        # Test valid range
        monkeypatch.setenv("MAX_CONCURRENT_REQUESTS", "50")
        settings = Settings()
        assert settings.max_concurrent_requests == 50

    def test_db_pool_size_constraints(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test db_pool_size respects min/max constraints."""
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql+asyncpg://user:password@localhost:5432/test_db",
        )

        # Test below minimum
        monkeypatch.setenv("DB_POOL_SIZE", "4")
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        assert "db_pool_size" in str(exc_info.value).lower()

        # Test above maximum
        monkeypatch.setenv("DB_POOL_SIZE", "51")
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        assert "db_pool_size" in str(exc_info.value).lower()

        # Test valid range
        monkeypatch.setenv("DB_POOL_SIZE", "25")
        settings = Settings()
        assert settings.db_pool_size == 25

    def test_db_max_overflow_constraints(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test db_max_overflow respects min/max constraints."""
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql+asyncpg://user:password@localhost:5432/test_db",
        )

        # Test below minimum (negative not allowed)
        monkeypatch.setenv("DB_MAX_OVERFLOW", "-1")
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        assert "db_max_overflow" in str(exc_info.value).lower()

        # Test above maximum
        monkeypatch.setenv("DB_MAX_OVERFLOW", "21")
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        assert "db_max_overflow" in str(exc_info.value).lower()

        # Test valid range
        monkeypatch.setenv("DB_MAX_OVERFLOW", "5")
        settings = Settings()
        assert settings.db_max_overflow == 5

    def test_log_level_enum_validation(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test log_level accepts valid enum values and rejects invalid ones."""
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql+asyncpg://user:password@localhost:5432/test_db",
        )

        # Test invalid log level
        monkeypatch.setenv("LOG_LEVEL", "INVALID")
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        assert "log_level" in str(exc_info.value).lower()

        # Test all valid log levels
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            monkeypatch.setenv("LOG_LEVEL", level)
            settings = Settings()
            assert settings.log_level == LogLevel[level]

    def test_case_insensitive_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test environment variables are case-insensitive."""
        # Use lowercase env vars
        monkeypatch.setenv(
            "database_url",
            "postgresql+asyncpg://user:password@localhost:5432/test_db",
        )
        monkeypatch.setenv("log_level", "debug")

        settings = Settings()

        # Should parse successfully despite lowercase
        assert str(settings.database_url).startswith("postgresql+asyncpg://")
        assert settings.log_level == LogLevel.DEBUG

    def test_type_coercion(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test automatic type coercion from string env vars."""
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql+asyncpg://user:password@localhost:5432/test_db",
        )
        monkeypatch.setenv("EMBEDDING_BATCH_SIZE", "75")  # String representation
        monkeypatch.setenv("DB_POOL_SIZE", "15")

        settings = Settings()

        # Should coerce strings to integers
        assert isinstance(settings.embedding_batch_size, int)
        assert settings.embedding_batch_size == 75
        assert isinstance(settings.db_pool_size, int)
        assert settings.db_pool_size == 15

    def test_extra_env_vars_forbidden(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that extra/unknown environment variables cause validation error."""
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql+asyncpg://user:password@localhost:5432/test_db",
        )
        monkeypatch.setenv("UNKNOWN_CONFIG_VALUE", "should_fail")

        # This will fail due to extra='forbid' in model_config
        with pytest.raises(ValidationError) as exc_info:
            Settings()

        error_msg = str(exc_info.value)
        assert "extra" in error_msg.lower() or "forbidden" in error_msg.lower()


class TestSingletonPattern:
    """Test settings singleton instance behavior."""

    def test_get_settings_returns_same_instance(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test get_settings() returns singleton instance."""
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql+asyncpg://user:password@localhost:5432/test_db",
        )

        # Reset singleton for test isolation by setting the module-level variable
        import src.config.settings as settings_module

        # Access private variable for test isolation only
        settings_module._settings_instance = None  # pyright: ignore[reportPrivateUsage]

        # Get settings multiple times
        settings1 = get_settings()
        settings2 = get_settings()

        # Should be same instance
        assert settings1 is settings2

    def test_module_level_settings_export(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test module-level settings export is available."""
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql+asyncpg://user:password@localhost:5432/test_db",
        )

        # Import module-level settings
        from src.config.settings import settings

        # Should be Settings instance
        assert isinstance(settings, Settings)
        assert str(settings.database_url).startswith("postgresql+asyncpg://")


class TestPerformanceWarnings:
    """Test performance-related warnings and validations."""

    def test_small_batch_size_warning(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test warning is issued for very small embedding batch sizes."""
        monkeypatch.setenv(
            "DATABASE_URL",
            "postgresql+asyncpg://user:password@localhost:5432/test_db",
        )
        monkeypatch.setenv("EMBEDDING_BATCH_SIZE", "5")

        # Should emit warning but still succeed
        with pytest.warns(UserWarning, match="EMBEDDING_BATCH_SIZE.*performance"):
            settings = Settings()
            assert settings.embedding_batch_size == 5


class TestEnvFileSupport:
    """Test .env file loading support."""

    def test_env_file_configuration(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Any
    ) -> None:
        """Test settings can load from .env file."""
        # Create temporary .env file
        env_file = tmp_path / ".env"
        env_file.write_text(
            "DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/test_db\n"
            "LOG_LEVEL=WARNING\n"
        )

        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        settings = Settings()

        # Should load from .env file
        assert str(settings.database_url).startswith("postgresql+asyncpg://test:test@")
        assert settings.log_level == LogLevel.WARNING


# ============================================================================
# Test Markers
# ============================================================================

pytestmark = pytest.mark.unit
