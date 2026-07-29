"""add user roles and role_permissions

Revision ID: 004
Revises: 003
Create Date: 2026-07-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = (
    "nav.dashboard",
    "nav.charts",
    "nav.statistics",
    "nav.craft",
    "nav.character",
    "nav.resources",
    "nav.search",
    "nav.admin",
    "feature.craft_prices",
)

DRIVER_PERMS = {"nav.craft", "nav.character"}


def _allowed(role: str, permission: str) -> bool:
    if role == "admin":
        return True
    if role == "user":
        return permission != "nav.admin"
    return permission in DRIVER_PERMS


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(32), nullable=False, server_default="user"),
    )
    op.create_index("ix_users_role", "users", ["role"])
    op.execute("UPDATE users SET role = 'admin' WHERE username = 'admin'")

    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("permission", sa.String(64), nullable=False),
        sa.Column("allowed", sa.Boolean(), nullable=False, server_default="true"),
        sa.UniqueConstraint("role", "permission", name="uq_role_permission"),
    )
    op.create_index("ix_role_permissions_role", "role_permissions", ["role"])

    rows = []
    for role in ("admin", "user", "driver", "other"):
        for perm in PERMISSIONS:
            rows.append(
                {
                    "role": role,
                    "permission": perm,
                    "allowed": _allowed(role, perm),
                }
            )
    op.bulk_insert(
        sa.table(
            "role_permissions",
            sa.column("role", sa.String),
            sa.column("permission", sa.String),
            sa.column("allowed", sa.Boolean),
        ),
        rows,
    )


def downgrade() -> None:
    op.drop_index("ix_role_permissions_role", table_name="role_permissions")
    op.drop_table("role_permissions")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_column("users", "role")
