from __future__ import annotations

import logging
from uuid import UUID

from app.core.config import Settings
from app.infrastructure.ai.chat.base import ChatProvider
from app.modules.knowledge.application.services.retrieval_service import (
    RetrievalService,
    RetrievedChunk,
)

logger = logging.getLogger(__name__)

REFUSAL_ANSWER = (
    "I don't have enough information in this workspace to answer that. "
    "Try uploading a relevant document or asking about something in your sources."
)

SYSTEM_PROMPT = (
    "You are KnowledgeOS, a retrieval-grounded assistant. "
    "Answer the user's question using ONLY the provided sources. "
    "If the sources are missing, incomplete, or unrelated, say you do not know. "
    "Do not use outside knowledge. "
    "Cite sources inline as [n] where n matches the source number. "
    "Keep answers concise and factual."
)


def should_refuse(chunks: list[RetrievedChunk], min_score: float) -> bool:
    if not chunks:
        return True
    return max(chunk.score for chunk in chunks) < min_score


def build_context(chunks: list[RetrievedChunk], max_chars: int) -> str:
    parts: list[str] = []
    used = 0
    for index, chunk in enumerate(chunks, start=1):
        block = f"[{index}] {chunk.filename} (chunk {chunk.chunk_index}):\n{chunk.content}"
        if used + len(block) > max_chars:
            remaining = max_chars - used
            if remaining < 80:
                break
            block = block[:remaining].rstrip() + "…"
        parts.append(block)
        used += len(block) + 2
        if used >= max_chars:
            break
    return "\n\n".join(parts)


def build_user_prompt(question: str, context: str) -> str:
    return (
        f"Sources:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the sources above. Cite claims with [n]."
    )


def extractive_answer(chunks: list[RetrievedChunk]) -> str:
    quotes = []
    for index, chunk in enumerate(chunks, start=1):
        excerpt = chunk.content.strip()
        if len(excerpt) > 500:
            excerpt = excerpt[:500].rstrip() + "…"
        quotes.append(f"[{index}] {chunk.filename}: {excerpt}")
    return (
        "I found the following in your workspace. "
        "No generative model is configured, so this is an extractive summary:\n\n"
        + "\n\n".join(quotes)
    )


class QAService:
    def __init__(
        self,
        retrieval: RetrievalService,
        chat: ChatProvider,
        settings: Settings,
    ) -> None:
        self._retrieval = retrieval
        self._chat = chat
        self._settings = settings

    async def ask(
        self,
        *,
        workspace_id: UUID,
        owner_id: UUID,
        question: str,
        top_k: int | None = None,
    ) -> tuple[str, bool, list[RetrievedChunk]]:
        chunks = await self._retrieval.search(
            workspace_id=workspace_id,
            owner_id=owner_id,
            query=question,
            top_k=top_k,
        )
        if should_refuse(chunks, self._settings.retrieval_min_score):
            return REFUSAL_ANSWER, False, chunks

        if not self._chat.supports_generation:
            return extractive_answer(chunks), True, chunks

        context = build_context(chunks, self._settings.rag_max_context_chars)
        user_prompt = build_user_prompt(question, context)
        try:
            answer = await self._chat.complete(system=SYSTEM_PROMPT, user=user_prompt)
        except Exception:
            logger.exception("Chat provider failed; using extractive fallback")
            return extractive_answer(chunks), True, chunks

        if not answer.strip():
            return extractive_answer(chunks), True, chunks
        return answer, True, chunks
