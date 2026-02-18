"""Central place for FastAPI dependencies and shared *Dep type aliases."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.tags import TagService

SessionDep = Annotated[Session, Depends(get_db)]


def get_tag_service(session: SessionDep) -> TagService:
    """Provide TagService for this request."""
    return TagService(session)


TagServiceDep = Annotated[TagService, Depends(get_tag_service)]
