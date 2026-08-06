#!/usr/bin/env python3
"""Fetch selected entities from masterwork.wiki/lu4-b-w-c into the local /lu4/ library.

Rewrites chronicle URLs to /lu4/ so existing parsers keep working, refreshes
raw HTML + library data/pages/catalog rows, and optionally rebuilds datasets.
"""
from __future__ import annotations

import argparse
import html as html_module
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from bs4 import BeautifulSoup  # noqa: E402

WIKI = ROOT / "data" / "wiki" / "library"
RAW = WIKI / "raw" / "lu4"
DATA = WIKI / "data"
PAGES = WIKI / "pages"
CATALOG = WIKI / "index" / "catalog.jsonl"

CHRONICLE = "lu4-b-w-c"
BASE = f"https://masterwork.wiki/{CHRONICLE}"
UA = {"User-Agent": "Mozilla/5.0 (compatible; Lu4AnaliticsSync/1.0)"}

ENTITY_RE = re.compile(rf"/{CHRONICLE}/(item|set|npc)/(\d+)-([a-z0-9-]+)")
PAGINATION_RE = re.compile(r"(?:dropPage|spoilPage)=(\d+)")
FAMILY_SLUG_RE = re.compile(r"(sages-worn|half-plate|sages-rag)")
STAT_LABELS = (
    "Grade",
    "Type",
    "P. Def.",
    "M. Def.",
    "Shield Def.",
    "Weight",
    "Crystal Amount",
    "NPC Sell Price",
    "MP Bonus",
)


def in_family(kind: str, slug: str) -> bool:
    if kind == "set":
        return bool(FAMILY_SLUG_RE.search(slug or ""))
    if kind == "item":
        return bool(FAMILY_SLUG_RE.search(slug or ""))
    return False

# Seed entities discovered from B-W-C search/set pages.
SEED: list[tuple[str, int, str]] = [
    # Sage's Worn
    ("item", 438, "sages-worn-robe"),
    ("item", 1125, "sages-worn-boots"),
    ("item", 1953, "sages-worn-robe-lining"),
    ("item", 1957, "sages-worn-boots-part"),
    ("item", 2198, "recipe-sages-worn-robe"),
    ("item", 2202, "recipe-sages-worn-boots"),
    ("item", 2451, "sages-worn-gloves"),
    ("item", 2933, "sages-worn-gloves-lining"),
    ("item", 2986, "recipe-sages-worn-gloves"),
    ("set", 919, "sages-worn-robe"),
    # Half Plate
    ("item", 61, "half-plate-gauntlets"),
    ("item", 353, "half-plate-armor"),
    ("item", 380, "half-plate-gaiters"),
    ("item", 712, "half-plate-armor"),
    ("item", 1949, "half-plate-gauntlets-design"),
    ("item", 1950, "half-plate-temper"),
    ("item", 1951, "half-plate-gaiters-part"),
    ("item", 2194, "recipe-half-plate-gauntlets"),
    ("item", 2195, "recipe-half-plate-armor"),
    ("item", 2196, "recipe-half-plate-gaiters"),
    ("item", 2412, "half-plate-helmet"),
    ("item", 2428, "half-plate-boots"),
    ("item", 2494, "half-plate-shield"),
    ("item", 2930, "half-plate-helmet-design"),
    ("item", 2932, "half-plate-boots-design"),
    ("item", 2934, "half-plate-shield-fragment"),
    ("item", 2983, "recipe-half-plate-helmet"),
    ("item", 2985, "recipe-half-plate-boots"),
    ("item", 2987, "recipe-half-plate-shield"),
    ("set", 910, "half-plate-armor"),
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def rewrite_html(html: str) -> str:
    html = html.replace(f"/{CHRONICLE}/", "/lu4/")
    html = html.replace(f"https://masterwork.wiki/{CHRONICLE}/", "https://masterwork.wiki/lu4/")
    html = html.replace(f"masterwork.wiki/{CHRONICLE}", "masterwork.wiki/lu4")
    return html


def fetch(url: str, *, retries: int = 3) -> str:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read().decode("utf-8", "replace")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last}")


def entity_key(kind: str, eid: int) -> str:
    return f"{kind}:{eid}"


