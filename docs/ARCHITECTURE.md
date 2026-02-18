# Todo App — Architecture & Technology Overview

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Tauri 2 Shell (Rust)                  │
│  ┌───────────────────────┐  ┌────────────────────────┐  │
│  │   React 19 Frontend   │  │  Python FastAPI Backend │  │
│  │   (Webview / Vite)    │──│  (Sidecar Process)     │  │
│  │   localhost:1420       │  │  localhost:18429        │  │
│  └───────────────────────┘  └──────────┬─────────────┘  │
│                                        │                 │
│                              ┌─────────▼──────────┐     │
│                              │  SQLite (WAL mode)  │     │
│                              │  %APPDATA%/todo.db  │     │
│                              └────────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

## Technology Stack

### Desktop Shell
| Technology      | Version | Purpose                              |
|-----------------|---------|--------------------------------------|
| **Tauri**       | 2.x     | Native desktop wrapper (Rust-based)  |
| tauri-plugin-opener       | —   | Open URLs/files natively         |
| tauri-plugin-window-state | —   | Persist window position/size     |

### Frontend
| Technology            | Version | Purpose                          |
|-----------------------|---------|----------------------------------|
| **React**             | 19.1    | UI framework                     |
| **TypeScript**        | 5.8     | Type safety                      |
| **Vite**              | 7.0     | Build tool & dev server          |
| **Tailwind CSS**      | 4.1     | Utility-first styling            |
| **TanStack Query**    | 5.x     | Server state / data fetching     |
| **Zustand**           | 5.x     | Client-side UI state             |
| **Lucide React**      | 0.564   | Icon library                     |
| **Emoji Mart**        | 5.6     | Emoji picker                     |

### Backend
| Technology       | Version  | Purpose                          |
|------------------|----------|----------------------------------|
| **FastAPI**      | >=0.115  | REST API framework               |
| **Uvicorn**      | >=0.30   | ASGI server                      |
| **SQLAlchemy**   | >=2.0    | ORM & database management        |
| **Pydantic**     | >=2.9    | Request/response validation      |
| **SQLite**       | —        | Embedded database (WAL mode)     |

---

## Component Architecture

### Frontend Structure

```
src/
├── App.tsx                          # Root: QueryClient, theme, routing
├── lib/api.ts                       # HTTP client (fetch → backend)
├── stores/uiStore.ts                # Zustand: sidebar, theme, route
├── hooks/                           # React Query hooks
│   ├── useTasks.ts
│   ├── useProjects.ts
│   └── ...
├── components/
│   ├── layout/
│   │   ├── Header.tsx               # Pin, snap-to-edge, theme, settings
│   │   └── Sidebar.tsx              # Nav (Inbox/Today/Activity), projects
│   ├── views/
│   │   ├── InboxView.tsx            # Tasks grouped by project
│   │   ├── ActivityView.tsx         # Completed tasks + AI reports
│   │   └── SettingsView.tsx         # Theme, AI provider config
│   ├── tasks/
│   │   ├── TaskList.tsx             # Task list with inline add
│   │   └── TaskItem.tsx             # Single task with editing
│   └── ui/
│       ├── CalendarPicker.tsx       # Date picker
│       ├── ColorPicker.tsx          # Project/tag colors
│       └── EmojiAutocomplete.tsx    # ':' trigger emoji picker
└── styles/
    └── globals.css                  # Tailwind 4 theme variables
```

### Backend Structure

```
backend/
├── main.py                          # FastAPI app, CORS, startup
├── database.py                      # SQLite engine, session, pragmas
├── api/
│   ├── tasks.py                     # CRUD, complete, reorder
│   ├── projects.py                  # CRUD + board columns
│   ├── tags.py                      # CRUD
│   ├── views.py                     # Inbox, Today, Completed
│   ├── search.py                    # FTS5 full-text search
│   ├── settings.py                  # AI provider config
│   └── reports.py                   # AI-powered daily summaries
├── models/
│   ├── task.py                      # Task, subtasks (self-ref)
│   ├── project.py                   # Project + BoardColumn
│   ├── tag.py                       # Tag + TaskTag junction
│   ├── reminder.py                  # Absolute/relative reminders
│   ├── settings.py                  # Singleton config row
│   └── sync_log.py                  # Change tracking
├── schemas/                         # Pydantic request/response models
└── services/                        # Business logic layer
```

FastAPI dependency injection (session, services) is centralized in `app.core.deps`; see [Backend dependency injection](backend-dependency-injection.md) for how to add and use dependencies.

---

## Database Schema (ERD)

