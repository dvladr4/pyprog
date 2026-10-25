"""Приём решения и его проверка."""
from __future__ import annotations

import asyncio

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.submission import Submission, TestResult
from app.models.task import Task
from app.services.testing.comparator import compare
from app.services.testing.sandbox import run_python
from app.services.testing.queue import get_semaphore


def create_submission(db: Session, *, user_id: int, task_id: int,
                      code: str, filename: str | None) -> Submission:
    sub = Submission(user_id=user_id, task_id=task_id, code=code,
                     filename=filename, status="pending")
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def _check_sync(sub_id: int) -> None:
    db = SessionLocal()
    try:
        sub = db.get(Submission, sub_id)
        if not sub:
            return
        task = db.get(Task, sub.task_id)
        sub.status = "running"
        db.commit()

        passed = 0
        total = len(task.tests)
        for i, test in enumerate(task.tests):
            files = None
            if task.requires_file_input and task.input_filename:
                fc = (test.file_content or "").replace("\r\n", "\n").replace("\r", "\n")
                files = {task.input_filename: fc}
            res = run_python(
                sub.code, test.input,
                timeout=settings.RUN_TIMEOUT_SEC,
                memory_mb=settings.RUN_MEMORY_MB,
                files=files,
            )
            ok = res.verdict == "OK" and compare(
                res.stdout, test.expected_output, task.compare_mode
            )
            db.add(TestResult(
                submission_id=sub.id, order=i, passed=ok,
                input=test.input, expected_output=test.expected_output,
                actual_output=res.stdout,
                execution_ms=res.execution_ms,
                error=res.stderr if res.verdict != "OK" else None,
            ))
            if ok:
                passed += 1

        sub.tests_passed = passed
        sub.total_tests = total
        if passed == total:
            sub.verdict = "OK"
        else:
            # грубая оценка: если были RE/TLE хотя бы в одном тесте
            sub.verdict = "WA"
        sub.status = "done"
        db.commit()
    finally:
        db.close()


async def check_submission_async(sub_id: int) -> None:
    async with get_semaphore():
        # блокирующий запуск — в пул потоков, чтобы не душить event loop
        await asyncio.to_thread(_check_sync, sub_id)
