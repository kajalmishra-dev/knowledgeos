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
    database_echo: bool | None = Field(default=None, validation_alias="DATABASE_ECHO")
    database_pool_size: int = Field(default=5, validation_alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, validation_alias="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, validation_alias="DATABASE_POOL_TIMEOUT")
    database_pool_recycle: int = Field(default=1800, validation_alias="DATABASE_POOL_RECYCLE")
    database_pool_pre_ping: bool = Field(default=True, validation_alias="DATABASE_POOL_PRE_PING")

    @property
    def sqlalchemy_echo(self) -> bool:
        if self.database_echo is not None:
            return self.database_echo
        return self.debug


@lru_cache
def get_settings() -> Settings:
    return Settings()
