import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from schemas.text import UnescapedStr


class DealHighlight(BaseModel):
    price: Decimal
    quantity: int
    recorded_at: datetime


class TradingAnalyticsResponse(BaseModel):
    min_price: Decimal | None
    max_price: Decimal | None
    avg_price: Decimal | None
    median_price: Decimal | None
    deal_count: int
    total_volume: int
    vwap: Decimal | None
    price_change: Decimal | None
    price_change_pct: Decimal | None
    avg_quantity: Decimal | None
    max_price_deal: DealHighlight | None
    max_volume_deal: DealHighlight | None
    std_dev: Decimal | None
    price_range: Decimal | None
    unique_sellers: int
    buy_count: int
    sell_count: int
    buy_sell_spread: Decimal | None
    total_value: Decimal | None


class ChartDealPoint(BaseModel):
    recorded_at: datetime
    price: Decimal
    quantity: int
    side: str | None
    seller_name: str
    total_cost: Decimal


class VolumeBucket(BaseModel):
    bucket_start: datetime
    buy_volume: int
    sell_volume: int


class TradingChartResponse(BaseModel):
    entity_id: uuid.UUID
    from_date: datetime
    to_date: datetime
    deals: list[ChartDealPoint]
    volume_buckets: list[VolumeBucket]


class OrderBookLevel(BaseModel):
    price: Decimal
    volume: int


class OrderBookResponse(BaseModel):
    buys: list[OrderBookLevel]
    sells: list[OrderBookLevel]


class LuckyMomentEvent(BaseModel):
    type: str
    severity: str
    title: str
    description: str
    recorded_at: datetime
    price: Decimal | None
    quantity: int | None
    side: str | None
    seller_name: str | None


class LuckyMomentsResponse(BaseModel):
    events: list[LuckyMomentEvent]


class ItemOverviewCard(BaseModel):
    entity_id: uuid.UUID
    display_name: UnescapedStr
    current_price: Decimal
    price_change_pct: Decimal
    total_volume: int
    deal_count: int
    sparkline: list[float]


class ItemsOverviewResponse(BaseModel):
    items: list[ItemOverviewCard]


class CraftMonitorCard(BaseModel):
    external_id: int
    entity_id: uuid.UUID | None
    display_name: UnescapedStr
    vwap: Decimal | None
    total_quantity: int
    price_change_pct: Decimal | None
    seller_count: int


class CraftMonitorResponse(BaseModel):
    period: str
    items: list[CraftMonitorCard]


class BuyPlanLot(BaseModel):
    seller_id: uuid.UUID
    seller_name: str
    price: Decimal
    available_quantity: int
    buy_quantity: int
    cost: Decimal
    recorded_at: datetime


class BuyPlanResponse(BaseModel):
    entity_id: uuid.UUID
    requested_quantity: int
    filled_quantity: int
    shortfall: int
    total_cost: Decimal
    avg_fill_price: Decimal | None
    lots: list[BuyPlanLot]


class TopOfferLot(BaseModel):
    seller_id: uuid.UUID
    seller_name: str
    quantity: int
    price: Decimal
    recorded_at: datetime


class TopOffersResponse(BaseModel):
    entity_id: uuid.UUID
    sells: list[TopOfferLot]
    buys: list[TopOfferLot]


class TradeRecordItem(BaseModel):
    id: uuid.UUID
    recorded_at: datetime
    seller_name: str
    quantity: int
    price: Decimal
    total_cost: Decimal
    side: str | None


class TradesListResponse(BaseModel):
    items: list[TradeRecordItem]
    total: int
    page: int
    limit: int
