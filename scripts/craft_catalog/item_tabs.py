"""Parse item page tabs: drop, spoil, enchant, restrictions, links."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None  # type: ignore

from .wiki_parse import ITEM_ID_RE, NPC_ID_RE, _clean_text, _parse_int, _require_bs4

RESTRICTION_KEYS = {
    "private warehouse": "private_warehouse",
    "clan warehouse": "clan_warehouse",
    "transfer within game account": "transfer_within_account",
    "trade": "trade",
    "drop": "drop",
    "private store": "private_store",
    "enchant": "enchant",
    "attribute": "attribute",
    "olympiad use": "olympiad_use",
}


def _chance_val(chance: str) -> float:
    match = re.search(r"([\d.]+)", chance or "")
    return float(match.group(1)) if match else 0.0


def collect_item_html_paths(item_dir: Path, item_id: int) -> list[Path]:
    """All HTML files for an item id, including drop/spoil pagination variants."""
    paths = sorted(item_dir.glob(f"{item_id}-*.html"))
    if not paths:
        return []
    primary = [p for p in paths if "__" not in p.name]
    variants = [p for p in paths if "__" in p.name]
    ordered: list[Path] = []
    seen: set[Path] = set()
    for p in primary + variants:
        if p not in seen:
            seen.add(p)
            ordered.append(p)
    return ordered


def parse_restrictions(soup: BeautifulSoup) -> dict[str, bool]:
    out: dict[str, bool] = {}
    for block in soup.select(".stat_restrictions .item_restriction"):
        img = block.select_one("img")
        label = _clean_text(block.get_text()).lower()
        key = RESTRICTION_KEYS.get(label)
        if not key:
            continue
        src = (img.get("src") or "") if img else ""
        out[key] = "check-yes" in src
    return out


def _parse_npc_source_rows(soup: BeautifulSoup, container_id: str) -> list[dict[str, Any]]:
    container = soup.select_one(f"#{container_id}")
    if container is None:
        return []

    table = container.select_one(".flex-table") or container
    rows: list[dict[str, Any]] = []
    for el in table.select(".flex-row"):
        classes = el.get("class") or []
        if "header-row" in classes:
            continue
        cells = el.select(".flex-cell")
        if len(cells) < 3:
            continue
        link = cells[0].select_one("a.item-name")
        if link is None:
            continue
        href = link.get("href") or ""
        npc_match = NPC_ID_RE.search(href)
        if not npc_match:
            continue
        name_el = link.select_one(".item-name__content")
        npc_name = _clean_text(name_el.get_text()) if name_el else _clean_text(link.get_text())
        npc_name = re.sub(r"\s+Lv\.\s*\d+$", "", npc_name).strip()
        level_el = link.select_one(".item-name__additional")
        level_raw = _clean_text(level_el.get_text()) if level_el else ""
        level = _parse_int(level_raw)
        chance_text = _clean_text(cells[2].get_text())
        rows.append(
            {
                "npc_id": int(npc_match.group(1)),
                "npc_name": npc_name,
                "npc_level": level,
                "npc_level_raw": level_raw,
                "npc_url": href.split("?", 1)[0],
                "amount": _clean_text(cells[1].get_text()),
                "chance": chance_text,
                "chance_val": _chance_val(chance_text),
            }
        )
    return rows


def parse_drop_spoil_from_html(html: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    _require_bs4()
    soup = BeautifulSoup(html, "html.parser")
    return (
        _parse_npc_source_rows(soup, "pjax_drop"),
        _parse_npc_source_rows(soup, "pjax_spoil"),
    )


def merge_source_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[int, str, str]] = set()
    merged: list[dict[str, Any]] = []
    for row in rows:
        key = (row["npc_id"], row.get("amount") or "", row.get("chance") or "")
        if key in seen:
            continue
        seen.add(key)
        merged.append(row)
    merged.sort(key=lambda r: (-r.get("chance_val", 0), r.get("npc_name", "").lower()))
    return merged


def collect_item_sources(item_dir: Path, item_id: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    drops: list[dict[str, Any]] = []
    spoils: list[dict[str, Any]] = []
    for path in collect_item_html_paths(item_dir, item_id):
        html = path.read_text(encoding="utf-8", errors="replace")
        page_drops, page_spoils = parse_drop_spoil_from_html(html)
        drops.extend(page_drops)
        spoils.extend(page_spoils)
    return merge_source_rows(drops), merge_source_rows(spoils)


def parse_enchant_table(soup: BeautifulSoup) -> list[dict[str, Any]]:
    pane = soup.select_one("#enchant")
    if pane is None:
        return []
    table = pane.select_one(".flex-table")
    if table is None:
        return []

    headers: list[str] = []
    rows_out: list[dict[str, Any]] = []
    for el in table.select(".flex-row"):
        classes = el.get("class") or []
        cells = [_clean_text(c.get_text()) for c in el.select(".flex-cell")]
        if "header-row" in classes:
            headers = [h.lower() for h in cells]
            continue
        if not cells:
            continue
        row: dict[str, Any] = {}
        for idx, val in enumerate(cells):
            header = headers[idx] if idx < len(headers) else f"col_{idx}"
            if header.startswith("enchant") or header == "enchant":
                level_match = re.search(r"\+(\d+)", val)
                row["level"] = int(level_match.group(1)) if level_match else 0
            elif "crystallization" in header:
                row["crystals"] = None if val in ("-", "") else _parse_int(val)
            elif "failed enchant" in header:
                row["fail_crystals"] = None if val in ("-", "") else _parse_int(val)
            else:
                stat_key = re.sub(r"[^a-z0-9]+", "_", header).strip("_")
                if stat_key:
                    row[stat_key] = val
        if row:
            rows_out.append(row)
    return rows_out


def _parse_link_rows(soup: BeautifulSoup, pane_id: str) -> list[dict[str, Any]]:
    pane = soup.select_one(f"#{pane_id}")
    if pane is None:
        return []
    rows: list[dict[str, Any]] = []
    for link in pane.select('a.item-name[href*="/lu4/"]'):
        href = link.get("href") or ""
        item_match = ITEM_ID_RE.search(href)
        quest_match = re.search(r"/lu4/quest/(\d+)-", href)
        if item_match:
            rows.append(
                {
                    "kind": "item",
                    "id": int(item_match.group(1)),
                    "name": _clean_text(link.get_text()),
                    "url": href.split("?", 1)[0],
                }
            )
        elif quest_match:
            rows.append(
                {
                    "kind": "quest",
                    "id": int(quest_match.group(1)),
                    "name": _clean_text(link.get_text()),
                    "url": href.split("?", 1)[0],
                }
            )
    return rows


def parse_item_links(soup: BeautifulSoup) -> dict[str, Any]:
    recipes: list[int] = []
    item_skills: list[dict[str, Any]] = []
    soul_crystals: list[int] = []

    for line in soup.select("#result-stats .stat_line"):
        name_el = line.select_one(".stat_name")
        if not name_el:
            continue
        label = _clean_text(name_el.get_text())
        for link in line.select('a.item-name[href*="/lu4/item/"]'):
            m = ITEM_ID_RE.search(link.get("href") or "")
            if not m:
                continue
            iid = int(m.group(1))
            if label == "Recipes":
                recipes.append(iid)
            elif label == "Soul Crystals":
                soul_crystals.append(iid)
        for link in line.select('a.item-name[href*="/lu4/skill/"]'):
            skill_match = re.search(r"/lu4/skill/(\d+)-", link.get("href") or "")
            if skill_match:
                item_skills.append(
                    {
                        "id": int(skill_match.group(1)),
                        "name": _clean_text(link.get_text()),
                        "url": (link.get("href") or "").split("?", 1)[0],
                    }
                )

    set_info: dict[str, Any] | None = None
    for line in soup.select("#result-stats .stat_line"):
        name_node = line.select_one(".stat_name")
        if name_node and "Set Part" in name_node.get_text():
            link = line.select_one('a.item-name[href*="/lu4/set/"]')
            if link:
                set_match = re.search(r"/lu4/set/(\d+)-", link.get("href") or "")
                name = _clean_text(link.get_text())
                name = re.sub(r"\s+(NG|D|C|B|A|S)$", "", name).strip()
                set_info = {
                    "id": int(set_match.group(1)) if set_match else None,
                    "name": name,
                    "url": (link.get("href") or "").split("?", 1)[0],
                }
            break

    return {
        "recipes": recipes,
        "item_skills": item_skills,
        "soul_crystals": soul_crystals,
        "set": set_info,
        "contained": _parse_link_rows(soup, "contained"),
        "quest_reward": _parse_link_rows(soup, "questreward"),
        "quest_goal": _parse_link_rows(soup, "questGoal"),
        "quest_related": _parse_link_rows(soup, "questRelated"),
        "capsule": _parse_link_rows(soup, "capsule"),
    }
