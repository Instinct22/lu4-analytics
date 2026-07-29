#!/usr/bin/env python3
"""Build craft_catalog.json from the local Lu4 wiki library."""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from craft_catalog.categories import apply_categories, apply_set_names, build_sets  # noqa: E402
from craft_catalog.set_meta import build_set_meta, enrich_set_meta  # noqa: E402
from craft_catalog.set_parse import parse_set_page  # noqa: E402
from craft_catalog.wiki_parse import (  # noqa: E402
    ITEM_ID_RE,
    load_html,
    parse_item_page,
    parse_recipe_variant,
)

WIKI = ROOT / "data" / "wiki" / "library"
OUT = ROOT / "data" / "datasets" / "craft_catalog.json"
ITEM_RAW = WIKI / "raw" / "lu4" / "item"
SET_RAW = WIKI / "raw" / "lu4" / "set"


def _collect_tree_ids(nodes: list) -> set[int]:
    ids: set[int] = set()
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        mid = node.get("id")
        if isinstance(mid, int):
            ids.add(mid)
        ids.update(_collect_tree_ids(node.get("children") or []))
    return ids


def build_catalog(wiki_root: Path = WIKI) -> dict:
    if not ITEM_RAW.is_dir():
        raise FileNotFoundError(f"Wiki item raw dir not found: {ITEM_RAW}")

    by_product: dict[str, list[dict]] = defaultdict(list)
    referenced_ids: set[int] = set()

    recipe_files = sorted(ITEM_RAW.glob("*.html"))
    seen_recipes: set[int] = set()
    for path in recipe_files:
        if "__" in path.name:
            continue
        html = load_html(path)
        if "recipe_content" not in html:
            continue
        m = re.match(r"^(\d+)-", path.name)
        if not m:
            continue
        recipe_id = int(m.group(1))
        if recipe_id in seen_recipes:
            continue
        seen_recipes.add(recipe_id)
        recipe_url = f"/lu4/item/{path.stem}"
        variant = parse_recipe_variant(html, recipe_id, recipe_url)
        if variant is None:
            continue
        product_id = variant.pop("product_id")
        variants = by_product[str(product_id)]
        if any(v.get("recipe_id") == recipe_id for v in variants):
            continue
        variants.append(variant)
        referenced_ids.add(recipe_id)
        referenced_ids.add(product_id)
        referenced_ids.update(_collect_tree_ids(variant.get("tree") or []))

    items: dict[str, dict] = {}
    for item_id in sorted(referenced_ids):
        matches = list(ITEM_RAW.glob(f"{item_id}-*.html"))
        if not matches:
            continue
        path = matches[0]
        url = f"/lu4/item/{path.stem}"
        html = load_html(path)
        item = parse_item_page(html, item_id, url)
        items[str(item_id)] = item

    for variants in by_product.values():
        variants.sort(key=lambda v: (v.get("rate") or 100, v.get("recipe_id") or 0))

    craftable_ids = {int(k) for k in by_product}
    fallback_set_names: dict[int, str] = {}
    for raw_pid, item in items.items():
        set_name = item.get("set_name")
        if set_name:
            try:
                fallback_set_names[int(raw_pid)] = set_name
            except (TypeError, ValueError):
                pass

    set_pages = []
    if SET_RAW.is_dir():
        for path in sorted(SET_RAW.glob("*.html")):
            if "__" in path.name:
                continue
            url = f"/lu4/set/{path.stem}"
            page = parse_set_page(load_html(path), url)
            if page is not None:
                set_pages.append(page)

    variant_count = sum(len(v) for v in by_product.values())
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "product_count": len(by_product),
        "variant_count": variant_count,
        "items": items,
        "byProduct": dict(by_product),
        "categories": {},
        "sets": {},
        "setMeta": {},
    }
    payload["sets"] = build_sets(set_pages, craftable_ids, items, fallback_set_names)
    payload["setMeta"] = build_set_meta(set_pages, payload["sets"], items, craftable_ids)
    enrich_set_meta(payload["setMeta"], items, wiki_root, set_pages, craftable_ids)
    apply_set_names(items, payload["sets"])
    apply_categories(payload)
    return payload


def _compare(existing: dict, built: dict) -> list[str]:
    issues: list[str] = []
    for key in ("product_count", "variant_count"):
        if existing.get(key) != built.get(key):
            issues.append(f"{key}: existing={existing.get(key)} built={built.get(key)}")

    ex_magic_d = existing.get("categories", {}).get("armors", {}).get("magic", {}).get("D", [])
    bu_magic_d = built.get("categories", {}).get("armors", {}).get("magic", {}).get("D", [])
    if sorted(ex_magic_d) != sorted(bu_magic_d):
        issues.append(f"armors.magic.D mismatch: existing={ex_magic_d} built={bu_magic_d}")

    ex_misc = set(sum(existing.get("categories", {}).get("armors", {}).get("misc", {}).values(), []))
    bu_misc = set(sum(built.get("categories", {}).get("armors", {}).get("misc", {}).values(), []))
    if ex_misc != bu_misc:
        issues.append(f"armors.misc ids differ: {len(ex_misc)} vs {len(bu_misc)}")

    ex_products = set(existing.get("byProduct", {}).keys())
    bu_products = set(built.get("byProduct", {}).keys())
    if ex_products != bu_products:
        issues.append(
            f"byProduct keys differ: missing={sorted(ex_products - bu_products)[:5]} "
            f"extra={sorted(bu_products - ex_products)[:5]}"
        )
    return issues


