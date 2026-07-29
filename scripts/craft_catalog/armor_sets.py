"""Rebuild armour set rosters from item set names and merged variant links.

The wiki set pages are not part of the local dataset, so membership is derived
from the ``set_name`` each armour piece carries. That field is authoritative:
shared pieces expose one entry per armour class (``Tallum Gloves Heavy Armor``
belongs to ``Tallum Plate Armor``, the light version to ``Tallum Leather Armor``),
which is exactly what is needed to place a piece in several sets at once.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

_FOUNDATION_RE = re.compile(r"\s+(?:NG|D|C|B|A|S)?\s*Foundation$", re.I)
_PVP_RE = re.compile(r"\{\s*pvp\s*\}", re.I)

# Display order of the pieces inside a set.
SLOT_ORDER: tuple[str, ...] = (
    "full body",
    "upper body",
    "lower body",
    "helmet",
    "gloves",
    "boots",
    "shield",
)


def _slot(type_str: str | None) -> str:
    parts = [part.strip() for part in (type_str or "").split("/") if part.strip()]
    return parts[-1].lower() if parts else ""


def _slot_rank(slot: str) -> tuple[int, str]:
    try:
        return (SLOT_ORDER.index(slot), slot)
    except ValueError:
        return (len(SLOT_ORDER), slot)


def normalize_set_name(raw: str | None) -> str | None:
    """Fold `... A Foundation` into the base set; drop PvP rosters."""
    name = (raw or "").strip()
    if not name or _PVP_RE.search(name):
        return None
    name = _FOUNDATION_RE.sub("", name).strip()
    return name or None


def _terminal_visible(iid: int, items: dict[int, dict[str, Any]]) -> int | None:
    seen: set[int] = set()
    current: int | None = iid
    while current is not None and current not in seen:
        seen.add(current)
        item = items.get(current)
        if item is None:
            return None
        if item.get("section") != "excluded":
            return current
        nxt = item.get("variant_of")
        current = nxt if isinstance(nxt, int) else None
    return None


def piece_label(item: dict[str, Any]) -> str:
    """Human-friendly piece name; the `Sealed ` prefix is noise inside a roster."""
    name = (item.get("name") or "").strip()
    if name.startswith("Sealed "):
        stripped = name[7:].strip()
        if stripped:
            return stripped
    return name


def _pick_member(ids: list[int], items: dict[int, dict[str, Any]], craftable_ids: set[int]) -> int:
    """One piece per slot: prefer the craftable (sealed) catalog entry."""

    def score(iid: int) -> tuple[bool, bool, int]:
        name = (items[iid].get("name") or "")
        return (iid not in craftable_ids, not name.startswith("Sealed "), iid)

    return min(ids, key=score)


def _grade_for(member_ids: list[int], items: dict[int, dict[str, Any]]) -> str:
    grades = Counter(
        (items[iid].get("grade") or "").strip().upper()
        for iid in member_ids
        if (items[iid].get("grade") or "").strip()
    )
    grades.pop("NG", None)
    if grades:
        return grades.most_common(1)[0][0]
    return "NG"


def rebuild_armor_sets(
    items: dict[str, Any] | dict[int, Any],
    *,
    craftable_ids: set[int],
    existing_sets: dict[str, Any] | None = None,
    existing_meta: dict[str, Any] | None = None,
) -> tuple[dict[str, list[int]], dict[str, dict[str, Any]]]:
    """Return (sets, set_meta) with rosters derived from the item library."""
    typed: dict[int, dict[str, Any]] = {}
    for raw_id, item in (items or {}).items():
        if not isinstance(item, dict):
            continue
        iid = item.get("id") if isinstance(item.get("id"), int) else int(raw_id)
        typed[iid] = item

    # set name -> slot -> candidate canonical ids
    rosters: dict[str, dict[str, list[int]]] = {}
    for iid, item in typed.items():
        if not (item.get("type") or "").lower().startswith("armor"):
            continue
        set_name = normalize_set_name(item.get("set_name"))
        if not set_name:
            continue
        canonical = _terminal_visible(iid, typed)
        if canonical is None:
            continue
        slot = _slot(typed[canonical].get("type") or item.get("type"))
        if not slot:
            continue
        bucket = rosters.setdefault(set_name, {}).setdefault(slot, [])
        if canonical not in bucket:
            bucket.append(canonical)

    sets: dict[str, list[int]] = dict(existing_sets or {})
    meta: dict[str, dict[str, Any]] = {
        name: dict(entry) for name, entry in (existing_meta or {}).items() if isinstance(entry, dict)
    }

    for set_name, slots in rosters.items():
        ordered_slots = sorted(slots, key=_slot_rank)
        member_ids = [_pick_member(slots[slot], typed, craftable_ids) for slot in ordered_slots]
        # A slot may resolve to a piece already picked for another slot.
        deduped: list[int] = []
        for iid in member_ids:
            if iid not in deduped:
                deduped.append(iid)
        if not deduped:
            continue

        entry = meta.get(set_name) or {}
        entry = dict(entry)
        entry["name"] = set_name
        entry["pvp"] = False
        entry["canonical"] = len(deduped) >= 2
        entry["craftableMemberIds"] = sorted(iid for iid in deduped if iid in craftable_ids)
        entry["allMemberIds"] = deduped
        entry["memberNames"] = {str(iid): piece_label(typed[iid]) for iid in deduped}
        entry["grade"] = _grade_for(deduped, typed)
        meta[set_name] = entry
        sets[set_name] = sorted(deduped)

    # Sets without a set_name source (S-grade rosters built from sealed pieces)
    # keep their membership but still get consistent ordering and labels.
    for set_name, entry in meta.items():
        if set_name in rosters:
            continue
        member_ids = [
            iid
            for iid in (entry.get("allMemberIds") or sets.get(set_name) or [])
            if isinstance(iid, int) and iid in typed
        ]
        if not member_ids:
            continue
        member_ids.sort(key=lambda iid: _slot_rank(_slot(typed[iid].get("type"))))
        entry["allMemberIds"] = member_ids
        entry["memberNames"] = {str(iid): piece_label(typed[iid]) for iid in member_ids}

    return sets, meta
