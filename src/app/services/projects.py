"""Project service: CRUD with computed task_count and soft delete."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException

from app.db.schema import Project, Task
from app.models.project import ProjectCreate, ProjectUpdate
from app.services.base import BaseService


class ProjectService(BaseService):
    def get_projects(self) -> list[tuple[Project, int]]:
        """List non-deleted, non-archived projects with task_count (non-deleted, incomplete)."""
        with self.session as session:
            projects = (
                session.query(Project)
                .filter(
                    Project.deleted_at.is_(None),
                    Project.is_archived.is_(False),
                )
                .order_by(Project.sort_order.asc(), Project.name.asc())
                .all()
            )
            result: list[tuple[Project, int]] = []
            for project in projects:
                count = (
                    session.query(Task)
                    .filter(
                        Task.project_id == project.id,
                        Task.deleted_at.is_(None),
                        Task.is_completed.is_(False),
                    )
                    .count()
                )
                result.append((project, count))
            return result

    def get_project(self, project_id: uuid.UUID) -> tuple[Project, int]:
        """Get single project with task_count. 404 if not found or soft-deleted."""
        with self.session as session:
            project = (
                session.query(Project)
                .filter(
                    Project.id == project_id,
                    Project.deleted_at.is_(None),
                )
                .first()
            )
            if not project:
                raise HTTPException(
                    status_code=404, detail="Project not found")
            count = (
                session.query(Task)
                .filter(
                    Task.project_id == project_id,
                    Task.deleted_at.is_(None),
                    Task.is_completed.is_(False),
                )
                .count()
            )
            return (project, count)

    def create_project(self, data: ProjectCreate) -> Project:
        with self.session as session:
            from app.db.schema import ViewMode

            project = Project(
                name=data.name,
                description=data.description or "",
                color=data.color,
                icon=data.icon,
                view_mode=ViewMode(data.view_mode),
            )
            session.add(project)
            session.commit()
            session.refresh(project)
            return project

    def update_project(self, project_id: uuid.UUID, data: ProjectUpdate) -> Project:
        with self.session as session:
            project = (
                session.query(Project)
                .filter(
                    Project.id == project_id,
                    Project.deleted_at.is_(None),
                )
                .first()
            )
            if not project:
                raise HTTPException(
                    status_code=404, detail="Project not found")
            update_data = data.model_dump(exclude_unset=True)
            if "view_mode" in update_data:
                from app.db.schema import ViewMode

                update_data["view_mode"] = ViewMode(update_data["view_mode"])
            for key, value in update_data.items():
                setattr(project, key, value)
            session.commit()
            session.refresh(project)
            return project

    def delete_project(self, project_id: uuid.UUID) -> None:
        """Soft delete project; set project_id = None on all its tasks first."""
        with self.session as session:
            project = (
                session.query(Project)
                .filter(
                    Project.id == project_id,
                    Project.deleted_at.is_(None),
                )
                .first()
            )
            if not project:
                raise HTTPException(
                    status_code=404, detail="Project not found")
            session.query(Task).filter(
                Task.project_id == project_id,
                Task.deleted_at.is_(None),
            ).update({Task.project_id: None})
            project.deleted_at = datetime.now(timezone.utc)
            session.commit()
