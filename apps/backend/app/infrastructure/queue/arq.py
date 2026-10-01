from uuid import UUID

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.core.config import Settings


class ArqJobQueue:
    def __init__(self, settings: Settings) -> None:
        self._redis_settings = RedisSettings.from_dsn(settings.redis_url)
        self._pool: ArqRedis | None = None

    async def _get_pool(self) -> ArqRedis:
        if self._pool is None or self._pool.closed:
            self._pool = await create_pool(self._redis_settings)
        return self._pool

    async def enqueue_ingestion(self, document_id: UUID) -> None:
        pool = await self._get_pool()
        await pool.enqueue_job("ingest_document", str(document_id))

    async def healthy(self) -> bool:
        try:
            pool = await self._get_pool()
            return bool(await pool.ping())
        except Exception:
            return False

    async def aclose(self) -> None:
        if self._pool is not None and not self._pool.closed:
            await self._pool.aclose()
