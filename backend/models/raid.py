import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class RaidBoss(Base):
    __tablename__ = "raid_bosses"

    external_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    level: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    map_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    map_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    respawn_raw: Mapped[str | None] = mapped_column(String(120), nullable=True)
    respawn_min_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    respawn_max_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    wiki_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RaidBossTimer(Base):
    """One row per boss: kill times are shared by the whole server."""

    __tablename__ = "raid_boss_timers"

    boss_external_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("raid_bosses.external_id", ondelete="CASCADE"),
        primary_key=True,
        autoincrement=False,
    )
    killed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    set_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
