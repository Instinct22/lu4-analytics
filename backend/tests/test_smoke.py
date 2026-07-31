"""Minimal smoke tests — guard refactors without a live database."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock

from tests.conftest import make_entity


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_openapi_available(client):
    r = client.get("/api/openapi.json")
    assert r.status_code == 200
    assert "paths" in r.json()


def test_protected_route_requires_auth(anon_client):
    r = anon_client.get("/api/statistics/dashboard")
    assert r.status_code == 401


def test_login_rejects_bad_credentials(client, mock_db):
    mock_db.scalar.return_value = None
    # Remove auth override so login uses mock_db only
    from api.deps import get_current_user
    from main import app

    app.dependency_overrides.pop(get_current_user, None)
    r = client.post("/api/auth/login", json={"username": "nope", "password": "wrong"})
    assert r.status_code == 401


def test_wiki_entity_not_found(client, mock_db):
    mock_db.get.return_value = None
    r = client.get(f"/api/wiki/entities/{uuid.uuid4()}")
    assert r.status_code == 404


def test_wiki_entity_ok(client, mock_db):
    entity = make_entity()
    mock_db.get.return_value = entity
    mock_db.scalars.return_value.all.return_value = []
    r = client.get(f"/api/wiki/entities/{entity.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["display_name"] == "Short Sword"
    assert body["entity_type"] == "item"


def test_generic_analytics_endpoint_is_gone(client, mock_db):
    assert client.get("/api/analytics/duals_catalog").status_code == 404


def test_duals_catalog_ok(client, mock_db):
    mock_db.scalar.return_value = SimpleNamespace(
        dataset_key="duals_catalog",
        generated_at=None,
        payload={"items": {}, "byProduct": {}},
    )
    r = client.get("/api/duals/catalog")
    assert r.status_code == 200
    assert r.json() == {"generated_at": None, "items": {}, "byProduct": {}}


def test_duals_catalog_not_loaded(client, mock_db):
    mock_db.scalar.return_value = None
    assert client.get("/api/duals/catalog").status_code == 404


def test_duals_catalog_requires_auth(anon_client):
    assert anon_client.get("/api/duals/catalog").status_code == 401


def test_weapon_upgrades_catalog_ok(client, mock_db):
    mock_db.scalar.return_value = SimpleNamespace(
        dataset_key="weapon_upgrades",
        generated_at=None,
        payload={"upgrades": [], "items": {}, "info": {}, "ng_to_d": None},
    )
    r = client.get("/api/upgrades/catalog")
    assert r.status_code == 200
    assert r.json()["upgrades"] == []


def test_weapon_upgrades_catalog_not_loaded(client, mock_db):
    mock_db.scalar.return_value = None
    assert client.get("/api/upgrades/catalog").status_code == 404


def test_weapon_upgrades_requires_auth(anon_client):
    assert anon_client.get("/api/upgrades/catalog").status_code == 401


def test_market_items_empty(client, mock_db):
    mock_db.execute.return_value.all.return_value = []
    r = client.get("/api/market/items")
    assert r.status_code == 200
    assert r.json()["items"] == []
