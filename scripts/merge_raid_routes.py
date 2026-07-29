"""Merge how_to_reach.json into raid_bosses.json."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTES = ROOT / "data" / "raid-bosses" / "how_to_reach.json"
DATASET = ROOT / "data" / "datasets" / "raid_bosses.json"


def main() -> None:
    routes = json.loads(ROUTES.read_text(encoding="utf-8"))
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    merged = 0
    for boss in payload.get("bosses") or []:
        npc_id = boss.get("id")
        route = routes.get(str(npc_id)) if npc_id is not None else None
        if route:
            boss["howToReach"] = route
            merged += 1
        else:
            boss.pop("howToReach", None)
    DATASET.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Merged howToReach for {merged} bosses into {DATASET}")


if __name__ == "__main__":
    main()
