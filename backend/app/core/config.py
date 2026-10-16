from functools import lru_cache
from typing import Optional
from pydantic import Field
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
    gemini_llm_model: str = "gemini-3.5-flash-lite"
    gemini_embedding_model: str = "gemini-embedding-001"
    # Existing migration stores vector(768); changing this requires a migration.
    gemini_embedding_dimension: int = Field(default=768, ge=768, le=768)
    rag_similarity_threshold: float = Field(default=0.60, ge=0.60, le=1.0)

    # ServiceNow
    servicenow_instance_url: Optional[str] = None
    servicenow_username: Optional[str] = None
    servicenow_password: Optional[str] = None
    servicenow_timeout_seconds: float = 10.0
    use_mock_servicenow: bool = False
    servicenow_caller_sys_id: Optional[str] = None
    servicenow_fallback_group_sys_id: Optional[str] = None
    servicenow_group_ids: dict[str, str] = Field(default_factory=dict)

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
