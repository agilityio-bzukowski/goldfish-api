from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    app_name: str = "Goldfish API"
    debug: bool = False
    # SQLite by default; set DATABASE_URL for PostgreSQL (e.g. postgresql://user:pass@host:5432/db)
    database_url: str = "sqlite:///./task_management.db"

    @property
    def sqlalchemy_database_uri(self) -> str:
        """Used by Alembic; same as database_url."""
        return self.database_url


settings = Settings()
