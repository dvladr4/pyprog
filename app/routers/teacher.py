from __future__ import annotations

from fastapi import (
    APIRouter, Depends, File, Form, HTTPException,
    Request, UploadFile,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.task import Task
from app.models.user import User
from app.services.comments import add_comment, delete_comment, list_comments_for_user
from app.services.reports import build_student_report, build_student_stats
from app.services.stats import build_overall_stats
from app.services.tasks import (
    add_test_with_file,
    append_tests,
    clear_test_file,
    delete_test,
    import_usloviya,
    parse_tests_json,
    replace_examples,
    replace_tests,
    update_test_with_file,
)


from app.utils.csrf import verify_csrf
from app.utils.templates import templates

router = APIRouter(prefix="/admin", tags=["teacher"])


def _require_teacher(request: Request) -> int:
    if request.session.get("role") != "teacher":
        raise HTTPException(status_code=303, headers={"Location": "/login/teacher"})
    return int(request.session["user_id"])


# ---------- дашборд ----------
@router.get("", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    _require_teacher(request)
    tasks = db.query(Task).order_by(Task.external_number).all()
    students = db.query(User).filter_by(role="student").order_by(User.name).all()
    return templates.TemplateResponse(
        request, "teacher/dashboard.html",
        {"tasks": tasks, "students": students},
    )


# ---------- ученики ----------
@router.post("/students", dependencies=[Depends(verify_csrf)])
def add_student(request: Request, name: str = Form(...),
                db: Session = Depends(get_db)):
    _require_teacher(request)
    name = name.strip()
    if name and not db.query(User).filter_by(role="student", name=name).first():
        db.add(User(role="student", name=name))
        db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.post("/students/{user_id}/delete", dependencies=[Depends(verify_csrf)])
def delete_student(user_id: int, request: Request,
                   db: Session = Depends(get_db)):
    _require_teacher(request)
    u = db.get(User, user_id)
    if u and u.role == "student":
        db.delete(u)
        db.commit()
    return RedirectResponse("/admin", status_code=303)


# ---------- создание задачи ----------
@router.get("/tasks/new", response_class=HTMLResponse)
def task_new(request: Request):
    _require_teacher(request)
    return templates.TemplateResponse(
        request, "teacher/task_edit.html",
        {"task": None, "examples": [], "tests": [],
         "form_action": "/admin/tasks", "form": None, "error": None},
    )


@router.post("/tasks", dependencies=[Depends(verify_csrf)])
def task_create(
    request: Request,
    external_number: int = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    compare_mode: str = Form("exact"),
    requires_file_input: str | None = Form(None),
    input_filename: str | None = Form(None),
    db: Session = Depends(get_db),
):
    _require_teacher(request)
    existing = db.query(Task).filter_by(external_number=external_number).first()
    if existing:
        return templates.TemplateResponse(
            request, "teacher/task_edit.html",
            {
                "task": None, "examples": [], "tests": [],
                "form_action": "/admin/tasks",
                "error": f"Задача с номером {external_number} уже существует "
                         f"(id={existing.id}).",
                "form": {
                    "external_number": external_number, "title": title,
                    "description": description, "compare_mode": compare_mode,
                    "input_filename": input_filename or "",
                    "requires_file_input": bool(requires_file_input),
                },
            },
            status_code=400,
        )
    t = Task(
        external_number=external_number, title=title,
        description=description or "", compare_mode=compare_mode or "exact",
        requires_file_input=bool(requires_file_input),
        input_filename=(input_filename or "").strip() or None,
        is_published=True,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return RedirectResponse(f"/admin/tasks/{t.id}/edit", status_code=303)


# ---------- редактирование задачи ----------
@router.get("/tasks/{task_id}/edit", response_class=HTMLResponse)
def task_edit(task_id: int, request: Request, db: Session = Depends(get_db)):
    _require_teacher(request)
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404)
    return templates.TemplateResponse(
        request, "teacher/task_edit.html",
        {"task": task, "examples": task.examples, "tests": task.tests,
         "form_action": f"/admin/tasks/{task.id}", "form": None, "error": None},
    )


@router.post("/tasks/{task_id}", dependencies=[Depends(verify_csrf)])
def task_update(
    task_id: int, request: Request,
    external_number: int = Form(...), title: str = Form(...),
    description: str = Form(""), compare_mode: str = Form("exact"),
    requires_file_input: str | None = Form(None),
    input_filename: str | None = Form(None),
    db: Session = Depends(get_db),
):
    _require_teacher(request)
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404)
    clash = (db.query(Task)
               .filter(Task.external_number == external_number, Task.id != task.id)
               .first())
    if clash:
        return templates.TemplateResponse(
            request, "teacher/task_edit.html",
            {
                "task": task, "examples": task.examples, "tests": task.tests,
                "form_action": f"/admin/tasks/{task.id}",
                "error": f"Номер {external_number} уже занят задачей id={clash.id}.",
                "form": {
                    "external_number": external_number, "title": title,
                    "description": description, "compare_mode": compare_mode,
                    "input_filename": input_filename or "",
                    "requires_file_input": bool(requires_file_input),
                },
            },
            status_code=400,
        )
    task.external_number = external_number
    task.title = title
    task.description = description or ""
    task.compare_mode = compare_mode or "exact"
    task.requires_file_input = bool(requires_file_input)
    task.input_filename = (input_filename or "").strip() or None
    db.commit()
    return RedirectResponse(f"/admin/tasks/{task.id}/edit", status_code=303)


@router.post("/tasks/{task_id}/delete", dependencies=[Depends(verify_csrf)])
def task_delete(task_id: int, request: Request, db: Session = Depends(get_db)):
    _require_teacher(request)
    task = db.get(Task, task_id)
    if task:
        db.delete(task)
        db.commit()
    return RedirectResponse("/admin", status_code=303)


# ---------- примеры ----------
@router.post("/tasks/{task_id}/examples", dependencies=[Depends(verify_csrf)])
def task_examples_save(
    task_id: int, request: Request,
    ex_input: list[str] = Form(default=[]),
    ex_output: list[str] = Form(default=[]),
    db: Session = Depends(get_db),
):
    _require_teacher(request)
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404)
    examples = [{"input": i, "output": o} for i, o in zip(ex_input, ex_output)]
    replace_examples(db, task, examples)
    return RedirectResponse(f"/admin/tasks/{task.id}/edit#examples", status_code=303)


