"""SQLAlchemy engine/session."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# SQLite + FastAPI: нужно check_same_thread=False
_connect_args = {"check_same_thread": False} if settings.DB_URL.startswith("sqlite") else {}
engine = create_engine(settings.DB_URL, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
