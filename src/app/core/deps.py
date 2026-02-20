"""Central place for FastAPI dependencies and shared *Dep type aliases."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.projects import ProjectService
from app.services.tags import TagService
from app.services.tasks import TaskService
from app.services.views import ViewService

SessionDep = Annotated[Session, Depends(get_db)]


def get_tag_service(session: SessionDep) -> TagService:
    """Provide TagService for this request."""
    return TagService(session)


def get_task_service(session: SessionDep) -> TaskService:
    """Provide TaskService for this request."""
    return TaskService(session)


def get_project_service(session: SessionDep) -> ProjectService:
    """Provide ProjectService for this request."""
    return ProjectService(session)


def get_view_service(session: SessionDep) -> ViewService:
    """Provide ViewService for this request."""
    return ViewService(session)

TagServiceDep = Annotated[TagService, Depends(get_tag_service)]
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
ViewServiceDep = Annotated[ViewService, Depends(get_view_service)]
