"""Classify items into gear / other / excluded and link sealed variants."""
from __future__ import annotations

import re
from typing import Any

_ARMOR_TYPE_MAP = {
    "heavy": "heavy",
    "light": "light",
    "robe": "magic",
}


def is_excluded(name: str, grade: str, item_type: str) -> bool:
    lowered_name = (name or "").lower()
    lowered_type = (item_type or "").lower()
    if lowered_type.startswith("quest item"):
        return True
    if "shadow" in lowered_name:
        return True
    if (grade or "").lower() == "common":
        return True
    return False


def is_gear_type(item_type: str) -> bool:
    parts = [p.strip().lower() for p in (item_type or "").split(" / ") if p.strip()]
    if not parts:
        return False
    return parts[0] in {"weapon", "armor", "accessory"}


def classify_section(name: str, grade: str, item_type: str, *, dual_ids: set[int] | None = None, item_id: int | None = None) -> str:
    if is_excluded(name, grade, item_type):
        return "excluded"
    if item_id is not None and dual_ids and item_id in dual_ids:
        return "gear"
    if is_gear_type(item_type):
        return "gear"
    return "other"


def armor_variant_type(item_type: str) -> str | None:
    parts = [p.strip() for p in (item_type or "").split(" / ") if p.strip()]
    if len(parts) < 2 or parts[0].lower() != "armor":
        return None
    return _ARMOR_TYPE_MAP.get(parts[1].lower())


def sealed_base_name(name: str) -> str | None:
    if not name.startswith("Sealed "):
        return None
    return name[7:].strip()


def build_sealed_groups(items: dict[int, dict[str, Any]]) -> None:
    """Mutate items with sealedGroup and variants fields."""
    by_base: dict[str, list[int]] = {}
    sealed_by_base: dict[str, int] = {}

    for iid, item in items.items():
        name = item.get("name") or ""
        base = sealed_base_name(name)
        if base:
            sealed_by_base[base.lower()] = iid
            continue
        if not is_gear_type(item.get("type") or ""):
            continue
        prefix = _armor_set_prefix(name)
        by_base.setdefault(prefix.lower(), []).append(iid)

    for iid, item in items.items():
        name = item.get("name") or ""
        base = sealed_base_name(name)
        if base:
            variants: list[dict[str, Any]] = []
            for uid in by_base.get(base.lower(), []):
                other = items[uid]
                vtype = armor_variant_type(other.get("type") or "")
                variants.append(
                    {
                        "id": uid,
                        "name": other.get("name"),
                        "armor_type": vtype,
                        "grade": other.get("grade"),
                        "url": other.get("url"),
                    }
                )
            item["sealed_group"] = {
                "base_name": base,
                "sealed_id": iid,
                "variants": sorted(variants, key=lambda v: (v.get("armor_type") or "", v.get("name") or "")),
            }
            continue

        if not is_gear_type(item.get("type") or ""):
            continue
        prefix = _armor_set_prefix(name)
        sealed_id = sealed_by_base.get(prefix.lower()) or sealed_by_base.get(name.lower())
        if sealed_id and sealed_id != iid:
            item["sealed_group"] = {
                "base_name": prefix,
                "sealed_id": sealed_id,
                "variants": [],
            }

    for iid, item in items.items():
        group = item.get("sealed_group")
        if not group or group.get("variants"):
            continue
        base = group.get("base_name") or ""
        variants = []
        for uid in by_base.get(base.lower(), []):
            if uid == iid:
                continue
            other = items[uid]
            variants.append(
                {
                    "id": uid,
                    "name": other.get("name"),
                    "armor_type": armor_variant_type(other.get("type") or ""),
                    "grade": other.get("grade"),
                    "url": other.get("url"),
                }
            )
        group["variants"] = sorted(variants, key=lambda v: (v.get("armor_type") or "", v.get("name") or ""))


_ARMOR_SUFFIXES = (
    "Leather Armor",
    "Leather Gloves",
    "Leather Boots",
    "Leather Helmet",
    "Breastplate",
    "Gaiters",
    "Gauntlets",
    "Gloves",
    "Boots",
    "Shield",
    "Helmet",
    "Robe",
    "Circlet",
    "Leggings",
    "Stockings",
    "Tunic",
)


def _armor_set_prefix(piece_name: str) -> str:
    for suffix in _ARMOR_SUFFIXES:
        if piece_name.endswith(f" {suffix}"):
            return piece_name[: -len(suffix)].strip()
    return piece_name


def other_subcategory(item_type: str, name: str, category: str | None = None) -> str:
    if category:
        top, _, sub = category.partition("/")
        if top == "other" and sub:
            return sub
        if top == "materials":
            return "materials"
    parts = [p.strip().lower() for p in (item_type or "").split(" / ") if p.strip()]
    if not parts:
        return "misc"
    if parts[0] == "other":
        return parts[1] if len(parts) > 1 else "misc"
    if parts[0] == "money":
        return "money"
    lowered = (name or "").lower()
    if "soulshot" in lowered or "spiritshot" in lowered:
        return "soulshots"
    return "misc"
