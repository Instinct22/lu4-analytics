"""Quest catalog schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class QuestNpc(BaseModel):
    id: int | None = None
    name: str = ""
    icon: str | None = None


class QuestReward(BaseModel):
    item_id: int | None = None
    name: str = ""
    grade: str | None = None
    icon: str | None = None
    qty: int | None = None


class QuestStep(BaseModel):
    title: str = ""
    text: str = ""
    images: list[str] = Field(default_factory=list)


class QuestBrief(BaseModel):
    id: int
    slug: str
    name: str
    level_min: int | None = None
    level_max: int | None = None
    description: str = ""
    start_npc: QuestNpc | None = None
    reward_count: int = 0


class QuestDetail(BaseModel):
    id: int
    slug: str
    name: str
    url: str | None = None
    source_url: str | None = None
    level_min: int | None = None
    level_max: int | None = None
    description: str = ""
    start_npc: QuestNpc | None = None
    rewards: list[QuestReward] = Field(default_factory=list)
    steps: list[QuestStep] = Field(default_factory=list)


class QuestCatalogResponse(BaseModel):
    quests: list[QuestBrief]
    count: int
    generated_at: str | None = None
