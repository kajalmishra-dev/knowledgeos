from app.core.config import Settings
from app.infrastructure.storage.base import ObjectStorage
from app.infrastructure.storage.memory import InMemoryStorage
from app.infrastructure.storage.minio import MinioStorage

_memory_storage: InMemoryStorage | None = None
_minio_storage: MinioStorage | None = None


def get_object_storage(settings: Settings) -> ObjectStorage:
    global _memory_storage, _minio_storage
    if settings.storage_backend == "memory":
        if _memory_storage is None:
            _memory_storage = InMemoryStorage()
        return _memory_storage
    if _minio_storage is None:
        _minio_storage = MinioStorage(settings)
    return _minio_storage
