"""Integration tests for /api/search."""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

BASE = "/api/search"
TASKS_BASE = "/api/tasks"


def _create_project(client: TestClient, name: str = "Test Project") -> str:
    r = client.post(
        "/api/projects",
        json={"name": name, "description": "", "color": "#6366f1", "icon": "folder"},
    )
    assert r.status_code == 201
    return r.json()["id"]


def test_search_no_q_returns_empty(client_with_test_db: TestClient) -> None:
    """GET /api/search without q returns 200 and empty list."""
    response = client_with_test_db.get(BASE)
    assert response.status_code == 200
    assert response.json() == []


def test_search_empty_q_returns_empty(client_with_test_db: TestClient) -> None:
    """GET /api/search?q= returns 200 and empty list."""
    response = client_with_test_db.get(BASE, params={"q": ""})
    assert response.status_code == 200
    assert response.json() == []


def test_search_no_results(client_with_test_db: TestClient) -> None:
    """GET /api/search?q=nonexistent returns 200 and empty list when no tasks match."""
    response = client_with_test_db.get(BASE, params={"q": "nonexistent"})
    assert response.status_code == 200
    assert response.json() == []


def test_search_matches_title(client_with_test_db: TestClient) -> None:
    """GET /api/search?q=term returns tasks whose title contains the term."""
    client_with_test_db.post(TASKS_BASE, json={"title": "Find me in title"})
    client_with_test_db.post(TASKS_BASE, json={"title": "Other task"})

    response = client_with_test_db.get(BASE, params={"q": "Find"})
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["title"] == "Find me in title"
    assert "id" in items[0]
    assert "tags" in items[0]
    assert "reminders" in items[0]


def test_search_matches_notes(client_with_test_db: TestClient) -> None:
    """GET /api/search?q=term returns tasks whose notes contain the term."""
    client_with_test_db.post(
        TASKS_BASE,
        json={"title": "Task A", "notes": "Secret keyword in notes"},
    )
    client_with_test_db.post(TASKS_BASE, json={"title": "Task B", "notes": "Other"})

    response = client_with_test_db.get(BASE, params={"q": "keyword"})
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["title"] == "Task A"
    assert "keyword" in (items[0].get("notes") or "").lower()


def test_search_case_insensitive(client_with_test_db: TestClient) -> None:
    """Search matches case-insensitively."""
    client_with_test_db.post(TASKS_BASE, json={"title": "CaseSensitive"})

    response = client_with_test_db.get(BASE, params={"q": "casesensitive"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "CaseSensitive"


def test_search_filter_by_project(client_with_test_db: TestClient) -> None:
    """GET /api/search?q=term&project_id=... returns only tasks in that project."""
    proj_a = _create_project(client_with_test_db, "Project A")
    proj_b = _create_project(client_with_test_db, "Project B")
    client_with_test_db.post(
        TASKS_BASE,
        json={"title": "Shared word", "project_id": proj_a},
    )
    client_with_test_db.post(
        TASKS_BASE,
        json={"title": "Shared word", "project_id": proj_b},
    )

    response = client_with_test_db.get(
        BASE, params={"q": "Shared", "project_id": proj_a}
    )
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["project_id"] == proj_a


def test_search_excludes_completed_by_default(client_with_test_db: TestClient) -> None:
    """By default search does not return completed tasks."""
    create_resp = client_with_test_db.post(
        TASKS_BASE, json={"title": "Done task"}
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]
    client_with_test_db.post(f"{TASKS_BASE}/{task_id}/complete")
    assert client_with_test_db.get(f"{TASKS_BASE}/{task_id}").json()["is_completed"]

    response = client_with_test_db.get(BASE, params={"q": "Done"})
    assert response.status_code == 200
    assert response.json() == []


def test_search_includes_completed_when_requested(
    client_with_test_db: TestClient,
) -> None:
    """GET /api/search?q=term&include_completed=true returns completed tasks."""
    create_resp = client_with_test_db.post(
        TASKS_BASE, json={"title": "Completed item"}
    )
    assert create_resp.status_code == 201
    task_id = create_resp.json()["id"]
    client_with_test_db.post(f"{TASKS_BASE}/{task_id}/complete")

    response = client_with_test_db.get(
        BASE, params={"q": "Completed", "include_completed": "true"}
    )
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["title"] == "Completed item"
    assert items[0]["is_completed"] is True
