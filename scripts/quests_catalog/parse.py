"""Parse Lu4 wiki raw HTML quest pages into structured records."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    from bs4 import BeautifulSoup, Tag
except ImportError:  # pragma: no cover
    BeautifulSoup = None  # type: ignore
    Tag = object  # type: ignore

ITEM_ID_RE = re.compile(r"/(?:lu4|eternal|masterwork)/item/(\d+)-", re.I)
NPC_ID_RE = re.compile(r"/(?:lu4|eternal|masterwork)/npc/(\d+)-", re.I)
I64_ICON_RE = re.compile(r"/i64/([^/?#]+)", re.I)
LEVEL_RANGE_RE = re.compile(
    r"(?:Level\s*:?\s*)?(\d+)\s*[~–—-]\s*(\d+)",
    re.I,
)
LEVEL_PLUS_RE = re.compile(r"(?:Level\s*:?\s*)?(\d+)\s*\+", re.I)
QTY_RE = re.compile(r"x\s*([\d\s\xa0]+)", re.I)
DEFAULT_LEVEL_MAX = 99


def _require_bs4() -> None:
    if BeautifulSoup is None:
        raise RuntimeError("beautifulsoup4 is required: pip install beautifulsoup4")


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def load_html(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_level(text: str | None) -> tuple[int | None, int | None]:
    """Return (level_min, level_max). Plus-only forms use max=None."""
    if not text:
        return None, None
    cleaned = _clean_text(text)
    m = LEVEL_RANGE_RE.search(cleaned)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        return (lo, hi) if lo <= hi else (hi, lo)
    m = LEVEL_PLUS_RE.search(cleaned)
    if m:
        return int(m.group(1)), None
    digits = re.search(r"\b(\d{1,3})\b", cleaned)
    if digits and "level" in cleaned.lower():
        n = int(digits.group(1))
        return n, n
    return None, None


def effective_level_max(level_min: int | None, level_max: int | None) -> int | None:
    if level_max is not None:
        return level_max
    if level_min is not None:
        return DEFAULT_LEVEL_MAX
    return None


def quest_overlaps_range(
    level_min: int | None,
    level_max: int | None,
    filter_min: int,
    filter_max: int,
) -> bool:
    """True when quest level window intersects [filter_min, filter_max]."""
    if level_min is None and level_max is None:
        return True
    q_min = level_min if level_min is not None else 0
    q_max = effective_level_max(level_min, level_max)
    if q_max is None:
        q_max = DEFAULT_LEVEL_MAX
    return q_min <= filter_max and q_max >= filter_min


def _icon_from_img(img: Tag | None) -> str | None:
    if img is None:
        return None
    m = I64_ICON_RE.search(img.get("src") or "")
    return m.group(1) if m else None


def _parse_linked_entity(anchor: Tag) -> dict[str, Any]:
    href = anchor.get("href") or ""
    class1 = anchor.select_one(".item-name__class-1")
    if class1:
        name = _clean_text(class1.get_text())
    else:
        # Clone content without grade / additional suffixes.
        content = anchor.select_one(".item-name__content")
        if content is not None:
            parts: list[str] = []
            for child in content.children:
                if getattr(child, "name", None) in {"span"} and "item-name__additional" in (
                    child.get("class") or []
                ):
                    continue
                if getattr(child, "name", None) in {"span"} and "item-grade" in (child.get("class") or []):
                    continue
                text = _clean_text(child.get_text() if hasattr(child, "get_text") else str(child))
                if text:
                    parts.append(text)
            name = " ".join(parts) if parts else _clean_text(content.get_text())
        else:
            name = _clean_text(anchor.get_text())
    grade_el = anchor.select_one(".item-grade")
    grade = _clean_text(grade_el.get_text()) if grade_el else None
    icon = _icon_from_img(anchor.select_one(".item-icon img, img"))
    item_m = ITEM_ID_RE.search(href)
    npc_m = NPC_ID_RE.search(href)
    out: dict[str, Any] = {"name": name}
    if icon:
        out["icon"] = icon
    if grade:
        out["grade"] = grade
    if item_m:
        out["item_id"] = int(item_m.group(1))
    if npc_m:
        out["npc_id"] = int(npc_m.group(1))
    return out


def _qty_near(node: Tag) -> int | None:
    parent = node.parent
    if parent is None:
        return None
    text = _clean_text(parent.get_text(" ", strip=True))
    m = QTY_RE.search(text)
    if not m:
        # Sibling text after the anchor
        for sib in node.next_siblings:
            chunk = _clean_text(getattr(sib, "get_text", lambda **_: str(sib))())
            if not chunk:
                continue
            m = QTY_RE.search(chunk)
            if m:
                break
        else:
            return None
    try:
        return int(m.group(1).replace(" ", "").replace("\xa0", ""))
    except ValueError:
        return None


def _rewards_from_container(container: Tag | None) -> list[dict[str, Any]]:
    if container is None:
        return []
    rewards: list[dict[str, Any]] = []
    seen: set[tuple[Any, str]] = set()
    for anchor in container.select("a.item-name"):
        href = anchor.get("href") or ""
        if not ITEM_ID_RE.search(href):
            continue
        ent = _parse_linked_entity(anchor)
        item_id = ent.get("item_id")
        key = (item_id, ent.get("name") or "")
        if key in seen:
            continue
        seen.add(key)
        qty = _qty_near(anchor)
        reward: dict[str, Any] = {
            "item_id": item_id,
            "name": ent.get("name") or "",
        }
        if ent.get("grade"):
            reward["grade"] = ent["grade"]
        if ent.get("icon"):
            reward["icon"] = ent["icon"]
        if qty is not None:
            reward["qty"] = qty
        rewards.append(reward)
    return rewards


def _npc_from_container(container: Tag | None) -> dict[str, Any] | None:
    if container is None:
        return None
    for anchor in container.select("a.item-name"):
        href = anchor.get("href") or ""
        if not NPC_ID_RE.search(href):
            continue
        ent = _parse_linked_entity(anchor)
        out: dict[str, Any] = {
            "id": ent.get("npc_id"),
            "name": ent.get("name") or "",
        }
        if ent.get("icon"):
            out["icon"] = ent["icon"]
        return out
    return None


def _parse_classic(soup: BeautifulSoup) -> dict[str, Any]:
    """Classic quest layout with .item-name__type and #result-stats."""
    title_el = soup.select_one(".item_title .item-name__content")
    name = _clean_text(title_el.get_text()) if title_el else ""

    type_el = soup.select_one(".item-name__type")
    level_min, level_max = parse_level(type_el.get_text() if type_el else None)

    description = ""
    start_npc = None
    rewards: list[dict[str, Any]] = []

    for line in soup.select("#result-stats .stat_line"):
        name_el = line.select_one(".stat_name")
        if name_el is None:
            text = _clean_text(line.get_text())
            if text and not description:
                description = text
            continue
        key = _clean_text(name_el.get_text()).lower()
        if key == "start npc":
            start_npc = _npc_from_container(line)
        elif key == "rewards":
            rewards = _rewards_from_container(line)

    steps: list[dict[str, Any]] = []
    for article in soup.select("#article.article_part, div#article"):
        h2 = article.find("h2")
        if h2 is None:
            continue
        title = _clean_text(h2.get_text())
        paras = [_clean_text(p.get_text()) for p in article.find_all("p", recursive=False)]
        paras = [p for p in paras if p]
        images: list[str] = []
        for img in article.select("img"):
            src = img.get("src") or ""
            if "/upload/" in src:
                images.append(src)
        steps.append(
            {
                "title": title,
                "text": "\n\n".join(paras),
                "images": images,
            }
        )

    return {
        "name": name,
        "level_min": level_min,
        "level_max": level_max,
        "description": description,
        "start_npc": start_npc,
        "rewards": rewards,
        "steps": steps,
        "layout": "classic",
    }


