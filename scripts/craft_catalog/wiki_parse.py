"""Parse Lu4 wiki raw HTML item and recipe pages."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - optional when running outside backend venv
    BeautifulSoup = None  # type: ignore

ITEM_ID_RE = re.compile(r"/lu4/item/(\d+)-")
NPC_ID_RE = re.compile(r"/lu4/npc/(\d+)-")
I64_ICON_RE = re.compile(r"/i64/([^/?#]+)$")
CRAFT_REQ_RE = re.compile(
    r"Requires Create Item - Skill Level (\d+) \((?:[^()]+?) Lv\. (\d+)\)",
    re.IGNORECASE,
)
NUMERIC_RE = re.compile(r"[\d\s]+")


def _require_bs4():
    if BeautifulSoup is None:
        raise RuntimeError("beautifulsoup4 is required: pip install beautifulsoup4")


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def _parse_int(value: str | None) -> int | None:
    if not value:
        return None
    digits = NUMERIC_RE.search(value.replace("\xa0", " "))
    if not digits:
        return None
    try:
        return int(digits.group(0).replace(" ", ""))
    except ValueError:
        return None


def _parse_stat_lines(soup: BeautifulSoup) -> dict[str, str]:
    stats: dict[str, str] = {}
    for line in soup.select("#result-stats .stat_line, .recipe_result .stat_line"):
        name_el = line.select_one(".stat_name")
        if not name_el:
            continue
        key = _clean_text(name_el.get_text())
        val_el = line.select_one(".stat_value, .stat_describe, span:not(.stat_name)")
        if val_el is None:
            continue
        val = _clean_text(val_el.get_text())
        if key and val:
            stats[key] = val
    return stats


def _item_stats(stats: dict[str, str]) -> dict[str, int | None]:
    out: dict[str, int | None] = {
        "p_atk": None,
        "m_atk": None,
        "p_def": None,
        "m_def": None,
        "shield_def": None,
        "crystals": None,
        "weight": None,
        "accuracy": None,
        "evasion": None,
        "crit_rate": None,
        "mp_bonus": None,
        "mp_consume": None,
    }
    mapping = {
        "P. Atk.": "p_atk",
        "M. Atk.": "m_atk",
        "P. Def.": "p_def",
        "M. Def.": "m_def",
        "Shield Def.": "shield_def",
        "Shield Defense": "shield_def",
        "Crystal Amount": "crystals",
        "Weight": "weight",
        "Accuracy": "accuracy",
        "Evasion": "evasion",
        "P. Crit. Rate.": "crit_rate",
        "MP Bonus": "mp_bonus",
        "MP Consume": "mp_consume",
    }
    combined = stats.get("P. Atk. / M. Atk.")
    if combined and "/" in combined:
        parts = [p.strip() for p in combined.split("/", 1)]
        if len(parts) == 2:
            if "P. Atk. / M. Atk." not in stats:
                stats = dict(stats)
            if out["p_atk"] is None:
                out["p_atk"] = _parse_int(parts[0])
            if out["m_atk"] is None:
                out["m_atk"] = _parse_int(parts[1])
    for label, key in mapping.items():
        if label in stats:
            out[key] = _parse_int(stats[label])
    cleaned = {k: v for k, v in out.items() if v is not None}
    return cleaned


def raw_html_path(wiki_root: Path, url: str) -> Path | None:
    """Resolve /lu4/item/123-slug to on-disk raw HTML."""
    m = ITEM_ID_RE.search(url or "")
    if not m:
        return None
    item_dir = wiki_root / "raw" / "lu4" / "item"
    matches = list(item_dir.glob(f"{m.group(1)}-*.html"))
    if not matches:
        return None
    return matches[0]


def load_html(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_item_icon(html: str) -> str | None:
    _require_bs4()
    soup = BeautifulSoup(html, "html.parser")
    img = soup.select_one(".item_head .item-icon img")
    if img is None:
        return None
    m = I64_ICON_RE.search(img.get("src") or "")
    return m.group(1) if m else None


def item_icon_from_wiki(wiki_root: Path, item_id: int) -> str | None:
    path = raw_html_path(wiki_root, f"/lu4/item/{item_id}")
    if path is None or not path.is_file():
        matches = list((wiki_root / "raw" / "lu4" / "item").glob(f"{item_id}-*.html"))
        if not matches:
            return None
        path = matches[0]
    return parse_item_icon(load_html(path))


def _item_slug_from_path(path: Path | None, item_id: int) -> str:
    if path is None:
        return str(item_id)
    stem = path.stem.split("__", 1)[0]
    prefix = f"{item_id}-"
    if stem.startswith(prefix):
        return stem[len(prefix) :]
    return stem


def parse_item_page(html: str, item_id: int, url: str, *, full: bool = False) -> dict[str, Any]:
    _require_bs4()
    from .item_tabs import (
        collect_item_sources,
        parse_enchant_table,
        parse_item_links,
        parse_restrictions,
    )

    soup = BeautifulSoup(html, "html.parser")

    name_el = soup.select_one(".item_title .item-name__content")
    name = _clean_text(name_el.get_text()) if name_el else f"#{item_id}"
    name = re.sub(r"\s+(NG|D|C|B|A|S)$", "", name).strip()

    grade_el = soup.select_one(".item_title .item-grade")
    grade = _clean_text(grade_el.get_text()) if grade_el else "NG"

    type_el = soup.select_one(".item-name__type")
    item_type = _clean_text(type_el.get_text()) if type_el else ""

    stats_raw = _parse_stat_lines(soup)
    combat = _item_stats(stats_raw)

    npc_sell = _parse_int(stats_raw.get("NPC Sell Price"))
    links = parse_item_links(soup)
    set_name = links.get("set", {}).get("name") if links.get("set") else None

    desc_el = soup.select_one(".item_part > .stat_line")
    description = None
    if desc_el and not desc_el.select_one(".stat_name"):
        description = _clean_text(desc_el.get_text())

    is_recipe = item_type == "Other / Recipe" or "recipe_content" in html

    icon = parse_item_icon(html)

    item: dict[str, Any] = {
        "id": item_id,
        "name": name,
        "grade": grade,
        "type": item_type,
        "set_name": set_name,
        "npc_sell": npc_sell,
        "url": url,
        "is_recipe_scroll": is_recipe,
    }
    if icon:
        item["icon"] = icon
    if combat:
        item["stats"] = combat
    if description:
        item["description"] = description
        item["effects"] = description

    if full:
        item["restrictions"] = parse_restrictions(soup)
        item["enchant"] = parse_enchant_table(soup)
        item["links"] = links
        item["stats_raw"] = stats_raw
    return item


def parse_item_full(item_dir: Path, item_id: int, url: str) -> dict[str, Any]:
    """Parse base item page plus merged drop/spoil from pagination variants."""
    from .item_tabs import collect_item_html_paths, collect_item_sources

    paths = collect_item_html_paths(item_dir, item_id)
    if not paths:
        return parse_item_page("", item_id, url, full=True)

    primary = next((p for p in paths if "__" not in p.name), paths[0])
    html = load_html(primary)
    item = parse_item_page(html, item_id, url, full=True)
    item["slug"] = _item_slug_from_path(primary, item_id)

    drops, spoils = collect_item_sources(item_dir, item_id)
    item["drops"] = drops
    item["spoils"] = spoils
    item["has_drop"] = bool(drops)
    item["has_spoil"] = bool(spoils)
    return item


def parse_recipe_variant(html: str, recipe_id: int, recipe_url: str) -> dict[str, Any] | None:
    _require_bs4()
    from .recipe_trees import parse_recipe_tree

    soup = BeautifulSoup(html, "html.parser")
    if not soup.select_one(".recipe_content"):
        return None

    result_link = None
    for line in soup.select(".recipe_result .stat_line"):
        name_el = line.select_one(".stat_name")
        if name_el and "Result" in name_el.get_text():
            result_link = line.select_one('a.item-name[href*="/lu4/item/"]')
            break
    if result_link is None:
        return None
    m = ITEM_ID_RE.search(result_link.get("href") or "")
    if not m:
        return None
    product_id = int(m.group(1))

    stats = _parse_stat_lines(soup)
    success = stats.get("Success Rate", "100%")
    rate_match = re.search(r"(\d+(?:\.\d+)?)", success or "")
    rate = float(rate_match.group(1)) if rate_match else 100.0

    crafter_level = None
    desc_block = soup.select_one(".item_part .stat_line")
    if desc_block:
        req = CRAFT_REQ_RE.search(desc_block.get_text(" "))
        if req:
            crafter_level = int(req.group(2))

    tree = parse_recipe_tree(soup)
    direct = [{"id": node["id"], "amount": node["amount"]} for node in tree]

    return {
        "recipe_id": recipe_id,
        "recipe_url": recipe_url,
        "product_id": product_id,
        "rate": rate,
        "crafter_level": crafter_level,
        "skill_level": stats.get("Level"),
        "mp": stats.get("MP Consume"),
        "success": success,
        "yield": 1,
        "tree": tree,
        "direct": direct,
    }
