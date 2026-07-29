#!/usr/bin/env python3
"""Download l4map.com data snapshots and build the local l2map library."""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
L2MAP = ROOT / "l2map"
RAW = L2MAP / "raw"
LIBRARY = L2MAP / "library"

BASE_URL = "https://l4map.com"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
)

# Paths discovered from l4map.com JS (data/*.json). Order: largest / most important first.
DATA_FILES = [
    "data/items.json",
    "data/npc_details.json",
    "data/class_skills.json",
    "data/skill_details.json",
    "data/icons/items.json",
    "data/npc_spawns.json",
    "data/item_sources.json",
    "data/craft_recipes.json",
    "data/quests.json",
    "data/armor_sets.json",
    "data/masterwork_bonuses.json",
    "data/base_stats.json",
    "data/enchant_bonuses.json",
    "data/clan_skills.json",
    "data/classes.json",
    "data/events.json",
]


def fetch_url(path: str) -> bytes:
    req = urllib.request.Request(
        f"{BASE_URL}/{path.lstrip('/')}",
        headers={"User-Agent": USER_AGENT, "Referer": f"{BASE_URL}/"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = resp.read()
    if body[:1] not in (b"{", b"["):
        preview = body[:120].decode("utf-8", errors="replace")
        raise RuntimeError(f"{path}: expected JSON, got: {preview!r}")
    return body


def save_raw(path: str, body: bytes) -> Path:
    dest = RAW / path.removeprefix("data/")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    return dest


def load_raw(name: str) -> dict | list:
    return json.loads((RAW / name).read_text(encoding="utf-8"))


def build_items_by_key(items: dict) -> dict[str, int]:
    by_key: dict[str, tuple[int, int]] = {}
    for sid, row in items.items():
        if not isinstance(row, dict) or row.get("name") is None:
            continue
        iid = int(row.get("id", sid))
        key = f"{row['name']}|{row.get('grade') or ''}"
        cur = by_key.get(key)
        if cur is None or iid < cur[0]:
            by_key[key] = (iid, iid)
    return {k: v[0] for k, v in by_key.items()}


def build_library(fetched_at: str) -> None:
    items_doc = load_raw("items.json")
    items: dict = items_doc.get("items") or {}

    craft = load_raw("craft_recipes.json")
    by_product: dict = craft.get("byProduct") or {}
    craft_items: dict = craft.get("items") or {}

    mw_doc = load_raw("masterwork_bonuses.json")
    mw_by_base: dict = mw_doc.get("byBaseId") or {}

    src_doc = load_raw("item_sources.json")
    drop: dict = src_doc.get("drop") or {}
    spoil: dict = src_doc.get("spoil") or {}

    enriched: dict[str, dict] = {}
    for sid, row in items.items():
        if not isinstance(row, dict):
            continue
        iid = str(row.get("id", sid))
        entry = dict(row)
        entry["key"] = f"{row.get('name', '')}|{row.get('grade') or ''}"
        entry["craftRecipes"] = by_product.get(iid) or by_product.get(sid) or []
        entry["masterwork"] = mw_by_base.get(iid) or mw_by_base.get(sid)
        entry["drop"] = drop.get(iid) or drop.get(sid) or []
        entry["spoil"] = spoil.get(iid) or spoil.get(sid) or []
        enriched[iid] = entry

    items_by_key = build_items_by_key(items)

    armor_sets_doc = load_raw("armor_sets.json")
    sets_raw = armor_sets_doc.get("sets") or armor_sets_doc
    if isinstance(sets_raw, dict) and "sets" in sets_raw:
        sets_raw = sets_raw["sets"]

    index = {
        "source": BASE_URL,
        "fetchedAt": fetched_at,
        "files": {
            "raw": "raw/",
            "itemsById": "library/items_by_id.json",
            "itemsByKey": "library/items_by_key.json",
            "armorSets": "library/armor_sets.json",
            "craftRecipes": "raw/craft_recipes.json",
            "itemSources": "raw/item_sources.json",
            "masterworkBonuses": "raw/masterwork_bonuses.json",
            "npcDetails": "raw/npc_details.json",
            "npcSpawns": "raw/npc_spawns.json",
            "quests": "raw/quests.json",
            "classes": "raw/classes.json",
            "classSkills": "raw/class_skills.json",
            "skillDetails": "raw/skill_details.json",
            "iconsIndex": "raw/icons/items.json",
        },
        "counts": {
            "items": len(enriched),
            "itemsByKey": len(items_by_key),
            "craftProducts": len(by_product),
            "craftItemRefs": len(craft_items),
            "masterworkBases": len(mw_by_base),
            "dropItems": len(drop),
            "spoilItems": len(spoil),
            "armorSets": len(sets_raw) if isinstance(sets_raw, dict) else 0,
        },
        "sourceMeta": {
            "items": items_doc.get("meta"),
            "craftRecipes": craft.get("meta"),
            "itemSources": src_doc.get("meta"),
            "armorSets": armor_sets_doc.get("meta") if isinstance(armor_sets_doc, dict) else None,
            "masterworkBonuses": mw_doc.get("meta"),
        },
    }

    LIBRARY.mkdir(parents=True, exist_ok=True)
    (LIBRARY / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (LIBRARY / "items_by_id.json").write_text(
        json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (LIBRARY / "items_by_key.json").write_text(
        json.dumps(items_by_key, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (LIBRARY / "armor_sets.json").write_text(
        json.dumps(armor_sets_doc, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> int:
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    RAW.mkdir(parents=True, exist_ok=True)

    manifest_files: list[dict] = []
    errors: list[str] = []

    for path in DATA_FILES:
        try:
            body = fetch_url(path)
            dest = save_raw(path, body)
            manifest_files.append(
                {
                    "path": path,
                    "local": str(dest.relative_to(ROOT)).replace("\\", "/"),
                    "bytes": len(body),
                    "ok": True,
                }
            )
            print(f"OK  {path} ({len(body):,} bytes)")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{path}: {exc}")
            manifest_files.append({"path": path, "ok": False, "error": str(exc)})
            print(f"ERR {path}: {exc}", file=sys.stderr)

    manifest = {
        "source": BASE_URL,
        "fetchedAt": fetched_at,
        "files": manifest_files,
        "errors": errors,
    }
    L2MAP.mkdir(parents=True, exist_ok=True)
    (L2MAP / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if not (RAW / "items.json").exists():
        print("items.json missing — library not built", file=sys.stderr)
        return 1

    build_library(fetched_at)
    print(f"Library written to {LIBRARY.relative_to(ROOT)}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
