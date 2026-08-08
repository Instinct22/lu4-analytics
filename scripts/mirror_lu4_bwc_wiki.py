#!/usr/bin/env python3
"""Mirror masterwork.wiki /lu4-b-w-c into ./wikilu4 (HTML + assets).

Faster parallel crawler with polite rate-limiting and incremental updates:
  - concurrent HTML + background asset workers
  - global RPS cap + jitter, retries / Retry-After, adaptive throttle
  - resumable via wikilu4/_state.json
  - page index wikilu4/_pages.json (content_hash) for --recheck

Scope:
  - prefer /lu4-b-w-c/ always: gamma links are rewritten to b-w-c before fetch
  - save lu4-gamma only when the same entity 404s on b-w-c
  - on startup + after each b-w-c save: delete gamma HTML that has a b-w-c twin
    (exact path+query twin only — not same entity id)
  - unescape &amp; in URLs so dropPage+spoilPage combo links are kept
  - revive visited URLs that have no local file; reseed drop/spoil pager edges
  - do NOT follow /masterwork/ or /eternal/ (listed in _foreign_redirects.txt)

Usage:
  py -3 scripts/mirror_lu4_bwc_wiki.py                  # full / resume crawl
  py -3 scripts/mirror_lu4_bwc_wiki.py --build-index    # hash existing HTML
  py -3 scripts/mirror_lu4_bwc_wiki.py --recheck --discover
      # freshness check + fill missing drop/spoil pagination + find new pages
  py -3 scripts/mirror_lu4_bwc_wiki.py --repair-pagination
  py -3 scripts/mirror_lu4_bwc_wiki.py --status

Serve offline:
  py -3 -m http.server 8765 --directory wikilu4
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import random
import re
import sys
import threading
import time
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlparse, urlunparse

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "wikilu4"
STATE_PATH = OUT_DIR / "_state.json"
MANIFEST_PATH = OUT_DIR / "_manifest.jsonl"
LOG_PATH = OUT_DIR / "_crawl.log"
PAGES_INDEX_PATH = OUT_DIR / "_pages.json"

HOST = "masterwork.wiki"
ORIGIN = f"https://{HOST}"
CHRONICLE = "lu4-b-w-c"
PREFIX = f"/{CHRONICLE}"
START = f"{ORIGIN}{PREFIX}/main"

ALLOWED_CHRONICLES = frozenset({"lu4-b-w-c", "lu4-gamma"})
FOREIGN_CHRONICLES = frozenset({"masterwork", "eternal"})

UA = "Mozilla/5.0 (compatible; Lu4AnaliticsMirror/1.5; +local offline archive)"
TIMEOUT = httpx.Timeout(45.0, connect=15.0)
ENTITY_ID_RE = re.compile(r"^(\d+)(?:-|$|__)")
PAGINATION_FILE_RE = re.compile(
    r"__(?:dropPage|spoilPage)_(\d+)(?:__|$|\.html)",
    re.I,
)

FOREIGN_TXT = OUT_DIR / "_foreign_redirects.txt"
FOREIGN_JSONL = OUT_DIR / "_foreign_redirects.jsonl"
SKIP_LOG_RE = re.compile(
    r"SKIP off-scope redirect (https://masterwork\.wiki/[^\s]+) -> (https://masterwork\.wiki/[^\s]+)"
)

# Soft errors: retry / requeue. Hard: permanent skip.
SOFT_STATUS = {408, 425, 429, 500, 502, 503, 504}
HARD_STATUS = {400, 401, 403, 404, 405, 410, 451}

SKIP_SUFFIXES = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".css",
    ".js",
    ".map",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".mp4",
    ".webm",
    ".pdf",
    ".json",
    ".xml",
)
ASSET_PREFIXES = (
    "/i64/",
    "/icon64/",
    "/assets/",
    "/img/",
    "/images/",
    "/static/",
    "/favicon",
)
HTML_QUERY_KEEP = re.compile(
    r"^(dropPage|spoilPage|page|per_page|Search\[.+\]|tab|level)$",
    re.I,
)
HREF_ATTRS = ("href", "src", "data-src", "data-lazy-src", "poster")
SRCSET_ATTRS = ("srcset", "data-srcset")
URL_IN_CSS = re.compile(r"url\(\s*['\"]?([^)'\"]+)['\"]?\s*\)", re.I)
LOCALE_RE = re.compile(
    r"^/(en|ru|uk)(/(?:lu4-b-w-c|lu4-gamma|masterwork|eternal)(?:/|$))",
    re.I,
)

# Noise stripped before content hashing (CSRF, analytics, cache-busters, our banner).
BANNER_RE = re.compile(r"^<!--\s*saved-from:.*?-->\s*", re.I | re.S)
CSRF_META_RE = re.compile(
    r'<meta\s+name="csrf-(?:token|param)"[^>]*>\s*',
    re.I,
)
GTM_BLOCK_RE = re.compile(
    r"<script[^>]*>\s*\(function\(w,d,s,l,i\).*?</script>\s*"
    r'|<!--\s*Google Tag Manager.*?-->\s*'
    r'|<noscript>.*?googletagmanager\.com.*?</noscript>\s*',
    re.I | re.S,
)
ASSET_V_RE = re.compile(r"(\.(?:css|js)\?v=)\d+", re.I)
SCRIPT_NONCE_RE = re.compile(r'\snonce="[^"]*"', re.I)

_log_lock = threading.Lock()
_manifest_lock = threading.Lock()
_index_lock = threading.Lock()


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg: str) -> None:
    line = f"[{utc_now()}] {msg}"
    print(line, flush=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with _log_lock:
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")


def strip_saved_banner(text: str) -> str:
    return BANNER_RE.sub("", text.lstrip("\ufeff"), count=1)


def normalize_html_for_hash(html: str) -> str:
    text = strip_saved_banner(html)
    text = CSRF_META_RE.sub("", text)
    text = GTM_BLOCK_RE.sub("", text)
    text = ASSET_V_RE.sub(r"\1", text)
    text = SCRIPT_NONCE_RE.sub("", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def content_hash(html: str) -> str:
    normalized = normalize_html_for_hash(html)
    return hashlib.sha256(normalized.encode("utf-8", "replace")).hexdigest()


# ---------------------------------------------------------------------------
# Page index (current snapshot only — no history)
# ---------------------------------------------------------------------------


@dataclass
class PageRecord:
    url: str
    path: str
    content_hash: str
    fetched_at: str
    checked_at: str
    final_url: str = ""
    etag: str | None = None
    last_modified: str | None = None
    bytes: int = 0
    status: int | None = 200

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "final_url": self.final_url or self.url,
            "path": self.path,
            "content_hash": self.content_hash,
            "etag": self.etag,
            "last_modified": self.last_modified,
            "bytes": self.bytes,
            "fetched_at": self.fetched_at,
            "checked_at": self.checked_at,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PageRecord:
        return cls(
            url=str(data["url"]),
            path=str(data.get("path") or ""),
            content_hash=str(data.get("content_hash") or ""),
            fetched_at=str(data.get("fetched_at") or ""),
            checked_at=str(data.get("checked_at") or data.get("fetched_at") or ""),
            final_url=str(data.get("final_url") or data.get("url") or ""),
            etag=data.get("etag"),
            last_modified=data.get("last_modified"),
            bytes=int(data.get("bytes") or 0),
            status=data.get("status"),
        )


class PageIndex:
    def __init__(self) -> None:
        self.pages: dict[str, PageRecord] = {}
        self.lock = threading.Lock()
        self.dirty = False
        self.stats = {
            "unchanged": 0,
            "updated": 0,
            "added": 0,
            "not_modified_304": 0,
            "checked": 0,
        }

    def load(self) -> None:
        if not PAGES_INDEX_PATH.exists():
            return
        data = json.loads(PAGES_INDEX_PATH.read_text(encoding="utf-8"))
        raw_pages = data.get("pages") if isinstance(data, dict) else data
        if not isinstance(raw_pages, dict):
            return
        with self.lock:
            self.pages = {
                url: PageRecord.from_dict(row)
                for url, row in raw_pages.items()
                if isinstance(row, dict) and row.get("url")
            }

    def save(self) -> None:
        with self.lock:
            unique: dict[int, PageRecord] = {}
            for rec in self.pages.values():
                unique[id(rec)] = rec
            payload = {
                "updated_at": utc_now(),
                "count": len(unique),
                "pages": {
                    (rec.final_url or rec.url): rec.to_dict()
                    for rec in sorted(unique.values(), key=lambda r: r.final_url or r.url)
                },
            }
            self.dirty = False
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        tmp = PAGES_INDEX_PATH.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        tmp.replace(PAGES_INDEX_PATH)

    def get(self, url: str) -> PageRecord | None:
        with self.lock:
            return self.pages.get(url)

    def urls(self) -> list[str]:
        with self.lock:
            seen: set[int] = set()
            out: list[str] = []
            for rec in self.pages.values():
                rid = id(rec)
                if rid in seen:
                    continue
                seen.add(rid)
                out.append(rec.final_url or rec.url)
            return out

    def __len__(self) -> int:
        with self.lock:
            return len({id(r) for r in self.pages.values()})

    def upsert(
        self,
        *,
        url: str,
        path: str,
        content_hash_value: str,
        final_url: str,
        body_len: int,
        etag: str | None,
        last_modified: str | None,
        status: int | None,
        changed: bool,
        is_new: bool,
    ) -> None:
        now = utc_now()
        primary = final_url or url
        with self.lock:
            prev = self.pages.get(url) or self.pages.get(primary)
            fetched_at = now if changed or is_new or not prev else prev.fetched_at
            rec = PageRecord(
                url=primary,
                path=path,
                content_hash=content_hash_value,
                fetched_at=fetched_at,
                checked_at=now,
                final_url=primary,
                etag=etag,
                last_modified=last_modified,
                bytes=body_len,
                status=status,
            )
            self.pages[primary] = rec
            if url != primary:
                self.pages[url] = rec
            self.dirty = True
            if is_new:
                self.stats["added"] += 1
            elif changed:
                self.stats["updated"] += 1
            else:
                self.stats["unchanged"] += 1
            self.stats["checked"] += 1

    def touch_checked(
        self,
        url: str,
        *,
        etag: str | None = None,
        last_modified: str | None = None,
        from_304: bool = False,
    ) -> None:
        now = utc_now()
        with self.lock:
            rec = self.pages.get(url)
            if rec is None:
                return
            rec.checked_at = now
            if etag:
                rec.etag = etag
            if last_modified:
                rec.last_modified = last_modified
            self.dirty = True
            self.stats["unchanged"] += 1
            self.stats["checked"] += 1
            if from_304:
                self.stats["not_modified_304"] += 1

    def remove(self, url: str) -> bool:
        with self.lock:
            rec = self.pages.pop(url, None)
            if rec is None:
                return False
            for key, val in list(self.pages.items()):
                if val is rec:
                    self.pages.pop(key, None)
            self.dirty = True
            return True


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------


def normalize_host_path(url: str) -> tuple[str, str, str] | None:
    # Unescape &amp; etc. so query keys like spoilPage survive parse_qsl.
    abs_url = urljoin(ORIGIN + "/", html.unescape(url.strip()))
    parsed = urlparse(abs_url)
    host = (parsed.hostname or "").lower()
    if host and host != HOST and not host.endswith("." + HOST):
        return None
    path = parsed.path or "/"
    path = LOCALE_RE.sub(r"\2", path)
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    return ORIGIN, path, parsed.query


def chronicle_from_path(path: str) -> str | None:
    parts = [p for p in path.split("/") if p]
    if not parts:
        return None
    return parts[0].lower()


def entity_key_from_path(path: str, query: str = "") -> str | None:
    """Path under chronicle, e.g. item/123-foo or skill/1-x/2 (+ optional query)."""
    chron = chronicle_from_path(path)
    if chron not in ALLOWED_CHRONICLES:
        return None
    parts = [p for p in path.split("/") if p]
    if len(parts) < 2:
        return None
    rest = "/".join(parts[1:])
    q = filter_html_query(query)
    return f"{rest}?{q}" if q else rest


def bwc_url_for_entity_key(key: str) -> str:
    if "?" in key:
        rest, q = key.split("?", 1)
        return canonical_html_url(f"/{CHRONICLE}/{rest}", q)
    return canonical_html_url(f"/{CHRONICLE}/{key}", "")


def gamma_url_for_entity_key(key: str) -> str:
    if "?" in key:
        rest, q = key.split("?", 1)
        return canonical_html_url(f"/lu4-gamma/{rest}", q)
    return canonical_html_url(f"/lu4-gamma/{key}", "")


def prefer_bwc_html_url(url: str) -> str:
    """Rewrite lu4-gamma HTML URLs to the preferred lu4-b-w-c twin."""
    norm = normalize_host_path(url)
    if norm is None:
        return url
    path, query = norm[1], norm[2]
    if chronicle_from_path(path) != "lu4-gamma":
        return canonical_html_url(path, query) if is_allowed_html(path) else url
    key = entity_key_from_path(path, query)
    if not key:
        return canonical_html_url(path, query)
    return bwc_url_for_entity_key(key)


def gamma_url_for_bwc_url(url: str) -> str | None:
    """Map a b-w-c URL to the same entity under lu4-gamma."""
    norm = normalize_host_path(url)
    if norm is None:
        return None
    path, query = norm[1], norm[2]
    if chronicle_from_path(path) != CHRONICLE:
        return None
    key = entity_key_from_path(path, query)
    if not key:
        return None
    return gamma_url_for_entity_key(key)


def entity_id_from_filename(name: str) -> str | None:
    """Leading numeric id from '981-red-sunset-sword.html' or query stems."""
    stem = Path(name).stem
    if "__" in stem:
        stem = stem.split("__", 1)[0]
    m = ENTITY_ID_RE.match(stem)
    return m.group(1) if m else None


def find_local_bwc_twins(gamma_local: Path) -> list[Path]:
    """Local b-w-c HTML that duplicates this gamma page (exact relative path only)."""
    gamma_root = OUT_DIR / "lu4-gamma"
    bwc_root = OUT_DIR / CHRONICLE
    try:
        rel = gamma_local.relative_to(gamma_root)
    except ValueError:
        return []
    exact = bwc_root / rel
    if exact.is_file() and exact.stat().st_size > 0:
        return [exact]
    return []


def find_local_gamma_twins(bwc_local: Path) -> list[Path]:
    """Local gamma HTML that duplicates this b-w-c page (exact relative path only)."""
    gamma_root = OUT_DIR / "lu4-gamma"
    bwc_root = OUT_DIR / CHRONICLE
    try:
        rel = bwc_local.relative_to(bwc_root)
    except ValueError:
        return []
    exact = gamma_root / rel
    if exact.is_file() and exact.stat().st_size > 0:
        return [exact]
    return []


def local_path_to_canon_url(local: Path) -> str | None:
    """Best-effort URL reconstruction from a saved HTML path under wikilu4/."""
    try:
        rel = local.relative_to(OUT_DIR).as_posix()
    except ValueError:
        return None
    if not rel.endswith(".html"):
        return None
    url_path = "/" + rel[: -len(".html")]
    name = Path(url_path).name
    query = ""
    if "__" in name:
        base, qpart = name.split("__", 1)
        url_path = str(Path(url_path).with_name(base)).replace("\\", "/")
        # Inverse of url_to_local_path query encoding: '=' -> '_', '&' -> '__'
        pairs: list[tuple[str, str]] = []
        for part in qpart.split("__"):
            if "_" not in part:
                continue
            key, val = part.split("_", 1)
            pairs.append((key, val))
        if pairs:
            query = urlencode(pairs)
    return canonical_html_url(url_path, query) if url_path.startswith("/") else None


def filter_html_query(query: str) -> str:
    if not query:
        return ""
    query = html.unescape(query)
    kept = [
        (k, v)
        for k, v in parse_qsl(query, keep_blank_values=True)
        if HTML_QUERY_KEEP.match(k)
    ]
    if not kept:
        return ""
    kept.sort(key=lambda kv: (kv[0], kv[1]))
    return urlencode(kept, doseq=True)


def delete_gamma_duplicates_for_bwc(
    bwc_url: str,
    index: PageIndex | None = None,
    state: CrawlState | None = None,
) -> int:
    """Delete gamma HTML twins of a saved b-w-c page; scrub index/queue. Returns deleted count."""
    local = url_to_local_path(bwc_url, is_html=True)
    to_delete: list[Path] = list(find_local_gamma_twins(local))
    g_exact = gamma_url_for_bwc_url(bwc_url)
    if g_exact:
        g_local = url_to_local_path(g_exact, is_html=True)
        if g_local.is_file() and g_local not in to_delete:
            to_delete.append(g_local)

    deleted = 0
    seen: set[Path] = set()
    for gpath in to_delete:
        resolved = gpath.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        try:
            gpath.unlink()
            deleted += 1
        except OSError as exc:
            log(f"WARN could not delete gamma dup {gpath}: {exc}")
            continue
        gurl = local_path_to_canon_url(gpath)
        if gurl and index is not None:
            index.remove(gurl)
            norm = normalize_host_path(gurl)
            if norm is not None:
                key = entity_key_from_path(norm[1], norm[2])
                if key:
                    index.remove(gamma_url_for_entity_key(key))
        if gurl and state is not None:
            state.mark_html_done(gurl)
    if g_exact:
        if index is not None:
            index.remove(g_exact)
        if state is not None:
            state.mark_html_done(g_exact)
    return deleted


def has_bwc_counterpart(url: str, index: PageIndex | None = None) -> bool:
    """True if this is (or maps to) a gamma URL whose b-w-c twin already exists locally."""
    norm = normalize_host_path(url)
    if norm is None:
        return False
    path, query = norm[1], norm[2]
    chron = chronicle_from_path(path)
    if chron != "lu4-gamma":
        return False
    key = entity_key_from_path(path, query)
    if not key:
        return False
    bwc = bwc_url_for_entity_key(key)
    local = url_to_local_path(bwc, is_html=True)
    if local.is_file() and local.stat().st_size > 0:
        return True
    if find_local_bwc_twins(url_to_local_path(canonical_html_url(path, query), is_html=True)):
        return True
    if index is not None and index.get(bwc) is not None:
        return True
    return False


def should_fetch_html(url: str, index: PageIndex | None = None) -> bool:
    """Whether URL is in scope and worth downloading (skip gamma dups of b-w-c)."""
    preferred = prefer_bwc_html_url(url)
    norm = normalize_host_path(preferred)
    if norm is None:
        return False
    path, query = norm[1], norm[2]
    if not is_allowed_html(path):
        return False
    # Gamma only if no local b-w-c twin; prefer_bwc already rewrote most cases.
    if chronicle_from_path(path) == "lu4-gamma":
        return not has_bwc_counterpart(canonical_html_url(path, query), index)
    return True


def is_allowed_html(path: str) -> bool:
    if chronicle_from_path(path) not in ALLOWED_CHRONICLES:
        return False
    lower = path.lower()
    return not any(lower.endswith(suf) for suf in SKIP_SUFFIXES)


def is_foreign_html(path: str) -> bool:
    return chronicle_from_path(path) in FOREIGN_CHRONICLES


def is_asset_path(path: str) -> bool:
    lower = path.lower()
    if any(lower.endswith(suf) for suf in SKIP_SUFFIXES):
        return True
    return any(path.startswith(p) for p in ASSET_PREFIXES)


def canonical_html_url(path: str, query: str = "") -> str:
    return urlunparse(("https", HOST, path, "", filter_html_query(query), ""))


def canonical_asset_url(path: str) -> str:
    return urlunparse(("https", HOST, path, "", "", ""))


def url_to_local_path(url: str, *, is_html: bool) -> Path:
    parsed = urlparse(url)
    path = parsed.path or "/"
    rel = "_root" if path == "/" else path.lstrip("/")
    local = OUT_DIR / rel
    if not is_html:
        return local
    if parsed.query:
        q = quote(parsed.query.replace("=", "_").replace("&", "__"), safe="._-[]%")
        if local.suffix.lower() in {".html", ".htm"}:
            return local.with_name(local.stem + "__" + q + local.suffix)
        return local.with_name(local.name + "__" + q + ".html")
    if local.suffix.lower() in {".html", ".htm"}:
        return local
    if local.suffix:
        return local.with_suffix(local.suffix + ".html")
    return local.with_name(local.name + ".html")


def purge_gamma_duplicates(index: PageIndex, state: CrawlState | None = None) -> dict[str, int]:
    """Delete gamma HTML that already has a b-w-c twin; scrub index + crawl queue."""
    deleted_files = 0
    gamma_root = OUT_DIR / "lu4-gamma"
    if gamma_root.is_dir():
        for gpath in list(gamma_root.rglob("*.html")):
            twins = find_local_bwc_twins(gpath)
            if not twins:
                continue
            try:
                gpath.unlink()
                deleted_files += 1
            except OSError as exc:
                log(f"WARN could not delete gamma dup {gpath}: {exc}")
                continue
            gurl = local_path_to_canon_url(gpath)
            if gurl:
                index.remove(gurl)
                if state is not None:
                    state.mark_html_done(gurl)

    removed_index = 0
    for url in list(index.urls()):
        if "/lu4-gamma/" not in url:
            continue
        if has_bwc_counterpart(url, index):
            if index.remove(url):
                removed_index += 1
            if state is not None:
                state.mark_html_done(url)

    dropped_frontier = 0
    rewritten_frontier = 0
    if state is not None:
        with state.lock:
            kept: deque[str] = deque()
            for url in state.frontier:
                if "/lu4-gamma/" not in url:
                    kept.append(url)
                    continue
                if has_bwc_counterpart(url, index):
                    state.frontier_set.discard(url)
                    state.visited.add(url)
                    dropped_frontier += 1
                    continue
                # Prefer fetching b-w-c instead of gamma.
                preferred = prefer_bwc_html_url(url)
                state.frontier_set.discard(url)
                state.visited.add(url)
                if preferred not in state.visited and preferred not in state.frontier_set:
                    kept.append(preferred)
                    state.frontier_set.add(preferred)
                    rewritten_frontier += 1
                else:
                    dropped_frontier += 1
            state.frontier = kept

    if index.dirty:
        index.save()

    return {
        "deleted_files": deleted_files,
        "removed_index": removed_index,
        "dropped_frontier": dropped_frontier,
        "rewritten_frontier": rewritten_frontier,
    }


def queue_bwc_promotions_from_gamma(
    state: CrawlState,
    index: PageIndex,
) -> int:
    """Enqueue b-w-c twins for every remaining local gamma page (promote away from gamma)."""
    gamma_root = OUT_DIR / "lu4-gamma"
    if not gamma_root.is_dir():
        return 0
    queued = 0
    seen: set[str] = set()
    for gpath in gamma_root.rglob("*.html"):
        if find_local_bwc_twins(gpath):
            continue
        gurl = local_path_to_canon_url(gpath)
        if not gurl:
            continue
        preferred = prefer_bwc_html_url(gurl)
        if preferred == gurl or preferred in seen:
            continue
        seen.add(preferred)
        if index.get(preferred) is not None:
            continue
        bwc_local = url_to_local_path(preferred, is_html=True)
        if bwc_local.is_file() and bwc_local.stat().st_size > 0:
            continue
        with state.lock:
            in_frontier = preferred in state.frontier_set
            previously_failed = preferred in state.failed
            already_ok = preferred in state.visited and not previously_failed
        if in_frontier or already_ok:
            continue
        if previously_failed:
            # Allow a fresh attempt so pages that exist on b-w-c can replace gamma.
            with state.lock:
                state.visited.discard(preferred)
                state.failed.pop(preferred, None)
                state.retry_counts.pop(preferred, None)
        state.enqueue_html(preferred)
        queued += 1
    return queued


def _force_requeue_html(state: CrawlState, url: str) -> bool:
    """Un-visit URL (and preferred twin) and enqueue. True if newly queued."""
    preferred = prefer_bwc_html_url(url)
    with state.lock:
        state.visited.discard(url)
        state.visited.discard(preferred)
        state.failed.pop(url, None)
        state.failed.pop(preferred, None)
        state.retry_counts.pop(url, None)
        state.retry_counts.pop(preferred, None)
        already = preferred in state.frontier_set
    if already:
        return False
    state.enqueue_html(preferred)
    return True


def revive_missing_html(state: CrawlState, prior: CrawlState | None = None) -> int:
    """Requeue visited/failed HTML URLs that have no local file on disk.

    When ``prior`` is set (e.g. recheck with a fresh state), candidates are taken
    from that previous crawl state.
    """
    source = prior if prior is not None else state
    with source.lock:
        candidates = list(source.visited) + list(source.failed.keys())
    revived = 0
    seen: set[str] = set()
    for url in candidates:
        preferred = prefer_bwc_html_url(url)
        if preferred in seen:
            continue
        seen.add(preferred)
        norm = normalize_host_path(preferred)
        if norm is None or not is_allowed_html(norm[1]):
            continue
        local = url_to_local_path(preferred, is_html=True)
        if local.is_file() and local.stat().st_size > 0:
            continue
        if _force_requeue_html(state, preferred):
            revived += 1
    return revived


def revive_missing_from_index(state: CrawlState, index: PageIndex) -> int:
    """Requeue indexed URLs whose HTML file is missing on disk."""
    revived = 0
    for url in index.urls():
        preferred = prefer_bwc_html_url(url)
        local = url_to_local_path(preferred, is_html=True)
        if local.is_file() and local.stat().st_size > 0:
            continue
        if _force_requeue_html(state, preferred):
            revived += 1
    return revived


def apply_pagination_repair(
    state: CrawlState,
    index: PageIndex,
    *,
    prior: CrawlState | None = None,
) -> dict[str, int]:
    """Revive missing HTML + reseed drop/spoil pager edges into ``state``."""
    missing_visited = revive_missing_html(state, prior=prior)
    missing_index = revive_missing_from_index(state, index)
    pager = repair_pagination_seeds(state)
    return {
        "missing_visited": missing_visited,
        "missing_index": missing_index,
        "pager_seeds": pager,
    }


def enqueue_discovered_html(
    state: CrawlState,
    index: PageIndex,
    html_links: set[str],
) -> int:
    """Enqueue unknown or on-disk-missing HTML links (fills pagination gaps)."""
    queued = 0
    for link in html_links:
        if not should_fetch_html(link, index):
            continue
        preferred = prefer_bwc_html_url(link)
        local = url_to_local_path(preferred, is_html=True)
        missing_file = not (local.is_file() and local.stat().st_size > 0)
        unknown = index.get(preferred) is None and index.get(link) is None
        if not (missing_file or unknown):
            continue
        if missing_file:
            if _force_requeue_html(state, preferred):
                queued += 1
            continue
        with state.lock:
            already = preferred in state.frontier_set or preferred in state.visited
        if already:
            continue
        state.enqueue_html(preferred)
        queued += 1
    return queued


def repair_pagination_seeds(state: CrawlState, *, min_edge: int = 8) -> int:
    """Requeue local drop/spoil pages so pager windows can walk past page 10.

    Also requeues base item/npc pages that already have high dropPage files, so
    fixed &amp; parsing rediscovers dropPage+spoilPage combo links.
    """
    bwc_root = OUT_DIR / CHRONICLE
    if not bwc_root.is_dir():
        return 0
    queued = 0
    seen: set[str] = set()
    base_entities: set[Path] = set()

    for path in bwc_root.rglob("*.html"):
        name = path.name
        if "dropPage" not in name and "spoilPage" not in name:
            continue
        nums = [int(n) for n in PAGINATION_FILE_RE.findall(name)]
        # Always reseed high pages; also any spoil/drop variant to rediscover combos.
        if nums and max(nums) < min_edge and "spoilPage" not in name:
            continue
        url = local_path_to_canon_url(path)
        if not url or url in seen:
            continue
        seen.add(url)
        if _force_requeue_html(state, url):
            queued += 1
        # Track base entity file (strip query suffix) for combo rediscovery.
        stem = path.stem
        if "__" in stem:
            base_name = stem.split("__", 1)[0] + ".html"
            base_entities.add(path.with_name(base_name))

    for base in base_entities:
        if not (base.is_file() and base.stat().st_size > 0):
            continue
        url = local_path_to_canon_url(base)
        if not url or url in seen:
            continue
        seen.add(url)
        if _force_requeue_html(state, url):
            queued += 1
    return queued


def seed_urls() -> list[str]:
    seeds = [
        START,
        f"{ORIGIN}{PREFIX}/classes",
        f"{ORIGIN}{PREFIX}/posts",
    ]
    for search_type in range(6):
        qs = urlencode(
            {
                "Search[query]": "",
                "Search[search_type]": search_type,
                "per_page": 100,
                "page": 1,
            }
        )
        seeds.append(f"{ORIGIN}{PREFIX}/search/result?{qs}")
    return seeds


def extract_urls(html: str, base_url: str) -> tuple[set[str], set[str]]:
    html_urls: set[str] = set()
    asset_urls: set[str] = set()

    def consider(raw: str) -> None:
        raw = raw.strip()
        if not raw or raw.startswith(("data:", "javascript:", "mailto:", "tel:", "#")):
            return
        norm = normalize_host_path(urljoin(base_url, raw))
        if norm is None:
            return
        _, path, query = norm
        if is_allowed_html(path):
            html_urls.add(prefer_bwc_html_url(canonical_html_url(path, query)))
        elif is_asset_path(path):
            asset_urls.add(canonical_asset_url(path))

    for attr in HREF_ATTRS:
        for match in re.finditer(rf'\b{attr}\s*=\s*["\']([^"\']+)["\']', html, re.I):
            consider(match.group(1))
    for attr in SRCSET_ATTRS:
        for match in re.finditer(rf'\b{attr}\s*=\s*["\']([^"\']+)["\']', html, re.I):
            for part in match.group(1).split(","):
                consider(part.strip().split(" ")[0])
    for match in URL_IN_CSS.finditer(html):
        consider(match.group(1))
    return html_urls, asset_urls


# ---------------------------------------------------------------------------
# Rate limit + adaptive throttle
# ---------------------------------------------------------------------------


class RateLimiter:
    """Token-bucket style limiter shared by all workers."""

    def __init__(self, rps: float) -> None:
        self._base_rps = max(0.5, rps)
        self._rps = self._base_rps
        self._lock = threading.Lock()
        self._next = time.monotonic()
        self._cooldown_until = 0.0
        self._recent_soft = 0
        self._recent_ok = 0
        self._window_started = time.monotonic()

    @property
    def rps(self) -> float:
        with self._lock:
            return self._rps

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            if now < self._cooldown_until:
                delay = self._cooldown_until - now
            else:
                delay = 0.0
            slot = max(self._next, now)
            interval = 1.0 / self._rps
            # Small jitter avoids synchronized bursts.
            jitter = random.uniform(0.0, interval * 0.15)
            self._next = slot + interval
            delay = max(delay, slot - now) + jitter
        if delay > 0:
            time.sleep(delay)

    def note_success(self) -> None:
        with self._lock:
            self._recent_ok += 1
            self._maybe_adapt_unlocked()

    def note_soft_error(self, retry_after: float | None = None) -> None:
        with self._lock:
            self._recent_soft += 1
            # Cut rate and optionally pause everyone.
            self._rps = max(0.5, self._rps * 0.55)
            cool = retry_after if retry_after is not None else min(30.0, 2.0 + self._recent_soft)
            cool = max(1.0, min(60.0, cool))
            self._cooldown_until = max(self._cooldown_until, time.monotonic() + cool)
            self._maybe_adapt_unlocked()
            log(
                f"THROTTLE soft-error rps={self._rps:.2f} cooldown={cool:.1f}s "
                f"(ok={self._recent_ok} soft={self._recent_soft})"
            )

    def _maybe_adapt_unlocked(self) -> None:
        now = time.monotonic()
        if now - self._window_started < 20.0:
            return
        total = self._recent_ok + self._recent_soft
        if total >= 20:
            soft_ratio = self._recent_soft / total
            if soft_ratio == 0 and self._rps < self._base_rps:
                self._rps = min(self._base_rps, self._rps * 1.15)
            elif soft_ratio > 0.15:
                self._rps = max(0.5, self._rps * 0.7)
        self._recent_ok = 0
        self._recent_soft = 0
        self._window_started = now


def parse_retry_after(resp: httpx.Response) -> float | None:
    raw = resp.headers.get("Retry-After")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


@dataclass
class FetchResult:
    ok: bool
    final_url: str = ""
    body: bytes = b""
    ctype: str = ""
    status: int | None = None
    soft: bool = False
    hard: bool = False
    error: str = ""
    retry_after: float | None = None
    etag: str | None = None
    last_modified: str | None = None
    not_modified: bool = False


def fetch_once(
    client: httpx.Client,
    limiter: RateLimiter,
    url: str,
    *,
    extra_headers: dict[str, str] | None = None,
) -> FetchResult:
    limiter.wait()
    try:
        resp = client.get(url, follow_redirects=True, headers=extra_headers or None)
    except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
        limiter.note_soft_error()
        return FetchResult(ok=False, soft=True, error=f"{type(exc).__name__}: {exc}")
    except Exception as exc:  # noqa: BLE001
        return FetchResult(ok=False, hard=True, error=f"{type(exc).__name__}: {exc}")

    status = resp.status_code
    etag = resp.headers.get("ETag")
    last_modified = resp.headers.get("Last-Modified")

    if status == 304:
        limiter.note_success()
        return FetchResult(
            ok=True,
            final_url=str(resp.url),
            status=304,
            not_modified=True,
            etag=etag,
            last_modified=last_modified,
        )

    if status in SOFT_STATUS:
        ra = parse_retry_after(resp)
        limiter.note_soft_error(ra)
        return FetchResult(
            ok=False,
            status=status,
            soft=True,
            error=f"HTTP {status}",
            retry_after=ra,
        )
    if status in HARD_STATUS or status >= 400:
        return FetchResult(ok=False, status=status, hard=True, error=f"HTTP {status}")

    limiter.note_success()
    ctype = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
    return FetchResult(
        ok=True,
        final_url=str(resp.url),
        body=resp.content,
        ctype=ctype,
        status=status,
        etag=etag,
        last_modified=last_modified,
    )


def fetch_with_retries(
    client: httpx.Client,
    limiter: RateLimiter,
    url: str,
    *,
    max_retries: int,
    extra_headers: dict[str, str] | None = None,
) -> FetchResult:
    last = FetchResult(ok=False, error="no attempt")
    for attempt in range(max_retries + 1):
        last = fetch_once(client, limiter, url, extra_headers=extra_headers)
        if last.ok or last.hard:
            return last
        base = last.retry_after if last.retry_after is not None else (1.5 * (2**attempt))
        sleep_for = min(45.0, base) + random.uniform(0.05, 0.4)
        time.sleep(sleep_for)
    return last


# ---------------------------------------------------------------------------
# Crawl state
# ---------------------------------------------------------------------------


class CrawlState:
    def __init__(self) -> None:
        self.visited: set[str] = set()
        self.frontier: deque[str] = deque()
        self.frontier_set: set[str] = set()
        self.failed: dict[str, str] = {}
        self.retry_counts: dict[str, int] = {}
        self.assets_done: set[str] = set()
        self.assets_frontier: deque[str] = deque()
        self.assets_frontier_set: set[str] = set()
        self.pages_saved = 0
        self.assets_saved = 0
        self.html_processed = 0
        self.html_inflight = 0
        self.asset_inflight = 0
        self.stop = False
        self.foreign_redirects: dict[str, str] = {}
        self.lock = threading.Lock()

    def enqueue_html(self, url: str) -> None:
        # Always prefer lu4-b-w-c twin when a gamma link is discovered.
        preferred = prefer_bwc_html_url(url)
        with self.lock:
            if preferred in self.visited or preferred in self.frontier_set:
                return
            self.frontier.append(preferred)
            self.frontier_set.add(preferred)

    def enqueue_asset(self, url: str) -> None:
        with self.lock:
            if url in self.assets_done or url in self.assets_frontier_set:
                return
            self.assets_frontier.append(url)
            self.assets_frontier_set.add(url)

    def claim_html(self) -> str | None:
        with self.lock:
            if self.stop or not self.frontier:
                return None
            url = self.frontier.popleft()
            self.frontier_set.discard(url)
            self.html_inflight += 1
            return url

    def claim_asset(self) -> str | None:
        with self.lock:
            if self.stop or not self.assets_frontier:
                return None
            url = self.assets_frontier.popleft()
            self.assets_frontier_set.discard(url)
            self.asset_inflight += 1
            return url

    def release_html_inflight(self) -> None:
        with self.lock:
            self.html_inflight = max(0, self.html_inflight - 1)

    def release_asset_inflight(self) -> None:
        with self.lock:
            self.asset_inflight = max(0, self.asset_inflight - 1)

    def requeue_html(self, url: str, err: str, *, max_retries: int) -> bool:
        """Return True if requeued, False if permanently failed."""
        with self.lock:
            n = self.retry_counts.get(url, 0) + 1
            self.retry_counts[url] = n
            if n > max_retries:
                self.visited.add(url)
                self.failed[url] = err
                return False
            if url not in self.frontier_set and url not in self.visited:
                self.frontier.append(url)
                self.frontier_set.add(url)
            return True

    def requeue_asset(self, url: str, *, max_retries: int) -> bool:
        with self.lock:
            key = f"asset:{url}"
            n = self.retry_counts.get(key, 0) + 1
            self.retry_counts[key] = n
            if n > max_retries:
                self.assets_done.add(url)
                return False
            if url not in self.assets_frontier_set and url not in self.assets_done:
                self.assets_frontier.append(url)
                self.assets_frontier_set.add(url)
            return True

    def mark_html_done(self, *urls: str) -> None:
        with self.lock:
            for url in urls:
                self.visited.add(url)
                self.failed.pop(url, None)
                self.retry_counts.pop(url, None)

    def mark_html_failed(self, url: str, err: str) -> None:
        with self.lock:
            self.visited.add(url)
            self.failed[url] = err

    def mark_asset_done(self, url: str) -> None:
        with self.lock:
            self.assets_done.add(url)
            self.retry_counts.pop(f"asset:{url}", None)

    def note_foreign_redirect(self, src: str, dst: str) -> bool:
        """Record foreign redirect. True if newly added."""
        with self.lock:
            if src in self.foreign_redirects:
                return False
            self.foreign_redirects[src] = dst
            return True

    def revive_html(self, url: str) -> bool:
        """Un-visit a URL and put it back on the frontier. True if enqueued."""
        with self.lock:
            self.visited.discard(url)
            self.failed.pop(url, None)
            self.retry_counts.pop(url, None)
            if url in self.frontier_set:
                return False
            self.frontier.append(url)
            self.frontier_set.add(url)
            return True

    def bump_pages(self) -> tuple[int, int]:
        with self.lock:
            self.pages_saved += 1
            return self.pages_saved, len(self.frontier)

    def bump_processed(self) -> int:
        with self.lock:
            self.html_processed += 1
            return self.html_processed

    def bump_assets(self) -> int:
        with self.lock:
            self.assets_saved += 1
            return self.assets_saved

    def idle(self) -> bool:
        with self.lock:
            return (
                not self.frontier
                and not self.assets_frontier
                and self.html_inflight == 0
                and self.asset_inflight == 0
            )

    def html_idle(self) -> bool:
        with self.lock:
            return not self.frontier and self.html_inflight == 0

    def request_stop(self) -> None:
        with self.lock:
            self.stop = True

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "updated_at": utc_now(),
                "pages_saved": self.pages_saved,
                "assets_saved": self.assets_saved,
                "visited": sorted(self.visited),
                "frontier": list(self.frontier),
                "failed": dict(self.failed),
                "retry_counts": dict(self.retry_counts),
                "assets_done": sorted(self.assets_done),
                "assets_frontier": list(self.assets_frontier),
                "foreign_redirects": dict(sorted(self.foreign_redirects.items())),
            }

    def load(self, data: dict[str, Any]) -> None:
        self.visited = set(data.get("visited") or [])
        self.frontier = deque(data.get("frontier") or [])
        self.frontier_set = set(self.frontier)
        self.failed = dict(data.get("failed") or {})
        self.retry_counts = dict(data.get("retry_counts") or {})
        self.assets_done = set(data.get("assets_done") or [])
        self.assets_frontier = deque(data.get("assets_frontier") or [])
        self.assets_frontier_set = set(self.assets_frontier)
        self.pages_saved = int(data.get("pages_saved") or 0)
        self.assets_saved = int(data.get("assets_saved") or 0)
        self.foreign_redirects = dict(data.get("foreign_redirects") or {})


def save_state(state: CrawlState) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    payload = json.dumps(state.snapshot(), ensure_ascii=False, separators=(",", ":"))
    last_exc: Exception | None = None
    for attempt in range(6):
        try:
            tmp.write_text(payload, encoding="utf-8")
            tmp.replace(STATE_PATH)
            return
        except PermissionError as exc:
            last_exc = exc
            time.sleep(0.2 * (attempt + 1))
        except OSError as exc:
            last_exc = exc
            time.sleep(0.2 * (attempt + 1))
    log(f"WARN save_state failed after retries: {last_exc}")


def load_state() -> CrawlState:
    state = CrawlState()
    if STATE_PATH.exists():
        state.load(json.loads(STATE_PATH.read_text(encoding="utf-8")))
    return state


def append_manifest(row: dict[str, Any]) -> None:
    with _manifest_lock:
        with MANIFEST_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_foreign_list(state: CrawlState) -> None:
    """Rewrite human-readable list of redirects into masterwork/eternal."""
    with state.lock:
        items = sorted(state.foreign_redirects.items())
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [f"{src} -> {dst}" for src, dst in items]
    FOREIGN_TXT.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def append_foreign_jsonl(src: str, dst: str) -> None:
    with _manifest_lock:
        with FOREIGN_JSONL.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {"from": src, "to": dst, "at": utc_now()},
                    ensure_ascii=False,
                )
                + "\n"
            )


def restore_gamma_skips(state: CrawlState, index: PageIndex | None = None) -> int:
    """Re-queue URLs previously skipped because they redirected to lu4-gamma.

    Enqueues the preferred lu4-b-w-c twin (gamma only as fetch fallback on 404).
    Skips when a b-w-c counterpart already exists locally.
    """
    if not LOG_PATH.exists():
        return 0
    revived = 0
    seen_src: set[str] = set()
    text = LOG_PATH.read_text(encoding="utf-8", errors="replace")
    for match in SKIP_LOG_RE.finditer(text):
        src, dst = match.group(1), match.group(2)
        if src in seen_src:
            continue
        seen_src.add(src)
        norm = normalize_host_path(dst)
        if norm is None:
            continue
        if chronicle_from_path(norm[1]) != "lu4-gamma":
            continue
        final_canon = canonical_html_url(norm[1], norm[2])
        if has_bwc_counterpart(final_canon, index):
            continue
        preferred = prefer_bwc_html_url(final_canon)
        bwc_local = url_to_local_path(preferred, is_html=True)
        if bwc_local.exists() and bwc_local.stat().st_size > 0:
            continue
        with state.lock:
            if src not in state.visited:
                continue
            state.visited.discard(src)
            state.failed.pop(src, None)
            state.retry_counts.pop(src, None)
        with state.lock:
            already = preferred in state.visited or preferred in state.frontier_set
        if already:
            continue
        state.enqueue_html(preferred)
        revived += 1
    return revived


def write_html(path: Path, source_url: str, body: bytes, final_url: str) -> str:
    """Write HTML with banner; return decoded body text (without banner)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = body.decode("utf-8", "replace")
    banner = (
        f"<!-- saved-from: {source_url}\n"
        f"     final-url: {final_url}\n"
        f"     fetched-at: {utc_now()} -->\n"
    )
    path.write_text(banner + text, encoding="utf-8", errors="replace")
    return text


