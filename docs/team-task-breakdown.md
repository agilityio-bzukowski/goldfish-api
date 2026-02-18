# Backend Task Breakdown — Task Management API

> **Stack**: Python 3.11+ / FastAPI / SQLAlchemy (or SQLModel) / SQLite
> **2 backend developers** (Dev 1, Dev 2)
> **Estimated**: 2-3 weeks

---

## Architecture Decisions (agree before coding)

| Decision | Recommendation | Why |
|----------|---------------|-----|
| ORM | SQLAlchemy 2.0+ (or SQLModel) | Mature, async-optional, great SQLite support |
| IDs | ULID strings | Sortable by creation time, no auto-increment issues |
| Timestamps | ISO 8601 strings in UTC | `"2026-02-16T14:30:00.000"` — portable, no timezone ORM headaches |
| Deletes | Soft delete (`deleted_at` column) | Every query must filter `deleted_at IS NULL` |
| Migrations | Auto-migration on startup | Inspect DB vs models, `ALTER TABLE ADD COLUMN` for new cols. No Alembic needed for a desktop app. |
| DB location | `%APPDATA%/com.todo.app/todo.db` (Win) | Standard per-platform app data path |
| DB mode | SQLite WAL + `foreign_keys=ON` + `busy_timeout=5000` | WAL for concurrent reads, FK enforcement, timeout for locks |

---

## Task 1: Project scaffolding + DB engine

**Assignee**: Dev 1
**Estimate**: 0.5 day
**Blocked by**: nothing

### Deliverable

FastAPI app that starts, serves `/api/health`, and connects to SQLite.

### File structure

```
backend/
  main.py              # FastAPI app, CORS, router registration, auto-migration
  config.py            # DB path, API host/port
  database/
    engine.py          # SQLAlchemy engine, SessionLocal, get_db dependency
    models.py          # All ORM models
  utils/
    ulid.py            # ULID generator
  api/                 # Route files (one per resource)
  schemas/             # Pydantic request/response models
  services/            # Shared business logic (e.g. get_or_create_settings)
```

### Implementation details

**`config.py`**:
```python
import os, sys

if sys.platform == "win32":
    APP_DIR = os.path.join(os.environ.get("APPDATA", "."), "com.todo.app")
else:
    APP_DIR = os.path.expanduser("~/.local/share/com.todo.app")

os.makedirs(APP_DIR, exist_ok=True)

DATABASE_URL = f"sqlite:///{os.path.join(APP_DIR, 'todo.db')}"
API_HOST = "127.0.0.1"
API_PORT = 18429
```

**`engine.py`** — Must set SQLite pragmas on every connection:
```python
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()
```

**`main.py`** — CORS must allow Tauri origins:
```python
allow_origins=["http://localhost:1420", "tauri://localhost", "https://tauri.localhost"]
```

### Acceptance criteria

- [ ] `GET /api/health` returns `{"status": "ok"}`
- [ ] SQLite DB file created at correct path
- [ ] WAL mode active (`PRAGMA journal_mode` returns `wal`)
- [ ] Foreign keys enabled
- [ ] ULID generation produces 26-char sortable strings

---

## Task 2: All database models

**Assignee**: Dev 1
**Estimate**: 1 day
**Blocked by**: Task 1

### Deliverable

All 8 tables defined as SQLAlchemy models + auto-created on startup via `Base.metadata.create_all()`.

### Models

#### `projects`

```python
id            = Column(String, primary_key=True, default=generate_ulid)
name          = Column(String, nullable=False)
description   = Column(Text, default="")
color         = Column(String, default="#6366f1")
icon          = Column(String, default="folder")
view_mode     = Column(String, default="list")    # CHECK: 'list' or 'board'
is_archived   = Column(Boolean, default=False)
sort_order    = Column(Float, nullable=False, default=0.0)
created_at    = Column(String, nullable=False, default=_utcnow)
updated_at    = Column(String, nullable=False, default=_utcnow, onupdate=_utcnow)
deleted_at    = Column(String, nullable=True)
sync_version  = Column(Integer, default=0)
device_id     = Column(String, nullable=False, default="LOCAL")
```

