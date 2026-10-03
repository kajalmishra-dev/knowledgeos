from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import AppError
from app.dependencies.auth import get_current_user
from app.dependencies.database import get_db
from app.dependencies.knowledge import (
    get_chat_provider,
    get_document_service,
    get_embedding_provider,
)
from app.infrastructure.ai.chat.base import ChatProvider
from app.infrastructure.ai.embeddings.base import EmbeddingProvider
from app.modules.auth.infrastructure.models.user import UserModel
from app.modules.knowledge.application.services.document_service import DocumentService
from app.modules.knowledge.application.services.qa_service import QAService
from app.modules.knowledge.application.services.retrieval_service import RetrievalService
from app.modules.knowledge.schemas.document import (
    AskRequest,
    AskResponse,
    Citation,
    DocumentResponse,
    SearchHit,
    SearchRequest,
    SearchResponse,
)
from app.modules.workspace.application.services.workspace_service import WorkspaceNotFoundError

router = APIRouter(prefix="/workspaces/{workspace_id}/documents", tags=["documents"])
search_router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["rag"])


async def _read_upload(upload: UploadFile, max_bytes: int) -> bytes:
    buffer = bytearray()
    while True:
        chunk = await upload.read(64 * 1024)
        if not chunk:
            break
        buffer.extend(chunk)
        if len(buffer) > max_bytes:
            raise AppError(
                f"File exceeds maximum size of {max_bytes} bytes.",
                status_code=413,
            )
    return bytes(buffer)


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, AppError):
        return HTTPException(status_code=exc.status_code, detail=exc.message)
    if isinstance(exc, WorkspaceNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    raise exc


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    workspace_id: UUID,
    upload: UploadFile = File(..., alias="file"),
    current_user: UserModel = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
    settings: Settings = Depends(get_settings),
) -> DocumentResponse:
    try:
        data = await _read_upload(upload, settings.max_upload_bytes)
        document = await service.upload(
            workspace_id=workspace_id,
            owner_id=current_user.id,
            filename=upload.filename or "upload",
            content_type=upload.content_type,
            data=data,
        )
    except (AppError, WorkspaceNotFoundError) as exc:
        raise _http_error(exc) from exc
    return DocumentResponse.model_validate(document)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    workspace_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> list[DocumentResponse]:
    try:
        documents = await service.list_for_workspace(workspace_id, current_user.id)
    except (AppError, WorkspaceNotFoundError) as exc:
        raise _http_error(exc) from exc
    return [DocumentResponse.model_validate(item) for item in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    workspace_id: UUID,
    document_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    try:
        document = await service.get_for_owner(workspace_id, document_id, current_user.id)
    except (AppError, WorkspaceNotFoundError) as exc:
        raise _http_error(exc) from exc
    return DocumentResponse.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    workspace_id: UUID,
    document_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> None:
    try:
        await service.delete(workspace_id, document_id, current_user.id)
    except (AppError, WorkspaceNotFoundError) as exc:
        raise _http_error(exc) from exc


@router.post("/{document_id}/reprocess", response_model=DocumentResponse)
async def reprocess_document(
    workspace_id: UUID,
    document_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    try:
        document = await service.reprocess(workspace_id, document_id, current_user.id)
    except (AppError, WorkspaceNotFoundError) as exc:
        raise _http_error(exc) from exc
    return DocumentResponse.model_validate(document)


@search_router.post("/search", response_model=SearchResponse)
async def search_workspace(
    workspace_id: UUID,
    payload: SearchRequest,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    embeddings: EmbeddingProvider = Depends(get_embedding_provider),
    settings: Settings = Depends(get_settings),
) -> SearchResponse:
    retrieval = RetrievalService(session, embeddings, settings)
    try:
        hits = await retrieval.search(
            workspace_id=workspace_id,
            owner_id=current_user.id,
            query=payload.query,
            top_k=payload.top_k,
        )
    except WorkspaceNotFoundError as exc:
        raise _http_error(exc) from exc
    return SearchResponse(
        query=payload.query,
        hits=[
            SearchHit(
                document_id=hit.document_id,
                filename=hit.filename,
                chunk_index=hit.chunk_index,
                content=hit.content,
                score=round(hit.score, 4),
            )
            for hit in hits
        ],
    )


@search_router.post("/ask", response_model=AskResponse)
async def ask_workspace(
    workspace_id: UUID,
    payload: AskRequest,
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    embeddings: EmbeddingProvider = Depends(get_embedding_provider),
    chat: ChatProvider = Depends(get_chat_provider),
    settings: Settings = Depends(get_settings),
) -> AskResponse:
    retrieval = RetrievalService(session, embeddings, settings)
    qa = QAService(retrieval, chat, settings)
    try:
        answer, grounded, chunks = await qa.ask(
            workspace_id=workspace_id,
            owner_id=current_user.id,
            question=payload.question,
            top_k=payload.top_k,
        )
    except WorkspaceNotFoundError as exc:
        raise _http_error(exc) from exc

    retrieved = [
        SearchHit(
            document_id=hit.document_id,
            filename=hit.filename,
            chunk_index=hit.chunk_index,
            content=hit.content,
            score=round(hit.score, 4),
        )
        for hit in chunks
    ]
    citations = [
        Citation(
            index=index,
            document_id=hit.document_id,
            filename=hit.filename,
            chunk_index=hit.chunk_index,
            score=round(hit.score, 4),
        )
        for index, hit in enumerate(chunks, start=1)
    ]
    return AskResponse(
        question=payload.question,
        answer=answer,
        grounded=grounded,
        citations=citations if grounded else [],
        retrieved=retrieved,
    )
