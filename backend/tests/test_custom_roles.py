"""Custom roles: create, assign, permissions matrix."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from api.deps import get_current_user, hash_password
from database import get_db
from main import app
from models.custom_role import CustomRole
from models.permissions import RolePermission
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


def test_create_custom_role(superadmin_user, mock_db):
    def override_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = lambda: superadmin_user
    app.dependency_overrides[get_db] = override_db
    custom_roles: list[CustomRole] = []
    role_permissions: list[RolePermission] = []

    def get_side_effect(model, pk):
        if model is CustomRole:
            return next((r for r in custom_roles if r.key == pk), None)
        return None

    mock_db.get.side_effect = get_side_effect

    def add_side_effect(obj):
        if isinstance(obj, CustomRole):
            custom_roles.append(obj)
        elif isinstance(obj, RolePermission):
            role_permissions.append(obj)

    mock_db.add.side_effect = add_side_effect
    mock_db.scalars.side_effect = scalars_by_model(
        {"RolePermission": role_permissions, "CustomRole": custom_roles}
    )

    with TestClient(app) as client:
        r = client.post(
            "/api/admin/custom-roles",
            json={"label": "Moderator", "preset_role": "user"},
        )
    assert r.status_code == 201
    data = r.json()
    assert data["label"] == "Moderator"
    assert data["key"] == "moderator"
    assert any(isinstance(obj, CustomRole) for obj in custom_roles)
    assert any(rp.role == "moderator" for rp in role_permissions)
    app.dependency_overrides.clear()


def test_custom_role_appears_in_role_matrix(superadmin_user, mock_db):
    def override_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = lambda: superadmin_user
    app.dependency_overrides[get_db] = override_db
    custom = CustomRole(key="moderator", label="Moderator")
    perms = [
        RolePermission(role="moderator", permission="nav.craft", allowed=True),
    ]

    mock_db.scalars.side_effect = scalars_by_model(
        {"RolePermission": perms, "CustomRole": [custom]}
    )
    mock_db.get.side_effect = lambda model, pk: custom if model is CustomRole and pk == "moderator" else None

    with TestClient(app) as client:
        r = client.get("/api/admin/roles")
    assert r.status_code == 200
    roles = {row["role"]: row for row in r.json()}
    assert "moderator" in roles
    assert roles["moderator"]["label"] == "Moderator"
    app.dependency_overrides.clear()


def test_delete_custom_role_blocked_when_users_assigned(superadmin_user, mock_db):
    def override_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = lambda: superadmin_user
    app.dependency_overrides[get_db] = override_db
    custom = CustomRole(key="moderator", label="Модератор")
    mock_db.get.return_value = custom
    mock_db.scalar.return_value = uuid.uuid4()

    with TestClient(app) as client:
        r = client.delete("/api/admin/custom-roles/moderator")
    assert r.status_code == 400
    app.dependency_overrides.clear()
