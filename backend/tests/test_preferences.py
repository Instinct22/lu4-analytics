"""Per-user craft state: warehouse, manual prices and chosen recipe variants."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from api.preferences import MAX_PAYLOAD_BYTES
from tests.conftest import scalars_by_model


def make_row(scope="craft_owned", payload=None, updated_at=None):
    return SimpleNamespace(
        scope=scope,
        payload=payload if payload is not None else {"1864": 10},
        updated_at=updated_at or datetime(2026, 7, 28, tzinfo=timezone.utc),
    )


def test_list_returns_all_scopes(client, mock_db):
    owned = make_row()
    prices = make_row("craft_prices", {"57": 100}, datetime(2026, 7, 29, tzinfo=timezone.utc))
    mock_db.scalars.side_effect = scalars_by_model({"UserPreference": [owned, prices]})
    r = client.get("/api/me/preferences")
    assert r.status_code == 200
    assert r.json()["scopes"] == {"craft_owned": {"1864": 10}, "craft_prices": {"57": 100}}
    assert r.json()["updated_at"] == {
        "craft_owned": "2026-07-28T00:00:00+00:00",
        "craft_prices": "2026-07-29T00:00:00+00:00",
    }


def test_get_missing_scope_returns_empty_payload(client, mock_db):
    mock_db.get.return_value = None
    r = client.get("/api/me/preferences/craft_owned")
    assert r.status_code == 200
    assert r.json() == {"scope": "craft_owned", "payload": {}, "updated_at": None}


def test_unknown_scope_is_rejected(client, mock_db):
    assert client.get("/api/me/preferences/whatever").status_code == 404
    assert client.put("/api/me/preferences/whatever", json={"payload": {}}).status_code == 404
    assert client.patch("/api/me/preferences/whatever", json={"patch": {}}).status_code == 404


def test_put_creates_row_for_user(craft_client, mock_db, craft_user):
    mock_db.get.return_value = None
    r = craft_client.put("/api/me/preferences/craft_owned", json={"payload": {"1864": 5}})
    assert r.status_code == 200
    assert r.json()["payload"] == {"1864": 5}

    added = mock_db.add.call_args[0][0]
    assert added.user_id == craft_user.id
    assert added.scope == "craft_owned"
    assert added.payload == {"1864": 5}
    assert mock_db.commit.called


def test_put_updates_existing_row(craft_client, mock_db):
    row = make_row(payload={"1864": 1})
    mock_db.get.return_value = row
    r = craft_client.put("/api/me/preferences/craft_owned", json={"payload": {"1864": 7}})
    assert r.status_code == 200
    assert row.payload == {"1864": 7}
    assert not mock_db.add.called


def test_oversized_payload_is_refused(craft_client, mock_db):
    mock_db.get.return_value = None
    payload = {str(i): i for i in range(MAX_PAYLOAD_BYTES)}
    r = craft_client.put("/api/me/preferences/craft_owned", json={"payload": payload})
    assert r.status_code == 413
    assert not mock_db.commit.called


def test_craft_cart_scope(craft_client, mock_db, craft_user):
    mock_db.get.return_value = None
    payload = {"2424": {"qty": 3, "variant": 0}, "5293": {"qty": 1}}
    r = craft_client.put("/api/me/preferences/craft_cart", json={"payload": payload})
    assert r.status_code == 200
    assert r.json()["payload"] == payload

    added = mock_db.add.call_args[0][0]
    assert added.user_id == craft_user.id
    assert added.scope == "craft_cart"
    assert added.payload == payload


def test_patch_merges_without_overwriting_other_keys(craft_client, mock_db):
    row = make_row(payload={"1864": 10, "1870": 3})
    mock_db.get.return_value = row
    r = craft_client.patch("/api/me/preferences/craft_owned", json={"patch": {"1864": 15}})
    assert r.status_code == 200
    assert row.payload == {"1864": 15, "1870": 3}
    assert not mock_db.add.called


def test_patch_zero_removes_key(craft_client, mock_db):
    row = make_row(payload={"1864": 10, "1870": 3})
    mock_db.get.return_value = row
    r = craft_client.patch("/api/me/preferences/craft_owned", json={"patch": {"1870": 0}})
    assert r.status_code == 200
    assert row.payload == {"1864": 10}


def test_patch_creates_row_when_missing(craft_client, mock_db, craft_user):
    mock_db.get.return_value = None
    r = craft_client.patch("/api/me/preferences/craft_owned", json={"patch": {"1864": 5}})
    assert r.status_code == 200
    added = mock_db.add.call_args[0][0]
    assert added.user_id == craft_user.id
    assert added.scope == "craft_owned"
    assert added.payload == {"1864": 5}


def test_patch_empty_owned_stays_empty(craft_client, mock_db):
    row = make_row(payload={})
    mock_db.get.return_value = row
    r = craft_client.patch("/api/me/preferences/craft_owned", json={"patch": {"1870": 0}})
    assert r.status_code == 200
    assert row.payload == {}


def test_patch_craft_cart_add_and_remove(craft_client, mock_db):
    row = make_row(
        scope="craft_cart",
        payload={"2424": {"qty": 3, "variant": 0}},
    )
    mock_db.get.return_value = row
    r = craft_client.patch(
        "/api/me/preferences/craft_cart",
        json={"patch": {"5293": {"qty": 2}, "2424": {"qty": 0}}},
    )
    assert r.status_code == 200
    assert row.payload == {"5293": {"qty": 2}}


def test_patch_oversized_merged_payload_is_refused(craft_client, mock_db):
    row = make_row(payload={"1864": 1})
    mock_db.get.return_value = row
    patch = {str(i): i for i in range(MAX_PAYLOAD_BYTES)}
    r = craft_client.patch("/api/me/preferences/craft_owned", json={"patch": patch})
    assert r.status_code == 413
    assert not mock_db.commit.called

def test_preferences_require_auth(anon_client):
    assert anon_client.get("/api/me/preferences").status_code == 401
