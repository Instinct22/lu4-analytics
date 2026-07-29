#!/usr/bin/env python3
"""Re-parse NPC spoil/drop tables into npc_loot without a full wiki import."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from database import SessionLocal
from services.npc_loot_import import import_npc_loot


def main() -> None:
    db = SessionLocal()
    try:
        import_npc_loot(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
