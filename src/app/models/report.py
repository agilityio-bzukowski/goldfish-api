from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ReportGenerateRequest(BaseModel):

    date: Optional[str] = None  # ISO date "YYYY-MM-DD" or null for today
    prompt: Optional[str] = None  # Optional extra instruction; task list is always included


class ReportGenerateResponse(BaseModel):

    date: str
    task_count: int
    report: str
