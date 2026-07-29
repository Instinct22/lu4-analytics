"""Trading dashboard analytics: stats, order book, lucky moments, items overview."""

from __future__ import annotations

import statistics
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.market import MarketRecord, Seller
from models.wiki import WikiEntity

PeriodKey = Literal["1h", "6h", "12h", "24h", "3d", "7d", "30d"]

PERIOD_HOURS: dict[str, int] = {
    "1h": 1,
    "6h": 6,
    "12h": 12,
    "24h": 24,
    "3d": 72,
    "7d": 168,
    "30d": 720,
}


def resolve_time_range(
    period: str | None,
    from_date: datetime | None,
    to_date: datetime | None,
) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    if from_date and to_date:
        return from_date, to_date
    hours = PERIOD_HOURS.get(period or "24h", 24)
    return now - timedelta(hours=hours), now


def _quantity(record: MarketRecord) -> int:
    return record.quantity if record.quantity is not None else 1


def _decimal(value: float | Decimal | int) -> Decimal:
    return Decimal(str(round(float(value), 2)))


def compute_analytics(records: list[MarketRecord]) -> dict:
    if not records:
        return {
            "min_price": None,
            "max_price": None,
            "avg_price": None,
            "median_price": None,
            "deal_count": 0,
            "total_volume": 0,
            "vwap": None,
            "price_change": None,
            "price_change_pct": None,
            "avg_quantity": None,
            "max_price_deal": None,
            "max_volume_deal": None,
            "std_dev": None,
            "price_range": None,
            "unique_sellers": 0,
            "buy_count": 0,
            "sell_count": 0,
            "buy_sell_spread": None,
            "total_value": None,
        }

    prices = [float(r.price) for r in records]
    quantities = [_quantity(r) for r in records]
    sorted_by_time = sorted(records, key=lambda r: r.recorded_at)

    total_volume = sum(quantities)
    total_value = sum(float(r.price) * q for r, q in zip(records, quantities))
    vwap = total_value / total_volume if total_volume else None

    first_price = float(sorted_by_time[0].price)
    last_price = float(sorted_by_time[-1].price)
    price_change = last_price - first_price
    price_change_pct = (price_change / first_price * 100) if first_price else None

    buy_prices = [float(r.price) for r in records if r.side == "buy"]
    sell_prices = [float(r.price) for r in records if r.side == "sell"]
    spread = None
    if buy_prices and sell_prices:
        spread = min(sell_prices) - max(buy_prices)

    max_price_record = max(records, key=lambda r: float(r.price))
    max_vol_record = max(records, key=lambda r: _quantity(r))

    std_dev = statistics.stdev(prices) if len(prices) > 1 else 0.0
    min_p, max_p = min(prices), max(prices)

    return {
        "min_price": _decimal(min_p),
        "max_price": _decimal(max_p),
        "avg_price": _decimal(sum(prices) / len(prices)),
        "median_price": _decimal(statistics.median(prices)),
        "deal_count": len(records),
        "total_volume": total_volume,
        "vwap": _decimal(vwap) if vwap is not None else None,
        "price_change": _decimal(price_change),
        "price_change_pct": _decimal(price_change_pct) if price_change_pct is not None else None,
        "avg_quantity": _decimal(sum(quantities) / len(quantities)),
        "max_price_deal": {
            "price": max_price_record.price,
            "quantity": _quantity(max_price_record),
            "recorded_at": max_price_record.recorded_at,
        },
        "max_volume_deal": {
            "price": max_vol_record.price,
            "quantity": _quantity(max_vol_record),
            "recorded_at": max_vol_record.recorded_at,
        },
        "std_dev": _decimal(std_dev),
        "price_range": _decimal(max_p - min_p),
        "unique_sellers": len({r.seller_id for r in records}),
        "buy_count": sum(1 for r in records if r.side == "buy"),
        "sell_count": sum(1 for r in records if r.side == "sell"),
        "buy_sell_spread": _decimal(spread) if spread is not None else None,
        "total_value": _decimal(total_value),
    }


def build_order_book(records: list[MarketRecord]) -> dict:
    """Aggregate volume by price and side within the selected range."""
    buy_levels: dict[Decimal, int] = defaultdict(int)
    sell_levels: dict[Decimal, int] = defaultdict(int)

    for record in records:
        if not record.side:
            continue
        vol = _quantity(record)
        if record.side == "buy":
            buy_levels[record.price] += vol
        elif record.side == "sell":
            sell_levels[record.price] += vol

    buys = [
        {"price": price, "volume": volume}
        for price, volume in sorted(buy_levels.items(), key=lambda x: float(x[0]), reverse=True)
    ]
    sells = [
        {"price": price, "volume": volume}
        for price, volume in sorted(sell_levels.items(), key=lambda x: float(x[0]))
    ]
    return {"buys": buys, "sells": sells}