Relationships: `columns` (BoardColumn), `tasks` (Task)

#### `board_columns`

```python
id              = Column(String, primary_key=True, default=generate_ulid)
project_id      = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
name            = Column(String, nullable=False)
color           = Column(String, default="#94a3b8")
sort_order      = Column(Float, nullable=False, default=0.0)
is_done_column  = Column(Boolean, default=False)
# + created_at, updated_at, deleted_at, sync_version, device_id
```

#### `tasks`

```python
id                   = Column(String, primary_key=True, default=generate_ulid)
title                = Column(String, nullable=False)
notes                = Column(Text, default="")
notes_plain          = Column(Text, default="")
is_completed         = Column(Boolean, default=False)
completed_at         = Column(String, nullable=True)
priority             = Column(Integer, default=0)      # CHECK: 0-4
due_date             = Column(String, nullable=True)    # "YYYY-MM-DD"
due_time             = Column(String, nullable=True)    # "HH:MM"
start_date           = Column(String, nullable=True)
project_id           = Column(String, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
board_column_id      = Column(String, ForeignKey("board_columns.id", ondelete="SET NULL"), nullable=True)
parent_task_id       = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
sort_order           = Column(Float, nullable=False, default=0.0)
sort_order_board     = Column(Float, nullable=False, default=0.0)
recurrence_rule      = Column(String, nullable=True)
recurrence_parent_id = Column(String, ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
# + created_at, updated_at, deleted_at, sync_version, device_id
```

Relationships: `project`, `board_column`, `subtasks` (self-referential), `tags` (M2M via task_tags), `reminders`

**GOTCHA — Self-referential relationship**: Use `remote_side=[id]` as a **column object list**, NOT a string like `remote_side="Task.id"`. The string form silently breaks.
```python
subtasks = relationship("Task", foreign_keys=[parent_task_id], backref="parent_task", remote_side=[id])
```

#### `tags`

```python
id    = Column(String, primary_key=True, default=generate_ulid)
name  = Column(String, nullable=False, unique=True)
color = Column(String, default="#8b5cf6")
# + created_at, updated_at, deleted_at, sync_version, device_id
```

Relationship: `tasks` (M2M via task_tags)

#### `task_tags` (junction table)

```python
task_id    = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
tag_id     = Column(String, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
created_at = Column(String, nullable=False, default=_utcnow)
sync_version = Column(Integer, default=0)
device_id  = Column(String, nullable=False, default="LOCAL")
```

#### `reminders`

```python
id               = Column(String, primary_key=True, default=generate_ulid)
task_id          = Column(String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
remind_at        = Column(String, nullable=False)   # ISO datetime UTC
type             = Column(String, default="absolute")  # CHECK: 'absolute' or 'relative'
relative_minutes = Column(Integer, nullable=True)
is_fired         = Column(Boolean, default=False)
# + created_at, updated_at, deleted_at, sync_version, device_id
```

#### `settings` (singleton row)

```python
id                 = Column(String, primary_key=True, default="default")
theme              = Column(String, default="system")
default_project_id = Column(String, ForeignKey("projects.id"), nullable=True)
sidebar_collapsed  = Column(Boolean, default=False)
last_sync_at       = Column(String, nullable=True)
cloud_user_id      = Column(String, nullable=True)
device_id          = Column(String, nullable=False, default="LOCAL")
updated_at         = Column(String, nullable=False, default=_utcnow, onupdate=_utcnow)
# AI config
ai_provider      = Column(String, default="openai")   # openai | anthropic | ollama
ai_model         = Column(String, default="gpt-4o-mini")
ai_api_key       = Column(String, nullable=True)
ai_base_url      = Column(String, nullable=True)
ai_report_prompt = Column(Text, default="Summarize what I accomplished today...")
```

#### `sync_log` (audit trail)

