#!/usr/bin/env python3
"""Set wiki_entities.image_path for items that have a local PNG icon."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import select, update

from config import settings
from database import SessionLocal
from models.wiki import WikiEntity


def main() -> None:
    images_dir = Path(settings.wiki_path) / "images"
    if not images_dir.is_dir():
        print(f"Images dir not found: {images_dir}", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        items = db.scalars(
            select(WikiEntity).where(
                WikiEntity.entity_type == "item",
                WikiEntity.external_id.is_not(None),
            )
        ).all()
        updated = cleared = 0
        for entity in items:
            rel = f"images/{entity.external_id}.png"
            path = images_dir / f"{entity.external_id}.png"
            if path.is_file() and path.stat().st_size > 50:
                if entity.image_path != rel:
                    entity.image_path = rel
                    updated += 1
            elif entity.image_path:
                entity.image_path = None
                cleared += 1
        db.commit()
        print(f"Updated image_path for {updated} items, cleared {cleared}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
