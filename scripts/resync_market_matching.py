#!/usr/bin/env python3
"""Re-normalize wiki item names and re-bind market records to canonical bases.

Fixes stale ``name_normalized`` keys (e.g. HTML entities like ``&#039;``) that
break variant matching, then folds every market record onto its canonical base
item with soul-ability / rarity / enchant stored as attributes.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from calculations.price_stats import recalculate_item_statistics
from database import SessionLocal
from services.import_service import rematch_market_records
from services.normalizers.items_encyclopedia import (
    _refresh_wiki_item_name_normalized,
    _sync_wiki_names_from_encyclopedia,
)


def main() -> None:
    db = SessionLocal()
    try:
        synced = _sync_wiki_names_from_encyclopedia(db)
        refreshed = _refresh_wiki_item_name_normalized(db)
        db.flush()
        print(f"Synced names from encyclopedia: {synced}")
        print(f"Refreshed normalized keys: {refreshed}")

        updated, affected = rematch_market_records(db)
        db.commit()
        print(f"Re-matched market records: {updated} changed, {len(affected)} entities affected")

        for index, entity_id in enumerate(affected, start=1):
            if entity_id is None:
                continue
            recalculate_item_statistics(db, entity_id)
            if index % 50 == 0:
                db.commit()
        db.commit()
        print("Recalculated statistics for affected items")
    finally:
        db.close()


if __name__ == "__main__":
    main()