```python
id             = Column(Integer, primary_key=True, autoincrement=True)
table_name     = Column(String, nullable=False)
row_id         = Column(String, nullable=False)
operation      = Column(String, nullable=False)  # CHECK: INSERT/UPDATE/DELETE
changed_fields = Column(Text, nullable=True)      # JSON
timestamp      = Column(String, nullable=False, default=_utcnow)
device_id      = Column(String, nullable=False, default="LOCAL")
synced         = Column(Boolean, default=False)
```

### Acceptance criteria

- [ ] `Base.metadata.create_all()` creates all 8 tables
- [ ] All CHECK constraints work (priority 0-4, view_mode list/board, etc.)
- [ ] Foreign key cascades work correctly (delete project → SET NULL on tasks)
- [ ] Self-referential Task relationship works (subtasks)
- [ ] M2M Task ↔ Tag via task_tags works

---

## Task 3: Auto-migration system

**Assignee**: Dev 1
**Estimate**: 0.5 day
**Blocked by**: Task 2

### Deliverable

A function that runs on startup AFTER `create_all()`. It inspects the DB schema vs model definitions and adds any missing columns via `ALTER TABLE`.

### Why this matters

`create_all()` only creates **new tables**. It does NOT add new columns to existing tables. Since this is a desktop app with no deploy pipeline, users need seamless upgrades when you add new fields.

### Implementation

```python
def _migrate_missing_columns():
    inspector = inspect(engine)
    with engine.connect() as conn:
        for table in Base.metadata.sorted_tables:
            existing = {col["name"] for col in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name not in existing:
                    col_type = column.type.compile(engine.dialect)
                    default = ""
                    if column.default is not None:
                        val = column.default.arg
                        if callable(val): val = val()
                        if isinstance(val, str):
                            default = f" DEFAULT '{val.replace(chr(39), chr(39)+chr(39))}'"
                        elif val is not None:
                            default = f" DEFAULT {val}"
                    nullable = "" if column.nullable else " NOT NULL"
                    stmt = f"ALTER TABLE {table.name} ADD COLUMN {column.name} {col_type}{nullable}{default}"
                    conn.execute(text(stmt))
        conn.commit()
```

### Acceptance criteria

- [ ] Adding a new column to a model → appears in DB on next startup (no manual SQL)
- [ ] Handles string defaults with proper quoting
- [ ] Handles callable defaults (e.g. `default=_utcnow`)
- [ ] Does NOT crash if column already exists

---

## Task 4: Pydantic schemas (request/response models)

**Assignee**: Dev 2
**Estimate**: 0.5 day
**Blocked by**: Task 2 (needs to match model definitions)

### Deliverable

All Pydantic schemas in `backend/schemas/`.

### `schemas/task.py`

```python
class TaskCreate(BaseModel):
    title: str
    notes: str = ""
    priority: int = 0
    due_date: str | None = None
    due_time: str | None = None
    project_id: str | None = None
    board_column_id: str | None = None
    parent_task_id: str | None = None
    recurrence_rule: str | None = None
    tag_ids: list[str] = []

class TaskUpdate(BaseModel):
    title: str | None = None
    notes: str | None = None
    priority: int | None = None
    due_date: str | None = None
    due_time: str | None = None
    project_id: str | None = None
    board_column_id: str | None = None
    parent_task_id: str | None = None
    sort_order: float | None = None
    sort_order_board: float | None = None
    recurrence_rule: str | None = None
    tag_ids: list[str] | None = None

class TaskReorder(BaseModel):
    items: list[dict]   # [{"id": "...", "sort_order": 1.0}]

class ReminderCreate(BaseModel):
    remind_at: str
    type: str = "absolute"
    relative_minutes: int | None = None

class ReminderResponse(BaseModel):
    id: str
    task_id: str
    remind_at: str
    type: str
    relative_minutes: int | None
    is_fired: bool
    created_at: str
    updated_at: str
    model_config = {"from_attributes": True}

class TagResponse(BaseModel):
    id: str
    name: str
    color: str
    created_at: str
    updated_at: str
    model_config = {"from_attributes": True}

class TaskResponse(BaseModel):
    id: str
    title: str
    notes: str
    notes_plain: str
    is_completed: bool
    completed_at: str | None
    priority: int
    due_date: str | None
    due_time: str | None
    start_date: str | None
    project_id: str | None
    board_column_id: str | None
    parent_task_id: str | None
    sort_order: float
    sort_order_board: float
    recurrence_rule: str | None
    recurrence_parent_id: str | None
    created_at: str
    updated_at: str
    tags: list["TagResponse"] = []
    subtasks: list["TaskResponse"] = []
    reminders: list["ReminderResponse"] = []
    model_config = {"from_attributes": True}

    @field_validator("tags", "subtasks", "reminders", mode="before")
    @classmethod
    def coerce_none_to_list(cls, v):
        if v is None:
            return []
        return v

TaskResponse.model_rebuild()
```

