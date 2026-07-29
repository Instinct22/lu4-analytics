"""Shared fixtures for smoke tests (no real Postgres required)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.deps import get_current_user, hash_password
from database import get_db
from main import app
from models.user import User


@pytest.fixture
def mock_db():
    db = MagicMock()
    # Empty role_permissions → fall back to DEFAULT_PERMISSIONS for the user's role
    db.scalars.return_value.all.return_value = []
    return db


@pytest.fixture
def test_user() -> User:
    return User(
        id=uuid.uuid4(),
        username="tester",
        password_hash=hash_password("secret"),
        role="admin",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def client(mock_db, test_user):
    def override_db():
        yield mock_db

    def override_user():
        return test_user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def anon_client(mock_db):
    """Client without auth override — protected routes should 401."""

    def override_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def scalars_by_model(rows_by_model: dict[str, list]):
    """Route db.scalars() by queried model so permission lookups stay empty."""

    def handler(stmt):
        entity = stmt.column_descriptions[0]["entity"]
        rows = rows_by_model.get(entity.__name__, [])
        return SimpleNamespace(all=lambda: list(rows))

    return handler


def make_entity(**kwargs):
    defaults = dict(
        id=uuid.uuid4(),
        entity_key="item:1",
        entity_type="item",
        external_id=1,
        name="Short Sword",
        display_name="Short Sword",
        name_normalized="short sword",
        slug="1-short-sword",
        url="/lu4/item/1-short-sword",
        source_url=None,
        summary=None,
        stats={},
        materials=[],
        content_md="# Short Sword",
        category_id=None,
        image_path=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)
