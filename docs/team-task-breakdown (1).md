# Goldfish — Backend Task Breakdown

> **Stack**: Python 3.11+ / FastAPI / Uvicorn / Poetry / SQLModel / SQLite / Alembic
> **Team**: 2 backend developers
> **Estimated total**: 2 weeks
>
> **Zero-blocking strategy**: Both developers start from an agreed-upon schema spec (SQLModel model definitions + request/response schemas) on day 1. Dev 1 builds the actual database layer while Dev 2 builds API endpoints using the schemas. They integrate at the end of week 1.

---

## Architecture Decisions

| Decision    | Choice                                               | Why                                                                                              |
| ----------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| ORM/Validation | SQLModel                                          | Pydantic + SQLAlchemy; single source for models and API schemas, great SQLite support            |
| Deps        | Poetry                                              | Reliable dependency management, lockfile, virtualenv                                             |
| Server      | Uvicorn                                             | ASGI server for FastAPI                                                                          |
| IDs         | ULID strings                                        | Sortable by creation time, no auto-increment issues                                              |
| Timestamps  | ISO 8601 strings in UTC                             | `"2026-02-16T14:30:00.000"` — portable, no timezone ORM headaches                                |
| Deletes     | Soft delete (`deleted_at`)                           | Every query must filter `deleted_at IS NULL`                                                     |
| Migrations  | Alembic                                             | Versioned schema changes; `alembic upgrade head` on startup or deploy                            |
| DB location | `%APPDATA%/com.todo.app/todo.db` (Win)              | Standard per-platform app data path                                                              |
| DB mode     | SQLite WAL + `foreign_keys=ON` + `busy_timeout=5000` | WAL for concurrent reads, FK enforcement, timeout for locks                                      |

---

## How the Zero-Blocking Split Works

```
Day 1 (kickoff):
  Both devs agree on SQLModel model definitions + request/response schemas (this document is the spec).
  Both devs can start immediately.

Dev 1 builds DOWNWARD (infrastructure → data layer → core APIs):
  Scaffold → Engine → Models → Migration → Task CRUD → Project CRUD

Dev 2 builds UPWARD (schemas → API endpoints that import schemas):
  Schemas → Tags → Settings+AI → Views → Search → Reminders

Integration point (end of week 1):
  Dev 2's endpoints import Dev 1's models + engine via `get_db` dependency.
  This is a mechanical merge — the SQLModel/schemas are the shared contract.
```

Dev 2 can develop and **unit-test endpoints using an in-memory SQLite** with the same models, or simply write the endpoint logic trusting the schema contract. The `get_db` dependency injection makes swapping the database trivial.

---

## File Structure

```
backend/
├── main.py              # FastAPI app, CORS, router registration (run with uvicorn)
├── config.py            # DB path, API host/port
├── pyproject.toml       # Poetry dependencies
├── database/
│   ├── engine.py        # SQLModel engine, Session, SQLite pragmas
│   └── models.py        # All 8 SQLModel table models
├── api/
│   ├── tasks.py         # Task CRUD + complete + reorder (7 endpoints)     [Dev 1]
│   ├── projects.py      # Project CRUD + board columns (6 endpoints)       [Dev 1]
│   ├── tags.py          # Tag CRUD (4 endpoints)                           [Dev 2]
│   ├── views.py         # Inbox, Today, Completed (3 endpoints)            [Dev 2]
│   ├── search.py        # FTS5 full-text search (1 endpoint)               [Dev 2]
│   ├── reminders.py     # Reminder CRUD + upcoming + fire (4 endpoints)    [Dev 2]
│   ├── settings.py      # AI settings get/patch (2 endpoints)              [Dev 2]
│   └── reports.py       # AI report generation (1 endpoint)                [Dev 2]
├── schemas/             #                                                  [Dev 2]
│   ├── task.py
│   ├── project.py
│   └── tag.py
├── services/
│   └── settings.py      # get_or_create_settings helper                    [Dev 2]
└── utils/
    └── ulid.py          # ULID generator                                   [Dev 1]
```

---

## Dev 1: Infrastructure + Core CRUD

### Task 1.1: Project scaffolding + DB engine

**Estimate**: 0.5 day
**Blocked by**: nothing

**Deliverable**: FastAPI app boots, connects to SQLite, serves `/api/health`.

**Files**: `main.py`, `config.py`, `database/engine.py`, `utils/ulid.py`

**Implementation details**:

`config.py`:

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