def local_url(kind: str, eid: int, slug: str) -> str:
    return f"/lu4/{kind}/{eid}-{slug}"


def source_url(kind: str, eid: int, slug: str) -> str:
    return f"{BASE}/{kind}/{eid}-{slug}"


def clear_entity_files(kind: str, eid: int) -> None:
    raw_dir = RAW / kind
    if raw_dir.is_dir():
        for path in raw_dir.glob(f"{eid}-*"):
            path.unlink()
    data_dir = DATA / kind
    if data_dir.is_dir():
        for path in data_dir.glob(f"{eid}-*.json"):
            path.unlink()
    pages_dir = PAGES / kind
    if pages_dir.is_dir():
        for path in pages_dir.glob(f"{eid}-*.md"):
            path.unlink()


def write_raw(kind: str, stem: str, source: str, html: str) -> Path:
    out_dir = RAW / kind
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{stem}.html"
    banner = f"<!-- saved-from: {source}\n     fetched-at: {_now()} -->\n"
    path.write_text(banner + html, encoding="utf-8")
    return path


def extract_entities(html: str) -> list[tuple[str, int, str]]:
    found: dict[tuple[str, int], str] = {}
    for kind, eid_s, slug in ENTITY_RE.findall(html):
        eid = int(eid_s)
        # Prefer longer/more specific slug if duplicates appear.
        prev = found.get((kind, eid))
        if prev is None or len(slug) > len(prev):
            found[(kind, eid)] = slug
    return [(kind, eid, slug) for (kind, eid), slug in found.items()]


def extract_pagination(html: str, kind: str, eid: int, slug: str) -> list[str]:
    """Return absolute B-W-C URLs for drop/spoil pages referenced on the item."""
    urls: set[str] = set()
    base_path = f"/{CHRONICLE}/item/{eid}-{slug}"
    for href in re.findall(r'href="([^"]+)"', html):
        if "dropPage=" not in href and "spoilPage=" not in href:
            continue
        full = urllib.parse.urljoin(BASE + "/", href)
        parsed = urllib.parse.urlparse(full)
        if f"/item/{eid}-" not in parsed.path and parsed.path != base_path:
            # Keep only pages for this item.
            if f"/{eid}-" not in parsed.path:
                continue
        qs = urllib.parse.parse_qs(parsed.query)
        parts: list[str] = []
        if "dropPage" in qs:
            parts.append(f"dropPage_{qs['dropPage'][0]}")
        if "spoilPage" in qs:
            parts.append(f"spoilPage_{qs['spoilPage'][0]}")
        if not parts:
            continue
        urls.add(full)
    return sorted(urls)


def pagination_stem(slug_stem: str, url: str) -> str:
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    bits: list[str] = []
    if "dropPage" in qs:
        bits.append(f"dropPage_{qs['dropPage'][0]}")
    if "spoilPage" in qs:
        bits.append(f"spoilPage_{qs['spoilPage'][0]}")
    suffix = "_".join(bits)
    return f"{slug_stem}__{suffix}" if suffix else slug_stem


def parse_title_name(soup: BeautifulSoup, kind: str) -> str:
    title = _clean(soup.title.get_text() if soup.title else "")
    title = html_module.unescape(title)
    for prefix in (
        "Lu4: B-W-C Wiki: Item ",
        "Lu4: B-W-C Wiki: Set ",
        "Lu4: B-W-C Wiki: NPC ",
        "Lu4 Wiki: Item ",
        "Lu4 Wiki: Set ",
        "Lu4 Wiki: NPC ",
    ):
        if title.startswith(prefix):
            title = title[len(prefix) :]
            break
    if kind == "set" and title.lower().startswith("set "):
        title = title[4:]
    return title or f"{kind}"


