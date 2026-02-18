# Task Management Backend

FastAPI backend with Poetry, SQLModel, Supabase, and Alembic.

## Stack

| Component | Choice |
|-----------|--------|
| Backend | FastAPI, Uvicorn, Python 3.11+ |
| Dependency management | Poetry |
| ORM & validation | SQLModel (SQLAlchemy + Pydantic) |
| Database | Supabase (PostgreSQL) |
| Migrations | Alembic |

## Setup

1. **Install dependencies**

   ```bash
   cd backend
   poetry install
   ```

2. **Environment**

   Copy `.env.example` to `.env` and set `DATABASE_URL` to your Supabase PostgreSQL connection string (use `postgresql+psycopg2://...` for the sync driver).

3. **Migrations**

   ```bash
   poetry run alembic revision --autogenerate -m "initial"
   poetry run alembic upgrade head
   ```

4. **Run**

   ```bash
   make run
   # or: PYTHONPATH=src poetry run uvicorn app.main:app --reload
   ```

   API: http://127.0.0.1:8000  
   Docs: http://127.0.0.1:8000/docs

## VS Code / Cursor – virtual environment

Open the **backend** folder in VS Code (or Cursor). The workspace is configured to use the Poetry venv.

- **Select interpreter:** `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux) → “Python: Select Interpreter” → choose `.venv (Poetry)` or the path ending in `backend/.venv/bin/python`.
- **Auto-activate in terminal:** With `.vscode/settings.json` in place, new terminals use the venv (prompt shows `(.venv)`).
- **Run/Debug:** Use the “Run and Debug” panel (or F5). Examples in `.vscode/launch.json`:
  - **FastAPI: run** – start the API with the debugger (reload enabled).
  - **Pytest: current file** – run tests in the active file under the debugger.
  - **Pytest: all tests** – run the full test suite under the debugger.
- **Tasks:** `Cmd+Shift+P` → “Tasks: Run Task” → “Run FastAPI server” or “Run tests”.

## Project layout

```
backend/
├── app/
│   ├── api/              # API routes
│   ├── core/             # Dependencies, shared code
│   ├── models/           # SQLModel table models
│   ├── schemas/          # SQLModel schemas (request/response, no table=True)
│   ├── config.py         # Settings (pydantic-settings)
│   ├── database.py       # Engine & session (SQLModel)
│   └── main.py           # FastAPI app
├── alembic/              # Migrations
├── .env.example
├── alembic.ini
├── pyproject.toml
└── README.md
```

# 
