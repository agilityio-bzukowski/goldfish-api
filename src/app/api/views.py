from fastapi import APIRouter, Query

from app.core.deps import ViewServiceDep
from app.models.task import TaskResponse

router = APIRouter(prefix="/views", tags=["views"])


@router.get("/inbox", response_model=list[TaskResponse])
def get_inbox(view_service: ViewServiceDep) -> list[TaskResponse]:
    return view_service.get_inbox_tasks()


@router.get("/today", response_model=list[TaskResponse])
def get_today(view_service: ViewServiceDep) -> list[TaskResponse]:
    """Incomplete tasks with due_date <= today, sorted by priority, due_date, sort_order."""
    return view_service.get_today_tasks()


@router.get("/completed", response_model=list[TaskResponse])
def get_completed(
    view_service: ViewServiceDep,
    days: int = Query(30, ge=1, le=365,
                      description="Last N days of completed tasks"),
) -> list[TaskResponse]:
    """Completed tasks from the last N days, sorted by completed_at DESC."""
    return view_service.get_completed_tasks(days=days)
