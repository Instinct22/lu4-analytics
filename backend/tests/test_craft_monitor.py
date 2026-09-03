"""Craft monitor settings + period VWAP aggregation."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from api.deps import get_current_user, hash_password
from calculations.craft_monitor import (
    CRAFT_MONITOR_PERIOD_HOURS,
    aggregate_lots,
    build_craft_monitor_cards,
    latest_lots_per_seller,
    price_change_pct,
)
from main import app
from models.user import User
from services.admin_settings import (
    DEFAULT_CRAFT_MONITOR,
    _normalize_craft_monitor,
    get_craft_monitor,
    set_craft_monitor,
)


def _lot(
    *,
    seller_id: uuid.UUID,
    price: str | float,
    quantity: int | None,
    recorded_at: datetime,
    side: str = "sell",
) -> SimpleNamespace:
    return SimpleNamespace(
        seller_id=seller_id,
        price=Decimal(str(price)),
        quantity=quantity,
        recorded_at=recorded_at,
        side=side,
    )


def test_normalize_craft_monitor_dedupes_and_sorts():
    assert _normalize_craft_monitor({"selectedIds": [3, 1, 2, 1, "x", None]}) == {
        "selectedIds": [1, 2, 3]
    }
    assert _normalize_craft_monitor([10, 5]) == {"selectedIds": [5, 10]}
    assert _normalize_craft_monitor("bad") == {"selectedIds": []}


def test_get_set_craft_monitor(mock_db):
    mock_db.get.return_value = None
    assert get_craft_monitor(mock_db) == DEFAULT_CRAFT_MONITOR

    set_craft_monitor(mock_db, [42, 7, 7])
    mock_db.add.assert_called()
    added = mock_db.add.call_args[0][0]
    assert added.key == "craft_monitor"
    assert added.value == {"selectedIds": [7, 42]}


def test_latest_lots_per_seller_keeps_newest_sell():
    s1 = uuid.uuid4()
    s2 = uuid.uuid4()
    t0 = datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc)
    records = [
        _lot(seller_id=s1, price=100, quantity=10, recorded_at=t0),
        _lot(seller_id=s1, price=120, quantity=5, recorded_at=t0 + timedelta(hours=1)),
        _lot(seller_id=s2, price=90, quantity=20, recorded_at=t0 + timedelta(minutes=30)),
        _lot(seller_id=s2, price=80, quantity=3, recorded_at=t0, side="buy"),
    ]
    lots = latest_lots_per_seller(records)
    by_seller = {lot.seller_id: lot for lot in lots}
    assert len(lots) == 2
    assert by_seller[s1].price == Decimal("120")
    assert by_seller[s1].quantity == 5
    assert by_seller[s2].price == Decimal("90")
    assert by_seller[s2].quantity == 20


def test_latest_lots_as_of_cutoff():
    s1 = uuid.uuid4()
    t0 = datetime(2026, 8, 3, 10, 0, tzinfo=timezone.utc)
    cutoff = t0 + timedelta(hours=1)
    records = [
        _lot(seller_id=s1, price=100, quantity=10, recorded_at=t0),
        _lot(seller_id=s1, price=200, quantity=1, recorded_at=t0 + timedelta(hours=2)),
    ]
    lots = latest_lots_per_seller(records, as_of=cutoff)
    assert len(lots) == 1
    assert lots[0].price == Decimal("100")


def test_aggregate_lots_vwap_and_quantity():
    s1 = uuid.uuid4()
    s2 = uuid.uuid4()
    t0 = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)
    lots = [
        _lot(seller_id=s1, price=100, quantity=2, recorded_at=t0),
        _lot(seller_id=s2, price=200, quantity=2, recorded_at=t0),
    ]
    agg = aggregate_lots(lots)
    assert agg["total_quantity"] == 4
    assert agg["seller_count"] == 2
    assert agg["vwap"] == Decimal("150.00")


def test_aggregate_lots_empty():
    agg = aggregate_lots([])
    assert agg["total_quantity"] == 0
    assert agg["vwap"] is None
    assert agg["seller_count"] == 0


def test_price_change_pct():
    assert price_change_pct(Decimal("120"), Decimal("100")) == Decimal("20.00")
    assert price_change_pct(Decimal("80"), Decimal("100")) == Decimal("-20.00")
    assert price_change_pct(None, Decimal("100")) is None
    assert price_change_pct(Decimal("100"), None) is None
    assert price_change_pct(Decimal("100"), Decimal("0")) is None


def test_craft_monitor_periods_include_extended():
    assert CRAFT_MONITOR_PERIOD_HOURS["2h"] == 2
    assert CRAFT_MONITOR_PERIOD_HOURS["3h"] == 3
    assert CRAFT_MONITOR_PERIOD_HOURS["1d"] == 24
    assert CRAFT_MONITOR_PERIOD_HOURS["3d"] == 72


def test_build_craft_monitor_cards_ignores_stale_outside_period():
    entity_id = uuid.uuid4()
    s1 = uuid.uuid4()
    s2 = uuid.uuid4()
    now = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)
    entity = SimpleNamespace(
        id=entity_id,
        external_id=1001,
        display_name="Varnish",
        entity_type="item",
    )
    records = [
        _lot(seller_id=s1, price=459, quantity=100, recorded_at=now - timedelta(days=30)),
        _lot(seller_id=s2, price=2100, quantity=50, recorded_at=now - timedelta(hours=2)),
        _lot(seller_id=s2, price=2200, quantity=30, recorded_at=now - timedelta(minutes=30)),
    ]

    db = MagicMock()
    entities_result = MagicMock()
    entities_result.all.return_value = [entity]
    records_result = MagicMock()
    records_result.all.return_value = records

    db.scalars.side_effect = [entities_result, records_result]

    with (
        patch(
            "calculations.craft_monitor.get_craft_monitor",
            return_value={"selectedIds": [1001]},
        ),
        patch("calculations.craft_monitor.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = now
        cards = build_craft_monitor_cards(db, period="1d")

    assert len(cards) == 1
    card = cards[0]
    # Only deals within 24h: (2100*50 + 2200*30) / 80 = 2137.50
    assert card["vwap"] == Decimal("2137.50")
    assert card["total_quantity"] == 80
    assert card["seller_count"] == 1


def test_build_craft_monitor_cards_includes_buy_and_sell_vwap():
    entity_id = uuid.uuid4()
    s1 = uuid.uuid4()
    s2 = uuid.uuid4()
    now = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)
    entity = SimpleNamespace(
        id=entity_id,
        external_id=1001,
        display_name="Varnish",
        entity_type="item",
    )
    records = [
        _lot(seller_id=s1, price=2200, quantity=30, recorded_at=now - timedelta(minutes=30), side="sell"),
        _lot(seller_id=s2, price=1800, quantity=100, recorded_at=now - timedelta(minutes=20), side="buy"),
    ]

    db = MagicMock()
    entities_result = MagicMock()
    entities_result.all.return_value = [entity]
    records_result = MagicMock()
    records_result.all.return_value = records

    db.scalars.side_effect = [entities_result, records_result]

    with (
        patch(
            "calculations.craft_monitor.get_craft_monitor",
            return_value={"selectedIds": [1001]},
        ),
        patch("calculations.craft_monitor.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = now
        cards = build_craft_monitor_cards(db, period="1d")

    assert len(cards) == 1
    card = cards[0]
    assert card["vwap"] == Decimal("1892.31")
    assert card["total_quantity"] == 130
    assert card["seller_count"] == 2


def test_build_craft_monitor_cards_change_pct():
    entity_id = uuid.uuid4()
    s1 = uuid.uuid4()
    now = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)
    older = now - timedelta(hours=2)
    entity = SimpleNamespace(
        id=entity_id,
        external_id=1001,
        display_name="Coal",
        entity_type="item",
    )
    records = [
        _lot(seller_id=s1, price=100, quantity=10, recorded_at=older),
        _lot(seller_id=s1, price=150, quantity=10, recorded_at=now),
    ]

    db = MagicMock()
    entities_result = MagicMock()
    entities_result.all.return_value = [entity]
    records_result = MagicMock()
    records_result.all.return_value = records

    # First scalars: entities; second: market records
    db.scalars.side_effect = [entities_result, records_result]

    with (
        patch(
            "calculations.craft_monitor.get_craft_monitor",
            return_value={"selectedIds": [1001]},
        ),
        patch("calculations.craft_monitor.datetime") as mock_dt,
    ):
        mock_dt.now.return_value = now
        cards = build_craft_monitor_cards(db, period="1h")

    assert len(cards) == 1
    card = cards[0]
    assert card["external_id"] == 1001
    assert card["display_name"] == "Coal"
    assert card["total_quantity"] == 10
    assert card["vwap"] == Decimal("150.00")
    assert card["price_change_pct"] == Decimal("50.00")
    assert card["seller_count"] == 1


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


def test_admin_craft_monitor_forbidden(client, mock_db, regular_admin):
    app.dependency_overrides[get_current_user] = lambda: regular_admin
    mock_db.scalars.return_value.all.return_value = []
    r = client.get("/api/admin/settings/craft-monitor")
    assert r.status_code == 403
    r = client.put("/api/admin/settings/craft-monitor", json={"selectedIds": [1]})
    assert r.status_code == 403
    app.dependency_overrides.clear()


def test_admin_craft_monitor_superadmin(client, mock_db, superadmin_user):
    app.dependency_overrides[get_current_user] = lambda: superadmin_user
    mock_db.get.return_value = None

    r = client.get("/api/admin/settings/craft-monitor")
    assert r.status_code == 200
    assert r.json() == {"selectedIds": []}

    r = client.put("/api/admin/settings/craft-monitor", json={"selectedIds": [9, 3, 3]})
    assert r.status_code == 200
    assert r.json() == {"selectedIds": [3, 9]}
    mock_db.commit.assert_called()
    app.dependency_overrides.clear()


def test_public_settings_craft_monitor(client, mock_db):
    mock_db.get.return_value = SimpleNamespace(
        key="craft_monitor",
        value={"selectedIds": [11, 22]},
    )
    r = client.get("/api/settings/craft-monitor")
    assert r.status_code == 200
    assert r.json() == {"selectedIds": [11, 22]}


def test_market_craft_monitor_endpoint(client, mock_db, superadmin_user):
    app.dependency_overrides[get_current_user] = lambda: superadmin_user
    with patch(
        "services.market_service.build_craft_monitor_cards",
        return_value=[
            {
                "external_id": 1001,
                "entity_id": uuid.uuid4(),
                "display_name": "Coal",
                "vwap": Decimal("150.00"),
                "total_quantity": 10,
                "price_change_pct": Decimal("5.00"),
                "seller_count": 1,
            }
        ],
    ):
        r = client.get("/api/market/craft-monitor", params={"period": "2h"})
    assert r.status_code == 200
    body = r.json()
    assert body["period"] == "2h"
    assert len(body["items"]) == 1
    assert body["items"][0]["display_name"] == "Coal"
    assert body["items"][0]["total_quantity"] == 10
    app.dependency_overrides.clear()


def test_market_craft_monitor_bad_period(client, mock_db, superadmin_user):
    app.dependency_overrides[get_current_user] = lambda: superadmin_user
    r = client.get("/api/market/craft-monitor", params={"period": "24h"})
    assert r.status_code == 422
    app.dependency_overrides.clear()


def test_market_craft_monitor_1d_period(client, mock_db, superadmin_user):
    app.dependency_overrides[get_current_user] = lambda: superadmin_user
    with patch(
        "services.market_service.build_craft_monitor_cards",
        return_value=[],
    ) as build:
        r = client.get("/api/market/craft-monitor", params={"period": "1d"})
    assert r.status_code == 200
    assert r.json()["period"] == "1d"
    assert build.called
    app.dependency_overrides.clear()


def test_market_craft_monitor_custom_range(client, mock_db, superadmin_user):
    app.dependency_overrides[get_current_user] = lambda: superadmin_user
    with patch(
        "services.market_service.build_craft_monitor_cards",
        return_value=[],
    ) as build:
        r = client.get(
            "/api/market/craft-monitor",
            params={
                "period": "1d",
                "from": "2026-08-01T00:00:00Z",
                "to": "2026-08-02T00:00:00Z",
            },
        )
    assert r.status_code == 200
    assert r.json()["period"] == "custom"
    assert build.called
    app.dependency_overrides.clear()


def test_resolve_craft_monitor_cutoff_custom():
    from calculations.craft_monitor import resolve_craft_monitor_cutoff

    start = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
    end = datetime(2026, 8, 2, 0, 0, tzinfo=timezone.utc)
    cutoff = resolve_craft_monitor_cutoff("1d", start, end)
    assert cutoff == start
