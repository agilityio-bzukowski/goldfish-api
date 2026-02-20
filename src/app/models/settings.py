"""Settings AI API schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.db.schema import AIProvider

SUPPORTED_PROVIDERS = [p.value for p in AIProvider]
SUPPORTED_PROVIDERS_STR = ", ".join(SUPPORTED_PROVIDERS)


def _validate_ai_provider(value: object) -> AIProvider:
    if isinstance(value, AIProvider):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        for p in AIProvider:
            if p.value == normalized:
                return p
    raise ValueError(f"Supported providers: {SUPPORTED_PROVIDERS_STR}")


class SettingsAIResponse(BaseModel):
    """AI settings returned by GET /api/settings/ai."""

    ai_provider: AIProvider = Field(
        description=f"AI provider. Supported: {SUPPORTED_PROVIDERS_STR}",
        examples=["openai"],
    )
    ai_model: str
    ai_api_key: Optional[str] = None
    ai_base_url: Optional[str] = None
    ai_report_prompt: Optional[str] = None


class SettingsAIUpdate(BaseModel):
    """Partial AI settings for PATCH /api/settings/ai."""

    ai_provider: Optional[AIProvider] = Field(
        default=None,
        description=f"AI provider. Supported: {SUPPORTED_PROVIDERS_STR}",
        examples=["openai"],
    )
    ai_model: Optional[str] = None
    ai_api_key: Optional[str] = None
    ai_base_url: Optional[str] = None
    ai_report_prompt: Optional[str] = None

    @field_validator("ai_provider", mode="before")
    @classmethod
    def validate_ai_provider(cls, value: object) -> Optional[AIProvider]:
        if value is None:
            return None
        return _validate_ai_provider(value)
