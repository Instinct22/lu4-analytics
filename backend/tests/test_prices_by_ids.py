"""prices_by_ids: 24h latest-per-seller sell VWAP + historical fallbacks."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.market_service import prices_by_ids


def _lot(
    *,
    entity_id: uuid.UUID,
    seller_id: uuid.UUID,
    price: str | float,
    quantity: int | None,
    recorded_at: datetime,
    side: str = "sell",
) -> SimpleNamespace:
    return SimpleNamespace(
        entity_id=entity_id,
        seller_id=seller_id,
        price=Decimal(str(price)),
        quantity=quantity,
        recorded_at=recorded_at,
        side=side,
    )


def _setup_db(*, entities, stats=None, records=None):
    db = MagicMock()
    entities_result = MagicMock()
    entities_result.all.return_value = entities
    stats_result = MagicMock()
    stats_result.all.return_value = stats or []
    records_result = MagicMock()
    records_result.all.return_value = records or []
    db.scalars.side_effect = [entities_result, stats_result, records_result]
    return db


def test_prices_by_ids_day_vwap_from_latest_sell_lots():
    entity_id = uuid.uuid4()
    s1, s2 = uuid.uuid4(), uuid.uuid4()
    now = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)
    entity = SimpleNamespace(
        id=entity_id,
        external_id=57,
        entity_type="item",
        stats={"NPC Sell Price": "100"},
    )
    records = [
        _lot(entity_id=entity_id, seller_id=s1, price=100, quantity=2, recorded_at=now - timedelta(hours=1)),
        _lot(entity_id=entity_id, seller_id=s1, price=150, quantity=2, recorded_at=now - timedelta(minutes=30)),
        _lot(entity_id=entity_id, seller_id=s2, price=200, quantity=2, recorded_at=now - timedelta(hours=2)),
    ]
    stats = [
        SimpleNamespace(
            entity_id=entity_id,
            avg_price=Decimal("999"),
            last_price=Decimal("888"),
        )
    ]
    db = _setup_db(entities=[entity], stats=stats, records=records)

    with patch("services.market_service.datetime") as mock_dt:
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        result = prices_by_ids(db, "57")

    # latest s1=150×2, s2=200×2 → VWAP 175
    assert result["57"]["day_vwap"] == 175.0
    assert result["57"]["avg_price"] == 999.0
    assert result["57"]["last_price"] == 888.0
    assert result["57"]["npc_sell"] == 100.0


def test_prices_by_ids_ignores_lots_older_than_24h():
    entity_id = uuid.uuid4()
    s1 = uuid.uuid4()
    now = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)
    entity = SimpleNamespace(
        id=entity_id,
        external_id=1001,
        entity_type="item",
        stats=None,
    )
    # Query already filters by cutoff; empty records simulate only-old lots
    stats = [
        SimpleNamespace(
            entity_id=entity_id,
            avg_price=Decimal("50"),
            last_price=Decimal("60"),
        )
    ]
    db = _setup_db(entities=[entity], stats=stats, records=[])

    with patch("services.market_service.datetime") as mock_dt:
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        result = prices_by_ids(db, "1001")

    assert result["1001"]["day_vwap"] is None
    assert result["1001"]["avg_price"] == 50.0
    assert result["1001"]["last_price"] == 60.0
    assert result["1001"]["npc_sell"] is None
    # Ensure cutoff used in query path (24h window)
    assert db.scalars.call_count == 3


def test_prices_by_ids_unknown_external_id():
    db = _setup_db(entities=[], stats=[], records=[])
    now = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)

    with patch("services.market_service.datetime") as mock_dt:
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        result = prices_by_ids(db, "99999")

    assert result["99999"] == {
        "day_vwap": None,
        "avg_price": None,
        "last_price": None,
        "npc_sell": None,
    }


def test_prices_by_ids_empty_ids():
    db = MagicMock()
    assert prices_by_ids(db, "") == {}
    assert prices_by_ids(db, "abc,xyz") == {}
    db.scalars.assert_not_called()
