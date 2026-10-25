"""Сервис комментариев учителя к решениям."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.comment import TeacherComment


def add_comment(db: Session, *, submission_id: int, teacher_id: int, text: str) -> TeacherComment:
    text = (text or "").strip()
    if not text:
        raise ValueError("Пустой комментарий")
    c = TeacherComment(
        submission_id=submission_id,
        teacher_id=teacher_id,
        text=text,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def delete_comment(db: Session, *, comment_id: int, teacher_id: int) -> bool:
    c = db.get(TeacherComment, comment_id)
    if not c or c.teacher_id != teacher_id:
        return False
    db.delete(c)
    db.commit()
    return True


def list_comments(db: Session, submission_id: int) -> list[TeacherComment]:
    return (
        db.query(TeacherComment)
        .filter_by(submission_id=submission_id)
        .order_by(TeacherComment.created_at)
        .all()
    )


def list_comments_for_user(db: Session, user_id: int) -> list[TeacherComment]:
    """Все комментарии к любым решениям ученика (для /me/report)."""
    from app.models.submission import Submission
    sub_ids = [
        row[0] for row in
        db.query(Submission.id).filter_by(user_id=user_id).all()
    ]
    if not sub_ids:
        return []
    return (
        db.query(TeacherComment)
        .filter(TeacherComment.submission_id.in_(sub_ids))
        .order_by(TeacherComment.created_at.desc())
        .all()
    )
