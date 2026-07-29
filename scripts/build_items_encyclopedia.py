#!/usr/bin/env python3
"""Build or finalize items_encyclopedia.json — self-contained library in data/datasets/."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from craft_catalog.categories import resolve_category  # noqa: E402
from craft_catalog.item_classify import (  # noqa: E402
    build_sealed_groups,
    classify_section,
    other_subcategory,
)
from craft_catalog.wiki_parse import parse_item_full  # noqa: E402
from encyclopedia_lib import finalize_payload  # noqa: E402

WIKI = ROOT / "data" / "wiki" / "library"
ITEM_RAW = WIKI / "raw" / "lu4" / "item"
CATALOG_JSONL = WIKI / "index" / "catalog.jsonl"
CRAFT_CATALOG = ROOT / "data" / "datasets" / "craft_catalog.json"
CRAFT_RESOURCES = ROOT / "data" / "datasets" / "craft_resources_data.json"
DUALS_CATALOG = ROOT / "data" / "datasets" / "duals_catalog.json"
OUT = ROOT / "data" / "datasets" / "items_encyclopedia.json"


def _load_json(path: Path) -> Any:
    if not path.is_file():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _load_item_ids() -> dict[int, str]:
    ids: dict[int, str] = {}
    if not CATALOG_JSONL.is_file():
        return ids
    for line in CATALOG_JSONL.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("type") != "item":
            continue
        iid = row.get("id")
        if isinstance(iid, int):
            ids[iid] = row.get("url") or f"/lu4/item/{iid}"
    return ids


def _dual_ids() -> set[int]:
    payload = _load_json(DUALS_CATALOG) or {}
    ids: set[int] = set()
    for raw in (payload.get("items") or {}).keys():
        try:
            ids.add(int(raw))
        except (TypeError, ValueError):
            pass
    for raw in (payload.get("byProduct") or {}).keys():
        try:
            ids.add(int(raw))
        except (TypeError, ValueError):
            pass
    return ids


def _resource_sources(payload: dict | None) -> dict[int, dict[str, list]]:
    out: dict[int, dict[str, list]] = {}
    if not payload:
        return out
    for section_key in ("base_materials", "craft_materials_lte_30"):
        for mat in payload.get(section_key) or []:
            if not isinstance(mat, dict):
                continue
            mid = mat.get("id")
            if not isinstance(mid, int):
                continue
            out[mid] = {"drop": mat.get("drop") or [], "spoil": mat.get("spoil") or []}
    return out


def _merge_sources(primary: list, secondary: list) -> list:
    seen: set[tuple] = set()
    merged: list = []
    for row in primary + secondary:
        if not isinstance(row, dict):
            continue
        key = (row.get("npc_id"), row.get("amount") or "", row.get("chance") or "")
        if key in seen:
            continue
        seen.add(key)
        merged.append(row)
    return merged


def _apply_craft(item: dict, craft_item: dict | None, by_product: dict) -> None:
    if not craft_item:
        return
    for field in ("category", "set_name", "is_recipe_scroll"):
        if craft_item.get(field) is not None and field not in item:
            item[field] = craft_item[field]
    iid = item["id"]
    variants = by_product.get(str(iid)) or by_product.get(iid) or []
    item["craft"] = {"craftable": bool(variants), "variants": variants}


def _apply_resources(item: dict, sources: dict | None) -> None:
    if not sources:
        return
    if sources.get("drop"):
        item["drops"] = _merge_sources(item.get("drops") or [], sources["drop"])
        item["has_drop"] = bool(item["drops"])
    if sources.get("spoil"):
        item["spoils"] = _merge_sources(item.get("spoils") or [], sources["spoil"])
        item["has_spoil"] = bool(item["spoils"])


def rebuild_from_wiki(*, limit: int | None = None) -> dict:
    """Optional: rebuild from wiki HTML in data/wiki/library (legacy pipeline)."""
    if not ITEM_RAW.is_dir():
        raise FileNotFoundError(
            f"Wiki item HTML not found at {ITEM_RAW}. "
            "Use --finalize-only to refresh the existing encyclopedia JSON."
        )

    item_urls = _load_item_ids()
    if limit:
        item_urls = dict(list(sorted(item_urls.items()))[:limit])

    craft_payload = _load_json(CRAFT_CATALOG) or {}
    craft_items = craft_payload.get("items") or {}
    by_product = craft_payload.get("byProduct") or {}
    set_meta = craft_payload.get("setMeta") or {}
    resource_map = _resource_sources(_load_json(CRAFT_RESOURCES))
    dual_ids = _dual_ids()

    items: dict[int, dict[str, Any]] = {}
    for iid, url in sorted(item_urls.items()):
        items[iid] = parse_item_full(ITEM_RAW, iid, url)

    build_sealed_groups(items)

    for iid, item in items.items():
        _apply_craft(item, craft_items.get(str(iid)) or craft_items.get(iid), by_product)
        _apply_resources(item, resource_map.get(iid))
        if not item.get("category"):
            item["category"] = resolve_category(item.get("type") or "", item.get("name") or "")
        item["section"] = classify_section(
            item.get("name") or "",
            item.get("grade") or "",
            item.get("type") or "",
            dual_ids=dual_ids,
            item_id=iid,
        )
        if item["section"] == "other":
            item["other_subcategory"] = other_subcategory(
                item.get("type") or "", item.get("name") or "", item.get("category")
            )
        if item.get("set_name") and item["set_name"] in set_meta:
            item["set"] = set_meta[item["set_name"]]
        elif item.get("links", {}).get("set"):
            item["set"] = item["links"]["set"]

    counts = {"gear": 0, "other": 0, "excluded": 0}
    for item in items.values():
        sec = item.get("section") or "other"
        counts[sec] = counts.get(sec, 0) + 1

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "item_count": len(items),
        "section_counts": counts,
        "items": {str(k): v for k, v in items.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build/finalize items encyclopedia")
    parser.add_argument(
        "--finalize-only",
        action="store_true",
        help="Normalize existing JSON only (default when OUT exists)",
    )
    parser.add_argument(
        "--rebuild-wiki",
        action="store_true",
        help="Rebuild from data/wiki/library HTML (optional legacy source)",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()

    craft_catalog = _load_json(CRAFT_CATALOG)

    if args.rebuild_wiki:
        raw = rebuild_from_wiki(limit=args.limit)
    elif args.finalize_only or args.out.is_file():
        if not args.out.is_file():
            raise SystemExit(f"No encyclopedia at {args.out}; run with --rebuild-wiki first.")
        raw = json.loads(args.out.read_text(encoding="utf-8"))
    else:
        raw = rebuild_from_wiki(limit=args.limit)

    payload = finalize_payload(raw, craft_catalog=craft_catalog)
    payload["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Wrote {payload['item_count']} items -> {args.out}")
    print("Library:", payload.get("library"))
    print("Sections:", payload.get("section_counts"))


if __name__ == "__main__":
    main()
