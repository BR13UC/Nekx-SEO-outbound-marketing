import logging
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import connect, init_db
from .routes.ab_tests_routes import router as ab_tests_router
from .routes.analytics_routes import router as analytics_router
from .routes.email_routes import router as email_router
from .routes.experiments_routes import router as experiments_router
from .routes.leads_routes import router as leads_router
from .routes.seo_routes import router as seo_router
from .routes.scheduler_routes import router as scheduler_router
from .routes.webhooks_routes import router as webhooks_router
from .tools.run_outbound_cycle import DEFAULT_CONFIG, load_scheduler_config, run_cycle

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
_scheduler_stop_event = threading.Event()
_scheduler_thread: threading.Thread | None = None


app = FastAPI(title="Nekx SEO Outreach Agent", version="0.1.0")


@app.on_event("startup")
def _startup() -> None:
    conn = connect()
    try:
        init_db(conn)
    finally:
        conn.close()
    _start_scheduler_loop()


@app.on_event("shutdown")
def _shutdown() -> None:
    _stop_scheduler_loop()


def _scheduler_loop(stop_event: threading.Event) -> None:
    logger = logging.getLogger("nekx.app.scheduler_loop")
    while not stop_event.is_set():
        sleep_seconds = 30
        try:
            cfg_path = Path(settings.scheduler_config_path)
            cfg = load_scheduler_config(cfg_path) if cfg_path.exists() else dict(DEFAULT_CONFIG)
            enabled = bool(cfg.get("enabled", True))
            try:
                interval_minutes = max(1, int(cfg.get("min_interval_minutes", DEFAULT_CONFIG["min_interval_minutes"])))
            except (TypeError, ValueError):
                interval_minutes = int(DEFAULT_CONFIG["min_interval_minutes"])

            if enabled:
                run_cycle(dry_run=False, mode="live")
                sleep_seconds = interval_minutes * 60
            else:
                sleep_seconds = 30
        except Exception:
            logger.exception("Scheduler loop iteration failed")
            sleep_seconds = 60

        stop_event.wait(sleep_seconds)


def _start_scheduler_loop() -> None:
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        return
    _scheduler_stop_event.clear()
    _scheduler_thread = threading.Thread(
        target=_scheduler_loop,
        args=(_scheduler_stop_event,),
        name="nekx-scheduler-loop",
        daemon=True,
    )
    _scheduler_thread.start()


def _stop_scheduler_loop() -> None:
    _scheduler_stop_event.set()
    if _scheduler_thread and _scheduler_thread.is_alive():
        _scheduler_thread.join(timeout=2)


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", include_in_schema=False)
def admin_index() -> FileResponse:
    return FileResponse(STATIC_DIR / "admin.html")


@app.get("/admin", include_in_schema=False)
def admin_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "admin.html")


@app.get(f"{settings.api_prefix}/health")
def health() -> dict:
    return {"ok": True}


app.include_router(leads_router, prefix=settings.api_prefix)
app.include_router(seo_router, prefix=settings.api_prefix)
app.include_router(experiments_router, prefix=settings.api_prefix)
app.include_router(ab_tests_router, prefix=settings.api_prefix)
app.include_router(email_router, prefix=settings.api_prefix)
app.include_router(webhooks_router, prefix=settings.api_prefix)
app.include_router(analytics_router, prefix=settings.api_prefix)
app.include_router(scheduler_router, prefix=settings.api_prefix)
