"""Admin settings helpers (public roles, permission UI groups)."""

from __future__ import annotations

import secrets
import string

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.permissions import DEFAULT_PERMISSION_GROUPS, DEFAULT_PUBLIC_ROLES
from models.admin_settings import AdminSetting

PUBLIC_ROLES_KEY = "public_roles"
PERMISSION_GROUPS_KEY = "permission_groups"
LEVEL_RESTRICTION_KEY = "level_restriction"
LEVEL_PRESET_KEY = "level_preset"

DEFAULT_LEVEL_BOUNDS: dict[str, int] = {"min": 20, "max": 85}
DEFAULT_LEVEL_RESTRICTION = DEFAULT_LEVEL_BOUNDS
DEFAULT_LEVEL_PRESET = DEFAULT_LEVEL_BOUNDS

_CONSONANTS = "bcdfghjklmnpqrstvwxyz"
_VOWELS = "aeiouy"


def get_setting(db: Session, key: str, default: dict | list) -> dict | list:
    row = db.get(AdminSetting, key)
    if row is None:
        return default
    return row.value


def set_setting(db: Session, key: str, value: dict | list) -> None:
    row = db.get(AdminSetting, key)
    if row is None:
        db.add(AdminSetting(key=key, value=value))
    else:
        row.value = value


def get_public_roles(db: Session) -> list[str]:
    raw = get_setting(db, PUBLIC_ROLES_KEY, list(DEFAULT_PUBLIC_ROLES))
    if not isinstance(raw, list):
        return list(DEFAULT_PUBLIC_ROLES)
    return [str(r) for r in raw if r]


def set_public_roles(db: Session, roles: list[str]) -> list[str]:
    cleaned = list(dict.fromkeys(str(r) for r in roles if r))
    set_setting(db, PUBLIC_ROLES_KEY, cleaned)
    return cleaned


def get_permission_groups(db: Session) -> list[dict]:
    raw = get_setting(db, PERMISSION_GROUPS_KEY, DEFAULT_PERMISSION_GROUPS)
    if not isinstance(raw, list):
        return DEFAULT_PERMISSION_GROUPS
    return raw


def set_permission_groups(db: Session, groups: list[dict]) -> list[dict]:
    set_setting(db, PERMISSION_GROUPS_KEY, groups)
    return groups


def _normalize_level_bounds(raw: dict) -> dict[str, int]:
    try:
        min_v = int(raw.get("min", DEFAULT_LEVEL_BOUNDS["min"]))
        max_v = int(raw.get("max", DEFAULT_LEVEL_BOUNDS["max"]))
    except (TypeError, ValueError):
        min_v = DEFAULT_LEVEL_BOUNDS["min"]
        max_v = DEFAULT_LEVEL_BOUNDS["max"]
    min_v = max(1, min(min_v, 99))
    max_v = max(1, min(max_v, 99))
    if min_v > max_v:
        min_v, max_v = max_v, min_v
    return {"min": min_v, "max": max_v}


def get_level_restriction(db: Session) -> dict[str, int]:
    raw = get_setting(db, LEVEL_RESTRICTION_KEY, DEFAULT_LEVEL_RESTRICTION)
    if not isinstance(raw, dict):
        return dict(DEFAULT_LEVEL_RESTRICTION)
    return _normalize_level_bounds(raw)


def set_level_restriction(db: Session, min_level: int, max_level: int) -> dict[str, int]:
    value = _normalize_level_bounds({"min": min_level, "max": max_level})
    set_setting(db, LEVEL_RESTRICTION_KEY, value)
    return value


def get_level_preset(db: Session) -> dict[str, int]:
    raw = get_setting(db, LEVEL_PRESET_KEY, DEFAULT_LEVEL_PRESET)
    if not isinstance(raw, dict):
        return dict(DEFAULT_LEVEL_PRESET)
    return _normalize_level_bounds(raw)


def set_level_preset(db: Session, min_level: int, max_level: int) -> dict[str, int]:
    value = _normalize_level_bounds({"min": min_level, "max": max_level})
    set_setting(db, LEVEL_PRESET_KEY, value)
    return value


def ensure_admin_settings(db: Session) -> None:
    if db.get(AdminSetting, PUBLIC_ROLES_KEY) is None:
        db.add(AdminSetting(key=PUBLIC_ROLES_KEY, value=list(DEFAULT_PUBLIC_ROLES)))
    if db.get(AdminSetting, PERMISSION_GROUPS_KEY) is None:
        db.add(AdminSetting(key=PERMISSION_GROUPS_KEY, value=DEFAULT_PERMISSION_GROUPS))
    if db.get(AdminSetting, LEVEL_RESTRICTION_KEY) is None:
        db.add(AdminSetting(key=LEVEL_RESTRICTION_KEY, value=dict(DEFAULT_LEVEL_RESTRICTION)))
    if db.get(AdminSetting, LEVEL_PRESET_KEY) is None:
        db.add(AdminSetting(key=LEVEL_PRESET_KEY, value=dict(DEFAULT_LEVEL_PRESET)))
    db.commit()


def generate_username(db: Session, length: int = 6) -> str:
    """Generate pronounceable username (CV syllables), unique in DB."""
    from models.user import User

    for _ in range(50):
        parts: list[str] = []
        while sum(len(p) for p in parts) < length:
            if len(parts) % 2 == 0:
                parts.append(secrets.choice(_CONSONANTS))
            else:
                parts.append(secrets.choice(_VOWELS))
        candidate = "".join(parts)[:length]
        exists = db.scalar(select(User.id).where(User.username == candidate))
        if not exists:
            return candidate
    raise RuntimeError("Could not generate unique username")


def generate_password(length: int = 8) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))
