"""Tasks API."""

import uuid

from fastapi import APIRouter, Response

from app.core.deps import TaskServiceDep
from app.models.task import (
    BulkCompleteResponse,
    TaskCreate,
    TaskReorder,
    TaskResponse,
    TaskUpdate,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=list[TaskResponse])
def list_tasks(
    task_service: TaskServiceDep,
) -> list[TaskResponse]:
    return task_service.get_tasks()


@router.post("/", response_model=TaskResponse, status_code=201)
def create_task(body: TaskCreate, task_service: TaskServiceDep) -> TaskResponse:
    return task_service.create_task(body)


@router.post("/bulk-complete", response_model=BulkCompleteResponse)
def bulk_complete(
    task_service: TaskServiceDep,
    project_id: uuid.UUID,
) -> BulkCompleteResponse:
    completed = task_service.bulk_complete(project_id)
    return BulkCompleteResponse(completed=completed)


@router.patch("/reorder", status_code=204, response_class=Response)
def reorder_tasks(body: TaskReorder, task_service: TaskServiceDep) -> None:
    task_service.reorder(body)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: uuid.UUID, task_service: TaskServiceDep) -> TaskResponse:
    return task_service.get_task(task_id)


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    task_service: TaskServiceDep,
) -> TaskResponse:
    return task_service.update_task(task_id, body)


@router.delete("/{task_id}", status_code=204, response_class=Response)
def delete_task(task_id: uuid.UUID, task_service: TaskServiceDep) -> None:
    task_service.delete_task(task_id)


@router.post("/{task_id}/complete", response_model=TaskResponse)
def complete_task(task_id: uuid.UUID, task_service: TaskServiceDep) -> TaskResponse:
    return task_service.complete_toggle(task_id)