def parse_stats(soup: BeautifulSoup) -> dict[str, str]:
    stats: dict[str, str] = {}
    for line in soup.select("#result-stats .stat_line, .recipe_result .stat_line, .item_part .stat_line"):
        name_el = line.select_one(".stat_name")
        if not name_el:
            # Set effect / free text line
            text = _clean(line.get_text())
            if text and "Set Parts" not in stats and "effect" not in stats:
                # Keep first free-text as effect-ish for sets.
                stats.setdefault("Effect", text)
            continue
        key = _clean(name_el.get_text())
        val_el = line.select_one(".stat_value, .stat_describe")
        val = _clean(val_el.get_text()) if val_el else _clean(line.get_text().replace(key, "", 1))
        if key and val:
            stats[key] = val

    # Set parts line
    parts = []
    for link in soup.select('.item_part a.item-name, a.item-name[href*="/set/"], a.item-name[href*="/item/"]'):
        pass
    set_parts_block = soup.select_one(".item_part")
    if set_parts_block:
        part_names = []
        for link in set_parts_block.select('a.item-name[href*="/item/"]'):
            name_el = link.select_one(".item-name__content") or link.select_one(".item-name__class-1")
            name = _clean(name_el.get_text()) if name_el else _clean(link.get_text())
            if name:
                part_names.append(name)
        if part_names:
            stats["Set Parts"] = " ".join(part_names)

    # Useful labels from item head
    for label in STAT_LABELS:
        if label in stats:
            continue
    grade = soup.select_one(".item_title .item-grade, .item-grade")
    if grade and "Grade" not in stats:
        stats["Grade"] = _clean(grade.get_text())
    type_el = soup.select_one(".item-name__type")
    if type_el and "Type" not in stats:
        stats["Type"] = _clean(type_el.get_text())
    return stats


def parse_materials(soup: BeautifulSoup) -> list[dict[str, Any]]:
    materials: list[dict[str, Any]] = []
    for row in soup.select(".recipe_content .flex-row, .materials .flex-row, .recipe_materials .flex-row"):
        link = row.select_one('a.item-name[href*="/item/"]')
        if not link:
            continue
        href = link.get("href") or ""
        m = re.search(r"/item/(\d+)-([a-z0-9-]+)", href)
        if not m:
            continue
        name_el = link.select_one(".item-name__content") or link.select_one(".item-name__class-1")
        name = _clean(name_el.get_text()) if name_el else _clean(link.get_text())
        cells = row.select(".flex-cell")
        amount = _clean(cells[1].get_text()) if len(cells) >= 2 else ""
        materials.append(
            {
                "key": f"item:{int(m.group(1))}",
                "type": "item",
                "id": int(m.group(1)),
                "name": name,
                "amount": amount,
                "url": f"/lu4/item/{m.group(1)}-{m.group(2)}",
            }
        )
    return materials


def parse_links(html: str, self_key: str) -> list[dict[str, Any]]:
    links: list[dict[str, Any]] = []
    seen: set[str] = set()
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.select("a[href]"):
        href = a.get("href") or ""
        m = re.search(r"/lu4/(item|set|npc)/(\d+)-([a-z0-9-]+)", href)
        if not m:
            continue
        kind, eid_s, slug = m.group(1), m.group(2), m.group(3)
        key = f"{kind}:{int(eid_s)}"
        if key == self_key or key in seen:
            continue
        seen.add(key)
        name_el = a.select_one(".item-name__content") or a.select_one(".item-name__class-1")
        name = _clean(name_el.get_text()) if name_el else _clean(a.get_text())
        name = re.sub(r"\s+Lv\.\s*\d+$", "", name).strip()
        links.append(
            {
                "key": key,
                "type": kind,
                "id": int(eid_s),
                "name": name or key,
                "url": f"/lu4/{kind}/{eid_s}-{slug}",
            }
        )
    return links


