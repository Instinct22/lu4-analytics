#!/usr/bin/env python3
"""Import analytics datasets only (no full wiki re-import)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from config import settings
from database import SessionLocal
from services.dataset_import import import_datasets


def main() -> None:
    keys = sys.argv[1:] or None
    db = SessionLocal()
    try:
        import_datasets(db, Path(settings.datasets_path), keys)
        print("Done.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
