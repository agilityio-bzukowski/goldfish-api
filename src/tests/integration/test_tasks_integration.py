"""Integration tests for /api/tasks."""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

BASE = "/api/tasks"


def _create_project(client: TestClient, name: str = "Test Project") -> str:
    r = client.post(
        "/api/projects",
        json={"name": name, "description": "",
              "color": "#6366f1", "icon": "folder"},
    )
    assert r.status_code == 201
    return r.json()["id"]


def test_list_tasks_empty(client_with_test_db: TestClient) -> None:
    """GET /api/tasks returns empty list when no tasks exist."""
    response = client_with_test_db.get(BASE)
    assert response.status_code == 200
    assert response.json() == []


def test_create_task(client_with_test_db: TestClient) -> None:
    """POST /api/tasks returns 201 and the created task."""
    response = client_with_test_db.post(
        BASE,
        json={"title": "My first task", "notes": "Some notes", "priority": 1},
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["title"] == "My first task"
    assert data["notes"] == "Some notes"
    assert data["priority"] == 1
    assert data["is_completed"] is False
    assert data["completed_at"] is None
    assert data["sort_order"] == 0.0
    assert "created_at" in data
    assert "updated_at" in data
    assert data["tags"] == []
    assert data["reminders"] == []


def test_create_task_with_project(client_with_test_db: TestClient) -> None:
    """POST /api/tasks with project_id links task to project."""
    project_id = _create_project(client_with_test_db)
    response = client_with_test_db.post(
        BASE,
        json={"title": "Task in project", "project_id": project_id},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["project_id"] == project_id


def test_list_tasks_after_create(client_with_test_db: TestClient) -> None:
    """GET /api/tasks returns created tasks."""
    client_with_test_db.post(BASE, json={"title": "Listed Task"})
    response = client_with_test_db.get(BASE)
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["title"] == "Listed Task"


def test_get_task(client_with_test_db: TestClient) -> None:
    """GET /api/tasks/{id} returns the task."""
    create_resp = client_with_test_db.post(
        BASE, json={"title": "Get me", "priority": 2}
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]
    response = client_with_test_db.get(f"{BASE}/{task_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Get me"
    assert response.json()["priority"] == 2


def test_get_task_404(client_with_test_db: TestClient) -> None:
    """GET /api/tasks/{id} returns 404 for unknown id."""
    response = client_with_test_db.get(
        f"{BASE}/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


def test_patch_task(client_with_test_db: TestClient) -> None:
    """PATCH /api/tasks/{id} updates the task."""
    create_resp = client_with_test_db.post(
        BASE, json={"title": "Original", "priority": 0}
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]
    response = client_with_test_db.patch(
        f"{BASE}/{task_id}",
        json={"title": "Updated", "priority": 3},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated"
    assert data["priority"] == 3


def test_patch_task_404(client_with_test_db: TestClient) -> None:
    """PATCH /api/tasks/{id} returns 404 for unknown id."""
    response = client_with_test_db.patch(
        f"{BASE}/00000000-0000-0000-0000-000000000000",
        json={"title": "No"},
    )
    assert response.status_code == 404


def test_delete_task_soft(client_with_test_db: TestClient) -> None:
    """DELETE /api/tasks/{id} soft-deletes; task no longer in list."""
    create_resp = client_with_test_db.post(
        BASE, json={"title": "To delete"}
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]
    response = client_with_test_db.delete(f"{BASE}/{task_id}")
    assert response.status_code == 204
    list_resp = client_with_test_db.get(BASE)
    assert list_resp.status_code == 200
    assert not any(t["id"] == task_id for t in list_resp.json())


def test_delete_task_404(client_with_test_db: TestClient) -> None:
    """DELETE /api/tasks/{id} returns 404 for unknown id."""
    response = client_with_test_db.delete(
        f"{BASE}/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


def test_complete_toggle(client_with_test_db: TestClient) -> None:
    """POST /api/tasks/{id}/complete toggles is_completed and sets/clears completed_at."""
    create_resp = client_with_test_db.post(BASE, json={"title": "Toggle me"})
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]
    assert create_resp.json()["is_completed"] is False
    assert create_resp.json()["completed_at"] is None

    complete_resp = client_with_test_db.post(f"{BASE}/{task_id}/complete")
    assert complete_resp.status_code == 200
    data = complete_resp.json()
    assert data["is_completed"] is True
    assert data["completed_at"] is not None

    uncomplete_resp = client_with_test_db.post(f"{BASE}/{task_id}/complete")
    assert uncomplete_resp.status_code == 200
    data2 = uncomplete_resp.json()
    assert data2["is_completed"] is False
    assert data2["completed_at"] is None


def test_complete_toggle_404(client_with_test_db: TestClient) -> None:
    """POST /api/tasks/{id}/complete returns 404 for unknown id."""
    response = client_with_test_db.post(
        f"{BASE}/00000000-0000-0000-0000-000000000000/complete"
    )
    assert response.status_code == 404


def test_bulk_complete(client_with_test_db: TestClient) -> None:
    """POST /api/tasks/bulk-complete completes all incomplete tasks in project."""
    project_id = _create_project(client_with_test_db)
    client_with_test_db.post(
        BASE, json={"title": "One", "project_id": project_id}
    )
    client_with_test_db.post(
        BASE, json={"title": "Two", "project_id": project_id}
    )
    response = client_with_test_db.post(
        f"{BASE}/bulk-complete?project_id={project_id}"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["completed"] == 2

    list_resp = client_with_test_db.get(BASE)
    tasks = [t for t in list_resp.json() if t["project_id"] == project_id]
    assert all(t["is_completed"] for t in tasks)


def test_reorder(client_with_test_db: TestClient) -> None:
    """PATCH /api/tasks/reorder updates sort_order for given tasks."""
    r1 = client_with_test_db.post(BASE, json={"title": "A"})
    r2 = client_with_test_db.post(BASE, json={"title": "B"})
    assert r1.status_code == 201 and r2.status_code == 201
    id_a, id_b = r1.json()["id"], r2.json()["id"]
    response = client_with_test_db.patch(
        f"{BASE}/reorder",
        json={"items": [{"id": id_a, "sort_order": 10.0},
                        {"id": id_b, "sort_order": 5.0}]},
    )
    assert response.status_code == 204
    list_resp = client_with_test_db.get(BASE)
    by_id = {t["id"]: t for t in list_resp.json()}
    assert by_id[id_a]["sort_order"] == 10.0
    assert by_id[id_b]["sort_order"] == 5.0


def test_full_crud_flow(client_with_test_db: TestClient) -> None:
    """Create -> list -> patch -> get -> complete -> delete in one flow."""
    r1 = client_with_test_db.post(
        BASE, json={"title": "CRUD Task", "priority": 1})
    assert r1.status_code == 201
    task_id = r1.json()["id"]

    r2 = client_with_test_db.get(BASE)
    assert r2.status_code == 200
    assert any(t["id"] == task_id for t in r2.json())

    r3 = client_with_test_db.patch(
        f"{BASE}/{task_id}", json={"title": "CRUD Task Updated", "priority": 2}
    )
    assert r3.status_code == 200
    assert r3.json()["title"] == "CRUD Task Updated"

    r4 = client_with_test_db.get(f"{BASE}/{task_id}")
    assert r4.status_code == 200
    assert r4.json()["priority"] == 2

    client_with_test_db.post(f"{BASE}/{task_id}/complete")
    r5 = client_with_test_db.delete(f"{BASE}/{task_id}")
    assert r5.status_code == 204

    r6 = client_with_test_db.get(BASE)
    assert not any(t["id"] == task_id for t in r6.json())
