from __future__ import annotations

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, Form, HTTPException,
    Request, UploadFile,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.submission import Submission
from app.models.task import Task
from app.models.user import User
from app.services.comments import list_comments, list_comments_for_user
from app.services.reports import build_student_report, build_student_stats
from app.services.submissions import check_submission_async, create_submission
from app.services.student_tasks import task_progress_view
from app.utils.csrf import verify_csrf
from app.utils.templates import templates

router = APIRouter(prefix="/tasks", tags=["student"])


def _require_student(request: Request) -> int:
    if request.session.get("role") != "student":
        raise HTTPException(status_code=303, headers={"Location": "/"})
    return int(request.session["user_id"])


# ---------- список задач ----------
# ---------- список задач ----------
@router.get("", response_class=HTMLResponse)
def task_list(request: Request, db: Session = Depends(get_db)):
    user_id = _require_student(request)
    tasks = (
        db.query(Task)
        .filter_by(is_published=True)
        .order_by(Task.external_number)
        .all()
    )
    progress = task_progress_view(db, user_id, tasks)
    return templates.TemplateResponse(
        request, "student/task_list.html",
        {
            "tasks": tasks,
            "progress": progress,
            "name": request.session.get("name"),
        },
    )

@router.get("/{task_id}", response_class=HTMLResponse)
def task_page(task_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = _require_student(request)
    task = db.get(Task, task_id)
    if not task or not task.is_published:
        raise HTTPException(404)

    # лучшая попытка ученика по этой задаче + её комментарии
    from app.services.student_tasks import best_submissions_by_task
    from app.services.comments import list_comments

    best = best_submissions_by_task(db, user_id, [task.id]).get(task.id)
    comments = list_comments(db, best.id) if best else []

    # данные для модалки/клеток (совместимо с report.js)
    progress = None
    test_results = []
    if best is not None:
        from app.models.submission import TestResult
        rows = (
            db.query(TestResult)
            .filter_by(submission_id=best.id)
            .order_by(TestResult.order)
            .all()
        )
        test_results = rows
        total = best.total_tests or len(rows)
        passed = best.tests_passed or 0
        progress = {
            "submission_id": best.id,
            "tests_passed": passed,
            "total_tests": total,
            "solved": bool(total) and passed == total,
            "has_solution": True,
        }

    return templates.TemplateResponse(
        request, "student/task.html",
        {
            "task": task,
            "submission": best,
            "test_results": test_results,
            "comments": comments,
            "progress": progress,
        },
    )


# ---------- отправка решения ----------
@router.post("/{task_id}/submit", dependencies=[Depends(verify_csrf)])
async def submit(
    task_id: int,
    request: Request,
    background: BackgroundTasks,
    code: str = Form(""),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    user_id = _require_student(request)
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404)

    if file and file.filename:
        code = (await file.read()).decode("utf-8", errors="replace")
    if not code.strip():
        raise HTTPException(400, "Пустой код")

    sub = create_submission(
        db, user_id=user_id, task_id=task.id,
        code=code, filename=file.filename if file else None,
    )
    background.add_task(check_submission_async, sub.id)
    return RedirectResponse(f"/submissions/{sub.id}", status_code=303)


# ---------- просмотр результата ----------
submissions_router = APIRouter(tags=["student"])


@submissions_router.get("/submissions/{sub_id}", response_class=HTMLResponse)
def view_submission(sub_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = _require_student(request)
    sub = db.get(Submission, sub_id)
    if not sub or sub.user_id != user_id:
        raise HTTPException(404)
    task = db.get(Task, sub.task_id)
    comments = list_comments(db, sub.id)
    return templates.TemplateResponse(
        request, "student/result.html",
        {"sub": sub, "task": task, "comments": comments, "mode": "student"},
    )


# ---------- мой отчёт ----------
student_me_router = APIRouter(tags=["student"])


@student_me_router.get("/me/report", response_class=HTMLResponse)
def my_report(request: Request, db: Session = Depends(get_db)):
    user_id = _require_student(request)
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404)
    report = build_student_report(db, user)
    stats = build_student_stats(db, user)
    comments = list_comments_for_user(db, user.id)
    return templates.TemplateResponse(
        request, "teacher/student_report.html",
        {"report": report, "stats": stats, "comments": comments, "mode": "student"},
    )