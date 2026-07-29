from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class CharacterRace(Base):
    __tablename__ = "character_races"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    #: Class tree of the race: branches with nested nodes.
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class CharacterClass(Base):
    __tablename__ = "character_classes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(96), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(96), nullable=False, default="")
    icon: Mapped[str] = mapped_column(Text, nullable=False, default="")
    portrait: Mapped[str] = mapped_column(Text, nullable=False, default="")
    race_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("character_races.id", ondelete="SET NULL"), nullable=True, index=True
    )
    #: levels, skills_by_level, skills_up_to_level.
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)


class CharacterSkill(Base):
    __tablename__ = "character_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    icon: Mapped[str] = mapped_column(Text, nullable=False, default="")
    type: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    #: levels and available_for.
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
