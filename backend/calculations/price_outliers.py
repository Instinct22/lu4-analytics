"""Statistical outlier detection for market deal prices (IQR method)."""

from __future__ import annotations

import uuid
from typing import TypeVar

from models.market import MarketRecord

T = TypeVar("T")

MIN_SAMPLE_SIZE = 4


def remove_outliers(values: list[float]) -> list[float]:
    if len(values) < MIN_SAMPLE_SIZE:
        return values

    sorted_vals = sorted(values)
    q1_index = len(sorted_vals) // 4
    q3_index = (3 * len(sorted_vals)) // 4
    q1 = sorted_vals[q1_index]
    q3 = sorted_vals[q3_index]
    iqr = q3 - q1
    if iqr == 0:
        return values

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    filtered = [value for value in values if lower <= value <= upper]
    return filtered or values


def _iqr_bounds(values: list[float]) -> tuple[float, float] | None:
    if len(values) < MIN_SAMPLE_SIZE:
        return None
    sorted_vals = sorted(values)
    q1 = sorted_vals[len(sorted_vals) // 4]
    q3 = sorted_vals[(3 * len(sorted_vals)) // 4]
    iqr = q3 - q1
    if iqr == 0:
        return None
    return q1 - 1.5 * iqr, q3 + 1.5 * iqr


def is_price_outlier(price: float, peers: list[float]) -> bool:
    bounds = _iqr_bounds(peers)
    if bounds is None:
        return False
    lower, upper = bounds
    return price < lower or price > upper


def _record_price(record: MarketRecord) -> float:
    return float(record.price)


def partition_market_records(
    records: list[MarketRecord],
) -> tuple[list[MarketRecord], list[MarketRecord]]:
    """Split records into clean vs outlier sets, grouped by side."""
    if len(records) < MIN_SAMPLE_SIZE:
        return records, []

    by_side: dict[str | None, list[MarketRecord]] = {}
    for record in records:
        by_side.setdefault(record.side, []).append(record)

    clean: list[MarketRecord] = []
    outliers: list[MarketRecord] = []

    for side_records in by_side.values():
        if len(side_records) < MIN_SAMPLE_SIZE:
            clean.extend(side_records)
            continue
        prices = [_record_price(r) for r in side_records]
        bounds = _iqr_bounds(prices)
        if bounds is None:
            clean.extend(side_records)
            continue
        lower, upper = bounds
        for record in side_records:
            price = _record_price(record)
            if price < lower or price > upper:
                outliers.append(record)
            else:
                clean.append(record)

    return clean, outliers


def is_market_record_outlier(record: MarketRecord, peers: list[MarketRecord]) -> bool:
    """True if record price is an outlier among peers with the same side."""
    same_side = [p for p in peers if p.id != record.id and p.side == record.side]
    if len(same_side) < MIN_SAMPLE_SIZE:
        return False
    peer_prices = [_record_price(p) for p in same_side]
    return is_price_outlier(_record_price(record), peer_prices)


def outlier_ids(records: list[MarketRecord]) -> set[uuid.UUID]:
    _, outliers = partition_market_records(records)
    return {record.id for record in outliers}


def without_outliers(records: list[MarketRecord]) -> list[MarketRecord]:
    clean, _ = partition_market_records(records)
    return clean or records
