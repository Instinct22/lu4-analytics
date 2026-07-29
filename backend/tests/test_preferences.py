"""Per-user craft state: warehouse, manual prices and chosen recipe variants."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from api.preferences import MAX_PAYLOAD_BYTES
from tests.conftest import scalars_by_model


def make_row(scope="craft_owned", payload=None):
    return SimpleNamespace(
        scope=scope,
        payload=payload if payload is not None else {"1864": 10},
        updated_at=datetime(2026, 7, 28, tzinfo=timezone.utc),
    )


def test_list_returns_all_scopes(client, mock_db):
    mock_db.scalars.side_effect = scalars_by_model(
        {"UserPreference": [make_row(), make_row("craft_prices", {"57": 100})]}
    )
    r = client.get("/api/me/preferences")
    assert r.status_code == 200
    assert r.json()["scopes"] == {"craft_owned": {"1864": 10}, "craft_prices": {"57": 100}}


def test_get_missing_scope_returns_empty_payload(client, mock_db):
    mock_db.get.return_value = None
    r = client.get("/api/me/preferences/craft_owned")
    assert r.status_code == 200
    assert r.json() == {"scope": "craft_owned", "payload": {}, "updated_at": None}


def test_unknown_scope_is_rejected(client, mock_db):
    assert client.get("/api/me/preferences/whatever").status_code == 404
    assert client.put("/api/me/preferences/whatever", json={"payload": {}}).status_code == 404


def test_put_creates_row_for_user(client, mock_db, test_user):
    mock_db.get.return_value = None
    r = client.put("/api/me/preferences/craft_owned", json={"payload": {"1864": 5}})
    assert r.status_code == 200
    assert r.json()["payload"] == {"1864": 5}

    added = mock_db.add.call_args[0][0]
    assert added.user_id == test_user.id
    assert added.scope == "craft_owned"
    assert added.payload == {"1864": 5}
    assert mock_db.commit.called


def test_put_updates_existing_row(client, mock_db):
    row = make_row(payload={"1864": 1})
    mock_db.get.return_value = row
    r = client.put("/api/me/preferences/craft_owned", json={"payload": {"1864": 7}})
    assert r.status_code == 200
    assert row.payload == {"1864": 7}
    assert not mock_db.add.called


def test_oversized_payload_is_refused(client, mock_db):
    mock_db.get.return_value = None
    payload = {str(i): i for i in range(MAX_PAYLOAD_BYTES)}
    r = client.put("/api/me/preferences/craft_owned", json={"payload": payload})
    assert r.status_code == 413
    assert not mock_db.commit.called


def test_preferences_require_auth(anon_client):
    assert anon_client.get("/api/me/preferences").status_code == 401