`engine.py` — create engine with `sqlmodel.create_engine(DATABASE_URL)` and set SQLite pragmas on every connection (use SQLAlchemy `event.listens_for(engine, "connect")` to run PRAGMAs: WAL, foreign_keys=ON, busy_timeout=5000).

`main.py` — CORS must allow Tauri origins:

```python
allow_origins=["http://localhost:1420", "tauri://localhost", "https://tauri.localhost"]
```

**Acceptance criteria**:

- `GET /api/health` returns `{"status": "ok"}`
- SQLite DB created at correct path, WAL mode active, FK enabled
- ULID generation produces 26-char sortable strings

---

### Task 1.2: Database models (8 tables)

**Estimate**: 1 day
**Blocked by**: nothing (start day 1 alongside Dev 2)

**Deliverable**: All SQLModel table models in `database/models.py`. Tables are created/updated via Alembic (Task 1.3), not on app startup.

**Models** (SQLModel with `table=True`; use `Field(..., foreign_key=...)` for FKs):

`projects`:

```python
from sqlmodel import SQLModel, Field

class Project(SQLModel, table=True):
    __tablename__ = "projects"
    id: str = Field(primary_key=True, default_factory=generate_ulid)
    name: str
    description: str = ""
    color: str = "#6366f1"
    icon: str = "folder"
    view_mode: str = "list"    # CHECK: 'list' or 'board'
    is_archived: bool = False
    sort_order: float = 0.0
    # + created_at, updated_at, deleted_at, sync_version, device_id
```

`board_columns`:

```python
class BoardColumn(SQLModel, table=True):
    __tablename__ = "board_columns"
    id: str = Field(primary_key=True, default_factory=generate_ulid)
    project_id: str = Field(foreign_key="projects.id")
    name: str
    color: str = "#94a3b8"
    sort_order: float = 0.0
    is_done_column: bool = False
    # + created_at, updated_at, deleted_at, sync_version, device_id
```

`tasks`:

```python
class Task(SQLModel, table=True):
    __tablename__ = "tasks"
    id: str = Field(primary_key=True, default_factory=generate_ulid)
    title: str
    notes: str = ""
    notes_plain: str = ""
    status: str | None = "todo"  # todo|in_progress|blocked|waiting|done
    is_completed: bool = False
    completed_at: str | None = None
    priority: int = 0      # CHECK: 0-4
    due_date: str | None = None    # "YYYY-MM-DD"
    due_time: str | None = None    # "HH:MM"
    start_date: str | None = None
    project_id: str | None = Field(default=None, foreign_key="projects.id")
    board_column_id: str | None = Field(default=None, foreign_key="board_columns.id")
    parent_task_id: str | None = Field(default=None, foreign_key="tasks.id")
    sort_order: float = 0.0
    sort_order_board: float = 0.0
    recurrence_rule: str | None = None
    recurrence_parent_id: str | None = Field(default=None, foreign_key="tasks.id")
    # + created_at, updated_at, deleted_at, sync_version, device_id
```

`tags`, `task_tags`, `reminders`, `settings`, `sync_log` — see Architecture doc for full definitions. Use `Relationship()` for back-refs (e.g. `subtasks: list["Task"] = Relationship(back_populates="parent_task")`).

**Gotcha — self-referential relationship**: Use `Relationship(back_populates="parent_task", sa_relationship_kwargs={"remote_side": "Task.id"})` for subtasks.

**Acceptance criteria**:

- All 8 tables created, CHECK constraints work
- FK cascades correct (delete project → SET NULL on tasks)
- Self-referential subtasks + M2M tags work

---

### Task 1.3: Alembic migrations

**Estimate**: 0.5 day
**Blocked by**: nothing (can start as soon as 1.1 + 1.2 are done, same dev)

**Deliverable**: Alembic configured for SQLModel/SQLite; initial migration from models; run `alembic upgrade head` on startup or as part of deploy.

**Setup**:

```bash
poetry add alembic
alembic init alembic
```

Configure `alembic.ini` and `alembic/env.py` to use the same `DATABASE_URL` as `config.py` and import all models from `database.models` so `target_metadata = SQLModel.metadata`. Use `sqlalchemy.url` from config in `env.py`:

```python
# alembic/env.py
from database.models import SQLModel  # or the shared Base
from config import DATABASE_URL
config.set_main_option("sqlalchemy.url", DATABASE_URL)
target_metadata = SQLModel.metadata
```