**GOTCHA — Pydantic + lazy relationships**: When SQLAlchemy returns unloaded lazy relations, they come as `None` instead of `[]`. Pydantic expects `list`. The `field_validator` with `mode="before"` coerces `None → []`.

### `schemas/project.py`

```python
class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    color: str = "#6366f1"
    icon: str = "folder"
    view_mode: str = "list"

class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    color: str | None = None
    icon: str | None = None
    view_mode: str | None = None
    is_archived: bool | None = None
    sort_order: float | None = None

class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    color: str
    icon: str
    view_mode: str
    is_archived: bool
    sort_order: float
    created_at: str
    updated_at: str
    task_count: int = 0
    model_config = {"from_attributes": True}

class BoardColumnResponse(BaseModel):
    id: str
    project_id: str
    name: str
    color: str
    sort_order: float
    is_done_column: bool
    created_at: str
    updated_at: str
    model_config = {"from_attributes": True}
```

### `schemas/tag.py`

```python
class TagCreate(BaseModel):
    name: str
    color: str = "#8b5cf6"

class TagUpdate(BaseModel):
    name: str | None = None
    color: str | None = None

class TagResponse(BaseModel):
    id: str
    name: str
    color: str
    created_at: str
    updated_at: str
    model_config = {"from_attributes": True}
```

---

## Task 5: Task CRUD API

**Assignee**: Dev 1
**Estimate**: 1.5 days
**Blocked by**: Tasks 2, 4

### Endpoints

| Method | Path | Status | Notes |
|--------|------|--------|-------|
| GET | `/api/tasks` | 200 | Query params: `project_id`, `parent_task_id`, `is_completed`, `priority`, `due_date`, `sort_by`, `order`, `limit`, `offset`. Default: top-level only (`parent_task_id IS NULL`). Use `joinedload` for tags, subtasks, reminders. |
| POST | `/api/tasks` | 201 | Auto-calculate `sort_order` (max existing + 1). Attach tags via `tag_ids`. |
| GET | `/api/tasks/:id` | 200/404 | Single task with all relationships. |
| PATCH | `/api/tasks/:id` | 200/404 | `exclude_unset=True`. Handle `tag_ids` separately: delete all task_tags, re-insert. |
| DELETE | `/api/tasks/:id` | 204/404 | Soft delete only. |
| POST | `/api/tasks/:id/complete` | 200/404 | Toggle `is_completed`. Set `completed_at` when completing, clear when un-completing. |
| POST | `/api/tasks/bulk-complete` | 200 | Query param `project_id`. Complete all active tasks in project. Return `{"completed": N}`. |
| PATCH | `/api/tasks/reorder` | 204 | Body: `{"items": [{"id": "...", "sort_order": 1.0}]}`. Batch update. |

### Key implementation details

**sort_order auto-calculation on create**:
```python
max_order = db.query(Task.sort_order).filter(
    Task.deleted_at.is_(None),
    Task.parent_task_id == data.parent_task_id
).order_by(Task.sort_order.desc()).first()
next_order = (max_order[0] + 1.0) if max_order else 0.0
```

**PATCH with tag_ids**:
```python
update_data = data.model_dump(exclude_unset=True)
tag_ids = update_data.pop("tag_ids", None)
if tag_ids is not None:
    db.query(TaskTag).filter(TaskTag.task_id == task_id).delete()
    for tag_id in tag_ids:
        db.add(TaskTag(task_id=task_id, tag_id=tag_id))
for key, value in update_data.items():
    setattr(task, key, value)
```

