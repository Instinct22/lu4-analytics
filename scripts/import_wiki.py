#!/usr/bin/env python3
"""Import wiki library into PostgreSQL (upsert by entity_key)."""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from models.wiki import EntityLink, WikiCategory, WikiEntity
from services.dataset_import import import_datasets
from services.name_matching import clean_display_name, normalize_product_name, slugify
from services.npc_loot_import import import_npc_loot

BATCH = 500
TYPE_SLUGS = {
    "item": ("Items", 1),
    "npc": ("NPC", 2),
    "skill": ("Skills", 3),
    "quest": ("Quests", 4),
    "location": ("Locations", 5),
    "class": ("Classes", 6),
    "set": ("Sets", 7),
    "posts": ("Articles", 8),
}


def wiki_root() -> Path:
    return Path(settings.wiki_path)


def datasets_root() -> Path:
    return Path(settings.datasets_path)


def ensure_categories(db: Session) -> dict[str, uuid.UUID]:
    mapping: dict[str, uuid.UUID] = {}
    for entity_type, (name, order) in TYPE_SLUGS.items():
        slug = slugify(name)
        cat = db.scalar(select(WikiCategory).where(WikiCategory.slug == slug))
        if cat is None:
            cat = WikiCategory(id=uuid.uuid4(), name=name, slug=slug, sort_order=order)
            db.add(cat)
            db.flush()
        mapping[entity_type] = cat.id
    db.commit()
    return mapping


def load_text(base: Path, rel: str | None) -> str | None:
    if not rel:
        return None
    path = base / rel
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def load_json(base: Path, rel: str | None) -> dict | list | None:
    if not rel:
        return None
    path = base / rel
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def extract_slug_from_url(url: str) -> str:
    parts = (url or "").strip("/").split("/")
    return parts[-1] if parts else slugify(url)


def import_entities(db: Session, base: Path, categories: dict[str, uuid.UUID]) -> dict[str, uuid.UUID]:
    catalog_path = base / "library/index/catalog.jsonl"
    if not catalog_path.exists():
        raise FileNotFoundError(catalog_path)

    existing = {
        e.entity_key: e
        for e in db.scalars(select(WikiEntity)).all()
    }
    key_to_id: dict[str, uuid.UUID] = {k: e.id for k, e in existing.items()}
    images_dir = base / "images"
    created = updated = 0

    with catalog_path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            entity_key = row["key"]
            entity_type = row.get("type") or "page"
            external_id = row.get("id")
            name = row.get("name") or entity_key
            display = clean_display_name(name)
            url = row.get("url") or ""
            data_rel = row.get("data")
            page_rel = row.get("page")

            data_obj = load_json(base, data_rel) or {}
            stats = data_obj.get("stats") if isinstance(data_obj, dict) else None
            materials = data_obj.get("materials") if isinstance(data_obj, dict) else None
            content_md = load_text(base, page_rel)
            source_url = None
            if isinstance(data_obj, dict):
                source_url = row.get("source_url") or data_obj.get("source_url")
            else:
                source_url = row.get("source_url")

            image_path = None
            if entity_type == "item" and external_id and (images_dir / f"{external_id}.png").exists():
                image_path = f"images/{external_id}.png"

            fields = dict(
                entity_type=entity_type,
                external_id=external_id,
                name=name,
                display_name=display,
                name_normalized=normalize_product_name(display),
                slug=extract_slug_from_url(url),
                url=url,
                source_url=source_url,
                summary=row.get("summary"),
                stats=stats,
                materials=materials,
                content_md=content_md,
                category_id=categories.get(entity_type),
                image_path=image_path,
            )

            entity = existing.get(entity_key)
            if entity is None:
                entity_id = uuid.uuid4()
                entity = WikiEntity(id=entity_id, entity_key=entity_key, **fields)
                db.add(entity)
                existing[entity_key] = entity
                key_to_id[entity_key] = entity_id
                created += 1
            else:
                for key, value in fields.items():
                    setattr(entity, key, value)
                key_to_id[entity_key] = entity.id
                updated += 1

            if (created + updated) % BATCH == 0:
                db.commit()
                print(f"  entities: {created + updated} (+{created} / ~{updated})")

    db.commit()
    print(f"Upserted entities: {created} created, {updated} updated")
    return key_to_id


def import_links(db: Session, base: Path, key_to_id: dict[str, uuid.UUID]) -> None:
    catalog_path = base / "library/index/catalog.jsonl"
    db.execute(delete(EntityLink))
    db.commit()

    links_batch: list[EntityLink] = []
    seen_links: set[tuple] = set()
    link_count = 0

    with catalog_path.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            source_key = row["key"]
            source_id = key_to_id.get(source_key)
            if not source_id:
                continue

            data_obj = load_json(base, row.get("data")) or {}
            if not isinstance(data_obj, dict):
                continue

            for link in data_obj.get("links") or []:
                target_key = link.get("key")
                if not target_key:
                    continue
                target_id = key_to_id.get(target_key)
                if not target_id or target_id == source_id:
                    continue
                pair = (source_id, target_id, "related")
                if pair in seen_links:
                    continue
                seen_links.add(pair)
                links_batch.append(
                    EntityLink(
                        id=uuid.uuid4(),
                        source_entity_id=source_id,
                        target_entity_id=target_id,
                        link_type="related",
                    )
                )
                link_count += 1

            if len(links_batch) >= BATCH:
                db.bulk_save_objects(links_batch)
                db.commit()
                links_batch.clear()

    if links_batch:
        db.bulk_save_objects(links_batch)
    db.commit()
    print(f"Imported {link_count} links (materials kept as JSONB on entities)")


def update_search_vectors(db: Session) -> None:
    db.execute(
        text(
            """
            UPDATE wiki_entities SET search_vector =
                setweight(to_tsvector('simple', coalesce(display_name, '')), 'A') ||
                setweight(to_tsvector('simple', coalesce(summary, '')), 'B') ||
                setweight(to_tsvector('simple', coalesce(content_md, '')), 'C')
            """
        )
    )
    db.commit()
    print("Updated search vectors")


def is_already_imported(db: Session) -> bool:
    count = db.scalar(text("SELECT COUNT(*) FROM wiki_entities"))
    return (count or 0) > 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Import wiki library into PostgreSQL")
    parser.add_argument(
        "--if-empty",
        action="store_true",
        help="Skip import if wiki_entities already contains data",
    )
    args = parser.parse_args()

    base = wiki_root()
    if not base.exists():
        print(f"wiki path not found: {base}", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        if args.if_empty and is_already_imported(db):
            print("Wiki already imported")
            return

        print("Creating categories...")
        categories = ensure_categories(db)
        print("Upserting entities...")
        key_to_id = import_entities(db, base, categories)
        print("Replacing links...")
        import_links(db, base, key_to_id)
        print("Updating search vectors...")
        update_search_vectors(db)
        print("Importing NPC loot...")
        import_npc_loot(db)
        print("Importing analytics datasets...")
        import_datasets(db, datasets_root())
        print("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
