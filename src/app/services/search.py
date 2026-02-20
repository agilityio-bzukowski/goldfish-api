"""Search service: full-text search over tasks (no raw SQL)."""

import uuid
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from app.db.schema import Task
from app.services.base import BaseService

MAX_QUERY_LEN = 100
SEARCH_LIMIT = 50


class SearchService(BaseService):
    """Search tasks by query; delegates to db/search layer."""

    def _normalize_query(self, q: str) -> Optional[str]:
        """Strip and validate search query. Returns None if invalid."""
        if not q or not isinstance(q, str):
            return None
        s = q.strip()
        if not s or len(s) > MAX_QUERY_LEN:
            return None
        return s

    def search(
        self,
        q: str,
        project_id: Optional[uuid.UUID] = None,
        include_completed: bool = False,
    ) -> List[Task]:
        """
        Return tasks matching the search query (title and notes), optionally
        filtered by project_id and include_completed. Results limited to 50.
        Eager-loads tags and reminders.
        """
        normalized = self._normalize_query(q)
        if not normalized:
            return []

        filter_completed = include_completed is False
        conditions = [
            Task.deleted_at.is_(None),
            or_(
                Task.title.ilike(f"%{normalized}%"),
                Task.notes_plain.ilike(f"%{normalized}%"),
                Task.notes.ilike(f"%{normalized}%"),
            ),
        ]
        if project_id is not None:
            conditions.append(Task.project_id == project_id)
        if filter_completed:
            conditions.append(Task.is_completed.is_(False))

        with self.session as session:
            return (
                session.query(Task)
                .filter(*conditions)
                .options(
                    joinedload(Task.tags),
                    joinedload(Task.reminders),
                )
                .order_by(Task.id)
                .limit(SEARCH_LIMIT)
                .all()
            )
