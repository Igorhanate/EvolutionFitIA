import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Migrations only need DATABASE_URL — load it without requiring full settings
# validation (which would need META_*, Hotmart, etc. env vars too).
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Base(DeclarativeBase):
    pass


def _database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    from app.config import settings
    return settings.DATABASE_URL


engine = create_engine(_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
