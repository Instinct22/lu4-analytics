import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from api.deps import CurrentUser, DbSession
from models.preferences import UserPreference

router = APIRouter()

#: Client state that used to live in localStorage.
SCOPES = frozenset({"craft_owned", "craft_prices", "craft_variants", "craft_cart"})

#: Guard against a runaway client filling the table with megabytes of JSON.
MAX_PAYLOAD_BYTES = 256 * 1024


class PreferenceIn(BaseModel):
    payload: dict


def _check_scope(scope: str) -> None:
    if scope not in SCOPES:
        raise HTTPException(status_code=404, detail=f"Unknown preference scope: {scope}")


@router.get("/preferences")
def list_preferences(db: DbSession, user: CurrentUser):
    rows = db.scalars(
        select(UserPreference).where(UserPreference.user_id == user.id)
    ).all()
    return {"scopes": {row.scope: row.payload for row in rows}}


@router.get("/preferences/{scope}")
def get_preference(scope: str, db: DbSession, user: CurrentUser):
    _check_scope(scope)
    row = db.get(UserPreference, (user.id, scope))
    return {
        "scope": scope,
        "payload": row.payload if row else {},
        "updated_at": row.updated_at.isoformat() if row and row.updated_at else None,
    }


@router.put("/preferences/{scope}")
def put_preference(scope: str, body: PreferenceIn, db: DbSession, user: CurrentUser):
    _check_scope(scope)
    if len(json.dumps(body.payload).encode()) > MAX_PAYLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Preference payload too large")

    row = db.get(UserPreference, (user.id, scope))
    if row is None:
        row = UserPreference(user_id=user.id, scope=scope, payload=body.payload)
        db.add(row)
    else:
        row.payload = body.payload
    db.commit()
    db.refresh(row)
    return {
        "scope": scope,
        "payload": row.payload,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }
