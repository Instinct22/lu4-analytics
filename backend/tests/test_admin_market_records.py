"""Superadmin market_records browser API."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from api.deps import get_current_user, hash_password
from main import app
from models.market import MarketRecord
from models.user import User


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


def test_market_records_admin_forbidden(client, mock_db, regular_admin):
    app.dependency_overrides[get_current_user] = lambda: regular_admin
    r = client.get("/api/admin/market-records")
    assert r.status_code == 403
    app.dependency_overrides.clear()


def test_market_records_list_superadmin(client, mock_db, superadmin_user):
    app.dependency_overrides[get_current_user] = lambda: superadmin_user
    record_id = uuid.uuid4()
    entity_id = uuid.uuid4()
    recorded_at = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)
    record = SimpleNamespace(
        id=record_id,
        entity_id=entity_id,
        product_name_raw="Sword +5",
        price=Decimal("100.50"),
        currency="adena",
        side="sell",
        quantity=2,
        recorded_at=recorded_at,
    )
    mock_db.scalar.return_value = 1
    exec_result = MagicMock()
    exec_result.all.return_value = [(record, "SellerOne", "Blessed Sword")]
    mock_db.execute.return_value = exec_result

    r = client.get("/api/admin/market-records", params={"page": 1, "limit": 50})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["limit"] == 50
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["id"] == str(record_id)
    assert item["item_name"] == "Blessed Sword"
    assert item["seller_name"] == "SellerOne"
    assert item["product_name_raw"] == "Sword +5"
    assert item["side"] == "sell"
    app.dependency_overrides.clear()


def test_market_records_search_passes_query(client, mock_db, superadmin_user):
    app.dependency_overrides[get_current_user] = lambda: superadmin_user
    mock_db.scalar.return_value = 0
    exec_result = MagicMock()
    exec_result.all.return_value = []
    mock_db.execute.return_value = exec_result

    r = client.get("/api/admin/market-records", params={"search": "SellerOne"})
    assert r.status_code == 200
    assert r.json()["total"] == 0
    assert mock_db.execute.called
    app.dependency_overrides.clear()


def test_market_records_delete(client, mock_db, superadmin_user):
    app.dependency_overrides[get_current_user] = lambda: superadmin_user
    record_id = uuid.uuid4()
    record = MagicMock(spec=MarketRecord)
    mock_db.get.return_value = record

    r = client.delete(f"/api/admin/market-records/{record_id}")
    assert r.status_code == 204
    mock_db.delete.assert_called_once_with(record)
    mock_db.commit.assert_called()
    app.dependency_overrides.clear()


def test_market_records_delete_not_found(client, mock_db, superadmin_user):
    app.dependency_overrides[get_current_user] = lambda: superadmin_user
    mock_db.get.return_value = None
    r = client.delete(f"/api/admin/market-records/{uuid.uuid4()}")
    assert r.status_code == 404
    app.dependency_overrides.clear()


def test_market_records_delete_admin_forbidden(client, mock_db, regular_admin):
    app.dependency_overrides[get_current_user] = lambda: regular_admin
    r = client.delete(f"/api/admin/market-records/{uuid.uuid4()}")
    assert r.status_code == 403
    app.dependency_overrides.clear()
