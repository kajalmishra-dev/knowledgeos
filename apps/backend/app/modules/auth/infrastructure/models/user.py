from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base
from app.infrastructure.database.mixins import BaseModel

if TYPE_CHECKING:
    from app.modules.auth.infrastructure.models.refresh_token import RefreshTokenModel
    from app.modules.workspace.infrastructure.models.workspace import WorkspaceModel


class UserModel(BaseModel, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    refresh_tokens: Mapped[list[RefreshTokenModel]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    workspaces: Mapped[list[WorkspaceModel]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )
