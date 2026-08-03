"""Global entity search using PostgreSQL full-text search with ILIKE fallback."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select

from api.deps import DbSession, require_permission
from models.wiki import WikiEntity
from schemas.market import SearchResponse, SearchResultGroup
from services.name_matching import unescape_text

router = APIRouter(dependencies=[Depends(require_permission("nav.search"))])

SEARCH_TYPES = ["item", "npc", "skill", "quest", "location", "class", "set", "posts"]


def _to_tsquery(q: str) -> str:
    """Build a simple AND tsquery from user input."""
    tokens = [t for t in "".join(c if c.isalnum() or c.isspace() else " " for c in q).split() if t]
    if not tokens:
        return ""
    return " & ".join(f"{t}:*" for t in tokens)


def _brief(entity: WikiEntity) -> dict:
    return {
        "id": str(entity.id),
        "display_name": unescape_text(entity.display_name),
        "entity_type": entity.entity_type,
        "external_id": entity.external_id,
        "slug": entity.slug,
        "image_path": entity.image_path,
    }


@router.get("", response_model=SearchResponse)
def search(
    db: DbSession,
    q: str = Query(min_length=1),
    types: list[str] | None = Query(None, alias="types"),
    limit: int = Query(20, ge=1, le=100),
):
    search_types = types or SEARCH_TYPES
    groups = []
    tsquery = _to_tsquery(q)
    use_fts = len(q.strip()) >= 3 and bool(tsquery)

    for entity_type in search_types:
        base = select(WikiEntity).where(WikiEntity.entity_type == entity_type)
        count_base = select(func.count()).select_from(WikiEntity).where(WikiEntity.entity_type == entity_type)

        if use_fts:
            tsq = func.to_tsquery("simple", tsquery)
            filt = WikiEntity.search_vector.op("@@")(tsq)
            query = base.where(filt).order_by(func.ts_rank(WikiEntity.search_vector, tsq).desc()).limit(limit)
            count_query = count_base.where(filt)
        else:
            pattern = f"%{q}%"
            filt = or_(
                WikiEntity.display_name.ilike(pattern),
                WikiEntity.name_normalized.ilike(pattern),
                WikiEntity.summary.ilike(pattern),
            )
            query = base.where(filt).limit(limit)
            count_query = count_base.where(filt)

        items = db.scalars(query).all()
        count = db.scalar(count_query) or 0
        if items:
            groups.append(
                SearchResultGroup(
                    entity_type=entity_type,
                    items=[_brief(i) for i in items],
                    total=count,
                )
            )

    return SearchResponse(query=q, groups=groups)
