"""Self-contained items encyclopedia: normalize records, no lu4/l2map paths."""
from __future__ import annotations

import copy
import re
from typing import Any

from craft_catalog.armor_sets import rebuild_armor_sets
from craft_catalog.item_variants import merge_gear_variants

LU4_ITEM_RE = re.compile(r"^/lu4/item/(\d+)(?:-([^/?#]+))?")
LU4_NPC_RE = re.compile(r"^/lu4/npc/(\d+)(?:-([^/?#]+))?")
LU4_SET_RE = re.compile(r"^/lu4/set/(\d+)(?:-([^/?#]+))?")
LU4_SKILL_RE = re.compile(r"^/lu4/skill/(\d+)(?:-([^/?#]+))?")
LU4_QUEST_RE = re.compile(r"^/lu4/quest/(\d+)(?:-([^/?#]+))?")

_STRIP_KEYS = frozenset({"provenance", "stats_raw"})


def _slug_from_lu4_url(url: str | None, pattern: re.Pattern[str]) -> tuple[int | None, str | None]:
    if not url:
        return None, None
    match = pattern.search(url.strip())
    if not match:
        return None, None
    iid = int(match.group(1))
    slug = match.group(2) if match.lastindex and match.lastindex >= 2 else None
    return iid, slug


def _ref(entity_type: str, entity_id: int | None, slug: str | None = None) -> dict[str, Any] | None:
    if entity_id is None:
        return None
    out: dict[str, Any] = {"type": entity_type, "id": entity_id}
    if slug:
        out["slug"] = slug
    return out


def normalize_source_row(row: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in row.items() if k not in ("npc_url", "item_url")}
    npc_id = out.get("npc_id")
    if npc_id is None and row.get("npcId") is not None:
        npc_id = row["npcId"]
        out["npc_id"] = npc_id
    if not out.get("npc_id") and row.get("npc_url"):
        parsed_id, _ = _slug_from_lu4_url(str(row["npc_url"]), LU4_NPC_RE)
        if parsed_id is not None:
            out["npc_id"] = parsed_id
    return out


def normalize_link_entry(entry: dict[str, Any]) -> dict[str, Any]:
    out = dict(entry)
    url = out.pop("url", None)
    kind = out.get("kind") or "item"
    if url:
        patterns = {
            "item": LU4_ITEM_RE,
            "npc": LU4_NPC_RE,
            "quest": LU4_QUEST_RE,
            "skill": LU4_SKILL_RE,
            "set": LU4_SET_RE,
        }
        iid, slug = _slug_from_lu4_url(url, patterns.get(kind, LU4_ITEM_RE))
        if iid is not None:
            out["id"] = iid
        if slug:
            out["slug"] = slug
    return out


