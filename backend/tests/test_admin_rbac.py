"""RBAC: superadmin, admin ownership, feature gates."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.deps import get_current_user, hash_password, user_has_permission
from core.permissions import PERMISSIONS
from database import get_db
from main import app
from models.user import User
from tests.conftest import scalars_by_model


@pytest.fixture
def superadmin_user() -> User:
    return User(
        id=uuid.uuid4(),
        username="admin",
        password_hash=hash_password("secret"),
        role="superadmin",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def regular_admin() -> User:
    return User(
        id=uuid.uuid4(),
        username="subadmin",
        password_hash=hash_password("secret"),
        role="admin",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


def test_superadmin_bypasses_all_permissions(mock_db, superadmin_user):
    assert user_has_permission(mock_db, superadmin_user, "admin.logs_view")
    assert user_has_permission(mock_db, superadmin_user, "feature.craft_warehouse")
    assert len([p for p in PERMISSIONS if user_has_permission(mock_db, superadmin_user, p)]) == len(
        PERMISSIONS
    )


def test_admin_cannot_access_roles_without_permission(client, mock_db, regular_admin):
    app.dependency_overrides[get_current_user] = lambda: regular_admin
    mock_db.scalars.side_effect = scalars_by_model({"RolePermission": []})
    r = client.get("/api/admin/roles")
    assert r.status_code == 403
    app.dependency_overrides.clear()


def test_admin_cannot_access_logs_without_permission(client, mock_db, regular_admin):
    app.dependency_overrides[get_current_user] = lambda: regular_admin
    r = client.get("/api/admin/login-logs")
    assert r.status_code == 403
    app.dependency_overrides.clear()


def test_superadmin_can_access_logs(client, mock_db, superadmin_user):
    app.dependency_overrides[get_current_user] = lambda: superadmin_user
    mock_db.scalar.return_value = 0
    mock_db.scalars.side_effect = scalars_by_model({"LoginLog": []})
    r = client.get("/api/admin/login-logs")
    assert r.status_code == 200
    app.dependency_overrides.clear()


def test_list_users_filters_for_admin(client, mock_db, regular_admin):
    own_id = regular_admin.id
    other_admin_id = uuid.uuid4()
    users = [
        User(
            id=uuid.uuid4(),
            username="visible",
            password_hash="x",
            role="user",
            is_active=True,
            created_by_id=own_id,
        ),
        User(
            id=uuid.uuid4(),
            username="hidden",
            password_hash="x",
            role="user",
            is_active=True,
            created_by_id=other_admin_id,
        ),
        User(
            id=uuid.uuid4(),
            username="super",
            password_hash="x",
            role="superadmin",
            is_active=True,
            created_by_id=None,
        ),
    ]

    app.dependency_overrides[get_current_user] = lambda: regular_admin
    mock_db.scalars.side_effect = scalars_by_model({"RolePermission": [], "User": [users[0]]})
    r = client.get("/api/admin/users")
    assert r.status_code == 200
    names = [u["username"] for u in r.json()]
    assert names == ["visible"]
    app.dependency_overrides.clear()


def test_raid_timers_empty_without_view_permission(client, mock_db):
    driver = User(
        id=uuid.uuid4(),
        username="driver1",
        password_hash=hash_password("secret"),
        role="driver",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    app.dependency_overrides[get_current_user] = lambda: driver
    mock_db.scalars.side_effect = scalars_by_model({"RolePermission": [], "RaidBossTimer": []})
    r = client.get("/api/raid/timers")
    assert r.status_code == 403
    app.dependency_overrides.clear()


def test_craft_owned_sync_blocked_for_admin(client, mock_db, regular_admin):
    app.dependency_overrides[get_current_user] = lambda: regular_admin
    mock_db.get.return_value = None
    r = client.put("/api/me/preferences/craft_owned", json={"payload": {"1864": 5}})
    assert r.status_code == 403
    app.dependency_overrides.clear()


def test_craft_owned_sync_allowed_for_user(craft_client, mock_db):
    mock_db.get.return_value = None
    r = craft_client.put("/api/me/preferences/craft_owned", json={"payload": {"1864": 5}})
    assert r.status_code == 200


def test_craft_cart_sync_allowed_for_user(craft_client, mock_db):
    mock_db.get.return_value = None
    r = craft_client.put(
        "/api/me/preferences/craft_cart",
        json={"payload": {"2424": {"qty": 1, "variant": 0}}},
    )
    assert r.status_code == 200


def test_raid_visibility_write_blocked_for_admin(client, mock_db, regular_admin):
    app.dependency_overrides[get_current_user] = lambda: regular_admin
    mock_db.scalars.side_effect = scalars_by_model({"RolePermission": []})
    r = client.put("/api/raid/visibility", json={"hiddenIds": [25025]})
    assert r.status_code == 403
    app.dependency_overrides.clear()


def test_raid_visibility_write_allowed_for_user(craft_client, mock_db):
    mock_db.get.return_value = None
    r = craft_client.put("/api/raid/visibility", json={"hiddenIds": [25025, 25044]})
    assert r.status_code == 200
    assert r.json()["hiddenIds"] == [25025, 25044]


def test_raid_visibility_read_returns_global_list(craft_client, mock_db):
    mock_db.get.return_value = SimpleNamespace(key="raid_hidden", value={"hiddenIds": [25025]})
    r = craft_client.get("/api/raid/visibility")
    assert r.status_code == 200
    assert r.json() == {"hiddenIds": [25025]}


def test_quick_create_requires_permission(client, mock_db):
    driver = User(
        id=uuid.uuid4(),
        username="driver1",
        password_hash=hash_password("secret"),
        role="driver",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    app.dependency_overrides[get_current_user] = lambda: driver
    mock_db.scalars.side_effect = scalars_by_model({"RolePermission": []})
    r = client.post("/api/admin/users/quick-create", json={"role": "user"})
    assert r.status_code == 403
    app.dependency_overrides.clear()
