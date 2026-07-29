"""Runtime helpers for the self-contained items encyclopedia."""

from __future__ import annotations

import copy
import re
from typing import Any

LU4_ITEM_RE = re.compile(r"^/lu4/item/(\d+)(?:-([^/?#]+))?")
LU4_NPC_RE = re.compile(r"^/lu4/npc/(\d+)(?:-([^/?#]+))?")


def _strip_lu4(path: str | None) -> str | None:
    if not path:
        return None
    text = path.strip()
    for pattern in (LU4_ITEM_RE, LU4_NPC_RE):
        match = pattern.match(text)
        if match:
            slug = match.group(2)
            return slug or None
    if text.startswith("/lu4/"):
        return None
    return text


def sanitize_item_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Remove legacy wiki paths before API responses."""
    out = copy.deepcopy(payload)
    out.pop("provenance", None)
    out.pop("stats_raw", None)
    out.pop("url", None)

    for field in ("drops", "spoils"):
        rows = out.get(field)
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict):
                    row.pop("npc_url", None)
                    row.pop("item_url", None)

    craft = out.get("craft")
    if isinstance(craft, dict) and isinstance(craft.get("variants"), list):
        for variant in craft["variants"]:
            if isinstance(variant, dict):
                variant.pop("recipe_url", None)

    links = out.get("links")
    if isinstance(links, dict):
        for key, val in links.items():
            if isinstance(val, list):
                for entry in val:
                    if isinstance(entry, dict):
                        entry.pop("url", None)
            elif isinstance(val, dict):
                val.pop("url", None)

    slug = out.get("slug") or _strip_lu4(payload.get("url"))
    if slug:
        out["slug"] = slug

    item_set = out.get("set")
    if isinstance(item_set, dict):
        item_set.pop("url", None)
    return out
