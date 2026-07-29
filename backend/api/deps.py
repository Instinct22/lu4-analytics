import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Callable

import bcrypt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from core.permissions import DEFAULT_PERMISSIONS, PERMISSIONS, default_allowed
from database import get_db
from models.permissions import RolePermission
from models.user import User

security = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: uuid.UUID, username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "username": username, "exp": expire, "type": "access"},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def create_refresh_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire, "type": "refresh"},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_role_permissions(db: Session, role: str) -> set[str]:
    rows = db.scalars(select(RolePermission).where(RolePermission.role == role)).all()
    if not rows:
        return set(DEFAULT_PERMISSIONS.get(role, frozenset()))
    allowed = {r.permission for r in rows if r.allowed}
    # Include defaults for any permission missing from DB (forward-compat)
    for perm in PERMISSIONS:
        if not any(r.permission == perm for r in rows) and default_allowed(role, perm):
            allowed.add(perm)
    return allowed


def user_has_permission(db: Session, user: User, permission: str) -> bool:
    return permission in get_role_permissions(db, user.role)


def require_permission(permission: str) -> Callable:
    def dependency(user: CurrentUser, db: DbSession) -> User:
        if not user_has_permission(db, user, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return dependency


def require_any_permission(*permissions: str) -> Callable:
    def dependency(user: CurrentUser, db: DbSession) -> User:
        perms = get_role_permissions(db, user.role)
        if not any(p in perms for p in permissions):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return dependency


def ensure_role_permissions_seeded(db: Session) -> None:
    """Insert missing (role, permission) rows with defaults."""
    from core.permissions import ROLES

    existing = {(r.role, r.permission) for r in db.scalars(select(RolePermission)).all()}
    added = False
    for role in ROLES:
        for perm in PERMISSIONS:
            if (role, perm) in existing:
                continue
            db.add(
                RolePermission(
                    role=role,
                    permission=perm,
                    allowed=default_allowed(role, perm),
                )
            )
            added = True
    if added:
        db.commit()


def verify_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    if not x_api_key or x_api_key != settings.import_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
