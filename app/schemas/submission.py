from __future__ import annotations
from pydantic import BaseModel


class SubmissionIn(BaseModel):
    code: str
    filename: str | None = None