def write_bytes(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)


def commit_html_page(
    *,
    index: PageIndex,
    state: CrawlState,
    requested_url: str,
    final_canon: str,
    local: Path,
    body_text: str,
    body_len: int,
    etag: str | None,
    last_modified: str | None,
    status: int | None,
    html_links: set[str],
    asset_links: set[str],
    skip_assets: bool,
    recheck_mode: bool,
) -> str:
    """Update index + queues after an HTML body is on disk. Returns change kind."""
    digest = content_hash(body_text)
    prev = index.get(requested_url) or index.get(final_canon)
    is_new = prev is None
    changed = is_new or prev.content_hash != digest
    rel = str(local.relative_to(OUT_DIR)).replace("\\", "/")

    index.upsert(
        url=requested_url,
        path=rel,
        content_hash_value=digest,
        final_url=final_canon,
        body_len=body_len,
        etag=etag,
        last_modified=last_modified,
        status=status,
        changed=changed,
        is_new=is_new,
    )

    if recheck_mode:
        # Always fill gaps: unknown URLs or files missing on disk (pagination).
        enqueue_discovered_html(state, index, html_links)
        if not skip_assets:
            for link in asset_links:
                state.enqueue_asset(link)
    else:
        for link in html_links:
            if should_fetch_html(link, index):
                state.enqueue_html(link)
        if not skip_assets:
            for link in asset_links:
                state.enqueue_asset(link)

    append_manifest(
        {
            "type": "html",
            "url": final_canon,
            "requested": requested_url,
            "path": rel,
            "bytes": body_len,
            "content_hash": digest,
            "changed": changed,
            "links": len(html_links),
            "assets": len(asset_links),
            "at": utc_now(),
        }
    )
    if is_new:
        return "added"
    if changed:
        return "updated"
    return "unchanged"


