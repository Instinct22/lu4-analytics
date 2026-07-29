#!/usr/bin/env python3
"""Compare craft catalog setMeta with l4map armor_sets.json dump."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_L4MAP = ROOT / "data" / "l4map_armor_sets.json"
DEFAULT_LOCAL = ROOT / "data" / "l4map_armor_sets_local.json"


def _normalize_name(name: str) -> str:
    text = re.sub(r"\{?\s*pvp\s*\}?", "", name or "", flags=re.IGNORECASE)
    text = re.sub(r"\s+(NG|D|C|B|A|S)$", "", text.strip())
    return text.lower()


def _catalog_sets(catalog: dict) -> dict[str, dict]:
    set_meta = catalog.get("setMeta") or {}
    if set_meta:
        return {
            name: meta
            for name, meta in set_meta.items()
            if isinstance(meta, dict) and meta.get("canonical") is not False and not meta.get("pvp")
        }
    items = catalog.get("items") or {}
    fallback: dict[str, dict] = {}
    for name, ids in (catalog.get("sets") or {}).items():
        fallback[name] = {
            "name": name,
            "grade": (items.get(str(ids[0])) or {}).get("grade") if ids else "",
            "craftableMemberIds": ids,
            "allMemberIds": ids,
        }
    return fallback


def _l4map_sets(payload: dict) -> dict[str, dict]:
    sets_block = payload.get("sets") if isinstance(payload.get("sets"), dict) else payload
    result: dict[str, dict] = {}
    for key, meta in (sets_block or {}).items():
        if not isinstance(meta, dict):
            continue
        if meta.get("canonical") is False or meta.get("pvp"):
            continue
        name = meta.get("name") or key
        result[_normalize_name(name)] = meta
    return result


def _member_ids(meta: dict, *, craftable_only: bool = False) -> set[int]:
    if craftable_only:
        raw = meta.get("craftableMemberIds") or []
    else:
        raw = meta.get("allMemberIds") or meta.get("members") or []
        if isinstance(raw, list) and raw and isinstance(raw[0], dict):
            raw = [row.get("id") for row in raw if isinstance(row, dict)]
    return {int(x) for x in raw if x is not None}


def compare_catalog_with_l4map(catalog: dict, l4map: dict) -> dict:
    ours = {
        _normalize_name(name): {"name": name, **meta}
        for name, meta in _catalog_sets(catalog).items()
    }
    theirs = _l4map_sets(l4map)

    our_names = set(ours)
    their_names = set(theirs)

    missing_in_ours = sorted(their_names - our_names)
    extra_in_ours = sorted(our_names - their_names)

    member_diffs = []
    for norm in sorted(our_names & their_names):
        our_meta = ours[norm]
        their_meta = theirs[norm]
        our_all = _member_ids(our_meta, craftable_only=False)
        their_all = _member_ids(their_meta, craftable_only=False)
        our_craft = _member_ids(our_meta, craftable_only=True)
        their_craft = _member_ids(their_meta, craftable_only=True)
        if our_all != their_all or our_craft != their_craft:
            member_diffs.append(
                {
                    "name": our_meta.get("name") or their_meta.get("name"),
                    "ourAll": sorted(our_all),
                    "theirAll": sorted(their_all),
                    "ourCraftable": sorted(our_craft),
                    "theirCraftable": sorted(their_craft),
                    "missingAll": sorted(their_all - our_all),
                    "extraAll": sorted(our_all - their_all),
                }
            )

    missing_meta = []
    for name, meta in ours.items():
        if not meta.get("icon"):
            missing_meta.append({"name": meta.get("name"), "field": "icon"})
        if not meta.get("effect") and not meta.get("effectRaw"):
            missing_meta.append({"name": meta.get("name"), "field": "effect"})

    return {
        "summary": {
            "catalogSets": len(ours),
            "l4mapSets": len(theirs),
            "matchedNames": len(our_names & their_names),
            "missingInCatalog": len(missing_in_ours),
            "extraInCatalog": len(extra_in_ours),
            "memberDiffs": len(member_diffs),
            "missingMetaFields": len(missing_meta),
        },
        "missingInCatalog": [theirs[name].get("name") or name for name in missing_in_ours],
        "extraInCatalog": [ours[name].get("name") or name for name in extra_in_ours],
        "memberDiffs": member_diffs,
        "missingMetaFields": missing_meta,
    }


def _load_l4map(path: Path) -> dict | None:
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8").lstrip()
    if text.startswith("<"):
        print(f"l4map dump at {path} looks like HTML (Cloudflare?) — skipping")
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print(f"l4map dump at {path} is not valid JSON — skipping")
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare catalog setMeta with l4map armor_sets.json")
    parser.add_argument("--catalog", type=Path, default=ROOT / "data" / "datasets" / "craft_catalog.json")
    parser.add_argument("--l4map", type=Path, default=DEFAULT_L4MAP, help="External l4map dump (browser save)")
    parser.add_argument(
        "--local",
        type=Path,
        default=DEFAULT_LOCAL,
        help="Local wiki-derived reference (scripts/export_l4map_armor_sets.py)",
    )
    parser.add_argument("--report", type=Path, default=ROOT / "data" / "reports" / "sets_diff.json")
    args = parser.parse_args()

    if not args.catalog.is_file():
        print(f"Catalog not found: {args.catalog}", file=sys.stderr)
        sys.exit(1)

    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    l4map_payload = _load_l4map(args.l4map)
    source = "l4map"
    if l4map_payload is None and args.local.is_file():
        l4map_payload = _load_l4map(args.local)
        source = "local"
    if l4map_payload is None:
        print(f"No l4map reference found ({args.l4map} or {args.local})")
        print("Run: py -3 scripts/export_l4map_armor_sets.py")
        print("Or save https://l4map.com/data/armor_sets.json in the browser for external diff.")
        report = {
            "summary": {"catalogSets": len(_catalog_sets(catalog)), "l4mapSets": 0},
            "note": "l4map dump missing — catalog-only meta audit",
            "missingMetaFields": compare_catalog_with_l4map(catalog, {"sets": {}})["missingMetaFields"],
        }
    else:
        report = compare_catalog_with_l4map(catalog, l4map_payload)
        report["referenceSource"] = source

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = report.get("summary") or {}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
