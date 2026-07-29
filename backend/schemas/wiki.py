import uuid

from pydantic import BaseModel


class WikiEntityBrief(BaseModel):
    id: uuid.UUID
    entity_key: str
    entity_type: str
    external_id: int | None
    name: str
    display_name: str
    slug: str
    url: str
    summary: str | None
    image_path: str | None

    model_config = {"from_attributes": True}


class EntityLinkResponse(BaseModel):
    id: uuid.UUID
    link_type: str
    target: WikiEntityBrief

    model_config = {"from_attributes": True}


class WikiEntityDetail(WikiEntityBrief):
    source_url: str | None
    stats: dict | None
    materials: list | None
    content_md: str | None
    category_id: uuid.UUID | None
    links: list[EntityLinkResponse] = []


class NpcItemLootEntry(BaseModel):
    item_id: int
    item_name: str
    item_grade: str
    item_url: str
    amount: str
    chance: str
    chance_val: float


class NpcLootResponse(BaseModel):
    spoils: list[NpcItemLootEntry]
    drops: list[NpcItemLootEntry]
