"""Сводная статистика по всем ученикам и задачам."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.submission import Submission
from app.models.task import Task
from app.models.user import User


def _best_submission(db: Session, user_id: int, task_id: int) -> Submission | None:
    rows = (
        db.query(Submission)
        .filter_by(user_id=user_id, task_id=task_id, status="done")
        .order_by(Submission.tests_passed.desc(), Submission.created_at.desc())
        .all()
    )
    return rows[0] if rows else None


def build_overall_stats(db: Session) -> dict[str, Any]:
    """Собирает матрицу «ученик × задача» и агрегаты.

    Возвращает:
    {
      "students": [User, ...],
      "tasks": [Task, ...],
      "matrix": {
        user_id: {
          task_id: {
            "tests_passed": int,
            "total_tests": int,
            "solved": bool,
            "submission_id": int | None,
          }, ...
        }, ...
      },
      "task_stats": {
        task_id: {
          "solved_count": int,
          "solved_percent": float,
          "tests_passed": int,
          "tests_total": int,
          "success_percent": float,
        }, ...
      },
      "student_stats": {
        user_id: {
          "solved_count": int,
          "total_tasks": int,
          "solved_percent": float,
          "tests_passed": int,
          "tests_total": int,
          "success_percent": float,
        }, ...
      },
      "summary": {
        "students": int,
        "tasks": int,
        "avg_solve_percent": float,
        "avg_success_percent": float,
      }
    }
    """
    students = (
        db.query(User)
        .filter_by(role="student", is_active=True)
        .order_by(User.name)
        .all()
    )
    tasks = (
        db.query(Task)
        .filter_by(is_published=True)
        .order_by(Task.external_number)
        .all()
    )

    matrix: dict[int, dict[int, dict[str, Any]]] = {}
    for s in students:
        matrix[s.id] = {}

    task_stats: dict[int, dict[str, Any]] = {
        t.id: {
            "solved_count": 0,
            "solved_percent": 0.0,
            "tests_passed": 0,
            "tests_total": 0,
            "success_percent": 0.0,
        }
        for t in tasks
    }
    student_stats: dict[int, dict[str, Any]] = {
        s.id: {
            "solved_count": 0,
            "total_tasks": len(tasks),
            "solved_percent": 0.0,
            "tests_passed": 0,
            "tests_total": 0,
            "success_percent": 0.0,
        }
        for s in students
    }

    for s in students:
        for t in tasks:
            sub = _best_submission(db, s.id, t.id)
            if sub is None:
                matrix[s.id][t.id] = {
                    "tests_passed": 0,
                    "total_tests": len(t.tests),
                    "solved": False,
                    "submission_id": None,
                }
                task_stats[t.id]["tests_total"] += len(t.tests)
                continue

            total = sub.total_tests or 0
            passed = sub.tests_passed or 0
            solved = bool(total) and passed == total

            matrix[s.id][t.id] = {
                "tests_passed": passed,
                "total_tests": total,
                "solved": solved,
                "submission_id": sub.id,
            }

            task_stats[t.id]["tests_passed"] += passed
            task_stats[t.id]["tests_total"] += total
            if solved:
                task_stats[t.id]["solved_count"] += 1

            student_stats[s.id]["tests_passed"] += passed
            student_stats[s.id]["tests_total"] += total
            if solved:
                student_stats[s.id]["solved_count"] += 1

    # проценты
    for t_id, st in task_stats.items():
        st["solved_percent"] = (
            st["solved_count"] / len(students) * 100.0 if students else 0.0
        )
        st["success_percent"] = (
            st["tests_passed"] / st["tests_total"] * 100.0
            if st["tests_total"] else 0.0
        )

    for s_id, st in student_stats.items():
        st["solved_percent"] = (
            st["solved_count"] / st["total_tasks"] * 100.0
            if st["total_tasks"] else 0.0
        )
        st["success_percent"] = (
            st["tests_passed"] / st["tests_total"] * 100.0
            if st["tests_total"] else 0.0
        )

    summary = {
        "students": len(students),
        "tasks": len(tasks),
        "avg_solve_percent": (
            sum(x["solved_percent"] for x in student_stats.values()) / len(students)
            if students else 0.0
        ),
        "avg_success_percent": (
            sum(x["success_percent"] for x in student_stats.values()) / len(students)
            if students else 0.0
        ),
    }

    return {
        "students": students,
        "tasks": tasks,
        "matrix": matrix,
        "task_stats": task_stats,
        "student_stats": student_stats,
        "summary": summary,
    }
