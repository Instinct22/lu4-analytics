"""Custom role CRUD and permission copying."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.permissions import PERMISSIONS, PRESET_ROLES, ROLES, default_allowed, is_system_role
from models.custom_role import CustomRole
from models.permissions import RolePermission
from services.admin_settings import get_public_roles, set_public_roles


def list_custom_roles(db: Session) -> list[CustomRole]:
    return db.scalars(select(CustomRole).order_by(CustomRole.label)).all()


def get_custom_role(db: Session, key: str) -> CustomRole | None:
    return db.get(CustomRole, key)


def is_custom_role(db: Session, key: str) -> bool:
    return get_custom_role(db, key) is not None


def role_label(db: Session, role: str) -> str:
    from core.permissions import ROLE_LABELS

    if role in ROLE_LABELS:
        return ROLE_LABELS[role]
    custom = get_custom_role(db, role)
    return custom.label if custom else role


def editable_roles(db: Session) -> list[str]:
    custom_keys = [r.key for r in list_custom_roles(db)]
    return [r for r in ROLES if r != "superadmin"] + custom_keys


def _slugify_label(label: str) -> str:
    cyrillic = {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "sch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
    parts: list[str] = []
    for ch in label.strip().lower():
        if ch in cyrillic:
            parts.append(cyrillic[ch])
        elif ch.isascii() and (ch.isalnum() or ch in "_-"):
            parts.append(ch)
        elif ch.isspace() or ch in "-_":
            parts.append("_")
    key = re.sub(r"_+", "_", "".join(parts)).strip("_")[:32]
    return key


def validate_role_key(db: Session, key: str) -> str:
    key = key.strip().lower()
    if len(key) < 2 or len(key) > 32:
        raise ValueError("Role key must be 2–32 characters")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", key):
        raise ValueError("Role key must start with a letter and contain only a-z, 0-9, _")
    if is_system_role(key):
        raise ValueError("This role key is reserved")
    if is_custom_role(db, key):
        raise ValueError("Role already exists")
    return key


def validate_preset_role(preset: str) -> str:
    if preset not in PRESET_ROLES:
        raise ValueError(f"Invalid preset role. Allowed: {', '.join(PRESET_ROLES)}")
    return preset


def _copy_permissions(db: Session, *, source_role: str, target_role: str) -> None:
    rows = db.scalars(select(RolePermission).where(RolePermission.role == source_role)).all()
    if rows:
        for row in rows:
            db.add(
                RolePermission(
                    role=target_role,
                    permission=row.permission,
                    allowed=row.allowed,
                )
            )
        return
    for perm in PERMISSIONS:
        db.add(
            RolePermission(
                role=target_role,
                permission=perm,
                allowed=default_allowed(source_role, perm),
            )
        )


def create_custom_role(
    db: Session,
    *,
    label: str,
    preset_role: str,
    key: str | None = None,
) -> CustomRole:
    label = label.strip()
    if not label:
        raise ValueError("Role name required")
    preset_role = validate_preset_role(preset_role)
    role_key = key.strip().lower() if key else _slugify_label(label)
    if len(role_key) < 2:
        raise ValueError("Could not derive a valid role key from name")
    role_key = validate_role_key(db, role_key)

    role = CustomRole(key=role_key, label=label)
    db.add(role)
    _copy_permissions(db, source_role=preset_role, target_role=role_key)

    public = get_public_roles(db)
    if role_key not in public:
        set_public_roles(db, public + [role_key])

    return role


def delete_custom_role(db: Session, key: str) -> None:
    role = get_custom_role(db, key)
    if role is None:
        raise ValueError("Role not found")

    from models.user import User

    in_use = db.scalar(select(User.id).where(User.role == key).limit(1))
    if in_use:
        raise ValueError("Role is assigned to users")

    for row in db.scalars(select(RolePermission).where(RolePermission.role == key)).all():
        db.delete(row)
    db.delete(role)

    public = [r for r in get_public_roles(db) if r != key]
    if public:
        set_public_roles(db, public)
