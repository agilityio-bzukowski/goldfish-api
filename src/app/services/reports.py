"""Report generation: aggregate tasks for a date and call AI for summary."""

from datetime import date

from fastapi import HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.schema import AIProvider, Settings, Task
from app.models.report import ReportGenerateRequest, ReportGenerateResponse
from app.services.ai_client import AIClient
from app.services.settings import SettingsService

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant that summarizes task lists into brief daily reports. "
    "Be concise and actionable."
)


class ReportsService:
    def __init__(
        self,
        session: Session,
        settings_service: SettingsService,
        ai_client_factory: callable,
    ) -> None:
        self._session = session
        self._settings_service = settings_service
        self._ai_client_factory = ai_client_factory

    @staticmethod
    def _validate_api_key(settings: Settings) -> None:
        is_ollama = settings.ai_provider == AIProvider.OLLAMA
        if not settings.ai_api_key and not is_ollama:
            raise HTTPException(
                status_code=400, detail="AI API key not configured")

    @staticmethod
    def _parse_report_date(raw: str | None) -> date:
        if not raw:
            return date.today()
        try:
            return date.fromisoformat(raw)
        except ValueError:
            raise HTTPException(
                status_code=422, detail="Invalid date format; use YYYY-MM-DD"
            ) from None

    def _tasks_for_date(self, report_date: date) -> list[Task]:
        return list(
            self._session.query(Task)
            .filter(Task.deleted_at.is_(None))
            .filter(
                or_(
                    Task.due_date == report_date,
                    (
                        (Task.is_completed.is_(True))
                        & (func.date(Task.completed_at) == report_date)
                    ),
                )
            )
            .order_by(Task.sort_order.asc())
            .all()
        )

    @staticmethod
    def _build_user_prompt(tasks: list[Task], report_date: date) -> str:
        lines = [
            f"- {t.title}" + (" (completed)" if t.is_completed else "")
            for t in tasks
        ]
        if not lines:
            return "No tasks for this date."
        return (
            f"Tasks for {report_date.isoformat()} ({len(lines)} total):\n\n"
            + "\n".join(lines)
        )

    def _build_ai_client(self, settings: Settings) -> AIClient:
        return self._ai_client_factory(
            provider=settings.ai_provider.value,
            api_key=settings.ai_api_key,
            model=settings.ai_model or "gpt-4o-mini",
            base_url=settings.ai_base_url,
        )

    async def generate_report(
        self, request: ReportGenerateRequest
    ) -> ReportGenerateResponse:
        settings = self._settings_service.get_or_create_settings()
        self._validate_api_key(settings)

        report_date = self._parse_report_date(request.date)
        tasks = self._tasks_for_date(report_date)
        user_prompt = self._build_user_prompt(tasks, report_date)
        if request.prompt:
            user_prompt = f"{user_prompt}\n\nAdditional instruction: {request.prompt}"

        ai_client = self._build_ai_client(settings)
        try:
            report_text = await ai_client.complete(
                system_prompt=settings.ai_report_prompt or DEFAULT_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
        except Exception as e:
            err_msg = str(e).strip() or type(e).__name__
            detail = f"AI request failed: {err_msg}"
            raise HTTPException(status_code=503, detail=detail) from e

        return ReportGenerateResponse(
            date=report_date.isoformat(),
            task_count=len(tasks),
            report=report_text,
        )
