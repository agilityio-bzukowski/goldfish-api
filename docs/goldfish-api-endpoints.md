# Task Management API — Endpoints

> **Note:** All request and response bodies below are suggestions and may change during implementation.
> **Stack:** FastAPI, SQLite, no authentication (desktop/Tauri app). Base path: `/api`.

---

## Conventions

- **IDs:** ULID strings (26 chars, sortable by creation time).
- **Timestamps:** ISO 8601 UTC, e.g. `"2026-02-16T14:30:00.000"`.
- **Deletes:** Soft delete only (`deleted_at` set); resources are never physically removed.
- **Errors:** Use the default messages below for consistency. Validation errors (422) use FastAPI’s default body; other errors can use `{"detail": "<message>"}`.

### Default error responses

| Status | When to use | Default message |
|--------|-------------|-----------------|
| **400** | Bad request (e.g. missing AI key, invalid params) | See per-endpoint messages below. |
| **404** | Resource not found or soft-deleted | See per-endpoint messages below. |
| **409** | Conflict (e.g. duplicate name) | See per-endpoint messages below. |
| **422** | Validation error (body/query) | FastAPI default (field-level messages). |
| **500** | Unexpected server error | `"An unexpected error occurred. Please try again later."` |

---

## Health

### `GET /api/health`

Liveness check. No auth.

**Errors:** None.

```json
Response 200: {
  "status": "ok"
}
```

---

## Tasks

### `GET /api/tasks`

List tasks.

**Errors:** None (returns empty list if no matches). Default: top-level only (`parent_task_id` implied null), non-deleted. Responses include nested `tags`, `subtasks`, `reminders` (e.g. via `joinedload`).

| Query param       | Type    | Description |
|-------------------|---------|-------------|
| `project_id`      | string  | Filter by project. |
| `parent_task_id`  | string  | Filter by parent (use empty or omit for top-level). |
| `is_completed`    | boolean | Filter by completion. |
| `priority`        | int     | Filter by priority (0–4). |
| `due_date`        | string  | Filter by due date. |
| `sort_by`         | string  | Sort field. |
| `order`           | string  | Sort order. |
| `limit`           | int     | Page size. |
| `offset`          | int     | Pagination offset. |

```json
Response 200: [
  {
    "id": "string",
    "title": "string",
    "notes": "string",
    "notes_plain": "string",
    "is_completed": false,
    "completed_at": null,
    "priority": 0,
    "due_date": null,
    "due_time": null,
    "start_date": null,
    "project_id": null,
    "board_column_id": null,
    "parent_task_id": null,
    "sort_order": 0.0,
    "sort_order_board": 0.0,
    "recurrence_rule": null,
    "recurrence_parent_id": null,
    "created_at": "string",
    "updated_at": "string",
    "tags": [],
    "subtasks": [],
    "reminders": []
  }
]
```

### `POST /api/tasks`

Create a task. `sort_order` is auto-calculated (max existing + 1 in same parent). Tags attached via `tag_ids`.

**Errors:** **422** — Invalid body (e.g. missing `title`, `priority` not 0–4). (max existing + 1 in same parent). Tags attached via `tag_ids`.

```json
Body: {
  "title": "string",
  "notes": "",
  "priority": 0,
  "due_date": null,
  "due_time": null,
  "project_id": null,
  "board_column_id": null,
  "parent_task_id": null,
  "recurrence_rule": null,
  "tag_ids": []
}

Response 201: <TaskResponse>
```

### `GET /api/tasks/:id`

Single task with all relationships. 404 if not found or soft-deleted.

**Errors:** **404** — `"Task not found."`

```json
Response 200: <TaskResponse>
Response 404: { "detail": "Task not found." }
```

### `PATCH /api/tasks/:id`

Partial update (`exclude_unset=True`). `tag_ids` handled by replacing all task–tag links (delete existing, insert new). 404 if not found.

**Errors:** **404** — `"Task not found."` **422** — Invalid body (e.g. `priority` not 0–4).

```json
Body: {
  "title": null,
  "notes": null,
  "priority": null,
  "due_date": null,
  "due_time": null,
  "project_id": null,
  "board_column_id": null,
  "parent_task_id": null,
  "sort_order": null,
  "sort_order_board": null,
  "recurrence_rule": null,
  "tag_ids": null
}
(all fields optional)

Response 200: <TaskResponse>
Response 404: { "detail": "Task not found." }
```

### `DELETE /api/tasks/:id`

Soft delete. 404 if not found.

**Errors:** **404** — `"Task not found."`

```json
Response 204: no body
Response 404: { "detail": "Task not found." }
```

### `POST /api/tasks/:id/complete`

Toggle `is_completed`. Sets `completed_at` when completing, clears when un-completing.

**Errors:** **404** — `"Task not found."`

```json
Response 200: <TaskResponse>
Response 404: { "detail": "Task not found." }
```

### `POST /api/tasks/bulk-complete`

Complete all active (non-completed) tasks in a project.

**Errors:** **400** — `"Project ID is required."` (when `project_id` is missing or invalid).

