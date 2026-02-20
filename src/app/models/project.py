"""Project API schemas."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator

# Hex color: #rgb or #rrggbb
HEX_COLOR_PATTERN = re.compile(r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$")
VIEW_MODES = ("list", "board")
ViewModeLiteral = Literal["list", "board"]


class ProjectCreate(BaseModel):
    """Schema for creating a project."""

    name: str
    description: str = ""
    color: str = "#6366f1"
    icon: str = "folder"
    view_mode: ViewModeLiteral = "list"

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("name must not be empty")
        return v.strip()

    @field_validator("color")
    @classmethod
    def color_hex(cls, v: str) -> str:
        if not HEX_COLOR_PATTERN.fullmatch(v.strip()):
            raise ValueError("color must be a hex color (#rgb or #rrggbb)")
        return v.strip()


class ProjectUpdate(BaseModel):
    """Schema for updating a project (all fields optional)."""

    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    view_mode: Optional[ViewModeLiteral] = None
    is_archived: Optional[bool] = None
    sort_order: Optional[float] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not v.strip():
            raise ValueError("name must not be empty")
        return v.strip()

    @field_validator("color")
    @classmethod
    def color_hex(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not HEX_COLOR_PATTERN.fullmatch(v.strip()):
            raise ValueError("color must be a hex color (#rgb or #rrggbb)")
        return v.strip()


class ProjectResponse(BaseModel):
    """Schema for project response with computed task_count."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    color: str
    icon: str
    view_mode: str
    is_archived: bool
    sort_order: float
    created_at: datetime
    updated_at: datetime
    task_count: int = 0