def build_chart_deals(records: list[MarketRecord], seller_names: dict[uuid.UUID, str]) -> list[dict]:
    return [
        {
            "recorded_at": r.recorded_at,
            "price": r.price,
            "quantity": _quantity(r),
            "side": r.side,
            "seller_name": seller_names.get(r.seller_id, "Unknown"),
            "total_cost": _decimal(float(r.price) * _quantity(r)),
        }
        for r in sorted(records, key=lambda x: x.recorded_at)
    ]


def build_volume_buckets(records: list[MarketRecord], bucket_count: int = 40) -> list[dict]:
    if not records:
        return []

    sorted_records = sorted(records, key=lambda r: r.recorded_at)
    start = sorted_records[0].recorded_at
    end = sorted_records[-1].recorded_at
    span = (end - start).total_seconds()
    if span <= 0:
        return [
            {
                "bucket_start": start,
                "buy_volume": sum(_quantity(r) for r in records if r.side == "buy"),
                "sell_volume": sum(_quantity(r) for r in records if r.side == "sell"),
            }
        ]

    bucket_seconds = span / bucket_count
    buckets: dict[int, dict] = {}

    for record in sorted_records:
        offset = (record.recorded_at - start).total_seconds()
        idx = min(int(offset / bucket_seconds), bucket_count - 1)
        if idx not in buckets:
            bucket_start = start + timedelta(seconds=idx * bucket_seconds)
            buckets[idx] = {"bucket_start": bucket_start, "buy_volume": 0, "sell_volume": 0}
        vol = _quantity(record)
        if record.side == "buy":
            buckets[idx]["buy_volume"] += vol
        elif record.side == "sell":
            buckets[idx]["sell_volume"] += vol

    return [buckets[i] for i in sorted(buckets)]


def detect_lucky_moments(records: list[MarketRecord], seller_names: dict[uuid.UUID, str]) -> list[dict]:
    if len(records) < 3:
        return []

    events: list[dict] = []
    sorted_records = sorted(records, key=lambda r: r.recorded_at)
    prices = [float(r.price) for r in sorted_records]
    avg_price = sum(prices) / len(prices)
    std_dev = statistics.stdev(prices) if len(prices) > 1 else 0.0
    quantities = [_quantity(r) for r in sorted_records]
    median_qty = statistics.median(quantities)

    # Cheap deals: price below avg - 1.5*std
    cheap_threshold = avg_price - 1.5 * std_dev if std_dev else avg_price * 0.85
    for record in sorted_records:
        price = float(record.price)
        if price < cheap_threshold:
            events.append(
                {
                    "type": "cheap_deal",
                    "severity": "high" if price < avg_price - 2 * std_dev else "medium",
                    "title": "Аномально дешёвая сделка",
                    "description": f"Цена {price:,.0f} ниже средней ({avg_price:,.0f})",
                    "recorded_at": record.recorded_at,
                    "price": record.price,
                    "quantity": _quantity(record),
                    "side": record.side,
                    "seller_name": seller_names.get(record.seller_id, "Unknown"),
                }
            )

    # Large volume at low price
    for record in sorted_records:
        qty = _quantity(record)
        price = float(record.price)
        if qty >= max(median_qty * 3, 10) and price <= avg_price:
            events.append(
                {
                    "type": "volume_spike",
                    "severity": "medium",
                    "title": "Большой объём по низкой цене",
                    "description": f"{qty} шт. по {price:,.0f}",
                    "recorded_at": record.recorded_at,
                    "price": record.price,
                    "quantity": qty,
                    "side": record.side,
                    "seller_name": seller_names.get(record.seller_id, "Unknown"),
                }
            )

    # Rolling price changes (window of 5 records)
    window = 5
    for i in range(window, len(sorted_records)):
        prev_avg = sum(prices[i - window : i]) / window
        curr = prices[i]
        if prev_avg <= 0:
            continue
        change_pct = (curr - prev_avg) / prev_avg * 100
        record = sorted_records[i]
        if change_pct <= -10:
            events.append(
                {
                    "type": "price_drop",
                    "severity": "high" if change_pct <= -20 else "medium",
                    "title": "Резкое падение цены",
                    "description": f"{change_pct:.1f}% от недавнего среднего",
                    "recorded_at": record.recorded_at,
                    "price": record.price,
                    "quantity": _quantity(record),
                    "side": record.side,
                    "seller_name": seller_names.get(record.seller_id, "Unknown"),
                }
            )
        elif change_pct >= 10:
            events.append(
                {
                    "type": "price_surge",
                    "severity": "high" if change_pct >= 20 else "medium",
                    "title": "Резкий рост цены",
                    "description": f"+{change_pct:.1f}% от недавнего среднего",
                    "recorded_at": record.recorded_at,
                    "price": record.price,
                    "quantity": _quantity(record),
                    "side": record.side,
                    "seller_name": seller_names.get(record.seller_id, "Unknown"),
                }
            )

    # Activity spike: bucket by hour
    hour_buckets: dict[datetime, int] = defaultdict(int)
    for record in sorted_records:
        bucket = record.recorded_at.replace(minute=0, second=0, microsecond=0)
        hour_buckets[bucket] += 1
    if hour_buckets:
        counts = list(hour_buckets.values())
        avg_count = sum(counts) / len(counts)
        for bucket, count in hour_buckets.items():
            if count >= max(avg_count * 2.5, 5):
                events.append(
                    {
                        "type": "activity_spike",
                        "severity": "medium",
                        "title": "Всплеск активности",
                        "description": f"{count} сделок за час (среднее {avg_count:.1f})",
                        "recorded_at": bucket,
                        "price": None,
                        "quantity": count,
                        "side": None,
                        "seller_name": None,
                    }
                )

    # Arbitrage: buy max > sell min in overlapping hour
    hour_side_prices: dict[datetime, dict[str, list[float]]] = defaultdict(lambda: {"buy": [], "sell": []})
    for record in sorted_records:
        if not record.side:
            continue
        bucket = record.recorded_at.replace(minute=0, second=0, microsecond=0)
        hour_side_prices[bucket][record.side].append(float(record.price))

    for bucket, sides in hour_side_prices.items():
        if sides["buy"] and sides["sell"]:
            best_buy = max(sides["buy"])
            best_sell = min(sides["sell"])
            if best_buy > best_sell:
                spread = best_buy - best_sell
                events.append(
                    {
                        "type": "arbitrage",
                        "severity": "high",
                        "title": "Арбитражная ситуация",
                        "description": f"Buy до {best_buy:,.0f}, Sell от {best_sell:,.0f} (спред {spread:,.0f})",
                        "recorded_at": bucket,
                        "price": _decimal(spread),
                        "quantity": None,
                        "side": None,
                        "seller_name": None,
                    }
                )

    events.sort(key=lambda e: e["recorded_at"], reverse=True)
    # Deduplicate similar events within same minute
    seen: set[tuple] = set()
    unique: list[dict] = []
    for event in events:
        key = (event["type"], event["recorded_at"].replace(second=0, microsecond=0))
        if key in seen:
            continue
        seen.add(key)
        unique.append(event)
    return unique[:50]


