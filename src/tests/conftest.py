"""Pytest fixtures."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.schema import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture
def client_with_test_db() -> Generator[TestClient, None, None]:
    """
    FastAPI test client with get_db overridden to use an isolated SQLite DB.

    Each test gets a fresh temp DB file so tests don't share state.
    Follows FastAPI's recommended pattern: app.dependency_overrides for testing.
    """
    from app.core.config import settings

    if not settings.database_url.startswith("sqlite"):
        pytest.skip(
            "client_with_test_db only supports SQLite (use test DB URL in CI)")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        test_db_path = Path(f.name)
    test_db_url = f"sqlite:///{test_db_path}"
    test_engine = create_engine(
        test_db_url,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(test_engine)

    def override_get_db() -> Generator[Session, None, None]:
        with Session(test_engine) as session:
            yield session

    # FastAPI’s built-in way to swap a dependency in tests.
    app.dependency_overrides[get_db] = override_get_db

    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        test_engine.dispose()
        try:
            test_db_path.unlink(missing_ok=True)
        except OSError:
            pass
