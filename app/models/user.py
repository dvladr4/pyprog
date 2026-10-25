from __future__ import annotations

from sqlalchemy import Boolean, Column, Integer, String
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    role = Column(String(16), nullable=False, index=True)   # student|teacher
    name = Column(String(128), nullable=False)
    username = Column(String(64), unique=True, nullable=True)
    password_hash = Column(String(256), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
