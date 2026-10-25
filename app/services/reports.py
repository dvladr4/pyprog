"""Агрегация результатов для отчётов учителя/ученика."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.submission import Submission, TestResult
from app.models.task import Task
from app.models.user import User


def _best_submission_for_task(db: Session, user_id: int, task_id: int) -> Submission | None:
    """Лучшая (по числу пройденных тестов) попытка ученика по задаче.

    Если лучших несколько — берём самую свежую.
    """
    rows = (
        db.query(Submission)
        .filter_by(user_id=user_id, task_id=task_id, status="done")
        .order_by(Submission.tests_passed.desc(), Submission.created_at.desc())
        .all()
    )
    return rows[0] if rows else None


def build_student_report(db: Session, user: User) -> dict[str, Any]:
    """Возвращает структуру, которую отрендерит Jinja-шаблон.

    {
        "user": User,
        "tasks": [
            {
                "task": Task,
                "total_tests": int,
                "tests_passed": int,
                "solved": bool,
                "submission": Submission | None,
                "test_results": [ {order, passed, input, expected_output,
                                   actual_output, error, execution_ms}, ... ],
            }, ...
        ],
        "summary": {
            "total_tasks": int,
            "solved": int,
            "solve_percent": float,
            "tests_passed": int,
            "tests_total": int,
            "success_percent": float,
        },
    }
    """
    tasks = (
        db.query(Task)
        .filter_by(is_published=True)
        .order_by(Task.external_number)
        .all()
    )

    task_rows: list[dict[str, Any]] = []
    total_tests = 0
    total_passed = 0
    solved_count = 0

    for task in tasks:
        sub = _best_submission_for_task(db, user.id, task.id)

        if sub is None:
            task_rows.append({
                "task": task,
                "total_tests": len(task.tests),
                "tests_passed": 0,
                "solved": False,
                "submission": None,
                "test_results": [],
            })
            total_tests += len(task.tests)
            continue

        results = (
            db.query(TestResult)
            .filter_by(submission_id=sub.id)
            .order_by(TestResult.order)
            .all()
        )
        total_tests += len(results)
        total_passed += sum(1 for r in results if r.passed)
        solved = bool(sub.total_tests) and sub.tests_passed == sub.total_tests
        if solved:
            solved_count += 1

        task_rows.append({
            "task": task,
            "total_tests": sub.total_tests or len(results),
            "tests_passed": sub.tests_passed,
            "solved": solved,
            "submission": sub,
            "test_results": results,
        })

    summary = {
        "total_tasks": len(tasks),
        "solved": solved_count,
        "solve_percent": (solved_count / len(tasks) * 100.0) if tasks else 0.0,
        "tests_passed": total_passed,
        "tests_total": total_tests,
        "success_percent": (total_passed / total_tests * 100.0) if total_tests else 0.0,
    }

    return {"user": user, "tasks": task_rows, "summary": summary}


# ---------- статистика по одному ученику (для /me/report) ----------

def build_student_stats(db, user) -> dict:
    """Совместимо по структуре с build_overall_stats() из services.stats,
    но только для одного ученика.

    Возвращает те же ключи: students, tasks, matrix, task_stats,
    student_stats, summary. Используется в шаблоне _stats_body.html
    одинаково для страницы учителя и страницы ученика.
    """
    from app.services.stats import build_overall_stats  # избегаем цикла импорта
    full = build_overall_stats(db)

    # Оставляем только одного ученика
    students = [s for s in full["students"] if s.id == user.id]
    tasks = full["tasks"]

    matrix = {user.id: full["matrix"].get(user.id, {})}
    student_stats = {user.id: full["student_stats"].get(
        user.id,
        {"solved_count": 0, "total_tasks": len(tasks), "solved_percent": 0.0,
         "tests_passed": 0, "tests_total": 0, "success_percent": 0.0},
    )}
    task_stats = full["task_stats"]  # они не зависят от выбора учеников? см. ниже

    # Внимание: task_stats в build_overall_stats считаются по всем ученикам.
    # Для одного ученика пересчитываем только по нему.
    task_stats_one = {
        t.id: {
            "solved_count": 0, "solved_percent": 0.0,
            "tests_passed": 0, "tests_total": 0, "success_percent": 0.0,
        }
        for t in tasks
    }
    cell = matrix[user.id]
    for t in tasks:
        c = cell.get(t.id)
        if not c or c["submission_id"] is None:
            task_stats_one[t.id]["tests_total"] += c["total_tests"] if c else len(t.tests)
            continue
        task_stats_one[t.id]["tests_passed"] += c["tests_passed"]
        task_stats_one[t.id]["tests_total"] += c["total_tests"]
        if c["solved"]:
            task_stats_one[t.id]["solved_count"] += 1

    for t_id, st in task_stats_one.items():
        st["solved_percent"] = (
            st["solved_count"] / 1 * 100.0 if st["solved_count"] else 0.0
        )
        st["success_percent"] = (
            st["tests_passed"] / st["tests_total"] * 100.0
            if st["tests_total"] else 0.0
        )

    summary = {
        "students": 1,
        "tasks": len(tasks),
        "avg_solve_percent": student_stats[user.id]["solved_percent"],
        "avg_success_percent": student_stats[user.id]["success_percent"],
    }

    return {
        "students": students,
        "tasks": tasks,
        "matrix": matrix,
        "task_stats": task_stats_one,
        "student_stats": student_stats,
        "summary": summary,
    }
