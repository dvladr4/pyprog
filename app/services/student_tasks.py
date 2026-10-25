"""Данные для страницы списка задач ученика."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.submission import Submission
from app.models.task import Task


def best_submissions_by_task(db: Session, user_id: int,
                             task_ids: list[int]) -> dict[int, Submission]:
    """Для каждой задачи — лучшая (по числу пройденных тестов) попытка."""
    if not task_ids:
        return {}

    rows = (
        db.query(Submission)
        .filter(
            Submission.user_id == user_id,
            Submission.task_id.in_(task_ids),
            Submission.status == "done",
        )
        .order_by(Submission.tests_passed.desc(), Submission.created_at.desc())
        .all()
    )

    best: dict[int, Submission] = {}
    for sub in rows:
        if sub.task_id not in best:
            best[sub.task_id] = sub
    return best


def task_progress_view(db: Session, user_id: int,
                       tasks: list[Task]) -> dict[int, dict]:
    """Собирает для шаблона удобное представление по каждой задаче."""
    best = best_submissions_by_task(db, user_id, [t.id for t in tasks])
    out: dict[int, dict] = {}
    for t in tasks:
        sub = best.get(t.id)
        total = len(t.tests)
        if sub is None:
            out[t.id] = {
                "submission_id": None,
                "tests_passed": 0,
                "total_tests": total,
                "solved": False,
                "has_solution": False,
            }
            continue
        passed = sub.tests_passed or 0
        total_used = sub.total_tests or total
        solved = bool(total_used) and passed == total_used
        out[t.id] = {
            "submission_id": sub.id,
            "tests_passed": passed,
            "total_tests": total_used,
            "solved": solved,
            "has_solution": True,
        }
    return out
