"""drop unused entity_materials table

Revision ID: 003
Revises: 002
Create Date: 2026-07-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("entity_materials")


def downgrade() -> None:
    op.create_table(
        "entity_materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("wiki_entities.id"), nullable=False, index=True),
        sa.Column("material_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("wiki_entities.id"), nullable=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("amount", sa.String(64), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
