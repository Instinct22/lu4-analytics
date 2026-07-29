import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class ItemStatistics(Base):
    __tablename__ = "item_statistics"
    __table_args__ = (UniqueConstraint("entity_id", "period", name="uq_item_stats_entity_period"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("wiki_entities.id"), index=True)
    period: Mapped[str] = mapped_column(String(8))
    min_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    max_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    avg_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    seller_count: Mapped[int] = mapped_column(Integer, default=0)
    price_change_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    last_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AnalyticsDataset(Base):
    __tablename__ = "analytics_datasets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
