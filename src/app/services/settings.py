from app.db.schema import Settings
from app.models.settings import SettingsAIUpdate
from app.services.base import BaseService


class SettingsService(BaseService):

    def get_or_create_settings(self) -> Settings:
        settings = (
            self.session.query(Settings).filter(
                Settings.id == "default").first()
        )
        if not settings:
            settings = Settings(id="default")
            self.session.add(settings)
            self.session.commit()
            self.session.refresh(settings)
        return settings

    def update_ai_settings(self, data: SettingsAIUpdate) -> Settings:
        settings = self.get_or_create_settings()
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(settings, key, value)
        self.session.commit()
        self.session.refresh(settings)
        return settings
