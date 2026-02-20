"""Central place for FastAPI dependencies and shared *Dep type aliases."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.ai_client import build_ai_client
from app.services.projects import ProjectService
from app.services.reminders import ReminderService
from app.services.reports import ReportsService
from app.services.search import SearchService
from app.services.settings import SettingsService
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


def get_search_service(session: SessionDep) -> SearchService:
    """Provide SearchService for this request."""
    return SearchService(session)


def get_reminder_service(session: SessionDep) -> ReminderService:
    """Provide ReminderService for this request."""
    return ReminderService(session)


def get_settings_service(session: SessionDep) -> SettingsService:
    """Provide SettingsService for this request."""
    return SettingsService(session)


def get_reports_service(session: SessionDep) -> ReportsService:
    """Provide ReportsService for this request."""
    return ReportsService(
        session=session,
        settings_service=SettingsService(session),
        ai_client_factory=build_ai_client,
    )


TagServiceDep = Annotated[TagService, Depends(get_tag_service)]
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
ViewServiceDep = Annotated[ViewService, Depends(get_view_service)]
SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]
ReminderServiceDep = Annotated[ReminderService, Depends(get_reminder_service)]
SettingsServiceDep = Annotated[SettingsService, Depends(get_settings_service)]
ReportsServiceDep = Annotated[ReportsService, Depends(get_reports_service)]
