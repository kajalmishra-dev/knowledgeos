from typing import Literal

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import text

from app.core.config import get_settings
from app.infrastructure.database.session import async_session_factory
from app.infrastructure.storage import get_object_storage

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["healthy"] = "healthy"
    service: str
    version: str


class ReadyResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, bool]


@router.get("/health", response_model=HealthResponse, summary="Service health check")
async def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        service=settings.app_name,
        version=settings.app_version,
    )


@router.get("/ready", response_model=ReadyResponse, summary="Dependency readiness check")
async def readiness_check() -> ReadyResponse | JSONResponse:
    settings = get_settings()
    checks = {"database": False, "redis": False, "storage": False}

    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        checks["database"] = False

    try:
        redis = Redis.from_url(settings.redis_url)
        try:
            checks["redis"] = bool(await redis.ping())
        finally:
            await redis.aclose()
    except Exception:
        checks["redis"] = False

    try:
        checks["storage"] = await get_object_storage(settings).healthy()
    except Exception:
        checks["storage"] = False

    payload = ReadyResponse(
        status="ready" if all(checks.values()) else "not_ready",
        checks=checks,
    )
    if payload.status != "ready":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=payload.model_dump(),
        )
    return payload
