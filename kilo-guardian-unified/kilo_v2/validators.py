"""Input validators for Kilo Guardian API endpoints using Pydantic."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, validator


class ChatRequest(BaseModel):
    """Validated chat request."""

    query: str = Field(
        ..., min_length=1, max_length=10000, description="User query to process"
    )
    session_id: Optional[str] = Field(None, max_length=100)

    @validator("query")
    def query_no_control_chars(cls, v):
        """Remove/reject control characters that might cause issues."""
        if any(ord(c) < 32 and c not in "\n\t\r" for c in v):
            raise ValueError("Query contains invalid control characters")
        return v.strip()


class ToolExecuteRequest(BaseModel):
    """Validated tool execution request."""

    tool: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Tool/plugin name",
    )
    action: str = Field("submit", max_length=50)
    data: Dict[str, Any] = Field(default_factory=dict)

    @validator("data")
    def validate_data_size(cls, v):
        """Prevent excessively large data payloads."""
        if len(v) > 50:
            raise ValueError("Data dictionary too large (max 50 fields)")
        return v


class PluginRestartRequest(BaseModel):
    """Validated plugin restart request."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Plugin name to restart",
    )


class SettingsUpdateRequest(BaseModel):
    """Validated settings update request."""

    setting: str = Field(
        ..., max_length=100, pattern=r"^[a-zA-Z0-9_.]+$", description="Setting key"
    )
    value: Any = Field(..., description="Setting value")


class VPNRequest(BaseModel):
    """Validated VPN operation request."""

    action: str = Field(
        ...,
        max_length=50,
        pattern=r"^[a-zA-Z_]+$",
        description="VPN action (start, stop, status, etc)",
    )
    config: Optional[Dict[str, Any]] = None
