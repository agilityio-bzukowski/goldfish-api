"""Reminders API."""

import uuid

from fastapi import APIRouter, Response

from app.core.deps import ReminderServiceDep
from app.models.reminder import ReminderCreateInput, ReminderDelete, ReminderFire, ReminderResponse

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.get("/upcoming", response_model=list[ReminderResponse])
def get_upcoming_reminders(reminder_service: ReminderServiceDep) -> list[ReminderResponse]:
    """Get upcoming reminders."""
    return reminder_service.get_upcoming_reminders()


@router.post("/", response_model=ReminderResponse, status_code=201)
def create_reminder(body: ReminderCreateInput, reminder_service: ReminderServiceDep) -> ReminderResponse:
    """Create reminder."""
    return reminder_service.create_reminder(body)


@router.delete("/{reminder_id}", status_code=204, response_class=Response)
def delete_reminder(reminder_id: uuid.UUID, reminder_service: ReminderServiceDep) -> None:
    """Delete reminder."""
    return reminder_service.delete_reminder(ReminderDelete(id=reminder_id))


@router.patch("/{reminder_id}/fire", response_model=ReminderResponse)
def fire_reminder(reminder_id: uuid.UUID, reminder_service: ReminderServiceDep) -> ReminderResponse:
    """Fire reminder."""
    return reminder_service.fire_reminder(ReminderFire(id=reminder_id))
