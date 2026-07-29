#!/usr/bin/env python3
"""Export l4map-compatible armor_sets.json from local craft catalog (no Cloudflare)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "data" / "datasets" / "craft_catalog.json"
DEFAULT_OUT = ROOT / "data" / "l4map_armor_sets_local.json"


def _member_row(item_id: int, items: dict) -> dict:
    raw = items.get(str(item_id)) or items.get(item_id) or {}
    row: dict = {"id": item_id}
    for key in ("name", "grade", "type", "npc_sell", "url"):
        if raw.get(key) is not None:
            row[key if key != "npc_sell" else "price"] = raw[key]
    return row


def catalog_to_l4map(catalog: dict) -> dict:
    set_meta = catalog.get("setMeta") or {}
    items = catalog.get("items") or {}
    sets_out: dict[str, dict] = {}

    for name, meta in set_meta.items():
        if not isinstance(meta, dict):
            continue
        set_id = meta.get("id")
        if set_id is None:
            craftable = meta.get("craftableMemberIds") or []
            set_id = int(craftable[0]) if craftable else None
        if set_id is None:
            continue

        member_ids = meta.get("allMemberIds") or meta.get("craftableMemberIds") or []
        member_names = meta.get("memberNames") or {}
        members = []
        for mid in member_ids:
            row = _member_row(int(mid), items)
            mname = member_names.get(str(mid))
            if mname and not row.get("name"):
                row["name"] = mname
            members.append(row)

        entry = {
            "id": set_id,
            "name": meta.get("name") or name,
            "grade": meta.get("grade") or "NG",
            "canonical": meta.get("canonical", True),
            "pvp": bool(meta.get("pvp")),
            "members": members,
            "craftableMemberIds": meta.get("craftableMemberIds") or [],
        }
        if meta.get("slug"):
            entry["slug"] = meta["slug"]
        if meta.get("url"):
            entry["url"] = meta["url"]
        if meta.get("icon"):
            entry["icon"] = meta["icon"]
        if meta.get("effect"):
            entry["effect"] = meta["effect"]
        if meta.get("effectRaw"):
            entry["effectRaw"] = meta["effectRaw"]

        sets_out[str(set_id)] = entry

    return {"sets": sets_out}


def main() -> None:
    parser = argparse.ArgumentParser(description="Export l4map armor_sets.json from craft catalog")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    if not args.catalog.is_file():
        print(f"Catalog not found: {args.catalog}", file=sys.stderr)
        sys.exit(1)

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    payload = catalog_to_l4map(catalog)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    visible = sum(
        1
        for meta in payload["sets"].values()
        if meta.get("canonical") is not False and not meta.get("pvp") and meta.get("members")
    )
    print(f"Exported {len(payload['sets'])} sets ({visible} visible) -> {args.output}")


if __name__ == "__main__":
    main()
