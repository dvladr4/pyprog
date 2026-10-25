from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class ExampleIn(BaseModel):
    input: str = ""
    output: str = ""


class TaskIn(BaseModel):
    external_number: int
    title: str
    description: str = ""
    requires_file_input: bool = False
    input_filename: str | None = None
    compare_mode: Literal["exact", "tokens", "ignore_whitespace", "float"] = "exact"
    examples: list[ExampleIn] = Field(default_factory=list)
