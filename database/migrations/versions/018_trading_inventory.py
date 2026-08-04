"""Shared trading inventory characters and snapshots

Revision ID: 018
Revises: 017
Create Date: 2026-08-04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ALL_ROLES = ("superadmin", "admin", "user", "driver", "other")

NEW_PERMISSIONS = (
    "nav.trading",
    "feature.trading_write",
)


def _default_allowed(role: str, permission: str) -> bool:
    if role == "superadmin":
        return True
    return False


def upgrade() -> None:
    op.create_table(
        "trading_characters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("nick", sa.String(128), nullable=False),
        sa.Column("clean_adena", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_trading_characters_kind", "trading_characters", ["kind"])

    op.create_table(
        "trading_inventory_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("character_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_external_id", sa.Integer(), nullable=False),
        sa.Column("item_name", sa.String(512), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["character_id"], ["trading_characters.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_trading_inventory_lines_character_id",
        "trading_inventory_lines",
        ["character_id"],
    )

    op.create_table(
        "trading_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_trading_snapshots_created_at", "trading_snapshots", ["created_at"])

    conn = op.get_bind()
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role", sa.String),
        sa.column("permission", sa.String),
        sa.column("allowed", sa.Boolean),
    )
    existing_rows = conn.execute(
        sa.text("SELECT role, permission FROM role_permissions")
    ).fetchall()
    existing = {(r[0], r[1]) for r in existing_rows}
    new_rows: list[dict] = []
    for role in ALL_ROLES:
        for perm in NEW_PERMISSIONS:
            if (role, perm) in existing:
                continue
            new_rows.append(
                {
                    "role": role,
                    "permission": perm,
                    "allowed": _default_allowed(role, perm),
                }
            )
    if new_rows:
        op.bulk_insert(role_permissions, new_rows)


def downgrade() -> None:
    op.drop_index("ix_trading_snapshots_created_at", table_name="trading_snapshots")
    op.drop_table("trading_snapshots")
    op.drop_index(
        "ix_trading_inventory_lines_character_id", table_name="trading_inventory_lines"
    )
    op.drop_table("trading_inventory_lines")
    op.drop_index("ix_trading_characters_kind", table_name="trading_characters")
    op.drop_table("trading_characters")

    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM role_permissions WHERE permission IN :perms").bindparams(
            sa.bindparam("perms", expanding=True)
        ),
        {"perms": list(NEW_PERMISSIONS)},
    )
