"""Простая in-process очередь проверок с ограничением параллелизма."""
from __future__ import annotations

import asyncio

from app.config import settings

_semaphore = asyncio.Semaphore(settings.RUN_MAX_CONCURRENT)


def get_semaphore() -> asyncio.Semaphore:
    return _semaphore
