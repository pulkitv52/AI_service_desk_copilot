from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and environment configuration."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General
    app_name: str = "AI Service Desk Copilot"
    app_version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # Gemini
    gemini_api_key: Optional[str] = None

    # ServiceNow
    servicenow_instance_url: Optional[str] = None
    servicenow_username: Optional[str] = None
    servicenow_password: Optional[str] = None
    servicenow_timeout_seconds: float = 10.0
    use_mock_servicenow: bool = False

    # Database
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/service_desk"
    )

    @property
    def is_servicenow_configured(self) -> bool:
        """Check if real ServiceNow credentials are fully configured."""
        if self.use_mock_servicenow:
            return False
        return bool(
            self.servicenow_instance_url
            and self.servicenow_username
            and self.servicenow_password
        )


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()
