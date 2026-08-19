import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ApiTokenScope = Literal["import", "market_scan", "trading_scan", "raid_life"]

API_TOKEN_SCOPES: tuple[ApiTokenScope, ...] = ("import", "market_scan", "trading_scan", "raid_life")

SCOPE_LABELS: dict[str, str] = {
    "import": "Импорт цен (POST /api/import)",
    "market_scan": "Скан рынка (POST /api/market/scan)",
    "trading_scan": "Скан инвентаря (POST /api/trading/inventory-scan)",
    "raid_life": "Статус жизни РБ (GET /api/raid/boss-life)",
}


class ApiTokenScopeItem(BaseModel):
    scope: ApiTokenScope
    label: str


class ApiTokenScopesResponse(BaseModel):
    items: list[ApiTokenScopeItem]


class CreateApiTokenRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    scopes: list[ApiTokenScope] = Field(min_length=1)
    expires_at: datetime | None = None


class ApiTokenItem(BaseModel):
    id: uuid.UUID
    name: str
    token_prefix: str
    scopes: list[str]
    created_by_id: uuid.UUID | None
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None
    is_active: bool

    model_config = {"from_attributes": True}


class ApiTokensListResponse(BaseModel):
    items: list[ApiTokenItem]
    legacy_key_configured: bool


class CreateApiTokenResponse(BaseModel):
    token: str
    item: ApiTokenItem
