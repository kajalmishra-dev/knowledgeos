"""FastAPI dependency injection providers."""

from app.dependencies.database import get_db

__all__ = ["get_db"]
