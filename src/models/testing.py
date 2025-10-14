"""
Integration test models for cross-server workflow validation.

Constitutional Compliance:
- Principle III: MCP protocol compliance validation
- Principle VIII: Complete type safety with Pydantic v2
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IntegrationTestStep(BaseModel):
    """
    Single step in an integration test workflow.

    Validates HTTP methods, status codes, and test assertions.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "step_number": 1,
                "server": "codebase-mcp",
                "action": "Search for authentication code",
                "api_call": {
                    "method": "POST",
                    "endpoint": "/mcp/search",
                    "payload": {"query": "authentication logic", "limit": 5}
                },
                "expected_response": {
                    "status_code": 200,
                    "results": "list[dict]"
                },
                "assertions": [
                    "status_code == 200",
                    "len(results) > 0"
                ]
            }
        }
    )

    step_number: int = Field(
        ge=1,
        description="Step sequence number (1-indexed)"
    )

    server: Literal["codebase-mcp", "workflow-mcp"] = Field(
        description="Target MCP server for this step"
    )

    action: str = Field(
        min_length=1,
        description="Human-readable action description"
    )

    api_call: dict[str, Any] = Field(
        description="API call details (method, endpoint, payload)"
    )

    expected_response: dict[str, Any] = Field(
        description="Expected response structure with status codes and data"
    )

    assertions: list[str] = Field(
        min_length=1,
        description="List of assertions to validate (Python expressions)"
    )

    @field_validator("api_call")
    @classmethod
    def validate_api_call_structure(cls, v: dict[str, Any]) -> dict[str, Any]:
        """
        Validate api_call contains required fields and valid HTTP method.

        Required fields:
        - method: HTTP method (GET, POST, PUT, PATCH, DELETE)
        - endpoint: API endpoint path
        - payload: Request body (optional for GET)
        """
        if "method" not in v:
            raise ValueError("api_call must contain 'method' field")

        if "endpoint" not in v:
            raise ValueError("api_call must contain 'endpoint' field")

        # Validate HTTP method
        valid_methods = {"GET", "POST", "PUT", "PATCH", "DELETE"}
        method = str(v["method"]).upper()
        if method not in valid_methods:
            raise ValueError(
                f"Invalid HTTP method '{method}'. Must be one of: {valid_methods}"
            )

        # Validate endpoint format
        endpoint = v["endpoint"]
        if not isinstance(endpoint, str) or not endpoint.startswith("/"):
            raise ValueError(f"Endpoint must be a string starting with '/': {endpoint}")

        return v

    @field_validator("expected_response")
    @classmethod
    def validate_expected_response(cls, v: dict[str, Any]) -> dict[str, Any]:
        """
        Validate expected_response contains status_code.

        Required fields:
        - status_code: HTTP status code (100-599)
        """
        if "status_code" not in v:
            raise ValueError("expected_response must contain 'status_code' field")

        # Validate status code range
        status_code = v["status_code"]
        if not isinstance(status_code, int):
            raise ValueError(f"status_code must be an integer: {status_code}")

        if not 100 <= status_code <= 599:
            raise ValueError(
                f"status_code must be in range 100-599: {status_code}"
            )

        return v

    @field_validator("assertions")
    @classmethod
    def validate_assertions_non_empty(cls, v: list[str]) -> list[str]:
        """Validate each assertion is a non-empty string."""
        if not v:
            raise ValueError("assertions must contain at least one assertion")

        for idx, assertion in enumerate(v):
            if not assertion or not assertion.strip():
                raise ValueError(f"Assertion at index {idx} is empty or whitespace")

        return v


