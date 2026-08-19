"""Admin API: user management and role permission matrix."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select

from api.deps import DbSession, hash_password, require_permission, user_has_permission
from core.client_ip import client_ip
from core.permissions import (
    ASSIGNABLE_ROLES,
    PERMISSION_LABELS,
    PERMISSIONS,
    ROLES,
    default_allowed,
    is_superadmin,
)
from models.login_log import LoginLog
from models.raid_timer_log import RaidTimerLog
from models.permissions import RolePermission
from models.user import User
from models.user_creation_log import UserCreationLog
from schemas.auth import (
    CreateUserRequest,
    CustomRoleItem,
    CustomRolesResponse,
    CreateCustomRoleRequest,
    LoginLogItem,
    LoginLogsResponse,
    BulkDeleteMarketRecordsRequest,
    BulkUpdateMarketRecordsRequest,
    MarketRecordsResponse,
    PermissionEntry,
    PermissionGroup,
    PermissionGroupsResponse,
    PublicRolesResponse,
    QuickCreateRequest,
    QuickCreateResponse,
    RaidTimerLogItem,
    RaidTimerLogsResponse,
    RolePermissionsResponse,
    CraftMonitorResponse,
    UpdateCraftMonitorRequest,
    UpdateLevelRestrictionRequest,
    UpdatePermissionGroupsRequest,
    UpdatePublicRolesRequest,
    UpdateRolePermissionsRequest,
    LevelRestrictionResponse,
    UpdateUserRequest,
    UserCreationLogItem,
    UserCreationLogsResponse,
    UserResponse,
)
from services.admin_market_records import (
    bulk_delete_market_records,
    bulk_update_market_records,
    delete_market_record,
    list_market_records,
)
from services.admin_settings import (
    generate_password,
    generate_username,
    get_craft_monitor,
    get_level_preset,
    get_level_restriction,
    get_permission_groups,
    get_public_roles,
    set_craft_monitor,
    set_level_preset,
    set_level_restriction,
    set_permission_groups,
    set_public_roles,
)
from services.custom_roles import (
    create_custom_role,
    delete_custom_role,
    editable_roles,
    is_custom_role,
    list_custom_roles,
    role_label,
)
from services.api_tokens import (
    create_api_token,
    legacy_key_configured,
    list_api_tokens,
    list_scope_catalog,
    revoke_api_token,
)
from schemas.api_token import (
    ApiTokenItem,
    ApiTokenScopesResponse,
    ApiTokensListResponse,
    CreateApiTokenRequest,
    CreateApiTokenResponse,
)

router = APIRouter()


def _require_api_tokens_manage(user: User, db: DbSession) -> None:
    if not user_has_permission(db, user, "admin.api_tokens_manage"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _require_superadmin(user: User) -> None:
    if not is_superadmin(user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin only")


def _require_logs(user: User, db: DbSession) -> None:
    if not user_has_permission(db, user, "admin.logs_view"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _require_roles_manage(user: User, db: DbSession) -> None:
    if not user_has_permission(db, user, "admin.roles_manage"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def _assignable_roles_for(admin: User, db: DbSession) -> list[str]:
    custom = [r.key for r in list_custom_roles(db)]
    if is_superadmin(admin.role):
        return list(ASSIGNABLE_ROLES) + custom
    return get_public_roles(db)


def _validate_assignable_role(role: str, admin: User, db: DbSession) -> str:
    allowed = _assignable_roles_for(admin, db)
    if role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Allowed: {', '.join(allowed)}",
        )
    return role


def _validate_matrix_role(role: str, db: DbSession) -> str:
    if role == "superadmin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Allowed: {', '.join(editable_roles(db))}",
        )
    if role in ROLES or is_custom_role(db, role):
        return role
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Invalid role. Allowed: {', '.join(editable_roles(db))}",
    )


def _users_query(admin: User):
    q = select(User)
    if not is_superadmin(admin.role):
        q = q.where(
            User.role != "superadmin",
            User.created_by_id == admin.id,
        )
    return q.order_by(User.username)


def _can_manage_user(admin: User, target: User) -> bool:
    if is_superadmin(admin.role):
        return True
    if target.role == "superadmin":
        return False
    if target.created_by_id != admin.id:
        return False
    return True


def _log_user_creation(
    db: DbSession,
    *,
    creator: User,
    created: User,
    request: Request | None,
) -> None:
    ip = client_ip(request) if request else ""
    db.add(
        UserCreationLog(
            id=uuid.uuid4(),
            creator_id=creator.id,
            creator_username=creator.username,
            created_user_id=created.id,
            created_username=created.username,
            role=created.role,
            ip_address=ip,
        )
    )


@router.get("/users", response_model=list[UserResponse])
def list_users(db: DbSession, admin: User = Depends(require_permission("nav.admin"))):
    return db.scalars(_users_query(admin)).all()


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    body: CreateUserRequest,
    request: Request,
    db: DbSession,
    admin: User = Depends(require_permission("nav.admin")),
):
    role = _validate_assignable_role(body.role, admin, db)
    username = body.username.strip()
    if not username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username required")
    existing = db.scalar(select(User).where(User.username == username))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")
    user = User(
        id=uuid.uuid4(),
        username=username,
        password_hash=hash_password(body.password),
        role=role,
        is_active=True,
        created_by_id=admin.id,
    )
    db.add(user)
    _log_user_creation(db, creator=admin, created=user, request=request)
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/users/quick-create",
    response_model=QuickCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def quick_create_user(
    body: QuickCreateRequest,
    request: Request,
    db: DbSession,
    admin: User = Depends(require_permission("admin.users_quick_create")),
):
    role = _validate_assignable_role(body.role, admin, db)
    username = generate_username(db)
    password = generate_password()
    user = User(
        id=uuid.uuid4(),
        username=username,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
        created_by_id=admin.id,
    )
    db.add(user)
    _log_user_creation(db, creator=admin, created=user, request=request)
    db.commit()
    db.refresh(user)
    return QuickCreateResponse(username=username, password=password, user=UserResponse.model_validate(user))


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: uuid.UUID,
    body: UpdateUserRequest,
    db: DbSession,
    admin: User = Depends(require_permission("nav.admin")),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not _can_manage_user(admin, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if body.role is not None:
        user.role = _validate_assignable_role(body.role, admin, db)
    if body.password is not None:
        user.password_hash = hash_password(body.password)
    if body.is_active is not None:
        user.is_active = body.is_active
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: uuid.UUID,
    db: DbSession,
    admin: User = Depends(require_permission("nav.admin")),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")
    if not _can_manage_user(admin, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    db.delete(user)
    db.commit()


@router.get("/market-records", response_model=MarketRecordsResponse)
def admin_list_market_records(
    db: DbSession,
    admin: User = Depends(require_permission("nav.admin")),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=50),
    search: str | None = Query(None, max_length=128),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    product: str | None = Query(None, max_length=128),
    seller: str | None = Query(None, max_length=128),
    price: str | None = Query(None, max_length=64),
    currency: str | None = Query(None, max_length=32),
    side: str | None = Query(None, max_length=16),
    quantity: str | None = Query(None, max_length=32),
    outliers_only: bool = Query(False),
):
    _require_superadmin(admin)
    return list_market_records(
        db,
        page=page,
        limit=limit,
        search=search,
        date_from=date_from,
        date_to=date_to,
        product=product,
        seller=seller,
        price=price,
        currency=currency,
        side=side,
        quantity=quantity,
        outliers_only=outliers_only,
    )


@router.patch("/market-records/bulk")
def admin_bulk_update_market_records(
    body: BulkUpdateMarketRecordsRequest,
    db: DbSession,
    admin: User = Depends(require_permission("nav.admin")),
):
    _require_superadmin(admin)
    updated = bulk_update_market_records(db, body)
    return {"updated": updated}


@router.post("/market-records/bulk-delete")
def admin_bulk_delete_market_records(
    body: BulkDeleteMarketRecordsRequest,
    db: DbSession,
    admin: User = Depends(require_permission("nav.admin")),
):
    _require_superadmin(admin)
    deleted = bulk_delete_market_records(db, body)
    return {"deleted": deleted}


@router.delete("/market-records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_market_record(
    record_id: uuid.UUID,
    db: DbSession,
    admin: User = Depends(require_permission("nav.admin")),
):
    _require_superadmin(admin)
    delete_market_record(db, record_id)


@router.get("/login-logs", response_model=LoginLogsResponse)
def list_login_logs(
    db: DbSession,
    admin: User = Depends(require_permission("nav.admin")),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
):
    _require_logs(admin, db)
    total = db.scalar(select(func.count()).select_from(LoginLog)) or 0
    rows = db.scalars(
        select(LoginLog)
        .order_by(LoginLog.logged_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return LoginLogsResponse(
        items=[LoginLogItem.model_validate(r) for r in rows],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/raid-timer-logs", response_model=RaidTimerLogsResponse)
def list_raid_timer_logs(
    db: DbSession,
    admin: User = Depends(require_permission("nav.admin")),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
):
    _require_logs(admin, db)
    total = db.scalar(select(func.count()).select_from(RaidTimerLog)) or 0
    rows = db.scalars(
        select(RaidTimerLog)
        .order_by(RaidTimerLog.logged_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return RaidTimerLogsResponse(
        items=[RaidTimerLogItem.model_validate(r) for r in rows],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/user-creation-logs", response_model=UserCreationLogsResponse)
def list_user_creation_logs(
    db: DbSession,
    admin: User = Depends(require_permission("nav.admin")),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
):
    _require_logs(admin, db)
    total = db.scalar(select(func.count()).select_from(UserCreationLog)) or 0
    rows = db.scalars(
        select(UserCreationLog)
        .order_by(UserCreationLog.logged_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return UserCreationLogsResponse(
        items=[UserCreationLogItem.model_validate(r) for r in rows],
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/settings/public-roles", response_model=PublicRolesResponse)
def get_public_roles_setting(db: DbSession, admin: User = Depends(require_permission("nav.admin"))):
    _require_superadmin(admin)
    return PublicRolesResponse(roles=get_public_roles(db))


@router.put("/settings/public-roles", response_model=PublicRolesResponse)
def update_public_roles_setting(
    body: UpdatePublicRolesRequest,
    db: DbSession,
    admin: User = Depends(require_permission("nav.admin")),
):
    _require_superadmin(admin)
    cleaned: list[str] = []
    for role in body.roles:
        if role in ROLES and role not in ("superadmin", "admin"):
            cleaned.append(role)
        elif is_custom_role(db, role):
            cleaned.append(role)
    if not cleaned:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one public role required")
    roles = set_public_roles(db, cleaned)
    db.commit()
    return PublicRolesResponse(roles=roles)


@router.get("/settings/permission-groups", response_model=PermissionGroupsResponse)
def get_permission_groups_setting(db: DbSession, admin: User = Depends(require_permission("nav.admin"))):
    _require_superadmin(admin)
    groups = get_permission_groups(db)
    return PermissionGroupsResponse(groups=[PermissionGroup.model_validate(g) for g in groups])


@router.put("/settings/permission-groups", response_model=PermissionGroupsResponse)
def update_permission_groups_setting(
    body: UpdatePermissionGroupsRequest,
    db: DbSession,
    admin: User = Depends(require_permission("nav.admin")),
):
    _require_superadmin(admin)
    groups = set_permission_groups(db, [g.model_dump() for g in body.groups])
    db.commit()
    return PermissionGroupsResponse(groups=body.groups)


@router.get("/settings/level-restriction", response_model=LevelRestrictionResponse)
def get_level_restriction_setting(db: DbSession, admin: User = Depends(require_permission("admin.level_restriction"))):
    _require_superadmin(admin)
    bounds = get_level_restriction(db)
    return LevelRestrictionResponse(min=bounds["min"], max=bounds["max"])


@router.put("/settings/level-restriction", response_model=LevelRestrictionResponse)
def update_level_restriction_setting(
    body: UpdateLevelRestrictionRequest,
    db: DbSession,
    admin: User = Depends(require_permission("admin.level_restriction")),
):
    _require_superadmin(admin)
    bounds = set_level_restriction(db, body.min, body.max)
    db.commit()
    return LevelRestrictionResponse(min=bounds["min"], max=bounds["max"])


@router.get("/settings/level-preset", response_model=LevelRestrictionResponse)
def get_level_preset_setting(db: DbSession, admin: User = Depends(require_permission("admin.level_preset"))):
    bounds = get_level_preset(db)
    return LevelRestrictionResponse(min=bounds["min"], max=bounds["max"])


@router.put("/settings/level-preset", response_model=LevelRestrictionResponse)
def update_level_preset_setting(
    body: UpdateLevelRestrictionRequest,
    db: DbSession,
    admin: User = Depends(require_permission("admin.level_preset")),
):
    bounds = set_level_preset(db, body.min, body.max)
    db.commit()
    return LevelRestrictionResponse(min=bounds["min"], max=bounds["max"])


@router.get("/settings/craft-monitor", response_model=CraftMonitorResponse)
def get_craft_monitor_setting(
    db: DbSession,
    admin: User = Depends(require_permission("nav.admin")),
):
    _require_superadmin(admin)
    value = get_craft_monitor(db)
    return CraftMonitorResponse(selectedIds=value["selectedIds"])


@router.put("/settings/craft-monitor", response_model=CraftMonitorResponse)
def update_craft_monitor_setting(
    body: UpdateCraftMonitorRequest,
    db: DbSession,
    admin: User = Depends(require_permission("nav.admin")),
):
    _require_superadmin(admin)
    value = set_craft_monitor(db, body.selectedIds)
    db.commit()
    return CraftMonitorResponse(selectedIds=value["selectedIds"])


@router.get("/custom-roles", response_model=CustomRolesResponse)
def list_custom_roles_endpoint(
    db: DbSession,
    admin: User = Depends(require_permission("nav.admin")),
):
    _require_superadmin(admin)
    rows = list_custom_roles(db)
    return CustomRolesResponse(items=[CustomRoleItem.model_validate(r) for r in rows])


@router.post("/custom-roles", response_model=CustomRoleItem, status_code=status.HTTP_201_CREATED)
def create_custom_role_endpoint(
    body: CreateCustomRoleRequest,
    db: DbSession,
    admin: User = Depends(require_permission("nav.admin")),
):
    _require_superadmin(admin)
    try:
        role = create_custom_role(
            db,
            label=body.label,
            preset_role=body.preset_role,
            key=body.key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()
    db.refresh(role)
    return CustomRoleItem.model_validate(role)


@router.delete("/custom-roles/{role_key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_custom_role_endpoint(
    role_key: str,
    db: DbSession,
    admin: User = Depends(require_permission("nav.admin")),
):
    _require_superadmin(admin)
    try:
        delete_custom_role(db, role_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    db.commit()


@router.get("/roles", response_model=list[RolePermissionsResponse])
def list_role_permissions(db: DbSession, admin: User = Depends(require_permission("nav.admin"))):
    _require_roles_manage(admin, db)
    rows = db.scalars(select(RolePermission)).all()
    roles = editable_roles(db)
    by_role: dict[str, dict[str, bool]] = {role: {} for role in roles}
    for row in rows:
        if row.role in by_role:
            by_role[row.role][row.permission] = row.allowed

    result: list[RolePermissionsResponse] = []
    for role in roles:
        stored = by_role[role]
        entries = []
        for perm in PERMISSIONS:
            allowed = stored[perm] if perm in stored else default_allowed(role, perm)
            entries.append(
                PermissionEntry(
                    permission=perm,
                    allowed=allowed,
                    label=PERMISSION_LABELS.get(perm, perm),
                )
            )
        result.append(
            RolePermissionsResponse(
                role=role,
                label=role_label(db, role),
                permissions=entries,
            )
        )
    return result


@router.put("/roles/{role}", response_model=RolePermissionsResponse)
def update_role_permissions(
    role: str,
    body: UpdateRolePermissionsRequest,
    db: DbSession,
    admin: User = Depends(require_permission("nav.admin")),
):
    _require_roles_manage(admin, db)
    role = _validate_matrix_role(role, db)
    for perm, allowed in body.permissions.items():
        if perm not in PERMISSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown permission: {perm}",
            )
        row = db.scalar(
            select(RolePermission).where(
                RolePermission.role == role,
                RolePermission.permission == perm,
            )
        )
        if row is None:
            db.add(RolePermission(role=role, permission=perm, allowed=bool(allowed)))
        else:
            row.allowed = bool(allowed)
    db.commit()

    stored = {
        r.permission: r.allowed
        for r in db.scalars(select(RolePermission).where(RolePermission.role == role)).all()
    }
    entries = [
        PermissionEntry(
            permission=perm,
            allowed=stored[perm] if perm in stored else default_allowed(role, perm),
            label=PERMISSION_LABELS.get(perm, perm),
        )
        for perm in PERMISSIONS
    ]
    return RolePermissionsResponse(
        role=role,
        label=role_label(db, role),
        permissions=entries,
    )


@router.get("/api-tokens/scopes", response_model=ApiTokenScopesResponse)
def get_api_token_scopes(db: DbSession, admin: User = Depends(require_permission("nav.admin"))):
    _require_api_tokens_manage(admin, db)
    return ApiTokenScopesResponse(items=list_scope_catalog())


@router.get("/api-tokens", response_model=ApiTokensListResponse)
def list_api_tokens_admin(db: DbSession, admin: User = Depends(require_permission("nav.admin"))):
    _require_api_tokens_manage(admin, db)
    return ApiTokensListResponse(
        items=list_api_tokens(db),
        legacy_key_configured=legacy_key_configured(),
    )


@router.post("/api-tokens", response_model=CreateApiTokenResponse)
def create_api_token_admin(
    body: CreateApiTokenRequest,
    db: DbSession,
    admin: User = Depends(require_permission("nav.admin")),
):
    _require_api_tokens_manage(admin, db)
    return create_api_token(db, body, admin)


@router.delete("/api-tokens/{token_id}", response_model=ApiTokenItem)
def revoke_api_token_admin(
    token_id: uuid.UUID,
    db: DbSession,
    admin: User = Depends(require_permission("nav.admin")),
):
    _require_api_tokens_manage(admin, db)
    return revoke_api_token(db, token_id)
