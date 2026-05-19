import logging

import httpx
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
    yield


app = FastAPI(
    title="Evolution Fit IA",
    description="SaaS fitness no WhatsApp com IA",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.ALLOWED_ORIGINS.split(",")],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

app.include_router(whatsapp.router, prefix="/webhook")
app.include_router(hotmart.router, prefix="/webhook")
app.include_router(admin.router, prefix="/admin")


@app.get("/")
async def health():
    details: dict = {}

    # Verifica banco
    try:
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        details["database"] = "ok"
    except Exception as e:
        details["database"] = str(e)

    # Verifica Evolution API
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"{settings.EVOLUTION_API_URL}/instance/fetchInstances",
                headers={"apikey": settings.EVOLUTION_API_TOKEN},
            )
            details["evolution_api"] = "ok" if resp.status_code == 200 else f"http_{resp.status_code}"
    except Exception as e:
        details["evolution_api"] = str(e)

    status = "ok" if all(v == "ok" for v in details.values()) else "degraded"
    return {"status": status, "details": details}
