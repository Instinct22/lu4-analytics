from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup

from config import settings

LIB_RAW = Path(settings.wiki_path) / "library" / "raw" / "lu4"


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _chance_val(chance: str) -> float:
    match = re.search(r"([\d.]+)", chance or "")
    return float(match.group(1)) if match else 0.0


def _format_chance(value: float) -> str:
    """Match wiki-style fixed decimals, trim trailing zeros after the point."""
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    if "." not in text:
        text += ".0"
    return f"{text}%"


def _npc_html_path(npc_url: str) -> Path:
    rel = npc_url.lstrip("/").split("?", 1)[0]
    rel = re.sub(r"^lu4/", "", rel)
    return LIB_RAW.joinpath(*rel.split("/")).with_suffix(".html")


def _npc_html_paths(npc_url: str) -> list[Path]:
    path = _npc_html_path(npc_url)
    if not path.exists():
        return []
    paths = [path]
    base = path.stem
    for suffix in ("__dropPage_", "__spoilPage_"):
        for page in sorted(path.parent.glob(f"{base}{suffix}*.html")):
            if page not in paths:
                paths.append(page)
    return paths


def _extract_item_name(link) -> str:
    for cls in (
        "item-name__class-1",
        "item-name__class-2",
        "item-name__class-3",
        "item-name__class-4",
        "item-name__class-5",
    ):
        el = link.select_one(f".{cls}")
        if el:
            return _clean(el.get_text())
    content = link.select_one(".item-name__content")
    if content:
        grade = content.select_one(".item-grade")
        if grade:
            grade.extract()
        return _clean(content.get_text())
    return _clean(link.get_text())


def _extract_item_grade(link) -> str:
    grade = link.select_one(".item-grade")
    return _clean(grade.get_text()) if grade else ""


def _parse_item_rows(html: str, kind: str) -> list[dict]:
    """Parse NPC spoil/drop tables.

    Drop tables on the wiki use Group Chance + within-group chance.
    Real drop chance = group_chance% * within_group% / 100.
    Spoil has no groups — the listed chance is already absolute.
    """
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one(f"#pjax_npc_{kind}")
    if container is None:
        return []

    table = container.select_one(".flex-table") or container
    rows: list[dict] = []
    # Default 100%: if a row appears before any divider, treat listed % as absolute.
    group_chance = 100.0
    apply_group = kind == "drop"

    for el in table.children:
        if getattr(el, "name", None) is None:
            continue
        classes = el.get("class") or []
        if el.name == "p" and "drop_group_divider" in classes:
            group_chance = _chance_val(_clean(el.get_text())) or 100.0
            continue
        if el.name != "div" or "flex-row" not in classes:
            continue
        if "header-row" in classes:
            continue

        cells = el.select(".flex-cell")
        if len(cells) < 3:
            continue
        link = cells[0].select_one("a.item-name")
        if link is None:
            continue
        href = link.get("href", "")
        match = re.search(r"/item/(\d+)-", href)
        if not match:
            continue

        within = _chance_val(_clean(cells[2].get_text()))
        if apply_group:
            # Real chance: first roll group, then roll within group.
            effective = round(group_chance * within / 100.0, 6)
            chance = _format_chance(effective)
            chance_val = effective
        else:
            chance = _clean(cells[2].get_text())
            chance_val = within

        rows.append(
            {
                "item_id": int(match.group(1)),
                "item_name": _extract_item_name(link),
                "item_grade": _extract_item_grade(link),
                "item_url": href.split("?", 1)[0],
                "amount": _clean(cells[1].get_text()),
                "chance": chance,
                "chance_val": chance_val,
            }
        )
    return rows


def _collect_kind(npc_url: str, kind: str) -> list[dict]:
    seen: set[tuple[int, str, str]] = set()
    items: list[dict] = []
    for page_path in _npc_html_paths(npc_url):
        html = page_path.read_text(encoding="utf-8", errors="replace")
        for row in _parse_item_rows(html, kind):
            key = (row["item_id"], row["amount"], row["chance"])
            if key in seen:
                continue
            seen.add(key)
            items.append(row)
    items.sort(key=lambda r: (-r["chance_val"], r["item_name"].lower()))
    return items


def get_npc_loot(npc_url: str) -> dict:
    return {
        "spoils": _collect_kind(npc_url, "spoil"),
        "drops": _collect_kind(npc_url, "drop"),
    }
