#!/usr/bin/env python3
"""Build quests_catalog.json from the local Lu4 wiki library."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from quests_catalog.parse import parse_quest_file  # noqa: E402

WIKI = ROOT / "data" / "wiki" / "library"
QUEST_RAW = WIKI / "raw" / "lu4" / "quest"
OUT = ROOT / "data" / "datasets" / "quests_catalog.json"


def build_catalog(quest_dir: Path = QUEST_RAW) -> dict:
    if not quest_dir.is_dir():
        raise FileNotFoundError(f"Wiki quest raw dir not found: {quest_dir}")

    quests: list[dict] = []
    seen: set[int] = set()
    for path in sorted(quest_dir.glob("*.html")):
        if "__" in path.name:
            continue
        parsed = parse_quest_file(path)
        if parsed is None:
            continue
        qid = parsed["id"]
        if qid in seen:
            continue
        seen.add(qid)
        quests.append(parsed)

    quests.sort(key=lambda q: (q.get("level_min") is None, q.get("level_min") or 0, q["id"]))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(quests),
        "quests": quests,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=OUT,
        help=f"Output JSON path (default: {OUT})",
    )
    parser.add_argument(
        "--quest-dir",
        type=Path,
        default=QUEST_RAW,
        help=f"Raw quest HTML directory (default: {QUEST_RAW})",
    )
    args = parser.parse_args()
    catalog = build_catalog(args.quest_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with_level = sum(1 for q in catalog["quests"] if q.get("level_min") is not None)
    print(f"Wrote {catalog['count']} quests ({with_level} with level) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
