import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Seller(Base):
    __tablename__ = "sellers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(256), unique=True)
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    records: Mapped[list["MarketRecord"]] = relationship(back_populates="seller")


class ImportLog(Base):
    __tablename__ = "import_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(128))
    records_count: Mapped[int] = mapped_column(Integer, default=0)
    matched_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="success")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    records: Mapped[list["MarketRecord"]] = relationship(back_populates="import_log")


class MarketRecord(Base):
    __tablename__ = "market_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wiki_entities.id"), nullable=True, index=True
    )
    product_name_raw: Mapped[str] = mapped_column(String(512))
    product_name_normalized: Mapped[str] = mapped_column(String(512), index=True)
    soul_crystal: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rarity: Mapped[str | None] = mapped_column(String(48), nullable=True)
    armor_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sealed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    enchant_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seller_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sellers.id"), index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(32), default="RUB")
    side: Mapped[str | None] = mapped_column(String(4), nullable=True)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    in_stock: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    import_log_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("import_logs.id"), nullable=True
    )
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    seller: Mapped[Seller] = relationship(back_populates="records")
    import_log: Mapped[ImportLog | None] = relationship(back_populates="records")