### Acceptance criteria

- [ ] List returns only non-deleted, top-level tasks by default
- [ ] Filtering by project_id, is_completed, priority works
- [ ] Create auto-calculates sort_order
- [ ] PATCH only updates provided fields
- [ ] Tag reassignment works (delete old + insert new)
- [ ] Toggle complete sets/clears `completed_at` timestamp
- [ ] Bulk complete returns count
- [ ] All responses include nested tags, subtasks, reminders (no N+1)

---

## Task 6: Project CRUD API

**Assignee**: Dev 2
**Estimate**: 1 day
**Blocked by**: Tasks 2, 4

### Endpoints

| Method | Path | Status | Notes |
|--------|------|--------|-------|
| GET | `/api/projects` | 200 | List non-archived, non-deleted. Include computed `task_count` (non-deleted, non-completed tasks). |
| POST | `/api/projects` | 201 | Auto-create 3 default board columns: "To Do" (sort 0), "In Progress" (sort 1), "Done" (sort 2, `is_done_column=True`). |
| GET | `/api/projects/:id` | 200/404 | Single project with task count. |
| PATCH | `/api/projects/:id` | 200/404 | Update name, color, icon, view_mode, is_archived, sort_order. |
| DELETE | `/api/projects/:id` | 204/404 | Soft delete. **IMPORTANT**: set `project_id = NULL` on all tasks belonging to this project first. |
| GET | `/api/projects/:id/columns` | 200 | List board columns sorted by sort_order. |

### GOTCHA — Soft delete does NOT trigger FK cascade

`ondelete="SET NULL"` only fires on real SQL `DELETE`. Since we use soft deletes (`deleted_at = now`), the FK cascade never triggers. You MUST manually nullify orphaned tasks:

```python
@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(...).first()
    if not project: raise HTTPException(404)
    # MUST do this — soft delete doesn't trigger FK cascade
    db.query(Task).filter(Task.project_id == project_id, Task.deleted_at.is_(None)).update(
        {Task.project_id: None}
    )
    project.deleted_at = _utcnow()
    db.commit()
```

### Acceptance criteria

- [ ] Project create auto-generates 3 board columns
- [ ] Task count is computed (not stored)
- [ ] Delete unassigns tasks (they move to "No project" / Inbox)
- [ ] Archived projects excluded from default list

---

## Task 7: Tag CRUD API

**Assignee**: Dev 2
**Estimate**: 0.5 day
**Blocked by**: Tasks 2, 4

### Endpoints

| Method | Path | Status | Notes |
|--------|------|--------|-------|
| GET | `/api/tags` | 200 | All non-deleted, sorted by name. |
| POST | `/api/tags` | 201/409 | Return 409 if name already exists. |
| PATCH | `/api/tags/:id` | 200/404 | Update name, color. |
| DELETE | `/api/tags/:id` | 204/404 | Soft delete. |

### Acceptance criteria

- [ ] Duplicate tag name returns 409
- [ ] Soft-deleted tags don't appear in list
- [ ] Deleting a tag doesn't delete associated tasks (junction table handles via CASCADE)

---

## Task 8: Views API (Inbox, Today, Completed)

**Assignee**: Dev 2
**Estimate**: 0.5 day
**Blocked by**: Task 5