# ---------------------------------------------------------------------------
# Workers
# ---------------------------------------------------------------------------


def process_html(
    client: httpx.Client,
    limiter: RateLimiter,
    state: CrawlState,
    index: PageIndex,
    url: str,
    *,
    skip_assets: bool,
    max_retries: int,
    recheck_mode: bool,
) -> None:
    try:
        original_url = url
        # Prefer b-w-c: never download gamma when we can try the twin first.
        preferred = prefer_bwc_html_url(url)
        gamma_fallback = (
            original_url
            if "/lu4-gamma/" in original_url
            else gamma_url_for_bwc_url(preferred)
        )
        url = preferred
        url_chron = chronicle_from_path(urlparse(url).path)

        # Only skip when we would still fetch gamma and a local b-w-c twin exists.
        # Never skip a b-w-c URL here — recheck must still validate it.
        if url_chron == "lu4-gamma":
            if not should_fetch_html(url, index) or has_bwc_counterpart(url, index):
                bwc = prefer_bwc_html_url(url)
                deleted = delete_gamma_duplicates_for_bwc(bwc, index, state)
                state.mark_html_done(original_url, url, bwc)
                log(
                    f"SKIP gamma duplicate (b-w-c exists) {original_url}"
                    + (f" deleted_gamma={deleted}" if deleted else "")
                )
                return
        elif url_chron == CHRONICLE:
            # Clean leftover gamma twins only when b-w-c is already on disk, then continue.
            bwc_local = url_to_local_path(url, is_html=True)
            if bwc_local.is_file() and bwc_local.stat().st_size > 0:
                deleted = delete_gamma_duplicates_for_bwc(url, index, state)
                if deleted:
                    log(f"PURGE gamma dups for {url}: deleted={deleted}")
                if gamma_fallback:
                    state.mark_html_done(gamma_fallback)

        if not should_fetch_html(url, index):
            state.mark_html_done(original_url, url)
            log(f"SKIP out-of-scope {original_url}")
            return

        extra: dict[str, str] = {}
        existing = index.get(url) if recheck_mode else None
        if existing:
            if existing.etag:
                extra["If-None-Match"] = existing.etag
            elif existing.last_modified:
                extra["If-Modified-Since"] = existing.last_modified

        result = fetch_with_retries(
            client,
            limiter,
            url,
            max_retries=max_retries,
            extra_headers=extra or None,
        )

        # b-w-c missing remotely → fall back to gamma only if still needed.
        if (
            not result.ok
            and result.hard
            and result.status == 404
            and chronicle_from_path(urlparse(url).path) == CHRONICLE
            and gamma_fallback
            and not has_bwc_counterpart(gamma_fallback, index)
        ):
            log(f"FALLBACK gamma (b-w-c 404) {url} -> {gamma_fallback}")
            state.mark_html_done(url)  # don't retry missing b-w-c forever
            url = gamma_fallback
            if not should_fetch_html(url, index):
                state.mark_html_done(original_url, url)
                return
            result = fetch_with_retries(
                client,
                limiter,
                url,
                max_retries=max_retries,
            )

        if not result.ok:
            if result.soft:
                if state.requeue_html(url, result.error, max_retries=max_retries):
                    log(f"RETRY html {url} ({result.error})")
                else:
                    log(f"FAIL html {url} ({result.error})")
            else:
                state.mark_html_failed(url, result.error)
                if original_url != url:
                    state.mark_html_done(original_url)
                log(f"FAIL html {url} ({result.error})")
            return

        if result.not_modified:
            index.touch_checked(
                url,
                etag=result.etag,
                last_modified=result.last_modified,
                from_304=True,
            )
            state.mark_html_done(original_url, url)
            if gamma_fallback and chronicle_from_path(urlparse(url).path) == CHRONICLE:
                delete_gamma_duplicates_for_bwc(url, index, state)
            # 304 has no body — rediscover missing pagination from local HTML.
            if recheck_mode:
                local_existing = url_to_local_path(url, is_html=True)
                if local_existing.is_file() and local_existing.stat().st_size > 0:
                    try:
                        raw = local_existing.read_text(encoding="utf-8", errors="replace")
                    except OSError:
                        raw = ""
                    if raw:
                        body_local = strip_saved_banner(raw)
                        html_links, asset_links = extract_urls(body_local, url)
                        enqueue_discovered_html(state, index, html_links)
                        if not skip_assets:
                            for link in asset_links:
                                state.enqueue_asset(link)
            return

        final_url = result.final_url
        norm = normalize_host_path(final_url)
        if norm is None:
            state.mark_html_done(original_url, url)
            log(f"SKIP external redirect {url} -> {final_url}")
            return

        path, query = norm[1], norm[2]
        if is_foreign_html(path):
            final_canon = canonical_html_url(path, query)
            state.mark_html_done(original_url, url)
            if state.note_foreign_redirect(url, final_canon):
                append_foreign_jsonl(url, final_canon)
                write_foreign_list(state)
                log(f"FOREIGN redirect {url} -> {final_canon}")
            return

        if not is_allowed_html(path):
            state.mark_html_done(original_url, url)
            log(f"SKIP other-chronicle redirect {url} -> {final_url}")
            return

        final_canon = canonical_html_url(path, query)

        # Redirect landed on gamma: prefer rewriting to b-w-c twin when local twin exists,
        # or if final is gamma and b-w-c twin already saved.
        if chronicle_from_path(path) == "lu4-gamma":
            if has_bwc_counterpart(final_canon, index):
                deleted = delete_gamma_duplicates_for_bwc(
                    prefer_bwc_html_url(final_canon), index, state
                )
                state.mark_html_done(original_url, url, final_canon)
                log(
                    f"SKIP gamma duplicate (b-w-c exists) {url} -> {final_canon}"
                    + (f" deleted_gamma={deleted}" if deleted else "")
                )
                return
            # Remote redirected to gamma — try saving under preferred b-w-c path only when
            # the body came from a b-w-c request that bounced; keep gamma file as last resort.
            preferred_final = prefer_bwc_html_url(final_canon)
            if preferred_final != final_canon:
                # Attempt dedicated b-w-c fetch once more if we only have gamma content.
                bwc_try = fetch_with_retries(
                    client, limiter, preferred_final, max_retries=max_retries
                )
                if bwc_try.ok and not bwc_try.not_modified:
                    result = bwc_try
                    final_url = bwc_try.final_url
                    norm2 = normalize_host_path(final_url)
                    if norm2 is not None and is_allowed_html(norm2[1]):
                        path, query = norm2[1], norm2[2]
                        final_canon = canonical_html_url(path, query)
                    else:
                        final_canon = preferred_final
                        path = urlparse(final_canon).path
                elif bwc_try.ok and bwc_try.not_modified:
                    index.touch_checked(
                        preferred_final,
                        etag=bwc_try.etag,
                        last_modified=bwc_try.last_modified,
                        from_304=True,
                    )
                    delete_gamma_duplicates_for_bwc(preferred_final, index, state)
                    state.mark_html_done(original_url, url, final_canon, preferred_final)
                    return

        local = url_to_local_path(final_canon, is_html=True)

        if result.ctype and "html" not in result.ctype and not result.ctype.startswith("text/"):
            write_bytes(local, result.body)
            state.mark_html_done(original_url, url, final_canon)
            if chronicle_from_path(path) == CHRONICLE:
                delete_gamma_duplicates_for_bwc(final_canon, index, state)
            return

        body_text = result.body.decode("utf-8", "replace")
        digest = content_hash(body_text)
        prev = index.get(url) or index.get(final_canon) or index.get(original_url)

        if recheck_mode and prev and prev.content_hash == digest:
            index.touch_checked(
                url,
                etag=result.etag or prev.etag,
                last_modified=result.last_modified or prev.last_modified,
            )
            if final_canon != url:
                index.touch_checked(
                    final_canon,
                    etag=result.etag,
                    last_modified=result.last_modified,
                )
            state.mark_html_done(original_url, url, final_canon)
            if chronicle_from_path(path) == CHRONICLE:
                delete_gamma_duplicates_for_bwc(final_canon, index, state)
            # Unchanged body still yields missing drop/spoil links after &amp; fix.
            html_links, asset_links = extract_urls(body_text, final_canon)
            enqueue_discovered_html(state, index, html_links)
            if not skip_assets:
                for link in asset_links:
                    state.enqueue_asset(link)
            return

        write_html(local, source_url=url, body=result.body, final_url=final_canon)
        html_links, asset_links = extract_urls(body_text, final_canon)
        kind = commit_html_page(
            index=index,
            state=state,
            requested_url=url,
            final_canon=final_canon,
            local=local,
            body_text=body_text,
            body_len=len(result.body),
            etag=result.etag,
            last_modified=result.last_modified,
            status=result.status,
            html_links=html_links,
            asset_links=asset_links,
            skip_assets=skip_assets,
            recheck_mode=recheck_mode,
        )

        if chronicle_from_path(path) == CHRONICLE:
            deleted = delete_gamma_duplicates_for_bwc(final_canon, index, state)
            if deleted:
                log(f"PURGE gamma dups for {final_canon}: deleted={deleted}")

        n, q = state.bump_pages()
        state.mark_html_done(original_url, url, final_canon)
        if gamma_fallback:
            state.mark_html_done(gamma_fallback)
        if kind != "unchanged" or n % 25 == 0 or n <= 10:
            chron = chronicle_from_path(path) or "?"
            log(f"OK html [{n}] {kind} queue={q} rps~{limiter.rps:.1f} [{chron}] {final_canon}")
    finally:
        state.bump_processed()
        state.release_html_inflight()


