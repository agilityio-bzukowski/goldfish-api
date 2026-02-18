import uuid

from fastapi import HTTPException

from app.db.schema import Tag
from app.models.tag import TagCreate, TagUpdate
from app.services.base import BaseService


class TagService(BaseService):
    def get_tags(self) -> list[Tag]:
        with self.session as session:
            return list(session.query(Tag).all())

    def create_tag(self, tag: TagCreate) -> Tag:
        with self.session as session:
            db_tag = Tag(**tag.model_dump())
            session.add(db_tag)
            session.commit()
            session.refresh(db_tag)
            return db_tag

    def get_tag(self, tag_id: uuid.UUID) -> Tag:
        with self.session as session:
            tag = session.query(Tag).filter(Tag.id == tag_id).first()
            if not tag:
                raise HTTPException(status_code=404, detail="Tag not found")
            return tag

    def update_tag(self, tag_id: uuid.UUID, tag_update: TagUpdate) -> Tag:
        with self.session as session:
            db_tag = session.query(Tag).filter(Tag.id == tag_id).first()
            if not db_tag:
                raise HTTPException(status_code=404, detail="Tag not found")

            for field, value in tag_update.model_dump(exclude_unset=True).items():
                setattr(db_tag, field, value)

            session.commit()
            session.refresh(db_tag)
            return db_tag

    def delete_tag(self, tag_id: uuid.UUID) -> None:
        with self.session as session:
            tag = session.query(Tag).filter(Tag.id == tag_id).first()
            if not tag:
                raise HTTPException(status_code=404, detail="Tag not found")
            session.delete(tag)
            session.commit()
