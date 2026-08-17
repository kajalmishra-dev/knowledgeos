import asyncio
from io import BytesIO

from minio import Minio
from minio.error import S3Error

from app.core.config import Settings


class MinioStorage:
    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.minio_bucket
        self._client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        payload = BytesIO(data)
        await asyncio.to_thread(
            self._client.put_object,
            self._bucket,
            key,
            payload,
            length=len(data),
            content_type=content_type,
        )

    async def get(self, key: str) -> bytes:
        def _read() -> bytes:
            response = self._client.get_object(self._bucket, key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()

        try:
            return await asyncio.to_thread(_read)
        except S3Error as exc:
            if exc.code in {"NoSuchKey", "NoSuchObject"}:
                raise FileNotFoundError(key) from exc
            raise

    async def delete(self, key: str) -> None:
        def _delete() -> None:
            try:
                self._client.remove_object(self._bucket, key)
            except S3Error as exc:
                if exc.code in {"NoSuchKey", "NoSuchObject"}:
                    return
                raise

        await asyncio.to_thread(_delete)

    async def healthy(self) -> bool:
        try:
            return bool(await asyncio.to_thread(self._client.bucket_exists, self._bucket))
        except Exception:
            return False
