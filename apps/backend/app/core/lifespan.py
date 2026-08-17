from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

import app.infrastructure.database.models  # noqa: F401
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.infrastructure.database.session import engine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.environment == "production" and settings.jwt_secret_key in {
        "",
        "dev-only-change-me",
    }:
        raise RuntimeError("Set a strong JWT_SECRET_KEY before running in production.")
    setup_logging(settings)
    yield
    await engine.dispose()