**Workflow**: After changing models, run `alembic revision --autogenerate -m "description"` then `alembic upgrade head`. On app startup or install, run `alembic upgrade head` so the DB is up to date.

**Acceptance criteria**:

- `alembic upgrade head` creates/updates all tables from current models
- New migrations are generated with `alembic revision --autogenerate` when models change
- Migrations run successfully on fresh DB and on existing DB (idempotent where applicable)

---

### Task 1.4: Task CRUD API (7 endpoints)

**Estimate**: 1.5 days
**Blocked by**: nothing (uses schemas from shared spec; integrates with Dev 2's schema files at merge)

**File**: `api/tasks.py` (~185 lines)

| Method | Path                       | Notes                                                                                                                                                           |
| ------ | -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GET    | `/api/tasks`               | Filters: project_id, parent_task_id, is_completed, priority, sort_by, order, limit, offset. Default: top-level only. `joinedload` for tags, subtasks, reminders |
| POST   | `/api/tasks`               | Auto-calculate sort_order (max + 1). Pass status (default "todo"). Attach tags via tag_ids                                                                      |
| GET    | `/api/tasks/{id}`          | Single task with all relationships                                                                                                                              |
| PATCH  | `/api/tasks/{id}`          | `exclude_unset=True`. Handle tag_ids separately: delete all task_tags, re-insert                                                                                |
| DELETE | `/api/tasks/{id}`          | Soft delete only                                                                                                                                                |
| POST   | `/api/tasks/{id}/complete` | Toggle `is_completed`. Set/clear `completed_at`                                                                                                                 |
| POST   | `/api/tasks/bulk-complete` | Complete all active tasks in a project. Return `{"completed": N}`                                                                                               |
| PATCH  | `/api/tasks/reorder`       | Body: `{"items": [{"id": "...", "sort_order": 1.0}]}`                                                                                                           |

**sort_order auto-calculation**:

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

**Acceptance criteria**:

- List returns non-deleted, top-level tasks by default with nested relations (no N+1)
- Create auto-calculates sort_order, passes status
- PATCH only updates provided fields, tag reassignment works
- Toggle complete sets/clears completed_at
- Bulk complete returns count

---

### Task 1.5: Project CRUD API (6 endpoints)

**Estimate**: 1 day
**Blocked by**: nothing

**File**: `api/projects.py` (~133 lines)

| Method | Path                         | Notes                                                                                                                 |
| ------ | ---------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| GET    | `/api/projects`              | Non-archived, non-deleted. Include computed `task_count`                                                              |
| POST   | `/api/projects`              | Auto-create 3 default board columns: "To Do" (sort 0), "In Progress" (sort 1), "Done" (sort 2, `is_done_column=True`) |
| GET    | `/api/projects/{id}`         | Single project with task count                                                                                        |
| PATCH  | `/api/projects/{id}`         | Update name, color, icon, view_mode, is_archived, sort_order                                                          |
| DELETE | `/api/projects/{id}`         | Soft delete. **Must** manually nullify project_id on child tasks                                                      |
| GET    | `/api/projects/{id}/columns` | Board columns sorted by sort_order                                                                                    |

**Gotcha — soft delete does NOT trigger FK cascade**:

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

**Acceptance criteria**:

- Create auto-generates 3 board columns
- Task count is computed (not stored)
- Delete unassigns tasks (they move to Inbox)
- Archived projects excluded from default list

---

## Dev 2: Schemas + Supporting APIs

### Task 2.1: SQLModel / Pydantic schemas

**Estimate**: 0.5 day
**Blocked by**: nothing (built from the agreed spec in this document)

**Deliverable**: All request/response schemas in `schemas/` (plain Pydantic models or SQLModel read schemas). These are the shared contract — both devs import from here. SQLModel table models can be reused for validation; use separate Create/Update/Response schemas where needed.

`schemas/task.py`:

```python
class TaskCreate(BaseModel):
    title: str
    notes: str = ""
    priority: int = 0
    status: str = "todo"              # todo|in_progress|blocked|waiting|done
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
    status: str | None = None
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
    status: str | None
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

**Gotcha — SQLModel/Pydantic + lazy relationships**: The session may return `None` for unloaded relations. Response schemas expect `list`. Use `@field_validator(..., mode="before")` to coerce `None → []` for `tags`, `subtasks`, `reminders`.

`schemas/project.py`: ProjectCreate, ProjectUpdate, ProjectResponse (with computed task_count), BoardColumnResponse.

`schemas/tag.py`: TagCreate, TagUpdate, TagResponse.

---

### Task 2.2: Tag CRUD API (4 endpoints)

**Estimate**: 0.5 day
**Blocked by**: nothing

**File**: `api/tags.py` (~58 lines)

| Method | Path             | Notes                             |
| ------ | ---------------- | --------------------------------- |
| GET    | `/api/tags`      | All non-deleted, sorted by name   |
| POST   | `/api/tags`      | Return 409 if name already exists |
| PATCH  | `/api/tags/{id}` | Update name, color                |
| DELETE | `/api/tags/{id}` | Soft delete                       |

**Acceptance criteria**:

- Duplicate tag name returns 409
- Soft-deleted tags don't appear in list
- Deleting a tag doesn't delete associated tasks (junction CASCADE handles it)

---

### Task 2.3: Settings + AI Reports API (3 endpoints)

**Estimate**: 1 day
**Blocked by**: nothing

**Files**: `api/settings.py` (~43 lines), `api/reports.py` (~146 lines), `services/settings.py`

**Settings** (2 endpoints):

| Method | Path               | Notes                                                    |
| ------ | ------------------ | -------------------------------------------------------- |
| GET    | `/api/settings/ai` | Auto-create "default" row if missing (singleton pattern) |
| PATCH  | `/api/settings/ai` | Update provider, model, api_key, base_url, report_prompt |

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

**Reports** (1 endpoint):

`POST /api/reports/generate` — Body: `{ "date": "2026-02-16" | null, "prompt": "..." | null }`

All three AI providers use the same OpenAI-compatible chat completion format:

```python
async def _call_llm(api_key, model, system_prompt, user_prompt, base_url):
    headers = {"Content-Type": "application/json"}
    if api_key:
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
        resp = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=60)
        return resp.json()["choices"][0]["message"]["content"]
