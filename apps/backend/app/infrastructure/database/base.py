from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

from app.infrastructure.database.conventions import NAMING_CONVENTION

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy ORM models."""

    metadata = metadata
