"""Точка входа FastAPI."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.routers import auth, student, teacher
from app.utils.templates import templates  # noqa: F401  — регистрация глобалов


def _bootstrap_db() -> None:
    """Создать таблицы и учителя из env, если их ещё нет.

    Вызывается при старте приложения. Идемпотентно:
      * create_all() не трогает существующие таблицы;
      * учитель создаётся, только если в БД нет ни одного teacher.
    """
    from app.database import Base, SessionLocal, engine
    from app.models.user import User
    from app.services.auth import hash_password
    from app import models  # noqa: F401 — регистрация моделей

    Path(settings.DATA_DIR).mkdir(parents=True, exist_ok=True)

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if not db.query(User).filter_by(role="teacher").first():
            db.add(User(
                role="teacher",
                name=settings.TEACHER_USERNAME,
                username=settings.TEACHER_USERNAME,
                password_hash=hash_password(settings.TEACHER_PASSWORD),
                is_active=True,
            ))
            db.commit()
    finally:
        db.close()


def create_app() -> FastAPI:
    _bootstrap_db()

    app = FastAPI(title="Тестирующая система")
    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

    static_dir = Path(__file__).resolve().parent.parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    app.include_router(auth.router)
    app.include_router(student.router)
    app.include_router(student.submissions_router)
    app.include_router(student.student_me_router)
    app.include_router(teacher.router)

    return app


app = create_app()
