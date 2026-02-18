"""SQLAlchemy Base, enums, association tables, and declarative models."""

import uuid
from datetime import date, datetime, timezone
from enum import Enum, IntEnum
from typing import List, Optional

from sqlalchemy import Column, Date, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Table
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    type_annotation_map = {date: Date()}

    id = mapped_column(
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

    name: Mapped[str]
    description: Mapped[str]
    color: Mapped[str]
    icon: Mapped[str]
    view_mode: Mapped[ViewMode] = mapped_column(
        SAEnum(ViewMode, name="view_mode_enum"), default=ViewMode.LIST
    )
    is_archived: Mapped[bool]
    sort_order: Mapped[int]

    # Relationships
    tasks: Mapped[List["Task"]] = relationship(back_populates="project")


class Tag(Base):
    __tablename__ = "tag"

    name: Mapped[str]
    color: Mapped[str]

    tasks: Mapped[List["Task"]] = relationship(
        back_populates="tags",
        secondary=task_tag_link,
    )


class Task(Base):
    __tablename__ = "task"

    title: Mapped[str]
    notes: Mapped[Optional[str]]
    notes_plain: Mapped[Optional[str]]
    is_completed: Mapped[bool]
    completed_at: Mapped[Optional[datetime]]
    priority: Mapped[PriorityLevel] = mapped_column(
        SAEnum(PriorityLevel, name="priority_level"),
        default=PriorityLevel.NONE,
        index=True,
    )
    due_date: Mapped[Optional[date]]
    due_time: Mapped[Optional[str]]
    start_date: Mapped[Optional[date]]
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("project.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    parent_task_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("task.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    recurrence_parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("task.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    sort_order: Mapped[int]
    recurrence_rule: Mapped[Optional[str]]

    # Relationships
    project: Mapped[Optional["Project"]] = relationship(back_populates="tasks")
    parent_task: Mapped[Optional["Task"]] = relationship(
        "Task",
        foreign_keys=[parent_task_id],
        back_populates="subtasks",
        remote_side="Task.id",
    )
    subtasks: Mapped[List["Task"]] = relationship(
        "Task",
        foreign_keys=[parent_task_id],
        back_populates="parent_task",
    )
    recurrence_parent: Mapped[Optional["Task"]] = relationship(
        "Task",
        foreign_keys=[recurrence_parent_id],
        remote_side="Task.id",
    )
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
        DateTime(timezone=True), index=True)
    type: Mapped[ReminderType] = mapped_column(
        SAEnum(ReminderType, name="reminder_type"),
        nullable=False,
    )
    relative_minutes: Mapped[Optional[int]]
    is_fired: Mapped[bool]

    task: Mapped["Task"] = relationship(back_populates="reminders")
