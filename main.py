import logging

import sqlalchemy
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pythonjsonlogger import jsonlogger

from app.config import settings
from app.database import engine
from app.routers import admin, hotmart, whatsapp


def _setup_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _setup_logging()
    with engine.connect() as conn:
        conn.execute(sqlalchemy.text("SELECT 1"))
    from app.services.scheduler_service import start_scheduler, stop_scheduler
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Evolution Fit IA",
    description="SaaS fitness no WhatsApp com IA",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(whatsapp.router, prefix="/webhook")
app.include_router(hotmart.router, prefix="/webhook")
app.include_router(admin.router, prefix="/admin")


@app.get("/")
async def health():
    try:
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        return {"status": "ok", "details": {"database": "ok"}}
    except Exception as e:
        return {"status": "degraded", "details": {"database": str(e)}}
