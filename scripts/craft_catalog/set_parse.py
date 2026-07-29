"""Parse Lu4 wiki raw HTML set pages."""
from __future__ import annotations

import html as html_module
import re
from dataclasses import dataclass, field

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None  # type: ignore

from .wiki_parse import ITEM_ID_RE, _clean_text

GRADE_SUFFIX_RE = re.compile(r"\s+(NG|D|C|B|A|S)$")
SET_TITLE_RE = re.compile(r"Set\s+(.+?)\s*$", re.IGNORECASE)
SET_SLUG_RE = re.compile(r"/set/(?:\d+-)?(.+?)(?:\.html)?$")
SET_URL_ID_RE = re.compile(r"/set/(\d+)(?:-(.+))?")
I64_ICON_RE = re.compile(r"/i64/([^/?#]+)$")
BR_SPLIT_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)


@dataclass
class SetPageInfo:
    name: str
    grade: str
    url: str
    is_pvp: bool
    set_id: int | None = None
    slug: str = ""
    icon: str | None = None
    effect_raw: str = ""
    effect_lines: list[str] = field(default_factory=list)
    members: list[tuple[int, str]] = field(default_factory=list)
    foundation_ids: set[int] = field(default_factory=set)


def _require_bs4():
    if BeautifulSoup is None:
        raise RuntimeError("beautifulsoup4 is required: pip install beautifulsoup4")


def _strip_grade(name: str) -> str:
    return GRADE_SUFFIX_RE.sub("", name or "").strip()


def _parse_set_url(url: str) -> tuple[int | None, str]:
    m = SET_URL_ID_RE.search(url or "")
    if not m:
        return None, ""
    set_id = int(m.group(1))
    slug = (m.group(2) or "").strip()
    if slug.endswith("-pvp"):
        slug = slug[:-4]
    return set_id, slug


def _parse_set_icon(soup: BeautifulSoup) -> str | None:
    img = soup.select_one(".item_head .item-icon img")
    if img is None:
        return None
    src = img.get("src") or ""
    m = I64_ICON_RE.search(src)
    return m.group(1) if m else None


def _parse_set_effect(soup: BeautifulSoup) -> tuple[str, list[str]]:
    item_part = soup.select_one(".item_part")
    if item_part is None:
        return "", []
    result_stats = item_part.select_one("#result-stats")
    for line in item_part.find_all("div", class_="stat_line", recursive=False):
        if line.select_one(".stat_name"):
            continue
        if result_stats is not None and line in result_stats.find_all("div", class_="stat_line"):
            continue
        raw_html = line.decode_contents()
        parts = [_clean_text(html_module.unescape(p)) for p in BR_SPLIT_RE.split(raw_html)]
        effect_lines = [part for part in parts if part]
        if not effect_lines:
            continue
        return "\n".join(effect_lines), effect_lines
    return "", []


def _member_name(link) -> str:
    name_el = link.select_one(".item-name__class-1") or link.select_one(".item-name__content")
    if name_el is None:
        return _clean_text(link.get_text())
    return _strip_grade(_clean_text(name_el.get_text()))


def _name_from_title(soup: BeautifulSoup) -> str:
    title_el = soup.find("title")
    if not title_el:
        return ""
    title = html_module.unescape(_clean_text(title_el.get_text()))
    m = SET_TITLE_RE.search(title)
    if not m:
        return ""
    return _strip_grade(m.group(1))


def _name_from_slug(url: str) -> str:
    m = SET_SLUG_RE.search(url or "")
    if not m:
        return ""
    slug = m.group(1)
    if slug.endswith("-pvp"):
        slug = slug[:-4]
    if not slug or slug.isdigit():
        return ""
    words = slug.replace("-", " ").split()
    return " ".join(w.capitalize() for w in words)


def _name_from_breadcrumbs(soup: BeautifulSoup) -> str:
    for step in soup.select(".breadcrumbs_step"):
        text = _strip_grade(_clean_text(step.get_text()))
        if text and text not in ("Main", "Sets (Lu4)", "Sets"):
            return text
    return ""


def _resolve_set_name(soup: BeautifulSoup, url: str) -> str:
    name_el = soup.select_one(".item_title .item-name__content")
    if name_el:
        name = _strip_grade(_clean_text(name_el.get_text()))
        if name:
            return name
    for resolver in (_name_from_title, lambda s: _name_from_breadcrumbs(s), lambda _: _name_from_slug(url)):
        name = resolver(soup)
        if name:
            return name
    return ""


def parse_set_page(html: str, url: str) -> SetPageInfo | None:
    _require_bs4()
    soup = BeautifulSoup(html, "html.parser")

    name = _resolve_set_name(soup, url)
    grade_el = soup.select_one(".item_title .item-grade")
    grade = _clean_text(grade_el.get_text()) if grade_el else "NG"
    set_id, slug = _parse_set_url(url)
    icon = _parse_set_icon(soup)
    effect_raw, effect_lines = _parse_set_effect(soup)

    title_text = _clean_text(soup.find("title").get_text()) if soup.find("title") else ""
    is_pvp = "-pvp" in (url or "").lower() or "{pvp}" in title_text.lower() or "{pvp}" in name.lower()

    members: list[tuple[int, str]] = []
    foundation_ids: set[int] = set()
    seen_ids: set[int] = set()

    for line in soup.select("#result-stats .stat_line"):
        name_node = line.select_one(".stat_name")
        if not name_node or "Set Parts" not in name_node.get_text():
            continue
        for link in line.select('a.item-name[href*="/lu4/item/"]'):
            href = link.get("href") or ""
            m = ITEM_ID_RE.search(href)
            if not m:
                continue
            item_id = int(m.group(1))
            member_name = _member_name(link)
            if link.select_one(".item-name__class-2"):
                foundation_ids.add(item_id)
                continue
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            members.append((item_id, member_name))

    if not name and members:
        name = members[0][1]

    if not name and not members:
        return None

    return SetPageInfo(
        name=name,
        grade=grade,
        url=url,
        is_pvp=is_pvp,
        set_id=set_id,
        slug=slug,
        icon=icon,
        effect_raw=effect_raw,
        effect_lines=effect_lines,
        members=members,
        foundation_ids=foundation_ids,
    )
