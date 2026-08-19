"""API tokens table and admin.api_tokens_manage permission

Revision ID: 027
Revises: 026
Create Date: 2026-08-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "027"
down_revision: Union[str, None] = "026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_PERMISSION = "admin.api_tokens_manage"
ALL_ROLES = ("superadmin", "admin", "user", "driver", "other")


def upgrade() -> None:
    op.create_table(
        "api_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("token_prefix", sa.String(16), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("scopes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_api_tokens_token_prefix", "api_tokens", ["token_prefix"])
    op.create_index("ix_api_tokens_created_by_id", "api_tokens", ["created_by_id"])

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
        if (role, NEW_PERMISSION) in existing:
            continue
        new_rows.append(
            {
                "role": role,
                "permission": NEW_PERMISSION,
                "allowed": role == "superadmin",
            }
        )
    if new_rows:
        op.bulk_insert(role_permissions, new_rows)


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM role_permissions WHERE permission = :perm"),
        {"perm": NEW_PERMISSION},
    )
    op.drop_index("ix_api_tokens_created_by_id", table_name="api_tokens")
    op.drop_index("ix_api_tokens_token_prefix", table_name="api_tokens")
    op.drop_table("api_tokens")