# ---------- тесты ----------
@router.post("/tasks/{task_id}/tests/upload", dependencies=[Depends(verify_csrf)])
async def task_tests_upload(
    task_id: int, request: Request,
    raw: str = Form(""),
    json_file: UploadFile | None = File(None),
    append: str | None = Form(None),
    db: Session = Depends(get_db),
):
    _require_teacher(request)
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404)
    text = raw or ""
    if json_file and json_file.filename:
        text = (await json_file.read()).decode("utf-8", errors="replace")
    try:
        tests = parse_tests_json(text)
    except ValueError as e:
        return _task_edit_with_error(request, db, task,
                                     f"Тесты не загружены: {e}")
    if append:
        append_tests(db, task, tests)
    else:
        replace_tests(db, task, tests)
    return RedirectResponse(f"/admin/tasks/{task.id}/edit#tests", status_code=303)


@router.post("/tasks/{task_id}/tests/clear", dependencies=[Depends(verify_csrf)])
def task_tests_clear(task_id: int, request: Request,
                     db: Session = Depends(get_db)):
    _require_teacher(request)
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404)
    replace_tests(db, task, [])
    return RedirectResponse(f"/admin/tasks/{task.id}/edit#tests", status_code=303)


@router.post("/tasks/{task_id}/tests/{test_id}/delete", dependencies=[Depends(verify_csrf)])
def task_test_delete(task_id: int, test_id: int, request: Request,
                     db: Session = Depends(get_db)):
    _require_teacher(request)
    delete_test(db, test_id, task_id)
    return RedirectResponse(f"/admin/tasks/{task_id}/edit#tests", status_code=303)


def _task_edit_with_error(request: Request, db: Session, task: Task, msg: str):
    return templates.TemplateResponse(
        request, "teacher/task_edit.html",
        {"task": task, "examples": task.examples, "tests": task.tests,
         "form_action": f"/admin/tasks/{task.id}", "form": None, "error": msg},
        status_code=400,
    )


# ---------- отчёт по ученику ----------
@router.get("/students/{user_id}/report", response_class=HTMLResponse)
def student_report(user_id: int, request: Request,
                   db: Session = Depends(get_db)):
    _require_teacher(request)
    user = db.get(User, user_id)
    if not user or user.role != "student":
        raise HTTPException(404, "Ученик не найден")
    data = build_student_report(db, user)
    stats = build_student_stats(db, user)
    comments = list_comments_for_user(db, user.id)
    return templates.TemplateResponse(
        request, "teacher/student_report.html",
        {"report": data, "stats": stats, "comments": comments, "mode": "teacher"},
    )


# ---------- сводная статистика ----------
@router.get("/stats", response_class=HTMLResponse)
def stats_page(request: Request, db: Session = Depends(get_db)):
    _require_teacher(request)
    stats = build_overall_stats(db)
    return templates.TemplateResponse(
        request, "teacher/stats.html", {"stats": stats},
    )


