#!/usr/bin/env python3
"""Merge wikilu4 (/lu4-b-w-c mirror) into the live data/wiki/library (/lu4).

Rule: if the new wiki has a valid entity → use it (including drop/spoil).
If the new wiki lacks an entity → keep the old one. Quests are never touched.

Reusable after each wikilu4 mirror refresh:

  py -3 scripts/merge_bwc_wiki_into_library.py --dry-run
  py -3 scripts/merge_bwc_wiki_into_library.py --apply --rebuild-datasets --sync-images
"""
from __future__ import annotations

import argparse
import html as html_module
import json
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from bs4 import BeautifulSoup  # noqa: E402

CHRONICLE = "lu4-b-w-c"
BASE = f"https://masterwork.wiki/{CHRONICLE}"
UA = {"User-Agent": "Mozilla/5.0 (compatible; Lu4AnaliticsMerge/1.0)"}

DEFAULT_NEW = ROOT / "wikilu4" / "lu4-b-w-c"
DEFAULT_LIB = ROOT / "data" / "wiki" / "library"
IMAGES_DIR = ROOT / "data" / "wiki" / "images"
I64_MIRROR = ROOT / "wikilu4" / "i64"

SCOPE_KINDS = ("item", "npc", "set", "skill", "class", "location", "posts")
SKIP_KINDS = frozenset({"quest"})

ENTITY_STEM_RE = re.compile(r"^(\d+)(?:-(.+))?$")
PAGINATION_RE = re.compile(
    r"__((?:dropPage|spoilPage)_\d+(?:_(?:dropPage|spoilPage)_\d+)*)$"
)
# Mirror encodes query as __dropPage_1__spoilPage_2; library uses single _
MIRROR_PAG_RE = re.compile(
    r"__((?:dropPage|spoilPage)_\d+(?:__(?:dropPage|spoilPage)_\d+)*)$"
)
TITLE_KIND_RE = re.compile(
    r"Wiki:\s*(Item|Npc|Quest|Set|Class|Location|Skill|Post)\s*(.*)$",
    re.I,
)
DROP_PAGE_RE = re.compile(r"(?:dropPage|spoilPage)=(\d+)")
I64_ICON_RE = re.compile(r"/i64/([^/?#\"']+)")
PNG_MAGIC = b"\x89PNG"
MIN_IMAGE_BYTES = 50

