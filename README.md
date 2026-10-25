# Тестирующая система (олимпиады по программированию)

FastAPI + SQLite + Jinja2. Роли: ученик / учитель.
Запуск локально:

    python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    cp .env.example .env                                 # при необходимости поправь
    python -m scripts.init_db                            # создать БД и залить примеры
    uvicorn app.main:app --reload

Открыть: http://127.0.0.1:8000

Учитель: логин `admin`, пароль берётся из `TEACHER_PASSWORD` (по умолчанию `admin123`).
Ученик: выбирает своё имя на главной странице.

Деплой на Amvera — см. `amvera.yml` и `Dockerfile`.
