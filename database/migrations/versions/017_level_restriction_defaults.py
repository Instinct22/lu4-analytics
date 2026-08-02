"""Level restriction defaults: permissions and admin settings

Revision ID: 017
Revises: 016
Create Date: 2026-08-02
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ALL_ROLES = ("superadmin", "admin", "user", "driver", "other")

NEW_PERMISSIONS = (
    "nav.settings",
    "feature.level_unrestricted",
    "admin.level_preset",
    "admin.level_restriction",
)

DEFAULT_LEVEL_BOUNDS = {"min": 20, "max": 85}


def _default_allowed(role: str, permission: str) -> bool:
    if role == "superadmin":
        return True
    if permission == "admin.users_quick_create":
        return role == "admin"
    if permission in ("admin.roles_manage", "admin.logs_view", "admin.level_restriction"):
        return False
    if permission == "admin.level_preset":
        return role == "admin"
    if permission == "feature.level_unrestricted":
        return False
    if permission == "nav.settings":
        return role in ("admin", "user", "driver", "other")
    return False


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

    new_rows: list[dict] = []
    for role in ALL_ROLES:
        for perm in NEW_PERMISSIONS:
            if (role, perm) in existing:
                continue
            new_rows.append(
                {"role": role, "permission": perm, "allowed": _default_allowed(role, perm)}
            )

    if new_rows:
        op.bulk_insert(role_permissions, new_rows)

    conn.execute(
        sa.text(
            """
            UPDATE role_permissions
            SET allowed = false
            WHERE permission = 'feature.level_unrestricted'
              AND role IN ('admin', 'user', 'driver', 'other')
            """
        )
    )

    admin_settings = sa.table(
        "admin_settings",
        sa.column("key", sa.String),
        sa.column("value", postgresql.JSONB),
    )
    for key in ("level_preset", "level_restriction"):
        exists = conn.execute(
            sa.text("SELECT 1 FROM admin_settings WHERE key = :key"),
            {"key": key},
        ).first()
        if not exists:
            op.bulk_insert(admin_settings, [{"key": key, "value": DEFAULT_LEVEL_BOUNDS}])


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission IN :perms"
        ).bindparams(sa.bindparam("perms", expanding=True)),
        {"perms": list(NEW_PERMISSIONS)},
    )
    conn.execute(
        sa.text("DELETE FROM admin_settings WHERE key IN ('level_preset', 'level_restriction')")
    )
