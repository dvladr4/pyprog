"""Jinja2Templates с общими глобалами (csrf_input)."""
from __future__ import annotations

from pathlib import Path
from fastapi import Request
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from app.utils.csrf import get_or_create_csrf_token

_templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))


def _csrf_input(request: Request) -> Markup:
    """Возвращает <input type="hidden" name="csrf_token" value="...">."""
    token = get_or_create_csrf_token(request)
    return Markup(
        f'<input type="hidden" name="csrf_token" value="{token}">'
    )


templates.env.globals["csrf_input"] = _csrf_input

templates.env.globals["get_or_create_csrf_token"] = get_or_create_csrf_token