### Endpoints

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/views/inbox` | ALL top-level tasks (both active + completed), ordered by `is_completed, sort_order`. Frontend groups by project. |
| GET | `/api/views/today` | Incomplete tasks where `due_date <= today`, sorted by `priority DESC, due_date, sort_order`. |
| GET | `/api/views/completed?days=30` | Completed tasks from last N days, sorted by `completed_at DESC`. |

All views must use `joinedload` for tags and reminders.

### Acceptance criteria

- [ ] Inbox returns ALL tasks (active + done) for frontend grouping
- [ ] Today includes overdue tasks (due_date < today)
- [ ] Completed respects the `days` param (default 30, max 365)

---

## Task 9: Search API (FTS5)

**Assignee**: Dev 1
**Estimate**: 0.5 day
**Blocked by**: Task 5

### Endpoint

`GET /api/search?q=term&project_id=X&include_completed=false`

### Implementation

Try FTS5 first, fallback to LIKE:
```python
try:
    # FTS5: create virtual table if not exists
    conn.execute(text("""
        CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts
        USING fts5(title, notes_plain, content=tasks, content_rowid=rowid)
    """))
    # Search with ranking
    fts_results = conn.execute(text(
        "SELECT rowid FROM tasks_fts WHERE tasks_fts MATCH :q ORDER BY rank LIMIT 50"
    ), {"q": q})
except:
    # Fallback: LIKE
    query = query.filter(or_(
        Task.title.ilike(f"%{q}%"),
        Task.notes_plain.ilike(f"%{q}%")
    ))
```

### Acceptance criteria

- [ ] Search matches title and notes
- [ ] Results limited to 50
- [ ] Can filter by project_id
- [ ] Can include/exclude completed tasks
- [ ] Works even if FTS5 extension is unavailable

---

## Task 10: Reminder API

**Assignee**: Dev 1
**Estimate**: 0.5 day
**Blocked by**: Task 5

### Endpoints

| Method | Path | Status | Notes |
|--------|------|--------|-------|
| POST | `/api/tasks/:id/reminders` | 201/404 | Create reminder. Validate task exists. |
| DELETE | `/api/reminders/:id` | 204/404 | Soft delete. |
| GET | `/api/reminders/upcoming?minutes=5` | 200 | Unfired reminders due within N minutes. **JOIN with Task** to include `task_title` in response. |
| PATCH | `/api/reminders/:id/fire` | 200/404 | Set `is_fired = true`. |

### `/upcoming` implementation detail

The response needs `task_title` for notifications. Use a JOIN:
```python
results = (
    db.query(Reminder, Task.title)
    .join(Task, Reminder.task_id == Task.id)
    .filter(
        Reminder.deleted_at.is_(None),
        Reminder.is_fired == False,
        Reminder.remind_at <= cutoff,
        Reminder.remind_at >= now_str,
        Task.deleted_at.is_(None),
    )
    .all()
)
return [
    {**ReminderResponse.model_validate(r).model_dump(), "task_title": title}
    for r, title in results
]
```

### Acceptance criteria

- [ ] Creating reminder for non-existent task returns 404
- [ ] `upcoming` returns only unfired reminders within the time window
- [ ] `upcoming` response includes `task_title`
- [ ] `fire` sets `is_fired = true` and doesn't return the reminder in `upcoming` again

---

## Task 11: Settings + AI Reports API

**Assignee**: Dev 2
**Estimate**: 1 day
**Blocked by**: Task 2

### Settings endpoints

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/settings/ai` | Auto-create "default" row if missing (singleton pattern). |
| PATCH | `/api/settings/ai` | Update provider, model, api_key, base_url, report_prompt. |

**Singleton pattern**:
```python
def get_or_create_settings(db: Session) -> Settings:
    settings = db.query(Settings).filter(Settings.id == "default").first()
    if not settings:
        settings = Settings(id="default")
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings
```

### Reports endpoint

`POST /api/reports/generate`

Body: `{ "date": "2026-02-16" | null, "prompt": "..." | null }`

Response: `{ "date": "2026-02-16", "task_count": 5, "report": "AI generated text..." }`

### AI provider logic

All three providers use the same OpenAI-compatible chat completion format:

```python
async def _call_openai(api_key: str | None, model: str, system_prompt: str, user_prompt: str, base_url: str):
    headers = {"Content-Type": "application/json"}
    if api_key:  # Ollama doesn't need a key
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1000,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{base_url}/v1/chat/completions", headers=headers, json=payload, timeout=60)
        return resp.json()["choices"][0]["message"]["content"]
```

**Provider-specific base URLs**:
- OpenAI: `https://api.openai.com`
- Anthropic: `https://api.anthropic.com` (note: Anthropic has its own format, but you can use the OpenAI-compatible proxy or implement separately)
- Ollama: `http://localhost:11434` (no key needed)

