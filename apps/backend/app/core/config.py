from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env relative to the backend package root, not the process cwd.
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
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

    jwt_secret_key: str = Field(
        default="dev-only-change-me",
        validation_alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=15,
        validation_alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    refresh_token_expire_days: int = Field(default=7, validation_alias="REFRESH_TOKEN_EXPIRE_DAYS")
    refresh_token_cookie_name: str = Field(
        default="refresh_token",
        validation_alias="REFRESH_TOKEN_COOKIE_NAME",
    )
    refresh_token_cookie_path: str = Field(
        default="/api/v1/auth",
        validation_alias="REFRESH_TOKEN_COOKIE_PATH",
    )
    refresh_token_cookie_secure: bool = Field(
        default=False,
        validation_alias="REFRESH_TOKEN_COOKIE_SECURE",
    )
    refresh_token_cookie_httponly: bool = Field(
        default=True,
        validation_alias="REFRESH_TOKEN_COOKIE_HTTPONLY",
    )
    refresh_token_cookie_samesite: Literal["lax", "strict", "none"] = Field(
        default="lax",
        validation_alias="REFRESH_TOKEN_COOKIE_SAMESITE",
    )

    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")

    minio_endpoint: str = Field(default="localhost:9000", validation_alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="minioadmin", validation_alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="minioadmin", validation_alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(default="knowledgeos", validation_alias="MINIO_BUCKET")
    minio_secure: bool = Field(default=False, validation_alias="MINIO_SECURE")

    storage_backend: Literal["minio", "memory"] = Field(
        default="minio",
        validation_alias="STORAGE_BACKEND",
    )
    ingestion_queue: Literal["arq", "inline"] = Field(
        default="arq",
        validation_alias="INGESTION_QUEUE",
    )

    max_upload_bytes: int = Field(default=10_000_000, validation_alias="MAX_UPLOAD_BYTES")
    chunk_size: int = Field(default=800, validation_alias="INGESTION_CHUNK_SIZE")
    chunk_overlap: int = Field(default=150, validation_alias="INGESTION_CHUNK_OVERLAP")

    embedding_provider: Literal["openai", "local"] = Field(
        default="local",
        validation_alias="EMBEDDING_PROVIDER",
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        validation_alias="EMBEDDING_MODEL",
    )
    embedding_dimensions: int = Field(default=1536, validation_alias="EMBEDDING_DIMENSIONS")

    chat_provider: Literal["openai", "extractive"] = Field(
        default="extractive",
        validation_alias="CHAT_PROVIDER",
    )
    chat_model: str = Field(default="gpt-4o-mini", validation_alias="CHAT_MODEL")
    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias="OPENAI_BASE_URL",
    )

    retrieval_top_k: int = Field(default=5, validation_alias="RETRIEVAL_TOP_K")
    retrieval_min_score: float = Field(default=0.18, validation_alias="RETRIEVAL_MIN_SCORE")
    rag_max_context_chars: int = Field(default=12_000, validation_alias="RAG_MAX_CONTEXT_CHARS")

    @property
    def sqlalchemy_echo(self) -> bool:
        if self.database_echo is not None:
            return self.database_echo
        return self.debug


@lru_cache
def get_settings() -> Settings:
    return Settings()
