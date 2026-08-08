"""prices_by_ids: Main fallbacks + window unique-seller VWAP."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.errors import AppError
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


def _setup_db(*, entities, stats=None, records_sequence=None):
    """records_sequence: list of record lists returned by successive scalars() calls after entities+stats."""
    db = MagicMock()
    entities_result = MagicMock()
    entities_result.all.return_value = entities
    stats_result = MagicMock()
    stats_result.all.return_value = stats or []
    side_effects = [entities_result, stats_result]
    for rows in records_sequence or []:
        rec = MagicMock()
        rec.all.return_value = rows
        side_effects.append(rec)
    db.scalars.side_effect = side_effects
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
    db = _setup_db(entities=[entity], stats=stats, records_sequence=[records])

    with patch("services.market_service.datetime") as mock_dt:
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        result = prices_by_ids(db, "57", "main")

    # latest s1=150×2, s2=200×2 → VWAP 175; no recent query when day_vwap present
    assert result["57"]["day_vwap"] == 175.0
    assert result["57"]["recent_vwap"] is None
    assert result["57"]["window_vwap"] is None
    assert result["57"]["avg_price"] == 999.0
    assert result["57"]["last_price"] == 888.0
    assert result["57"]["npc_sell"] == 100.0
    assert db.scalars.call_count == 3


def test_prices_by_ids_main_recent_vwap_when_no_24h():
    entity_id = uuid.uuid4()
    s1, s2, s3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    now = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)
    entity = SimpleNamespace(
        id=entity_id,
        external_id=1001,
        entity_type="item",
        stats=None,
    )
    # Day window empty; recent DISTINCT ON returns latest per seller (s1 has duplicate older row filtered out by query)
    recent = [
        _lot(entity_id=entity_id, seller_id=s1, price=100, quantity=1, recorded_at=now - timedelta(days=3)),
        _lot(entity_id=entity_id, seller_id=s2, price=200, quantity=3, recorded_at=now - timedelta(days=2)),
        _lot(entity_id=entity_id, seller_id=s3, price=300, quantity=1, recorded_at=now - timedelta(days=4)),
    ]
    db = _setup_db(entities=[entity], stats=[], records_sequence=[[], recent])

    with patch("services.market_service.datetime") as mock_dt:
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        result = prices_by_ids(db, "1001", "main")

    # (100*1 + 200*3 + 300*1) / 5 = 200
    assert result["1001"]["day_vwap"] is None
    assert result["1001"]["recent_vwap"] == 200.0
    assert result["1001"]["window_vwap"] is None
    assert db.scalars.call_count == 4


def test_prices_by_ids_main_recent_caps_at_20_unique_sellers():
    entity_id = uuid.uuid4()
    now = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)
    entity = SimpleNamespace(
        id=entity_id,
        external_id=77,
        entity_type="item",
        stats=None,
    )
    # 25 unique sellers; newest 20 are price=10 qty=1; oldest 5 are price=1000
    recent = []
    for i in range(25):
        recent.append(
            _lot(
                entity_id=entity_id,
                seller_id=uuid.uuid4(),
                price=10 if i < 20 else 1000,
                quantity=1,
                recorded_at=now - timedelta(days=i + 1),
            )
        )
    db = _setup_db(entities=[entity], stats=[], records_sequence=[[], recent])

    with patch("services.market_service.datetime") as mock_dt:
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        result = prices_by_ids(db, "77", "main")

    assert result["77"]["day_vwap"] is None
    assert result["77"]["recent_vwap"] == 10.0


def test_prices_by_ids_window_1h_only():
    entity_id = uuid.uuid4()
    s1, s2 = uuid.uuid4(), uuid.uuid4()
    now = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)
    entity = SimpleNamespace(
        id=entity_id,
        external_id=57,
        entity_type="item",
        stats={"NPC Sell Price": "50"},
    )
    # Query already applies cutoff; only in-window lots returned
    records = [
        _lot(entity_id=entity_id, seller_id=s1, price=100, quantity=2, recorded_at=now - timedelta(minutes=20)),
        _lot(entity_id=entity_id, seller_id=s2, price=200, quantity=2, recorded_at=now - timedelta(minutes=40)),
    ]
    db = _setup_db(entities=[entity], stats=[], records_sequence=[records])

    with patch("services.market_service.datetime") as mock_dt:
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        result = prices_by_ids(db, "57", "1h")

    assert result["57"]["window_vwap"] == 150.0
    assert result["57"]["day_vwap"] is None
    assert result["57"]["recent_vwap"] is None
    assert result["57"]["npc_sell"] == 50.0
    # No recent DISTINCT ON query in window mode
    assert db.scalars.call_count == 3


def test_prices_by_ids_window_empty():
    entity_id = uuid.uuid4()
    now = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)
    entity = SimpleNamespace(
        id=entity_id,
        external_id=1001,
        entity_type="item",
        stats={"NPC Sell Price": "10"},
    )
    db = _setup_db(entities=[entity], stats=[], records_sequence=[[]])

    with patch("services.market_service.datetime") as mock_dt:
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        result = prices_by_ids(db, "1001", "12h")

    assert result["1001"]["window_vwap"] is None
    assert result["1001"]["day_vwap"] is None
    assert result["1001"]["recent_vwap"] is None
    assert result["1001"]["npc_sell"] == 10.0


def test_prices_by_ids_unknown_external_id():
    db = _setup_db(entities=[], stats=[], records_sequence=[[]])
    now = datetime(2026, 8, 4, 12, 0, tzinfo=timezone.utc)

    with patch("services.market_service.datetime") as mock_dt:
        mock_dt.now.return_value = now
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        result = prices_by_ids(db, "99999")

    assert result["99999"] == {
        "day_vwap": None,
        "recent_vwap": None,
        "window_vwap": None,
        "avg_price": None,
        "last_price": None,
        "npc_sell": None,
    }


def test_prices_by_ids_empty_ids():
    db = MagicMock()
    assert prices_by_ids(db, "") == {}
    assert prices_by_ids(db, "abc,xyz") == {}
    db.scalars.assert_not_called()


def test_prices_by_ids_bad_period():
    db = MagicMock()
    with pytest.raises(AppError) as exc:
        prices_by_ids(db, "57", "2h")
    assert exc.value.status_code == 400
