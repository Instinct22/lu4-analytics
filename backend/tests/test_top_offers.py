"""Top buy/sell offers from latest lots."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from calculations.top_offers import build_top_offers


def _lot(seller_id, side, price, quantity, recorded_at, currency="adena"):
    return SimpleNamespace(
        seller_id=seller_id,
        side=side,
        price=Decimal(str(price)),
        quantity=quantity,
        recorded_at=recorded_at,
        currency=currency,
    )


def test_build_top_offers_sorts_and_limits():
    s1, s2, s3, s4 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    entity_id = uuid.uuid4()
    t0 = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)
    records = [
        _lot(s1, "sell", 100, 10, t0),
        _lot(s2, "sell", 80, 20, t0),
        _lot(s3, "sell", 90, 15, t0),
        _lot(s4, "sell", 70, 5, t0),
        _lot(s1, "buy", 50, 10, t0),
        _lot(s2, "buy", 60, 20, t0),
        _lot(s3, "buy", 55, 15, t0),
        _lot(s1, "sell", 200, 1, t0.replace(hour=11), currency="master_coin"),
    ]

    db = MagicMock()
    records_result = MagicMock()
    records_result.all.return_value = records
    sellers_result = MagicMock()
    sellers_result.all.return_value = [
        SimpleNamespace(id=s1, name="A"),
        SimpleNamespace(id=s2, name="B"),
        SimpleNamespace(id=s3, name="C"),
        SimpleNamespace(id=s4, name="D"),
    ]
    db.scalars.side_effect = [records_result, sellers_result]

    data = build_top_offers(db, entity_id, limit=3)
    assert [row["seller_name"] for row in data["sells"]] == ["D", "B", "C"]
    assert [row["seller_name"] for row in data["buys"]] == ["B", "C", "A"]
    assert data["sells"][0]["price"] == Decimal("70.00")
    assert data["buys"][0]["price"] == Decimal("60.00")
