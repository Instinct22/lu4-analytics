"""API token generation, verification, and admin CRUD."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from models.api_token import ApiToken
from models.user import User
from schemas.api_token import (
    API_TOKEN_SCOPES,
    ApiTokenItem,
    ApiTokenScope,
    CreateApiTokenRequest,
    CreateApiTokenResponse,
    SCOPE_LABELS,
    ApiTokenScopeItem,
)

TOKEN_PREFIX_LEN = 12


def hash_api_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _token_prefix(token: str) -> str:
    return token[:TOKEN_PREFIX_LEN]


def generate_api_token_secret() -> str:
    return f"lu4_{secrets.token_urlsafe(24)}"


def legacy_key_configured() -> bool:
    return bool(settings.import_api_key) and settings.import_api_key != "change-import-key"


def to_api_token_item(row: ApiToken) -> ApiTokenItem:
    now = datetime.now(timezone.utc)
    active = row.revoked_at is None and (row.expires_at is None or row.expires_at > now)
    return ApiTokenItem(
        id=row.id,
        name=row.name,
        token_prefix=row.token_prefix,
        scopes=list(row.scopes or []),
        created_by_id=row.created_by_id,
        created_at=row.created_at,
        last_used_at=row.last_used_at,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        is_active=active,
    )


def list_api_tokens(db: Session) -> list[ApiTokenItem]:
    rows = db.scalars(select(ApiToken).order_by(ApiToken.created_at.desc())).all()
    return [to_api_token_item(r) for r in rows]


def list_scope_catalog() -> list[ApiTokenScopeItem]:
    return [ApiTokenScopeItem(scope=s, label=SCOPE_LABELS[s]) for s in API_TOKEN_SCOPES]


def create_api_token(db: Session, body: CreateApiTokenRequest, creator: User) -> CreateApiTokenResponse:
    invalid = [s for s in body.scopes if s not in API_TOKEN_SCOPES]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown scopes: {', '.join(invalid)}",
        )

    plain = generate_api_token_secret()
    row = ApiToken(
        name=body.name.strip(),
        token_prefix=_token_prefix(plain),
        token_hash=hash_api_token(plain),
        scopes=sorted(set(body.scopes)),
        created_by_id=creator.id,
        expires_at=body.expires_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return CreateApiTokenResponse(token=plain, item=to_api_token_item(row))


def revoke_api_token(db: Session, token_id: uuid.UUID) -> ApiTokenItem:
    row = db.get(ApiToken, token_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")
    if row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(row)
    return to_api_token_item(row)


class ApiTokenAuthResult:
    __slots__ = ("ok", "missing_scope")

    def __init__(self, ok: bool, *, missing_scope: bool = False) -> None:
        self.ok = ok
        self.missing_scope = missing_scope


def verify_api_token(db: Session, api_key: str, scope: ApiTokenScope) -> ApiTokenAuthResult:
    if api_key == settings.import_api_key:
        return ApiTokenAuthResult(True)

    prefix = _token_prefix(api_key)
    row = db.scalar(select(ApiToken).where(ApiToken.token_prefix == prefix))
    if row is None:
        return ApiTokenAuthResult(False)

    now = datetime.now(timezone.utc)
    if row.revoked_at is not None:
        return ApiTokenAuthResult(False)
    if row.expires_at is not None and row.expires_at <= now:
        return ApiTokenAuthResult(False)

    expected = row.token_hash
    actual = hash_api_token(api_key)
    if not hmac.compare_digest(expected, actual):
        return ApiTokenAuthResult(False)

    scopes = row.scopes or []
    if scope not in scopes:
        return ApiTokenAuthResult(False, missing_scope=True)

    row.last_used_at = now
    db.commit()
    return ApiTokenAuthResult(True)
