"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-07-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=True, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "wiki_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("wiki_categories.id"), nullable=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
    )

    op.create_table(
        "wiki_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_key", sa.String(128), nullable=False, unique=True),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("external_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("display_name", sa.String(512), nullable=False),
        sa.Column("name_normalized", sa.String(512), nullable=False),
        sa.Column("slug", sa.String(256), nullable=False),
        sa.Column("url", sa.String(512), nullable=False),
        sa.Column("source_url", sa.String(512), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("stats", postgresql.JSONB(), nullable=True),
        sa.Column("materials", postgresql.JSONB(), nullable=True),
        sa.Column("content_md", sa.Text(), nullable=True),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("wiki_categories.id"), nullable=True),
        sa.Column("image_path", sa.String(512), nullable=True),
        sa.Column("search_vector", postgresql.TSVECTOR(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_wiki_entities_entity_type", "wiki_entities", ["entity_type"])
    op.create_index("ix_wiki_entities_external_id", "wiki_entities", ["external_id"])
    op.create_index("ix_wiki_entities_name_normalized", "wiki_entities", ["name_normalized"])
    op.create_index("ix_wiki_entities_display_name", "wiki_entities", ["display_name"])
    op.create_index("ix_wiki_entities_search_vector", "wiki_entities", ["search_vector"], postgresql_using="gin")

    op.create_table(
        "entity_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("wiki_entities.id"), nullable=False),
        sa.Column("target_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("wiki_entities.id"), nullable=False),
        sa.Column("link_type", sa.String(32), server_default="related"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_entity_links_source", "entity_links", ["source_entity_id"])
    op.create_index("ix_entity_links_target", "entity_links", ["target_entity_id"])

    op.create_table(
        "entity_materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("wiki_entities.id"), nullable=False),
        sa.Column("material_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("wiki_entities.id"), nullable=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("amount", sa.String(64), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
    )

    op.create_table(
        "sellers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False, unique=True),
        sa.Column("slug", sa.String(256), nullable=False, unique=True),
        sa.Column("website", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "import_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(128), nullable=False),
        sa.Column("records_count", sa.Integer(), server_default="0"),
        sa.Column("matched_count", sa.Integer(), server_default="0"),
        sa.Column("status", sa.String(32), server_default="success"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "market_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("wiki_entities.id"), nullable=True),
        sa.Column("product_name_raw", sa.String(512), nullable=False),
        sa.Column("product_name_normalized", sa.String(512), nullable=False),
        sa.Column("seller_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sellers.id"), nullable=False),
        sa.Column("price", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), server_default="RUB"),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("in_stock", sa.Boolean(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("import_log_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("import_logs.id"), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_market_records_entity_recorded", "market_records", ["entity_id", "recorded_at"])
    op.create_index("ix_market_records_name_normalized", "market_records", ["product_name_normalized"])

    op.create_table(
        "item_statistics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("wiki_entities.id"), nullable=False),
        sa.Column("period", sa.String(8), nullable=False),
        sa.Column("min_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("max_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("avg_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("seller_count", sa.Integer(), server_default="0"),
        sa.Column("price_change_pct", sa.Numeric(8, 2), nullable=True),
        sa.Column("last_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("entity_id", "period", name="uq_item_stats_entity_period"),
    )

    op.create_table(
        "analytics_datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("dataset_key", sa.String(64), nullable=False, unique=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("analytics_datasets")
    op.drop_table("item_statistics")
    op.drop_table("market_records")
    op.drop_table("import_logs")
    op.drop_table("sellers")
    op.drop_table("entity_materials")
    op.drop_table("entity_links")
    op.drop_table("wiki_entities")
    op.drop_table("wiki_categories")
    op.drop_table("users")
