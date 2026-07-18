from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="KnowledgeOS API", validation_alias="APP_NAME")
    app_version: str = Field(default="0.1.0", validation_alias="APP_VERSION")
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        validation_alias="ENVIRONMENT",
    )
    debug: bool = Field(default=False, validation_alias="DEBUG")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    api_v1_prefix: str = Field(default="/api/v1", validation_alias="API_V1_PREFIX")

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/knowledgeos",
        validation_alias="DATABASE_URL",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
