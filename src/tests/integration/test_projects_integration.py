"""Integration tests for /api/projects."""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

BASE = "/api/projects"


def test_create_project(client_with_test_db: TestClient) -> None:
    """POST /api/projects returns 201 and the created project."""
    response = client_with_test_db.post(
        BASE,
        json={
            "name": "My Project",
            "description": "A test project",
            "color": "#6366f1",
            "icon": "folder",
            "view_mode": "list",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == "My Project"
    assert data["description"] == "A test project"
    assert data["color"] == "#6366f1"
    assert data["icon"] == "folder"
    assert data["view_mode"] == "list"
    assert data["is_archived"] is False
    assert data["task_count"] == 0
    assert "created_at" in data
    assert "updated_at" in data


def test_list_projects_after_create(client_with_test_db: TestClient) -> None:
    """GET /api/projects returns the created project."""
    client_with_test_db.post(
        BASE,
        json={"name": "Listed Project", "description": "", "color": "#ff0000"},
    )
    response = client_with_test_db.get(BASE)
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["name"] == "Listed Project"
    assert items[0]["task_count"] == 0


def test_get_project(client_with_test_db: TestClient) -> None:
    """GET /api/projects/{id} returns the project with task_count."""
    create_resp = client_with_test_db.post(
        BASE, json={"name": "Get me", "description": "Desc"}
    )
    assert create_resp.status_code == 201
    project_id = create_resp.json()["id"]
    response = client_with_test_db.get(f"{BASE}/{project_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Get me"
    assert data["description"] == "Desc"
    assert data["task_count"] == 0


def test_get_project_404(client_with_test_db: TestClient) -> None:
    """GET /api/projects/{id} returns 404 for unknown id."""
    response = client_with_test_db.get(
        f"{BASE}/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


def test_patch_project(client_with_test_db: TestClient) -> None:
    """PATCH /api/projects/{id} updates the project."""
    create_resp = client_with_test_db.post(
        BASE, json={"name": "Original", "color": "#111111"}
    )
    assert create_resp.status_code == 201
    project_id = create_resp.json()["id"]
    response = client_with_test_db.patch(
        f"{BASE}/{project_id}",
        json={"name": "Updated", "color": "#222222", "is_archived": True},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated"
    assert data["color"] == "#222222"
    assert data["is_archived"] is True


def test_delete_project_soft(client_with_test_db: TestClient) -> None:
    """DELETE /api/projects/{id} soft-deletes; project no longer in list."""
    create_resp = client_with_test_db.post(
        BASE, json={"name": "To delete", "description": ""}
    )
    assert create_resp.status_code == 201
    project_id = create_resp.json()["id"]
    response = client_with_test_db.delete(f"{BASE}/{project_id}")
    assert response.status_code == 204
    list_resp = client_with_test_db.get(BASE)
    assert list_resp.status_code == 200
    assert not any(p["id"] == project_id for p in list_resp.json())


def test_delete_project_unassigns_tasks(client_with_test_db: TestClient) -> None:
    """DELETE /api/projects/{id} sets project_id=null on its tasks (move to Inbox)."""
    create_proj = client_with_test_db.post(
        BASE, json={"name": "Project with tasks", "description": ""}
    )
    assert create_proj.status_code == 201
    project_id = create_proj.json()["id"]

    create_task = client_with_test_db.post(
        "/api/tasks",
        json={"title": "Task in project", "project_id": project_id},
    )
    assert create_task.status_code == 201
    task_id = create_task.json()["id"]

    client_with_test_db.delete(f"{BASE}/{project_id}")
    task_resp = client_with_test_db.get(f"/api/tasks/{task_id}")
    assert task_resp.status_code == 200
    assert task_resp.json()["project_id"] is None


def test_delete_project_404(client_with_test_db: TestClient) -> None:
    """DELETE /api/projects/{id} returns 404 for unknown id."""
    response = client_with_test_db.delete(
        f"{BASE}/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


def test_project_task_count(client_with_test_db: TestClient) -> None:
    """task_count is number of non-deleted, incomplete tasks in project."""
    create_proj = client_with_test_db.post(
        BASE, json={"name": "Count project", "description": ""}
    )
    assert create_proj.status_code == 201
    project_id = create_proj.json()["id"]

    client_with_test_db.post(
        "/api/tasks",
        json={"title": "Incomplete", "project_id": project_id},
    )
    client_with_test_db.post(
        "/api/tasks",
        json={"title": "Other incomplete", "project_id": project_id},
    )
    get_resp = client_with_test_db.get(f"{BASE}/{project_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["task_count"] == 2

    list_resp = client_with_test_db.get(BASE)
    proj = next(p for p in list_resp.json() if p["id"] == project_id)
    assert proj["task_count"] == 2


def test_full_crud_flow(client_with_test_db: TestClient) -> None:
    """Create -> list -> patch -> get -> delete in one flow."""
    r1 = client_with_test_db.post(
        BASE, json={"name": "CRUD Project", "description": "D", "color": "#abc"}
    )
    assert r1.status_code == 201
    project_id = r1.json()["id"]

    r2 = client_with_test_db.get(BASE)
    assert r2.status_code == 200
    assert any(p["id"] == project_id for p in r2.json())

    r3 = client_with_test_db.patch(
        f"{BASE}/{project_id}", json={"name": "CRUD Project Updated"}
    )
    assert r3.status_code == 200
    assert r3.json()["name"] == "CRUD Project Updated"

    r4 = client_with_test_db.get(f"{BASE}/{project_id}")
    assert r4.status_code == 200
    assert r4.json()["name"] == "CRUD Project Updated"

    r5 = client_with_test_db.delete(f"{BASE}/{project_id}")
    assert r5.status_code == 204

    r6 = client_with_test_db.get(BASE)
    assert not any(p["id"] == project_id for p in r6.json())
