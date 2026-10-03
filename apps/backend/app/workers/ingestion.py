import logging
from uuid import UUID

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.infrastructure.ai.factory import create_embedding_provider
from app.infrastructure.database.session import async_session_factory
from app.infrastructure.storage import get_object_storage
from app.modules.knowledge.application.services.ingestion_service import (
    IngestionService,
    TransientIngestionError,
)
from app.modules.knowledge.infrastructure.models.document import DocumentModel, DocumentStatus

logger = logging.getLogger(__name__)


async def startup(ctx: dict) -> None:
    settings = get_settings()
    setup_logging(settings)
    ctx["settings"] = settings
    ctx["storage"] = get_object_storage(settings)
    ctx["embeddings"] = create_embedding_provider(settings)
    logger.info("Ingestion worker started")


async def shutdown(ctx: dict) -> None:
    embeddings = ctx.get("embeddings")
    close = getattr(embeddings, "aclose", None)
    if close is not None:
        await close()


async def ingest_document(ctx: dict, document_id: str) -> None:
    settings = ctx["settings"]
    async with async_session_factory() as session:
        service = IngestionService(
            session=session,
            storage=ctx["storage"],
            embeddings=ctx["embeddings"],
            settings=settings,
        )
        try:
            await service.process(UUID(document_id))
            await session.commit()
        except TransientIngestionError:
            await session.rollback()
            document = await session.get(DocumentModel, UUID(document_id))
            if document is not None:
                document.status = DocumentStatus.PENDING
                document.error_message = "Ingestion will be retried after a transient failure."
                await session.commit()
            raise


class WorkerSettings:
    functions = [ingest_document]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 2
    max_tries = 3
    job_timeout = 600
    keep_result = 3600
