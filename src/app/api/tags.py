"""Tags API."""

import uuid

from fastapi import APIRouter, Response

from app.core.deps import TagServiceDep
from app.models.tag import TagCreate, TagRead, TagUpdate

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("/", response_model=list[TagRead])
def list_tags(tag_service: TagServiceDep) -> list[TagRead]:
    """List tags."""
    return tag_service.get_tags()


@router.post("/", response_model=TagRead, status_code=201)
def create_tag(body: TagCreate, tag_service: TagServiceDep) -> TagRead:
    """Create tag. Return 409 if name already exists."""
    return tag_service.create_tag(body)


@router.patch("/{tag_id}", response_model=TagRead)
def update_tag(tag_id: uuid.UUID, body: TagUpdate, tag_service: TagServiceDep) -> TagRead:
    """Update tag."""
    return tag_service.update_tag(tag_id, body)


@router.delete("/{tag_id}", status_code=204, response_class=Response)
def delete_tag(tag_id: uuid.UUID, tag_service: TagServiceDep):
    """Soft delete tag."""
    tag_service.delete_tag(tag_id)
