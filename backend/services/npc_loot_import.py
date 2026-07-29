"""Parse NPC spoil/drop tables from raw wiki HTML into npc_loot.

Runs as part of the wiki import. When the raw HTML tree is absent (production
after the first import) the step is skipped and existing rows are kept.
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from models.npc_loot import NpcLoot
from models.wiki import WikiEntity
from services.npc_loot import LIB_RAW, get_npc_loot

BATCH = 200


def raw_html_available() -> bool:
    return LIB_RAW.exists()


def rows_for_npc(npc_external_id: int, loot: dict) -> list[NpcLoot]:
    rows: list[NpcLoot] = []
    for kind, key in (("spoil", "spoils"), ("drop", "drops")):
        for order, entry in enumerate(loot.get(key) or []):
            rows.append(
                NpcLoot(
                    npc_external_id=npc_external_id,
                    kind=kind,
                    item_external_id=entry["item_id"],
                    item_name=entry["item_name"],
                    item_grade=entry["item_grade"],
                    item_url=entry["item_url"],
                    amount=entry["amount"],
                    chance_text=entry["chance"],
                    chance_val=entry["chance_val"],
                    sort_order=order,
                )
            )
    return rows


def import_npc_loot(db: Session) -> tuple[int, int]:
    """Return (npcs processed, loot rows written)."""
    if not raw_html_available():
        print(f"Skipping NPC loot: raw HTML not found at {LIB_RAW}")
        return 0, 0

    npcs = db.execute(
        select(WikiEntity.external_id, WikiEntity.url).where(
            WikiEntity.entity_type == "npc",
            WikiEntity.external_id.is_not(None),
        )
    ).all()

    processed = written = 0
    pending: list[NpcLoot] = []
    for external_id, url in npcs:
        loot = get_npc_loot(url)
        rows = rows_for_npc(external_id, loot)
        db.execute(delete(NpcLoot).where(NpcLoot.npc_external_id == external_id))
        pending.extend(rows)
        processed += 1
        written += len(rows)

        if processed % BATCH == 0:
            db.bulk_save_objects(pending)
            db.commit()
            pending.clear()
            print(f"  npc loot: {processed}/{len(npcs)} npcs, {written} rows")

    if pending:
        db.bulk_save_objects(pending)
    db.commit()
    print(f"Imported NPC loot: {written} rows for {processed} npcs")
    return processed, written
