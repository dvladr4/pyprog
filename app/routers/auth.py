from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth import authenticate_teacher, get_or_create_student
from app.utils.csrf import verify_csrf
from app.utils.templates import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    if request.session.get("role") == "teacher":
        return RedirectResponse("/admin", status_code=303)
    if request.session.get("role") == "student":
        return RedirectResponse("/tasks", status_code=303)
    students = (
        db.query(User)
        .filter_by(role="student", is_active=True)
        .order_by("name")
        .all()
    )
    return templates.TemplateResponse(
        request, "auth/index.html", {"students": students}
    )


@router.post("/login/student", dependencies=[Depends(verify_csrf)])
def login_student(request: Request, name: str = Form(...),
                  db: Session = Depends(get_db)):
    user = get_or_create_student(db, name)
    if not user:
        return RedirectResponse("/?error=unknown_student", status_code=303)
    request.session["role"] = "student"
    request.session["user_id"] = user.id
    request.session["name"] = user.name
    return RedirectResponse("/tasks", status_code=303)


@router.get("/login/teacher", response_class=HTMLResponse)
def teacher_login_form(request: Request):
    return templates.TemplateResponse(request, "auth/teacher_login.html", {})


@router.post("/login/teacher", dependencies=[Depends(verify_csrf)])
def login_teacher(request: Request, username: str = Form(...),
                  password: str = Form(...), db: Session = Depends(get_db)):
    user = authenticate_teacher(db, username, password)
    if not user:
        return RedirectResponse("/login/teacher?error=1", status_code=303)
    request.session["role"] = "teacher"
    request.session["user_id"] = user.id
    request.session["name"] = user.name
    return RedirectResponse("/admin", status_code=303)


@router.post("/logout", dependencies=[Depends(verify_csrf)])
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)