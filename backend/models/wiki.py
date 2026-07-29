import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class WikiCategory(Base):
    __tablename__ = "wiki_categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wiki_categories.id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(128))
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    entities: Mapped[list["WikiEntity"]] = relationship(back_populates="category")


class WikiEntity(Base):
    __tablename__ = "wiki_entities"
    __table_args__ = (
        UniqueConstraint("entity_type", "external_id", name="uq_wiki_entities_type_external_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), index=True)
    external_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(512))
    display_name: Mapped[str] = mapped_column(String(512), index=True)
    name_normalized: Mapped[str] = mapped_column(String(512), index=True)
    slug: Mapped[str] = mapped_column(String(256), index=True)
    url: Mapped[str] = mapped_column(String(512))
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    stats: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    materials: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    content_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wiki_categories.id"), nullable=True
    )
    image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    search_vector = mapped_column(TSVECTOR, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    category: Mapped[WikiCategory | None] = relationship(back_populates="entities")
    outgoing_links: Mapped[list["EntityLink"]] = relationship(
        foreign_keys="EntityLink.source_entity_id", back_populates="source"
    )
    incoming_links: Mapped[list["EntityLink"]] = relationship(
        foreign_keys="EntityLink.target_entity_id", back_populates="target"
    )


class EntityLink(Base):
    __tablename__ = "entity_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("wiki_entities.id"), index=True)
    target_entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("wiki_entities.id"), index=True)
    link_type: Mapped[str] = mapped_column(String(32), default="related")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source: Mapped[WikiEntity] = relationship(foreign_keys=[source_entity_id], back_populates="outgoing_links")
    target: Mapped[WikiEntity] = relationship(foreign_keys=[target_entity_id], back_populates="incoming_links")
