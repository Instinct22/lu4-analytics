"""Shared trading inventory: bank / merchant characters and snapshots."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class TradingCharacter(Base):
    __tablename__ = "trading_characters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # bank | merchant
    nick: Mapped[str] = mapped_column(String(128), nullable=False)
    clean_adena: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # sell | buy — merchants only; bank always sell
    trade_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="sell")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    items: Mapped[list[TradingInventoryLine]] = relationship(
        "TradingInventoryLine",
        back_populates="character",
        cascade="all, delete-orphan",
        order_by="TradingInventoryLine.sort_order",
    )


class TradingInventoryLine(Base):
    __tablename__ = "trading_inventory_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("trading_characters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_external_id: Mapped[int] = mapped_column(Integer, nullable=False)
    item_name: Mapped[str] = mapped_column(String(512), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=0)
    # sell = inventory for sale; buy = shopping list
    list_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="sell", index=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    character: Mapped[TradingCharacter] = relationship("TradingCharacter", back_populates="items")


class TradingSnapshot(Base):
    __tablename__ = "trading_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
