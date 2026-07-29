from decimal import Decimal

from sqlalchemy import Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class NpcLoot(Base):
    """Spoil and drop rows parsed from wiki HTML once, at import time."""

    __tablename__ = "npc_loot"
    __table_args__ = (
        Index("ix_npc_loot_npc_kind", "npc_external_id", "kind"),
        Index("ix_npc_loot_item", "item_external_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    npc_external_id: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(8), nullable=False)
    item_external_id: Mapped[int] = mapped_column(Integer, nullable=False)
    item_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    item_grade: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    item_url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    amount: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    chance_text: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    chance_val: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
