from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.infrastructure.ai.embeddings.base import EmbeddingProvider
from app.modules.knowledge.infrastructure.models.chunk import DocumentChunkModel
from app.modules.knowledge.infrastructure.models.document import DocumentModel, DocumentStatus
from app.modules.workspace.application.services.workspace_service import WorkspaceService


@dataclass(frozen=True)
class RetrievedChunk:
    document_id: UUID
    filename: str
    chunk_index: int
    content: str
    score: float


class RetrievalService:
    def __init__(
        self,
        session: AsyncSession,
        embeddings: EmbeddingProvider,
        settings: Settings,
    ) -> None:
        self._session = session
        self._embeddings = embeddings
        self._settings = settings
        self._workspaces = WorkspaceService(session)

    async def search(
        self,
        *,
        workspace_id: UUID,
        owner_id: UUID,
        query: str,
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        await self._workspaces.get_for_owner(workspace_id, owner_id)
        limit = top_k or self._settings.retrieval_top_k
        query_vector = (await self._embeddings.embed([query]))[0]
        distance = DocumentChunkModel.embedding.cosine_distance(query_vector)
        stmt = (
            select(
                DocumentChunkModel,
                DocumentModel.original_filename,
                (1 - distance).label("score"),
            )
            .join(DocumentModel, DocumentModel.id == DocumentChunkModel.document_id)
            .where(DocumentChunkModel.workspace_id == workspace_id)
            .where(DocumentModel.status == DocumentStatus.COMPLETED)
            .order_by(distance)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        hits: list[RetrievedChunk] = []
        for chunk, filename, score in result.all():
            hits.append(
                RetrievedChunk(
                    document_id=chunk.document_id,
                    filename=filename,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    score=float(score),
                )
            )
        return hits
