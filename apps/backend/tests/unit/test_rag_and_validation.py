from uuid import uuid4

import pytest

from app.core.exceptions import AppError
from app.infrastructure.ai.embeddings.local import LocalEmbeddingProvider
from app.modules.knowledge.application.services.document_service import _resolve_file
from app.modules.knowledge.application.services.qa_service import (
    REFUSAL_ANSWER,
    RetrievedChunk,
    extractive_answer,
    should_refuse,
)


@pytest.mark.asyncio
async def test_local_embeddings_are_similar_for_overlapping_text() -> None:
    provider = LocalEmbeddingProvider(64)
    vectors = await provider.embed(
        [
            "Paris is the capital of France",
            "The capital of France is Paris",
            "Quantum chromodynamics lattice gluon plasma",
        ]
    )

    def cosine(left: list[float], right: list[float]) -> float:
        return sum(a * b for a, b in zip(left, right, strict=True))

    assert cosine(vectors[0], vectors[1]) > cosine(vectors[0], vectors[2])


def test_should_refuse_when_scores_are_low() -> None:
    chunks = [
        RetrievedChunk(
            document_id=uuid4(),
            filename="a.md",
            chunk_index=0,
            content="hello",
            score=0.05,
        )
    ]
    assert should_refuse(chunks, min_score=0.18) is True
    assert should_refuse([], min_score=0.18) is True


def test_extractive_answer_includes_citations() -> None:
    chunks = [
        RetrievedChunk(
            document_id=uuid4(),
            filename="notes.md",
            chunk_index=0,
            content="Paris is the capital of France.",
            score=0.9,
        )
    ]
    answer = extractive_answer(chunks)
    assert "[1] notes.md" in answer
    assert "Paris" in answer
    assert REFUSAL_ANSWER.startswith("I don't have enough information")


def test_resolve_file_rejects_unsupported_extension() -> None:
    with pytest.raises(AppError) as exc:
        _resolve_file("payload.exe", "application/octet-stream")
    assert exc.value.status_code == 415


def test_resolve_file_accepts_markdown() -> None:
    name, content_type, source_type = _resolve_file("My Notes.md", "text/markdown")
    assert name.endswith(".md")
    assert content_type == "text/markdown"
    assert source_type == "markdown"