```json
Query: ?project_id=<string>

Response 200: {
  "completed": 5
}
Response 400: { "detail": "Project ID is required." }
```

### `PATCH /api/tasks/reorder`

Batch update sort order.

**Errors:** **422** — Invalid body (e.g. missing or invalid `items`).

```json
Body: {
  "items": [
    { "id": "task_ulid_1", "sort_order": 1.0 },
    { "id": "task_ulid_2", "sort_order": 2.0 }
  ]
}

Response 204: no body
Response 422: { "detail": "Invalid reorder payload." }
```

---

## Projects

### `GET /api/projects`

List non-archived, non-deleted projects.

**Errors:** None (returns empty list if none). Each item includes computed `task_count` (non-deleted, non-completed tasks).

```json
Response 200: [
  {
    "id": "string",
    "name": "string",
    "description": "string",
    "color": "#6366f1",
    "icon": "folder",
    "view_mode": "list",
    "is_archived": false,
    "sort_order": 0.0,
    "created_at": "string",
    "updated_at": "string",
    "task_count": 0
  }
]
```

### `POST /api/projects`

Create project. Auto-creates 3 default board columns: "To Do" (sort 0), "In Progress" (sort 1), "Done" (sort 2, `is_done_column: true`).

**Errors:** **422** — Invalid body (e.g. missing `name`, invalid `view_mode`).: "To Do" (sort 0), "In Progress" (sort 1), "Done" (sort 2, `is_done_column: true`).

```json
Body: {
  "name": "string",
  "description": "",
  "color": "#6366f1",
  "icon": "folder",
  "view_mode": "list"
}

Response 201: <ProjectResponse>
```

### `GET /api/projects/:id`

Single project with `task_count`. 404 if not found or soft-deleted.

**Errors:** **404** — `"Project not found."`

```json
Response 200: <ProjectResponse>
Response 404: { "detail": "Project not found." }
```

### `PATCH /api/projects/:id`

Update name, description, color, icon, view_mode, is_archived, sort_order.

**Errors:** **404** — `"Project not found."` **422** — Invalid body.

```json
Body: {
  "name": null,
  "description": null,
  "color": null,
  "icon": null,
  "view_mode": null,
  "is_archived": null,
  "sort_order": null
}
(all optional)

Response 200: <ProjectResponse>
Response 404: { "detail": "Project not found." }
```

### `DELETE /api/projects/:id`

Soft delete. **Before** setting `deleted_at`, the API sets `project_id = NULL` on all tasks that belonged to this project (soft delete does not trigger FK cascade). 404 if not found.

**Errors:** **404** — `"Project not found."`

```json
Response 204: no body
Response 404: { "detail": "Project not found." }
```

### `GET /api/projects/:id/columns`

List board columns for the project, sorted by `sort_order`.

**Errors:** **404** — `"Project not found."`

```json
Response 200: [
  {
    "id": "string",
    "project_id": "string",
    "name": "string",
    "color": "#94a3b8",
    "sort_order": 0.0,
    "is_done_column": false,
    "created_at": "string",
    "updated_at": "string"
  }
]
```

---

## Tags

### `GET /api/tags`

All non-deleted tags, sorted by name.

**Errors:** None (returns empty list if none).

```json
Response 200: [
  {
    "id": "string",
    "name": "string",
    "color": "#8b5cf6",
    "created_at": "string",
    "updated_at": "string"
  }
]
```

### `POST /api/tags`

Create tag. 409 if a tag with the same name already exists.

**Errors:** **409** — `"A tag with this name already exists."` **422** — Invalid body (e.g. missing `name`).

```json
Body: {
  "name": "string",
  "color": "#8b5cf6"
}

Response 201: <TagResponse>
Response 409: { "detail": "A tag with this name already exists." }
```

### `PATCH /api/tags/:id`

Update name and/or color.

**Errors:** **404** — `"Tag not found."` **409** — `"A tag with this name already exists."` (if changing name) **422** — Invalid body.

```json
Body: {
  "name": null,
  "color": null
}
(both optional)

Response 200: <TagResponse>
Response 404: { "detail": "Tag not found." }
```

### `DELETE /api/tags/:id`

Soft delete. Does not delete tasks; junction table uses CASCADE for link removal.

**Errors:** **404** — `"Tag not found."`

```json
Response 204: no body
Response 404: { "detail": "Tag not found." }
```

---

## Views

Convenience endpoints for Inbox, Today, and Completed. All use `joinedload` for tags and reminders where applicable.

### `GET /api/views/inbox`

All top-level tasks (active + completed), ordered by `is_completed`, then `sort_order`. Frontend may group by project.

**Errors:** None (returns empty list if none).

### `GET /api/views/today`

Incomplete tasks where `due_date <= today`, sorted by `priority DESC`, `due_date`, `sort_order`. Includes overdue.

**Errors:** None (returns empty list if none).

### `GET /api/views/completed`

Completed tasks from the last N days, sorted by `completed_at DESC`.

**Errors:** **422** — Invalid `days` (e.g. &gt; 365). Default message: `"days must be between 1 and 365."`

