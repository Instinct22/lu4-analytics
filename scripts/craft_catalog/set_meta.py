"""Build enriched set metadata for craft catalog."""
from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .set_parse import SetPageInfo

_VARIANT_KEYWORDS = ("leather", "robe", "tunic", "shirt", "mail")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _grade_for_set(set_name: str, craftable_ids: list[int], items: dict, page: SetPageInfo | None) -> str:
    if page and page.grade:
        return page.grade
    for pid in craftable_ids:
        item = items.get(str(pid)) or items.get(pid)
        if isinstance(item, dict) and item.get("grade"):
            return item["grade"]
    return "NG"


def _is_variant_set(name: str, craftable_count: int, all_count: int) -> bool:
    lower = (name or "").lower()
    if craftable_count <= 1 and any(keyword in lower for keyword in _VARIANT_KEYWORDS):
        return True
    return craftable_count <= 1 and all_count <= 2


def _index_set_pages(set_pages: list[SetPageInfo]) -> dict[str, SetPageInfo]:
    indexed: dict[str, SetPageInfo] = {}
    for page in sorted(set_pages, key=lambda row: len(row.members), reverse=True):
        if page.is_pvp or not page.name:
            continue
        indexed.setdefault(page.name, page)
    return indexed


def build_set_meta(
    set_pages: list[SetPageInfo],
    sets_map: dict[str, list[int]],
    items: dict,
    craftable_ids: set[int],
) -> dict[str, dict]:
    """Merge wiki set pages with craftable membership into setMeta records."""
    pages_by_name = _index_set_pages(set_pages)
    meta: dict[str, dict] = {}

    for set_name, craftable_members in sets_map.items():
        craftable_member_ids = sorted({int(pid) for pid in craftable_members})
        page = pages_by_name.get(set_name)
        all_member_ids = sorted({mid for mid, _ in page.members}) if page else craftable_member_ids
        member_names = {str(mid): mname for mid, mname in page.members} if page else {}

        entry: dict = {
            "name": set_name,
            "grade": _grade_for_set(set_name, craftable_member_ids, items, page),
            "pvp": bool(page.is_pvp) if page else False,
            "canonical": True,
            "craftableMemberIds": craftable_member_ids,
            "allMemberIds": all_member_ids,
            "memberNames": member_names,
        }

        if page:
            if page.set_id is not None:
                entry["id"] = page.set_id
            if page.slug:
                entry["slug"] = page.slug
            if page.url:
                entry["url"] = page.url
            if page.icon:
                entry["icon"] = page.icon
            if page.effect_lines:
                entry["effect"] = page.effect_lines
            if page.effect_raw:
                entry["effectRaw"] = page.effect_raw

        if _is_variant_set(set_name, len(craftable_member_ids), len(all_member_ids)):
            entry["canonical"] = False

        meta[set_name] = entry

    return meta


def _resolve_sealed_display_roster(
    page: SetPageInfo | None,
    craftable_member_ids: list[int],
    craftable_ids: set[int],
    items: dict,
) -> tuple[list[int], dict[str, str]]:
    """Map wiki set roster to sealed craftable item ids for UI display."""
    from .categories import _primary_piece_rank, _resolve_craftable_member, _sealed_name_index

    craftable_set = set(craftable_member_ids)

    def _item_name(pid: int) -> str:
        item = items.get(str(pid)) or items.get(pid)
        return (item or {}).get("name") or ""

    if page:
        sealed_index = _sealed_name_index(items, craftable_ids)
        page_members = list(page.members)
        if page.name and not any(name == page.name for _, name in page_members):
            page_members.insert(0, (-1, page.name))
        resolved_rows: list[tuple[int, str, tuple[int, str]]] = []
        for member_id, member_name in page_members:
            sealed_id = _resolve_craftable_member(member_id, member_name, craftable_ids, sealed_index)
            if sealed_id is None or sealed_id not in craftable_set:
                continue
            if any(row[0] == sealed_id for row in resolved_rows):
                continue
            resolved_rows.append((sealed_id, member_name, _primary_piece_rank(member_name)))
        if resolved_rows:
            resolved_rows.sort(key=lambda row: row[2])
            member_ids = [row[0] for row in resolved_rows]
            names = {str(pid): _item_name(pid) for pid in member_ids if _item_name(pid)}
            return member_ids, names

    member_ids = sorted(craftable_member_ids)
    names = {str(pid): _item_name(pid) for pid in member_ids if _item_name(pid)}
    return member_ids, names


def _slug_from_name(name: str) -> str:
    slug = _SLUG_RE.sub("-", (name or "").lower()).strip("-")
    return slug or "set"


def enrich_set_meta(
    meta: dict[str, dict],
    items: dict,
    wiki_root: Path,
    set_pages: list[SetPageInfo] | None = None,
    craftable_ids: set[int] | None = None,
) -> None:
    """Fill missing icons and sealed display rosters from local wiki."""
    from .wiki_parse import item_icon_from_wiki

    pages_by_name = _index_set_pages(set_pages or [])
    craftable = craftable_ids or set()

    for set_name, entry in meta.items():
        if not entry.get("icon"):
            for pid in entry.get("craftableMemberIds") or []:
                icon = item_icon_from_wiki(wiki_root, int(pid))
                if icon:
                    entry["icon"] = icon
                    break

        page = pages_by_name.get(set_name)
        grade = entry.get("grade") or ""
        craftable_members = entry.get("craftableMemberIds") or []
        if craftable_members and grade in ("S", "A", "B", "C", "D"):
            member_ids, names = _resolve_sealed_display_roster(
                page, craftable_members, craftable, items
            )
            if member_ids:
                entry["allMemberIds"] = member_ids
                if names:
                    entry["memberNames"] = names

        if grade == "S":
            if entry.get("id") is None and craftable_members:
                entry["id"] = int(craftable_members[0])
            if not entry.get("slug"):
                entry["slug"] = _slug_from_name(set_name)
            if not entry.get("url") and entry.get("slug"):
                entry["url"] = (
                    f"/lu4/set/{entry.get('id', craftable_members[0] if craftable_members else 0)}-{entry['slug']}"
                )
