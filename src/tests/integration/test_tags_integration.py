import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

BASE = "/api/tags"


def test_list_tags_empty(client_with_test_db: TestClient) -> None:
    """GET /api/tags returns empty list when no tags exist."""
    response = client_with_test_db.get(BASE)
    assert response.status_code == 200
    assert response.json() == []


def test_create_tag(client_with_test_db: TestClient) -> None:
    """POST /api/tags returns 201 and the created tag with id, name, color, timestamps."""
    response = client_with_test_db.post(
        BASE,
        json={"name": "Integration Tag", "color": "#ff0000"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == "Integration Tag"
    assert data["color"] == "#ff0000"
    assert "created_at" in data
    assert "updated_at" in data


def test_list_tags_after_create(client_with_test_db: TestClient) -> None:
    """GET /api/tags returns the tag created in the same session."""
    create_resp = client_with_test_db.post(
        BASE,
        json={"name": "Listed Tag", "color": "#00ff00"},
    )
    assert create_resp.status_code == 201

    response = client_with_test_db.get(BASE)
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["name"] == "Listed Tag"
    assert items[0]["color"] == "#00ff00"
    assert "id" in items[0]


def test_patch_tag(client_with_test_db: TestClient) -> None:
    """PATCH /api/tags/{id} updates the tag and returns 200."""
    create_resp = client_with_test_db.post(
        BASE,
        json={"name": "To Update", "color": "#111111"},
    )
    assert create_resp.status_code == 201
    tag_id = create_resp.json()["id"]

    response = client_with_test_db.patch(
        f"{BASE}/{tag_id}",
        json={"color": "#222222"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == tag_id
    assert data["name"] == "To Update"
    assert data["color"] == "#222222"


def test_patch_tag_404(client_with_test_db: TestClient) -> None:
    """PATCH /api/tags/{id} returns 404 for unknown id."""
    response = client_with_test_db.patch(
        f"{BASE}/00000000-0000-0000-0000-000000000000",
        json={"name": "No"},
    )
    assert response.status_code == 404


def test_delete_tag(client_with_test_db: TestClient) -> None:
    """DELETE /api/tags/{id} returns 204 and removes the tag."""
    create_resp = client_with_test_db.post(
        BASE,
        json={"name": "To Delete", "color": "#333333"},
    )
    assert create_resp.status_code == 201
    tag_id = create_resp.json()["id"]

    response = client_with_test_db.delete(f"{BASE}/{tag_id}")
    assert response.status_code == 204

    list_resp = client_with_test_db.get(BASE)
    assert list_resp.status_code == 200
    assert not any(t["id"] == tag_id for t in list_resp.json())


def test_delete_tag_404(client_with_test_db: TestClient) -> None:
    """DELETE /api/tags/{id} returns 404 for unknown id."""
    response = client_with_test_db.delete(
        f"{BASE}/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


def test_full_crud_flow(client_with_test_db: TestClient) -> None:
    """Create -> list -> patch -> get -> delete in one flow."""
    # Create
    r1 = client_with_test_db.post(
        BASE, json={"name": "CRUD Tag", "color": "#abc"})
    assert r1.status_code == 201
    tag_id = r1.json()["id"]

    # List
    r2 = client_with_test_db.get(BASE)
    assert r2.status_code == 200
    assert any(t["id"] == tag_id for t in r2.json())

    # Patch
    r3 = client_with_test_db.patch(
        f"{BASE}/{tag_id}", json={"name": "CRUD Tag Updated"})
    assert r3.status_code == 200
    assert r3.json()["name"] == "CRUD Tag Updated"

    # Delete
    r4 = client_with_test_db.delete(f"{BASE}/{tag_id}")
    assert r4.status_code == 204

    # Gone from list
    r5 = client_with_test_db.get(BASE)
    assert r5.status_code == 200
    assert not any(t["id"] == tag_id for t in r5.json())
