from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from app.db.schema import Reminder, ReminderType, Task
from app.models.reminder import ReminderCreateInput, ReminderDelete, ReminderFire
from app.services.base import BaseService


class ReminderService(BaseService):
    def __init__(self, session: Session):
        self.session = session

    def get_upcoming_reminders(self):
        q = self.session.query(Reminder).filter(
            Reminder.deleted_at.is_(None), Reminder.is_fired.is_(False))
        q = q.order_by(Reminder.remind_at.asc())
        q = q.options(joinedload(Reminder.task))
        return list(q.all())

    def create_reminder(self, data: ReminderCreateInput) -> Reminder:
        task = self.session.query(Task).filter(Task.id == data.task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        reminder = Reminder(
            task_id=data.task_id,
            remind_at=data.remind_at,
            type=ReminderType.ABSOLUTE,
            relative_minutes=None,
        )
        self.session.add(reminder)
        self.session.commit()
        self.session.refresh(reminder)
        return reminder

    def delete_reminder(self, data: ReminderDelete) -> None:
        reminder = self.session.query(Reminder).filter(
            Reminder.id == data.id, Reminder.deleted_at.is_(None)).first()
        if not reminder:
            raise HTTPException(
                status_code=404, detail="Reminder not found")
        reminder.deleted_at = datetime.now(timezone.utc)
        self.session.commit()

    def fire_reminder(self, data: ReminderFire) -> Reminder:
        reminder = self.session.query(Reminder).filter(
            Reminder.id == data.id, Reminder.deleted_at.is_(None)).first()
        if not reminder:
            raise HTTPException(
                status_code=404, detail="Reminder not found")
        reminder.is_fired = True
        self.session.commit()
        self.session.refresh(reminder)
        return reminder
