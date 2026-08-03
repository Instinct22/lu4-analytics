"""Top buy/sell offers from latest lot per seller."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from calculations.craft_monitor import _decimal, _quantity, latest_lots_per_seller
from core.currency import normalize_currency
from models.market import MarketRecord, Seller


def build_top_offers(db: Session, entity_id: uuid.UUID, limit: int = 5) -> dict:
    records = list(
        db.scalars(
            select(MarketRecord)
            .where(MarketRecord.entity_id == entity_id)
            .where(MarketRecord.side.in_(("buy", "sell")))
            .order_by(MarketRecord.recorded_at.desc())
        ).all()
    )
    adena_records = [r for r in records if normalize_currency(r.currency) == "adena"]

    sell_lots = latest_lots_per_seller(adena_records, side="sell")
    buy_lots = latest_lots_per_seller(adena_records, side="buy")
    sell_lots.sort(key=lambda r: (float(r.price), -_quantity(r)))
    buy_lots.sort(key=lambda r: (-float(r.price), -_quantity(r)))

    top_sell = sell_lots[:limit]
    top_buy = buy_lots[:limit]
    seller_ids = {lot.seller_id for lot in top_sell + top_buy}
    names = {
        row.id: row.name
        for row in db.scalars(select(Seller).where(Seller.id.in_(seller_ids))).all()
    } if seller_ids else {}

    def to_row(lot: MarketRecord) -> dict:
        return {
            "seller_id": lot.seller_id,
            "seller_name": names.get(lot.seller_id, "Unknown"),
            "quantity": _quantity(lot),
            "price": _decimal(lot.price),
            "recorded_at": lot.recorded_at,
        }

    return {
        "entity_id": entity_id,
        "sells": [to_row(lot) for lot in top_sell],
        "buys": [to_row(lot) for lot in top_buy],
    }
