from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base
from app.infrastructure.database.mixins import BaseModel

if TYPE_CHECKING:
    from app.modules.auth.infrastructure.models.user import UserModel
    from app.modules.knowledge.infrastructure.models.document import DocumentModel


class WorkspaceModel(BaseModel, Base):
    __tablename__ = "workspaces"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    owner: Mapped[UserModel] = relationship(back_populates="workspaces")
    documents: Mapped[list[DocumentModel]] = relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