```json
Query: ?days=30   (default 30, max 365)

Response 200: [ <TaskResponse>, ... ]
Response 422: { "detail": "days must be between 1 and 365." }
```

---

## Search

### `GET /api/search`

Full-text search over task title and notes (FTS5 if available, else LIKE). Results limited to 50.

**Errors:** **422** — Missing or invalid `q`. Default: `"Search query is required."`

```json
Query:
  ?q=term
  &project_id=<string>     (optional)
  &include_completed=false (optional)

Response 200: [ <TaskResponse>, ... ]
Response 422: { "detail": "Search query is required." }
```

---

## Reminders

### `POST /api/tasks/:id/reminders`

Create a reminder for a task. 404 if task does not exist or is soft-deleted.

**Errors:** **404** — `"Task not found."` **422** — Invalid body (e.g. missing or invalid `remind_at`, invalid `type`).

```json
Body: {
  "remind_at": "2026-02-16T14:30:00.000",
  "type": "absolute",
  "relative_minutes": null
}

Response 201: {
  "id": "string",
  "task_id": "string",
  "remind_at": "string",
  "type": "string",
  "relative_minutes": null,
  "is_fired": false,
  "created_at": "string",
  "updated_at": "string"
}
Response 404: { "detail": "Task not found." }
```

### `DELETE /api/reminders/:id`

Soft delete reminder.

**Errors:** **404** — `"Reminder not found."`

```json
Response 204: no body
Response 404: { "detail": "Reminder not found." }
```

### `GET /api/reminders/upcoming`

Unfired reminders due within the next N minutes. Includes `task_title` (via JOIN with Task).

**Errors:** None (returns empty list if none).

```json
Query: ?minutes=5

Response 200: [
  {
    "id": "string",
    "task_id": "string",
    "remind_at": "string",
    "type": "string",
    "relative_minutes": null,
    "is_fired": false,
    "created_at": "string",
    "updated_at": "string",
    "task_title": "string"
  }
]
```

### `PATCH /api/reminders/:id/fire`

Mark reminder as fired (`is_fired = true`). It will no longer appear in `upcoming`.

**Errors:** **404** — `"Reminder not found."`

```json
Response 200: <ReminderResponse>
Response 404: { "detail": "Reminder not found." }
```

---

## Settings (AI)

Singleton settings row (id `"default"`). GET auto-creates the row if missing.

### `GET /api/settings/ai`

Return AI-related settings. Creates default row if none exists.

**Errors:** None (singleton auto-created).

```json
Response 200: {
  "id": "default",
  "theme": "system",
  "default_project_id": null,
  "sidebar_collapsed": false,
  "last_sync_at": null,
  "cloud_user_id": null,
  "device_id": "LOCAL",
  "updated_at": "string",
  "ai_provider": "openai",
  "ai_model": "gpt-4o-mini",
  "ai_api_key": null,
  "ai_base_url": null,
  "ai_report_prompt": "Summarize what I accomplished today..."
}
```

### `PATCH /api/settings/ai`

Update only provided fields (provider, model, api_key, base_url, report_prompt, etc.).

**Errors:** **422** — Invalid body (e.g. invalid `ai_provider` or `view_mode`).

```json
Body: {
  "theme": null,
  "default_project_id": null,
  "sidebar_collapsed": null,
  "ai_provider": null,
  "ai_model": null,
  "ai_api_key": null,
  "ai_base_url": null,
  "ai_report_prompt": null
}
(all optional)

Response 200: <settings object>
```

---

## Reports

### `POST /api/reports/generate`

Generate an AI report for a given date using completed tasks. Uses settings from `/api/settings/ai`. 400 if API key required but not set (Ollama does not require a key).

**Errors:** **400** — `"AI API key not configured."` (when provider is OpenAI/Anthropic and key is missing). **422** — Invalid body (e.g. invalid `date`). **502** / **503** — `"AI service is temporarily unavailable."` (when upstream AI call fails).

```json
Body: {
  "date": "2026-02-16",
  "prompt": null
}
(both optional; date defaults to today, prompt to default report prompt)

Response 200: {
  "date": "2026-02-16",
  "task_count": 5,
  "report": "AI generated text..."
}
Response 400: { "detail": "AI API key not configured." }
Response 502: { "detail": "AI service is temporarily unavailable." }
```

---

## Response type reference

- **TaskResponse:** id, title, notes, notes_plain, is_completed, completed_at, priority, due_date, due_time, start_date, project_id, board_column_id, parent_task_id, sort_order, sort_order_board, recurrence_rule, recurrence_parent_id, created_at, updated_at, tags (TagResponse[]), subtasks (TaskResponse[]), reminders (ReminderResponse[]).
- **ProjectResponse:** id, name, description, color, icon, view_mode, is_archived, sort_order, created_at, updated_at, task_count.
- **BoardColumnResponse:** id, project_id, name, color, sort_order, is_done_column, created_at, updated_at.
- **TagResponse:** id, name, color, created_at, updated_at.
- **ReminderResponse:** id, task_id, remind_at, type, relative_minutes, is_fired, created_at, updated_at.
