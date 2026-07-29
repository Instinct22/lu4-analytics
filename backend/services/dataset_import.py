"""Single entry point for loading analytics datasets into Postgres.

Each dataset is described by a :class:`DatasetSpec`. A payload can be kept as a
JSONB blob in ``analytics_datasets`` and/or exploded into relational tables by a
normalizer registered for its key.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.analytics import AnalyticsDataset

Normalizer = Callable[[Session, Any], None]


@dataclass(frozen=True)
class DatasetSpec:
    key: str
    filename: str
    #: Keep the raw payload in analytics_datasets. Disabled once every consumer
    #: reads from normalized tables instead.
    store_blob: bool = True


#: The craft_catalog and craft_resources datasets used to be importable here.
#: items_encyclopedia now fills the same tables, and re-running the old
#: normalizers would delete those rows, so they are no longer registered.
_SPEC_LIST: tuple[DatasetSpec, ...] = (
    DatasetSpec("items_encyclopedia", "items_encyclopedia.json", store_blob=False),
    DatasetSpec("character", "character_data.json", store_blob=False),
    # Small enough to hand over whole; sliced into /api/items/browse.
    DatasetSpec("duals_catalog", "duals_catalog.json"),
    # Bosses live in raid_bosses; the blob is kept only for the map config.
    DatasetSpec("raid_bosses", "raid_bosses.json"),
)

DATASETS: dict[str, DatasetSpec] = {spec.key: spec for spec in _SPEC_LIST}

_NORMALIZERS: dict[str, Normalizer] = {}


def register_normalizer(key: str) -> Callable[[Normalizer], Normalizer]:
    """Register a callable that explodes a payload into relational tables."""

    def wrap(fn: Normalizer) -> Normalizer:
        _NORMALIZERS[key] = fn
        return fn

    return wrap


def _load_normalizers() -> None:
    """Import normalizer modules so their decorators run (lazy, avoids cycles)."""
    import services.normalizers  # noqa: F401


def parse_generated_at(payload: Any) -> datetime | None:
    if not isinstance(payload, dict):
        return None
    for field in ("generated_at", "generated"):
        if field not in payload:
            continue
        try:
            return datetime.fromisoformat(str(payload[field]).replace(" ", "T"))
        except ValueError:
            return None
    return None


def load_payload(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def upsert_blob(db: Session, key: str, payload: Any, generated: datetime | None) -> None:
    existing = db.scalar(select(AnalyticsDataset).where(AnalyticsDataset.dataset_key == key))
    if existing:
        existing.payload = payload
        existing.generated_at = generated
    else:
        db.add(
            AnalyticsDataset(
                id=uuid.uuid4(),
                dataset_key=key,
                payload=payload,
                generated_at=generated,
            )
        )


def drop_blob(db: Session, key: str) -> None:
    existing = db.scalar(select(AnalyticsDataset).where(AnalyticsDataset.dataset_key == key))
    if existing:
        db.delete(existing)


def specs(keys: Iterable[str] | None = None) -> Iterator[DatasetSpec]:
    if keys is None:
        yield from _SPEC_LIST
        return
    for key in keys:
        spec = DATASETS.get(key)
        if spec is None:
            raise KeyError(f"Unknown dataset key: {key}")
        yield spec


def import_dataset(db: Session, spec: DatasetSpec, datasets_dir: Path) -> bool:
    """Load one dataset. Returns False when its source file is missing."""
    path = datasets_dir / spec.filename
    if not path.exists():
        return False

    payload = load_payload(path)
    generated = parse_generated_at(payload)

    if spec.store_blob:
        upsert_blob(db, spec.key, payload, generated)
    else:
        drop_blob(db, spec.key)

    normalizer = _NORMALIZERS.get(spec.key)
    if normalizer is not None:
        normalizer(db, payload)

    db.commit()
    return True


def import_datasets(db: Session, datasets_dir: Path, keys: Iterable[str] | None = None) -> None:
    _load_normalizers()
    for spec in specs(keys):
        if import_dataset(db, spec, datasets_dir):
            target = "tables" if spec.key in _NORMALIZERS else "jsonb"
            print(f"Loaded dataset: {spec.key} -> {target}")
        else:
            print(f"Skipping {spec.key}: {datasets_dir / spec.filename} not found")
