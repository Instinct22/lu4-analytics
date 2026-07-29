from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from api.deps import DbSession, require_permission
from calculations.price_stats import get_dashboard_stats
from models.market import MarketRecord
from models.user import User
from schemas.market import DashboardResponse

router = APIRouter()

StatsUser = Annotated[User, Depends(require_permission("nav.statistics"))]


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(db: DbSession, user: StatsUser):
    stats = get_dashboard_stats(db)
    return DashboardResponse(
        entity_counts=stats["entity_counts"],
        total_imports=stats["total_imports"],
        total_market_records=stats["total_market_records"],
        unmatched_records=stats["unmatched_records"],
        recent_imports=[
            {
                "id": str(i.id),
                "source": i.source,
                "records_count": i.records_count,
                "matched_count": i.matched_count,
                "status": i.status,
                "created_at": i.created_at.isoformat(),
            }
            for i in stats["recent_imports"]
        ],
    )


@router.get("/unmatched")
def unmatched_records(db: DbSession, user: StatsUser, limit: int = 100):
    records = db.scalars(
        select(MarketRecord)
        .where(MarketRecord.entity_id.is_(None))
        .order_by(MarketRecord.recorded_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": str(r.id),
            "product_name": r.product_name_raw,
            "price": float(r.price),
            "recorded_at": r.recorded_at.isoformat(),
        }
        for r in records
    ]
