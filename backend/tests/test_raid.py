"""Raid bosses: respawn parsing, normalizer output and endpoint permissions."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from api.deps import get_current_user, hash_password
from models.user import User
from services.normalizers.raid_bosses import normalize_raid_bosses
from services.raid_respawn import parse_respawn
from tests.conftest import scalars_by_model


class FakeSession:
    """Just enough of a Session for the normalizer: select-all, add, delete."""

    def __init__(self, existing=()):
        self._existing = list(existing)
        self.added: list = []
        self.deleted: list = []

    def scalars(self, _stmt):
        return SimpleNamespace(all=lambda: list(self._existing))

    def add(self, obj):
        self.added.append(obj)

    def delete(self, obj):
        self.deleted.append(obj)


PAYLOAD = {
    "map": {"width": 10, "height": 20, "image": "/m.webp", "flag": "/f.png"},
    "bosses": [
        {
            "id": 25372,
            "name": "Discarded Guardian",
            "level": 20,
            "x": 931.0,
            "y": 2547.0,
            "image": "http://img/1.png",
            "wikiUrl": "https://wiki/npc/25372",
            "location": "Gludio",
            "respawn": "6 hours ± 2 hours",
            "stats": {"hp": "12345"},
            "lore": "Ancient guardian",
            "howToReach": "Talking Island → Elven Ruins",
            "skills": [{"name": "Raid Boss", "level": 1, "desc": "note"}],
            "drops": [{"groupChance": "100%", "items": []}],
        },
        {
            "id": 29001,
            "name": "Queen Ant",
            "level": 40,
            "respawn": "Fixed",
        },
    ],
}


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("6 hours ± 2 hours", (14400, 28800)),
        ("9 hours ± 1 hour", (28800, 36000)),
        ("30 minutes ± 10 minutes", (1200, 2400)),
        ("6 hours", (21600, 21600)),
        ("Fixed", None),
        ("", None),
        (None, None),
        ("who knows", None),
    ],
)
def test_parse_respawn(raw, expected):
    assert parse_respawn(raw) == expected


def test_parse_respawn_recovers_mangled_plusminus():
    assert parse_respawn("6 hours \ufffd 2 hours") == (14400, 28800)


def test_normalizer_creates_rows_with_window():
    db = FakeSession()
    normalize_raid_bosses(db, PAYLOAD)

    assert len(db.added) == 2
    guardian = next(b for b in db.added if b.external_id == 25372)
    assert guardian.name == "Discarded Guardian"
    assert guardian.level == 20
    assert (guardian.map_x, guardian.map_y) == (931.0, 2547.0)
    assert (guardian.respawn_min_sec, guardian.respawn_max_sec) == (14400, 28800)
    assert guardian.payload["lore"] == "Ancient guardian"
    assert guardian.payload["howToReach"] == "Talking Island → Elven Ruins"
    assert guardian.payload["drops"][0]["groupChance"] == "100%"

    # Fixed respawn leaves the window empty, so timers stay unavailable.
    ant = next(b for b in db.added if b.external_id == 29001)
    assert ant.respawn_min_sec is None
    assert ant.payload["drops"] == []


def test_normalizer_updates_existing_and_drops_missing():
    kept = SimpleNamespace(external_id=25372, name="Old name", respawn_min_sec=None, payload={})
    gone = SimpleNamespace(external_id=99999, name="Removed upstream")
    db = FakeSession([kept, gone])

    normalize_raid_bosses(db, PAYLOAD)

    assert kept.name == "Discarded Guardian"
    assert kept.respawn_min_sec == 14400
    assert [b.external_id for b in db.added] == [29001]
    assert db.deleted == [gone]


def test_bosses_endpoint_returns_map_config(client, mock_db):
    mock_db.scalar.return_value = None
    r = client.get("/api/raid/bosses")
    assert r.status_code == 200
    body = r.json()
    assert body["bosses"] == []
    assert body["map"]["width"] == 1808


def test_timers_endpoint_lists_rows(client, mock_db):
    timer = SimpleNamespace(
        boss_external_id=25372,
        killed_at=datetime(2026, 7, 28, 10, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 28, 10, 0, tzinfo=timezone.utc),
    )
    mock_db.scalars.side_effect = scalars_by_model({"RaidBossTimer": [timer]})
    r = client.get("/api/raid/timers")
    assert r.status_code == 200
    assert r.json()["timers"][0]["bossId"] == 25372


def test_set_timer_rejects_unknown_boss(client, mock_db):
    mock_db.get.return_value = None
    r = client.post("/api/raid/timers/1", json={})
    assert r.status_code == 404


def test_set_timer_rejects_fixed_respawn(client, mock_db):
    mock_db.get.return_value = SimpleNamespace(external_id=1, respawn_min_sec=None)
    r = client.post("/api/raid/timers/1", json={})
    assert r.status_code == 400


def test_driver_role_cannot_see_or_write_timers(client):
    from main import app

    driver = User(
        id=uuid.uuid4(),
        username="driver",
        password_hash=hash_password("secret"),
        role="driver",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    app.dependency_overrides[get_current_user] = lambda: driver

    assert client.get("/api/raid/bosses").status_code == 403
    assert client.post("/api/raid/timers/1", json={}).status_code == 403
    assert client.delete("/api/raid/timers/1").status_code == 403


def test_user_role_can_read_and_write_timers(client, mock_db):
    from main import app

    plain_user = User(
        id=uuid.uuid4(),
        username="member",
        password_hash=hash_password("secret"),
        role="user",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    app.dependency_overrides[get_current_user] = lambda: plain_user
    mock_db.get.return_value = None

    assert client.get("/api/raid/bosses").status_code == 200
    # Boss lookup fails, but the permission gate has already been passed.
    assert client.post("/api/raid/timers/1", json={}).status_code == 404


def test_notes_endpoint_lists_rows(client, mock_db, test_user):
    from main import app

    plain_user = User(
        id=uuid.uuid4(),
        username="member",
        password_hash=hash_password("secret"),
        role="user",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    app.dependency_overrides[get_current_user] = lambda: plain_user

    note = SimpleNamespace(boss_external_id=25372, note="farm tonight")
    mock_db.scalars.side_effect = scalars_by_model({"RaidBossTimer": [], "RaidBossNote": [note]})
    r = client.get("/api/raid/notes")
    assert r.status_code == 200
    assert r.json()["notes"] == [{"bossId": 25372, "note": "farm tonight"}]

    app.dependency_overrides[get_current_user] = lambda: test_user


def test_set_note_creates_and_clears(client, mock_db, test_user):
    from main import app

    plain_user = User(
        id=uuid.uuid4(),
        username="member",
        password_hash=hash_password("secret"),
        role="user",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    app.dependency_overrides[get_current_user] = lambda: plain_user

    boss = SimpleNamespace(external_id=25372, name="Discarded Guardian")
    stored = {"row": None}

    def get_side(model, pk):
        if model.__name__ == "RaidBoss":
            return boss if pk == 25372 else None
        if model.__name__ == "RaidBossNote":
            return stored["row"]
        return None

    mock_db.get.side_effect = get_side

    r = client.put("/api/raid/notes/25372", json={"note": "check window"})
    assert r.status_code == 200
    assert r.json() == {"bossId": 25372, "note": "check window"}
    assert mock_db.add.called
    assert mock_db.commit.called

    stored["row"] = SimpleNamespace(boss_external_id=25372, note="check window")
    r = client.put("/api/raid/notes/25372", json={"note": ""})
    assert r.status_code == 200
    assert r.json() == {"bossId": 25372, "note": ""}
    assert mock_db.delete.called

    app.dependency_overrides[get_current_user] = lambda: test_user


def test_set_note_rejects_unknown_boss(client, mock_db, test_user):
    from main import app

    plain_user = User(
        id=uuid.uuid4(),
        username="member",
        password_hash=hash_password("secret"),
        role="user",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    app.dependency_overrides[get_current_user] = lambda: plain_user
    mock_db.get.return_value = None
    r = client.put("/api/raid/notes/1", json={"note": "x"})
    assert r.status_code == 404

    app.dependency_overrides[get_current_user] = lambda: test_user


def test_driver_cannot_write_notes(client, test_user):
    from main import app

    driver = User(
        id=uuid.uuid4(),
        username="driver",
        password_hash=hash_password("secret"),
        role="driver",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    app.dependency_overrides[get_current_user] = lambda: driver

    assert client.put("/api/raid/notes/1", json={"note": "x"}).status_code == 403

    app.dependency_overrides[get_current_user] = lambda: test_user
