# Backend: Dependency Injection

This doc describes how FastAPI dependency injection is structured in this project and how to add or use dependencies.

## Where dependencies live

All FastAPI dependency **providers** and **`*Dep` type aliases** are defined in a single module:

- **`backend/src/app/core/deps.py`**

Do **not** define `Depends(...)` or service factories in router modules (`api/*.py`). Routers only import the shared type aliases (e.g. `TagServiceDep`) from `app.core.deps` and use them as route parameters.

## Pattern

We follow FastAPI’s recommended approach (see [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies)):

1. **`Annotated` + `Depends`**: Use `Annotated[SomeType, Depends(dependency)]` for parameters.
2. **Shared type aliases**: Define once in `core/deps.py`, reuse everywhere:
   - `SessionDep` — database session per request
   - `TagServiceDep` — `TagService` instance (and future `*ServiceDep` for other services)
3. **Sub-dependencies**: A dependency function can depend on another by declaring it as a parameter (e.g. `get_tag_service(session: SessionDep) -> TagService`). FastAPI resolves the tree automatically.

## Adding a new service

1. **Implement the service** in `app.services.*` (e.g. `app.services.tasks.TaskService`).
2. **Register it in `core/deps.py`**:
   - Add a provider: `def get_*_service(session: SessionDep) -> *Service: return *Service(session)`
   - Add the type alias: `*ServiceDep = Annotated[*Service, Depends(get_*_service)]`
3. **Use it in the router**: Import only `*ServiceDep` from `app.core.deps` and add it as a path operation parameter, e.g. `def list_items(*_service: *ServiceDep)`.

Example for a hypothetical `TaskService`:

```python
# In core/deps.py
def get_task_service(session: SessionDep) -> TaskService:
    return TaskService(session)

TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
```

```python
# In api/tasks.py
from app.core.deps import TaskServiceDep

@router.get("")
def list_tasks(task_service: TaskServiceDep):
    return task_service.get_tasks()
```

## Database session

- **Session creation** lives in **`app.db.session`** (engine and `get_db`). `core.deps` imports `get_db` from `app.db.session` and builds `SessionDep` from it.
- **Tests** that need a test database override the dependency:
  - `app.dependency_overrides[get_db] = override_get_db`
  - Import `get_db` from **`app.db.session`** in tests (same callable the app uses).

## Summary checklist

- One place for dependencies: **`core/deps.py`**.
- Routers only import **`*Dep`** aliases from `app.core.deps`; no local `Depends(...)` or service constructors in routers.
- New services: add **`get_*_service`** and **`*ServiceDep`** in `core/deps.py`, then use **`*ServiceDep`** in the relevant router.
