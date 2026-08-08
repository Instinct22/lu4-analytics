from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class CraftItem(Base):
    __tablename__ = "craft_items"

    external_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    grade: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    type: Mapped[str] = mapped_column(String(96), nullable=False, default="")
    category: Mapped[str] = mapped_column(String(96), nullable=False, default="", index=True)
    set_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    npc_sell: Mapped[int | None] = mapped_column(Integer, nullable=True)
    npc_buy: Mapped[int | None] = mapped_column(Integer, nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_recipe_scroll: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    stats: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class CraftRecipe(Base):
    """One craft variant of a product; `tree` keeps the nested material tree."""

    __tablename__ = "craft_recipes"
    __table_args__ = (
        Index("ix_craft_recipes_product", "product_external_id", "variant_index"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    product_external_id: Mapped[int] = mapped_column(Integer, nullable=False)
    recipe_external_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    #: Position in the product's variant list; the UI stores a chosen index.
    variant_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    yield_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 3), nullable=True)
    crafter_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    skill_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    mp: Mapped[str | None] = mapped_column(String(32), nullable=True)
    success: Mapped[str | None] = mapped_column(String(32), nullable=True)
    recipe_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    tree: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)


class CraftRecipeMaterial(Base):
    """Flattened recipe tree: answers "where is this material used"."""

    __tablename__ = "craft_recipe_materials"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("craft_recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    material_external_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    #: True for top-level materials, False for nested ones.
    is_direct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CraftMaterialSource(Base):
    """Where a craft material comes from: NPC spoil or drop."""

    __tablename__ = "craft_material_sources"
    __table_args__ = (
        Index("ix_craft_material_sources_material", "material_external_id", "source_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    material_external_id: Mapped[int] = mapped_column(Integer, nullable=False)
    source_kind: Mapped[str] = mapped_column(String(8), nullable=False)
    npc_external_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    npc_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    npc_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    npc_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    npc_level_raw: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    amount: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    chance_text: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    chance_val: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    locations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
