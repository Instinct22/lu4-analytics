"""Buy-plan cheapest-fill aggregation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from calculations.buy_plan import build_buy_plan


def _lot(seller_id, price, quantity, recorded_at):
    return SimpleNamespace(
        seller_id=seller_id,
        price=Decimal(str(price)),
        quantity=quantity,
        recorded_at=recorded_at,
        side="sell",
    )


def test_build_buy_plan_fills_cheapest_first():
    s1, s2, s3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    entity_id = uuid.uuid4()
    t0 = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)
    records = [
        _lot(s1, 100, 40, t0),
        _lot(s2, 80, 30, t0),
        _lot(s3, 90, 100, t0),
        _lot(s1, 120, 10, t0),  # older superseded? same time - last wins if same; use later for s1
    ]
    # Make s1's expensive lot newer so latest is 120/10 — but we want cheapest fill from latest
    records = [
        _lot(s1, 120, 50, t0),
        _lot(s2, 80, 30, t0),
        _lot(s3, 90, 25, t0),
    ]

    db = MagicMock()
    records_result = MagicMock()
    records_result.all.return_value = records
    sellers_result = MagicMock()
    sellers_result.all.return_value = [
        SimpleNamespace(id=s1, name="A"),
        SimpleNamespace(id=s2, name="B"),
        SimpleNamespace(id=s3, name="C"),
    ]
    db.scalars.side_effect = [records_result, sellers_result]

    plan = build_buy_plan(db, entity_id, 50)
    assert plan["filled_quantity"] == 50
    assert plan["shortfall"] == 0
    assert [row["seller_name"] for row in plan["lots"]] == ["B", "C"]
    assert plan["lots"][0]["buy_quantity"] == 30
    assert plan["lots"][1]["buy_quantity"] == 20
    assert plan["total_cost"] == Decimal("4200.00")


def test_build_buy_plan_shortfall():
    s1 = uuid.uuid4()
    entity_id = uuid.uuid4()
    t0 = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)
    records = [_lot(s1, 10, 5, t0)]

    db = MagicMock()
    records_result = MagicMock()
    records_result.all.return_value = records
    sellers_result = MagicMock()
    sellers_result.all.return_value = [SimpleNamespace(id=s1, name="Solo")]
    db.scalars.side_effect = [records_result, sellers_result]

    plan = build_buy_plan(db, entity_id, 20)
    assert plan["filled_quantity"] == 5
    assert plan["shortfall"] == 15
