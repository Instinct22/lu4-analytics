"""Admin API: user management and role permission matrix."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from api.deps import DbSession, hash_password, require_permission
from core.permissions import (
    PERMISSION_LABELS,
    PERMISSIONS,
    ROLE_LABELS,
    ROLES,
    default_allowed,
)
from models.login_log import LoginLog
from models.permissions import RolePermission
from models.user import User
from schemas.auth import (
    CreateUserRequest,
    LoginLogItem,
    LoginLogsResponse,
    PermissionEntry,
    RolePermissionsResponse,
    UpdateRolePermissionsRequest,
    UpdateUserRequest,
    UserResponse,
)

router = APIRouter()

AdminUser = Depends(require_permission("nav.admin"))


def _validate_role(role: str) -> str:
    if role not in ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Allowed: {', '.join(ROLES)}",
        )
    return role


@router.get("/users", response_model=list[UserResponse], dependencies=[AdminUser])
def list_users(db: DbSession):
    users = db.scalars(select(User).order_by(User.username)).all()
    return users


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED, dependencies=[AdminUser])
def create_user(body: CreateUserRequest, db: DbSession):
    role = _validate_role(body.role)
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
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserResponse, dependencies=[AdminUser])
def update_user(user_id: uuid.UUID, body: UpdateUserRequest, db: DbSession):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if body.role is not None:
        user.role = _validate_role(body.role)
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
    db.delete(user)
    db.commit()


@router.get("/login-logs", response_model=LoginLogsResponse)
def list_login_logs(
    db: DbSession,
    admin: User = Depends(require_permission("nav.admin")),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=100),
):
    if admin.username != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only primary admin")
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


@router.get("/roles", response_model=list[RolePermissionsResponse], dependencies=[AdminUser])
def list_role_permissions(db: DbSession):
    rows = db.scalars(select(RolePermission)).all()
    by_role: dict[str, dict[str, bool]] = {role: {} for role in ROLES}
    for row in rows:
        if row.role in by_role:
            by_role[row.role][row.permission] = row.allowed

    result: list[RolePermissionsResponse] = []
    for role in ROLES:
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
                label=ROLE_LABELS.get(role, role),
                permissions=entries,
            )
        )
    return result


@router.put("/roles/{role}", response_model=RolePermissionsResponse, dependencies=[AdminUser])
def update_role_permissions(role: str, body: UpdateRolePermissionsRequest, db: DbSession):
    role = _validate_role(role)
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
        label=ROLE_LABELS.get(role, role),
        permissions=entries,
    )
