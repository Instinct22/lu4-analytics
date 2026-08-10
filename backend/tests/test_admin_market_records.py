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
from services.import_service import ResolvedMarketItem


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

    r = client.get(
        "/api/admin/market-records",
        params={
            "seller": "SellerOne",
            "product": "Sword",
            "side": "sell",
            "date_from": "2026-08-01T00:00:00Z",
            "date_to": "2026-08-04T00:00:00Z",
        },
    )
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


def test_market_records_bulk_delete(client, mock_db, superadmin_user):
    app.dependency_overrides[get_current_user] = lambda: superadmin_user
    id1, id2 = uuid.uuid4(), uuid.uuid4()
    rec1, rec2 = MagicMock(spec=MarketRecord), MagicMock(spec=MarketRecord)
    mock_db.scalars.return_value.all.return_value = [rec1, rec2]

    r = client.post("/api/admin/market-records/bulk-delete", json={"ids": [str(id1), str(id2)]})
    assert r.status_code == 200
    assert r.json()["deleted"] == 2
    assert mock_db.delete.call_count == 2
    mock_db.commit.assert_called()
    app.dependency_overrides.clear()


def test_market_records_bulk_update(client, mock_db, superadmin_user):
    app.dependency_overrides[get_current_user] = lambda: superadmin_user
    record_id = uuid.uuid4()
    record = MagicMock(spec=MarketRecord)
    record.id = record_id
    record.price = Decimal("10")
    mock_db.get.return_value = record

    seller = MagicMock()
    seller.id = uuid.uuid4()

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "services.admin_market_records.get_or_create_seller",
            lambda db, name: seller,
        )
        mp.setattr(
            "services.admin_market_records.resolve_market_item",
            lambda db, name: ResolvedMarketItem(None, None, None, None, None, None),
        )
        r = client.patch(
            "/api/admin/market-records/bulk",
            json={
                "items": [
                    {
                        "id": str(record_id),
                        "product_name_raw": "New Sword",
                        "seller_name": "NewSeller",
                        "price": "55.5",
                        "currency": "adena",
                        "side": "buy",
                        "quantity": 3,
                        "recorded_at": "2026-08-03T12:00:00Z",
                    }
                ]
            },
        )

    assert r.status_code == 200
    assert r.json()["updated"] == 1
    assert record.product_name_raw == "New Sword"
    assert record.price == Decimal("55.5")
    assert record.side == "buy"
    assert record.quantity == 3
    assert record.seller_id == seller.id
    mock_db.commit.assert_called()
    app.dependency_overrides.clear()


def _make_record(price: str, entity_id: uuid.UUID | None = None, side: str = "sell"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        entity_id=entity_id or uuid.uuid4(),
        side=side,
        price=Decimal(price),
        recorded_at=datetime.now(timezone.utc),
    )


def test_collect_outlier_ids_flags_extreme_price():
    from services.admin_market_records import _collect_outlier_ids

    entity_id = uuid.uuid4()
    outlier = _make_record("111111", entity_id=entity_id)
    peers = [
        _make_record("1000", entity_id=entity_id),
        _make_record("1100", entity_id=entity_id),
        _make_record("1050", entity_id=entity_id),
        _make_record("1020", entity_id=entity_id),
        outlier,
    ]
    db = MagicMock()
    db.scalars.return_value.all.return_value = peers

    outlier_ids = _collect_outlier_ids(db)
    assert outlier.id in outlier_ids
    assert len(outlier_ids) == 1


def test_list_market_records_outliers_only_empty():
    from services.admin_market_records import list_market_records

    db = MagicMock()
    db.scalars.return_value.all.return_value = []

    response = list_market_records(db, page=1, limit=50, outliers_only=True)
    assert response.total == 0
    assert response.items == []
    db.execute.assert_not_called()


def test_list_market_records_outliers_only_filters_query(client, mock_db, superadmin_user):
    from services import admin_market_records

    app.dependency_overrides[get_current_user] = lambda: superadmin_user
    outlier_id = uuid.uuid4()
    entity_id = uuid.uuid4()
    outlier = SimpleNamespace(
        id=outlier_id,
        entity_id=entity_id,
        product_name_raw="Gemstone C",
        price=Decimal("111111"),
        currency="adena",
        side="sell",
        quantity=1,
        recorded_at=datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc),
    )

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(admin_market_records, "_collect_outlier_ids", lambda _db: {outlier_id})
        mock_db.scalar.return_value = 1
        exec_result = MagicMock()
        exec_result.all.return_value = [(outlier, "sadqgez", "Gemstone C")]
        mock_db.execute.return_value = exec_result

        r = client.get("/api/admin/market-records", params={"outliers_only": True})

    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(outlier_id)
    assert body["items"][0]["is_outlier"] is True
    app.dependency_overrides.clear()
