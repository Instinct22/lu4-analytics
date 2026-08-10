"""Tests for IQR-based market price outlier detection."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from calculations.price_outliers import (
    is_market_record_outlier,
    is_price_outlier,
    outlier_ids,
    partition_market_records,
    remove_outliers,
    without_outliers,
)


def _record(price: float, side: str = "sell"):
    return SimpleNamespace(
        id=uuid4(),
        price=Decimal(str(price)),
        side=side,
        recorded_at=datetime.now(timezone.utc),
    )


def test_remove_outliers_filters_extreme_value():
    values = [1000.0, 1100.0, 1050.0, 111111.0, 1020.0]
    filtered = remove_outliers(values)
    assert 111111.0 not in filtered
    assert len(filtered) == 4


def test_partition_market_records_flags_outlier():
    records = [
        _record(1000),
        _record(1100),
        _record(1050),
        _record(111111),
        _record(1020),
    ]
    clean, outliers = partition_market_records(records)
    assert len(outliers) == 1
    assert float(outliers[0].price) == 111111.0
    assert len(clean) == 4


def test_partition_skips_filter_when_fewer_than_four_records():
    records = [_record(1000), _record(111111), _record(900)]
    clean, outliers = partition_market_records(records)
    assert outliers == []
    assert clean == records


def test_buy_and_sell_are_partitioned_separately():
    records = [
        _record(1000, "buy"),
        _record(1100, "buy"),
        _record(1050, "buy"),
        _record(1020, "buy"),
        _record(50000, "buy"),
        _record(2000, "sell"),
        _record(2100, "sell"),
        _record(2050, "sell"),
        _record(2020, "sell"),
        _record(80000, "sell"),
    ]
    clean, outliers = partition_market_records(records)
    assert len(outliers) == 2
    outlier_prices = {float(r.price) for r in outliers}
    assert outlier_prices == {50000.0, 80000.0}
    assert len(clean) == 8


def test_is_price_outlier_respects_iqr_bounds():
    peers = [1000.0, 1100.0, 1050.0, 1020.0]
    assert is_price_outlier(111111.0, peers) is True
    assert is_price_outlier(1050.0, peers) is False


def test_is_market_record_outlier_uses_same_side_peers():
    target = _record(111111, "sell")
    peers = [
        _record(1000, "sell"),
        _record(1100, "sell"),
        _record(1050, "sell"),
        _record(1020, "sell"),
        _record(50000, "buy"),
    ]
    assert is_market_record_outlier(target, peers) is True

    normal = _record(1050, "sell")
    assert is_market_record_outlier(normal, peers) is False


def test_outlier_ids_returns_flagged_record_ids():
    outlier = _record(111111)
    records = [
        _record(1000),
        _record(1100),
        _record(1050),
        _record(1020),
        outlier,
    ]
    ids = outlier_ids(records)
    assert ids == {outlier.id}


def test_without_outliers_returns_clean_subset():
    outlier = _record(111111)
    records = [
        _record(1000),
        _record(1100),
        _record(1050),
        _record(1020),
        outlier,
    ]
    clean = without_outliers(records)
    assert len(clean) == 4
    assert outlier not in clean
