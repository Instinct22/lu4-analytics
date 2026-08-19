"""Raid boss life status API and timer phase logic."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.deps import create_access_token, hash_password
from database import get_db
from main import app
from models.raid import RaidBoss, RaidBossTimer
from models.user import User
from services.api_tokens import hash_api_token
from services.raid_timers import build_boss_life_list, evaluate_timer_phase, life_from_phase
from tests.conftest import scalars_by_model


@pytest.fixture
def raid_life_client(mock_db):
    def override_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _boss(
    external_id: int,
    name: str,
    *,
    min_sec: int = 14400,
    max_sec: int = 28800,
    level: int = 20,
) -> RaidBoss:
    return RaidBoss(
        external_id=external_id,
        name=name,
        level=level,
        map_x=1.0,
        map_y=2.0,
        location="Gludio",
        respawn_raw="6 hours ± 2 hours",
        respawn_min_sec=min_sec,
        respawn_max_sec=max_sec,
        image_url=None,
        wiki_url=None,
        payload={},
    )


def test_evaluate_timer_phase_waiting_soon_window_overdue():
    now = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)
    killed = now - timedelta(hours=2)
    min_sec = 4 * 3600
    max_sec = 8 * 3600

    assert evaluate_timer_phase(killed, min_sec, max_sec, now) == "waiting"

    soon_now = datetime(2026, 8, 19, 13, 45, tzinfo=timezone.utc)
    assert evaluate_timer_phase(killed, min_sec, max_sec, soon_now) == "soon"

    window_now = datetime(2026, 8, 19, 14, 30, tzinfo=timezone.utc)
    assert evaluate_timer_phase(killed, min_sec, max_sec, window_now) == "window"

    overdue_now = datetime(2026, 8, 19, 21, 0, tzinfo=timezone.utc)
    assert evaluate_timer_phase(killed, min_sec, max_sec, overdue_now) == "overdue"


def test_life_from_phase():
    assert life_from_phase("waiting") == "no"
    assert life_from_phase("idle") == "no"
    assert life_from_phase("soon") == "yes"
    assert life_from_phase("window") == "yes"
    assert life_from_phase("overdue") == "yes"


def test_build_boss_life_list_excludes_hidden(monkeypatch):
    now = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)
    visible = _boss(1, "Visible Boss")
    hidden = _boss(2, "Hidden Boss")
    timer = RaidBossTimer(
        boss_external_id=1,
        killed_at=now - timedelta(hours=5),
        set_by_user_id=None,
        updated_at=now,
    )

    db = MagicMock()
    db.scalars.side_effect = [
        SimpleNamespace(all=lambda: [visible, hidden]),
        SimpleNamespace(all=lambda: [timer]),
    ]
    monkeypatch.setattr(
        "services.raid_timers.get_raid_hidden",
        lambda _db: {"hiddenIds": [2]},
    )

    rows = build_boss_life_list(db, now=now)
    assert len(rows) == 1
    assert rows[0]["name"] == "Visible Boss"
    assert rows[0]["life"] in ("yes", "no")


def test_boss_life_unauthenticated(raid_life_client, mock_db, monkeypatch):
    mock_db.scalars.side_effect = scalars_by_model({"RaidBoss": [], "RaidBossTimer": []})
    monkeypatch.setattr("services.raid_timers.get_raid_hidden", lambda _db: {"hiddenIds": []})

    r = raid_life_client.get("/api/raid/boss-life")
    assert r.status_code == 401


def test_boss_life_jwt_requires_timer_permission(raid_life_client, mock_db, monkeypatch):
    driver = User(
        id=uuid.uuid4(),
        username="driver1",
        password_hash=hash_password("secret"),
        role="driver",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    mock_db.get.return_value = driver
    mock_db.scalars.side_effect = scalars_by_model({"RolePermission": [], "RaidBoss": [], "RaidBossTimer": []})
    monkeypatch.setattr("services.raid_timers.get_raid_hidden", lambda _db: {"hiddenIds": []})

    token = create_access_token(driver.id, driver.username)
    r = raid_life_client.get("/api/raid/boss-life", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_boss_life_jwt_with_permission(raid_life_client, mock_db, monkeypatch):
    user = User(
        id=uuid.uuid4(),
        username="raider",
        password_hash=hash_password("secret"),
        role="user",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    fixed_now = datetime(2026, 8, 19, 10, 0, tzinfo=timezone.utc)
    boss = _boss(25372, "Discarded Guardian")
    killed = fixed_now - timedelta(hours=2)
    timer = RaidBossTimer(
        boss_external_id=25372,
        killed_at=killed,
        set_by_user_id=None,
        updated_at=killed,
    )

    mock_db.get.return_value = user
    mock_db.scalars.side_effect = [
        SimpleNamespace(all=lambda: []),
        SimpleNamespace(all=lambda: [boss]),
        SimpleNamespace(all=lambda: [timer]),
    ]
    monkeypatch.setattr("services.raid_timers.get_raid_hidden", lambda _db: {"hiddenIds": []})
    monkeypatch.setattr(
        "services.raid_timers.datetime",
        SimpleNamespace(now=lambda tz=None: fixed_now, timezone=timezone),
    )

    token = create_access_token(user.id, user.username)
    r = raid_life_client.get("/api/raid/boss-life", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["bosses"] == [{"name": "Discarded Guardian", "life": "no"}]


def test_boss_life_api_token_with_scope(raid_life_client, mock_db, monkeypatch):
    plain = "lu4_raidlife1234567890abcd"
    fixed_now = datetime(2026, 8, 19, 15, 30, tzinfo=timezone.utc)
    boss = _boss(1, "Soon Boss")
    killed = fixed_now - timedelta(hours=4, minutes=15)
    timer = RaidBossTimer(
        boss_external_id=1,
        killed_at=killed,
        set_by_user_id=None,
        updated_at=killed,
    )

    token_row = SimpleNamespace(
        scopes=["raid_life"],
        revoked_at=None,
        expires_at=None,
        token_hash=hash_api_token(plain),
        token_prefix=plain[:12],
        last_used_at=None,
    )

    mock_db.scalar.return_value = token_row
    mock_db.commit.side_effect = lambda: None
    mock_db.scalars.side_effect = [
        SimpleNamespace(all=lambda: [boss]),
        SimpleNamespace(all=lambda: [timer]),
    ]
    monkeypatch.setattr("services.raid_timers.get_raid_hidden", lambda _db: {"hiddenIds": []})
    monkeypatch.setattr(
        "services.raid_timers.datetime",
        SimpleNamespace(now=lambda tz=None: fixed_now, timezone=timezone),
    )

    r = raid_life_client.get("/api/raid/boss-life", headers={"X-Api-Key": plain})
    assert r.status_code == 200
    assert r.json()["bosses"][0]["life"] == "yes"


def test_boss_life_api_token_wrong_scope(raid_life_client, mock_db):
    plain = "lu4_wrongscope1234567890ab"
    token_row = SimpleNamespace(
        scopes=["import"],
        revoked_at=None,
        expires_at=None,
        token_hash=hash_api_token(plain),
        token_prefix=plain[:12],
        last_used_at=None,
    )
    mock_db.scalar.return_value = token_row

    r = raid_life_client.get("/api/raid/boss-life", headers={"X-Api-Key": plain})
    assert r.status_code == 403
