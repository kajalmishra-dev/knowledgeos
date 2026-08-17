from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.infrastructure.ai.embeddings.base import EmbeddingProvider
from app.infrastructure.storage.base import ObjectStorage
from app.modules.knowledge.application.chunking import chunk_text
from app.modules.knowledge.infrastructure.models.chunk import DocumentChunkModel
from app.modules.knowledge.infrastructure.models.document import DocumentModel, DocumentStatus
from app.modules.knowledge.infrastructure.parsers import ParseError, parse_document

logger = logging.getLogger(__name__)


class TransientIngestionError(Exception):
    """Storage/embedding/database glitches that the worker should retry."""


class IngestionService:
    def __init__(
        self,
        session: AsyncSession,
        storage: ObjectStorage,
        embeddings: EmbeddingProvider,
        settings: Settings,
    ) -> None:
        self._session = session
        self._storage = storage
        self._embeddings = embeddings
        self._settings = settings

    async def process(self, document_id: UUID) -> None:
        document = await self._session.get(DocumentModel, document_id)
        if document is None:
            logger.warning("Ingestion skipped; document_id=%s not found", document_id)
            return

        document.status = DocumentStatus.PROCESSING
        document.error_message = None
        await self._session.flush()

        try:
            data = await self._storage.get(document.storage_key)
            text = parse_document(
                data=data,
                source_type=document.source_type,
                filename=document.original_filename,
            )
            text = text.strip()
            if not text:
                raise ParseError(f"No extractable text in '{document.original_filename}'.")

            chunks = chunk_text(
                text,
                chunk_size=self._settings.chunk_size,
                overlap=self._settings.chunk_overlap,
            )
            if not chunks:
                raise ParseError(f"No chunks produced for '{document.original_filename}'.")

            vectors = await self._embeddings.embed(chunks)
            if len(vectors) != len(chunks):
                raise RuntimeError("Embedding provider returned the wrong number of vectors.")

            await self._session.execute(
                delete(DocumentChunkModel).where(DocumentChunkModel.document_id == document.id)
            )
            for index, (content, embedding) in enumerate(zip(chunks, vectors, strict=True)):
                self._session.add(
                    DocumentChunkModel(
                        document_id=document.id,
                        workspace_id=document.workspace_id,
                        chunk_index=index,
                        content=content,
                        embedding=embedding,
                        token_count=_estimate_tokens(content),
                    )
                )

            document.status = DocumentStatus.COMPLETED
            document.chunk_count = len(chunks)
            document.error_message = None
            await self._session.flush()
            logger.info(
                "Ingestion completed document_id=%s chunks=%s",
                document.id,
                len(chunks),
            )
        except ParseError as exc:
            await self._mark_failed(document, str(exc))
        except FileNotFoundError as exc:
            await self._mark_failed(document, f"Stored object missing: {exc}")
        except Exception as exc:
            logger.exception("Transient ingestion error document_id=%s", document_id)
            raise TransientIngestionError(str(exc)) from exc

    async def _mark_failed(self, document: DocumentModel, message: str) -> None:
        logger.warning("Ingestion failed document_id=%s error=%s", document.id, message)
        document.status = DocumentStatus.FAILED
        document.chunk_count = 0
        document.error_message = message[:2000]
        await self._session.execute(
            delete(DocumentChunkModel).where(DocumentChunkModel.document_id == document.id)
        )
        await self._session.flush()


def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))