```

**Provider base URLs**:

- OpenAI: `https://api.openai.com/v1`
- Anthropic: `https://api.anthropic.com/v1`
- Ollama: `http://localhost:11434/v1` (no key needed)

**Gotcha**: Skip API key validation for Ollama:

```python
if not settings.ai_api_key and settings.ai_provider != "ollama":
    raise HTTPException(400, "AI API key not configured")
```

**Acceptance criteria**:

- Settings GET auto-creates default row, PATCH updates only provided fields
- Report generation works with OpenAI and Ollama
- Returns 400 if key missing for OpenAI/Anthropic
- Returns meaningful error if AI call fails

---

### Task 2.4: Views API (3 endpoints)

**Estimate**: 0.5 day
**Blocked by**: nothing

**File**: `api/views.py` (~68 lines)

| Method | Path                           | Notes                                                                                                       |
| ------ | ------------------------------ | ----------------------------------------------------------------------------------------------------------- |
| GET    | `/api/views/inbox`             | ALL top-level tasks (active + completed), ordered by `is_completed, sort_order`. Frontend groups by project |
| GET    | `/api/views/today`             | Incomplete tasks where `due_date <= today`, sorted by `priority DESC, due_date, sort_order`                 |
| GET    | `/api/views/completed?days=30` | Completed tasks from last N days, sorted by `completed_at DESC`                                             |

All views must use `joinedload` for tags and reminders.

**Acceptance criteria**:

- Inbox returns ALL tasks (active + done) for frontend grouping
- Today includes overdue tasks (due_date < today)
- Completed respects the `days` param (default 30, max 365)

---

### Task 2.5: Search API (1 endpoint)

**Estimate**: 0.5 day
**Blocked by**: nothing

**File**: `api/search.py` (~57 lines)

`GET /api/search?q=term&project_id=X&include_completed=false`

**Implementation** — try FTS5 first, fallback to LIKE:

```python
try:
    conn.execute(text("""
        CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts
        USING fts5(title, notes_plain, content=tasks, content_rowid=rowid)
    """))
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

**Acceptance criteria**:

- Matches title and notes, results limited to 50
- Can filter by project_id, include/exclude completed
- Works even if FTS5 extension is unavailable

---

### Task 2.6: Reminder API (4 endpoints)

**Estimate**: 0.5 day
**Blocked by**: nothing

**File**: `api/reminders.py` (~86 lines)

| Method | Path                                | Notes                                                                   |
| ------ | ----------------------------------- | ----------------------------------------------------------------------- |
| POST   | `/api/tasks/{id}/reminders`         | Create reminder. Validate task exists                                   |
| DELETE | `/api/reminders/{id}`               | Soft delete                                                             |
| GET    | `/api/reminders/upcoming?minutes=5` | Unfired reminders due within N minutes. JOIN with Task for `task_title` |
| PATCH  | `/api/reminders/{id}/fire`          | Set `is_fired = true`                                                   |

**`/upcoming` must include task_title** for frontend notifications:

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

**Acceptance criteria**:

- Creating reminder for non-existent task returns 404
- `upcoming` returns only unfired reminders within the window, includes task_title
- `fire` prevents reminder from appearing again in upcoming

---

## Task Assignment Summary

| Task | Description                         | Dev   | Estimate | Blocked by |
| ---- | ----------------------------------- | ----- | -------- | ---------- |
| 1.1  | Project scaffolding + DB engine     | Dev 1 | 0.5d     | nothing    |
| 1.2  | Database models (8 tables)          | Dev 1 | 1d       | nothing    |
| 1.3  | Alembic migrations                  | Dev 1 | 0.5d     | nothing    |
| 1.4  | Task CRUD API (7 endpoints)         | Dev 1 | 1.5d     | nothing    |
| 1.5  | Project CRUD API (6 endpoints)      | Dev 1 | 1d       | nothing    |
| 2.1  | SQLModel/Pydantic schemas (contract) | Dev 2 | 0.5d     | nothing    |
| 2.2  | Tag CRUD API (4 endpoints)          | Dev 2 | 0.5d     | nothing    |
| 2.3  | Settings + AI Reports (3 endpoints) | Dev 2 | 1d       | nothing    |
| 2.4  | Views API (3 endpoints)             | Dev 2 | 0.5d     | nothing    |
| 2.5  | Search API (1 endpoint)             | Dev 2 | 0.5d     | nothing    |
| 2.6  | Reminder API (4 endpoints)          | Dev 2 | 0.5d     | nothing    |

**Dev 1 total**: 4.5 days (infrastructure + core entities: tasks, projects)
**Dev 2 total**: 3.5 days (schemas + supporting APIs: tags, views, search, reminders, AI)

---

## Parallel Execution Timeline

```
         Day 1       Day 2       Day 3       Day 4       Day 5
Dev 1:  [1.1 Scaffold + 1.2 Models        ] [1.3 Alembic] [1.4 Task CRUD            ]
Dev 2:  [2.1 Schemas ] [2.2 Tags] [2.3 Settings + AI Reports] [2.4 Views] [2.5 Search]

         Day 6       Day 7       Day 8       Day 9       Day 10
Dev 1:  [1.4 contd  ] [1.5 Project CRUD   ] [Integration + bug fixes               ]
Dev 2:  [2.6 Remind ] [Integration + bug fixes                                      ]

Integration merge (Day 7-8):
  - Dev 2's API files import Dev 1's models + get_db
  - Wire all routers into main.py
  - End-to-end testing across all 28 endpoints
```

**Key insight**: Neither developer is ever waiting. Dev 2 writes all endpoint logic using the SQLModel/Pydantic schemas as the contract. At integration, the only change is adding the real `db: Session = Depends(get_db)` imports and wiring routers into `main.py`. Run the API with `uvicorn main:app` (or via Poetry script).

---

## Known Gotchas

1. **Schema changes require a new Alembic migration** — run `alembic revision --autogenerate` after model changes, then `alembic upgrade head` on startup/deploy (Task 1.3).

2. **SQLModel/Pydantic + lazy relationships**: Unloaded relations may be `None`. Fix with `@field_validator("field", mode="before")` to coerce `None → []`.

3. **Self-referential relationships**: In SQLModel use `Relationship(..., sa_relationship_kwargs={"remote_side": "Task.id"})` (or the column object) for subtasks.

4. **Soft delete doesn't trigger FK cascade**: `ondelete="SET NULL"` only fires on real SQL `DELETE`. When soft-deleting a project, you must manually nullify `project_id` on child tasks.

5. **Ollama doesn't need an API key**: Don't block report generation with a "key required" check when provider is Ollama.

6. **CORS for Tauri**: Must include all three origins: `http://localhost:1420`, `tauri://localhost`, `https://tauri.localhost`.

7. **FTS5 may not be available**: Always have a `LIKE` fallback for search.

8. **Timestamp consistency**: Always use `datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]` for millisecond precision without the `+00:00` suffix.