def process_asset(
    client: httpx.Client,
    limiter: RateLimiter,
    state: CrawlState,
    url: str,
    *,
    max_retries: int,
) -> None:
    try:
        local = url_to_local_path(url, is_html=False)
        if local.exists() and local.stat().st_size > 0:
            state.mark_asset_done(url)
            return

        result = fetch_with_retries(client, limiter, url, max_retries=max_retries)
        if not result.ok:
            if result.soft:
                if state.requeue_asset(url, max_retries=max_retries):
                    log(f"RETRY asset {url} ({result.error})")
                else:
                    log(f"FAIL asset {url} ({result.error})")
            else:
                state.mark_asset_done(url)
                if result.status != 404:
                    log(f"FAIL asset {url} ({result.error})")
            return

        final_url = result.final_url
        norm = normalize_host_path(final_url)
        if norm is not None and is_asset_path(norm[1]):
            local = url_to_local_path(canonical_asset_url(norm[1]), is_html=False)

        write_bytes(local, result.body)
        n = state.bump_assets()
        state.mark_asset_done(url)
        append_manifest(
            {
                "type": "asset",
                "url": url,
                "final_url": final_url,
                "path": str(local.relative_to(OUT_DIR)).replace("\\", "/"),
                "bytes": len(result.body),
                "at": utc_now(),
            }
        )
        if n % 100 == 0:
            with state.lock:
                aq = len(state.assets_frontier)
            log(f"OK assets saved={n} queue={aq} rps~{limiter.rps:.1f}")
    finally:
        state.release_asset_inflight()


