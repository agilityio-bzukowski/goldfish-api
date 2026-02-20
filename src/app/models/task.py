"""Task API schemas."""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.db.schema import PriorityLevel


# Re-export / minimal schemas for nested responses (avoid circular imports)
class TagResponse(BaseModel):
    """Minimal tag for nesting in task response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    color: str
    created_at: datetime
    updated_at: datetime


class ReminderCreate(BaseModel):
    """Schema for creating a reminder."""

    remind_at: str  # ISO datetime
    type: str = "absolute"
    relative_minutes: Optional[int] = None


class ReminderResponse(BaseModel):
    """Schema for reminder in task response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    remind_at: datetime
    type: str
    relative_minutes: Optional[int] = None
    is_fired: bool
    created_at: datetime
    updated_at: datetime


DUE_TIME_PATTERN = re.compile(r"^([01]?\d|2[0-3]):[0-5]\d(:[0-5]\d)?$")


class TaskCreate(BaseModel):
    """Schema for creating a task."""

    title: str
    notes: str = ""
    priority: PriorityLevel = PriorityLevel.NONE
    due_date: Optional[date] = None
    due_time: Optional[str] = None
    project_id: Optional[uuid.UUID] = None
    tag_ids: list[uuid.UUID] = []

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("title must not be empty")
        return v.strip()

    @field_validator("due_time")
    @classmethod
    def due_time_format(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        if not DUE_TIME_PATTERN.fullmatch(v.strip()):
            raise ValueError("due_time must be HH:MM or HH:MM:SS")
        return v.strip()


class TaskUpdate(BaseModel):
    """Schema for updating a task (all fields optional)."""

    title: Optional[str] = None
    notes: Optional[str] = None
    priority: Optional[PriorityLevel] = None
    due_date: Optional[date] = None
    due_time: Optional[str] = None
    project_id: Optional[uuid.UUID] = None
    sort_order: Optional[float] = None
    tag_ids: Optional[list[uuid.UUID]] = None

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if not v.strip():
            raise ValueError("title must not be empty")
        return v.strip()

    @field_validator("due_time")
    @classmethod
    def due_time_format(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        if not DUE_TIME_PATTERN.fullmatch(v.strip()):
            raise ValueError("due_time must be HH:MM or HH:MM:SS")
        return v.strip()


class TaskReorderItem(BaseModel):
    """Single item for reorder body."""

    id: uuid.UUID
    sort_order: float


class TaskReorder(BaseModel):
    """Schema for reorder request."""

    items: list[TaskReorderItem]

    @model_validator(mode="after")
    def items_not_empty(self) -> "TaskReorder":
        if not self.items:
            raise ValueError("items must not be empty")
        return self


class TaskResponse(BaseModel):
    """Schema for task response with nested tags and reminders."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    notes: str
    notes_plain: Optional[str] = None
    is_completed: bool
    completed_at: Optional[datetime] = None
    priority: int
    due_date: Optional[date] = None
    due_time: Optional[str] = None
    start_date: Optional[date] = None
    project_id: Optional[uuid.UUID] = None
    sort_order: float
    created_at: datetime
    updated_at: datetime
    tags: list[TagResponse] = []
    reminders: list[ReminderResponse] = []

    @field_validator("tags", "reminders", mode="before")
    @classmethod
    def coerce_none_to_list(cls, v: Any) -> list:
        if v is None:
            return []
        return v


class BulkCompleteResponse(BaseModel):
    """Response for bulk-complete endpoint."""

    completed: int
