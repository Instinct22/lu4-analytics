"""Category rules for craft catalog items (single source of truth)."""
from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .set_parse import SetPageInfo

GRADE_ORDER = ("NG", "D", "C", "B", "A", "S")

_ARMOR_SET_SLOT_SUFFIXES = (
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
)

_PRIMARY_PIECE_PRIORITY = {
    "Breastplate": 0,
    "Robe": 1,
    "Leather Armor": 2,
    "Gaiters": 3,
    "Leggings": 4,
    "Helmet": 5,
    "Circlet": 6,
    "Gauntlets": 7,
    "Gloves": 8,
    "Boots": 9,
    "Shield": 10,
}

_WEAPON_SUB = {
    "sword": "swords",
    "dagger": "daggers",
    "bow": "bows",
    "blunt": "blunts",
    "polearm": "poles",
    "fist": "fists",
    "misc.": "misc",
    "misc": "misc",
}

_ARMOR_NONE_SLOT = {
    "boots": "boots",
    "gloves": "gloves",
    "helmet": "helmets",
    "shield": "shields",
    "hair accessory": "misc",
}


def resolve_category(item_type: str, name: str = "") -> str:
    """Map wiki item type (+ name heuristics) to catalog category path."""
    parts = [p.strip() for p in (item_type or "").split(" / ") if p.strip()]
    if not parts:
        return "other/misc"

    head = parts[0].lower()
    if head == "weapon" and len(parts) >= 2:
        sub = _WEAPON_SUB.get(parts[1].lower(), "misc")
        return f"weapons/{sub}"

    if head == "armor":
        if len(parts) >= 2 and parts[1] == "Heavy":
            return "armors/heavy"
        if len(parts) >= 2 and parts[1] == "Light":
            return "armors/light"
        if len(parts) >= 2 and parts[1] == "Robe":
            return "armors/magic"
        slot = parts[2].lower() if len(parts) >= 3 else ""
        if parts[1] == "None" and slot in _ARMOR_NONE_SLOT:
            return f"armors/{_ARMOR_NONE_SLOT[slot]}"
        return "armors/misc"

    if head == "accessory":
        if "sealed" in (name or "").lower():
            return "other/sealed"
        return "other/jewelry"

    if head == "other":
        sub = parts[1].lower() if len(parts) >= 2 else ""
        if sub == "material":
            return "materials/material"
        if sub == "recipe":
            return "other/recipes"
        if sub == "potion":
            return "other/consumables"
        if sub in {"arrow", "dyes", "elixir"}:
            return "other/misc"
        lowered = (name or "").lower()
        if "soulshot" in lowered or "spiritshot" in lowered:
            return "other/soulshots"
        return "other/misc"

    if head == "quest item":
        return "other/misc"

    if head == "money":
        return "other/misc"

    lowered = (name or "").lower()
    if "soulshot" in lowered or "spiritshot" in lowered:
        return "other/soulshots"
    return "other/misc"


def category_top_level(category: str) -> str:
    return (category or "other/misc").split("/", 1)[0]


def _grade_sort_key(grade: str) -> tuple[int, str]:
    try:
        return (GRADE_ORDER.index(grade), grade)
    except ValueError:
        return (len(GRADE_ORDER), grade)


def _sealed_name_index(items: dict, craftable_ids: set[int]) -> dict[str, int]:
    index: dict[str, int] = {}
    for raw_id, item in items.items():
        if not isinstance(item, dict):
            continue
        try:
            pid = int(raw_id)
        except (TypeError, ValueError):
            continue
        if pid not in craftable_ids:
            continue
        name = item.get("name") or ""
        if name.startswith("Sealed "):
            index[name[7:].lower()] = pid
    return index


def _resolve_craftable_member(
    member_id: int,
    member_name: str,
    craftable_ids: set[int],
    sealed_index: dict[str, int],
) -> int | None:
    if member_id in craftable_ids:
        return member_id
    if member_name:
        sealed_id = sealed_index.get(member_name.lower())
        if sealed_id is not None:
            return sealed_id
    return None


def _armor_set_prefix(piece_name: str) -> str:
    for suffix in _ARMOR_SET_SLOT_SUFFIXES:
        if piece_name.endswith(f" {suffix}"):
            return piece_name[: -len(suffix)].strip()
    return piece_name


def _primary_piece_rank(piece_name: str) -> tuple[int, str]:
    for suffix, rank in _PRIMARY_PIECE_PRIORITY.items():
        if piece_name.endswith(f" {suffix}"):
            return (rank, piece_name)
    return (99, piece_name)


