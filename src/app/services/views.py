

from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import joinedload

from app.db.schema import Task
from app.services.base import BaseService


class ViewService(BaseService):
    def get_inbox_tasks(self) -> list[Task]:
        """All top-level non-deleted tasks (active + completed), ordered by is_completed, sort_order."""
        with self.session as session:
            q = (
                session.query(Task)
                .filter(Task.deleted_at.is_(None))
                .order_by(Task.is_completed.asc(), Task.sort_order.asc())
                .options(joinedload(Task.tags), joinedload(Task.reminders))
            )
            return list(q.all())

    def get_today_tasks(self) -> list[Task]:
        """Incomplete tasks with due_date <= today, ordered by priority DESC, due_date, sort_order."""
        today = date.today()
        with self.session as session:
            q = (
                session.query(Task)
                .filter(
                    Task.deleted_at.is_(None),
                    Task.is_completed.is_(False),
                    Task.due_date.isnot(None),
                    Task.due_date <= today,
                )
                .order_by(
                    Task.priority.desc(),
                    Task.due_date.asc(),
                    Task.sort_order.asc(),
                )
                .options(joinedload(Task.tags), joinedload(Task.reminders))
            )
            return list(q.all())

    def get_completed_tasks(self, days: int = 30) -> list[Task]:
        """Completed tasks from the last N days, ordered by completed_at DESC."""
        if not (1 <= days <= 365):
            raise HTTPException(
                status_code=422,
                detail="days must be between 1 and 365",
            )
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        with self.session as session:
            q = (
                session.query(Task)
                .filter(
                    Task.deleted_at.is_(None),
                    Task.is_completed.is_(True),
                    Task.completed_at.isnot(None),
                    Task.completed_at >= cutoff,
                )
                .order_by(Task.completed_at.desc())
                .options(joinedload(Task.tags), joinedload(Task.reminders))
            )
            return list(q.all())
