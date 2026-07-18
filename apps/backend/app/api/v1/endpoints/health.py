from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["healthy"] = "healthy"
    service: str
    version: str


@router.get("/health", response_model=HealthResponse, summary="Service health check")
async def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        service=settings.app_name,
        version=settings.app_version,
    )
