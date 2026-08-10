"""Add nav.craft_profitability permission

Revision ID: 026
Revises: 025
Create Date: 2026-08-10
"""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "026"
down_revision: Union[str, None] = "025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_PERMISSION = "nav.craft_profitability"
SOURCE_PERMISSION = "feature.craft_prices"
ALL_ROLES = ("superadmin", "admin", "user", "driver", "other")

_DRIVER_PERMS = frozenset({"nav.craft", "nav.items", "nav.character", "nav.settings"})
_ADMIN_ONLY = frozenset({"nav.admin", "admin.roles_manage", "admin.logs_view"})
_LEVEL_UNRESTRICTED = frozenset({"feature.level_unrestricted"})
_TRADING_PERMS = frozenset({"nav.trading", "feature.trading_write"})

ALL_PERMISSIONS = (
    "nav.dashboard",
    "nav.charts",
    "nav.statistics",
    "nav.craft_profitability",
    "nav.craft",
    "nav.items",
    "nav.character",
    "nav.resources",
    "nav.search",
    "nav.quests",
    "nav.raid_bosses",
    "nav.trading",
    "nav.settings",
    "nav.admin",
    "feature.craft_prices",
    "feature.craft_bulk",
    "feature.craft_warehouse",
    "feature.raid_timers_view",
    "feature.raid_route",
    "feature.raid_timers_write",
    "feature.raid_visibility",
    "feature.trading_write",
    "feature.level_unrestricted",
    "admin.roles_manage",
    "admin.logs_view",
    "admin.users_quick_create",
    "admin.level_preset",
    "admin.level_restriction",
)

_USER_NAV = frozenset(
    p
    for p in ALL_PERMISSIONS
    if p not in _ADMIN_ONLY
    and not p.startswith("admin.")
    and p not in _LEVEL_UNRESTRICTED
    and p not in _TRADING_PERMS
)

DEFAULT_PERMISSIONS: dict[str, frozenset[str]] = {
    "superadmin": frozenset(ALL_PERMISSIONS),
    "admin": frozenset({"nav.admin", "admin.users_quick_create"}),
    "user": _USER_NAV,
    "driver": _DRIVER_PERMS | {"feature.craft_bulk", "feature.craft_warehouse"},
    "other": _DRIVER_PERMS | {"feature.craft_bulk", "feature.craft_warehouse"},
}


def _default_allowed(role: str, permission: str) -> bool:
    return permission in DEFAULT_PERMISSIONS.get(role, frozenset())


def upgrade() -> None:
    conn = op.get_bind()
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role", sa.String),
        sa.column("permission", sa.String),
        sa.column("allowed", sa.Boolean),
    )

    existing_rows = conn.execute(
        sa.text("SELECT role, permission, allowed FROM role_permissions")
    ).fetchall()
    existing = {(r[0], r[1]): r[2] for r in existing_rows}

    roles = sorted({r[0] for r in existing_rows} | set(ALL_ROLES))
    new_rows: list[dict] = []
    for role in roles:
        if (role, NEW_PERMISSION) in existing:
            continue
        if (role, SOURCE_PERMISSION) in existing:
            allowed = existing[(role, SOURCE_PERMISSION)]
        else:
            allowed = _default_allowed(role, NEW_PERMISSION)
        new_rows.append({"role": role, "permission": NEW_PERMISSION, "allowed": allowed})

    if new_rows:
        op.bulk_insert(role_permissions, new_rows)

    row = conn.execute(
        sa.text("SELECT value FROM admin_settings WHERE key = 'permission_groups'")
    ).fetchone()
    if row is None:
        return

    groups = row[0]
    if not isinstance(groups, list):
        return

    changed = False
    for group in groups:
        if not isinstance(group, dict) or group.get("id") != "analytics":
            continue
        perms = group.get("permissions")
        if not isinstance(perms, list):
            continue
        if NEW_PERMISSION not in perms:
            perms.append(NEW_PERMISSION)
            changed = True
        break

    if changed:
        conn.execute(
            sa.text("UPDATE admin_settings SET value = CAST(:value AS jsonb) WHERE key = 'permission_groups'"),
            {"value": json.dumps(groups)},
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM role_permissions WHERE permission = :perm"),
        {"perm": NEW_PERMISSION},
    )

    row = conn.execute(
        sa.text("SELECT value FROM admin_settings WHERE key = 'permission_groups'")
    ).fetchone()
    if row is None:
        return

    groups = row[0]
    if not isinstance(groups, list):
        return

    changed = False
    for group in groups:
        if not isinstance(group, dict):
            continue
        perms = group.get("permissions")
        if not isinstance(perms, list) or NEW_PERMISSION not in perms:
            continue
        group["permissions"] = [p for p in perms if p != NEW_PERMISSION]
        changed = True

    if changed:
        conn.execute(
            sa.text("UPDATE admin_settings SET value = CAST(:value AS jsonb) WHERE key = 'permission_groups'"),
            {"value": json.dumps(groups)},
        )
