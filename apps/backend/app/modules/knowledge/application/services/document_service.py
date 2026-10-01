from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import AppError
from app.infrastructure.queue.base import JobQueue
from app.infrastructure.storage.base import ObjectStorage
from app.modules.knowledge.infrastructure.models.document import DocumentModel, DocumentStatus
from app.modules.workspace.application.services.workspace_service import WorkspaceService

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS: dict[str, tuple[str, str]] = {
    ".pdf": ("application/pdf", "pdf"),
    ".md": ("text/markdown", "markdown"),
    ".markdown": ("text/markdown", "markdown"),
    ".txt": ("text/plain", "text"),
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "docx",
    ),
}

_UNSAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


class DocumentService:
    def __init__(
        self,
        session: AsyncSession,
        storage: ObjectStorage,
        queue: JobQueue,
        settings: Settings,
    ) -> None:
        self._session = session
        self._storage = storage
        self._queue = queue
        self._settings = settings
        self._workspaces = WorkspaceService(session)

    async def upload(
        self,
        *,
        workspace_id: UUID,
        owner_id: UUID,
        filename: str,
        content_type: str | None,
        data: bytes,
    ) -> DocumentModel:
        await self._workspaces.get_for_owner(workspace_id, owner_id)
        if not data:
            raise AppError("Empty files are not allowed.", status_code=400)
        if len(data) > self._settings.max_upload_bytes:
            raise AppError(
                f"File exceeds maximum size of {self._settings.max_upload_bytes} bytes.",
                status_code=413,
            )

        safe_name, resolved_type, source_type = _resolve_file(filename, content_type)
        document = DocumentModel(
            id=uuid4(),
            workspace_id=workspace_id,
            owner_id=owner_id,
            original_filename=safe_name,
            content_type=resolved_type,
            source_type=source_type,
            storage_key="pending",
            size_bytes=len(data),
            checksum_sha256=hashlib.sha256(data).hexdigest(),
            status=DocumentStatus.PENDING,
            error_message=None,
            chunk_count=0,
        )
        document.storage_key = f"{workspace_id}/{document.id}/{safe_name}"
        await self._storage.put(document.storage_key, data, resolved_type)
        self._session.add(document)
        await self._session.commit()
        await self._session.refresh(document)

        try:
            await self._queue.enqueue_ingestion(document.id)
        except Exception:
            logger.exception("Failed to enqueue ingestion for document_id=%s", document.id)
            document.status = DocumentStatus.FAILED
            document.error_message = "Failed to enqueue ingestion job."
            await self._session.commit()
            await self._session.refresh(document)
            return document

        await self._session.refresh(document)
        return document

    async def list_for_workspace(self, workspace_id: UUID, owner_id: UUID) -> list[DocumentModel]:
        await self._workspaces.get_for_owner(workspace_id, owner_id)
        result = await self._session.execute(
            select(DocumentModel)
            .where(DocumentModel.workspace_id == workspace_id)
            .order_by(DocumentModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_for_owner(
        self, workspace_id: UUID, document_id: UUID, owner_id: UUID
    ) -> DocumentModel:
        await self._workspaces.get_for_owner(workspace_id, owner_id)
        document = await self._session.get(DocumentModel, document_id)
        if document is None or document.workspace_id != workspace_id:
            raise AppError("Document not found.", status_code=404)
        return document

    async def delete(self, workspace_id: UUID, document_id: UUID, owner_id: UUID) -> None:
        document = await self.get_for_owner(workspace_id, document_id, owner_id)
        await self._storage.delete(document.storage_key)
        await self._session.delete(document)
        await self._session.flush()

    async def reprocess(
        self, workspace_id: UUID, document_id: UUID, owner_id: UUID
    ) -> DocumentModel:
        document = await self.get_for_owner(workspace_id, document_id, owner_id)
        document.status = DocumentStatus.PENDING
        document.error_message = None
        await self._session.commit()
        await self._queue.enqueue_ingestion(document.id)
        await self._session.refresh(document)
        return document

    async def delete_all_in_workspace(self, workspace_id: UUID, owner_id: UUID) -> None:
        documents = await self.list_for_workspace(workspace_id, owner_id)
        for document in documents:
            await self._storage.delete(document.storage_key)
            await self._session.delete(document)
        await self._session.flush()


def _resolve_file(filename: str, content_type: str | None) -> tuple[str, str, str]:
    original = Path(filename or "upload").name
    safe_name = _UNSAFE_FILENAME.sub("_", original).strip("._")[:200] or "upload"
    suffix = Path(safe_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise AppError(
            "Unsupported file type. Allowed: PDF, Markdown, TXT, DOCX.",
            status_code=415,
        )
    default_type, source_type = ALLOWED_EXTENSIONS[suffix]
    resolved_type = content_type.split(";")[0].strip().lower() if content_type else default_type
    if resolved_type in {"application/octet-stream", "binary/octet-stream", ""}:
        resolved_type = default_type
    allowed_types = {item[0] for item in ALLOWED_EXTENSIONS.values()}
    if resolved_type not in allowed_types and resolved_type != default_type:
        # Use the extension when the client sends a generic MIME type; reject explicit mismatches.
        if resolved_type not in allowed_types:
            resolved_type = default_type
    return safe_name, default_type, source_type
