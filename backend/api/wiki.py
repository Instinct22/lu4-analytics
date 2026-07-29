"""HTTP layer for wiki entity reads and NPC loot."""

import uuid

from fastapi import APIRouter

from api.deps import CurrentUser, DbSession
from schemas.wiki import NpcLootResponse, WikiEntityBrief, WikiEntityDetail
from services import wiki_service

router = APIRouter()


@router.get("/npc/{external_id}/loot", response_model=NpcLootResponse)
def get_npc_loot_by_external(external_id: int, db: DbSession, user: CurrentUser):
    return NpcLootResponse(**wiki_service.npc_loot_response(db, external_id))


@router.get("/entities/by-external/{entity_type}/{external_id}", response_model=WikiEntityDetail)
def get_entity_by_external(
    entity_type: str,
    external_id: int,
    db: DbSession,
    user: CurrentUser,
):
    entity = wiki_service.get_entity_by_external(db, entity_type, external_id)
    return wiki_service.build_entity_detail(db, entity)


@router.get("/entities/{entity_id}", response_model=WikiEntityDetail)
def get_entity(entity_id: uuid.UUID, db: DbSession, user: CurrentUser):
    entity = wiki_service.get_entity_or_404(db, entity_id)
    return wiki_service.build_entity_detail(db, entity)


@router.get("/entities/{entity_id}/graph", response_model=list[WikiEntityBrief])
def entity_graph(entity_id: uuid.UUID, db: DbSession, user: CurrentUser):
    return wiki_service.entity_graph(db, entity_id)
