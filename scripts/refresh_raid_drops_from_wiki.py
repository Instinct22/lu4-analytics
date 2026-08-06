#!/usr/bin/env python3
"""Refresh raid_bosses.json drop tables from local wiki NPC HTML.

Updates only the ``drops`` field for each existing boss. Boss IDs, map coords,
respawn, skills, and other metadata are preserved so raid timers (FK by
external_id) and visibility settings stay intact.

  py -3 scripts/refresh_raid_drops_from_wiki.py
  docker compose exec -T backend python /scripts/import_datasets.py raid_bosses
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
RAID_JSON = ROOT / "data" / "datasets" / "raid_bosses.json"
NPC_RAW = ROOT / "data" / "wiki" / "library" / "raw" / "lu4" / "npc"
ENC_JSON = ROOT / "data" / "datasets" / "items_encyclopedia.json"

I64_RE = re.compile(r"/i64/([^/?#\"']+)")
ITEM_RE = re.compile(r"/lu4/item/(\d+)-")


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _chance_text(raw: str) -> str:
    m = re.search(r"([\d.]+)", raw or "")
    if not m:
        return raw.strip()
    val = float(m.group(1))
    text = f"{val:.6f}".rstrip("0").rstrip(".")
    if "." not in text:
        text += ".0"
    return f"{text}%"


def _item_name(link) -> str:
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


def _item_grade(link) -> str | None:
    grade = link.select_one(".item-grade")
    text = _clean(grade.get_text()) if grade else ""
    return text or None


def _item_icon(row, link) -> str | None:
    img = row.select_one("img[src*='/i64/']") or link.select_one("img[src*='/i64/']")
    if not img:
        return None
    m = I64_RE.search(img.get("src") or "")
    return m.group(1) if m else None


def parse_drop_groups(html: str) -> list[dict]:
    """Parse wiki NPC drop pane into raid_bosses drop-group shape.

    Item ``chance`` is the within-group % as shown on the wiki (UI also shows
    groupChance separately).
    """
    soup = BeautifulSoup(html, "html.parser")
    container = soup.select_one("#pjax_npc_drop")
    if container is None:
        return []
    table = container.select_one(".flex-table") or container

    groups: list[dict] = []
    current: dict | None = None

    for el in table.children:
        if getattr(el, "name", None) is None:
            continue
        classes = el.get("class") or []
        if el.name == "p" and "drop_group_divider" in classes:
            raw = _clean(el.get_text())
            m = re.search(r"Group Chance:\s*([\d.]+)\s*%", raw, re.I)
            gc = f"{m.group(1)}%" if m else "100%"
            current = {"groupChance": gc, "items": []}
            groups.append(current)
            continue
        if el.name != "div" or "flex-row" not in classes or "header-row" in classes:
            continue
        if current is None:
            current = {"groupChance": "100%", "items": []}
            groups.append(current)

        cells = el.select(":scope > .flex-cell") or el.select(".flex-cell")
        if len(cells) < 3:
            continue
        link = cells[0].select_one("a.item-name") or cells[0].select_one('a[href*="/item/"]')
        if link is None:
            continue
        href = link.get("href") or ""
        m = ITEM_RE.search(href.replace("/lu4-b-w-c/", "/lu4/"))
        if not m:
            continue
        item_id = int(m.group(1))
        amount = _clean(cells[1].get_text()) or None
        chance = _chance_text(_clean(cells[2].get_text()))
        current["items"].append(
            {
                "name": _item_name(link) or None,
                "grade": _item_grade(link),
                "amount": amount,
                "chance": chance,
                "icon": _item_icon(el, link),
                "itemId": item_id,
            }
        )

    return [g for g in groups if g.get("items")]


def find_npc_html(npc_id: int) -> Path | None:
    matches = sorted(NPC_RAW.glob(f"{npc_id}-*.html"))
    base = [p for p in matches if "__" not in p.name]
    if base:
        return base[0]
    return matches[0] if matches else None


def load_icon_fallback() -> dict[int, str]:
    if not ENC_JSON.is_file():
        return {}
    payload = json.loads(ENC_JSON.read_text(encoding="utf-8"))
    out: dict[int, str] = {}
    for raw_id, meta in (payload.get("items") or {}).items():
        if not isinstance(meta, dict):
            continue
        icon = meta.get("icon")
        if not icon or not isinstance(icon, str):
            continue
        try:
            iid = int(meta.get("id") if meta.get("id") is not None else raw_id)
        except (TypeError, ValueError):
            continue
        out[iid] = icon
    return out


def main() -> int:
    if not RAID_JSON.is_file():
        print(f"Missing {RAID_JSON}", file=sys.stderr)
        return 2
    if not NPC_RAW.is_dir():
        print(f"Missing NPC raw dir {NPC_RAW}", file=sys.stderr)
        return 2

    payload = json.loads(RAID_JSON.read_text(encoding="utf-8"))
    bosses = payload.get("bosses") or []
    icons = load_icon_fallback()

    updated = 0
    missing_html = 0
    empty_drop = 0
    unchanged_ids: list[int] = []

    for boss in bosses:
        npc_id = boss.get("id")
        if not isinstance(npc_id, int):
            continue
        path = find_npc_html(npc_id)
        if path is None:
            missing_html += 1
            unchanged_ids.append(npc_id)
            continue
        html = path.read_text(encoding="utf-8", errors="replace")
        groups = parse_drop_groups(html)
        for g in groups:
            for it in g["items"]:
                if not it.get("icon") and it.get("itemId") in icons:
                    it["icon"] = icons[it["itemId"]]
        if not groups:
            empty_drop += 1
            # Keep previous drops if wiki page has no drop pane
            continue
        boss["drops"] = groups
        # Keep wiki URL pointing at /lu4/ for app consistency
        slug = path.stem
        boss["wikiUrl"] = f"https://masterwork.wiki/lu4/npc/{slug}"
        updated += 1

    RAID_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Updated drops for {updated}/{len(bosses)} bosses -> {RAID_JSON}\n"
        f"  missing html: {missing_html}\n"
        f"  empty drop pane (kept old): {empty_drop}\n"
        f"  boss id count unchanged: {len(bosses)}"
    )

    # Sanity: Flame Lord Shadar
    shadar = next((b for b in bosses if b.get("id") == 25152), None)
    if shadar:
        names = [it.get("name") for g in shadar.get("drops") or [] for it in g.get("items") or []]
        print(f"  Shadar sample items: {names[:8]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