def _set_grade_counts(payload: dict) -> dict[str, int]:
    items = payload.get("items") or {}
    counts: dict[str, int] = defaultdict(int)
    for member_ids in (payload.get("sets") or {}).values():
        if not member_ids:
            continue
        first = items.get(str(member_ids[0])) or items.get(member_ids[0])
        grade = (first or {}).get("grade") or "NG"
        counts[grade] += 1
    return dict(counts)


def _incomplete_b_sets(payload: dict) -> list[str]:
    items = payload.get("items") or {}
    incomplete: list[str] = []
    for set_name, member_ids in (payload.get("sets") or {}).items():
        if not member_ids:
            continue
        first = items.get(str(member_ids[0])) or items.get(member_ids[0])
        if (first or {}).get("grade") != "B":
            continue
        if len(member_ids) < 4:
            incomplete.append(set_name)
    return incomplete


def _check_sets(built: dict) -> list[str]:
    issues: list[str] = []
    grade_counts = _set_grade_counts(built)
    if grade_counts.get("A", 0) <= 0:
        issues.append(f"A-grade sets: expected > 0, got {grade_counts.get('A', 0)}")
    if grade_counts.get("S", 0) <= 0:
        issues.append(f"S-grade sets: expected > 0, got {grade_counts.get('S', 0)}")

    avadon = built.get("sets", {}).get("Avadon Breastplate")
    if not avadon or len(avadon) < 4:
        issues.append(f"Avadon Breastplate set: expected >= 4 craftable parts, got {avadon}")

    incomplete_b = _incomplete_b_sets(built)
    if len(incomplete_b) > 8:
        issues.append(f"B-grade incomplete sets (>8 with <4 parts): {len(incomplete_b)}")

    set_meta = built.get("setMeta") or {}
    for grade in ("A",):
        grade_sets = [
            name
            for name, meta in set_meta.items()
            if isinstance(meta, dict) and meta.get("grade") == grade
        ]
        if not grade_sets:
            continue
        missing_icon = sum(1 for name in grade_sets if not (set_meta[name] or {}).get("icon"))
        missing_effect = sum(
            1
            for name in grade_sets
            if not (set_meta[name] or {}).get("effect") and not (set_meta[name] or {}).get("effectRaw")
        )
        if missing_icon > len(grade_sets) // 2:
            issues.append(f"{grade}-grade setMeta: {missing_icon}/{len(grade_sets)} missing icon")
        if missing_effect > len(grade_sets) // 2:
            issues.append(f"{grade}-grade setMeta: {missing_effect}/{len(grade_sets)} missing effect")

        for name in grade_sets:
            meta = set_meta[name] or {}
            craftable = meta.get("craftableMemberIds") or []
            all_ids = meta.get("allMemberIds") or []
            if len(all_ids) < len(craftable):
                issues.append(f"{name}: allMemberIds shorter than craftableMemberIds")

    s_sets = [name for name, meta in set_meta.items() if isinstance(meta, dict) and meta.get("grade") == "S"]
    if s_sets:
        missing_s_icon = sum(1 for name in s_sets if not (set_meta[name] or {}).get("icon"))
        if missing_s_icon:
            issues.append(f"S-grade setMeta: {missing_s_icon}/{len(s_sets)} missing icon")
    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Build craft_catalog.json from wiki library")
    parser.add_argument("--check", action="store_true", help="Compare with existing output without writing")
    parser.add_argument("--dry-run", action="store_true", help="Build but do not write craft_catalog.json")
    parser.add_argument("-o", "--output", type=Path, default=OUT)
    args = parser.parse_args()

    built = build_catalog()
    grade_counts = _set_grade_counts(built)
    incomplete_b = _incomplete_b_sets(built)
    print(
        f"Built catalog: products={built['product_count']} variants={built['variant_count']} "
        f"items={len(built['items'])} sets={len(built.get('sets', {}))} "
        f"setMeta={len(built.get('setMeta', {}))} "
        f"by_grade={grade_counts} incomplete_B={len(incomplete_b)}"
    )

    set_issues = _check_sets(built)
    if set_issues:
        print("Set checks:")
        for issue in set_issues:
            print(f"  - {issue}")
    else:
        print("Set checks: OK")

    if args.output.exists():
        existing = json.loads(args.output.read_text(encoding="utf-8"))
        issues = _compare(existing, built)
        if issues:
            print("Check differences:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("Check: key metrics match existing catalog")
    elif args.check:
        print("Check skipped: no existing catalog file")

    if args.check or args.dry_run:
        return

    args.output.write_text(json.dumps(built, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
