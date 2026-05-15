from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
from app.routers import whatsapp, hotmart, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Verifica conexão com banco na inicialização
    with engine.connect() as conn:
        conn.execute(__import__("sqlalchemy").text("SELECT 1"))
    yield


app = FastAPI(
    title="Evolution Fit IA",
    description="SaaS fitness no WhatsApp com IA",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(whatsapp.router, prefix="/webhook")
app.include_router(hotmart.router, prefix="/webhook")
app.include_router(admin.router, prefix="/admin")


@app.get("/")
async def health():
    return {"status": "ok", "service": "Evolution Fit IA"}
