"""Daily average price aggregation by calendar day."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

from calculations.trading_analytics import (
    PERIOD_HOURS,
    build_daily_avg_prices,
    resolve_time_range,
)


def _record(
    *,
    price: str | float,
    side: str,
    recorded_at: datetime,
) -> SimpleNamespace:
    return SimpleNamespace(
        seller_id=uuid.uuid4(),
        price=Decimal(str(price)),
        quantity=1,
        recorded_at=recorded_at,
        side=side,
    )


def test_build_daily_avg_prices_empty():
    assert build_daily_avg_prices([]) == []


def test_build_daily_avg_prices_splits_buy_and_sell_by_day():
    day1 = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)
    day2 = datetime(2026, 9, 2, 8, 0, tzinfo=timezone.utc)
    records = [
        _record(price=100, side="buy", recorded_at=day1),
        _record(price=200, side="buy", recorded_at=day1 + timedelta(hours=2)),
        _record(price=150, side="sell", recorded_at=day1 + timedelta(hours=1)),
        _record(price=300, side="sell", recorded_at=day2),
    ]
    points = build_daily_avg_prices(records)
    assert len(points) == 2

    assert points[0]["day"] == datetime(2026, 9, 1, tzinfo=timezone.utc)
    assert points[0]["buy_avg_price"] == Decimal("150.00")
    assert points[0]["sell_avg_price"] == Decimal("150.00")
    assert points[0]["buy_deal_count"] == 2
    assert points[0]["sell_deal_count"] == 1

    assert points[1]["day"] == datetime(2026, 9, 2, tzinfo=timezone.utc)
    assert points[1]["buy_avg_price"] is None
    assert points[1]["sell_avg_price"] == Decimal("300.00")
    assert points[1]["buy_deal_count"] == 0
    assert points[1]["sell_deal_count"] == 1


def test_build_daily_avg_prices_ignores_unknown_side():
    day = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
    records = [
        _record(price=100, side="buy", recorded_at=day),
        _record(price=999, side=None, recorded_at=day),  # type: ignore[arg-type]
    ]
    points = build_daily_avg_prices(records)
    assert len(points) == 1
    assert points[0]["buy_avg_price"] == Decimal("100.00")
    assert points[0]["buy_deal_count"] == 1


def test_resolve_time_range_new_period_keys():
    for key, hours in (("2d", 48), ("14d", 336)):
        assert PERIOD_HOURS[key] == hours
        start, end = resolve_time_range(key, None, None)
        delta_hours = (end - start).total_seconds() / 3600
        assert abs(delta_hours - hours) < 0.01