def _build_sealed_armor_fallback_sets(
    items: dict,
    craftable_ids: set[int],
    assigned_ids: set[int],
) -> dict[str, list[int]]:
    """Group unassigned sealed armor when wiki set pages are missing (e.g. S-grade)."""
    groups: dict[str, list[tuple[int, str, tuple[int, str]]]] = defaultdict(list)
    for raw_id in craftable_ids:
        if raw_id in assigned_ids:
            continue
        item = items.get(str(raw_id)) or items.get(raw_id)
        if not isinstance(item, dict):
            continue
        name = item.get("name") or ""
        if not name.startswith("Sealed "):
            continue
        category = item.get("category") or resolve_category(item.get("type") or "", name)
        if not category.startswith("armors/"):
            continue
        base_name = name[7:]
        prefix = _armor_set_prefix(base_name)
        groups[prefix].append((raw_id, base_name, _primary_piece_rank(base_name)))

    fallback: dict[str, list[int]] = {}
    for members in groups.values():
        if len(members) < 2:
            continue
        members.sort(key=lambda row: row[2])
        set_name = members[0][1]
        fallback[set_name] = sorted({row[0] for row in members})
    return fallback


def build_sets(
    set_pages: list[SetPageInfo],
    craftable_product_ids: set[int],
    items: dict,
    fallback_by_item: dict[int, str] | None = None,
) -> dict[str, list[int]]:
    """Build armor set membership from wiki set pages (craftable parts only)."""
    sealed_index = _sealed_name_index(items, craftable_product_ids)
    sets_map: dict[str, set[int]] = defaultdict(set)
    item_to_set: dict[int, str] = {}

    ordered_pages = sorted(
        set_pages,
        key=lambda page: len(page.members),
        reverse=True,
    )
    for page in ordered_pages:
        if page.is_pvp or not page.name:
            continue
        page_members = list(page.members)
        if page.name and not any(name == page.name for _, name in page_members):
            page_members.insert(0, (-1, page.name))
        for member_id, member_name in page_members:
            craftable_id = _resolve_craftable_member(
                member_id,
                member_name,
                craftable_product_ids,
                sealed_index,
            )
            if craftable_id is None:
                continue
            if craftable_id in item_to_set:
                continue
            sets_map[page.name].add(craftable_id)
            item_to_set[craftable_id] = page.name

    for raw_pid, set_name in (fallback_by_item or {}).items():
        if not set_name:
            continue
        try:
            pid = int(raw_pid)
        except (TypeError, ValueError):
            continue
        if pid not in craftable_product_ids or pid in item_to_set:
            continue
        sets_map[set_name].add(pid)
        item_to_set[pid] = set_name

    for set_name, member_ids in _build_sealed_armor_fallback_sets(
        items, craftable_product_ids, set(item_to_set)
    ).items():
        if set_name in sets_map:
            continue
        for pid in member_ids:
            if pid in item_to_set:
                continue
            sets_map[set_name].add(pid)
            item_to_set[pid] = set_name

    return {name: sorted(ids) for name, ids in sets_map.items() if ids}


def apply_set_names(items: dict, sets_map: dict[str, list[int]]) -> None:
    """Propagate set names onto craftable items for API consistency."""
    id_to_name: dict[int, str] = {}
    for set_name, member_ids in sets_map.items():
        for member_id in member_ids:
            id_to_name[member_id] = set_name
    for raw_id, item in items.items():
        if not isinstance(item, dict):
            continue
        try:
            pid = int(raw_id)
        except (TypeError, ValueError):
            continue
        if pid in id_to_name:
            item["set_name"] = id_to_name[pid]


def apply_categories(payload: dict) -> None:
    """Set item.category from type/name and rebuild categories tree from byProduct."""
    items: dict = payload.get("items") or {}
    for item in items.values():
        if not isinstance(item, dict):
            continue
        item["category"] = resolve_category(item.get("type") or "", item.get("name") or "")

    by_product = payload.get("byProduct") or {}
    categories: dict[str, dict] = {
        "weapons": defaultdict(lambda: defaultdict(list)),
        "armors": defaultdict(lambda: defaultdict(list)),
        "materials": defaultdict(list),
        "other": defaultdict(list),
    }

    for raw_pid in by_product:
        try:
            pid = int(raw_pid)
        except (TypeError, ValueError):
            continue
        item = items.get(str(pid)) or items.get(pid)
        if not item:
            continue
        category = item.get("category") or "other/misc"
        top, _, sub = category.partition("/")
        grade = item.get("grade") or "NG"
        if top in ("weapons", "armors") and sub:
            categories[top][sub][grade].append(pid)
        elif top == "materials" and sub:
            categories["materials"][sub].append(pid)
        elif top == "other" and sub:
            categories["other"][sub].append(pid)

    payload["categories"] = {
        "weapons": {
            sub: {g: sorted(set(ids)) for g, ids in grades.items()}
            for sub, grades in categories["weapons"].items()
        },
        "armors": {
            sub: {g: sorted(set(ids)) for g, ids in grades.items()}
            for sub, grades in categories["armors"].items()
        },
        "materials": {sub: sorted(set(ids)) for sub, ids in categories["materials"].items()},
        "other": {sub: sorted(set(ids)) for sub, ids in categories["other"].items()},
    }
