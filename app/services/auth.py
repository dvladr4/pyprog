"""Аутентификация: хэши паролей, поиск/создание пользователей."""
from __future__ import annotations

import hashlib
import hmac
import secrets

from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User

_ITER = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _ITER)
    return f"pbkdf2_sha256${_ITER}${salt}${h.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt, hhex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iters))
        return hmac.compare_digest(h.hex(), hhex)
    except Exception:
        return False


def get_or_create_student(db: Session, name: str) -> User | None:
    user = db.query(User).filter_by(role="student", name=name).first()
    return user


def authenticate_teacher(db: Session, username: str, password: str) -> User | None:
    user = db.query(User).filter_by(role="teacher", username=username).first()
    if not user or not user.password_hash:
        return None
    if verify_password(password, user.password_hash):
        return user
    return None
