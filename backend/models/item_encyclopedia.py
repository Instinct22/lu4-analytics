from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class ItemEncyclopedia(Base):
    __tablename__ = "item_encyclopedia"

    external_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    section: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    grade: Mapped[str] = mapped_column(String(16), nullable=False, default="", index=True)
    type: Mapped[str] = mapped_column(String(96), nullable=False, default="")
    other_subcategory: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    icon: Mapped[str | None] = mapped_column(String(128), nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False, default="")
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
