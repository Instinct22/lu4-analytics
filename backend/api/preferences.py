import json
import copy

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from api.deps import CurrentUser, DbSession
from models.preferences import UserPreference

router = APIRouter()

#: Client state that used to live in localStorage.
SCOPES = frozenset({"craft_owned", "craft_prices", "craft_variants", "craft_cart"})

#: Numeric map scopes: item id -> quantity or price.
MAP_SCOPES = frozenset({"craft_owned", "craft_prices", "craft_variants"})

#: Guard against a runaway client filling the table with megabytes of JSON.
MAX_PAYLOAD_BYTES = 256 * 1024


class PreferenceIn(BaseModel):
    payload: dict


class PreferencePatchIn(BaseModel):
    patch: dict


def _check_scope(scope: str) -> None:
    if scope not in SCOPES:
        raise HTTPException(status_code=404, detail=f"Unknown preference scope: {scope}")


def _check_payload_size(payload: dict) -> None:
    if len(json.dumps(payload).encode()) > MAX_PAYLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Preference payload too large")


def _merge_map_payload(existing: dict, patch: dict) -> dict:
    merged = {**existing, **patch}
    return {k: v for k, v in merged.items() if isinstance(v, (int, float)) and v > 0}


def _merge_cart_payload(existing: dict, patch: dict) -> dict:
    merged = copy.deepcopy(existing)
    for key, line in patch.items():
        if not isinstance(line, dict):
            continue
        qty = line.get("qty")
        if not isinstance(qty, (int, float)) or qty <= 0:
            merged.pop(key, None)
            continue
        entry: dict = {"qty": int(qty)}
        variant = line.get("variant")
        if isinstance(variant, (int, float)):
            entry["variant"] = int(variant)
        merged[key] = entry
    return merged


def _merge_payload(scope: str, existing: dict, patch: dict) -> dict:
    if scope in MAP_SCOPES:
        return _merge_map_payload(existing, patch)
    if scope == "craft_cart":
        return _merge_cart_payload(existing, patch)
    return {**existing, **patch}


def _preference_response(scope: str, row: UserPreference) -> dict:
    return {
        "scope": scope,
        "payload": row.payload,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("/preferences")
def list_preferences(db: DbSession, user: CurrentUser):
    rows = db.scalars(
        select(UserPreference).where(UserPreference.user_id == user.id)
    ).all()
    return {
        "scopes": {row.scope: row.payload for row in rows},
        "updated_at": {
            row.scope: row.updated_at.isoformat()
            for row in rows
            if row.updated_at is not None
        },
    }


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
    _check_payload_size(body.payload)

    row = db.get(UserPreference, (user.id, scope))
    if row is None:
        row = UserPreference(user_id=user.id, scope=scope, payload=body.payload)
        db.add(row)
    else:
        row.payload = body.payload
    db.commit()
    db.refresh(row)
    return _preference_response(scope, row)


@router.patch("/preferences/{scope}")
def patch_preference(scope: str, body: PreferencePatchIn, db: DbSession, user: CurrentUser):
    _check_scope(scope)

    row = db.get(UserPreference, (user.id, scope))
    existing = row.payload if row else {}
    merged = _merge_payload(scope, existing, body.patch)
    _check_payload_size(merged)

    if row is None:
        row = UserPreference(user_id=user.id, scope=scope, payload=merged)
        db.add(row)
    else:
        row.payload = merged
    db.commit()
    db.refresh(row)
    return _preference_response(scope, row)
