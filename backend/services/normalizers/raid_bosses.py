"""Explode the raid_bosses dataset into the raid_bosses table."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from models.npc_loot import NpcLoot
from models.raid import RaidBoss
from models.wiki import WikiCategory, WikiEntity
from services.name_matching import normalize_product_name
from services.npc_loot_import import rows_for_npc
from services.dataset_import import register_normalizer
from services.raid_respawn import parse_respawn
from services.raid_routes import how_to_reach_for


def _replace_loot(db: Session, external_id: int, boss: dict) -> None:
    loot = {"drops": [], "spoils": []}
    for kind in loot:
        for group in boss.get(kind) or []:
            factor = Decimal((group.get("groupChance") or "100%").rstrip("%")) / 100
            for item in group["items"]:
                chance = Decimal(item["chance"].rstrip("%")) * factor
                loot[kind].append({
                    "item_id": item["itemId"], "item_name": item["name"],
                    "item_grade": item.get("grade") or "", "item_url": item["url"],
                    "amount": item["amount"], "chance_val": chance,
                    "chance": f"{chance.normalize():f}%",
                })
    db.execute(delete(NpcLoot).where(NpcLoot.npc_external_id == external_id))
    db.add_all(rows_for_npc(external_id, loot))


def _update_wiki_entity(db: Session, external_id: int, boss: dict) -> None:
    key = f"npc:{external_id}"
    entity = db.scalar(select(WikiEntity).where(WikiEntity.entity_key == key))
    if entity is None:
        category_id = db.scalar(select(WikiCategory.id).where(WikiCategory.slug == "npc"))
        entity = WikiEntity(entity_key=key, entity_type="npc", external_id=external_id, category_id=category_id)
        db.add(entity)

    entity.name = entity.display_name = boss["name"]
    entity.name_normalized = normalize_product_name(entity.name)
    entity.source_url = boss["wikiUrl"]
    entity.url = urlsplit(entity.source_url).path
    entity.slug = entity.url.rsplit("/", 1)[-1]
    entity.image_path = boss.get("image")
    entity.summary = f"{boss['bossType']} · Lv. {boss['level']}"
    entity.stats = {k: v for k, v in {
        "Level": boss["level"], "Race": boss.get("race"), "Location": boss.get("location"),
        "Respawn": boss.get("respawn"), **boss["stats"],
    }.items() if v is not None}
    lines = [boss.get("lore") or "", "Skills"]
    for skill in boss["skills"]:
        lines.extend([skill["name"], f"Lv. {skill['level']}", skill.get("desc") or ""])
    for kind, title in (("drops", "Drop"), ("spoils", "Spoil")):
        if boss[kind]:
            lines.extend([title, "Item", "Amount", "Chance"])
        for group in boss[kind]:
            if group["groupChance"]:
                lines.append(f"Group Chance: {group['groupChance']}")
            for item in group["items"]:
                lines.extend([item["name"], item.get("grade") or "", item["amount"], item["chance"]])
    entity.content_md = "## Content\n" + "\n".join(filter(None, lines))
    entity.search_vector = (
        func.setweight(func.to_tsvector("simple", entity.name), "A")
        .op("||")(func.setweight(func.to_tsvector("simple", entity.summary), "B"))
        .op("||")(func.setweight(func.to_tsvector("simple", entity.content_md), "C"))
    )


@register_normalizer("raid_bosses")
def normalize_raid_bosses(db: Session, payload: Any, *, prune_missing: bool = True) -> None:
    if not isinstance(payload, dict):
        return

    existing = {b.external_id: b for b in db.scalars(select(RaidBoss)).all()}
    seen: set[int] = set()

    for boss in payload.get("bosses") or []:
        external_id = boss.get("id")
        if not isinstance(external_id, int):
            continue
        seen.add(external_id)
        window = parse_respawn(boss.get("respawn"))
        if "spoils" in boss:
            _replace_loot(db, external_id, boss)
            _update_wiki_entity(db, external_id, boss)

        fields = dict(
            name=boss.get("name") or f"Boss {external_id}",
            level=boss.get("level"),
            map_x=boss.get("x"),
            map_y=boss.get("y"),
            location=boss.get("location"),
            respawn_raw=boss.get("respawn"),
            respawn_min_sec=window[0] if window else None,
            respawn_max_sec=window[1] if window else None,
            image_url=boss.get("image"),
            wiki_url=boss.get("wikiUrl"),
            payload={
                "stats": boss.get("stats") or {},
                "lore": boss.get("lore"),
                "howToReach": how_to_reach_for(external_id, boss),
                "skills": boss.get("skills") or [],
                "drops": boss.get("drops") or [],
                "spoils": boss.get("spoils") or [],
                "race": boss.get("race"),
                "bossType": boss.get("bossType"),
                "spawnPoints": boss.get("spawnPoints") or [],
                "minions": boss.get("minions") or [],
                "soulCrystals": boss.get("soulCrystals") or [],
                "detailsPending": boss.get("detailsPending", False),
            },
        )

        row = existing.get(external_id)
        if row is None:
            db.add(RaidBoss(external_id=external_id, **fields))
        else:
            for key, value in fields.items():
                setattr(row, key, value)

    # Bosses removed upstream take their timers with them (FK cascade).
    if not prune_missing:
        return
    for external_id, row in existing.items():
        if external_id not in seen:
            db.delete(row)