def fetch_records(
    db: Session,
    entity_id: uuid.UUID,
    from_date: datetime,
    to_date: datetime,
    side: str | None = None,
) -> tuple[list[MarketRecord], dict[uuid.UUID, str]]:
    query = (
        select(MarketRecord, Seller.name)
        .join(Seller, MarketRecord.seller_id == Seller.id)
        .where(MarketRecord.entity_id == entity_id)
        .where(MarketRecord.recorded_at >= from_date)
        .where(MarketRecord.recorded_at <= to_date)
    )
    if side:
        query = query.where(MarketRecord.side == side)

    rows = db.execute(query.order_by(MarketRecord.recorded_at)).all()
    records = [r for r, _ in rows]
    seller_names = {r.seller_id: name for r, name in rows}
    return records, seller_names


def build_items_overview(db: Session, from_date: datetime, to_date: datetime, limit: int = 60) -> list[dict]:
    """Mini-monitoring cards for all items with market data in the period."""
    rows = db.execute(
        select(
            WikiEntity.id,
            WikiEntity.display_name,
            func.count(MarketRecord.id).label("deal_count"),
            func.sum(func.coalesce(MarketRecord.quantity, 1)).label("total_volume"),
        )
        .join(MarketRecord, MarketRecord.entity_id == WikiEntity.id)
        .where(MarketRecord.recorded_at >= from_date)
        .where(MarketRecord.recorded_at <= to_date)
        .where(MarketRecord.side.is_not(None))
        .group_by(WikiEntity.id, WikiEntity.display_name)
        .order_by(func.count(MarketRecord.id).desc())
        .limit(limit)
    ).all()

    items: list[dict] = []
    for row in rows:
        records, _ = fetch_records(db, row.id, from_date, to_date)
        if not records:
            continue
        sorted_records = sorted(records, key=lambda r: r.recorded_at)
        first_price = float(sorted_records[0].price)
        last_price = float(sorted_records[-1].price)
        change_pct = ((last_price - first_price) / first_price * 100) if first_price else 0

        # Sparkline: up to 20 bucket medians
        bucket_count = min(20, len(sorted_records))
        span = (sorted_records[-1].recorded_at - sorted_records[0].recorded_at).total_seconds()
        sparkline: list[float] = []
        if span <= 0:
            sparkline = [last_price]
        else:
            bucket_seconds = span / bucket_count
            start = sorted_records[0].recorded_at
            for i in range(bucket_count):
                b_start = start + timedelta(seconds=i * bucket_seconds)
                b_end = start + timedelta(seconds=(i + 1) * bucket_seconds)
                bucket_prices = [
                    float(r.price) for r in sorted_records if b_start <= r.recorded_at < b_end
                ]
                if bucket_prices:
                    sparkline.append(statistics.median(bucket_prices))

        items.append(
            {
                "entity_id": row.id,
                "display_name": row.display_name,
                "current_price": _decimal(last_price),
                "price_change_pct": _decimal(change_pct),
                "total_volume": int(row.total_volume or 0),
                "deal_count": row.deal_count,
                "sparkline": sparkline,
            }
        )
    return items
