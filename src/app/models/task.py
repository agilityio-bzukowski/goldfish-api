"""Task API schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, field_validator


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


class TaskCreate(BaseModel):
    """Schema for creating a task."""

    title: str
    notes: str = ""
    priority: int = 0
    due_date: Optional[str] = None
    due_time: Optional[str] = None
    project_id: Optional[uuid.UUID] = None
    parent_task_id: Optional[uuid.UUID] = None
    tag_ids: list[uuid.UUID] = []


class TaskUpdate(BaseModel):
    """Schema for updating a task (all fields optional)."""

    title: Optional[str] = None
    notes: Optional[str] = None
    priority: Optional[int] = None
    due_date: Optional[str] = None
    due_time: Optional[str] = None
    project_id: Optional[uuid.UUID] = None
    parent_task_id: Optional[uuid.UUID] = None
    sort_order: Optional[float] = None
    tag_ids: Optional[list[uuid.UUID]] = None


class TaskReorderItem(BaseModel):
    """Single item for reorder body."""

    id: uuid.UUID
    sort_order: float


class TaskReorder(BaseModel):
    """Schema for reorder request."""

    items: list[TaskReorderItem]


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
