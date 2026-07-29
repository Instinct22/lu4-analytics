"""Build nested recipe material trees from wiki HTML accordions."""
from __future__ import annotations

import re
from typing import Any

ITEM_ID_RE = re.compile(r"/lu4/item/(\d+)-")


def _material_from_accordion(acc) -> tuple[int, int] | None:
    link = acc.select_one('a.item-name[href*="/lu4/item/"]')
    amount_el = acc.select_one(".material-amount")
    if link is None or amount_el is None:
        return None
    m = ITEM_ID_RE.search(link.get("href") or "")
    if not m:
        return None
    amount_raw = amount_el.get("data-initial-amount") or amount_el.get_text(strip=True)
    try:
        amount = int(str(amount_raw).strip())
    except ValueError:
        return None
    return int(m.group(1)), amount


def _parse_accordion_node(acc) -> dict[str, Any] | None:
    parsed = _material_from_accordion(acc)
    if parsed is None:
        return None
    material_id, amount = parsed
    children: list[dict[str, Any]] = []
    body = acc.select_one(".accordion-collapse .accordion-body")
    if body:
        for child_acc in body.select(":scope > .accordion"):
            child = _parse_accordion_node(child_acc)
            if child:
                children.append(child)
    return {"id": material_id, "amount": amount, "children": children}


def parse_recipe_tree(soup) -> list[dict[str, Any]]:
    content = soup.select_one(".recipe_content")
    if content is None:
        return []
    materials_wrap = content.select_one("h5.recipe_content_header + div, h5 + div")
    if materials_wrap is None:
        return []
    tree: list[dict[str, Any]] = []
    for acc in materials_wrap.select(":scope > .accordion"):
        node = _parse_accordion_node(acc)
        if node:
            tree.append(node)
    return tree
