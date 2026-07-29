import uuid

from fastapi import APIRouter, HTTPException, Request, status

from core.client_ip import client_ip
from sqlalchemy import select

from api.deps import (
    CurrentUser,
    DbSession,
    create_access_token,
    create_refresh_token,
    get_role_permissions,
    verify_password,
)
from jose import JWTError, jwt
from config import settings
from models.login_log import LoginLog
from models.user import User
from schemas.auth import LoginRequest, MeResponse, RefreshRequest, TokenResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: DbSession):
    user = db.scalar(select(User).where(User.username == body.username))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")

    db.add(
        LoginLog(
            id=uuid.uuid4(),
            user_id=user.id,
            username=user.username,
            ip_address=client_ip(request),
        )
    )
    db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id, user.username),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: DbSession):
    try:
        payload = jwt.decode(body.refresh_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return TokenResponse(
        access_token=create_access_token(user.id, user.username),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/me", response_model=MeResponse)
def me(user: CurrentUser, db: DbSession):
    perms = sorted(get_role_permissions(db, user.role))
    return MeResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        permissions=perms,
    )