```
┌──────────────┐       ┌──────────────────┐
│   projects   │       │   board_columns  │
├──────────────┤       ├──────────────────┤
│ id (ULID) PK │──┐    │ id (ULID) PK     │
│ name         │  │    │ project_id FK  ──│──┐
│ color        │  │    │ name             │  │
│ icon         │  │    │ position         │  │
│ view_mode    │  │    └──────────────────┘  │
│ sort_order   │  │                          │
│ deleted_at   │  │    ┌───────────────────┐ │
└──────────────┘  └────│ tasks             │ │
                       ├───────────────────┤ │
                  ┌────│ id (ULID) PK      │ │
                  │    │ title             │ │
                  │    │ notes             │ │
                  │    │ priority (0-4)    │ │
                  │    │ due_date          │ │
                  │    │ due_time          │ │
                  │    │ is_completed      │ │
                  │    │ project_id FK   ──│─┘
                  │    │ parent_task_id FK │──┐ (self-ref)
                  │    │ board_column_id   │  │
                  │    │ sort_order        │  │
                  │    │ recurrence_rule   │  │
                  │    │ deleted_at        │  │
                  │    └───────┬───────────┘  │
                  │            │              │
                  └────────────┘ (subtasks)   │
                                              │
┌──────────────┐     ┌──────────────┐         │
│    tags      │     │  task_tags   │         │
├──────────────┤     ├──────────────┤         │
│ id (ULID) PK │─────│ tag_id FK    │         │
│ name         │     │ task_id FK ──│─────────┘
│ color        │     └──────────────┘
└──────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  reminders   │     │   settings   │     │   sync_log   │
├──────────────┤     ├──────────────┤     ├──────────────┤
│ id (ULID) PK │     │ id='default' │     │ id PK        │
│ task_id FK   │     │ ai_provider  │     │ entity_type  │
│ type         │     │ ai_model     │     │ entity_id    │
│ trigger_at   │     │ api_key      │     │ operation    │
│ offset_mins  │     │ report_prompt│     │ sync_version │
└──────────────┘     └──────────────┘     └──────────────┘
```

**Key design choices:**
- **ULID** primary keys (sortable, timestamp-embedded)
- **Soft deletes** via `deleted_at` (no hard deletes)
- **WAL mode** for concurrent reads during writes
- **Self-referential** `parent_task_id` for subtasks

---

## API Endpoints

| Method | Endpoint                     | Description                    |
|--------|------------------------------|--------------------------------|
| GET    | `/api/health`                | Health check                   |
| GET    | `/api/tasks`                 | List tasks (with filters)      |
| POST   | `/api/tasks`                 | Create task                    |
| GET    | `/api/tasks/{id}`            | Get single task                |
| PATCH  | `/api/tasks/{id}`            | Update task                    |
| DELETE | `/api/tasks/{id}`            | Soft-delete task               |
| POST   | `/api/tasks/{id}/complete`   | Toggle completion              |
| POST   | `/api/tasks/bulk-complete`   | Complete all active tasks      |
| PATCH  | `/api/tasks/reorder`         | Batch reorder tasks            |
| GET    | `/api/projects`              | List projects                  |
| POST   | `/api/projects`              | Create project (+ columns)     |
| GET    | `/api/projects/{id}`         | Get project                    |
| PATCH  | `/api/projects/{id}`         | Update project                 |
| DELETE | `/api/projects/{id}`         | Delete project                 |
| GET    | `/api/projects/{id}/columns` | Get Kanban columns             |
| GET    | `/api/tags`                  | List tags                      |
| POST   | `/api/tags`                  | Create tag                     |
| PATCH  | `/api/tags/{id}`             | Update tag                     |
| DELETE | `/api/tags/{id}`             | Delete tag                     |
| GET    | `/api/views/inbox`           | Inbox view (grouped)           |
| GET    | `/api/views/today`           | Tasks due today or earlier     |
| GET    | `/api/views/completed`       | Completed tasks (30 days)      |
| GET    | `/api/search?q=`             | Full-text search (FTS5)        |
| GET    | `/api/settings/ai`           | Get AI settings                |
| PATCH  | `/api/settings/ai`           | Update AI settings             |
| POST   | `/api/reports/generate`      | Generate AI daily report       |

---

## Data Flow

```
User Interaction
       │
       ▼
┌─────────────────┐    HTTP (fetch)     ┌──────────────────┐
│  React Component │ ──────────────────► │  FastAPI Router   │
│  (TaskItem, etc) │                     │  (api/tasks.py)   │
└────────┬────────┘                     └────────┬─────────┘
         │                                       │
         │  React Query                          │  SQLAlchemy
         │  (cache + invalidate)                 │  (ORM)
         │                                       │
         ▼                                       ▼
┌─────────────────┐                     ┌──────────────────┐
│  Zustand Store   │                     │  SQLite Database  │
│  (UI state only) │                     │  (WAL mode)       │
└─────────────────┘                     └──────────────────┘
```

**State management split:**
- **React Query** — all server data (tasks, projects, tags, settings)
- **Zustand** — UI-only state (active route, sidebar, theme) persisted to `localStorage`

---

## Runtime Configuration

| Setting              | Value                                    |
|----------------------|------------------------------------------|
| Backend host         | `127.0.0.1:18429`                        |
| Frontend dev server  | `localhost:1420` (Vite HMR on 1421)      |
| Database path        | `%APPDATA%/com.todo.app/todo.db`         |
| Window size          | 380 x 700 px (min 320 x 400)            |
| Always on top        | Toggleable via header pin button         |
| CORS origins         | `localhost:1420`, `tauri://localhost`     |

---

## Development Workflow

```
dev.bat
  │
  ├─► taskkill node.exe, python.exe, todo.exe
  │
  └─► python scripts/dev.py
        │
        ├─► uvicorn backend.main:app  (port 18429, reload)
        │
        ├─► wait 2s for backend boot
        │
        └─► npx tauri dev  (Vite + Tauri webview)
```

**Never run `npx tauri dev` alone** — it only starts the frontend, not the backend sidecar.
