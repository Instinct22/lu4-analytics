"""Superadmin listing and deletion of market_records (chart source table)."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from models.market import MarketRecord, Seller
from models.wiki import WikiEntity
from schemas.auth import MarketRecordAdminItem, MarketRecordsResponse


def _parse_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value.strip())
    except (ValueError, AttributeError):
        return None


def list_market_records(
    db: Session,
    *,
    page: int = 1,
    limit: int = 50,
    search: str | None = None,
) -> MarketRecordsResponse:
    query = (
        select(MarketRecord, Seller.name, WikiEntity.display_name)
        .join(Seller, MarketRecord.seller_id == Seller.id)
        .outerjoin(WikiEntity, MarketRecord.entity_id == WikiEntity.id)
    )
    count_query = (
        select(func.count())
        .select_from(MarketRecord)
        .join(Seller, MarketRecord.seller_id == Seller.id)
        .outerjoin(WikiEntity, MarketRecord.entity_id == WikiEntity.id)
    )

    term = (search or "").strip()
    if term:
        pattern = f"%{term}%"
        filters = [
            MarketRecord.product_name_raw.ilike(pattern),
            MarketRecord.product_name_normalized.ilike(pattern),
            Seller.name.ilike(pattern),
            WikiEntity.display_name.ilike(pattern),
            MarketRecord.currency.ilike(pattern),
            MarketRecord.side.ilike(pattern),
            cast(MarketRecord.price, String).ilike(pattern),
            cast(MarketRecord.quantity, String).ilike(pattern),
        ]
        parsed = _parse_uuid(term)
        if parsed is not None:
            filters.extend(
                [
                    MarketRecord.id == parsed,
                    MarketRecord.entity_id == parsed,
                ]
            )
        filt = or_(*filters)
        query = query.where(filt)
        count_query = count_query.where(filt)

    total = db.scalar(count_query) or 0
    rows = db.execute(
        query.order_by(MarketRecord.recorded_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    items = [
        MarketRecordAdminItem(
            id=record.id,
            entity_id=record.entity_id,
            item_name=item_name,
            product_name_raw=record.product_name_raw,
            seller_name=seller_name,
            price=record.price,
            currency=record.currency,
            side=record.side,
            quantity=record.quantity,
            recorded_at=record.recorded_at,
        )
        for record, seller_name, item_name in rows
    ]
    return MarketRecordsResponse(items=items, total=total, page=page, limit=limit)


def delete_market_record(db: Session, record_id: uuid.UUID) -> None:
    record = db.get(MarketRecord, record_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    db.delete(record)
    db.commit()
