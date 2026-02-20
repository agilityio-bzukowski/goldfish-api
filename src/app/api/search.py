from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query

from app.core.deps import SearchServiceDep
from app.models.task import TaskResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[TaskResponse])
def search(
    search_service: SearchServiceDep,
    q: str = Query("", description="Search term (title and notes)"),
    project_id: Optional[UUID] = Query(None, description="Filter by project"),
    include_completed: bool = Query(
        False, description="Include completed tasks"),
) -> list[TaskResponse]:
    """Search tasks by query; optionally filter by project and completed status. Max 50 results."""
    tasks = search_service.search(
        q=q,
        project_id=project_id,
        include_completed=include_completed,
    )
    return [TaskResponse.model_validate(t) for t in tasks]
