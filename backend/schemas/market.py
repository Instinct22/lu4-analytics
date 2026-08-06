import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from schemas.text import UnescapedStr


class DashboardResponse(BaseModel):
    entity_counts: dict[str, int]
    total_imports: int
    total_market_records: int
    unmatched_records: int
    recent_imports: list[dict]


class MarketTimelinePoint(BaseModel):
    bucket_start: datetime
    median_price: Decimal
    weighted_avg: Decimal | None
    seller_count: int
    record_count: int
    min_price: Decimal
    max_price: Decimal


class MarketTimelineSideSeries(BaseModel):
    buy: list[MarketTimelinePoint]
    sell: list[MarketTimelinePoint]


class MarketTimelineResponse(BaseModel):
    entity_id: uuid.UUID
    interval: str
    from_date: datetime | None
    to_date: datetime | None
    adena: MarketTimelineSideSeries
    master_coin: MarketTimelineSideSeries


class MarketItemOption(BaseModel):
    id: uuid.UUID
    external_id: int | None = None
    display_name: UnescapedStr
    record_count: int


class MarketItemsResponse(BaseModel):
    items: list[MarketItemOption]


class MarketVariantsResponse(BaseModel):
    soul_crystals: list[str]
    rarities: list[str]
    armor_classes: list[str] = []
    enchant_levels: list[int]
    has_sealed: bool = False


class SearchResultGroup(BaseModel):
    entity_type: str
    items: list[dict]
    total: int


class SearchResponse(BaseModel):
    query: str
    groups: list[SearchResultGroup]