class IntegrationTestCase(BaseModel):
    """
    Cross-server workflow test scenario.

    Constitutional Compliance:
    - Principle III: Validates MCP protocol compliance across servers
    - Principle VIII: Type-safe test definitions with Pydantic v2

    Supports multi-step workflows that span codebase-mcp and workflow-mcp
    servers, validating data flow and integration points.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "test_id": "int-test-001",
                "test_name": "Search to Work Item Workflow",
                "test_description": "Validate cross-server workflow from code search to work item creation",
                "required_servers": ["codebase-mcp", "workflow-mcp"],
                "setup_steps": [
                    "Index test repository in codebase-mcp",
                    "Create test project in workflow-mcp"
                ],
                "workflow_steps": [
                    {
                        "step_number": 1,
                        "server": "codebase-mcp",
                        "action": "Search for authentication code",
                        "api_call": {
                            "method": "POST",
                            "endpoint": "/mcp/search",
                            "payload": {"query": "authentication logic", "limit": 5}
                        },
                        "expected_response": {
                            "status_code": 200,
                            "results": "list[dict]"
                        },
                        "assertions": [
                            "status_code == 200",
                            "len(results) > 0"
                        ]
                    },
                    {
                        "step_number": 2,
                        "server": "workflow-mcp",
                        "action": "Create work item with entity reference",
                        "api_call": {
                            "method": "POST",
                            "endpoint": "/mcp/work_items",
                            "payload": {
                                "title": "Fix authentication bug",
                                "entity_references": ["{{results[0].chunk_id}}"]
                            }
                        },
                        "expected_response": {
                            "status_code": 201,
                            "id": "string"
                        },
                        "assertions": [
                            "status_code == 201",
                            "id is not None"
                        ]
                    }
                ],
                "teardown_steps": [
                    "Delete test work item",
                    "Clear indexed repository"
                ],
                "last_run_status": "pass",
                "last_run_timestamp": "2025-10-13T10:30:00Z",
                "last_run_error": None
            }
        }
    )

    # Identification
    test_id: str = Field(
        min_length=1,
        description="Unique test identifier (UUID or test-### format)"
    )

    test_name: str = Field(
        min_length=1,
        max_length=255,
        description="Human-readable test name"
    )

    test_description: str = Field(
        min_length=1,
        description="Detailed test scenario description"
    )

    # Configuration
    required_servers: list[Literal["codebase-mcp", "workflow-mcp"]] = Field(
        min_length=1,
        description="List of MCP servers required for this test"
    )

    # Test Definition
    setup_steps: list[str] = Field(
        default_factory=list,
        description="Setup actions before test execution"
    )

    workflow_steps: list[IntegrationTestStep] = Field(
        min_length=1,
        description="Sequence of workflow steps to execute"
    )

    teardown_steps: list[str] = Field(
        default_factory=list,
        description="Cleanup actions after test execution"
    )

    # Execution Status
    last_run_status: Literal["pass", "fail", "skipped", "not_run"] = Field(
        default="not_run",
        description="Status from last test execution"
    )

    last_run_timestamp: datetime | None = Field(
        default=None,
        description="ISO 8601 timestamp of last test execution"
    )

    last_run_error: str | None = Field(
        default=None,
        description="Error message if last run failed"
    )

    @field_validator("required_servers")
    @classmethod
    def validate_unique_servers(
        cls, v: list[Literal["codebase-mcp", "workflow-mcp"]]
    ) -> list[Literal["codebase-mcp", "workflow-mcp"]]:
        """Validate required_servers contains no duplicates."""
        if len(v) != len(set(v)):
            raise ValueError("required_servers must not contain duplicates")
        return v

    @field_validator("workflow_steps")
    @classmethod
    def validate_workflow_steps_sequence(
        cls, v: list[IntegrationTestStep]
    ) -> list[IntegrationTestStep]:
        """
        Validate workflow_steps have sequential step_numbers.

        Requirements:
        - Step numbers must be sequential (1, 2, 3, ...)
        - No gaps in sequence
        - No duplicate step numbers
        """
        if not v:
            raise ValueError("workflow_steps must contain at least one step")

        # Extract and validate step numbers
        step_numbers = [step.step_number for step in v]

        # Check for duplicates
        if len(step_numbers) != len(set(step_numbers)):
            raise ValueError("workflow_steps must not contain duplicate step_numbers")

        # Check for sequential ordering (must start at 1)
        sorted_steps = sorted(step_numbers)
        expected_sequence = list(range(1, len(v) + 1))

        if sorted_steps != expected_sequence:
            raise ValueError(
                f"workflow_steps must have sequential step_numbers starting at 1. "
                f"Expected: {expected_sequence}, Got: {sorted_steps}"
            )

        return v

    @field_validator("last_run_error")
    @classmethod
    def validate_last_run_error_consistency(
        cls, v: str | None, info: Any
    ) -> str | None:
        """
        Validate last_run_error is set only when last_run_status is 'fail'.

        Requirements:
        - If status is 'fail', error message should be present
        - If status is not 'fail', error message should be None
        """
        # Access other field values through info.data
        if hasattr(info, "data"):
            status = info.data.get("last_run_status")

            if status == "fail" and not v:
                raise ValueError(
                    "last_run_error must be set when last_run_status is 'fail'"
                )

            if status != "fail" and v is not None:
                raise ValueError(
                    f"last_run_error must be None when last_run_status is '{status}'"
                )

        return v
