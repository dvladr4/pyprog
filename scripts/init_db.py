"""Инициализация БД: создать таблицы, добавить учителя и демо-учеников.

    python -m scripts.init_db
"""
from __future__ import annotations

import os
from pathlib import Path

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.models.user import User
from app.services.auth import hash_password


def main() -> None:
    # 1. папка данных
    Path(settings.DATA_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.DATA_DIR, "tasks").mkdir(parents=True, exist_ok=True)

    # 2. таблицы
    from app import models  # noqa: F401  — регистрация всех моделей
    Base.metadata.create_all(bind=engine)

    # 3. учитель
    db = SessionLocal()
    try:
        teacher = db.query(User).filter_by(role="teacher").first()
        if not teacher:
            teacher = User(
                role="teacher",
                name=settings.TEACHER_USERNAME,
                username=settings.TEACHER_USERNAME,
                password_hash=hash_password(settings.TEACHER_PASSWORD),
                is_active=True,
            )
            db.add(teacher)
            db.commit()
            print(f"[init_db] учитель создан: {settings.TEACHER_USERNAME}")

        # 4. демо-ученики (можно удалить)
        demo_students = ["Белов Павел", "Андреев Никита"]
        for name in demo_students:
            if not db.query(User).filter_by(name=name, role="student").first():
                db.add(User(role="student", name=name, is_active=True))
        db.commit()
        print("[init_db] готово. Откройте приложение и войдите как учитель.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
