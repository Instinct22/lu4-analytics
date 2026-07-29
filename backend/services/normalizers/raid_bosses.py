"""Explode the raid_bosses dataset into the raid_bosses table."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.raid import RaidBoss
from services.dataset_import import register_normalizer
from services.raid_respawn import parse_respawn
from services.raid_routes import how_to_reach_for


@register_normalizer("raid_bosses")
def normalize_raid_bosses(db: Session, payload: Any) -> None:
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
            },
        )

        row = existing.get(external_id)
        if row is None:
            db.add(RaidBoss(external_id=external_id, **fields))
        else:
            for key, value in fields.items():
                setattr(row, key, value)

    # Bosses removed upstream take their timers with them (FK cascade).
    for external_id, row in existing.items():
        if external_id not in seen:
            db.delete(row)
