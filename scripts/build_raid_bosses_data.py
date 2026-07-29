"""Build raid bosses dataset from l4map markers + npc_details + local wiki."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKERS = ROOT / "data" / "raid-bosses" / "boss_markers_lu4.html"
DETAILS = ROOT / "data" / "raid-bosses" / "npc_details.json"
ICON_LOOKUPS = ROOT / "data" / "raid-bosses" / "icon_lookups.json"
HOW_TO_REACH = ROOT / "data" / "raid-bosses" / "how_to_reach.json"
WIKI_BY_NAME = ROOT.parent / "library" / "index" / "by_name.json"
WIKI_NPC_DIR = ROOT.parent / "library" / "data" / "npc"
OUT_JSON = ROOT / "data" / "datasets" / "raid_bosses.json"
RAID_IMAGES = ROOT / "data" / "wiki" / "images" / "raid-bosses"

MAP_WIDTH = 1808
MAP_HEIGHT = 2658

MARKER_TAG_RE = re.compile(r"<img\s+class=\"marker_flag\"[^>]*>", re.DOTALL)
ATTR_RE = re.compile(r'([\w-]+)="([^"]*)"')
STYLE_POS_RE = re.compile(r"top:([0-9.]+)px;\s*left:([0-9.]+)px")
NPC_ID_RE = re.compile(r"/npc/(\d+)-")
LEVEL_RE = re.compile(r"\s*Lv\.\s*(\d+)\s*$")
CONTRIB_HINT = "greatest contribution"


def fix_text(s: str | None) -> str | None:
    if s is None:
        return None
    # mojibake / replacement for ± from scraped sources
    return (
        s.replace("\ufffd", "±")
        .replace(" â†’ ", " → ")
        .replace("â†’", "→")
        .strip()
    )


def parse_hpmp(raw: str | None) -> tuple[str | None, str | None]:
    if not raw:
        return None, None
    parts = [p.strip() for p in raw.split("/")]
    if len(parts) >= 2:
        return parts[0], parts[1]
    return raw, None


def parse_pair(raw: str | None) -> tuple[str | None, str | None]:
    return parse_hpmp(raw)


def lore_from_skills(skills: list[dict]) -> str | None:
    for skill in skills:
        if skill.get("name") != "Raid Boss":
            continue
        desc = fix_text(skill.get("desc") or "") or ""
        if not desc or CONTRIB_HINT in desc:
            continue
        return desc
    return None


def normalize_skills(skills: list[dict]) -> list[dict]:
    out = []
    for skill in skills:
        name = skill.get("name") or ""
        desc = fix_text(skill.get("desc") or "") or ""
        if name == "Raid Boss" and (CONTRIB_HINT in desc or not desc):
            # keep mechanic note once
            if any(s["name"] == "Raid Boss" and CONTRIB_HINT in (s.get("desc") or "") for s in out):
                continue
        if name == "Raid Boss" and CONTRIB_HINT not in desc and desc:
            continue  # lore shown separately
        out.append(
            {
                "name": name,
                "level": skill.get("level"),
                "desc": desc or None,
            }
        )
    return out


def normalize_drops(
    groups: list[dict] | None,
    icon_items: dict[str, str],
    icon_by_name: dict[str, str],
    wiki_item_ids: dict[str, int],
) -> list[dict]:
    if not groups:
        return []
    result = []
    for g in groups:
        items = []
        for it in g.get("items") or []:
            name = it.get("name") or ""
            grade = it.get("grade")
            icon = None
            if name and grade:
                icon = icon_items.get(f"{name}|{grade}")
            if not icon and name:
                icon = icon_by_name.get(name)
            item_id = wiki_item_ids.get(name.lower()) if name else None
            items.append(
                {
                    "name": name or None,
                    "grade": grade,
                    "amount": it.get("amount"),
                    "chance": it.get("chance"),
                    "icon": icon,
                    "itemId": item_id,
                }
            )
        if items:
            result.append({"groupChance": g.get("groupChance"), "items": items})
    return result


def load_wiki_item_ids() -> dict[str, int]:
    if not WIKI_BY_NAME.exists():
        return {}
    raw = json.loads(WIKI_BY_NAME.read_text(encoding="utf-8"))
    out: dict[str, int] = {}
    for key, refs in raw.items():
        if not isinstance(refs, list) or not refs:
            continue
        # "lu4 wiki: item proof of loyalty" -> proof of loyalty
        lower = key.lower()
        marker = "item "
        idx = lower.find(marker)
        if idx < 0:
            continue
        name = lower[idx + len(marker) :].strip()
        for ref in refs:
            if isinstance(ref, str) and ref.startswith("item:"):
                try:
                    out[name] = int(ref.split(":", 1)[1])
                except ValueError:
                    pass
                break
    return out


def wiki_location(npc_id: int) -> str | None:
    matches = list(WIKI_NPC_DIR.glob(f"{npc_id}-*.json"))
    # prefer non-paginated base file
    base = [p for p in matches if "__" not in p.name]
    path = (base[0] if base else matches[0]) if matches else None
    if not path:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    loc = (data.get("stats") or {}).get("Location")
    if loc:
        return loc
    for link in data.get("links") or []:
        if link.get("type") == "location" and link.get("name"):
            return link["name"]
    return None


def wiki_slug_url(npc_id: int, fallback_url: str) -> str:
    matches = list(WIKI_NPC_DIR.glob(f"{npc_id}-*.json"))
    base = [p for p in matches if "__" not in p.name]
    path = (base[0] if base else matches[0]) if matches else None
    if path:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("url"):
                return f"https://masterwork.wiki{data['url']}"
        except Exception:
            pass
    return fallback_url


def parse_markers(html: str) -> list[dict]:
    # Drop HTML comments so disabled spawn points are not imported
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
    bosses: list[dict] = []
    seen: set[tuple[int | None, float, float]] = set()
    for tag in MARKER_TAG_RE.finditer(html):
        attrs = dict(ATTR_RE.findall(tag.group(0)))
        label = attrs.get("data-label", "").strip()
        url = attrs.get("data-url", "")
        image = attrs.get("data-image") or None
        pos = STYLE_POS_RE.search(attrs.get("style", ""))
        if not label or not pos:
            continue
        top, left = pos.groups()
        npc_m = NPC_ID_RE.search(url)
        lvl_m = LEVEL_RE.search(label)
        name = LEVEL_RE.sub("", label).strip() if lvl_m else label
        npc_id = int(npc_m.group(1)) if npc_m else None
        x, y = float(left), float(top)
        key = (npc_id, x, y)
        if key in seen:
            continue
        seen.add(key)
        bosses.append(
            {
                "name": name,
                "label": label,
                "level": int(lvl_m.group(1)) if lvl_m else None,
                "npcId": npc_id,
                "wikiUrl": url,
                "image": image,
                "x": x,
                "y": y,
            }
        )
    return bosses


def raid_boss_image(npc_id: int | None, remote_url: str | None) -> str | None:
    if npc_id is not None:
        for ext in (".jpg", ".jpeg", ".png", ".webp"):
            path = RAID_IMAGES / f"{npc_id}{ext}"
            if path.is_file() and path.stat().st_size > 50:
                return f"images/raid-bosses/{npc_id}{ext}"
    return remote_url


def main() -> None:
    html = MARKERS.read_text(encoding="utf-8")
    markers = parse_markers(html)
    details_raw = json.loads(DETAILS.read_text(encoding="utf-8"))
    icon_lookups = json.loads(ICON_LOOKUPS.read_text(encoding="utf-8")) if ICON_LOOKUPS.exists() else {}
    icon_items = icon_lookups.get("items") or {}
    icon_by_name = icon_lookups.get("itemsByName") or {}
    wiki_item_ids = load_wiki_item_ids()

    bosses = []
    missing = []
    for m in markers:
        npc_id = m["npcId"]
        detail = details_raw.get(str(npc_id), {}) if npc_id is not None else {}
        stats_raw = detail.get("stats") or {}
        skills = detail.get("skills") or []
        hp, mp = parse_hpmp(fix_text(stats_raw.get("hpmp")))
        p_atk, m_atk = parse_pair(fix_text(stats_raw.get("atk")))
        p_def, m_def = parse_pair(fix_text(stats_raw.get("def")))
        acc, eva = parse_pair(fix_text(stats_raw.get("acceva")))
        exp, sp = parse_pair(fix_text(stats_raw.get("expsp")))

        if not detail:
            missing.append(npc_id)

        location = wiki_location(npc_id) if npc_id else None
        wiki_url = wiki_slug_url(npc_id, m["wikiUrl"]) if npc_id else m["wikiUrl"]

        bosses.append(
            {
                "id": npc_id,
                "name": m["name"],
                "level": m["level"],
                "x": m["x"],
                "y": m["y"],
                "image": raid_boss_image(npc_id, m["image"]),
                "wikiUrl": wiki_url,
                "location": location,
                "respawn": fix_text(stats_raw.get("respawn")),
                "stats": {
                    "hp": hp,
                    "mp": mp,
                    "pAtk": p_atk,
                    "mAtk": m_atk,
                    "pDef": p_def,
                    "mDef": m_def,
                    "accuracy": acc,
                    "evasion": eva,
                    "exp": exp,
                    "sp": sp,
                    "atkAttr": fix_text(stats_raw.get("atkAttr")),
                    "defAttr": fix_text(stats_raw.get("defAttr")),
                },
                "lore": lore_from_skills(skills),
                "skills": normalize_skills(skills),
                "drops": normalize_drops(
                    detail.get("drops"), icon_items, icon_by_name, wiki_item_ids
                ),
            }
        )

    bosses.sort(key=lambda b: (b["level"] or 0, b["name"] or ""))

    routes: dict[str, str] = {}
    if HOW_TO_REACH.is_file():
        raw_routes = json.loads(HOW_TO_REACH.read_text(encoding="utf-8"))
        if isinstance(raw_routes, dict):
            routes = {str(k): str(v) for k, v in raw_routes.items() if v}
    for boss in bosses:
        npc_id = boss.get("id")
        route = routes.get(str(npc_id)) if npc_id is not None else None
        if route:
            boss["howToReach"] = route

    payload = {
        "source": {
            "map": "https://l4map.com/",
            "wikiPost": "https://masterwork.wiki/lu4/posts/post/385-lu4-raid-bosses",
        },
        "map": {
            "width": MAP_WIDTH,
            "height": MAP_HEIGHT,
            "image": "/raid-map/map_lu4.webp",
            "flag": "/raid-map/flag.png",
        },
        "bosses": bosses,
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(bosses)} bosses -> {OUT_JSON}")
    print(f"Missing details: {len(missing)} {missing[:10]}")
    with_icons = sum(
        1
        for b in bosses
        for g in b["drops"]
        for it in g["items"]
        if it.get("icon")
    )
    print(f"Drop rows with icons: {with_icons}")


if __name__ == "__main__":
    main()
