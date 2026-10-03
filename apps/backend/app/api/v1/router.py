from fastapi import APIRouter

from app.api.v1.endpoints import health
from app.modules.auth.api.router import router as auth_router
from app.modules.knowledge.api.router import router as document_router
from app.modules.knowledge.api.router import search_router
from app.modules.workspace.api.router import router as workspace_router

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(workspace_router)
api_v1_router.include_router(document_router)
api_v1_router.include_router(search_router)
