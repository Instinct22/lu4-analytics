"""Market queries: timeline, items, prices, trades."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from calculations.buy_plan import build_buy_plan
from calculations.craft_monitor import (
    CRAFT_MONITOR_PERIOD_HOURS,
    aggregate_lots,
    build_craft_monitor_cards,
    latest_lots_per_seller,
)
from calculations.market_timeline import INTERVAL_SECONDS, build_market_timeline
from calculations.price_outliers import outlier_ids, partition_market_records, without_outliers
from calculations.npc_prices import compute_npc_buy
from calculations.static_prices import static_avg_price
from calculations.top_offers import build_top_offers
from calculations.trading_analytics import (
    apply_variant_filters,
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
from models.craft import CraftItem
from models.market import MarketRecord, Seller
from models.wiki import WikiEntity
from services.import_service import _pick_canonical_entity
from services.name_matching import clean_display_name
from schemas.market import (
    MarketItemOption,
    MarketItemsResponse,
    MarketTimelinePoint,
    MarketTimelineResponse,
    MarketTimelineSideSeries,
    MarketVariantsResponse,
)
from schemas.trading import (
    BuyPlanLot,
    BuyPlanResponse,
    ChartDealPoint,
    CraftMonitorCard,
    CraftMonitorResponse,
    DealHighlight,
    ItemOverviewCard,
    ItemsOverviewResponse,
    LuckyMomentEvent,
    LuckyMomentsResponse,
    OrderBookLevel,
    OrderBookResponse,
    TopOfferLot,
    TopOffersResponse,
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


def _split_outliers(
    records: list[MarketRecord],
) -> tuple[list[MarketRecord], list[MarketRecord], int]:
    clean, outliers = partition_market_records(records)
    return clean, outliers, len(outliers)


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
    soul_crystal: str | None = None,
    enchant_level: int | str | None = None,
    rarity: str | None = None,
    armor_class: str | None = None,
    sealed: str | bool | None = None,
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
    query = apply_variant_filters(query, soul_crystal, enchant_level, rarity, armor_class, sealed)

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
    """Items that have market scan data, one row per canonical base item.

    Several wiki entities can share ``name_normalized`` (SA/rare variants). The
    chart select shows a single base entry; soul ability / rarity / enchant are
    chosen via variant filters on the item page.
    """
    query = (
        select(
            WikiEntity.id,
            WikiEntity.external_id,
            WikiEntity.display_name,
            WikiEntity.name_normalized,
            func.count(MarketRecord.id).label("record_count"),
        )
        .join(MarketRecord, MarketRecord.entity_id == WikiEntity.id)
        .where(MarketRecord.side.is_not(None))
        .group_by(
            WikiEntity.id,
            WikiEntity.external_id,
            WikiEntity.display_name,
            WikiEntity.name_normalized,
        )
    )
    if q:
        query = query.where(WikiEntity.display_name.ilike(f"%{q}%"))

    rows = db.execute(query).all()
    if not rows:
        return MarketItemsResponse(items=[])

    entity_ids = [row.id for row in rows]
    entities_by_id = {
        entity.id: entity
        for entity in db.scalars(select(WikiEntity).where(WikiEntity.id.in_(entity_ids))).all()
    }

    groups: dict[str, list] = defaultdict(list)
    for row in rows:
        key = row.name_normalized or str(row.id)
        groups[key].append(row)

    items: list[MarketItemOption] = []
    for group in groups.values():
        entities = [entities_by_id[row.id] for row in group if row.id in entities_by_id]
        canonical = _pick_canonical_entity(db, entities)
        if canonical is None:
            continue
        items.append(
            MarketItemOption(
                id=canonical.id,
                external_id=canonical.external_id,
                display_name=clean_display_name(canonical.display_name),
                record_count=sum(row.record_count for row in group),
            )
        )

    items.sort(key=lambda item: item.record_count, reverse=True)
    return MarketItemsResponse(items=items[:limit])


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
    entity_ids = [e.id for e in entities]

    stats_rows = (
        db.scalars(
            select(ItemStatistics).where(
                ItemStatistics.entity_id.in_(entity_ids),
                ItemStatistics.period == "all",
            )
        ).all()
        if entity_ids
        else []
    )
    stats_by_entity = {s.entity_id: s for s in stats_rows}

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)
    records_by_entity: dict[uuid.UUID, list[MarketRecord]] = defaultdict(list)
    if entity_ids:
        day_records = db.scalars(
            select(MarketRecord)
            .where(MarketRecord.entity_id.in_(entity_ids))
            .where(MarketRecord.side == "sell")
            .where(MarketRecord.recorded_at >= cutoff)
            .order_by(MarketRecord.recorded_at.desc())
        ).all()
        for record in day_records:
            if record.entity_id is not None:
                records_by_entity[record.entity_id].append(record)

    craft_rows = (
        db.scalars(select(CraftItem).where(CraftItem.external_id.in_(id_list))).all()
        if id_list
        else []
    )
    craft_by_ext = {row.external_id: row for row in craft_rows}

    empty = {
        "day_vwap": None,
        "avg_price": None,
        "last_price": None,
        "npc_sell": None,
        "npc_buy": None,
    }
    result: dict[str, dict] = {}
    for ext_id in id_list:
        entity = entity_by_ext.get(ext_id)
        craft_item = craft_by_ext.get(ext_id)
        if not entity:
            result[str(ext_id)] = dict(empty)
            continue
        st = stats_by_entity.get(entity.id)
        day_agg = aggregate_lots(
            latest_lots_per_seller(without_outliers(records_by_entity.get(entity.id, [])))
        )
        day_vwap = day_agg["vwap"]
        npc_sell = _parse_npc_sell(entity.stats)
        if npc_sell is None and craft_item and craft_item.npc_sell is not None:
            npc_sell = float(craft_item.npc_sell)
        npc_buy = None
        if craft_item:
            buy_val = craft_item.npc_buy
            if buy_val is None:
                buy_val = compute_npc_buy(
                    craft_item.npc_sell,
                    craft_item.grade,
                    craft_item.category,
                )
            npc_buy = float(buy_val) if buy_val is not None else None
        static = static_avg_price(ext_id)
        result[str(ext_id)] = {
            "day_vwap": static if static is not None else (float(day_vwap) if day_vwap is not None else None),
            "avg_price": static if static is not None else (float(st.avg_price) if st and st.avg_price is not None else None),
            "last_price": static if static is not None else (float(st.last_price) if st and st.last_price is not None else None),
            "npc_sell": npc_sell,
            "npc_buy": npc_buy,
        }
    return result


def trading_chart(
    db: Session,
    entity_id: uuid.UUID,
    period: str,
    from_date: datetime | None,
    to_date: datetime | None,
    soul_crystal: str | None = None,
    enchant_level: int | str | None = None,
    rarity: str | None = None,
    armor_class: str | None = None,
    sealed: str | bool | None = None,
) -> TradingChartResponse:
    get_item_or_404(db, entity_id)
    start, end = resolve_time_range(period, from_date, to_date)
    records, seller_names = fetch_records(
        db, entity_id, start, end,
        soul_crystal=soul_crystal, enchant_level=enchant_level, rarity=rarity, armor_class=armor_class, sealed=sealed,
    )
    clean, outliers, excluded_count = _split_outliers(records)
    return TradingChartResponse(
        entity_id=entity_id,
        from_date=start,
        to_date=end,
        deals=[ChartDealPoint(**d) for d in build_chart_deals(clean, seller_names)],
        volume_buckets=[VolumeBucket(**b) for b in build_volume_buckets(clean)],
        excluded_outlier_count=excluded_count,
        outlier_deals=[ChartDealPoint(**d) for d in build_chart_deals(outliers, seller_names)],
    )


def trading_analytics(
    db: Session,
    entity_id: uuid.UUID,
    period: str,
    from_date: datetime | None,
    to_date: datetime | None,
    soul_crystal: str | None = None,
    enchant_level: int | str | None = None,
    rarity: str | None = None,
    armor_class: str | None = None,
    sealed: str | bool | None = None,
) -> TradingAnalyticsResponse:
    get_item_or_404(db, entity_id)
    start, end = resolve_time_range(period, from_date, to_date)
    records, _ = fetch_records(
        db, entity_id, start, end,
        soul_crystal=soul_crystal, enchant_level=enchant_level, rarity=rarity, armor_class=armor_class, sealed=sealed,
    )
    clean, _, excluded_count = _split_outliers(records)
    stats = compute_analytics(clean)
    max_price_deal = stats.pop("max_price_deal")
    max_volume_deal = stats.pop("max_volume_deal")
    return TradingAnalyticsResponse(
        **stats,
        max_price_deal=DealHighlight(**max_price_deal) if max_price_deal else None,
        max_volume_deal=DealHighlight(**max_volume_deal) if max_volume_deal else None,
        excluded_outlier_count=excluded_count,
    )


def order_book(
    db: Session,
    entity_id: uuid.UUID,
    period: str,
    from_date: datetime | None,
    to_date: datetime | None,
    soul_crystal: str | None = None,
    enchant_level: int | str | None = None,
    rarity: str | None = None,
    armor_class: str | None = None,
    sealed: str | bool | None = None,
) -> OrderBookResponse:
    get_item_or_404(db, entity_id)
    start, end = resolve_time_range(period, from_date, to_date)
    records, _ = fetch_records(
        db, entity_id, start, end,
        soul_crystal=soul_crystal, enchant_level=enchant_level, rarity=rarity, armor_class=armor_class, sealed=sealed,
    )
    clean, _, _ = _split_outliers(records)
    book = build_order_book(clean)
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
    soul_crystal: str | None = None,
    enchant_level: int | str | None = None,
    rarity: str | None = None,
    armor_class: str | None = None,
    sealed: str | bool | None = None,
) -> LuckyMomentsResponse:
    get_item_or_404(db, entity_id)
    start, end = resolve_time_range(period, from_date, to_date)
    records, seller_names = fetch_records(
        db, entity_id, start, end,
        soul_crystal=soul_crystal, enchant_level=enchant_level, rarity=rarity, armor_class=armor_class, sealed=sealed,
    )
    clean, _, _ = _split_outliers(records)
    events = detect_lucky_moments(clean, seller_names)
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


def buy_plan(db: Session, entity_id: uuid.UUID, quantity: int) -> BuyPlanResponse:
    get_item_or_404(db, entity_id)
    plan = build_buy_plan(db, entity_id, quantity)
    return BuyPlanResponse(
        entity_id=plan["entity_id"],
        requested_quantity=plan["requested_quantity"],
        filled_quantity=plan["filled_quantity"],
        shortfall=plan["shortfall"],
        total_cost=plan["total_cost"],
        avg_fill_price=plan["avg_fill_price"],
        lots=[BuyPlanLot(**lot) for lot in plan["lots"]],
    )


def top_offers(
    db: Session,
    entity_id: uuid.UUID,
    limit: int = 5,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> TopOffersResponse:
    get_item_or_404(db, entity_id)
    data = build_top_offers(db, entity_id, limit=limit, from_date=from_date, to_date=to_date)
    return TopOffersResponse(
        entity_id=data["entity_id"],
        sells=[TopOfferLot(**lot) for lot in data["sells"]],
        buys=[TopOfferLot(**lot) for lot in data["buys"]],
    )


def craft_monitor(
    db: Session,
    period: str,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> CraftMonitorResponse:
    if from_date and to_date:
        resolved = "custom"
    elif period in CRAFT_MONITOR_PERIOD_HOURS:
        resolved = period
    else:
        raise AppError(
            f"Unsupported period: {period}",
            code="bad_request",
            status_code=400,
        )
    items = build_craft_monitor_cards(db, period, from_date, to_date)
    return CraftMonitorResponse(
        period=resolved,
        items=[CraftMonitorCard(**item) for item in items],
    )


def market_variants(db: Session, entity_id: uuid.UUID) -> MarketVariantsResponse:
    """Distinct variant facets recorded for one base item."""
    get_item_or_404(db, entity_id)
    soul_rows = db.scalars(
        select(MarketRecord.soul_crystal)
        .where(MarketRecord.entity_id == entity_id)
        .where(MarketRecord.soul_crystal.is_not(None))
        .distinct()
    ).all()
    rarity_rows = db.scalars(
        select(MarketRecord.rarity)
        .where(MarketRecord.entity_id == entity_id)
        .where(MarketRecord.rarity.is_not(None))
        .distinct()
    ).all()
    armor_rows = db.scalars(
        select(MarketRecord.armor_class)
        .where(MarketRecord.entity_id == entity_id)
        .where(MarketRecord.armor_class.is_not(None))
        .distinct()
    ).all()
    enchant_rows = db.scalars(
        select(MarketRecord.enchant_level)
        .where(MarketRecord.entity_id == entity_id)
        .where(MarketRecord.enchant_level.is_not(None))
        .distinct()
    ).all()
    has_sealed = db.scalar(
        select(func.count())
        .select_from(MarketRecord)
        .where(MarketRecord.entity_id == entity_id)
        .where(MarketRecord.sealed.is_not(None))
    ) or 0
    return MarketVariantsResponse(
        soul_crystals=sorted(v for v in soul_rows if v),
        rarities=sorted(v for v in rarity_rows if v),
        armor_classes=sorted(v for v in armor_rows if v),
        enchant_levels=sorted(v for v in enchant_rows if v is not None),
        has_sealed=bool(has_sealed),
    )


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
    soul_crystal: str | None = None,
    enchant_level: int | str | None = None,
    rarity: str | None = None,
    armor_class: str | None = None,
    sealed: str | bool | None = None,
) -> TradesListResponse:
    get_item_or_404(db, entity_id)
    start, end = resolve_time_range(period, from_date, to_date)

    all_records, _ = fetch_records(
        db, entity_id, start, end,
        soul_crystal=soul_crystal, enchant_level=enchant_level, rarity=rarity, armor_class=armor_class, sealed=sealed,
    )
    outlier_id_set = outlier_ids(all_records)

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
    query = apply_variant_filters(query, soul_crystal, enchant_level, rarity, armor_class, sealed)
    count_query = apply_variant_filters(count_query, soul_crystal, enchant_level, rarity, armor_class, sealed)

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
            soul_crystal=record.soul_crystal,
            rarity=record.rarity,
            armor_class=record.armor_class,
            sealed=record.sealed,
            enchant_level=record.enchant_level,
            is_outlier=record.id in outlier_id_set,
        )
        for record, seller_name in rows
    ]
    return TradesListResponse(items=items, total=total, page=page, limit=limit)
