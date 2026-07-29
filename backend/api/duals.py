from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from api.deps import DbSession, require_permission
from models.analytics import AnalyticsDataset

router = APIRouter()

DATASET_KEY = "duals_catalog"


@router.get("/catalog", dependencies=[Depends(require_permission("nav.items"))])
def get_catalog(db: DbSession):
    """Small enough (about 230 KB) that slicing it would buy nothing."""
    dataset = db.scalar(select(AnalyticsDataset).where(AnalyticsDataset.dataset_key == DATASET_KEY))
    if dataset is None:
        raise HTTPException(status_code=404, detail="Duals catalog not loaded")
    return {
        "generated_at": dataset.generated_at.isoformat() if dataset.generated_at else None,
        **(dataset.payload if isinstance(dataset.payload, dict) else {}),
    }
