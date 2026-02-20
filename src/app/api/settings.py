from fastapi import APIRouter

from app.core.deps import SettingsServiceDep
from app.models.settings import SettingsAIResponse, SettingsAIUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/ai", response_model=SettingsAIResponse)
def get_ai_settings(settings_service: SettingsServiceDep) -> SettingsAIResponse:
    """Get AI settings (singleton); auto-creates default row if missing."""
    settings = settings_service.get_or_create_settings()
    return SettingsAIResponse(
        ai_provider=settings.ai_provider,
        ai_model=settings.ai_model or "gpt-4o-mini",
        ai_api_key=settings.ai_api_key,
        ai_base_url=settings.ai_base_url,
        ai_report_prompt=settings.ai_report_prompt,
    )


@router.patch("/ai", response_model=SettingsAIResponse)
def patch_ai_settings(
    body: SettingsAIUpdate,
    settings_service: SettingsServiceDep,
) -> SettingsAIResponse:
    """Update AI settings (partial)."""
    settings = settings_service.update_ai_settings(body)
    return SettingsAIResponse(
        ai_provider=settings.ai_provider,
        ai_model=settings.ai_model or "gpt-4o-mini",
        ai_api_key=settings.ai_api_key,
        ai_base_url=settings.ai_base_url,
        ai_report_prompt=settings.ai_report_prompt,
    )
