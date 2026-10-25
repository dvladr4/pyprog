from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    external_number = Column(Integer, unique=True, nullable=False, index=True)
    title = Column(String(256), nullable=False)
    description = Column(Text, default="")
    requires_file_input = Column(Boolean, default=False)
    input_filename = Column(String(128), nullable=True)   # e.g. input.txt
    compare_mode = Column(String(32), default="exact")    # exact|tokens|ignore_whitespace|float
    is_published = Column(Boolean, default=True)

    examples = relationship("TaskExample", cascade="all, delete-orphan",
                            order_by="TaskExample.order", back_populates="task")
    tests = relationship("TaskTest", cascade="all, delete-orphan",
                         order_by="TaskTest.order", back_populates="task")


class TaskExample(Base):
    __tablename__ = "task_examples"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    order = Column(Integer, default=0)
    input = Column(Text, default="")
    output = Column(Text, default="")

    task = relationship("Task", back_populates="examples")


class TaskTest(Base):
    __tablename__ = "task_tests"

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    order = Column(Integer, default=0)
    input = Column(Text, default="")
    expected_output = Column(Text, default="")
    file_content = Column(Text, nullable=True)   # для задач с open()

    task = relationship("Task", back_populates="tests")
