"""Superadmin listing, filtering, update and deletion of market_records."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from core.currency import normalize_currency
from models.market import MarketRecord, Seller
from models.wiki import WikiEntity
from schemas.auth import (
    BulkDeleteMarketRecordsRequest,
    BulkUpdateMarketRecordsRequest,
    MarketRecordAdminItem,
    MarketRecordsResponse,
)
from services.import_service import find_item_by_name, get_or_create_seller
from services.name_matching import normalize_product_name


def _parse_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value.strip())
    except (ValueError, AttributeError):
        return None


def _apply_filters(
    query,
    count_query,
    *,
    search: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    product: str | None = None,
    seller: str | None = None,
    price: str | None = None,
    currency: str | None = None,
    side: str | None = None,
    quantity: str | None = None,
):
    filters = []

    if date_from is not None:
        filters.append(MarketRecord.recorded_at >= date_from)
    if date_to is not None:
        filters.append(MarketRecord.recorded_at <= date_to)

    product_term = (product or "").strip()
    if product_term:
        pattern = f"%{product_term}%"
        filters.append(
            or_(
                MarketRecord.product_name_raw.ilike(pattern),
                MarketRecord.product_name_normalized.ilike(pattern),
                WikiEntity.display_name.ilike(pattern),
            )
        )

    seller_term = (seller or "").strip()
    if seller_term:
        filters.append(Seller.name.ilike(f"%{seller_term}%"))

    price_term = (price or "").strip()
    if price_term:
        filters.append(cast(MarketRecord.price, String).ilike(f"%{price_term}%"))

    currency_term = (currency or "").strip()
    if currency_term:
        filters.append(MarketRecord.currency.ilike(f"%{currency_term}%"))

    side_term = (side or "").strip().lower()
    if side_term:
        filters.append(MarketRecord.side.ilike(f"%{side_term}%"))

    quantity_term = (quantity or "").strip()
    if quantity_term:
        filters.append(cast(MarketRecord.quantity, String).ilike(f"%{quantity_term}%"))

    term = (search or "").strip()
    if term:
        pattern = f"%{term}%"
        search_filters = [
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
            search_filters.extend(
                [
                    MarketRecord.id == parsed,
                    MarketRecord.entity_id == parsed,
                ]
            )
        filters.append(or_(*search_filters))

    if filters:
        for filt in filters:
            query = query.where(filt)
            count_query = count_query.where(filt)

    return query, count_query


def list_market_records(
    db: Session,
    *,
    page: int = 1,
    limit: int = 50,
    search: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    product: str | None = None,
    seller: str | None = None,
    price: str | None = None,
    currency: str | None = None,
    side: str | None = None,
    quantity: str | None = None,
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

    query, count_query = _apply_filters(
        query,
        count_query,
        search=search,
        date_from=date_from,
        date_to=date_to,
        product=product,
        seller=seller,
        price=price,
        currency=currency,
        side=side,
        quantity=quantity,
    )

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


def bulk_delete_market_records(db: Session, body: BulkDeleteMarketRecordsRequest) -> int:
    if not body.ids:
        return 0
    records = db.scalars(select(MarketRecord).where(MarketRecord.id.in_(body.ids))).all()
    for record in records:
        db.delete(record)
    db.commit()
    return len(records)


def _normalize_side(value: str | None) -> str | None:
    if value is None:
        return None
    raw = value.strip().lower()
    if not raw:
        return None
    if raw in {"buy", "покупка", "b"}:
        return "buy"
    if raw in {"sell", "продажа", "s"}:
        return "sell"
    if len(raw) > 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid side: {value}",
        )
    return raw


def bulk_update_market_records(db: Session, body: BulkUpdateMarketRecordsRequest) -> int:
    if not body.items:
        return 0

    updated = 0
    for item in body.items:
        record = db.get(MarketRecord, item.id)
        if record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Record not found: {item.id}",
            )

        name = item.product_name_raw.strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="product_name_raw cannot be empty",
            )
        record.product_name_raw = name
        record.product_name_normalized = normalize_product_name(name)
        entity = find_item_by_name(db, name)
        record.entity_id = entity.id if entity else None

        seller_name = item.seller_name.strip()
        if not seller_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="seller_name cannot be empty",
            )
        seller = get_or_create_seller(db, seller_name)
        record.seller_id = seller.id

        if item.price < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="price cannot be negative",
            )
        record.price = Decimal(item.price)
        record.currency = normalize_currency(item.currency)
        record.side = _normalize_side(item.side)

        if item.quantity is not None and item.quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="quantity cannot be negative",
            )
        record.quantity = item.quantity
        record.recorded_at = item.recorded_at

        updated += 1

    db.commit()
    return updated
