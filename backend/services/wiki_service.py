"""Wiki entity reads and graph helpers."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.errors import AppError
from models.npc_loot import NpcLoot
from models.wiki import EntityLink, WikiEntity
from schemas.wiki import EntityLinkResponse, WikiEntityBrief, WikiEntityDetail
from services.npc_loot import get_npc_loot


def get_entity_or_404(db: Session, entity_id: uuid.UUID) -> WikiEntity:
    entity = db.get(WikiEntity, entity_id)
    if entity is None:
        raise AppError("Entity not found", code="not_found", status_code=404)
    return entity


def get_entity_by_external(db: Session, entity_type: str, external_id: int) -> WikiEntity:
    entity = db.scalar(
        select(WikiEntity).where(
            WikiEntity.entity_type == entity_type,
            WikiEntity.external_id == external_id,
        )
    )
    if entity is None:
        raise AppError("Entity not found", code="not_found", status_code=404)
    return entity


def get_npc_by_external(db: Session, external_id: int) -> WikiEntity:
    entity = db.scalar(
        select(WikiEntity).where(
            WikiEntity.entity_type == "npc",
            WikiEntity.external_id == external_id,
        )
    )
    if entity is None:
        raise AppError("NPC not found", code="not_found", status_code=404)
    return entity


def build_entity_detail(db: Session, entity: WikiEntity) -> WikiEntityDetail:
    links = db.scalars(select(EntityLink).where(EntityLink.source_entity_id == entity.id)).all()
    link_responses: list[EntityLinkResponse] = []
    for link in links:
        target = db.get(WikiEntity, link.target_entity_id)
        if target:
            link_responses.append(
                EntityLinkResponse(
                    id=link.id,
                    link_type=link.link_type,
                    target=WikiEntityBrief.model_validate(target),
                )
            )
    detail = WikiEntityDetail.model_validate(entity)
    detail.links = link_responses
    return detail


def entity_graph(db: Session, entity_id: uuid.UUID) -> list[WikiEntityBrief]:
    get_entity_or_404(db, entity_id)
    link_ids = db.scalars(
        select(EntityLink.target_entity_id).where(EntityLink.source_entity_id == entity_id)
    ).all()
    if not link_ids:
        return []
    related = db.scalars(select(WikiEntity).where(WikiEntity.id.in_(link_ids)).limit(100)).all()
    return [WikiEntityBrief.model_validate(r) for r in related]


def _loot_entry(row: NpcLoot) -> dict:
    return {
        "item_id": row.item_external_id,
        "item_name": row.item_name,
        "item_grade": row.item_grade,
        "item_url": row.item_url,
        "amount": row.amount,
        "chance": row.chance_text,
        "chance_val": float(row.chance_val),
    }


def npc_loot_response(db: Session, external_id: int) -> dict:
    entity = get_npc_by_external(db, external_id)
    rows = db.scalars(
        select(NpcLoot)
        .where(NpcLoot.npc_external_id == external_id)
        .order_by(NpcLoot.sort_order)
    ).all()
    if rows:
        return {
            "spoils": [_loot_entry(r) for r in rows if r.kind == "spoil"],
            "drops": [_loot_entry(r) for r in rows if r.kind == "drop"],
        }
    # Nothing imported for this NPC yet — parse the HTML as before.
    return get_npc_loot(entity.url)