**GOTCHA**: Skip API key validation for Ollama:
```python
if not settings.ai_api_key and settings.ai_provider != "ollama":
    raise HTTPException(400, "AI API key not configured")
```

### Acceptance criteria

- [ ] Settings GET auto-creates default row
- [ ] Settings PATCH updates only provided fields
- [ ] Report generation works with OpenAI
- [ ] Report generation works with Ollama (no API key)
- [ ] Returns 400 if key missing for OpenAI/Anthropic
- [ ] Returns meaningful error if AI call fails

---

## Task 12: Docker setup

**Assignee**: Dev 1 or Dev 2 (whoever finishes first)
**Estimate**: 0.5 day
**Blocked by**: All API tasks

### Deliverable

`Dockerfile` + `docker-compose.yml` for the backend API.

### Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
EXPOSE 18429
CMD ["python", "-m", "backend.main"]
```

### docker-compose.yml

```yaml
services:
  api:
    build: .
    ports:
      - "18429:18429"
    volumes:
      - todo-data:/app/data
    environment:
      - TODO_DB_PATH=/app/data/todo.db
volumes:
  todo-data:
```

### Acceptance criteria

- [ ] `docker compose up` starts the API
- [ ] DB persists across container restarts (volume)
- [ ] Health check passes: `curl http://localhost:18429/api/health`

---

## Task Assignment Summary

| Task | Description | Dev | Estimate | Depends on |
|------|-------------|-----|----------|------------|
| 1 | Project scaffolding + DB engine | Dev 1 | 0.5d | — |
| 2 | All database models | Dev 1 | 1d | 1 |
| 3 | Auto-migration system | Dev 1 | 0.5d | 2 |
| 4 | Pydantic schemas | Dev 2 | 0.5d | 2 |
| 5 | Task CRUD API | Dev 1 | 1.5d | 2, 4 |
| 6 | Project CRUD API | Dev 2 | 1d | 2, 4 |
| 7 | Tag CRUD API | Dev 2 | 0.5d | 2, 4 |
| 8 | Views API | Dev 2 | 0.5d | 5 |
| 9 | Search API (FTS5) | Dev 1 | 0.5d | 5 |
| 10 | Reminder API | Dev 1 | 0.5d | 5 |
| 11 | Settings + AI Reports | Dev 2 | 1d | 2 |
| 12 | Docker setup | Either | 0.5d | All |

### Parallel execution timeline

```
Week 1:
  Dev 1: [Task 1] → [Task 2] → [Task 3] → [Task 5 start]
  Dev 2:                        [Task 4] → [Task 6] → [Task 7]

Week 2:
  Dev 1: [Task 5 finish] → [Task 9] → [Task 10]
  Dev 2: [Task 8] → [Task 11] → [Task 12]
```

---

## Known Gotchas (from real implementation)

1. **SQLAlchemy `create_all()` does NOT add columns to existing tables**. That's why Task 3 (auto-migration) exists. Without it, any new column you add to a model will silently not appear in the DB.

2. **Pydantic + lazy-loaded relationships**: SQLAlchemy returns `None` for unloaded relationships. Pydantic expects `list`. Fix with `@field_validator("field", mode="before")` to coerce `None → []`.

3. **Self-referential relationships**: Use `remote_side=[id]` with the actual column object, NOT a string.

4. **Soft delete doesn't trigger FK `ondelete`**: `ondelete="SET NULL"` only works with real SQL `DELETE`. When soft-deleting a project, you MUST manually nullify `project_id` on child tasks.

5. **Ollama doesn't need an API key**: Don't block report generation with a "key required" check when provider is Ollama.

6. **CORS origins for Tauri**: Must include all three: `http://localhost:1420`, `tauri://localhost`, `https://tauri.localhost`.

7. **SQLite FTS5 may not be available**: Always have a `LIKE` fallback for search.

8. **Timestamp format consistency**: Always use `datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]` to get millisecond precision without the `+00:00` suffix.
