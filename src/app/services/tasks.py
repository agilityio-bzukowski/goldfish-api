"""Task service: CRUD, complete toggle, bulk complete, reorder."""

import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import delete, insert
from sqlalchemy.orm import joinedload

from app.db.schema import PriorityLevel, Project, Tag, Task, task_tag_link
from app.models.task import TaskCreate, TaskReorder, TaskUpdate
from app.services.base import BaseService

PRIORITY_MIN = 0
PRIORITY_MAX = 4


class TaskService(BaseService):
    @staticmethod
    def _parse_date(s: str | None) -> date | None:
        if not s:
            return None
        return date.fromisoformat(s)

    def _validate_project_exists(self, session, project_id: uuid.UUID) -> None:
        project = (
            session.query(Project)
            .filter(Project.id == project_id, Project.deleted_at.is_(None))
            .first()
        )
        if not project:
            raise HTTPException(
                status_code=404,
                detail="Project not found",
            )

    def _validate_tag_ids_exist(self, session, tag_ids: list[uuid.UUID]) -> None:
        if not tag_ids:
            return
        found = (
            session.query(Tag.id)
            .filter(Tag.id.in_(tag_ids), Tag.deleted_at.is_(None))
            .all()
        )
        found_ids = {r[0] for r in found}
        missing = set(tag_ids) - found_ids
        if missing:
            raise HTTPException(
                status_code=422,
                detail=f"Tag(s) not found: {sorted(missing)}",
            )

    def get_tasks(
        self,
        project_id: uuid.UUID | None = None,
        is_completed: bool | None = None,
        priority: int | None = None,
        due_date: str | None = None,
        sort_by: str = "sort_order",
        order: str = "asc",
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Task]:
        if priority is not None and not (PRIORITY_MIN <= priority <= PRIORITY_MAX):
            raise HTTPException(
                status_code=422,
                detail=f"priority must be between {PRIORITY_MIN} and {PRIORITY_MAX}",
            )
        due_date_parsed = None
        if due_date:
            try:
                due_date_parsed = self._parse_date(due_date)
            except ValueError:
                raise HTTPException(
                    status_code=422,
                    detail="due_date must be ISO date (YYYY-MM-DD)",
                )
        with self.session as session:
            q = session.query(Task).filter(Task.deleted_at.is_(None))

            priority_val = PriorityLevel(priority) if priority is not None else None
            optional_filters = [
                (Task.project_id, project_id),
                (Task.is_completed, is_completed),
                (Task.priority, priority_val),
                (Task.due_date, due_date_parsed),
            ]
            q = q.filter(
                *(col == val for col, val in optional_filters if val is not None)
            )

            order_col = getattr(Task, sort_by, Task.sort_order)
            q = q.order_by(order_col.desc() if order ==
                           "desc" else order_col.asc())
            q = q.offset(offset).limit(limit)
            q = q.options(joinedload(Task.tags), joinedload(Task.reminders))

            return list(q.all())

    def create_task(self, data: TaskCreate) -> Task:
        with self.session as session:
            if data.project_id is not None:
                self._validate_project_exists(session, data.project_id)
            self._validate_tag_ids_exist(session, data.tag_ids)

            max_row = (
                session.query(Task.sort_order)
                .filter(Task.deleted_at.is_(None))
                .order_by(Task.sort_order.desc())
                .first()
            )
            next_order = (max_row[0] + 1.0) if max_row else 0.0

            due_date_parsed = self._parse_date(
                data.due_date) if data.due_date else None
            task = Task(
                title=data.title,
                notes=data.notes or "",
                notes_plain=data.notes or "",
                priority=PriorityLevel(data.priority),
                due_date=due_date_parsed,
                due_time=data.due_time,
                project_id=data.project_id,
                sort_order=next_order,
            )
            session.add(task)
            session.flush()
            for tag_id in data.tag_ids:
                session.execute(
                    insert(task_tag_link).values(
                        task_id=task.id,
                        tag_id=tag_id,
                    )
                )
            session.commit()
            session.refresh(task)
            # Reload with relationships
            session.refresh(task)
            task = (
                session.query(Task)
                .filter(Task.id == task.id)
                .options(
                    joinedload(Task.tags),
                    joinedload(Task.reminders),
                )
                .one()
            )
            return task

    def get_task(self, task_id: uuid.UUID) -> Task:
        with self.session as session:
            task = (
                session.query(Task)
                .filter(Task.id == task_id, Task.deleted_at.is_(None))
                .options(
                    joinedload(Task.tags),
                    joinedload(Task.reminders),
                )
                .first()
            )
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            return task

    def update_task(self, task_id: uuid.UUID, data: TaskUpdate) -> Task:
        with self.session as session:
            task = (
                session.query(Task)
                .filter(Task.id == task_id, Task.deleted_at.is_(None))
                .first()
            )
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")

            update_data = data.model_dump(exclude_unset=True)
            tag_ids = update_data.pop("tag_ids", None)

            project_id = update_data.get("project_id")
            if project_id is not None:
                self._validate_project_exists(session, project_id)
            if tag_ids is not None:
                self._validate_tag_ids_exist(session, tag_ids)
            if tag_ids is not None:
                session.execute(
                    delete(task_tag_link).where(
                        task_tag_link.c.task_id == task_id)
                )
                for tag_id in tag_ids:
                    session.execute(
                        insert(task_tag_link).values(
                            task_id=task_id,
                            tag_id=tag_id,
                        )
                    )
            for key, value in update_data.items():
                if key == "due_date" and value is not None:
                    try:
                        value = self._parse_date(value)
                    except ValueError:
                        raise HTTPException(
                            status_code=422,
                            detail="due_date must be ISO date (YYYY-MM-DD)",
                        )
                if key == "priority" and value is not None:
                    if not (PRIORITY_MIN <= value <= PRIORITY_MAX):
                        raise HTTPException(
                            status_code=422,
                            detail=f"priority must be between {PRIORITY_MIN} and {PRIORITY_MAX}",
                        )
                    value = PriorityLevel(value)
                setattr(task, key, value)

            session.commit()
            session.refresh(task)
            task = (
                session.query(Task)
                .filter(Task.id == task_id)
                .options(
                    joinedload(Task.tags),
                    joinedload(Task.reminders),
                )
                .one()
            )
            return task

    def delete_task(self, task_id: uuid.UUID) -> None:
        with self.session as session:
            task = session.query(Task).filter(
                Task.id == task_id, Task.deleted_at.is_(None)
            ).first()
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            task.deleted_at = datetime.now(timezone.utc)
            session.commit()

    def complete_toggle(self, task_id: uuid.UUID) -> Task:
        with self.session as session:
            task = (
                session.query(Task)
                .filter(Task.id == task_id, Task.deleted_at.is_(None))
                .first()
            )
            if not task:
                raise HTTPException(status_code=404, detail="Task not found")
            task.is_completed = not task.is_completed
            task.completed_at = datetime.now(
                timezone.utc) if task.is_completed else None
            session.commit()
            session.refresh(task)
            task = (
                session.query(Task)
                .filter(Task.id == task_id)
                .options(
                    joinedload(Task.tags),
                    joinedload(Task.reminders),
                )
                .one()
            )
            return task

    def bulk_complete(self, project_id: uuid.UUID) -> int:
        with self.session as session:
            self._validate_project_exists(session, project_id)
            now = datetime.now(timezone.utc)
            q = (
                session.query(Task)
                .filter(
                    Task.deleted_at.is_(None),
                    Task.project_id == project_id,
                    Task.is_completed.is_(False),
                )
            )
            count = 0
            for task in q.all():
                task.is_completed = True
                task.completed_at = now
                count += 1
            session.commit()
            return count

    def reorder(self, data: TaskReorder) -> None:
        with self.session as session:
            for item in data.items:
                session.query(Task).filter(
                    Task.id == item.id,
                    Task.deleted_at.is_(None),
                ).update({Task.sort_order: item.sort_order})
            session.commit()
