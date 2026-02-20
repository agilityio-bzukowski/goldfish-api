from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ReminderResponse(BaseModel):
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
    task_id: uuid.UUID
    remind_at: datetime


class ReminderCreate(BaseModel):
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
    model_config = ConfigDict(from_attributes=True)

    remind_at: Optional[datetime] = None
    type: Optional[str] = None
    relative_minutes: Optional[int] = None
    is_fired: Optional[bool] = None


class ReminderDelete(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID


class ReminderFire(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
