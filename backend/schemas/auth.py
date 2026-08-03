import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from schemas.text import UnescapedStr


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str | None
    role: str
    is_active: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class MeResponse(UserResponse):
    permissions: list[str]


class RefreshRequest(BaseModel):
    refresh_token: str


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
    role: str = "user"


class UpdateUserRequest(BaseModel):
    password: str | None = Field(default=None, min_length=1, max_length=128)
    role: str | None = None
    is_active: bool | None = None


class PermissionEntry(BaseModel):
    permission: str
    allowed: bool
    label: str | None = None


class RolePermissionsResponse(BaseModel):
    role: str
    label: str
    permissions: list[PermissionEntry]


class UpdateRolePermissionsRequest(BaseModel):
    permissions: dict[str, bool]


class LoginLogItem(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    username: str
    ip_address: str
    logged_at: datetime

    model_config = {"from_attributes": True}


class LoginLogsResponse(BaseModel):
    items: list[LoginLogItem]
    total: int
    page: int
    limit: int


class RaidTimerLogItem(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    username: str
    ip_address: str
    boss_external_id: int
    boss_name: str
    action: str
    killed_at: datetime | None = None
    logged_at: datetime

    model_config = {"from_attributes": True}


class RaidTimerLogsResponse(BaseModel):
    items: list[RaidTimerLogItem]
    total: int
    page: int
    limit: int


class UserCreationLogItem(BaseModel):
    id: uuid.UUID
    creator_id: uuid.UUID | None = None
    creator_username: str
    created_user_id: uuid.UUID | None = None
    created_username: str
    role: str
    ip_address: str
    logged_at: datetime

    model_config = {"from_attributes": True}


class UserCreationLogsResponse(BaseModel):
    items: list[UserCreationLogItem]
    total: int
    page: int
    limit: int


class QuickCreateRequest(BaseModel):
    role: str = "user"


class QuickCreateResponse(BaseModel):
    username: str
    password: str
    user: UserResponse


class PublicRolesResponse(BaseModel):
    roles: list[str]


class UpdatePublicRolesRequest(BaseModel):
    roles: list[str]


class LevelRestrictionResponse(BaseModel):
    min: int
    max: int


class UpdateLevelRestrictionRequest(BaseModel):
    min: int
    max: int


class CraftMonitorResponse(BaseModel):
    selectedIds: list[int]


class UpdateCraftMonitorRequest(BaseModel):
    selectedIds: list[int]


class PermissionGroup(BaseModel):
    id: str
    label: str
    permissions: list[str]


class PermissionGroupsResponse(BaseModel):
    groups: list[PermissionGroup]


class UpdatePermissionGroupsRequest(BaseModel):
    groups: list[PermissionGroup]


class CustomRoleItem(BaseModel):
    key: str
    label: str

    model_config = {"from_attributes": True}


class CustomRolesResponse(BaseModel):
    items: list[CustomRoleItem]


class CreateCustomRoleRequest(BaseModel):
    label: str
    preset_role: str = "user"
    key: str | None = None


class MarketRecordAdminItem(BaseModel):
    id: uuid.UUID
    entity_id: uuid.UUID | None = None
    item_name: UnescapedStr | None = None
    product_name_raw: UnescapedStr
    seller_name: str
    price: Decimal
    currency: str
    side: str | None = None
    quantity: int | None = None
    recorded_at: datetime


class MarketRecordsResponse(BaseModel):
    items: list[MarketRecordAdminItem]
    total: int
    page: int
    limit: int
