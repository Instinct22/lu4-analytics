#!/usr/bin/env python3
"""Validate items_encyclopedia.json against reference items and set coverage."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENC = ROOT / "data" / "datasets" / "items_encyclopedia.json"

REFERENCE_IDS = {
    6661: {"name": "Earring of Orfen", "min_drops": 1, "min_enchant": 8},
    960: {"min_drops": 15, "min_spoils": 1},
}


def _legacy_paths(item: dict) -> list[str]:
    hits: list[str] = []
    if isinstance(item.get("url"), str) and "/lu4/" in item["url"]:
        hits.append("url")
    if item.get("provenance"):
        hits.append("provenance")
    for row in (item.get("drops") or []) + (item.get("spoils") or []):
        if isinstance(row, dict) and row.get("npc_url"):
            hits.append("npc_url")
    return hits


def main() -> int:
    if not ENC.is_file():
        print(f"Missing {ENC}", file=sys.stderr)
        return 1

    payload = json.loads(ENC.read_text(encoding="utf-8"))
    items = payload.get("items") or {}
    errors: list[str] = []

    if not payload.get("library"):
        errors.append("Missing library metadata — run finalize_encyclopedia.py")

    for iid, spec in REFERENCE_IDS.items():
        item = items.get(str(iid))
        if not item:
            errors.append(f"Missing reference item {iid}")
            continue
        if spec.get("name") and item.get("name") != spec["name"]:
            errors.append(f"Item {iid} name mismatch: {item.get('name')}")
        if spec.get("min_drops") and len(item.get("drops") or []) < spec["min_drops"]:
            errors.append(f"Item {iid} drops below minimum")
        if spec.get("min_spoils") and len(item.get("spoils") or []) < spec["min_spoils"]:
            errors.append(f"Item {iid} spoils below minimum")
        if spec.get("min_enchant") and len(item.get("enchant") or []) < spec["min_enchant"]:
            errors.append(f"Item {iid} enchant rows below minimum")
        legacy = _legacy_paths(item)
        if legacy:
            errors.append(f"Item {iid} still has legacy fields: {', '.join(legacy)}")
        item_set = item.get("set")
        if isinstance(item_set, dict) and item_set.get("url"):
            errors.append(f"Item {iid} set still has url")

    set_names_enc = {
        (item.get("set_name") or "").lower()
        for item in items.values()
        if isinstance(item, dict) and item.get("set_name")
    }
    craft_sets = (payload.get("craft") or {}).get("sets") or {}
    craft_set_names = {name.lower() for name in craft_sets if isinstance(name, str)}
    overlap = set_names_enc & craft_set_names

    craft_meta = (payload.get("craft") or {}).get("set_meta") or {}
    legacy_set_urls = sum(
        1 for entry in craft_meta.values() if isinstance(entry, dict) and entry.get("url")
    )
    if legacy_set_urls:
        errors.append(f"craft.set_meta still has {legacy_set_urls} legacy url fields")

    by_product = (payload.get("craft") or {}).get("by_product") or {}
    recipe_urls = 0
    for variants in by_product.values():
        if not isinstance(variants, list):
            continue
        for variant in variants:
            if isinstance(variant, dict) and variant.get("recipe_url"):
                recipe_urls += 1
    if recipe_urls:
        errors.append(f"craft.by_product still has {recipe_urls} recipe_url fields")

    print(f"Items: {payload.get('item_count')} sections={payload.get('section_counts')}")
    print(f"Library: {(payload.get('library') or {}).get('id')}")
    print(f"Set name overlap encyclopedia/craft.sets: {len(overlap)}")
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1
    print("Validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
