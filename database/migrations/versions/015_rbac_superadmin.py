"""RBAC superadmin expansion: created_by, logs, admin settings, new permissions

Revision ID: 015
Revises: 014
Create Date: 2026-07-31
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_PERMISSIONS = (
    "feature.craft_bulk",
    "feature.craft_warehouse",
    "feature.raid_timers_view",
    "feature.raid_route",
    "admin.roles_manage",
    "admin.logs_view",
    "admin.users_quick_create",
)

ALL_ROLES = ("superadmin", "admin", "user", "driver", "other")

DEFAULT_PUBLIC_ROLES = ["user", "driver", "other"]

DEFAULT_PERMISSION_GROUPS = [
    {
        "id": "analytics",
        "label": "Аналитика",
        "permissions": ["nav.dashboard", "nav.charts", "nav.statistics"],
    },
    {
        "id": "raid",
        "label": "Рейд-боссы",
        "permissions": [
            "nav.raid_bosses",
            "feature.raid_timers_view",
            "feature.raid_route",
            "feature.raid_timers_write",
        ],
    },
    {
        "id": "craft",
        "label": "Крафт",
        "permissions": [
            "nav.craft",
            "feature.craft_prices",
            "feature.craft_bulk",
            "feature.craft_warehouse",
        ],
    },
    {
        "id": "administration",
        "label": "Администрирование",
        "permissions": ["nav.admin", "admin.users_quick_create", "admin.roles_manage", "admin.logs_view"],
    },
]


def _default_new_perm(role: str, permission: str) -> bool:
    if role == "superadmin":
        return True
    if permission == "admin.users_quick_create":
        return role == "admin"
    if permission in ("admin.roles_manage", "admin.logs_view"):
        return False
    if permission in ("feature.raid_timers_view", "feature.raid_route"):
        return role == "user"
    if permission in ("feature.craft_bulk", "feature.craft_warehouse"):
        return role in ("user", "driver", "other")
    return False


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_users_created_by_id",
        "users",
        "users",
        ["created_by_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_users_created_by_id", "users", ["created_by_id"])

    op.execute("UPDATE users SET role = 'superadmin' WHERE username = 'admin' AND role = 'admin'")

    op.create_table(
        "user_creation_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("creator_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("creator_username", sa.String(64), nullable=False),
        sa.Column("created_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_username", sa.String(64), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=False, server_default=""),
        sa.Column(
            "logged_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_user_creation_logs_creator_id", "user_creation_logs", ["creator_id"])
    op.create_index("ix_user_creation_logs_created_user_id", "user_creation_logs", ["created_user_id"])
    op.create_index("ix_user_creation_logs_creator_username", "user_creation_logs", ["creator_username"])
    op.create_index("ix_user_creation_logs_created_username", "user_creation_logs", ["created_username"])
    op.create_index("ix_user_creation_logs_logged_at", "user_creation_logs", ["logged_at"])

    op.create_table(
        "admin_settings",
        sa.Column("key", sa.String(64), primary_key=True, nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=False),
    )

    admin_settings = sa.table(
        "admin_settings",
        sa.column("key", sa.String),
        sa.column("value", postgresql.JSONB),
    )
    op.bulk_insert(
        admin_settings,
        [
            {"key": "public_roles", "value": DEFAULT_PUBLIC_ROLES},
            {"key": "permission_groups", "value": DEFAULT_PERMISSION_GROUPS},
        ],
    )

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
            allowed = _default_new_perm(role, perm)
            if perm in ("feature.raid_timers_view", "feature.raid_route") and existing.get((role, "nav.raid_bosses")):
                allowed = True
            if perm in ("feature.craft_bulk", "feature.craft_warehouse") and existing.get((role, "nav.craft")):
                allowed = True
            new_rows.append({"role": role, "permission": perm, "allowed": allowed})

    if new_rows:
        op.bulk_insert(role_permissions, new_rows)

    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role, permission, allowed)
            SELECT 'superadmin', p.permission, true
            FROM role_permissions p
            WHERE p.role = 'admin'
              AND NOT EXISTS (
                  SELECT 1 FROM role_permissions r
                  WHERE r.role = 'superadmin' AND r.permission = p.permission
              )
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM role_permissions WHERE role = 'superadmin'"))
    conn.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission IN :perms"
        ).bindparams(sa.bindparam("perms", expanding=True)),
        {"perms": list(NEW_PERMISSIONS)},
    )

    op.execute("UPDATE users SET role = 'admin' WHERE role = 'superadmin'")

    op.drop_table("admin_settings")
    op.drop_index("ix_user_creation_logs_logged_at", table_name="user_creation_logs")
    op.drop_index("ix_user_creation_logs_created_username", table_name="user_creation_logs")
    op.drop_index("ix_user_creation_logs_creator_username", table_name="user_creation_logs")
    op.drop_index("ix_user_creation_logs_created_user_id", table_name="user_creation_logs")
    op.drop_index("ix_user_creation_logs_creator_id", table_name="user_creation_logs")
    op.drop_table("user_creation_logs")

    op.drop_index("ix_users_created_by_id", table_name="users")
    op.drop_constraint("fk_users_created_by_id", "users", type_="foreignkey")
    op.drop_column("users", "created_by_id")
