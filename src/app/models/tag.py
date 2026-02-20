"""Tag API schemas."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

# Hex color: #rgb or #rrggbb
HEX_COLOR_PATTERN = re.compile(r"^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$")


class TagBase(BaseModel):
    """Shared tag fields."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    color: str

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


class TagCreate(TagBase):
    """Schema for creating a tag."""


class TagUpdate(BaseModel):
    """Schema for updating a tag (all fields optional)."""

    name: Optional[str] = None
    color: Optional[str] = None

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


class TagRead(TagBase):
    """Schema for reading a tag (response)."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# Alias for use in TaskResponse and other nested responses
TagResponse = TagRead