def build_index_from_disk() -> int:
    """Hash existing HTML under allowed chronicles into _pages.json."""
    index = PageIndex()
    if PAGES_INDEX_PATH.exists():
        index.load()
    count = 0
    for chron in sorted(ALLOWED_CHRONICLES):
        root = OUT_DIR / chron
        if not root.exists():
            continue
        for path in root.rglob("*.html"):
            try:
                raw = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            body = strip_saved_banner(raw)
            digest = content_hash(body)
            rel = str(path.relative_to(OUT_DIR)).replace("\\", "/")
            # Recover URL from banner when present.
            url = None
            m = re.search(r"final-url:\s*(\S+)", raw[:500])
            if m:
                url = m.group(1).rstrip(" -->")
            if not url:
                m2 = re.search(r"saved-from:\s*(\S+)", raw[:500])
                if m2:
                    url = m2.group(1)
            if not url:
                # Reconstruct from path: lu4-b-w-c/item/x.html -> /lu4-b-w-c/item/x
                stem = path.as_posix()
                if stem.startswith(str(OUT_DIR).replace("\\", "/") + "/"):
                    pass
                url_path = "/" + rel
                if url_path.endswith(".html"):
                    url_path = url_path[: -len(".html")]
                # Drop query-encoded filename suffixes for index key when possible.
                if "__" in Path(url_path).name:
                    # Keep as file-derived URL without query — still unique enough with path.
                    pass
                url = ORIGIN + url_path
            norm = normalize_host_path(url)
            if norm is None or not is_allowed_html(norm[1]):
                continue
            canon = canonical_html_url(norm[1], norm[2])
            now = utc_now()
            prev = index.get(canon)
            index.upsert(
                url=canon,
                path=rel,
                content_hash_value=digest,
                final_url=canon,
                body_len=path.stat().st_size,
                etag=prev.etag if prev else None,
                last_modified=prev.last_modified if prev else None,
                status=200,
                changed=prev is None or prev.content_hash != digest,
                is_new=prev is None,
            )
            count += 1
            if count % 500 == 0:
                log(f"build-index hashed {count} files…")
    index.save()
    log(f"build-index done: {len(index)} pages in {PAGES_INDEX_PATH}")
    return 0


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_crawl(args: argparse.Namespace) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    index = PageIndex()
    if PAGES_INDEX_PATH.exists() and not (args.fresh and args.fresh_index):
        index.load()

    if args.build_index:
        stats = purge_gamma_duplicates(index, None)
        log(
            f"Purged gamma duplicates before build-index: "
            f"files={stats['deleted_files']} index={stats['removed_index']}"
        )
        return build_index_from_disk()

    if args.purge_gamma:
        state = load_state() if STATE_PATH.exists() else CrawlState()
        stats = purge_gamma_duplicates(index, state)
        if STATE_PATH.exists():
            save_state(state)
        log(
            f"Gamma purge done: deleted_files={stats['deleted_files']} "
            f"removed_index={stats['removed_index']} "
            f"dropped_frontier={stats['dropped_frontier']} "
            f"rewritten_frontier={stats.get('rewritten_frontier', 0)}"
        )
        return 0

    if args.status:
        if STATE_PATH.exists():
            st = load_state()
            snap = st.snapshot()
        else:
            snap = {
                "pages_saved": 0,
                "assets_saved": 0,
                "visited": [],
                "frontier": [],
                "failed": {},
                "assets_done": [],
                "assets_frontier": [],
                "foreign_redirects": {},
            }
        print(
            json.dumps(
                {
                    "pages_saved": snap["pages_saved"],
                    "assets_saved": snap["assets_saved"],
                    "visited": len(snap["visited"]),
                    "frontier": len(snap["frontier"]),
                    "failed": len(snap["failed"]),
                    "assets_done": len(snap["assets_done"]),
                    "assets_frontier": len(snap["assets_frontier"]),
                    "foreign_redirects": len(snap.get("foreign_redirects") or {}),
                    "page_index": len(index),
                    "page_index_path": str(PAGES_INDEX_PATH),
                    "foreign_list": str(FOREIGN_TXT),
                    "out": str(OUT_DIR),
                },
                indent=2,
            )
        )
        return 0

    if args.fresh:
        state = CrawlState()
        for path in (STATE_PATH, MANIFEST_PATH, LOG_PATH, FOREIGN_TXT, FOREIGN_JSONL):
            if path.exists():
                path.unlink()
        if args.fresh_index and PAGES_INDEX_PATH.exists():
            PAGES_INDEX_PATH.unlink()
            index = PageIndex()
    elif STATE_PATH.exists() and not args.recheck:
        state = load_state()
        log(
            f"Resuming from {STATE_PATH} "
            f"(visited={len(state.visited)}, frontier={len(state.frontier)}, "
            f"assets_q={len(state.assets_frontier)})"
        )
    else:
        state = CrawlState()

    # Drop gamma pages that already exist under b-w-c (disk + queue + index).
    purge_stats = purge_gamma_duplicates(index, state if not args.recheck else None)
    log(
        f"Gamma dedupe purge: deleted_files={purge_stats['deleted_files']} "
        f"removed_index={purge_stats['removed_index']} "
        f"dropped_frontier={purge_stats['dropped_frontier']} "
        f"rewritten_frontier={purge_stats.get('rewritten_frontier', 0)}"
    )
    if not args.recheck and STATE_PATH.exists():
        save_state(state)

    # --- Recheck / discover setup ---
    if args.recheck:
        if len(index) == 0:
            log("Page index empty. Run --build-index first (or finish a crawl that fills it).")
            return 1
        prior = load_state() if STATE_PATH.exists() else None
        state = CrawlState()
        queued = 0
        for url in index.urls():
            if should_fetch_html(url, index):
                state.enqueue_html(url)
                queued += 1
        # Full freshness pass always walks listing/search to find new entities.
        if args.discover:
            for seed in seed_urls():
                state.enqueue_html(seed)
        # Purge again against empty frontier after queueing (recheck uses fresh state).
        purge_gamma_duplicates(index, state)
        promoted = queue_bwc_promotions_from_gamma(state, index)
        if promoted:
            log(f"Queued {promoted} b-w-c promotions for existing lu4-gamma pages")
        # Always repair pagination gaps during recheck (missing files + pager edges).
        repair = apply_pagination_repair(state, index, prior=prior)
        log(
            f"Recheck repair: missing_visited={repair['missing_visited']} "
            f"missing_index={repair['missing_index']} "
            f"pager_seeds={repair['pager_seeds']}"
        )
        log(
            f"Recheck mode: {queued} indexed URLs queued"
            + (" + discover seeds" if args.discover else "")
            + f" frontier={len(state.frontier)}"
        )
    else:
        for seed in seed_urls():
            state.enqueue_html(seed)
        if not args.fresh:
            revived = restore_gamma_skips(state, index)
            if revived:
                log(f"Restored {revived} previously skipped lu4-gamma redirects into the queue")
                save_state(state)
        promoted = queue_bwc_promotions_from_gamma(state, index)
        if promoted:
            log(f"Queued {promoted} b-w-c promotions for existing lu4-gamma pages")
            save_state(state)
        # Heal incomplete drop/spoil pagination from earlier buggy runs.
        if args.repair_pagination or not args.fresh:
            repair = apply_pagination_repair(state, index, prior=None)
            if any(repair.values()):
                log(
                    f"Pagination repair: missing_visited={repair['missing_visited']} "
                    f"missing_index={repair['missing_index']} "
                    f"pager_seeds={repair['pager_seeds']}"
                )
                save_state(state)

    html_workers = max(1, args.html_workers)
    asset_workers = 0 if args.skip_assets else max(1, args.asset_workers)
    total_cap = max(2, args.max_concurrency)
    if html_workers + asset_workers > total_cap:
        if asset_workers:
            html_workers = max(1, min(html_workers, total_cap - 1))
            asset_workers = max(1, total_cap - html_workers)
        else:
            html_workers = min(html_workers, total_cap)

    limiter = RateLimiter(args.rps)
    pages_start = state.pages_saved
    processed_start = state.html_processed
    mode = "recheck" if args.recheck else "crawl"

    log(
        f"Start {mode} -> {OUT_DIR} html_workers={html_workers} asset_workers={asset_workers} "
        f"rps={args.rps} max_concurrency={total_cap} skip_assets={args.skip_assets} "
        f"frontier={len(state.frontier)} index={len(index)}"
    )

    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en,en-US;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }
    limits = httpx.Limits(
        max_connections=total_cap + 4,
        max_keepalive_connections=total_cap,
    )

    last_save = time.monotonic()
    last_progress_log = time.monotonic()

    def checkpoint(force: bool = False) -> None:
        nonlocal last_save
        now = time.monotonic()
        if force or now - last_save >= args.save_every:
            if not args.recheck:
                save_state(state)
            write_foreign_list(state)
            if index.dirty or force:
                index.save()
            last_save = now

    def html_budget_left() -> bool:
        if args.max_pages is None:
            return True
        with state.lock:
            if args.recheck:
                return (state.html_processed - processed_start + state.html_inflight) < args.max_pages
            return (state.pages_saved - pages_start) < args.max_pages

    try:
        with httpx.Client(headers=headers, timeout=TIMEOUT, limits=limits, http2=False) as client:
            with ThreadPoolExecutor(max_workers=html_workers + max(asset_workers, 1)) as pool:
                html_futs: set[Future[None]] = set()
                asset_futs: set[Future[None]] = set()

                def reap(futs: set[Future[None]]) -> None:
                    done = {f for f in futs if f.done()}
                    for f in done:
                        exc = f.exception()
                        if exc:
                            log(f"WORKER error: {type(exc).__name__}: {exc}")
                        futs.discard(f)

                page_cap_logged = False
                while True:
                    reap(html_futs)
                    reap(asset_futs)

                    while len(html_futs) < html_workers and html_budget_left():
                        url = state.claim_html()
                        if url is None:
                            break
                        fut = pool.submit(
                            process_html,
                            client,
                            limiter,
                            state,
                            index,
                            url,
                            skip_assets=args.skip_assets,
                            max_retries=args.retries,
                            recheck_mode=args.recheck,
                        )
                        html_futs.add(fut)

                    hit_page_cap = args.max_pages is not None and not html_budget_left()
                    if asset_workers and not hit_page_cap:
                        while len(asset_futs) < asset_workers:
                            url = state.claim_asset()
                            if url is None:
                                break
                            fut = pool.submit(
                                process_asset,
                                client,
                                limiter,
                                state,
                                url,
                                max_retries=args.retries,
                            )
                            asset_futs.add(fut)

                    checkpoint()

                    now = time.monotonic()
                    if now - last_progress_log >= 30.0:
                        with state.lock:
                            log(
                                f"PROGRESS pages_written={state.pages_saved} "
                                f"index_checked={index.stats['checked']} "
                                f"updated={index.stats['updated']} added={index.stats['added']} "
                                f"unchanged={index.stats['unchanged']} "
                                f"html_q={len(state.frontier)} asset_q={len(state.assets_frontier)} "
                                f"rps~{limiter.rps:.1f}"
                            )
                        last_progress_log = now

                    if hit_page_cap:
                        if not page_cap_logged:
                            log(
                                f"Reached --max-pages={args.max_pages}; "
                                "finishing in-flight work then stopping"
                            )
                            page_cap_logged = True
                        if not html_futs and not asset_futs:
                            break
                        time.sleep(0.05)
                        continue

                    if state.html_idle() and (args.skip_assets or state.idle()):
                        if not html_futs and (args.skip_assets or (not asset_futs and state.idle())):
                            break

                    if not html_futs and not asset_futs:
                        if state.html_idle() and (args.skip_assets or state.idle()):
                            break
                        time.sleep(0.05)
                    else:
                        time.sleep(0.02)

                state.request_stop()
                for fut in list(html_futs) + list(asset_futs):
                    try:
                        fut.result(timeout=120)
                    except Exception as exc:  # noqa: BLE001
                        log(f"WORKER finalize error: {exc}")
    finally:
        checkpoint(force=True)

    snap = state.snapshot()
    log(
        f"Done ({mode}). pages_written={snap['pages_saved']} assets_saved={snap['assets_saved']} "
        f"index={len(index)} checked={index.stats['checked']} "
        f"updated={index.stats['updated']} added={index.stats['added']} "
        f"unchanged={index.stats['unchanged']} http_304={index.stats['not_modified_304']} "
        f"frontier_left={len(snap['frontier'])} failed={len(snap['failed'])}"
    )
    if snap["frontier"] or snap["assets_frontier"]:
        log("Queue not empty - re-run the same command to continue.")
    foreign_n = len(snap.get("foreign_redirects") or {})
    if foreign_n:
        write_foreign_list(state)
        log(f"Foreign redirects (masterwork/eternal): {foreign_n} -> {FOREIGN_TXT}")
    if snap["failed"]:
        log(f"Failed URLs recorded in {STATE_PATH} under key 'failed'.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Mirror / incremental update of masterwork.wiki /lu4-b-w-c into ./wikilu4"
    )
    p.add_argument(
        "--html-workers",
        type=int,
        default=4,
        help="Parallel HTML downloads (default 4, safe)",
    )
    p.add_argument(
        "--asset-workers",
        type=int,
        default=6,
        help="Parallel asset downloads (default 6)",
    )
    p.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Compatibility alias: sets both html/asset workers",
    )
    p.add_argument(
        "--rps",
        type=float,
        default=8.0,
        help="Global requests/sec budget across all workers (default 8)",
    )
    p.add_argument(
        "--max-concurrency",
        type=int,
        default=12,
        help="Hard cap on html+asset workers combined (default 12)",
    )
    p.add_argument(
        "--retries",
        type=int,
        default=4,
        help="Retries per URL on soft errors before giving up (default 4)",
    )
    p.add_argument("--max-pages", type=int, default=None, help="Stop after N written HTML pages")
    p.add_argument("--skip-assets", action="store_true", help="Do not download images/css/js")
    p.add_argument(
        "--save-every",
        type=float,
        default=15.0,
        help="Seconds between state/index checkpoints (default 15)",
    )
    p.add_argument(
        "--recheck",
        action="store_true",
        help=(
            "Incremental update: recheck indexed pages, download only if changed; "
            "also repairs missing HTML and drop/spoil pagination gaps"
        ),
    )
    p.add_argument(
        "--discover",
        action="store_true",
        help="With --recheck, also seed search/listing pages to find new entities",
    )
    p.add_argument(
        "--build-index",
        action="store_true",
        help="Build/refresh _pages.json hashes from existing local HTML (no network)",
    )
    p.add_argument("--fresh", action="store_true", help="Ignore crawl state and start clean")
    p.add_argument(
        "--fresh-index",
        action="store_true",
        help="With --fresh, also wipe _pages.json",
    )
    p.add_argument("--status", action="store_true", help="Print crawl/index status and exit")
    p.add_argument(
        "--purge-gamma",
        action="store_true",
        help="Delete local lu4-gamma HTML that already has a lu4-b-w-c twin, then exit",
    )
    p.add_argument(
        "--repair-pagination",
        action="store_true",
        help=(
            "Force requeue of missing visited HTML and drop/spoil pager edges "
            "(also included automatically with --recheck and on crawl resume)"
        ),
    )
    p.add_argument("--delay", type=float, default=None, help=argparse.SUPPRESS)
    p.add_argument("--asset-batch", type=int, default=None, help=argparse.SUPPRESS)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.workers is not None:
        args.html_workers = args.workers
        args.asset_workers = args.workers
    if args.delay is not None and args.delay > 0:
        args.rps = min(args.rps, max(0.5, 1.0 / args.delay))
    try:
        return run_crawl(args)
    except KeyboardInterrupt:
        log("Interrupted - progress saved")
        return 130


if __name__ == "__main__":
    sys.exit(main())
