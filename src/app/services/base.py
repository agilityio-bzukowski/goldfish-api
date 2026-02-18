"""Shared service logic."""

from sqlalchemy.orm import Session


class BaseService:
    """Base service with session injection."""

    def __init__(self, session: Session) -> None:
        self.session = session
