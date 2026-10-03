from typing import Protocol
from uuid import UUID


class JobQueue(Protocol):
    async def enqueue_ingestion(self, document_id: UUID) -> None: ...

    async def healthy(self) -> bool: ...
