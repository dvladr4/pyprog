from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from app.database import Base


class TeacherComment(Base):
    __tablename__ = "teacher_comments"

    id = Column(Integer, primary_key=True)
    submission_id = Column(Integer, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
