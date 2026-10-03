"""
Import all ORM model modules here for Alembic metadata discovery.
"""

from app.modules.auth.infrastructure.models import RefreshTokenModel, UserModel
from app.modules.knowledge.infrastructure.models import DocumentChunkModel, DocumentModel
from app.modules.workspace.infrastructure.models import WorkspaceModel

__all__ = [
    "DocumentChunkModel",
    "DocumentModel",
    "RefreshTokenModel",
    "UserModel",
    "WorkspaceModel",
]