def build_page_md(kind: str, eid: int, slug: str, name: str, stats: dict[str, str], html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    content = soup.select_one("#pjax-container, .item_part, .npc_part, main") or soup.body
    text = _clean(content.get_text("\n")) if content else ""
    # Keep markdown reasonably small.
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    body = "\n".join(lines[:120])
    md = [
        f"# {name}",
        "",
        f"- Source: {source_url(kind, eid, slug)}",
        f"- Path: {local_url(kind, eid, slug)}",
        f"- Type: {kind}",
        f"- Key: {entity_key(kind, eid)}",
        "",
        "## Stats",
    ]
    for k, v in stats.items():
        md.append(f"- {k}: {v}")
    md.extend(["", "## Content", body, ""])
    return "\n".join(md)


def write_library_entity(kind: str, eid: int, slug: str, html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    name = parse_title_name(soup, kind)
    stats = parse_stats(soup)
    materials = parse_materials(soup) if kind == "item" else []
    key = entity_key(kind, eid)
    url = local_url(kind, eid, slug)
    # Keep source_url pointing at B-W-C for freshness, local url stays /lu4/.
    src_live = source_url(kind, eid, slug)
    links = parse_links(html, key)
    stem = f"{eid}-{slug}"
    data_obj = {
        "key": key,
        "type": kind,
        "id": eid,
        "name": name,
        "url": url,
        "source_url": src_live,
        "raw_html": f"library/raw/lu4/{kind}/{stem}.html",
        "stats": stats,
        "materials": materials,
        "links": links,
    }
    data_path = DATA / kind / f"{stem}.json"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text(json.dumps(data_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    page_path = PAGES / kind / f"{stem}.md"
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_text(build_page_md(kind, eid, slug, name, stats, html), encoding="utf-8")

    summary_bits = [kind]
    if stats.get("Grade"):
        summary_bits.append(f"Grade {stats['Grade']}")
    if materials:
        summary_bits.append(f"{len(materials)} materials")
    if stats.get("Set Parts"):
        summary_bits.append("set")
    catalog_row = {
        "key": key,
        "id": eid,
        "type": kind,
        "name": name,
        "url": url,
        "source_url": src_live,
        "data": f"library/data/{kind}/{stem}.json",
        "page": f"library/pages/{kind}/{stem}.md",
        "summary": ", ".join(summary_bits),
    }
    return catalog_row


def upsert_catalog(rows: list[dict[str, Any]]) -> None:
    by_key = {row["key"]: row for row in rows}
    existing: list[dict[str, Any]] = []
    if CATALOG.is_file():
        for line in CATALOG.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            existing.append(json.loads(line))
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in existing:
        key = row.get("key")
        if key in by_key:
            out.append(by_key[key])
            seen.add(key)
        else:
            out.append(row)
    for key, row in by_key.items():
        if key not in seen:
            out.append(row)
    CATALOG.parent.mkdir(parents=True, exist_ok=True)
    with CATALOG.open("w", encoding="utf-8") as f:
        for row in out:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _family_npc_ids() -> set[int]:
    """NPC ids linked from already-indexed family item/set JSON."""
    ids: set[int] = set()
    for kind in ("item", "set"):
        data_dir = DATA / kind
        if not data_dir.is_dir():
            continue
        for path in data_dir.glob("*.json"):
            if not in_family(kind, path.stem.split("-", 1)[-1]):
                continue
            try:
                obj = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            for link in obj.get("links") or []:
                if link.get("type") == "npc" and isinstance(link.get("id"), int):
                    ids.add(int(link["id"]))
    return ids


def rebuild_from_existing_raw() -> list[dict[str, Any]]:
    """Rebuild data/pages/catalog for family entities already on disk."""
    catalog_rows: list[dict[str, Any]] = []
    npc_ids = _family_npc_ids()
    for kind in ("item", "set", "npc"):
        raw_dir = RAW / kind
        if not raw_dir.is_dir():
            continue
        for path in sorted(raw_dir.glob("*.html")):
            if "__" in path.name:
                continue
            m = re.match(r"^(\d+)-([a-z0-9-]+)$", path.stem)
            if not m:
                continue
            eid = int(m.group(1))
            slug = m.group(2)
            if kind in {"item", "set"} and not in_family(kind, slug):
                continue
            if kind == "npc" and eid not in npc_ids:
                continue
            html = path.read_text(encoding="utf-8", errors="replace")
            # Ensure parsers see /lu4/ links.
            if f"/{CHRONICLE}/" in html:
                html = rewrite_html(html)
                path.write_text(html, encoding="utf-8")
            row = write_library_entity(kind, eid, slug, html)
            catalog_rows.append(row)
            print(f"indexed {kind}/{path.stem}")
    by_key = {r["key"]: r for r in catalog_rows}
    rows = list(by_key.values())
    upsert_catalog(rows)
    print(f"Catalog upserted: {len(rows)} entities")
    return rows


def sync(
    *,
    follow_npcs: bool = True,
    follow_items: bool = True,
    sleep_s: float = 0.35,
) -> list[dict[str, Any]]:
    # queue entries: kind, id, slug, depth
    queue: list[tuple[str, int, str, int]] = [(k, i, s, 0) for k, i, s in SEED]
    seen: set[tuple[str, int]] = set()
    catalog_rows: list[dict[str, Any]] = []

    while queue:
        kind, eid, slug, depth = queue.pop(0)
        ident = (kind, eid)
        if ident in seen:
            continue
        seen.add(ident)

        live = source_url(kind, eid, slug)
        print(f"fetch [d{depth}] {live}")
        try:
            raw_html = fetch(live)
        except Exception as exc:  # noqa: BLE001
            print(f"  SKIP {live}: {exc}")
            continue

        # Resolve canonical slug from the fetched HTML if redirected/changed.
        entities_on_page = extract_entities(raw_html)
        for ek, ee, es in entities_on_page:
            if ek == kind and ee == eid:
                slug = es
                break

        html = rewrite_html(raw_html)
        clear_entity_files(kind, eid)
        stem = f"{eid}-{slug}"
        write_raw(kind, stem, live, html)
        row = write_library_entity(kind, eid, slug, html)
        catalog_rows.append(row)
        print(f"  saved {kind}/{stem}")

        # Pagination variants only for family items (avoid hammering common mats).
        if kind == "item" and in_family(kind, slug):
            for page_url in extract_pagination(raw_html, kind, eid, slug):
                time.sleep(max(sleep_s, 0.8))
                try:
                    page_html = rewrite_html(fetch(page_url))
                except Exception as exc:  # noqa: BLE001
                    print(f"  SKIP page {page_url}: {exc}")
                    time.sleep(3.0)
                    continue
                pstem = pagination_stem(stem, page_url)
                write_raw(kind, pstem, page_url, page_html)
                print(f"  saved page {pstem}")

        # Expansion rules (keep crawl inside Sage's Worn / Half Plate family):
        # - from family items/sets: follow family items/sets + NPCs
        # - never refetch generic materials (leather/stem/...) — already in library
        # - NPCs: no further expansion
        if kind != "npc" and in_family(kind, slug):
            for ek, ee, es in entities_on_page:
                if (ek, ee) in seen:
                    continue
                if ek in {"item", "set"} and follow_items and in_family(ek, es):
                    queue.append((ek, ee, es, depth + 1))
                elif ek == "npc" and follow_npcs:
                    queue.append((ek, ee, es, depth + 1))

        time.sleep(sleep_s)

    # Deduplicate catalog rows by key (last wins).
    by_key = {r["key"]: r for r in catalog_rows}
    catalog_rows = list(by_key.values())
    upsert_catalog(catalog_rows)
    print(f"Catalog upserted: {len(catalog_rows)} entities")
    return catalog_rows


def rebuild_datasets() -> None:
    from build_craft_catalog import OUT as CRAFT_OUT
    from build_craft_catalog import build_catalog
    from build_items_encyclopedia import OUT as ENC_OUT
    from build_items_encyclopedia import finalize_payload, rebuild_from_wiki

    print("Building craft_catalog.json ...")
    craft = build_catalog()
    CRAFT_OUT.parent.mkdir(parents=True, exist_ok=True)
    CRAFT_OUT.write_text(json.dumps(craft, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  products={craft.get('product_count')} variants={craft.get('variant_count')}")

    print("Building items_encyclopedia.json ...")
    raw = rebuild_from_wiki()
    payload = finalize_payload(raw, craft_catalog=craft)
    payload["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    ENC_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  items={payload.get('item_count')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Sage's Worn / Half Plate from lu4-b-w-c")
    parser.add_argument("--no-npcs", action="store_true", help="Do not fetch related NPC pages")
    parser.add_argument("--no-follow-items", action="store_true", help="Do not follow linked items")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild craft/encyclopedia datasets")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Do not fetch; rebuild library layers from existing family raw HTML",
    )
    parser.add_argument("--sleep", type=float, default=0.35)
    args = parser.parse_args()

    if args.offline:
        rows = rebuild_from_existing_raw()
    else:
        rows = sync(
            follow_npcs=not args.no_npcs,
            follow_items=not args.no_follow_items,
            sleep_s=args.sleep,
        )
    if args.rebuild:
        rebuild_datasets()
    print("Done.", len(rows), "entities synced")


if __name__ == "__main__":
    main()
