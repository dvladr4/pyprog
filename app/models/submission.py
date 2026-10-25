from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(Text, nullable=False)
    filename = Column(String(256), nullable=True)
    status = Column(String(16), default="pending")   # pending|running|done|error
    verdict = Column(String(16), nullable=True)      # OK|WA|TLE|RE|CE
    tests_passed = Column(Integer, default=0)
    total_tests = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    results = relationship("TestResult", cascade="all, delete-orphan",
                           back_populates="submission", order_by="TestResult.order")


class TestResult(Base):
    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True)
    submission_id = Column(Integer, ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    order = Column(Integer, default=0)
    passed = Column(Boolean, default=False)
    input = Column(Text, default="")
    expected_output = Column(Text, default="")
    actual_output = Column(Text, default="")
    execution_ms = Column(Float, default=0.0)
    error = Column(Text, nullable=True)

    submission = relationship("Submission", back_populates="results")
