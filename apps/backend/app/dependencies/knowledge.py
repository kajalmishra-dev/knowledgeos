from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.dependencies.database import get_db
from app.infrastructure.ai.chat.base import ChatProvider
from app.infrastructure.ai.embeddings.base import EmbeddingProvider
from app.infrastructure.ai.factory import create_chat_provider, create_embedding_provider
from app.infrastructure.queue.arq import ArqJobQueue
from app.infrastructure.queue.base import JobQueue
from app.infrastructure.queue.inline import InlineJobQueue
from app.infrastructure.storage import get_object_storage
from app.infrastructure.storage.base import ObjectStorage
from app.modules.knowledge.application.services.document_service import DocumentService

_arq_queue: ArqJobQueue | None = None
_embedding_provider: EmbeddingProvider | None = None
_chat_provider: ChatProvider | None = None


def get_storage(settings: Settings = Depends(get_settings)) -> ObjectStorage:
    return get_object_storage(settings)


def get_embedding_provider(settings: Settings = Depends(get_settings)) -> EmbeddingProvider:
    global _embedding_provider
    if _embedding_provider is None:
        _embedding_provider = create_embedding_provider(settings)
    return _embedding_provider


def get_chat_provider(settings: Settings = Depends(get_settings)) -> ChatProvider:
    global _chat_provider
    if _chat_provider is None:
        _chat_provider = create_chat_provider(settings)
    return _chat_provider


def get_job_queue(
    settings: Settings = Depends(get_settings),
    storage: ObjectStorage = Depends(get_storage),
    embeddings: EmbeddingProvider = Depends(get_embedding_provider),
) -> JobQueue:
    global _arq_queue
    if settings.ingestion_queue == "inline":
        return InlineJobQueue(settings, storage, embeddings)
    if _arq_queue is None:
        _arq_queue = ArqJobQueue(settings)
    return _arq_queue


def get_document_service(
    session: AsyncSession = Depends(get_db),
    storage: ObjectStorage = Depends(get_storage),
    queue: JobQueue = Depends(get_job_queue),
    settings: Settings = Depends(get_settings),
) -> DocumentService:
    return DocumentService(session, storage, queue, settings)
