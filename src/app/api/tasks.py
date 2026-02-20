"""Tasks API."""

import uuid

from fastapi import APIRouter, Query, Response

from app.core.deps import TaskServiceDep
from app.models.task import (
    BulkCompleteResponse,
    TaskCreate,
    TaskResponse,
    TaskReorder,
    TaskSortBy,
    TaskSortOrder,
    TaskUpdate,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=list[TaskResponse])
def list_tasks(
    task_service: TaskServiceDep,
    project_id: uuid.UUID | None = None,
    is_completed: bool | None = None,
    priority: int | None = None,
    due_date: str | None = None,
    sort_by: TaskSortBy = Query(
        TaskSortBy.SORT_ORDER,
        description="Column to sort by",
    ),
    order: TaskSortOrder = Query(
        TaskSortOrder.ASC,
        description="Sort direction",
    ),
    limit: int | None = Query(None, ge=1, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
) -> list[TaskResponse]:
    """List tasks with optional filters (non-deleted only)."""
    return task_service.get_tasks(
        project_id=project_id,
        is_completed=is_completed,
        priority=priority,
        due_date=due_date,
        sort_by=sort_by.value,
        order=order.value,
        limit=limit,
        offset=offset,
    )


@router.post("/", response_model=TaskResponse, status_code=201)
def create_task(body: TaskCreate, task_service: TaskServiceDep) -> TaskResponse:
    """Create task. sort_order auto-calculated; tag_ids linked."""
    return task_service.create_task(body)


@router.post("/bulk-complete", response_model=BulkCompleteResponse)
def bulk_complete(
    task_service: TaskServiceDep,
    project_id: uuid.UUID,
) -> BulkCompleteResponse:
    """Complete all active (incomplete) tasks in the given project."""
    completed = task_service.bulk_complete(project_id)
    return BulkCompleteResponse(completed=completed)


@router.patch("/reorder", status_code=204, response_class=Response)
def reorder_tasks(body: TaskReorder, task_service: TaskServiceDep) -> None:
    """Batch update sort_order for given task ids."""
    task_service.reorder(body)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: uuid.UUID, task_service: TaskServiceDep) -> TaskResponse:
    """Get single task with tags and reminders."""
    return task_service.get_task(task_id)


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    task_service: TaskServiceDep,
) -> TaskResponse:
    """Update task. Use tag_ids to replace tag associations."""
    return task_service.update_task(task_id, body)


@router.delete("/{task_id}", status_code=204, response_class=Response)
def delete_task(task_id: uuid.UUID, task_service: TaskServiceDep) -> None:
    """Soft delete task."""
    task_service.delete_task(task_id)


@router.post("/{task_id}/complete", response_model=TaskResponse)
def complete_task(task_id: uuid.UUID, task_service: TaskServiceDep) -> TaskResponse:
    """Toggle task completion; sets/clears completed_at."""
    return task_service.complete_toggle(task_id)
