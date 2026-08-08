"""HTTP layer for market timeline, trading analytics, and craft prices."""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from api.deps import DbSession, require_any_permission
from models.user import User
from schemas.market import MarketItemsResponse, MarketTimelineResponse, MarketVariantsResponse
from schemas.trading import (
    BuyPlanResponse,
    CraftMonitorResponse,
    ItemsOverviewResponse,
    LuckyMomentsResponse,
    OrderBookResponse,
    TopOffersResponse,
    TradesListResponse,
    TradingAnalyticsResponse,
    TradingChartResponse,
)
from services import market_service

router = APIRouter()

MarketUser = Annotated[
    User,
    Depends(
        require_any_permission(
            "nav.dashboard",
            "nav.charts",
            "nav.statistics",
            "feature.craft_prices",
        )
    ),
]
PricesByIdsUser = Annotated[
    User,
    Depends(require_any_permission("feature.craft_prices", "nav.trading")),
]


@router.get("/timeline", response_model=MarketTimelineResponse)
def market_timeline(
    db: DbSession,
    user: MarketUser,
    entity_id: uuid.UUID,
    interval: str = Query("5m"),
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    soul_crystal: str | None = Query(None),
    enchant_level: str | None = Query(None),
    rarity: str | None = Query(None),
    armor_class: str | None = Query(None),
    sealed: str | None = Query(None),
):
    return market_service.market_timeline(
        db, entity_id, interval, from_date, to_date, soul_crystal, enchant_level, rarity, armor_class, sealed
    )


@router.get("/items", response_model=MarketItemsResponse)
def market_items(
    db: DbSession,
    user: MarketUser,
    q: str | None = Query(None),
    limit: int = Query(30, ge=1, le=2000),
):
    return market_service.market_items(db, q, limit)


@router.get("/variants", response_model=MarketVariantsResponse)
def market_variants(
    db: DbSession,
    user: MarketUser,
    entity_id: uuid.UUID,
):
    return market_service.market_variants(db, entity_id)


@router.get("/prices-by-ids")
def prices_by_ids(
    db: DbSession,
    user: PricesByIdsUser,
    ids: str = Query(..., description="Comma-separated item external IDs"),
    period: str = Query("main", pattern="^(main|1h|12h|1d)$"),
):
    return market_service.prices_by_ids(db, ids, period)


@router.get("/chart", response_model=TradingChartResponse)
def trading_chart(
    db: DbSession,
    user: MarketUser,
    entity_id: uuid.UUID,
    period: str = Query("24h"),
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    soul_crystal: str | None = Query(None),
    enchant_level: str | None = Query(None),
    rarity: str | None = Query(None),
    armor_class: str | None = Query(None),
    sealed: str | None = Query(None),
):
    return market_service.trading_chart(
        db, entity_id, period, from_date, to_date, soul_crystal, enchant_level, rarity, armor_class, sealed
    )


@router.get("/analytics", response_model=TradingAnalyticsResponse)
def trading_analytics(
    db: DbSession,
    user: MarketUser,
    entity_id: uuid.UUID,
    period: str = Query("24h"),
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    soul_crystal: str | None = Query(None),
    enchant_level: str | None = Query(None),
    rarity: str | None = Query(None),
    armor_class: str | None = Query(None),
    sealed: str | None = Query(None),
):
    return market_service.trading_analytics(
        db, entity_id, period, from_date, to_date, soul_crystal, enchant_level, rarity, armor_class, sealed
    )


@router.get("/order-book", response_model=OrderBookResponse)
def order_book(
    db: DbSession,
    user: MarketUser,
    entity_id: uuid.UUID,
    period: str = Query("24h"),
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    soul_crystal: str | None = Query(None),
    enchant_level: str | None = Query(None),
    rarity: str | None = Query(None),
    armor_class: str | None = Query(None),
    sealed: str | None = Query(None),
):
    return market_service.order_book(
        db, entity_id, period, from_date, to_date, soul_crystal, enchant_level, rarity, armor_class, sealed
    )


@router.get("/lucky-moments", response_model=LuckyMomentsResponse)
def lucky_moments(
    db: DbSession,
    user: MarketUser,
    entity_id: uuid.UUID,
    period: str = Query("24h"),
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    soul_crystal: str | None = Query(None),
    enchant_level: str | None = Query(None),
    rarity: str | None = Query(None),
    armor_class: str | None = Query(None),
    sealed: str | None = Query(None),
):
    return market_service.lucky_moments(
        db, entity_id, period, from_date, to_date, soul_crystal, enchant_level, rarity, armor_class, sealed
    )


@router.get("/items-overview", response_model=ItemsOverviewResponse)
def items_overview(
    db: DbSession,
    user: MarketUser,
    period: str = Query("24h"),
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    limit: int = Query(60, ge=1, le=200),
):
    return market_service.items_overview(db, period, from_date, to_date, limit)


@router.get("/craft-monitor", response_model=CraftMonitorResponse)
def craft_monitor(
    db: DbSession,
    user: MarketUser,
    period: str = Query("1d", pattern="^(1h|2h|3h|6h|12h|1d|3d)$"),
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
):
    return market_service.craft_monitor(db, period, from_date, to_date)


@router.get("/buy-plan", response_model=BuyPlanResponse)
def buy_plan(
    db: DbSession,
    user: MarketUser,
    entity_id: uuid.UUID,
    quantity: int = Query(..., ge=1, le=10_000_000),
):
    return market_service.buy_plan(db, entity_id, quantity)


@router.get("/top-offers", response_model=TopOffersResponse)
def top_offers(
    db: DbSession,
    user: MarketUser,
    entity_id: uuid.UUID,
    limit: int = Query(5, ge=1, le=20),
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
):
    return market_service.top_offers(db, entity_id, limit, from_date, to_date)


@router.get("/trades", response_model=TradesListResponse)
def list_trades(
    db: DbSession,
    user: MarketUser,
    entity_id: uuid.UUID,
    side: str = Query(..., pattern="^(buy|sell)$"),
    period: str = Query("24h"),
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    search: str | None = Query(None),
    sort_by: str = Query("recorded_at", pattern="^(recorded_at|price|quantity|seller_name)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    soul_crystal: str | None = Query(None),
    enchant_level: str | None = Query(None),
    rarity: str | None = Query(None),
    armor_class: str | None = Query(None),
    sealed: str | None = Query(None),
):
    return market_service.list_trades(
        db,
        entity_id=entity_id,
        side=side,
        period=period,
        from_date=from_date,
        to_date=to_date,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        limit=limit,
        soul_crystal=soul_crystal,
        enchant_level=enchant_level,
        rarity=rarity,
        armor_class=armor_class,
        sealed=sealed,
    )
