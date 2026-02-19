"""Projects API."""

import uuid

from fastapi import APIRouter, Response

from app.core.deps import ProjectServiceDep
from app.models.project import ProjectCreate, ProjectResponse, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/", response_model=list[ProjectResponse])
def list_projects(project_service: ProjectServiceDep) -> list[ProjectResponse]:
    """List non-archived, non-deleted projects with task_count."""
    items = project_service.get_projects()
    return [
        ProjectResponse.model_validate(project).model_copy(update={"task_count": count})
        for project, count in items
    ]


@router.post("/", response_model=ProjectResponse, status_code=201)
def create_project(body: ProjectCreate, project_service: ProjectServiceDep) -> ProjectResponse:
    """Create project."""
    project = project_service.create_project(body)
    return ProjectResponse.model_validate(project)


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: uuid.UUID,
    project_service: ProjectServiceDep,
) -> ProjectResponse:
    """Get single project with task_count."""
    project, count = project_service.get_project(project_id)
    return ProjectResponse.model_validate(project).model_copy(
        update={"task_count": count}
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdate,
    project_service: ProjectServiceDep,
) -> ProjectResponse:
    """Update project."""
    project = project_service.update_project(project_id, body)
    _, count = project_service.get_project(project_id)
    return ProjectResponse.model_validate(project).model_copy(
        update={"task_count": count}
    )


@router.delete("/{project_id}", status_code=204, response_class=Response)
def delete_project(
    project_id: uuid.UUID,
    project_service: ProjectServiceDep,
) -> None:
    """Soft delete project; unassigns all its tasks (move to Inbox)."""
    project_service.delete_project(project_id)