@router.get("/stats/export", response_class=HTMLResponse)
def stats_export(request: Request, db: Session = Depends(get_db)):
    _require_teacher(request)
    stats = build_overall_stats(db)
    html = templates.get_template("teacher/stats.html").render(
        {"request": request, "stats": stats}
    )
    from fastapi.responses import Response
    return Response(
        content=html, media_type="text/html",
        headers={"Content-Disposition": 'attachment; filename="stats.html"'},
    )


# ---------- импорт usloviya.json ----------
@router.get("/import", response_class=HTMLResponse)
def import_page(request: Request):
    _require_teacher(request)
    return templates.TemplateResponse(
        request, "teacher/import.html",
        {"result": None, "error": None, "raw": ""},
    )


@router.post("/import", dependencies=[Depends(verify_csrf)])
async def import_usloviya_route(
    request: Request,
    raw: str = Form(""),
    json_file: UploadFile | None = File(None),
    tests_dir: str = Form(""),
    overwrite: str | None = Form(None),
    db: Session = Depends(get_db),
):
    _require_teacher(request)
    text = raw or ""
    if json_file and json_file.filename:
        text = (await json_file.read()).decode("utf-8", errors="replace")
    if not text.strip():
        return templates.TemplateResponse(
            request, "teacher/import.html",
            {"result": None, "error": "Пустой ввод", "raw": raw},
            status_code=400,
        )
    try:
        result = import_usloviya(db, text,
                                 tests_dir=tests_dir.strip() or None,
                                 overwrite=bool(overwrite))
    except ValueError as e:
        return templates.TemplateResponse(
            request, "teacher/import.html",
            {"result": None, "error": str(e), "raw": raw}, status_code=400,
        )
    return templates.TemplateResponse(
        request, "teacher/import.html",
        {"result": result, "error": None, "raw": ""},
    )


# ---------- комментарии ----------
@router.post("/comments", dependencies=[Depends(verify_csrf)])
def comments_add(
    request: Request,
    submission_id: int = Form(...),
    text: str = Form(...),
    db: Session = Depends(get_db),
):
    teacher_id = _require_teacher(request)
    try:
        add_comment(db, submission_id=submission_id,
                    teacher_id=teacher_id, text=text)
    except ValueError:
        pass
    referer = request.headers.get("referer") or "/admin"
    return RedirectResponse(referer, status_code=303)


@router.post("/comments/{comment_id}/delete", dependencies=[Depends(verify_csrf)])
def comments_delete(
    comment_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    teacher_id = _require_teacher(request)
    delete_comment(db, comment_id=comment_id, teacher_id=teacher_id)
    referer = request.headers.get("referer") or "/admin"
    return RedirectResponse(referer, status_code=303)


# ---------- тесты для задач с open() ----------
@router.post("/tasks/{task_id}/tests/open/add", dependencies=[Depends(verify_csrf)])
async def open_test_add(
    task_id: int,
    request: Request,
    expected_output: str = Form(""),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    _require_teacher(request)
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404)
    if not task.requires_file_input:
        raise HTTPException(400, "Задача не помечена как использующая open()")

    content = ""
    if file and file.filename:
        content = (await file.read()).decode("utf-8", errors="replace")
        content = content.replace("\r\n", "\n").replace("\r", "\n")

    add_test_with_file(db, task, file_content=content, expected_output=expected_output)
    return RedirectResponse(f"/admin/tasks/{task.id}/edit#open-tests", status_code=303)


@router.post("/tasks/{task_id}/tests/{test_id}/open/update", dependencies=[Depends(verify_csrf)])
async def open_test_update(
    task_id: int,
    test_id: int,
    request: Request,
    expected_output: str = Form(""),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    _require_teacher(request)
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404)

    content: str | None = None
    if file and file.filename:
        content = (await file.read()).decode("utf-8", errors="replace")
        content = content.replace("\r\n", "\n").replace("\r", "\n")

    update_test_with_file(db, task, test_id,
                          file_content=content,
                          expected_output=expected_output)
    return RedirectResponse(f"/admin/tasks/{task.id}/edit#open-tests", status_code=303)


@router.post("/tasks/{task_id}/tests/{test_id}/file/clear", dependencies=[Depends(verify_csrf)])
def open_test_clear_file(task_id: int, test_id: int, request: Request,
                         db: Session = Depends(get_db)):
    _require_teacher(request)
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(404)
    clear_test_file(db, task, test_id)
    return RedirectResponse(f"/admin/tasks/{task.id}/edit#open-tests", status_code=303)
