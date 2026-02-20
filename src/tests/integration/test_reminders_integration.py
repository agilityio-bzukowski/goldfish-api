"""Integration tests for /api/reminders."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

BASE = "/api/reminders"
TASKS_BASE = "/api/tasks"


def _create_task(client: TestClient, title: str = "Test Task") -> str:
    r = client.post(TASKS_BASE, json={"title": title})
    assert r.status_code == 201
    return r.json()["id"]


def _parse_remind_at(s: str) -> datetime:
    """Parse remind_at string (API may omit timezone suffix) and normalize to UTC for comparison."""
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def test_get_upcoming_empty(client_with_test_db: TestClient) -> None:
    """GET /api/reminders/upcoming returns 200 and empty list when no reminders exist."""
    response = client_with_test_db.get(f"{BASE}/upcoming")
    assert response.status_code == 200
    assert response.json() == []


def test_get_upcoming_returns_created_reminder(client_with_test_db: TestClient) -> None:
    """After creating a task and a reminder, get upcoming returns the reminder."""
    task_id = _create_task(client_with_test_db)
    remind_at = "2026-03-01T10:00:00+00:00"
    create_resp = client_with_test_db.post(
        BASE,
        json={"task_id": task_id, "remind_at": remind_at},
    )
    assert create_resp.status_code == 201
    reminder_id = create_resp.json()["id"]

    response = client_with_test_db.get(f"{BASE}/upcoming")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["id"] == reminder_id
    assert items[0]["task_id"] == task_id
    # API may serialize datetime with or without timezone suffix
    assert _parse_remind_at(items[0]["remind_at"]
                            ) == _parse_remind_at(remind_at)
    assert items[0]["is_fired"] is False
    assert items[0]["type"] == "absolute"


def test_get_upcoming_excludes_fired(client_with_test_db: TestClient) -> None:
    """Fired reminders are excluded from upcoming."""
    task_id = _create_task(client_with_test_db)
    remind_at = "2026-03-01T10:00:00+00:00"
    create_resp = client_with_test_db.post(
        BASE,
        json={"task_id": task_id, "remind_at": remind_at},
    )
    assert create_resp.status_code == 201
    reminder_id = create_resp.json()["id"]

    fire_resp = client_with_test_db.patch(f"{BASE}/{reminder_id}/fire")
    assert fire_resp.status_code == 200
    assert fire_resp.json()["is_fired"] is True

    response = client_with_test_db.get(f"{BASE}/upcoming")
    assert response.status_code == 200
    assert response.json() == []


def test_get_upcoming_excludes_deleted(client_with_test_db: TestClient) -> None:
    """Soft-deleted reminders are excluded from upcoming."""
    task_id = _create_task(client_with_test_db)
    remind_at = "2026-03-01T10:00:00+00:00"
    create_resp = client_with_test_db.post(
        BASE,
        json={"task_id": task_id, "remind_at": remind_at},
    )
    assert create_resp.status_code == 201
    reminder_id = create_resp.json()["id"]

    delete_resp = client_with_test_db.delete(f"{BASE}/{reminder_id}")
    assert delete_resp.status_code == 204

    response = client_with_test_db.get(f"{BASE}/upcoming")
    assert response.status_code == 200
    assert response.json() == []


def test_create_reminder(client_with_test_db: TestClient) -> None:
    """POST /api/reminders with task_id and remind_at returns 201 and the created reminder."""
    task_id = _create_task(client_with_test_db)
    remind_at = "2026-04-15T14:30:00+00:00"
    response = client_with_test_db.post(
        BASE,
        json={"task_id": task_id, "remind_at": remind_at},
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["task_id"] == task_id
    assert _parse_remind_at(data["remind_at"]) == _parse_remind_at(remind_at)
    assert data["type"] == "absolute"
    assert data["is_fired"] is False
    assert data["relative_minutes"] is None
    assert "created_at" in data
    assert "updated_at" in data


def test_create_reminder_404_invalid_task(client_with_test_db: TestClient) -> None:
    """POST /api/reminders with non-existent task_id returns 404."""
    fake_task_id = "00000000-0000-0000-0000-000000000000"
    remind_at = "2026-04-15T14:30:00+00:00"
    response = client_with_test_db.post(
        BASE,
        json={"task_id": fake_task_id, "remind_at": remind_at},
    )
    assert response.status_code == 404
    assert "Task not found" in response.json().get("detail", "")


def test_delete_reminder(client_with_test_db: TestClient) -> None:
    """DELETE /api/reminders/{id} returns 204; reminder no longer in upcoming."""
    task_id = _create_task(client_with_test_db)
    remind_at = "2026-03-01T10:00:00+00:00"
    create_resp = client_with_test_db.post(
        BASE,
        json={"task_id": task_id, "remind_at": remind_at},
    )
    assert create_resp.status_code == 201
    reminder_id = create_resp.json()["id"]

    response = client_with_test_db.delete(f"{BASE}/{reminder_id}")
    assert response.status_code == 204

    upcoming = client_with_test_db.get(f"{BASE}/upcoming")
    assert upcoming.status_code == 200
    assert not any(r["id"] == reminder_id for r in upcoming.json())


def test_delete_reminder_404(client_with_test_db: TestClient) -> None:
    """DELETE /api/reminders/{id} returns 404 for unknown id."""
    response = client_with_test_db.delete(
        f"{BASE}/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404
    assert "Reminder not found" in response.json().get("detail", "")


def test_fire_reminder(client_with_test_db: TestClient) -> None:
    """PATCH /api/reminders/{id}/fire returns 200 and is_fired true; excluded from upcoming."""
    task_id = _create_task(client_with_test_db)
    remind_at = "2026-03-01T10:00:00+00:00"
    create_resp = client_with_test_db.post(
        BASE,
        json={"task_id": task_id, "remind_at": remind_at},
    )
    assert create_resp.status_code == 201
    reminder_id = create_resp.json()["id"]

    response = client_with_test_db.patch(f"{BASE}/{reminder_id}/fire")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == reminder_id
    assert data["is_fired"] is True

    upcoming = client_with_test_db.get(f"{BASE}/upcoming")
    assert upcoming.status_code == 200
    assert not any(r["id"] == reminder_id for r in upcoming.json())


def test_fire_reminder_404(client_with_test_db: TestClient) -> None:
    """PATCH /api/reminders/{id}/fire returns 404 for unknown id."""
    response = client_with_test_db.patch(
        f"{BASE}/00000000-0000-0000-0000-000000000000/fire"
    )
    assert response.status_code == 404
    assert "Reminder not found" in response.json().get("detail", "")
