"""SQLAlchemy Base, enums, association tables, and declarative models."""

import uuid
from datetime import date, datetime, timezone
from enum import Enum, IntEnum
from typing import List, Optional

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, String, Table, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    type_annotation_map = {date: Date()}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


# Enums

class PriorityLevel(IntEnum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


class ReminderType(str, Enum):
    ABSOLUTE = "absolute"
    RELATIVE = "relative"


class ViewMode(str, Enum):
    LIST = "list"
    BOARD = "board"


# ASSOCIATION TABLES

task_tag_link = Table(
    "task_tag_link",
    Base.metadata,
    Column("task_id", UUID(as_uuid=True), ForeignKey(
        "task.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", UUID(as_uuid=True), ForeignKey(
        "tag.id", ondelete="CASCADE"), primary_key=True),
)


# MODELS

class Project(Base):
    __tablename__ = "project"

    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(default="", nullable=False)
    color: Mapped[str] = mapped_column(default="#6366f1", nullable=False)
    icon: Mapped[str] = mapped_column(default="folder", nullable=False)
    view_mode: Mapped[ViewMode] = mapped_column(
        SAEnum(ViewMode, name="view_mode_enum"), default=ViewMode.LIST
    )
    is_archived: Mapped[bool] = mapped_column(default=False, nullable=False)
    sort_order: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    tasks: Mapped[List["Task"]] = relationship(back_populates="project")


class Tag(Base):
    __tablename__ = "tag"

    name: Mapped[str] = mapped_column(nullable=False, unique=True)
    color: Mapped[str] = mapped_column(default="#8b5cf6", nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    tasks: Mapped[List["Task"]] = relationship(
        back_populates="tags",
        secondary=task_tag_link,
    )


class Task(Base):
    __tablename__ = "task"

    title: Mapped[str] = mapped_column(nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(default="")
    notes_plain: Mapped[Optional[str]] = mapped_column(default="")
    is_completed: Mapped[bool] = mapped_column(default=False, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)
    priority: Mapped[PriorityLevel] = mapped_column(
        SAEnum(PriorityLevel, name="priority_level"),
        default=PriorityLevel.NONE,
        index=True,
    )
    due_date: Mapped[Optional[date]] = mapped_column(nullable=True)
    due_time: Mapped[Optional[str]] = mapped_column(nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(nullable=True)
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    sort_order: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False)
    sort_order_board: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    project: Mapped[Optional["Project"]] = relationship(back_populates="tasks")
    tags: Mapped[List["Tag"]] = relationship(
        back_populates="tasks",
        secondary=task_tag_link,
    )
    reminders: Mapped[List["Reminder"]] = relationship(back_populates="task")


class Reminder(Base):
    __tablename__ = "reminder"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("task.id", ondelete="CASCADE"),
        index=True,
    )
    remind_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True
    )
    type: Mapped[ReminderType] = mapped_column(
        SAEnum(ReminderType, name="reminder_type"),
        nullable=False,
    )
    relative_minutes: Mapped[Optional[int]] = mapped_column(nullable=True)
    is_fired: Mapped[bool] = mapped_column(default=False, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    task: Mapped["Task"] = relationship(back_populates="reminders")


class Settings(Base):
    __tablename__ = "settings"

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default="default")
    theme: Mapped[str] = mapped_column(default="system", nullable=False)
    default_project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project.id", ondelete="SET NULL"),
        nullable=True,
    )
    sidebar_collapsed: Mapped[bool] = mapped_column(
        default=False, nullable=False)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cloud_user_id: Mapped[Optional[str]] = mapped_column(nullable=True)
    device_id: Mapped[str] = mapped_column(default="LOCAL", nullable=False)
    # AI config
    ai_provider: Mapped[str] = mapped_column(default="openai", nullable=False)
    ai_model: Mapped[str] = mapped_column(
        default="gpt-4o-mini", nullable=False)
    ai_api_key: Mapped[Optional[str]] = mapped_column(nullable=True)
    ai_base_url: Mapped[Optional[str]] = mapped_column(nullable=True)
    ai_report_prompt: Mapped[Optional[str]] = mapped_column(Text, default=None)
