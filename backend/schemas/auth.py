import uuid
from datetime import datetime

from pydantic import BaseModel, Field


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
