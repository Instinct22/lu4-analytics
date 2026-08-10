"""Cheapest-fill plan: buy N units from latest sell lots per seller."""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from calculations.craft_monitor import _decimal, _quantity, latest_lots_per_seller
from calculations.price_outliers import without_outliers
from models.market import MarketRecord, Seller


def build_buy_plan(db: Session, entity_id: uuid.UUID, quantity: int) -> dict:
    need = max(0, int(quantity))
    records = list(
        db.scalars(
            select(MarketRecord)
            .where(MarketRecord.entity_id == entity_id)
            .where(MarketRecord.side == "sell")
            .order_by(MarketRecord.recorded_at.desc())
        ).all()
    )
    lots = latest_lots_per_seller(without_outliers(records))
    lots.sort(key=lambda r: (float(r.price), -_quantity(r)))

    seller_ids = {lot.seller_id for lot in lots}
    names = {
        row.id: row.name
        for row in db.scalars(select(Seller).where(Seller.id.in_(seller_ids))).all()
    } if seller_ids else {}

    remaining = need
    rows: list[dict] = []
    total_cost = 0.0
    filled = 0

    for lot in lots:
        if remaining <= 0:
            break
        available = _quantity(lot)
        if available <= 0:
            continue
        take = min(available, remaining)
        cost = float(lot.price) * take
        rows.append(
            {
                "seller_id": lot.seller_id,
                "seller_name": names.get(lot.seller_id, "Unknown"),
                "price": _decimal(lot.price),
                "available_quantity": available,
                "buy_quantity": take,
                "cost": _decimal(cost),
                "recorded_at": lot.recorded_at,
            }
        )
        total_cost += cost
        filled += take
        remaining -= take

    return {
        "entity_id": entity_id,
        "requested_quantity": need,
        "filled_quantity": filled,
        "shortfall": max(0, need - filled),
        "total_cost": _decimal(total_cost) if filled else Decimal("0"),
        "avg_fill_price": _decimal(total_cost / filled) if filled else None,
        "lots": rows,
    }
