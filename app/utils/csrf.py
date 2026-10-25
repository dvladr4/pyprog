"""CSRF-защита на сессиях, без сторонних библиотек."""
from __future__ import annotations

import secrets
from fastapi import Form, HTTPException, Request


_SESSION_KEY = "_csrf_token"


def get_or_create_csrf_token(request: Request) -> str:
    token = request.session.get(_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        request.session[_SESSION_KEY] = token
    return token


def _check(request: Request, token: str | None) -> None:
    expected = request.session.get(_SESSION_KEY)
    if not expected or not token or not secrets.compare_digest(expected, token):
        raise HTTPException(
            status_code=400,
            detail="CSRF token invalid or expired. Обновите страницу и попробуйте снова.",
        )


def verify_csrf(request: Request, csrf_token: str | None = Form(None)) -> None:
    """FastAPI dependency для POST-роутов.

    Ожидает поле csrf_token (его шлёт {{ csrf_input(request) }} в шаблонах).
    Если поле пустое/неверное — 400.
    """
    _check(request, csrf_token)
