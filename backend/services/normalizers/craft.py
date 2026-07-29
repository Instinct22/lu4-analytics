"""Explode the craft catalog and material sources into relational tables.

Legacy path: the items_encyclopedia normalizer now fills the same tables from a
single source. These functions are deliberately not registered as normalizers —
they start with a DELETE and would drop the encyclopedia-derived rows. Only the
meta keys below are still part of the live read path.
"""

from __future__ import annotations

from typing import Any, Iterator

from sqlalchemy import delete
from sqlalchemy.orm import Session

from models.craft import CraftItem, CraftMaterialSource, CraftRecipe, CraftRecipeMaterial
from services.dataset_import import upsert_blob

#: Category tree, set membership and counters: small, nested, never queried by SQL.
CATALOG_META_KEY = "craft_catalog_meta"
#: Material list without the spoil/drop arrays that moved into the table.
RESOURCES_META_KEY = "craft_resources_meta"

RESOURCE_SECTIONS = (("base", "base_materials"), ("craft", "craft_materials_lte_30"))


def _flatten_tree(nodes: list, depth: int = 0) -> Iterator[tuple[int, int, bool]]:
    """Yield (material_id, amount, is_direct) for every node of a recipe tree."""
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        material_id = node.get("id")
        if isinstance(material_id, int):
            yield material_id, int(node.get("amount") or 1), depth == 0
        yield from _flatten_tree(node.get("children") or [], depth + 1)


def normalize_craft_catalog(db: Session, payload: Any) -> None:
    if not isinstance(payload, dict):
        return

    # Materials cascade with their recipes.
    db.execute(delete(CraftRecipe))
    db.execute(delete(CraftItem))
    db.flush()

    for raw_id, item in (payload.get("items") or {}).items():
        if not isinstance(item, dict):
            continue
        external_id = item.get("id") if isinstance(item.get("id"), int) else int(raw_id)
        db.add(
            CraftItem(
                external_id=external_id,
                name=item.get("name") or f"#{external_id}",
                grade=item.get("grade") or "",
                type=item.get("type") or "",
                category=item.get("category") or "",
                set_name=item.get("set_name"),
                npc_sell=item.get("npc_sell"),
                url=item.get("url") or "",
                is_recipe_scroll=bool(item.get("is_recipe_scroll")),
                description=item.get("description"),
                stats=item.get("stats"),
            )
        )
    db.flush()

    for raw_id, variants in (payload.get("byProduct") or {}).items():
        try:
            product_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        for index, variant in enumerate(variants or []):
            if not isinstance(variant, dict):
                continue
            recipe = CraftRecipe(
                product_external_id=product_id,
                recipe_external_id=variant.get("recipe_id"),
                variant_index=index,
                yield_amount=int(variant.get("yield") or 1),
                rate=variant.get("rate"),
                crafter_level=variant.get("crafter_level"),
                skill_level=variant.get("skill_level"),
                mp=variant.get("mp"),
                success=variant.get("success"),
                recipe_url=variant.get("recipe_url"),
                tree=variant.get("tree") or [],
            )
            db.add(recipe)
            db.flush()
            for material_id, amount, is_direct in _flatten_tree(variant.get("tree") or []):
                db.add(
                    CraftRecipeMaterial(
                        recipe_id=recipe.id,
                        material_external_id=material_id,
                        amount=amount,
                        is_direct=is_direct,
                    )
                )

    upsert_blob(
        db,
        CATALOG_META_KEY,
        {
            "generated_at": payload.get("generated_at"),
            "product_count": payload.get("product_count"),
            "variant_count": payload.get("variant_count"),
            "categories": payload.get("categories") or {},
            "sets": payload.get("sets") or {},
            "setMeta": payload.get("setMeta") or {},
            "itemIcons": {
                str(raw_id): item["icon"]
                for raw_id, item in (payload.get("items") or {}).items()
                if isinstance(item, dict) and item.get("icon")
            },
        },
        None,
    )


def _npc_level(raw: Any) -> int | None:
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return None


def normalize_craft_resources(db: Session, payload: Any) -> None:
    if not isinstance(payload, dict):
        return

    db.execute(delete(CraftMaterialSource))
    db.flush()

    materials_meta: list[dict] = []
    for section, key in RESOURCE_SECTIONS:
        for material in payload.get(key) or []:
            if not isinstance(material, dict):
                continue
            material_id = material.get("id")
            if not isinstance(material_id, int):
                continue

            for kind, field in (("spoil", "spoil"), ("drop", "drop")):
                for order, source in enumerate(material.get(field) or []):
                    db.add(
                        CraftMaterialSource(
                            material_external_id=material_id,
                            source_kind=kind,
                            npc_external_id=source.get("npc_id"),
                            npc_name=source.get("npc_name") or "",
                            npc_url=source.get("npc_url") or "",
                            npc_level=_npc_level(source.get("npc_level")),
                            npc_level_raw=str(source.get("npc_level") or ""),
                            amount=source.get("amount") or "",
                            chance_text=source.get("chance") or "",
                            chance_val=source.get("chance_val") or 0,
                            locations=source.get("locations") or [],
                            sort_order=order,
                        )
                    )

            materials_meta.append(
                {
                    "id": material_id,
                    "section": section,
                    "name": material.get("name"),
                    "grade": material.get("grade"),
                    "url": material.get("url"),
                    "desc": material.get("desc"),
                    "crafter_level": material.get("crafter_level"),
                    "skill_level": material.get("skill_level"),
                    "mp": material.get("mp"),
                    "success": material.get("success"),
                    "recipe_url": material.get("recipe_url"),
                    "tree": material.get("tree") or [],
                    "spoil_count": material.get("spoil_count") or len(material.get("spoil") or []),
                    "drop_count": material.get("drop_count") or len(material.get("drop") or []),
                }
            )

    upsert_blob(
        db,
        RESOURCES_META_KEY,
        {
            "generated_at": payload.get("generated_at"),
            "min_npc_level": payload.get("min_npc_level"),
            "max_npc_level": payload.get("max_npc_level"),
            "materials": materials_meta,
        },
        None,
    )
