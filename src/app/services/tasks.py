"""Task service: CRUD, complete toggle, bulk complete, reorder."""

import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy import delete, insert
from sqlalchemy.orm import joinedload

from app.db.schema import Project, Tag, Task, task_tags
from app.models.task import TaskCreate, TaskReorder, TaskUpdate
from app.services.base import BaseService


class TaskService(BaseService):

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
            self) -> list[Task]:
        q = self.session.query(Task).filter(Task.deleted_at.is_(None))
        q = q.order_by(Task.sort_order.asc())
        q = q.options(joinedload(Task.tags), joinedload(Task.reminders))
        return list(q.all())

    def create_task(self, data: TaskCreate) -> Task:
        if data.project_id is not None:
            self._validate_project_exists(self.session, data.project_id)

        self._validate_tag_ids_exist(self.session, data.tag_ids)

        max_row = (
            self.session.query(Task.sort_order)
            .filter(Task.deleted_at.is_(None))
            .order_by(Task.sort_order.desc())
            .first()
        )
        next_order = (max_row[0] + 1.0) if max_row else 0.0

        task = Task(
            title=data.title,
            notes=data.notes or "",
            notes_plain=data.notes or "",
            priority=data.priority,
            due_date=data.due_date,
            due_time=data.due_time,
            start_date=date.fromisoformat(
                data.start_date) if data.start_date else date.today(),
            project_id=data.project_id,
            sort_order=next_order,
        )
        self.session.add(task)
        self.session.flush()
        for tag_id in data.tag_ids:
            self.session.execute(
                insert(task_tags).values(
                    task_id=task.id,
                    tag_id=tag_id,
                )
            )
        self.session.commit()
        self.session.refresh(task)
        task = (
            self.session.query(Task)
            .filter(Task.id == task.id)
            .options(
                joinedload(Task.tags),
                joinedload(Task.reminders),
            )
            .one()
        )
        return task

    def get_task(self, task_id: uuid.UUID) -> Task:
        task = (
            self.session.query(Task)
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
        task = (
            self.session.query(Task)
            .filter(Task.id == task_id, Task.deleted_at.is_(None))
            .first()
        )
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        update_data = data.model_dump(exclude_unset=True)
        tag_ids = update_data.pop("tag_ids", None)
        project_id = update_data.get("project_id")

        if project_id is not None:
            self._validate_project_exists(self.session, project_id)

        if tag_ids is not None:
            self._validate_tag_ids_exist(self.session, tag_ids)

        if tag_ids is not None:
            self.session.execute(
                delete(task_tags).where(
                    task_tags.c.task_id == task_id)
            )
            for tag_id in tag_ids:
                self.session.execute(
                    insert(task_tags).values(
                        task_id=task_id,
                        tag_id=tag_id,
                    )
                )

        for key, value in update_data.items():
            setattr(task, key, value)

        self.session.commit()
        self.session.refresh(task)
        task = (
            self.session.query(Task)
            .filter(Task.id == task_id)
            .options(
                joinedload(Task.tags),
                joinedload(Task.reminders),
            )
            .one()
        )
        return task

    def delete_task(self, task_id: uuid.UUID) -> None:
        task = self.session.query(Task).filter(
            Task.id == task_id, Task.deleted_at.is_(None)
        ).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        task.deleted_at = datetime.now(timezone.utc)
        self.session.commit()

    def complete_toggle(self, task_id: uuid.UUID) -> Task:
        task = (
            self.session.query(Task)
            .filter(Task.id == task_id, Task.deleted_at.is_(None))
            .first()
        )
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        task.is_completed = not task.is_completed
        task.completed_at = datetime.now(
            timezone.utc) if task.is_completed else None

        self.session.commit()
        self.session.refresh(task)

        task = (
            self.session.query(Task)
            .filter(Task.id == task_id)
            .options(
                joinedload(Task.tags),
                joinedload(Task.reminders),
            )
            .one()
        )
        return task

    def bulk_complete(self, project_id: uuid.UUID) -> int:
        self._validate_project_exists(self.session, project_id)

        now = datetime.now(timezone.utc)
        q = (
            self.session.query(Task)
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
        self.session.commit()
        return count

    def reorder(self, data: TaskReorder) -> None:
        for item in data.items:
            self.session.query(Task).filter(
                Task.id == item.id,
                Task.deleted_at.is_(None),
            ).update({Task.sort_order: item.sort_order})
        self.session.commit()