KIND_TITLE = {
    "item": "item",
    "npc": "npc",
    "quest": "quest",
    "set": "set",
    "class": "class",
    "location": "location",
    "skill": "skill",
    "posts": "post",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _clean(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def norm_name(s: str) -> str:
    s = html_module.unescape(s or "").lower()
    for pref in (
        "item ",
        "npc ",
        "quest ",
        "set ",
        "class ",
        "location ",
        "skill ",
        "post ",
    ):
        if s.startswith(pref):
            s = s[len(pref) :]
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def rewrite_html(html: str) -> str:
    html = html.replace(f"/{CHRONICLE}/", "/lu4/")
    html = html.replace(f"https://masterwork.wiki/{CHRONICLE}/", "https://masterwork.wiki/lu4/")
    html = html.replace(f"masterwork.wiki/{CHRONICLE}", "masterwork.wiki/lu4")
    html = html.replace(f"/en/{CHRONICLE}/", "/lu4/")
    # Search widget project flag — keep parsers/UI consistent with /lu4 library.
    html = html.replace(f"project={CHRONICLE}", "project=lu4")
    return html


def strip_banner(html: str) -> str:
    return re.sub(r"^<!-- saved-from:.*?-->\s*", "", html, count=1, flags=re.S)


def entity_key(kind: str, eid: int) -> str:
    return f"{kind}:{eid}"


def parse_title(html: str) -> tuple[str | None, str]:
    # Fast path: regex on <title> — avoid BeautifulSoup for inventory.
    m_tag = re.search(r"<title[^>]*>(.*?)</title>", html[:20000], re.I | re.S)
    title = _clean(html_module.unescape(m_tag.group(1))) if m_tag else ""
    title = title.replace("&#039;", "'").replace("&amp;", "&")
    m = TITLE_KIND_RE.search(title)
    if not m:
        for kind_label in ("Item", "Npc", "Quest", "Set", "Class", "Location", "Skill"):
            token = f"Wiki: {kind_label} "
            idx = title.find(token)
            if idx >= 0:
                return kind_label.lower(), title[idx + len(token) :].strip()
        return None, title
    return m.group(1).lower(), _clean(m.group(2))


def normalize_pag_suffix(suffix: str) -> str:
    """Normalize mirror __a__b style to library __a_b style."""
    parts = [p for p in suffix.strip("_").split("__") if p]
    return "__" + "_".join(parts)


def split_stem(stem: str) -> tuple[str, str | None]:
    """Return (base_stem, pagination_suffix_or_None)."""
    m = MIRROR_PAG_RE.search(stem) or PAGINATION_RE.search(stem)
    if not m:
        return stem, None
    base = stem[: m.start()]
    suffix = normalize_pag_suffix(m.group(1) if m.lastindex else m.group(0))
    return base, suffix


def parse_entity_stem(stem: str) -> tuple[int, str] | None:
    base, _ = split_stem(stem)
    m = ENTITY_STEM_RE.match(base)
    if not m:
        return None
    eid = int(m.group(1))
    slug = m.group(2) or ""
    return eid, slug


@dataclass
class FileRef:
    path: Path
    rel: str  # relative to kind root, posix
    stem: str
    base_stem: str
    pag_suffix: str | None
    eid: int
    slug: str


@dataclass
class EntityInv:
    kind: str
    eid: int
    slug: str = ""
    base: FileRef | None = None
    variants: list[FileRef] = field(default_factory=list)
    nested: list[FileRef] = field(default_factory=list)  # skill/class levels
    name: str = ""
    title_kind: str | None = None

    @property
    def stem(self) -> str:
        if self.slug:
            return f"{self.eid}-{self.slug}"
        return str(self.eid)


def inventory_kind(kind_root: Path, kind: str) -> dict[int, EntityInv]:
    out: dict[int, EntityInv] = {}
    if not kind_root.is_dir():
        return out

    def ensure(eid: int, slug: str) -> EntityInv:
        ent = out.get(eid)
        if ent is None:
            ent = EntityInv(kind=kind, eid=eid, slug=slug)
            out[eid] = ent
        elif slug and not ent.slug:
            ent.slug = slug
        return ent

    bases_by_id: dict[int, list[FileRef]] = defaultdict(list)

    # Top-level HTML (base + pagination)
    for path in kind_root.glob("*.html"):
        parsed = parse_entity_stem(path.stem)
        if not parsed:
            continue
        eid, slug = parsed
        base_stem, pag = split_stem(path.stem)
        base_parsed = parse_entity_stem(base_stem)
        if base_parsed:
            eid, slug = base_parsed
        ref = FileRef(
            path=path,
            rel=path.name,
            stem=path.stem,
            base_stem=base_stem,
            pag_suffix=pag,
            eid=eid,
            slug=slug,
        )
        ent = ensure(eid, slug)
        if pag:
            ent.variants.append(ref)
        else:
            bases_by_id[eid].append(ref)

    # Choose canonical base when multiple slugs exist for one id.
    for eid, bases in bases_by_id.items():
        ent = out[eid]
        if len(bases) == 1:
            ent.base = bases[0]
            ent.slug = bases[0].slug
            continue
        # Prefer slug that matches title name; else prefer slug used by most variants;
        # else prefer shortest slug (adena over kanon-tanor).
        scored: list[tuple[int, int, FileRef]] = []
        var_slug_counts: dict[str, int] = defaultdict(int)
        for v in ent.variants:
            var_slug_counts[v.slug] += 1
        for ref in bases:
            html = strip_banner(ref.path.read_text(encoding="utf-8", errors="replace")[:20000])
            _tk, name = parse_title(html)
            name_n = norm_name(name)
            slug_n = norm_name(ref.slug.replace("-", " "))
            match = 1 if slug_n and (slug_n in name_n or name_n in slug_n) else 0
            scored.append((match, var_slug_counts.get(ref.slug, 0), ref))
        scored.sort(key=lambda t: (-t[0], -t[1], len(t[2].slug), t[2].slug))
        best = scored[0][2]
        ent.base = best
        ent.slug = best.slug

    # Nested: skill/<id>-<slug>/<level>.html and class/<id>-<slug>/<n>.html
    if kind in {"skill", "class", "posts"}:
        for path in kind_root.rglob("*.html"):
            rel = path.relative_to(kind_root)
            if len(rel.parts) < 2:
                continue
            parent = rel.parts[0]
            parsed = parse_entity_stem(parent)
            if not parsed:
                continue
            eid, slug = parsed
            ref = FileRef(
                path=path,
                rel=rel.as_posix(),
                stem=path.stem,
                base_stem=parent,
                pag_suffix=None,
                eid=eid,
                slug=slug,
            )
            ent = ensure(eid, slug)
            ent.nested.append(ref)
            if ent.base is None and kind == "skill":
                ent.slug = slug

    return out


def load_entity_meta(ent: EntityInv) -> None:
    path = ent.base.path if ent.base else (ent.nested[0].path if ent.nested else None)
    if path is None or not path.is_file():
        return
    html = strip_banner(path.read_text(encoding="utf-8", errors="replace"))
    title_kind, name = parse_title(html)
    ent.title_kind = title_kind
    ent.name = name


def is_valid_new(kind: str, ent: EntityInv) -> bool:
    if ent.base is None and not ent.nested:
        return False
    if not ent.title_kind and not ent.name:
        load_entity_meta(ent)
    expected = KIND_TITLE.get(kind)
    if ent.title_kind and expected and ent.title_kind != expected:
        # Allow posts/post soft match
        if not (kind == "posts" and ent.title_kind in {"post", "posts"}):
            return False
    return True


def max_pagination_linked(html: str) -> tuple[int, int]:
    drop_max = spoil_max = 0
    for m in re.finditer(r"dropPage=(\d+)", html):
        drop_max = max(drop_max, int(m.group(1)))
    for m in re.finditer(r"spoilPage=(\d+)", html):
        spoil_max = max(spoil_max, int(m.group(1)))
    return drop_max, spoil_max


def pagination_coverage(ent: EntityInv) -> dict[str, Any]:
    drop_pages = set()
    spoil_pages = set()
    for v in ent.variants:
        suf = v.pag_suffix or ""
        for m in re.finditer(r"dropPage_(\d+)", suf):
            drop_pages.add(int(m.group(1)))
        for m in re.finditer(r"spoilPage_(\d+)", suf):
            spoil_pages.add(int(m.group(1)))
    linked_drop = linked_spoil = 0
    if ent.base and ent.base.path.is_file():
        html = ent.base.path.read_text(encoding="utf-8", errors="replace")
        linked_drop, linked_spoil = max_pagination_linked(html)
    incomplete = (linked_drop > 0 and max(drop_pages or [0]) < linked_drop) or (
        linked_spoil > 0 and max(spoil_pages or [0]) < linked_spoil
    )
    return {
        "drop_pages": sorted(drop_pages),
        "spoil_pages": sorted(spoil_pages),
        "linked_drop_max": linked_drop,
        "linked_spoil_max": linked_spoil,
        "incomplete": incomplete,
    }


def fetch_url(url: str, *, retries: int = 3) -> str:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read().decode("utf-8", "replace")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last = exc
            time.sleep(1.2 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last}")


def extract_pagination_urls(html: str, kind: str, eid: int, slug: str) -> list[str]:
    urls: set[str] = set()
    for href in re.findall(r'href="([^"]+)"', html):
        if "dropPage=" not in href and "spoilPage=" not in href:
            continue
        full = urllib.parse.urljoin(BASE + "/", href.replace("/lu4/", f"/{CHRONICLE}/"))
        parsed = urllib.parse.urlparse(full)
        if f"/{kind}/{eid}-" not in parsed.path and f"/{kind}/{eid}" not in parsed.path:
            continue
        urls.add(full)
    return sorted(urls)


def pagination_stem_from_url(base_stem: str, url: str) -> str:
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    bits: list[str] = []
    if "dropPage" in qs:
        bits.append(f"dropPage_{qs['dropPage'][0]}")
    if "spoilPage" in qs:
        bits.append(f"spoilPage_{qs['spoilPage'][0]}")
    return f"{base_stem}__{'_'.join(bits)}" if bits else base_stem


def write_raw_file(path: Path, source: str, html: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    banner = f"<!-- saved-from: {source}\n     fetched-at: {_now()} -->\n"
    path.write_text(banner + html, encoding="utf-8")


def clear_entity_top_level(raw_kind: Path, eid: int) -> list[str]:
    removed: list[str] = []
    if not raw_kind.is_dir():
        return removed
    for path in list(raw_kind.glob(f"{eid}-*")) + list(raw_kind.glob(f"{eid}.html")):
        if path.is_file():
            removed.append(path.name)
            path.unlink()
    return removed


def clear_entity_data_pages(lib: Path, kind: str, eid: int) -> None:
    for sub in ("data", "pages"):
        d = lib / sub / kind
        if not d.is_dir():
            continue
        for path in list(d.glob(f"{eid}-*")) + list(d.glob(f"{eid}.*")):
            if path.is_file():
                path.unlink()
        # nested data/pages for skill/class
        for path in d.glob(f"{eid}-*"):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)


# --- library data/pages builders (generalized from sync_bw_c_entities) ---

STAT_LABELS = (
    "Grade",
    "Type",
    "P. Def.",
    "M. Def.",
    "P. Atk.",
    "M. Atk.",
    "Shield Def.",
    "Weight",
    "Crystal Amount",
    "NPC Sell Price",
    "MP Bonus",
    "Level",
    "HP",
    "MP",
)


def parse_stats(soup: BeautifulSoup) -> dict[str, str]:
    stats: dict[str, str] = {}
    for line in soup.select(
        "#result-stats .stat_line, .recipe_result .stat_line, .item_part .stat_line, .npc_part .stat_line"
    ):
        name_el = line.select_one(".stat_name")
        if not name_el:
            text = _clean(line.get_text())
            if text:
                stats.setdefault("Effect", text)
            continue
        key = _clean(name_el.get_text())
        val_el = line.select_one(".stat_value, .stat_describe")
        val = _clean(val_el.get_text()) if val_el else _clean(line.get_text().replace(key, "", 1))
        if key and val:
            stats[key] = val
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
        m = re.search(r"/item/(\d+)-([a-z0-9-]*)", href)
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
        m = re.search(r"/lu4/(item|set|npc|skill|class|location|quest)/(\d+)(?:-([a-z0-9-]+))?", href)
        if not m:
            continue
        kind, eid_s, slug = m.group(1), m.group(2), m.group(3) or ""
        key = f"{kind}:{int(eid_s)}"
        if key == self_key or key in seen:
            continue
        seen.add(key)
        name_el = a.select_one(".item-name__content") or a.select_one(".item-name__class-1")
        name = _clean(name_el.get_text()) if name_el else _clean(a.get_text())
        name = re.sub(r"\s+Lv\.\s*\d+$", "", name).strip()
        url = f"/lu4/{kind}/{eid_s}-{slug}" if slug else f"/lu4/{kind}/{eid_s}"
        links.append(
            {
                "key": key,
                "type": kind,
                "id": int(eid_s),
                "name": name or key,
                "url": url,
            }
        )
    return links


def build_page_md(
    kind: str, eid: int, slug: str, name: str, stats: dict[str, str], html: str, source: str
) -> str:
    soup = BeautifulSoup(html, "html.parser")
    content = soup.select_one("#pjax-container, .item_part, .npc_part, main") or soup.body
    text = _clean(content.get_text("\n")) if content else ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    body = "\n".join(lines[:120])
    url = f"/lu4/{kind}/{eid}-{slug}" if slug else f"/lu4/{kind}/{eid}"
    md = [
        f"# {name}",
        "",
        f"- Source: {source}",
        f"- Path: {url}",
        f"- Type: {kind}",
        f"- Key: {entity_key(kind, eid)}",
        "",
        "## Stats",
    ]
    for k, v in stats.items():
        md.append(f"- {k}: {v}")
    md.extend(["", "## Content", body, ""])
    return "\n".join(md)


def write_library_entity(
    lib: Path, kind: str, eid: int, slug: str, html: str, *, source_live: str
) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    _tk, name = parse_title(html)
    if not name:
        name = parse_title_fallback(soup, kind)
    stats = parse_stats(soup)
    materials = parse_materials(soup) if kind == "item" else []
    key = entity_key(kind, eid)
    url = f"/lu4/{kind}/{eid}-{slug}" if slug else f"/lu4/{kind}/{eid}"
    links = parse_links(html, key)
    stem = f"{eid}-{slug}" if slug else str(eid)
    data_obj = {
        "key": key,
        "type": kind,
        "id": eid,
        "name": name,
        "url": url,
        "source_url": source_live,
        "raw_html": f"library/raw/lu4/{kind}/{stem}.html",
        "stats": stats,
        "materials": materials,
        "links": links,
    }
    data_path = lib / "data" / kind / f"{stem}.json"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text(json.dumps(data_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    page_path = lib / "pages" / kind / f"{stem}.md"
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_text(
        build_page_md(kind, eid, slug, name, stats, html, source_live), encoding="utf-8"
    )

    summary_bits = [kind]
    if stats.get("Grade"):
        summary_bits.append(f"Grade {stats['Grade']}")
    if materials:
        summary_bits.append(f"{len(materials)} materials")
    return {
        "key": key,
        "id": eid,
        "type": kind,
        "name": name,
        "url": url,
        "source_url": source_live,
        "data": f"library/data/{kind}/{stem}.json",
        "page": f"library/pages/{kind}/{stem}.md",
        "summary": ", ".join(summary_bits),
    }


def parse_title_fallback(soup: BeautifulSoup, kind: str) -> str:
    h = soup.select_one("h1, .item_title, .item-name__content")
    return _clean(h.get_text()) if h else kind


def upsert_catalog(catalog_path: Path, rows: list[dict[str, Any]]) -> None:
    by_key = {row["key"]: row for row in rows}
    existing: list[dict[str, Any]] = []
    if catalog_path.is_file():
        for line in catalog_path.read_text(encoding="utf-8").splitlines():
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
    # Deduplicate any remaining duplicate keys (keep last)
    final: dict[str, dict[str, Any]] = {}
    for row in out:
        k = row.get("key")
        if isinstance(k, str):
            final[k] = row
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    with catalog_path.open("w", encoding="utf-8") as f:
        for row in final.values():
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def rebuild_by_name_and_graph(lib: Path) -> dict[str, int]:
    data_root = lib / "data"
    by_name: dict[str, list[str]] = defaultdict(list)
    graph: dict[str, dict[str, Any]] = {}
    count = 0
    for kind_dir in data_root.iterdir() if data_root.is_dir() else []:
        if not kind_dir.is_dir():
            continue
        for path in kind_dir.rglob("*.json"):
            # Skip pagination variants in data if any
            if "__" in path.stem:
                continue
            try:
                obj = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            key = obj.get("key")
            if not isinstance(key, str):
                continue
            name = norm_name(str(obj.get("name") or ""))
            if name and key not in by_name[name]:
                by_name[name].append(key)
            needs = []
            for mat in obj.get("materials") or []:
                mk = mat.get("key")
                if isinstance(mk, str):
                    needs.append(mk)
            refs = []
            for link in obj.get("links") or []:
                lk = link.get("key")
                if isinstance(lk, str) and lk != key:
                    refs.append(lk)
            graph[key] = {
                "type": obj.get("type"),
                "name": obj.get("name"),
                "needs": sorted(set(needs)),
                "references": sorted(set(refs)),
            }
            count += 1
    index = lib / "index"
    index.mkdir(parents=True, exist_ok=True)
    (index / "by_name.json").write_text(
        json.dumps(dict(sorted(by_name.items())), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (index / "graph.json").write_text(
        json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {"entities": count, "names": len(by_name), "graph_nodes": len(graph)}


def decide_actions(
    old_map: dict[int, EntityInv],
    new_map: dict[int, EntityInv],
    kind: str,
) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    all_ids = sorted(set(old_map) | set(new_map))
    # Title validation is important for item/npc (slug collisions). Skills/classes are path-trusted.
    validate_title = kind in {"item", "npc", "set", "location"}

    for eid in all_ids:
        old_e = old_map.get(eid)
        new_e = new_map.get(eid)
        if new_e and validate_title:
            load_entity_meta(new_e)
        if old_e and validate_title and not old_e.name and old_e.base:
            load_entity_meta(old_e)

        if new_e and validate_title and not is_valid_new(kind, new_e):
            decisions.append(
                {
                    "action": "quarantine",
                    "kind": kind,
                    "id": eid,
                    "reason": f"title_kind={new_e.title_kind!r} name={new_e.name!r}",
                    "new_slug": new_e.slug,
                    "old_slug": old_e.slug if old_e else None,
                }
            )
            if old_e:
                decisions.append(
                    {
                        "action": "keep",
                        "kind": kind,
                        "id": eid,
                        "reason": "quarantine_fallback_old",
                        "old_slug": old_e.slug,
                        "name": old_e.name,
                    }
                )
            continue

        if new_e and old_e:
            cov = pagination_coverage(new_e) if kind in {"item", "npc"} else {}
            # If old has pagination pages new lacks, treat as incomplete (union keep).
            if kind in {"item", "npc"} and old_e.variants:
                old_cov = pagination_coverage(old_e)
                new_drop = set(cov.get("drop_pages") or [])
                old_drop = set(old_cov.get("drop_pages") or [])
                new_spoil = set(cov.get("spoil_pages") or [])
                old_spoil = set(old_cov.get("spoil_pages") or [])
                if (old_drop - new_drop) or (old_spoil - new_spoil):
                    cov = dict(cov)
                    cov["incomplete"] = True
                    cov["old_only_drop_pages"] = sorted(old_drop - new_drop)
                    cov["old_only_spoil_pages"] = sorted(old_spoil - new_spoil)
            decisions.append(
                {
                    "action": "replace",
                    "kind": kind,
                    "id": eid,
                    "old_slug": old_e.slug,
                    "new_slug": new_e.slug,
                    "name_old": old_e.name,
                    "name_new": new_e.name,
                    "name_changed": norm_name(old_e.name) != norm_name(new_e.name)
                    if old_e.name and new_e.name
                    else False,
                    "incomplete_pagination": bool(cov.get("incomplete")),
                    "coverage": cov,
                }
            )
        elif new_e:
            cov = pagination_coverage(new_e) if kind in {"item", "npc"} else {}
            decisions.append(
                {
                    "action": "add",
                    "kind": kind,
                    "id": eid,
                    "new_slug": new_e.slug,
                    "name_new": new_e.name,
                    "incomplete_pagination": bool(cov.get("incomplete")),
                    "coverage": cov,
                }
            )
        else:
            decisions.append(
                {
                    "action": "keep",
                    "kind": kind,
                    "id": eid,
                    "old_slug": old_e.slug if old_e else None,
                    "name": old_e.name if old_e else None,
                    "reason": "old_only",
                }
            )
    return decisions


def apply_entity(
    *,
    kind: str,
    decision: dict[str, Any],
    new_map: dict[int, EntityInv],
    old_map: dict[int, EntityInv],
    lib: Path,
    fetch_missing: bool,
    sleep_s: float,
) -> dict[str, Any]:
    action = decision["action"]
    eid = int(decision["id"])
    result: dict[str, Any] = {"kind": kind, "id": eid, "action": action, "files_written": []}
    if action in {"keep", "quarantine"}:
        return result

    new_e = new_map[eid]
    raw_kind = lib / "raw" / "lu4" / kind
    incomplete = bool(decision.get("incomplete_pagination"))
    # Items/NPC: keep old-only pagination page numbers (union). New overwrites shared pages.
    keep_old_pag = incomplete and kind in {"item", "npc"}
    cov = decision.get("coverage") or {}
    has_old_only_pages = bool(cov.get("old_only_drop_pages") or cov.get("old_only_spoil_pages"))
    if has_old_only_pages:
        keep_old_pag = True

    # Prepare rewritten base + variants from mirror
    written_pag_stems: set[str] = set()
    base_html = None
    source_live = ""

    if new_e.base and new_e.base.path.is_file():
        raw_html = strip_banner(new_e.base.path.read_text(encoding="utf-8", errors="replace"))
        source_live = f"{BASE}/{kind}/{new_e.stem}"
        base_html = rewrite_html(raw_html)

        # Fetch missing pagination pages
        if fetch_missing and kind in {"item", "npc"} and incomplete:
            try:
                for page_url in extract_pagination_urls(raw_html, kind, eid, new_e.slug):
                    pstem = pagination_stem_from_url(new_e.stem, page_url)
                    # Skip if already in mirror variants
                    if any(v.stem.replace("__", "_").endswith(pstem.split("__", 1)[-1]) for v in new_e.variants):
                        # still may need write from mirror below
                        pass
                    dest = raw_kind / f"{pstem}.html"
                    # Only fetch if not present in new variants list
                    have = False
                    for v in new_e.variants:
                        _, suf = split_stem(v.stem)
                        want = "__" + pstem.split("__", 1)[-1] if "__" in pstem else None
                        if suf and want and normalize_pag_suffix(suf) == normalize_pag_suffix(want):
                            have = True
                            break
                    if have:
                        continue
                    time.sleep(max(sleep_s, 0.35))
                    try:
                        page_html = rewrite_html(fetch_url(page_url))
                        if not keep_old_pag:
                            pass
                        write_raw_file(dest, page_url, page_html)
                        written_pag_stems.add(pstem)
                        result["files_written"].append(dest.name)
                    except Exception as exc:  # noqa: BLE001
                        result.setdefault("fetch_errors", []).append(f"{page_url}: {exc}")
                # Recompute incomplete after fetch
                # (best-effort; keep_old_pag stays if any fetch_errors)
                if result.get("fetch_errors"):
                    keep_old_pag = True
                elif has_old_only_pages:
                    keep_old_pag = True
                else:
                    # If we fetched everything linked, allow full replace
                    drop_m, spoil_m = max_pagination_linked(raw_html)
                    have_drop = {
                        int(m.group(1))
                        for m in re.finditer(r"dropPage_(\d+)", " ".join(written_pag_stems))
                    }
                    for v in new_e.variants:
                        for m in re.finditer(r"dropPage_(\d+)", v.pag_suffix or ""):
                            have_drop.add(int(m.group(1)))
                    if drop_m and max(have_drop or [0]) >= drop_m:
                        keep_old_pag = False
            except Exception as exc:  # noqa: BLE001
                result.setdefault("fetch_errors", []).append(str(exc))
                keep_old_pag = True

    # Snapshot old pagination content BEFORE clearing (paths will be deleted).
    old_pag_blobs: list[tuple[str, str]] = []  # (pag_suffix_normalized, html)
    if keep_old_pag and eid in old_map:
        for v in old_map[eid].variants:
            if not v.path.is_file():
                continue
            _, suf = split_stem(v.stem)
            if not suf:
                continue
            old_pag_blobs.append(
                (
                    normalize_pag_suffix(suf),
                    v.path.read_text(encoding="utf-8", errors="replace"),
                )
            )

    # Clear top-level entity files (base+pag), then restore kept old pag if needed
    if kind != "skill":  # skills are mostly nested dirs
        clear_entity_top_level(raw_kind, eid)
    clear_entity_data_pages(lib, kind, eid)

    # Write base
    if base_html is not None and new_e.base:
        dest = raw_kind / f"{new_e.stem}.html"
        write_raw_file(dest, source_live, base_html)
        result["files_written"].append(dest.name)

    # Write mirror variants (prefer canonical slug files when duplicates exist)
    variants_by_suf: dict[str, FileRef] = {}
    for v in new_e.variants:
        _, suf = split_stem(v.stem)
        if not suf:
            continue
        ns = normalize_pag_suffix(suf)
        prev = variants_by_suf.get(ns)
        if prev is None:
            variants_by_suf[ns] = v
        elif v.slug == new_e.slug and prev.slug != new_e.slug:
            variants_by_suf[ns] = v

    for ns, v in variants_by_suf.items():
        raw = strip_banner(v.path.read_text(encoding="utf-8", errors="replace"))
        html = rewrite_html(raw)
        stem = f"{new_e.stem}{ns}"
        if stem in written_pag_stems:
            continue
        src = f"{BASE}/{kind}/{new_e.stem}"
        dest = raw_kind / f"{stem}.html"
        write_raw_file(dest, src, html)
        result["files_written"].append(dest.name)
        written_pag_stems.add(stem)

    # Restore old pagination not overlapping new stems
    if keep_old_pag and old_pag_blobs:
        new_sufs = set()
        for stem in written_pag_stems:
            _, suf = split_stem(stem)
            if suf:
                new_sufs.add(normalize_pag_suffix(suf))
        for ns, html_blob in old_pag_blobs:
            if ns in new_sufs:
                continue
            dest = raw_kind / f"{new_e.stem}{ns}.html"
            if not dest.exists():
                write_raw_file(dest, f"preserved-old-pagination:{new_e.stem}{ns}", rewrite_html(strip_banner(html_blob)))
                result["files_written"].append(dest.name)
                result.setdefault("kept_old_pagination", []).append(dest.name)

    # Nested skill/class/posts
    if new_e.nested:
        # Snapshot old nested levels before deleting dirs
        old_levels: dict[str, str] = {}  # level filename -> html
        if eid in old_map:
            for n in old_map[eid].nested:
                if n.path.is_file():
                    old_levels[Path(n.rel).name] = n.path.read_text(
                        encoding="utf-8", errors="replace"
                    )

        if kind in {"skill", "class"}:
            if raw_kind.is_dir():
                for d in raw_kind.iterdir():
                    if d.is_dir() and (d.name == str(eid) or d.name.startswith(f"{eid}-")):
                        shutil.rmtree(d, ignore_errors=True)

            parent = new_e.stem if new_e.slug else str(eid)
            new_level_names: set[str] = set()
            for n in new_e.nested:
                level_name = Path(n.rel).name
                new_level_names.add(level_name)
                dest = raw_kind / parent / level_name
                raw = strip_banner(n.path.read_text(encoding="utf-8", errors="replace"))
                html = rewrite_html(raw)
                src = f"{BASE}/{kind}/{parent}/{level_name.replace('.html', '')}"
                write_raw_file(dest, src, html)
                result["files_written"].append(f"{parent}/{level_name}")

            for level_name, html_blob in old_levels.items():
                if level_name in new_level_names:
                    continue
                dest = raw_kind / parent / level_name
                if not dest.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    write_raw_file(
                        dest,
                        f"preserved-old:{level_name}",
                        rewrite_html(strip_banner(html_blob)),
                    )
                    result["files_written"].append(f"{parent}/{level_name}")
        else:
            for n in new_e.nested:
                dest = raw_kind / n.rel
                raw = strip_banner(n.path.read_text(encoding="utf-8", errors="replace"))
                write_raw_file(dest, f"{BASE}/{kind}/{n.rel}", rewrite_html(raw))
                result["files_written"].append(n.rel)

    # Index library entity from base (or first nested for skill-only)
    html_for_index = base_html
    if html_for_index is None and new_e.nested:
        p = raw_kind / (new_e.stem if new_e.slug else str(eid)) / new_e.nested[0].path.name
        if p.is_file():
            html_for_index = strip_banner(p.read_text(encoding="utf-8", errors="replace"))
            source_live = f"{BASE}/{kind}/{new_e.stem}"
    if html_for_index:
        # Ensure skill without top-level still gets a data stub from first level
        if kind == "skill" and new_e.base is None:
            # Write a synthetic pointer file? Prefer index from nested level 1 or min
            pass
        if kind != "skill" or new_e.base is not None or html_for_index:
            row = write_library_entity(
                lib, kind, eid, new_e.slug, html_for_index, source_live=source_live or BASE
            )
            result["catalog_row"] = row

    result["keep_old_pagination"] = keep_old_pag
    return result


def sync_images_for_entities(item_ids: list[int], skill_ids: list[int]) -> dict[str, int]:
    stats = {"copied": 0, "downloaded": 0, "skipped": 0, "errors": 0}
    raw_item = DEFAULT_LIB / "raw" / "lu4" / "item"

    def valid_png(path: Path) -> bool:
        if not path.is_file() or path.stat().st_size < MIN_IMAGE_BYTES:
            return False
        try:
            return path.read_bytes()[:4] == PNG_MAGIC
        except OSError:
            return False

    def ensure_image(local: Path, candidates: list[Path], remote_urls: list[str]) -> None:
        if valid_png(local):
            stats["skipped"] += 1
            return
        for src in candidates:
            if src.is_file() and src.stat().st_size >= MIN_IMAGE_BYTES:
                data = src.read_bytes()
                if data[:4] == PNG_MAGIC or local.suffix.lower() != ".png":
                    local.parent.mkdir(parents=True, exist_ok=True)
                    local.write_bytes(data)
                    stats["copied"] += 1
                    return
        for url in remote_urls:
            try:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = resp.read()
                if len(data) < MIN_IMAGE_BYTES:
                    continue
                if local.suffix.lower() == ".png" and not data.startswith(PNG_MAGIC):
                    continue
                local.parent.mkdir(parents=True, exist_ok=True)
                tmp = local.with_suffix(local.suffix + ".part")
                tmp.write_bytes(data)
                tmp.replace(local)
                stats["downloaded"] += 1
                return
            except Exception:  # noqa: BLE001
                continue
        stats["errors"] += 1

    for iid in item_ids:
        icon = None
        # find any html for item
        paths = list(raw_item.glob(f"{iid}-*.html")) if raw_item.is_dir() else []
        base = next((p for p in paths if "__" not in p.name), paths[0] if paths else None)
        if base:
            m = I64_ICON_RE.search(base.read_text(encoding="utf-8", errors="replace")[:50000])
            if m:
                icon = m.group(1)
        local = IMAGES_DIR / f"{iid}.png"
        cands = [I64_MIRROR / icon] if icon else []
        remotes = [f"https://masterwork.wiki/i64/{icon}"] if icon else []
        ensure_image(local, cands, remotes)

    for sid in skill_ids:
        local = IMAGES_DIR / "wiki" / "skills" / f"skill{sid}.png"
        icon = f"skill{sid}.png"
        ensure_image(local, [I64_MIRROR / icon], [f"https://masterwork.wiki/i64/{icon}"])

    return stats


def rebuild_datasets() -> dict[str, Any]:
    from build_craft_catalog import OUT as CRAFT_OUT
    from build_craft_catalog import build_catalog
    from build_items_encyclopedia import OUT as ENC_OUT
    from build_items_encyclopedia import finalize_payload, rebuild_from_wiki

    out: dict[str, Any] = {}
    print("Building craft_catalog.json ...")
    craft = build_catalog()
    CRAFT_OUT.parent.mkdir(parents=True, exist_ok=True)
    CRAFT_OUT.write_text(json.dumps(craft, ensure_ascii=False, indent=2), encoding="utf-8")
    out["craft"] = {
        "products": craft.get("product_count"),
        "variants": craft.get("variant_count"),
    }
    print(f"  products={out['craft']['products']} variants={out['craft']['variants']}")

    print("Building items_encyclopedia.json ...")
    raw = rebuild_from_wiki()
    payload = finalize_payload(raw, craft_catalog=craft)
    payload["generated_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    ENC_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    out["encyclopedia"] = {"items": payload.get("item_count")}
    print(f"  items={out['encyclopedia']['items']}")

    # Raid bosses dataset is primarily l4map-based; still refresh if script works.
    try:
        print("Building raid_bosses.json ...")
        import build_raid_bosses_data as raid_mod

        # Fix known wrong wiki paths relative to project
        raid_mod.WIKI_BY_NAME = DEFAULT_LIB / "index" / "by_name.json"
        raid_mod.WIKI_NPC_DIR = DEFAULT_LIB / "data" / "npc"
        raid_mod.main()
        out["raid"] = "ok"
    except Exception as exc:  # noqa: BLE001
        print(f"  WARN raid rebuild skipped: {exc}")
        out["raid"] = f"skipped: {exc}"
    return out


def catalog_key_count(lib: Path) -> int:
    cat = lib / "index" / "catalog.jsonl"
    if not cat.is_file():
        return 0
    keys = set()
    for line in cat.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            keys.add(json.loads(line).get("key"))
        except json.JSONDecodeError:
            continue
    return len(keys)


def run(args: argparse.Namespace) -> int:
    new_root: Path = args.new_root
    lib: Path = args.library_root
    kinds = [k.strip() for k in args.kinds.split(",") if k.strip()] if args.kinds else list(SCOPE_KINDS)
    kinds = [k for k in kinds if k not in SKIP_KINDS]

    report: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "new_root": str(new_root),
        "library_root": str(lib),
        "dry_run": args.dry_run,
        "kinds": kinds,
        "decisions": {},
        "summary": {},
        "apply_results": [],
        "warnings": [],
    }

    pre_keys = catalog_key_count(lib)
    report["catalog_keys_before"] = pre_keys

    all_decisions: list[dict[str, Any]] = []
    inventories: dict[str, tuple[dict[int, EntityInv], dict[int, EntityInv]]] = {}

    for kind in kinds:
        print(f"Inventory {kind}...", flush=True)
        old_map = inventory_kind(lib / "raw" / "lu4" / kind, kind)
        new_map = inventory_kind(new_root / kind, kind)
        inventories[kind] = (old_map, new_map)
        decisions = decide_actions(old_map, new_map, kind)
        all_decisions.extend(decisions)
        counts = defaultdict(int)
        for d in decisions:
            counts[d["action"]] += 1
        report["decisions"][kind] = {
            "counts": dict(counts),
            "old": len(old_map),
            "new": len(new_map),
            "incomplete_replace": sum(
                1 for d in decisions if d.get("action") == "replace" and d.get("incomplete_pagination")
            ),
            "samples": {
                "replace": [d for d in decisions if d["action"] == "replace"][:8],
                "add": [d for d in decisions if d["action"] == "add"][:8],
                "keep": [d for d in decisions if d["action"] == "keep"][:8],
                "quarantine": [d for d in decisions if d["action"] == "quarantine"][:8],
            },
        }
        print(
            f"  old={len(old_map)} new={len(new_map)} "
            f"replace={counts['replace']} add={counts['add']} "
            f"keep={counts['keep']} quarantine={counts['quarantine']}",
            flush=True,
        )

    summary = defaultdict(int)
    for d in all_decisions:
        summary[d["action"]] += 1
    report["summary"] = dict(summary)

    if args.dry_run or not args.apply:
        if not args.apply and not args.dry_run:
            report["warnings"].append("Neither --dry-run nor --apply set; defaulting to dry-run")
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nDry-run report -> {report_path}")
        print("Summary:", dict(summary))
        return 0

    # APPLY
    fetch_missing = args.fetch_missing_pages
    catalog_rows: list[dict[str, Any]] = []
    touched_items: list[int] = []
    touched_skills: list[int] = []

    for kind in kinds:
        old_map, new_map = inventories[kind]
        kind_decisions = [d for d in all_decisions if d["kind"] == kind and d["action"] in {"replace", "add"}]
        print(f"Applying {kind}: {len(kind_decisions)} entities...", flush=True)
        for i, decision in enumerate(kind_decisions, 1):
            if i % 100 == 0 or i == len(kind_decisions):
                print(f"  {kind} {i}/{len(kind_decisions)}", flush=True)
            res = apply_entity(
                kind=kind,
                decision=decision,
                new_map=new_map,
                old_map=old_map,
                lib=lib,
                fetch_missing=fetch_missing and kind in {"item", "npc"},
                sleep_s=args.sleep,
            )
            report["apply_results"].append(
                {
                    "kind": kind,
                    "id": decision["id"],
                    "action": decision["action"],
                    "files": len(res.get("files_written") or []),
                    "keep_old_pagination": res.get("keep_old_pagination"),
                    "fetch_errors": res.get("fetch_errors"),
                }
            )
            row = res.get("catalog_row")
            if row:
                catalog_rows.append(row)
            if kind == "item":
                touched_items.append(int(decision["id"]))
            if kind == "skill":
                touched_skills.append(int(decision["id"]))

    print(f"Upserting catalog ({len(catalog_rows)} rows)...")
    upsert_catalog(lib / "index" / "catalog.jsonl", catalog_rows)

    print("Rebuilding by_name.json + graph.json...")
    idx_stats = rebuild_by_name_and_graph(lib)
    report["index_rebuild"] = idx_stats

    post_keys = catalog_key_count(lib)
    report["catalog_keys_after"] = post_keys
    if post_keys < pre_keys:
        report["warnings"].append(
            f"catalog keys decreased {pre_keys} -> {post_keys} (may be dedup; inspect report)"
        )

    if args.rebuild_datasets:
        report["datasets"] = rebuild_datasets()

    if args.sync_images:
        print("Syncing images for touched items/skills...")
        report["images"] = sync_images_for_entities(touched_items, touched_skills)
        print("  ", report["images"])

    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    # Trim apply_results if huge
    if len(report["apply_results"]) > 5000:
        report["apply_results_truncated"] = len(report["apply_results"])
        report["apply_results"] = report["apply_results"][:5000]
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDone. Report -> {report_path}")
    print("Summary:", dict(summary), f"catalog {pre_keys} -> {post_keys}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--new-root", type=Path, default=DEFAULT_NEW)
    p.add_argument("--library-root", type=Path, default=DEFAULT_LIB)
    p.add_argument("--dry-run", action="store_true", help="Report only, no writes")
    p.add_argument("--apply", action="store_true", help="Write merged library")
    p.add_argument("--kinds", default=",".join(SCOPE_KINDS), help="Comma-separated kinds")
    p.add_argument(
        "--fetch-missing-pages",
        dest="fetch_missing_pages",
        action="store_true",
        default=True,
        help="Fetch missing drop/spoil pages from live B-W-C (default on with --apply)",
    )
    p.add_argument(
        "--no-fetch-missing-pages",
        dest="fetch_missing_pages",
        action="store_false",
        help="Do not hit the network for pagination",
    )
    p.add_argument("--rebuild-datasets", action="store_true")
    p.add_argument("--sync-images", action="store_true")
    p.add_argument("--sleep", type=float, default=0.25)
    p.add_argument(
        "--report",
        default=str(ROOT / "data" / "_tmp_wiki_fetch" / "merge_bwc_report.json"),
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.new_root.is_dir():
        print(f"ERROR: new wiki root missing: {args.new_root}", file=sys.stderr)
        return 2
    if not (args.library_root / "raw" / "lu4").is_dir():
        print(f"ERROR: library raw/lu4 missing under {args.library_root}", file=sys.stderr)
        return 2
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
