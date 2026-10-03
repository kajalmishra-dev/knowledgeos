from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    original_filename: str
    content_type: str
    source_type: str
    size_bytes: int
    status: str
    error_message: str | None
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=20)


class SearchHit(BaseModel):
    document_id: UUID
    filename: str
    chunk_index: int
    content: str
    score: float


class SearchResponse(BaseModel):
    query: str
    hits: list[SearchHit]


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=20)


class Citation(BaseModel):
    index: int
    document_id: UUID
    filename: str
    chunk_index: int
    score: float


class AskResponse(BaseModel):
    question: str
    answer: str
    grounded: bool
    citations: list[Citation]
    retrieved: list[SearchHit]
