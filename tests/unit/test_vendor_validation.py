"""Unit tests for vendor validation functions.

Tests validate_vendor_name() and validate_create_vendor_metadata() functions
from src.services.validation module. Covers edge cases, invalid inputs, and
successful validation scenarios.

Constitutional Compliance:
- Principle VII: TDD (comprehensive test coverage before implementation)
- Principle VIII: Type safety (100% type annotations)

Test Coverage:
- T015: Vendor name validation (empty, whitespace, length, character constraints)
- T016: Vendor metadata validation (None, empty, valid/invalid types, ISO 8601)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from src.services.validation import (
    validate_vendor_name,
    validate_create_vendor_metadata,
)


# ==============================================================================
# T015: Test validate_vendor_name()
# ==============================================================================


class TestValidateVendorName:
    """Test suite for validate_vendor_name() function."""

    def test_empty_string_raises_value_error(self) -> None:
        """Test that empty string raises ValueError."""
        with pytest.raises(ValueError, match="Vendor name cannot be empty"):
            validate_vendor_name("")

    def test_whitespace_only_string_raises_value_error(self) -> None:
        """Test that whitespace-only string raises ValueError."""
        with pytest.raises(ValueError, match="Vendor name cannot be empty"):
            validate_vendor_name("   ")

        with pytest.raises(ValueError, match="Vendor name cannot be empty"):
            validate_vendor_name("\t\n")

    def test_name_too_short_raises_value_error(self) -> None:
        """Test that name with 0 characters raises ValueError.

        Note: This is covered by empty string test, but explicitly testing
        the length constraint for completeness.
        """
        with pytest.raises(ValueError, match="Vendor name cannot be empty"):
            validate_vendor_name("")

    def test_name_too_long_raises_value_error(self) -> None:
        """Test that name with 101+ characters raises ValueError."""
        long_name = "A" * 101
        with pytest.raises(
            ValueError, match=r"Vendor name must be 1-100 characters, got 101"
        ):
            validate_vendor_name(long_name)

    def test_name_exactly_100_chars_passes(self) -> None:
        """Test that name with exactly 100 characters passes validation."""
        max_length_name = "A" * 100
        # Should not raise
        validate_vendor_name(max_length_name)

    def test_valid_alphanumeric_characters_pass(self) -> None:
        """Test that alphanumeric characters pass validation."""
        valid_names = [
            "AcmeCorp",
            "Vendor123",
            "ABC",
            "Test1234",
            "vendor",
            "VENDOR",
            "VeNdOr123",
        ]
        for name in valid_names:
            validate_vendor_name(name)  # Should not raise

    def test_valid_spaces_pass(self) -> None:
        """Test that spaces within name pass validation."""
        valid_names = [
            "Acme Corp",
            "Big Vendor Inc",
            "A B C",
            "Vendor 123",
        ]
        for name in valid_names:
            validate_vendor_name(name)  # Should not raise

    def test_valid_hyphens_pass(self) -> None:
        """Test that hyphens within name pass validation."""
        valid_names = [
            "Acme-Corp",
            "Big-Vendor-Inc",
            "A-B-C",
            "Vendor-123",
        ]
        for name in valid_names:
            validate_vendor_name(name)  # Should not raise

    def test_valid_underscores_pass(self) -> None:
        """Test that underscores within name pass validation."""
        valid_names = [
            "Acme_Corp",
            "Big_Vendor_Inc",
            "A_B_C",
            "Vendor_123",
        ]
        for name in valid_names:
            validate_vendor_name(name)  # Should not raise

    def test_mixed_valid_characters_pass(self) -> None:
        """Test that mixed valid characters pass validation."""
        valid_names = [
            "Acme Corp-123",
            "Big_Vendor-Inc 456",
            "A-B_C 789",
            "Test_Vendor-123 XYZ",
        ]
        for name in valid_names:
            validate_vendor_name(name)  # Should not raise

    @pytest.mark.parametrize(
        "invalid_char",
        [
            "@",
            "!",
            "#",
            "$",
            "%",
            "^",
            "&",
            "*",
            "(",
            ")",
            "+",
            "=",
            "[",
            "]",
            "{",
            "}",
            "|",
            "\\",
            ";",
            ":",
            "'",
            '"',
            "<",
            ">",
            ",",
            ".",
            "?",
            "/",
            "~",
            "`",
        ],
    )
    def test_invalid_characters_raise_value_error(self, invalid_char: str) -> None:
        """Test that invalid characters raise ValueError."""
        invalid_name = f"Vendor{invalid_char}Corp"
        with pytest.raises(
            ValueError,
            match="Vendor name must contain only alphanumeric characters, "
            "spaces, hyphens, and underscores",
        ):
            validate_vendor_name(invalid_name)

    def test_unicode_characters_raise_value_error(self) -> None:
        """Test that unicode characters raise ValueError."""
        invalid_names = [
            "Vendör",  # ö
            "Vendør",  # ø
            "Vend🏢r",  # emoji
            "供应商",  # Chinese
            "Продавец",  # Cyrillic
        ]
        for name in invalid_names:
            with pytest.raises(
                ValueError,
                match="Vendor name must contain only alphanumeric characters",
            ):
                validate_vendor_name(name)


# ==============================================================================
# T016: Test validate_create_vendor_metadata()
# ==============================================================================


class TestValidateCreateVendorMetadata:
    """Test suite for validate_create_vendor_metadata() function."""

    def test_none_input_returns_empty_dict(self) -> None:
        """Test that None input returns empty dict."""
        result = validate_create_vendor_metadata(None)
        assert result == {}

    def test_empty_dict_input_returns_empty_dict(self) -> None:
        """Test that empty dict input returns empty dict."""
        result = validate_create_vendor_metadata({})
        assert result == {}

    def test_valid_scaffolder_version_passes_through(self) -> None:
        """Test that valid scaffolder_version string passes through."""
        metadata = {"scaffolder_version": "1.0.0"}
        result = validate_create_vendor_metadata(metadata)
        assert result == {"scaffolder_version": "1.0.0"}

    def test_invalid_scaffolder_version_type_raises_value_error(self) -> None:
        """Test that invalid scaffolder_version type (int) raises ValueError."""
        metadata: dict[str, Any] = {"scaffolder_version": 123}
        with pytest.raises(ValueError, match="scaffolder_version must be string"):
            validate_create_vendor_metadata(metadata)

    def test_invalid_scaffolder_version_none_raises_value_error(self) -> None:
        """Test that scaffolder_version=None raises ValueError."""
        metadata: dict[str, Any] = {"scaffolder_version": None}
        with pytest.raises(ValueError, match="scaffolder_version must be string"):
            validate_create_vendor_metadata(metadata)

    def test_valid_created_at_iso8601_passes_through(self) -> None:
        """Test that valid created_at ISO 8601 string passes through."""
        iso_timestamp = "2025-10-11T12:00:00Z"
        metadata = {"created_at": iso_timestamp}
        result = validate_create_vendor_metadata(metadata)
        assert result == {"created_at": iso_timestamp}

    def test_valid_created_at_with_microseconds_passes(self) -> None:
        """Test that ISO 8601 with microseconds passes validation."""
        iso_timestamp = "2025-10-11T12:00:00.123456Z"
        metadata = {"created_at": iso_timestamp}
        result = validate_create_vendor_metadata(metadata)
        assert result == {"created_at": iso_timestamp}

    def test_valid_created_at_with_timezone_passes(self) -> None:
        """Test that ISO 8601 with timezone offset passes validation."""
        iso_timestamp = "2025-10-11T12:00:00+05:00"
        metadata = {"created_at": iso_timestamp}
        result = validate_create_vendor_metadata(metadata)
        assert result == {"created_at": iso_timestamp}

    def test_invalid_created_at_format_raises_value_error(self) -> None:
        """Test that invalid created_at format raises ValueError."""
        # Note: datetime.fromisoformat() accepts some partial formats like "2025-10-11"
        # We test truly invalid formats that fail ISO 8601 parsing
        invalid_timestamps = [
            "2025/10/11 12:00:00",  # Wrong separator
            "10-11-2025T12:00:00Z",  # Wrong date order
            "not-a-timestamp",  # Invalid string
            "2025-13-01T12:00:00Z",  # Invalid month
            "2025-10-32T12:00:00Z",  # Invalid day
        ]
        for invalid_ts in invalid_timestamps:
            metadata = {"created_at": invalid_ts}
            with pytest.raises(
                ValueError, match="created_at must be valid ISO 8601 format"
            ):
                validate_create_vendor_metadata(metadata)

    def test_invalid_created_at_type_raises_value_error(self) -> None:
        """Test that invalid created_at type raises ValueError."""
        metadata: dict[str, Any] = {"created_at": 1234567890}
        with pytest.raises(ValueError, match="created_at must be ISO 8601 string"):
            validate_create_vendor_metadata(metadata)

    def test_invalid_created_at_none_raises_value_error(self) -> None:
        """Test that created_at=None raises ValueError."""
        metadata: dict[str, Any] = {"created_at": None}
        with pytest.raises(ValueError, match="created_at must be ISO 8601 string"):
            validate_create_vendor_metadata(metadata)

    def test_unknown_fields_pass_through_without_validation(self) -> None:
        """Test that unknown fields pass through without validation."""
        metadata = {
            "custom_field": "value",
            "another_field": 123,
            "nested_field": {"key": "value"},
        }
        result = validate_create_vendor_metadata(metadata)
        assert result == metadata

    def test_mixed_known_and_unknown_fields(self) -> None:
        """Test that mixed known and unknown fields are handled correctly."""
        metadata = {
            "scaffolder_version": "2.0.0",
            "created_at": "2025-10-11T15:30:00Z",
            "custom_field": "custom_value",
            "another_field": 456,
        }
        result = validate_create_vendor_metadata(metadata)
        assert result == metadata

    def test_known_fields_validated_unknown_fields_ignored(self) -> None:
        """Test that known fields are validated while unknown fields ignored."""
        metadata: dict[str, Any] = {
            "scaffolder_version": 123,  # Invalid - should raise
            "custom_field": "anything",  # Unknown - should be ignored
        }
        with pytest.raises(ValueError, match="scaffolder_version must be string"):
            validate_create_vendor_metadata(metadata)

    def test_partial_known_fields_validation(self) -> None:
        """Test validation with only some known fields present."""
        # Only scaffolder_version
        result1 = validate_create_vendor_metadata({"scaffolder_version": "1.0.0"})
        assert result1 == {"scaffolder_version": "1.0.0"}

        # Only created_at
        result2 = validate_create_vendor_metadata(
            {"created_at": "2025-10-11T12:00:00Z"}
        )
        assert result2 == {"created_at": "2025-10-11T12:00:00Z"}

    def test_empty_string_values_for_known_fields(self) -> None:
        """Test that empty strings for known fields are handled appropriately."""
        # Empty scaffolder_version should pass (string validation only checks type)
        result1 = validate_create_vendor_metadata({"scaffolder_version": ""})
        assert result1 == {"scaffolder_version": ""}

        # Empty created_at should fail ISO 8601 validation
        metadata = {"created_at": ""}
        with pytest.raises(
            ValueError, match="created_at must be valid ISO 8601 format"
        ):
            validate_create_vendor_metadata(metadata)

    def test_complex_metadata_structure(self) -> None:
        """Test validation with complex nested metadata structure."""
        metadata = {
            "scaffolder_version": "3.1.4",
            "created_at": "2025-10-11T18:45:30.123456Z",
            "extractor_config": {
                "parser": "tabula",
                "ocr_enabled": False,
                "settings": {"precision": 2, "mode": "lattice"},
            },
            "vendor_info": {
                "contact": "support@vendor.com",
                "docs_url": "https://docs.vendor.com",
            },
            "tags": ["financial", "insurance", "commission"],
            "priority": 1,
        }
        result = validate_create_vendor_metadata(metadata)
        assert result == metadata


# ==============================================================================
# Edge Cases and Integration Tests
# ==============================================================================


class TestVendorValidationEdgeCases:
    """Edge case tests for vendor validation functions."""

    def test_vendor_name_single_character(self) -> None:
        """Test that single character name is valid."""
        validate_vendor_name("A")  # Should not raise

    def test_vendor_name_boundary_99_chars(self) -> None:
        """Test name with 99 characters (just under limit)."""
        name_99 = "A" * 99
        validate_vendor_name(name_99)  # Should not raise

    def test_metadata_all_known_fields_valid(self) -> None:
        """Test metadata with all known fields valid."""
        metadata = {
            "scaffolder_version": "1.2.3",
            "created_at": "2025-10-11T12:00:00Z",
        }
        result = validate_create_vendor_metadata(metadata)
        assert result == metadata

    def test_metadata_processes_all_fields(self) -> None:
        """Test that all fields are included in result."""
        metadata = {
            "z_field": "last",
            "a_field": "first",
            "scaffolder_version": "1.0.0",
        }
        result = validate_create_vendor_metadata(metadata)
        # All fields should be present (order may vary due to validation logic)
        assert set(result.keys()) == {"z_field", "a_field", "scaffolder_version"}
        assert result["z_field"] == "last"
        assert result["a_field"] == "first"
        assert result["scaffolder_version"] == "1.0.0"
