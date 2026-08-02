"""Admin raid timer audit log (primary admin only)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api.deps import get_current_user, hash_password
from database import get_db
from main import app
from models.user import User
from tests.conftest import scalars_by_model


@pytest.fixture
def timer_writer() -> User:
    return User(
        id=uuid.uuid4(),
        username="raider",
        password_hash=hash_password("secret"),
        role="user",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def timer_client(mock_db, timer_writer):
    def override_db():
        yield mock_db

    def override_user():
        return timer_writer

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_set_timer_writes_audit_log(timer_client, mock_db, timer_writer):
    boss = SimpleNamespace(external_id=25372, name="Discarded Guardian", respawn_min_sec=14400)

    def get_side_effect(model, pk):
        if model.__name__ == "RaidBoss":
            return boss
        return None

    mock_db.get.side_effect = get_side_effect

    r = timer_client.post(
        "/api/raid/timers/25372",
        json={"killed_at": "2026-07-29T12:00:00+00:00"},
        headers={"X-Real-IP": "203.0.113.10"},
    )
    assert r.status_code == 200

    added = [call.args[0] for call in mock_db.add.call_args_list]
    log = next(obj for obj in added if getattr(obj, "action", None) == "set")
    assert log.username == timer_writer.username
    assert log.user_id == timer_writer.id
    assert log.ip_address == "203.0.113.10"
    assert log.boss_name == "Discarded Guardian"
    assert log.action == "set"
    assert log.killed_at is not None


def test_clear_timer_writes_audit_log(timer_client, mock_db, timer_writer):
    boss = SimpleNamespace(external_id=25372, name="Discarded Guardian")
    timer = SimpleNamespace(boss_external_id=25372)

    def get_side_effect(model, pk):
        if model.__name__ == "RaidBoss":
            return boss
        if model.__name__ == "RaidBossTimer":
            return timer
        return None

    mock_db.get.side_effect = get_side_effect

    r = timer_client.delete("/api/raid/timers/25372", headers={"X-Forwarded-For": "198.51.100.5, 10.0.0.1"})
    assert r.status_code == 200

    added = [call.args[0] for call in mock_db.add.call_args_list]
    log = next(obj for obj in added if getattr(obj, "action", None) == "clear")
    assert log.username == timer_writer.username
    assert log.ip_address == "198.51.100.5"
    assert log.boss_name == "Discarded Guardian"


def test_raid_timer_logs_superadmin_only(client, mock_db):
    primary = User(
        id=uuid.uuid4(),
        username="admin",
        password_hash=hash_password("secret"),
        role="superadmin",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    app.dependency_overrides[get_current_user] = lambda: primary
    mock_db.scalar.return_value = 0
    mock_db.scalars.side_effect = scalars_by_model({"RaidTimerLog": []})

    assert client.get("/api/admin/raid-timer-logs").status_code == 200

    other_admin = User(
        id=uuid.uuid4(),
        username="otheradmin",
        password_hash=hash_password("secret"),
        role="admin",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    app.dependency_overrides[get_current_user] = lambda: other_admin
    assert client.get("/api/admin/raid-timer-logs").status_code == 403
