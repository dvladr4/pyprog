"""Настройки приложения (pydantic-settings + .env)."""
from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    SECRET_KEY: str = "dev-only-change-me"
    TEACHER_USERNAME: str = "admin"
    TEACHER_PASSWORD: str = "admin123"

    DB_URL: str = "sqlite:///./data/db.sqlite3"
    DATA_DIR: str = "./data"

    RUN_TIMEOUT_SEC: float = 5.0
    RUN_MEMORY_MB: int = 128
    RUN_MAX_CONCURRENT: int = 4

    @property
    def data_path(self) -> Path:
        return Path(self.DATA_DIR).resolve()


settings = Settings()
