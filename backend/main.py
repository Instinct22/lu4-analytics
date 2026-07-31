from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from api import (
    admin,
    auth,
    character,
    craft,
    duals,
    import_,
    items,
    market,
    market_scan,
    preferences,
    raid,
    search,
    statistics,
    upgrades,
    wiki,
)
from config import settings
from core.errors import register_exception_handlers


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from api.deps import ensure_role_permissions_seeded
    from database import SessionLocal

    db = SessionLocal()
    try:
        ensure_role_permissions_seeded(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Lu4 Analytics API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Catalog responses reach several MB. nginx compresses proxied traffic too, but
# the dev server talks to uvicorn directly.
app.add_middleware(GZipMiddleware, minimum_size=1024)

register_exception_handlers(app)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(import_.router, prefix="/api/import", tags=["import"])
app.include_router(market_scan.router, prefix="/api/market/scan", tags=["market-scan"])
app.include_router(wiki.router, prefix="/api/wiki", tags=["wiki"])
app.include_router(market.router, prefix="/api/market", tags=["market"])
app.include_router(statistics.router, prefix="/api/statistics", tags=["statistics"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(duals.router, prefix="/api/duals", tags=["duals"])
app.include_router(raid.router, prefix="/api/raid", tags=["raid"])
app.include_router(character.router, prefix="/api/character", tags=["character"])
app.include_router(craft.router, prefix="/api/craft", tags=["craft"])
app.include_router(upgrades.router, prefix="/api/upgrades", tags=["upgrades"])
app.include_router(items.router, prefix="/api/items", tags=["items"])
app.include_router(preferences.router, prefix="/api/me", tags=["preferences"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
