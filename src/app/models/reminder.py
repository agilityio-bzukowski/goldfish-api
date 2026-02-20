"""Task API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# Re-export / minimal schemas for nested responses (avoid circular imports)
class ReminderResponse(BaseModel):
    """Schema for reminder response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    remind_at: datetime
    type: str
    relative_minutes: Optional[int] = None
    is_fired: bool
    created_at: datetime
    updated_at: datetime


class ReminderCreateInput(BaseModel):
    """Schema for creating a reminder (request body)."""

    task_id: uuid.UUID
    remind_at: datetime


class ReminderCreate(BaseModel):
    """Schema for reminder in task response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    remind_at: datetime
    type: str
    relative_minutes: Optional[int] = None
    is_fired: Optional[bool] = False
    created_at: datetime
    updated_at: datetime


class ReminderUpdate(BaseModel):
    """Schema for updating a reminder."""

    model_config = ConfigDict(from_attributes=True)

    remind_at: Optional[datetime] = None
    type: Optional[str] = None
    relative_minutes: Optional[int] = None
    is_fired: Optional[bool] = None


class ReminderDelete(BaseModel):
    """Schema for deleting a reminder."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID


class ReminderFire(BaseModel):
    """Schema for firing a reminder."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
