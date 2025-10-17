from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ProjectConfig(BaseModel):
    """Project configuration within config file."""
    name: str = Field(..., min_length=1, max_length=255)
    id: Optional[str] = Field(None, description="Project UUID (optional)")

class CodebaseMCPConfig(BaseModel):
    """Root configuration for .codebase-mcp/config.json."""
    version: str = Field(..., pattern=r'^\d+\.\d+$')
    project: ProjectConfig
    auto_switch: bool = Field(True, description="Enable automatic project switching")
    strict_mode: bool = Field(False, description="Reject operations if project mismatch")
    dry_run: bool = Field(False, description="Log intended switches without executing")
    description: Optional[str] = Field(None, max_length=1000)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# JSON Schema for validation
CONFIG_SCHEMA = {
    "type": "object",
    "required": ["version", "project"],
    "properties": {
        "version": {"type": "string", "pattern": "^\\d+\\.\\d+$"},
        "project": {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string", "minLength": 1, "maxLength": 255},
                "id": {"type": "string", "format": "uuid"}
            }
        },
        "auto_switch": {"type": "boolean"},
        "strict_mode": {"type": "boolean"},
        "dry_run": {"type": "boolean"},
        "description": {"type": "string", "maxLength": 1000},
        "created_at": {"type": "string", "format": "date-time"},
        "updated_at": {"type": "string", "format": "date-time"}
    }
}
