"""Build weapon_upgrades.json from wiki post 364 (NG/D equipment upgrade)."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

from bs4 import BeautifulSoup, Tag

ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "data" / "wiki" / "library" / "raw" / "lu4" / "posts" / "post" / "364-ngd-equipment-upgrade.html"
OUT_PATH = ROOT / "data" / "datasets" / "weapon_upgrades.json"
ENCYCLOPEDIA_PATH = ROOT / "data" / "datasets" / "items_encyclopedia.json"

ITEM_HREF_RE = re.compile(r"/lu4/item/(\d+)-")
ADENA_COST_RE = re.compile(r"x\s*([\d\s\u00a0]+)")

SKIP_HEADINGS = {
    "armor for warriors",
    "armor for mages",
    "helmets, gloves, boots",
    "shields and jewelry",
    "heavy armor",
    "light armor",
    "magic armor",
}

CATEGORY_LABELS: dict[str, str] = {
    "one-handed swords": "Одноручные мечи",
    "one-handed axes": "Одноручные топоры",
    "two-handed swords": "Двуручные мечи",
    "axes": "Топоры",
    "spears": "Копья",
    "fists": "Кастеты",
    "daggers": "Кинжалы",
    "bows": "Луки",
    "magic weapon": "Магическое оружие",
    "magic swords and daggers": "Магические мечи и кинжалы",
    "one-handed staves and scroll of wisdom": "Одноручные посохи и свитки",
    "two-handed staves": "Двуручные посохи",
}


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def parse_item_links(cell: Tag | None) -> list[int]:
    if cell is None:
        return []
    ids: list[int] = []
    for link in cell.find_all("a", href=True):
        match = ITEM_HREF_RE.search(link["href"])
        if not match:
            continue
        item_id = int(match.group(1))
        if item_id == 57:  # Adena
            continue
        if item_id not in ids:
            ids.append(item_id)
    return ids


def parse_adena_cost(cell: Tag | None) -> int | None:
    if cell is None:
        return None
    text = cell.get_text(" ", strip=True)
    match = ADENA_COST_RE.search(text)
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(1))
    return int(digits) if digits else None


def parse_item_from_link(link: Tag) -> dict | None:
    match = ITEM_HREF_RE.search(link.get("href", ""))
    if not match:
        return None
    item_id = int(match.group(1))
    if item_id == 57:
        return None
    name_el = link.select_one(".item-name__class-1")
    grade_el = link.select_one(".item-grade")
    icon_el = link.select_one("img")
    return {
        "id": item_id,
        "name": unescape(name_el.get_text(strip=True)) if name_el else f"Item {item_id}",
        "grade": grade_el.get_text(strip=True) if grade_el else "",
        "icon": icon_el.get("src", "").replace("/i64/", "").replace("/icon64/", "") if icon_el else None,
    }


def collect_items(root: Tag, items: dict[str, dict]) -> None:
    for link in root.find_all("a", href=True):
        parsed = parse_item_from_link(link)
        if parsed is None:
            continue
        key = str(parsed["id"])
        if key not in items:
            items[key] = parsed


def heading_text(tag: Tag) -> str:
    return unescape(tag.get_text(" ", strip=True))


def is_weapon_section(grade: str | None, kind: str | None, category: str | None) -> bool:
    if grade not in {"NG", "D"}:
        return False
    if kind not in {"physical", "magic"}:
        return False
    return category is not None


def parse_upgrade_table(
    table: Tag,
    *,
    grade: str,
    kind: str,
    category: str,
    category_label: str,
    upgrades: list[dict],
) -> None:
    tbody = table.find("tbody")
    if tbody is None:
        return
    headers = [th.get_text(" ", strip=True).lower() for th in table.find_all("th")]
    has_cost = any("cost" in h or "improvement" in h for h in headers)

    for row in tbody.find_all("tr", recursive=False):
        cells = row.find_all("td", recursive=False)
        if len(cells) < 2:
            continue

        if has_cost and len(cells) >= 3:
            from_ids = parse_item_links(cells[0])
            cost = parse_adena_cost(cells[1])
            to_ids = parse_item_links(cells[2])
        else:
            from_ids = parse_item_links(cells[0])
            cost = None
            to_ids = parse_item_links(cells[1])

        if not from_ids or not to_ids:
            continue

        upgrades.append(
            {
                "grade": grade,
                "kind": kind,
                "category": category,
                "category_label": category_label,
                "from_ids": from_ids,
                "cost_adena": cost,
                "to_ids": to_ids,
            }
        )


def enrich_items_from_encyclopedia(items: dict[str, dict]) -> None:
    if not ENCYCLOPEDIA_PATH.is_file():
        return
    payload = json.loads(ENCYCLOPEDIA_PATH.read_text(encoding="utf-8"))
    catalog = payload.get("items") or {}
    for key, entry in items.items():
        wiki = catalog.get(key) if isinstance(catalog, dict) else None
        if not isinstance(wiki, dict):
            continue
        if wiki.get("name"):
            entry["name"] = wiki["name"]
        if wiki.get("grade"):
            entry["grade"] = wiki["grade"]
        if wiki.get("icon"):
            entry["icon"] = wiki["icon"]
        if wiki.get("npc_sell") is not None:
            entry["npc_sell"] = wiki["npc_sell"]
        stats = wiki.get("stats")
        if isinstance(stats, dict):
            if stats.get("p_atk") is not None:
                entry["p_atk"] = stats["p_atk"]
            if stats.get("m_atk") is not None:
                entry["m_atk"] = stats["m_atk"]


def build() -> dict:
    html = HTML_PATH.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    content = soup.select_one("#article-content")
    if content is None:
        raise RuntimeError("article-content not found")

    items: dict[str, dict] = {}
    collect_items(content, items)

    grade: str | None = None
    kind: str | None = None
    category: str | None = None
    category_label: str | None = None
    upgrades: list[dict] = []
    ng_to_d: dict | None = None
    in_ng_to_d = False
    weapon_mode = False

    for node in content.find_all(["h2", "h3", "p", "table"]):
        if node.name == "h2":
            title = heading_text(node).lower()
            in_ng_to_d = "ng" in title and "d" in title and "weapon" in title
            if in_ng_to_d:
                grade = kind = category = category_label = None
                weapon_mode = False
                continue
            if title.startswith("no-grade"):
                grade, kind, category, category_label = "NG", None, None, None
                in_ng_to_d = False
                weapon_mode = False
                continue
            if title.startswith("d-grade"):
                grade, kind, category, category_label = "D", None, None, None
                in_ng_to_d = False
                weapon_mode = False
                continue
            weapon_mode = False
            continue

        if node.name == "h3":
            title = heading_text(node).lower()
            if any(skip in title for skip in SKIP_HEADINGS):
                weapon_mode = False
                kind = category = category_label = None
                continue
            if "physical weapon" in title:
                kind = "physical"
                category = category_label = None
                weapon_mode = True
                continue
            if title == "magic weapon":
                kind = "magic"
                category = category_label = None
                weapon_mode = True
                continue
            weapon_mode = False
            continue

        if node.name == "p":
            if not weapon_mode or kind is None:
                continue
            bold = node.find("b")
            if bold is None:
                continue
            label_raw = heading_text(bold)
            label_key = label_raw.lower()
            if any(skip in label_key for skip in SKIP_HEADINGS):
                weapon_mode = False
                continue
            category = slugify(label_raw)
            category_label = CATEGORY_LABELS.get(label_key, label_raw)
            continue

        if node.name != "table":
            continue

        if in_ng_to_d:
            tbody = node.find("tbody")
            if tbody is None:
                continue
            rows = tbody.find_all("tr", recursive=False)
            if not rows:
                continue
            cells = rows[0].find_all("td", recursive=False)
            if len(cells) < 2:
                continue
            from_ids = parse_item_links(cells[0])
            to_ids = parse_item_links(cells[1])
            pairs = [
                {"from_id": left, "to_id": right}
                for left, right in zip(from_ids, to_ids, strict=False)
            ]
            ng_to_d = {
                "coupon_id": 38214,
                "coupon_name": "Weapon Upgrade Coupon",
                "npc": "Newbie Guide",
                "profession": "1st Profession",
                "from_ids": from_ids,
                "to_ids": to_ids,
                "pairs": pairs,
            }
            continue

        if not is_weapon_section(grade, kind, category):
            continue
        parse_upgrade_table(
            node,
            grade=grade or "NG",
            kind=kind or "physical",
            category=category or "unknown",
            category_label=category_label or category or "Unknown",
            upgrades=upgrades,
        )

    enrich_items_from_encyclopedia(items)

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_url": "https://masterwork.wiki/lu4/posts/post/364-ngd-equipment-upgrade",
        "info": {
            "where": "Торговцы NPC (магазины оружия и брони)",
            "ng_to_d_where": "NPC Newbie Guide",
            "ng_rule": "NG-апгрейды без наценки: итоговая цена одинакова при покупке топового NG или пошаговом апгрейде.",
            "d_rule": "D-апгрейды с небольшой наценкой: пошаговый апгрейд дороже прямой покупки финального предмета.",
            "tax_note": "Цены без налога замка (до +15%). На NG-апгрейды налог не распространяется.",
            "how": "Отдайте старое снаряжение, заплатите Adena и получите улучшенный предмет.",
        },
        "upgrades": upgrades,
        "ng_to_d": ng_to_d,
        "items": items,
    }


def main() -> None:
    payload = build()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    ng = sum(1 for u in payload["upgrades"] if u["grade"] == "NG")
    d = sum(1 for u in payload["upgrades"] if u["grade"] == "D")
    print(f"Wrote {OUT_PATH.name}: {ng} NG + {d} D weapon upgrade rows, {len(payload['items'])} items")


if __name__ == "__main__":
    main()
