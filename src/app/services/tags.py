import uuid
from datetime import datetime, timezone

from fastapi import HTTPException

from app.db.schema import Tag
from app.models.tag import TagCreate, TagUpdate
from app.services.base import BaseService


class TagService(BaseService):
    def get_tags(self) -> list[Tag]:
        with self.session as session:
            return list(
                session.query(Tag).filter(Tag.deleted_at.is_(None)).all()
            )

    def create_tag(self, tag: TagCreate) -> Tag:
        with self.session as session:
            existing = (
                session.query(Tag)
                .filter(
                    Tag.deleted_at.is_(None),
                    Tag.name == tag.name.strip(),
                )
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail="A tag with this name already exists",
                )
            tag = Tag(**tag.model_dump())
            session.add(tag)
            session.commit()
            session.refresh(tag)
            return tag

    def get_tag(self, tag_id: uuid.UUID) -> Tag:
        with self.session as session:
            tag = (
                session.query(Tag)
                .filter(Tag.id == tag_id, Tag.deleted_at.is_(None))
                .first()
            )
            if not tag:
                raise HTTPException(status_code=404, detail="Tag not found")
            return tag

    def update_tag(self, tag_id: uuid.UUID, tag_update: TagUpdate) -> Tag:
        with self.session as session:
            db_tag = (
                session.query(Tag)
                .filter(Tag.id == tag_id, Tag.deleted_at.is_(None))
                .first()
            )
            if not db_tag:
                raise HTTPException(status_code=404, detail="Tag not found")

            updates = tag_update.model_dump(exclude_unset=True)
            if "name" in updates:
                other = (
                    session.query(Tag)
                    .filter(
                        Tag.deleted_at.is_(None),
                        Tag.name == updates["name"].strip(),
                        Tag.id != tag_id,
                    )
                    .first()
                )
                if other:
                    raise HTTPException(
                        status_code=409,
                        detail="A tag with this name already exists",
                    )
            for field, value in updates.items():
                setattr(db_tag, field, value)

            session.commit()
            session.refresh(db_tag)
            return db_tag

    def delete_tag(self, tag_id: uuid.UUID) -> None:
        with self.session as session:
            tag = (
                session.query(Tag)
                .filter(Tag.id == tag_id, Tag.deleted_at.is_(None))
                .first()
            )
            if not tag:
                raise HTTPException(status_code=404, detail="Tag not found")
            tag.deleted_at = datetime.now(timezone.utc)
            session.commit()
