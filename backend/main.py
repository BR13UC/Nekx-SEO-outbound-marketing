from fastapi import FastAPI

from .config import settings
from .database import connect, init_db
from .routes.analytics_routes import router as analytics_router
from .routes.email_routes import router as email_router
from .routes.experiments_routes import router as experiments_router
from .routes.leads_routes import router as leads_router
from .routes.seo_routes import router as seo_router
from .routes.webhooks_routes import router as webhooks_router


app = FastAPI(title="Nekx SEO Outreach Agent", version="0.1.0")


@app.on_event("startup")
def _startup() -> None:
    conn = connect()
    try:
        init_db(conn)
    finally:
        conn.close()


@app.get(f"{settings.api_prefix}/health")
def health() -> dict:
    return {"ok": True}


app.include_router(leads_router, prefix=settings.api_prefix)
app.include_router(seo_router, prefix=settings.api_prefix)
app.include_router(experiments_router, prefix=settings.api_prefix)
app.include_router(email_router, prefix=settings.api_prefix)
app.include_router(webhooks_router, prefix=settings.api_prefix)
app.include_router(analytics_router, prefix=settings.api_prefix)
