"""Pydantic schemas for shared trading inventory."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


CharacterKind = Literal["bank", "merchant"]
TradeMode = Literal["sell", "buy"]


class InventoryLineIn(BaseModel):
    item_external_id: int
    item_name: str = Field(min_length=1, max_length=512)
    quantity: int = Field(ge=0)
    unit_price: Decimal = Field(ge=0)


class InventoryLineOut(BaseModel):
    id: uuid.UUID
    item_external_id: int
    item_name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal


class CharacterCreate(BaseModel):
    kind: CharacterKind
    nick: str = Field(min_length=1, max_length=128)


class CharacterUpdate(BaseModel):
    clean_adena: Decimal = Field(ge=0)
    description: str | None = None
    trade_mode: TradeMode = "sell"
    sell_items: list[InventoryLineIn] = Field(default_factory=list)
    buy_items: list[InventoryLineIn] = Field(default_factory=list)


class CharacterOut(BaseModel):
    id: uuid.UUID
    kind: CharacterKind
    nick: str
    clean_adena: Decimal
    description: str | None
    trade_mode: TradeMode
    adena_in_items: Decimal
    buy_cost: Decimal
    total_adena: Decimal
    sort_order: int
    updated_at: datetime | None = None
    sell_items: list[InventoryLineOut] = Field(default_factory=list)
    buy_items: list[InventoryLineOut] = Field(default_factory=list)
    # Active list for the current trade_mode (compat / convenience)
    items: list[InventoryLineOut] = Field(default_factory=list)


class CharactersResponse(BaseModel):
    characters: list[CharacterOut]


class ItemSearchHit(BaseModel):
    external_id: int
    display_name: str


class ItemCatalogHit(BaseModel):
    external_id: int
    display_name: str
    group: Literal["resource", "item"] = "item"


class ItemSearchResponse(BaseModel):
    items: list[ItemSearchHit]


class ItemCatalogResponse(BaseModel):
    items: list[ItemCatalogHit]


class SnapshotCreate(BaseModel):
    label: str | None = Field(default=None, max_length=255)


class SnapshotListItem(BaseModel):
    id: uuid.UUID
    created_at: datetime
    label: str | None = None


class SnapshotsListResponse(BaseModel):
    snapshots: list[SnapshotListItem]


class SnapshotDetailResponse(BaseModel):
    id: uuid.UUID
    created_at: datetime
    label: str | None = None
    payload: dict
