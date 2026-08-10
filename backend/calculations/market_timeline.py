from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from core.currency import normalize_currency
from calculations.price_outliers import remove_outliers

IntervalKey = Literal["5s", "15s", "1m", "5m", "30m", "1h"]

INTERVAL_SECONDS: dict[IntervalKey, int] = {
    "5s": 5,
    "15s": 15,
    "1m": 60,
    "5m": 300,
    "30m": 1800,
    "1h": 3600,
}


def unit_price(record_price: Decimal, quantity: int | None) -> float:
    qty = quantity or 1
    return float(record_price)


def weighted_average(records) -> float | None:
    total_qty = sum((record.quantity or 1) for record in records)
    if total_qty <= 0:
        return None
    total_value = sum(float(record.price) * (record.quantity or 1) for record in records)
    return total_value / total_qty


def aggregate_bucket(records) -> dict | None:
    if not records:
        return None

    unit_prices = [unit_price(record.price, record.quantity) for record in records]
    cleaned = remove_outliers(unit_prices)
    seller_ids = {record.seller_id for record in records}
    weighted_avg = weighted_average(records)

    return {
        "median_price": Decimal(str(round(statistics.median(cleaned), 2))),
        "weighted_avg": Decimal(str(round(weighted_avg, 2))) if weighted_avg is not None else None,
        "seller_count": len(seller_ids),
        "record_count": len(records),
        "min_price": Decimal(str(round(min(cleaned), 2))),
        "max_price": Decimal(str(round(max(cleaned), 2))),
    }


def floor_to_bucket(ts: datetime, interval_sec: int) -> datetime:
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    seconds = int((ts - epoch).total_seconds())
    bucket_start = seconds - (seconds % interval_sec)
    return epoch + timedelta(seconds=bucket_start)


def build_market_timeline(
    records,
    interval: IntervalKey,
) -> dict[str, dict[str, list[dict]]]:
    interval_sec = INTERVAL_SECONDS[interval]
    buckets: dict[tuple[str, str, datetime], list] = defaultdict(list)

    for record in records:
        if not record.side:
            continue
        currency = normalize_currency(record.currency)
        if currency not in {"adena", "master_coin"}:
            continue
        bucket_start = floor_to_bucket(record.recorded_at, interval_sec)
        buckets[(currency, record.side, bucket_start)].append(record)

    series: dict[str, dict[str, list[dict]]] = {
        "adena": {"buy": [], "sell": []},
        "master_coin": {"buy": [], "sell": []},
    }

    for (currency, side, bucket_start), bucket_records in sorted(
        buckets.items(),
        key=lambda item: item[0][2],
    ):
        aggregated = aggregate_bucket(bucket_records)
        if aggregated is None:
            continue
        series[currency][side].append(
            {
                "bucket_start": bucket_start,
                **aggregated,
            }
        )

    return series