def _article_guide_steps(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """Split pictorial guide blocks after the 'Quest guide' heading."""
    content = soup.select_one("#article-content")
    if content is None:
        return []

    guide_h2 = None
    for h2 in content.find_all("h2"):
        title = _clean_text(h2.get_text())
        if re.search(r"quest\s+guide|walkthrough|guide\b", title, re.I):
            guide_h2 = h2
            break
    if guide_h2 is None:
        # First h2 inside content that isn't a sidebar leftover
        for h2 in content.find_all("h2"):
            title = _clean_text(h2.get_text())
            if title and "useful quest" not in title.lower():
                guide_h2 = h2
                break
    if guide_h2 is None:
        return []

    # Collect siblings until next major section / end of parent
    parent = guide_h2.parent
    if parent is None:
        return []
    chunks: list[list] = [[]]
    past = False
    for child in parent.children:
        if not getattr(child, "name", None):
            continue
        if child is guide_h2:
            past = True
            continue
        if not past:
            continue
        if child.name in {"h2", "h1"}:
            break
        if child.name == "hr":
            if chunks[-1]:
                chunks.append([])
            continue
        chunks[-1].append(child)

    steps: list[dict[str, Any]] = []
    for idx, nodes in enumerate(chunks, start=1):
        if not nodes:
            continue
        texts: list[str] = []
        images: list[str] = []
        for node in nodes:
            for img in node.find_all("img") if hasattr(node, "find_all") else []:
                src = img.get("src") or ""
                if "/upload/" in src and src not in images:
                    images.append(src)
            if getattr(node, "name", None) == "p":
                text = _clean_text(node.get_text())
                if text:
                    texts.append(text)
            elif getattr(node, "name", None) == "figure":
                continue
        if not texts and not images:
            continue
        first = texts[0] if texts else ""
        m = re.match(r"^(\d+)[.\)]\s*(.*)$", first)
        if m:
            title = f"{m.group(1)}. {m.group(2)[:80]}".strip() if m.group(2) else f"Step {m.group(1)}"
            body = "\n\n".join([m.group(2)] + texts[1:]) if m.group(2) else "\n\n".join(texts[1:])
        else:
            title = f"Step {idx}"
            body = "\n\n".join(texts)
        steps.append({"title": title, "text": body, "images": images})
    return steps


def _parse_article_layout(soup: BeautifulSoup) -> dict[str, Any]:
    """Article-style quest pages with info tables."""
    title_el = soup.select_one("#article h1, .article-section h1")
    if title_el is None:
        crumbs = soup.select(".breadcrumbs_step")
        title_el = crumbs[-1] if crumbs else None
    name = _clean_text(title_el.get_text()) if title_el else ""
    # Strip leading "Quest " prefix noise when present in article titles
    if name.lower().startswith("quest "):
        name = name[6:].strip()

    level_min: int | None = None
    level_max: int | None = None
    start_npc = None
    rewards: list[dict[str, Any]] = []
    quest_type = ""
    location = ""

    for row in soup.select("#article-content table tr, #article table tr"):
        cells = row.find_all("td", recursive=False)
        if not cells:
            continue
        label = _clean_text(cells[0].get_text()).lower()
        value_cell = cells[1] if len(cells) >= 2 else None
        if label == "level" and value_cell is not None:
            level_min, level_max = parse_level(value_cell.get_text())
        elif label == "start npc" and value_cell is not None:
            start_npc = _npc_from_container(value_cell)
        elif label.startswith("reward") and value_cell is not None:
            for r in _rewards_from_container(value_cell):
                key = (r.get("item_id"), r.get("name"))
                if not any((x.get("item_id"), x.get("name")) == key for x in rewards):
                    rewards.append(r)
        elif label == "type" and value_cell is not None:
            quest_type = _clean_text(value_cell.get_text())
        elif label == "starting location" and value_cell is not None:
            location = _clean_text(value_cell.get_text())

    description_parts = [p for p in (quest_type, location and f"Location: {location}") if p]
    description = " | ".join(description_parts)

    steps = _article_guide_steps(soup)
    if steps and not description:
        description = (steps[0].get("text") or "")[:280]

    return {
        "name": name,
        "level_min": level_min,
        "level_max": level_max,
        "description": description,
        "start_npc": start_npc,
        "rewards": rewards,
        "steps": steps,
        "layout": "article",
    }


def parse_quest_html(html: str, *, quest_id: int, slug: str, source_url: str | None = None) -> dict[str, Any]:
    _require_bs4()
    soup = BeautifulSoup(html, "html.parser")

    if soup.select_one(".item-name__type") or soup.select_one("#result-stats"):
        parsed = _parse_classic(soup)
    else:
        parsed = _parse_article_layout(soup)

    # Fallback level from page title / name (e.g. "37+")
    if parsed["level_min"] is None:
        lo, hi = parse_level(parsed.get("name") or "")
        if lo is None:
            # saved-from comment or title tag
            title = soup.title.get_text() if soup.title else ""
            lo, hi = parse_level(title)
        parsed["level_min"], parsed["level_max"] = lo, hi

    if not parsed.get("name"):
        parsed["name"] = slug.replace("-", " ").title()

    url = f"/lu4/quest/{quest_id}-{slug}"
    return {
        "id": quest_id,
        "slug": slug,
        "name": parsed["name"],
        "url": url,
        "source_url": source_url or f"https://masterwork.wiki{url}",
        "level_min": parsed["level_min"],
        "level_max": parsed["level_max"],
        "description": parsed.get("description") or "",
        "start_npc": parsed.get("start_npc"),
        "rewards": parsed.get("rewards") or [],
        "steps": parsed.get("steps") or [],
    }


def parse_quest_file(path: Path) -> dict[str, Any] | None:
    m = re.match(r"^(\d+)-(.+)\.html$", path.name)
    if not m:
        return None
    quest_id = int(m.group(1))
    slug = m.group(2)
    html = load_html(path)
    source_url = None
    saved = re.search(r"saved-from:\s*(\S+)", html)
    if saved:
        source_url = saved.group(1).rstrip()
    return parse_quest_html(html, quest_id=quest_id, slug=slug, source_url=source_url)
