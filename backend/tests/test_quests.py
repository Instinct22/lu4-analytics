"""Quests catalog: level overlap helpers and API permissions."""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest

from api.deps import get_current_user, hash_password
from models.user import User
from services.quests_service import (
    clear_catalog_cache,
    get_quest,
    list_quests,
    quest_overlaps_range,
)

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from quests_catalog.parse import parse_level  # noqa: E402


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Level: 2 ~ 5", (2, 5)),
        ("10 ~ 15", (10, 15)),
        ("35 ~ 45", (35, 45)),
        ("37+", (37, None)),
        ("Level: 20+", (20, None)),
        ("", (None, None)),
        (None, (None, None)),
    ],
)
def test_parse_level(raw, expected):
    assert parse_level(raw) == expected


@pytest.mark.parametrize(
    "q_min,q_max,f_min,f_max,expected",
    [
        (10, 15, 12, 20, True),
        (10, 15, 1, 9, False),
        (10, 15, 16, 20, False),
        (10, 15, 10, 15, True),
        (37, None, 40, 50, True),  # 37+ → max 99
        (37, None, 1, 30, False),
        (None, None, 1, 99, True),
        (2, 5, 5, 5, True),
    ],
)
def test_quest_overlaps_range(q_min, q_max, f_min, f_max, expected):
    assert quest_overlaps_range(q_min, q_max, f_min, f_max) is expected


SAMPLE_CATALOG = {
    "generated_at": "2026-01-01T00:00:00+00:00",
    "count": 2,
    "quests": [
        {
            "id": 1,
            "slug": "letters-of-love",
            "name": "Letters of Love",
            "url": "/lu4/quest/1-letters-of-love",
            "source_url": "https://masterwork.wiki/lu4/quest/1-letters-of-love",
            "level_min": 2,
            "level_max": 5,
            "description": "Deliver a letter.",
            "start_npc": {"id": 30048, "name": "Darin", "icon": "t_ic_humans_big.png"},
            "rewards": [{"item_id": 906, "name": "Necklace of Knowledge", "grade": "NG", "icon": "a.png"}],
            "steps": [{"title": "1: Delivery", "text": "Talk to Darin.", "images": []}],
        },
        {
            "id": 105,
            "slug": "skirmish-with-the-orcs",
            "name": "Skirmish with the Orcs",
            "level_min": 10,
            "level_max": 15,
            "description": "Help the Elves.",
            "start_npc": {"id": 30218, "name": "Kendell", "icon": "t_ic_elves_big.png"},
            "rewards": [],
            "steps": [],
        },
    ],
}


@pytest.fixture
def patch_catalog(monkeypatch):
    clear_catalog_cache()
    monkeypatch.setattr("services.quests_service.load_catalog", lambda: SAMPLE_CATALOG)
    yield
    clear_catalog_cache()


def test_list_quests_filters_by_level_overlap(patch_catalog):
    body = list_quests(min_level=12, max_level=20)
    assert [q["id"] for q in body["quests"]] == [105]


def test_list_quests_search(patch_catalog):
    body = list_quests(q="darin")
    assert [q["id"] for q in body["quests"]] == [1]


def test_get_quest_detail(patch_catalog):
    quest = get_quest(1)
    assert quest is not None
    assert quest["name"] == "Letters of Love"
    assert quest["rewards"][0]["item_id"] == 906
    assert quest["steps"][0]["title"] == "1: Delivery"
    assert get_quest(999) is None


def test_quests_endpoint_ok(client, mock_db, patch_catalog):
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

    r = client.get("/api/quests")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    assert body["quests"][0]["id"] == 1

    r = client.get("/api/quests/1")
    assert r.status_code == 200
    assert r.json()["slug"] == "letters-of-love"

    r = client.get("/api/quests?min_level=12&max_level=20")
    assert r.status_code == 200
    assert [q["id"] for q in r.json()["quests"]] == [105]


def test_quests_endpoint_404(client, mock_db, patch_catalog):
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
    assert client.get("/api/quests/999").status_code == 404


def test_driver_role_cannot_read_quests(client):
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
    assert client.get("/api/quests").status_code == 403


def test_user_role_can_read_quests(client, mock_db, patch_catalog):
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
    assert client.get("/api/quests").status_code == 200
