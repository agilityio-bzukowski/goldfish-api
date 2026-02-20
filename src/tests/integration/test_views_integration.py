"""Integration tests for /api/views (inbox, today, completed)."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

BASE = "/api/views"
TASKS_BASE = "/api/tasks"


def _create_task(
    client: TestClient,
    title: str,
    *,
    due_date: str | None = None,
    complete: bool = False,
) -> str:
    """Create a task via API; optionally set due_date and/or complete it. Returns task id."""
    payload: dict = {"title": title}
    if due_date is not None:
        payload["due_date"] = due_date
    r = client.post(TASKS_BASE, json=payload)
    assert r.status_code == 201, r.text
    task_id = r.json()["id"]
    if complete:
        complete_r = client.post(f"{TASKS_BASE}/{task_id}/complete")
        assert complete_r.status_code == 200, complete_r.text
    return task_id


@pytest.fixture
def client_with_view_fixtures(client_with_test_db: TestClient) -> TestClient:
    """
    Client with tasks in different states for view testing:

    - inbox_only: no due_date, not completed → appears only in /inbox
    - today_task: due_date=today, not completed → appears in /inbox and /today
    - completed_task: completed → appears in /inbox and /completed
    """
    today = date.today().isoformat()
    _create_task(client_with_test_db, "Inbox only", due_date=None, complete=False)
    _create_task(client_with_test_db, "Today task", due_date=today, complete=False)
    _create_task(client_with_test_db, "Completed task", due_date=None, complete=True)
    return client_with_test_db

def test_get_inbox(client_with_view_fixtures: TestClient) -> None:
    """GET /api/views/inbox returns all non-deleted tasks (active + completed)."""
    response = client_with_view_fixtures.get(f"{BASE}/inbox")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 3
    titles = {t["title"] for t in items}
    assert titles == {"Inbox only", "Today task", "Completed task"}


def test_get_today(client_with_view_fixtures: TestClient) -> None:
    """GET /api/views/today returns incomplete tasks with no due_date or due_date <= today."""
    response = client_with_view_fixtures.get(f"{BASE}/today")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    titles = {t["title"] for t in items}
    assert titles == {"Inbox only", "Today task"}
    for t in items:
        assert t["is_completed"] is False


def test_get_completed(client_with_view_fixtures: TestClient) -> None:
    """GET /api/views/completed returns only completed tasks from the last N days."""
    response = client_with_view_fixtures.get(f"{BASE}/completed")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["title"] == "Completed task"
    assert items[0]["is_completed"] is True
    assert items[0]["completed_at"] is not None