"""Craft resource market monitor: latest-per-seller VWAP, qty, period change %."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from calculations.trading_analytics import PERIOD_HOURS
from calculations.price_outliers import without_outliers
from models.market import MarketRecord
from models.wiki import WikiEntity
from services.admin_settings import get_craft_monitor

CraftMonitorPeriod = Literal["1h", "2h", "3h", "6h", "12h", "1d", "3d"]

CRAFT_MONITOR_PERIOD_HOURS: dict[str, int] = {
    "1h": 1,
    "2h": 2,
    "3h": 3,
    "6h": 6,
    "12h": 12,
    "1d": 24,
    "3d": 72,
}


def _quantity(record: MarketRecord) -> int:
    return record.quantity if record.quantity is not None else 1


def _decimal(value: float | Decimal | int) -> Decimal:
    return Decimal(str(round(float(value), 2)))


def latest_lots_per_seller(
    records: list[MarketRecord],
    *,
    side: str = "sell",
    as_of: datetime | None = None,
) -> list[MarketRecord]:
    """Keep the newest lot per seller for a side, optionally as of a cutoff timestamp."""
    best: dict[uuid.UUID, MarketRecord] = {}
    for record in records:
        if record.side != side:
            continue
        if as_of is not None and record.recorded_at > as_of:
            continue
        prev = best.get(record.seller_id)
        if prev is None or record.recorded_at > prev.recorded_at:
            best[record.seller_id] = record
    return list(best.values())


def aggregate_lots(lots: list[MarketRecord]) -> dict:
    if not lots:
        return {
            "vwap": None,
            "total_quantity": 0,
            "seller_count": 0,
        }
    total_qty = 0
    total_value = 0.0
    for lot in lots:
        qty = _quantity(lot)
        total_qty += qty
        total_value += float(lot.price) * qty
    vwap = (total_value / total_qty) if total_qty > 0 else None
    return {
        "vwap": _decimal(vwap) if vwap is not None else None,
        "total_quantity": total_qty,
        "seller_count": len(lots),
    }


def price_change_pct(current_vwap: Decimal | None, previous_vwap: Decimal | None) -> Decimal | None:
    if current_vwap is None or previous_vwap is None:
        return None
    prev = float(previous_vwap)
    if prev == 0:
        return None
    return _decimal((float(current_vwap) - prev) / prev * 100)


def resolve_craft_monitor_cutoff(
    period: str | None,
    from_date: datetime | None,
    to_date: datetime | None,
) -> datetime:
    """Cutoff timestamp for the previous VWAP snapshot."""
    now = datetime.now(timezone.utc)
    if from_date and to_date:
        span = to_date - from_date
        if span.total_seconds() <= 0:
            return from_date
        return to_date - span
    hours = CRAFT_MONITOR_PERIOD_HOURS.get(period or "1h")
    if hours is None:
        hours = PERIOD_HOURS.get(period or "1h", 1)
    return now - timedelta(hours=hours)


def build_craft_monitor_cards(
    db: Session,
    period: str = "1h",
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> list[dict]:
    cutoff = resolve_craft_monitor_cutoff(period, from_date, to_date)

    selected_ids = get_craft_monitor(db)["selectedIds"]
    if not selected_ids:
        return []

    entities = db.scalars(
        select(WikiEntity).where(
            WikiEntity.entity_type == "item",
            WikiEntity.external_id.in_(selected_ids),
        )
    ).all()
    entity_by_ext = {e.external_id: e for e in entities if e.external_id is not None}

    cards: list[dict] = []
    for ext_id in selected_ids:
        entity = entity_by_ext.get(ext_id)
        if entity is None:
            cards.append(
                {
                    "external_id": ext_id,
                    "entity_id": None,
                    "display_name": f"#{ext_id}",
                    "vwap": None,
                    "total_quantity": 0,
                    "price_change_pct": None,
                    "seller_count": 0,
                }
            )
            continue

        records = without_outliers(
            list(
                db.scalars(
                    select(MarketRecord)
                    .where(MarketRecord.entity_id == entity.id)
                    .where(MarketRecord.side == "sell")
                    .order_by(MarketRecord.recorded_at.desc())
                ).all()
            )
        )

        current = aggregate_lots(latest_lots_per_seller(records))
        previous = aggregate_lots(latest_lots_per_seller(records, as_of=cutoff))
        change = price_change_pct(current["vwap"], previous["vwap"])

        cards.append(
            {
                "external_id": ext_id,
                "entity_id": entity.id,
                "display_name": entity.display_name,
                "vwap": current["vwap"],
                "total_quantity": current["total_quantity"],
                "price_change_pct": change,
                "seller_count": current["seller_count"],
            }
        )
    return cards
