from uuid import UUID

from app.core.config import Settings
from app.infrastructure.ai.embeddings.base import EmbeddingProvider
from app.infrastructure.database.session import async_session_factory
from app.infrastructure.storage.base import ObjectStorage


class InlineJobQueue:
    """Runs ingestion in-process. Used for tests and local demos without a worker."""

    def __init__(
        self,
        settings: Settings,
        storage: ObjectStorage,
        embeddings: EmbeddingProvider,
    ) -> None:
        self._settings = settings
        self._storage = storage
        self._embeddings = embeddings

    async def enqueue_ingestion(self, document_id: UUID) -> None:
        from app.modules.knowledge.application.services.ingestion_service import IngestionService

        async with async_session_factory() as session:
            service = IngestionService(
                session=session,
                storage=self._storage,
                embeddings=self._embeddings,
                settings=self._settings,
            )
            await service.process(document_id)
            await session.commit()

    async def healthy(self) -> bool:
        return True
