"""Tag API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TagBase(BaseModel):
    """Shared tag fields."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    color: str


class TagCreate(TagBase):
    """Schema for creating a tag."""


class TagUpdate(BaseModel):
    """Schema for updating a tag (all fields optional)."""

    name: Optional[str] = None
    color: Optional[str] = None


class TagRead(TagBase):
    """Schema for reading a tag (response)."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
