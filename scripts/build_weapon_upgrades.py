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

# Weapon subcategory labels (from the <b> headings under Physical/Magic weapon).
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

# h3 group headings for armor / jewelry sections.
ARMOR_GROUP_LABELS: dict[str, str] = {
    "armor for warriors": "Броня воинов",
    "armor for mages": "Броня магов",
    "heavy armor": "Тяжёлая броня",
    "light armor": "Лёгкая броня",
    "magic armor": "Магическая броня",
    "helmets, gloves, boots": "Шлемы, перчатки, ботинки",
    "shields and jewelry": "Щиты и бижутерия",
}

# <b> subcategory labels inside armor / jewelry groups.
SUB_LABELS: dict[str, str] = {
    "upper armor": "Верхняя броня",
    "lower armor": "Нижняя броня",
    "helmets": "Шлемы",
    "gloves": "Перчатки",
    "boots": "Ботинки",
    "shields": "Щиты",
    "necklaces": "Ожерелья",
    "earrings": "Серьги",
    "rings": "Кольца",
}


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def classify_armor_sub(
    group_key: str, sub_key: str, sub_raw: str
) -> tuple[str, str, str]:
    """Map an armor/jewelry <b> subheading to (kind, category, category_label)."""
    group_label = ARMOR_GROUP_LABELS.get(group_key, group_key)
    sub_label = SUB_LABELS.get(sub_key, sub_raw)
    if sub_key.startswith("shield"):
        return "armor", "shields", "Щиты"
    if sub_key.startswith("necklace"):
        return "jewelry", "necklaces", "Ожерелья"
    if sub_key.startswith("earring"):
        return "jewelry", "earrings", "Серьги"
    if sub_key.startswith("ring"):
        return "jewelry", "rings", "Кольца"
    # Helmets/Gloves/Boots need no group prefix — the piece name is self-explanatory.
    if group_key == "helmets, gloves, boots":
        return "armor", slugify(sub_key), sub_label
    # Upper/Lower armor belongs to a specific armor group (warriors, heavy, ...).
    return "armor", slugify(f"{group_key} {sub_key}"), f"{group_label}: {sub_label}"


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
            for stat in ("p_atk", "m_atk", "p_def", "m_def"):
                if stats.get(stat) is not None:
                    entry[stat] = stats[stat]


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
    group_key: str | None = None
    category: str | None = None
    category_label: str | None = None
    upgrades: list[dict] = []
    ng_to_d: dict | None = None
    in_ng_to_d = False
    section_mode = False

    for node in content.find_all(["h2", "h3", "p", "table"]):
        if node.name == "h2":
            title = heading_text(node).lower()
            in_ng_to_d = "ng" in title and "d" in title and "weapon" in title
            kind = group_key = category = category_label = None
            section_mode = False
            if in_ng_to_d:
                grade = None
            elif title.startswith("no-grade"):
                grade = "NG"
            elif title.startswith("d-grade"):
                grade = "D"
            continue

        if node.name == "h3":
            title = heading_text(node).lower()
            in_ng_to_d = False
            kind = group_key = category = category_label = None
            section_mode = False
            if "physical weapon" in title:
                kind = "physical"
                section_mode = True
                continue
            if "magic weapon" in title:
                kind = "magic"
                # NG magic weapons use one table without subcategory headings.
                category = "magic_weapon"
                category_label = CATEGORY_LABELS.get("magic weapon", "Магическое оружие")
                section_mode = True
                continue
            for gk in ARMOR_GROUP_LABELS:
                if gk in title:
                    group_key = gk
                    section_mode = True
                    break
            continue

        if node.name == "p":
            if not section_mode:
                continue
            bold = node.find("b")
            if bold is None:
                continue
            sub_raw = heading_text(bold)
            sub_key = sub_raw.lower()
            if group_key is not None:
                kind, category, category_label = classify_armor_sub(group_key, sub_key, sub_raw)
            elif kind in ("physical", "magic"):
                category = slugify(sub_raw)
                category_label = CATEGORY_LABELS.get(sub_key, sub_raw)
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

        if grade not in {"NG", "D"} or kind is None or category is None:
            continue
        parse_upgrade_table(
            node,
            grade=grade,
            kind=kind,
            category=category,
            category_label=category_label or category,
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
    by_kind: dict[str, int] = {}
    for u in payload["upgrades"]:
        by_kind[u["kind"]] = by_kind.get(u["kind"], 0) + 1
    kinds = ", ".join(f"{k}={v}" for k, v in sorted(by_kind.items()))
    print(
        f"Wrote {OUT_PATH.name}: {ng} NG + {d} D upgrade rows ({kinds}), "
        f"{len(payload['items'])} items"
    )


if __name__ == "__main__":
    main()