def normalize_craft_variant(variant: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(variant)
    recipe_url = out.pop("recipe_url", None)
    if recipe_url and not out.get("recipe_id"):
        rid, _ = _slug_from_lu4_url(recipe_url, LU4_ITEM_RE)
        if rid is not None:
            out["recipe_id"] = rid
    return out


def normalize_item(item: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(item)
    for key in _STRIP_KEYS:
        out.pop(key, None)

    if out.get("url"):
        _, slug = _slug_from_lu4_url(str(out["url"]), LU4_ITEM_RE)
        if slug and not out.get("slug"):
            out["slug"] = slug
    out.pop("url", None)

    if out.get("weight") is not None and isinstance(out.get("stats"), dict):
        if "weight" not in out["stats"]:
            out["stats"]["weight"] = out["weight"]

    for field in ("drops", "spoils"):
        rows = out.get(field)
        if isinstance(rows, list):
            out[field] = [normalize_source_row(r) for r in rows if isinstance(r, dict)]

    craft = out.get("craft")
    if isinstance(craft, dict) and isinstance(craft.get("variants"), list):
        craft["variants"] = [normalize_craft_variant(v) for v in craft["variants"] if isinstance(v, dict)]

    links = out.get("links")
    if isinstance(links, dict):
        normalized_links: dict[str, Any] = {}
        for key, val in links.items():
            if key == "set" and isinstance(val, dict):
                set_url = val.get("url")
                sid, sslug = _slug_from_lu4_url(set_url, LU4_SET_RE) if set_url else (val.get("id"), None)
                normalized_links["set"] = _ref("set", sid, sslug) or val
            elif isinstance(val, list):
                normalized_links[key] = [normalize_link_entry(x) for x in val if isinstance(x, dict)]
            else:
                normalized_links[key] = val
        out["links"] = normalized_links

    item_set = out.get("set")
    if isinstance(item_set, dict):
        cleaned_set = dict(item_set)
        set_url = cleaned_set.pop("url", None)
        sid, sslug = _slug_from_lu4_url(set_url, LU4_SET_RE) if set_url else (cleaned_set.get("id"), None)
        if sid is not None:
            cleaned_set["id"] = sid
        if sslug and not cleaned_set.get("slug"):
            cleaned_set["slug"] = sslug
        out["set"] = cleaned_set

    sealed = out.get("sealed_group")
    if isinstance(sealed, dict) and isinstance(sealed.get("variants"), list):
        for variant in sealed["variants"]:
            if isinstance(variant, dict):
                variant.pop("url", None)

    _apply_npc_buy_fields(out)
    return out


def _apply_npc_buy_fields(item: dict[str, Any]) -> None:
    try:
        from npc_prices import apply_npc_buy_to_item
    except ImportError:
        return
    apply_npc_buy_to_item(item)


def build_craft_bundle(payload: dict[str, Any]) -> dict[str, Any]:
    """Derive craft catalog shape from encyclopedia items."""
    items = payload.get("items") or {}
    by_product: dict[str, list] = {}
    craft_items: dict[str, dict] = {}
    item_icons: dict[str, str] = {}
    referenced: set[int] = set()

    def collect_tree_ids(nodes: list) -> None:
        for node in nodes or []:
            if not isinstance(node, dict):
                continue
            mid = node.get("id")
            if isinstance(mid, int):
                referenced.add(mid)
            collect_tree_ids(node.get("children") or [])

    for raw_id, item in items.items():
        if not isinstance(item, dict):
            continue
        iid = item.get("id") if isinstance(item.get("id"), int) else int(raw_id)
        craft = item.get("craft") or {}
        variants = craft.get("variants") or []
        if variants:
            by_product[str(iid)] = variants
            referenced.add(iid)
            for variant in variants:
                if isinstance(variant, dict):
                    rid = variant.get("recipe_id")
                    if isinstance(rid, int):
                        referenced.add(rid)
                    collect_tree_ids(variant.get("tree") or [])

    for raw_id, item in items.items():
        if not isinstance(item, dict):
            continue
        iid = item.get("id") if isinstance(item.get("id"), int) else int(raw_id)
        if iid not in referenced and item.get("section") != "gear":
            continue
        if iid not in referenced and not item.get("craft", {}).get("craftable"):
            continue
        if iid not in referenced:
            continue
        craft_items[str(iid)] = {
            "id": iid,
            "name": item.get("name"),
            "grade": item.get("grade"),
            "type": item.get("type"),
            "category": item.get("category"),
            "set_name": item.get("set_name"),
            "npc_sell": item.get("npc_sell"),
            "npc_buy": item.get("npc_buy"),
            "is_recipe_scroll": item.get("is_recipe_scroll"),
            "description": item.get("description") or item.get("effects"),
            "stats": item.get("stats"),
            "icon": item.get("icon"),
        }
        if item.get("icon"):
            item_icons[str(iid)] = item["icon"]

    embedded = payload.get("craft") or {}
    return {
        "generated_at": payload.get("generated_at"),
        "product_count": len(by_product),
        "variant_count": sum(len(v) for v in by_product.values()),
        "items": craft_items or embedded.get("items") or {},
        "byProduct": by_product or embedded.get("by_product") or embedded.get("byProduct") or {},
        "categories": embedded.get("categories") or {},
        "sets": embedded.get("sets") or {},
        "setMeta": embedded.get("set_meta") or embedded.get("setMeta") or {},
        "itemIcons": item_icons or embedded.get("itemIcons") or {},
    }


def normalize_by_product(by_product: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for pid, variants in by_product.items():
        if not isinstance(variants, list):
            out[pid] = variants
            continue
        out[pid] = [normalize_craft_variant(v) for v in variants if isinstance(v, dict)]
    return out


def normalize_set_meta(meta: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, entry in meta.items():
        if not isinstance(entry, dict):
            out[key] = entry
            continue
        cleaned = dict(entry)
        url = cleaned.pop("url", None)
        if url and not cleaned.get("slug"):
            _, slug = _slug_from_lu4_url(url, LU4_SET_RE)
            if slug:
                cleaned["slug"] = slug
        out[key] = cleaned
    return out


def finalize_payload(payload: dict[str, Any], *, craft_catalog: dict | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "library": {
            "id": "items_encyclopedia",
            "version": 1,
            "description": "Self-contained Lu4 Analytics item library",
        },
        "generated_at": payload.get("generated_at"),
        "item_count": payload.get("item_count"),
        "section_counts": payload.get("section_counts") or {},
    }

    if craft_catalog:
        raw_meta = craft_catalog.get("setMeta") or {}
        out["craft"] = {
            "categories": craft_catalog.get("categories") or {},
            "sets": craft_catalog.get("sets") or {},
            "set_meta": normalize_set_meta(raw_meta),
            "by_product": normalize_by_product(craft_catalog.get("byProduct") or {}),
        }

    if payload.get("craft"):
        incoming = dict(payload["craft"])
        if craft_catalog:
            # Fresh catalog meta wins over stale embedded craft trees.
            incoming.pop("categories", None)
            incoming.pop("sets", None)
            incoming.pop("set_meta", None)
            incoming.pop("setMeta", None)
        out["craft"] = {**(out.get("craft") or {}), **incoming}

    items_in: dict[str, Any] = payload.get("items") or {}
    items_out: dict[str, Any] = {}
    counts = {"gear": 0, "other": 0, "excluded": 0}

    craft_by_product = normalize_by_product((craft_catalog or {}).get("byProduct") or {})
    if payload.get("craft", {}).get("by_product"):
        craft_by_product = normalize_by_product(payload["craft"]["by_product"]) or craft_by_product

    for raw_id, item in items_in.items():
        if not isinstance(item, dict):
            continue
        normalized = normalize_item(item)
        sec = normalized.get("section") or "other"
        counts[sec] = counts.get(sec, 0) + 1
        items_out[str(normalized.get("id", raw_id))] = normalized

    merge_gear_variants(items_out, craft_by_product=craft_by_product)

    if craft_catalog:
        catalog_items = craft_catalog.get("items") or {}
        for raw_id, item in items_out.items():
            if not isinstance(item, dict):
                continue
            iid = item.get("id") if isinstance(item.get("id"), int) else int(raw_id)
            ci = catalog_items.get(str(iid)) or catalog_items.get(iid)
            if isinstance(ci, dict) and ci.get("category"):
                item["category"] = ci["category"]

    for item in items_out.values():
        if isinstance(item, dict):
            _apply_npc_buy_fields(item)

    counts = {"gear": 0, "other": 0, "excluded": 0}
    for item in items_out.values():
        if isinstance(item, dict):
            sec = item.get("section") or "other"
            counts[sec] = counts.get(sec, 0) + 1

    out["items"] = items_out
    out["item_count"] = len(items_out)
    out["section_counts"] = counts

    craft_bundle = build_craft_bundle(out)
    out.setdefault("craft", {})
    out["craft"].setdefault("by_product", normalize_by_product(craft_bundle.get("byProduct") or {}))
    out["craft"].setdefault("categories", craft_bundle.get("categories") or {})
    out["craft"].setdefault("sets", craft_bundle.get("sets") or {})
    out["craft"]["by_product"] = normalize_by_product(out["craft"].get("by_product") or {})
    raw_set_meta = craft_bundle.get("setMeta") or out["craft"].get("set_meta") or {}
    out["craft"]["set_meta"] = normalize_set_meta(raw_set_meta if isinstance(raw_set_meta, dict) else {})

    # Rosters must be derived after variants are merged so that shared pieces
    # resolve to the canonical (sealed) catalog entry.
    sets, set_meta = rebuild_armor_sets(
        items_out,
        craftable_ids={int(pid) for pid in out["craft"].get("by_product") or {}},
        existing_sets=out["craft"].get("sets") or {},
        existing_meta=out["craft"].get("set_meta") or {},
    )
    out["craft"]["sets"] = sets
    out["craft"]["set_meta"] = normalize_set_meta(set_meta)

    return out
