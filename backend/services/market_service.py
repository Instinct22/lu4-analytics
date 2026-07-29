"""Market queries: timeline, items, prices, trades."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from calculations.market_timeline import INTERVAL_SECONDS, build_market_timeline
from calculations.trading_analytics import (
    build_chart_deals,
    build_items_overview,
    build_order_book,
    build_volume_buckets,
    compute_analytics,
    detect_lucky_moments,
    fetch_records,
    resolve_time_range,
)
from core.errors import AppError
from models.analytics import ItemStatistics
from models.market import MarketRecord, Seller
from models.wiki import WikiEntity
from schemas.market import (
    MarketItemOption,
    MarketItemsResponse,
    MarketTimelinePoint,
    MarketTimelineResponse,
    MarketTimelineSideSeries,
)
from schemas.trading import (
    ChartDealPoint,
    DealHighlight,
    ItemOverviewCard,
    ItemsOverviewResponse,
    LuckyMomentEvent,
    LuckyMomentsResponse,
    OrderBookLevel,
    OrderBookResponse,
    TradeRecordItem,
    TradesListResponse,
    TradingAnalyticsResponse,
    TradingChartResponse,
    VolumeBucket,
)


def _parse_npc_sell(stats: dict | None) -> float | None:
    if not stats:
        return None
    for key in ("NPC Sell Price", "Npc Sell Price", "Sell Price"):
        val = stats.get(key)
        if val is None:
            continue
        digits = "".join(c for c in str(val) if c.isdigit())
        if digits:
            return float(digits)
    return None


def get_item_or_404(db: Session, entity_id: uuid.UUID) -> WikiEntity:
    entity = db.get(WikiEntity, entity_id)
    if entity is None:
        raise AppError("Item not found", code="not_found", status_code=404)
    return entity


def _timeline_side_series(raw: dict[str, list[dict]]) -> MarketTimelineSideSeries:
    return MarketTimelineSideSeries(
        buy=[MarketTimelinePoint(**point) for point in raw["buy"]],
        sell=[MarketTimelinePoint(**point) for point in raw["sell"]],
    )


def market_timeline(
    db: Session,
    entity_id: uuid.UUID,
    interval: str,
    from_date: datetime | None,
    to_date: datetime | None,
) -> MarketTimelineResponse:
    if interval not in INTERVAL_SECONDS:
        raise AppError(
            f"Invalid interval. Allowed: {', '.join(INTERVAL_SECONDS)}",
            code="invalid_interval",
            status_code=400,
        )
    get_item_or_404(db, entity_id)

    query = (
        select(MarketRecord)
        .where(MarketRecord.entity_id == entity_id)
        .where(MarketRecord.side.is_not(None))
    )
    if from_date:
        query = query.where(MarketRecord.recorded_at >= from_date)
    if to_date:
        query = query.where(MarketRecord.recorded_at <= to_date)

    records = db.scalars(query.order_by(MarketRecord.recorded_at)).all()
    series = build_market_timeline(records, interval)  # type: ignore[arg-type]

    return MarketTimelineResponse(
        entity_id=entity_id,
        interval=interval,
        from_date=from_date,
        to_date=to_date,
        adena=_timeline_side_series(series["adena"]),
        master_coin=_timeline_side_series(series["master_coin"]),
    )


def market_items(db: Session, q: str | None, limit: int) -> MarketItemsResponse:
    query = (
        select(
            WikiEntity.id,
            WikiEntity.display_name,
            func.count(MarketRecord.id).label("record_count"),
        )
        .join(MarketRecord, MarketRecord.entity_id == WikiEntity.id)
        .where(MarketRecord.side.is_not(None))
        .group_by(WikiEntity.id, WikiEntity.display_name)
        .order_by(func.count(MarketRecord.id).desc())
        .limit(limit)
    )
    if q:
        query = query.where(WikiEntity.display_name.ilike(f"%{q}%"))

    rows = db.execute(query).all()
    return MarketItemsResponse(
        items=[
            MarketItemOption(id=row.id, display_name=row.display_name, record_count=row.record_count)
            for row in rows
        ]
    )


def prices_by_ids(db: Session, ids: str) -> dict[str, dict]:
    id_list: list[int] = []
    for part in ids.split(","):
        part = part.strip()
        if part.isdigit():
            id_list.append(int(part))
    if not id_list:
        return {}

    entities = db.scalars(
        select(WikiEntity).where(
            WikiEntity.entity_type == "item",
            WikiEntity.external_id.in_(id_list),
        )
    ).all()
    entity_by_ext = {e.external_id: e for e in entities if e.external_id is not None}

    stats_rows = db.scalars(
        select(ItemStatistics).where(
            ItemStatistics.entity_id.in_([e.id for e in entities]),
            ItemStatistics.period == "all",
        )
    ).all()
    stats_by_entity = {s.entity_id: s for s in stats_rows}

    result: dict[str, dict] = {}
    for ext_id in id_list:
        entity = entity_by_ext.get(ext_id)
        if not entity:
            result[str(ext_id)] = {"avg_price": None, "last_price": None, "npc_sell": None}
            continue
        st = stats_by_entity.get(entity.id)
        result[str(ext_id)] = {
            "avg_price": float(st.avg_price) if st and st.avg_price is not None else None,
            "last_price": float(st.last_price) if st and st.last_price is not None else None,
            "npc_sell": _parse_npc_sell(entity.stats),
        }
    return result


def trading_chart(
    db: Session,
    entity_id: uuid.UUID,
    period: str,
    from_date: datetime | None,
    to_date: datetime | None,
) -> TradingChartResponse:
    get_item_or_404(db, entity_id)
    start, end = resolve_time_range(period, from_date, to_date)
    records, seller_names = fetch_records(db, entity_id, start, end)
    return TradingChartResponse(
        entity_id=entity_id,
        from_date=start,
        to_date=end,
        deals=[ChartDealPoint(**d) for d in build_chart_deals(records, seller_names)],
        volume_buckets=[VolumeBucket(**b) for b in build_volume_buckets(records)],
    )


def trading_analytics(
    db: Session,
    entity_id: uuid.UUID,
    period: str,
    from_date: datetime | None,
    to_date: datetime | None,
) -> TradingAnalyticsResponse:
    get_item_or_404(db, entity_id)
    start, end = resolve_time_range(period, from_date, to_date)
    records, _ = fetch_records(db, entity_id, start, end)
    stats = compute_analytics(records)
    max_price_deal = stats.pop("max_price_deal")
    max_volume_deal = stats.pop("max_volume_deal")
    return TradingAnalyticsResponse(
        **stats,
        max_price_deal=DealHighlight(**max_price_deal) if max_price_deal else None,
        max_volume_deal=DealHighlight(**max_volume_deal) if max_volume_deal else None,
    )


def order_book(
    db: Session,
    entity_id: uuid.UUID,
    period: str,
    from_date: datetime | None,
    to_date: datetime | None,
) -> OrderBookResponse:
    get_item_or_404(db, entity_id)
    start, end = resolve_time_range(period, from_date, to_date)
    records, _ = fetch_records(db, entity_id, start, end)
    book = build_order_book(records)
    return OrderBookResponse(
        buys=[OrderBookLevel(**level) for level in book["buys"]],
        sells=[OrderBookLevel(**level) for level in book["sells"]],
    )


def lucky_moments(
    db: Session,
    entity_id: uuid.UUID,
    period: str,
    from_date: datetime | None,
    to_date: datetime | None,
) -> LuckyMomentsResponse:
    get_item_or_404(db, entity_id)
    start, end = resolve_time_range(period, from_date, to_date)
    records, seller_names = fetch_records(db, entity_id, start, end)
    events = detect_lucky_moments(records, seller_names)
    return LuckyMomentsResponse(events=[LuckyMomentEvent(**e) for e in events])


def items_overview(
    db: Session,
    period: str,
    from_date: datetime | None,
    to_date: datetime | None,
    limit: int,
) -> ItemsOverviewResponse:
    start, end = resolve_time_range(period, from_date, to_date)
    items = build_items_overview(db, start, end, limit)
    return ItemsOverviewResponse(items=[ItemOverviewCard(**item) for item in items])


def list_trades(
    db: Session,
    *,
    entity_id: uuid.UUID,
    side: str,
    period: str,
    from_date: datetime | None,
    to_date: datetime | None,
    search: str | None,
    sort_by: str,
    sort_order: str,
    page: int,
    limit: int,
) -> TradesListResponse:
    get_item_or_404(db, entity_id)
    start, end = resolve_time_range(period, from_date, to_date)

    query = (
        select(MarketRecord, Seller.name)
        .join(Seller, MarketRecord.seller_id == Seller.id)
        .where(MarketRecord.entity_id == entity_id)
        .where(MarketRecord.side == side)
        .where(MarketRecord.recorded_at >= start)
        .where(MarketRecord.recorded_at <= end)
    )
    count_query = (
        select(func.count())
        .select_from(MarketRecord)
        .join(Seller, MarketRecord.seller_id == Seller.id)
        .where(MarketRecord.entity_id == entity_id)
        .where(MarketRecord.side == side)
        .where(MarketRecord.recorded_at >= start)
        .where(MarketRecord.recorded_at <= end)
    )

    if search:
        pattern = f"%{search}%"
        filt = or_(Seller.name.ilike(pattern), MarketRecord.product_name_raw.ilike(pattern))
        query = query.where(filt)
        count_query = count_query.where(filt)

    sort_columns = {
        "recorded_at": MarketRecord.recorded_at,
        "price": MarketRecord.price,
        "quantity": MarketRecord.quantity,
        "seller_name": Seller.name,
    }
    sort_col = sort_columns[sort_by]
    order = sort_col.asc() if sort_order == "asc" else sort_col.desc()

    total = db.scalar(count_query) or 0
    rows = db.execute(query.order_by(order).offset((page - 1) * limit).limit(limit)).all()

    items = [
        TradeRecordItem(
            id=record.id,
            recorded_at=record.recorded_at,
            seller_name=seller_name,
            quantity=record.quantity if record.quantity is not None else 1,
            price=record.price,
            total_cost=record.price * (record.quantity if record.quantity is not None else 1),
            side=record.side,
        )
        for record, seller_name in rows
    ]
    return TradesListResponse(items=items, total=total, page=page, limit=limit)
