"""normalize the craft catalog and material sources

Revision ID: 009
Revises: 008
Create Date: 2026-07-28
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "craft_items",
        sa.Column("external_id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("grade", sa.String(16), nullable=False, server_default=""),
        sa.Column("type", sa.String(96), nullable=False, server_default=""),
        sa.Column("category", sa.String(96), nullable=False, server_default=""),
        sa.Column("set_name", sa.String(255), nullable=True),
        sa.Column("npc_sell", sa.Integer(), nullable=True),
        sa.Column("url", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_recipe_scroll", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("stats", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index("ix_craft_items_name", "craft_items", ["name"])
    op.create_index("ix_craft_items_category", "craft_items", ["category"])
    op.create_index("ix_craft_items_set_name", "craft_items", ["set_name"])

    op.create_table(
        "craft_recipes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_external_id", sa.Integer(), nullable=False),
        sa.Column("recipe_external_id", sa.Integer(), nullable=True),
        sa.Column("variant_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("yield_amount", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("rate", sa.Numeric(8, 3), nullable=True),
        sa.Column("crafter_level", sa.Integer(), nullable=True),
        sa.Column("skill_level", sa.String(32), nullable=True),
        sa.Column("mp", sa.String(32), nullable=True),
        sa.Column("success", sa.String(32), nullable=True),
        sa.Column("recipe_url", sa.Text(), nullable=True),
        sa.Column("tree", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    )
    op.create_index(
        "ix_craft_recipes_product", "craft_recipes", ["product_external_id", "variant_index"]
    )
    op.create_index("ix_craft_recipes_recipe_external_id", "craft_recipes", ["recipe_external_id"])

    op.create_table(
        "craft_recipe_materials",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("material_external_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_direct", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["recipe_id"], ["craft_recipes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_craft_recipe_materials_recipe_id", "craft_recipe_materials", ["recipe_id"])
    op.create_index(
        "ix_craft_recipe_materials_material", "craft_recipe_materials", ["material_external_id"]
    )

    op.create_table(
        "craft_material_sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("material_external_id", sa.Integer(), nullable=False),
        sa.Column("source_kind", sa.String(8), nullable=False),
        sa.Column("npc_external_id", sa.Integer(), nullable=True),
        sa.Column("npc_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("npc_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("npc_level", sa.Integer(), nullable=True),
        sa.Column("npc_level_raw", sa.String(32), nullable=False, server_default=""),
        sa.Column("amount", sa.String(64), nullable=False, server_default=""),
        sa.Column("chance_text", sa.String(32), nullable=False, server_default=""),
        sa.Column("chance_val", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("locations", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_craft_material_sources_material",
        "craft_material_sources",
        ["material_external_id", "source_kind"],
    )
    op.create_index(
        "ix_craft_material_sources_npc", "craft_material_sources", ["npc_external_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_craft_material_sources_npc", table_name="craft_material_sources")
    op.drop_index("ix_craft_material_sources_material", table_name="craft_material_sources")
    op.drop_table("craft_material_sources")
    op.drop_index("ix_craft_recipe_materials_material", table_name="craft_recipe_materials")
    op.drop_index("ix_craft_recipe_materials_recipe_id", table_name="craft_recipe_materials")
    op.drop_table("craft_recipe_materials")
    op.drop_index("ix_craft_recipes_recipe_external_id", table_name="craft_recipes")
    op.drop_index("ix_craft_recipes_product", table_name="craft_recipes")
    op.drop_table("craft_recipes")
    op.drop_index("ix_craft_items_set_name", table_name="craft_items")
    op.drop_index("ix_craft_items_category", table_name="craft_items")
    op.drop_index("ix_craft_items_name", table_name="craft_items")
    op.drop_table("craft_items")
